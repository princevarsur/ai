/**
 * ThemisMark — the signature SVG mark.
 *
 * A minimal single-stroke balance scale (35 × 40px viewBox).
 * Static at rest. When `thinking={true}`, the path slowly draws
 * itself via stroke-dashoffset — reads as "the system is weighing".
 *
 * Usage:
 *   <ThemisMark size={32} />                  // static
 *   <ThemisMark size={32} thinking />         // animating
 */
export default function ThemisMark({ size = 32, thinking = false, color = 'currentColor' }) {
  // Path length ≈ 200; set as CSS var so the keyframe can reference it.
  const pathLen = 200;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 35 40"
      fill="none"
      aria-hidden="true"
      className={thinking ? 'themis-mark-thinking' : undefined}
      style={{ display: 'block', flexShrink: 0 }}
    >
      {/*
        Balance scale — single continuous path:
          - Vertical fulcrum post
          - Horizontal arm
          - Left pan arc
          - Right pan arc
      */}
      <g stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        {/* Fulcrum post */}
        <line
          x1="17.5" y1="6"
          x2="17.5" y2="34"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
        {/* Base */}
        <line
          x1="10" y1="34"
          x2="25" y2="34"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
        {/* Horizontal arm */}
        <line
          x1="5" y1="10"
          x2="30" y2="10"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
        {/* Left pan chain */}
        <line x1="5" y1="10" x2="5" y2="18"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
        {/* Left pan arc */}
        <path
          d="M1 18 Q5 23 9 18"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
        {/* Right pan chain */}
        <line x1="30" y1="10" x2="30" y2="18"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
        {/* Right pan arc */}
        <path
          d="M26 18 Q30 23 34 18"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
        {/* Top knob */}
        <circle cx="17.5" cy="6" r="1.5"
          className="mark-path"
          style={{ '--path-len': pathLen, strokeDasharray: pathLen, strokeDashoffset: 0 }}
        />
      </g>
    </svg>
  );
}
