/**
 * FB20 (2026-11-26, briefs/site-wheel-3d-2026-11-26.md): the 3D product wheel's rules, apart from the DOM so they are
 * tested on their own (web/test/wheel3d.test.ts).
 *
 *  - the ring: the options are round cards on a horizontal ring, seen from above at 30–45° (RING.tilt), its front arc
 *    nearest the viewer. A card faces the viewer (a circle stays a circle) and turns a little with the ring;
 *  - the depth: a card's place round the ring gives its `front` (1 in front, 0 at the back). Behind, a card recedes
 *    (the perspective), dims and blurs (a blurred copy of its picture fades in: opacity only, never a per-frame filter);
 *  - the ring closes on itself (3 to 12 options): the positions wrap, and a move always takes the short way round;
 *  - the physics: drag, inertia and a gentle snap to the nearest card (a critically damped spring, as ArcPhysics).
 */

export const RING = {
  /** the view from above, degrees (the owner's 30–45°) */
  tilt: 36,
  /** a short cell (a phone held upright): the flatter end of the owner's range */
  tiltShort: 32,
  /** how much a card turns with the ring (0: always square to the viewer; 1: it faces out from the ring's axis) */
  yaw: 0.35,
  /** the perspective, in ring radii */
  persp: 3.2,
  /** the chord between two neighbours, in card widths (a little air between the front three) */
  air: 1.06,
  /** the smallest ring, in card widths (three or four options: the back cards peek out beside the front one) */
  minRadius: 1.05,
  /** a card behind: the most it dims (the veil) and the least it shows */
  veil: 0.55,
  floor: 0.3,
} as const;

/** the room while the wheel is open: −1.1 EV, and darker still away from the product (the close-up's vignette) */
export const DIM = { ev: -1.1, vig: 0.35 } as const;
/** the selection moment: the dim lifts as the chosen option's layer cross-fades in (the brief's 600–900 ms) */
export const REVEAL_MS = 800;

export type RingGeom = {
  n: number;
  /** a card's width at the ring's middle depth (front cards are bigger by the perspective) */
  cw: number;
  /** the ring's radius and the perspective, px */
  r: number;
  p: number;
  /** degrees between two cards, and the view's tilt */
  step: number;
  tilt: number;
  /** the ring's centre in its cell, px (the perspective's origin) */
  cx: number;
  cy: number;
};

const rad = (d: number) => (d * Math.PI) / 180;

/** the projected scale and height of a point of the ring at angle `a` (degrees from the front), for a card of width 1 */
function at(a: number, k: number, tilt: number) {
  const r = k;
  const p = RING.persp * r;
  const z = r * Math.cos(rad(a)) * Math.cos(rad(tilt));
  const y = r * Math.cos(rad(a)) * Math.sin(rad(tilt));
  const x = r * Math.sin(rad(a));
  const s = p / (p - z);
  return { s, x: x * s, y: y * s };
}

/**
 * The ring for `n` options in a cell of `w` × `h` px: the card's width, the ring's radius and where its centre sits.
 * The whole ring (its back cards included, whatever turn it is at) fits the cell's height; across, the front three
 * cards fit, and the ring may reach past the sides, where its cards are already behind and faded.
 */
export function ringGeom(n: number, w: number, h: number, maxCw = 168): RingGeom {
  const count = Math.max(1, n);
  const step = 360 / count;
  const tilt = h < 230 ? RING.tiltShort : RING.tilt;
  const k = Math.max(RING.minRadius, RING.air / (2 * Math.sin(rad(step / 2))));
  // the height for a card of width 1: the back card's top to the front card's bottom
  const f = at(0, k, tilt);
  const b = at(180, k, tilt);
  const hk = f.y + f.s / 2 - (b.y - b.s / 2);
  // the width: the front card and its two neighbours (three options: the two behind it)
  const nb = at(Math.min(step, 180), k, tilt);
  const wk = Math.max(f.s, 2 * Math.abs(nb.x) + nb.s);
  const cw = Math.max(40, Math.min(maxCw, (h * 0.96) / hk, (w * 0.94) / wk));
  return { n: count, cw, r: k * cw, p: RING.persp * k * cw, step, tilt, cx: w / 2, cy: (h - hk * cw) / 2 + (-(b.y - b.s / 2)) * cw };
}

/** the short signed distance from `pos` to card `i` round a ring of `n` (−n/2 … n/2) */
export function ringDelta(i: number, pos: number, n: number): number {
  let d = (i - pos) % n;
  if (d > n / 2) d -= n;
  if (d < -n / 2) d += n;
  return d;
}
/** a whole position round the ring, as a card's index (0 … n−1) */
export const ringIndex = (pos: number, n: number): number => (((Math.round(pos) % n) + n) % n) as number;

export type CardPose = {
  transform: string;
  /** 1 in front … 0 at the back */
  front: number;
  /** the card's depth order (higher: nearer) */
  z: number;
  opacity: number;
  veil: number;
  /** the blurred copy's opacity (behind: the card goes soft) */
  soft: number;
  /** only the front half takes a tap */
  live: boolean;
};

/**
 * Card `i` when the ring is at `pos`. RTL: the next option sits to the left (an angle the other way round). The card
 * is placed on the ring (rotateY, translateZ), turned back towards the viewer but for RING.yaw of the ring's turn, and
 * tilted up by the view's tilt, so it faces the viewer square in the ring's tilted space.
 */
export function cardPose(i: number, pos: number, g: RingGeom): CardPose {
  const d = ringDelta(i, pos, g.n);
  const a = -d * g.step;
  const front = (1 + Math.cos(rad(a))) / 2;
  const k = Math.pow(front, 0.8);
  const back = 1 - front;
  return {
    transform: `rotateY(${a.toFixed(3)}deg) translateZ(${g.r.toFixed(1)}px) rotateY(${(-a * (1 - RING.yaw)).toFixed(3)}deg) rotateX(${g.tilt}deg)`,
    front,
    z: Math.round(front * 100),
    opacity: RING.floor + (1 - RING.floor) * k,
    veil: RING.veil * back,
    soft: Math.min(1, Math.max(0, (0.72 - front) / 0.45)),
    live: front > 0.55,
  };
}

/**
 * Drag, inertia and snap round a ring. `pos` is a continuous position (any real number: the ring wraps); the card in
 * front is ringIndex(pos). Pixel deltas are converted by `pxPerItem`; RTL is the caller's (the sign of dx).
 */
export class RingPhysics {
  pos = 0;
  vel = 0;
  target: number | null = null;
  private lastT = 0;
  constructor(
    public count: number,
    public pxPerItem = 160,
  ) {}
  get index(): number {
    return ringIndex(this.pos, this.count);
  }
  setIndex(i: number): void {
    this.pos = i;
    this.vel = 0;
    this.target = null;
  }
  startDrag(nowMs: number): void {
    this.vel = 0;
    this.lastT = nowMs;
    this.target = null;
  }
  drag(dx: number, nowMs: number): number {
    const d = dx / this.pxPerItem;
    this.pos += d;
    const dt = Math.max(1, nowMs - this.lastT) / 1000;
    this.vel = this.vel * 0.6 + (d / dt) * 0.4;
    this.lastT = nowMs;
    this.target = null;
    return this.pos;
  }
  /** on release: the velocity carries it on (at most a turn of the ring), and it snaps to the card it would rest on */
  release(): number {
    const carry = Math.max(-this.count, Math.min(this.count, this.vel * 0.24));
    this.target = Math.round(this.pos + carry);
    return ringIndex(this.target, this.count);
  }
  /** to card `i` the short way round */
  goTo(i: number): void {
    this.target = this.pos + ringDelta(i, this.pos, this.count);
    this.target = Math.round(this.target);
  }
  /** one step of the critically damped spring (as ArcPhysics: real time, small fixed sub-steps); true while moving */
  step(dtSec: number): boolean {
    if (this.target === null) return false;
    const k = 90;
    const c = 2 * Math.sqrt(k);
    for (let left = Math.min(Math.max(dtSec, 0), 0.25); left > 0; left -= 1 / 120) {
      const dt = Math.min(left, 1 / 120);
      const acc = -k * (this.pos - this.target) - c * this.vel;
      this.vel += acc * dt;
      this.pos += this.vel * dt;
    }
    if (Math.abs(this.pos - this.target) < 0.001 && Math.abs(this.vel) < 0.01) {
      // the position is kept small: the same card, the nearest turn to zero
      this.pos = ringIndex(this.target, this.count);
      this.vel = 0;
      this.target = null;
      return false;
    }
    return true;
  }
}
