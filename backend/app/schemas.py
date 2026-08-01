"""
Pydantic models mirroring shared/extracted_drawing_data.schema.json.

All bbox fields are [x, y, w, h] normalized to [0, 1] relative to image size.
"""

from __future__ import annotations

from typing import Annotated

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


# ── Top-level response model ───────────────────────────────────────────────────


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
