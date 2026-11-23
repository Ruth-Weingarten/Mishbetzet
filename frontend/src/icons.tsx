const base = {
  fill: 'none', stroke: 'currentColor', strokeWidth: 1.9,
  strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, 'aria-hidden': true,
}

export const Pencil = ({ size = 22, color }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...base} stroke={color ?? 'currentColor'}>
    <path d="M4 20l4-1 11-11-3-3L5 16l-1 4z" /><path d="M14 6l3 3" />
  </svg>
)

export const Bell = ({ size = 20 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...base}>
    <path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4l2-2z" /><path d="M10 20a2 2 0 0 0 4 0" />
  </svg>
)

export const Book = ({ size = 22 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...base} style={{ flex: 'none', marginTop: 2 }}>
    <path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2V5z" /><path d="M4 19a2 2 0 0 1 2-2h13" />
  </svg>
)

export const Check = ({ size = 18, color = '#D9532C' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" {...base} stroke={color} strokeWidth={3}>
    <path d="M4 13l5 5L21 4" />
  </svg>
)
