"""
POST /api/extract — stub router.

Accepts a multipart file upload (PDF or image) and returns a placeholder
ExtractedDrawingData response. Business logic will be implemented in a
future milestone.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas import (
    Dimension,
    ExtractedDrawingData,
    GDTCallout,
    SurfaceFinish,
)

router = APIRouter(tags=["extraction"])

_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/webp",
}


@router.post(
    "/extract",
    response_model=ExtractedDrawingData,
    summary="Extract structured data from an engineering drawing",
    status_code=status.HTTP_200_OK,
)
async def extract_drawing(
    file: UploadFile = File(..., description="PDF or raster image of the drawing."),
) -> ExtractedDrawingData:
    """
    **[STUB]** Accepts a drawing file and returns placeholder extracted data.

    In the real implementation this endpoint will:
    1. Decode the uploaded PDF/image with PyMuPDF / Pillow.
    2. Send the page image to a Hugging Face vision-language model via httpx.
    3. Parse the model response into an `ExtractedDrawingData` object.
    4. Return the structured result to the frontend.
    """
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported file type '{file.content_type}'. "
                f"Accepted types: {sorted(_ALLOWED_CONTENT_TYPES)}"
            ),
        )

    # ── Placeholder response (no real processing) ──────────────────────────────
    return ExtractedDrawingData(
        part_name="[STUB] Part Name",
        material="[STUB] Material",
        scale="1:1",
        revision="A",
        quantity="1",
        dimensions=[
            Dimension(value="25.40", tolerance="±0.05", bbox=[0.1, 0.2, 0.05, 0.03])
        ],
        gdt_callouts=[
            GDTCallout(
                characteristic="flatness",
                tolerance_zone="0.02",
                datum_refs="A",
                bbox=[0.3, 0.4, 0.08, 0.04],
            )
        ],
        surface_finish=[
            SurfaceFinish(value="Ra 1.6", bbox=[0.5, 0.6, 0.04, 0.03])
        ],
        notes=["[STUB] This is a placeholder response. No real extraction performed."],
    )
