export const colors = {
  bg: {
    primary: '#0A0A0F',
    surface: '#12121A',
    elevated: '#1A1A25',
  },
  accent: {
    gradient: 'linear-gradient(135deg, #00D4AA, #00A3FF)',
    from: '#00D4AA',
    to: '#00A3FF',
  },
  success: '#00FF88',
  danger: '#FF3366',
  warning: '#FFB800',
  text: {
    primary: '#E8E8ED',
    secondary: '#6B6B80',
    muted: '#45455A',
  },
  border: {
    subtle: 'rgba(255, 255, 255, 0.06)',
    hover: 'rgba(255, 255, 255, 0.12)',
  },
} as const;

export const fonts = {
  heading: "'Space Grotesk', sans-serif",
  body: "'DM Sans', sans-serif",
  mono: "'JetBrains Mono', monospace",
} as const;

export const radii = {
  chip: '4px',
  button: '6px',
  card: '8px',
  modal: '12px',
} as const;

export const animations = {
  duration: {
    fast: 150,
    normal: 200,
    slow: 300,
    content: 500,
  },
  easing: {
    enter: 'ease-out',
    exit: 'ease-in',
    move: [0.4, 0, 0.2, 1],
  },
  spring: {
    stiffness: 300,
    damping: 30,
  },
  stagger: 50,
} as const;

export const shadows = {
  glow: {
    accent: '0 0 20px rgba(0, 212, 170, 0.15)',
    success: '0 0 20px rgba(0, 255, 136, 0.15)',
    danger: '0 0 20px rgba(255, 51, 102, 0.15)',
  },
} as const;
