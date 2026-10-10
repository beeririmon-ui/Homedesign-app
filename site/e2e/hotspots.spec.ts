/**
 * Product marks QA (docs/studio-rules.md ו.4, "כן לנקודות" 2026-10-10): screenshots of the room at 1280 and 400 px,
 * written to assets/qa/hotspots/ for review by eye: at rest (clean, no marks), after the pointer moved over the room
 * (marks shown), with one product focused by the keyboard and one under the pointer. Also checks that every mark
 * sits on its own product (inside the silhouette) unless it had to move aside for a neighbour, by at most one target.
 */
import { test, expect } from '@playwright/test';
import { mkdirSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = resolve(SITE, '../assets/qa/hotspots');
type Scene = { slots: Record<string, { outline?: [number, number][][] | null }> };
const scene = JSON.parse(readFileSync(resolve(SITE, '.generated/scene.living-room.nordic.json'), 'utf8')) as Scene;

for (const [w, h] of [
  [1280, 800],
  [400, 860],
] as const) {
  test(`marks and outlines at ${w} px`, async ({ page }) => {
    mkdirSync(OUT, { recursive: true });
    await page.setViewportSize({ width: w, height: h });
    await page.goto('/rooms/living-room/');
    await expect(page.locator('button.hotspot:visible').first()).toBeVisible({ timeout: 20_000 });
    await page.locator('.stage').dispatchEvent('pointerdown');
    await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 20_000 });
    const stage = page.locator('.stage');
    // at rest: the first-visit hint and the touch above have faded, the room is clean
    await page.mouse.move(1, 1);
    await expect(stage).not.toHaveAttribute('data-marks', 'on', { timeout: 10_000 });
    await page.waitForTimeout(800);
    await expect(page.locator('button.hotspot[data-slot="vase"] .mark')).toHaveCSS('opacity', '0');
    await stage.screenshot({ path: resolve(OUT, `room-${w}-rest.png`) });

    // the pointer moves over the room (a point on the back wall, on no product): the marks show
    const box = (await stage.boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.12);
    await page.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.13);
    await expect(stage).toHaveAttribute('data-marks', 'on');
    await expect(page.locator('button.hotspot[data-slot="vase"] .mark')).toHaveCSS('opacity', '1');
    await page.waitForTimeout(400);
    await stage.screenshot({ path: resolve(OUT, `room-${w}-after-move.png`) });

    // every visible mark is on its product: its centre inside the silhouette, or within 46 px of it
    const marks = await page.evaluate(() => {
      const e = window.__hdEngine!;
      const r = document.querySelector('canvas.room-canvas')!.getBoundingClientRect();
      return Array.from(document.querySelectorAll<HTMLElement>('button.hotspot'))
        .filter((b) => getComputedStyle(b).visibility === 'visible' && !b.hidden)
        .map((b) => {
          const c = b.getBoundingClientRect();
          return { slot: b.dataset.slot!, x: c.x + c.width / 2 - r.x, y: c.y + c.height / 2 - r.y, cam: e.cam, vp: e.vp, aspect: e.aspect };
        });
    });
    for (const m of marks) {
      const polys = scene.slots[m.slot]?.outline ?? [];
      const fw = Math.max(m.vp.w, m.vp.h * m.aspect);
      const fh = fw / m.aspect;
      const toScreen = ([u, v]: [number, number]) => [m.vp.w / 2 + (u - m.cam.cu) * fw * m.cam.z, m.vp.h / 2 + (v - m.cam.cv) * fh * m.cam.z] as const;
      let best = Infinity;
      for (const p of polys)
        for (let i = 0; i < p.length; i++) {
          const [ax, ay] = toScreen(p[i]!);
          best = Math.min(best, Math.hypot(ax - m.x, ay - m.y));
        }
      const inside = polys.some((p) => {
        let c = false;
        for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
          const [xi, yi] = toScreen(p[i]!);
          const [xj, yj] = toScreen(p[j]!);
          if (yi > m.y !== yj > m.y && m.x < ((xj - xi) * (m.y - yi)) / (yj - yi) + xi) c = !c;
        }
        return c;
      });
      expect(inside || best <= 46, `${m.slot} mark is off its product`).toBe(true);
    }

    // one product lit by the keyboard: the marks show, the outline glows and the label shows
    await page.mouse.move(1, 1);
    await expect(stage).not.toHaveAttribute('data-marks', 'on', { timeout: 10_000 });
    const target = page.locator('button.hotspot[data-slot="sofa-cover"]');
    if (await target.isVisible()) {
      await target.focus();
      await expect(stage).toHaveAttribute('data-marks', 'on');
      await expect(page.locator('.outlines path[data-slot="sofa-cover"]')).toHaveAttribute('data-on', 'true');
      await page.waitForTimeout(400);
      await stage.screenshot({ path: resolve(OUT, `room-${w}-focus-sofa.png`) });
      await target.blur();
      await expect(stage).not.toHaveAttribute('data-marks', 'on');
    }
    const vase = page.locator('button.hotspot[data-slot="vase"]');
    if (await vase.isVisible()) {
      await vase.hover();
      await expect(page.locator('.outlines path[data-slot="vase"]')).toHaveAttribute('data-on', 'true');
      await page.waitForTimeout(400);
      await stage.screenshot({ path: resolve(OUT, `room-${w}-hover-vase.png`) });
    }
  });
}
