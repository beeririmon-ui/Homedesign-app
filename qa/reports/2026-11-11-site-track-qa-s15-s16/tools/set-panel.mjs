/**
 * qa-agent, S15 (2026-11-11): the set panel and the wheel's words in Chromium (master-designer §2 and §5), both houses,
 * 1280 and 400: the hotspot's name, the wheel's line and heading, the set names in wheel order, the pieces' words
 * ("עוד לא במכירה", "המלאי אינו זמין כעת", the hidden "לסל: … בלבד"), the note and the button of a set with a piece out
 * of stock, and the list under the room (intro_he). A screen of each panel.
 *   QA_BASE=… QA_COPY=<copy>/site QA_OUT=<folder> node set-panel.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const { chromium } = createRequire(join(COPY, 'package.json'))('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = {};
for (const [house, url] of [
  ['warm-modern', '/rooms/living-room/?style=warm-modern'],
  ['nordic', '/rooms/living-room/'],
]) {
  for (const vp of [
    { w: 1280, h: 800 },
    { w: 400, h: 860, m: true },
  ]) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: vp.w, height: vp.h }, isMobile: !!vp.m, hasTouch: !!vp.m });
    ctx.setDefaultTimeout(45_000);
    const page = await ctx.newPage();
    await page.goto(`${BASE}${url}`, { waitUntil: 'load' });
    const spot = page.locator('button.hotspot[data-slot="cushions"]');
    await spot.waitFor({ state: 'attached' });
    const out = { hotspot_label: await spot.getAttribute('aria-label') };
    out.room_list = await page.evaluate(() => [...document.querySelectorAll('.room-intro p, .room-list p, .room-intro')].map((x) => x.textContent.replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 3));
    await spot.focus();
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog');
    await dialog.waitFor();
    await page.waitForTimeout(1500);
    out.eyebrow = await dialog.locator('.picker-head .eyebrow').textContent();
    out.heading = await dialog.locator('.picker-head h2').textContent();
    out.options = await dialog.evaluate((d) => [...d.querySelectorAll('[role=radio], .wheel-option, button[aria-pressed]')].map((b) => (b.getAttribute('aria-label') ?? b.textContent).replace(/\s+/g, ' ').trim()).slice(0, 8));
    out.panel = await dialog.evaluate((d) => {
      const p = d.querySelector('.set-panel');
      if (!p) return null;
      return {
        items_label: p.querySelector('.set-items')?.getAttribute('aria-label'),
        items: [...p.querySelectorAll('.set-item')].map((li) => li.innerText.replace(/\s+/g, ' ').trim()),
        hidden_buy: [...p.querySelectorAll('.set-buy .sr-only')].map((s) => s.textContent),
        note: p.querySelector('.set-note')?.textContent ?? null,
        button: [...p.querySelectorAll('button')].map((b) => b.textContent.replace(/\s+/g, ' ').trim()).find((t) => t.startsWith('הסט')) ?? null,
      };
    });
    out.words_in_dialog = await dialog.evaluate((d) => ({ variations: /וריאצי/.test(d.innerText), set_tag: d.innerText.includes('(סט)'), in_room: d.innerText.includes('· בחדר'), temp: d.innerText.includes('מיקום זמני') }));
    await page.screenshot({ path: join(OUT, 'overlays', `s15-wheel-${house}-${vp.w}.png`) });
    res[`${house}_${vp.w}`] = out;
    console.log(house, vp.w, JSON.stringify(out));
    await ctx.close();
  }
}
await browser.close();
writeFileSync(join(OUT, 'data/set-panel.json'), JSON.stringify(res, null, 1));
