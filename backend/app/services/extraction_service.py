"""
Extraction service — calls Hugging Face Inference API (Qwen2.5-VL-7B-Instruct)
with the drawing PNG (+ optional text layer) and parses the JSON response into
an ExtractedDrawingData Pydantic model.

Design goals (demo build):
- One call to the model, no retries — fail fast with a clear error message.
- Encode the PNG as a base64 data-URL so we never need a public image host.
- Include the text layer in the user prompt when available (richer context).
- Parse with Pydantic; surface a structured error if the model returns bad JSON.
- Demo fallback: on ANY failure, check if the drawing matches a known demo
  sample (by SHA-256 of page_01.png, then by original filename). If it does,
  return the pre-computed extraction with source='demo_fallback' so the demo
  degrades gracefully even on a flaky connection.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
from pydantic import ValidationError

from app.schemas import DrawingMeta, ExtractedDrawingData, ExtractionResult
from app.services.drawing_service import STORAGE_ROOT

# ── Config ─────────────────────────────────────────────────────────────────────

HF_API_TOKEN: str = os.environ.get("HF_API_TOKEN", "")
HF_MODEL_ID: str = os.environ.get(
    "HF_MODEL_ID", "Qwen/Qwen2.5-VL-7B-Instruct"
)
HF_API_BASE = "https://api-inference.huggingface.co/models"
HF_TIMEOUT = 120.0  # seconds — VL models can be slow on cold start

# ── Demo data paths ────────────────────────────────────────────────────────────

_DEMO_DATA_DIR = Path(__file__).resolve().parents[2] / "demo_data"

# Lazy-loaded: maps sha256 → demo_id and basename → demo_id
_DEMO_HASHES: dict[str, str] = {}     # sha256 hex → demo_id, e.g. "bracket"
_DEMO_FILENAMES: dict[str, str] = {}  # image basename → demo_id
_demo_registry_loaded = False


# ── System prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert engineering drawing analyser. Your job is to extract structured \
data from the provided engineering drawing image and return it as a single valid \
JSON object — nothing else.

The JSON MUST conform exactly to this schema (all fields required):

{
  "part_name":     string,   // part name from title block
  "material":      string,   // material spec from title block
  "scale":         string,   // drawing scale, e.g. "1:1" or "NTS"
  "revision":      string,   // revision letter/number, e.g. "A"
  "quantity":      string,   // quantity required, e.g. "1"
  "dimensions": [            // every dimension annotation on the drawing
    {
      "value":     string,   // nominal value, e.g. "25.40"
      "tolerance": string,   // tolerance, e.g. "±0.05" or "REF"
      "bbox":      [x, y, w, h]  // normalized [0,1] relative to image size
    }
  ],
  "gdt_callouts": [          // every GD&T feature control frame
    {
      "characteristic":  string,  // e.g. "flatness", "true position"
      "tolerance_zone":  string,  // e.g. "0.02", "Ø0.1 M"
      "datum_refs":      string,  // e.g. "A|B|C" or ""
      "bbox":            [x, y, w, h]
    }
  ],
  "surface_finish": [        // every surface finish / roughness symbol
    {
      "value":  string,      // e.g. "Ra 1.6", "63 μin"
      "bbox":   [x, y, w, h]
    }
  ],
  "notes": [string]          // general notes from title block or note field
}

bbox rules:
- x, y = top-left corner of the annotation, normalized by image width/height
- w, h = width/height of the annotation bounding box, normalized
- All four values MUST be floats in [0.0, 1.0]

If a field cannot be found in the drawing, use an empty string "" or empty array [].
Do NOT add extra keys. Do NOT wrap the JSON in markdown code fences.
Output ONLY the raw JSON object.
"""


# ── Public entry point ─────────────────────────────────────────────────────────


async def run_extraction(drawing_id: str) -> ExtractionResult:
    """
    Load artefacts for *drawing_id*, call the HF API, parse the response,
    and persist the result as ``extraction.json`` in the drawing storage dir.

    On any failure (network, timeout, bad JSON, schema mismatch) tries a
    demo fallback before returning an error result.

    Returns an :class:`ExtractionResult` (success or structured failure).
    """
    drawing_dir = STORAGE_ROOT / drawing_id
    if not drawing_dir.is_dir():
        return _error_result(drawing_id, f"Drawing '{drawing_id}' not found in storage.")

    # ── Load PNG ───────────────────────────────────────────────────────────────
    png_path = drawing_dir / "page_01.png"
    if not png_path.is_file():
        return _error_result(drawing_id, "Rendered PNG not found — was the drawing uploaded?")

    image_b64 = base64.b64encode(png_path.read_bytes()).decode("ascii")
    image_data_url = f"data:image/png;base64,{image_b64}"

    # ── Load text layer (optional) ─────────────────────────────────────────────
    text_hint = ""
    text_path = drawing_dir / "text_layer.txt"
    if text_path.is_file():
        raw_text = text_path.read_text(encoding="utf-8").strip()
        if raw_text:
            text_hint = (
                "\n\nAdditional context — text extracted directly from the PDF vector layer "
                "(use this to improve accuracy of part name, material, dimensions, etc.):\n"
                f"```\n{raw_text[:4000]}\n```"
            )

    # ── Build messages ─────────────────────────────────────────────────────────
    user_content: list[dict] = [
        {"type": "image_url", "image_url": {"url": image_data_url}},
        {
            "type": "text",
            "text": (
                "Extract all engineering data from this drawing and return it as JSON."
                + text_hint
            ),
        },
    ]

    payload = {
        "model": HF_MODEL_ID,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 2048,
        "temperature": 0.1,
    }

    # ── Call HF API ────────────────────────────────────────────────────────────
    url = f"{HF_API_BASE}/{HF_MODEL_ID}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {HF_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=HF_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException:
        return _with_fallback(
            drawing_id, drawing_dir,
            "Request to Hugging Face API timed out (120 s).",
        )
    except httpx.RequestError as exc:
        return _with_fallback(
            drawing_id, drawing_dir,
            f"Network error calling HF API: {exc}",
        )

    if resp.status_code != 200:
        return _with_fallback(
            drawing_id, drawing_dir,
            f"HF API returned HTTP {resp.status_code}: {resp.text[:300]}",
            raw_response=resp.text,
        )

    # ── Extract JSON from model reply ──────────────────────────────────────────
    try:
        choice = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        return _with_fallback(
            drawing_id, drawing_dir,
            f"Unexpected response structure from HF API: {exc}",
            raw_response=resp.text,
        )

    json_str = _strip_fences(choice)

    try:
        raw_dict = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return _with_fallback(
            drawing_id, drawing_dir,
            f"Model output is not valid JSON: {exc}",
            raw_response=choice,
        )

    # ── Validate with Pydantic ─────────────────────────────────────────────────
    try:
        data = ExtractedDrawingData.model_validate(raw_dict)
    except ValidationError as exc:
        return _with_fallback(
            drawing_id, drawing_dir,
            f"Model JSON does not match schema: {exc.error_count()} error(s). "
            f"First: {exc.errors()[0]['msg']}",
            raw_response=choice,
        )

    # ── Persist and return ─────────────────────────────────────────────────────
    result = ExtractionResult(
        drawing_id=drawing_id,
        status="ok",
        data=data,
        source="hf_api",
        raw_response=None,
        extracted_at=_utcnow(),
    )
    _persist(drawing_dir, result)
    return result


# ── Demo fallback ──────────────────────────────────────────────────────────────


def _load_demo_registry() -> None:
    """
    Lazily build two lookup dicts from demo_data/manifest.json:
      _DEMO_HASHES    : sha256(demo PNG) → demo_id
      _DEMO_FILENAMES : image basename   → demo_id
    Called once on the first extraction attempt.
    """
    global _demo_registry_loaded, _DEMO_HASHES, _DEMO_FILENAMES
    if _demo_registry_loaded:
        return

    manifest_path = _DEMO_DATA_DIR / "manifest.json"
    if not manifest_path.is_file():
        _demo_registry_loaded = True
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for ex in manifest.get("examples", []):
        demo_id = ex["id"]
        img_path = _DEMO_DATA_DIR / ex["image"]
        if img_path.is_file():
            sha = hashlib.sha256(img_path.read_bytes()).hexdigest()
            _DEMO_HASHES[sha] = demo_id
        _DEMO_FILENAMES[ex["image"]] = demo_id

    _demo_registry_loaded = True


def _find_demo_match(drawing_dir: Path) -> str | None:
    """
    Return the demo_id if the drawing's PNG matches a known demo sample,
    or None if no match is found.

    Checks in order:
      1. SHA-256 of page_01.png  (content match — survives renames)
      2. original_filename from meta.json  (fast pre-filter)
    """
    _load_demo_registry()

    # 1 — Hash match
    png_path = drawing_dir / "page_01.png"
    if png_path.is_file():
        sha = hashlib.sha256(png_path.read_bytes()).hexdigest()
        if sha in _DEMO_HASHES:
            return _DEMO_HASHES[sha]

    # 2 — Filename match (basename only)
    meta_path = drawing_dir / "meta.json"
    if meta_path.is_file():
        try:
            meta = DrawingMeta.model_validate_json(meta_path.read_text(encoding="utf-8"))
            basename = Path(meta.original_filename).name
            if basename in _DEMO_FILENAMES:
                return _DEMO_FILENAMES[basename]
        except Exception:
            pass

    return None


def _with_fallback(
    drawing_id: str,
    drawing_dir: Path,
    error_message: str,
    raw_response: str | None = None,
) -> ExtractionResult:
    """
    Try to return a demo fallback result.
    If no fallback is available, return a plain error result.
    """
    demo_id = _find_demo_match(drawing_dir)
    if demo_id:
        json_path = _DEMO_DATA_DIR / f"drawing_{demo_id}.json"
        if json_path.is_file():
            try:
                raw_dict = json.loads(json_path.read_text(encoding="utf-8"))
                data = ExtractedDrawingData.model_validate(raw_dict)
                result = ExtractionResult(
                    drawing_id=drawing_id,
                    status="ok",
                    data=data,
                    source="demo_fallback",
                    raw_response=None,
                    extracted_at=_utcnow(),
                )
                _persist(drawing_dir, result)
                return result
            except Exception:
                pass  # fallback itself failed — fall through to error

    return _error_result(drawing_id, error_message, raw_response)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped its output anyway."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1).strip()
    brace = text.find("{")
    if brace > 0:
        text = text[brace:]
    return text


def _error_result(
    drawing_id: str,
    message: str,
    raw_response: str | None = None,
) -> ExtractionResult:
    result = ExtractionResult(
        drawing_id=drawing_id,
        status="error",
        error_message=message,
        data=None,
        source="hf_api",
        raw_response=raw_response,
        extracted_at=_utcnow(),
    )
    drawing_dir = STORAGE_ROOT / drawing_id
    if drawing_dir.is_dir():
        _persist(drawing_dir, result)
    return result


def _persist(drawing_dir: Path, result: ExtractionResult) -> None:
    """Write extraction.json next to the other artefacts."""
    (drawing_dir / "extraction.json").write_text(
        result.model_dump_json(indent=2, exclude={"raw_response"}),
        encoding="utf-8",
    )


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()
