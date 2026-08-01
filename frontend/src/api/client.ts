/**
 * api/client.ts — shared axios instance.
 * Base URL read from VITE_API_URL env var (falls back to localhost for dev).
 */
import axios from 'axios';

export const BASE_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});
