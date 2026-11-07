/**
 * qa-agent, 2026-11-07 (S3-S5): QA's S4 items, rechecked on QA's snapshot (register v5).
 *  1. "המראה כולו לסל" on every frame, each in a fresh context: what lands vs the frame's dotted, sellable items and their
 *     units (G-ED.6); a sellable item without a dot must not land; a second press changes nothing and says so
 *  2. SET1, the triptych: the detail page (no pack choice, the set note), the sheet's add, the cart line
 *  3. two tabs: tab 2 adds and removes; does tab 1's count follow without a reload
 *   QA_BASE=http://127.0.0.1:8799 node check-s4fix.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT_DIR = '/home/user/homedesign-app/qa/reports/2026-11-07-site-track-qa-s3-s5/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const res = { base: BASE, run_at: new Date().toISOString(), look: [] };
const cart = (p) => p.evaluate(() => JSON.parse(localStorage.getItem('hd.story.cart') ?? 'null'));

// 1. the look
for (const style of ['nordic', 'warm-modern', 'modern-country', 'boho', 'mediterranean', 'japandi']) {
  const probe = await browser.newContext({ locale: 'he-IL' });
  const pp = await probe.newPage();
  await pp.goto(`${BASE}/story/living-room/${style}/`, { waitUntil: 'load' });
  const frames = await pp.evaluate(() => JSON.parse(document.getElementById('st-data').textContent).frames.map((f) => f.id));
  await probe.close();
  if (!frames.length) res.look.push({ page: style, frames: 0 });
  for (const id of frames) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
    const p = await ctx.newPage();
    await p.goto(`${BASE}/story/living-room/${style}/`, { waitUntil: 'load' });
    await p.waitForTimeout(600);
    const exp = await p.evaluate((id) => {
      const d = JSON.parse(document.getElementById('st-data').textContent);
      const items = d.frames.find((f) => f.id === id).items.map((k) => d.items[k]);
      const sold = items.filter((x) => x.status === 'available' && x.variant_id);
      const want = {};
      for (const x of sold.filter((x) => x.dot)) want[x.variant_id] = Math.max(want[x.variant_id] ?? 0, x.units);
      return {
        want,
        sold_without_dot: sold.filter((x) => !x.dot).map((x) => x.variant_id),
        button: document.getElementById(`look-${id}`)?.textContent.trim() ?? null,
        units_line: document.querySelector(`#look-${id} ~ .st-look-units`)?.textContent.trim() ?? null,
      };
    }, id);
    const btn = p.locator(`#look-${id}`);
    let first = null, second = null, said = null, said2 = null;
    if (await btn.count()) {
      await btn.scrollIntoViewIfNeeded();
      await btn.click();
      await p.waitForTimeout(500);
      first = ((await cart(p))?.items ?? []).map((i) => ({ variant_id: i.variant_id, pack: i.pack, qty: i.qty }));
      said = await p.evaluate(() => [...document.querySelectorAll('[aria-live], .mag-live, .live-region')].map((e) => e.textContent.trim()).filter(Boolean).join(' | '));
      await p.waitForTimeout(3000);
      await btn.click();
      await p.waitForTimeout(500);
      second = ((await cart(p))?.items ?? []).map((i) => ({ variant_id: i.variant_id, qty: i.qty }));
      said2 = await p.evaluate(() => [...document.querySelectorAll('[aria-live], .mag-live, .live-region')].map((e) => e.textContent.trim()).filter(Boolean).join(' | '));
      // a reload, then the look again: still idempotent across a reload (storage, not memory)
      await p.reload({ waitUntil: 'load' });
      await p.waitForTimeout(500);
      await p.locator(`#look-${id}`).click();
      await p.waitForTimeout(500);
    }
    const third = ((await cart(p))?.items ?? []).map((i) => ({ variant_id: i.variant_id, qty: i.qty }));
    const got = Object.fromEntries((first ?? []).map((x) => [x.variant_id, x.qty]));
    const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    res.look.push({
      page: style,
      frame: id,
      button: exp.button,
      units_line: exp.units_line,
      expected: exp.want,
      added: got,
      matches_dotted_with_units: first ? same(Object.keys(got).sort(), Object.keys(exp.want).sort()) && Object.entries(exp.want).every(([k, n]) => got[k] === n) : null,
      sold_without_dot: exp.sold_without_dot,
      sold_without_dot_added: exp.sold_without_dot.filter((v) => v in got),
      second_press_unchanged: first ? same(first.map((x) => [x.variant_id, x.qty]), second.map((x) => [x.variant_id, x.qty])) : null,
      after_reload_unchanged: first ? same(first.map((x) => [x.variant_id, x.qty]), third.map((x) => [x.variant_id, x.qty])) : null,
      announced_first: said,
      announced_second: said2,
    });
    if (style === 'boho') await p.screenshot({ path: `${OUT_DIR}/boho-look-after-1280.png`, fullPage: false });
    await ctx.close();
  }
}

// 2. SET1, the triptych
{
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  const it = await p.evaluate(() => {
    const d = JSON.parse(document.getElementById('st-data').textContent);
    const [k, x] = Object.entries(d.items).find(([, x]) => x.product.includes('triptych'));
    return { key: k, href: x.href, variant_id: x.variant_id, set_qty: x.set_qty, price_he: x.price_he, notes: x.notes_he, units: x.units, status: x.status };
  });
  await p.goto(BASE + it.href, { waitUntil: 'load' });
  await p.waitForTimeout(400);
  const detail = await p.evaluate(() => {
    const d = JSON.parse(document.getElementById('st-data').textContent).detail;
    return {
      set_qty: d.set_qty,
      skus: d.skus.map((s) => ({ id: s.variant_id ?? s.id, unit: s.unit_price_agorot ?? null, price: s.price_agorot })),
      pack_radios: document.querySelectorAll('input[name="st-pack"]').length,
      pack_block: !!document.getElementById('st-pd-pack'),
      color_axis: document.querySelectorAll('.st-pd-axis[data-axis="color"]').length,
      axes: [...document.querySelectorAll('.st-pd-axis')].map((a) => a.dataset.axis),
      notes: document.querySelector('#detail .st-notes')?.textContent.trim() ?? null,
      price: document.getElementById('st-pd-price')?.textContent.trim(),
    };
  });
  await p.evaluate(() => localStorage.removeItem('hd.story.cart'));
  await p.locator('#st-pd-add').click();
  await p.waitForTimeout(400);
  const stored = (await cart(p))?.items ?? [];
  await p.locator('#st-cart-open').click();
  await p.waitForTimeout(400);
  const line = await p.evaluate(() => [...document.querySelectorAll('#st-cart-lines .st-cart-line')].map((l) => l.textContent.replace(/\s+/g, ' ').trim()));
  await p.screenshot({ path: `${OUT_DIR}/triptych-detail-cart-1280.png` });
  // a hand-edited single-piece line: held, not charged
  await p.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('hd.story.cart'));
    s.items[0].pack = 'unit';
    localStorage.setItem('hd.story.cart', JSON.stringify(s));
  });
  await p.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(500);
  const unitAtCheckout = await p.evaluate(() => ({ lines: [...document.querySelectorAll('#co-lines li')].map((l) => l.textContent), held: document.getElementById('co-held').hidden ? null : document.getElementById('co-held').textContent }));
  res.set1_triptych = { item: it, detail, stored: stored.map((i) => ({ variant_id: i.variant_id, pack: i.pack, qty: i.qty })), cart_lines: line, single_piece_line_at_checkout: unitAtCheckout };
  await ctx.close();
}

// 3. two tabs
{
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: 1280, height: 900 } });
  const t1 = await ctx.newPage();
  await t1.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  await t1.waitForTimeout(500);
  const count = (p) => p.evaluate(() => document.getElementById('st-cart-open')?.textContent.replace(/\s+/g, ' ').trim());
  const c0 = await count(t1);
  const t2 = await ctx.newPage();
  await t2.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await t2.waitForTimeout(500);
  await t2.locator('#look-A').click();
  await t2.waitForTimeout(800);
  const c1 = await count(t1);
  const c1b = await count(t2);
  await t2.evaluate(() => localStorage.removeItem('hd.story.cart'));
  await t2.waitForTimeout(800);
  const c2 = await count(t1);
  // tab 1 opens its cart after tab 2 added again: does it show tab 2's lines?
  await t2.reload({ waitUntil: 'load' });
  await t2.waitForTimeout(400);
  await t2.locator('#look-A').click();
  await t2.waitForTimeout(600);
  await t1.locator('#st-cart-open').click();
  await t1.waitForTimeout(500);
  const t1Lines = await t1.evaluate(() => document.querySelectorAll('#st-cart-lines .st-cart-line').length);
  res.two_tabs = { tab1_before: c0, tab1_after_tab2_look: c1, tab2_after_its_look: c1b, tab1_after_tab2_cleared: c2, tab1_cart_lines_after_tab2_look_again: t1Lines };
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
