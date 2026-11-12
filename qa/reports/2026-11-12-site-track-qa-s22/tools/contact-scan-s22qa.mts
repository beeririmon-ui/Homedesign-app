/**
 * QA S22, ה23 (my S20 contact-scan, extended): every page at 1280 AND 400 counts the VISIBLE contact blocks (exactly one
 * with contact details, none without), and the order page's "אין גישה" measures the space between the error box and the
 * contact line under it (and between that line and the block), at both widths.
 * With contact details the screenshots mask the address and phone links (the values are made at run time; they are
 * not evidence and must not be published). (S20 header follows.) QA S20, ת61, rendered in Chromium against my own server, after hydration: where the site offers contact, and whether it
 * has any. Every page of the sitemap, the cart, the checkout, 404, and the order page in its states (received, delivered,
 * "אין גישה" in another browser), placed and paid through the API and the mock payment page, the supplier's answers played
 * through the local admin path (the dev token of the copy's api/.dev.vars, a dummy).
 * For each page: the contact blocks ([data-contact]), every mailto: and tel: link, every sentence that offers contact
 * (OFFER), in the visible text, hidden text and every attribute. Without contact details: none of them anywhere. With
 * them: the block on every page, an offer only where a block is on the page, the hrefs, the touch target, dir=ltr.
 * Screenshots of the order page (delivered, "אין גישה"), returns and accessibility, 1280 and 400.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=http://127.0.0.1:8820 --site=<copy>/site --mode=no-contact|contact --out=<json> --shots=<dir>
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';
import { chromium, type Page } from '@playwright/test';

const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!;
const SITE = arg('site')!;
const MODE = arg('mode') as 'contact' | 'no-contact';
const OUT = arg('out')!;
const SHOTS = arg('shots')!;
mkdirSync(SHOTS, { recursive: true });
const OFFER = /כתבו לנו|לכתוב לנו|כתבי לנו|פנו אלינו|לפנות אלינו|צרו קשר|צרו איתנו קשר|יצירת קשר|שלחו לנו|התקשרו|חייגו|contact us|write to us|get in touch/i;
const token = /^ADMIN_DEV_TOKEN=(.+)$/m.exec(readFileSync(join(SITE, 'api/.dev.vars'), 'utf8'))![1]!.trim();
const built = JSON.parse(readFileSync(join(SITE, '.generated/copy.he.json'), 'utf8')) as { contact: { email: string; phone: string | null; phone_href: string | null } | null; strings: Record<string, string | null> };
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8'));

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
const page = await ctx.newPage();

type Got = { visible: number; blocks: number; blockText: string[]; links: string[]; offers: string[]; targets: { href: string; h: number; dir: string | null }[] };
async function read(p: Page): Promise<Got> {
  return p.evaluate((src) => {
    const OFFER = new RegExp(src, 'i');
    const texts = [document.body.innerText, document.body.textContent ?? '', document.title];
    for (const el of Array.from(document.querySelectorAll('*'))) for (const a of Array.from(el.attributes)) if (a.name !== 'class' && a.name !== 'style' && a.name !== 'd') texts.push(a.value);
    const offers = new Set<string>();
    for (const t of texts) for (const s of t.split(/[.!?\n]+/)) if (OFFER.test(s)) offers.add(s.trim().slice(0, 160));
    const blocks = Array.from(document.querySelectorAll('[data-contact]'));
    const visible = blocks.filter((b) => (b as HTMLElement).getClientRects().length > 0 && getComputedStyle(b).visibility !== 'hidden' && (b as HTMLElement).offsetHeight > 0).length;
    const links = Array.from(document.querySelectorAll('a[href^="mailto:"], a[href^="tel:"]')).map((a) => a.getAttribute('href')!);
    const targets = Array.from(document.querySelectorAll('[data-contact] a')).map((a) => ({ href: a.getAttribute('href') ?? '', h: Math.round(a.getBoundingClientRect().height), dir: a.getAttribute('dir') }));
    return { visible, blocks: blocks.length, blockText: blocks.map((b) => (b as HTMLElement).innerText.replace(/\s+/g, ' ').trim()), links, offers: [...offers], targets };
  }, OFFER.source);
}
const rows: { page: string; got: Got; problems: string[] }[] = [];
function judge(name: string, got: Got, opts: { footer?: boolean; blockAfter?: string } = {}) {
  const problems: string[] = [];
  if (MODE === 'no-contact') {
    if (got.blocks) problems.push(`${got.blocks} contact block(s)`);
    if (got.visible) problems.push(`${got.visible} visible`);
    if (got.links.length) problems.push(`links ${got.links.join(' ')}`);
    for (const o of got.offers) problems.push(`offers contact: "${o}"`);
  } else {
    const c = built.contact!;
    if (opts.footer !== false && got.blocks < 1) problems.push('no contact block');
    if (got.visible !== 1) problems.push(`${got.visible} visible contact blocks (want 1)`);
    for (const o of got.offers) if (!got.blocks) problems.push(`offers contact with no block on the page: "${o}"`);
    for (const t of got.targets) {
      if (t.href !== `mailto:${c.email}` && t.href !== `tel:${c.phone_href}`) problems.push(`href ${t.href}`);
      if (t.h < 44) problems.push(`touch target ${t.h}px < 44 (${t.href})`);
      if (t.dir !== 'ltr') problems.push(`dir ${t.dir} (${t.href})`);
    }
  }
  rows.push({ page: name, got, problems });
  console.log(`${problems.length ? 'FAIL' : 'ok  '} ${name.padEnd(52)} visible ${got.visible} blocks ${got.blocks} links ${got.links.length} offers ${got.offers.length}${problems.length ? '  | ' + problems.join('; ') : ''}`);
}
const sitemap = await (await fetch(`${BASE}/sitemap.xml`)).text();
const paths = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]!.replace(/&amp;/g, '&')).pathname);
for (const w of [1280, 400])
  for (const path of [...paths, '/cart/', '/checkout/', '/no-such-page/']) {
    await page.setViewportSize({ width: w, height: 900 });
    await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
    judge(`${path} @${w}`, await read(page));
  }
await page.setViewportSize({ width: 1280, height: 900 });
// ---- the order page ----
const h = { 'cf-connecting-ip': `10.22.${MODE.length}.9`, 'content-type': 'application/json' };
async function api(path: string, init: RequestInit = {}) {
  return fetch(BASE + path, { ...init, headers: { ...h, ...(init.headers ?? {}) } });
}
async function place(): Promise<{ id: string; token: string }> {
  const sold = catalog.products.find((p: { price_agorot: number | null; availability: { status: string } }) => p.price_agorot && p.availability.status === 'available');
  const cart = await (await api('/api/cart', { method: 'POST', body: '{}' })).json();
  await api(`/api/cart/${cart.id}/items`, { method: 'PUT', body: JSON.stringify({ variant_id: sold.variants[0].id, qty: 1 }) });
  const co = await (await api('/api/checkout', { method: 'POST', body: JSON.stringify({ cart_id: cart.id, customer: { full_name: 'בודק קשר', email: 'qa61@example.com', phone: '050-1234567' }, address: { city: 'חיפה', street: 'הנמל', house: '12' }, shipping_method: 'express', consents: { terms: true } }) })).json();
  const session = new URL(co.redirect_url).pathname.split('/').pop();
  await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', 'cf-connecting-ip': h['cf-connecting-ip'] }, body: 'outcome=success', redirect: 'manual' });
  return { id: co.order_id, token: co.order_token };
}
async function waitStatus(o: { id: string; token: string }, s: string) {
  for (let i = 0; i < 60; i++) {
    const v = await (await fetch(`${BASE}/api/orders/${o.id}`, { headers: { 'x-order-token': o.token } })).json();
    if (v.status === s) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`order ${o.id} never reached ${s}`);
}
const supplier = (o: { id: string }, event: string) => api(`/api/admin/orders/${o.id}/mock-supplier`, { method: 'POST', headers: { 'x-hd-dev-admin': token }, body: JSON.stringify({ event }) });
async function openOrder(p: Page, o: { id: string; token: string }) {
  await p.addInitScript(([id, t]) => localStorage.setItem(`hd.order.${id}`, t!), [o.id, o.token]);
  await p.goto(`${BASE}/order/${o.id}/`);
  await p.locator('.order-sheet').waitFor({ timeout: 15_000 });
}
const o = await place();
await waitStatus(o, 'sent_to_supplier');
const op = await ctx.newPage();
await openOrder(op, o);
judge('/order/<id>/ received @1280', await read(op));
await op.setViewportSize({ width: 400, height: 900 });
judge('/order/<id>/ received @400', await read(op));
await op.setViewportSize({ width: 1280, height: 900 });
const received = await op.locator('.order-sheet > p.small.muted').innerText();
await supplier(o, 'shipped');
await waitStatus(o, 'shipped');
await supplier(o, 'delivered');
await waitStatus(o, 'delivered');
await op.reload();
await op.locator('.order-sheet').waitFor();
const delivered = await op.locator('.order-sheet > p.small.muted').innerText();
// the block right after the delivered line (the next element sibling), when there is one
const afterDelivered = await op.evaluate(() => {
  const p = document.querySelector('.order-sheet > p.small.muted');
  const n = p?.nextElementSibling;
  return n ? `${n.tagName.toLowerCase()}.${n.className}${n.hasAttribute('data-contact') ? ' [data-contact]' : ''}` : null;
});
judge('/order/<id>/ delivered @1280', await read(op));
await op.setViewportSize({ width: 400, height: 900 });
judge('/order/<id>/ delivered @400', await read(op));
await op.setViewportSize({ width: 1280, height: 900 });
for (const w of [1280, 400]) {
  await op.setViewportSize({ width: w, height: 900 });
  await op.screenshot({ path: join(SHOTS, `qa22-h23-order-delivered-${w}-${MODE}.png`), fullPage: true, mask: MODE === 'contact' ? [op.locator('[data-contact] a')] : [] });
}
const other = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
await other.addInitScript({ content: 'window.__name = (f) => f;' });
const p2 = await other.newPage();
await p2.goto(`${BASE}/order/${o.id}/`);
await p2.getByRole('alert').waitFor();
const noAccess = await p2.getByRole('alert').innerText();
const noAccessNext = await p2.evaluate(() => Array.from(document.querySelectorAll('.order-no-access-contact, [data-contact]')).map((e) => (e as HTMLElement).innerText.replace(/\s+/g, ' ').trim()));
const gaps: Record<string, unknown> = {};
for (const w of [1280, 400]) {
  await p2.setViewportSize({ width: w, height: 900 });
  await p2.waitForTimeout(200);
  judge(`/order/<id>/ another browser ("אין גישה") @${w}`, await read(p2));
  gaps[w] = await p2.evaluate(() => {
    const box = document.querySelector('.notice.error')?.getBoundingClientRect();
    const line = document.querySelector('.order-no-access-contact')?.getBoundingClientRect();
    const block = document.querySelector('main [data-contact]')?.getBoundingClientRect();
    return box && line ? { box_bottom: box.bottom, line_top: line.top, under_box: Math.round((line.top - box.bottom) * 10) / 10, line_to_block: block ? Math.round((block.top - line.bottom) * 10) / 10 : null } : null;
  });
  await p2.screenshot({ path: join(SHOTS, `qa22-h23-order-no-access-${w}-${MODE}.png`), fullPage: true, mask: MODE === 'contact' ? [p2.locator('[data-contact] a')] : [] });
}
await other.close();
for (const [path, name] of [['/returns/', 'returns'], ['/accessibility/', 'accessibility']] as const) {
  await page.goto(BASE + path);
  await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
  for (const w of [1280, 400]) {
    await page.setViewportSize({ width: w, height: 900 });
    await page.screenshot({ path: join(SHOTS, `qa22-h23-${name}-${w}-${MODE}.png`), fullPage: true, mask: MODE === 'contact' ? [page.locator('[data-contact] a')] : [] });
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}
await browser.close();
const lines = { gaps, received, delivered, afterDelivered, noAccess, noAccessNext, want: { delivered: built.strings['order.next.delivered'], no_access: built.strings['order.no_access'], no_access_contact: built.strings['order.no_access_contact'] } };
const problems = rows.flatMap((r) => r.problems.map((p) => `${r.page}: ${p}`));
if (delivered !== built.strings['order.next.delivered']) problems.push(`delivered line "${delivered}"`);
if (noAccess !== built.strings['order.no_access']) problems.push(`no_access line "${noAccess}"`);
if (MODE === 'contact' && afterDelivered && !afterDelivered.includes('[data-contact]')) problems.push(`after the delivered line: ${afterDelivered}, not the block`);
if (MODE === 'contact') for (const [w, g] of Object.entries(gaps)) if (!g || (g as { under_box: number }).under_box < 24) problems.push(`under "אין גישה" at ${w}: ${JSON.stringify(g)}`);
writeFileSync(OUT, JSON.stringify({ base: BASE, mode: MODE, contact: built.contact, pages: rows.length, problems, lines, rows }, null, 1) + '\n');
console.log(JSON.stringify({ mode: MODE, pages: rows.length, problems, lines }, null, 1));
