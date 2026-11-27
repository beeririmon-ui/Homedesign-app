/**
 * MOCK9 (2026-11-27, briefs/site-mock9-route-ui-2026-11-27.md; FB21): the guided route. The owner's order of the
 * stations (living → kitchen D1 → bath B1 → bedroom MB0 → boy → girl → work), and the legs between them as
 * tools/make-route.ts wrote them: a real leg is a clip (a video over the canvas); a leg without one fades through the warm
 * light (MOCK11, FB26: no longer the MOCK7 push) behind the same interface, so a real leg drops in with one line of tools/tour/route.json.
 *
 * The rules a trip follows (FB21):
 *  - one station ahead plays its leg at the leg's own pace ("הלאה", or the scroll that scrubs it like the arrival);
 *  - two or more stations ahead play the legs chained, ×2 for two, ×2.5 for three, ×3 from four, and skip the ease
 *    frames between legs (the ease-in of every leg but the first, the ease-out of every leg but the last: the
 *    manifest's `fast_forward` rule);
 *  - back is never a video played backward (FB8): a soft fade through the light, about 450 ms.
 * No import but the generated data: the unit tests read it on its own.
 */
import data from '@generated/route.json';
import type { GroupId } from './data';

/** a real leg's file for one screen; `poster` is its first frame (MOCK10: what a web view shows before a frame) */
export type LegVideo = {
  src: string;
  poster: string;
  w: number;
  h: number;
  fps: number;
  frames: number;
  bytes: number;
  ease_in: [number, number];
  ease_out: [number, number];
};
export type Leg = { id: string; from: GroupId; to: GroupId; real: Record<'desktop' | 'phone', LegVideo> | null; qa: string | null };
const R = data as unknown as { order: GroupId[]; legs: Leg[] };

/** the stations in the owner's order */
export const ROUTE: readonly GroupId[] = R.order;
/** the legs, `LEGS[i]` from `ROUTE[i]` to `ROUTE[i + 1]` */
export const LEGS: readonly Leg[] = R.legs;
export const stationOf = (g: GroupId): number => ROUTE.indexOf(g);
export const nextOf = (g: GroupId): GroupId | null => ROUTE[stationOf(g) + 1] ?? null;
/** the fade through the light, back to a station behind (ms) */
export const BACK_MS = 450;
/** the soft blend at a leg's ends: the visitor's composition to the leg's first frame, its last frame to the room (ms;
 *  the manifest's `swap`: 160–200) */
export const LEG_BLEND_MS = 180;
/** a jump's pace: one station the leg's own, two ×2, three ×2.5, four and more ×3 */
export const rateFor = (stations: number): number => (stations <= 1 ? 1 : Math.min(3, 1 + stations / 2));

export type Hop = { leg: Leg; skipIn: boolean; skipOut: boolean };
export type Trip = { kind: 'stay' } | { kind: 'back'; to: GroupId; ms: number } | { kind: 'ahead'; to: GroupId; stations: number; rate: number; hops: Hop[] };

/** what going from station `from` to station `to` plays */
export function trip(from: GroupId, to: GroupId): Trip {
  const a = stationOf(from);
  const b = stationOf(to);
  if (a < 0 || b < 0 || a === b) return { kind: 'stay' };
  if (b < a) return { kind: 'back', to, ms: BACK_MS };
  const legs = LEGS.slice(a, b);
  const n = legs.length;
  return {
    kind: 'ahead',
    to,
    stations: n,
    rate: rateFor(n),
    hops: legs.map((leg, i) => ({ leg, skipIn: i > 0, skipOut: i < n - 1 })),
  };
}

/**
 * The stretch of a real leg's file a hop plays (s): the whole leg, or without the ease frames a chain skips. Frame i
 * (1-based) is on screen from (i − 1) / fps; the stretch ends on its last frame's time.
 */
export function span(v: LegVideo, hop: Pick<Hop, 'skipIn' | 'skipOut'>): { start: number; end: number } {
  const first = hop.skipIn ? v.ease_in[1] + 1 : 1;
  const last = hop.skipOut ? v.ease_out[0] - 1 : v.frames;
  return { start: (first - 1) / v.fps, end: (last - 1) / v.fps };
}

/** a leg's file for this screen: a phone (900 CSS px or less, the room engine's own rule) takes the 30 fps one */
export const legFile = (leg: Leg, cssWidth: number): LegVideo | null => (leg.real ? (cssWidth <= 900 ? leg.real.phone : leg.real.desktop) : null);
