/**
 * api/client.ts — shared axios instance.
 * Base URL read from VITE_API_URL env var (falls back to localhost for dev).
 */
import axios from 'axios';

// In dev: Vite proxies /api/* → http://localhost:8000, so BASE_URL = '' (same origin).
// In production: set VITE_API_URL to the deployed backend URL.
export const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? '';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});
