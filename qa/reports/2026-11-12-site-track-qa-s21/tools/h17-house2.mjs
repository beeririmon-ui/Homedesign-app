/**
 * qa-agent, S21 (ה17, house.spec ת22): ONE press after hydration, then no retry: does the dialog open by itself, and
 * when? Per run: hydrated at the press (Preact's `l` on the hotspot), the focused element connected before and after
 * the press, the same element still in the page after, and the time from the press to the dialog (up to 20 s).
 *   QA_COPY=<copy>/site node h17-house2.mjs <base> <out.json> [runs]
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const [BASE, OUT, RUNS = '12'] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const out = [];
for (let run = 0; run < Number(RUNS); run++)
  for (const v of [{ width: 1280, height: 720, dpr: 1 }, { width: 390, height: 844, dpr: 3 }]) {
    const ctx = await b.newContext({ locale: 'he-IL', viewport: { width: v.width, height: v.height }, deviceScaleFactor: v.dpr, isMobile: v.dpr > 1, hasTouch: v.dpr > 1 });
    const p = await ctx.newPage();
    const t0 = Date.now();
    await p.goto(`${BASE}/rooms/living-room/?style=warm-modern`);
    await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 20000 });
    await p.evaluate(() => {
      window.__qaH = { replaced: 0 };
      const h = document.querySelector('button.hotspot');
      window.__qaH.el = h;
      new MutationObserver(() => { if (!window.__qaH.el.isConnected) window.__qaH.replaced++; }).observe(document.body, { childList: true, subtree: true });
    });
    const hyd = await p.evaluate(() => !!document.querySelector('button.hotspot')?.l);
    await p.locator('button.hotspot').first().focus();
    const before = await p.evaluate(() => ({ focused: document.activeElement === window.__qaH.el, connected: window.__qaH.el.isConnected }));
    const tp = Date.now();
    await p.keyboard.press('Enter');
    const after = await p.evaluate(() => ({ focused_same: document.activeElement === window.__qaH.el, active: document.activeElement?.className ?? document.activeElement?.tagName, connected: window.__qaH.el.isConnected }));
    const opened = await p.getByRole('dialog').first().waitFor({ state: 'visible', timeout: 20000 }).then(() => Date.now() - tp, () => null);
    const rep = await p.evaluate(() => window.__qaH.replaced);
    out.push({ view: `${v.width}@${v.dpr}`, press_at: tp - t0, hydrated: hyd, before, after, open_ms_after_one_press: opened, el_replaced: rep });
    console.log(JSON.stringify(out.at(-1)));
    await ctx.close();
  }
await b.close();
const opens = out.map((r) => r.open_ms_after_one_press).filter((x) => x !== null).sort((a, b) => a - b);
const summary = { runs: out.length, opened_after_one_press: opens.length, never: out.filter((r) => r.open_ms_after_one_press === null).length, over_5s: opens.filter((x) => x > 5000).length, median_ms: opens[Math.floor(opens.length / 2)], max_ms: opens.at(-1), lost_focus: out.filter((r) => !r.before.focused || !r.after.connected).length };
writeFileSync(OUT, JSON.stringify({ summary, runs: out }, null, 1));
console.log(JSON.stringify(summary));
