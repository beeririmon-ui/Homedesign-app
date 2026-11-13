/**
 * MOCK2 (2026-11-13), FB1 ("first of all I want the interface to work smoothly"): what the tour counts while it moves.
 *
 * The rule the sprint is built on: during an animated frame nothing may decode, upload a texture, link a program, read
 * the GPU back or make the browser lay the page out. Those are the five counters here. Each effect gets a window
 * (engine.run opens it), and what happened inside it is kept per effect: the counters, the frame intervals, the script
 * time per frame, and the pixels composed. A test fails when a counter is above 0 (e2e/mock2.spec.ts); the owner can
 * copy the same table off his own phone from the temporary panel.
 *
 * `dom` wraps every place where our own code asks the browser for a measurement (offsetWidth, getBoundingClientRect,
 * clientWidth…), which is what forces a layout. Counting our own reads is the honest measure: a counter at 0 means the
 * page's code asked for nothing while the effect ran.
 */
export type Counts = {
  /** image decodes that finished (createImageBitmap) */
  decode: number;
  /** textures uploaded to the GPU (texImage2D, with its mip levels) */
  upload: number;
  /** shader programs compiled and linked */
  compile: number;
  /** pixels read back from the GPU (a stall: the CPU waits for the GPU) */
  readback: number;
  /** measurements our code asked the browser for, each of which can force a layout */
  layout: number;
};
export const zero = (): Counts => ({ decode: 0, upload: 0, compile: 0, readback: 0, layout: 0 });
const minus = (a: Counts, b: Counts): Counts => ({
  decode: a.decode - b.decode,
  upload: a.upload - b.upload,
  compile: a.compile - b.compile,
  readback: a.readback - b.readback,
  layout: a.layout - b.layout,
});
export const sum = (c: Counts): number => c.decode + c.upload + c.compile + c.readback + c.layout;

export type EffectStat = {
  label: string;
  frames: number;
  ms: number;
  fps: number;
  /** the frame intervals: median, 95th and the worst */
  dt_p50: number;
  dt_p95: number;
  dt_max: number;
  /** frames longer than 20 ms and than 34 ms (one and two dropped frames at 60 Hz) */
  long20: number;
  long34: number;
  /** the longest run of frames over 20 ms */
  long_run: number;
  /** the script time of a frame — the whole of it: the effect's own work and handing the frame to the driver */
  js_mean: number;
  js_p95: number;
  js_max: number;
  /**
   * The effect's own script time: posing the layers and setting what the display adds, without the GL calls that
   * hand the frame over. On this machine those calls are a software rasteriser and cost milliseconds; on a phone with
   * a card they are a few microseconds. This is the number that carries over.
   */
  step_mean: number;
  step_p95: number;
  step_max: number;
  /** frames whose own script ran over 8 ms (the budget for the worst frame) */
  step_over8: number;
  /** megapixels composed per frame, on average and at the worst */
  mpx: number;
  mpx_max: number;
  counts: Counts;
  /** the resolution the display pass ran at, at its lowest (1 = full) */
  min_scale: number;
};

const pct = (a: number[], q: number): number => [...a].sort((x, y) => x - y)[Math.min(a.length - 1, Math.floor(a.length * q))] ?? 0;
const r1 = (x: number): number => +x.toFixed(1);
const r2 = (x: number): number => +x.toFixed(2);

export class Metrics {
  /** every counter since the page opened */
  readonly total: Counts = zero();
  /** the last run of every effect */
  readonly effects: Record<string, EffectStat> = {};
  /** the order the effects ran in */
  readonly order: string[] = [];
  /** MOCK3: a window per effect that is running — two effects may overlap (the wheel rises while the camera lands) */
  private open = new Map<string, Counts>();

  count(k: keyof Counts, n = 1): void {
    this.total[k] += n;
  }
  /** a measurement of the page: counted, because asking for one can force a layout */
  dom<T>(f: () => T): T {
    this.total.layout++;
    return f();
  }
  begin(label: string): void {
    this.open.set(label, { ...this.total });
  }
  end(label: string, dt: number[], js: number[], px: number[], minScale: number, step: number[] = []): EffectStat {
    const at = this.open.get(label);
    const counts = at ? minus(this.total, at) : zero();
    this.open.delete(label);
    const ms = dt.reduce((a, b) => a + b, 0);
    let run = 0;
    let longRun = 0;
    for (const d of dt) {
      run = d > 20 ? run + 1 : 0;
      if (run > longRun) longRun = run;
    }
    const stat: EffectStat = {
      label,
      frames: dt.length,
      ms: Math.round(ms),
      fps: dt.length ? r1((1000 * dt.length) / ms) : 0,
      dt_p50: r1(pct(dt, 0.5)),
      dt_p95: r1(pct(dt, 0.95)),
      dt_max: r1(Math.max(0, ...dt)),
      long20: dt.filter((d) => d > 20).length,
      long34: dt.filter((d) => d > 34).length,
      long_run: longRun,
      js_mean: r2(js.reduce((a, b) => a + b, 0) / (js.length || 1)),
      js_p95: r2(pct(js, 0.95)),
      js_max: r2(Math.max(0, ...js)),
      step_mean: r2(step.reduce((a, b) => a + b, 0) / (step.length || 1)),
      step_p95: r2(pct(step, 0.95)),
      step_max: r2(Math.max(0, ...step)),
      step_over8: step.filter((x) => x > 8).length,
      mpx: r2(px.reduce((a, b) => a + b, 0) / (px.length || 1) / 1e6),
      mpx_max: r2(Math.max(0, ...px) / 1e6),
      counts,
      min_scale: r2(minScale),
    };
    if (!this.effects[label]) this.order.push(label);
    this.effects[label] = stat;
    return stat;
  }
  reset(): void {
    for (const k of Object.keys(this.effects)) delete this.effects[k];
    this.order.length = 0;
  }
}
export const metrics = new Metrics();

/** one line for the temporary panel: what the last effect cost */
export function statLine(s: EffectStat): string {
  const bad = sum(s.counts);
  return (
    `${s.label}: ${s.fps} fps, ${s.long20} long frames of ${s.frames} (worst ${s.dt_max} ms), script ${s.step_mean}/${s.step_max} ms, frame ${s.js_mean}/${s.js_max} ms` +
    (bad ? `, ${bad} interruptions` : ', 0 interruptions')
  );
}

/** what the owner copies off his phone: the device, and the table of every effect that ran */
export function report(m: Metrics, env: Record<string, string | number>): string {
  const head = Object.entries(env)
    .map(([k, v]) => `${k}: ${v}`)
    .join('\n');
  const rows = m.order.map((l) => {
    const s = m.effects[l]!;
    const c = s.counts;
    return [
      s.label,
      s.frames,
      s.fps,
      `${s.dt_p50}/${s.dt_p95}/${s.dt_max}`,
      `${s.long20}/${s.long34}`,
      s.long_run,
      `${s.step_mean}/${s.step_max}`,
      `${s.js_mean}/${s.js_max}`,
      `${s.mpx}`,
      s.min_scale,
      `${c.decode}/${c.upload}/${c.compile}/${c.readback}/${c.layout}`,
    ].join(' | ');
  });
  return [
    'tour mock-up (MOCK3) — frame report',
    head,
    '',
    'effect | frames | fps | frame p50/p95/max ms | >20/>34 ms | longest run | script mean/max ms | frame work mean/max ms | MP composed | min scale | decode/upload/compile/readback/layout',
    ...rows,
    '',
    'every count above should be 0: nothing may decode, upload, compile, read back or measure the page while an effect runs.',
  ].join('\n');
}
