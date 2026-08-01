/**
 * hooks/useUpload.ts
 *
 * Manages the two-step upload pipeline:
 *   1. POST /api/upload  (multipart) → drawing_id
 *   2. POST /api/extract/{id}        → ExtractionResult
 *
 * Components switch to the review screen immediately and watch `phase` for
 * progress — the upload runs in the background without blocking navigation.
 */
import { useState, useCallback } from 'react';
import { api } from '../api/client';
import type { ExtractionResult, UploadResponse } from '../api/types';

export type UploadPhase = 'idle' | 'uploading' | 'extracting' | 'done' | 'error';

export interface UseUploadReturn {
  phase: UploadPhase;
  drawingId: string | null;
  extraction: ExtractionResult | null;
  error: string | null;
  /** 0–100 percentage for a progress bar */
  progress: number;
  upload: (file: File) => Promise<void>;
  reset: () => void;
}

export function useUpload(): UseUploadReturn {
  const [phase, setPhase] = useState<UploadPhase>('idle');
  const [drawingId, setDrawingId] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const upload = useCallback(async (file: File) => {
    setPhase('uploading');
    setError(null);
    setDrawingId(null);
    setExtraction(null);
    setProgress(5);

    try {
      // ── Step 1: Upload ──────────────────────────────────────────────────────
      const formData = new FormData();
      formData.append('file', file);

      const upResp = await api.post<UploadResponse>('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          if (e.total) setProgress(Math.round((e.loaded / e.total) * 45) + 5);
        },
      });

      const id = upResp.data.drawing_id;
      setDrawingId(id);
      setProgress(50);

      // ── Step 2: Extract ─────────────────────────────────────────────────────
      setPhase('extracting');
      setProgress(60);

      const exResp = await api.post<ExtractionResult>(`/api/extract/${id}`);
      setExtraction(exResp.data);
      setProgress(100);
      setPhase('done');
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Upload failed. Is the backend running?';
      setError(msg);
      setPhase('error');
    }
  }, []);

  const reset = useCallback(() => {
    setPhase('idle');
    setDrawingId(null);
    setExtraction(null);
    setError(null);
    setProgress(0);
  }, []);

  return { phase, drawingId, extraction, error, progress, upload, reset };
}
