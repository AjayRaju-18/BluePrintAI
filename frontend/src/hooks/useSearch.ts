/**
 * hooks/useSearch.ts
 *
 * Debounced text search against GET /api/search?q=.
 * Returns empty results (not an error) when the index is empty.
 */
import { useState, useCallback, useRef } from 'react';
import { api } from '../api/client';
import type { SearchResponse } from '../api/types';

const DEBOUNCE_MS = 400;

export interface UseSearchReturn {
  query: string;
  results: SearchResponse | null;
  loading: boolean;
  error: string | null;
  search: (q: string) => void;
  clearSearch: () => void;
}

export function useSearch(): UseSearchReturn {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const search = useCallback((q: string) => {
    setQuery(q);
    if (timerRef.current) clearTimeout(timerRef.current);

    if (!q.trim()) {
      setResults(null);
      return;
    }

    timerRef.current = setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await api.get<SearchResponse>('/api/search', {
          params: { q: q.trim(), top_k: 5 },
        });
        setResults(resp.data);
      } catch {
        setError('Search failed. Is the backend running?');
        setResults(null);
      } finally {
        setLoading(false);
      }
    }, DEBOUNCE_MS);
  }, []);

  const clearSearch = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setQuery('');
    setResults(null);
    setError(null);
  }, []);

  return { query, results, loading, error, search, clearSearch };
}
