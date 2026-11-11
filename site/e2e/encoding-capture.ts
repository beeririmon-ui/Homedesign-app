/**
 * S12: one drawing of the room stage, as the browser paints it, for e2e/encoding.spec.ts (QA's method,
 * qa/reports/2026-11-10-site-track-qa-s8-s10/tools/base-quality.mjs): a fresh context at the view's size and dpr, the
 * layers' requests answered as the caller says, the engine started and settled, the controls hidden, the canvas read.
 */
import { expect, type Browser, type Page, type Route } from '@playwright/test';
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
export async function capture(browser: Browser, url: string, v: View, answers: [RegExp, Answer][], slot?: string) {
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
  await hide(page, '.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back, .stage-vignette');
  await page.mouse.move(0, 0);
  await settle(page);
  // the stage is still when two readings in a row are the same picture (a CSS fade or a late frame otherwise differs)
  const canvas = page.locator('canvas.room-canvas');
  let shot = await canvas.screenshot();
  for (let i = 0; i < 30; i++) {
    const next = await canvas.screenshot();
    if (next.equals(shot)) break;
    shot = next;
  }
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
