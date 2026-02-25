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
            d="M25 20 C15 20, 10 25, 10 35 L10 50 C10 60, 15 65, 25 65 L28 65 L25 75 L32 65 L40 65 C50 65, 55 60, 55 50 L55 35 C55 25, 50 20, 40 20 Z"
            fill="url(#gradient1)"
            opacity="0.9"
          />
          {/* Sound wave lines inside */}
          <path
            d="M22 38 L28 42 L22 46 M30 35 L38 42.5 L30 50 M40 38 L46 42 L40 46"
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
            d="M60 25 C50 25, 45 30, 45 40 L45 55 C45 65, 50 70, 60 70 L63 70 L60 80 L67 70 L75 70 C85 70, 90 65, 90 55 L90 40 C90 30, 85 25, 75 25 Z"
            fill="url(#gradient2)"
            opacity="0.9"
          />
          {/* Connection dots */}
          <circle cx="60" cy="47.5" r="3" fill="white" />
          <circle cx="67.5" cy="47.5" r="3" fill="white" />
          <circle cx="75" cy="47.5" r="3" fill="white" />
        </g>

        {/* Connection line between bubbles */}
        <line
          x1="50"
          y1="42.5"
          x2="50"
          y2="42.5"
          stroke="url(#gradient1)"
          strokeWidth="2"
          opacity="0.6"
        >
          <animate
            attributeName="x2"
            from="50"
            to="50"
            dur="2s"
            repeatCount="indefinite"
          />
        </line>
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
