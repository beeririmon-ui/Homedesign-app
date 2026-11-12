/**
 * qa-agent, S21 (2026-11-12), ה17 and the house.spec fix: do the retries hide a real failure? A press is retried only
 * while it lands before hydration; a press AFTER hydration must work the first time. For each run (fresh context):
 *   house  the warm-modern house; the hotspot focused and Enter pressed, as house.spec ת22 does, once per 5 s until the
 *          dialog opens; for each press: was the hotspot hydrated (Preact keeps its listeners on the element as `l`)?
 *   stage  the Nordic room; a press on the stage, as encoding-capture does; for each press: hydrated? did the engine start?
 * A failure hidden by the retry = a press made on a hydrated element that did nothing, followed by one that worked.
 *   QA_COPY=<copy>/site node h17-probe.mjs <base> <out.json> [runs]
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const [BASE, OUT, RUNS = '8'] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const views = [
  { width: 1280, height: 720, dpr: 1 },
  { width: 390, height: 844, dpr: 3 },
];
const out = { house: [], stage: [] };
for (let run = 0; run < Number(RUNS); run++)
  for (const v of views) {
    {
      const ctx = await b.newContext({ locale: 'he-IL', viewport: { width: v.width, height: v.height }, deviceScaleFactor: v.dpr, isMobile: v.dpr > 1, hasTouch: v.dpr > 1 });
      const p = await ctx.newPage();
      const t0 = Date.now();
      await p.goto(`${BASE}/rooms/living-room/?style=warm-modern`);
      await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 20000 });
      const presses = [];
      let open = false;
      for (let i = 0; i < 8 && !open; i++) {
        const hyd = await p.evaluate(() => !!document.querySelector('button.hotspot')?.l);
        await p.locator('button.hotspot').first().focus();
        await p.keyboard.press('Enter');
        const at = Date.now() - t0;
        open = await p.getByRole('dialog').first().waitFor({ state: 'visible', timeout: 5000 }).then(() => true, () => false);
        presses.push({ at, hydrated: hyd, opened: open });
      }
      out.house.push({ view: `${v.width}@${v.dpr}`, presses, hidden_failure: presses.some((x, i) => x.hydrated && !x.opened && presses.slice(i + 1).some((y) => y.opened)) });
      await ctx.close();
    }
    {
      const ctx = await b.newContext({ locale: 'he-IL', viewport: { width: v.width, height: v.height }, deviceScaleFactor: v.dpr });
      const p = await ctx.newPage();
      const t0 = Date.now();
      await p.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
      await p.locator('section.stage').waitFor({ timeout: 20000 });
      await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 20000 });
      const sb = await p.locator('section.stage').boundingBox();
      const presses = [];
      let started = false;
      for (let i = 0; i < 8 && !started; i++) {
        const hyd = await p.evaluate(() => !!document.querySelector('button.hotspot')?.l);
        await p.mouse.click(sb.x + 20, sb.y + sb.height / 2);
        const at = Date.now() - t0;
        let ok = false;
        for (let k = 0; k < 20 && !ok; k++) {
          ok = await p.evaluate(() => !!window.__hdEngine);
          if (!ok) await sleep(100);
        }
        started = ok;
        presses.push({ at, hydrated: hyd, engine: ok });
      }
      out.stage.push({ view: `${v.width}@${v.dpr}`, presses, hidden_failure: presses.some((x, i) => x.hydrated && !x.engine && presses.slice(i + 1).some((y) => y.engine)) });
      await ctx.close();
    }
    console.log(`run ${run} ${v.width}: house ${JSON.stringify(out.house.at(-1).presses)} | stage ${JSON.stringify(out.stage.at(-1).presses)}`);
  }
await b.close();
const sum = (rows) => ({
  runs: rows.length,
  first_press_worked: rows.filter((r) => r.presses[0]?.opened || r.presses[0]?.engine).length,
  retried: rows.filter((r) => r.presses.length > 1).length,
  retried_with_first_press_before_hydration: rows.filter((r) => r.presses.length > 1 && !r.presses[0].hydrated).length,
  hydrated_press_that_did_nothing: rows.flatMap((r) => r.presses).filter((x) => x.hydrated && !(x.opened || x.engine)).length,
  hidden_failures: rows.filter((r) => r.hidden_failure).length,
  never_worked: rows.filter((r) => !r.presses.some((x) => x.opened || x.engine)).length,
});
out.summary = { house: sum(out.house), stage: sum(out.stage) };
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out.summary));
