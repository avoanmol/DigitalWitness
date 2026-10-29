import type { SVGProps } from "react";

/**
 * DigitalWitness logomark — a document outline with a folded top-right corner.
 * The fold triangle and a polyline inside form an implied "W", connecting the
 * name to documentation and evidence.
 *
 * Usage:
 *   <LogoMark size={32} />            — brass on transparent
 *   <LogoMark size={32} reversed />   — warm brass for dark backgrounds
 */
export function LogoMark({
  size = 32,
  reversed = false,
  className,
  ...props
}: SVGProps<SVGSVGElement> & { size?: number; reversed?: boolean }) {
  const ink  = reversed ? "#E2BD78" : "#A97C2E";
  const fold = reversed ? "#CDA557" : "#8B6627";
  const rule = reversed ? "rgba(226,189,120,0.48)" : "rgba(169,124,46,0.3)";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={className}
      {...props}
    >
      {/* Document body with folded top-right corner */}
      <path
        d="M5 4 H21 L27 10 V28 H5 Z"
        stroke={ink}
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      {/* Fold crease */}
      <path
        d="M21 4 L21 10 L27 10"
        stroke={fold}
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      {/* Implied W — two V-strokes sitting on a base rule */}
      <polyline
        points="9,13 12,20 16,15 20,20 23,13"
        stroke={ink}
        strokeWidth="1.7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Bottom rule — anchors the W visually */}
      <line x1="9" y1="23" x2="23" y2="23" stroke={rule} strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
