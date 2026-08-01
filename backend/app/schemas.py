"""
Pydantic models mirroring shared/extracted_drawing_data.schema.json.

All bbox fields are [x, y, w, h] normalized to [0, 1] relative to image size.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ── Shared type alias ──────────────────────────────────────────────────────────

BBox = Annotated[
    list[float],
    Field(
        min_length=4,
        max_length=4,
        description="Normalized bounding box [x, y, w, h] in [0, 1].",
    ),
]


# ── Sub-models ─────────────────────────────────────────────────────────────────


class Dimension(BaseModel):
    """A single dimensional annotation on the drawing."""

    value: str = Field(..., description="Nominal dimension value (e.g. '25.4').")
    tolerance: str = Field(..., description="Tolerance string (e.g. '±0.05', 'REF').")
    bbox: BBox


class GDTCallout(BaseModel):
    """A GD&T feature control frame annotation."""

    characteristic: str = Field(
        ..., description="GD&T characteristic (e.g. 'flatness', 'true position')."
    )
    tolerance_zone: str = Field(
        ..., description="Tolerance zone value (e.g. '0.05', 'Ø0.1 M')."
    )
    datum_refs: str = Field(
        ..., description="Referenced datums as a string (e.g. 'A|B|C', '')."
    )
    bbox: BBox


class SurfaceFinish(BaseModel):
    """A surface finish / roughness annotation."""

    value: str = Field(
        ..., description="Surface roughness value (e.g. 'Ra 1.6', '63 μin')."
    )
    bbox: BBox


# ── Top-level extraction model ─────────────────────────────────────────────────


class ExtractedDrawingData(BaseModel):
    """Complete extraction result for one engineering drawing."""

    part_name: str = Field(..., description="Name or identifier of the part.")
    material: str = Field(..., description="Material specification.")
    scale: str = Field(..., description="Drawing scale (e.g. '1:1', 'NTS').")
    revision: str = Field(..., description="Drawing revision identifier.")
    quantity: str = Field(..., description="Required quantity.")
    dimensions: list[Dimension] = Field(default_factory=list)
    gdt_callouts: list[GDTCallout] = Field(default_factory=list)
    surface_finish: list[SurfaceFinish] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ── Upload / storage models ────────────────────────────────────────────────────


class DrawingMeta(BaseModel):
    """
    Metadata written to storage/<drawing_id>/meta.json after upload.
    Also returned as part of UploadResponse.
    """

    drawing_id: str = Field(..., description="Unique hex ID for this drawing.")
    original_filename: str = Field(..., description="Original uploaded filename.")
    content_type: str = Field(..., description="MIME type of the upload.")
    pdf_type: Literal["vector", "raster"] | None = Field(
        None,
        description=(
            "'vector' if the PDF has a selectable text layer, "
            "'raster' if scanned/image-only, "
            "None for direct image uploads."
        ),
    )
    has_text_layer: bool = Field(
        False,
        description="True when a text_layer.txt was extracted from a vector PDF.",
    )
    page_count: int | None = Field(None, description="Total pages (PDFs only).")
    render_png: str = Field(
        ..., description="Filename of the 300-DPI PNG render inside the storage dir."
    )
    text_layer_file: str | None = Field(
        None, description="Filename of the extracted text layer, if any."
    )
    created_at: str = Field(..., description="ISO-8601 UTC timestamp of ingestion.")


class UploadResponse(BaseModel):
    """Response body for POST /api/upload."""

    drawing_id: str = Field(..., description="ID to pass to subsequent API calls.")
    original_filename: str
    pdf_type: Literal["vector", "raster"] | None
    has_text_layer: bool
    page_count: int | None
    render_url: str = Field(
        ...,
        description="URL to fetch the rendered PNG preview.",
    )
    created_at: str


# ── Extraction result model ────────────────────────────────────────────────────


class ExtractionResult(BaseModel):
    """
    Envelope returned by POST /api/extract/{drawing_id}.

    On success: status='ok',  data=ExtractedDrawingData, error_message=None.
    On failure: status='error', data=None, error_message=<human-readable reason>.
    """

    drawing_id: str
    status: Literal["ok", "error"]
    data: ExtractedDrawingData | None = None
    error_message: str | None = Field(
        None,
        description="Human-readable failure reason (only when status='error').",
    )
    raw_response: str | None = Field(
        None,
        description="Raw model output — present on parse errors to aid debugging.",
    )
    extracted_at: str = Field(..., description="ISO-8601 UTC timestamp.")


# ── Drawing detail (GET /api/drawings/{id}) ────────────────────────────────────


class DrawingDetail(BaseModel):
    """Combined image + extraction response for a single drawing."""

    drawing_id: str
    preview_url: str = Field(..., description="URL to the 300-DPI PNG preview image.")
    extraction: ExtractionResult | None = Field(
        None,
        description="Latest extraction result, or None if extraction hasn't run yet.",
    )
    verified: bool = Field(
        False,
        description="True if a human has reviewed and confirmed the extraction.",
    )


# ── Review models (PUT /api/drawings/{id}/review) ─────────────────────────────


class ReviewRequest(BaseModel):
    """Body for submitting a corrected extraction."""

    data: ExtractedDrawingData = Field(
        ..., description="The (human-corrected) extraction data to store and index."
    )


class ReviewResponse(BaseModel):
    """Confirmation that the review was accepted and indexed."""

    drawing_id: str
    verified: bool
    indexed: bool
    message: str


# ── Demo seed models (GET /api/demo/seed) ─────────────────────────────────────


class SeededExample(BaseModel):
    """Metadata about one seeded demo example."""

    drawing_id: str
    label: str
    description: str
    tags: list[str] = Field(default_factory=list)
    preview_url: str
    extraction_url: str


class SeedResult(BaseModel):
    """Response from GET /api/demo/seed."""

    seeded_count: int
    examples: list[SeededExample]
    message: str
