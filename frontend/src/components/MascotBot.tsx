/**
 * MascotBot — the Blueprint AI mascot.
 *
 * Pure inline SVG: no images, no external files, no complex paths.
 * Shapes only: semicircular protractor arc (head), rounded rects (body/limbs),
 * circles (eyes, end caps), a 3×3 dot grid chest panel.
 *
 * Animations are driven by CSS classes defined in HomeScreen.css.
 */
export default function MascotBot() {
  return (
    <div className="mascot-wrapper" aria-hidden="true">
      {/* Speech bubble (CSS-positioned above the SVG) */}
      <div className="mascot-bubble" role="img" aria-label="Mascot speech bubble">
        Drop a drawing —<br />I'll pull the specs.
      </div>

      <svg
        className="mascot-svg"
        viewBox="0 0 120 192"
        xmlns="http://www.w3.org/2000/svg"
        overflow="visible"
        aria-hidden="true"
        focusable="false"
      >
        {/* ── Protractor arc (head) ─────────────────────────────────────── */}
        {/* Semicircle curving UP from (22,75) through (60,37) to (98,75) */}
        <path
          d="M 22 75 A 38 38 0 0 0 98 75"
          fill="none"
          stroke="var(--color-ink)"
          strokeWidth="5"
          strokeLinecap="round"
        />

        {/* Degree tick marks (inner r=31, outer r=38, every 30°) */}
        {/* 0° */}
        <line x1="91" y1="75" x2="98" y2="75" stroke="var(--color-ink)" strokeWidth="2.5" strokeLinecap="round" />
        {/* 30° */}
        <line x1="86.9" y1="56.5" x2="92.9" y2="56" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" />
        {/* 60° */}
        <line x1="75.5" y1="48.1" x2="79.0" y2="42.1" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" />
        {/* 90° */}
        <line x1="60" y1="44" x2="60" y2="37" stroke="var(--color-ink)" strokeWidth="2.5" strokeLinecap="round" />
        {/* 120° */}
        <line x1="44.5" y1="48.1" x2="41.0" y2="42.1" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" />
        {/* 150° */}
        <line x1="33.1" y1="56.5" x2="27.1" y2="56" stroke="var(--color-ink)" strokeWidth="2" strokeLinecap="round" />
        {/* 180° */}
        <line x1="29" y1="75" x2="22" y2="75" stroke="var(--color-ink)" strokeWidth="2.5" strokeLinecap="round" />

        {/* Center pivot dot */}
        <circle cx="60" cy="75" r="3.5" fill="var(--color-amber)" />

        {/* ── Face (lower head rectangle) ───────────────────────────────── */}
        <rect x="22" y="68" width="76" height="28" rx="12" fill="var(--color-ink)" />

        {/* Eyes */}
        <circle className="mascot-eye" cx="44" cy="82" r="5" fill="var(--color-amber)" />
        <circle className="mascot-eye" cx="76" cy="82" r="5" fill="var(--color-amber)" />
        {/* Eye glow rings */}
        <circle className="mascot-eye-ring" cx="44" cy="82" r="9" fill="none" stroke="var(--color-amber)" strokeWidth="1.5" />
        <circle className="mascot-eye-ring" cx="76" cy="82" r="9" fill="none" stroke="var(--color-amber)" strokeWidth="1.5" />

        {/* ── Neck ──────────────────────────────────────────────────────── */}
        <rect x="50" y="96" width="20" height="10" rx="4" fill="var(--color-ink)" />

        {/* ── Body ──────────────────────────────────────────────────────── */}
        <rect x="20" y="106" width="80" height="54" rx="14" fill="var(--color-ink)" />

        {/* Chest panel (blueprint grid background) */}
        <rect className="mascot-chest" x="32" y="114" width="56" height="38" rx="8"
          fill="rgba(94,200,216,0.18)" stroke="rgba(94,200,216,0.30)" strokeWidth="1" />

        {/* Blueprint grid — 3×3 cyan dots */}
        {([0, 1, 2] as const).flatMap((row) =>
          ([0, 1, 2] as const).map((col) => (
            <circle
              key={`d-${row}-${col}`}
              className="mascot-grid-dot"
              cx={44 + col * 14}
              cy={124 + row * 11}
              r="2.3"
              fill="var(--color-cyan)"
            />
          ))
        )}

        {/* ── Arms ──────────────────────────────────────────────────────── */}
        <rect x="1" y="116" width="21" height="10" rx="5" fill="var(--color-ink)" />
        <rect x="98" y="116" width="21" height="10" rx="5" fill="var(--color-ink)" />
        {/* Arm end caps (amber) */}
        <circle cx="2" cy="121" r="5.5" fill="var(--color-amber)" />
        <circle cx="118" cy="121" r="5.5" fill="var(--color-amber)" />

        {/* ── Legs ──────────────────────────────────────────────────────── */}
        <rect x="32" y="160" width="20" height="22" rx="8" fill="var(--color-ink)" />
        <rect x="68" y="160" width="20" height="22" rx="8" fill="var(--color-ink)" />
        {/* Feet */}
        <rect x="27" y="177" width="28" height="9" rx="4.5" fill="var(--color-ink)" opacity="0.55" />
        <rect x="65" y="177" width="28" height="9" rx="4.5" fill="var(--color-ink)" opacity="0.55" />
      </svg>
    </div>
  );
}
