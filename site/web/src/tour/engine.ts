/**
 * MOCK1: the tour's engine. It holds the room as a list of layers with a state each, composes what changed, and shows it
 * through the room engine's camera (engine/camera.ts). An effect (tour/fx.ts) is one `run`: a function of its own time
 * from 0 to 1 that poses layers and sets what the display adds; at 0 it is the frame before it and at 1 the frame after
 * it, which is what `seams` records and the tests hold it to.
 */
import type { Box, Cam, Viewport } from '../engine/types';
import { Loader } from '../engine/loader';
import { camForBox, clampCam, defaultCam, lerpCam } from '../engine/camera';
import { supportsAvif } from '../media';
import { timeScale } from '../motion';
import { FX, MASK_PER_M, TourGL, layer, restDisplay, type Display, type LayerDraw, type Px } from './gl';
import { metrics, type EffectStat } from './metrics';
import { NORDIC, WM, baseOf, layerUrl, nordicLayers, tour, widthFor, type Draw, type HouseId, type TourSlot } from './data';

/** cubic-bezier(x1, y1, x2, y2), as CSS: the designer's curves (section 7) */
export function bezier(x1: number, y1: number, x2: number, y2: number): (x: number) => number {
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;
  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) {
      const f = ((ax * t + bx) * t + cx) * t - x;
      const d = (3 * ax * t + 2 * bx) * t + cx;
      if (Math.abs(f) < 1e-6 || !d) break;
      t -= f / d;
    }
    return ((ay * t + by) * t + cy) * t;
  };
}
export const EASE = {
  /** the camera in code */
  camera: bezier(0.65, 0, 0.35, 1),
  /** something appears */
  out: bezier(0.16, 1, 0.3, 1),
  /** something leaves */
  in: bezier(0.7, 0, 0.84, 0),
};
export const clamp01 = (x: number): number => (x < 0 ? 0 : x > 1 ? 1 : x);

/**
 * MOCK2: `?mock2=off` puts the scheduling back the way MOCK1 had it — textures upload while the door pushes, the taps
 * read the mask back inside the call, the programs are only linked, the door opens before the room is ready, the marks
 * are placed on every frame of a camera move and the display pass never drops resolution. It exists so the
 * before-and-after table is measured on the same build, by the same tool (tools/mock2-perf.ts --old).
 */
export const LEGACY = typeof location !== 'undefined' && new URLSearchParams(location.search).get('mock2') === 'off';

type Anim = { label: string; start: number; dur: number; step: (t: number) => void; done: () => void; quiet: boolean };
export type FrameLog = { dt: number[]; js: number[]; px: number[]; step: number[] };
export type Seam = { label: string; first: { max: number; px: number }; last: { max: number; px: number } };
/** what a slot's two layers look like for now (an effect's pose); absent values are the layer at rest */
export type Pose = {
  pos?: number;
  a?: number;
  s?: number;
  lod?: number;
  slod?: number;
  dy?: number;
  gain?: number;
  clip?: [number, number];
  sclip?: [number, number];
};

export type TourOptions = {
  canvas: HTMLCanvasElement;
  reduceMotion: boolean;
  onCamera?: (cam: Cam, vp: Viewport) => void;
  /** MOCK3: the window changed size (a resize, a rotation): the page puts its own camera back (a close-up, a zoom) */
  onResize?: () => void;
};

export class TourEngine {
  readonly loader = new Loader(6);
  readonly gl: TourGL;
  cam: Cam = { cu: 0.5, cv: 0.5, z: 1 };
  vp: Viewport = { w: 1, h: 1 };
  rest: Cam = { cu: 0.5, cv: 0.5, z: 1 };
  /** where the camera looks from the door on a narrow screen (a wide one shows the whole frame: the rest camera) */
  doorCu = 0.5;
  /** what the display adds over the composition; an effect sets it and puts it back */
  d: Display;
  house: HouseId = WM;
  selection: Record<string, number> = Object.fromEntries(tour.slots.map((s) => [s.id, 1]));
  /** the slots whose product is in the room now */
  visible = new Set<string>();
  ready = false;
  reduce: boolean;
  /** frame times of every effect that ran, by its label (the frame-rate evidence) */
  frames: Record<string, FrameLog> = {};
  /** the tests: an effect is run at its two ends only, and what each end differs by from the frame beside it is kept */
  sync = false;
  seams: Seam[] = [];
  lastLabel = '';
  private front: 0 | 1 = 0;
  private poses = new Map<string, Pose[]>();
  private dirty = new Set<string>();
  private all = false;
  private anims = new Set<Anim>();
  private raf = 0;
  private last = 0;
  private ext: 'avif' | 'webp' = 'webp';
  private ro: ResizeObserver | null = null;
  private destroyed = false;
  private defaults: Promise<void> | null = null;
  private nordic: Draw[] | null = null;
  private loading = new Map<string, Promise<void>>();

  static create(o: TourOptions): TourEngine | null {
    // MOCK2: the width is chosen once, from the canvas the tour opens in (data.ts widthFor)
    const gl = TourGL.create(
      o.canvas,
      widthFor(
        Math.max(
          1,
          metrics.dom(() => o.canvas.clientWidth),
        ),
      ),
      tour.camera,
    );
    return gl ? new TourEngine(o, gl) : null;
  }
  private constructor(
    private o: TourOptions,
    gl: TourGL,
  ) {
    this.gl = gl;
    this.reduce = o.reduceMotion;
    this.d = restDisplay(this.cam, this.vp, tour.aspect);
  }

  // ---------- loading ----------
  private ensure(dr: Draw, priority: number, mips: boolean): Promise<void> {
    let p = this.loading.get(dr.key);
    if (!p) {
      p = this.loader
        .load(dr.url, priority)
        .then((img) => {
          metrics.count('decode');
          return this.upload(() => this.gl.upload(dr.key, img, mips));
        })
        .then(() => undefined);
      this.loading.set(dr.key, p);
      p.catch(() => this.loading.delete(dr.key));
    }
    return p;
  }
  /**
   * MOCK2: textures go to the GPU one at a time, between frames, and **never while anything moves** — the door's slow
   * push included, which MOCK1 let through. An upload in the middle of a move is a dropped frame. The same queue
   * carries the one other thing that stalls the main thread, the taps' read-back of the mask.
   */
  private uploads: (() => void)[] = [];
  private pumping = false;
  private upload(job: () => void): Promise<void> {
    return new Promise((resolve) => {
      this.uploads.push(() => {
        if (!this.destroyed) job();
        resolve();
      });
      this.pump();
    });
  }
  /** the queue runs on animation frames, and only on frames where nothing is moving */
  private pump(): void {
    if (this.pumping || this.destroyed) return;
    this.pumping = true;
    const tick = (): void => {
      if (this.destroyed) {
        this.pumping = false;
        return;
      }
      // MOCK1's rule, kept for the before-and-after measurement: an upload could land inside the door's slow push
      const idle = LEGACY ? [...this.anims].every((a) => a.label === 'door-push') : !this.anims.size;
      if (idle) {
        // as many as fit in a frame's quiet half, so the room is ready soon without a frame of its own running long
        const t0 = performance.now();
        do this.uploads.shift()?.();
        while (this.uploads.length && performance.now() - t0 < 8);
        if (!this.uploads.length) {
          this.gl.flushTaps();
          // and then one more thing to fetch, so its decode lands on a quiet frame too
          this.starts.shift()?.();
        }
      }
      if (this.uploads.length || this.starts.length || this.gl.tapsDue) requestAnimationFrame(tick);
      else this.pumping = false;
    };
    requestAnimationFrame(tick);
  }
  private keys(s: TourSlot, pos: number): [Draw, Draw] {
    const w = this.gl.width;
    return [
      { key: `${s.id}:${pos}:s`, url: layerUrl(s, pos, 'shadow', w), rect: s.rect, shadow: true },
      { key: `${s.id}:${pos}:p`, url: layerUrl(s, pos, 'product', w), rect: s.rect, shadow: false },
    ];
  }
  /** an option's layer and shadow, loaded and on the GPU */
  option(slotId: string, pos: number, priority = 0): Promise<void> {
    const s = this.slot(slotId);
    return Promise.all(this.keys(s, pos).map((k) => this.ensure(k, priority, true))).then(() => undefined);
  }
  slot(id: string): TourSlot {
    return tour.slots.find((s) => s.id === id)!;
  }

  /** The empty room first (the door looks into it); the default products behind it; then every other option. */
  async start(): Promise<void> {
    this.ext = (await supportsAvif()) ? 'avif' : 'webp';
    this.measure();
    await this.ensure(baseOf(WM, this.ext, this.gl.width), 0, false);
    if (this.destroyed) return;
    this.all = true;
    this.ready = true;
    this.render();
    // MOCK2: every display program is compiled, linked and drawn with before anything moves
    this.gl.warm(LEGACY);
    this.warmP = this.products().then(() => {
      // the first composition with the products in it, and the mask, are made while the visitor is still at the door
      if (this.destroyed || this.warmed) return;
      this.warmed = true;
      const was = [...this.visible];
      for (const s of tour.slots) this.settle(s.id, true);
      this.flush();
      this.mask(true);
      this.visible.clear();
      for (const id of was) this.visible.add(id);
      for (const s of tour.slots) this.dirty.add(s.id);
      this.flush();
    });
  }
  /**
   * MOCK2: the room is ready to be animated — every default layer fetched, decoded, uploaded and composed once, every
   * program compiled and drawn with. The door waits for this before it opens (FB1: nothing loads inside a move).
   */
  whenWarm(): Promise<void> {
    return LEGACY ? Promise.resolve() : (this.warmP ?? Promise.resolve());
  }
  get warmReady(): boolean {
    return this.warmed && !this.uploads.length;
  }
  private warmed = false;
  private warmP: Promise<void> | null = null;
  /**
   * Everything the visitor may ask for next, behind the room that is shown (the skeleton: variants load in the
   * background after the room is on screen): every other option, then the Nordic house. Called once the room rests.
   */
  background(): void {
    if (this.inBackground || this.destroyed) return;
    this.inBackground = true;
    // MOCK2: a background load is *started* on a frame where nothing moves, one at a time. Starting them all at once
    // meant a decode landing in the middle of the door's slow push (FB1: nothing happens inside a move).
    for (const s of tour.slots)
      for (const o of s.options) if (o.position !== this.selection[s.id]) this.later(() => void this.option(s.id, o.position, 2).catch(() => undefined));
    this.later(() => void this.otherHouse().catch(() => undefined));
  }
  /** runs `job` on the next frame where nothing is moving (the same queue the uploads wait in) */
  private later(job: () => void): void {
    this.starts.push(job);
    this.pump();
  }
  private starts: (() => void)[] = [];
  private inBackground = false;
  /** the default products are here (the reveal waits for them) */
  products(): Promise<void> {
    return (this.defaults ??= Promise.all(tour.slots.map((s) => this.option(s.id, this.selection[s.id]!, 1))).then(() => undefined));
  }
  /** the Nordic house's layers (the style change waits for them) */
  otherHouse(): Promise<void> {
    this.nordic ??= nordicLayers(this.gl.width);
    return Promise.all([this.ensure(baseOf(NORDIC, this.ext, this.gl.width), 3, false), ...this.nordic.map((l) => this.ensure(l, 3, false))]).then(
      () => undefined,
    );
  }

  // ---------- the composition ----------
  /** the layers of a house, the base first; `everything`: every product, shown or not (the mask of a reveal) */
  private list(house: HouseId = this.house, everything = false): LayerDraw[] {
    if (house === NORDIC)
      return [layer(baseOf(NORDIC, this.ext, this.gl.width).key, [0, 1, 0, 1], false), ...(this.nordic ?? []).map((l) => layer(l.key, l.rect, l.shadow))];
    const out = [layer(baseOf(WM, this.ext, this.gl.width).key, [0, 1, 0, 1], false)];
    for (const s of tour.slots) {
      const code = Math.round(s.depth_m * MASK_PER_M);
      const poses = everything ? [{}] : (this.poses.get(s.id) ?? (this.visible.has(s.id) ? [{}] : []));
      const made = poses.map((p) => {
        const [sh, pr] = this.keys(s, p.pos ?? this.selection[s.id]!);
        return [
          { ...layer(sh.key, s.rect, true), opacity: p.s ?? p.a ?? 1, lod: p.slod ?? 0, clip: p.sclip ?? p.clip ?? [0, 1] },
          { ...layer(pr.key, s.rect, false, code), opacity: p.a ?? 1, lod: p.lod ?? 0, dy: p.dy ?? 0, gain: p.gain ?? 1, clip: p.clip ?? [0, 1] },
        ] as [LayerDraw, LayerDraw];
      });
      // every shadow of the slot under every product of it (a swap draws two of each)
      out.push(...made.map((m) => m[0]), ...made.map((m) => m[1]));
    }
    return out;
  }
  /** poses a slot's layers for the next frame (an effect); [] hides it */
  pose(slotId: string, poses: Pose[]): void {
    this.poses.set(slotId, poses);
    this.dirty.add(slotId);
  }
  /** the slot is at rest again: in the room or out of it */
  settle(slotId: string, visible: boolean): void {
    this.poses.delete(slotId);
    if (visible) this.visible.add(slotId);
    else this.visible.delete(slotId);
    this.dirty.add(slotId);
  }
  /** the mask of the products: the ones in the room, or all of them (a reveal lights a product before it is there) */
  mask(everything = false, forTaps = !everything): void {
    this.gl.composeMask(this.list(this.house, everything), forTaps);
    if (!forTaps) return;
    // the read-back itself waits for a frame where nothing moves (MOCK2); MOCK1 did it here, inside the effect
    if (LEGACY) this.gl.flushTaps();
    else this.pump();
  }
  /** the slot under a point of the canvas, among the products in the room */
  slotAt(u: number, v: number): TourSlot | null {
    const code = this.gl.codeAt(u, v);
    return code ? (tour.slots.find((s) => Math.round(s.depth_m * MASK_PER_M) === code && this.visible.has(s.id)) ?? null) : null;
  }
  private rect(s: TourSlot): Px {
    const { width: w, height: h } = this.gl;
    const pad = 10;
    return [
      Math.max(0, Math.round(s.rect[0] * w) - pad),
      Math.max(0, Math.round(s.rect[2] * h) - pad),
      Math.min(w, Math.round(s.rect[1] * w) + pad),
      Math.min(h, Math.round(s.rect[3] * h) + pad),
    ];
  }
  /** the frame's width in the device's own pixels at this camera: what decides whether the mip levels are read */
  private frameDevicePx(): number {
    const dpr = Math.min(2, (typeof devicePixelRatio === 'number' ? devicePixelRatio : 1) || 1);
    return Math.max(this.vp.w, this.vp.h * tour.aspect) * this.cam.z * dpr;
  }
  private flush(): number {
    if (!this.all && !this.dirty.size) return 0;
    this.gl.compose(this.front, this.list(), this.all ? null : [...this.dirty].map((id) => this.rect(this.slot(id))), this.gl.needMips(this.frameDevicePx()));
    this.all = false;
    this.dirty.clear();
    return this.gl.shaded;
  }
  /**
   * Composes what changed and draws the frame now. MOCK2: while something moves and frames run long, the display pass
   * is drawn at a fraction of the canvas and stretched (`scale`); at rest it is always the full resolution, so the
   * frame the room settles on is exactly the composition of its layers.
   */
  render(): number {
    if (!this.ready || this.destroyed) return 0;
    const px = this.flush();
    this.d.cam = this.cam;
    this.d.vp = this.vp;
    this.gl.display(this.d, this.front, !LEGACY && this.anims.size ? this.scale : 1);
    return px;
  }
  /** the resolution of the display pass while moving: 1, or less on a device that cannot keep up */
  scale = 1;
  private minScale = 1;
  /** how far down it may go; the step is taken only after two frames in a row run long */
  static readonly SCALE_FLOOR = 0.62;
  resetDisplay(): void {
    const { door, doorR, doorAmt } = this.d;
    this.d = { ...restDisplay(this.cam, this.vp, tour.aspect), door, doorR, doorAmt };
  }

  /**
   * A whole change at once: `change` sets the next state (a house, the products in the room), it is composed beside the
   * frame on screen, and `step` takes the display from one to the other (the default: a plain dissolve).
   */
  async between(label: string, ms: number, change: () => void, step?: (t: number) => void): Promise<void> {
    this.flush();
    change();
    const next = (this.front ? 0 : 1) as 0 | 1;
    // the whole next frame is composed here, which is the room's own area: MOCK2 gives it a frame of its own, so the
    // first frame of the effect does not carry it
    this.gl.compose(next, this.list(), null, this.gl.needMips(this.frameDevicePx()));
    this.all = false;
    this.dirty.clear();
    if (!this.sync) await new Promise((r) => requestAnimationFrame(() => r(null)));
    await this.run(label, ms, step ?? ((t) => (this.d.mix = t)), () => {
      this.front = next;
      this.resetDisplay();
    });
  }
  /** the next house, for `between` */
  setHouse(h: HouseId): void {
    this.house = h;
  }

  // ---------- the camera ----------
  /** the camera at the door: the rest camera, turned to `doorCu` where the screen is narrower than the frame */
  atDoor(): Cam {
    // reduced motion: the wall only fades, so the door already looks where the room rests
    return clampCam({ ...this.rest, cu: !this.reduce && this.vp.w / this.vp.h < 1.1 ? this.doorCu : this.rest.cu }, this.vp, tour.aspect);
  }
  camFor(box: Box, reserve: number): Cam {
    return camForBox(box, this.vp, tour.aspect, reserve);
  }
  /**
   * MOCK2: the page's marks are placed when the camera lands, not on every frame of the move. Placing them per frame
   * wrote a transform for every mark and measured a label, which is a style recalculation and a layout inside the
   * animation; they are invisible while the camera travels anyway.
   */
  moveCam(label: string, to: Cam, ms: number, also?: (e: number, t: number) => void, ease: (t: number) => number = EASE.camera): Promise<void> {
    const from = { ...this.cam };
    return this.run(
      label,
      this.reduce ? 0 : ms,
      (t) => {
        const e = ease(t);
        this.cam = t >= 1 ? { ...to } : lerpCam(from, to, e);
        also?.(e, t);
        if (LEGACY) this.o.onCamera?.(this.cam, this.vp);
      },
      () => this.o.onCamera?.(this.cam, this.vp),
    );
  }
  panBy(dxCss: number): void {
    if (this.cam.z > 1.001 || this.anims.size) return;
    const fw = Math.max(this.vp.w, this.vp.h * tour.aspect);
    this.cam = clampCam({ ...this.cam, cu: this.cam.cu - dxCss / fw }, this.vp, tour.aspect);
    this.rest = { ...this.cam };
    this.o.onCamera?.(this.cam, this.vp);
    this.render();
  }

  // ---------- the loop ----------
  /** Runs `step` from 0 to 1 over `ms` (the evidence's slow motion stretches it), then `done`. Never rejects. */
  run(label: string, ms: number, step: (t: number) => void, done?: () => void, quiet = false): Promise<void> {
    if (this.sync) return Promise.resolve(quiet ? done?.() : this.ends(label, step, done));
    ms *= timeScale();
    // the evidence reads the last run of each effect
    this.frames[label] = { dt: [], js: [], px: [], step: [] };
    this.lastLabel = label;
    // MOCK2: what happened while this effect ran — decodes, uploads, compiles, read-backs, layouts (metrics.ts)
    // MOCK3: every effect has a window of its own, so two that overlap are each held to their own counters
    metrics.begin(label);
    if (!this.anims.size) this.minScale = this.scale = 1;
    return new Promise((resolve) => {
      const finish = () => {
        done?.();
        const f = this.frames[label]!;
        this.stat = metrics.end(label, f.dt, f.js, f.px, this.minScale, f.step);
        if (!this.anims.size) this.scale = 1;
        resolve();
      };
      if (ms <= 0 || this.destroyed) {
        step(1);
        finish();
        this.render();
        return;
      }
      this.anims.add({ label, start: performance.now(), dur: ms, step, done: finish, quiet });
      if (!this.raf) this.raf = requestAnimationFrame(this.frame);
    });
  }
  /**
   * MOCK3: an effect of the page itself — the panel opening, the wheel rising, the strip coming back. The browser moves
   * it (transform and opacity); the engine only holds the rule over it: nothing uploads while it runs, its frames are
   * timed, and its counters are kept like any other effect's. The canvas is not drawn again for it.
   */
  ui(label: string, ms: number): Promise<void> {
    return this.run(label, this.reduce ? 0 : ms, () => undefined, undefined, true);
  }
  /**
   * MOCK3: a gesture — a pinch, a drag of the zoomed picture. It lasts until `stop(label)`; the page sets the camera
   * from its pointer events and the frame is drawn once per animation frame, under the same rule as every effect.
   */
  hold(label: string): void {
    if (this.sync || [...this.anims].some((a) => a.label === label)) return;
    void this.run(label, Infinity, () => undefined);
  }
  /** a pause between beats (the designer's 0.2 s of quiet): nothing is drawn meanwhile */
  wait(ms: number): Promise<void> {
    return this.sync ? Promise.resolve() : new Promise((r) => setTimeout(r, ms * timeScale()));
  }
  /** stops an effect where it is (the door's slow push, when the visitor walks in); its promise resolves */
  stop(label: string): void {
    for (const a of [...this.anims])
      if (a.label === label) {
        this.anims.delete(a);
        a.done();
      }
  }
  get busy(): boolean {
    return this.anims.size > 0;
  }
  private frame = (now: number): void => {
    this.raf = 0;
    const t0 = performance.now();
    const labels = [...this.anims].map((a) => a.label);
    const draw = [...this.anims].some((a) => !a.quiet);
    for (const a of [...this.anims]) {
      const t = Math.min(1, (now - a.start) / a.dur);
      a.step(t);
      if (t >= 1) {
        this.anims.delete(a);
        a.done();
      }
    }
    // MOCK2: the effect's own script time, apart from handing the frame to the driver (which is a software rasteriser
    // on this machine and a few microseconds on a phone with a card)
    const step = performance.now() - t0;
    // an effect of the page alone leaves the canvas as it is: the frame it runs over is already there
    const px = draw ? this.render() : 0;
    const js = performance.now() - t0;
    if (this.last) {
      const dt = now - this.last;
      for (const l of labels) {
        const f = (this.frames[l] ??= { dt: [], js: [], px: [], step: [] });
        f.dt.push(dt);
        f.js.push(js);
        f.px.push(px);
        f.step.push(step);
      }
      // MOCK2: a device that cannot hold the frame draws the next ones smaller rather than late; two long frames in a
      // row take a step down, and the resolution is full again the moment the effect ends
      if (dt > 20 && !LEGACY && draw) {
        if (this.slow++ >= 1 && this.scale > TourEngine.SCALE_FLOOR) {
          this.scale = Math.max(TourEngine.SCALE_FLOOR, this.scale - 0.18);
          this.minScale = Math.min(this.minScale, this.scale);
          this.slow = 0;
        }
      } else this.slow = 0;
    }
    this.last = this.anims.size ? now : 0;
    if (this.anims.size) this.raf = requestAnimationFrame(this.frame);
  };
  private slow = 0;
  /** the last effect's numbers, for the temporary panel */
  stat: EffectStat | null = null;

  /** the tests' run: the effect at 0 against the frame before it, and at 1 against the frame after it */
  private ends(label: string, step: (t: number) => void, done?: () => void): void {
    const shot = () => {
      this.render();
      return this.gl.readScreen().data;
    };
    const diff = (a: Uint8Array, b: Uint8Array) => {
      let max = 0;
      let px = 0;
      for (let i = 0; i < a.length; i += 4) {
        const d = Math.max(Math.abs(a[i]! - b[i]!), Math.abs(a[i + 1]! - b[i + 1]!), Math.abs(a[i + 2]! - b[i + 2]!));
        if (d) px++;
        if (d > max) max = d;
      }
      return { max, px };
    };
    const before = shot();
    step(0);
    const first = diff(before, shot());
    step(1);
    const end = shot();
    done?.();
    this.seams.push({ label, first, last: diff(end, shot()) });
  }

  // ---------- size ----------
  private measure(): boolean {
    const el = this.o.canvas;
    const vp = metrics.dom(() => ({ w: Math.max(1, el.clientWidth), h: Math.max(1, el.clientHeight) }));
    // the same size: nothing to do, and the camera (a close-up, a zoom) stays where it is
    if (vp.w === this.vp.w && vp.h === this.vp.h) return false;
    this.vp = vp;
    this.gl.resize(this.vp.w, this.vp.h, Math.min(this.dprCap, devicePixelRatio || 1));
    this.rest = defaultCam(this.vp, tour.aspect, tour.mobile_center_u);
    this.cam = { ...this.rest };
    return true;
  }
  /** the canvas is drawn at the device's own pixels up to this ratio (MOCK3: the sharpness switch raises it) */
  dprCap = 2;
  /** MOCK3: the canvas at another pixel ratio, on a frame where nothing moves (the camera stays where it is) */
  setDprCap(cap: number): void {
    if (cap === this.dprCap || this.anims.size) return;
    this.dprCap = cap;
    this.gl.resize(this.vp.w, this.vp.h, Math.min(cap, devicePixelRatio || 1));
    this.render();
  }
  /**
   * The window's size is measured here and only here: when the tour starts, and when the window is resized or the
   * phone is turned (MOCK3: never during an animation of ours — a rotation in the middle of one is the visitor's own
   * doing and costs one layout). The camera goes back to the whole frame; the page puts a close-up back (onResize).
   */
  observe(): void {
    this.ro = new ResizeObserver(() => {
      if (this.destroyed) return;
      const door = this.d.doorAmt > 0;
      if (!this.measure()) return;
      if (door) this.cam = this.atDoor();
      this.o.onResize?.();
      this.o.onCamera?.(this.cam, this.vp);
      this.render();
    });
    this.ro.observe(this.o.canvas);
  }

  /** the tests: the composition's own pixels in a rectangle of the canvas (px), top row first */
  read(r: Px): Uint8Array {
    this.flush();
    return this.gl.readTarget(this.front, r);
  }

  destroy(): void {
    this.destroyed = true;
    cancelAnimationFrame(this.raf);
    for (const a of [...this.anims]) a.done();
    this.anims.clear();
    this.ro?.disconnect();
    this.gl.destroy();
  }
}
export { FX };
