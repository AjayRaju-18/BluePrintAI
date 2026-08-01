"""
POST /api/upload  — ingest a drawing file and return a drawing_id.
GET  /api/drawing/{drawing_id}/preview — serve the rendered PNG.
GET  /api/drawing/{drawing_id}/meta    — return stored DrawingMeta.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.schemas import DrawingMeta, UploadResponse
from app.services.drawing_service import STORAGE_ROOT, ingest_upload

router = APIRouter(tags=["upload"])

_ACCEPTED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/webp",
}

_MAX_BYTES = 50 * 1024 * 1024  # 50 MB — generous for demo PDFs


# ── POST /api/upload ───────────────────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=UploadResponse,
    summary="Upload a drawing (PDF or image) for processing",
    status_code=status.HTTP_201_CREATED,
)
async def upload_drawing(
    file: UploadFile = File(..., description="PDF or raster image of the drawing."),
) -> UploadResponse:
    """
    Accepts a PDF or image upload and:
    - Detects whether the PDF is vector-text or raster-scanned
    - Renders page 1 to a 300-DPI PNG
    - Extracts the text layer from vector PDFs
    - Stores everything under `/backend/storage/<drawing_id>/`

    Returns a `drawing_id` to reference in subsequent API calls.
    """
    if file.content_type not in _ACCEPTED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported type '{file.content_type}'. Accepted: {sorted(_ACCEPTED_TYPES)}",
        )

    raw = await file.read()

    if len(raw) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds 50 MB limit ({len(raw) / 1_048_576:.1f} MB received).",
        )

    meta: DrawingMeta = ingest_upload(
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        file_bytes=raw,
    )

    return UploadResponse(
        drawing_id=meta.drawing_id,
        original_filename=meta.original_filename,
        pdf_type=meta.pdf_type,
        has_text_layer=meta.has_text_layer,
        page_count=meta.page_count,
        render_url=f"/api/drawing/{meta.drawing_id}/preview",
        created_at=meta.created_at,
    )


# ── GET /api/drawing/{drawing_id}/preview ─────────────────────────────────────


@router.get(
    "/drawing/{drawing_id}/preview",
    summary="Serve the rendered PNG preview for a drawing",
    response_class=FileResponse,
)
async def drawing_preview(drawing_id: str) -> FileResponse:
    """Returns the 300-DPI PNG render of page 1."""
    png_path = _require_file(drawing_id, "page_01.png")
    return FileResponse(str(png_path), media_type="image/png")


# ── GET /api/drawing/{drawing_id}/meta ────────────────────────────────────────


@router.get(
    "/drawing/{drawing_id}/meta",
    response_model=DrawingMeta,
    summary="Return stored metadata for a drawing",
)
async def drawing_meta(drawing_id: str) -> DrawingMeta:
    """Returns the DrawingMeta that was stored during upload."""
    meta_path = _require_file(drawing_id, "meta.json")
    return DrawingMeta.model_validate_json(meta_path.read_text(encoding="utf-8"))


# ── Helpers ────────────────────────────────────────────────────────────────────


def _drawing_dir(drawing_id: str) -> Path:
    d = STORAGE_ROOT / drawing_id
    if not d.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing '{drawing_id}' not found.",
        )
    return d


def _require_file(drawing_id: str, filename: str) -> Path:
    p = _drawing_dir(drawing_id) / filename
    if not p.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found for drawing '{drawing_id}'.",
        )
    return p
