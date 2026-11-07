/**
 * qa-agent, 2026-11-07 (interface track S4, the shop): checked in the browser against QA's snapshot of web/dist.
 *  1. "המראה כולו לסל" on every frame: what lands in the test cart vs the frame's items (each sellable product once, in
 *     the frame's option), the "לא נכללים" line vs the unpriced / not-sold items, and a second press
 *  2. the cart: + / − / remove, the focus after each, the cap at 20; a PRE1 line (a snapshot that was for sale, on a page
 *     where it is not): shown, out of the sum, out of the checkout and the order
 *  3. /story/checkout/ next to the real /checkout/ (a real cart through the local API): fields, labels, autocomplete, the
 *     messages of an empty submit, the summary and its focus, the field-level errors, the shipping (below and over the
 *     free threshold); then a valid test order: the requests made, the order page, the cart emptied, what the browser keeps
 *  4. SET1 on the detail pages: "איך לקנות", the set by default, a single unit only where offered, "(משוער)"
 *  5. PRE1 in the tool's wheel (/rooms/living-room/, the rug): the tag, no add button, a waitlist
 *
 *   QA_BASE=http://127.0.0.1:8799 node qa/reports/2026-11-07-site-track-qa-s4/tools/check-shop.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const OUT = process.argv[2] ?? '/dev/stdout';
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8788';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = { base: BASE, run_at: new Date().toISOString() };
const newCtx = (w = 1280, h = 900) => browser.newContext({ viewport: { width: w, height: h }, locale: 'he-IL' });
const storyCart = (page) => page.evaluate(() => JSON.parse(localStorage.getItem('hd.story.cart') ?? 'null'));

// ---------- 1. the whole look ----------
res.look = [];
for (const style of ['nordic', 'warm-modern', 'modern-country', 'boho']) {
  const ctx = await newCtx();
  const page = await ctx.newPage();
  await page.goto(`${BASE}/story/living-room/${style}/`, { waitUntil: 'load' });
  await page.waitForTimeout(800);
  const frames = await page.evaluate(() => JSON.parse(document.getElementById('st-data').textContent).frames.map((f) => f.id));
  for (const id of frames) {
    await page.evaluate(() => localStorage.removeItem('hd.story.cart'));
    const expect = await page.evaluate((id) => {
      const d = JSON.parse(document.getElementById('st-data').textContent);
      const items = d.frames.find((f) => f.id === id).items.map((k) => d.items[k]);
      return {
        sellable: [...new Set(items.filter((x) => x.status === 'available' && x.variant_id).map((x) => x.variant_id))],
        sellable_without_dot: items.filter((x) => x.status === 'available' && !x.dot).map((x) => x.product),
        unpriced: items.filter((x) => x.status === 'unpriced').length,
        unavailable: items.filter((x) => x.status === 'unavailable').length,
        button: document.getElementById(`look-${id}`)?.textContent.trim() ?? null,
        left: document.querySelector(`#look-${id} + .st-look-left`)?.textContent.trim() ?? null,
      };
    }, id);
    const btn = page.locator(`#look-${id}`);
    let first = null;
    let second = null;
    if (await btn.count()) {
      await btn.scrollIntoViewIfNeeded();
      await btn.click();
      await page.waitForTimeout(400);
      first = (await storyCart(page))?.items.map((i) => ({ variant_id: i.variant_id, pack: i.pack, qty: i.qty })) ?? [];
      await page.waitForTimeout(2700);
      await btn.click();
      await page.waitForTimeout(400);
      second = (await storyCart(page))?.items.map((i) => ({ variant_id: i.variant_id, qty: i.qty })) ?? [];
    }
    const got = (first ?? []).map((x) => x.variant_id);
    res.look.push({
      page: style,
      frame: id,
      button: expect.button,
      left: expect.left,
      expected: expect.sellable,
      added: got,
      each_once: got.length === new Set(got).size && (first ?? []).every((x) => x.qty === 1 && x.pack === 'set'),
      same_set: got.length === expect.sellable.length && expect.sellable.every((v) => got.includes(v)),
      left_counts_ok: !expect.left || ((expect.unpriced === 0 || expect.left.includes(expect.unpriced === 1 ? 'מוצר אחד בלי' : `${expect.unpriced} מוצרים בלי`)) && (expect.unavailable === 0 || expect.left.includes('אינו זמין'))),
      unpriced: expect.unpriced,
      unavailable: expect.unavailable,
      sellable_without_dot: expect.sellable_without_dot,
      second_press_quantities: second ? [...new Set(second.map((x) => x.qty))] : null,
    });
  }
  await ctx.close();
}

// ---------- 2. the cart: quantity, remove, focus; a PRE1 line ----------
{
  const ctx = await newCtx();
  const page = await ctx.newPage();
  await page.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  await page.waitForTimeout(800);
  await page.evaluate(() => localStorage.removeItem('hd.story.cart'));
  await page.locator('#look-A').click();
  await page.waitForTimeout(400);
  // a PRE1 line: the rug, as a snapshot taken while it was for sale (it is not for sale on this page)
  const rug = await page.evaluate(() => {
    const d = JSON.parse(document.getElementById('st-data').textContent);
    const it = Object.values(d.items).find((x) => x.product === 'rug-cj-braided-wool-natural');
    const s = JSON.parse(localStorage.getItem('hd.story.cart'));
    const v = { variant_id: it.variant_id ?? 'rug-cj-braided-wool-natural:200x300+square', product_id: it.product, name_he: it.name_he, option_he: null, price_agorot: 129900, set_qty: 1, available: true };
    s.items.push({ variant_id: v.variant_id, pack: 'set', qty: 1, v });
    localStorage.setItem('hd.story.cart', JSON.stringify(s));
    return { status: it.status, variant_id: v.variant_id, name_he: it.name_he };
  });
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(800);
  await page.locator('#st-cart-open').click();
  await page.waitForTimeout(500);
  const state = () =>
    page.evaluate(() => ({
      lines: [...document.querySelectorAll('#st-cart-lines .st-cart-line')].map((l) => ({ name: l.querySelector('.mag-credit-name').textContent, qty: l.querySelector('output').textContent })),
      held: document.getElementById('st-cart-held').hidden ? null : document.getElementById('st-cart-held').textContent.trim(),
      total: document.getElementById('st-cart-total').textContent,
      focus: document.activeElement ? `${document.activeElement.tagName.toLowerCase()}#${document.activeElement.id}[${document.activeElement.dataset?.act ?? ''}] ${document.activeElement.getAttribute('aria-label') ?? ''}` : null,
      live: document.getElementById('mag-live')?.textContent ?? '',
    }));
  const c0 = await state();
  const sumOfLines = await page.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('hd.story.cart'));
    return s.items.length;
  });
  const first = page.locator('#st-cart-lines .st-cart-line').first();
  await first.locator('button[data-act="more"]').click();
  await page.waitForTimeout(300);
  const c1 = await state();
  await page.locator('#st-cart-lines .st-cart-line').first().locator('button[data-act="less"]').click();
  await page.waitForTimeout(300);
  const c2 = await state();
  // the cap: 20
  for (let i = 0; i < 22; i++) {
    await page.locator('#st-cart-lines .st-cart-line').first().locator('button[data-act="more"]').click();
    await page.waitForTimeout(60);
  }
  const c3 = await state();
  await page.locator('#st-cart-lines .st-cart-line').first().locator('button[data-act="remove"]').click();
  await page.waitForTimeout(300);
  const c4 = await state();
  // keyboard: the − at quantity 1 removes the line; where does the focus go
  await page.locator('#st-cart-lines .st-cart-line').first().locator('button[data-act="less"]').focus();
  await page.keyboard.press('Enter');
  await page.waitForTimeout(300);
  const c5 = await state();
  res.cart = { pre1_seeded: rug, items_in_storage: sumOfLines, opened: c0, after_plus: c1, after_minus: c2, after_22_plus: c3, after_remove: c4, after_minus_at_1_by_keyboard: c5 };
  // the checkout with the PRE1 line still in the storage
  await page.keyboard.press('Escape');
  await page.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await page.waitForTimeout(800);
  res.cart.checkout_with_pre1 = await page.evaluate(() => ({
    held: document.getElementById('co-held')?.hidden ? null : document.getElementById('co-held')?.textContent,
    lines: [...document.querySelectorAll('#co-lines li')].map((l) => l.textContent),
    subtotal: document.getElementById('co-subtotal').textContent,
    total: document.getElementById('co-total').textContent,
  }));
  res.cart.pre1_in_checkout_lines = res.cart.checkout_with_pre1.lines.some((l) => l.includes(rug.name_he));
  await ctx.close();
}

// ---------- 3. the test checkout next to the real one ----------
const fieldsOf = (page, formSel) =>
  page.evaluate((formSel) => {
    const f = document.querySelector(formSel);
    if (!f) return null;
    return [...f.querySelectorAll('input, select, textarea')].map((el) => ({
      name: el.name,
      type: el.type,
      id: el.id,
      label: el.id ? (document.querySelector(`label[for="${el.id}"]`)?.textContent.trim() ?? el.closest('label')?.textContent.trim() ?? null) : (el.closest('label')?.textContent.trim() ?? null),
      autocomplete: el.getAttribute('autocomplete'),
      inputmode: el.getAttribute('inputmode'),
      required: el.required,
      maxlength: el.getAttribute('maxlength'),
      value: el.type === 'radio' || el.type === 'checkbox' ? el.value : undefined,
    }));
  }, formSel);
const errorsOf = (page) =>
  page.evaluate(() => {
    const out = {};
    for (const el of document.querySelectorAll('[aria-invalid="true"]')) {
      const ids = (el.getAttribute('aria-describedby') ?? '').split(' ').filter(Boolean);
      const near = ids.map((i) => document.getElementById(i)?.textContent.trim()).filter(Boolean);
      const sib = el.id ? document.getElementById(`err-${el.id.replace(/^f-/, '')}`) ?? document.getElementById(`e-${el.id.replace(/^f-/, '')}`) : null;
      out[el.name] = { described: near, next: sib && !sib.hidden ? sib.textContent.trim() : null };
    }
    const a = document.activeElement;
    return {
      fields: out,
      focus: a ? `${a.tagName.toLowerCase()}#${a.id}.${[...a.classList].join('.')}` : null,
      summary_text: a?.textContent?.trim().slice(0, 400) ?? null,
      summary_links: a ? [...a.querySelectorAll('a')].map((x) => x.getAttribute('href')) : [],
      summary_role: a?.getAttribute('role') ?? a?.querySelector('[role]')?.getAttribute('role') ?? null,
    };
  });
{
  const ctx = await newCtx();
  const page = await ctx.newPage();
  // the real site: a cart through the local API, then /checkout/
  const variant = 'wall-decor-cj-macrame-dowel-50x70:default';
  const real = await page.evaluate(
    async ({ variant }) => {
      const c = await (await fetch('/api/cart', { method: 'POST' })).json();
      const r = await fetch(`/api/cart/${c.id}/items`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ variant_id: variant, pack: 'set', qty: 1 }) });
      return { id: c.id, put: r.status };
    },
    { variant },
  ).catch(async () => {
    await page.goto(`${BASE}/`, { waitUntil: 'load' });
    return null;
  });
  let realCart = real;
  if (!realCart) {
    await page.goto(`${BASE}/`, { waitUntil: 'load' });
    realCart = await page.evaluate(async ({ variant }) => {
      const c = await (await fetch('/api/cart', { method: 'POST' })).json();
      const r = await fetch(`/api/cart/${c.id}/items`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ variant_id: variant, pack: 'set', qty: 1 }) });
      localStorage.setItem('hd.cart', c.id);
      return { id: c.id, put: r.status };
    }, { variant });
  }
  await page.goto(`${BASE}/checkout/`, { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  const realForm = (await page.locator('form').count()) ? 'form' : null;
  const realFields = realForm ? await fieldsOf(page, 'form') : null;
  const realShipping = await page.evaluate(() => [...document.querySelectorAll('input[name="shipping"]')].map((r) => r.closest('label')?.textContent.replace(/\s+/g, ' ').trim()));
  if (realForm) {
    await page.locator('form button[type="submit"]').click();
    await page.waitForTimeout(600);
  }
  const realErrors = realForm ? await errorsOf(page) : null;
  // the story's test checkout with the look of the Nordic frame A (over ₪299) and with one cushion (below)
  const p2 = await ctx.newPage();
  const requests = [];
  p2.on('request', (r) => requests.push({ method: r.method(), url: r.url().replace(BASE, '') }));
  await p2.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  await p2.evaluate(() => localStorage.removeItem('hd.story.cart'));
  await p2.waitForTimeout(500);
  await p2.evaluate(() => window.__story.openSheet('A-5'));
  await p2.waitForTimeout(400);
  await p2.locator('#st-add').click();
  await p2.waitForTimeout(300);
  await p2.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p2.waitForTimeout(800);
  const below = await p2.evaluate(() => ({ subtotal: document.getElementById('co-subtotal').textContent, shipping: document.getElementById('co-shipping').textContent, free: document.getElementById('co-free').textContent, ship_labels: [...document.querySelectorAll('input[name="shipping"]')].map((r) => r.closest('label')?.textContent.replace(/\s+/g, ' ').trim()) }));
  await p2.goto(`${BASE}/story/living-room/nordic/`, { waitUntil: 'load' });
  await p2.waitForTimeout(500);
  await p2.locator('#look-A').click();
  await p2.waitForTimeout(400);
  await p2.goto(`${BASE}/story/checkout/`, { waitUntil: 'load' });
  await p2.waitForTimeout(800);
  const over = await p2.evaluate(() => ({ subtotal: document.getElementById('co-subtotal').textContent, shipping: document.getElementById('co-shipping').textContent, free: document.getElementById('co-free').textContent }));
  await p2.locator('input[name="shipping"][value="express"]').check();
  await p2.waitForTimeout(200);
  const overExpress = await p2.evaluate(() => ({ shipping: document.getElementById('co-shipping').textContent, total: document.getElementById('co-total').textContent }));
  await p2.locator('input[name="shipping"][value="economy"]').check();
  const storyFields = await fieldsOf(p2, '#co-form');
  await p2.locator('#co-form button[type="submit"]').click();
  await p2.waitForTimeout(500);
  const storyErrors = await errorsOf(p2);
  // a valid order
  const typed = { full_name: 'דנה לוי-בדיקה', email: 'dana.qa@example.com', phone: '050-1234567', city: 'חיפה', street: 'הרצל', house: '12', zip: '3303112' };
  for (const [k, v] of Object.entries(typed)) await p2.locator(`#f-${k}`).fill(v);
  await p2.locator('#f-terms').check();
  const before = requests.length;
  await Promise.all([p2.waitForURL(/\/story\/order\//, { timeout: 15000 }), p2.locator('#co-form button[type="submit"]').click()]);
  await p2.waitForTimeout(1200);
  const orderPage = await p2.evaluate(() => ({
    url: location.pathname + location.search,
    number: document.getElementById('or-number')?.textContent,
    greeting: document.getElementById('or-greeting')?.textContent,
    lines: [...document.querySelectorAll('#or-lines li')].length,
    sum: document.getElementById('or-sum')?.textContent,
    city: document.getElementById('or-city')?.textContent,
    focus: document.activeElement?.id,
    cart_after: localStorage.getItem('hd.story.cart'),
    count_badge: document.getElementById('st-cart-count')?.textContent,
    storage: Object.fromEntries(Object.keys(localStorage).map((k) => [k, localStorage.getItem(k)])),
    session: Object.fromEntries(Object.keys(sessionStorage).map((k) => [k, sessionStorage.getItem(k)])),
    cookies: document.cookie,
  }));
  const afterReqs = requests.slice(before);
  const allStorage = JSON.stringify(orderPage.storage) + JSON.stringify(orderPage.session) + orderPage.cookies;
  res.checkout = {
    real_cart: realCart,
    real_fields: realFields,
    story_fields: storyFields,
    field_diff: realFields && storyFields ? { only_real: realFields.filter((a) => !storyFields.some((b) => b.name === a.name && (b.value ?? '') === (a.value ?? ''))).map((x) => x.name + (x.value ? `=${x.value}` : '')), only_story: storyFields.filter((a) => !realFields.some((b) => b.name === a.name && (b.value ?? '') === (a.value ?? ''))).map((x) => x.name + (x.value ? `=${x.value}` : '')), attr_diff: storyFields.filter((a) => { const b = realFields.find((x) => x.name === a.name && (x.value ?? '') === (a.value ?? '')); return b && (b.type !== a.type || b.autocomplete !== a.autocomplete || b.inputmode !== a.inputmode || b.required !== a.required || b.maxlength !== a.maxlength || b.label !== a.label); }).map((a) => ({ story: a, real: realFields.find((x) => x.name === a.name && (x.value ?? '') === (a.value ?? '')) })) } : null,
    real_shipping: realShipping,
    real_errors: realErrors,
    story_errors: storyErrors,
    same_messages: realErrors && storyErrors ? Object.keys(realErrors.fields).every((k) => JSON.stringify(realErrors.fields[k].described) === JSON.stringify(storyErrors.fields[k]?.described) || realErrors.fields[k].described[0] === storyErrors.fields[k]?.next) : null,
    shipping_below: below,
    shipping_over: over,
    shipping_over_express: overExpress,
    order_page: { ...orderPage, storage: Object.keys(orderPage.storage), session: Object.keys(orderPage.session) },
    stored_orders: orderPage.storage['hd.story.orders'] ? JSON.parse(orderPage.storage['hd.story.orders']) : null,
    personal_data_in_storage: Object.fromEntries(Object.entries(typed).map(([k, v]) => [k, allStorage.includes(v)])),
    requests_on_submit_and_order: afterReqs,
    non_get_or_api: afterReqs.filter((r) => r.method !== 'GET' || r.url.startsWith('/api/')),
  };
  await ctx.close();
}

// ---------- 4. SET1 ----------
{
  const ctx = await newCtx();
  const page = await ctx.newPage();
  res.set1 = [];
  for (const style of ['nordic', 'warm-modern', 'modern-country', 'boho']) {
    await page.goto(`${BASE}/story/living-room/${style}/`, { waitUntil: 'load' });
    const hrefs = await page.evaluate(() => [...new Set(Object.values(JSON.parse(document.getElementById('st-data').textContent).items).map((x) => x.href.split('?')[0]))]);
    for (const h of hrefs) {
      await page.goto(BASE + h, { waitUntil: 'load' });
      await page.waitForTimeout(250);
      const r = await page.evaluate(() => {
        const d = JSON.parse(document.getElementById('st-data').textContent).detail;
        const radios = [...document.querySelectorAll('input[name="st-pack"]')].map((x) => ({ value: x.value, checked: x.checked, label: x.closest('label')?.textContent.replace(/\s+/g, ' ').trim() }));
        const units = d.skus.filter((k) => k.unit_price_agorot != null);
        return { product: d.product, set_qty: d.set_qty, skus: d.skus.length, skus_with_unit: units.length, unit_estimated: units.some((k) => k.unit_estimated), how_to_buy: !!document.getElementById('st-pd-pack'), radios, estimated_mark: !!document.getElementById('st-pd-pack')?.textContent.includes('משוער'), status: d.status };
      });
      if (r.set_qty > 1 || r.radios.length) res.set1.push({ page: h, ...r });
    }
  }
  // the cart line for a single piece
  const single = res.set1.find((x) => x.radios.some((r) => r.value === 'unit') && x.status === 'available');
  if (single) {
    await page.goto(BASE + single.page, { waitUntil: 'load' });
    await page.evaluate(() => localStorage.removeItem('hd.story.cart'));
    await page.locator('input[name="st-pack"][value="unit"]').check({ force: true });
    await page.waitForTimeout(200);
    const price = await page.locator('#st-pd-price').textContent();
    await page.locator('#st-pd-add').click();
    await page.waitForTimeout(300);
    await page.locator('#st-cart-open').click();
    await page.waitForTimeout(400);
    res.set1_cart = { page: single.page, price_shown: price, line: await page.locator('#st-cart-lines .st-cart-line .mag-credit-name').first().textContent(), detail: await page.locator('#st-cart-lines .st-cart-line .mag-credit-detail').first().textContent() };
  }
  await ctx.close();
}

// ---------- 5. PRE1 in the wheel ----------
{
  const ctx = await newCtx();
  const page = await ctx.newPage();
  await page.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 }).catch(() => null);
  await page.waitForTimeout(1000);
  const rugBtn = page.locator('button.hotspot[data-slot="rug"]');
  let wheel = null;
  if (await rugBtn.count()) {
    await rugBtn.click({ force: true });
    await page.waitForTimeout(1500);
    wheel = await page.evaluate(() => {
      const opts = [...document.querySelectorAll('[role="radio"], [role="option"], .wheel-option, .variant-card')].slice(0, 12).map((o) => ({ text: o.textContent.replace(/\s+/g, ' ').trim().slice(0, 140), aria: o.getAttribute('aria-label'), checked: o.getAttribute('aria-checked') ?? o.getAttribute('aria-selected') }));
      const body = document.body.textContent;
      return {
        options: opts,
        tag_present: body.includes('אינו במלאי'),
        unavailable_text: body.includes('המלאי אינו זמין כעת'),
        waitlist: !!document.querySelector('form[action*="waitlist"], [data-waitlist], #waitlist, .waitlist') || /עדכנו אותי|רשימת המתנה/.test(body),
        add_buttons: [...document.querySelectorAll('button')].filter((b) => /הוספה לסל|להוסיף לסל/.test(b.textContent) && b.offsetParent !== null).map((b) => ({ text: b.textContent.trim(), disabled: b.disabled })),
      };
    });
  }
  res.wheel_pre1 = wheel;
  await page.screenshot({ path: '/home/user/homedesign-app/qa/reports/2026-11-07-site-track-qa-s4/overlays/wheel-rug-1280.png' });
  await ctx.close();
}
await browser.close();
writeFileSync(OUT, JSON.stringify(res, null, 1));
console.log('done');
