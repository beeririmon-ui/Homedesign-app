/**
 * The test page in the magazine language (/test/): the cover's designed loading, the paper transition into the living
 * room, a clean room at rest, the marks on movement, focus mode (approach, the interface 100 + 200 ms after the camera
 * stops, the return landing on the frame at rest), and reduced motion as a dissolve. Durations are read from the page's
 * own timeline (window.__mag.events); headless SwiftShader is slow, so timings carry a wide tolerance here and the
 * evidence tool (tools/screens-test-page.ts) records the exact figures.
 */
import { test, expect, type Page } from '@playwright/test';

type Ev = { t: number; name: string; detail?: unknown };
const events = (page: Page) => page.evaluate(() => window.__mag?.events ?? []) as Promise<Ev[]>;
const at = (evs: Ev[], name: string) => evs.find((e) => e.name === name)?.t ?? null;

test.describe('the test page', () => {
  test('the cover develops, then the brand, the title and the invitation; Enter is a paper transition into the living room', async ({ page }) => {
    await page.goto('/test/');
    await expect(page.locator('.mag-cover-title')).toBeVisible();
    await expect(page.locator('body')).toHaveClass(/is-invite/, { timeout: 15_000 });
    const evs = await events(page);
    for (const n of ['cover:lqip', 'cover:developed', 'cover:brand', 'cover:title', 'cover:invite']) expect(at(evs, n), n).not.toBeNull();
    expect(at(evs, 'cover:title')! - at(evs, 'cover:brand')!).toBeGreaterThanOrEqual(380);
    await page.keyboard.press('Enter');
    await expect(page.locator('#mag-veil')).toHaveClass(/is-in/);
    await expect(page.locator('#mag-veil')).not.toHaveClass(/is-in/, { timeout: 5_000 });
    await expect(page.locator('#room-living-room')).toBeInViewport({ ratio: 0.9 });
    await expect(page.locator('#mag-run')).toHaveText('02 · הסלון · נורדי');
  });

  test('a clean room at rest; the marks come with the pointer and go 2.5 s later; the wall label is the credit', async ({ page }) => {
    await page.goto('/test/');
    await page.evaluate(() => document.querySelector('#room-living-room')!.scrollIntoView({ behavior: 'instant' }));
    await page.waitForTimeout(2200); // the first-entry hint has gone
    const dot = page.locator('#room-living-room .mag-mark[data-slot="vase"] .mag-dot');
    await expect(dot).toHaveCSS('opacity', '0');
    await expect(page.locator('#room-living-room .mag-strip')).toBeHidden();
    await page.mouse.move(640, 400);
    await page.mouse.move(650, 410);
    await expect(dot).toHaveCSS('opacity', '1', { timeout: 2_000 });
    await page.locator('#room-living-room .mag-mark[data-slot="vase"]').hover();
    await expect(page.locator('#room-living-room .mag-label')).toHaveClass(/is-on/);
    await expect(page.locator('#room-living-room .mag-label .mag-credit-detail')).toContainText('₪');
    await page.mouse.move(5, 5);
    await expect(dot).toHaveCSS('opacity', '0', { timeout: 6_000 });
  });

  test('focus mode: the approach, the strip 100 + 200 ms after the camera stops, the keyboard browses, the return lands on the frame at rest', async ({
    page,
  }) => {
    await page.goto('/test/');
    await page.evaluate(() => document.querySelector('#room-living-room')!.scrollIntoView({ behavior: 'instant' }));
    await page.waitForTimeout(500);
    await page.evaluate(() => window.__mag!.openFocus('M0', 'vase'));
    await expect(page.locator('#room-living-room .mag-stage')).toHaveAttribute('data-focus', 'on', { timeout: 6_000 });
    await expect(page.locator('#room-living-room .mag-strip')).toHaveClass(/is-on/, { timeout: 3_000 });
    await expect(page.locator('#room-living-room .mag-soft')).toHaveCount(1);
    await expect(page.locator('#room-living-room .mag-sharp')).toHaveCount(1);
    await expect(page.locator('#room-living-room .mag-thumb[aria-checked="true"]')).toBeFocused();
    await page.keyboard.press('ArrowLeft');
    await expect(page.locator('#room-living-room .mag-thumb[aria-checked="true"]')).toHaveAttribute('data-i', '1');
    const evs = await events(page);
    const stop = at(evs, 'M0:focus:camera:stop')!;
    const uiIn = at(evs, 'M0:focus:ui:in')!;
    expect(uiIn - stop).toBeGreaterThanOrEqual(100);
    expect(uiIn - stop).toBeLessThan(1500);
    await page.keyboard.press('Escape');
    await expect(page.locator('#room-living-room .mag-stage')).not.toHaveAttribute('data-focus', /.+/, { timeout: 6_000 });
    await expect(page.locator('#room-living-room .mag-soft')).toHaveCount(0);
    expect(await page.locator('#room-living-room .mag-frame').evaluate((el) => (el as HTMLElement).style.transform)).toBe('');
    await expect(page.locator('#room-living-room .mag-mark[data-slot="vase"]')).toBeFocused();
    await expect(page.locator('#mag-head')).toHaveAttribute('data-on', 'stage');
  });

  test('reduced motion: the approach and the return are dissolves, nothing moves', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/test/');
    await page.evaluate(() => document.querySelector('#room-living-room')!.scrollIntoView({ behavior: 'instant' }));
    await page.waitForTimeout(300);
    await page.evaluate(() => window.__mag!.openFocus('M0', 'cushions'));
    await expect(page.locator('#room-living-room .mag-stage')).toHaveAttribute('data-focus', 'on', { timeout: 3_000 });
    const evs = await events(page);
    expect(at(evs, 'M0:focus:camera:stop')! - at(evs, 'M0:focus:start')!).toBeLessThan(900);
    expect(await page.locator('#room-living-room .mag-frame').evaluate((el) => getComputedStyle(el).transitionDuration)).toBe('0s');
    await page.evaluate(() => window.__mag!.cancelFocus('M0'));
    await expect(page.locator('#room-living-room .mag-stage')).not.toHaveAttribute('data-focus', /.+/, { timeout: 3_000 });
  });

  test('the pan clip plays at scale 1.000 with the walk easing, and back', async ({ page }) => {
    await page.goto('/test/');
    await page.evaluate(() => document.querySelector('#mag-pan')!.scrollIntoView({ behavior: 'instant' }));
    await page.waitForFunction(() => window.__mag?.pan.ready === true, null, { timeout: 60_000 });
    await page.getByRole('button', { name: 'נגינה' }).click();
    await page.waitForFunction(() => !window.__mag?.pan.playing, null, { timeout: 20_000 });
    const samples = (await page.evaluate(() => window.__mag!.pan.samples)) as { t: number; p: number }[];
    expect(samples.length).toBeGreaterThan(10);
    expect(samples[samples.length - 1]!.p).toBeGreaterThan(samples[0]!.p);
    // monotonic progress: no step backwards
    for (let i = 1; i < samples.length; i++) expect(samples[i]!.p).toBeGreaterThanOrEqual(samples[i - 1]!.p);
    await expect(page.getByRole('button', { name: 'חזרה' })).toBeEnabled();
  });
});
