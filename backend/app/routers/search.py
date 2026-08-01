"""
GET /api/search?q={query}

Embeds the query string with the local all-MiniLM-L6-v2 model and
returns the top-5 nearest drawings from the FAISS index.

- Empty index → empty results list, HTTP 200 (never an error).
- Each result includes drawing_id, part_name (label), similarity score
  in [0,1] (higher = more similar), L2 distance, and preview_url.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.schemas import SearchResponse, SearchResult
from app.services import vector_store

router = APIRouter(tags=["search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search across indexed drawings",
)
async def search_drawings(
    q: str = Query(..., min_length=1, description="Free-text search query."),
    top_k: int = Query(5, ge=1, le=20, description="Max results to return."),
) -> SearchResponse:
    """
    Embeds *q* with the local `all-MiniLM-L6-v2` model and returns the
    top-*top_k* most semantically similar drawings from the FAISS index.

    **Returns an empty list** when the index is empty — never an error.
    Run `GET /api/demo/seed` first to populate the index with demo data.

    Similarity score is `1 / (1 + L2_distance)`, in the range `(0, 1]`.
    A score of 1.0 means a perfect match; lower scores indicate less similarity.
    """
    hits = await vector_store.search_by_text(q, top_k=top_k)

    results = [
        SearchResult(
            drawing_id=hit.drawing_id,
            part_name=hit.label,
            score=hit.score,
            distance=hit.distance,
            preview_url=hit.preview_url,
        )
        for hit in hits
    ]

    return SearchResponse(
        query=q,
        results=results,
        index_size=vector_store.size(),
    )
