/**
 * qa-agent, 2026-11-07: the first-load weight of /test/story/ counted the way frontend-dev counts it (README §"משקל
 * הטעינה הראשונה"): response bodies, text gzipped, media and fonts as they are; no headers. Counted next to the bytes on
 * the wire (measure-story.mjs) so the two can be compared. Local preview only.
 *
 *   node qa/reports/2026-11-07-site-story-prototype-qa/tools/measure-weight-bodies.mjs [out.json]
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const OUT = process.argv[2] ?? '/dev/stdout';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = {};
for (const vp of [
  { name: 'phone_400_dpr1', w: 400, h: 800, dpr: 1, mobile: true },
  { name: 'phone_400_dpr3', w: 400, h: 800, dpr: 3, mobile: true },
  { name: 'phone_390_dpr3', w: 390, h: 844, dpr: 3, mobile: true },
  { name: 'desk_1280_dpr1', w: 1280, h: 800, dpr: 1, mobile: false },
]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr, isMobile: vp.mobile, hasTouch: vp.mobile, locale: 'he-IL' });
  const page = await ctx.newPage();
  const rows = [];
  page.on('response', async (r) => {
    try {
      const b = await r.body();
      const ct = r.headers()['content-type'] ?? '';
      const text = /(html|javascript|css|json|svg|xml|text)/.test(ct);
      rows.push({ url: r.url().replace('http://127.0.0.1:8788', ''), type: ct.split(';')[0], body: b.length, counted: text ? gzipSync(b, { level: 9 }).length : b.length });
    } catch {}
  });
  await page.goto('http://127.0.0.1:8788/test/story/', { waitUntil: 'load' });
  await page.waitForTimeout(3000);
  const kind = (u, t) =>
    /\/media\/test\/story\/[^/]+\/m?\d+\.(avif|webp)$/.test(u) ? 'frame' : /\/media\/test\/story\/products\//.test(u) ? 'product_photos' : /woff/.test(u + t) ? 'fonts' : /javascript/.test(t) ? 'js' : /css/.test(t) ? 'css' : /html/.test(t) ? 'html' : 'other';
  const by = {};
  for (const r of rows) {
    const k = kind(r.url, r.type);
    by[k] ??= { n: 0, kb: 0 };
    by[k].n++;
    by[k].kb += r.counted / 1024;
  }
  for (const k in by) by[k].kb = Math.round(by[k].kb * 10) / 10;
  res[vp.name] = { total_kb: Math.round(rows.reduce((s, r) => s + r.counted, 0) / 102.4) / 10, requests: rows.length, by, rows };
  await ctx.close();
}
await browser.close();
writeFileSync(OUT, JSON.stringify(res, null, 1));
for (const [k, v] of Object.entries(res)) console.log(k, v.total_kb, 'KB', v.requests, 'requests', JSON.stringify(v.by));
