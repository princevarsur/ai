import React from 'react';

export default function ChalkBookLoader({ size = 68 }) {
  const width = size * 1.4;
  const height = size;

  return (
    <div className="chalk-book-wrapper" style={{
      width: `${width}px`,
      height: `${height}px`,
      position: 'relative',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'transparent',
      perspective: '600px',
    }}>
      <style>{`
        .chalk-outline {
          filter: url(#charcoal-roughness);
        }

        .charcoal-leaf {
          position: absolute;
          right: 50%;
          top: 12%;
          width: 45%;
          height: 76%;
          transform-origin: right center;
          transform-style: preserve-3d;
          background: transparent;
          border: 2.2px solid var(--ink, #1F2227);
          border-radius: 2px 8px 8px 2px;
          display: flex;
          flex-direction: column;
          padding: 8px 6px;
          gap: 5px;
          filter: url(#charcoal-roughness);
          opacity: 0.95;
        }

        .leaf-1 { animation: char-flip 3.2s cubic-bezier(0.35, 0.1, 0.25, 1) infinite 0s; z-index: 4; }
        .leaf-2 { animation: char-flip 3.2s cubic-bezier(0.35, 0.1, 0.25, 1) infinite 1.1s; z-index: 3; }
        .leaf-3 { animation: char-flip 3.2s cubic-bezier(0.35, 0.1, 0.25, 1) infinite 2.2s; z-index: 2; }

        .char-line {
          height: 2px;
          background: var(--ink, #1F2227);
          opacity: 0.65;
          border-radius: 2px;
          width: 85%;
          filter: url(#charcoal-roughness);
        }
        .char-line.short { width: 55%; }

        @keyframes char-flip {
          0% {
            transform: rotateY(0deg);
            opacity: 0.9;
          }
          45% {
            transform: rotateY(-90deg) scaleY(1.04);
            opacity: 1;
          }
          90% {
            transform: rotateY(-179deg);
            opacity: 0.9;
          }
          91% { opacity: 0; transform: rotateY(-179deg); }
          99% { opacity: 0; transform: rotateY(0deg); }
          100% { opacity: 0.9; transform: rotateY(0deg); }
        }
      `}</style>

      {/* SVG Filter for Charcoal Black Hand-Drawn Outline Texture */}
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <filter id="charcoal-roughness" x="-10%" y="-10%" width="120%" height="120%">
            <feTurbulence type="fractalNoise" baseFrequency="0.08" numOctaves="2" result="noise" />
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.6" xChannelSelector="R" yChannelSelector="G" />
          </filter>
        </defs>
      </svg>

      {/* Static Transparent Open Book Base (Charcoal Chalk Outlines Only) */}
      <svg
        width="100%"
        height="100%"
        viewBox="0 0 120 86"
        fill="none"
        className="chalk-outline"
        style={{ position: 'absolute', inset: 0 }}
      >
        {/* Left Open Page Outline */}
        <path
          d="M 60 14 C 42 12, 22 15, 6 20 L 6 76 C 22 71, 42 68, 60 72 Z"
          stroke="var(--ink, #1F2227)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Right Open Page Outline */}
        <path
          d="M 60 14 C 78 12, 98 15, 114 20 L 114 76 C 98 71, 78 68, 60 72 Z"
          stroke="var(--ink, #1F2227)"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Central Spine Fold */}
        <line x1="60" y1="14" x2="60" y2="73" stroke="var(--ink, #1F2227)" strokeWidth="2.2" strokeLinecap="round" />

        {/* Sketched Text Lines on Left Page */}
        <line x1="14" y1="30" x2="52" y2="28" stroke="var(--ink, #1F2227)" strokeWidth="1.8" strokeLinecap="round" strokeOpacity="0.55" />
        <line x1="14" y1="42" x2="48" y2="40" stroke="var(--ink, #1F2227)" strokeWidth="1.8" strokeLinecap="round" strokeOpacity="0.55" />
        <line x1="14" y1="54" x2="36" y2="52" stroke="var(--ink, #1F2227)" strokeWidth="1.8" strokeLinecap="round" strokeOpacity="0.55" />

        {/* Sketched Text Lines on Right Page */}
        <line x1="68" y1="28" x2="106" y2="30" stroke="var(--ink, #1F2227)" strokeWidth="1.8" strokeLinecap="round" strokeOpacity="0.55" />
        <line x1="68" y1="40" x2="102" y2="42" stroke="var(--ink, #1F2227)" strokeWidth="1.8" strokeLinecap="round" strokeOpacity="0.55" />
        <line x1="68" y1="52" x2="92" y2="54" stroke="var(--ink, #1F2227)" strokeWidth="1.8" strokeLinecap="round" strokeOpacity="0.55" />
      </svg>

      {/* 3D Flipping Leaves (Transparent with Charcoal Outline & Lines) */}
      <div className="charcoal-leaf leaf-1">
        <div className="char-line" />
        <div className="char-line short" />
        <div className="char-line" style={{ marginTop: 4 }} />
      </div>
      
      <div className="charcoal-leaf leaf-2">
        <div className="char-line short" />
        <div className="char-line" />
        <div className="char-line short" style={{ marginTop: 4 }} />
      </div>

      <div className="charcoal-leaf leaf-3">
        <div className="char-line" />
        <div className="char-line short" />
      </div>
    </div>
  );
}
