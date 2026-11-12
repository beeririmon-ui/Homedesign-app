/**
 * QA S20, ת62, rendered: the build whose provider declares ONLY order_confirmation (setup-email-copy.sh, qa-oc). In the
 * browser against its own server: the checkout (hint, boxes, total), the order page (received, shipped, delayed, another
 * browser), a product on hold, the privacy policy, and every page of the sitemap. Every promise read on these pages must
 * be a sentence of an email line whose needs are all order_confirmation; my own words for shipping, delay, invoice,
 * back in stock and marketing must never be promised.
 *   cd <email copy>/site && node node_modules/tsx/dist/cli.mjs <this> --base=http://127.0.0.1:8822 --site=<copy>/site --tools=<qa tools> --out=<json> --shots=<dir>
 */
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium, type Page } from '@playwright/test';

const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const BASE = arg('base')!;
const SITE = arg('site')!;
const TOOLS = arg('tools')!;
const OUT = arg('out')!;
const SHOTS = arg('shots')!;
const L = (await import(pathToFileURL(join(SITE, 'tools/lib/promises.ts')).href)) as typeof import('../build-s20/site/tools/lib/promises');
const { ORDER_DELAY_HE } = (await import(pathToFileURL(join(SITE, 'shared/src/constants.ts')).href)) as { ORDER_DELAY_HE: string };
const built = JSON.parse(readFileSync(join(SITE, '.generated/copy.he.json'), 'utf8')) as { capabilities: string[]; strings: Record<string, string | null> };
const src = L.loadCopy(join(SITE, 'copy/promises.he.json'));
const allowed = L.allowedPromises(src, built.capabilities as never);
const catalog = JSON.parse(readFileSync(join(SITE, '.generated/catalog.public.json'), 'utf8'));
const token = /^ADMIN_DEV_TOKEN=(.+)$/m.exec(readFileSync(join(SITE, 'api/.dev.vars'), 'utf8'))![1]!.trim();
const NOT_REAL: [string, RegExp][] = [
  ['invoice_email', /חשבוני|קבלה/u],
  ['shipping_update', /משלוח|מעקב|יוצאת|החבילה/u],
  ['delay_notice', /מועד המסירה|עיכוב|יתעכב|ישתנה|איחור/u],
  ['back_in_stock', /חוזר|למלאי|במלאי|לבקש עדכון/u],
  ['marketing', /דיוור שיווקי נשלח|מוצרים חדשים|ניוזלטר|מבצע/u],
];
const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
await ctx.addInitScript({ content: 'window.__name = (f) => f;' });
const results: Record<string, unknown> = { capabilities: built.capabilities, allowed: [...allowed] };
const problems: string[] = [];
const promisesSeen = new Map<string, Set<string>>();
async function scan(p: Page, name: string) {
  const texts: string[] = await p.evaluate(() => {
    const out = [document.body.innerText, document.body.textContent ?? '', document.title];
    for (const el of Array.from(document.querySelectorAll('*'))) for (const a of Array.from(el.attributes)) if (a.name !== 'class' && a.name !== 'style' && a.name !== 'd') out.push(a.value);
    return out;
  });
  for (const t of texts)
    for (const f of L.promiseFindings(t)) {
      (promisesSeen.get(f.sentence) ?? promisesSeen.set(f.sentence, new Set()).get(f.sentence)!).add(name);
      if (!allowed.has(f.sentence)) problems.push(`${name}: a promise not allowed with ${built.capabilities.join('+')}: "${f.sentence}"`);
      for (const [cap, rx] of NOT_REAL) if (rx.test(f.sentence.replace(/שירות ה\S+|חברת ה\S+/gu, ''))) problems.push(`${name}: promises ${cap}: "${f.sentence}"`);
    }
}
const h = { 'cf-connecting-ip': '10.62.0.1', 'content-type': 'application/json' };
const api = (path: string, init: RequestInit = {}) => fetch(BASE + path, { ...init, headers: { ...h, ...(init.headers ?? {}) } });
const sold = catalog.products.find((p: { slot: string; price_agorot: number | null; availability: { status: string } }) => p.price_agorot && p.availability.status === 'available');
async function place() {
  const cart = await (await api('/api/cart', { method: 'POST', body: '{}' })).json();
  await api(`/api/cart/${cart.id}/items`, { method: 'PUT', body: JSON.stringify({ variant_id: sold.variants[0].id, qty: 1 }) });
  const co = await (await api('/api/checkout', { method: 'POST', body: JSON.stringify({ cart_id: cart.id, customer: { full_name: 'בודקת יכולות', email: 'qa62@example.com', phone: '050-1234567' }, address: { city: 'חיפה', street: 'הנמל', house: '12' }, shipping_method: 'express', consents: { terms: true } }) })).json();
  const session = new URL(co.redirect_url).pathname.split('/').pop();
  await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', 'cf-connecting-ip': '10.62.0.1' }, body: 'outcome=success', redirect: 'manual' });
  return { id: co.order_id as string, token: co.order_token as string };
}
async function waitStatus(o: { id: string; token: string }, s: string) {
  for (let i = 0; i < 60; i++) {
    if ((await (await fetch(`${BASE}/api/orders/${o.id}`, { headers: { 'x-order-token': o.token } })).json()).status === s) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`never ${s}`);
}
const page = await ctx.newPage();
// O1 the checkout
{
  const cart = await (await api('/api/cart', { method: 'POST', body: '{}' })).json();
  await api(`/api/cart/${cart.id}/items`, { method: 'PUT', body: JSON.stringify({ variant_id: sold.variants[0].id, qty: 1 }) });
  await page.addInitScript((id) => localStorage.setItem('hd.cart', id), cart.id);
  await page.goto(BASE + '/checkout/');
  await page.getByLabel('אימייל').waitFor();
  const r = { email_hint: await page.locator('#h-email').innerText(), checkboxes: await page.getByRole('checkbox').count(), total_note: await page.locator('.summary .small.muted').innerText() };
  results.O1 = r;
  if (r.email_hint !== built.strings['checkout.email_hint'] || r.checkboxes !== 1 || r.total_note !== built.strings['checkout.total_note']) problems.push(`O1 ${JSON.stringify(r)}`);
  await page.screenshot({ path: join(SHOTS, 'qa-oc-checkout-1280.png'), fullPage: true });
  await scan(page, 'checkout');
}
// O2 the order page
{
  const o = await place();
  await waitStatus(o, 'sent_to_supplier');
  const op = await ctx.newPage();
  await op.addInitScript(([id, t]) => localStorage.setItem(`hd.order.${id}`, t!), [o.id, o.token]);
  await op.goto(`${BASE}/order/${o.id}/`);
  await op.locator('.order-sheet').waitFor();
  const received = await op.locator('.order-sheet > p.small.muted').innerText();
  await scan(op, 'order received');
  await op.screenshot({ path: join(SHOTS, 'qa-oc-order-received-1280.png'), fullPage: true });
  await api(`/api/admin/orders/${o.id}/mock-supplier`, { method: 'POST', headers: { 'x-hd-dev-admin': token }, body: JSON.stringify({ event: 'shipped' }) });
  await waitStatus(o, 'shipped');
  await op.reload();
  await op.locator('.order-sheet').waitFor();
  const shipped = await op.locator('.order-sheet > p.small.muted').innerText();
  await scan(op, 'order shipped');
  const other = await browser.newContext({ locale: 'he-IL' });
  const p2 = await other.newPage();
  await p2.goto(`${BASE}/order/${o.id}/`);
  await p2.getByRole('alert').waitFor();
  const noAccess = await p2.getByRole('alert').innerText();
  await scan(p2, 'order, another browser');
  await p2.screenshot({ path: join(SHOTS, 'qa-oc-order-no-access-1280.png'), fullPage: true });
  await other.close();
  const stuck = await place();
  await waitStatus(stuck, 'sent_to_supplier');
  execFileSync('bash', [join(TOOLS, 'd1-exec.sh'), `UPDATE supplier_shipments SET status = 'failed', supplier_order_id = NULL, reach = 'none', attempts = 5, last_error = 'refused' WHERE order_id = '${stuck.id}'; UPDATE orders SET status = 'supplier_error' WHERE id = '${stuck.id}';`], { env: { ...process.env, QA_COPY: SITE }, stdio: 'ignore' });
  const sp = await ctx.newPage();
  await sp.addInitScript(([id, t]) => localStorage.setItem(`hd.order.${id}`, t!), [stuck.id, stuck.token]);
  await sp.goto(`${BASE}/order/${stuck.id}/`);
  await sp.locator('.order-delay').waitFor();
  await sp.waitForTimeout(500);
  const delay = await sp.locator('.order-delay').innerText();
  await scan(sp, 'order delayed');
  results.O2 = { received, shipped, noAccess, delay };
  if (received !== built.strings['order.next.received']) problems.push(`O2 received "${received}"`);
  if (noAccess !== built.strings['order.no_access']) problems.push(`O2 no_access "${noAccess}"`);
  if (delay !== ORDER_DELAY_HE) problems.push(`O2 delay "${delay}" (want only "${ORDER_DELAY_HE}")`);
}
// O3 a product on hold, O4 the privacy policy, and the sitemap
{
  const held = catalog.products.find((p: { availability: { status: string } }) => p.availability.status !== 'available');
  const sitemap = await (await fetch(`${BASE}/sitemap.xml`)).text();
  const paths = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => new URL(m[1]!.replace(/&amp;/g, '&')).pathname);
  for (const path of [...paths, '/cart/', '/no-such-page/']) {
    await page.goto(BASE + path, { waitUntil: 'domcontentloaded' });
    await page.waitForLoadState('networkidle', { timeout: 8_000 }).catch(() => undefined);
    await scan(page, path);
    if (path.includes(held.id)) {
      results.O3 = { product: held.id, forms: await page.locator('.waitlist form, form.waitlist-form').count(), buttons: await page.locator('.waitlist button').count(), status: await page.locator('.waitlist-status').innerText().catch(() => null) };
    }
    if (path === '/privacy/') {
      const t = await page.locator('main').innerText();
      results.O4 = { processors_email: t.includes(built.strings['privacy.processors']!), marketing_no_email: t.includes(built.strings['privacy.marketing']!) };
    }
  }
}
await browser.close();
results.promises_seen = Object.fromEntries([...promisesSeen].map(([s, p]) => [s, [...p].length]));
results.problems = problems;
writeFileSync(OUT, JSON.stringify(results, null, 1) + '\n');
console.log(JSON.stringify(results, null, 1));
