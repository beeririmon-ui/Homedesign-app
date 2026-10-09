/**
 * Performance gates (skeleton-spec, "ביצועים"):
 *   - first load of the living room on a mid-range phone ≤ 3 MB, measured as bytes received until the room is composed
 *   - only reachable transitions are preloaded (from the living room: T-E0 only)
 *   - 60 fps animations: frame times of the zoom and the wheel. Headless Chromium renders WebGL in software
 *     (SwiftShader), so the frame gate is enforced only with HD_GPU=1 on a machine with a GPU; otherwise the numbers
 *     are reported as annotations.
 */
import { test, expect, devices } from '@playwright/test';

const MB = 1024 * 1024;
const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];

test.describe('mobile', () => {
  test.use(pixel);

  test('first load of the living room ≤ 3 MB and only reachable transitions preload', async ({ page }) => {
    let bytes = 0;
    const urls: string[] = [];
    const client = await page.context().newCDPSession(page);
    await client.send('Network.enable');
    client.on('Network.loadingFinished', (e) => (bytes += e.encodedDataLength));
    page.on('request', (r) => urls.push(r.url()));
    await page.goto('/rooms/living-room/');
    await expect(page.locator('button.hotspot:visible').first()).toBeVisible({ timeout: 30_000 });
    const atPoster = bytes;
    // the engine starts on the first touch: count everything until the WebGL composition is on screen
    await page.locator('.stage').dispatchEvent('pointerdown', { pointerId: 1, pointerType: 'touch', isPrimary: true });
    await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30_000 });
    await page.waitForTimeout(300);
    const atReady = bytes;
    console.log(`poster and hotspots: ${(atPoster / MB).toFixed(2)} MB`);
    test.info().annotations.push({ type: 'first-load', description: `${(atReady / MB).toFixed(2)} MB until the room is composed` });
    console.log(`first load (mobile, until composed): ${(atReady / MB).toFixed(2)} MB`);
    expect(atReady).toBeLessThanOrEqual(3 * MB);

    await page.waitForTimeout(6000); // background: other variants, depth, reachable transitions
    const transitions = new Set(urls.filter((u) => u.includes('/media/transitions/')).map((u) => u.split('/media/transitions/')[1]!.split('/')[0]));
    expect([...transitions].every((t) => t === 'T-E0')).toBe(true);
  });
});

test('animation frame times (zoom and wheel)', async ({ page }) => {
  await page.goto('/rooms/living-room/');
  await expect(page.locator('button.hotspot:visible').first()).toBeVisible({ timeout: 30_000 });
  await page.evaluate(() => (window.__hdFrames = []));
  await page.locator('button.hotspot[data-slot="vase"]').click();
  await expect(page.getByRole('dialog')).toBeVisible();
  const zoom = await page.evaluate(() => window.__hdFrames ?? []);

  // wheel: rAF intervals while it spins between options
  const wheel = await page.evaluate(async () => {
    const times: number[] = [];
    let last = performance.now();
    let on = true;
    const tick = (t: number) => {
      times.push(t - last);
      last = t;
      if (on) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
    document.querySelector<HTMLElement>('.arc-card[aria-checked="true"]')?.dispatchEvent(new KeyboardEvent('keydown', { key: 'End', bubbles: true }));
    await new Promise((r) => setTimeout(r, 900));
    on = false;
    return times.slice(1);
  });
  const p95 = (a: number[]) => [...a].sort((x, y) => x - y)[Math.floor(a.length * 0.95)] ?? 0;
  const report = `zoom: ${zoom.length} frames, p95 ${p95(zoom).toFixed(1)} ms · wheel: ${wheel.length} frames, p95 ${p95(wheel).toFixed(1)} ms`;
  test.info().annotations.push({ type: 'frames', description: report });
  console.log(report);
  if (process.env.HD_GPU === '1') {
    expect(p95(zoom)).toBeLessThanOrEqual(20);
    expect(p95(wheel)).toBeLessThanOrEqual(20);
  }
});
