/**
 * qa-agent, S19 (2026-11-12): the cost of ת55's full page loads, A/B. The same customer actions on two servers:
 *   S19  my public build of f33cfe42 (the cart and the checkout load as their own documents)
 *   S17  my S17 flag build of a988b099 (the same cart code; the cart and the checkout were in-site moves)
 * Cases:
 *   storage   localStorage throws (as with "block all site data"): add on a product page, then the header's cart link
 *   slow-add  the cart PUT held 1.5 s; the header's cart link clicked 200 ms after "add" (a slow mobile network)
 *   flash     the cart GET held 0 / 800 ms: from the click on the cart link, and on "continue to payment", how long the
 *             customer sees the empty state ("הסל ריק.", "הסל ריק, אין מה לשלם.") before the lines (sampled every 25 ms)
 *
 *   QA_COPY=<a copy>/site node cart-ab.mjs <out.json> <label>=<base> ...
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const [OUT, ...servers] = process.argv.slice(2);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
async function ctxFor(o) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: o.viewport ?? { width: 1280, height: 800 } });
  ctx.setDefaultTimeout(20_000);
  if (o.blockStorage)
    await ctx.addInitScript(() => {
      const deny = () => {
        throw new DOMException('The operation is insecure.', 'SecurityError');
      };
      Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
      Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
    });
  await ctx.route('**/*', async (route) => {
    const u = new URL(route.request().url());
    if (u.hostname !== '127.0.0.1') return route.abort();
    const m = route.request().method();
    if (o.slowPut && m === 'PUT' && /\/api\/cart\/[^/]+\/items/.test(u.pathname)) await new Promise((r) => setTimeout(r, o.slowPut));
    if (o.slowGet && m === 'GET' && /^\/api\/cart\/[^/]+\/?$/.test(u.pathname)) await new Promise((r) => setTimeout(r, o.slowGet));
    return route.continue();
  });
  return ctx;
}
const badge = (page) => page.locator('header a[href="/cart/"]').first().getAttribute('aria-label').catch(() => null);
async function toProductAndAdd(page, base, wait = true) {
  await page.goto(`${base}/rooms/living-room/`, { waitUntil: 'load' });
  await page.getByRole('link', { name: /^אגרטל/ }).first().click();
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  if (wait) await page.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
}
/** sample from the click until the lines show (or 4 s): ms with the empty state visible, ms to the first line */
async function sample(page, click, emptySel, lineSel) {
  const t = Date.now();
  await click();
  let empty = 0;
  let first = null;
  let last = Date.now();
  while (Date.now() - t < 4000) {
    const s = await page
      .evaluate(
        ([e, l]) => {
          const vis = (x) => !!x && !!(x.offsetWidth || x.offsetHeight || x.getClientRects().length);
          return { empty: vis(document.querySelector(e)), line: vis(document.querySelector(l)) };
        },
        [emptySel, lineSel],
      )
      .catch(() => null);
    const now = Date.now();
    if (s?.empty) empty += now - last;
    last = now;
    if (s?.line) {
      first = now - t;
      break;
    }
    await new Promise((r) => setTimeout(r, 25));
  }
  return { empty_visible_ms: empty, first_line_ms: first };
}
const out = {};
for (const sv of servers) {
  const [label, base] = sv.split('=');
  const r = {};
  {
    const ctx = await ctxFor({ blockStorage: true });
    const page = await ctx.newPage();
    await toProductAndAdd(page, base);
    const b = await badge(page);
    await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
    await page.waitForURL(/\/cart\/$/);
    await page.waitForTimeout(1500);
    r.storage_blocked = { badge_before: b, cart_lines: await page.locator('.cart-line').count(), empty: await page.locator('.cart-empty').count() };
    await ctx.close();
  }
  {
    const ctx = await ctxFor({ slowPut: 1500 });
    const page = await ctx.newPage();
    await toProductAndAdd(page, base, false);
    await page.waitForTimeout(200);
    const b = await badge(page);
    await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
    await page.waitForURL(/\/cart\/$/);
    await page.waitForTimeout(2800);
    r.slow_add_then_cart = { badge_at_click: b, cart_lines_after_3s: await page.locator('.cart-line').count(), badge_after: await badge(page) };
    await ctx.close();
  }
  for (const delay of [0, 800]) {
    const ctx = await ctxFor({ slowGet: delay });
    const page = await ctx.newPage();
    await toProductAndAdd(page, base);
    await page.waitForTimeout(300);
    const cart = await sample(page, () => page.getByRole('link', { name: /^סל הקניות/ }).first().click(), '.cart-empty', '.cart-line');
    await page.waitForTimeout(300);
    const checkout = await sample(page, () => page.getByRole('link', { name: 'להמשך לתשלום' }).click(), 'form .cart-empty, .checkout-empty, main p:only-child', '.summary li, .order-lines li, .checkout-lines li, .line');
    // the checkout's empty text, by its words (its class is not known to this tool)
    r[`flash_get_${delay}ms`] = { cart, checkout_sampled: checkout };
    await ctx.close();
  }
  // the checkout's empty words, by text: the same sampling with the text itself
  for (const delay of [0, 800]) {
    const ctx = await ctxFor({ slowGet: delay });
    const page = await ctx.newPage();
    await toProductAndAdd(page, base);
    await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
    await page.locator('.cart-line').first().waitFor();
    const t = Date.now();
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    let empty = 0;
    let last = Date.now();
    let ready = null;
    while (Date.now() - t < 4000) {
      const s = await page.evaluate(() => ({ empty: document.body.innerText.includes('הסל ריק, אין מה לשלם'), pay: !!document.querySelector('button[type="submit"]') && !document.body.innerText.includes('הסל ריק') })).catch(() => null);
      const now = Date.now();
      if (s?.empty) empty += now - last;
      last = now;
      if (s?.pay) {
        ready = now - t;
        break;
      }
      await new Promise((res) => setTimeout(res, 25));
    }
    r[`checkout_empty_words_get_${delay}ms`] = { empty_visible_ms: empty, form_ready_ms: ready };
    await ctx.close();
  }
  out[label] = r;
  console.log(`${label}: ${JSON.stringify(r)}`);
}
await browser.close();
writeFileSync(OUT, JSON.stringify(out, null, 1));
