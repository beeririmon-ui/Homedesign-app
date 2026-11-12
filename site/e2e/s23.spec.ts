/**
 * S23, QA S21 (qa/reports/2026-11-12-site-track-qa-s21.md), one test or more per item:
 *  ת72 (a) a link's "#c=" plants nothing: storage works and holds no cart (the room, the cart, a product), or storage is
 *          refused on a page that is not the cart or the checkout;
 *  ת72 (b) storage refused, the header's "סל" pressed on the cart page: no "#c=" in the address or the tab's history;
 *  ת72 (c) storage refused, a real profile: the browser's History database holds no cart id (it travels in window.name),
 *          and a navigation to another site clears window.name;
 *  ת73 (a) the shop: a saved vase ×2, its load fails, "הוספה לסל": refused with the error, still ×2 on the server; the
 *          next add once the API answers: ×3;
 *  ת73 (b) the story: "המראה כולו לסל" pressed while the saved cart's GET is held 2.5 s: ×3 stays ×3, "already" said;
 *  ת74     the story: a failed load (500, 503, no network): the count a blank (not busy, never "0"), the cart's error and
 *          "לנסות שוב" (never "הסל ריק."); the retry once the API answers brings the saved lines;
 *  ת75     the back/forward cache on (Playwright turns it off): back to a product page and to a story page after the
 *          cart changed elsewhere: the count read again;
 *  ה29     an add whose PUT lands 6 s later (its page gone by then), the cart pressed 200 ms after it (the shop) or
 *          reached by a link (from the story): never "הסל ריק." or "סל (0)", and the line once it lands;
 *  ה30     no JavaScript: the cart and the checkout say what to do.
 */
import { expect, test, chromium, type APIRequestContext, type Browser, type BrowserContext, type Page } from '@playwright/test';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const VASE = 'vase-textured-white-stoneware-w90r9';
const STORY = '/story/living-room/boho/';
const executablePath = process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium';
const ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];

/** in every new document, from its first script: what the customer could see, per frame (as S21's spec) */
const SAMPLER = `(() => {
  const s = (window.__hdSeen = { frames: 0, empty: 0, zero: 0, pay_empty: 0, story_zero: 0, lines_at: null, persisted: [] });
  addEventListener('pageshow', (e) => s.persisted.push(e.persisted));
  const look = () => {
    const body = document.body;
    if (!body) return;
    s.frames++;
    const text = body.innerText || '';
    const head = document.querySelector('header a[href="/cart/"]');
    if (/הסל ריק\\./.test(text)) s.empty++;
    if (/הסל ריק, אין מה לשלם/.test(text)) s.pay_empty++;
    if (head && /סל \\(0\\)/.test(head.innerText || head.textContent || '')) s.zero++;
    if (document.getElementById('st-cart-count')?.textContent === '0') s.story_zero++;
    if (s.lines_at === null && document.querySelector('.cart-line, .summary li')) s.lines_at = performance.now();
  };
  document.addEventListener('readystatechange', look);
  const tick = () => {
    look();
    if (s.frames < 1200) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
})();`;
type Seen = { frames: number; empty: number; zero: number; pay_empty: number; story_zero: number; lines_at: number | null; persisted: boolean[] };
const seen = (page: Page) => page.evaluate(() => (window as unknown as { __hdSeen: Seen }).__hdSeen);
const DENY_STORAGE = () => {
  const deny = () => {
    throw new DOMException('The operation is insecure.', 'SecurityError');
  };
  Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
  Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
};
/**
 * `holdPut` (ה29): a PUT of a line never answers the page that sent it, and reaches the server `ms` later, sent by the
 * test: a keepalive write that lands after its page is gone. (The test runner's Playwright, 1.56, aborts a request held
 * by a route once its page navigates and hands the page the error, which a browser never does to a keepalive fetch;
 * QA's tools, on Playwright 1.64, hold it in the network and see the server get it.) A PUT sets an absolute quantity.
 */
type Opt = {
  cartId?: string;
  noStorage?: boolean;
  slowGet?: number;
  failGet?: 500 | 503 | 'abort';
  holdPut?: { ms: number; request: APIRequestContext };
  js?: boolean;
};
async function context(browser: Browser, base: string, o: Opt = {}): Promise<BrowserContext> {
  const ctx = await browser.newContext({
    locale: 'he-IL',
    viewport: { width: 1280, height: 800 },
    javaScriptEnabled: o.js ?? true,
    ...(o.cartId ? { storageState: { cookies: [], origins: [{ origin: base, localStorage: [{ name: 'hd.cart', value: o.cartId }] }] } } : {}),
  });
  await ctx.addInitScript(SAMPLER);
  if (o.noStorage) await ctx.addInitScript(DENY_STORAGE);
  if (o.holdPut) {
    const { ms, request } = o.holdPut;
    await ctx.exposeBinding('__hdHoldPut', (_src, u: string, body: string) => {
      setTimeout(() => void request.put(u, { data: JSON.parse(body) as object }).catch(() => null), ms);
    });
    await ctx.addInitScript(() => {
      const w = window as unknown as { fetch: typeof fetch; __hdHoldPut: (u: string, b: string) => void };
      const f = w.fetch;
      w.fetch = function (input: RequestInfo | URL, init?: RequestInit) {
        const u = typeof input === 'string' ? input : input instanceof URL ? input.pathname : input.url;
        if (init?.method === 'PUT' && /\/api\/cart\/[^/]+\/items$/.test(u)) {
          w.__hdHoldPut(u, String(init.body));
          return new Promise<Response>(() => {});
        }
        return f.call(this, input, init);
      } as typeof fetch;
    });
  }
  await route(ctx, o);
  return ctx;
}
async function route(ctx: BrowserContext, o: Opt): Promise<void> {
  await ctx.route(/\/api\/cart\//, async (r) => {
    const m = r.request().method();
    const u = new URL(r.request().url()).pathname;
    const isGet = m === 'GET' && /^\/api\/cart\/[^/]+\/?$/.test(u);
    if (isGet && o.failGet === 'abort') return r.abort('internetdisconnected');
    if (isGet && o.failGet === 503)
      return r.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'unavailable', message_he: 'השרת עמוס כרגע. נסו שוב בעוד רגע. קוד השגיאה: E-S23TEST2' }),
      });
    if (isGet && o.failGet) return r.fulfill({ status: o.failGet, contentType: 'text/plain', body: 'boom' });
    if (isGet && o.slowGet) await new Promise((ok) => setTimeout(ok, o.slowGet));
    return r.fallback();
  });
}
const headerCart = (page: Page) => page.locator('header a[href="/cart/"]').first();
/** the cart in the header is known (the app is mounted and the saved cart read) */
const known = (page: Page) => expect(page.locator('header a[href="/cart/"][aria-busy="true"]')).toHaveCount(0, { timeout: 20_000 });

// ---------- the API, from outside the browser
let VARIANT = '';
async function savedCart(request: APIRequestContext, lines: [string, number][]): Promise<string> {
  const c = await request.post('/api/cart');
  expect(c.status()).toBe(201);
  const id = ((await c.json()) as { id: string }).id;
  for (const [v, qty] of lines) expect((await request.put(`/api/cart/${id}/items`, { data: { variant_id: v, pack: 'set', qty } })).status()).toBe(200);
  return id;
}
const serverCart = async (request: APIRequestContext, id: string) =>
  ((await (await request.get(`/api/cart/${id}`)).json()) as { lines: { variant_id: string; qty: number }[] }).lines;
/** a saved cart made by the story's "המראה כולו לסל" (its lines are a look's) */
async function storyCart(browser: Browser, base: string): Promise<{ id: string; count: string }> {
  const ctx = await context(browser, base);
  const p = await ctx.newPage();
  await p.goto(`${STORY}#list-A`, { waitUntil: 'load' });
  await p.locator('#look-A').click();
  await expect(p.locator('#st-cart-count')).toHaveText(/^[1-9]/);
  const id = (await p.evaluate(() => localStorage.getItem('hd.cart')))!;
  const count = (await p.locator('#st-cart-count').textContent())!;
  await ctx.close();
  return { id, count };
}

test.describe('S23 (QA S21): the cart id, the story’s cart, the cache and the slow write', () => {
  test.beforeAll(async ({ browser, baseURL }) => {
    // the variant the vase page adds by default
    const ctx = await context(browser, baseURL!);
    const p = await ctx.newPage();
    await p.goto(`/p/${VASE}/`, { waitUntil: 'load' });
    await known(p);
    await p.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(p.locator('.cart-count')).toHaveText('1');
    const id = await p.evaluate(() => localStorage.getItem('hd.cart'));
    const r = await p.request.get(`/api/cart/${id}`);
    VARIANT = ((await r.json()) as { lines: { variant_id: string }[] }).lines[0]!.variant_id;
    await ctx.close();
  });

  test('ת72 (a): storage works and holds no cart: a link with someone else’s #c= plants nothing (room, cart, product)', async ({
    browser,
    baseURL,
    request,
  }) => {
    const other = await savedCart(request, [[VARIANT, 3]]);
    for (const p of [`/rooms/living-room/#c=${other}`, `/cart/#c=${other}`, `/p/${VASE}/#c=${other}`]) {
      const ctx = await context(browser, baseURL!);
      const page = await ctx.newPage();
      await page.goto(p, { waitUntil: 'load' });
      await known(page);
      expect(new URL(page.url()).hash, p).toBe('');
      expect(await page.evaluate(() => localStorage.getItem('hd.cart')), p).toBeNull();
      await expect(page.locator('.cart-count'), p).toHaveText('0');
      if (p.startsWith('/cart/')) await expect(page.getByRole('heading', { name: 'הסל ריק.' })).toBeVisible();
      // the visitor's add goes into a cart of their own
      await page.goto(`/p/${VASE}/`, { waitUntil: 'load' });
      await known(page);
      await page.getByRole('button', { name: 'הוספה לסל' }).click();
      await expect(page.locator('.cart-count')).toHaveText('1');
      const mine = await page.evaluate(() => localStorage.getItem('hd.cart'));
      expect(mine, p).not.toBe(other);
      expect(mine, p).toBeTruthy();
      await ctx.close();
    }
    expect((await serverCart(request, other)).map((l) => l.qty)).toEqual([3]);
  });

  test('ת72 (a): storage refused: a page that is not the cart or the checkout takes no #c= either, and drops it', async ({ browser, baseURL, request }) => {
    const other = await savedCart(request, [[VARIANT, 3]]);
    for (const p of [`/rooms/living-room/#c=${other}`, `/p/${VASE}/#c=${other}`, `${STORY}#c=${other}`]) {
      const ctx = await context(browser, baseURL!, { noStorage: true });
      const page = await ctx.newPage();
      await page.goto(p, { waitUntil: 'load' });
      if (p.startsWith(STORY)) await expect(page.locator('#st-cart-open')).not.toHaveAttribute('aria-busy', 'true');
      else await known(page);
      expect(await page.evaluate(() => window.name), p).not.toContain(other);
      if (p.startsWith(STORY)) await expect(page.locator('#st-cart-count'), p).toHaveText('0');
      else await expect(page.locator('.cart-count'), p).toHaveText('0');
      if (!p.startsWith(STORY)) expect(new URL(page.url()).hash, p).toBe('');
      await ctx.close();
    }
  });

  test('ת72 (b): storage refused, "סל" pressed on the cart page itself: no #c= in the address or the tab’s history; the lines stay', async ({
    browser,
    baseURL,
  }) => {
    const ctx = await context(browser, baseURL!, { noStorage: true });
    const page = await ctx.newPage();
    const cdp = await ctx.newCDPSession(page);
    const urls: string[] = [];
    page.on('framenavigated', (f) => f === page.mainFrame() && urls.push(f.url()));
    await page.goto(`/p/${VASE}/`, { waitUntil: 'load' });
    await known(page);
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('1');
    expect(await page.evaluate(() => [...document.querySelectorAll('a[href*="c="]')].length)).toBe(0);
    await headerCart(page).click();
    await page.waitForURL(/\/cart\/$/);
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await headerCart(page).click();
    await page.waitForLoadState('load');
    await expect(page.locator('.cart-line')).toHaveCount(1);
    await expect(page.locator('.cart-count')).toHaveText('1');
    await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
    await page.waitForURL(/\/checkout\/$/);
    await expect(page.locator('.summary li')).toHaveCount(1);
    const history = ((await cdp.send('Page.getNavigationHistory')) as { entries: { url: string }[] }).entries.map((e) => e.url);
    expect([...urls, ...history].filter((u) => /[#&?]c=/.test(u))).toEqual([]);
    expect(await seen(page)).toMatchObject({ empty: 0, zero: 0, pay_empty: 0 });
    await ctx.close();
  });

  test('ת72 (c): storage refused, a real profile: the History database keeps no cart id; another site does not see window.name', async ({ baseURL }) => {
    const dir = mkdtempSync(join(tmpdir(), 'hd-s23-profile-'));
    try {
      const ctx = await chromium.launchPersistentContext(dir, { executablePath, args: ARGS, headless: true, locale: 'he-IL', baseURL });
      await ctx.addInitScript(DENY_STORAGE);
      const page = ctx.pages()[0] ?? (await ctx.newPage());
      await page.goto(`/p/${VASE}/`, { waitUntil: 'load' });
      await known(page);
      await page.getByRole('button', { name: 'הוספה לסל' }).click();
      await expect(page.locator('.cart-count')).toHaveText('1');
      const name = await page.evaluate(() => window.name);
      const id = /"c":"([^"]+)"/.exec(name)?.[1];
      expect(id, name).toBeTruthy();
      await headerCart(page).click();
      await page.waitForURL(/\/cart\/$/);
      await expect(page.locator('.cart-line')).toHaveCount(1);
      await page.getByRole('link', { name: 'להמשך לתשלום' }).click();
      await page.waitForURL(/\/checkout\/$/);
      await expect(page.locator('.summary li')).toHaveCount(1);
      // a link to another site in the same tab (127.0.0.1 and localhost are two sites): the name does not go along (every
      // page of ours sends COOP same-origin, so the browser moves the tab to a new browsing context group, without it)
      const other = baseURL!.replace('127.0.0.1', 'localhost');
      await page.evaluate((href) => {
        const a = document.createElement('a');
        a.href = href;
        a.id = 'hd-away';
        a.textContent = 'away';
        document.body.prepend(a);
      }, `${other}/accessibility/`);
      await page.locator('#hd-away').click();
      await page.waitForURL(/localhost/);
      const there = await page.evaluate(() => window.name);
      await page.waitForTimeout(1200);
      await ctx.close();
      const { DatabaseSync } = await import('node:sqlite');
      const db = new DatabaseSync(join(dir, 'Default', 'History'), { readOnly: true });
      const rows = db.prepare('SELECT url FROM urls').all() as { url: string }[];
      db.close();
      const urls = rows.map((r) => r.url);
      test
        .info()
        .annotations.push({ type: 'history', description: JSON.stringify({ urls: urls.map((u) => u.replace(baseURL!, '')), name_on_another_site: there }) });
      expect(urls.some((u) => u.includes('/checkout/'))).toBe(true);
      expect(urls.filter((u) => u.includes(id!) || /[#&?]c=/.test(u))).toEqual([]);
      expect(there).toBe('');
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });

  test('ת73 (a): the shop, an add after a load that failed: refused with the error, ×2 stays ×2; once the API answers, ×3', async ({
    browser,
    baseURL,
    request,
  }) => {
    const id = await savedCart(request, [[VARIANT, 2]]);
    const ctx = await context(browser, baseURL!, { cartId: id, failGet: 500 });
    const page = await ctx.newPage();
    await page.goto(`/p/${VASE}/`, { waitUntil: 'load' });
    await expect(headerCart(page)).not.toHaveAttribute('aria-busy', 'true');
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.live-region')).toContainText('לא הצלחנו לטעון את הסל');
    await page.waitForTimeout(500);
    expect((await serverCart(request, id)).map((l) => l.qty)).toEqual([2]);
    expect(await page.evaluate(() => localStorage.getItem('hd.cart'))).toBe(id);
    // the API answers again: the add loads first, then adds to the saved quantity
    await ctx.unrouteAll({ behavior: 'ignoreErrors' });
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await expect(page.locator('.cart-count')).toHaveText('3');
    expect((await serverCart(request, id)).map((l) => l.qty)).toEqual([3]);
    await ctx.close();
  });

  test('ת73 (b): the story, "המראה כולו לסל" pressed while the saved cart’s GET is held 2.5 s: ×3 stays ×3, "already in the cart" said', async ({
    browser,
    baseURL,
    request,
  }) => {
    const { id } = await storyCart(browser, baseURL!);
    const saved = await serverCart(request, id);
    const first = saved[0]!;
    expect((await request.put(`/api/cart/${id}/items`, { data: { variant_id: first.variant_id, pack: 'set', qty: 3 } })).status()).toBe(200);
    const before = await serverCart(request, id);
    const ctx = await context(browser, baseURL!, { cartId: id, slowGet: 2500 });
    const page = await ctx.newPage();
    await page.goto(`${STORY}#list-A`, { waitUntil: 'load' });
    await page.locator('#look-A').click();
    await expect(page.locator('#mag-live')).toContainText('המראה כבר בסל', { timeout: 10_000 });
    const after = await serverCart(request, id);
    expect(after.find((l) => l.variant_id === first.variant_id)?.qty).toBe(3);
    expect(after.map((l) => `${l.variant_id}:${l.qty}`).sort()).toEqual(before.map((l) => `${l.variant_id}:${l.qty}`).sort());
    expect((await seen(page)).story_zero).toBe(0);
    await ctx.close();
  });

  for (const fail of [500, 503, 'abort'] as const)
    test(`ת74: the story’s load fails (${fail}): a blank count, the error and "לנסות שוב", never "0" or "הסל ריק."; the retry brings the lines`, async ({
      browser,
      baseURL,
    }) => {
      const { id, count } = await storyCart(browser, baseURL!);
      const ctx = await context(browser, baseURL!, { cartId: id, failGet: fail });
      const page = await ctx.newPage();
      await page.goto(STORY, { waitUntil: 'load' });
      await expect(page.locator('#st-cart-open')).not.toHaveAttribute('aria-busy', 'true');
      await expect(page.locator('#st-cart-count')).toHaveText('');
      await page.locator('#st-cart-open').click();
      const err = page.locator('#st-cart-error');
      await expect(err).toBeVisible();
      await expect(err).toHaveAttribute('role', 'alert');
      // the server's words with its code (as the API words them), the network's, or the plain line
      await expect(err).toContainText(fail === 503 ? 'E-S23TEST2' : fail === 'abort' ? 'אין חיבור לשרת' : 'לא הצלחנו לטעון את הסל');
      await expect(page.locator('#st-cart-retry')).toBeVisible();
      await expect(page.locator('#st-cart-empty')).toBeHidden();
      await expect(page.locator('#st-cart-pay')).toBeHidden();
      await expect(page.locator('#st-cart-clear')).toBeHidden();
      expect(await seen(page)).toMatchObject({ empty: 0, story_zero: 0 });
      // the API answers again
      await ctx.unrouteAll({ behavior: 'ignoreErrors' });
      await page.locator('#st-cart-retry').click();
      await expect(page.locator('#st-cart-count')).toHaveText(count);
      await expect(page.locator('#st-cart-lines li').first()).toBeVisible();
      await expect(err).toBeHidden();
      await expect(page.locator('#st-cart-pay')).toBeVisible();
      await ctx.close();
    });

  test('ת75: the back/forward cache on: back to a product page and to a story page reads the cart again', async ({ baseURL, request }) => {
    // as a customer's browser: Playwright's Chromium starts with the cache off (QA's tools/bfcache.mjs)
    const b = await chromium.launch({ executablePath, args: ARGS, ignoreDefaultArgs: ['--disable-back-forward-cache'] });
    try {
      const id = await savedCart(request, [[VARIANT, 1]]);
      const ctx = await context(b, baseURL!, { cartId: id });
      const page = await ctx.newPage();
      await page.goto(`${baseURL}/p/${VASE}/`, { waitUntil: 'load' });
      await expect(page.locator('.cart-count')).toHaveText('1');
      await headerCart(page).click();
      await page.waitForURL(/\/cart\/$/);
      await page.getByRole('button', { name: 'הגדלת הכמות' }).click();
      await expect(page.locator('.cart-count')).toHaveText('2');
      await page.goBack({ waitUntil: 'commit' });
      await expect(page.locator('.cart-count')).toHaveText('2', { timeout: 5_000 });
      const shop = await seen(page);
      // the story: its count, then the cart changes on another page, then back
      await page.goto(`${baseURL}${STORY}`, { waitUntil: 'load' });
      await expect(page.locator('#st-cart-count')).toHaveText('2');
      await page.goto(`${baseURL}/p/${VASE}/`, { waitUntil: 'load' });
      await known(page);
      await page.getByRole('button', { name: 'הוספה לסל' }).click();
      await expect(page.locator('.cart-count')).toHaveText('3');
      await page.goBack({ waitUntil: 'commit' });
      await expect(page.locator('#st-cart-count')).toHaveText('3', { timeout: 5_000 });
      const story = await seen(page);
      test.info().annotations.push({ type: 'bfcache', description: JSON.stringify({ shop: shop.persisted, story: story.persisted }) });
      // both pages came back from the cache (else this test proves nothing)
      expect(shop.persisted).toContain(true);
      expect(story.persisted).toContain(true);
      await ctx.close();
    } finally {
      await b.close();
    }
  });

  test('ה29: an add whose PUT takes 6 s, the cart pressed 200 ms later: never "הסל ריק." or "סל (0)", and the line once it lands', async ({
    browser,
    baseURL,
    request,
  }) => {
    const ctx = await context(browser, baseURL!, { holdPut: { ms: 6000, request } });
    const page = await ctx.newPage();
    await page.goto(`/p/${VASE}/`, { waitUntil: 'load' });
    await known(page);
    await page.getByRole('button', { name: 'הוספה לסל' }).click();
    await page.waitForTimeout(200);
    await headerCart(page).click();
    await page.waitForURL(/\/cart\/$/, { timeout: 12_000 });
    await expect(page.locator('.cart-line')).toHaveCount(1, { timeout: 15_000 });
    await expect(page.locator('.cart-count')).toHaveText('1');
    expect(await seen(page)).toMatchObject({ empty: 0, zero: 0 });
    expect(await page.evaluate(() => window.name)).toBe('');
    await ctx.close();
  });

  test('ה29: from the story, a look whose first PUT takes 6 s, then a link to the cart: never empty, and the line once it lands', async ({
    browser,
    baseURL,
    request,
  }) => {
    const ctx = await context(browser, baseURL!, { holdPut: { ms: 6000, request } });
    const page = await ctx.newPage();
    await page.goto(`${STORY}#list-A`, { waitUntil: 'load' });
    await expect(page.locator('#st-cart-open')).not.toHaveAttribute('aria-busy', 'true');
    await page.locator('#look-A').click();
    await page.waitForTimeout(400);
    // a link the page follows (a typed address starts the tab afresh: window.name does not go along, README)
    await page.evaluate(() => location.assign('/cart/'));
    await page.waitForURL(/\/cart\/$/);
    await expect(page.locator('.cart-line').first()).toBeVisible({ timeout: 15_000 });
    expect(await seen(page)).toMatchObject({ empty: 0, zero: 0 });
    await ctx.close();
  });

  test('ה30: without JavaScript the cart and the checkout say what to do (and never "empty")', async ({ browser, baseURL }) => {
    const ctx = await context(browser, baseURL!, { js: false });
    const page = await ctx.newPage();
    for (const p of ['/cart/', '/checkout/']) {
      await page.goto(p, { waitUntil: 'load' });
      // (Playwright's text matcher skips <noscript>: the line is found by its class)
      await expect(page.locator('.cart-noscript'), p).toBeVisible();
      await expect(page.locator('.cart-noscript'), p).toHaveText(/^הסל והתשלום פועלים עם JavaScript\./);
      await expect(page.getByText('הסל ריק')).toHaveCount(0);
    }
    await ctx.close();
  });
});
