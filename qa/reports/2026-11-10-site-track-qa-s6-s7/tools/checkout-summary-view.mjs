/** qa-agent, 2026-11-10 (S6-S7): the site checkout after an empty submit, as the viewport shows it (not a full-page
 * capture): where focus is, whether the error summary's heading is under the sticky header, and the skip link. */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-pings', '--disable-features=PushMessaging,GCMChannelStatusRequest,MediaRouter'] });
const res = [];
for (const [w, h, mouse] of [[400, 860, true], [1280, 900, true], [400, 860, false]]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h }, isMobile: w < 500, hasTouch: w < 500 });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/`, { waitUntil: 'load' });
  await p.evaluate(async () => {
    const c = await (await fetch('/api/cart', { method: 'POST', headers: { 'content-type': 'application/json' }, body: '{}' })).json();
    await fetch(`/api/cart/${c.id}/items`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ variant_id: 'cushions-washed-cotton-frayed-ws8a6:50x50+rust-orange', qty: 1 }) });
    localStorage.setItem('hd.cart', c.id);
  });
  await p.goto(`${BASE}/checkout/`, { waitUntil: 'load' });
  await p.waitForTimeout(900);
  if (mouse) await p.locator('form button[type="submit"]').first().click();
  else { await p.locator('form button[type="submit"]').first().focus(); await p.keyboard.press('Enter'); }
  await p.waitForTimeout(900);
  const r = await p.evaluate(() => {
    const head = document.querySelector('.site-header, header');
    const hb = head?.getBoundingClientRect();
    const a = document.activeElement;
    const ab = a?.getBoundingClientRect();
    const sum = document.querySelector('[role="alert"], .error-summary, #errors, [id*="error"]');
    const title = sum?.querySelector('h2, h3, p, strong') ?? sum;
    const tb = title?.getBoundingClientRect();
    const skip = [...document.querySelectorAll('a')].find((x) => /דילוג/.test(x.textContent));
    const sb = skip?.getBoundingClientRect();
    return {
      header: hb ? [Math.round(hb.top), Math.round(hb.bottom), getComputedStyle(head).position] : null,
      focus: a ? `${a.tagName.toLowerCase()}#${a.id}.${(a.className || '').toString().split(' ')[0]} "${(a.textContent || '').trim().slice(0, 30)}" top ${Math.round(ab.top)}` : null,
      summary_title: title ? `${(title.textContent || '').trim().slice(0, 40)} top ${Math.round(tb.top)} bottom ${Math.round(tb.bottom)}` : null,
      title_under_header: hb && tb ? tb.top < hb.bottom : null,
      skip_link_visible: sb ? sb.width > 2 && sb.height > 2 && sb.bottom > 0 && sb.top < innerHeight : null,
    };
  });
  await p.screenshot({ path: `${OV}/site-checkout-after-empty-submit-${w}-${mouse ? 'mouse' : 'keyboard'}.png` });
  res.push({ width: w, by: mouse ? 'mouse' : 'keyboard', ...r });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
