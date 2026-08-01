"""
GET /api/demo/seed  — load the 2-3 pre-built examples from /backend/demo_data
    into storage, bypassing the model, and index them all into FAISS.

Can be called:
  - Once on first run to pre-populate the demo.
  - Any time as a "Reset demo" action between client meetings.
    It wipes the FAISS index and all storage entries that came from
    demo seed data, then re-seeds cleanly.
"""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status

from app.schemas import (
    DrawingMeta,
    ExtractedDrawingData,
    ExtractionResult,
    SeedResult,
    SeededExample,
)
from app.services.drawing_service import STORAGE_ROOT
from app.services import vector_store

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_DATA_DIR = Path(__file__).resolve().parents[2] / "demo_data"
SEED_REGISTRY = STORAGE_ROOT / "seed_registry.json"   # tracks which drawing_ids are seeded


# ── GET /api/demo/seed ────────────────────────────────────────────────────────


@router.get(
    "/seed",
    response_model=SeedResult,
    summary="Load seeded demo examples into storage and FAISS (also resets demo state)",
)
async def seed_demo() -> SeedResult:
    """
    Reads ``demo_data/manifest.json``, then for each example:

    1. Removes any previously-seeded storage directory for that example
       (identified via ``seed_registry.json``).
    2. Creates a fresh ``storage/<drawing_id>/`` directory.
    3. Copies the PNG image as ``page_01.png``.
    4. Writes ``meta.json`` (marks ``is_demo=True``).
    5. Writes ``extraction.json`` + ``verified.flag`` from the pre-computed JSON.
    6. Indexes the extraction into FAISS.

    Resets the FAISS index before re-seeding so every call starts clean.
    """
    manifest_path = DEMO_DATA_DIR / "manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="demo_data/manifest.json not found.",
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    examples = manifest.get("examples", [])

    # ── Wipe previous seed state ───────────────────────────────────────────────
    await _wipe_previous_seeds()
    await vector_store.reset()

    # ── Seed each example ──────────────────────────────────────────────────────
    seeded: list[SeededExample] = []
    new_registry: list[dict] = []

    for ex in examples:
        drawing_id = _stable_demo_id(ex["id"])
        drawing_dir = STORAGE_ROOT / drawing_id
        drawing_dir.mkdir(parents=True, exist_ok=True)

        # Copy PNG
        src_png = DEMO_DATA_DIR / ex["image"]
        if not src_png.is_file():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Demo image not found: {ex['image']}",
            )
        shutil.copy2(src_png, drawing_dir / "page_01.png")

        # Load pre-computed extraction JSON
        src_json = DEMO_DATA_DIR / ex["extraction"]
        if not src_json.is_file():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Demo extraction not found: {ex['extraction']}",
            )
        raw_data = json.loads(src_json.read_text(encoding="utf-8"))
        extraction_data = ExtractedDrawingData.model_validate(raw_data)

        now = datetime.now(timezone.utc).isoformat()

        # Write meta.json
        meta = DrawingMeta(
            drawing_id=drawing_id,
            original_filename=ex["image"],
            content_type="image/png",
            pdf_type=None,
            has_text_layer=False,
            page_count=None,
            render_png="page_01.png",
            text_layer_file=None,
            created_at=now,
        )
        (drawing_dir / "meta.json").write_text(
            meta.model_dump_json(indent=2), encoding="utf-8"
        )

        # Write extraction.json (pre-verified)
        result = ExtractionResult(
            drawing_id=drawing_id,
            status="ok",
            data=extraction_data,
            error_message=None,
            raw_response=None,
            extracted_at=now,
        )
        (drawing_dir / "extraction.json").write_text(
            result.model_dump_json(indent=2), encoding="utf-8"
        )

        # Mark as verified (no human review needed for demo data)
        (drawing_dir / "verified.flag").write_text(now, encoding="utf-8")

        # Index into FAISS
        await vector_store.add(drawing_id, ex["label"], extraction_data)

        seeded.append(
            SeededExample(
                drawing_id=drawing_id,
                label=ex["label"],
                description=ex.get("description", ""),
                tags=ex.get("tags", []),
                preview_url=f"/api/drawing/{drawing_id}/preview",
                extraction_url=f"/api/drawings/{drawing_id}",
            )
        )
        new_registry.append({"demo_id": ex["id"], "drawing_id": drawing_id})

    # Persist seed registry for future reset
    SEED_REGISTRY.write_text(json.dumps(new_registry, indent=2), encoding="utf-8")

    return SeedResult(
        seeded_count=len(seeded),
        examples=seeded,
        message=(
            f"Demo seeded with {len(seeded)} example(s). "
            "FAISS index reset and rebuilt. Ready to demo."
        ),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _stable_demo_id(demo_slug: str) -> str:
    """
    Generate a deterministic drawing_id for a demo slug so the same
    preview URLs survive multiple seed calls.
    Uses a UUID5 (name-based) so it's stable but not guessable.
    """
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"blueprint-ai-demo.{demo_slug}").hex


async def _wipe_previous_seeds() -> None:
    """Remove storage directories created by a previous seed call."""
    if not SEED_REGISTRY.is_file():
        return
    registry = json.loads(SEED_REGISTRY.read_text(encoding="utf-8"))
    for entry in registry:
        old_dir = STORAGE_ROOT / entry["drawing_id"]
        if old_dir.is_dir():
            shutil.rmtree(old_dir)
