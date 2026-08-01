"""
Blueprint AI — FastAPI application entry point.

Routes registered here:
  GET  /health          → health check
  POST /api/extract     → (stub) drawing extraction  [see routers/extract.py]
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import extract as extract_router

# ── App instance ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Blueprint AI Drawing Interpreter",
    description=(
        "Backend API for extracting structured data from engineering drawings "
        "using vision-language models."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────

app.include_router(extract_router.router, prefix="/api")


# ── Health check ───────────────────────────────────────────────────────────────


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Returns service liveness status."""
    return {"status": "ok"}


# ── Dev entry point ────────────────────────────────────────────────────────────


def run() -> None:
    """Convenience entry point defined in pyproject.toml [project.scripts]."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("APP_HOST", "0.0.0.0"),
        port=int(os.getenv("APP_PORT", "8000")),
        reload=True,
    )


if __name__ == "__main__":
    run()
