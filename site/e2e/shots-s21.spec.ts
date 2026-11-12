/**
 * S21, the evidence (qa/reports/2026-11-07-site-track/s21/screens and data/s21-timings.json), at 1280 and 400, with axe
 * on each state: QA ת63, the cart and the checkout while a saved cart loads (the cart API held 1.5 s, as QA's
 * flash-shot.mjs: a picture 400 ms after the click), once loaded, and when the load failed (the API answers 503). And
 * the timings of QA's slow-API case (800 ms): from the click to the first line, and the frames that showed an empty state.
 * Runs only as `HD_SHOTS_DIR=<dir> npx --no-install playwright test --project=evidence e2e/shots-s21.spec.ts`, against the
 * local build with its Worker (npm run preview).
 */
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Browser, type Page } from '@playwright/test';

const DIR = process.env.HD_SHOTS_DIR ?? '';
test.skip(!DIR, 'evidence only: set HD_SHOTS_DIR');
test.describe.configure({ mode: 'serial', timeout: 180_000 });

const WIDTHS = [1280, 400] as const;
const timings: Record<string, unknown> = {};
async function shot(page: Page, name: string, full = false) {
  mkdirSync(join(DIR, 'screens'), { recursive: true });
  await page.screenshot({ path: join(DIR, 'screens', `${name}.png`), fullPage: full });
}
async function axe(page: Page) {
  const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(r.violations.map((v) => `${v.id}: ${v.nodes.length}`)).toEqual([]);
}
async function ctxFor(browser: Browser, w: number, getMs: number, fail = false) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: w === 400 ? 860 : 800 } });
  await ctx.route(/\/api\/cart\/[^/]+\/?$/, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    if (getMs) await new Promise((r) => setTimeout(r, getMs));
    if (fail) return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'unavailable' }) });
    return route.fallback();
  });
  return ctx;
}
async function addVase(page: Page) {
  await page.goto('/rooms/living-room/', { waitUntil: 'load' });
  await page
    .getByRole('link', { name: /^אגרטל/ })
    .first()
    .click();
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  await expect(page.locator('.cart-count')).toHaveText('1');
}

for (const w of WIDTHS)
  test(`${w}: the cart and the checkout while the saved cart loads, loaded, and when the load failed`, async ({ browser }) => {
    const ctx = await ctxFor(browser, w, 1500);
    const page = await ctx.newPage();
    await addVase(page);
    await page
      .getByRole('link', { name: /^סל הקניות/ })
      .first()
      .click();
    await page.waitForURL(/\/cart\/$/);
    await page.waitForTimeout(400);
    await expect(page.locator('.cart-loading')).toBeVisible();
    await shot(page, `cart-while-loading-${w}`);
    await axe(page);
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await shot(page, `cart-loaded-${w}`);
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await page.waitForURL(/\/checkout\/$/);
    await page.waitForTimeout(400);
    await expect(page.locator('.cart-loading')).toBeVisible();
    await shot(page, `checkout-while-loading-${w}`);
    await axe(page);
    await expect(page.locator('.summary li')).toHaveCount(1);
    await shot(page, `checkout-loaded-${w}`);
    await ctx.close();

    const bad = await ctxFor(browser, w, 0, true);
    const p2 = await bad.newPage();
    // the same browser's cart (a new context starts empty): an add, then the cart with its GET failing
    await bad.unroute(/\/api\/cart\/[^/]+\/?$/);
    await addVase(p2);
    await bad.route(/\/api\/cart\/[^/]+\/?$/, (r) =>
      r.request().method() === 'GET'
        ? r.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: 'unavailable' }) })
        : r.fallback(),
    );
    await p2
      .getByRole('link', { name: /^סל הקניות/ })
      .first()
      .click();
    await p2.waitForURL(/\/cart\/$/);
    await expect(p2.getByRole('button', { name: 'לנסות שוב' })).toBeVisible();
    await expect(p2.getByText('הסל ריק.')).toHaveCount(0);
    await shot(p2, `cart-load-failed-${w}`);
    await axe(p2);
    await bad.close();
  });

test('timings: the cart API held 800 ms and 0 ms, from the click to the first line, and frames with an empty state', async ({ browser }) => {
  for (const ms of [0, 800]) {
    const ctx = await ctxFor(browser, 1280, ms);
    const page = await ctx.newPage();
    await addVase(page);
    const sample = async (click: () => Promise<void>, line: string) => {
      const t = Date.now();
      await click();
      let empty = 0;
      let first: number | null = null;
      while (Date.now() - t < 5000) {
        const s = await page
          .evaluate(
            (l) => ({
              empty: /הסל ריק|סל \(0\)/.test(document.body?.innerText ?? ''),
              line: !!document.querySelector(l),
              busy: !!document.querySelector('[aria-busy="true"]'),
            }),
            line,
          )
          .catch(() => null);
        if (s?.empty) empty++;
        if (s?.line) {
          first = Date.now() - t;
          break;
        }
        await new Promise((r) => setTimeout(r, 25));
      }
      return { first_line_ms: first, samples_with_empty_words: empty };
    };
    const cart = await sample(
      () =>
        page
          .getByRole('link', { name: /^סל הקניות/ })
          .first()
          .click(),
      '.cart-line',
    );
    const checkout = await sample(() => page.getByRole('link', { name: 'להמשך לתשלום' }).click(), '.summary li');
    timings[`get_${ms}ms`] = { cart, checkout };
    await ctx.close();
  }
  mkdirSync(join(DIR, 'data'), { recursive: true });
  writeFileSync(join(DIR, 'data', 's21-timings.json'), JSON.stringify(timings, null, 1));
});
