/**
 * Room-to-room transitions: a frame sequence drawn on a canvas. Frames are decoded ahead (createImageBitmap
 * in the loader) so playback is a cheap drawImage per frame. Cover-fitted like the room frame.
 */
import { type Loader, type Decoded } from './loader';
import { mediaUrl } from '../media';
import type { Scene } from './types';

type Transition = Scene['transitions'][string];

export function frameUrls(t: Transition): string[] {
  return Array.from({ length: t.frames }, (_, i) => mediaUrl(`${t.src}/${String(i + 1).padStart(3, '0')}`, undefined, 'webp'));
}

/** Preload only transitions reachable from the current room (skeleton-spec, performance). */
export function preloadTransition(loader: Loader, t: Transition, priority = 2): Promise<Decoded[]> {
  return Promise.all(frameUrls(t).map((u) => loader.load(u, priority)));
}

export async function playSequence(
  canvas: HTMLCanvasElement,
  frames: Decoded[],
  opts: { durationMs: number; reverse?: boolean; centerU?: number; onFrame?: (dt: number) => void },
): Promise<void> {
  const ctx = canvas.getContext('2d', { alpha: false });
  if (!ctx || !frames.length) return;
  const dpr = Math.min(2, devicePixelRatio || 1);
  canvas.width = Math.round(canvas.clientWidth * dpr);
  canvas.height = Math.round(canvas.clientHeight * dpr);
  const first = frames[0]!;
  const iw = first.width;
  const ih = first.height;
  const s = Math.max(canvas.width / iw, canvas.height / ih);
  const w = iw * s;
  const h = ih * s;
  const cu = opts.centerU ?? 0.5;
  const x = Math.min(0, Math.max(canvas.width - w, canvas.width / 2 - cu * w));
  const y = (canvas.height - h) / 2;
  const draw = (i: number) => ctx.drawImage(frames[i]!, x, y, w, h);
  return new Promise((resolve) => {
    const t0 = performance.now();
    let last = t0;
    const step = (now: number) => {
      opts.onFrame?.(now - last);
      last = now;
      const k = Math.min(1, (now - t0) / opts.durationMs);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      const i = Math.round((opts.reverse ? 1 - e : e) * (frames.length - 1));
      draw(i);
      if (k < 1) requestAnimationFrame(step);
      else resolve();
    };
    draw(opts.reverse ? frames.length - 1 : 0);
    requestAnimationFrame(step);
  });
}
