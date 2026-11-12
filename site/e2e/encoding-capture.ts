/**
 * S12: one drawing of the room stage, as the browser paints it, for e2e/encoding.spec.ts (QA's method,
 * qa/reports/2026-11-10-site-track-qa-s8-s10/tools/base-quality.mjs): a fresh context at the view's size and dpr, the
 * layers' requests answered as the caller says, the engine started and settled, the controls hidden, the canvas read.
 */
import { expect, type Browser, type Locator, type Page, type Route } from '@playwright/test';
import sharp from 'sharp';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { View } from '../tools/lib/encoding';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const BASE_URL = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';
export type Box = [number, number, number, number];

// ---------- one drawing of the stage ----------
export type Answer = (route: Route, m: RegExpExecArray) => Promise<void>;
/** `before`: runs once the engine is ready, before the zoom and the reading (S14: a set chosen on the engine) */
export async function capture(browser: Browser, url: string, v: View, answers: [RegExp, Answer][], slot?: string, before?: (page: Page) => Promise<void>) {
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
  await page.goto(url, { waitUntil: 'load' });
  await expect(page.locator('section.stage')).toBeVisible({ timeout: 20_000 });
  await expect(page.locator('button.hotspot').first()).toBeAttached({ timeout: 20_000 });
  // S21, QA ה17: on a busy runner a press can land before the page hydrates, and nothing starts the engine: the press
  // is made again until the engine is there (never a longer fixed wait), then it must be ready
  const sb = (await page.locator('section.stage').boundingBox())!;
  await expect(async () => {
    if (!(await page.evaluate(() => !!window.__hdEngine))) await page.mouse.click(sb.x + 20, sb.y + sb.height / 2);
    expect(await page.evaluate(() => !!window.__hdEngine)).toBe(true);
  }).toPass({ timeout: 60_000, intervals: [500, 1_000, 2_000] });
  await expect.poll(() => page.evaluate(() => window.__hdEngine?.ready ?? false), { timeout: 60_000 }).toBe(true);
  if (before) {
    await before(page);
    await settle(page);
  }
  if (v.zoom && slot) {
    // a press can land before the stage takes it (its marks still placing): pressed again until the wheel is open
    const dialog = page.getByRole('dialog');
    await expect(async () => {
      if (!(await dialog.isVisible())) {
        await page.locator(`button.hotspot[data-slot="${slot}"]`).focus();
        await page.keyboard.press('Enter');
      }
      await expect(dialog).toBeVisible({ timeout: 4_000 });
    }).toPass({ timeout: 30_000 });
    await settle(page);
    await hide(page, '[role="dialog"], .wheel, .wheel-wrap');
  }
  await page.mouse.move(0, 0);
  // S21, QA ה17: read only once the page is settled. Under load (QA: 12–14 on 4 cores) a capture caught the product
  // marks that a press shows for a few seconds (each mark sets its own visibility, so hiding their parent once is not
  // enough): a 0.19% patch in one of the two drawings. Now every mark and control is hidden before every reading, the
  // engine has no animation and no picture on its way, and three readings in a row are the same picture.
  const shot = await stillShot(page, page.locator('canvas.room-canvas'), STAGE_OVER);
  const eng = await page.evaluate(() => {
    const e = window.__hdEngine!;
    return { cam: { ...e.cam }, vp: { ...e.vp } };
  });
  await ctx.close();
  const { data, info } = await sharp(shot).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, eng };
}
/**
 * S14, QA ת29/ת30 (§4): the poster as the page rests on it: a fresh context, the poster's requests answered as the caller
 * says, nothing that signals intent (no pointer over the stage, no focus, no touch), so the engine never starts; the
 * controls hidden; the <img class="poster"> read as the browser draws it. `file` is the file the browser chose
 * (its width), `engine` whether an engine ran at all (it must not).
 */
export async function capturePoster(browser: Browser, url: string, v: View, answers: [RegExp, Answer][]) {
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
  const img = page.locator('img.poster');
  await expect(img).toBeVisible({ timeout: 20_000 });
  await expect.poll(() => img.evaluate((i: HTMLImageElement) => i.complete && i.naturalWidth > 0 && !!i.currentSrc), { timeout: 30_000 }).toBe(true);
  // hidden again before every shot: the page hydrates after the poster is drawn (its marks, shown on a first entry,
  // are made then), so a hide done once can miss them (S14: the Nordic room's 13 marks, ≈0.1–0.3% of the frame)
  const still = () => hide(page, POSTER_OVER).then(() => img.screenshot());
  let shot = await still();
  for (let i = 0; i < 30; i++) {
    const next = await still();
    if (next.equals(shot)) break;
    shot = next;
  }
  const info0 = await page.evaluate(() => ({
    src: document.querySelector<HTMLImageElement>('img.poster')!.currentSrc,
    engine: !!window.__hdEngine,
  }));
  await ctx.close();
  const { data, info } = await sharp(shot).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, file: new URL(info0.src).pathname.split('/').pop()!, engine: info0.engine };
}

/** what lies over the composed stage: the controls, the marks (each hotspot too: one shown sets its own visibility) */
const STAGE_OVER = '.stage-ui, .hotspots, button.hotspot, .hotspot .mark, .stage-temp-note, .outlines, .stage-back, .stage-vignette';
/** S21 (ה17): the engine is at rest: no animation, and no picture on its way to it (the loader's queue is empty) */
const engineIdle = (page: Page) =>
  page.evaluate(
    () =>
      new Promise<boolean>((res) =>
        requestAnimationFrame(() => {
          const e = window.__hdEngine as unknown as { ready?: boolean; anims?: Set<unknown>; loader?: { active?: number; queue?: unknown[] } };
          res(!!e?.ready && (!e.anims || e.anims.size === 0) && !e.loader?.active && !e.loader?.queue?.length);
        }),
      ),
  );
/**
 * S21, QA ה17: a reading of the stage once it is settled: what lies over it hidden again before every reading, the
 * engine idle, and the same picture three readings in a row (up to 40 readings; the test fails on a stage that never
 * settles rather than reading a moving one).
 */
async function stillShot(page: Page, el: Locator, over: string): Promise<Buffer> {
  const read = async () => {
    await hide(page, over);
    await expect.poll(() => engineIdle(page), { timeout: 30_000 }).toBe(true);
    return el.screenshot({ animations: 'disabled' });
  };
  let shot = await read();
  let same = 0;
  for (let i = 0; i < 40 && same < 2; i++) {
    const next = await read();
    same = next.equals(shot) ? same + 1 : 0;
    shot = next;
  }
  expect(same, 'the stage never settled: three readings in a row differed').toBe(2);
  return shot;
}

/** what lies over the poster at rest: the controls, the marks (each hotspot too: one shown sets its own visibility) */
const POSTER_OVER = '.stage-ui, .hotspots, button.hotspot, .hotspot .mark, .stage-temp-note, .outlines, .stage-back, .stage-vignette, canvas.room-canvas';
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

export const file = (rel: string) => readFileSync(resolve(SITE, 'web/public/media', rel));
export const fulfil = (route: Route, body: Buffer, contentType: string) =>
  route.fulfill({ status: 200, contentType, body, headers: { 'cache-control': 'no-store' } });
/** the stage pixels inside a frame rectangle (u0 u1 v0 v1), through the engine's camera */
export function within(
  c: { w: number; h: number; eng: { cam: { cu: number; cv: number; z: number }; vp: { w: number; h: number } } },
  rect: Box,
  aspect: number,
) {
  const k = c.w / c.eng.vp.w;
  const fw = Math.max(c.eng.vp.w, c.eng.vp.h * aspect) * c.eng.cam.z;
  const fh = fw / aspect;
  const x = (u: number) => Math.round((c.eng.vp.w / 2 + (u - c.eng.cam.cu) * fw) * k);
  const y = (v: number) => Math.round((c.eng.vp.h / 2 + (v - c.eng.cam.cv) * fh) * k);
  return { x0: Math.max(0, x(rect[0])), x1: Math.min(c.w, x(rect[1])), y0: Math.max(0, y(rect[2])), y1: Math.min(c.h, y(rect[3])) };
}
export const crop = (d: Buffer, w: number, b: { x0: number; x1: number; y0: number; y1: number }) => {
  const out = Buffer.alloc((b.x1 - b.x0) * (b.y1 - b.y0) * 4);
  for (let y = b.y0; y < b.y1; y++) d.copy(out, (y - b.y0) * (b.x1 - b.x0) * 4, (y * w + b.x0) * 4, (y * w + b.x1) * 4);
  return out;
};
