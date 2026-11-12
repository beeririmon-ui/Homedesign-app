/**
 * qa-agent, S21 (2026-11-12): ת63 on my isolated copy of 7b42ddc1, with my own tooling (beyond S19's cart-ab.mjs, which
 * samples every 25 ms from the click). A recorder in every new document from its first script (an init script):
 *   - a MutationObserver on the whole document (every DOM change, from the parser's first nodes on), readystatechange,
 *     pageshow (persisted = from the back/forward cache), and every animation frame for 12 s;
 *   - at each, the state a customer could see: "הסל ריק." (rendered text: closed dialogs and display:none are not),
 *     "הסל ריק, אין מה לשלם.", the header's "סל (0)", the story's count, any [aria-busy="true"], the lines, the error,
 *     "לנסות שוב", and the address's fragment; only the changes of state are kept, with their time and source.
 * Cases (each on a phone, 400×860 @2 with touch, and a desktop, 1280×800), a saved cart made through the API first:
 *   flash      the header's cart (click / tap), then "להמשך לתשלום": cart GET held 0, 800, 2000 ms; cold cache per case
 *   direct     /cart/ and /checkout/ typed (a full load with no page before), GET held 2000
 *   slowjs     every /assets/*.js held 2000 ms (the prerendered page alone), GET 0 and 1500; and JS never arriving
 *   warm       the same context twice (warm cache)
 *   keyboard   Tab to the header's cart and Enter
 *   bfcache    product → cart (qty changed to 2) → back → forward
 *   story      the story page's count while the saved cart loads (GET 800/2000), then its cart and "לתשלום"
 *   failed     cart GET answered 500, 503 with the server's words, or the network failing: cart, checkout, header,
 *              story; then "לנסות שוב" once the API answers
 *   addfail    a saved cart with the vase ×2; its load fails; "הוספה לסל" on the vase: what the server holds after
 *   addearly   (the old bug) a saved cart with the vase ×1; "הוספה לסל" pressed while its GET is held 2.5 s
 *   storyearly the story's "המראה כולו לסל" pressed while its GET is held 2.5 s, over a saved cart that has a look item ×3
 *   inflight   the add's PUT held 1.5 s / 6 s; the cart clicked 200 ms after "add": the wait, the keepalive flag, the line
 *   nostorage  storage refused: product → cart → checkout; session history (CDP), Referer of every request, the server's
 *              log (by the caller), hash after reading; the header's cart clicked ON the cart page; the story's "לתשלום"
 *   fixation   storage works, nothing saved: a link /rooms/living-room/#c=<someone else's cart> and /cart/#c=<…>
 *   a11y       axe (WCAG 2.0/2.1 A+AA) on the cart and the checkout while loading and after a failed load
 *
 *   QA_COPY=<copy>/site node cart-flash.mjs <base> <out.json> [case,case…] [screens-dir]
 */
import { createRequire } from 'node:module';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
const req = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = req('playwright-core');
const AXE = req.resolve('axe-core/axe.min.js');
const [BASE, OUT, ONLY = '', SHOTS = ''] = process.argv.slice(2);
const only = ONLY ? new Set(ONLY.split(',')) : null;
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const VIEWS = {
  phone: { viewport: { width: 400, height: 860 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true },
  desktop: { viewport: { width: 1280, height: 800 } },
};
const VASE = 'vase-textured-white-stoneware-w90r9';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---------- the API, from outside the browser ----------
async function api(method, path, body) {
  const r = await fetch(`${BASE}/api${path}`, { method, headers: body ? { 'content-type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  const t = await r.text();
  let j = null;
  try {
    j = JSON.parse(t);
  } catch {}
  return { status: r.status, body: j ?? t };
}
let VARIANT = null;
async function savedCart(lines = [[null, 1]]) {
  const c = await api('POST', '/cart');
  if (c.status !== 201) throw new Error(`cart create ${c.status}`);
  for (const [v, qty] of lines) {
    const r = await api('PUT', `/cart/${c.body.id}/items`, { variant_id: v ?? VARIANT, pack: 'set', qty });
    if (r.status !== 200) throw new Error(`cart put ${r.status} ${JSON.stringify(r.body).slice(0, 200)}`);
  }
  return c.body.id;
}
const serverCart = async (id) => (await api('GET', `/cart/${id}`)).body;

// ---------- the recorder ----------
const RECORDER = `(() => {
  if (window.__qa) return;
  const t0 = performance.now();
  const q = (window.__qa = { t0, changes: [], frames: 0, mo: 0, seen: {}, persisted: [], first_busy_ms: null, lines_ms: null, ready_ms: null, url0: location.href });
  let last = '';
  const vis = (el) => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length) && getComputedStyle(el).visibility !== 'hidden';
  const look = (src) => {
    const b = document.body;
    const text = b ? b.innerText || '' : '';
    const head = document.querySelector('header a[href="/cart/"]');
    const sc = document.getElementById('st-cart-count');
    const st = {
      empty: /הסל ריק\\./.test(text) ? 1 : 0,
      pay_empty: /הסל ריק, אין מה לשלם/.test(text) ? 1 : 0,
      zero: head && /סל\\s*\\(\\s*0\\s*\\)/.test(head.innerText || '') ? 1 : 0,
      head: head ? (head.innerText || '').replace(/\\s+/g, ' ').trim() : null,
      head_label: head ? head.getAttribute('aria-label') : null,
      story_count: sc ? sc.textContent : null,
      story_busy: sc ? sc.closest('button')?.getAttribute('aria-busy') ?? '' : null,
      busy: document.querySelectorAll('[aria-busy="true"]').length,
      loading: document.querySelector('.cart-loading') ? 1 : 0,
      lines: document.querySelectorAll('.cart-line').length + document.querySelectorAll('.summary li').length,
      error: [...document.querySelectorAll('.notice.error, [role="alert"]')].filter(vis).map((e) => e.textContent.trim()).filter(Boolean).join(' | ') || null,
      retry: [...document.querySelectorAll('button')].some((x) => vis(x) && /לנסות שוב/.test(x.textContent || '')) ? 1 : 0,
      hash: location.hash,
    };
    for (const k of ['empty', 'pay_empty', 'zero']) if (st[k]) q.seen[k] = (q.seen[k] || 0) + 1;
    if (st.story_count === '0') q.seen.story_zero = (q.seen.story_zero || 0) + 1;
    const ms = Math.round(performance.now() - t0);
    if (st.busy && q.first_busy_ms === null) q.first_busy_ms = ms;
    if (st.lines && q.lines_ms === null) q.lines_ms = ms;
    const key = JSON.stringify(st);
    if (key !== last) {
      last = key;
      q.changes.push({ ms, src, ...st });
    }
  };
  q.look = look;
  new MutationObserver(() => { q.mo++; look('mo'); }).observe(document, { subtree: true, childList: true, characterData: true, attributes: true });
  document.addEventListener('readystatechange', () => look('rs:' + document.readyState));
  addEventListener('pageshow', (e) => { q.persisted.push(e.persisted); look('pageshow' + (e.persisted ? ':bfcache' : '')); });
  const tick = () => { q.frames++; look('raf'); if (performance.now() - t0 < 12000) requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
})();`;
/** a fetch wrapper: the keepalive flag of every cart write */
const FETCHES = `(() => {
  const f = window.fetch;
  window.__qaFetch = [];
  window.fetch = function (input, init) {
    try {
      const u = typeof input === 'string' ? input : input.url;
      if (/\\/api\\/cart/.test(u)) window.__qaFetch.push({ u: u.replace(/\\/cart\\/[^/]+/, '/cart/<id>'), m: (init && init.method) || 'GET', keepalive: !!(init && init.keepalive), at: Math.round(performance.now()) });
    } catch {}
    return f.apply(this, arguments);
  };
})();`;
const NOSTORE = () => {
  const deny = () => {
    throw new DOMException('The operation is insecure.', 'SecurityError');
  };
  Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
  Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
};

async function context(o = {}) {
  const view = VIEWS[o.view ?? 'desktop'];
  const opts = { locale: 'he-IL', ...view, ...(o.bypassCSP ? { bypassCSP: true } : {}) };
  if (o.cartId) opts.storageState = { cookies: [], origins: [{ origin: BASE, localStorage: [{ name: 'hd.cart', value: o.cartId }] }] };
  const ctx = await browser.newContext(opts);
  ctx.setDefaultTimeout(20_000);
  await ctx.addInitScript(RECORDER);
  await ctx.addInitScript(FETCHES);
  if (o.noStorage) await ctx.addInitScript(NOSTORE);
  const log = (ctx.__reqs = []);
  await ctx.route('**/*', async (route) => {
    const rq = route.request();
    const u = new URL(rq.url());
    if (u.hostname !== '127.0.0.1') return route.abort();
    const m = rq.method();
    log.push({ m, u: u.pathname + u.search + u.hash, referer: (await rq.allHeaders())['referer'] ?? null, t: Date.now() });
    const isGet = m === 'GET' && /^\/api\/cart\/[^/]+\/?$/.test(u.pathname);
    if (isGet && o.failGet) {
      if (o.failGet === 'abort') return route.abort('internetdisconnected');
      if (o.failGet === 503) return route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ error: { code: 'unavailable', message_he: 'השרת עמוס כרגע. נסו שוב בעוד רגע. קוד השגיאה: E-QA21TEST' } }) });
      return route.fulfill({ status: o.failGet, contentType: 'text/plain', body: 'boom' });
    }
    if (isGet && o.slowGet) await sleep(o.slowGet);
    if (o.slowPut && m === 'PUT' && /\/api\/cart\/[^/]+\/items$/.test(u.pathname)) await sleep(o.slowPut);
    if (o.slowJs && /\/assets\/.*\.js$/.test(u.pathname)) {
      if (o.slowJs === 'never') return route.abort();
      await sleep(o.slowJs);
    }
    return route.continue();
  });
  return ctx;
}
const qa = (page) => page.evaluate(() => ({ ...window.__qa, look: undefined, fetches: window.__qaFetch })).catch((e) => ({ error: String(e) }));
const press = async (o, loc) => (VIEWS[o.view ?? 'desktop'].hasTouch ? loc.tap() : loc.click());
const headerCart = (page) => page.locator('header a[href="/cart/"]').first();
async function toProduct(page) {
  await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
  await page.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
}
const verdictOf = (s) => ({ empty: s.seen?.empty ?? 0, pay_empty: s.seen?.pay_empty ?? 0, zero: s.seen?.zero ?? 0, story_zero: s.seen?.story_zero ?? 0 });
const short = (s) => ({ ...verdictOf(s), fetches: s.fetches, first_busy_ms: s.first_busy_ms, lines_ms: s.lines_ms, frames: s.frames, mo: s.mo, persisted: s.persisted, changes: s.changes?.slice(0, 14) });
async function shot(page, name) {
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `${name}.png`) }).catch(() => null);
}
/** wait until the URL's path is `p` and its document's recorder has run for at least `ms` after the lines (or 6 s) */
async function settle(page, ms = 600) {
  await page.waitForFunction(() => window.__qa && (window.__qa.lines_ms !== null || window.__qa.changes.some((c) => c.retry || /הסל ריק/.test(c.error || ''))), null, { timeout: 8000 }).catch(() => null);
  await sleep(ms);
}

const out = { base: BASE, at: new Date().toISOString(), cases: {} };
const run = async (name, fn) => {
  if (only && !only.has(name.split(':')[0])) return;
  const t = Date.now();
  try {
    out.cases[name] = await fn();
  } catch (e) {
    out.cases[name] = { error: String(e).slice(0, 600) };
  }
  out.cases[name].ms = Date.now() - t;
  console.log(`${name}: ${JSON.stringify(out.cases[name]).slice(0, 700)}`);
  writeFileSync(OUT, JSON.stringify(out, null, 1));
};

// the variant the vase page adds by default (the one the API needs)
{
  const ctx = await context();
  const p = await ctx.newPage();
  await p.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  await p.getByRole('button', { name: 'הוספה לסל' }).click();
  await p.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
  const id = await p.evaluate(() => localStorage.getItem('hd.cart'));
  VARIANT = (await serverCart(id)).lines[0].variant_id;
  await ctx.close();
  console.log(`variant ${VARIANT}`);
}

for (const view of ['phone', 'desktop']) {
  // ---- flash: the header's cart, then the checkout
  for (const g of [0, 800, 2000])
    await run(`flash:${view}:get${g}`, async () => {
      const id = await savedCart();
      const ctx = await context({ view, cartId: id, slowGet: g });
      const page = await ctx.newPage();
      await toProduct(page);
      await page.waitForFunction(() => /סל \(1\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''), null, { timeout: 10000 });
      const product = await qa(page);
      const t = Date.now();
      await press({ view }, headerCart(page));
      await page.waitForURL(/\/cart\/$/);
      if (g === 2000) {
        await sleep(700);
        await shot(page, `qa-cart-loading-${view}`);
      }
      await settle(page);
      const cart = await qa(page);
      const tc = Date.now();
      await press({ view }, page.getByRole('link', { name: 'להמשך לתשלום' }));
      await page.waitForURL(/\/checkout\/$/);
      if (g === 2000) {
        await sleep(700);
        await shot(page, `qa-checkout-loading-${view}`);
      }
      await settle(page);
      const checkout = await qa(page);
      await ctx.close();
      return { product: verdictOf(product), cart: short(cart), checkout: short(checkout), click_to_cart_lines_ms: cart.lines_ms, wall_ms: [tc - t, Date.now() - tc] };
    });
  // ---- direct loads
  await run(`direct:${view}`, async () => {
    const id = await savedCart();
    const ctx = await context({ view, cartId: id, slowGet: 2000 });
    const page = await ctx.newPage();
    const r = {};
    for (const p of ['/cart/', '/checkout/', '/rooms/living-room/', `/p/${VASE}/`]) {
      await page.goto(`${BASE}${p}`, { waitUntil: 'load' });
      await settle(page, 2600);
      r[p] = short(await qa(page));
    }
    await ctx.close();
    return r;
  });
  // ---- slow JS: the prerendered page alone for 2 s; and JS that never comes
  for (const [js, g] of [
    [2000, 0],
    [2000, 1500],
    ['never', 0],
  ])
    await run(`slowjs:${view}:js${js}:get${g}`, async () => {
      const id = await savedCart();
      const ctx = await context({ view, cartId: id, slowJs: js, slowGet: g });
      const page = await ctx.newPage();
      const r = {};
      for (const p of ['/cart/', '/checkout/']) {
        await page.goto(`${BASE}${p}`, { waitUntil: 'domcontentloaded' });
        await sleep(400);
        if (js === 'never') await shot(page, `qa-${p.replaceAll('/', '')}-no-js-${view}`);
        await settle(page, js === 'never' ? 3000 : 1000);
        r[p] = short(await qa(page));
      }
      await ctx.close();
      return r;
    });
  // ---- warm cache
  await run(`warm:${view}`, async () => {
    const id = await savedCart();
    const ctx = await context({ view, cartId: id, slowGet: 800 });
    const page = await ctx.newPage();
    const r = [];
    for (let i = 0; i < 2; i++) {
      await toProduct(page);
      await press({ view }, headerCart(page));
      await page.waitForURL(/\/cart\/$/);
      await settle(page);
      r.push(short(await qa(page)));
    }
    await ctx.close();
    return { first: r[0], second: r[1] };
  });
  // ---- the story
  for (const g of [800, 2000])
    await run(`story:${view}:get${g}`, async () => {
      const ctx0 = await context({ view });
      const p0 = await ctx0.newPage();
      await p0.goto(`${BASE}/story/living-room/boho/#list-A`, { waitUntil: 'load' });
      await press({ view }, p0.locator('#look-A'));
      await p0.waitForFunction(() => /^[1-9]/.test(document.getElementById('st-cart-count')?.textContent ?? ''), null, { timeout: 10000 });
      const id = await p0.evaluate(() => localStorage.getItem('hd.cart'));
      const n = await p0.locator('#st-cart-count').textContent();
      await ctx0.close();
      const ctx = await context({ view, cartId: id, slowGet: g });
      const page = await ctx.newPage();
      await page.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
      await page.waitForFunction((n) => document.getElementById('st-cart-count')?.textContent === n, n, { timeout: 10000 });
      const story = await qa(page);
      await press({ view }, page.locator('#st-cart-open'));
      await sleep(300);
      const dialog = await page.evaluate(() => ({ open: !!document.querySelector('#st-cart')?.open, empty_visible: !!document.getElementById('st-cart-empty') && !document.getElementById('st-cart-empty').hidden }));
      await press({ view }, page.locator('#st-cart-pay'));
      await page.waitForURL(/\/checkout\/$/);
      await settle(page);
      const checkout = await qa(page);
      await ctx.close();
      return { saved_count: n, story: short(story), dialog, checkout: short(checkout) };
    });
  // ---- failed loads
  for (const f of [500, 503, 'abort'])
    await run(`failed:${view}:${f}`, async () => {
      const id = await savedCart();
      const ctx = await context({ view, cartId: id, failGet: f });
      const page = await ctx.newPage();
      const r = {};
      for (const p of ['/cart/', '/checkout/', `/p/${VASE}/`, '/story/living-room/boho/']) {
        await page.goto(`${BASE}${p}`, { waitUntil: 'load' });
        await settle(page, 1500);
        r[p] = short(await qa(page));
        if (p.startsWith('/story/') && !(await page.locator('#st-cart-open').count())) r[p].note = 'no story page in this build';
        else if (p.startsWith('/story/')) {
          await press({ view }, page.locator('#st-cart-open'));
          await sleep(300);
          r[p].dialog = await page.evaluate(() => ({ empty_visible: !document.getElementById('st-cart-empty')?.hidden, text: document.querySelector('#st-cart')?.innerText?.slice(0, 200) }));
          await shot(page, `qa-story-cart-failed-${f}-${view}`);
        }
        if (p === '/cart/') await shot(page, `qa-cart-failed-${f}-${view}`);
        if (p === '/checkout/') await shot(page, `qa-checkout-failed-${f}-${view}`);
      }
      // "לנסות שוב" once the API answers again
      await ctx.unrouteAll({ behavior: 'ignoreErrors' });
      await page.goto(`${BASE}/cart/`, { waitUntil: 'load' }).catch(() => null);
      await ctx.close();
      const ctx2 = await context({ view, cartId: id, failGet: f });
      const p2 = await ctx2.newPage();
      await p2.goto(`${BASE}/cart/`, { waitUntil: 'load' });
      await settle(p2, 800);
      await ctx2.unrouteAll({ behavior: 'ignoreErrors' });
      await ctx2.route('**/*', (rt) => (new URL(rt.request().url()).hostname === '127.0.0.1' ? rt.continue() : rt.abort()));
      const retry = p2.getByRole('button', { name: 'לנסות שוב' });
      const hadRetry = await retry.count();
      if (hadRetry) await press({ view }, retry);
      await p2.locator('.cart-line').first().waitFor({ timeout: 8000 }).catch(() => null);
      await sleep(300);
      r.retry = { had_button: hadRetry, after: short(await qa(p2)) };
      await ctx2.close();
      return r;
    });
}

// ---- the rest on the desktop (and the phone where the press itself differs)
await run('keyboard', async () => {
  const id = await savedCart();
  const ctx = await context({ cartId: id, slowGet: 800 });
  const page = await ctx.newPage();
  await toProduct(page);
  await page.waitForFunction(() => /סל \(1\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''));
  await headerCart(page).focus();
  await page.keyboard.press('Enter');
  await page.waitForURL(/\/cart\/$/);
  await settle(page);
  const cart = short(await qa(page));
  const link = page.getByRole('link', { name: 'להמשך לתשלום' });
  await link.focus();
  await page.keyboard.press('Enter');
  await page.waitForURL(/\/checkout\/$/);
  await settle(page);
  const checkout = short(await qa(page));
  const focus = await page.evaluate(() => ({ active: document.activeElement?.tagName, busy_left: document.querySelectorAll('[aria-busy="true"]').length }));
  await ctx.close();
  return { cart, checkout, focus };
});

await run('bfcache', async () => {
  const id = await savedCart();
  const ctx = await context({ cartId: id });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Page.enable');
  const notUsed = [];
  cdp.on('Page.backForwardCacheNotUsed', (e) => notUsed.push({ reasons: e.notRestoredExplanations?.map((x) => x.reason) }));
  await toProduct(page);
  await page.waitForFunction(() => /סל \(1\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''));
  await headerCart(page).click();
  await page.waitForURL(/\/cart\/$/);
  await page.locator('.cart-line').first().waitFor();
  // the quantity to 2 on the cart page
  const plus = page.locator('.cart-line button[aria-label*="הוספת"], .cart-line button:has-text("+")').first();
  let changed = false;
  if (await plus.count()) {
    await plus.click();
    changed = true;
  } else {
    const sel = page.locator('.cart-line select').first();
    if (await sel.count()) {
      await sel.selectOption('2');
      changed = true;
    }
  }
  await page.waitForFunction(() => /סל \(2\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''), null, { timeout: 8000 }).catch(() => null);
  const afterChange = await page.evaluate(() => document.querySelector('header a[href="/cart/"]')?.innerText);
  await page.goBack({ waitUntil: 'load' });
  await sleep(1500);
  const back = short(await qa(page));
  const backHead = await page.evaluate(() => document.querySelector('header a[href="/cart/"]')?.innerText);
  await page.goForward({ waitUntil: 'load' });
  await sleep(1500);
  const fwd = short(await qa(page));
  await ctx.close();
  return { changed, afterChange, back_header: backHead, back, forward: fwd, bfcache_not_used: notUsed, server: (await serverCart(id)).lines?.map((l) => l.qty) };
});

await run('addfail', async () => {
  const id = await savedCart([[null, 2]]);
  const ctx = await context({ cartId: id, failGet: 500 });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  await settle(page, 800);
  const before = await serverCart(id);
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  await sleep(1500);
  const after = await serverCart(id);
  const ls = await page.evaluate(() => localStorage.getItem('hd.cart'));
  const head = await page.evaluate(() => document.querySelector('header a[href="/cart/"]')?.innerText);
  await ctx.close();
  return { saved_qty: before.lines.map((l) => l.qty), after_add_qty: after.lines.map((l) => l.qty), same_id: ls === id, header_after: head };
});

await run('addearly', async () => {
  const id = await savedCart([[null, 1]]);
  const ctx = await context({ cartId: id, slowGet: 2500 });
  const page = await ctx.newPage();
  const t = Date.now();
  await page.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  const btn = page.getByRole('button', { name: 'הוספה לסל' });
  // one press 1.2 s after the load (hydrated locally in ~0.3 s), well inside the 2.5 s GET; the PUTs are recorded
  await sleep(1200);
  await btn.click();
  const presses = 1;
  const pressedAt = Date.now() - t;
  await sleep(3500);
  const after = await serverCart(id);
  const ls = await page.evaluate(() => localStorage.getItem('hd.cart'));
  const s = short(await qa(page));
  await ctx.close();
  return { pressed_at_ms: pressedAt, presses, same_id: ls === id, new_id: ls === id ? null : ls, server_qty_after: after.lines.map((l) => l.qty), header: s.changes.at(-1)?.head, fetches: s.fetches, record: s };
});

await run('storyearly', async () => {
  // a saved cart (through the story, so its lines are the look's), then one of its items set to 3 through the API
  const ctx0 = await context();
  const p0 = await ctx0.newPage();
  await p0.goto(`${BASE}/story/living-room/boho/#list-A`, { waitUntil: 'load' });
  await p0.locator('#look-A').click();
  await p0.waitForFunction(() => /^[1-9]/.test(document.getElementById('st-cart-count')?.textContent ?? ''), null, { timeout: 10000 });
  const id = await p0.evaluate(() => localStorage.getItem('hd.cart'));
  await ctx0.close();
  const saved = await serverCart(id);
  const first = saved.lines[0];
  await api('PUT', `/cart/${id}/items`, { variant_id: first.variant_id, pack: first.pack, qty: 3 });
  const before = (await serverCart(id)).lines.map((l) => `${l.variant_id}:${l.qty}`);
  const ctx = await context({ cartId: id, slowGet: 2500 });
  const page = await ctx.newPage();
  const t = Date.now();
  await page.goto(`${BASE}/story/living-room/boho/#list-A`, { waitUntil: 'load' });
  await page.locator('#look-A').click();
  const pressedAt = Date.now() - t;
  await sleep(4000);
  const after = (await serverCart(id)).lines.map((l) => `${l.variant_id}:${l.qty}`);
  const s = short(await qa(page));
  const live = await page.evaluate(() => document.querySelector('[role="status"], .st-live, #st-live')?.textContent ?? null);
  await ctx.close();
  return { pressed_at_ms: pressedAt, before, after, first_item_before: `${first.variant_id}:3`, story: s, announced: live };
});

for (const [put, label] of [
  [1500, 'put1500'],
  [6000, 'put6000'],
])
  for (const view of ['phone', 'desktop'])
    await run(`inflight:${view}:${label}`, async () => {
      const ctx = await context({ view, slowPut: put });
      const page = await ctx.newPage();
      await page.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
      await sleep(500);
      await press({ view }, page.getByRole('button', { name: 'הוספה לסל' }));
      await sleep(200);
      const t = Date.now();
      await press({ view }, headerCart(page));
      const busy = await page.evaluate(() => document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-busy')).catch(() => 'navigated');
      const fetches = await page.evaluate(() => window.__qaFetch).catch(() => null);
      await page.waitForURL(/\/cart\/$/, { timeout: 12000 });
      const navMs = Date.now() - t;
      await settle(page, 1200);
      const cart = short(await qa(page));
      const id = await page.evaluate(() => localStorage.getItem('hd.cart'));
      await sleep(put === 6000 ? 4000 : 500);
      const server = id ? (await serverCart(id)).lines?.length : null;
      const cartAfterWait = short(await qa(page));
      await ctx.close();
      return { click_to_navigation_ms: navMs, link_busy_while_waiting: busy, fetches, cart, server_lines_later: server, cart_lines_on_page_later: cartAfterWait.changes.at(-1)?.lines };
    });

await run('nostorage', async () => {
  const ctx = await context({ noStorage: true });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await page.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  await page.getByRole('button', { name: 'הוספה לסל' }).click();
  await page.waitForFunction(() => /סל \(1\)/.test(document.querySelector('header a[href="/cart/"]')?.innerText ?? ''));
  const hrefs = await page.evaluate(() => [...document.querySelectorAll('a[href*="#c="]')].map((a) => a.getAttribute('href')));
  await headerCart(page).click();
  await page.waitForURL(/\/cart\//);
  await settle(page);
  const cart = short(await qa(page));
  const cartUrl = page.url();
  // the header's cart clicked on the cart page itself
  await headerCart(page).click();
  await sleep(1500);
  const sameCartUrl = page.url();
  const sameCart = short(await qa(page));
  const h1 = (await cdp.send('Page.getNavigationHistory')).entries.map((e) => e.url.replace(BASE, ''));
  await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
  await page.waitForURL(/\/checkout\//);
  await settle(page);
  const checkout = short(await qa(page));
  const checkoutUrl = page.url();
  // a product's link on the checkout, then back twice
  const h2 = (await cdp.send('Page.getNavigationHistory')).entries.map((e) => e.url.replace(BASE, ''));
  await page.goBack({ waitUntil: 'load' });
  await sleep(800);
  const backUrl = page.url();
  const back = short(await qa(page));
  const refs = ctx.__reqs.filter((r) => (r.referer ?? '').includes('#') || r.u.includes('c=')).map((r) => `${r.m} ${r.u} ref=${r.referer}`);
  const allRefs = [...new Set(ctx.__reqs.map((r) => r.referer).filter(Boolean))].map((x) => x.replace(BASE, ''));
  // the story's "לתשלום" without storage
  await page.goto(`${BASE}/story/living-room/boho/#list-A`, { waitUntil: 'load' });
  let storyCheckout = { changes: [{}], seen: {} };
  if (await page.locator('#look-A').count()) {
    await page.locator('#look-A').click();
    await page.waitForFunction(() => /^[1-9]/.test(document.getElementById('st-cart-count')?.textContent ?? ''), null, { timeout: 10000 });
    await page.locator('#st-cart-open').click();
    await page.locator('#st-cart-pay').click();
    await page.waitForURL(/\/checkout\//);
    await settle(page);
    storyCheckout = short(await qa(page));
  }
  const h3 = (await cdp.send('Page.getNavigationHistory')).entries.map((e) => e.url.replace(BASE, ''));
  await ctx.close();
  return {
    hrefs_with_id_in_dom: hrefs,
    cart: { url: cartUrl.replace(BASE, ''), ...cart },
    header_cart_on_the_cart_page: { url: sameCartUrl.replace(BASE, ''), last: sameCart.changes.at(-1) },
    checkout: { url: checkoutUrl.replace(BASE, ''), ...checkout },
    back_from_checkout: { url: backUrl.replace(BASE, ''), last: back.changes.at(-1) },
    story_checkout: { lines: storyCheckout.changes.at(-1)?.lines, hash: storyCheckout.changes.at(-1)?.hash, ...verdictOf(storyCheckout) },
    session_history: { after_cart_twice: h1, at_checkout: h2, after_story: h3, with_id: [...h1, ...h2, ...h3].filter((u) => u.includes('c=')) },
    requests_with_a_fragment_or_c_in_url_or_referer: refs,
    referers_seen: allRefs,
  };
});

await run('fixation', async () => {
  // someone else's cart (made here through the API, with the vase ×3)
  const other = await savedCart([[null, 3]]);
  const r = {};
  for (const p of [`/rooms/living-room/#c=${other}`, `/cart/#c=${other}`, `/p/${VASE}/#c=${other}`]) {
    const ctx = await context();
    const page = await ctx.newPage();
    await page.goto(`${BASE}${p}`, { waitUntil: 'load' });
    await settle(page, 1200);
    const ls = await page.evaluate(() => localStorage.getItem('hd.cart'));
    const head = await page.evaluate(() => document.querySelector('header a[href="/cart/"]')?.innerText);
    // the customer adds on the product page: whose cart gets it?
    await page.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await sleep(1500);
    const ls2 = await page.evaluate(() => localStorage.getItem('hd.cart'));
    r[p.replace(other, '<other>')] = { adopted: ls === other, header: head, after_add_stored_is_other: ls2 === other, url_after: page.url().replace(BASE, '').replace(other, '<other>') };
    await ctx.close();
  }
  r.other_cart_qty_now = (await serverCart(other)).lines?.map((l) => l.qty);
  return r;
});

await run('a11y', async () => {
  const id = await savedCart();
  const r = {};
  for (const [label, o] of [
    ['loading', { slowGet: 6000 }],
    ['failed', { failGet: 503 }],
  ])
    for (const view of ['phone', 'desktop'])
      for (const p of ['/cart/', '/checkout/']) {
        // axe is injected, so this context bypasses the page's CSP (the page itself is unchanged)
        const ctx = await context({ view, cartId: id, bypassCSP: true, ...o });
        const page = await ctx.newPage();
        await page.goto(`${BASE}${p}`, { waitUntil: 'load' });
        await sleep(label === 'loading' ? 900 : 1500);
        await page.addScriptTag({ path: AXE });
        const res = await page.evaluate(async () => {
          const x = await window.axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] } });
          return x.violations.map((v) => `${v.id}: ${v.nodes.length}`);
        });
        const attrs = await page.evaluate(() => ({
          header: { busy: document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-busy'), label: document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') },
          region_busy: document.querySelector('.cart-loading')?.getAttribute('aria-busy') ?? null,
          sr_text: document.querySelector('.cart-loading .sr-only')?.textContent ?? null,
          alert: document.querySelector('[role="alert"]')?.textContent ?? null,
          retry: !!document.querySelector('.cart-unavailable button'),
          h1: document.querySelector('h1')?.textContent,
          title: document.title,
        }));
        r[`${label}:${view}:${p}`] = { violations: res, ...attrs };
        await ctx.close();
      }
  return r;
});

await browser.close();
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log('done');
