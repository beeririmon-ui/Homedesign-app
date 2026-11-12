/**
 * QA S18 (2026-11-12), questions 3 and 5, in a browser against my own server (the copy's flag build):
 * - the honest lines as a customer meets them: checkout through the form, the mock payment page, the order page in this
 *   browser and another, with storage blocked, shipped with and without a number (DOM order and position), delivered
 *   (is there a way to "write to us"?), delayed, canceled, refunded, failed;
 * - the story sheet of an item on hold ("…בדף המוצר אפשר לבקש עדכון כשהוא חוזר") and the product page it links to;
 * - every page text checked with the gate's promiseFindings, screenshots at 1280 and 400 for the evidence.
 * Run: cd <copy>/site && HD_BASE_URL=http://127.0.0.1:8798 QA_OUT=<dir> npx --no-install playwright test --config=qa18/qa18.config.ts
 */
import { execFileSync } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { expect, test, type Page } from '@playwright/test';
import { placeOrder, supplierSays, waitStatus, openCustomerOrder, type Placed } from '../e2e/ops';
import { promiseFindings } from '../tools/lib/promises';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = process.env.QA_OUT!;
mkdirSync(join(OUT, 'shots'), { recursive: true });
const built = JSON.parse(readFileSync(join(SITE, '.generated/copy.he.json'), 'utf8')) as { strings: Record<string, string | null> };
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8')) as {
  products: { id: string; slot: string; price_agorot: number | null; variants: { id: string }[]; availability: { status: string } }[];
};
const results: Record<string, unknown> = {};
const note = (k: string, v: unknown) => {
  results[k] = v;
  writeFileSync(join(OUT, 'qa-s18-flows.json'), JSON.stringify(results, null, 1) + '\n');
};
function d1(sql: string) {
  execFileSync('node', ['../node_modules/wrangler/wrangler-dist/qasrv18.js', 'd1', 'execute', 'DB', '--local', '--persist-to', '../.wrangler-state', '--command', sql], {
    cwd: join(SITE, 'api'),
    stdio: 'pipe',
  });
}
async function read(page: Page) {
  return page.evaluate(() => ({
    text: document.body.innerText,
    attrs: Array.from(document.querySelectorAll('[aria-label],[title],[placeholder],img[alt]')).flatMap((el) =>
      ['aria-label', 'title', 'placeholder', 'alt'].map((a) => el.getAttribute(a) ?? '').filter(Boolean),
    ),
  }));
}
async function promisesOn(page: Page) {
  const r = await read(page);
  return [r.text, ...r.attrs].flatMap((t) => promiseFindings(t).map((f) => `${f.rule}: "${f.sentence}"`));
}
async function shots(page: Page, name: string) {
  for (const w of [1280, 400]) {
    await page.setViewportSize({ width: w, height: w === 400 ? 860 : 900 });
    await page.screenshot({ path: join(OUT, 'shots', `${name}-${w}.png`), fullPage: true });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}
const next = (page: Page) => page.locator('.order-sheet > p.small.muted');

test.describe.configure({ mode: 'serial', timeout: 180_000 });

test('F1 checkout through the form, the mock payment page, and the order page in this browser', async ({ page, request }) => {
  const h = { 'cf-connecting-ip': '10.18.18.1' };
  const p = catalog.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available')!;
  const cart = (await (await request.post('/api/cart', { headers: h })).json()) as { id: string };
  expect((await request.put(`/api/cart/${cart.id}/items`, { headers: h, data: { variant_id: p.variants[0]!.id, qty: 1 } })).status()).toBe(200);
  await page.addInitScript((id) => {
    if (!localStorage.getItem('hd.cart.seeded')) {
      localStorage.setItem('hd.cart', id);
      localStorage.setItem('hd.cart.seeded', '1');
    }
  }, cart.id);
  await page.goto('/checkout/');
  const checkoutPromises = await promisesOn(page);
  const consentBoxes = await page.getByRole('checkbox').count();
  await shots(page, 'checkout');
  await page.getByLabel('שם מלא').fill('נועה QA');
  await page.getByLabel('אימייל').fill('noa.qa18@example.com');
  await page.getByLabel('טלפון').fill('050-1818182');
  await page.getByLabel('עיר').fill('חיפה');
  await page.getByLabel('רחוב').fill('הנמל');
  await page.locator('#f-house').fill('18');
  await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
  await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
  await page.waitForURL(/mock-pay/, { timeout: 20_000 });
  const payText = await read(page);
  const payPromises = [payText.text, ...payText.attrs].flatMap((t) => promiseFindings(t).map((f) => `${f.rule}: "${f.sentence}"`));
  await page.screenshot({ path: join(OUT, 'shots', 'mock-pay-1280.png'), fullPage: true });
  await page.getByRole('button', { name: /אישור תשלום/ }).click();
  await page.waitForURL(/\/order\//, { timeout: 20_000 });
  await expect(page.locator('.order-sheet')).toBeVisible({ timeout: 20_000 });
  await expect(next(page)).toHaveText(built.strings['order.next.received']!, { timeout: 20_000 });
  const orderUrl = page.url();
  const id = orderUrl.split('/order/')[1]!.replace(/\/$/, '');
  const numberShown = await page.locator('.order-sheet strong.num').innerText();
  const orderPromises = await promisesOn(page);
  await shots(page, 'order-received');
  // "כדאי לשמור את הקישור. הוא נפתח רק בדפדפן הזה": the saved link, later, in this browser (a new tab, a reload)
  const tab = await page.context().newPage();
  await tab.goto(orderUrl);
  await expect(tab.locator('.order-sheet')).toBeVisible({ timeout: 15_000 });
  const sameBrowserLater = await next(tab).innerText();
  await tab.close();
  // the URL carries no token: the link alone opens nothing elsewhere
  const urlHasToken = /token|[?#]/.test(orderUrl);
  // in another browser
  const other = await page.context().browser()!.newContext({ locale: 'he-IL' });
  const p2 = await other.newPage();
  await p2.goto(orderUrl);
  await expect(p2.getByRole('alert')).toBeVisible({ timeout: 15_000 });
  const otherBrowser = await p2.getByRole('alert').innerText();
  await p2.screenshot({ path: join(OUT, 'shots', 'order-other-browser-1280.png'), fullPage: true });
  await other.close();
  note('F1', { checkoutPromises, consentBoxes, payPromises, order_id: id, numberShown, line: built.strings['order.next.received'], orderPromises, sameBrowserLater, urlHasToken, otherBrowser });
  expect(checkoutPromises).toEqual([]);
  expect(payPromises).toEqual([]);
  expect(orderPromises).toEqual([]);
  expect(urlHasToken).toBe(false);
});

test('F2 storage blocked (a browser that blocks all site data): checkout in one tab, back from payment', async ({ browser, request }) => {
  const ctx = await browser.newContext({ locale: 'he-IL' });
  await ctx.addInitScript(() => {
    Object.defineProperty(window, 'localStorage', {
      configurable: true,
      get() {
        throw new DOMException('The operation is insecure.', 'SecurityError');
      },
    });
  });
  const page = await ctx.newPage();
  const p = catalog.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available')!;
  // the customer's path: the product page, "add to cart", then the cart and the checkout by the site's own links
  await page.goto(`/p/${p.id}/`).catch(() => undefined);
  const productUrl = page.url();
  const add = page.getByRole('button', { name: /הוספה לסל|הוסף לסל/ }).first();
  const canAdd = await add.isVisible().catch(() => false);
  let outcome = 'no add button on the product page';
  let shown = '';
  if (canAdd) {
    await add.click();
    await page.waitForTimeout(800);
    await page.goto('/checkout/');
    await page.waitForLoadState('networkidle').catch(() => undefined);
    const hasForm = await page.getByLabel('אימייל').isVisible().catch(() => false);
    outcome = hasForm ? 'checkout form shown after a full page load' : 'no checkout form after a full page load (the cart id did not survive)';
    shown = (await page.locator('main, .page').first().innerText().catch(() => '')).slice(0, 300);
  }
  // the order page itself, after a full page load, for an order this browser just placed (the token was only in memory)
  const placed = await placeOrder(request, '10.18.18.2');
  await page.goto(`/order/${placed.id}/`);
  await expect(page.getByRole('alert')).toBeVisible({ timeout: 15_000 });
  const orderAlert = await page.getByRole('alert').innerText();
  await page.screenshot({ path: join(OUT, 'shots', 'order-storage-blocked-1280.png'), fullPage: true });
  note('F2', { productUrl, canAdd, outcome, shown, orderAlert, line_no_access: built.strings['order.no_access'] });
  await ctx.close();
});

let paid: Placed;
test('F3 shipped with a number: the number is above the line; without: no "למעלה"', async ({ page, request }) => {
  paid = await placeOrder(request, '10.18.18.3');
  await waitStatus(request, paid, 'sent_to_supplier');
  await supplierSays(request, paid, 'shipped');
  await waitStatus(request, paid, 'shipped');
  await openCustomerOrder(page, paid);
  await expect(next(page)).toHaveText(built.strings['order.next.shipped']!);
  const pos = await page.evaluate(() => {
    const t = document.querySelector('.order-tracking');
    const l = document.querySelector('.order-sheet > p.small.muted');
    const num = t?.querySelector('.num')?.textContent ?? null;
    return {
      tracking_number_shown: num,
      tracking_before_line_in_dom: !!(t && l && t.compareDocumentPosition(l) & Node.DOCUMENT_POSITION_FOLLOWING),
      tracking_y: t?.getBoundingClientRect().top ?? null,
      line_y: l?.getBoundingClientRect().top ?? null,
    };
  });
  await shots(page, 'order-shipped-number');
  d1(`UPDATE supplier_shipments SET tracking_number = NULL, tracking_url = NULL WHERE order_id = '${paid.id}';`);
  await page.reload();
  await expect(next(page)).toHaveText(built.strings['order.next.shipped_no_number']!);
  const noNumberText = await page.locator('.order-sheet').innerText();
  await shots(page, 'order-shipped-no-number');
  note('F3', { ...pos, noNumberLine: await next(page).innerText(), saysAbove: noNumberText.includes('למעלה'), promises: await promisesOn(page) });
  expect(pos.tracking_before_line_in_dom).toBe(true);
  expect(noNumberText).not.toContain('מספר המשלוח למעלה');
});

test('F4 delivered: "כתבו לנו": is there a way to write on the page?', async ({ page, request }) => {
  await supplierSays(request, paid, 'delivered');
  await waitStatus(request, paid, 'delivered');
  await openCustomerOrder(page, paid);
  await expect(next(page)).toHaveText(built.strings['order.next.delivered']!);
  const contact = await page.evaluate(() => ({
    mailto: Array.from(document.querySelectorAll('a[href^="mailto:"]')).map((a) => a.getAttribute('href')),
    tel: Array.from(document.querySelectorAll('a[href^="tel:"]')).map((a) => a.getAttribute('href')),
    contactLinks: Array.from(document.querySelectorAll('a')).filter((a) => /צור קשר|יצירת קשר|שירות לקוחות|contact/i.test(a.textContent ?? '') || /contact/.test(a.getAttribute('href') ?? '')).map((a) => `${a.textContent?.trim()} → ${a.getAttribute('href')}`),
    footer: document.querySelector('footer')?.innerText ?? null,
  }));
  await shots(page, 'order-delivered');
  note('F4', { line: await next(page).innerText(), ...contact, promises: await promisesOn(page) });
});

test('F5 the other states: delayed, canceled, refunded, payment failed, pending', async ({ page, request }) => {
  const out: Record<string, unknown> = {};
  const states: [string, string][] = [
    ['supplier_error', 'delayed'],
    ['canceled', 'canceled'],
    ['refunded', 'refunded'],
    ['payment_failed', 'failed'],
    ['pending_payment', 'pending'],
  ];
  let ip = 10;
  for (const [status, name] of states) {
    const o = await placeOrder(request, `10.18.19.${ip++}`);
    d1(`UPDATE orders SET status = '${status}' WHERE id = '${o.id}';`);
    await openCustomerOrder(page, o);
    await page.waitForTimeout(400);
    out[name] = {
      next_line: (await next(page).count()) ? await next(page).innerText() : null,
      delay: (await page.locator('.order-delay').count()) ? await page.locator('.order-delay').innerText() : null,
      promises: await promisesOn(page),
      h1: await page.locator('h1').innerText(),
    };
    await page.screenshot({ path: join(OUT, 'shots', `order-${name}-1280.png`), fullPage: true });
  }
  note('F5', out);
});

test('F6 the story sheet of an item on hold, and the product page it links to', async ({ page }) => {
  const out: Record<string, unknown> = {};
  for (const style of ['nordic', 'boho', 'warm-modern']) {
    await page.goto(`/story/living-room/${style}/`);
    await page.waitForLoadState('networkidle').catch(() => undefined);
    const ids = await page.evaluate(() => {
      const d = JSON.parse(document.getElementById('st-data')!.textContent!) as { items: Record<string, { status: string; href?: string }> };
      return Object.entries(d.items)
        .filter(([, v]) => v.status === 'unavailable')
        .map(([k, v]) => ({ id: k, href: v.href ?? null }));
    });
    const rows: unknown[] = [];
    for (const it of ids) {
      const opener = page.locator(`.st-open[data-item="${it.id}"], .st-mark[data-item="${it.id}"]`).first();
      if (!(await opener.count())) {
        rows.push({ ...it, opened: false });
        continue;
      }
      await opener.evaluate((el) => (el as HTMLElement).click());
      await expect(page.locator('#st-why')).toBeVisible({ timeout: 10_000 });
      const why = await page.locator('#st-why').innerText();
      await page.screenshot({ path: join(OUT, 'shots', `story-${style}-${it.id}-sheet-1280.png`) });
      let productPage: unknown = null;
      if (it.href) {
        const pp = await page.context().newPage();
        await pp.goto(it.href);
        await pp.waitForLoadState('networkidle').catch(() => undefined);
        productPage = {
          waitlistStatus: (await pp.locator('.waitlist-status').count()) ? await pp.locator('.waitlist-status').first().innerText() : null,
          formControls: await pp.locator('.waitlist button, .waitlist input, .waitlist form').count(),
          askUpdateButton: await pp.getByRole('button', { name: /עדכנו|עדכון/ }).count(),
        };
        await pp.screenshot({ path: join(OUT, 'shots', `story-${style}-${it.id}-product-1280.png`), fullPage: true });
        await pp.close();
      }
      rows.push({ ...it, opened: true, why, gate: promiseFindings(why), productPage });
      await page.keyboard.press('Escape');
    }
    out[style] = rows;
  }
  note('F6', out);
});
