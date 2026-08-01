"""
POST /api/extract/{drawing_id}

Sends the stored PNG render (plus text layer if available) to the
Hugging Face Inference API (Qwen/Qwen2.5-VL-7B-Instruct) and returns
structured ExtractedDrawingData parsed from the model's JSON output.

On any failure (network, bad JSON, schema mismatch) the endpoint returns
HTTP 200 with status='error' and a clear human-readable message rather
than retrying. The caller decides what to do.

Also exposes:
  GET /api/extract/{drawing_id}/result — retrieve a previously stored result.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, status

from app.schemas import ExtractionResult
from app.services.extraction_service import run_extraction
from app.services.drawing_service import STORAGE_ROOT

router = APIRouter(tags=["extraction"])


# ── POST /api/extract/{drawing_id} ─────────────────────────────────────────────


@router.post(
    "/extract/{drawing_id}",
    response_model=ExtractionResult,
    summary="Run AI extraction on an uploaded drawing",
    status_code=status.HTTP_200_OK,
)
async def extract_drawing(drawing_id: str) -> ExtractionResult:
    """
    Sends the 300-DPI PNG (and optional text layer) for *drawing_id* to the
    Hugging Face Inference API running **Qwen/Qwen2.5-VL-7B-Instruct**.

    The model is instructed to return a JSON object matching the shared
    `ExtractedDrawingData` schema with normalized bounding boxes.

    - **On success** → `status='ok'`, `data` contains the parsed extraction.
    - **On failure** → `status='error'`, `error_message` explains why.
      `raw_response` is included when the model returned something but it
      failed to parse, so you can inspect what went wrong.

    The result is always written to `storage/<drawing_id>/extraction.json`.
    """
    _require_drawing(drawing_id)
    result = await run_extraction(drawing_id)
    return result


# ── GET /api/extract/{drawing_id}/result ──────────────────────────────────────


@router.get(
    "/extract/{drawing_id}/result",
    response_model=ExtractionResult,
    summary="Retrieve a previously stored extraction result",
)
async def get_extraction_result(drawing_id: str) -> ExtractionResult:
    """Returns the `ExtractionResult` that was persisted during a prior extraction call."""
    _require_drawing(drawing_id)
    result_path = STORAGE_ROOT / drawing_id / "extraction.json"
    if not result_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No extraction result found for drawing '{drawing_id}'. Run POST /api/extract/{drawing_id} first.",
        )
    return ExtractionResult.model_validate_json(result_path.read_text(encoding="utf-8"))


# ── Helpers ────────────────────────────────────────────────────────────────────


def _require_drawing(drawing_id: str) -> None:
    if not (STORAGE_ROOT / drawing_id).is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Drawing '{drawing_id}' not found. Upload it first via POST /api/upload.",
        )
