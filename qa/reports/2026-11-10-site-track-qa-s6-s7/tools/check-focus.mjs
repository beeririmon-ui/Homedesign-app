/**
 * qa-agent, 2026-11-10 (S6-S7; from the S3-S5 tool): G5.16, stricter than system.spec: at each Tab stop, does the focused element look
 * different from itself unfocused (outline, box-shadow, border, background, text decoration)? system.spec counts any
 * 2 px border, or any box-shadow, as a ring even when it is there without focus.
 *   QA_BASE=http://127.0.0.1:8799 node check-focus.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const res = [];
const pages = ['/story/', '/story/living-room/nordic/', '/story/living-room/boho/', '/story/living-room/nordic/p/cushions-boucle-teddy-d7wrb/', '/story/checkout/', '/story/living-room/warm-modern/tool/', '/rooms/living-room/?from=%2Fstory%2Fliving-room%2Fnordic%2F'];
for (const w of [1280, 400]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: w > 500 ? 900 : 860 } });
  const p = await ctx.newPage();
  for (const u of pages) {
    await p.goto(BASE + u, { waitUntil: 'load' });
    await p.waitForTimeout(700);
    await p.locator('body').click({ position: { x: 1, y: 1 } }).catch(() => {});
    const bad = [];
    let stops = 0;
    for (let i = 0; i < 40; i++) {
      await p.keyboard.press('Tab');
      const r = await p.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body) return null;
        const pick = (s) => [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderColor, s.borderWidth, s.backgroundColor, s.textDecorationLine, s.color].join('|');
        const on = pick(getComputedStyle(el));
        const at = `${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}${typeof el.className === 'string' && el.className ? '.' + el.className.trim().split(/\s+/)[0] : ''}`;
        // the same element, unfocused: a clone is not styled the same; blur and read, then focus back
        el.blur();
        const off = pick(getComputedStyle(el));
        el.focus({ preventScroll: true });
        const s = getComputedStyle(el);
        const r = el.getBoundingClientRect();
        return { at, differs: on !== off, outline: `${s.outlineStyle} ${s.outlineWidth}`, shadow: s.boxShadow !== 'none', visible: r.width > 0 && r.height > 0 };
      });
      if (!r) continue;
      stops++;
      if (!r.differs && r.visible && !bad.some((b) => b.at === r.at)) bad.push(r);
    }
    res.push({ width: w, page: u, stops, no_visible_change: bad });
  }
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
for (const r of res) console.log(r.width, r.page, 'stops', r.stops, 'no change on focus:', JSON.stringify(r.no_visible_change.map((b) => b.at)));
