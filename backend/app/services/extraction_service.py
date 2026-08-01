"""
Extraction service — calls Hugging Face Inference API (Qwen2.5-VL-7B-Instruct)
with the drawing PNG (+ optional text layer) and parses the JSON response into
an ExtractedDrawingData Pydantic model.

Design goals (demo build):
- One call to the model, no retries — fail fast with a clear error message.
- Encode the PNG as a base64 data-URL so we never need a public image host.
- Include the text layer in the user prompt when available (richer context).
- Parse with Pydantic; surface a structured error if the model returns bad JSON.
"""

from __future__ import annotations

import base64
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
                f"```\n{raw_text[:4000]}\n```"  # cap at 4 k chars for token budget
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
        "temperature": 0.1,  # low temp → more deterministic JSON output
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
        return _error_result(drawing_id, "Request to Hugging Face API timed out (120 s).")
    except httpx.RequestError as exc:
        return _error_result(drawing_id, f"Network error calling HF API: {exc}")

    if resp.status_code != 200:
        snippet = resp.text[:300]
        return _error_result(
            drawing_id,
            f"HF API returned HTTP {resp.status_code}: {snippet}",
            raw_response=resp.text,
        )

    # ── Extract JSON from model reply ──────────────────────────────────────────
    try:
        choice = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, json.JSONDecodeError) as exc:
        return _error_result(
            drawing_id,
            f"Unexpected response structure from HF API: {exc}",
            raw_response=resp.text,
        )

    json_str = _strip_fences(choice)

    try:
        raw_dict = json.loads(json_str)
    except json.JSONDecodeError as exc:
        return _error_result(
            drawing_id,
            f"Model output is not valid JSON: {exc}",
            raw_response=choice,
        )

    # ── Validate with Pydantic ─────────────────────────────────────────────────
    try:
        data = ExtractedDrawingData.model_validate(raw_dict)
    except ValidationError as exc:
        return _error_result(
            drawing_id,
            f"Model JSON does not match schema: {exc.error_count()} error(s). "
            f"First: {exc.errors()[0]['msg']}",
            raw_response=choice,
        )

    # ── Persist result ─────────────────────────────────────────────────────────
    result = ExtractionResult(
        drawing_id=drawing_id,
        status="ok",
        data=data,
        raw_response=None,  # don't persist the full base64-heavy response
        extracted_at=_utcnow(),
    )
    _persist(drawing_dir, result)
    return result


# ── Helpers ────────────────────────────────────────────────────────────────────


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped its output anyway."""
    text = text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1).strip()
    # If model prepended prose before the JSON, grab from first {
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
