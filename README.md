# Blueprint AI — Drawing Interpreter

> Extract structured engineering data (dimensions, GD&T, surface finish, BOM fields) from PDF/image drawings using a vision-language model pipeline.

---

## Project Structure

```
blueprint-ai-drawing-interpreter/
├── backend/                  # Python 3.11 · FastAPI
│   ├── app/
│   │   ├── main.py           # FastAPI app, CORS, health endpoint
│   │   ├── schemas.py        # Pydantic models (ExtractedDrawingData, …)
│   │   └── routers/
│   │       └── extract.py    # POST /api/extract (stub)
│   ├── demo_data/            # Seeded examples for instant demo (no API call)
│   │   ├── manifest.json     # Index of all demo examples
│   │   ├── drawing_bracket.{png,json}
│   │   ├── drawing_shaft.{png,json}
│   │   └── drawing_flange.{png,json}
│   └── pyproject.toml        # PEP 621 package + dependencies
├── frontend/                 # React 18 · Vite · TypeScript
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   └── types/
│   │       └── extractedDrawingData.ts   # TS interfaces (mirrors schema)
│   ├── vite.config.ts        # Dev proxy → localhost:8000
│   └── package.json
├── shared/
│   └── extracted_drawing_data.schema.json   # JSON Schema draft-07
├── .env.example
└── README.md
```

---

## Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11 |
| pip | 23+ |
| Node.js | 18+ |
| npm | 9+ |

---

## Setup

### 1 — Clone & configure environment

```bash
git clone <your-remote-url>
cd blueprint-ai-drawing-interpreter

cp .env.example .env
# Edit .env and set HF_API_TOKEN to your Hugging Face token
# https://huggingface.co/settings/tokens
```

### 2 — Backend

```bash
cd backend

# Create & activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install the package and all dependencies
pip install -e .
```

### 3 — Frontend

```bash
cd frontend
npm install
```

---

## Running (Development)

Open **two terminals** from the project root.

### Terminal 1 — Backend

```bash
cd backend
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS/Linux

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at:
- Swagger UI → http://localhost:8000/docs
- ReDoc      → http://localhost:8000/redoc
- Health     → http://localhost:8000/health

### Terminal 2 — Frontend

```bash
cd frontend
npm run dev
```

Frontend available at → **http://localhost:5173**

> The Vite dev server proxies all `/api/*` requests to `http://localhost:8000`, so no CORS configuration is needed during development.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Description |
|---|---|
| `HF_API_TOKEN` | Hugging Face Inference API token (required for model calls) |
| `APP_HOST` | Host the backend binds to (default: `0.0.0.0`) |
| `APP_PORT` | Port the backend listens on (default: `8000`) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins (default: `http://localhost:5173`) |

---

## API Reference

### `GET /health`
Returns `{ "status": "ok" }`.

### `POST /api/extract`
Upload a drawing file (multipart/form-data, field name `file`).

**Accepted content types:** `application/pdf`, `image/png`, `image/jpeg`, `image/tiff`, `image/webp`

**Response:** `ExtractedDrawingData` JSON object (see `shared/extracted_drawing_data.schema.json`).

> ⚠️ Currently returns a **stub/placeholder** response. Real extraction logic has not been implemented yet.

---

## Shared Schema

`shared/extracted_drawing_data.schema.json` is the single source of truth for the extraction data shape.

- **Backend** → Pydantic models in `backend/app/schemas.py`
- **Frontend** → TypeScript interfaces in `frontend/src/types/extractedDrawingData.ts`

All `bbox` fields are `[x, y, width, height]` normalized to `[0, 1]` relative to image dimensions.

---

## 🎬 Demo Script (60-second client walkthrough)

Use this sequence when demoing to clients. No live API key required for steps 1–2.

### Step 1 — Seeded example (≈ 15 s)
1. Open **http://localhost:5173** in a browser.
2. In the **"Load Demo"** panel, click any of the three seeded examples
   (Mounting Bracket · Drive Shaft · Flange Plate).
3. The extraction result loads **instantly** from pre-computed JSON — no API call.
4. Point out the structured fields: part name, material, revision, all dimensions
   with tolerances, GD&T callouts, surface finish specs, and notes.

### Step 2 — Bounding-box overlay (≈ 15 s)
1. With a result loaded, hover over any **dimension** or **GD&T callout** row
   in the results panel.
2. The corresponding annotation highlights on the drawing image via the bbox overlay.
3. Demonstrate cross-linking: the data is spatially anchored to the drawing.

### Step 3 — Live upload (≈ 20 s)
1. Drag & drop (or click **Choose file**) to upload your own PDF or image drawing.
2. The backend calls the Hugging Face Inference API and returns a real extraction.
3. Results populate the same viewer — same UX, real AI output.

### Step 4 — Similarity search (≈ 10 s)
1. With any result open, click **"Find Similar"**.
2. The backend encodes the extraction using `sentence-transformers` + FAISS
   and returns the closest seeded examples by semantic similarity.
3. Explain the use case: "Find all parts with similar GD&T profiles or material specs."

> **Tip for pitches**: Run step 1 first to guarantee a smooth start even if the
> network is slow. Switch to step 3 live only if the client wants to see their
> own drawing processed.

---

## Roadmap

- [ ] PDF → image conversion (PyMuPDF)
- [ ] Vision-language model integration (Hugging Face Inference API)
- [ ] Structured response parsing → `ExtractedDrawingData`
- [ ] Frontend: result viewer with bounding-box overlay
- [ ] Frontend: similarity search via FAISS + sentence-transformers
- [ ] Frontend: export to JSON / CSV
