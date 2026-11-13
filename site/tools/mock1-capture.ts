/**
 * MOCK1: the screen captures of the tour for the owner, at a phone size and at 1280: one per reveal concept (the door,
 * the way in, the reveal), one of the close-up and the wheel's swap, one of the style change.
 *
 *   tsx tools/mock1-capture.ts <out dir>      against `npm run preview` (HD_BASE_URL, default http://127.0.0.1:8788)
 *
 * How they are made, and what they are: this machine has no GPU, so the browser cannot draw the tour at 60 frames a
 * second in real time (tools/mock1-fps.ts says how far it is). The page is therefore recorded in slow motion (every
 * duration of the tour stretched by SLOW, the evidence's `__hdSlowMo`), and the recording is brought back to real speed
 * at 60 fps (ffmpeg setpts). The film plays at the tour's real speed, uncropped; its smoothness is the design's, not a
 * measurement of this machine or of a phone. The frame-rate table is the measurement.
 */
import { chromium, devices, type BrowserContext, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const OUT = join(process.argv[2] ?? 'test-results/mock1', 'captures');
const BASE = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';
const TOUR = process.env.HD_TOUR_URL ?? `${BASE}/tour/`;
const ONLY = process.env.HD_CAPTURE_ONLY?.split(',') ?? null;
const executablePath = process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium';
const args = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'];
const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
const PROFILES = [
  { id: '1280', context: { viewport: { width: 1280, height: 720 } }, size: { width: 1280, height: 720 }, up: 1, slow: 5, slot: 'vase' },
  // the phone's own screen (412 × 839 CSS px). The browser films a page at one pixel per CSS px, whatever the screen's
  // density (a larger film size only pads it), so the phone film is doubled afterwards: softer than the phone itself
  { id: 'phone', context: pixel, size: { ...pixel.viewport }, up: 2, slow: 8, slot: 'framed-art' },
] as const;
type Profile = (typeof PROFILES)[number];

mkdirSync(OUT, { recursive: true });
const tmp = mkdtempSync(join(tmpdir(), 'mock1-'));
const browser = await chromium.launch({ executablePath, args });

/** records `scene` in slow motion and writes it at real speed; the film starts where the scene calls `begin` */
async function film(
  p: Profile,
  name: string,
  query: string,
  scene: (page: Page, s: { begin: () => void; hold: (ms: number) => Promise<void>; rest: (phase?: 'door' | 'room') => Promise<unknown> }) => Promise<void>,
) {
  if (ONLY && !ONLY.some((o) => name.includes(o))) return;
  const ctx: BrowserContext = await browser.newContext({ ...p.context, locale: 'he-IL', recordVideo: { dir: tmp, size: p.size } });
  await ctx.addInitScript((k) => ((window as unknown as { __hdSlowMo: number }).__hdSlowMo = k), p.slow);
  // tsx (esbuild) wraps named functions in a helper the page does not have
  await ctx.addInitScript({ content: 'globalThis.__name = (f) => f;' });
  const t0 = Date.now();
  const page = await ctx.newPage();
  let from = 0;
  await page.goto(TOUR + query);
  await page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
  // everything the scene shows is loaded before it starts: a film of the tour, not of this machine's disk
  await page.evaluate(async () => {
    const e = window.__hdTour!;
    await e.products();
    await e.otherHouse();
    for (const id of Object.keys(e.selection)) for (const o of e.slot(id).options) await e.option(id, o.position);
  });
  await scene(page, {
    begin: () => (from = (Date.now() - t0) / 1000),
    hold: (ms) => page.waitForTimeout(ms * p.slow),
    rest: (phase = 'room') =>
      page.waitForFunction((ph) => window.__hdTourState?.phase === ph && window.__hdTourState.busy === false, phase, { timeout: 300_000 }),
  });
  const to = (Date.now() - t0) / 1000;
  const video = page.video()!;
  await ctx.close();
  const out = join(OUT, `mock1-${name}-${p.id}.mp4`);
  execFileSync(
    'ffmpeg',
    [
      '-y',
      '-loglevel',
      'error',
      '-ss',
      from.toFixed(2),
      '-to',
      to.toFixed(2),
      '-i',
      await video.path(),
      '-vf',
      `setpts=PTS/${p.slow},fps=60,scale=trunc(iw*${p.up}/2)*2:trunc(ih*${p.up}/2)*2:flags=lanczos`,
      '-an',
      '-c:v',
      'libx264',
      '-preset',
      'slow',
      '-crf',
      '27',
      '-pix_fmt',
      'yuv420p',
      '-movflags',
      '+faststart',
      out,
    ],
    { stdio: 'inherit' },
  );
  console.log(`${out}: ${((to - from) / p.slow).toFixed(1)} s, ${(statSync(out).size / 1048576).toFixed(2)} MB`);
}

for (const p of PROFILES) {
  // HD_CAPTURE_PROFILE=phone (or 1280): one size only
  if (process.env.HD_CAPTURE_PROFILE && process.env.HD_CAPTURE_PROFILE !== p.id) continue;
  // 1–3: the door, the way in and the reveal, once per concept
  for (const fx of ['a', 'b', 'c'] as const)
    await film(p, `reveal-${fx}`, `?fx=${fx}`, async (page, s) => {
      s.begin();
      await s.hold(1400);
      await page.locator('#tour-enter').click();
      await s.rest();
      await s.hold(1800);
    });
  // 4: the close-up and the wheel: every option of the slot, and back; then the choice and the way out
  await film(p, 'closeup-wheel', '?skip=1', async (page, s) => {
    await s.rest();
    s.begin();
    await s.hold(700);
    await page.locator(`.tour-spot[data-slot="${p.slot}"]`).click({ force: true });
    await page.getByRole('dialog').waitFor({ timeout: 300_000 });
    await s.rest();
    await s.hold(700);
    const n = await page.evaluate((id) => window.__hdTour!.slot(id).options.length, p.slot);
    for (const key of [...Array<string>(n - 1).fill('ArrowLeft'), ...Array<string>(n - 1).fill('ArrowRight'), 'ArrowLeft']) {
      await page.keyboard.press(key);
      await s.hold(1250);
    }
    await page.keyboard.press('Enter');
    await s.rest();
    await s.hold(1500);
  });
  // 5: the style change: the first time (Y1, strip and dress) to the Nordic house and back, then the repeat (Y2, the wave)
  await film(p, 'style-change', '?skip=1&st=y1', async (page, s) => {
    await s.rest();
    s.begin();
    await s.hold(800);
    const to = async (house: 'nordic' | 'warm-modern') => {
      await page.locator(`.segmented button[data-house="${house}"]`).click();
      await page.waitForFunction((h) => window.__hdTourState?.house === h && window.__hdTourState.busy === false, house, { timeout: 300_000 });
      await s.hold(1500);
    };
    await to('nordic');
    await to('warm-modern');
    await page.evaluate(() => (document.querySelector<HTMLInputElement>('input[name="tour-st"][value="y2"]')!.click(), undefined));
    await to('nordic');
    await to('warm-modern');
  });
}
await browser.close();
rmSync(tmp, { recursive: true, force: true });
