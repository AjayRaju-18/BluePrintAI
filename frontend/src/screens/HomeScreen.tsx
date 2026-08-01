import { useRef, useState, useCallback } from 'react';
import './HomeScreen.css';
import TopBar from '../components/TopBar';
import MascotBot from '../components/MascotBot';
import { useSearch } from '../hooks/useSearch';
import { BASE_URL } from '../api/client';
import { api } from '../api/client';
import type { SeedResult } from '../api/types';

interface HomeScreenProps {
  onFileSelect: (file: File) => void;
}

export default function HomeScreen({ onFileSelect }: HomeScreenProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cmdInputRef  = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [seedStatus, setSeedStatus] = useState<'idle' | 'loading' | 'done'>('idle');
  const { query, results, loading: searchLoading, error: searchError, search, clearSearch } = useSearch();

  // ── File selection helpers ──────────────────────────────────────────────────

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelect(file);
      e.target.value = ''; // allow re-selecting same file
    },
    [onFileSelect],
  );

  const triggerFilePicker = useCallback(() => fileInputRef.current?.click(), []);

  // ── Drag-and-drop on command bar ────────────────────────────────────────────

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback(() => setIsDragging(false), []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) onFileSelect(file);
    },
    [onFileSelect],
  );

  // ── Command bar send (search if text, pick file if empty) ──────────────────

  const handleSend = useCallback(() => {
    if (query.trim()) return; // search already debounced
    triggerFilePicker();
  }, [query, triggerFilePicker]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && query.trim()) search(query); // immediate on Enter
      if (e.key === 'Escape') clearSearch();
    },
    [query, search, clearSearch],
  );

  // ── Seed demo data ──────────────────────────────────────────────────────────

  const seedDemo = useCallback(async () => {
    setSeedStatus('loading');
    try {
      await api.get<SeedResult>('/api/demo/seed');
      setSeedStatus('done');
      setTimeout(() => setSeedStatus('idle'), 3000);
    } catch {
      setSeedStatus('idle');
    }
  }, []);

  const showSeedChip = results?.index_size === 0 || seedStatus !== 'idle';

  return (
    <>
      {/* ── Icon rail (left sidebar / bottom tab on mobile) ────────────────── */}
      <nav className="icon-rail" aria-label="Main navigation">
        <div className="icon-rail__brand" aria-hidden="true">⬡</div>

        <a className="icon-rail__item active" href="#home" aria-current="page">
          <span className="icon-rail__icon home-nav-icon">⊞</span>
          <span className="icon-rail__label">Home</span>
        </a>

        <a className="icon-rail__item" href="#upload" aria-label="Upload a drawing" onClick={(e) => { e.preventDefault(); triggerFilePicker(); }}>
          <span className="icon-rail__icon home-nav-icon">⬆</span>
          <span className="icon-rail__label">Upload</span>
        </a>

        <a className="icon-rail__item" href="#search" aria-label="Search" onClick={(e) => { e.preventDefault(); cmdInputRef.current?.focus(); }}>
          <span className="icon-rail__icon home-nav-icon">⌖</span>
          <span className="icon-rail__label">Search</span>
        </a>
      </nav>

      {/* ── App shell content ──────────────────────────────────────────────── */}
      <div className="app-shell">
        <div className="content-area">
          <div className="glass-panel home-panel anim-fade-up">

            {/* Top bar */}
            <TopBar pageTitle="Drawing Studio" />
            <hr className="divider" aria-hidden="true" />

            {/* ── Hero ──────────────────────────────────────────────────────── */}
            <section className="home-hero" aria-labelledby="hero-headline">
              <div className="hero-content anim-fade-up">
                <h2 id="hero-headline" className="hero-headline">
                  Ready to read your<br />next drawing?
                </h2>
                <p className="hero-subtext">
                  Upload any engineering drawing and Blueprint AI extracts
                  dimensions, GD&amp;T callouts, materials, and more — instantly.
                </p>
                <div className="hero-actions">
                  <button
                    id="hero-upload-btn"
                    className="btn-pill btn-pill--amber"
                    type="button"
                    onClick={triggerFilePicker}
                  >
                    ⬆ Upload a drawing
                  </button>
                  <button
                    className="btn-pill btn-pill--ghost"
                    type="button"
                    onClick={() => cmdInputRef.current?.focus()}
                  >
                    ⌖ Search library
                  </button>
                </div>
              </div>

              <MascotBot />
            </section>

            <hr className="divider" aria-hidden="true" />

            {/* ── Feature cards ─────────────────────────────────────────────── */}
            <section className="home-cards anim-stagger" aria-label="Quick actions">
              <div className="feature-grid">

                {/* Upload card */}
                <div
                  className="feature-card feature-card--clickable"
                  role="button"
                  tabIndex={0}
                  id="card-upload"
                  aria-label="Upload a drawing — start a new extraction"
                  onClick={triggerFilePicker}
                  onKeyDown={(e) => e.key === 'Enter' && triggerFilePicker()}
                >
                  <div className="feature-card__icon feature-card__icon--amber">⬆</div>
                  <div className="feature-card__heading">Upload a drawing</div>
                  <div className="feature-card__subtitle">
                    Drop a PDF or image and get dimensions, GD&amp;T, and materials extracted in seconds.
                  </div>
                  <span className="feature-card__tag">New extraction</span>
                </div>

                {/* Review card */}
                <div
                  className="feature-card feature-card--clickable"
                  role="button"
                  tabIndex={0}
                  id="card-review"
                  aria-label="Review extractions — browse saved drawings"
                  onClick={triggerFilePicker}
                  onKeyDown={(e) => e.key === 'Enter' && triggerFilePicker()}
                  title="Upload a drawing to start reviewing extractions"
                >
                  <div className="feature-card__icon">◫</div>
                  <div className="feature-card__heading">Review extractions</div>
                  <div className="feature-card__subtitle">
                    Browse, correct, and verify past AI-extracted drawing data.
                  </div>
                  <span className="feature-card__tag">History</span>
                </div>

                {/* Search card */}
                <div
                  className="feature-card feature-card--clickable"
                  role="button"
                  tabIndex={0}
                  id="card-search"
                  aria-label="Search the library — semantic FAISS search"
                  onClick={() => cmdInputRef.current?.focus()}
                  onKeyDown={(e) => e.key === 'Enter' && cmdInputRef.current?.focus()}
                >
                  <div className="feature-card__icon feature-card__icon--ink">⌖</div>
                  <div className="feature-card__heading">Search the library</div>
                  <div className="feature-card__subtitle">
                    Find drawings by part name, material, or GD&amp;T characteristic via semantic search.
                  </div>
                  <span className="feature-card__tag">Semantic search</span>
                </div>

              </div>
            </section>

            {/* ── Footer row ────────────────────────────────────────────────── */}
            <div className="home-footer-row">
              <span className="label">Blueprint AI — demo build</span>
              <span className="label">Powered by Qwen2.5-VL &amp; FAISS</span>
            </div>

            {/* ── Command bar ───────────────────────────────────────────────── */}
            <section className="home-cmd" aria-label="Search and upload">
              <div
                className={`command-bar${isDragging ? ' command-bar--dragging' : ''}`}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
              >
                <div className="command-bar__row">
                  {/* Leading icon */}
                  <span className="command-bar__lead" aria-hidden="true">
                    {searchLoading ? <span className="spinner" /> : '⌖'}
                  </span>

                  {/* Text input */}
                  <input
                    ref={cmdInputRef}
                    id="cmd-input"
                    className="command-bar__input"
                    type="text"
                    placeholder="Ask about a drawing, or drop a file to extract it"
                    value={query}
                    onChange={(e) => search(e.target.value)}
                    onKeyDown={handleKeyDown}
                    aria-label="Search drawings or type a query"
                    autoComplete="off"
                  />

                  {/* Clear button (when searching) */}
                  {query && (
                    <button
                      className="command-bar__icon-btn"
                      type="button"
                      onClick={clearSearch}
                      aria-label="Clear search"
                    >
                      ✕
                    </button>
                  )}

                  {/* Send / upload button */}
                  <button
                    className="command-bar__icon-btn command-bar__icon-btn--send"
                    type="button"
                    onClick={handleSend}
                    aria-label={query.trim() ? 'Search' : 'Upload a file'}
                  >
                    {query.trim() ? '→' : '⬆'}
                  </button>
                </div>

                {/* Quick-action chips */}
                <div className="command-bar__chips" role="group" aria-label="Quick actions">
                  <button
                    className="btn-pill btn-pill--ghost btn-pill--sm"
                    type="button"
                    id="chip-upload"
                    onClick={triggerFilePicker}
                  >
                    ⬆ Upload drawing
                  </button>

                  <button
                    className="btn-pill btn-pill--ghost btn-pill--sm"
                    type="button"
                    id="chip-search"
                    onClick={() => cmdInputRef.current?.focus()}
                  >
                    ⌖ Search library
                  </button>

                  {showSeedChip ? (
                    <button
                      className={`btn-pill btn-pill--ghost btn-pill--sm${seedStatus === 'loading' ? ' loading' : ''}`}
                      type="button"
                      id="chip-seed"
                      onClick={seedDemo}
                      disabled={seedStatus === 'loading'}
                    >
                      {seedStatus === 'done' ? '✓ Demo ready' : '⊕ Seed demo data'}
                    </button>
                  ) : (
                    <button
                      className="btn-pill btn-pill--ghost btn-pill--sm"
                      type="button"
                      id="chip-recent"
                      disabled
                      aria-disabled="true"
                      title="Upload a drawing to see recent extractions"
                    >
                      ◫ View recent
                    </button>
                  )}

                  <button
                    className="btn-pill btn-pill--ghost btn-pill--sm"
                    type="button"
                    id="chip-more"
                    aria-label="More actions"
                  >
                    ···
                  </button>
                </div>
              </div>

              {/* ── Search results ─────────────────────────────────────────── */}
              {searchError && (
                <div className="search-empty" role="alert">{searchError}</div>
              )}

              {results && !searchError && (
                <div className="search-results" role="listbox" aria-label="Search results">
                  {results.results.length === 0 ? (
                    <div className="search-empty">
                      No drawings found for "{query}".{' '}
                      {results.index_size === 0
                        ? 'Seed demo data or upload a drawing first.'
                        : 'Try a different query.'}
                    </div>
                  ) : (
                    results.results.map((hit) => (
                      <div
                        key={hit.drawing_id}
                        className="search-result-item"
                        role="option"
                        aria-selected="false"
                        tabIndex={0}
                      >
                        <img
                          className="search-result-thumb"
                          src={`${BASE_URL}${hit.preview_url}`}
                          alt={hit.part_name}
                          loading="lazy"
                        />
                        <div className="search-result-info">
                          <div className="search-result-name">{hit.part_name}</div>
                          <div className="search-result-score">
                            Similarity: {(hit.score * 100).toFixed(0)}%
                          </div>
                        </div>
                        <span className="label">{hit.drawing_id.slice(0, 8)}</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </section>

          </div>{/* /glass-panel */}
        </div>{/* /content-area */}
      </div>{/* /app-shell */}

      {/* Hidden file input (shared by all upload triggers) */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,image/png,image/jpeg,image/tiff,image/webp"
        className="sr-only"
        aria-hidden="true"
        tabIndex={-1}
        onChange={handleFileChange}
      />
    </>
  );
}
