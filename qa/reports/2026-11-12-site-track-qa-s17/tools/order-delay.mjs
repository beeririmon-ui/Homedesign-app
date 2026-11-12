/**
 * qa-agent, S17 (2026-11-12): the delay copy (master-designer §7) on the order page, in Chromium, against my flag-build
 * server: an order placed and paid through the public API and the mock payment page, then put in supplier_error on MY
 * D1 (d1-exec.sh), then shipped. What is read: the progress line and its current step, the line under it (text, ink,
 * colour, frame, icon), its live region (polite, never alert; on the page before the text is put in, by a
 * MutationObserver from the first byte), the third sentence and every e-mail promise on the page, the API's status_he;
 * and after "shipped", that the line is gone with no message. Screens at 1280 and 400.
 *   QA_COPY=<copy>/site QA_BASE=http://127.0.0.1:8799 QA_OUT=<dir> QA_TOOLS=<dir> node order-delay.mjs
 */
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const { chromium, request: pwRequest } = createRequire(join(COPY, 'package.json'))('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const TOOLS = process.env.QA_TOOLS;
const sql = (s) => spawnSync('bash', [join(TOOLS, 'd1-exec.sh'), s], { encoding: 'utf8', env: { ...process.env, QA_COPY: COPY } }).status;
const api = await pwRequest.newContext({ baseURL: BASE });
const catalog = JSON.parse(spawnSync('cat', [join(COPY, '.generated/catalog.public.json')], { encoding: 'utf8', maxBuffer: 1e8 }).stdout);
const p = catalog.products.find((x) => x.slot === 'vase' && x.price_agorot && x.availability.status === 'available');
const h = { 'cf-connecting-ip': '10.17.0.9' };
const cart = await (await api.post('/api/cart', { headers: h })).json();
await api.put(`/api/cart/${cart.id}/items`, { headers: h, data: { variant_id: p.variants[0].id, qty: 1 } });
const co = await (await api.post('/api/checkout', { headers: h, data: { cart_id: cart.id, customer: { full_name: 'אורנה בודקת', email: 'orna.delay17@example.invalid', phone: '054-7716209' }, address: { city: 'מצפה בדיקה', street: 'הבודקים', house: '9' }, shipping_method: 'express', consents: { terms: true, marketing: false } } })).json();
const session = new URL(co.redirect_url, BASE).pathname.split('/').pop();
await api.post(`/mock-pay/${session}/complete`, { headers: h, form: { outcome: 'success' }, maxRedirects: 0 });
const view = async () => (await api.get(`/api/orders/${co.order_id}`, { headers: { 'x-order-token': co.order_token } })).json();
for (let i = 0; i < 40 && !['sent_to_supplier', 'supplier_error'].includes((await view()).status); i++) await new Promise((r) => setTimeout(r, 750));
const before = (await view()).status;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
async function read(label, vp) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: vp.w, height: vp.h }, isMobile: !!vp.m, hasTouch: !!vp.m });
  await ctx.addInitScript(([id, token]) => {
    localStorage.setItem(`hd.order.${id}`, token);
    window.__qa = { t0: performance.now(), regionAt: null, textAt: null, alerts: 0 };
    new MutationObserver(() => {
      const r = document.querySelector('.order-delay');
      if (r && window.__qa.regionAt === null) window.__qa.regionAt = performance.now();
      if (r && r.textContent && window.__qa.textAt === null) window.__qa.textAt = performance.now();
    }).observe(document, { subtree: true, childList: true, characterData: true });
  }, [co.order_id, co.order_token]);
  const page = await ctx.newPage();
  await page.goto(`${BASE}/order/${co.order_id}/`);
  await page.locator('.order-sheet').waitFor({ timeout: 20_000 });
  await page.waitForTimeout(700);
  const r = await page.evaluate(() => {
    const d = document.querySelector('.order-delay');
    const cs = d ? getComputedStyle(d) : null;
    const body = getComputedStyle(document.querySelector('.order-sheet p') ?? document.body);
    const cur = document.querySelector('.order-steps [aria-current="step"]');
    return {
      steps: [...document.querySelectorAll('.order-steps li')].map((li) => li.textContent),
      current: cur?.textContent ?? null,
      steps_label: document.querySelector('.order-steps')?.getAttribute('aria-label') ?? null,
      line: d?.textContent ?? null,
      line_attrs: d ? { 'aria-live': d.getAttribute('aria-live'), role: d.getAttribute('role'), tag: d.tagName } : null,
      line_colour: cs?.color ?? null,
      body_colour: body.color,
      line_border: cs ? `${cs.borderTopWidth} ${cs.borderTopStyle}` : null,
      line_background: cs?.backgroundColor ?? null,
      line_icon: d ? d.querySelectorAll('svg, img, i, [class*="icon"]').length : null,
      line_font: cs ? `${cs.fontSize} ${cs.fontWeight}` : null,
      body_font: `${body.fontSize} ${body.fontWeight}`,
      alerts: [...document.querySelectorAll('[role="alert"]')].map((e) => e.textContent.slice(0, 60)),
      live_regions: [...document.querySelectorAll('[aria-live], [role="status"]')].map((e) => `${e.tagName.toLowerCase()}.${e.className} ${e.getAttribute('aria-live') ?? e.getAttribute('role')}: "${e.textContent.slice(0, 50)}"`),
      third_sentence: document.body.innerText.includes('אם מועד המסירה ישתנה'),
      old_word: document.body.innerText.includes('מתעכבת'),
      mail_promises: document.body.innerText.split(/\n|(?<=\.)\s/).filter((s) => /מייל|אימייל|דוא"ל/.test(s)).map((s) => s.trim()),
      timing: { regionAt: window.__qa.regionAt, textAt: window.__qa.textAt, gap_ms: window.__qa.textAt !== null && window.__qa.regionAt !== null ? Math.round(window.__qa.textAt - window.__qa.regionAt) : null },
    };
  });
  await page.screenshot({ path: join(OUT, `delay-${label}-${vp.w}.png`), fullPage: true });
  await ctx.close();
  return r;
}
const res = { order_status_before: before, order: co.order_id.replace(/\d{6}$/, '······') };
sql(`UPDATE orders SET status = 'supplier_error' WHERE id = '${co.order_id}'`);
res.api_supplier_error = (await view()).status_he;
res.delayed_1280 = await read('supplier-error', { w: 1280, h: 900 });
res.delayed_400 = await read('supplier-error', { w: 400, h: 860, m: true });
sql(`UPDATE orders SET status = 'shipped' WHERE id = '${co.order_id}'`);
res.api_shipped = (await view()).status_he;
res.shipped_400 = await read('shipped', { w: 400, h: 860, m: true });
sql(`UPDATE orders SET status = 'sent_to_supplier' WHERE id = '${co.order_id}'`);
res.normal_1280 = await read('sent-to-supplier', { w: 1280, h: 900 });
await browser.close();
writeFileSync(join(OUT, 'order-delay.json'), JSON.stringify(res, null, 1));
const d = res.delayed_1280;
console.log(`QA delay copy: before ${before}; API status_he in supplier_error "${res.api_supplier_error}", shipped "${res.api_shipped}"`);
console.log(`  delayed: steps ${d.steps.join(' · ')}, current "${d.current}", label "${d.steps_label}"; line "${d.line}"; ${JSON.stringify(d.line_attrs)}; ink ${d.line_colour} vs ${d.body_colour}; border ${d.line_border}; bg ${d.line_background}; icons ${d.line_icon}; font ${d.line_font} vs ${d.body_font}; alerts ${JSON.stringify(d.alerts)}; region before text: ${JSON.stringify(d.timing)}; third sentence ${d.third_sentence}; "מתעכבת" ${d.old_word}`);
console.log(`  delayed 400: line "${res.delayed_400.line}", gap ${res.delayed_400.timing.gap_ms} ms`);
console.log(`  mail promises on the delayed page: ${JSON.stringify(d.mail_promises)}`);
console.log(`  shipped: current "${res.shipped_400.current}", line "${res.shipped_400.line}", live regions ${JSON.stringify(res.shipped_400.live_regions)}, alerts ${JSON.stringify(res.shipped_400.alerts)}`);
console.log(`  normal (sent_to_supplier): current "${res.normal_1280.current}", line "${res.normal_1280.line}"`);
