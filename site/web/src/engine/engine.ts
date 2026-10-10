/**
 * RoomEngine v0: composes a room from its layers (data/slots order), shows it with a camera,
 * cross-fades variant changes (0.3 s) and style changes (~1 s), and zooms with depth parallax (0.8-1.2 s).
 * Renders on demand only: no animation, no frames.
 */
import type { CatalogRoom } from '@hd/shared';
import type { Cam, LayerSpec, Scene, Viewport, Box } from './types';
import type { Compositor, DrawLayer } from './compositor';
import { GLCompositor } from './gl';
import { Canvas2DCompositor } from './canvas2d';
import { Loader } from './loader';
import { buildLayers, slotSources } from './layers';
import { camForBox, clampCam, coverSize, defaultCam, easeInOutCubic, easeOutCubic, lerpCam } from './camera';
import { mediaUrl, supportsAvif } from '../media';
import { timeScale } from '../motion';

type Anim = { start: number; dur: number; step: (t: number) => void; done?: () => void };

export type EngineOptions = {
  canvas: HTMLCanvasElement;
  scene: Scene;
  room: CatalogRoom;
  selection: Record<string, number>;
  reduceMotion: boolean;
  poster?: HTMLImageElement | null;
  forceCanvas2d?: boolean;
  onCamera?: (cam: Cam, vp: Viewport) => void;
  onReady?: () => void;
  onFrame?: (dtMs: number) => void;
};

export class RoomEngine {
  readonly loader = new Loader(6);
  cam: Cam = { cu: 0.5, cv: 0.5, z: 1 };
  vp: Viewport = { w: 1, h: 1 };
  ready = false;
  private comp: Compositor;
  private selection: Record<string, number>;
  private restCam: Cam | null = null;
  private userPanned = false;
  private mix = 1;
  private parallax = 0;
  private focus = 0.3;
  private drift: [number, number] = [0, 0];
  private blur = 0;
  private ext: 'avif' | 'webp' = 'webp';
  private res: 'lo' | 'hi' = 'lo';
  private compWidth = 1920;
  private shellUrl = '';
  private anims = new Set<Anim>();
  private raf = 0;
  private lastFrame = 0;
  private ro: ResizeObserver | null = null;
  private destroyed = false;
  private uploaded = new Set<string>();

  constructor(private o: EngineOptions) {
    this.selection = { ...o.selection };
    this.comp = (!o.forceCanvas2d && GLCompositor.create(o.canvas)) || new Canvas2DCompositor(o.canvas);
    o.canvas.addEventListener('webglcontextlost', this.onLost, false);
    o.canvas.addEventListener('webglcontextrestored', this.onRestored, false);
  }

  get kind(): Compositor['kind'] {
    return this.comp.kind;
  }

  get aspect(): number {
    return this.o.scene.aspect;
  }

  private layerUrl(l: LayerSpec): string {
    if (l.kind === 'base') return this.shellUrl || mediaUrl(l.src, this.compWidth, this.ext);
    // product, shadow and light layers are WebP only: lossless alpha (lossy AVIF alpha rings into a stain)
    return mediaUrl(l.src, this.o.scene.widths[this.res], 'webp');
  }

  private srcUrl(src: string): string {
    const base = this.o.scene.base.find((b) => b.src === src);
    return base ? this.shellUrl || mediaUrl(src, this.compWidth, this.ext) : mediaUrl(src, this.o.scene.widths[this.res], 'webp');
  }

  async start(): Promise<void> {
    this.ext = this.o.scene.formats.includes('avif') && (await supportsAvif()) ? 'avif' : 'webp';
    this.measure();
    const shell = this.o.scene.base[0]!;
    const poster = this.o.poster;
    if (poster && poster.currentSrc) {
      this.shellUrl = poster.currentSrc;
      const m = /\.(\d{3,4})\.(avif|webp)$/.exec(poster.currentSrc);
      this.compWidth = m ? Number(m[1]) : 1920;
      void this.loader.adopt(poster.currentSrc, poster);
    } else {
      const need = this.vp.w * Math.min(2, devicePixelRatio || 1) * (coverSize(this.vp, this.aspect).fw / this.vp.w);
      this.compWidth = shell.widths.find((w) => w >= need) ?? shell.widths[shell.widths.length - 1]!;
    }
    // phones: compose at the lo width (half the pixels to blend; the shell texture stays the poster's)
    if (this.vp.w <= 900) this.compWidth = Math.min(this.compWidth, this.o.scene.widths.lo);
    this.res = this.compWidth > this.o.scene.widths.lo ? 'hi' : 'lo';

    const layers = buildLayers(this.o.room, this.o.scene, this.selection);
    // the depth map (a few KB) comes with the first composition: the arrival dolly needs it from its first frame
    const depth = this.loader.load(mediaUrl(this.o.scene.depth.src, undefined, 'webp'), 0).then((d) => !this.destroyed && this.comp.setDepth(d));
    await Promise.all([...layers.map((l) => this.ensure(l.key, this.layerUrl(l), 0)), depth.catch(() => undefined)]);
    if (this.destroyed) return;
    this.comp.compose(this.draw(layers), this.compWidth);
    this.mix = 1;
    this.ready = true;
    this.requestRender();
    this.o.onReady?.();

    // after the room is shown: every other variant in the background
    for (const slot of this.o.room.slots)
      for (const src of slotSources(this.o.scene, slot.id)) void this.ensure(src, this.srcUrl(src), 1).catch(() => undefined);
  }

  private async ensure(key: string, url: string, priority: number): Promise<void> {
    if (this.uploaded.has(key)) return;
    const img = await this.loader.load(url, priority);
    if (this.destroyed || this.uploaded.has(key)) return;
    this.comp.upload(key, img);
    this.uploaded.add(key);
  }

  private draw(layers: LayerSpec[]): DrawLayer[] {
    return layers.map((l) => ({ key: l.key, rect: l.rect, blend: l.blend, opacity: 1 }));
  }

  // ---------- selection & style ----------
  async setSelection(slotId: string, position: number, durationMs = 300): Promise<void> {
    if (this.selection[slotId] === position) return;
    this.selection = { ...this.selection, [slotId]: position };
    await this.recompose(durationMs);
  }

  getSelection(): Record<string, number> {
    return { ...this.selection };
  }

  /** Same-frame cross-fade of all layers (style switch, ~1 s). */
  async crossfadeAll(durationMs = 1000): Promise<void> {
    await this.recompose(durationMs);
  }

  private async recompose(durationMs: number): Promise<void> {
    const layers = buildLayers(this.o.room, this.o.scene, this.selection);
    await Promise.all(layers.map((l) => this.ensure(l.key, this.layerUrl(l), 0)));
    if (this.destroyed) return;
    this.comp.swap();
    this.comp.compose(this.draw(layers), this.compWidth);
    const dur = this.o.reduceMotion ? 0 : durationMs;
    this.mix = dur ? 0 : 1;
    await this.animate(dur, (t) => (this.mix = t));
  }

  // ---------- camera ----------
  zoomToBox(box: Box, depth: number, opts: { durationMs?: number; reserve?: number } = {}): Promise<void> {
    const from = { ...this.cam };
    const to = camForBox(box, this.vp, this.aspect, opts.reserve ?? 0);
    this.focus = depth;
    return this.moveCam(from, to, opts.durationMs ?? 1000);
  }

  zoomOut(durationMs = 1000): Promise<void> {
    return this.moveCam({ ...this.cam }, this.restCam ?? defaultCam(this.vp, this.aspect, this.o.scene.mobile_center_u), durationMs);
  }

  private moveCam(from: Cam, to: Cam, durationMs: number): Promise<void> {
    const dur = this.o.reduceMotion ? 0 : durationMs;
    const zoomingIn = to.z > from.z;
    return this.animate(
      dur,
      (t) => {
        const e = easeInOutCubic(t);
        this.cam = lerpCam(from, to, e);
        // dolly parallax: near objects travel faster than far ones while the camera moves, none at rest
        this.parallax = (zoomingIn ? 1 : -1) * 0.075 * Math.sin(Math.PI * e);
        this.o.onCamera?.(this.cam, this.vp);
      },
      () => {
        this.parallax = 0;
        this.cam = to;
        this.o.onCamera?.(this.cam, this.vp);
      },
    );
  }

  /**
   * Arrival from a room-to-room transition: a dolly, not a zoom. The camera is still travelling forward when the
   * transition hands over, so near things (floor, armchair, pouf) start smaller and grow into place faster than the
   * back wall, the view slides slightly sideways, and a radial motion blur follows the speed. Everything decelerates
   * (ease-out) and lands exactly on the rest camera: the last frame IS the composed room, nothing jumps.
   * `reverse` plays the same move backwards (leaving the room): accelerating away, for the overlay to take over.
   */
  arrive(durationMs = 1100, opts: { reverse?: boolean } = {}): Promise<void> {
    const rest = this.restCam ?? defaultCam(this.vp, this.aspect, this.o.scene.mobile_center_u);
    const dur = this.o.reduceMotion || this.comp.kind !== 'webgl2' ? 0 : durationMs;
    const reverse = opts.reverse === true;
    const focus = 0.1; // the back wall barely moves; nearer planes travel more
    const apply = (t: number) => {
      const k = reverse ? 1 - t : t; // position along the arrival (1 = landed)
      const left = 1 - easeOutCubic(k); // distance still to travel
      const speed = (1 - k) * (1 - k); // derivative of the ease-out, normalised
      this.focus = focus;
      this.parallax = -0.11 * left;
      this.drift = [-0.012 * left, 0.004 * left];
      this.blur = 0.045 * speed;
      this.cam = { ...rest, z: rest.z * (1 - 0.035 * left) };
    };
    return this.animate(dur, apply, () => {
      if (reverse) return; // the transition overlay covers the room from here on
      this.parallax = 0;
      this.drift = [0, 0];
      this.blur = 0;
      this.cam = rest;
      this.o.onCamera?.(this.cam, this.vp);
    });
  }

  panBy(dxCss: number): void {
    const { fw } = coverSize(this.vp, this.aspect);
    this.cam = clampCam({ ...this.cam, cu: this.cam.cu - dxCss / (fw * this.cam.z) }, this.vp, this.aspect);
    if (this.cam.z === 1) {
      this.restCam = { ...this.cam };
      this.userPanned = true;
    }
    this.o.onCamera?.(this.cam, this.vp);
    this.requestRender();
  }

  /** Ambient depth drift from the pointer (desktop) — off when zoomed or with reduced motion. */
  setDrift(nx: number, ny: number): void {
    if (this.o.reduceMotion || this.cam.z > 1.01 || this.anims.size) return;
    this.drift = [nx * 0.006, ny * 0.004];
    this.requestRender();
  }

  frameToScreen(u: number, v: number): { x: number; y: number } {
    const { fw, fh } = coverSize(this.vp, this.aspect);
    return { x: this.vp.w / 2 + (u - this.cam.cu) * fw * this.cam.z, y: this.vp.h / 2 + (v - this.cam.cv) * fh * this.cam.z };
  }

  // ---------- loop ----------
  private animate(durationMs: number, step: (t: number) => void, done?: () => void): Promise<void> {
    durationMs *= timeScale();
    return new Promise((resolve) => {
      if (durationMs <= 0) {
        step(1);
        done?.();
        this.requestRender();
        resolve();
        return;
      }
      this.anims.add({
        start: performance.now(),
        dur: durationMs,
        step,
        done: () => {
          done?.();
          resolve();
        },
      });
      this.requestRender();
    });
  }

  requestRender(): void {
    if (this.raf || this.destroyed) return;
    this.raf = requestAnimationFrame(this.frame);
  }

  private frame = (now: number): void => {
    this.raf = 0;
    if (this.lastFrame && this.anims.size) this.o.onFrame?.(now - this.lastFrame);
    this.lastFrame = this.anims.size ? now : 0;
    for (const a of [...this.anims]) {
      const t = Math.min(1, (now - a.start) / a.dur);
      a.step(t);
      if (t >= 1) {
        this.anims.delete(a);
        a.done?.();
      }
    }
    if (this.ready)
      this.comp.display({
        cam: this.cam,
        vp: this.vp,
        aspect: this.aspect,
        mix: this.mix,
        parallax: this.parallax,
        focus: this.focus,
        drift: this.drift,
        blur: this.blur,
      });
    if (this.anims.size) this.requestRender();
  };

  // ---------- size ----------
  private measure(): void {
    const el = this.o.canvas;
    const w = Math.max(1, el.clientWidth);
    const h = Math.max(1, el.clientHeight);
    this.vp = { w, h };
    this.comp.resize(w, h, Math.min(2, devicePixelRatio || 1));
    this.cam = this.userPanned && this.restCam ? clampCam(this.cam, this.vp, this.aspect) : defaultCam(this.vp, this.aspect, this.o.scene.mobile_center_u);
    if (!this.userPanned) this.restCam = { ...this.cam };
  }

  observe(): void {
    this.ro = new ResizeObserver(() => {
      if (this.cam.z > 1.01) return; // keep the zoom; re-measure on zoom out
      this.measure();
      this.o.onCamera?.(this.cam, this.vp);
      this.requestRender();
    });
    this.ro.observe(this.o.canvas);
  }

  // ---------- context loss ----------
  private onLost = (e: Event): void => {
    e.preventDefault();
    this.ready = false;
  };

  private onRestored = (): void => {
    const gl = GLCompositor.create(this.o.canvas);
    if (!gl) return;
    this.comp = gl;
    this.uploaded.clear();
    this.measure();
    void (async () => {
      const layers = buildLayers(this.o.room, this.o.scene, this.selection);
      await Promise.all(layers.map((l) => this.ensure(l.key, this.layerUrl(l), 0)));
      void this.loader.load(mediaUrl(this.o.scene.depth.src, undefined, 'webp'), 0).then((d) => this.comp.setDepth(d));
      this.comp.compose(this.draw(layers), this.compWidth);
      this.ready = true;
      this.requestRender();
    })();
  };

  destroy(): void {
    this.destroyed = true;
    cancelAnimationFrame(this.raf);
    this.ro?.disconnect();
    this.o.canvas.removeEventListener('webglcontextlost', this.onLost);
    this.o.canvas.removeEventListener('webglcontextrestored', this.onRestored);
    this.comp.destroy();
  }
}
