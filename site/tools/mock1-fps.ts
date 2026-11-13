/**
 * MOCK1: the frame times of every animation of the tour, on a desktop profile (1280 × 720) and on a mid-range phone
 * profile (Pixel 7's screen, the CPU throttled ×4), from the engine's own log (web/src/tour/engine.ts `frames`: the
 * interval between frames, the script time of each frame and the pixels it composed).
 *
 *   tsx tools/mock1-fps.ts <out dir>          against `npm run preview` (HD_BASE_URL, default http://127.0.0.1:8788)
 *
 * Each effect is run on its own, at its real speed, with the page's own marks (rings, labels) running over it. For a
 * reference on the same machine the room engine's zoom (S23, as QA accepted it) is measured the same way.
 *
 * What the numbers are: this machine has no GPU. Chromium draws WebGL in software (SwiftShader), so the interval between
 * frames here is the cost of rasterising the canvas on the CPU, not of the page's code. The numbers that carry over to a
 * real phone are the script time per frame under the ×4 throttle, and the pixels composed per frame. HD_GPU=1 (a machine
 * with a GPU) turns the 60 fps gate on: no effect may drop two frames in a row.
 */
import { chromium, devices, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const OUT = process.argv[2] ?? 'test-results/mock1';
const BASE = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';
const TOUR = process.env.HD_TOUR_URL ?? `${BASE}/tour/`;
const executablePath = process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium';
const GPU = process.env.HD_GPU === '1';
const args = GPU ? [] : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'];
const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
const PROFILES = [
  { id: 'desktop', label: 'desktop 1280 × 720', context: { viewport: { width: 1280, height: 720 } }, throttle: 1 },
  { id: 'phone', label: 'phone (Pixel 7 screen, CPU ×4)', context: pixel, throttle: 4 },
] as const;

type Log = { dt: number[]; js: number[]; px: number[] };
export type Row = {
  effect: string;
  frames: number;
  ms: number;
  fps: number;
  dt_p50: number;
  dt_p95: number;
  dt_max: number;
  /** frames longer than 1.5 × 16.7 ms: a dropped frame at 60 Hz */
  long: number;
  /** the longest run of them */
  long_run: number;
  js_mean: number;
  js_p95: number;
  js_max: number;
  mpx: number;
};
const pct = (a: number[], q: number) => [...a].sort((x, y) => x - y)[Math.min(a.length - 1, Math.floor(a.length * q))] ?? 0;
const r1 = (x: number) => +x.toFixed(1);
function row(effect: string, l: Log): Row {
  const ms = l.dt.reduce((a, b) => a + b, 0);
  let run = 0;
  let longRun = 0;
  for (const d of l.dt) {
    run = d > 25 ? run + 1 : 0;
    longRun = Math.max(longRun, run);
  }
  return {
    effect,
    frames: l.dt.length,
    ms: Math.round(ms),
    fps: l.dt.length ? r1((1000 * l.dt.length) / ms) : 0,
    dt_p50: r1(pct(l.dt, 0.5)),
    dt_p95: r1(pct(l.dt, 0.95)),
    dt_max: r1(Math.max(0, ...l.dt)),
    long: l.dt.filter((d) => d > 25).length,
    long_run: longRun,
    js_mean: +(l.js.reduce((a, b) => a + b, 0) / (l.js.length || 1)).toFixed(2),
    js_p95: +pct(l.js, 0.95).toFixed(2),
    js_max: +Math.max(0, ...l.js).toFixed(2),
    mpx: +(l.px.reduce((a, b) => a + b, 0) / (l.px.length || 1) / 1e6).toFixed(2),
  };
}

/** every effect of the tour, one after the other, each at its real speed; the engine keeps the last run of each label */
async function tourRun(page: Page): Promise<Record<string, Log>> {
  await page.goto(TOUR);
  await page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
  return page.evaluate(async () => {
    const e = window.__hdTour!;
    const m = window.__hdTourFx!;
    const ui = m.ui;
    const out: Record<string, { dt: number[]; js: number[]; px: number[] }> = {};
    const keep = (label: string, as = label) => {
      const f = e.frames[label];
      if (f) out[as] = { dt: [...f.dt], js: [...f.js], px: [...f.px] };
    };
    const rest = () => new Promise((r) => setTimeout(r, 350));
    const px = (name: string) => parseFloat(getComputedStyle(document.querySelector('.tour')!).getPropertyValue(name));
    const door = { cx: px('--dx'), cy: px('--dy'), hw: px('--dw') / 2, hh: px('--dh') / 2, r: px('--dr') };
    await e.products();
    await e.otherHouse();
    const vase = e.slot('vase');
    for (const o of vase.options) await e.option('vase', o.position);
    await rest();
    await m.enter(e);
    keep('enter');
    for (const k of ['a', 'b', 'c'] as const) {
      await rest();
      await m.reveal(e, ui, k);
      keep(`reveal-${k}`);
      await rest();
      await m.collect(e, ui);
    }
    keep('collect');
    await m.reveal(e, ui, 'b');
    await rest();
    const b = vase.options[0]!.box;
    await e.moveCam('zoom-in', e.camFor([b[0] - 0.02, b[1] + 0.02, b[2] - 0.05, b[3] + 0.05], 0.5), 1000, (k) => {
      e.d.vig = 0.1 * k;
      e.d.vigBox = vase.rect;
    });
    keep('zoom-in');
    for (const [to, dir, kind] of [
      [2, 1, 's1'],
      [3, 1, 's2'],
      [1, -1, 's3'],
    ] as const) {
      await rest();
      await m.swap(e, ui, vase, to, dir, kind);
      keep(`swap-${kind}`);
    }
    await rest();
    await e.moveCam('zoom-out', e.rest, 1000, (k) => (e.d.vig = 0.1 * (1 - k)));
    keep('zoom-out');
    await rest();
    await m.style(e, ui, 'nordic', 'y1', 'b');
    keep('style-y1', 'style-y1 (the shell, to Nordic)');
    keep('style-y1-nordic', 'style-y1 (the plane over the Nordic room)');
    await rest();
    await m.style(e, ui, 'warm-modern', 'y1', 'b');
    keep('style-y1', 'style-y1 (the shell, back)');
    keep('reveal-b', 'style-y1 (the short reveal)');
    await rest();
    await m.style(e, ui, 'nordic', 'y2', 'b');
    keep('style-y2', 'style-y2 (to Nordic)');
    await rest();
    await m.style(e, ui, 'warm-modern', 'y2', 'b');
    keep('style-y2', 'style-y2 (back)');
    await rest();
    await m.collect(e, ui);
    await m.leave(e, door);
    keep('leave');
    return out;
  });
}

/** the reference: the room engine's zoom into the wheel on the warm-modern house's page, as S23 has it */
async function roomZoom(page: Page): Promise<Log> {
  await page.goto(`${BASE}/rooms/living-room/?style=warm-modern`);
  const spot = page.locator('button.hotspot:visible').first();
  await spot.waitFor({ timeout: 60_000 });
  await page.evaluate(() => (window.__hdFrames = []));
  await spot.click({ force: true });
  await page.getByRole('dialog').waitFor({ timeout: 60_000 });
  const dt = await page.evaluate(() => window.__hdFrames ?? []);
  return { dt, js: [], px: [] };
}

const browser = await chromium.launch({ executablePath, args });
const result: Record<string, { label: string; rows: Row[] }> = {};
for (const p of PROFILES) {
  const ctx = await browser.newContext({ ...p.context, locale: 'he-IL' });
  // tsx (esbuild) wraps named functions in a helper the page does not have
  await ctx.addInitScript({ content: 'globalThis.__name = (f) => f;' });
  const page = await ctx.newPage();
  if (p.throttle > 1) await (await ctx.newCDPSession(page)).send('Emulation.setCPUThrottlingRate', { rate: p.throttle });
  const logs = await tourRun(page);
  const rows = Object.entries(logs).map(([k, l]) => row(k, l));
  if (!process.env.HD_TOUR_URL) rows.push(row('reference: the room engine, zoom into the wheel (S23)', await roomZoom(page)));
  result[p.id] = { label: p.label, rows };
  await ctx.close();
}
await browser.close();

mkdirSync(join(OUT, 'data'), { recursive: true });
writeFileSync(
  join(OUT, 'data', 'frame-rates.json'),
  JSON.stringify({ gpu: GPU, renderer: GPU ? 'the machine’s GPU' : 'SwiftShader (software, no GPU)', profiles: result }, null, 1),
);
const md = Object.values(result)
  .map(
    (p) =>
      `### ${p.label}\n\n| effect | frames | ms | fps | frame p50 / p95 / max (ms) | long frames (> 25 ms) | longest run | script per frame: mean / p95 / max (ms) | composed per frame (MP) |\n| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n` +
      p.rows
        .map(
          (r) =>
            `| ${r.effect} | ${r.frames} | ${r.ms} | ${r.fps} | ${r.dt_p50} / ${r.dt_p95} / ${r.dt_max} | ${r.long} | ${r.long_run} | ${r.js_mean} / ${r.js_p95} / ${r.js_max} | ${r.mpx} |`,
        )
        .join('\n'),
  )
  .join('\n\n');
writeFileSync(join(OUT, 'data', 'frame-rates.md'), md + '\n');
console.log(md);
if (GPU) {
  const bad = Object.values(result).flatMap((p) =>
    p.rows.filter((r) => r.long_run >= 2 && !r.effect.startsWith('reference')).map((r) => `${p.label}: ${r.effect} dropped ${r.long_run} frames in a row`),
  );
  if (bad.length) {
    console.error(bad.join('\n'));
    process.exit(1);
  }
}
