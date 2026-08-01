"""
GET /api/drawings/{drawing_id}  — returns image URL + extracted JSON.
PUT /api/drawings/{drawing_id}/review — accepts corrected JSON, marks as
    verified, and triggers FAISS indexing.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError

from app.schemas import (
    DrawingDetail,
    ExtractedDrawingData,
    ExtractionResult,
    ReviewRequest,
    ReviewResponse,
)
from app.services.drawing_service import STORAGE_ROOT
from app.services import vector_store

router = APIRouter(prefix="/drawings", tags=["drawings"])


# ── GET /api/drawings/{drawing_id} ────────────────────────────────────────────


@router.get(
    "/{drawing_id}",
    response_model=DrawingDetail,
    summary="Get image URL and extracted data for a drawing",
)
async def get_drawing(drawing_id: str) -> DrawingDetail:
    """
    Returns the preview image URL and the latest extraction result
    (or None if extraction hasn't run yet) for the given drawing.
    """
    drawing_dir = _require_dir(drawing_id)

    # Load extraction if available
    extraction: ExtractionResult | None = None
    result_path = drawing_dir / "extraction.json"
    if result_path.is_file():
        extraction = ExtractionResult.model_validate_json(
            result_path.read_text(encoding="utf-8")
        )

    # Load review flag if present
    verified = (drawing_dir / "verified.flag").is_file()

    return DrawingDetail(
        drawing_id=drawing_id,
        preview_url=f"/api/drawing/{drawing_id}/preview",
        extraction=extraction,
        verified=verified,
    )


# ── PUT /api/drawings/{drawing_id}/review ─────────────────────────────────────


@router.put(
    "/{drawing_id}/review",
    response_model=ReviewResponse,
    summary="Submit corrected extraction data and mark drawing as verified",
    status_code=status.HTTP_200_OK,
)
async def review_drawing(
    drawing_id: str,
    body: ReviewRequest,
) -> ReviewResponse:
    """
    Accepts a (human-corrected) ``ExtractedDrawingData`` payload,
    overwrites the stored ``extraction.json`` with ``status='ok'``,
    writes a ``verified.flag`` sentinel file, and adds/updates the
    drawing's embedding in the FAISS similarity index.
    """
    drawing_dir = _require_dir(drawing_id)

    # Build a verified ExtractionResult from the submitted data
    now = datetime.now(timezone.utc).isoformat()
    result = ExtractionResult(
        drawing_id=drawing_id,
        status="ok",
        data=body.data,
        error_message=None,
        raw_response=None,
        extracted_at=now,
    )

    # Persist
    (drawing_dir / "extraction.json").write_text(
        result.model_dump_json(indent=2), encoding="utf-8"
    )
    (drawing_dir / "verified.flag").write_text(now, encoding="utf-8")

    # Index into FAISS
    label = body.data.part_name or drawing_id
    await vector_store.add(drawing_id, label, body.data)

    return ReviewResponse(
        drawing_id=drawing_id,
        verified=True,
        indexed=True,
        message=f"Drawing '{drawing_id}' verified and indexed.",
    )


# ── Helper ─────────────────────────────────────────────────────────────────────


def _require_dir(drawing_id: str):
    d = STORAGE_ROOT / drawing_id
    if not d.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing '{drawing_id}' not found.",
        )
    return d
