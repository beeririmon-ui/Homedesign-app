/**
 * qa-agent, 2026-11-07: independent spot-check of the story prototype (/test/story/) on the local preview build.
 * Local Chromium only (/opt/pw-browsers/chromium); no `playwright install`; no network beyond http://127.0.0.1:8788.
 *
 *   node qa/reports/2026-11-07-site-story-prototype-qa/tools/measure-story.mjs [out.json]
 *
 * Measures
 *   1. first load (no scroll): every response until load + 3 s quiet; bytes on the wire, and text gzipped (zlib, level 9)
 *   2. LCP / FCP on a throttled phone (latency 150 ms, 4 Mbit/s, CPU x4), 400x800 @1 and 390x844 @3, five cold runs each
 *   3. the dots: every visible .st-mark at 390x844 (phone) and 1280x800 (desktop): centre, rect; pairwise centre distance
 *      and overlap of the 46x46 targets
 *   4. contrast: text on paper from computed colours (WCAG 2.x); text on the frames (the "טיוטה / בדיקה" chip and the
 *      desktop top band) from the pixels under the text box with the text hidden: p5 and min
 *   5. axe (WCAG 2.0/2.1 A+AA, the tags of e2e/story.spec.ts) at 390 and 1280: at rest, sheet open, cart open
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const { AxeBuilder } = require('@axe-core/playwright');
const sharp = require('sharp');

const BASE = 'http://127.0.0.1:8788';
const URL_ = `${BASE}/test/story/`;
const OUT = process.argv[2] ?? '/dev/stdout';
const exe = '/opt/pw-browsers/chromium';
const args = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
const browser = await chromium.launch({ executablePath: exe, args });
const result = { run_at: new Date().toISOString(), url: URL_, browser: `Chromium headless (${browser.version()}), SwiftShader` };

const textTypes = /(html|javascript|css|json|svg|xml|text)/;
async function firstLoad(name, vp) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr, isMobile: vp.mobile, hasTouch: vp.mobile, locale: 'he-IL' });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  const reqs = new Map();
  cdp.on('Network.responseReceived', (e) => reqs.set(e.requestId, { url: e.response.url, mime: e.response.mimeType, status: e.response.status }));
  cdp.on('Network.loadingFinished', (e) => {
    const r = reqs.get(e.requestId);
    if (r) r.wire = e.encodedDataLength;
  });
  const bodies = [];
  page.on('response', async (resp) => {
    try {
      const ct = resp.headers()['content-type'] ?? '';
      if (textTypes.test(ct)) bodies.push({ url: resp.url(), gz: gzipSync(await resp.body(), { level: 9 }).length, raw: (await resp.body()).length });
    } catch {}
  });
  await page.goto(URL_, { waitUntil: 'load' });
  await page.waitForTimeout(3000);
  const lcp = await page.evaluate(
    () =>
      new Promise((res) => {
        let last = null;
        new PerformanceObserver((l) => {
          for (const e of l.getEntries()) last = e;
        }).observe({ type: 'largest-contentful-paint', buffered: true });
        setTimeout(() => res(last ? { t: Math.round(last.startTime), el: last.element?.tagName ?? null, url: last.url || null } : null), 200);
      }),
  );
  const fcp = await page.evaluate(() => Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? -1));
  const rows = [...reqs.values()].filter((r) => r.url.startsWith(BASE));
  const gzOf = (u) => bodies.find((b) => b.url === u)?.gz;
  const kind = (r) =>
    /\/media\/test\/story\/[^/]+\/(m?\d+)\.(avif|webp)/.test(r.url)
      ? 'frame'
      : /\/media\/test\/story\/products\//.test(r.url)
        ? 'product_photos'
        : /font|woff/.test(r.mime + r.url)
          ? 'fonts'
          : /javascript/.test(r.mime)
            ? 'js'
            : /css/.test(r.mime)
              ? 'css'
              : /html/.test(r.mime)
                ? 'html'
                : 'other';
  const by = {};
  let wire = 0;
  let gzTotal = 0;
  for (const r of rows) {
    const k = kind(r);
    const g = textTypes.test(r.mime) ? (gzOf(r.url) ?? r.wire) : r.wire;
    by[k] ??= { n: 0, wire_kb: 0, text_gzip_kb: 0 };
    by[k].n++;
    by[k].wire_kb += (r.wire ?? 0) / 1024;
    by[k].text_gzip_kb += (g ?? 0) / 1024;
    wire += r.wire ?? 0;
    gzTotal += g ?? 0;
  }
  for (const k of Object.keys(by)) for (const f of ['wire_kb', 'text_gzip_kb']) by[k][f] = Math.round(by[k][f] * 10) / 10;
  const frames = rows.filter((r) => kind(r) === 'frame').map((r) => `${r.url.replace(BASE, '')} ${((r.wire ?? 0) / 1024).toFixed(1)} KB`);
  await ctx.close();
  return { viewport: `${vp.w}x${vp.h} @${vp.dpr}`, requests: rows.length, total_wire_kb: Math.round(wire / 102.4) / 10, total_text_gzip_kb: Math.round(gzTotal / 102.4) / 10, by, frames, fcp_ms: fcp, lcp };
}

async function throttled(vp, runs = 5) {
  const out = [];
  for (let i = 0; i < runs; i++) {
    const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: vp.dpr, isMobile: true, hasTouch: true, locale: 'he-IL' });
    const page = await ctx.newPage();
    const cdp = await ctx.newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
    await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: (4 * 1000 * 1000) / 8, uploadThroughput: (750 * 1000) / 8 });
    await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
    await page.addInitScript(() => {
      window.__qaLcp = [];
      new PerformanceObserver((l) => {
        for (const e of l.getEntries()) window.__qaLcp.push({ t: Math.round(e.startTime), el: e.element?.tagName ?? null, url: e.url || null, size: e.size });
      }).observe({ type: 'largest-contentful-paint', buffered: true });
    });
    await page.goto(URL_, { waitUntil: 'load', timeout: 60_000 });
    await page.waitForTimeout(4000);
    const r = await page.evaluate(() => ({ lcp: window.__qaLcp.at(-1) ?? null, fcp: Math.round(performance.getEntriesByName('first-contentful-paint')[0]?.startTime ?? -1) }));
    out.push(r);
    await ctx.close();
  }
  const l = out.map((r) => r.lcp?.t ?? NaN).sort((a, b) => a - b);
  const f = out.map((r) => r.fcp).sort((a, b) => a - b);
  return { viewport: `${vp.w}x${vp.h} @${vp.dpr}`, conditions: 'latency 150 ms, 4 Mbit/s down, 750 kbit/s up, CPU x4, cache off', runs: out, lcp_median_ms: l[Math.floor(l.length / 2)], lcp_max_ms: l.at(-1), fcp_median_ms: f[Math.floor(f.length / 2)] };
}

async function dots(vp) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, isMobile: vp.mobile, hasTouch: vp.mobile, locale: 'he-IL' });
  const page = await ctx.newPage();
  await page.goto(URL_, { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  const frames = {};
  for (const id of ['nordic-A', 'nordic-B', 'warm-modern-A']) {
    await page.locator(`#frame-${id} .mag-stage`).scrollIntoViewIfNeeded();
    await page.waitForTimeout(500);
    frames[id] = await page.evaluate((id) => {
      const stage = document.querySelector(`#frame-${id} .mag-stage`);
      const img = document.querySelector(`#frame-${id} .mag-pic img`);
      const frame = document.querySelector(`#frame-${id} .mag-frame`);
      const s = stage.getBoundingClientRect();
      const f = frame.getBoundingClientRect();
      const marks = [...stage.querySelectorAll('.st-mark')].map((m) => {
        const r = m.getBoundingClientRect();
        const cs = getComputedStyle(m);
        const visible = !m.hidden && cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0;
        return { item: m.dataset.item, visible, cx: r.x + r.width / 2 - s.x, cy: r.y + r.height / 2 - s.y, w: r.width, h: r.height, inside_stage: r.x >= s.x - 0.5 && r.right <= s.right + 0.5 && r.y >= s.y - 0.5 && r.bottom <= s.bottom + 0.5 };
      });
      const draft = stage.querySelector('.st-draft');
      const dr = draft.getBoundingClientRect();
      return {
        stage: { w: s.width, h: s.height },
        frame_box: { x: f.x - s.x, y: f.y - s.y, w: f.width, h: f.height },
        img_current: img.currentSrc.replace(location.origin, ''),
        draft: { text: draft.textContent, visible: dr.width > 0 && getComputedStyle(draft).display !== 'none', x: dr.x - s.x, y: dr.y - s.y, w: dr.width, h: dr.height },
        marks,
      };
    }, id);
    const vis = frames[id].marks.filter((m) => m.visible);
    const pairs = [];
    for (let i = 0; i < vis.length; i++)
      for (let j = i + 1; j < vis.length; j++) {
        const a = vis[i];
        const b = vis[j];
        const dx = Math.abs(a.cx - b.cx);
        const dy = Math.abs(a.cy - b.cy);
        pairs.push({ a: a.item, b: b.item, dist: Math.round(Math.hypot(dx, dy) * 10) / 10, squares_overlap: dx < 46 && dy < 46 });
      }
    pairs.sort((p, q) => p.dist - q.dist);
    frames[id].closest_pairs = pairs.slice(0, 4);
    frames[id].pairs_under_44 = pairs.filter((p) => p.dist < 44);
    frames[id].pairs_squares_overlap = pairs.filter((p) => p.squares_overlap);
  }
  await ctx.close();
  return { viewport: `${vp.w}x${vp.h}`, frames };
}

const lum = ([r, g, b]) => {
  const c = (v) => {
    v /= 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * c(r) + 0.7152 * c(g) + 0.0722 * c(b);
};
const ratio = (a, b) => {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
};
const rgbOf = (s) => s.match(/[\d.]+/g).slice(0, 4).map(Number);
/** a colour with alpha over the paper */
const over = (c, bg) => (c.length === 4 && c[3] < 1 ? c.slice(0, 3).map((v, i) => v * c[3] + bg[i] * (1 - c[3])) : c.slice(0, 3));

async function contrast(vp) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, isMobile: vp.mobile, hasTouch: vp.mobile, locale: 'he-IL' });
  const page = await ctx.newPage();
  await page.goto(URL_, { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  const paper = [244, 241, 236];
  // text on paper: computed colour against the nearest opaque background
  const onPaper = await page.evaluate(() => {
    const sel = ['.st-title', '.st-line', '.st-kicker', '.st-link', '.mag-credit-name', '.mag-credit-detail', '.st-no-dot', '.mag-cap', '.mag-lead', '.mag-h2', '.st-style .mag-cap', '.mag-foot .mag-cap', '.st-draft'];
    const bgOf = (el) => {
      for (let e = el; e; e = e.parentElement) {
        const b = getComputedStyle(e).backgroundColor;
        if (b && b !== 'rgba(0, 0, 0, 0)' && b !== 'transparent') return b;
      }
      return 'rgb(255, 255, 255)';
    };
    return sel.map((s) => {
      const el = [...document.querySelectorAll(s)].find((e) => e.getBoundingClientRect().width > 0);
      return el ? { sel: s, color: getComputedStyle(el).color, bg: bgOf(el), size: getComputedStyle(el).fontSize, weight: getComputedStyle(el).fontWeight } : { sel: s, missing: true };
    });
  });
  const paperRows = onPaper.map((r) => (r.missing ? r : { ...r, ratio: Math.round(ratio(over(rgbOf(r.color), paper), over(rgbOf(r.bg), paper)) * 100) / 100 }));
  // text on the frames: hide the text, screenshot the text box, p5 / min contrast of the pixels against the text colour
  const overFrames = [];
  for (const id of ['nordic-A', 'nordic-B', 'warm-modern-A']) {
    await page.locator(`#frame-${id} .mag-stage`).scrollIntoViewIfNeeded();
    await page.waitForTimeout(700);
    const targets = [`#frame-${id} .st-draft`];
    if (vp.w >= 720) targets.push('#mag-head .mag-brand', '#mag-head .mag-nav a', '#mag-head .st-cart-btn');
    for (const t of targets) {
      const el = page.locator(t).first();
      if (!(await el.isVisible())) continue;
      const color = await el.evaluate((e) => getComputedStyle(e).color);
      // the glyph boxes: the text itself, padding excluded (a Range over the text nodes)
      const box = await el.evaluate((e) => {
        const r = document.createRange();
        r.selectNodeContents(e);
        const b = r.getBoundingClientRect();
        return { x: b.x, y: b.y, w: b.width, h: b.height };
      });
      await el.evaluate((e) => (e.style.setProperty('color', 'transparent', 'important'), e.querySelectorAll('*').forEach((c) => c.style.setProperty('color', 'transparent', 'important'))));
      const shot = await page.screenshot({ clip: { x: Math.max(0, box.x), y: Math.max(0, box.y), width: Math.max(1, box.w), height: Math.max(1, box.h) } });
      await el.evaluate((e) => (e.style.removeProperty('color'), e.querySelectorAll('*').forEach((c) => c.style.removeProperty('color'))));
      const { data, info } = await sharp(shot).raw().toBuffer({ resolveWithObject: true });
      const tc = over(rgbOf(color), paper);
      const rs = [];
      for (let i = 0; i < data.length; i += info.channels) rs.push(ratio(tc, [data[i], data[i + 1], data[i + 2]]));
      rs.sort((a, b) => a - b);
      overFrames.push({ frame: id, target: t, text: color, p5: Math.round(rs[Math.floor(rs.length * 0.05)] * 100) / 100, min: Math.round(rs[0] * 100) / 100, px: rs.length });
    }
  }
  await ctx.close();
  return { viewport: `${vp.w}x${vp.h}`, on_paper: paperRows, over_frames: overFrames };
}

async function axe(vp) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, deviceScaleFactor: 1, isMobile: vp.mobile, hasTouch: vp.mobile, locale: 'he-IL' });
  const page = await ctx.newPage();
  const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];
  const run = async () => {
    const r = await new AxeBuilder({ page }).withTags(TAGS).analyze();
    return { violations: r.violations.map((v) => `${v.id} (${v.impact}) x${v.nodes.length}: ${v.nodes[0]?.target.join(' ')}`), incomplete: r.incomplete.map((v) => `${v.id} x${v.nodes.length}`), passes: r.passes.length };
  };
  await page.goto(URL_, { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  const out = { viewport: `${vp.w}x${vp.h}`, tags: TAGS };
  out.rest = await run();
  await page.evaluate(() => window.__story.openSheet('nordic-A-5'));
  await page.waitForTimeout(600);
  out.sheet_open = await run();
  const add = page.getByRole('button', { name: 'הוספה לסל' });
  if (await add.isVisible()) await add.click();
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  await page.locator('#st-cart-open').click();
  await page.waitForTimeout(600);
  out.cart_open = await run();
  // the same with the WCAG 2.2 target-size rule as information (not in the spec's tags)
  await page.keyboard.press('Escape');
  await page.waitForTimeout(400);
  const r22 = await new AxeBuilder({ page }).withTags(['wcag22aa']).analyze();
  out.wcag22aa_info = { violations: r22.violations.map((v) => `${v.id} (${v.impact}) x${v.nodes.length}`) };
  await ctx.close();
  return out;
}

const phone390 = { w: 390, h: 844, dpr: 3, mobile: true };
const phone400 = { w: 400, h: 800, dpr: 1, mobile: true };
const phone400x3 = { w: 400, h: 800, dpr: 3, mobile: true };
const desk = { w: 1280, h: 800, dpr: 1, mobile: false };

result.first_load = {
  phone_400_dpr1: await firstLoad('phone400', phone400),
  phone_400_dpr3: await firstLoad('phone400x3', phone400x3),
  phone_390_dpr3: await firstLoad('phone390', phone390),
  desk_1280_dpr1: await firstLoad('desk', desk),
};
result.throttled = { phone_400_dpr1: await throttled(phone400), phone_390_dpr3: await throttled(phone390) };
result.dots = { phone_390: await dots({ w: 390, h: 844, mobile: true }), phone_400: await dots({ w: 400, h: 800, mobile: true }), desk_1280: await dots(desk), desk_1440: await dots({ w: 1440, h: 900, mobile: false }) };
result.contrast = { phone_390: await contrast({ w: 390, h: 844, mobile: true }), desk_1280: await contrast(desk) };
result.axe = { phone_390: await axe({ w: 390, h: 844, mobile: true }), desk_1280: await axe(desk) };
await browser.close();
writeFileSync(OUT, JSON.stringify(result, null, 1));
console.log('done', OUT);
