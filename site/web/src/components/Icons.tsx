/** Inline icons (decorative: aria-hidden). Stroke follows currentColor. */
const base = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.7, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'aria-hidden': 'true', focusable: 'false' } as const;

export const IconHouse = () => (
  <svg {...base} viewBox="0 0 32 32" stroke-width={2}>
    <path d="M6 27V14l10-8 10 8v13h-6.5v-8h-7v8z" />
  </svg>
);
export const IconBag = () => (
  <svg {...base}>
    <path d="M5 8h14l-1 12H6z" />
    <path d="M9 8V6a3 3 0 0 1 6 0v2" />
  </svg>
);
export const IconTheme = () => (
  <svg {...base}>
    <path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z" />
  </svg>
);
export const IconClose = () => (
  <svg {...base}>
    <path d="M6 6l12 12M18 6L6 18" />
  </svg>
);
/** Points to the visual left ("next" in RTL). */
export const IconLeft = () => (
  <svg {...base}>
    <path d="M15 5l-7 7 7 7" />
  </svg>
);
export const IconRight = () => (
  <svg {...base}>
    <path d="M9 5l7 7-7 7" />
  </svg>
);
export const IconDoor = () => (
  <svg {...base}>
    <path d="M6 21V4h10v17M4 21h16M13 12h.01" />
  </svg>
);
