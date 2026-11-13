/**
 * MOCK3, the evidence (qa/reports/2026-11-07-site-track/mock3/screens): the tour at a phone held upright (390×844), a
 * phone on its side (844×390) and a wide screen (1440×900) — the door, the room at rest, zoomed, the close-up with the
 * wheel, and the panel of "המשך הסיור" open; and the temporary switches on the phone.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-tour3.spec.ts`, against
 * the local build (npm run preview).
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { test, type Browser, type Page } from '@playwright/test';

const DIR = process.env.HD_SHOTS_DIR ?? '';
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 300_000 });

const SIZES = [
  { name: '390x844-portrait', width: 390, height: 844, dpr: 3, touch: true },
  { name: '844x390-landscape', width: 844, height: 390, dpr: 3, touch: true },
  { name: '1440x900-desktop', width: 1440, height: 900, dpr: 1, touch: false },
] as const;
type Size = (typeof SIZES)[number];
const ready = (page: Page) => page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60_000 });
const atRest = (page: Page, phase: 'door' | 'room' = 'room') =>
  page.waitForFunction((p) => window.__hdTourState?.phase === p && window.__hdTourState.busy === false, phase, { timeout: 120_000 });
const settle = (page: Page, ms = 500) => page.waitForTimeout(ms);
async function shot(page: Page, name: string) {
  mkdirSync(join(DIR, 'screens'), { recursive: true });
  await page.screenshot({ path: join(DIR, 'screens', `${name}.jpg`), type: 'jpeg', quality: 86 });
}
const open = (browser: Browser, s: Size) =>
  browser.newContext({ locale: 'he-IL', viewport: { width: s.width, height: s.height }, deviceScaleFactor: s.dpr, hasTouch: s.touch, isMobile: s.touch });
/** where the window and everything round it sit, for the README's numbers */
const boxes = (page: Page) =>
  page.evaluate(() => {
    const r = (sel: string) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const b = el.getBoundingClientRect();
      return { x: +b.x.toFixed(1), y: +b.y.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) };
    };
    return {
      viewport: { w: innerWidth, h: innerHeight },
      window: r('.tour-win'),
      top: r('.tour-top'),
      strip: r('.tour-strip'),
      fold: r('#tour-fold'),
      zoom: r('#tour-zoom'),
    };
  });

for (const s of SIZES) {
  test(`the tour at ${s.name}`, async ({ browser }) => {
    const ctx = await open(browser, s);
    const page = await ctx.newPage();
    await page.goto('/tour/');
    await ready(page);
    await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 120_000 });
    await settle(page, 800);
    await shot(page, `${s.name}-1-door`);
    const layout: Record<string, unknown> = { door: await boxes(page) };
    await page.locator('#tour-enter').click();
    await atRest(page);
    await settle(page, 1200);
    await shot(page, `${s.name}-2-room`);
    layout.room = await boxes(page);
    if (s.touch) {
      await page.locator('#tour-zoom').click();
      await atRest(page);
      await settle(page);
      await shot(page, `${s.name}-3-zoomed`);
      await page.locator('#tour-zoom').click();
      await atRest(page);
      await settle(page);
      await page.locator('.tour-tile[data-slot="vase"]').click();
    } else await page.locator('.tour-spot[data-slot="vase"]').click();
    await page.getByRole('dialog').waitFor();
    await atRest(page);
    await settle(page, 700);
    await shot(page, `${s.name}-4-closeup-wheel`);
    await page.keyboard.press('Escape');
    await atRest(page);
    await settle(page);
    await page.locator('#tour-fold').click();
    await settle(page, 900);
    await shot(page, `${s.name}-5-panel`);
    mkdirSync(join(DIR, 'data'), { recursive: true });
    writeFileSync(join(DIR, 'data', `layout-${s.name}.json`), JSON.stringify(layout, null, 1));
    await ctx.close();
  });
}

test('the phone: the temporary switches', async ({ browser }) => {
  const s = SIZES[0];
  for (const [name, query] of [
    ['fill', 'frame=fill'],
    ['dots', 'pick=dots'],
    ['dark', 'bg=dark'],
  ] as const) {
    const ctx = await open(browser, s);
    const page = await ctx.newPage();
    await page.goto(`/tour/?skip=1&${query}`);
    await ready(page);
    await atRest(page);
    await settle(page, 1200);
    await shot(page, `${s.name}-switch-${name}`);
    await ctx.close();
  }
});

/**
 * The sharpness of a zoomed picture on a phone (the brief's item 11). A phone composes the room at 1920; this compares
 * what the window shows at ×2, ×2.5 and ×4 (the close-up of a small product) with the same view composed from the
 * 2720 layers, at two phones' pixel ratios and in two places of the room. Three renderings of every view:
 *   a. as shipped: composed at 1920, the canvas at twice the CSS pixels (the engine's cap);
 *   b. the switch "חדות בזום": composed at 1920, the canvas at the screen's own pixels;
 *   c. the reference: composed at 2720, the canvas at the screen's own pixels.
 * The numbers: the detail in the picture (the mean absolute Laplacian of its luminance) as a share of the reference's,
 * and how far the pixels are from the reference's. The crops are saved side by side, a | b | c.
 */
test('sharpness when zoomed on a phone: composed at 1920, against 2720', async ({ browser }) => {
  const sharp = (await import('sharp')).default;
  const PHONES = [
    { name: 'dpr2.6-412', width: 412, height: 915, dpr: 2.625 },
    { name: 'dpr3-390', width: 390, height: 844, dpr: 3 },
  ];
  const VIEWS = [
    { name: 'textiles', u: 0.72, v: 0.72 },
    { name: 'art-and-lamp', u: 0.64, v: 0.42 },
  ];
  const ZOOMS = [2, 2.5, 4];
  const MODES = [
    { key: 'a', query: '', cap: 2 },
    { key: 'b', query: '', cap: 3 },
    { key: 'c', query: '&w=hi', cap: 3 },
  ] as const;
  type Shot = { data: Buffer; w: number; h: number };
  const grey = async (png: Buffer): Promise<Shot> => {
    const { data, info } = await sharp(png).greyscale().raw().toBuffer({ resolveWithObject: true });
    return { data, w: info.width, h: info.height };
  };
  const detail = (s: Shot): number => {
    let sum = 0;
    for (let y = 1; y < s.h - 1; y++)
      for (let x = 1; x < s.w - 1; x++) {
        const i = y * s.w + x;
        sum += Math.abs(4 * s.data[i]! - s.data[i - 1]! - s.data[i + 1]! - s.data[i - s.w]! - s.data[i + s.w]!);
      }
    return sum / ((s.w - 2) * (s.h - 2));
  };
  const apart = (a: Shot, b: Shot) => {
    const d: number[] = [];
    for (let i = 0; i < a.data.length; i++) d.push(Math.abs(a.data[i]! - b.data[i]!));
    d.sort((x, y) => x - y);
    return { mean: +(d.reduce((x, y) => x + y, 0) / d.length).toFixed(2), p99: d[Math.floor(d.length * 0.99)]! };
  };
  const rows: Record<string, unknown>[] = [];
  const memory: Record<string, unknown> = {};
  for (const ph of PHONES) {
    const shots = new Map<string, Buffer>();
    for (const m of MODES) {
      const ctx = await browser.newContext({
        locale: 'he-IL',
        viewport: { width: ph.width, height: ph.height },
        deviceScaleFactor: ph.dpr,
        hasTouch: true,
        isMobile: true,
      });
      const page = await ctx.newPage();
      await page.goto(`/tour/?skip=1${m.query}`);
      await ready(page);
      await atRest(page);
      // the picture alone: the marks are taken off it for the comparison
      await page.evaluate(() => document.querySelectorAll<HTMLElement>('.tour-spots, .tour-rings').forEach((el) => (el.style.display = 'none')));
      memory[`${ph.name} ${m.key}`] = await page.evaluate((cap) => {
        const e = window.__hdTour! as unknown as { setDprCap(c: number): void; gl: { width: number; vram: number } };
        e.setDprCap(cap);
        const c = document.querySelector('canvas.room-canvas') as HTMLCanvasElement;
        return {
          composed_at: e.gl.width,
          textures_mb: +(e.gl.vram / 1048576).toFixed(1),
          canvas: `${c.width}×${c.height}`,
          canvas_mb: +((c.width * c.height * 4) / 1048576).toFixed(2),
        };
      }, m.cap);
      for (const z of ZOOMS)
        for (const v of VIEWS) {
          await page.evaluate(
            ([u, vv, zz]) => {
              const e = window.__hdTour! as unknown as { cam: { cu: number; cv: number; z: number }; render(): number };
              const h = 1 / (2 * zz!);
              e.cam = { cu: Math.min(1 - h, Math.max(h, u!)), cv: Math.min(1 - h, Math.max(h, vv!)), z: zz! };
              e.render();
            },
            [v.u, v.v, z] as const,
          );
          await page.waitForTimeout(150);
          shots.set(`${m.key} ${z} ${v.name}`, await page.locator('.tour-win').screenshot());
        }
      await ctx.close();
    }
    mkdirSync(join(DIR, 'screens'), { recursive: true });
    for (const z of ZOOMS)
      for (const v of VIEWS) {
        const [a, b, c] = await Promise.all(MODES.map((m) => grey(shots.get(`${m.key} ${z} ${v.name}`)!)));
        const ref = detail(c!);
        rows.push({
          phone: ph.name,
          zoom: z,
          view: v.name,
          detail_as_shipped: +(detail(a!) / ref).toFixed(3),
          detail_with_the_switch: +(detail(b!) / ref).toFixed(3),
          from_reference_as_shipped: apart(a!, c!),
          from_reference_with_the_switch: apart(b!, c!),
        });
        // the middle of the window, 1 : 1 in the screen's own pixels: a | b | c
        const meta = await sharp(shots.get(`a ${z} ${v.name}`)!).metadata();
        const side = Math.min(340, meta.height! - 2);
        const cut = { left: Math.round((meta.width! - side) / 2), top: Math.round((meta.height! - side) / 2), width: side, height: side };
        const parts = await Promise.all(
          MODES.map((m) =>
            sharp(shots.get(`${m.key} ${z} ${v.name}`)!)
              .extract(cut)
              .png()
              .toBuffer(),
          ),
        );
        await sharp({ create: { width: side * 3 + 16, height: side, channels: 3, background: '#f4f1ec' } })
          .composite(parts.map((input, i) => ({ input, left: i * (side + 8), top: 0 })))
          .webp({ lossless: true, effort: 6 })
          .toFile(join(DIR, 'screens', `sharp-${ph.name}-x${z}-${v.name}.webp`));
      }
  }
  mkdirSync(join(DIR, 'data'), { recursive: true });
  writeFileSync(
    join(DIR, 'data', 'sharpness.json'),
    JSON.stringify(
      {
        modes: {
          a: 'composed at 1920, canvas at ×2 (as shipped)',
          b: 'composed at 1920, canvas at the screen’s pixels (the switch)',
          c: 'composed at 2720, canvas at the screen’s pixels (the reference)',
        },
        memory,
        rows,
      },
      null,
      1,
    ),
  );
});

/**
 * The Artifact preview (site/dist-artifact, `npm run preview:artifact`) as the owner opens it on his phone: served as
 * the Artifact host serves it (the page wrapped in a document, its media beside it), walked from the door to the panel.
 * No page error, no request that fails, nothing fetched from anywhere but the preview itself and Google Fonts.
 */
test('the Artifact preview on a phone: the door, the room, a close-up, the panel', async ({ browser }) => {
  const { spawn } = await import('node:child_process');
  const { existsSync, readFileSync } = await import('node:fs');
  const out = join(process.cwd(), 'dist-artifact');
  test.skip(!existsSync(join(out, 'index.html')), 'run npm run preview:artifact first');
  const PORT = 5197;
  const ORIGIN = `http://127.0.0.1:${PORT}`;
  const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '-d', out], { stdio: 'ignore' });
  try {
    await new Promise((r) => setTimeout(r, 900));
    const wrapped = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>${readFileSync(join(out, 'index.html'), 'utf8')}</body></html>`;
    const problems: string[] = [];
    let bytes = 0;
    for (const s of [SIZES[0], SIZES[1]]) {
      const ctx = await open(browser, s);
      const page = await ctx.newPage();
      page.on('pageerror', (e) => problems.push(`${s.name} pageerror: ${e.message}`));
      page.on('requestfailed', (r) => !/fonts\.(googleapis|gstatic)/.test(r.url()) && problems.push(`${s.name} failed: ${r.url()}`));
      page.on('response', (r) => {
        if (r.status() >= 400 && r.url().startsWith(ORIGIN)) problems.push(`${s.name} ${r.status()}: ${r.url()}`);
        if (s === SIZES[0] && r.url().startsWith(ORIGIN))
          void r.body().then(
            (b) => (bytes += b.length),
            () => undefined,
          );
      });
      page.on('request', (r) => {
        const u = new URL(r.url());
        if (u.origin !== ORIGIN && u.protocol.startsWith('http') && !/^fonts\.(googleapis|gstatic)\.com$/.test(u.hostname))
          problems.push(`${s.name} external: ${r.url()}`);
      });
      await page.route(`${ORIGIN}/`, (route) => route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: wrapped }));
      await page.goto(`${ORIGIN}/`);
      await ready(page);
      await page.waitForFunction(() => window.__hdTour?.warmReady === true, undefined, { timeout: 120_000 });
      await page.locator('#tour-enter').click();
      await atRest(page);
      await settle(page, 1000);
      await shot(page, `artifact-${s.name}-room`);
      const w = (await boxes(page)).window!;
      if (Math.abs(w.w / w.h - 16 / 9) > 0.02) problems.push(`${s.name}: the window is ${w.w}×${w.h}`);
      await page.locator('.tour-tile[data-slot="vase"]').click();
      await page.getByRole('dialog').waitFor();
      await atRest(page);
      await settle(page, 600);
      await shot(page, `artifact-${s.name}-closeup`);
      await page.keyboard.press('Escape');
      await atRest(page);
      await page.locator('#tour-fold').click();
      await settle(page, 800);
      // "קנה את המראה" in the preview goes to the list under the tour (the style's magazine page is not in it)
      if ((await page.locator('#tour-look').getAttribute('href')) !== '#tour-items') problems.push(`${s.name}: the look's link`);
      await ctx.close();
    }
    mkdirSync(join(DIR, 'data'), { recursive: true });
    writeFileSync(join(DIR, 'data', 'artifact-walk.json'), JSON.stringify({ problems, phone_bytes_until_the_panel: bytes }, null, 1));
    if (problems.length) throw new Error(problems.join('\n'));
  } finally {
    server.kill();
  }
});
