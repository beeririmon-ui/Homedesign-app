/**
 * qa-agent, 2026-11-07 (S3-S5): the story budgets in the browser (QA's snapshot, wrangler dev, gzip on). A phone (412 ×
 * 915, DPR 2) and a desktop (1280 × 900, DPR 1); a cold context per page; bytes on the wire (CDP encodedDataLength) until
 * load + 2.5 s without scrolling, split by type; FCP and LCP; JS and CSS on the wire.
 *   QA_BASE=http://127.0.0.1:8799 node measure-story-budgets.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const pages = [
  '/story/',
  '/story/living-room/nordic/',
  '/story/living-room/modern-country/',
  '/story/living-room/boho/',
  '/story/living-room/mediterranean/',
  '/story/living-room/japandi/',
  '/story/living-room/nordic/p/cushions-boucle-teddy-d7wrb/',
  '/story/living-room/boho/p/cushions-washed-cotton-frayed-ws8a6/',
  '/story/checkout/',
  '/story/living-room/warm-modern/tool/',
];
const res = [];
for (const [dev, vp, dpr] of [['phone', { width: 412, height: 915 }, 2], ['desktop', { width: 1280, height: 900 }, 1]]) {
  for (const u of pages) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: vp, deviceScaleFactor: dpr, isMobile: dev === 'phone', hasTouch: dev === 'phone' });
    const p = await ctx.newPage();
    const cdp = await ctx.newCDPSession(p);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    const reqs = new Map();
    cdp.on('Network.responseReceived', (e) => reqs.set(e.requestId, { url: e.response.url.replace(BASE, ''), type: e.type, n: 0 }));
    cdp.on('Network.loadingFinished', (e) => { const r = reqs.get(e.requestId); if (r) r.n = e.encodedDataLength; });
    await p.addInitScript(() => {
      window.__lcp = 0;
      new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__lcp = e.startTime; }).observe({ type: 'largest-contentful-paint', buffered: true });
    });
    await p.goto(BASE + u, { waitUntil: 'load' });
    await p.waitForTimeout(2500);
    const t = await p.evaluate(() => ({ fcp: Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? 0), lcp: Math.round(window.__lcp) }));
    const list = [...reqs.values()];
    const kb = (f) => Math.round(list.filter(f).reduce((n, r) => n + r.n, 0) / 102.4) / 10;
    res.push({
      device: dev,
      page: u,
      total_kb: kb(() => true),
      js_kb: kb((r) => r.type === 'Script'),
      css_kb: kb((r) => r.type === 'Stylesheet'),
      font_kb: kb((r) => r.type === 'Font'),
      img_kb: kb((r) => r.type === 'Image'),
      html_kb: kb((r) => r.type === 'Document'),
      requests: list.length,
      ...t,
      biggest: list.sort((a, b) => b.n - a.n).slice(0, 3).map((r) => `${r.url.slice(0, 70)} ${Math.round(r.n / 1024)}KB`),
    });
    await ctx.close();
  }
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
for (const r of res) console.log(r.device.padEnd(8), r.page.padEnd(62), String(r.total_kb).padStart(7), 'KB  js', r.js_kb, 'css', r.css_kb, 'img', r.img_kb, 'font', r.font_kb, '| FCP', r.fcp, 'LCP', r.lcp);
