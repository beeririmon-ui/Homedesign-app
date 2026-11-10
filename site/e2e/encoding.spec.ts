/**
 * S12, QA S8–S10 §4 (S10 question 4): the tool-layer encoding threshold, checked on the build as the browser draws it.
 * QA's method (qa/reports/2026-11-10-site-track-qa-s8-s10/tools/base-quality.mjs): the same page is drawn twice per view,
 * once with the layer's requests answered by the approved pixels (the encoder's own resize, lossless) and once by the
 * file the build made, and the two canvases are compared (tools/lib/encoding.ts: p99 ≤ 6, p99.9 ≤ 10, ≤ 0.2% above 8
 * levels, ΔE00 p99 ≤ 3.5), at QA's five views.
 *  - **warm-modern:** the base (AVIF, and the WebP fallback), and the default set's product layer inside its own area.
 *  - **Nordic:** the base, reported per view. Its layers are temporary (the preview render until the final layers pass QA).
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, type Browser, type Page, type Route } from '@playwright/test';
import sharp from 'sharp';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { VIEWS, failures, measure, type Measure, type View } from '../tools/lib/encoding';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = resolve(SITE, '..');
const BASE_URL = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';
type Box = [number, number, number, number];

// ---------- the approved pixels ----------
const wm = JSON.parse(readFileSync(resolve(SITE, 'tools/house/living-room.warm-modern.json'), 'utf8')) as {
  pilot: string;
  layers_dir: string;
  approved: { composites: Record<string, string> };
  sets: { id: string }[];
  slot: { id: string };
};
const lay = join(REPO, wm.pilot, wm.layers_dir);
const LAYERED = existsSync(join(lay, 'base.png'));
const wmBase = LAYERED ? join(lay, 'base.png') : join(REPO, wm.pilot, wm.approved.composites[wm.sets[0]!.id]!);
const house = JSON.parse(readFileSync(resolve(SITE, '.generated/house.living-room.warm-modern.json'), 'utf8')) as {
  scene: { aspect: number; slots: Record<string, { product: { rect: Box; src: string[] } }> };
};
const temp = JSON.parse(readFileSync(resolve(SITE, 'tools/temp/living-room.nordic.json'), 'utf8')) as { source_manifest_id: string };
const assets = JSON.parse(readFileSync(resolve(REPO, 'assets/manifest.json'), 'utf8')) as { assets: { id: string; path: string }[] };
const nordicSource = resolve(REPO, assets.assets.find((a) => a.id === temp.source_manifest_id)!.path);

const refCache = new Map<string, Promise<Buffer>>();
/** the encoder's input at that width, as a lossless PNG (make-house: removeAlpha + resize; make-temp-assets: resize) */
function reference(source: string, width: number, removeAlpha: boolean): Promise<Buffer> {
  const key = `${source}@${width}`;
  let p = refCache.get(key);
  if (!p) {
    const img = sharp(source);
    refCache.set(key, (p = (removeAlpha ? img.removeAlpha() : img).resize({ width }).png({ compressionLevel: 1 }).toBuffer()));
  }
  return p;
}
/** the default set's product layer, losslessly: make-house's cut of the approved set, at the layer's width */
async function productReference(width: number): Promise<Buffer> {
  const src = LAYERED ? join(lay, `cushions-set-${wm.sets[0]!.id}.png`) : join(REPO, wm.pilot, wm.approved.composites[wm.sets[0]!.id]!);
  const rect = house.scene.slots[wm.slot.id]!.product.rect;
  const W = 2720;
  const H = 1530;
  const cut = {
    left: Math.round(rect[0] * W),
    top: Math.round(rect[2] * H),
    width: Math.round((rect[1] - rect[0]) * W),
    height: Math.round((rect[3] - rect[2]) * H),
  };
  return sharp(src).ensureAlpha().extract(cut).resize({ width }).png({ compressionLevel: 1 }).toBuffer();
}

// ---------- one drawing of the stage ----------
type Answer = (route: Route, m: RegExpExecArray) => Promise<void>;
async function capture(browser: Browser, url: string, v: View, answers: [RegExp, Answer][], slot?: string) {
  const ctx = await browser.newContext({
    baseURL: BASE_URL,
    locale: 'he-IL',
    viewport: { width: v.w, height: v.h },
    deviceScaleFactor: v.dpr,
    isMobile: v.dpr > 1,
    hasTouch: v.dpr > 1,
    reducedMotion: 'reduce',
  });
  const page = await ctx.newPage();
  for (const [re, answer] of answers)
    await page.route(re, async (route) => {
      const m = re.exec(new URL(route.request().url()).pathname);
      if (m) await answer(route, m);
      else await route.continue();
    });
  await page.goto(url);
  await expect(page.locator('section.stage')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
  const sb = (await page.locator('section.stage').boundingBox())!;
  await page.mouse.click(sb.x + 20, sb.y + sb.height / 2);
  await expect.poll(() => page.evaluate(() => window.__hdEngine?.ready ?? false), { timeout: 30_000 }).toBe(true);
  if (v.zoom && slot) {
    await page.locator(`button.hotspot[data-slot="${slot}"]`).focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('dialog')).toBeVisible({ timeout: 15_000 });
    await settle(page);
    await hide(page, '[role="dialog"], .wheel, .wheel-wrap');
  }
  await hide(page, '.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back, .stage-vignette');
  await page.mouse.move(0, 0);
  await settle(page);
  const shot = await page.locator('canvas.room-canvas').screenshot();
  const eng = await page.evaluate(() => {
    const e = window.__hdEngine!;
    return { cam: { ...e.cam }, vp: { ...e.vp } };
  });
  await ctx.close();
  const { data, info } = await sharp(shot).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, eng };
}
/** the page's CSP allows no style element: the controls are hidden through their style attribute */
const hide = (page: Page, sel: string) =>
  page.evaluate((s) => document.querySelectorAll<HTMLElement>(s).forEach((el) => (el.style.visibility = 'hidden')), sel);
/** waits until the engine has drawn its last frame (no animation left), never a fixed time */
const settle = (page: Page) =>
  expect
    .poll(
      () =>
        page.evaluate(
          () =>
            new Promise<boolean>((res) =>
              requestAnimationFrame(() => {
                const e = window.__hdEngine as unknown as { anims?: Set<unknown> };
                res(!e.anims || e.anims.size === 0);
              }),
            ),
        ),
      { timeout: 15_000 },
    )
    .toBe(true);

const file = (rel: string) => readFileSync(resolve(SITE, 'web/public/media', rel));
const fulfil = (route: Route, body: Buffer, contentType: string) => route.fulfill({ status: 200, contentType, body, headers: { 'cache-control': 'no-store' } });
const fmt = (m: Measure) => `${m.p99}/${m.p999}/${m.max} · ${(m.over8 * 100).toFixed(2)}% · ΔE ${m.de00_p99}`;
const evidence: Record<string, Record<string, Measure & { pass: boolean }>> = {};
const note = (layer: string, view: string, m: Measure) => ((evidence[layer] ??= {})[view] = { ...m, pass: failures(m).length === 0 });

/** the stage pixels inside a frame rectangle (u0 u1 v0 v1), through the engine's camera */
function within(c: { w: number; h: number; eng: { cam: { cu: number; cv: number; z: number }; vp: { w: number; h: number } } }, rect: Box, aspect: number) {
  const k = c.w / c.eng.vp.w;
  const fw = Math.max(c.eng.vp.w, c.eng.vp.h * aspect) * c.eng.cam.z;
  const fh = fw / aspect;
  const x = (u: number) => Math.round((c.eng.vp.w / 2 + (u - c.eng.cam.cu) * fw) * k);
  const y = (v: number) => Math.round((c.eng.vp.h / 2 + (v - c.eng.cam.cv) * fh) * k);
  return { x0: Math.max(0, x(rect[0])), x1: Math.min(c.w, x(rect[1])), y0: Math.max(0, y(rect[2])), y1: Math.min(c.h, y(rect[3])) };
}
const crop = (d: Buffer, w: number, b: { x0: number; x1: number; y0: number; y1: number }) => {
  const out = Buffer.alloc((b.x1 - b.x0) * (b.y1 - b.y0) * 4);
  for (let y = b.y0; y < b.y1; y++) d.copy(out, (y - b.y0) * (b.x1 - b.x0) * 4, (y * w + b.x0) * 4, (y * w + b.x1) * 4);
  return out;
};

test.describe('the tool-layer encoding threshold (S12, QA S8–S10 §4), as the browser draws it', () => {
  test.describe.configure({ timeout: 600_000 });

  test('warm-modern: the base (AVIF q70 and its WebP fallback) and the default set’s layer meet it in every view', async ({ browser }) => {
    const BASE = /\/media\/house\/living-room\/warm-modern\/M0\/base\/shell\.(\d+)\.(avif|webp)$/;
    const PRODUCT = /\/media\/house\/living-room\/warm-modern\/M0\/slots\/[a-z-]+\/1\.product\.(\d+)\.webp$/;
    const refBase: Answer = async (r, m) => fulfil(r, await reference(wmBase, Number(m[1]), true), 'image/png');
    const refProduct: Answer = async (r, m) =>
      fulfil(
        r,
        await productReference(Math.round(Number(m[1]) * (house.scene.slots[wm.slot.id]!.product.rect[1] - house.scene.slots[wm.slot.id]!.product.rect[0]))),
        'image/png',
      );
    // the WebP fallback: the engine asks for the AVIF where the browser decodes it; here it is answered with the WebP
    const webpBase: Answer = async (r, m) => fulfil(r, file(`house/living-room/warm-modern/M0/base/shell.${m[1]}.webp`), 'image/webp');
    const url = '/rooms/living-room/?style=warm-modern';
    const bad: string[] = [];
    for (const v of VIEWS) {
      const ref = await capture(
        browser,
        url,
        v,
        [
          [BASE, refBase],
          [PRODUCT, refProduct],
        ],
        wm.slot.id,
      );
      const avif = await capture(browser, url, v, [[PRODUCT, refProduct]], wm.slot.id);
      const m = measure(ref.data, avif.data, false);
      note('warm-modern base, AVIF', v.id, m);
      for (const f of failures(m)) bad.push(`base AVIF ${v.id}: ${f}`);
      if (v.id === '1920@1' || v.id === '400@3') {
        const webp = await capture(
          browser,
          url,
          v,
          [
            [BASE, webpBase],
            [PRODUCT, refProduct],
          ],
          wm.slot.id,
        );
        const mw = measure(ref.data, webp.data, false);
        note('warm-modern base, WebP fallback', v.id, mw);
        for (const f of failures(mw)) bad.push(`base WebP ${v.id}: ${f}`);
        // the product layer, inside the set's own area (its residual is diluted to nothing over the whole frame)
        const prod = await capture(browser, url, v, [[BASE, refBase]], wm.slot.id);
        const box = within(ref, house.scene.slots[wm.slot.id]!.product.rect, house.scene.aspect);
        const mp = measure(crop(ref.data, ref.w, box), crop(prod.data, prod.w, box), false);
        note('warm-modern set B layer (WebP q86, lossless alpha)', v.id, mp);
        for (const f of failures(mp)) bad.push(`set layer ${v.id}: ${f}`);
      }
      console.log(`encoding warm-modern ${v.id}: base AVIF ${fmt(m)}`);
    }
    write();
    expect(bad, bad.join('\n')).toEqual([]);
  });

  test('Nordic: its base, measured the same way and reported (its layers are temporary)', async ({ browser }) => {
    const BASE = /\/media\/rooms\/living-room\/nordic\/M0\/base\/shell\.(\d+)\.(avif|webp)$/;
    const refBase: Answer = async (r, m) => fulfil(r, await reference(nordicSource, Number(m[1]), false), 'image/png');
    for (const v of VIEWS) {
      const ref = await capture(browser, '/rooms/living-room/', v, [[BASE, refBase]], 'vase');
      const enc = await capture(browser, '/rooms/living-room/', v, [], 'vase');
      expect(enc.w).toBe(ref.w);
      const m = measure(ref.data, enc.data, false);
      note('Nordic base (temporary), AVIF', v.id, m);
      console.log(`encoding nordic ${v.id}: base AVIF ${fmt(m)}${failures(m).length ? ` · over: ${failures(m).join(', ')}` : ''}`);
    }
    write();
  });
});

function write() {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(dir, { recursive: true });
  const path = join(dir, 'encoding.json');
  const prev = existsSync(path) ? (JSON.parse(readFileSync(path, 'utf8')) as { layers: typeof evidence }).layers : {};
  writeFileSync(path, JSON.stringify({ threshold: 'p99 ≤ 6, p99.9 ≤ 10, ≤ 0.2% above 8 levels, ΔE00 p99 ≤ 3.5', layers: { ...prev, ...evidence } }, null, 1));
}
