/**
 * Fallback compositor (no WebGL2, or a lost context). Canvas 2D supports the same blend modes
 * (multiply, screen) natively; zoom works, parallax does not.
 */
import type { Compositor, DisplayState, DrawLayer } from './compositor';
import type { Decoded } from './loader';
import { coverSize } from './camera';

function surface(w: number, h: number): HTMLCanvasElement {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

export class Canvas2DCompositor implements Compositor {
  readonly kind = 'canvas2d' as const;
  private ctx: CanvasRenderingContext2D;
  private images = new Map<string, Decoded>();
  private prev: HTMLCanvasElement | null = null;
  private next: HTMLCanvasElement | null = null;

  constructor(private canvas: HTMLCanvasElement) {
    this.ctx = canvas.getContext('2d', { alpha: false })!;
  }

  upload(key: string, img: Decoded): void {
    this.images.set(key, img);
  }
  has(key: string): boolean {
    return this.images.has(key);
  }
  setDepth(): void {
    /* no parallax in 2D */
  }

  compose(layers: DrawLayer[], width: number): void {
    const w = Math.min(width, 2752);
    const h = Math.round(w / (16 / 9));
    if (!this.next || this.next.width !== w) {
      this.prev = surface(w, h);
      this.next = surface(w, h);
    }
    const ctx = this.next.getContext('2d')!;
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#141312';
    ctx.fillRect(0, 0, w, h);
    for (const l of layers) {
      const img = this.images.get(l.key);
      if (!img) continue;
      ctx.globalCompositeOperation = l.blend === 'multiply' ? 'multiply' : l.blend === 'screen' ? 'screen' : 'source-over';
      ctx.globalAlpha = l.opacity;
      ctx.drawImage(img, l.rect[0] * w, l.rect[2] * h, (l.rect[1] - l.rect[0]) * w, (l.rect[3] - l.rect[2]) * h);
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
  }

  swap(): void {
    [this.prev, this.next] = [this.next, this.prev];
  }

  display(s: DisplayState): void {
    if (!this.next || !this.prev) return;
    const ctx = this.ctx;
    const dpr = this.canvas.width / Math.max(1, s.vp.w);
    const { fw, fh } = coverSize(s.vp, s.aspect);
    const scale = fw * s.cam.z * dpr;
    const x = (s.vp.w / 2 - s.cam.cu * fw * s.cam.z) * dpr;
    const y = (s.vp.h / 2 - s.cam.cv * fh * s.cam.z) * dpr;
    const draw = (src: HTMLCanvasElement, alpha: number) => {
      ctx.globalAlpha = alpha;
      ctx.drawImage(src, x, y, scale, (scale * fh) / fw);
    };
    ctx.imageSmoothingQuality = 'high';
    if (s.mix < 1) draw(this.prev, 1);
    if (s.mix > 0) draw(this.next, s.mix);
    ctx.globalAlpha = 1;
  }

  resize(cssW: number, cssH: number, dpr: number): void {
    this.canvas.width = Math.max(1, Math.round(cssW * dpr));
    this.canvas.height = Math.max(1, Math.round(cssH * dpr));
  }

  destroy(): void {
    for (const i of this.images.values()) if ('close' in i) i.close();
    this.images.clear();
  }
}
