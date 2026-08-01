/**
 * TopBar — panel-top navigation strip.
 * Left: brand name + version tag.
 * Centre: page title.
 * Right: Upgrade pill button (visual placeholder for the demo).
 */
interface TopBarProps {
  pageTitle?: string;
  onUpgrade?: () => void;
}

export default function TopBar({
  pageTitle = 'Drawing Studio',
  onUpgrade,
}: TopBarProps) {
  return (
    <header className="top-bar">
      {/* Left — brand */}
      <div className="top-bar__brand">
        <span className="top-bar__logo" aria-hidden="true">⬡</span>
        <span className="top-bar__name">BluePrint AI</span>
        <span className="top-bar__version">v0.1</span>
      </div>

      {/* Centre — page title */}
      <h1 className="top-bar__title">{pageTitle}</h1>

      {/* Right — upgrade CTA */}
      <button
        className="btn-pill btn-pill--amber top-bar__upgrade"
        type="button"
        onClick={onUpgrade}
        aria-label="Upgrade to Pro"
      >
        Upgrade ↗
      </button>
    </header>
  );
}
