type LogoProps = {
  compact?: boolean;
  className?: string;
};

export function LokiMark({ className = "" }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={className}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        d="M8 32C14.5 22.5 22.5 18 32 18C41.5 18 49.5 22.5 56 32C49.5 41.5 41.5 46 32 46C22.5 46 14.5 41.5 8 32Z"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M19 22L14 9L27 18M45 22L50 9L37 18"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M32 22L42 32L32 42L22 32L32 22Z"
        fill="currentColor"
      />
      <path
        d="M32 27L36 32L32 37L28 32L32 27Z"
        fill="var(--mark-ink, #151515)"
      />
    </svg>
  );
}

export function EyeOfLokiLogo({ compact, className = "" }: LogoProps) {
  return (
    <div className={`brand-lockup ${className}`}>
      <span className="brand-mark-shell">
        <LokiMark />
      </span>
      {!compact && (
        <span className="brand-type">
          <span>EYE OF</span>
          <strong>LOKI</strong>
        </span>
      )}
    </div>
  );
}
