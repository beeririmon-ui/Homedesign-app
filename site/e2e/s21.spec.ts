/**
 * S21, QA ת63: the cost of S19's full page loads of the cart and the checkout (ת55), measured with QA's own cases
 * (qa/reports/2026-11-12-site-track-qa-s19/tools/cart-ab.mjs):
 *  (1) the cart API held 800 ms: from the click to the lines, the cart never says "הסל ריק." and the header never "סל (0)";
 *      the checkout never says "הסל ריק, אין מה לשלם."; meanwhile the page is aria-busy; the prerendered pages say none
 *      of it either;
 *  (2) storage refused (localStorage and sessionStorage throw, as with "block all site data"): an add on a product page,
 *      then the header's cart, then the checkout: the line is there each time (the id travels in #c=, and is removed);
 *  (3) an add still on its way (the cart PUT held 1.5 s) when the header's cart is clicked 200 ms later: kept;
 *  (4) the story's "לתשלום" without storage reaches the checkout with the line.
 * Every frame of the new document is sampled from its first line of script (an init script), not every 25 ms.
 */
import { expect, test, type BrowserContext, type Page } from '@playwright/test';

/** in every new document: per frame, from the first script on, what the customer could see */
const SAMPLER = `(() => {
  const s = (window.__hdSeen = { frames: 0, empty: 0, zero: 0, pay_empty: 0, busy: 0, lines_at: null, t0: performance.now(), first_busy: null });
  const look = () => {
    const body = document.body;
    if (!body) return;
    s.frames++;
    const text = body.innerText || '';
    const head = document.querySelector('header a[href="/cart/"]');
    if (/הסל ריק\\./.test(text)) s.empty++;
    if (/הסל ריק, אין מה לשלם/.test(text)) s.pay_empty++;
    if (head && /סל \\(0\\)/.test(head.innerText || head.textContent || '')) s.zero++;
    if (document.querySelector('[aria-busy="true"]')) {
      s.busy++;
      if (s.first_busy === null) s.first_busy = Math.round(performance.now() - s.t0);
    }
    if (s.lines_at === null && document.querySelector('.cart-line, .summary li')) s.lines_at = Math.round(performance.now() - s.t0);
  };
  document.addEventListener('readystatechange', look);
  const tick = () => {
    look();
    if (s.lines_at === null || s.frames < 400) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})();`;
type Seen = { frames: number; empty: number; zero: number; pay_empty: number; busy: number; lines_at: number | null; first_busy: number | null };
const seen = (page: Page) => page.evaluate(() => (window as unknown as { __hdSeen: Seen }).__hdSeen);

async function context(
  browser: import('@playwright/test').Browser,
  o: { slowGet?: number; slowPut?: number; blockStorage?: boolean; viewport?: { width: number; height: number } } = {},
): Promise<BrowserContext> {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: o.viewport ?? { width: 1280, height: 800 } });
  await ctx.addInitScript(SAMPLER);
  if (o.blockStorage)
    await ctx.addInitScript(() => {
      const deny = () => {
        throw new DOMException('The operation is insecure.', 'SecurityError');
      };
      Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
      Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
    });
  await ctx.route(/\/api\/cart\//, async (route) => {
    const m = route.request().method();
    const u = new URL(route.request().url()).pathname;
    if (o.slowPut && m === 'PUT' && /\/api\/cart\/[^/]+\/items$/.test(u)) await new Promise((r) => setTimeout(r, o.slowPut));
    if (o.slowGet && m === 'GET' && /^\/api\/cart\/[^/]+\/?$/.test(u)) await new Promise((r) => setTimeout(r, o.slowGet));
    return route.fallback();
  });
  return ctx;
}
/** the room, a vase's product page, "הוספה לסל" (waits for the header to count it unless `wait` is false) */
async function addVase(page: Page, wait = true) {
  await page.goto('/rooms/living-room/', { waitUntil: 'load' });
  await page
    .getByRole('link', { name: /^אגרטל/ })
    .first()
    .click();
  await expect(page.locator('#product-title')).toBeVisible();
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  if (wait) await expect(page.locator('.cart-count')).toHaveText('1');
}
const headerCart = (page: Page) => page.getByRole('link', { name: /^סל הקניות/ }).first();

test.describe('S21 (QA ת63): the cart and the checkout as their own documents, without their cost', () => {
  test('the prerendered cart and checkout say nothing they do not know: no "(0)", no "הסל ריק", aria-busy', async ({ request }) => {
    for (const p of ['/cart/', '/checkout/', '/rooms/living-room/']) {
      const html = await (await request.get(p)).text();
      expect(html, p).not.toMatch(/סל \(<span[^>]*>0<\/span>\)|הסל ריק/);
      expect(html, p).toMatch(/aria-busy="true"/);
    }
  });

  test('(1) the cart API held 800 ms: the cart and the checkout are busy, never empty, and the header never "סל (0)"', async ({ browser }) => {
    const ctx = await context(browser, { slowGet: 800 });
    const page = await ctx.newPage();
    await addVase(page);
    await headerCart(page).click();
    await page.waitForURL(/\/cart\/$/);
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await expect(page.locator('.cart-count')).toHaveText('1');
    const cart = await seen(page);
    expect(cart, JSON.stringify(cart)).toMatchObject({ empty: 0, zero: 0, pay_empty: 0 });
    // the 800 ms are spent in a busy state, said to assistive technology
    expect(cart.busy).toBeGreaterThan(0);
    expect(cart.lines_at).toBeGreaterThan(700);
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);

    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await page.waitForURL(/\/checkout\/$/);
    await expect(page.locator('.summary li')).toHaveCount(1);
    await expect(page.getByRole('button', { name: 'מעבר לתשלום מאובטח' })).toBeVisible();
    const pay = await seen(page);
    expect(pay, JSON.stringify(pay)).toMatchObject({ empty: 0, zero: 0, pay_empty: 0 });
    expect(pay.busy).toBeGreaterThan(0);
    test.info().annotations.push({ type: 'timings', description: JSON.stringify({ cart, pay }) });
    await ctx.close();
  });

  test('(1) a cart that is really empty still says so, once it is known', async ({ browser }) => {
    const ctx = await context(browser, { slowGet: 800 });
    const page = await ctx.newPage();
    await page.goto('/cart/');
    await expect(page.getByRole('heading', { name: 'הסל ריק.' })).toBeVisible();
    await expect(page.locator('.cart-count')).toHaveText('0');
    await page.goto('/checkout/');
    await expect(page.getByText('הסל ריק, אין מה לשלם.')).toBeVisible();
    await ctx.close();
  });

  test('(2) storage refused: the cart and the checkout still have the line (the id in #c=, removed once read)', async ({ browser }) => {
    const ctx = await context(browser, { blockStorage: true });
    const page = await ctx.newPage();
    await addVase(page);
    await headerCart(page).click();
    await page.waitForURL(/\/cart\/(#.*)?$/);
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await expect(page.locator('.cart-count')).toHaveText('1');
    // the fragment was read and taken out of the address
    expect(new URL(page.url()).hash).toBe('');
    expect(await seen(page)).toMatchObject({ empty: 0, zero: 0 });

    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await page.waitForURL(/\/checkout\/(#.*)?$/);
    await expect(page.locator('.summary li')).toHaveCount(1);
    expect(new URL(page.url()).hash).toBe('');
    expect(await seen(page)).toMatchObject({ pay_empty: 0, zero: 0 });
    // the address in the history has no id either
    expect(await page.evaluate(() => location.href)).not.toContain('#c=');
    await ctx.close();
  });

  test('(3) an add still on its way when the header’s cart is clicked (the PUT held 1.5 s): kept', async ({ browser }) => {
    const ctx = await context(browser, { slowPut: 1500 });
    const page = await ctx.newPage();
    await addVase(page, false);
    await page.waitForTimeout(200);
    await headerCart(page).click();
    await page.waitForURL(/\/cart\/$/, { timeout: 10_000 });
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await expect(page.locator('.cart-count')).toHaveText('1');
    expect(await seen(page)).toMatchObject({ empty: 0, zero: 0 });
    await ctx.close();
  });

  test('(3) and with storage refused too: the add lands, then the id goes along', async ({ browser }) => {
    const ctx = await context(browser, { slowPut: 1500, blockStorage: true });
    const page = await ctx.newPage();
    await addVase(page, false);
    await page.waitForTimeout(200);
    await headerCart(page).click();
    await page.waitForURL(/\/cart\/(#.*)?$/, { timeout: 10_000 });
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await ctx.close();
  });

  test('(4) the story’s "לתשלום" without storage reaches the checkout with the line', async ({ browser }) => {
    const ctx = await context(browser, { blockStorage: true });
    const page = await ctx.newPage();
    await page.goto('/story/living-room/boho/#list-A', { waitUntil: 'load' });
    await page.locator('#look-A').click();
    await expect(page.locator('#st-cart-count')).not.toHaveText(/^0?$/);
    const n = Number(await page.locator('#st-cart-count').textContent());
    await page.locator('#st-cart-open').click();
    await page.locator('#st-cart-pay').click();
    await page.waitForURL(/\/checkout\/(#.*)?$/);
    await expect(page.locator('.cart-count')).toHaveText(String(n));
    await expect(page.locator('.summary li').first()).toBeVisible();
    expect(new URL(page.url()).hash).toBe('');
    await ctx.close();
  });

  test('the story’s count waits for the saved cart: a blank, busy, never "0" over a cart that has lines', async ({ browser }) => {
    const ctx = await context(browser, { slowGet: 800 });
    const page = await ctx.newPage();
    await page.goto('/story/living-room/boho/#list-A', { waitUntil: 'load' });
    await page.locator('#look-A').click();
    await expect(page.locator('#st-cart-count')).not.toHaveText(/^0?$/);
    const n = await page.locator('#st-cart-count').textContent();
    await page.addInitScript(() => {
      const w = window as unknown as { __hdCount: string[] };
      w.__hdCount = [];
      const tick = () => {
        const el = document.getElementById('st-cart-count');
        if (el) w.__hdCount.push(`${el.textContent}|${el.closest('button')?.getAttribute('aria-busy') ?? ''}`);
        if (w.__hdCount.length < 300) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    await page.reload({ waitUntil: 'load' });
    await expect(page.locator('#st-cart-count')).toHaveText(n!);
    const counts = await page.evaluate(() => (window as unknown as { __hdCount: string[] }).__hdCount);
    expect(counts.filter((c) => c.startsWith('0|'))).toEqual([]);
    expect(counts.some((c) => c === '|true')).toBe(true);
    await ctx.close();
  });
});
