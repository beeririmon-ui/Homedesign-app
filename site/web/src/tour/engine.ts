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
import { NORDIC, WM, baseOf, layerUrl, nordicLayers, tour, type Draw, type HouseId, type TourSlot } from './data';

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

type Anim = { label: string; start: number; dur: number; step: (t: number) => void; done: () => void };
export type FrameLog = { dt: number[]; js: number[]; px: number[] };
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
    const gl = TourGL.create(o.canvas, tour.native, tour.camera);
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
      p = this.loader.load(dr.url, priority).then((img) => this.upload(() => this.gl.upload(dr.key, img, mips)));
      this.loading.set(dr.key, p);
      p.catch(() => this.loading.delete(dr.key));
    }
    return p;
  }
  /**
   * Textures go to the GPU one at a time, between frames, and never while an effect runs (the door's slow push apart):
   * an upload in the middle of a move is a dropped frame.
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
  private pump(): void {
    if (this.pumping) return;
    this.pumping = true;
    const tick = () => {
      if ([...this.anims].every((a) => a.label === 'door-push')) this.uploads.shift()?.();
      if (this.uploads.length && !this.destroyed) setTimeout(tick, this.anims.size ? 24 : 0);
      else this.pumping = false;
    };
    setTimeout(tick, 0);
  }
  private keys(s: TourSlot, pos: number): [Draw, Draw] {
    return [
      { key: `${s.id}:${pos}:s`, url: layerUrl(s, pos, 'shadow'), rect: s.rect, shadow: true },
      { key: `${s.id}:${pos}:p`, url: layerUrl(s, pos, 'product'), rect: s.rect, shadow: false },
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
    await this.ensure(baseOf(WM, this.ext), 0, false);
    if (this.destroyed) return;
    this.all = true;
    this.ready = true;
    this.render();
    this.gl.warm();
    void this.products();
  }
  /**
   * Everything the visitor may ask for next, behind the room that is shown (the skeleton: variants load in the
   * background after the room is on screen): every other option, then the Nordic house. Called once the room rests.
   */
  background(): void {
    if (this.inBackground || this.destroyed) return;
    this.inBackground = true;
    for (const s of tour.slots)
      for (const o of s.options) if (o.position !== this.selection[s.id]) void this.option(s.id, o.position, 2).catch(() => undefined);
    void this.otherHouse().catch(() => undefined);
  }
  private inBackground = false;
  /** the default products are here (the reveal waits for them) */
  products(): Promise<void> {
    return (this.defaults ??= Promise.all(tour.slots.map((s) => this.option(s.id, this.selection[s.id]!, 1))).then(() => undefined));
  }
  /** the Nordic house's layers (the style change waits for them) */
  otherHouse(): Promise<void> {
    this.nordic ??= nordicLayers();
    return Promise.all([this.ensure(baseOf(NORDIC, this.ext), 3, false), ...this.nordic.map((l) => this.ensure(l, 3, false))]).then(() => undefined);
  }

  // ---------- the composition ----------
  /** the layers of a house, the base first; `everything`: every product, shown or not (the mask of a reveal) */
  private list(house: HouseId = this.house, everything = false): LayerDraw[] {
    if (house === NORDIC) return [layer(baseOf(NORDIC, this.ext).key, [0, 1, 0, 1], false), ...(this.nordic ?? []).map((l) => layer(l.key, l.rect, l.shadow))];
    const out = [layer(baseOf(WM, this.ext).key, [0, 1, 0, 1], false)];
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
  private flush(): number {
    if (!this.all && !this.dirty.size) return 0;
    this.gl.compose(this.front, this.list(), this.all ? null : [...this.dirty].map((id) => this.rect(this.slot(id))));
    this.all = false;
    this.dirty.clear();
    return this.gl.shaded;
  }
  /** composes what changed and draws the frame now */
  render(): number {
    if (!this.ready || this.destroyed) return 0;
    const px = this.flush();
    this.d.cam = this.cam;
    this.d.vp = this.vp;
    this.gl.display(this.d, this.front);
    return px;
  }
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
    this.gl.compose(next, this.list(), null);
    this.all = false;
    this.dirty.clear();
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
  moveCam(label: string, to: Cam, ms: number, also?: (e: number, t: number) => void): Promise<void> {
    const from = { ...this.cam };
    return this.run(label, this.reduce ? 0 : ms, (t) => {
      const e = EASE.camera(t);
      this.cam = t >= 1 ? { ...to } : lerpCam(from, to, e);
      also?.(e, t);
      this.o.onCamera?.(this.cam, this.vp);
    });
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
  run(label: string, ms: number, step: (t: number) => void, done?: () => void): Promise<void> {
    if (this.sync) return Promise.resolve(this.ends(label, step, done));
    ms *= timeScale();
    // the evidence reads the last run of each effect
    this.frames[label] = { dt: [], js: [], px: [] };
    this.lastLabel = label;
    return new Promise((resolve) => {
      const finish = () => {
        done?.();
        resolve();
      };
      if (ms <= 0 || this.destroyed) {
        step(1);
        finish();
        this.render();
        return;
      }
      this.anims.add({ label, start: performance.now(), dur: ms, step, done: finish });
      if (!this.raf) this.raf = requestAnimationFrame(this.frame);
    });
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
    for (const a of [...this.anims]) {
      const t = Math.min(1, (now - a.start) / a.dur);
      a.step(t);
      if (t >= 1) {
        this.anims.delete(a);
        a.done();
      }
    }
    const px = this.render();
    const js = performance.now() - t0;
    if (this.last)
      for (const l of labels) {
        const f = (this.frames[l] ??= { dt: [], js: [], px: [] });
        f.dt.push(now - this.last);
        f.js.push(js);
        f.px.push(px);
      }
    this.last = this.anims.size ? now : 0;
    if (this.anims.size) this.raf = requestAnimationFrame(this.frame);
  };

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
  private measure(): void {
    const el = this.o.canvas;
    this.vp = { w: Math.max(1, el.clientWidth), h: Math.max(1, el.clientHeight) };
    this.gl.resize(this.vp.w, this.vp.h, Math.min(2, devicePixelRatio || 1));
    this.rest = defaultCam(this.vp, tour.aspect, tour.mobile_center_u);
    this.cam = { ...this.rest };
  }
  observe(): void {
    this.ro = new ResizeObserver(() => {
      if (this.cam.z > 1.03 || this.destroyed) return;
      const door = this.d.doorAmt > 0;
      this.measure();
      if (door) this.cam = this.atDoor();
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
