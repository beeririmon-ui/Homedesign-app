/**
 * qa-agent, 2026-11-11 (ת8/ת12 at b94c5bc1): the names a buyer reads, on the pages, for the nine variants of ת8 (the
 * designer's table, docs/proposals/names-labels-he-2026-11-10.md, read from that file, not from the e2e) and every piece
 * of the warm-modern house's three sets (added with house=warm-modern, as the set panel does). One cart through the API;
 * then the site's /cart/, /checkout/ (filled and sent through the UI), the mock payment, the order page. Each page's
 * whole visible text is scanned for Latin letters (a unit after a number, 3000K, aside), and the nine lines are compared
 * to the table, on every page. The order's snapshot (order_items.name_he, what the invoice is issued from) is read
 * from D1 by the caller (wrangler d1 execute) with the order id this prints.
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_REPO=<repo> QA_OUT=<qa folder> node lines-pages.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const gen = (f) => JSON.parse(readFileSync(join(COPY, '.generated', f), 'utf8'));

// the designer's table, parsed from the proposal
const md = readFileSync(join(process.env.QA_REPO, 'docs/proposals/names-labels-he-2026-11-10.md'), 'utf8');
const sec = md.split('## תשעת הווריאנטים של ת8, בכלל החדש')[1].split('\n## ')[0];
const table = sec
  .split('\n')
  .filter((l) => /^\| \d \|/.test(l))
  .map((l) => l.split('|').map((x) => x.trim()))
  .map((c) => ({ n: Number(c[1]), where: c[2], line: c[3] }));
// the nine variants: card + option values (from S6–S7 ת8 and the designer's ninth)
const NINE = [
  ['cushions-cj-washed-cotton-frayed', ['50x50', 'white']],
  ['cushions-cj-washed-cotton-frayed', ['50x50', 'earthy-orange']],
  ['cushions-cj-washed-cotton-frayed', ['30x50', 'moss-green']],
  ['sofa-cover-cj-washed-hemp-throw', ['150x200', 'raw-jute-color']],
  ['sofa-cover-cj-cotton-muslin-fringe', ['150x200', 'flax-brown']],
  ['cushions-cj-boucle-teddy', ['milk-tea-color', '50x50']],
  ['cushions-cj-boucle-teddy', ['white', '50x50']],
  ['planter-cj-seagrass-belly', ['yellow', '35x37-cm']],
  ['cushions-cj-wide-stripe-corduroy-light-green', ['camel']],
];
const cats = [gen('catalog.full.json'), gen('catalog.story.full.json')];
function variantOf(card, values) {
  for (const c of cats) {
    const p = c.products.find((x) => x.card_id === card);
    const v = p?.variants_full?.find((x) => x.active && x.id.slice(x.id.indexOf(':') + 1).split('+').sort().join() === [...values].sort().join());
    if (v) return v.id;
  }
  return null;
}
const nine = NINE.map(([card, values], i) => ({ n: i + 1, card, values, variant: variantOf(card, values), want: table[i]?.line }));
const house = gen('house.living-room.warm-modern.json');
const setPieces = house.sets.flatMap((s) => s.items.map((it) => ({ set: s.id, variant: it.variant_id, label: `${it.name_he} · ${it.option_he}` })));

const latin = (s) => /[A-Za-z]/.test(String(s).replace(/\d+\s*K\b/g, ''));
const latinWords = (s) => [...new Set((String(s).replace(/\d+\s*K\b/g, '').match(/[A-Za-z][A-Za-z0-9'’-]*/g) ?? []))];
const h = { 'content-type': 'application/json', 'cf-connecting-ip': '198.51.100.131' };
const api = async (path, init = {}) => {
  const r = await fetch(`${BASE}${path}`, { ...init, headers: { ...h, ...(init.headers ?? {}) } });
  return { status: r.status, body: await r.json().catch(() => null) };
};
const cart = (await api('/api/cart', { method: 'POST' })).body.id;
const puts = [];
for (const x of [...nine.map((n) => ({ variant: n.variant, house: undefined })), ...setPieces.map((p) => ({ variant: p.variant, house: 'warm-modern' }))]) {
  if (!x.variant) continue;
  const r = await api(`/api/cart/${cart}/items`, { method: 'PUT', body: JSON.stringify({ variant_id: x.variant, pack: 'set', qty: 1, ...(x.house ? { house: x.house } : {}) }) });
  puts.push({ variant: x.variant, status: r.status, error: r.body?.error ?? null });
}
const apiCart = (await api(`/api/cart/${cart}`)).body;
console.log("puts", JSON.stringify(puts.map((x) => [x.variant, x.status, x.error])), "nine", JSON.stringify(nine.map((n) => n.variant)), "table", table.length, "api lines", apiCart?.lines?.length);

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const res = { base: BASE, table, nine, set_pieces: setPieces, puts, api_cart: apiCart?.lines?.map((l) => ({ v: l.variant_id, line: l.option_he ? `${l.name_he} · ${l.option_he}` : l.name_he })), pages: {} };
// the phone first (the cart and the checkout only); then 1280, which places the order (the cart is closed after it)
for (const vp of [
  { w: 400, h: 860, m: true },
  { w: 1280, h: 900 },
]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: vp.w, height: vp.h }, isMobile: !!vp.m, hasTouch: !!vp.m, extraHTTPHeaders: { 'cf-connecting-ip': `198.51.100.${vp.w === 1280 ? 141 : 142}` } });
  ctx.setDefaultTimeout(120000);
  const p = await ctx.newPage();
  await p.goto(`${BASE}/`);
  await p.evaluate((id) => localStorage.setItem('hd.cart', id), cart);
  const pg = {};
  await p.goto(`${BASE}/cart/`);
  await p.waitForTimeout(3000);
  if (!(await p.locator('.cart-line').count()))
    console.log('cart page empty?', await p.evaluate(() => localStorage.getItem('hd.cart')), cart, (await p.evaluate(() => document.body.innerText)).slice(0, 300).replace(/\n/g, ' '));
  await p.locator('.cart-line').first().waitFor();
  await p.waitForTimeout(800);
  pg.cart = await p.evaluate(() => ({
    lines: [...document.querySelectorAll('.cart-line')].map((li) => [li.querySelector('.title')?.textContent?.trim() ?? '', li.querySelector('.pack-line')?.textContent?.trim() ?? ''].filter(Boolean).join(' · ')),
    text: document.querySelector('main')?.innerText ?? document.body.innerText,
  }));
  await p.screenshot({ path: join(OUT, 'overlays', `lines-cart-${vp.w}.png`), fullPage: true });
  await p.goto(`${BASE}/checkout/`);
  await p.locator('aside.summary li').first().waitFor();
  pg.checkout = await p.evaluate(() => ({
    lines: [...document.querySelectorAll('aside.summary li')].map((li) => li.textContent.replace(/\s+× \d+$/, '').trim()),
    text: document.querySelector('main')?.innerText ?? document.body.innerText,
  }));
  if (vp.w === 1280) {
    // the order, through the UI (the same cart; only once)
    await p.getByLabel('שם מלא').fill('בודקת איכות');
    await p.getByLabel('אימייל').fill('qa@example.invalid');
    await p.getByLabel('טלפון').fill('050-0000000');
    await p.getByLabel('עיר').fill('חיפה');
    await p.getByLabel('רחוב').fill('הנמל');
    await p.getByLabel('מספר בית').fill('1');
    await p.getByRole('checkbox', { name: /קראתי ואני מסכים/ }).check();
    await p.getByRole('button', { name: 'מעבר לתשלום מאובטח' }).click();
    await p.waitForURL(/\/mock-pay\/ms_/);
    pg.mock_pay_text = await p.evaluate(() => document.body.innerText);
    await p.getByRole('button', { name: 'אישור תשלום (מדומה)' }).click();
    await p.waitForURL(/\/order\/\d+\/$/);
    res.order_id = p.url().match(/\/order\/(\d+)\//)[1];
    await p.locator('ul.order-lines li').first().waitFor();
    await p.waitForTimeout(2500);
    pg.order = await p.evaluate(() => ({
      lines: [...document.querySelectorAll('ul.order-lines li')].map((li) => li.textContent.replace(/\s+× \d+ · .*$/s, '').trim()),
      text: document.querySelector('main')?.innerText ?? document.body.innerText,
    }));
    await p.screenshot({ path: join(OUT, 'overlays', `lines-order-${vp.w}.png`), fullPage: true });
  }
  for (const [k, v] of Object.entries(pg)) {
    if (typeof v === 'string') {
      pg[k] = { latin_words: latinWords(v) };
      continue;
    }
    v.latin_words = latinWords(v.text);
    v.latin_lines = v.lines.filter(latin);
    v.nine = nine.map((n) => ({ n: n.n, want: n.want, found: v.lines.includes(n.want) }));
    delete v.text;
  }
  res.pages[vp.w] = pg;
  await ctx.close();
}
await browser.close();
writeFileSync(join(OUT, 'data/lines-pages.json'), JSON.stringify(res, null, 1));
console.log(
  JSON.stringify(
    {
      nine_variants: nine.map((n) => [n.n, !!n.variant]),
      table_rows: table.length,
      puts: puts.map((x) => `${x.status}${x.error ? ':' + x.error : ''}`).join(' '),
      order_id: res.order_id,
      pages: Object.fromEntries(
        Object.entries(res.pages).map(([w, pg]) => [
          w,
          Object.fromEntries(Object.entries(pg).map(([k, v]) => [k, { lines: v.lines?.length, nine_found: v.nine?.filter((x) => x.found).length, latin_lines: v.latin_lines, latin_words: v.latin_words }])),
        ]),
      ),
    },
    null,
    1,
  ),
);
