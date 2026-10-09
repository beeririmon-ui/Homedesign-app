import { signal } from '@preact/signals';

/** One polite live region for the whole app: announcements are also shown as a short toast. */
export const announcement = signal<{ id: number; text: string } | null>(null);
let n = 0;
let timer: ReturnType<typeof setTimeout> | undefined;
export function announce(text: string): void {
  announcement.value = { id: ++n, text };
  clearTimeout(timer);
  timer = setTimeout(() => (announcement.value = null), 3200);
}

export type ThemePref = 'system' | 'light' | 'dark';
export const theme = signal<ThemePref>('system');

export function loadTheme(): void {
  try {
    const t = localStorage.getItem('hd.theme');
    if (t === 'light' || t === 'dark') theme.value = t;
  } catch {
    /* storage unavailable */
  }
  applyTheme();
}
export function cycleTheme(): void {
  theme.value = theme.value === 'system' ? 'dark' : theme.value === 'dark' ? 'light' : 'system';
  try {
    if (theme.value === 'system') localStorage.removeItem('hd.theme');
    else localStorage.setItem('hd.theme', theme.value);
  } catch {
    /* storage unavailable */
  }
  applyTheme();
}
function applyTheme(): void {
  const el = document.documentElement;
  if (theme.value === 'system') el.removeAttribute('data-theme');
  else el.setAttribute('data-theme', theme.value);
}
