import { signal } from '@preact/signals';

/** One polite live region for the whole app: announcements are said, never shown (S6, §7.2: no toast). */
export const announcement = signal<{ id: number; text: string } | null>(null);
let n = 0;
let timer: ReturnType<typeof setTimeout> | undefined;
export function announce(text: string): void {
  announcement.value = { id: ++n, text };
  clearTimeout(timer);
  timer = setTimeout(() => (announcement.value = null), 3200);
}
