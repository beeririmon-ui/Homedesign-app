/**
 * qa-agent, 2026-11-07 (interface track S1/S2): spot-check of the weights, LCP and axe on the story routes, and the
 * link from a dot to its detail page when one house shows two options of the same card. Local preview, local Chromium.
 *
 *   node qa/reports/2026-11-07-site-track-qa-s1-s2/tools/measure-story-s12.mjs out.json
 *
 * Weights: response bodies until load + 3 s with no scrolling, text gzipped (zlib level 9), media and fonts as they are
 * (the way frontend-dev counts). LCP: latency 150 ms, 4 Mbit/s, CPU x4, cache off, five cold runs. axe: the tags of
 * e2e/story.spec.ts (WCAG 2.0/2.1 A + AA), and WCAG 2.2 AA as information.
 */
import { createRequire } from 'node:module';
import { statSync, writeFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const { AxeBuilder } = require('@axe-core/playwright');
const OUT = process.argv[2] ?? '/dev/stdout';
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8788';
const DIST = '/home/user/homedesign-app/site/web/dist';
const stamp = () => ({ story_index: statSync(`${DIST}/story/index.html`).mtime.toISOString(), detail: statSync(`${DIST}/story/living-room/warm-modern/p/cushions-cj-boucle-teddy/index.html`).mtime.toISOString() });
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = { run_at: new Date().toISOString(), dist_before: stamp(), browser: browser.version() };
const ctxOf = (vp) => browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr ?? 1, isMobile: !!vp.mobile, hasTouch: !!vp.mobile, locale: 'he-IL' });

async function weight(path, vp) {
  const ctx = await ctxOf(vp);
  const page = await ctx.newPage();
  const rows = [];
  page.on('response', async (r) => {
    try {
      const b = await r.body();
      const ct = r.headers()['content-type'] ?? '';
      rows.push({ url: r.url().replace(BASE, ''), body: b.length, counted: /(html|javascript|css|json|svg|xml|text)/.test(ct) ? gzipSync(b, { level: 9 }).length : b.length, type: ct.split(';')[0] });
    } catch {}
  });
  await page.goto(BASE + path, { waitUntil: 'load' });
  await page.waitForTimeout(3000);
  await ctx.close();
  const kind = (u, t) => (/\/media\/story\/living-room\/[^/]+\/[AB]\//.test(u) ? 'frames' : /\/media\/story\/products\/|\/crops?\//.test(u) ? 'product_images' : /woff/.test(u + t) ? 'fonts' : /javascript/.test(t) ? 'js' : /css/.test(t) ? 'css' : /html/.test(t) ? 'html' : 'other');
  const by = {};
  for (const r of rows) {
    const k = kind(r.url, r.type);
    by[k] = Math.round(((by[k] ?? 0) + r.counted / 1024) * 10) / 10;
  }
  return { path, viewport: `${vp.w}x${vp.h} @${vp.dpr ?? 1}`, total_kb: Math.round(rows.reduce((s, r) => s + r.counted, 0) / 102.4) / 10, requests: rows.length, by };
}
async function lcp(path, vp, runs = 5) {
  const out = [];
  for (let i = 0; i < runs; i++) {
    const ctx = await ctxOf({ ...vp, mobile: true });
    const page = await ctx.newPage();
    const cdp = await ctx.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: 500000, uploadThroughput: 93750 });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
    await page.addInitScript(() => {
      window.__qaLcp = [];
      new PerformanceObserver((l) => l.getEntries().forEach((e) => window.__qaLcp.push({ t: Math.round(e.startTime), el: e.element?.tagName ?? null }))).observe({ type: 'largest-contentful-paint', buffered: true });
    });
    await page.goto(BASE + path, { waitUntil: 'load', timeout: 60000 });
    await page.waitForTimeout(4000);
    out.push(await page.evaluate(() => window.__qaLcp.at(-1) ?? null));
    await ctx.close();
  }
  const t = out.map((x) => x?.t ?? NaN).sort((a, b) => a - b);
  return { path, viewport: `${vp.w}x${vp.h} @${vp.dpr ?? 1}`, runs: out, median_ms: t[Math.floor(t.length / 2)], max_ms: t.at(-1) };
}
async function axe(path, vp, setup) {
  const ctx = await ctxOf(vp);
  const page = await ctx.newPage();
  await page.goto(BASE + path, { waitUntil: 'load' });
  await page.waitForTimeout(2200);
  if (setup) await setup(page);
  const r = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']).analyze();
  const r22 = await new AxeBuilder({ page }).withTags(['wcag22aa']).analyze();
  const scroll = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  await ctx.close();
  return { path, viewport: `${vp.w}x${vp.h}`, state: setup ? 'sheet open' : 'rest', violations: r.violations.map((v) => `${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0]?.target.join(' ')}`), wcag22aa: r22.violations.map((v) => `${v.id} x${v.nodes.length}`), sideways_scroll_px: scroll };
}

const P400 = { w: 400, h: 800, mobile: true };
const NORDIC = '/story/living-room/nordic/';
const DETAIL = '/story/living-room/warm-modern/p/cushions-cj-boucle-teddy/';
res.weights = [
  await weight(NORDIC, P400),
  await weight(NORDIC, { ...P400, dpr: 3 }),
  await weight(NORDIC, { w: 1280, h: 800 }),
  await weight('/story/', P400),
  await weight('/story/', { w: 1280, h: 800 }),
  await weight('/story/living-room/boho/', P400),
  await weight(DETAIL, P400),
  await weight(DETAIL, { w: 1280, h: 800 }),
];
res.lcp = [await lcp(NORDIC, P400), await lcp(DETAIL, P400)];
const pages = [
  '/story/',
  ...['nordic', 'warm-modern', 'modern-country', 'boho', 'mediterranean', 'japandi'].map((s) => `/story/living-room/${s}/`),
  '/story/living-room/nordic/p/cushions-cj-linen-look-charcoal/',
  DETAIL,
  '/story/living-room/nordic/p/pendant-cj-silk-ribbed-pumpkin-40/',
  '/story/living-room/nordic/p/rug-cj-braided-wool-natural/',
  '/story/living-room/modern-country/p/curtains-aliexpress-linen-blend-s-fold-180502/',
];
res.axe = [];
for (const vp of [{ w: 390, h: 844, mobile: true }, { w: 1280, h: 800 }]) {
  for (const p of pages) res.axe.push(await axe(p, vp));
  res.axe.push(await axe(NORDIC, vp, async (page) => (await page.evaluate(() => window.__story.openSheet('A-5')), await page.waitForTimeout(600))));
}
// the two boucle cushions of the warm-modern house: where "לדף המוצר" and the list row lead, and what that page opens on
{
  const ctx = await ctxOf({ w: 1280, h: 800 });
  const page = await ctx.newPage();
  await page.goto(BASE + '/story/living-room/warm-modern/', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  const items = await page.evaluate(() => {
    const d = JSON.parse(document.getElementById('st-data').textContent);
    return Object.values(d.items).filter((x) => x.product === 'cushions-cj-boucle-teddy').map((x) => ({ id: x.id, name_he: x.name_he, values: x.values, href: x.href }));
  });
  res.two_options_one_house = [];
  for (const it of items) {
    await page.evaluate((id) => window.__story.openSheet(id), it.id);
    await page.waitForTimeout(500);
    const link = await page.locator('#st-page').getAttribute('href');
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    const p2 = await ctx.newPage();
    await p2.goto(BASE + link, { waitUntil: 'load' });
    await p2.waitForFunction(() => !!window.__story?.detail?.(), undefined, { timeout: 15000 });
    const opened = await p2.evaluate(() => ({ key: window.__story.detail().current().key, title: document.querySelector('h1')?.textContent?.trim() }));
    await p2.close();
    res.two_options_one_house.push({ ...it, sheet_link: link, detail_opens_on: opened.key, detail_title: opened.title, matches_the_dot: opened.key === Object.values(it.values).join('+') || opened.key.includes(it.values.color) });
  }
  await ctx.close();
}
await browser.close();
res.dist_after = stamp();
res.dist_changed_during_run = JSON.stringify(res.dist_before) !== JSON.stringify(res.dist_after);
writeFileSync(OUT, JSON.stringify(res, null, 1));
console.log(JSON.stringify({ dist: [res.dist_before, res.dist_after, res.dist_changed_during_run], weights: res.weights.map((w) => [w.path, w.viewport, w.total_kb]), lcp: res.lcp.map((l) => [l.path, l.median_ms, l.max_ms]), axe_violations: res.axe.filter((a) => a.violations.length || a.wcag22aa.length || a.sideways_scroll_px > 0), two: res.two_options_one_house }, null, 1));
