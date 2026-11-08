/** qa-agent, 2026-11-07 (S3-S5): the tool draft's mark, the multiply layer, and what the first load fetches (bytes). */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const res = [];
for (const w of [1280, 400]) {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: w > 500 ? 900 : 860 } });
  const p = await ctx.newPage();
  const cdp = await ctx.newCDPSession(p);
  await cdp.send('Network.enable');
  const bytes = new Map();
  cdp.on('Network.responseReceived', (e) => bytes.set(e.requestId, { url: e.response.url.replace(BASE, ''), n: 0 }));
  cdp.on('Network.loadingFinished', (e) => { const b = bytes.get(e.requestId); if (b) b.n = e.encodedDataLength; });
  await p.goto(`${BASE}/story/living-room/warm-modern/tool/`, { waitUntil: 'load' });
  await p.waitForTimeout(1500);
  const r = await p.evaluate(() => {
    const m = document.querySelector('.st-draft');
    const st = document.getElementById('td-stage').getBoundingClientRect();
    const b = m.getBoundingClientRect();
    return {
      text: m.textContent.trim(),
      box: [b.left, b.top, b.width, b.height].map(Math.round),
      stage: [st.left, st.top, st.width, st.height].map(Math.round),
      corner: { from_top_of_stage: Math.round(b.top - st.top), from_left: Math.round(b.left - st.left), from_right: Math.round(st.right - b.right) },
      visible: getComputedStyle(m).opacity,
      blend: [...document.querySelectorAll('.st-td-layer')].map((x) => `${x.className}:${getComputedStyle(x).mixBlendMode}`),
    };
  });
  const list = [...bytes.values()];
  res.push({ width: w, ...r, first_load_kb: Math.round(list.reduce((n, x) => n + x.n, 0) / 102.4) / 10, nordic_layer_kb: Math.round(list.filter((x) => x.url.includes('/tool/living-room/nordic/')).reduce((n, x) => n + x.n, 0) / 102.4) / 10, files: list.map((x) => `${x.url} ${x.n}`) });
  await p.screenshot({ path: `/home/user/homedesign-app/qa/reports/2026-11-07-site-track-qa-s3-s5/overlays/tool-draft-mark-${w}.png` });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
for (const r of res) console.log(JSON.stringify({ ...r, files: undefined }));
