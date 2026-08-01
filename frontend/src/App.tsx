import './App.css'

/**
 * App — placeholder shell UI.
 *
 * Business logic (file upload → POST /api/extract → render results)
 * will be implemented in a future milestone.
 */
function App() {
  return (
    <div className="app-shell">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="logo-mark" aria-hidden="true">⬡</div>
        <div className="header-text">
          <h1 className="app-title">Blueprint AI</h1>
          <p className="app-subtitle">Engineering Drawing Interpreter</p>
        </div>
      </header>

      {/* ── Main ── */}
      <main className="app-main">
        <section className="upload-card" aria-label="Drawing upload">
          <div className="upload-icon" aria-hidden="true">📐</div>
          <h2 className="upload-heading">Upload a Drawing</h2>
          <p className="upload-description">
            Drop a PDF or raster image of an engineering drawing to extract
            dimensions, GD&amp;T callouts, surface finish specs, and more.
          </p>

          <label id="file-upload-label" htmlFor="file-upload" className="upload-btn">
            Choose file
            <input
              id="file-upload"
              type="file"
              accept=".pdf,image/png,image/jpeg,image/tiff,image/webp"
              className="visually-hidden"
              aria-labelledby="file-upload-label"
            />
          </label>

          <p className="upload-hint">PDF · PNG · JPEG · TIFF · WEBP</p>
        </section>

        {/* ── Status banner ── */}
        <div className="status-banner" role="status">
          <span className="status-dot" aria-hidden="true" />
          Backend integration coming soon — scaffolding only.
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="app-footer">
        Blueprint AI Drawing Interpreter &mdash; v0.1.0
      </footer>
    </div>
  )
}

export default App
