/**
 * qa-agent, 2026-11-11 (ת21 at b94c5bc1): "החדר שלך" on the order page, for orders made through the API the way the
 * engine makes them (PUT with `house`), paid through the mock page (the real webhook path), then the order page opened
 * in the browser with the order's token. For each case: which house figures are drawn, which slot and option each layer
 * is, the layer files, and the "not in the room yet" list with its pictures; a screen of each.
 *   1  the brief's case: the beige lumbar cushion and the Pecan throw, both from set B, house warm-modern
 *   2  the same cushion in another colour (no layer), house warm-modern
 *   3  the Pecan throw (set B) and the white bouclé (set A), house warm-modern: two options of one slot
 *   4  the Nordic vase (the room's) and another vase of the same slot, house nordic
 *   5  the Pecan throw bought in the Nordic house (house nordic)
 *   6  the beige cushion bought off the engine (no house)
 *   7  a house that does not exist (japandi): nothing drawn, the line listed
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node your-room.mjs
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
const story = JSON.parse(readFileSync(join(COPY, '.generated/catalog.story.public.json'), 'utf8'));

let ipn = 10;
async function api(path, init = {}) {
  const r = await fetch(`${BASE}${path}`, { ...init, redirect: 'manual', headers: { 'content-type': 'application/json', 'cf-connecting-ip': `203.0.113.${ipn++ % 250}`, ...(init.headers ?? {}) } });
  const text = await r.text();
  let body = null;
  try {
    body = JSON.parse(text);
  } catch {
    body = text.slice(0, 200);
  }
  return { status: r.status, body, location: r.headers.get('location') };
}
async function order(lines) {
  const cart = (await api('/api/cart', { method: 'POST' })).body.id;
  const put = [];
  for (const l of lines) put.push({ ...l, r: (await api(`/api/cart/${cart}/items`, { method: 'PUT', body: JSON.stringify({ pack: 'set', qty: 1, ...l }) })).status });
  const c = await api('/api/checkout', {
    method: 'POST',
    body: JSON.stringify({
      cart_id: cart,
      customer: { full_name: 'בודקת איכות', email: 'qa@example.invalid', phone: '050-0000000' },
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

// the variants
const setItems = Object.fromEntries(house.sets.map((s) => [s.id, s.items.map((i) => i[0] ?? i.variant_id ?? i.id)]));
const flat = (s) => house.sets.find((x) => x.id === s).items.map((i) => (Array.isArray(i) ? i[0] : (i.variant_id ?? i.id)));
const B = flat('B');
const A = flat('A');
const beige = B.find((v) => v.includes('linen-look-charcoal') && v.includes('beige'));
const pecan = B.find((v) => v.includes('pecan'));
const whiteBoucle = A.find((v) => v.includes('boucle-teddy') && v.includes('white'));
// the same lumbar cushion in another colour: another SKU of that product with the same size and filling
const storyFull = JSON.parse(readFileSync(join(COPY, '.generated/catalog.story.full.json'), 'utf8'));
const lumbarP = storyFull.products.find((p) => p.id === beige.split(':')[0]);
const otherColour = lumbarP?.variants_full?.filter((v) => v.active).map((v) => v.id).find((v) => v !== beige && v.endsWith('+pillow-core-and-pillowcase+30x50')) ?? null;
// the Nordic vase slot: the room's option and another one
const room = pub.rooms?.find((r) => r.id === 'living-room') ?? null;
const vaseSlot = room?.slots.find((s) => s.id === 'vase');
const vaseIds = (vaseSlot?.options ?? []).filter((o) => o.product_id).map((o) => o.product_id);
const prodOf = (id) => pub.products.find((p) => p.id === id);
const vaseDefault = vaseIds[0] ? prodOf(vaseIds[0])?.variants[0]?.id : null;
const vaseOther = vaseIds[1] ? prodOf(vaseIds[1])?.variants[0]?.id : null;

const CASES = [
  { id: 1, what: 'beige lumbar + Pecan throw (set B), warm-modern', lines: [{ variant_id: beige, house: 'warm-modern' }, { variant_id: pecan, house: 'warm-modern' }] },
  { id: 2, what: 'the lumbar cushion in another colour, warm-modern', lines: otherColour ? [{ variant_id: otherColour, house: 'warm-modern' }] : [] },
  { id: 3, what: 'Pecan throw (set B) + white bouclé (set A), warm-modern', lines: [{ variant_id: pecan, house: 'warm-modern' }, { variant_id: whiteBoucle, house: 'warm-modern' }] },
  { id: 4, what: 'the room vase + another vase of the slot, nordic', lines: vaseDefault && vaseOther ? [{ variant_id: vaseDefault, house: 'nordic' }, { variant_id: vaseOther, house: 'nordic' }] : [] },
  { id: 5, what: 'Pecan throw bought in the Nordic house', lines: [{ variant_id: pecan, house: 'nordic' }] },
  { id: 6, what: 'beige lumbar off the engine (no house)', lines: [{ variant_id: beige }] },
  { id: 7, what: 'beige lumbar, house japandi (no such house)', lines: [{ variant_id: beige, house: 'japandi' }] },
];

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const res = { base: BASE, variants: { beige, pecan, whiteBoucle, otherColour, vaseDefault, vaseOther }, set_B: B, set_A: A, cases: [] };
const ONLY = process.env.QA_CASES ? process.env.QA_CASES.split(',').map(Number) : null;
for (const c of CASES) {
  if (ONLY && !ONLY.includes(c.id)) continue;
  if (!c.lines.length) {
    res.cases.push({ ...c, skipped: 'no variant for the case' });
    continue;
  }
  const o = await order(c.lines);
  const out = { ...c, order: o };
  if (o.order_id) {
    for (const vp of [
      { w: 1280, h: 900 },
      { w: 400, h: 860, m: true },
    ]) {
      const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: vp.w, height: vp.h }, isMobile: !!vp.m, hasTouch: !!vp.m });
    ctx.setDefaultTimeout(120000);
      const p = await ctx.newPage();
      await p.goto(`${BASE}/`, { waitUntil: 'domcontentloaded' });
      await p.evaluate(([id, t]) => localStorage.setItem(`hd.order.${id}`, t), [o.order_id, o.token]);
      await p.goto(`${BASE}/order/${o.order_id}/`, { waitUntil: 'load' });
      await p.locator('.order-lines').waitFor({ timeout: 120000 });
      await p.waitForTimeout(2500);
      const dom = await p.evaluate(() => ({
        lines: [...document.querySelectorAll('.order-lines li')].map((li) => li.textContent.replace(/\s+/g, ' ').trim()),
        figures: [...document.querySelectorAll('figure.your-room')].map((f) => ({
          house: f.dataset.house,
          caption: f.querySelector('figcaption')?.textContent.trim(),
          layers: [...f.querySelectorAll('span[data-slot]')].map((s) => ({ slot: s.dataset.slot, position: s.dataset.position, imgs: [...s.querySelectorAll('img')].map((i) => i.getAttribute('src')) })),
          base: f.querySelector('img')?.currentSrc ?? null,
        })),
        missing: [...document.querySelectorAll('.your-room-missing li')].map((li) => ({ variant: li.dataset.variant, img: li.querySelector('img')?.getAttribute('src') ?? null, text: li.textContent.replace(/\s+/g, ' ').trim() })),
      }));
      await p.locator('.your-rooms').screenshot({ path: join(OUT, 'overlays', `your-room-case${c.id}-${vp.w}.png`) }).catch(() => undefined);
      out[`dom_${vp.w}`] = dom;
      await ctx.close();
    }
    const d = out.dom_1280;
    // what a drawn layer shows: in the warm-modern house the set at that position (all its pieces); in the Nordic house
    // the option at that position, in the option the room shows (its default variant)
    const drawnVariants = (fig) =>
      fig.layers.flatMap((l) => {
        if (fig.house === 'warm-modern') return setItems[house.sets.find((s) => s.position === Number(l.position))?.id] ?? [];
        const opt = room?.slots.find((s) => s.id === l.slot)?.options.find((o) => o.position === Number(l.position));
        const prod = opt?.product_id ? prodOf(opt.product_id) : null;
        return prod ? [prod.variants[0].id] : [];
      });
    out.summary = {
      figures: d.figures.map((f) => `${f.house}: ${f.layers.map((l) => `${l.slot}#${l.position}`).join(', ')}`),
      missing: d.missing.map((m) => m.variant),
      // every line bought is either in a drawn layer or listed as missing
      unaccounted: c.lines
        .map((l) => l.variant_id)
        .filter((v) => !d.missing.some((m) => m.variant === v) && !d.figures.some((f) => drawnVariants(f).includes(v))),
      drawn: d.figures.map((f) => ({ house: f.house, shows: drawnVariants(f) })),
    };
  }
  res.cases.push(out);
  console.log(c.id, c.what, JSON.stringify(out.summary ?? out.order));
}
await browser.close();
writeFileSync(join(OUT, process.env.QA_CASES ? `data/your-room-cases-${process.env.QA_CASES.replace(/,/g, '-')}.json` : 'data/your-room.json'), JSON.stringify(res, null, 1));
