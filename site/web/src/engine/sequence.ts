/**
 * Room-to-room transitions: a frame sequence drawn on a canvas. Frames are decoded ahead (createImageBitmap
 * in the loader) so playback is a cheap drawImage per frame. Cover-fitted like the room frame.
 *
 * The player is driven by a fractional frame position, so the caller owns the timing (speed ramp, hand-off):
 *   - between two source frames it blends them (30 fps footage stays smooth at 60 Hz and above);
 *   - with `trail` it leaves part of the previous screen frame in place: a cheap motion blur that grows with speed;
 *   - with `push` it keeps scaling the picture about the centre of travel, so the motion does not stall on the
 *     last frames while the room takes over.
 */
import { type Loader, type Decoded } from './loader';
import { mediaUrl } from '../media';
import type { Scene } from './types';
import { timeScale } from '../motion';

type Transition = Scene['transitions'][string];

export function frameUrls(t: Transition): string[] {
  return Array.from({ length: t.frames }, (_, i) => mediaUrl(`${t.src}/${String(i + 1).padStart(3, '0')}`, undefined, 'webp'));
}

/** Preload only transitions reachable from the current room (skeleton-spec, performance). */
export function preloadTransition(loader: Loader, t: Transition, priority = 2): Promise<Decoded[]> {
  return Promise.all(frameUrls(t).map((u) => loader.load(u, priority)));
}

export class SequencePlayer {
  private ctx: CanvasRenderingContext2D | null;
  private x = 0;
  private y = 0;
  private w = 0;
  private h = 0;

  constructor(
    private canvas: HTMLCanvasElement,
    private frames: Decoded[],
    centerU = 0.5,
  ) {
    this.ctx = canvas.getContext('2d', { alpha: false });
    const dpr = Math.min(2, devicePixelRatio || 1);
    canvas.width = Math.max(1, Math.round(canvas.clientWidth * dpr));
    canvas.height = Math.max(1, Math.round(canvas.clientHeight * dpr));
    const first = frames[0];
    if (!first) return;
    const s = Math.max(canvas.width / first.width, canvas.height / first.height);
    this.w = first.width * s;
    this.h = first.height * s;
    this.x = Math.min(0, Math.max(canvas.width - this.w, canvas.width / 2 - centerU * this.w));
    this.y = (canvas.height - this.h) / 2;
  }

  get length(): number {
    return this.frames.length;
  }

  /** Draws the sequence at a fractional frame position. trail 0..1 (motion blur), push ≥ 1 (extra forward scale). */
  draw(pos: number, opts: { trail?: number; push?: number } = {}): void {
    const ctx = this.ctx;
    if (!ctx || !this.frames.length) return;
    const p = Math.min(this.frames.length - 1, Math.max(0, pos));
    const i = Math.floor(p);
    const f = p - i;
    const push = opts.push ?? 1;
    const cx = this.canvas.width / 2;
    const cy = this.canvas.height / 2;
    const w = this.w * push;
    const h = this.h * push;
    const x = cx + (this.x - cx) * push;
    const y = cy + (this.y - cy) * push;
    // with a trail, the new picture covers the old one only partly: the previous screen frame shows through
    const keep = Math.min(0.6, Math.max(0, opts.trail ?? 0));
    ctx.globalAlpha = 1 - keep;
    ctx.drawImage(this.frames[i]!, x, y, w, h);
    if (f > 0.02 && i + 1 < this.frames.length) {
      ctx.globalAlpha = f * (1 - keep);
      ctx.drawImage(this.frames[i + 1]!, x, y, w, h);
    }
    ctx.globalAlpha = 1;
  }
}

/** rAF loop for `durationMs`, calling step(t) with t from 0 to 1. */
export function tween(durationMs: number, step: (t: number, dtMs: number) => void): Promise<void> {
  durationMs *= timeScale();
  return new Promise((resolve) => {
    if (durationMs <= 0) {
      step(1, 0);
      resolve();
      return;
    }
    const t0 = performance.now();
    let last = t0;
    const frame = (now: number) => {
      const t = Math.min(1, (now - t0) / durationMs);
      step(t, now - last);
      last = now;
      if (t < 1) requestAnimationFrame(frame);
      else resolve();
    };
    requestAnimationFrame(frame);
  });
}
