/**
 * qa-agent, S15 (2026-11-11): master-designer's copy on the order page ("החדר שלך", docs/proposals/your-room-copy-2026-11-11.md
 * §1), on my own orders (not the e2e's), made through the API the way the engine makes them (PUT with `house`), paid on
 * the mock page, then opened in Chromium with the order's token at 1280 and 400. For each: the captions, the list's lead,
 * every row and its reason, the caption's and the list's computed max-width and their line counts, and a screen.
 *   1  two pieces of set B (Pecan throw + camel corduroy): "… הזמנתם ממנו 2 פריטים מתוך 4."
 *   2  the whole of set B: "… עם מה שהזמנתם, בגוונים שבחרתם." and no list
 *   3  Pecan (set B) + Clay throw (set C): one piece of B drawn; C listed "בהדמיה, באותו מקום: סט קאמל ופקאן."
 *   4  only a variant with no layer (the lumbar in another colour): the lead "לפריטים שהזמנתם אין הדמיה בחדר.", no reason
 *   5  two houses in one order: set B's Pecan (warm-modern) and the Nordic room's vase: a figure and a caption each
 *   QA_BASE=… QA_COPY=<copy>/site QA_OUT=<folder> node your-room-s15.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const house = JSON.parse(readFileSync(join(COPY, '.generated/house.living-room.warm-modern.json'), 'utf8'));
const pub = JSON.parse(readFileSync(join(COPY, '.generated/catalog.public.json'), 'utf8'));
const storyFull = JSON.parse(readFileSync(join(COPY, '.generated/catalog.story.full.json'), 'utf8'));

let ipn = 10;
async function api(path, init = {}) {
  const r = await fetch(`${BASE}${path}`, { ...init, redirect: 'manual', headers: { 'content-type': 'application/json', 'cf-connecting-ip': `198.51.100.${ipn++ % 250}`, ...(init.headers ?? {}) } });
  const text = await r.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    body = text.slice(0, 200);
  }
  return { status: r.status, body };
}
async function order(lines) {
  const cart = (await api('/api/cart', { method: 'POST' })).body.id;
  const put = [];
  for (const l of lines) put.push({ ...l, r: (await api(`/api/cart/${cart}/items`, { method: 'PUT', body: JSON.stringify({ pack: 'set', qty: 1, ...l }) })).status });
  const c = await api('/api/checkout', {
    method: 'POST',
    body: JSON.stringify({
      cart_id: cart,
      customer: { full_name: 'בודקת נוסח', email: 'copy.qa1516@example.invalid', phone: '050-0000000' },
      address: { city: 'חיפה', street: 'הנמל', house: '1' },
      shipping_method: 'economy',
      consents: { terms: true, marketing: false },
    }),
  });
  if (c.status !== 201) return { put, checkout: c };
  const session = new URL(c.body.redirect_url).pathname.split('/').pop();
  const pay = await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', redirect: 'manual', body: new URLSearchParams({ outcome: 'success' }) });
  return { put, order_id: c.body.order_id, token: c.body.order_token, paid: pay.status };
}
const items = (id) => house.sets.find((s) => s.id === id).items.map((i) => i.variant_id);
const B = items('B');
const C = items('C');
const pecan = B.find((v) => v.includes('pecan'));
const camel = B.find((v) => v.includes(':camel'));
const clay = C.find((v) => v.includes('clay'));
const beige = B.find((v) => v.includes('linen-look-charcoal'));
const lumbarP = storyFull.products.find((p) => p.id === beige.split(':')[0]);
const otherColour = lumbarP?.variants_full?.filter((v) => v.active && v.id !== beige).map((v) => v.id).find((v) => v.endsWith('+pillow-core-and-pillowcase+30x50')) ?? null;
const vaseSlot = pub.rooms.find((r) => r.id === 'living-room').slots.find((s) => s.id === 'vase');
const vaseDefault = pub.products.find((p) => p.id === vaseSlot.options[0].product_id).variants[0].id;

const CASES = [
  { id: 1, what: 'two pieces of set B', lines: [pecan, camel].map((v) => ({ variant_id: v, house: 'warm-modern' })) },
  { id: 2, what: 'the whole of set B', lines: B.map((v) => ({ variant_id: v, house: 'warm-modern' })) },
  { id: 3, what: 'Pecan (B) + Clay throw (C)', lines: [pecan, clay].map((v) => ({ variant_id: v, house: 'warm-modern' })) },
  { id: 4, what: 'only a variant with no layer', lines: otherColour ? [{ variant_id: otherColour, house: 'warm-modern' }] : [] },
  { id: 5, what: 'two houses: Pecan (warm-modern) + the Nordic vase', lines: [{ variant_id: pecan, house: 'warm-modern' }, { variant_id: vaseDefault, house: 'nordic' }] },
];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = { base: BASE, variants: { pecan, camel, clay, otherColour, vaseDefault }, cases: [] };
for (const c of CASES) {
  if (!c.lines.length) {
    res.cases.push({ ...c, skipped: 'no variant' });
    continue;
  }
  const o = await order(c.lines);
  const out = { id: c.id, what: c.what, order: { id: o.order_id, paid: o.paid, put: o.put?.map((p) => p.r) } };
  for (const vp of [
    { w: 1280, h: 900 },
    { w: 400, h: 860, m: true },
  ]) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: vp.w, height: vp.h }, isMobile: !!vp.m, hasTouch: !!vp.m });
    ctx.setDefaultTimeout(90_000);
    const p = await ctx.newPage();
    await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
    await p.evaluate(([id, t]) => localStorage.setItem(`hd.order.${id}`, t), [o.order_id, o.token]);
    await p.goto(`${BASE}/order/${o.order_id}/`, { waitUntil: 'load' });
    await p.locator('.order-lines').waitFor();
    await p.waitForTimeout(2500);
    out[`at_${vp.w}`] = await p.evaluate(() => {
      const lineCount = (el) => {
        if (!el) return null;
        const r = document.createRange();
        r.selectNodeContents(el);
        const tops = new Set([...r.getClientRects()].map((x) => Math.round(x.top)));
        return tops.size;
      };
      const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
      const list = document.querySelector('.your-room-list');
      return {
        rem_px: rem,
        figures: [...document.querySelectorAll('figure.your-room')].map((f) => {
          const cap = f.querySelector('figcaption');
          return { house: f.dataset.house, caption: cap?.textContent.trim(), caption_lines: lineCount(cap), caption_maxw: getComputedStyle(cap).maxWidth, caption_w: Math.round(cap.getBoundingClientRect().width), labelled_by_caption: f.getAttribute('aria-labelledby') === cap.id };
        }),
        lead: document.querySelector('.your-room-lead')?.textContent.trim() ?? null,
        list_maxw: list ? getComputedStyle(list).maxWidth : null,
        list_labelled: document.querySelector('.your-room-missing')?.getAttribute('aria-labelledby') ?? null,
        rows: [...document.querySelectorAll('.your-room-missing li')].map((li) => ({
          variant: li.dataset.variant,
          why_kind: li.dataset.why,
          name: li.querySelector('span')?.childNodes[0]?.textContent?.trim(),
          why: li.querySelector('.your-room-why')?.textContent.trim() ?? null,
          why_block: li.querySelector('.your-room-why') ? getComputedStyle(li.querySelector('.your-room-why')).display : null,
          img: li.querySelector('img') ? 'img' : li.querySelector('.your-room-noimg') ? 'neutral tile' : null,
        })),
      };
    });
    await p.locator('.your-rooms').screenshot({ path: join(OUT, 'overlays', `s15-your-room-case${c.id}-${vp.w}.png`) }).catch(() => undefined);
    await ctx.close();
  }
  res.cases.push(out);
  const a = out.at_1280;
  console.log(
    `${c.id} ${c.what}: ${a.figures.map((f) => `[${f.house}] "${f.caption}" (${f.caption_lines} line(s) at 1280, ${out.at_400.figures.find((x) => x.house === f.house)?.caption_lines} at 400; max-width ${f.caption_maxw})`).join(' + ')}; lead ${JSON.stringify(a.lead)}; rows ${JSON.stringify(a.rows.map((r) => `${r.name} | ${r.why}`))}`,
  );
}
await browser.close();
writeFileSync(join(OUT, 'data/your-room-s15.json'), JSON.stringify(res, null, 1));
