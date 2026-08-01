"""
Drawing ingestion service.

Responsibilities:
- Accept a raw file upload (PDF or raster image)
- Detect PDF type: vector (has selectable text) vs raster (scanned)
- Render page 1 to a 300-DPI PNG using PyMuPDF
- Extract the text layer from vector PDFs
- Compute SHA-256 of the rendered PNG (for demo fallback matching)
- Persist everything under /backend/storage/<drawing_id>/
- Return a DrawingMeta describing what was stored
"""

from __future__ import annotations

import hashlib
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import fitz  # PyMuPDF
from PIL import Image

from app.schemas import DrawingMeta

# ── Storage root (created at startup if absent) ────────────────────────────────

STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage"
STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────────

RENDER_DPI = 300
# PyMuPDF matrix for 300 DPI (72 pt/inch baseline → scale = 300/72)
_RENDER_MATRIX = fitz.Matrix(RENDER_DPI / 72, RENDER_DPI / 72)

# Minimum character count on page 1 to be considered a "vector" PDF
_VECTOR_CHAR_THRESHOLD = 20


# ── Public entry point ─────────────────────────────────────────────────────────


def ingest_upload(
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> DrawingMeta:
    """
    Process an uploaded file and persist it to storage.

    Returns a :class:`DrawingMeta` describing the stored artefacts.
    """
    drawing_id = _new_id()
    dest_dir = STORAGE_ROOT / drawing_id
    dest_dir.mkdir(parents=True, exist_ok=True)

    is_pdf = content_type == "application/pdf" or filename.lower().endswith(".pdf")

    if is_pdf:
        meta = _process_pdf(drawing_id, dest_dir, filename, file_bytes)
    else:
        meta = _process_image(drawing_id, dest_dir, filename, content_type, file_bytes)

    # Persist meta.json alongside the artefacts
    (dest_dir / "meta.json").write_text(
        meta.model_dump_json(indent=2), encoding="utf-8"
    )
    return meta


# ── PDF processing ─────────────────────────────────────────────────────────────


def _process_pdf(
    drawing_id: str,
    dest_dir: Path,
    filename: str,
    pdf_bytes: bytes,
) -> DrawingMeta:
    # Save the original
    original_path = dest_dir / "original.pdf"
    original_path.write_bytes(pdf_bytes)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page_count = len(doc)
    page = doc[0]  # always work on page 1 for the demo

    # ── Detect PDF type ────────────────────────────────────────────────────────
    raw_text = page.get_text("text").strip()
    pdf_type: Literal["vector", "raster"] = (
        "vector" if len(raw_text) >= _VECTOR_CHAR_THRESHOLD else "raster"
    )

    # ── Render page 1 → PNG at 300 DPI ────────────────────────────────────────
    pix = page.get_pixmap(matrix=_RENDER_MATRIX, alpha=False)
    png_path = dest_dir / "page_01.png"
    pix.save(str(png_path))

    # ── Extract text layer (vector PDFs only) ─────────────────────────────────
    text_path: Path | None = None
    if pdf_type == "vector":
        words = page.get_text("words")
        text_content = "\n".join(w[4] for w in words)
        text_path = dest_dir / "text_layer.txt"
        text_path.write_text(text_content, encoding="utf-8")

    doc.close()

    png_sha256 = _sha256(png_path)

    return DrawingMeta(
        drawing_id=drawing_id,
        original_filename=filename,
        content_type="application/pdf",
        pdf_type=pdf_type,
        has_text_layer=pdf_type == "vector",
        page_count=page_count,
        render_png="page_01.png",
        text_layer_file="text_layer.txt" if text_path else None,
        png_sha256=png_sha256,
        created_at=_utcnow(),
    )


# ── Image processing ───────────────────────────────────────────────────────────


def _process_image(
    drawing_id: str,
    dest_dir: Path,
    filename: str,
    content_type: str,
    img_bytes: bytes,
) -> DrawingMeta:
    # Normalise to PNG using Pillow (handles TIFF, WEBP, JPEG, etc.)
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    png_path = dest_dir / "page_01.png"
    img.save(str(png_path), format="PNG")

    # Also save the original
    suffix = Path(filename).suffix or ".bin"
    (dest_dir / f"original{suffix}").write_bytes(img_bytes)

    png_sha256 = _sha256(png_path)

    return DrawingMeta(
        drawing_id=drawing_id,
        original_filename=filename,
        content_type=content_type,
        pdf_type=None,
        has_text_layer=False,
        page_count=None,
        render_png="page_01.png",
        text_layer_file=None,
        png_sha256=png_sha256,
        created_at=_utcnow(),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    """Compute hex-encoded SHA-256 of a file."""
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _new_id() -> str:
    return uuid.uuid4().hex


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()
