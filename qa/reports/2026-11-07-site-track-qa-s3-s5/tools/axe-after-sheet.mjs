/** qa-agent, 2026-11-07 (S3-S5): boho A failed at 1280: open the sheet from the list, Escape, then axe at once and after 1 s. */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const AXE = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const out = {};
for (const fail of [true, false]) {
  const ctx = await browser.newContext({ locale: 'he-IL', bypassCSP: true, viewport: { width: 1280, height: 900 } });
  const p = await ctx.newPage();
  if (fail) await p.route(/\/media\/story\/living-room\/boho\/A\/(m?\d+)\.(avif|webp)/, (r) => r.abort('failed'));
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.locator('#frame-A').scrollIntoViewIfNeeded();
  await p.waitForTimeout(1500);
  await p.locator('.st-credit .st-open').first().click();
  await p.waitForTimeout(500);
  await p.keyboard.press('Escape');
  await p.addScriptTag({ content: AXE });
  const run = () => p.evaluate(async () => (await window.axe.run(document, { runOnly: ['color-contrast'] })).violations.flatMap((v) => v.nodes.map((n) => `${n.target.join(' ')} | ${n.failureSummary.split('\n')[1]?.trim()}`)));
  const now = await run();
  await p.waitForTimeout(1200);
  out[fail ? 'failed' : 'loaded'] = { at_once: now, after_1200ms: await run() };
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
