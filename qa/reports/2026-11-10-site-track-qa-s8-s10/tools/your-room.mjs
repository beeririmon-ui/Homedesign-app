/**
 * qa-agent, 2026-11-10 (S8, §9.5 "החדר שלך"), on the isolated copy of b0a71cd2. Three paid orders through the API (the mock
 * hosted page, the dummy secret), each then opened on /order/<id>/ in Chromium at 1280 and 400 with its token:
 *   nordic-in-room   the Nordic wheel's cushion in the colour the room shows (boucle teddy, white 50×50): the control
 *   nordic-other     the same cushion in another colour the shop sells (boucle teddy, wine red 50×50)
 *   warm-modern-B    set B from the warm-modern house (S10): corduroy camel, the lumbar, the muslin throw in Pecan
 * For each: which layers "החדר שלך" draws (slot, option position, the file), the caption, and whether the drawn option is
 * the variant that was bought. The figure is also compared with my own composite of the same files at the same size
 * (sharp: the base, each drawn layer in its rect; a shadow multiplies) to see that every layer sits where the engine puts it.
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node your-room.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const COPY = process.env.QA_COPY;
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const OV = join(OUT, 'overlays');
const IP = '203.0.113.84';
const H = { 'content-type': 'application/json', 'cf-connecting-ip': IP };
const call = async (method, path, body, extra = {}) => {
  const r = await fetch(BASE + path, { method, headers: { ...H, ...extra }, body: body ? JSON.stringify(body) : undefined, redirect: 'manual' });
  return { status: r.status, body: await r.json().catch(() => null) };
};
const house = JSON.parse(readFileSync(join(COPY, '.generated/house.living-room.warm-modern.json'), 'utf8'));
const setB = house.sets.find((s) => s.id === 'B').items.map((i) => i.variant_id).filter((v) => !v.includes(':50x50+oatmeal'));
const orders = {
  'nordic-in-room': ['cushions-boucle-teddy-d7wrb:white+50x50'],
  'nordic-other': ['cushions-boucle-teddy-d7wrb:wine-red+50x50'],
  'warm-modern-B': setB,
};
async function order(variants) {
  const cart = (await call('POST', '/api/cart')).body.id;
  const put = [];
  for (const v of variants) put.push([v, (await call('PUT', `/api/cart/${cart}/items`, { variant_id: v, pack: 'set', qty: 1 })).status]);
  const co = await call('POST', '/api/checkout', {
    cart_id: cart,
    customer: { full_name: 'בדיקת איכות', email: 'qa@example.com', phone: '050-1234567' },
    address: { city: 'חיפה', street: 'הרצל', house: '12' },
    shipping_method: 'economy',
    consents: { terms: true },
  });
  const session = co.body.redirect_url.split('/mock-pay/')[1].replace(/\/.*$/, '');
  const pay = await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', headers: { 'content-type': 'application/x-www-form-urlencoded', 'cf-connecting-ip': IP }, body: 'outcome=success', redirect: 'manual' });
  return { put, id: co.body.order_id, token: co.body.order_token, pay: pay.status };
}

const scene = JSON.parse(readFileSync(join(COPY, '.generated/scene.living-room.nordic.json'), 'utf8'));
const catalog = JSON.parse(readFileSync(join(COPY, '.generated/catalog.public.json'), 'utf8'));
const room = catalog.rooms.find((r) => r.id === 'living-room');
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--disable-background-networking'] });
const res = { base: BASE, run_at: new Date().toISOString(), orders: [] };
for (const [name, variants] of Object.entries(orders)) {
  const o = await order(variants);
  const r = { name, bought: variants, put: o.put, order_id: o.id, pay: o.pay, views: [] };
  for (const [w, h] of [[1280, 900], [400, 860]]) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h }, extraHTTPHeaders: { 'cf-connecting-ip': IP } });
    await ctx.addInitScript(([id, t]) => localStorage.setItem(`hd.order.${id}`, t), [o.id, o.token]);
    const p = await ctx.newPage();
    await p.goto(`${BASE}/order/${o.id}/`, { waitUntil: 'load' });
    await p.locator('.order-steps, .notice').first().waitFor({ timeout: 20000 });
    await p.waitForTimeout(2500);
    const fig = await p.evaluate(() => {
      const f = document.querySelector('.your-room');
      if (!f) return null;
      const frame = f.querySelector('.your-room-frame');
      const fb = frame.getBoundingClientRect();
      const base = frame.querySelector('img:not(.your-room-layer)');
      return {
        caption: f.querySelector('figcaption')?.textContent.trim(),
        frame: [fb.left, fb.top, fb.width, fb.height].map((x) => Math.round(x * 100) / 100),
        base: base ? { src: base.currentSrc.split('/media/')[1], box: (() => { const b = base.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((x) => Math.round(x * 100) / 100); })(), natural: [base.naturalWidth, base.naturalHeight], fit: getComputedStyle(base).objectFit } : null,
        layers: [...frame.querySelectorAll('.your-room-layer')].map((i) => ({ src: i.currentSrc.split('/media/')[1], cls: i.className, blend: getComputedStyle(i).mixBlendMode, box: (() => { const b = i.getBoundingClientRect(); return [b.left - fb.left, b.top - fb.top, b.width, b.height].map((x) => Math.round(x * 100) / 100); })() })),
      };
    });
    const v = { viewport: `${w}x${h}`, figure: fig };
    if (fig) {
      await p.locator('.your-room').scrollIntoViewIfNeeded();
      await p.locator('.your-room').screenshot({ path: join(OV, `your-room-${name}-${w}.png`) });
      // the drawn options, and the bought variants
      v.drawn = fig.layers
        .filter((l) => !l.cls.includes('is-multiply') && !l.cls.includes('is-screen'))
        .map((l) => {
          const m = /slots\/([^/]+)\/(\d+)\.product/.exec(l.src);
          const slot = room.slots.find((s) => s.id === m?.[1]);
          const opt = slot?.options[Number(m?.[2]) - 1];
          const prod = catalog.products.find((x) => x.id === opt?.product_id);
          const inRoom = prod?.options ? prod.options.axes.map((a, k) => a.values[prod.options.v[prod.options.room][k]][0]).join('+') : 'default';
          const bought = variants.filter((x) => x.startsWith(`${opt?.product_id}:`));
          return { slot: m?.[1], position: Number(m?.[2]), product: opt?.product_id, drawn_option: inRoom, bought, drawn_is_bought: bought.some((b) => b.split(':')[1].split('+').sort().join('+') === inRoom.split('+').sort().join('+')) };
        });
      // alignment: my composite of the same files at the figure's size
      if (w === 1280) {
        const shot = await p.locator('.your-room-frame').screenshot();
        const meta = await sharp(shot).metadata();
        const W = meta.width, Hh = meta.height;
        const baseFile = join(COPY, 'web/public/media', `${scene.base[0].src}.1920.webp`);
        const comps = [];
        for (const l of fig.layers) {
          const file = join(COPY, 'web/public/media', l.src.replace(/\?.*$/, ''));
          const k = W / fig.frame[2];
          comps.push({ input: await sharp(file).resize(Math.round(l.box[2] * k), Math.round(l.box[3] * k), { fit: 'fill' }).png().toBuffer(), left: Math.round(l.box[0] * k), top: Math.round(l.box[1] * k), blend: l.cls.includes('is-multiply') ? 'multiply' : l.cls.includes('is-screen') ? 'screen' : 'over' });
        }
        const mine = await sharp(baseFile).resize(W, Hh, { fit: 'fill' }).composite(comps).removeAlpha().raw().toBuffer();
        const got = await sharp(shot).removeAlpha().raw().toBuffer();
        const hist = new Uint32Array(256);
        const vis = Buffer.alloc(W * Hh * 3);
        for (let i = 0; i < W * Hh; i++) {
          const d = Math.max(Math.abs(mine[i * 3] - got[i * 3]), Math.abs(mine[i * 3 + 1] - got[i * 3 + 1]), Math.abs(mine[i * 3 + 2] - got[i * 3 + 2]));
          hist[d]++;
          const g = (got[i * 3] + got[i * 3 + 1] + got[i * 3 + 2]) / 9;
          vis[i * 3] = Math.min(255, g + d * 6); vis[i * 3 + 1] = g; vis[i * 3 + 2] = g;
        }
        const pct = (q) => { let c = 0; for (let d = 0; d < 256; d++) { c += hist[d]; if (c >= q * W * Hh) return d; } return 255; };
        v.vs_my_composite = { size: [W, Hh], p99: pct(0.99), p999: pct(0.999) };
        await sharp(vis, { raw: { width: W, height: Hh, channels: 3 } }).jpeg({ quality: 80 }).toFile(join(OV, `your-room-${name}-vs-mine.jpg`));
      }
    }
    r.views.push(v);
    await ctx.close();
  }
  res.orders.push(r);
}
await browser.close();
writeFileSync(join(OUT, 'data/your-room.json'), JSON.stringify(res, null, 1));
console.log(JSON.stringify(res.orders.map((o) => ({ name: o.name, put: o.put, pay: o.pay, views: o.views.map((v) => ({ vp: v.viewport, caption: v.figure?.caption ?? null, layers: v.figure?.layers.map((l) => `${l.src} ${l.blend}`), drawn: v.drawn, vs_mine: v.vs_my_composite })) })), null, 1));
