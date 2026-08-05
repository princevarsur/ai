/**
 * ThemisMark — signature SVG balance mark.
 *
 * A minimal single-stroke balance scale (35 × 40px viewBox).
 * When `thinking={true}`, the beam gracefully oscillates around its fulcrum,
 * providing intuitive physical motion representing judicial weighing ofevidence.
 */
export default function ThemisMark({ size = 32, thinking = false, color = 'currentColor' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 35 40"
      fill="none"
      aria-hidden="true"
      className={thinking ? 'themis-mark-thinking' : undefined}
      style={{ display: 'block', flexShrink: 0, overflow: 'visible' }}
    >
      <g stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        {/* Stationary Fulcrum Base */}
        <g className="mark-fulcrum">
          <line x1="17.5" y1="6" x2="17.5" y2="34" />
          <line x1="10" y1="34" x2="25" y2="34" />
          <circle cx="17.5" cy="6" r="1.5" />
        </g>

        {/* Oscillating Beam and Pan Assembly (Pivot at 17.5, 10) */}
        <g className="themis-beam" style={{ transformOrigin: '17.5px 10px' }}>
          {/* Horizontal arm */}
          <line x1="5" y1="10" x2="30" y2="10" />
          {/* Left pan chain & arc */}
          <line x1="5" y1="10" x2="5" y2="18" />
          <path d="M1 18 Q5 23 9 18" />
          {/* Right pan chain & arc */}
          <line x1="30" y1="10" x2="30" y2="18" />
          <path d="M26 18 Q30 23 34 18" />
        </g>
      </g>
    </svg>
  );
}
