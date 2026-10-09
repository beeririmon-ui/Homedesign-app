/**
 * Drag, inertia and snap for the variant arc. `pos` is a continuous index (0 … n-1).
 * Pixel deltas are converted by `pxPerItem`; RTL is handled by the caller (sign of dx).
 */
export class ArcPhysics {
  pos = 0;
  vel = 0; // items per second
  target: number | null = null;
  private lastT = 0;

  constructor(
    public count: number,
    public pxPerItem = 220,
  ) {}

  setIndex(i: number): void {
    this.pos = this.clampIndex(i);
    this.vel = 0;
    this.target = null;
  }

  clampIndex(i: number): number {
    return Math.max(0, Math.min(this.count - 1, Math.round(i)));
  }

  /** Called on pointer move; returns the new pos. Rubber-band past the ends. */
  drag(dxItemsPositive: number, nowMs: number): number {
    const dItems = dxItemsPositive / this.pxPerItem;
    const over = this.pos < 0 ? -this.pos : this.pos > this.count - 1 ? this.pos - (this.count - 1) : 0;
    this.pos += dItems * (over > 0 ? 0.35 : 1);
    const dt = Math.max(1, nowMs - this.lastT) / 1000;
    this.vel = this.vel * 0.6 + (dItems / dt) * 0.4;
    this.lastT = nowMs;
    this.target = null;
    return this.pos;
  }

  startDrag(nowMs: number): void {
    this.vel = 0;
    this.lastT = nowMs;
    this.target = null;
  }

  /** On release: project with the velocity (inertia) and pick the item it would come to rest on. */
  release(): number {
    const projected = this.pos + this.vel * 0.22;
    this.target = this.clampIndex(projected);
    return this.target;
  }

  goTo(i: number): void {
    this.target = this.clampIndex(i);
  }

  /** Critically damped spring toward the target. Returns true while moving. */
  step(dtSec: number): boolean {
    if (this.target === null) return false;
    const k = 90;
    const c = 2 * Math.sqrt(k);
    const dt = Math.min(dtSec, 1 / 30);
    const a = -k * (this.pos - this.target) - c * this.vel;
    this.vel += a * dt;
    this.pos += this.vel * dt;
    if (Math.abs(this.pos - this.target) < 0.001 && Math.abs(this.vel) < 0.01) {
      this.pos = this.target;
      this.vel = 0;
      this.target = null;
      return false;
    }
    return true;
  }
}
