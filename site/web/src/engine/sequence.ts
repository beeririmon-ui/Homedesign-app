/**
 * Room-to-room transitions: a frame sequence drawn on a canvas. Cover-fitted like the room frame; the picture's scale
 * is 1.000 throughout (Design Bible "תנועה: אסור", gates G3.18 / G5.8: no push, no zoom without a dolly).
 *
 * Memory and decoding (gates G3.18, G6.9): preloading fetches only the compressed frames (~50 KB each); decoding happens
 * in a window of WINDOW frames around the playhead, in the direction of travel. Before a transition plays the first
 * window is decoded (prime), so the first frames never wait on a decode; frames left behind are released.
 *
 * The player is driven by a fractional frame position, so the caller owns the timing (speed ramp, hand-off):
 *   - between two source frames it blends them (30 fps footage stays smooth at 60 Hz and above);
 *   - with `trail` it leaves part of the previous screen frame in place: a cheap motion blur that grows with speed;
 *   - a frame whose decode has not landed yet is drawn as the nearest decoded one, never a stall or a blank.
 */
import { type Loader, type Decoded, decodeBlob, release } from './loader';
import { mediaUrl } from '../media';
import type { Scene } from './types';
import { timeScale } from '../motion';

type Transition = Scene['transitions'][string];

/** decoded frames kept ahead of the playhead (the plan's proposal: up to 30) */
export const WINDOW = 24;
/** decoded frames kept behind the playhead (frame blending and a short rewind) */
const BEHIND = 3;

export function frameUrls(t: Transition): string[] {
  return Array.from({ length: t.frames }, (_, i) => mediaUrl(`${t.src}/${String(i + 1).padStart(3, '0')}`, undefined, 'webp'));
}

/** Preload (fetch, not decode) only transitions reachable from the current room (skeleton-spec, performance). */
export function preloadTransition(loader: Loader, t: Transition, priority = 2): Promise<Blob[]> {
  return Promise.all(frameUrls(t).map((u) => loader.fetch(u, priority)));
}

/** The frames of one transition: compressed bytes for all, decoded drawables in a moving window. */
export class FrameWindow {
  private decoded: (Decoded | undefined)[];
  private pending: (Promise<void> | undefined)[];
  private generation = 0;

  constructor(private blobs: Blob[]) {
    this.decoded = new Array<Decoded | undefined>(blobs.length).fill(undefined);
    this.pending = new Array<Promise<void> | undefined>(blobs.length).fill(undefined);
  }

  get length(): number {
    return this.blobs.length;
  }

  private decode(i: number): Promise<void> {
    const have = this.pending[i];
    if (have) return have;
    const gen = this.generation;
    const p = decodeBlob(this.blobs[i]!).then((d) => {
      if (gen === this.generation) this.decoded[i] = d;
      else release(d);
    });
    this.pending[i] = p;
    return p;
  }

  /** Decodes the window around `pos` in the direction of travel (dir +1 forward, −1 backward); releases what is behind. */
  ensure(pos: number, dir: 1 | -1 = 1): void {
    const i = Math.round(pos);
    const lo = dir > 0 ? i - BEHIND : i - WINDOW;
    const hi = dir > 0 ? i + WINDOW : i + BEHIND;
    for (let k = 0; k < this.blobs.length; k++) {
      if (k >= lo && k <= hi) {
        if (!this.decoded[k] && !this.pending[k]) void this.decode(k).catch(() => undefined);
      } else if (this.decoded[k] || this.pending[k]) {
        release(this.decoded[k]);
        this.decoded[k] = undefined;
        this.pending[k] = undefined;
      }
    }
  }

  /** Resolves when the window around `pos` is decoded: called before a transition plays (pre-decode). */
  async prime(pos: number, dir: 1 | -1 = 1): Promise<void> {
    this.ensure(pos, dir);
    const i = Math.round(pos);
    const lo = dir > 0 ? i - BEHIND : i - WINDOW;
    const hi = dir > 0 ? i + WINDOW : i + BEHIND;
    const waits: Promise<void>[] = [];
    for (let k = Math.max(0, lo); k <= Math.min(this.blobs.length - 1, hi); k++) waits.push(this.decode(k).catch(() => undefined));
    await Promise.all(waits);
  }

  /** The frame, or the nearest decoded one at or before it, or any decoded one. */
  get(i: number): Decoded | undefined {
    const k = Math.min(this.blobs.length - 1, Math.max(0, i));
    if (this.decoded[k]) return this.decoded[k];
    for (let d = 1; d < this.blobs.length; d++) {
      if (this.decoded[k - d]) return this.decoded[k - d];
      if (this.decoded[k + d]) return this.decoded[k + d];
    }
    return undefined;
  }

  /** Releases every decoded frame (the transition ended). The compressed bytes stay cached by the loader. */
  close(): void {
    this.generation++;
    for (let k = 0; k < this.decoded.length; k++) {
      release(this.decoded[k]);
      this.decoded[k] = undefined;
      this.pending[k] = undefined;
    }
  }
}

export class SequencePlayer {
  private ctx: CanvasRenderingContext2D | null;
  private x = 0;
  private y = 0;
  private w = 0;
  private h = 0;
  private fitted = false;

  constructor(
    private canvas: HTMLCanvasElement,
    private frames: FrameWindow,
    private centerU = 0.5,
  ) {
    this.ctx = canvas.getContext('2d', { alpha: false });
    const dpr = Math.min(2, devicePixelRatio || 1);
    canvas.width = Math.max(1, Math.round(canvas.clientWidth * dpr));
    canvas.height = Math.max(1, Math.round(canvas.clientHeight * dpr));
  }

  get length(): number {
    return this.frames.length;
  }

  /** Decodes the first window (forward from `pos`, or backward) before playback starts. */
  prime(pos: number, dir: 1 | -1 = 1): Promise<void> {
    return this.frames.prime(pos, dir);
  }

  close(): void {
    this.frames.close();
  }

  private fit(first: Decoded): void {
    const s = Math.max(this.canvas.width / first.width, this.canvas.height / first.height);
    this.w = first.width * s;
    this.h = first.height * s;
    this.x = Math.min(0, Math.max(this.canvas.width - this.w, this.canvas.width / 2 - this.centerU * this.w));
    this.y = (this.canvas.height - this.h) / 2;
    this.fitted = true;
  }

  /** Draws the sequence at a fractional frame position, keeping the decode window ahead. trail 0..1 (motion blur). */
  draw(pos: number, opts: { trail?: number; dir?: 1 | -1 } = {}): void {
    const ctx = this.ctx;
    if (!ctx || !this.frames.length) return;
    const p = Math.min(this.frames.length - 1, Math.max(0, pos));
    this.frames.ensure(p, opts.dir ?? 1);
    const i = Math.floor(p);
    const f = p - i;
    const a = this.frames.get(i);
    if (!a) return;
    if (!this.fitted) this.fit(a);
    // with a trail, the new picture covers the old one only partly: the previous screen frame shows through
    const keep = Math.min(0.6, Math.max(0, opts.trail ?? 0));
    ctx.globalAlpha = 1 - keep;
    ctx.drawImage(a, this.x, this.y, this.w, this.h);
    if (f > 0.02 && i + 1 < this.frames.length) {
      const b = this.frames.get(i + 1);
      if (b && b !== a) {
        ctx.globalAlpha = f * (1 - keep);
        ctx.drawImage(b, this.x, this.y, this.w, this.h);
      }
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
