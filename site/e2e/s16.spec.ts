/**
 * S16, the fixes of QA S13–S14 in the browser (briefs/site-s16-qa-fixes-2026-11-11.md):
 * - ת43: a phone without AVIF entering the warm-modern house: the poster's WebP fallback (q95), the engine at idle,
 *   and the whole first load ≤ 3 MB until the room is composed. With AVIF, the engine still waits for intent.
 * - ה1: while the poster is on its way, the stage shows the inlined placeholder of the same composition, not the dark
 *   stage colour.
 * - ת37: the order page and the cart show the server's own message, with its error code.
 */
import { test, expect, devices, type Page } from '@playwright/test';
import sharp from 'sharp';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIST = resolve(dirname(fileURLToPath(import.meta.url)), '../web/dist');
const MB = 1024 * 1024;
const HOUSE = '/rooms/living-room/?style=warm-modern';
const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];

/** a browser without AVIF: the page's probe fails, and every AVIF the page asks for is answered with its WebP fallback */
async function withoutAvif(page: Page): Promise<{ fallback: () => number; asked: string[] }> {
  await page.addInitScript(() => {
    const d = Object.getOwnPropertyDescriptor(HTMLImageElement.prototype, 'src')!;
    Object.defineProperty(HTMLImageElement.prototype, 'src', {
      ...d,
      set(v: string) {
        d.set!.call(this, String(v).startsWith('data:image/avif') ? 'data:image/avif;base64,AAAA' : v);
      },
    });
  });
  let bytes = 0;
  const asked: string[] = [];
  await page.route(/\/media\/.+\.avif(\?.*)?$/, async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/\.avif$/, '.webp');
    const body = readFileSync(resolve(DIST, `.${path}`));
    bytes += body.length;
    asked.push(path);
    await route.fulfill({ status: 200, contentType: 'image/webp', body });
  });
  return { fallback: () => bytes, asked };
}

test.describe('ת43: a phone without AVIF in the warm-modern house', () => {
  test.use(pixel);

  test('the WebP poster, the engine at idle, and the first load ≤ 3 MB until the room is composed', async ({ page }) => {
    const nonAvif = await withoutAvif(page);
    let bytes = 0;
    const client = await page.context().newCDPSession(page);
    await client.send('Network.enable');
    // the answered AVIF requests are counted by their WebP bytes (nonAvif); everything else as received
    const routed = new Set<string>();
    const urlOf = new Map<string, string>();
    const got: [string, number][] = [];
    client.on('Network.requestWillBeSent', (e) => {
      urlOf.set(e.requestId, e.request.url);
      if (/\.avif(\?.*)?$/.test(e.request.url)) routed.add(e.requestId);
    });
    client.on('Network.loadingFinished', (e) => {
      if (routed.has(e.requestId)) return;
      bytes += e.encodedDataLength;
      got.push([urlOf.get(e.requestId) ?? '?', e.encodedDataLength]);
    });
    await page.goto(HOUSE);
    // no pointer, no touch, no focus: the engine starts at idle because the browser has no AVIF
    // the first load is what the page received until the room is composed (the engine then fetches the other variants)
    await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 45_000, polling: 10 });
    const total = bytes + nonAvif.fallback();
    if (process.env.HD_DEBUG_BYTES)
      console.log(
        got
          .sort((a, b) => b[1] - a[1])
          .slice(0, 25)
          .map(([u, b]) => `${(b / 1024).toFixed(0)} KB ${u}`)
          .join('\n'),
      );
    console.log(
      `no AVIF, warm-modern house, until composed: ${(total / MB).toFixed(2)} MB (WebP fallbacks ${(nonAvif.fallback() / MB).toFixed(2)} MB: ${nonAvif.asked.join(', ')})`,
    );
    test.info().annotations.push({ type: 'first-load-no-avif', description: `${(total / MB).toFixed(2)} MB` });
    expect(nonAvif.asked.some((p) => /\/poster\/default\.\d+\.webp$/.test(p))).toBe(true);
    expect(total).toBeLessThanOrEqual(3 * MB);
  });

  test('with AVIF, the engine still waits for intent (the poster is the room at rest)', async ({ page }) => {
    await page.goto(HOUSE);
    await page.waitForLoadState('load');
    await page.waitForTimeout(3000);
    expect(await page.evaluate(() => !!window.__hdEngine)).toBe(false);
  });
});

test('ה1: while the poster is on its way, the stage is the placeholder of the same room, not the dark stage', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  let release!: () => void;
  const held = new Promise<void>((r) => (release = r));
  await page.route(/\/poster\/default\.\d+\.(avif|webp)$/, async (route) => {
    await held;
    await route.continue().catch(() => undefined);
  });
  await page.goto(HOUSE, { waitUntil: 'domcontentloaded' });
  const style = (await page.locator('.stage img.poster').getAttribute('style')) ?? '';
  expect(style).toMatch(/background-image:\s*url\("?data:image\/webp;base64,/);
  const shot = await page.locator('.stage').screenshot({ animations: 'disabled' });
  const { channels } = await sharp(shot).stats();
  const mean = channels.slice(0, 3).reduce((s, c) => s + c.mean, 0) / 3;
  console.log(`the stage while the poster waits: mean ${mean.toFixed(1)} (the stage colour #141312 is about 19)`);
  // the warm room in light (the placeholder) rather than #141312
  expect(mean).toBeGreaterThan(90);
  release();
});

test('ת37: the order page and the cart show the server’s message and its error code, as the checkout does', async ({ page }) => {
  const id = '1234567890';
  await page.addInitScript(
    ([orderId]) => {
      localStorage.setItem(`hd.order.${orderId}`, 'tok-s16-0123456789abcdef');
      localStorage.setItem('hd.cart', 'cart-s16-test');
    },
    [id],
  );
  const said = (code: string) => `משהו השתבש אצלנו. נסו שוב בעוד רגע. אם זה חוזר, כתבו לנו וציינו את הקוד ${code}.`;
  await page.route(`**/api/orders/${id}`, (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'internal_error', error_id: 'E-ORDS16AB', message_he: said('E-ORDS16AB') }),
    }),
  );
  await page.route('**/api/cart/cart-s16-test', (r) =>
    r.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'internal_error', error_id: 'E-CRTS16AB', message_he: said('E-CRTS16AB') }),
    }),
  );
  await page.goto(`/order/${id}/`);
  await expect(page.locator('main [role="alert"]')).toContainText('E-ORDS16AB');
  await page.goto('/cart/');
  await expect(page.locator('main [role="alert"]')).toContainText('E-CRTS16AB');
});
