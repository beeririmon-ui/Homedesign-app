/**
 * MOCK9 (2026-11-27, FB21): the guided route's banner. Delicate and half transparent: the station the visitor is at,
 * the next one lit, a "הלאה" arrow that walks there, and a slim rail of every station in the route's order that scrolls
 * like a rail of rooms (it keeps the station shown in the middle, and follows a chained jump station by station).
 * A station ahead travels there (chained, faster); a station behind goes back through the light (tour/route.ts).
 * The page holds the rules; this only draws the route and says what was pressed.
 */
import { useEffect, useRef } from 'preact/hooks';
import { GROUP_HE, type GroupId } from './data';
import { ROUTE } from './route';

const two = (n: number): string => String(n).padStart(2, '0');

export function RouteBanner({
  at,
  off,
  busy,
  onGo,
}: {
  /** the station shown: where the visitor is, or the one a chain is passing */
  at: GroupId;
  /** hidden (the door, the walk in, a close-up open, the panel open) */
  off: boolean;
  busy: boolean;
  onGo: (g: GroupId) => void;
}) {
  const rail = useRef<HTMLOListElement>(null);
  const i = ROUTE.indexOf(at);
  const next = ROUTE[i + 1] ?? null;
  // the rail keeps the station shown in its middle (a relative scroll: the same in either direction of the page)
  useEffect(() => {
    const r = rail.current;
    const b = r?.querySelector<HTMLElement>('[data-k="here"]');
    if (!r || !b) return;
    const rr = r.getBoundingClientRect();
    const br = b.getBoundingClientRect();
    const dx = br.left + br.width / 2 - (rr.left + rr.width / 2);
    if (Math.abs(dx) > 1) r.scrollBy({ left: dx, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [at, off]);
  const hide = off ? ({ inert: true, 'aria-hidden': 'true' } as const) : {};
  return (
    <nav class="route" aria-label="מסלול הסיור" data-off={off ? '' : undefined} data-busy={busy ? '' : undefined} {...hide}>
      <ol class="route-rail" ref={rail}>
        {ROUTE.map((g, k) => {
          const kind = k < i ? 'past' : k === i ? 'here' : k === i + 1 ? 'next' : 'ahead';
          return (
            <li key={g}>
              <button
                type="button"
                data-k={kind}
                data-g={g}
                aria-current={kind === 'here' ? 'step' : undefined}
                aria-label={`${two(k + 1)} ${GROUP_HE[g]}${kind === 'here' ? ', כאן' : kind === 'past' ? ', חזרה' : ''}`}
                disabled={kind === 'here'}
                onClick={() => onGo(g)}
              >
                <span class="n" aria-hidden="true">
                  {two(k + 1)}
                </span>
                <span class="nm" aria-hidden="true">
                  {GROUP_HE[g]}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      {next ? (
        <button type="button" class="route-next" id="route-next" aria-label={`הלאה: ${GROUP_HE[next]}`} onClick={() => onGo(next)}>
          <span class="k" aria-hidden="true">
            הבא
          </span>
          <span class="nm" aria-hidden="true">
            {GROUP_HE[next]}
          </span>
          <span class="arr" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 12H5M11 6l-6 6 6 6" />
            </svg>
          </span>
        </button>
      ) : (
        <button
          type="button"
          class="route-next"
          id="route-next"
          data-end=""
          aria-label={`סוף המסלול. חזרה ל${GROUP_HE[ROUTE[0]!]}`}
          onClick={() => onGo(ROUTE[0]!)}
        >
          <span class="k" aria-hidden="true">
            סוף המסלול
          </span>
          <span class="nm" aria-hidden="true">
            {GROUP_HE[ROUTE[0]!]}
          </span>
          <span class="arr" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </span>
        </button>
      )}
    </nav>
  );
}
