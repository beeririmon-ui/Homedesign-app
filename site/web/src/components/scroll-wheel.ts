/**
 * MOCK6 (2026-11-25, briefs/site-mock6-kids-rooms-2026-11-25.md ch. 3): the wheel of many options. The owner asked for
 * "in the scroll, many options" for the kids' art (FB12; the designer's 10 sets a room, docs/proposals/wm-fb12-2026-11-25.md
 * ב.4, ב.8). The 3D arc (VariantWheel) shows two or three options well; from MANY_FROM options on, the wheel is a
 * scroll-snap carousel (ScrollWheel.tsx) with a counter ("3 / 10"), the keys and a swipe, and only the option it rests on
 * is asked for (its patch loads then, never all of them ahead: data.ts `behind`).
 *
 * The rules here are plain functions, so the fixture of ten options (web/test/mock6-tour.test.ts) tests them without a
 * browser; the component wires them to the DOM.
 */

/** from this many options a wheel is the scroll-snap carousel (the 3D arc keeps two or three: the throws, the towels) */
export const MANY_FROM = 4;
/** the owner's counter under the carousel: "3 / 10" (the option it rests on, of how many) */
export const counterHe = (index: number, n: number): string => `${index + 1} / ${n}`;
/** a card's name for a screen reader: "3 מתוך 10: …" (as the 3D arc says it) */
export const cardLabelHe = (index: number, n: number, name: string): string => `${index + 1} מתוך ${n}: ${name}`;

/**
 * The card a scroller rests on: the one whose centre is nearest the scroller's centre (x in the viewport's pixels, so it
 * holds in a right-to-left scroller, whose scrollLeft runs negative). Ties go to the lower index.
 */
export function nearest(centers: readonly number[], mid: number): number {
  let best = 0;
  let d = Infinity;
  centers.forEach((c, i) => {
    const di = Math.abs(c - mid);
    if (di < d - 0.5) {
      d = di;
      best = i;
    }
  });
  return best;
}

/**
 * A key's move, in a right-to-left page (the next option is to the left, as in the 3D arc): ← and ↓ the next, → and ↑
 * the previous, Home the first, End the last, Page Down / Page Up three at a time. Null: not the wheel's key.
 */
export function keyStep(key: string, index: number, n: number): number | null {
  const clamp = (i: number) => Math.max(0, Math.min(n - 1, i));
  switch (key) {
    case 'ArrowLeft':
    case 'ArrowDown':
      return clamp(index + 1);
    case 'ArrowRight':
    case 'ArrowUp':
      return clamp(index - 1);
    case 'Home':
      return 0;
    case 'End':
      return n - 1;
    case 'PageDown':
      return clamp(index + 3);
    case 'PageUp':
      return clamp(index - 3);
    default:
      return null;
  }
}

/**
 * The cards worth drawing: the one the wheel rests on and `reach` on each side (a phone shows about three). A card
 * outside them keeps its place and its name, without its picture, until the visitor comes near it: a wheel of ten loads
 * the pictures it shows, not ten.
 */
export function inReach(index: number, n: number, reach = 2): Set<number> {
  const out = new Set<number>();
  for (let i = Math.max(0, index - reach); i <= Math.min(n - 1, index + reach); i++) out.add(i);
  return out;
}

/**
 * The patch loader: the option the wheel rests on is the only one asked for. A rest that comes while a patch is still
 * loading waits for it and then asks for the newest rest only (the ones passed on the way are never asked for); a rest
 * on the option already loaded asks for nothing. `load` is the tour's swap (it fetches the patch, then changes the
 * product in the room); in the fixture it records what was asked.
 */
export class RestLoader {
  private wanted: number | null = null;
  private busy = false;
  constructor(
    private readonly load: (pos: number) => Promise<void>,
    private current: number,
  ) {}
  /** the wheel came to rest on option `pos` (1-based) */
  rest(pos: number): Promise<void> {
    this.wanted = pos;
    return this.run();
  }
  get shown(): number {
    return this.current;
  }
  private async run(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    try {
      while (this.wanted !== null && this.wanted !== this.current) {
        const to = this.wanted;
        await this.load(to);
        this.current = to;
      }
    } finally {
      this.wanted = null;
      this.busy = false;
    }
  }
}
