import './ReviewScreen.css';
import { BASE_URL } from '../api/client';
import type { UseUploadReturn } from '../hooks/useUpload';

interface ReviewScreenProps {
  upload: UseUploadReturn;
  onBack: () => void;
}

export default function ReviewScreen({ upload, onBack }: ReviewScreenProps) {
  const { phase, drawingId, extraction, error, progress } = upload;

  const data = extraction?.data ?? null;
  const isLoading = phase === 'uploading' || phase === 'extracting';
  const isDone    = phase === 'done';
  const isError   = phase === 'error';

  const phaseLabel = phase === 'uploading' ? 'Uploading drawing…' : 'Analysing with AI…';
  const phaseSub   = phase === 'extracting'
    ? 'Running Qwen2.5-VL — this takes 20–60 s on first call.'
    : 'Sending to Blueprint AI backend…';

  return (
    <div className="app-shell">
      <div className="content-area">
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', minHeight: 'calc(100vh - 64px)' }}>

          {/* ── Nav ───────────────────────────────────────────────────────── */}
          <div className="review-nav">
            <button className="back-btn" type="button" onClick={onBack} id="review-back-btn">
              ← Back
            </button>
            <span className="review-nav__title">
              {isLoading ? 'Processing…' : isDone ? (data?.part_name || 'Extraction Result') : 'Error'}
            </span>
            {extraction?.source === 'demo_fallback' && (
              <span className="source-badge source-badge--demo" title="HF API was unavailable; showing pre-computed demo result">
                ⚠ Demo result
              </span>
            )}
            {extraction?.source === 'hf_api' && isDone && (
              <span className="source-badge source-badge--live">
                ✓ Live extraction
              </span>
            )}
          </div>
          <hr className="divider" />

          {/* ── Loading ────────────────────────────────────────────────────── */}
          {isLoading && (
            <div className="review-loading anim-fade-in">
              <span className="spinner spinner--amber" style={{ width: 36, height: 36, borderWidth: 3 }} />
              <div>
                <div className="review-loading__label">{phaseLabel}</div>
                <div className="review-loading__sub">{phaseSub}</div>
              </div>
              <div className="progress-track" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
                <div className="progress-bar" style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          {/* ── Error ─────────────────────────────────────────────────────── */}
          {isError && (
            <div className="review-error anim-scale-in">
              <div className="review-error__icon">⚠</div>
              <div className="review-error__title">Extraction failed</div>
              <div className="review-error__message">{error}</div>
              <button className="btn-pill btn-pill--amber" type="button" onClick={onBack}>
                Try again
              </button>
            </div>
          )}

          {/* ── Done — review body ─────────────────────────────────────────── */}
          {isDone && data && drawingId && (
            <>
              <div className="review-body anim-fade-up">

                {/* Left — drawing preview */}
                <div className="review-preview">
                  <div className="preview-img-wrap">
                    <img
                      className="preview-img"
                      src={`${BASE_URL}/api/drawing/${drawingId}/preview`}
                      alt={`Drawing preview — ${data.part_name}`}
                    />
                  </div>
                  <div className="body-sm" style={{ color: 'var(--color-ink-subtle)', fontSize: '0.75rem' }}>
                    ID: {drawingId.slice(0, 16)}…
                  </div>
                </div>

                {/* Right — extracted data */}
                <div className="review-data">

                  {/* Title block */}
                  <div className="data-section">
                    <div className="data-section__title">Title block</div>
                    <div className="title-block">
                      {[
                        { label: 'Part name', value: data.part_name },
                        { label: 'Material',  value: data.material },
                        { label: 'Scale',     value: data.scale },
                        { label: 'Revision',  value: data.revision },
                        { label: 'Quantity',  value: data.quantity },
                      ].map(({ label, value }) => (
                        <div key={label} className="field-card">
                          <div className="field-card__label">{label}</div>
                          <div className={`field-card__value${!value ? ' field-card__value--empty' : ''}`}>
                            {value || '—'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Notes */}
                  {data.notes.length > 0 && (
                    <div className="data-section">
                      <div className="data-section__title">Notes</div>
                      <ul style={{ paddingLeft: 'var(--sp-4)', display: 'flex', flexDirection: 'column', gap: 'var(--sp-1)' }}>
                        {data.notes.map((n, i) => (
                          <li key={i} className="body-sm" style={{ color: 'var(--color-ink)' }}>{n}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Dimensions */}
                  <div className="data-section">
                    <div className="data-section__title">Dimensions ({data.dimensions.length})</div>
                    {data.dimensions.length === 0 ? (
                      <div className="data-empty">No dimensions extracted.</div>
                    ) : (
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Value</th>
                            <th>Tolerance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.dimensions.map((d, i) => (
                            <tr key={i}>
                              <td>{d.value}</td>
                              <td>{d.tolerance || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* GD&T */}
                  <div className="data-section">
                    <div className="data-section__title">GD&amp;T callouts ({data.gdt_callouts.length})</div>
                    {data.gdt_callouts.length === 0 ? (
                      <div className="data-empty">No GD&amp;T callouts extracted.</div>
                    ) : (
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Characteristic</th>
                            <th>Tolerance zone</th>
                            <th>Datums</th>
                          </tr>
                        </thead>
                        <tbody>
                          {data.gdt_callouts.map((g, i) => (
                            <tr key={i}>
                              <td>{g.characteristic}</td>
                              <td>{g.tolerance_zone}</td>
                              <td>{g.datum_refs || '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Surface finish */}
                  {data.surface_finish.length > 0 && (
                    <div className="data-section">
                      <div className="data-section__title">Surface finish ({data.surface_finish.length})</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--sp-2)' }}>
                        {data.surface_finish.map((s, i) => (
                          <span key={i} className="btn-pill btn-pill--ghost btn-pill--sm" style={{ cursor: 'default' }}>
                            {s.value}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                </div>{/* /review-data */}
              </div>{/* /review-body */}

              {/* ── Action footer ──────────────────────────────────────────── */}
              <div className="review-actions">
                <button className="btn-pill btn-pill--amber" type="button" id="review-verify-btn">
                  ✓ Verify &amp; index
                </button>
                <button className="btn-pill btn-pill--ghost" type="button" onClick={onBack}>
                  Upload another
                </button>
                <span className="spacer" />
                <span className="label" style={{ color: 'var(--color-ink-subtle)' }}>
                  {drawingId.slice(0, 8)}
                </span>
              </div>
            </>
          )}

          {/* Extraction returned status=error (API itself worked, model failed) */}
          {isDone && extraction?.status === 'error' && (
            <div className="review-error anim-scale-in">
              <div className="review-error__icon">🤔</div>
              <div className="review-error__title">Extraction returned an error</div>
              <div className="review-error__message">{extraction.error_message}</div>
              <div style={{ display: 'flex', gap: 'var(--sp-3)' }}>
                <button className="btn-pill btn-pill--amber" type="button" onClick={onBack}>
                  Try again
                </button>
              </div>
            </div>
          )}

        </div>{/* /glass-panel */}
      </div>{/* /content-area */}
    </div>
  );
}
