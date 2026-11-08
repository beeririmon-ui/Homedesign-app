/** qa-agent, 2026-11-07 (S3-S5): in the failed-frame state, does the message cover the draft mark (".st-draft")? */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const out = [];
for (const [w, h] of [[360, 740], [390, 844], [400, 860], [720, 900], [1280, 900]]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h } });
  const p = await ctx.newPage();
  await p.route(/\/media\/story\/living-room\/boho\/A\/(m?\d+)\.(avif|webp)/, (r) => r.abort('failed'));
  await p.goto(`${BASE}/story/living-room/boho/`, { waitUntil: 'load' });
  await p.waitForTimeout(1500);
  out.push({ viewport: `${w}x${h}`, ...(await p.evaluate(() => {
    const st = document.querySelector('#frame-A .mag-stage');
    const m = st.querySelector('.st-img-error')?.getBoundingClientRect();
    const d = st.querySelector('.st-draft') ?? document.querySelector('#frame-A .st-draft');
    const b = d?.getBoundingClientRect();
    const r = (x) => x && [x.left, x.top, x.right, x.bottom].map(Math.round);
    const overlap = m && b ? Math.max(0, Math.min(m.right, b.right) - Math.max(m.left, b.left)) * Math.max(0, Math.min(m.bottom, b.bottom) - Math.max(m.top, b.top)) : 0;
    return { message: r(m), draft: r(b), overlap_px2: Math.round(overlap), draft_area_px2: b ? Math.round(b.width * b.height) : null };
  })) });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
for (const o of out) console.log(JSON.stringify(o));
