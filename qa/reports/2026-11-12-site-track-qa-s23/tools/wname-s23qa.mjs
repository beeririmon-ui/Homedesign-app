/**
 * qa-agent, S23 (ת72 (c)): a window.name that ANOTHER site gives the tab must never be read as the cart. The carrier
 * (web/src/state/carrier.ts) reads `hd1:{"c":…}` from window.name when storage is refused. Someone else's cart is made
 * through the API (the vase ×3); a page that is not ours (route-fulfilled, so no DNS and no network) names the tab with
 * that cart, then sends the visitor to our /cart/ in each way a page can name a tab:
 *   assign   window.name = 'hd1:{…}', then a link click (the case frontend-dev's e2e covers)
 *   open     window.open(our cart, 'hd1:{…}'): the popup's name is the target name
 *   target   <a target='hd1:{…}' href=our cart>: a new tab named by the link
 *   sameSite the same as assign, from another port of 127.0.0.1 (same site, another origin: only COOP clears it)
 * each with storage refused and with storage kept. On our page: the name at its first script (an init script), the
 * cart lines shown, "הסל ריק." shown, and (storage kept) the id stored.
 *   QA_COPY=<copy>/site node wname-s23qa.mjs <base> <out.json>
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const [BASE, OUT] = process.argv.slice(2);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const VASE = 'vase-textured-white-stoneware-w90r9';
async function api(method, path, body) {
  const r = await fetch(`${BASE}/api${path}`, { method, headers: body ? { 'content-type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  return { status: r.status, body: await r.json().catch(() => null) };
}
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
// the vase's variant, through a real add
let VARIANT;
{
  const ctx = await browser.newContext();
  const p = await ctx.newPage();
  await p.goto(`${BASE}/p/${VASE}/`, { waitUntil: 'load' });
  await p.getByRole('button', { name: 'הוספה לסל' }).click();
  await p.waitForFunction(() => /סל הקניות, [1-9]/.test(document.querySelector('header a[href="/cart/"]')?.getAttribute('aria-label') ?? ''));
  const id = await p.evaluate(() => localStorage.getItem('hd.cart'));
  VARIANT = (await api('GET', `/cart/${id}`)).body.lines[0].variant_id;
  await ctx.close();
}
const other = (await api('POST', '/cart')).body.id;
await api('PUT', `/cart/${other}/items`, { variant_id: VARIANT, pack: 'set', qty: 3 });
const NAME = `hd1:${JSON.stringify({ c: other })}`;
const ourOrigin = new URL(BASE).origin;
const ourPort = new URL(BASE).port;
const FOREIGN = { crossSite: 'http://foreign-qa.test', sameSite: `http://127.0.0.1:${Number(ourPort) + 9}` };
const page_ = (how) => {
  const to = `${BASE}/cart/`;
  const js = JSON.stringify(NAME);
  if (how === 'assign') return `<!doctype html><title>x</title><script>window.name=${js}</script><a id="go" href="${to}">go</a>`;
  if (how === 'open') return `<!doctype html><title>x</title><button id="go" onclick='window.open(${JSON.stringify(to)}, ${js})'>go</button>`;
  return `<!doctype html><title>x</title><a id="go" target='${NAME.replaceAll("'", '&#39;')}' href="${to}">go</a>`;
};
const NOSTORE = () => {
  const deny = () => {
    throw new DOMException('The operation is insecure.', 'SecurityError');
  };
  Object.defineProperty(window, 'localStorage', { get: deny, configurable: true });
  Object.defineProperty(window, 'sessionStorage', { get: deny, configurable: true });
};
const out = { base: BASE, other_cart_lines: 1, cases: {} };
for (const [how, from] of [
  ['assign', 'crossSite'],
  ['open', 'crossSite'],
  ['target', 'crossSite'],
  ['assign', 'sameSite'],
  ['open', 'sameSite'],
])
  for (const storage of ['refused', 'kept']) {
    const ctx = await browser.newContext({ locale: 'he-IL' });
    if (storage === 'refused') await ctx.addInitScript(NOSTORE);
    await ctx.addInitScript(`(() => { if (location.origin === ${JSON.stringify(ourOrigin)}) window.__qaName0 = window.name; })()`);
    await ctx.route('**/*', (r) => {
      const u = new URL(r.request().url());
      if (u.origin === FOREIGN[from]) return r.fulfill({ status: 200, contentType: 'text/html', body: page_(how) });
      return u.hostname === '127.0.0.1' && u.port === ourPort ? r.continue() : r.abort();
    });
    const page = await ctx.newPage();
    await page.goto(`${FOREIGN[from]}/`, { waitUntil: 'load' });
    const foreignName = await page.evaluate(() => window.name);
    const popupP = how === 'assign' ? null : ctx.waitForEvent('page', { timeout: 8000 });
    await page.locator('#go').click();
    const ours = popupP ? await popupP : page;
    await ours.waitForURL(/\/cart\//, { timeout: 15000 });
    await ours.waitForLoadState('load');
    await ours.waitForFunction(() => document.querySelector('.cart-line') || /הסל ריק\./.test(document.body.innerText), null, { timeout: 15000 }).catch(() => null);
    await sleep(800);
    const st = await ours.evaluate(() => ({
      name_at_first_script: window.__qaName0 ?? null,
      name_now: window.name,
      lines: document.querySelectorAll('.cart-line').length,
      empty_shown: /הסל ריק\./.test(document.body.innerText),
      header: document.querySelector('header a[href="/cart/"]')?.innerText ?? null,
      stored: (() => {
        try {
          return localStorage.getItem('hd.cart');
        } catch {
          return 'refused';
        }
      })(),
    }));
    const key = `${how}:${from}:${storage}`;
    out.cases[key] = { foreign_name_set: foreignName === NAME || how !== 'assign' ? true : foreignName, ...st, name_at_first_script: st.name_at_first_script?.replace(other, '<other>') ?? null, name_now: st.name_now.replace(other, '<other>'), stored: st.stored === other ? '<other>' : st.stored, read_other_cart: st.lines > 0 || st.stored === other };
    console.log(key, JSON.stringify(out.cases[key]));
    await ctx.close();
  }
out.other_cart_qty_after = (await api('GET', `/cart/${other}`)).body.lines.map((l) => l.qty);
await browser.close();
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log('read the other cart in', Object.values(out.cases).filter((c) => c.read_other_cart).length, 'of', Object.keys(out.cases).length, '; other cart qty', out.other_cart_qty_after);
