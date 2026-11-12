/**
 * S23, QA ת72 (c) and ה29: what this tab tells the next page it loads, kept in `window.name` and never in the address
 * (so never in the tab's history, the browser's History database, a referrer or a server's log).
 * - **`c`, the cart id,** only when this browser keeps no storage (with storage, localStorage has it). It replaces the
 *   `#c=` fragment of S21.
 * - **`w`, the cart writes still on their way** (ה29): the line each one sets. A page left while a write was on its way
 *   (a slow phone network: over the 4 s the move waits) leaves its mark, and the next page reads the cart again until
 *   the write has landed (at most PENDING_WAIT_MS after it began), never saying "empty" meanwhile.
 *
 * Why window.name: it stays with the tab across its navigations within the site (a link, a reload, back and forward, a
 * typed address). Every page of the site sends the same Cross-Origin-Opener-Policy (same-origin, web/public/_headers),
 * so no navigation between them changes the browsing context group, which would clear it; a navigation to another site
 * does, and current browsers clear the name on a cross-site navigation in any case (the e2e checks Chromium's). A new
 * tab or window starts without it, as it started without the fragment.
 *
 * A name that is not ours (a window opened with a target name) is never overwritten. Shared by the shop (state/cart.ts)
 * and the story (story/api-cart.ts): both see the same cart id and the same marks.
 */
import type { Cart, Pack } from '@hd/shared';

const PREFIX = 'hd1:';
/** a cart id as the API and the mock make them (base64url or hex) */
export const CART_ID = /^[A-Za-z0-9_-]{8,80}$/;
/** how long after a write began the next page keeps reading the cart for it (ה29) */
export const PENDING_WAIT_MS = 12_000;
/** how often it reads again meanwhile */
export const REREAD_MS = 700;
/** a mark older than this is dropped when the name is read (a write that never said how it ended) */
const MARK_MAX_AGE_MS = 60_000;

/** a write on its way: the line it sets (variant, pack, absolute quantity), when it began, and its own key */
export type PendingWrite = { v: string; p: Pack; q: number; t: number; k: string };
type Carried = { c?: string; w?: PendingWrite[] };

const isMark = (x: unknown): x is PendingWrite => {
  const m = x as PendingWrite | null;
  return (
    !!m &&
    typeof m.v === 'string' &&
    m.v.length > 0 &&
    m.v.length <= 200 &&
    (m.p === 'set' || m.p === 'unit') &&
    Number.isInteger(m.q) &&
    m.q >= 0 &&
    m.q <= 20 &&
    typeof m.t === 'number' &&
    Number.isFinite(m.t) &&
    typeof m.k === 'string' &&
    m.k.length <= 40
  );
};

function name(): string | null {
  try {
    return typeof window === 'undefined' ? null : window.name;
  } catch {
    return null;
  }
}
/** what the name carries: read, never trusted beyond its shape */
function read(): Carried {
  const n = name();
  if (!n || !n.startsWith(PREFIX)) return {};
  try {
    const x = JSON.parse(n.slice(PREFIX.length)) as Carried;
    const now = Date.now();
    return {
      c: typeof x.c === 'string' && CART_ID.test(x.c) ? x.c : undefined,
      w: Array.isArray(x.w) ? x.w.filter(isMark).filter((m) => now - m.t < MARK_MAX_AGE_MS && m.t <= now + 1000) : undefined,
    };
  } catch {
    return {};
  }
}
function write(c: Carried): void {
  const n = name();
  // a name that is not ours stays as it is
  if (n === null || (n !== '' && !n.startsWith(PREFIX))) return;
  const next = c.c || c.w?.length ? `${PREFIX}${JSON.stringify({ ...(c.c ? { c: c.c } : {}), ...(c.w?.length ? { w: c.w.slice(-30) } : {}) })}` : '';
  if (next === n) return;
  try {
    window.name = next;
  } catch {
    /* a frame that may not name itself: nothing is carried */
  }
}

/** the cart id the page before carried (a browser without storage), or null */
export function carriedCartId(): string | null {
  return read().c ?? null;
}
/** the cart id for the next page, or none (null: storage keeps it, or there is no cart) */
export function carryCartId(id: string | null): void {
  const cur = read();
  if ((cur.c ?? null) === (id && CART_ID.test(id) ? id : null)) return;
  write({ ...cur, c: id && CART_ID.test(id) ? id : undefined });
}

/** ה29: marks a write on its way; the function returned clears the mark (call it once the write has its answer) */
export function markWrite(v: string, p: Pack, q: number): { key: string; done: () => void } {
  const key = Math.random().toString(36).slice(2, 10);
  const cur = read();
  // a later write of the same line replaces the earlier one's mark: the line ends as the later one sets it
  write({ ...cur, w: [...(cur.w ?? []).filter((m) => !(m.v === v && m.p === p)), { v, p, q: Math.max(0, Math.min(20, Math.trunc(q))), t: Date.now(), k: key }] });
  return {
    key,
    done: () => {
      const now = read();
      if (now.w?.some((m) => m.k === key)) write({ ...now, w: now.w.filter((m) => m.k !== key) });
    },
  };
}

/**
 * ה29: the writes a page before this one left on their way (not this page's own, `own`), still within PENDING_WAIT_MS,
 * that the cart read now does not show yet: a line whose quantity differs (or that is there when the write removed it).
 */
export function writesNotLanded(cart: Cart | null, own: ReadonlySet<string>, now = Date.now()): PendingWrite[] {
  const marks = (read().w ?? []).filter((m) => !own.has(m.k) && now - m.t < PENDING_WAIT_MS);
  return marks.filter((m) => {
    const line = cart?.lines.find((l) => l.variant_id === m.v && l.pack === m.p);
    return m.q === 0 ? !!line : line?.qty !== m.q;
  });
}
/** ה29: the marks of other pages are settled (their writes landed, or their time is up): they are dropped */
export function settleForeignWrites(own: ReadonlySet<string>): void {
  const cur = read();
  if (!cur.w?.length) return;
  const keep = cur.w.filter((m) => own.has(m.k));
  if (keep.length !== cur.w.length) write({ ...cur, w: keep });
}
