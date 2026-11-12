/**
 * qa-agent, S17 (2026-11-12): AN1 (Cloudflare Web Analytics) in Chromium, against the PUBLIC build served by its own
 * Worker. No network: every request off 127.0.0.1 is stopped here. Cloudflare's script is replaced by MY STUB (the real
 * one cannot be fetched): it counts that it ran and, as a worst case, reports location.href and document.referrer to
 * cloudflareinsights.com when it loads, on every pushState and on pagehide. So what is measured is (1) which pages carry
 * the tag, (2) where the CSP lets a beacon script load and report and where it stops it (an injected one too: what
 * Cloudflare's automatic setup would do), (3) cookies and storage, (4) the addresses a document that loaded the beacon
 * passes through on a real purchase (a client-side move to the cart and the checkout keeps the document), and what a
 * worst-case beacon could see. Not measured: the real script's own behaviour (spa:false, its reports, cookies).
 *
 *   QA_COPY=<public copy>/site QA_BASE=http://127.0.0.1:8796 QA_OUT=<out.json> node an-browser.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative } from 'node:path';
const COPY = process.env.QA_COPY;
const { chromium } = createRequire(join(COPY, 'package.json'))('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8796';
const OUT = process.env.QA_OUT;
const DIST = join(COPY, 'web/dist');
const DEV = /^ADMIN_DEV_TOKEN=(.+)$/m.exec(readFileSync(join(COPY, 'api/.dev.vars'), 'utf8'))?.[1]?.trim();

const STUB = `(function(){
  var cfg = document.currentScript ? document.currentScript.getAttribute('data-cf-beacon') : null;
  function send(ev){ try { navigator.sendBeacon('https://cloudflareinsights.com/cdn-cgi/rum', JSON.stringify({ev: ev, href: location.href, ref: document.referrer, cfg: cfg})); } catch (e) { window.__qaBeaconErr = String(e); } }
  window.__qaBeacon = (window.__qaBeacon || 0) + 1;
  send('load');
  var push = history.pushState; history.pushState = function(){ var r = push.apply(this, arguments); send('pushState'); return r; };
  addEventListener('pagehide', function(){ send('pagehide'); });
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
const setCookies = [];
async function context(extraHeaders) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 800 }, ...(extraHeaders ? { extraHTTPHeaders: extraHeaders } : {}) });
  ctx.setDefaultTimeout(30_000);
  await ctx.addInitScript(() => {
    window.__csp = [];
    document.addEventListener('securitypolicyviolation', (e) => window.__csp.push({ blocked: e.blockedURI, directive: e.effectiveDirective }));
  });
  await ctx.route('**/*', async (route) => {
    const u = new URL(route.request().url());
    if (u.hostname === '127.0.0.1' || u.hostname === 'localhost') return route.continue();
    if (u.href === 'https://static.cloudflareinsights.com/beacon.min.js')
      return route.fulfill({ status: 200, contentType: 'application/javascript', body: STUB });
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
  ctx.on('response', (r) => {
    const sc = r.headers()['set-cookie'];
    if (sc) setCookies.push({ url: r.url().replace(BASE, ''), cookie: sc.slice(0, 80) });
  });
  return ctx;
}

const pages = {};
async function visit(ctx, path, label = path) {
  const page = await ctx.newPage();
  const resp = await page.goto(`${BASE}${path}`, { waitUntil: 'load' });
  await page.waitForTimeout(400);
  const tags = await page.$$eval('script[src*="cloudflareinsights"]', (els) => els.map((e) => ({ src: e.getAttribute('src'), cfg: e.getAttribute('data-cf-beacon') })));
  const ran = await page.evaluate(() => window.__qaBeacon ?? 0);
  const csp = resp?.headers()['content-security-policy'] ?? null;
  const html = (await resp?.text().catch(() => '')) ?? '';
  pages[label] = {
    status: resp?.status(),
    tag_in_html: /static\.cloudflareinsights\.com\/beacon\.min\.js/.test(html),
    tags: tags.length,
    cfg: tags[0]?.cfg ?? null,
    stub_ran: ran,
    csp_allows_script: csp ? csp.split(',').every((p) => !/script-src/.test(p) || /static\.cloudflareinsights\.com/.test(p.split('script-src')[1].split(';')[0])) : null,
    csp_policies: csp ? csp.split(',').length : 0,
    violations: await page.evaluate(() => window.__csp),
  };
  return page;
}

// ---- 1. every prerendered page, the 404, an order page, the admin
const ctx1 = await context();
for (const r of htmlRoutes) await (await visit(ctx1, r)).close();
await (await visit(ctx1, '/no-such-page/', '404 (/no-such-page/)')).close();
await (await visit(ctx1, '/order/1234567890/', 'order (unknown id)')).close();
const ctxAdmin = await context(DEV ? { 'x-hd-dev-admin': DEV } : undefined);
await (await visit(ctxAdmin, '/admin/', 'admin')).close();

// ---- 2. an injected beacon (Cloudflare's automatic setup) and a direct report, on the private pages
const injected = {};
for (const [ctx, path] of [
  [ctx1, '/cart/'],
  [ctx1, '/checkout/'],
  [ctx1, '/order/1234567890/'],
  [ctxAdmin, '/admin/'],
  [ctx1, '/'],
]) {
  const page = await ctx.newPage();
  await page.goto(`${BASE}${path}`, { waitUntil: 'load' });
  const before = reports.length;
  const load = await page.evaluate(
    () =>
      new Promise((res) => {
        const s = document.createElement('script');
        s.src = 'https://static.cloudflareinsights.com/beacon.min.js?qa-injected';
        s.onload = () => res('loaded');
        s.onerror = () => res('blocked');
        document.head.appendChild(s);
        setTimeout(() => res('timeout'), 3000);
      }),
  );
  const beacon = await page.evaluate(() => {
    try {
      return String(navigator.sendBeacon('https://cloudflareinsights.com/cdn-cgi/rum', 'qa-direct'));
    } catch (e) {
      return `threw ${e.name}`;
    }
  });
  await page.waitForTimeout(500);
  injected[path] = { script: load, sendBeacon: beacon, reports_reached: reports.length - before, violations: await page.evaluate(() => window.__csp.map((v) => v.directive)) };
  await page.close();
}

// ---- 3. a purchase in one tab, as a customer: home → a product → the cart → the checkout → pay → the order page → home
const ctx3 = await context();
const page = await ctx3.newPage();
const docs = [];
page.on('domcontentloaded', () => docs.push(page.url().replace(BASE, '')));
const r0 = reports.length;
await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
const steps = [];
const step = async (name, fn) => {
  const d = docs.length;
  await fn();
  await page.waitForTimeout(600);
  steps.push({ step: name, url: page.url().replace(BASE, ''), new_document: docs.length > d, beacon_loaded_in_this_document: await page.evaluate(() => window.__qaBeacon ?? 0) });
};
await step('a product (link in the list under the room)', () => page.getByRole('link', { name: /^אגרטל/ }).first().click());
await step('add to cart', () => page.getByRole('button', { name: 'הוספה לסל' }).click());
await step('the cart (header link)', () => page.getByRole('link', { name: /^סל הקניות/ }).click());
await step('the checkout', () => page.getByRole('link', { name: 'להמשך לתשלום' }).click());
await step('fill and pay', async () => {
  await page.getByLabel('שם מלא').fill('Orna QA-Analytics');
  await page.getByLabel('אימייל').fill('orna.an17@example.invalid');
  await page.getByLabel('טלפון').fill('054-7716207');
  await page.getByLabel('עיר').fill('מצפה בדיקה');
  await page.getByLabel('רחוב').fill('הבודקים');
  await page.getByLabel('מספר בית').fill('7');
  await page.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
  await page.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
  await page.waitForURL(/\/mock-pay\//);
});
await step('confirm the mock payment → the order page', async () => {
  await page.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
  await page.waitForURL(/\/order\/[1-9]\d{9}\/$/);
  await page.locator('.order-sheet').waitFor();
});
const orderUrl = page.url().replace(BASE, '');
await step('from the order page to the home page (the logo / first link to /)', () => page.locator('a[href="/"]').first().click());
// storage and cookies as the customer's browser holds them at the end (before the tab leaves the site)
const storage = await page.evaluate(() => ({ local: Object.keys(localStorage), session: Object.keys(sessionStorage), cookie: document.cookie })).catch(() => null);
await page.goto('about:blank');
await page.waitForTimeout(500);
const journeyReports = reports.slice(r0).map((x) => ({ ev: x.body?.ev ?? '?', href: (x.body?.href ?? '').replace(BASE, ''), ref: (x.body?.ref ?? '').replace(BASE, '') }));
const piiInReports = journeyReports.filter((x) => /Orna|orna\.an17|7716207|מצפה|הבודקים/.test(JSON.stringify(x)));

// ---- 4. cookies and storage after all of it
const cookies = [...(await ctx1.cookies()), ...(await ctx3.cookies()), ...(await ctxAdmin.cookies())];
await browser.close();

const withTag = Object.entries(pages).filter(([, v]) => v.tags > 0).map(([k]) => k);
const without = Object.entries(pages).filter(([, v]) => v.tags === 0).map(([k]) => k);
const res = {
  base: BASE,
  routes: htmlRoutes.length,
  pages,
  with_tag: withTag,
  without_tag: without,
  stub_ran_without_tag: Object.entries(pages).filter(([, v]) => v.tags === 0 && v.stub_ran > 0).map(([k]) => k),
  injected,
  journey: { steps, order_url_pattern: orderUrl.replace(/\d{10}/, '<10 digits>'), reports: journeyReports, pii_in_reports: piiInReports },
  cookies,
  set_cookie_headers: setCookies,
  storage_after: storage,
  external_requests_stopped: [...new Set(external)],
};
writeFileSync(OUT, JSON.stringify(res, null, 1));
console.log(
  `QA AN1 browser: ${htmlRoutes.length} prerendered pages + 404 + order + admin; with the tag ${withTag.length}: ${withTag.filter((p) => !p.startsWith('/p/')).join(' ')} + ${withTag.filter((p) => p.startsWith('/p/')).length} product pages; without: ${without.join(' ')}`,
);
console.log(`  the stub ran on a page without the tag: ${res.stub_ran_without_tag.length ? res.stub_ran_without_tag.join(' ') : 'none'}`);
console.log(`  injected beacon on the private pages: ${JSON.stringify(injected)}`);
console.log(`  journey: ${steps.map((s) => `${s.step} → ${s.url} (${s.new_document ? 'new document' : 'same document'}, beacon ${s.beacon_loaded_in_this_document ? 'loaded' : 'not loaded'})`).join(' | ')}`);
console.log(`  worst-case reports during the journey: ${journeyReports.map((x) => `${x.ev} ${x.href}${x.ref ? ` (ref ${x.ref})` : ''}`).join(' | ')}; PII in them: ${piiInReports.length}`);
console.log(`  cookies: ${cookies.length}; Set-Cookie headers: ${setCookies.length}; storage after: ${JSON.stringify(storage)}; external requests stopped: ${res.external_requests_stopped.length}`);
