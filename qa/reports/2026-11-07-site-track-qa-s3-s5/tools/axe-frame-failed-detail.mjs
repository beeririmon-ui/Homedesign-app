/** qa-agent, 2026-11-07 (S3-S5): axe's color-contrast nodes on boho, frame A failed vs loaded, at 1280 and 400. */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const AXE = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const out = {};
for (const [label, fail, w, style] of [['boho-failed-1280', true, 1280, 'boho'], ['boho-loaded-1280', false, 1280, 'boho'], ['boho-failed-400', true, 400, 'boho'], ['nordic-B-failed-1280', true, 1280, 'nordic']]) {
  const ctx = await browser.newContext({ locale: 'he-IL', bypassCSP: true, viewport: { width: w, height: w > 500 ? 900 : 860 } });
  const p = await ctx.newPage();
  const fr = style === 'nordic' ? 'B' : 'A';
  if (fail) await p.route(new RegExp(`/media/story/living-room/${style}/${fr}/(m?\\d+)\\.(avif|webp)`), (r) => r.abort('failed'));
  await p.goto(`${BASE}/story/living-room/${style}/`, { waitUntil: 'load' });
  await p.locator(`#frame-${fr}`).scrollIntoViewIfNeeded();
  await p.waitForTimeout(2000);
  await p.addScriptTag({ content: AXE });
  out[label] = await p.evaluate(async () => {
    const r = await window.axe.run(document, { runOnly: ['color-contrast'] });
    return {
      violations: r.violations.flatMap((v) => v.nodes.map((n) => ({ target: n.target.join(' '), summary: n.failureSummary.split('\n').slice(1, 2).join(' '), html: n.html.slice(0, 120) }))),
      incomplete: r.incomplete.reduce((n, v) => n + v.nodes.length, 0),
    };
  });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
console.log(JSON.stringify(out, null, 1));
