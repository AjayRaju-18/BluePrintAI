/**
 * api/types.ts — TypeScript shapes for all API responses.
 * Mirrors the Pydantic schemas in backend/app/schemas.py.
 */

// ── Upload ─────────────────────────────────────────────────────────────────────

export interface UploadResponse {
  drawing_id: string;
  original_filename: string;
  pdf_type: 'vector' | 'raster' | null;
  has_text_layer: boolean;
  page_count: number | null;
  render_url: string;
  created_at: string;
}

// ── Extraction ─────────────────────────────────────────────────────────────────

export type BBox = [number, number, number, number];

export interface Dimension {
  value: string;
  tolerance: string;
  bbox: BBox;
}

export interface GDTCallout {
  characteristic: string;
  tolerance_zone: string;
  datum_refs: string;
  bbox: BBox;
}

export interface SurfaceFinish {
  value: string;
  bbox: BBox;
}

export interface ExtractedDrawingData {
  part_name: string;
  material: string;
  scale: string;
  revision: string;
  quantity: string;
  dimensions: Dimension[];
  gdt_callouts: GDTCallout[];
  surface_finish: SurfaceFinish[];
  notes: string[];
}

export type ExtractionStatus = 'ok' | 'error';
export type ExtractionSource = 'hf_api' | 'demo_fallback';

export interface ExtractionResult {
  drawing_id: string;
  status: ExtractionStatus;
  data: ExtractedDrawingData | null;
  error_message: string | null;
  source: ExtractionSource | null;
  extracted_at: string;
}

// ── Drawing detail ─────────────────────────────────────────────────────────────

export interface DrawingDetail {
  drawing_id: string;
  preview_url: string;
  extraction: ExtractionResult | null;
  verified: boolean;
}

// ── Search ─────────────────────────────────────────────────────────────────────

export interface SearchResult {
  drawing_id: string;
  part_name: string;
  score: number;       // 1/(1+L2_distance), higher = more similar
  distance: number;
  preview_url: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  index_size: number;
}

// ── Demo seed ─────────────────────────────────────────────────────────────────

export interface SeededExample {
  drawing_id: string;
  label: string;
  description: string;
  tags: string[];
  preview_url: string;
  extraction_url: string;
}

export interface SeedResult {
  seeded_count: number;
  examples: SeededExample[];
  message: string;
}
