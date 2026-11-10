/**
 * qa-agent, 2026-11-10 (S10): does the warm-modern set panel show all four pieces of a set? At 1280×720, 1440×900,
 * 1920×1080, 400×800 and 390×844 @3, the wheel open on each set: every .set-item's box against the viewport and against
 * its scroll container (the nearest ancestor that scrolls), the container's scrollHeight / clientHeight and overflow-y,
 * and whether anything says there is more below (a fade, a cut line, a count).
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node set-panel-fit.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const res = [];
for (const v of [
  { w: 1280, h: 720, dpr: 1 },
  { w: 1440, h: 900, dpr: 1 },
  { w: 1920, h: 1080, dpr: 1 },
  { w: 400, h: 800, dpr: 1, m: true },
  { w: 390, h: 844, dpr: 3, m: true },
]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, deviceScaleFactor: v.dpr, isMobile: !!v.m, hasTouch: !!v.m });
  const p = await ctx.newPage();
  await p.goto(`${BASE}/rooms/living-room/?style=warm-modern`, { waitUntil: 'load' });
  await p.locator('button.hotspot[data-slot="cushions"]').waitFor({ state: 'attached', timeout: 20000 });
  await p.locator('button.hotspot[data-slot="cushions"]').focus();
  await p.keyboard.press('Enter');
  const dialog = p.getByRole('dialog');
  await dialog.waitFor({ timeout: 20000 });
  await p.waitForTimeout(1200);
  const sets = [];
  for (let i = 0; i < 3; i++) {
    if (i) { await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(900); }
    sets.push(
      await p.evaluate(() => {
        const items = [...document.querySelectorAll('[role="dialog"] .set-item')];
        const scroller = (el) => { for (let e = el.parentElement; e; e = e.parentElement) { const s = getComputedStyle(e); if (/(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 1) return e; } return null; };
        const sc = items.length ? scroller(items[0]) : null;
        const cb = sc?.getBoundingClientRect();
        const vh = window.innerHeight;
        return {
          label: document.querySelector('[role="dialog"] [role="radio"][aria-checked="true"]')?.getAttribute('aria-label'),
          scroller: sc ? { cls: sc.className, scrollHeight: sc.scrollHeight, clientHeight: sc.clientHeight, overflowY: getComputedStyle(sc).overflowY, mask: getComputedStyle(sc).maskImage || getComputedStyle(sc).webkitMaskImage } : null,
          items: items.map((li) => {
            const b = li.getBoundingClientRect();
            const inView = b.top >= 0 && b.bottom <= vh;
            const inScroller = !cb || (b.top >= cb.top - 0.5 && b.bottom <= cb.bottom + 0.5);
            const partly = cb ? b.top < cb.bottom && b.bottom > cb.bottom : false;
            return { name: li.querySelector('.set-name')?.textContent.trim().slice(0, 30), top: Math.round(b.top), bottom: Math.round(b.bottom), fully_visible: inView && inScroller, cut_at_scroller_edge: partly };
          }),
        };
      }),
    );
  }
  await p.screenshot({ path: join(OUT, 'overlays', `set-panel-fit-${v.w}x${v.h}.png`) });
  res.push({ viewport: `${v.w}x${v.h}@${v.dpr}`, sets });
  await ctx.close();
}
await browser.close();
writeFileSync(join(OUT, 'data/set-panel-fit.json'), JSON.stringify(res, null, 1));
console.log(JSON.stringify(res.map((r) => ({ vp: r.viewport, sets: r.sets.map((s) => ({ label: s.label?.slice(0, 8), scroller: s.scroller && `${s.scroller.scrollHeight}/${s.scroller.clientHeight} ${s.scroller.overflowY}`, visible: s.items.map((x) => (x.fully_visible ? '✓' : x.cut_at_scroller_edge ? 'cut' : '✗')).join('') })) })), null, 1));
