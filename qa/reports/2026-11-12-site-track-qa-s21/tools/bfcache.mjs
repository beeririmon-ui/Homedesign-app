/**
 * qa-agent, S21 (ת63, back/forward cache): Playwright starts Chromium with the back/forward cache off; here it is on
 * (its switch removed from the default arguments), as in a customer's browser. A saved cart with the vase ×1:
 *   A  product page → the header's cart → the quantity to 2 → back: is the product page restored from the cache, and
 *      what does its header say (a stale "סל (1)"?) → forward
 *   B  the header's cart pressed while the cart GET is held 2 s, then back at once (the product page left mid-load)
 *   C  storage refused: product → the header's cart (#c= read and removed) → back → forward: the cart page restored?
 * Every state is recorded from the first script of every document, as cart-flash.mjs does (the same recorder).
 *   QA_COPY=<copy>/site node bfcache.mjs <base> <out.json>
 */
import { createRequire } from 'node:module';
import { writeFileSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
const req = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = req('playwright-core');
const [BASE, OUT] = process.argv.slice(2);
const here = dirname(fileURLToPath(import.meta.url));
const src = readFileSync(join(here, 'cart-flash.mjs'), 'utf8');
const RECORDER = eval(src.slice(src.indexOf('const RECORDER = `') + 'const RECORDER = '.length, src.indexOf('`;', src.indexOf('const RECORDER = `')) + 1));
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', ignoreDefaultArgs: ['--disable-back-forward-cache'], args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const VASE = 'vase-textured-white-stoneware-w90r9';
async function api(method, path, body) {
  const r = await fetch(`${BASE}/api${path}`, { method, headers: body ? { 'content-type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  return { status: r.status, body: await r.json().catch(() => null) };
}
async function savedCart(qty = 1) {
  const c = await api('POST', '/cart');
  await api('PUT', `/cart/${c.body.id}/items`, { variant_id: `${VASE}:large`, pack: 'set', qty });
  return c.body.id;
}
async function ctxFor(o = {}) {
  const ctx = await b.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 800 }, ...(o.cartId ? { storageState: { cookies: [], origins: [{ origin: BASE, localStorage: [{ name: 'hd.cart', value: o.cartId }] }] } } : {}) });
  await ctx.addInitScript(RECORDER);
  if (o.noStorage)
    await ctx.addInitScript(() => {
      const deny = () => {
        throw new DOMException('The operation is insecure.', 'SecurityError');
      };
      Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
      Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
    });
  await ctx.route('**/*', async (r) => {
    const u = new URL(r.request().url());
    if (u.hostname !== '127.0.0.1') return r.abort();
    if (o.slowGet && r.request().method() === 'GET' && /^\/api\/cart\/[^/]+\/?$/.test(u.pathname)) await sleep(o.slowGet);
    return r.continue();
  });
  return ctx;
}
const state = (p) =>
  p.evaluate(() => ({
    url: location.pathname + location.hash,
    head: document.querySelector('header a[href="/cart/"]')?.innerText,
    busy: document.querySelectorAll('[aria-busy="true"]').length,
    lines: document.querySelectorAll('.cart-line').length,
    seen: window.__qa?.seen,
    persisted: window.__qa?.persisted,
  }));
const head = (p) => p.evaluate(() => document.querySelector('header a[href="/cart/"]')?.innerText);
async function watch(p) {
  const cdp = await p.context().newCDPSession(p);
  await cdp.send('Page.enable');
  const notUsed = [];
  cdp.on('Page.backForwardCacheNotUsed', (e) => notUsed.push((e.notRestoredExplanations ?? []).map((x) => x.reason)));
  return notUsed;
}
const out = {};
{
  const id = await savedCart(1);
  const ctx = await ctxFor({ cartId: id });
  const p = await ctx.newPage();
  const notUsed = await watch(p);
  await p.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  await p.waitForFunction(() => /סל \(1\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''));
  await sleep(500);
  await p.locator('header a[href="/cart/"]').first().click();
  await p.waitForURL(/\/cart\/$/);
  await p.locator('.cart-line').first().waitFor();
  const sel = p.locator('.cart-line select').first();
  const plus = p.locator('.cart-line button').filter({ hasText: '+' }).first();
  if (await sel.count()) await sel.selectOption('2');
  else if (await plus.count()) await plus.click();
  await p.waitForFunction(() => /סל \(2\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''), null, { timeout: 8000 }).catch(() => null);
  const cartHead = await head(p);
  await p.goBack({ waitUntil: 'commit' });
  await sleep(1200);
  const back = await state(p);
  await sleep(3000);
  const backLater = await state(p);
  await p.goForward({ waitUntil: 'commit' });
  await sleep(1200);
  const fwd = await state(p);
  out.A = { cart_header_after_change: cartHead, back, back_after_4s: backLater, forward: fwd, bfcache_not_used: notUsed };
  await ctx.close();
}
{
  const id = await savedCart(1);
  const ctx = await ctxFor({ cartId: id, slowGet: 2000 });
  const p = await ctx.newPage();
  const notUsed = await watch(p);
  await p.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  await sleep(300);
  await p.locator('header a[href="/cart/"]').first().click();
  await p.waitForURL(/\/cart\/$/);
  await sleep(300);
  await p.goBack({ waitUntil: 'commit' });
  await sleep(300);
  const back = await state(p);
  await sleep(2600);
  const backLater = await state(p);
  out.B = { back_300ms: back, back_3s: backLater, bfcache_not_used: notUsed };
  await ctx.close();
}
{
  const ctx = await ctxFor({ noStorage: true });
  const p = await ctx.newPage();
  const notUsed = await watch(p);
  await p.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  await p.getByRole('button', { name: 'הוספה לסל' }).click();
  await p.waitForFunction(() => /סל \(1\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''));
  await p.locator('header a[href="/cart/"]').first().click();
  await p.waitForURL(/\/cart\//);
  await p.locator('.cart-line').first().waitFor();
  const cart = await state(p);
  await p.goBack({ waitUntil: 'commit' });
  await sleep(1000);
  const back = await state(p);
  await p.goForward({ waitUntil: 'commit' });
  await sleep(1500);
  const fwd = await state(p);
  out.C = { cart, back, forward: fwd, bfcache_not_used: notUsed };
  await ctx.close();
}
await b.close();
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
