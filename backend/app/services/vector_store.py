"""
VectorStore — FAISS-backed similarity index for engineering drawings.

One focused module. No external API calls. Everything runs locally.

Storage layout  (auto-created on first write):
    backend/storage/faiss_index/
        index.faiss   — FAISS IndexFlatL2 binary
        id_map.json   — list of { "vector_idx": int, "drawing_id": str, "label": str }

Text blob per drawing (the fields that matter for semantic similarity):
    part_name | material | notes… | GD&T characteristics… | dimension values…

Embedding model: sentence-transformers all-MiniLM-L6-v2 (384-dim, ~80 MB, local).
Model is loaded lazily on the first add/search call so server startup stays instant.

Thread safety: a single asyncio.Lock guards all index mutations.
Blocking CPU work (embed, FAISS ops) is offloaded via asyncio.to_thread so the
FastAPI event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path
from typing import NamedTuple

import numpy as np

from app.schemas import ExtractedDrawingData
from app.services.drawing_service import STORAGE_ROOT

# ── Storage paths ──────────────────────────────────────────────────────────────

INDEX_DIR = STORAGE_ROOT / "faiss_index"
INDEX_FILE = INDEX_DIR / "index.faiss"
MAP_FILE = INDEX_DIR / "id_map.json"

# ── Constants ──────────────────────────────────────────────────────────────────

_MODEL_NAME = "all-MiniLM-L6-v2"
_DIM = 384          # output dimension of all-MiniLM-L6-v2

# ── Module-level state ────────────────────────────────────────────────────────

_lock = asyncio.Lock()
_model = None           # SentenceTransformer, loaded once
_index = None           # faiss.IndexFlatL2
_id_map: list[dict] = []  # [{"vector_idx": int, "drawing_id": str, "label": str}]


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════


class SearchHit(NamedTuple):
    drawing_id: str
    label: str
    distance: float      # L2 distance — lower = more similar
    score: float         # similarity score in [0, 1] — higher = more similar
    preview_url: str


def text_from_drawing(data: ExtractedDrawingData) -> str:
    """
    Build the text blob used for embedding.

    Includes: part name, material, notes, GD&T characteristics,
    and dimension values. Joined with ' | ' as delimiter.
    """
    parts: list[str] = []

    if data.part_name:
        parts.append(data.part_name)
    if data.material:
        parts.append(data.material)

    parts.extend(note for note in data.notes if note)
    parts.extend(g.characteristic for g in data.gdt_callouts if g.characteristic)
    parts.extend(d.value for d in data.dimensions if d.value)

    return " | ".join(parts)


async def add(drawing_id: str, label: str, data: ExtractedDrawingData) -> None:
    """
    Embed *data* and upsert its vector into the index.

    If *drawing_id* already exists it is removed first (upsert semantics).
    Persists to disk after every write.
    """
    text = text_from_drawing(data)
    vec = await asyncio.to_thread(_embed, text)

    async with _lock:
        _ensure_loaded()
        _upsert(drawing_id, label, vec)
        _save()


async def search(
    data: ExtractedDrawingData,
    top_k: int = 5,
) -> list[SearchHit]:
    """
    Return up to *top_k* drawings most similar to *data* (ascending L2 distance).
    Returns an empty list when the index is empty.
    """
    async with _lock:
        _ensure_loaded()
        if _index.ntotal == 0:
            return []

    text = text_from_drawing(data)
    vec = await asyncio.to_thread(_embed, text)

    async with _lock:
        k = min(top_k, _index.ntotal)
        distances, indices = _index.search(vec.reshape(1, -1), k)

    hits: list[SearchHit] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        entry = _id_map[idx]
        d = float(dist)
        hits.append(
            SearchHit(
                drawing_id=entry["drawing_id"],
                label=entry["label"],
                distance=d,
                score=round(1.0 / (1.0 + d), 4),
                preview_url=f"/api/drawing/{entry['drawing_id']}/preview",
            )
        )
    return hits


async def reset() -> None:
    """
    Wipe the on-disk index directory and clear all in-memory state.
    Call this before re-seeding the demo.
    """
    async with _lock:
        global _index, _id_map
        _index = None
        _id_map = []
        if INDEX_DIR.is_dir():
            shutil.rmtree(INDEX_DIR)


def size() -> int:
    """Return the number of vectors currently in the index (0 if unloaded)."""
    if _index is None:
        _ensure_loaded()
    return _index.ntotal if _index else 0


async def search_by_text(
    query: str,
    top_k: int = 5,
) -> list[SearchHit]:
    """
    Embed a raw text *query* and return the top-k most similar drawings.

    - Returns an empty list when the index is empty (never raises).
    - Results are ordered by ascending L2 distance (most similar first).
    - Each hit includes both ``distance`` and ``score`` (= 1/(1+distance)).
    """
    async with _lock:
        _ensure_loaded()
        if _index.ntotal == 0:
            return []

    vec = await asyncio.to_thread(_embed, query)

    async with _lock:
        k = min(top_k, _index.ntotal)
        distances, indices = _index.search(vec.reshape(1, -1), k)

    hits: list[SearchHit] = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0:
            continue
        entry = _id_map[idx]
        d = float(dist)
        hits.append(
            SearchHit(
                drawing_id=entry["drawing_id"],
                label=entry["label"],
                distance=d,
                score=round(1.0 / (1.0 + d), 4),
                preview_url=f"/api/drawing/{entry['drawing_id']}/preview",
            )
        )
    return hits


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers  (all called with _lock held or from to_thread)
# ══════════════════════════════════════════════════════════════════════════════


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # lazy import
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _embed(text: str) -> np.ndarray:
    """Synchronous embed — run via asyncio.to_thread."""
    vec = _get_model().encode([text])
    return vec[0].astype(np.float32)


def _ensure_loaded() -> None:
    """Load index + id_map from disk into module state if not already loaded."""
    global _index, _id_map
    import faiss

    if _index is not None:
        return

    if INDEX_FILE.is_file() and MAP_FILE.is_file():
        _index = faiss.read_index(str(INDEX_FILE))
        _id_map = json.loads(MAP_FILE.read_text(encoding="utf-8"))
    else:
        _index = faiss.IndexFlatL2(_DIM)
        _id_map = []


def _upsert(drawing_id: str, label: str, vec: np.ndarray) -> None:
    """
    Remove any existing entry for *drawing_id*, then append the new vector.

    Because IndexFlatL2 has no native delete, we rebuild the matrix
    from surviving vectors. At demo scale (< 100 drawings) this is
    effectively instantaneous.
    """
    import faiss

    survivors = [e for e in _id_map if e["drawing_id"] != drawing_id]

    if len(survivors) < len(_id_map):
        # Rebuild without the stale vector
        if survivors:
            kept = np.stack(
                [_index.reconstruct(e["vector_idx"]) for e in survivors]
            ).astype(np.float32)
        else:
            kept = np.empty((0, _DIM), dtype=np.float32)

        _index.reset()
        if len(kept):
            _index.add(kept)

        # Re-number vector_idx sequentially
        for i, e in enumerate(survivors):
            e["vector_idx"] = i

    new_idx = _index.ntotal
    _index.add(vec.reshape(1, -1))
    survivors.append({"vector_idx": new_idx, "drawing_id": drawing_id, "label": label})

    global _id_map
    _id_map = survivors


def _save() -> None:
    """Flush index binary and id_map JSON to disk."""
    import faiss

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(_index, str(INDEX_FILE))
    MAP_FILE.write_text(json.dumps(_id_map, indent=2), encoding="utf-8")
