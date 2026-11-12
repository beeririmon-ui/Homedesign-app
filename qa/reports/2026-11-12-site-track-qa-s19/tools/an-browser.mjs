/**
 * qa-agent, S19 (2026-11-12): ת55 in Chromium against the PUBLIC build (HD_PUBLIC=1, a dummy 32-hex token) served by its
 * own Worker. No network: every request off 127.0.0.1 is stopped here, and Cloudflare's script is replaced by MY STUB, a
 * worst case: it reports location.href and document.referrer on load, on every pushState and on pagehide, AND it
 * listens to every input, change and keyup in its document and reports what was typed, and at pagehide every field's
 * value. So "nothing typed is observed" is measured, not assumed. (The real script's own behaviour is not measured.)
 *
 *   1. the pages that carry the tag (every prerendered page, the 404, an order page, the admin), as S17;
 *   2. the journeys: J1 by mouse (room → product → cart → checkout → pay → order → home → room); J2 by keyboard (Enter on
 *      the header's cart link and on "continue to payment"); J3 back and forward through them; for each step: the URL, a
 *      new document or not, the tag in it, the stub ran in it;
 *   3. the cost of the full loads: C1 storage blocked (localStorage throws, as with "block all site data"); C2 a slow add
 *      (the cart PUT held 1.5 s) and a click on the cart 200 ms after "add"; C3 back to the room after changing the
 *      cart (a stale header count?); C4 focus and title on the full loads; C5 time from the click to the first cart line
 *      and to the checkout form, at 1280 and 400; the bytes moved by the full load with a warm cache.
 *
 *   QA_COPY=<public copy>/site QA_BASE=http://127.0.0.1:8816 QA_OUT=<out.json> [QA_ONLY=journeys|costs] node an-browser.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
const COPY = process.env.QA_COPY;
const { chromium } = createRequire(join(COPY, 'package.json'))('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8816';
const OUT = process.env.QA_OUT;
const ONLY = process.env.QA_ONLY ?? '';
const SHOTS = process.env.QA_SHOTS;
const DIST = join(COPY, 'web/dist');
const DEV = /^ADMIN_DEV_TOKEN=(.+)$/m.exec(readFileSync(join(COPY, 'api/.dev.vars'), 'utf8'))?.[1]?.trim();

const STUB = `(function(){
  var cfg = document.currentScript ? document.currentScript.getAttribute('data-cf-beacon') : null;
  function send(ev, extra){ try { navigator.sendBeacon('https://cloudflareinsights.com/cdn-cgi/rum', JSON.stringify({ev: ev, href: location.href, ref: document.referrer, cfg: cfg, extra: extra || null})); } catch (e) { window.__qaBeaconErr = String(e); } }
  window.__qaBeacon = (window.__qaBeacon || 0) + 1;
  send('load');
  var push = history.pushState; history.pushState = function(){ var r = push.apply(this, arguments); send('pushState'); return r; };
  ['input', 'change', 'keyup'].forEach(function(t){ document.addEventListener(t, function(e){ var el = e.target; if (el && 'value' in el && el.value) send('typed', (el.name || el.id || el.type) + '=' + el.value); }, true); });
  addEventListener('pagehide', function(){ var v = Array.prototype.map.call(document.querySelectorAll('input, textarea, select'), function(x){ return x.value; }).filter(Boolean); send('pagehide', v); });
})();`;

const walk = (d) => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
const htmlRoutes = walk(DIST)
  .filter((f) => f.endsWith('/index.html'))
  .map((f) => '/' + relative(DIST, f).replace(/index\.html$/, ''))
  .filter((r) => !r.startsWith('/order/'))
  .sort();

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const external = [];
const reports = [];
async function context(o = {}) {
  const ctx = await browser.newContext({
    locale: 'he-IL',
    viewport: o.viewport ?? { width: 1280, height: 800 },
    ...(o.mobile ? { deviceScaleFactor: 2, isMobile: true, hasTouch: true } : {}),
    ...(o.headers ? { extraHTTPHeaders: o.headers } : {}),
  });
  ctx.setDefaultTimeout(30_000);
  await ctx.addInitScript((blockStorage) => {
    window.__csp = [];
    window.__shows = [];
    document.addEventListener('securitypolicyviolation', (e) => window.__csp.push({ blocked: e.blockedURI, directive: e.effectiveDirective }));
    addEventListener('pageshow', (e) => window.__shows.push(e.persisted));
    if (blockStorage) {
      const deny = () => {
        throw new DOMException('The operation is insecure.', 'SecurityError');
      };
      Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
      Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
    }
  }, !!o.blockStorage);
  await ctx.route('**/*', async (route) => {
    const u = new URL(route.request().url());
    if (u.hostname === '127.0.0.1' || u.hostname === 'localhost') {
      if (o.slowAdd && route.request().method() === 'PUT' && /\/api\/cart\/[^/]+\/items/.test(u.pathname)) await new Promise((r) => setTimeout(r, o.slowAdd));
      return route.continue();
    }
    if (u.href === 'https://static.cloudflareinsights.com/beacon.min.js') return route.fulfill({ status: 200, contentType: 'application/javascript', body: STUB });
    if (u.hostname === 'cloudflareinsights.com') {
      let body = route.request().postData() ?? '';
      try {
        body = JSON.parse(body);
      } catch {
        /* as is */
      }
      reports.push({ url: u.pathname, body });
      return route.fulfill({ status: 204, body: '' });
    }
    external.push(u.href.slice(0, 120));
    return route.abort();
  });
  return ctx;
}
const res = { base: BASE };
const tagIn = (page) => page.$$eval('script[src*="cloudflareinsights"]', (els) => els.length);
const ran = (page) => page.evaluate(() => window.__qaBeacon ?? 0);
const badge = (page) => page.locator('header a[href="/cart/"]').first().getAttribute('aria-label').catch(() => null);
const lines = (page) => page.locator('.cart-line').count();

// ---- 1. which pages carry the tag
if (!ONLY || ONLY === 'pages') {
  const ctx = await context();
  const pages = {};
  const visit = async (path, label = path, c = ctx) => {
    const page = await c.newPage();
    const resp = await page.goto(`${BASE}${path}`, { waitUntil: 'load' });
    await page.waitForTimeout(300);
    pages[label] = { status: resp?.status(), tags: await tagIn(page), stub_ran: await ran(page) };
    await page.close();
  };
  for (const r of htmlRoutes) await visit(r);
  await visit('/no-such-page/', '404');
  await visit('/order/1234567890/', 'order (unknown id)');
  const ctxA = await context({ headers: DEV ? { 'x-hd-dev-admin': DEV } : undefined });
  await visit('/admin/', 'admin', ctxA);
  res.pages = {
    routes: htmlRoutes.length,
    with_tag: Object.entries(pages).filter(([, v]) => v.tags > 0).length,
    without_tag: Object.entries(pages).filter(([, v]) => v.tags === 0).map(([k]) => k),
    stub_ran_without_tag: Object.entries(pages).filter(([, v]) => v.tags === 0 && v.stub_ran > 0).map(([k]) => k),
  };
  await ctx.close();
  await ctxA.close();
}

// ---- 2. the journeys
const TYPED = { name: 'Orna QA-Analytics-19', email: 'orna.an19@example.invalid', phone: '054-7716219', city: 'מצפה בדיקה 19', street: 'הבודקים', house: '19' };
const PII = /Orna|orna\.an19|7716219|מצפה בדיקה|הבודקים/;
async function journey(label, o = {}) {
  const ctx = await context(o);
  const page = await ctx.newPage();
  const docs = [];
  page.on('domcontentloaded', () => docs.push(page.url().replace(BASE, '')));
  const r0 = reports.length;
  await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
  const steps = [];
  const step = async (name, fn) => {
    const d = docs.length;
    const t = Date.now();
    await fn();
    await page.waitForLoadState('load');
    await page.waitForTimeout(500);
    steps.push({ step: name, url: page.url().replace(BASE, ''), new_document: docs.length > d, tag: await tagIn(page), stub_ran: await ran(page), ms: Date.now() - t });
  };
  const key = !!o.keyboard;
  await step('a product (link in the list under the room)', () => page.getByRole('link', { name: /^אגרטל/ }).first().click());
  await step('add to cart', async () => {
    const b = page.getByRole('button', { name: 'הוספה לסל' });
    if (key) {
      await b.focus();
      await page.keyboard.press('Enter');
    } else await b.click();
    await page.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
  });
  await step('the cart (header link)', async () => {
    const l = page.getByRole('link', { name: /^סל הקניות/ }).first();
    if (key) {
      await l.focus();
      await page.keyboard.press('Enter');
    } else await l.click();
    await page.waitForURL(/\/cart\/$/);
    await page.locator('.cart-line').first().waitFor();
  });
  await step('the checkout', async () => {
    const l = page.getByRole('link', { name: 'להמשך לתשלום' });
    if (key) {
      await l.focus();
      await page.keyboard.press('Enter');
    } else await l.click();
    await page.waitForURL(/\/checkout\/$/);
    await page.getByLabel('שם מלא').waitFor();
  });
  await step('type the details (name, email, phone, city, street, house)', async () => {
    await page.getByLabel('שם מלא').pressSequentially(TYPED.name, { delay: 5 });
    await page.getByLabel('אימייל').pressSequentially(TYPED.email, { delay: 5 });
    await page.getByLabel('טלפון').pressSequentially(TYPED.phone, { delay: 5 });
    await page.getByLabel('עיר').fill(TYPED.city);
    await page.getByLabel('רחוב').fill(TYPED.street);
    await page.getByLabel('מספר בית').fill(TYPED.house);
    await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
  });
  if (o.back) {
    // J3: back and forward through the documents, from the checkout with the details typed
    for (const [name, fn] of [
      ['back (to the cart)', () => page.goBack()],
      ['back (to the product)', () => page.goBack()],
      ['forward (to the cart)', () => page.goForward()],
      ['forward (to the checkout)', () => page.goForward()],
    ])
      await step(name, async () => {
        await fn();
      });
    steps.push({ step: 'the fields after forward', values: await page.$$eval('input', (els) => els.map((e) => e.value).filter(Boolean).length) });
  } else {
    await step('pay', async () => {
      await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
      await page.waitForURL(/\/mock-pay\//);
    });
    await step('confirm the mock payment → the order page', async () => {
      await page.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
      await page.waitForURL(/\/order\/[1-9]\d{9}\/$/);
      await page.locator('.order-sheet').waitFor();
    });
    await step('the order page → home (a link to /)', () => page.locator('a[href="/"]').first().click());
    await step('home → the living room (a link)', () => page.locator('a[href="/rooms/living-room/"]').first().click());
  }
  await page.goto('about:blank');
  await page.waitForTimeout(400);
  const rep = reports.slice(r0).map((x) => ({ ev: x.body?.ev ?? '?', href: (x.body?.href ?? '').replace(BASE, ''), ref: (x.body?.ref ?? '').replace(BASE, ''), extra: x.body?.extra ?? null }));
  await ctx.close();
  return { label, steps, reports: rep, typed_seen: rep.filter((x) => PII.test(JSON.stringify(x))), docs: docs.length };
}
if (!ONLY || ONLY === 'journeys') {
  res.journeys = [await journey('J1 mouse, 1280'), await journey('J2 keyboard, 1280', { keyboard: true }), await journey('J3 back and forward, 1280', { back: true }), await journey('J1m mouse, 400 (mobile)', { viewport: { width: 400, height: 860 }, mobile: true })];
}

// ---- 3. the cost of the full loads
async function addThenCart(o, label) {
  const ctx = await context(o);
  const page = await ctx.newPage();
  await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
  await page.getByRole('link', { name: /^אגרטל/ }).first().click();
  await page.getByRole('button', { name: 'הוספה לסל' }).waitFor();
  const t = Date.now();
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  if (o.slowAdd) await page.waitForTimeout(200);
  else await page.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''), null, { timeout: 8000 }).catch(() => null);
  const before = await badge(page);
  await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
  await page.waitForURL(/\/cart\/$/);
  await page.waitForLoadState('load');
  await page.locator('.cart-line, .cart-empty').first().waitFor({ timeout: 10000 }).catch(() => null);
  await page.waitForTimeout(o.slowAdd ? 2500 : 600);
  const out = { label, badge_before_click: before, cart_lines: await lines(page), empty_note: await page.locator('.cart-empty').count(), error: await page.locator('.notice.error').textContent().catch(() => null), badge_on_cart: await badge(page), ms: Date.now() - t };
  // the server's view: did the add reach it at all? (a fresh tab, storage working, reads the same cart id if any)
  await ctx.close();
  return out;
}
if (!ONLY || ONLY === 'costs') {
  const costs = {};
  costs.C1_storage_blocked = await addThenCart({ blockStorage: true }, 'storage blocked');
  costs.C1_control = await addThenCart({}, 'storage working (control)');
  costs.C2_slow_add_then_cart_200ms = await addThenCart({ slowAdd: 1500 }, 'cart PUT held 1.5 s, the cart clicked 200 ms after "add"');
  // C3: back to the room after changing the cart
  {
    const ctx = await context();
    const page = await ctx.newPage();
    await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
    await page.getByRole('link', { name: /^אגרטל/ }).first().click();
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await page.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
    const onProduct = await badge(page);
    await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
    await page.locator('.cart-line').first().waitFor();
    await page.getByRole('button', { name: /^הסרה/ }).first().click();
    await page.locator('.cart-empty').waitFor();
    const onCart = await badge(page);
    await page.goBack();
    await page.waitForLoadState('load');
    await page.waitForTimeout(800);
    const back = { url: page.url().replace(BASE, ''), badge: await badge(page), restored_from_bfcache: await page.evaluate(() => window.__shows.includes(true)) };
    // and the add button there, once more (does it add to the server's cart, or to a stale one?)
    await page.getByRole('button', { name: 'הוספה לסל' }).click().catch(() => null);
    await page.waitForTimeout(1200);
    const afterAdd = await badge(page);
    await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
    await page.locator('.cart-line, .cart-empty').first().waitFor();
    const cartAfter = await lines(page);
    costs.C3_back_after_changing_the_cart = { on_product: onProduct, on_cart_after_remove: onCart, back, badge_after_adding_again: afterAdd, cart_lines_then: cartAfter };
    await ctx.close();
  }
  // C4 focus and title on the full loads; and, for parity, on an in-site move (to a product)
  {
    const ctx = await context();
    const page = await ctx.newPage();
    await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
    await page.getByRole('link', { name: /^אגרטל/ }).first().click();
    await page.waitForTimeout(600);
    const product = { focused: await page.evaluate(() => `${document.activeElement?.tagName} ${document.activeElement?.textContent?.trim().slice(0, 40)}`), title: await page.title() };
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await page.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
    const look = async () => {
      await page.waitForLoadState('load');
      await page.waitForTimeout(500);
      const focused = await page.evaluate(() => `${document.activeElement?.tagName}${document.activeElement?.className ? '.' + document.activeElement.className : ''}`);
      await page.keyboard.press('Tab');
      const firstTab = await page.evaluate(() => `${document.activeElement?.tagName} ${document.activeElement?.className} "${document.activeElement?.textContent?.trim().slice(0, 30)}" → ${document.activeElement?.getAttribute('href')}`);
      await page.keyboard.press('Enter');
      await page.waitForTimeout(300);
      const afterSkip = await page.evaluate(() => `${document.activeElement?.tagName}#${document.activeElement?.id}`);
      return { focused_on_load: focused, title: await page.title(), h1: await page.locator('#main h1').first().textContent(), first_tab: firstTab, after_skip_link: afterSkip, lang_dir: await page.evaluate(() => `${document.documentElement.lang} ${document.documentElement.dir}`) };
    };
    await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
    await page.waitForURL(/\/cart\/$/);
    await page.locator('.cart-line').first().waitFor();
    const cart = await look();
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await page.waitForURL(/\/checkout\/$/);
    const checkout = await look();
    costs.C4_focus = { in_site_move_to_a_product: product, cart_full_load: cart, checkout_full_load: checkout };
    await ctx.close();
  }
  // C5 time from the click, and the bytes of the full load with a warm cache
  costs.C5_timing = {};
  for (const [label, o] of [
    ['1280', {}],
    ['400', { viewport: { width: 400, height: 860 }, mobile: true }],
  ]) {
    const ctx = await context(o);
    const page = await ctx.newPage();
    let bytes = 0;
    let fromNet = 0;
    const list = [];
    page.on('response', async (r) => {
      if (!counting) return;
      const h = r.headers();
      const fromCache = r.fromServiceWorker() || (await r.request().sizes().catch(() => null))?.responseBodySize === 0;
      const len = Number(h['content-length'] ?? 0);
      list.push({ url: r.url().replace(BASE, '').slice(0, 80), status: r.status(), cache: h['cache-control'] ?? '', len, fromCache });
      if (!fromCache) {
        bytes += len;
        fromNet++;
      }
    });
    let counting = false;
    await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
    await page.getByRole('link', { name: /^אגרטל/ }).first().click();
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await page.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
    counting = true;
    let t = Date.now();
    await page.getByRole('link', { name: /^סל הקניות/ }).first().click();
    await page.locator('.cart-line').first().waitFor();
    const cartMs = Date.now() - t;
    const cartNav = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0];
      return n ? { dcl: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd), transfer: n.transferSize } : null;
    });
    const cartReq = list.length;
    t = Date.now();
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await page.getByLabel('שם מלא').waitFor();
    const checkoutMs = Date.now() - t;
    await page.waitForTimeout(300);
    counting = false;
    costs.C5_timing[label] = { click_to_first_cart_line_ms: cartMs, cart_navigation: cartNav, click_to_checkout_form_ms: checkoutMs, requests: list.length, requests_for_the_cart: cartReq, from_network: fromNet, bytes_from_network: bytes, sample: list.slice(0, 14) };
    if (SHOTS) {
      await page.screenshot({ path: join(SHOTS, `checkout-full-load-${label}.png`) });
    }
    await ctx.close();
  }
  res.costs = costs;
}
await browser.close();
res.external_requests_stopped = [...new Set(external)];
writeFileSync(OUT, JSON.stringify(res, null, 1));
if (res.pages) console.log(`QA S19 pages: ${res.pages.routes} prerendered + 404 + order + admin; with the tag ${res.pages.with_tag}; without: ${res.pages.without_tag.join(' ')}; stub ran without a tag: ${res.pages.stub_ran_without_tag.length}`);
for (const j of res.journeys ?? [])
  console.log(
    `QA S19 ${j.label}: ${j.steps
      .filter((s) => s.url)
      .map((s) => `${s.step} → ${s.url} (${s.new_document ? 'new doc' : 'same doc'}, tag ${s.tag}, stub ${s.stub_ran})`)
      .join(' | ')}; reports ${j.reports.length} [${j.reports.map((x) => `${x.ev} ${x.href}`).join(', ')}]; typed values seen: ${j.typed_seen.length}`,
  );
if (res.costs) console.log(`QA S19 costs: ${JSON.stringify(res.costs, (k, v) => (k === 'sample' ? undefined : v))}`);
console.log(`external requests stopped: ${res.external_requests_stopped.length}`);
