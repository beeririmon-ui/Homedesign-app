export function prefersReducedMotion(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** Slow-motion factor for evidence screenshots (tools/screens-room.ts sets window.__hdSlowMo); 1 otherwise. */
export function timeScale(): number {
  const k = (globalThis as { __hdSlowMo?: unknown }).__hdSlowMo;
  return typeof k === 'number' && k > 0 ? k : 1;
}
