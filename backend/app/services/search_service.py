"""
FAISS similarity-search service.

Converts an ExtractedDrawingData into a text embedding using
sentence-transformers (all-MiniLM-L6-v2), maintains a flat
cosine-similarity FAISS index, and persists the index + metadata
sidecar to disk so state survives server restarts.

Design (demo build):
- Lazy model loading — SentenceTransformer loads once on first use.
- Index stored at: backend/storage/faiss.index
- Metadata sidecar:  backend/storage/faiss_meta.json
  Each entry: { "drawing_id": str, "label": str, "vector_idx": int }
- Thread-safe via a module-level asyncio.Lock (single-process demo server).
- On reset: both files are deleted and re-created from scratch.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import NamedTuple

import numpy as np

from app.schemas import ExtractedDrawingData
from app.services.drawing_service import STORAGE_ROOT

# ── Paths ──────────────────────────────────────────────────────────────────────

INDEX_PATH = STORAGE_ROOT / "faiss.index"
META_PATH = STORAGE_ROOT / "faiss_meta.json"

# ── Embedding model (lazy singleton) ──────────────────────────────────────────

_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
_embed_model = None  # loaded on first use


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415
        _embed_model = SentenceTransformer(_EMBED_MODEL_NAME)
    return _embed_model


# ── In-memory index state ─────────────────────────────────────────────────────

_lock = asyncio.Lock()

# List of {"drawing_id": str, "label": str, "vector_idx": int}
_meta: list[dict] = []
_faiss_index = None   # faiss.IndexFlatIP, loaded lazily


# ── Public API ─────────────────────────────────────────────────────────────────


class SearchHit(NamedTuple):
    drawing_id: str
    label: str
    score: float          # cosine similarity in [0, 1]
    preview_url: str


async def index_drawing(
    drawing_id: str,
    label: str,
    data: ExtractedDrawingData,
) -> None:
    """Embed *data* and upsert the vector into the FAISS index."""
    text = _drawing_to_text(data)
    vector = await asyncio.to_thread(_embed, text)

    async with _lock:
        _load_index_if_needed()
        _upsert(drawing_id, label, vector)
        _save()


async def search_similar(
    data: ExtractedDrawingData,
    top_k: int = 5,
) -> list[SearchHit]:
    """Return up to *top_k* drawings most similar to *data*."""
    if _faiss_index is None or _faiss_index.ntotal == 0:
        _load_index_if_needed()
    if _faiss_index is None or _faiss_index.ntotal == 0:
        return []

    text = _drawing_to_text(data)
    vector = await asyncio.to_thread(_embed, text)

    async with _lock:
        k = min(top_k, _faiss_index.ntotal)
        scores, idxs = _faiss_index.search(vector.reshape(1, -1), k)

    hits: list[SearchHit] = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx < 0:
            continue
        entry = _meta[idx]
        hits.append(
            SearchHit(
                drawing_id=entry["drawing_id"],
                label=entry["label"],
                score=float(score),
                preview_url=f"/api/drawing/{entry['drawing_id']}/preview",
            )
        )
    return hits


async def reset_index() -> None:
    """Delete the on-disk index and reset all in-memory state."""
    async with _lock:
        global _faiss_index, _meta
        _faiss_index = None
        _meta = []
        INDEX_PATH.unlink(missing_ok=True)
        META_PATH.unlink(missing_ok=True)


def index_size() -> int:
    """Return the number of vectors currently indexed."""
    if _faiss_index is None:
        _load_index_if_needed()
    return _faiss_index.ntotal if _faiss_index else 0


# ── Internal helpers ───────────────────────────────────────────────────────────


def _drawing_to_text(data: ExtractedDrawingData) -> str:
    """
    Serialize the extraction to a single text string for embedding.
    Includes all semantically meaningful fields.
    """
    parts = [
        f"Part: {data.part_name}",
        f"Material: {data.material}",
        f"Scale: {data.scale}",
        f"Revision: {data.revision}",
        f"Quantity: {data.quantity}",
    ]
    for d in data.dimensions:
        parts.append(f"Dimension {d.value} tol {d.tolerance}")
    for g in data.gdt_callouts:
        parts.append(f"GDT {g.characteristic} zone {g.tolerance_zone} datum {g.datum_refs}")
    for s in data.surface_finish:
        parts.append(f"Surface finish {s.value}")
    parts.extend(data.notes)
    return " | ".join(parts)


def _embed(text: str) -> np.ndarray:
    """Run the sentence-transformer embedding synchronously (called via to_thread)."""
    model = _get_embed_model()
    vec = model.encode([text], normalize_embeddings=True)
    return vec[0].astype(np.float32)


def _load_index_if_needed() -> None:
    """Load persisted index + meta from disk into module-level state."""
    global _faiss_index, _meta
    import faiss  # noqa: PLC0415

    if _faiss_index is not None:
        return

    if INDEX_PATH.is_file() and META_PATH.is_file():
        _faiss_index = faiss.read_index(str(INDEX_PATH))
        _meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    else:
        # Dimension 384 matches all-MiniLM-L6-v2 output
        _faiss_index = faiss.IndexFlatIP(384)
        _meta = []


def _upsert(drawing_id: str, label: str, vector: np.ndarray) -> None:
    """
    Remove any existing vector for *drawing_id* then add the new one.
    FAISS IndexFlatIP doesn't support in-place update, so we rebuild
    on upsert (demo scale: < 100 drawings, trivially fast).
    """
    import faiss  # noqa: PLC0415

    # Filter out existing entry for this drawing_id
    survivors = [e for e in _meta if e["drawing_id"] != drawing_id]
    new_idx = len(survivors)

    if len(survivors) < len(_meta):
        # Rebuild index without the old vector
        old_vectors = np.array(
            [
                _faiss_index.reconstruct(e["vector_idx"])
                for e in _meta
                if e["drawing_id"] != drawing_id
            ],
            dtype=np.float32,
        )
        _faiss_index.reset()
        if len(old_vectors):
            _faiss_index.add(old_vectors)
        # Re-number vector_idx in survivors
        for i, e in enumerate(survivors):
            e["vector_idx"] = i
    else:
        new_idx = _faiss_index.ntotal

    _faiss_index.add(vector.reshape(1, -1))
    survivors.append({"drawing_id": drawing_id, "label": label, "vector_idx": new_idx})

    global _meta
    _meta = survivors


def _save() -> None:
    """Flush index and metadata to disk."""
    import faiss  # noqa: PLC0415
    faiss.write_index(_faiss_index, str(INDEX_PATH))
    META_PATH.write_text(json.dumps(_meta, indent=2), encoding="utf-8")
