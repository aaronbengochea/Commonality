interface LogoProps {
  size?: number;
  showText?: boolean;
  variant?: 'default' | 'icon-only';
}

export function Logo({ size = 200, showText = true, variant = 'default' }: LogoProps) {
  const iconSize = variant === 'icon-only' ? size : size * 0.4;
  const fontSize = size * 0.12;

  return (
    <div className="flex items-center gap-4">
      {/* Icon: Overlapping speech bubbles forming a connection */}
      <svg
        width={iconSize}
        height={iconSize}
        viewBox="0 0 100 100"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Background glow effect */}
        <defs>
          <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
          <linearGradient id="gradient2" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ec4899" />
            <stop offset="100%" stopColor="#f43f5e" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
            <feMerge>
              <feMergeNode in="coloredBlur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* Left chat bubble with sound wave */}
        <g filter="url(#glow)">
          <path
            d="M25 10 C15 10, 10 15, 10 25 L10 45 C10 55, 15 60, 25 60 L28 60 L25 70 L32 60 L45 60 C55 60, 60 55, 60 45 L60 25 C60 15, 55 10, 45 10 Z"
            fill="url(#gradient1)"
            opacity="0.9"
          />
          {/* Sound wave lines inside */}
          <path
            d="M22 28 L28 33 L22 38 M30 25 L38 33 L30 41 M40 28 L46 33 L40 38"
            stroke="white"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        </g>

        {/* Right chat bubble with connection dots */}
        <g filter="url(#glow)">
          <path
            d="M55 20 C45 20, 40 25, 40 35 L40 55 C40 65, 45 70, 55 70 L58 70 L55 80 L62 70 L75 70 C85 70, 90 65, 90 55 L90 35 C90 25, 85 20, 75 20 Z"
            fill="url(#gradient2)"
            opacity="0.9"
          />
          {/* Connection dots */}
          <circle cx="58" cy="45" r="3" fill="white" />
          <circle cx="65" cy="45" r="3" fill="white" />
          <circle cx="72" cy="45" r="3" fill="white" />
        </g>
      </svg>

      {/* Text logo */}
      {showText && variant === 'default' && (
        <div className="flex flex-col justify-center">
          <div
            className="font-bold tracking-tight"
            style={{
              fontSize: fontSize * 2,
              background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            Commonality
          </div>
          <div
            className="tracking-wider uppercase opacity-60"
            style={{
              fontSize: fontSize * 0.6,
              color: '#64748b',
              marginTop: -fontSize * 0.3,
            }}
          >
            Chat &bull; Voice &bull; Connect
          </div>
        </div>
      )}
    </div>
  );
}
