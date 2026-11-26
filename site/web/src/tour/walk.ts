/**
 * MOCK8 (2026-11-26, briefs/site-mock8-integrate-2026-11-26.md; FB19): the arrival's walk advances by gentle scroll
 * impulses with inertia. A small push plays a stretch of the walk and eases to a stop; two or three small pushes reach
 * the living room. Forward only (FB8): nothing here ever plays the walk backward.
 *
 * The model is the walk's playhead (seconds of the walk) and its rate (the video's playbackRate): every impulse moves
 * the target on by a share of the walk; the rate rises to a walking pace (never a jump) and falls at a constant
 * deceleration so the walk stops on the target. A target within `snap` impulses of the end is the end itself: the last
 * push walks through, and at the end the walk keeps a walking pace (the walk's own frames ease onto the room's, or the
 * tour walks on from them), it does not stop on its last frame. No import: the unit tests read it on its own.
 */
export type WalkParams = {
  /** the walk's length (s) */
  duration: number;
  /** the share of the walk one impulse plays */
  impulse: number;
  /** a target within this many impulses of the end is the end */
  snap: number;
};
/** the walking pace's ceiling, its rise and its fall (rate units: 1 = the walk's own speed) */
export const WALK = { max: 1.25, acc: 3.2, dec: 1.15, end: 0.95, rest: 0.06, min: 0.0625 } as const;
/** a gesture: wheel events closer than this (ms) are one push; its first event plays 0.8 of an impulse, the rest of it
 *  adds by how far it scrolled, up to 1.3 impulses in all */
export const GESTURE = { gap: 220, first: 0.8, perPx: 1 / 600, cap: 1.3, swipePx: 24 } as const;

export class WalkPlay {
  /** where the walk is going (s) */
  target = 0;
  /** the rate it plays at now (0: resting) */
  rate = 0;
  pushes = 0;
  constructor(readonly p: WalkParams) {}
  /** one push of `k` impulses from where the walk is (`t`, s); returns the new target */
  push(t: number, k = 1): number {
    const { duration: d, impulse, snap } = this.p;
    const from = Math.max(this.target, t);
    let to = Math.min(d, from + impulse * d * k);
    if (d - to <= snap * impulse * d) to = d;
    this.target = to;
    this.pushes++;
    return to;
  }
  /** the end is the target: the walk keeps walking into what comes after it */
  get through(): boolean {
    return this.target >= this.p.duration - 1e-6;
  }
  /** the rate for the next `dt` seconds, at playhead `t` (s); 0: rest */
  step(t: number, dt: number): number {
    const dist = this.target - t;
    let want = dist > 0.004 ? Math.min(WALK.max, Math.sqrt(2 * WALK.dec * dist)) : 0;
    if (this.through) want = Math.max(want, WALK.end);
    const d = want - this.rate;
    this.rate += Math.max(-WALK.dec * 2 * dt, Math.min(WALK.acc * dt, d));
    if (want < WALK.rest && this.rate < WALK.rest) this.rate = 0;
    return this.rate;
  }
  get resting(): boolean {
    return this.rate === 0;
  }
}

/** a gesture's pushes: wheel events of one gesture add up, a new gesture starts a new push */
export class Gesture {
  private last = -1e9;
  private sum = 0;
  /** the impulses an event of `px` pixels at `now` (ms) adds (0: nothing), and whether it starts a new push */
  wheel(px: number, now: number): { k: number; fresh: boolean } {
    if (px <= 0) return { k: 0, fresh: false };
    const fresh = now - this.last > GESTURE.gap;
    this.last = now;
    if (fresh) {
      this.sum = GESTURE.first;
      return { k: GESTURE.first, fresh };
    }
    const add = Math.max(0, Math.min(GESTURE.cap - this.sum, px * GESTURE.perPx));
    this.sum += add;
    return { k: add, fresh };
  }
}
