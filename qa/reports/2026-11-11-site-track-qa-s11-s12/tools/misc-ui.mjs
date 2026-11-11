/**
 * qa-agent, 2026-11-11 (S11–S12 at b94c5bc1): the smaller findings, in the browser against the copy's Worker.
 *  ת11  a line that stops being sold after it was added: the cart says so ("פריט אחד כבר לא זמין והוסר. הוא לא ייגבה.")
 *       and charges nothing (the variant is switched off in D1 by the caller between the two halves: QA_PHASE=add|look)
 *  ת14  from the story's contents (/story/) to the tool and back ("חזרה לסיפור")
 *  ת22  the set panel of the warm-modern wheel: every piece of every set whole on screen (1280×720, 400×800)
 *  ת23  a direct entry to ?style=warm-modern on a phone: no Nordic or transition bytes, 15 s at rest
 *  ת25  the empty checkout's way back: a target of 44 px at least
 *   QA_BASE=… QA_COPY=<copy>/site QA_OUT=<qa folder> QA_PHASE=add|look|rest node misc-ui.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const STATE = join(OUT, 'data/misc-ui.json');
const res = existsSync(STATE) ? JSON.parse(readFileSync(STATE, 'utf8')) : {};
const save = () => writeFileSync(STATE, JSON.stringify(res, null, 1));
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const ctxOf = async (v) => {
  const c = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, isMobile: !!v.m, hasTouch: !!v.m, extraHTTPHeaders: { 'cf-connecting-ip': '198.51.100.222' } });
  c.setDefaultTimeout(120000);
  return c;
};
const PHASE = process.env.QA_PHASE ?? 'rest';
const VARIANT = 'cushions-wide-stripe-corduroy-light-green-narue:camel';

if (PHASE === 'add') {
  const h = { 'content-type': 'application/json', 'cf-connecting-ip': '198.51.100.223' };
  const cart = (await (await fetch(`${BASE}/api/cart`, { method: 'POST', headers: h })).json()).id;
  for (const v of [VARIANT, 'sofa-cover-cotton-muslin-fringe-0iz5d:150x200+pecan'])
    await fetch(`${BASE}/api/cart/${cart}/items`, { method: 'PUT', headers: h, body: JSON.stringify({ variant_id: v, qty: 1, pack: 'set' }) });
  res.t11 = { cart, before: await (await fetch(`${BASE}/api/cart/${cart}`, { headers: h })).json() };
  save();
  console.log('cart', cart, 'lines', res.t11.before.lines.length);
}

if (PHASE === 'look') {
  // the variant was switched off by the caller (D1); the cart page, the checkout page, then a checkout through the API
  const cart = res.t11.cart;
  const out = {};
  for (const v of [{ w: 1280, h: 900 }]) {
    const ctx = await ctxOf(v);
    const p = await ctx.newPage();
    await p.goto(`${BASE}/`);
    await p.evaluate((id) => localStorage.setItem('hd.cart', id), cart);
    await p.goto(`${BASE}/cart/`);
    await p.locator('.cart-line').first().waitFor();
    await p.waitForTimeout(800);
    out.cart_text = await p.evaluate(() => document.querySelector('main').innerText);
    await p.screenshot({ path: join(OUT, 'overlays', 't11-cart-removed.png'), fullPage: true });
    await p.goto(`${BASE}/checkout/`);
    await p.locator('aside.summary li').first().waitFor();
    out.checkout_text = await p.evaluate(() => document.querySelector('main').innerText);
    await ctx.close();
  }
  const api = await (await fetch(`${BASE}/api/cart/${cart}`, { headers: { 'cf-connecting-ip': '198.51.100.223' } })).json();
  out.api = { lines: api.lines.map((l) => l.variant_id), removed: api.removed, subtotal: api.subtotal_agorot };
  out.notice_in_cart = out.cart_text.includes('פריט אחד כבר לא זמין והוסר. הוא לא ייגבה.');
  out.notice_in_checkout = out.checkout_text.includes('פריט אחד כבר לא זמין והוסר');
  delete out.cart_text;
  delete out.checkout_text;
  res.t11.after = out;
  save();
  console.log('ת11', JSON.stringify(out));
}

if (PHASE === 'rest') {
  // ת14
  {
    const ctx = await ctxOf({ w: 1280, h: 900 });
    const p = await ctx.newPage();
    await p.goto(`${BASE}/story/`);
    const link = p.locator('a[href*="/rooms/"][href*="from="]').first();
    const href = await link.getAttribute('href');
    await link.click();
    await p.waitForURL(/\/rooms\//);
    const back = p.getByRole('link', { name: /חזרה לסיפור/ });
    const n = await back.count();
    const backHref = n ? await back.first().getAttribute('href') : null;
    if (n) {
      await back.first().click();
      await p.waitForLoadState('load');
    }
    res.t14 = { link: href, back_links: n, back_href: backHref, landed: p.url().replace(BASE, '') };
    console.log('ת14', JSON.stringify(res.t14));
    await ctx.close();
  }
  // ת22
  res.t22 = [];
  for (const v of [
    { w: 1280, h: 720 },
    { w: 1440, h: 900 },
    { w: 400, h: 800, m: true },
  ]) {
    const ctx = await ctxOf(v);
    const p = await ctx.newPage();
    await p.goto(`${BASE}/rooms/living-room/?style=warm-modern`);
    await p.locator('button.hotspot[data-slot="cushions"]').waitFor({ state: 'attached' });
    const dialog = p.getByRole('dialog');
    for (let i = 0; i < 6 && !(await dialog.isVisible()); i++) {
      await p.locator('button.hotspot[data-slot="cushions"]').focus();
      await p.keyboard.press('Enter');
      await p.waitForTimeout(2000);
    }
    await p.waitForTimeout(1500);
    const sets = [];
    for (let k = 0; k < 3; k++) {
      const rows = await p.evaluate(() => {
        const d = document.querySelector('[role="dialog"]');
        const items = [...d.querySelectorAll('li')].filter((li) => /₪/.test(li.textContent) && li.offsetParent);
        const vv = { h: innerHeight, w: innerWidth };
        return items.map((li) => {
          const r = li.getBoundingClientRect();
          // the nearest scrolling box above the row
          let s = li.parentElement;
          while (s && s !== d.parentElement && !(s.scrollHeight > s.clientHeight + 1 && /auto|scroll/.test(getComputedStyle(s).overflowY))) s = s.parentElement;
          const sb = s && s !== d.parentElement ? s.getBoundingClientRect() : { top: 0, bottom: vv.h };
          return { text: li.textContent.replace(/\s+/g, ' ').trim().slice(0, 70), top: Math.round(r.top), bottom: Math.round(r.bottom), whole_on_screen: r.top >= 0 && r.bottom <= vv.h && r.top >= sb.top - 0.5 && r.bottom <= sb.bottom + 0.5, scroller: s && s !== d.parentElement ? s.className.slice(0, 30) : null };
        });
      });
      sets.push(rows);
      // on a phone the dialog scrolls as a whole: what is under the fold is reached by scrolling the dialog, not cut
      await p.keyboard.press('ArrowLeft');
      await p.waitForTimeout(900);
    }
    await p.screenshot({ path: join(OUT, 'overlays', `t22-set-panel-${v.w}x${v.h}.png`) });
    res.t22.push({ viewport: `${v.w}x${v.h}`, sets });
    console.log('ת22', v.w, JSON.stringify(sets.map((rows) => rows.map((r) => `${r.whole_on_screen ? 'ok' : 'CUT'}:${r.text.slice(0, 18)}${r.scroller ? `(${r.scroller})` : ''}`))));
    await ctx.close();
  }
  // ת23
  {
    const ctx = await ctxOf({ w: 400, h: 860, m: true });
    const p = await ctx.newPage();
    const reqs = [];
    p.on('request', (r) => reqs.push(r.url().replace(BASE, '')));
    await p.goto(`${BASE}/rooms/living-room/?style=warm-modern`, { waitUntil: 'load' });
    await p.waitForTimeout(15000);
    const nordic = reqs.filter((u) => /\/media\/rooms\/(living-room|hall)\/nordic\/|\/media\/transitions\//.test(u));
    res.t23 = { requests: reqs.length, nordic_or_transition: nordic, media: reqs.filter((u) => u.startsWith('/media/')) };
    console.log('ת23', JSON.stringify({ n: reqs.length, nordic }));
    await ctx.close();
  }
  // ת25
  res.t25 = [];
  for (const v of [
    { w: 400, h: 800, m: true },
    { w: 1280, h: 800 },
  ]) {
    const ctx = await ctxOf(v);
    const p = await ctx.newPage();
    await p.goto(`${BASE}/checkout/`);
    await p.waitForTimeout(1500);
    const box = await p.evaluate(() => {
      const a = [...document.querySelectorAll('main a, main button')].find((x) => /חזרה לסלון/.test(x.textContent));
      if (!a) return null;
      const r = a.getBoundingClientRect();
      return { text: a.textContent.trim(), w: Math.round(r.width), h: Math.round(r.height) };
    });
    res.t25.push({ viewport: `${v.w}`, box });
    console.log('ת25', v.w, JSON.stringify(box));
    await ctx.close();
  }
  save();
}
await browser.close();
