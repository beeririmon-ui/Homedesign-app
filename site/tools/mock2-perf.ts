/**
 * MOCK2 (2026-11-13), FB1: what every effect of the tour costs, and what it interrupts.
 *
 *   tsx tools/mock2-perf.ts <out dir> [--old]    against `npm run preview` (HD_BASE_URL, default 127.0.0.1:8788)
 *
 * Two profiles: a desktop (1280 × 720) and a mid-range phone (Pixel 7's screen, the CPU throttled ×4). Each effect is
 * run on its own, at its real speed, with the page's own marks running over it, and the engine's own counters are read
 * back (web/src/tour/metrics.ts): decodes, texture uploads, shader compiles, GPU read-backs and layout measurements
 * inside the effect, beside the frame intervals, the script time per frame and the pixels composed.
 *
 * What the numbers are: this machine has no GPU, and Chromium draws WebGL in software (SwiftShader). The interval
 * between frames here is the cost of rasterising the canvas on a CPU, not of the page's code. What carries over to a
 * real phone is the script time per frame under the ×4 throttle, the pixels composed, the memory the textures hold,
 * and every counter above: those are the page's own work, and they are what this sprint changed. The owner's own
 * reading is the "העתקת דוח" button on his phone.
 *
 * `--old` measures the same effects with the sprint's fixes turned off (?mock2=off), for the before-and-after table.
 */
import { chromium, devices, type Page } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const OUT = process.argv[2] ?? 'test-results/mock2';
const OLD = process.argv.includes('--old');
const BASE = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';
const TOUR = `${BASE}/tour/${OLD ? '?mock2=off' : ''}`;
const executablePath = process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium';
const GPU = process.env.HD_GPU === '1';
const args = GPU ? [] : ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'];
const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
const PROFILES = [
  { id: 'desktop', label: 'desktop 1280 × 720', context: { viewport: { width: 1280, height: 720 } }, throttle: 1 },
  { id: 'phone', label: 'phone (Pixel 7 screen, CPU ×4)', context: pixel, throttle: 4 },
] as const;

type Counts = { decode: number; upload: number; compile: number; readback: number; layout: number };
type Stat = {
  label: string;
  frames: number;
  fps: number;
  dt_p50: number;
  dt_p95: number;
  dt_max: number;
  long20: number;
  long34: number;
  long_run: number;
  js_mean: number;
  js_p95: number;
  js_max: number;
  step_mean: number;
  step_p95: number;
  step_max: number;
  step_over8: number;
  mpx: number;
  min_scale: number;
  counts: Counts;
};
type Run = { stats: Stat[]; width: number; vram: number; canvas: string; totals: Record<string, number> };

/** every effect of the tour, one after the other, each at its real speed */
async function tourRun(page: Page): Promise<Run> {
  await page.goto(TOUR);
  await page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 120_000 });
  return page.evaluate(async () => {
    const e = window.__hdTour!;
    const m = window.__hdTourFx!;
    const ui = m.ui;
    const rest = () => new Promise((r) => setTimeout(r, 400));
    const px = (name: string) => parseFloat(getComputedStyle(document.querySelector('.tour')!).getPropertyValue(name));
    const door = { cx: px('--dx'), cy: px('--dy'), hw: px('--dw') / 2, hh: px('--dh') / 2, r: px('--dr') };
    // the room is made ready first: the door waits for exactly this before it opens
    await e.whenWarm();
    await e.otherHouse();
    const vase = e.slot('vase');
    for (const o of vase.options) await e.option('vase', o.position);
    await rest();
    const metrics = m.metrics;
    metrics.reset();
    await m.enter(e);
    for (const k of ['a', 'b', 'c'] as const) {
      await rest();
      await m.reveal(e, ui, k);
      await rest();
      await m.collect(e, ui);
    }
    await m.reveal(e, ui, 'b');
    await rest();
    const b = vase.options[0]!.box;
    await e.moveCam('zoom-in', e.camFor([b[0] - 0.02, b[1] + 0.02, b[2] - 0.05, b[3] + 0.05], 0.5), 1000, (k) => {
      e.d.vig = 0.1 * k;
      e.d.vigBox = vase.rect;
    });
    for (const [to, dir, kind] of [
      [2, 1, 's1'],
      [3, 1, 's2'],
      [1, -1, 's3'],
    ] as const) {
      await rest();
      await m.swap(e, ui, vase, to, dir, kind);
    }
    await rest();
    await e.moveCam('zoom-out', e.rest, 1000, (k) => (e.d.vig = 0.1 * (1 - k)));
    for (const [to, kind] of [
      ['nordic', 'y1'],
      ['warm-modern', 'y1'],
      ['nordic', 'y2'],
      ['warm-modern', 'y2'],
    ] as const) {
      await rest();
      await m.style(e, ui, to, kind, 'b');
    }
    await rest();
    await m.collect(e, ui);
    await m.leave(e, door);
    const canvas = document.querySelector('canvas.room-canvas') as HTMLCanvasElement;
    return {
      stats: metrics.order.map((l: string) => metrics.effects[l]!),
      width: e.gl.width,
      vram: e.gl.vram,
      canvas: `${canvas.width}×${canvas.height}`,
      totals: metrics.total as unknown as Record<string, number>,
    };
  });
}

const browser = await chromium.launch({ executablePath, args });
const result: Record<string, { label: string; run: Run }> = {};
for (const p of PROFILES) {
  const ctx = await browser.newContext({ ...p.context, locale: 'he-IL' });
  // tsx (esbuild) wraps named functions in a helper the page does not have
  await ctx.addInitScript({ content: 'globalThis.__name = (f) => f;' });
  const page = await ctx.newPage();
  if (p.throttle > 1) await (await ctx.newCDPSession(page)).send('Emulation.setCPUThrottlingRate', { rate: p.throttle });
  result[p.id] = { label: p.label, run: await tourRun(page) };
  await ctx.close();
}
await browser.close();

mkdirSync(join(OUT, 'data'), { recursive: true });
const name = OLD ? 'frames-before' : 'frames-after';
writeFileSync(
  join(OUT, 'data', `${name}.json`),
  JSON.stringify({ gpu: GPU, mock2: !OLD, renderer: GPU ? 'the machine’s GPU' : 'SwiftShader (software, no GPU)', profiles: result }, null, 1),
);
const md = Object.values(result)
  .map((p) => {
    const r = p.run;
    const head =
      `### ${p.label}\n\n` +
      `composition ${r.width} px wide, canvas ${r.canvas}, the room's textures and targets ${(r.vram / 1048576).toFixed(1)} MB\n\n` +
      `| effect | frames | fps | frame p50 / p95 / max (ms) | > 20 / > 34 ms | longest run | the effect's own script: mean / p95 / max (ms) | the whole frame's script: mean / max (ms) | composed per frame (MP) | min scale | decode / upload / compile / read-back / layout |\n` +
      `| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n`;
    return (
      head +
      r.stats
        .map(
          (s) =>
            `| ${s.label} | ${s.frames} | ${s.fps} | ${s.dt_p50} / ${s.dt_p95} / ${s.dt_max} | ${s.long20} / ${s.long34} | ${s.long_run} | ` +
            `${s.step_mean} / ${s.step_p95} / ${s.step_max} | ${s.js_mean} / ${s.js_max} | ${s.mpx} | ${s.min_scale} | ` +
            `${s.counts.decode} / ${s.counts.upload} / ${s.counts.compile} / ${s.counts.readback} / ${s.counts.layout} |`,
        )
        .join('\n')
    );
  })
  .join('\n\n');
writeFileSync(join(OUT, 'data', `${name}.md`), md + '\n');
console.log(md);

// the gate: nothing may interrupt an effect, whatever the machine's frame rate is
const bad = Object.values(result).flatMap((p) =>
  p.run.stats
    .filter((s) => s.counts.decode + s.counts.upload + s.counts.compile + s.counts.readback + s.counts.layout > 0)
    .map((s) => `${p.label}: ${s.label} was interrupted (${JSON.stringify(s.counts)})`),
);
if (GPU)
  bad.push(
    ...Object.values(result).flatMap((p) =>
      p.run.stats.filter((s) => s.long_run >= 2).map((s) => `${p.label}: ${s.label} dropped ${s.long_run} frames in a row`),
    ),
  );
if (bad.length && !OLD) {
  for (const b of bad) console.error(b);
  process.exit(1);
}
