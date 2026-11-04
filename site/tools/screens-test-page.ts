/**
 * Evidence for the test page in the magazine language (art direction §10, briefs/site-test-page-2026-11-03.md), on
 * web/dist (Chromium headless + SwiftShader, so every frame-time figure is a floor, not the phone's number):
 *   screens/    screenshots at 1280×800 and 400×800 (and the clean-room check at 1920×1080): the cover's timeline, the
 *               contents, the room at rest, the marks, the wall label, focus mode (approach, strip, variant, landing),
 *               the cushions close-up on the phone, the paper transition, the pan, the states, the focus rings, the grid
 *   evidence.json / evidence.md   the measured figures per check, with the thresholds of §10
 *
 *   npm run screens:test-page          (after npm run build; serves web/dist itself)
 */
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { extname, join } from 'node:path';
import { chromium, type Browser, type BrowserContext, type Page } from '@playwright/test';
import sharp from 'sharp';
import { repoPath, sitePath } from './lib/paths';

const PORT = 5199;
const ORIGIN = `http://127.0.0.1:${PORT}`;
const DIST = sitePath('web/dist');
const OUT = repoPath('qa/reports/2026-11-03-site-test-page');
const SHOTS = join(OUT, 'screens');
mkdirSync(SHOTS, { recursive: true });

// ---------- a static server for dist (avif/webp with their types; /test/ → /test/index.html) ----------
const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.avif': 'image/avif',
  '.webp': 'image/webp',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
};
const server = createServer((req, res) => {
  let p = decodeURIComponent((req.url ?? '/').split('?')[0]!);
  if (p.endsWith('/')) p += 'index.html';
  const file = join(DIST, p);
  if (!file.startsWith(DIST) || !existsSync(file) || statSync(file).isDirectory()) {
    res.writeHead(404);
    res.end();
    return;
  }
  res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream', 'content-length': statSync(file).size, 'cache-control': 'no-store' });
  createReadStream(file).pipe(res);
});
await new Promise<void>((r) => server.listen(PORT, '127.0.0.1', r));

// ---------- page-side helpers as a string: tsx would inject a __name helper into a closure the page lacks ----------
const HELPERS = `
window.__ev = {
  lcp: [], paint: {},
  sample(sel, prop, ms) { return new Promise((res) => { const el = document.querySelector(sel); const out = []; const t0 = performance.now();
    const f = () => { const t = performance.now(); out.push([t, getComputedStyle(el)[prop]]); if (t - t0 < ms) requestAnimationFrame(f); else res(out); }; requestAnimationFrame(f); }); },
  frames(ms) { return new Promise((res) => { const out = []; let last = performance.now(); const t0 = last;
    const f = () => { const t = performance.now(); out.push(t - last); last = t; if (t - t0 < ms) requestAnimationFrame(f); else res(out.slice(1)); }; requestAnimationFrame(f); }); },
  firstChange(sel, prop, timeout) { return new Promise((res) => { const el = document.querySelector(sel); const v0 = getComputedStyle(el)[prop]; const t0 = performance.now();
    const f = () => { const t = performance.now(); if (getComputedStyle(el)[prop] !== v0) res(t - t0); else if (t - t0 > timeout) res(null); else requestAnimationFrame(f); }; requestAnimationFrame(f); }); },
  rect(sel) { const r = document.querySelector(sel).getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; },
  rects(sel) { return [...document.querySelectorAll(sel)].map((el) => { const r = el.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height, slot: el.dataset.slot, box: el.dataset.box, text: (el.textContent || '').trim().slice(0, 40), aria: el.getAttribute('aria-label') }; }); },
  css(sel, props) { const el = document.querySelector(sel); const cs = getComputedStyle(el); const o = {}; for (const p of props) o[p] = cs.getPropertyValue(p) || cs[p]; return o; },
  token(name) { return getComputedStyle(document.body).getPropertyValue(name).trim(); },
  now() { return performance.now(); },
};
try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__ev.lcp.push({ t: e.startTime, size: e.size, el: e.element ? (e.element.className || e.element.tagName) : '' }); }).observe({ type: 'largest-contentful-paint', buffered: true }); } catch {}
try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__ev.paint[e.name] = e.startTime; }).observe({ type: 'paint', buffered: true }); } catch {}
`;

const browser: Browser = await chromium.launch({
  executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--font-render-hinting=none'],
});
const evidence: Record<string, unknown> = {};
const notes: string[] = [];
const problems: string[] = [];
type Shot = { name: string; caption: string };
const shots: Shot[] = [];

async function ctxOf(w: number, h: number, reduced = false): Promise<BrowserContext> {
  const ctx = await browser.newContext({
    viewport: { width: w, height: h },
    deviceScaleFactor: 1,
    locale: 'he-IL',
    reducedMotion: reduced ? 'reduce' : 'no-preference',
    isMobile: w < 720,
    hasTouch: w < 720,
  });
  await ctx.addInitScript(HELPERS);
  return ctx;
}
async function open(ctx: BrowserContext, hash = ''): Promise<Page> {
  const page = await ctx.newPage();
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') problems.push(`console: ${m.text()}`);
  });
  await page.goto(`${ORIGIN}/test/${hash}`, { waitUntil: 'load' });
  return page;
}
async function shot(page: Page, name: string, caption: string, clip?: { x: number; y: number; width: number; height: number }): Promise<Buffer> {
  const png = await page.screenshot(clip ? { clip } : {});
  writeFileSync(join(SHOTS, `${name}.png`), png);
  shots.push({ name, caption });
  return png;
}
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
type Ev = { t: number; name: string; detail?: unknown };
const events = async (page: Page): Promise<Ev[]> => (await page.evaluate('window.__mag.events')) as Ev[];
const at = (evs: Ev[], name: string): number | null => evs.find((e) => e.name === name)?.t ?? null;
const atLast = (evs: Ev[], name: string): number | null => [...evs].reverse().find((e) => e.name === name)?.t ?? null;
const goTo = (page: Page, sel: string) => page.evaluate(`document.querySelector('${sel}').scrollIntoView({ behavior: 'instant', block: 'start' })`);
const pct = (xs: number[], p: number): number => {
  const s = [...xs].sort((a, b) => a - b);
  return s[Math.min(s.length - 1, Math.floor((p / 100) * s.length))] ?? 0;
};
const r1 = (x: number) => Math.round(x * 10) / 10;

// ---------- colour maths: sRGB → Lab, ΔE00, WCAG contrast ----------
function lab(r: number, g: number, b: number): [number, number, number] {
  const lin = (c: number) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  const R = lin(r);
  const G = lin(g);
  const B = lin(b);
  const X = (R * 0.4124 + G * 0.3576 + B * 0.1805) / 0.95047;
  const Y = R * 0.2126 + G * 0.7152 + B * 0.0722;
  const Z = (R * 0.0193 + G * 0.1192 + B * 0.9505) / 1.08883;
  const f = (t: number) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  return [116 * f(Y) - 16, 500 * (f(X) - f(Y)), 200 * (f(Y) - f(Z))];
}
function dE00(l1: [number, number, number], l2: [number, number, number]): number {
  const [L1, a1, b1] = l1;
  const [L2, a2, b2] = l2;
  const rad = Math.PI / 180;
  const C1 = Math.hypot(a1, b1);
  const C2 = Math.hypot(a2, b2);
  const Cm = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)));
  const a1p = a1 * (1 + G);
  const a2p = a2 * (1 + G);
  const C1p = Math.hypot(a1p, b1);
  const C2p = Math.hypot(a2p, b2);
  const h = (a: number, b: number) => {
    if (a === 0 && b === 0) return 0;
    const d = Math.atan2(b, a) / rad;
    return d < 0 ? d + 360 : d;
  };
  const h1p = h(a1p, b1);
  const h2p = h(a2p, b2);
  const dLp = L2 - L1;
  const dCp = C2p - C1p;
  let dhp = 0;
  if (C1p * C2p !== 0) {
    dhp = h2p - h1p;
    if (dhp > 180) dhp -= 360;
    else if (dhp < -180) dhp += 360;
  }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp / 2) * rad);
  const Lm = (L1 + L2) / 2;
  const Cmp = (C1p + C2p) / 2;
  let hm = h1p + h2p;
  if (C1p * C2p !== 0) {
    if (Math.abs(h1p - h2p) > 180) hm += hm < 360 ? 360 : -360;
    hm /= 2;
  }
  const T = 1 - 0.17 * Math.cos((hm - 30) * rad) + 0.24 * Math.cos(2 * hm * rad) + 0.32 * Math.cos((3 * hm + 6) * rad) - 0.2 * Math.cos((4 * hm - 63) * rad);
  const dTheta = 30 * Math.exp(-(((hm - 275) / 25) ** 2));
  const RC = 2 * Math.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7));
  const SL = 1 + (0.015 * (Lm - 50) ** 2) / Math.sqrt(20 + (Lm - 50) ** 2);
  const SC = 1 + 0.045 * Cmp;
  const SH = 1 + 0.015 * Cmp * T;
  const RT = -Math.sin(2 * dTheta * rad) * RC;
  return Math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH));
}
const lum = (r: number, g: number, b: number): number => {
  const lin = (c: number) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
};
const contrast = (l1: number, l2: number): number => (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
function parseRgb(s: string): [number, number, number, number] {
  const m = s.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
  return m ? [Number(m[1]), Number(m[2]), Number(m[3]), m[4] === undefined ? 1 : Number(m[4])] : [0, 0, 0, 1];
}
async function raw(png: Buffer): Promise<{ data: Buffer; w: number; h: number }> {
  const { data, info } = await sharp(png).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height };
}
/** ΔE00 statistics between two raw RGB buffers of the same size, optionally only inside a mask predicate. */
function dEStats(
  a: { data: Buffer; w: number; h: number },
  b: { data: Buffer; w: number; h: number },
  inside?: (x: number, y: number) => boolean,
  step = 2,
): { p50: number; p95: number; p99: number; max: number; over1: number; n: number } {
  const ds: number[] = [];
  for (let y = 0; y < a.h; y += step)
    for (let x = 0; x < a.w; x += step) {
      if (inside && !inside(x, y)) continue;
      const i = (y * a.w + x) * 3;
      ds.push(dE00(lab(a.data[i]!, a.data[i + 1]!, a.data[i + 2]!), lab(b.data[i]!, b.data[i + 1]!, b.data[i + 2]!)));
    }
  return {
    p50: r1(pct(ds, 50)),
    p95: r1(pct(ds, 95)),
    p99: r1(pct(ds, 99)),
    max: r1(ds.reduce((m, d) => Math.max(m, d), 0)),
    over1: r1((100 * ds.filter((d) => d > 1).length) / ds.length),
    n: ds.length,
  };
}
/** The 5th percentile of the WCAG contrast of a text colour against every pixel of a region (text on a picture). */
function contrastOnRegion(
  img: { data: Buffer; w: number; h: number },
  region: { x: number; y: number; w: number; h: number },
  text: [number, number, number],
): { p5: number; min: number; Lp5: number } {
  const lt = lum(...text);
  const cs: number[] = [];
  const Ls: number[] = [];
  for (let y = Math.max(0, Math.floor(region.y)); y < Math.min(img.h, region.y + region.h); y++)
    for (let x = Math.max(0, Math.floor(region.x)); x < Math.min(img.w, region.x + region.w); x++) {
      const i = (y * img.w + x) * 3;
      const l = lum(img.data[i]!, img.data[i + 1]!, img.data[i + 2]!);
      cs.push(contrast(lt, l));
      Ls.push(lab(img.data[i]!, img.data[i + 1]!, img.data[i + 2]!)[0]);
    }
  return { p5: r1(pct(cs, 5) * 10) / 10, min: r1(cs.reduce((m, c) => Math.min(m, c), Infinity) * 10) / 10, Lp5: r1(pct(Ls, 5)) };
}

// =====================================================================================================================
// 1. the cover timeline, the opening figures, the paper transition (desktop 1280 and phone 400)
// =====================================================================================================================
async function coverRun(w: number, h: number, tag: string): Promise<void> {
  const ctx = await ctxOf(w, h);
  const page = await ctx.newPage();
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  let bytes = 0;
  const urls: { url: string; bytes: number }[] = [];
  page.on('response', (r) => {
    void r
      .body()
      .then((b) => {
        bytes += b.length;
        urls.push({ url: r.url().replace(ORIGIN, ''), bytes: b.length });
      })
      .catch(() => {});
  });
  const t0 = Date.now();
  await page.goto(`${ORIGIN}/test/`, { waitUntil: 'commit' });
  // the first paint: the LQIP is in the HTML, before the module runs
  await page.waitForFunction('document.querySelector(".mag-lqip")', null, { timeout: 10_000 });
  await shot(page, `${tag}-cover-1-lqip`, 'the cover at first paint: the LQIP of H0 under the paper, the type not yet printed');
  await page.waitForFunction('document.body.classList.contains("is-invite")', null, { timeout: 20_000 });
  const inviteAt = Date.now() - t0;
  await sleep(700);
  await shot(page, `${tag}-cover-2-invite`, 'the cover developed: the brand in the band, the cover line in Display, the invitation with its 24 px hairline');
  const evs = await events(page);
  const nav = (await page.evaluate('performance.timing.navigationStart')) as number;
  const origin = (await page.evaluate('performance.timeOrigin')) as number;
  void nav;
  const paint = (await page.evaluate('window.__ev.paint')) as Record<string, number>;
  const lcp = (await page.evaluate('window.__ev.lcp')) as { t: number; size: number; el: string }[];
  const developed = at(evs, 'cover:developed');
  const brand = at(evs, 'cover:brand');
  const title = at(evs, 'cover:title');
  const invite = at(evs, 'cover:invite');
  const fonts = at(evs, 'cover:fonts');
  const timeline = {
    first_paint_ms: r1(paint['first-paint'] ?? NaN),
    first_contentful_paint_ms: r1(paint['first-contentful-paint'] ?? NaN),
    lcp_ms: r1(lcp.at(-1)?.t ?? NaN),
    lcp_element: lcp.at(-1)?.el ?? null,
    h0_sharp_ms: r1(developed ?? NaN),
    fonts_ready_ms: r1(fonts ?? NaN),
    brand_after_fonts_ms: brand !== null && fonts !== null ? r1(brand - fonts) : null,
    title_after_brand_ms: brand !== null && title !== null ? r1(title - brand) : null,
    invite_after_title_ms: title !== null && invite !== null ? r1(invite - title) : null,
    invite_wall_ms: inviteAt,
    bytes_until_invite: bytes,
    files: urls.sort((a, b) => b.bytes - a.bytes).slice(0, 8),
    time_origin: origin,
  };
  // the paper transition: Enter → the veil → the living room; the response time to the first frame of the veil
  const response = page.evaluate(`window.__ev.firstChange('#mag-veil', 'opacity', 2000)`);
  await page.keyboard.press('Enter');
  const responseMs = (await response) as number | null;
  await sleep(120);
  await shot(page, `${tag}-paper-mid`, 'the paper transition, mid-way: paper over the cover (150 ms out, 200 ms hold)');
  await page.waitForFunction('!document.getElementById("mag-veil").classList.contains("is-in")', null, { timeout: 5000 });
  await sleep(500);
  const evs2 = await events(page);
  const out = at(evs2, 'paper:out');
  const inn = at(evs2, 'paper:in');
  await shot(page, `${tag}-living-after-paper`, 'the living room after the paper transition, the running head "02 · הסלון · נורדי"');
  evidence[`cover_${tag}`] = {
    ...timeline,
    paper_response_ms: responseMs === null ? null : r1(responseMs),
    paper_out_to_in_ms: out !== null && inn !== null ? r1(inn - out) : null,
    run_head: await page.textContent('#mag-run'),
  };
  await ctx.close();
}

// the opening under a throttled network and CPU (Fast 4G-like: 4 Mbit/s down, 150 ms RTT; CPU ×4), the phone window
async function throttledOpening(): Promise<void> {
  const ctx = await ctxOf(400, 800);
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 150,
    downloadThroughput: (4 * 1024 * 1024) / 8,
    uploadThroughput: (1 * 1024 * 1024) / 8,
  });
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  let bytes = 0;
  page.on('response', (r) => {
    void r
      .body()
      .then((b) => (bytes += b.length))
      .catch(() => {});
  });
  await page.goto(`${ORIGIN}/test/`, { waitUntil: 'commit' });
  await page.waitForFunction('document.body.classList.contains("is-invite")', null, { timeout: 60_000 });
  await sleep(300);
  const evs = await events(page);
  const paint = (await page.evaluate('window.__ev.paint')) as Record<string, number>;
  const lcp = (await page.evaluate('window.__ev.lcp')) as { t: number; size: number; el: string }[];
  evidence.opening_throttled_phone = {
    network: 'Fast 4G-like: 4 Mbit/s down, 1 Mbit/s up, 150 ms RTT; CPU ×4 (CDP emulation, headless)',
    first_contentful_paint_ms: r1(paint['first-contentful-paint'] ?? NaN),
    lcp_ms: r1(lcp.at(-1)?.t ?? NaN),
    lcp_element: lcp.at(-1)?.el ?? null,
    h0_sharp_ms: r1(at(evs, 'cover:developed') ?? NaN),
    invite_ms: r1(at(evs, 'cover:invite') ?? NaN),
    bytes_until_invite: bytes,
  };
  await ctx.close();
}

// =====================================================================================================================
// 2. the living room at rest (clean), the marks, the wall label, the targets, focus mode: desktop 1280×800
// =====================================================================================================================
async function livingDesktop(): Promise<void> {
  const ctx = await ctxOf(1280, 800);
  const page = await open(ctx);
  await goTo(page, '#room-living-room');
  await page.mouse.move(2, 2);
  await sleep(3200); // 3 s without input: the hint has come and gone
  const rest = await shot(page, 'desk-living-rest', 'the living room at rest, 3 s without input: no marks, no label, nothing on the picture');
  const dots = (await page.evaluate(`[...document.querySelectorAll('#room-living-room .mag-dot')].map((d) => getComputedStyle(d).opacity)`)) as string[];
  const overlayOff = await page.evaluate(
    `(() => { const st = document.querySelector('#room-living-room .mag-stage'); return { marks: st.dataset.marks, label: st.querySelector('.mag-label').classList.contains('is-on'), strip: st.querySelector('.mag-strip').hidden, outline: st.querySelector('.mag-outline').classList.contains('is-on') }; })()`,
  );
  // the same frame with every overlay element removed from the DOM: the difference must be zero
  await page.evaluate(
    `document.querySelectorAll('#room-living-room .mag-mark, #room-living-room .mag-outline, #room-living-room .mag-label').forEach((e) => (e.style.display = 'none'))`,
  );
  await sleep(100);
  const bare = await page.screenshot();
  await page.evaluate(
    `document.querySelectorAll('#room-living-room .mag-mark, #room-living-room .mag-outline, #room-living-room .mag-label').forEach((e) => (e.style.display = ''))`,
  );
  const headH = parseFloat((await page.evaluate(`window.__ev.token('--head-h')`)) as string) || 64;
  const dRest = dEStats(await raw(rest), await raw(bare), (_x, y) => y > headH);
  evidence.clean_room_rest_1280 = { dots_opacity: [...new Set(dots)], overlay: overlayOff, dE00_vs_overlays_removed: dRest };

  // the marks: a pointer movement brings them within --d-mark-in; they go --t-mark-idle after the last movement
  const sampler = page.evaluate(`window.__ev.sample('#room-living-room .mag-mark[data-slot="vase"] .mag-dot', 'opacity', 5200)`);
  await sleep(50);
  const tMove = (await page.evaluate('performance.now()')) as number;
  await page.mouse.move(640, 420);
  await page.mouse.move(646, 426);
  await sleep(400);
  await shot(page, 'desk-living-marks', 'the marks after a pointer movement: 6 px ink dots on the products, nothing else');
  const samples = (await sampler) as [number, string][];
  const evs = await events(page);
  const on = atLast(evs, 'M0:marks:on');
  const off = atLast(evs, 'M0:marks:off');
  const ops = samples.map(([t, v]) => [t - tMove, Number(v)] as [number, number]);
  const appear = ops.find(([, o]) => o >= 0.99)?.[0] ?? null;
  const firstVisible = ops.find(([, o]) => o > 0.02)?.[0] ?? null;
  const fadeStart = ops.find(([t, o], i) => i > 0 && t > 1000 && o < 0.99 && ops[i - 1]![1] >= 0.99)?.[0] ?? null;
  const gone = ops.find(([t, o]) => t > 1000 && o <= 0.005)?.[0] ?? null;
  // periodic change: once at 1, the opacity must not leave 1 before the fade; count direction changes
  let turns = 0;
  for (let i = 2; i < ops.length; i++) {
    const d1 = Math.sign(ops[i - 1]![1] - ops[i - 2]![1]);
    const d2 = Math.sign(ops[i]![1] - ops[i - 1]![1]);
    if (d1 && d2 && d1 !== d2) turns++;
  }
  evidence.marks_timing_1280 = {
    first_visible_ms_after_move: firstVisible === null ? null : r1(firstVisible),
    appear_ms_after_move: appear === null ? null : r1(appear),
    marks_on_event_ms: on === null ? null : r1(on - tMove),
    marks_off_event_ms_after_on: on !== null && off !== null ? r1(off - on) : null,
    fade_start_ms: fadeStart === null ? null : r1(fadeStart),
    gone_ms: gone === null ? null : r1(gone),
    opacity_direction_changes: turns,
    samples: ops.length,
    tokens: {
      mark_in: await page.evaluate(`window.__ev.token('--d-mark-in')`),
      mark_out: await page.evaluate(`window.__ev.token('--d-mark-out')`),
      idle: await page.evaluate(`window.__ev.token('--t-mark-idle')`),
    },
  };

  // the targets and the marks inside their boxes (check 3)
  const frameRect = (await page.evaluate(`window.__ev.rect('#room-living-room .mag-pic img')`)) as { x: number; y: number; w: number; h: number };
  const marks = (await page.evaluate(`window.__ev.rects('#room-living-room .mag-mark')`)) as {
    x: number;
    y: number;
    w: number;
    h: number;
    slot: string;
    box: string;
  }[];
  const overlaps: string[] = [];
  for (let i = 0; i < marks.length; i++)
    for (let j = i + 1; j < marks.length; j++) {
      const a = marks[i]!;
      const b = marks[j]!;
      if (a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h) overlaps.push(`${a.slot}×${b.slot}`);
    }
  const inside = marks.map((m) => {
    const [u0, u1, v0, v1] = m.box.split(',').map(Number) as [number, number, number, number];
    const u = (m.x + m.w / 2 - frameRect.x) / frameRect.w;
    const v = (m.y + m.h / 2 - frameRect.y) / frameRect.h;
    return { slot: m.slot, w: r1(m.w), h: r1(m.h), inside_box: u >= u0 && u <= u1 && v >= v0 && v <= v1 };
  });
  evidence.targets_1280 = {
    marks: inside,
    min_size: Math.min(...marks.map((m) => Math.min(m.w, m.h))),
    overlaps,
    all_inside_box: inside.every((m) => m.inside_box),
    note: 'inside the G1 fidelity box of the product (the alpha of the final layer waits for the layers)',
  };

  // the wall label on hover (check 4: the outline, the halo, and what changes outside them)
  await page.mouse.move(640, 420);
  const vase = page.locator('#room-living-room .mag-mark[data-slot="vase"]');
  await vase.hover();
  await sleep(350);
  const hover = await shot(
    page,
    'desk-living-label',
    'hover on the vase: the product outline and the wall label (name · material · size · price) 12 px above it',
  );
  const outline = (await page.evaluate(`window.__ev.css('#room-living-room .mag-outline', ['border-width', 'box-shadow', 'outline-width'])`)) as Record<
    string,
    string
  >;
  const outlineRect = (await page.evaluate(`window.__ev.rect('#room-living-room .mag-outline')`)) as { x: number; y: number; w: number; h: number };
  const labelRect = (await page.evaluate(`window.__ev.rect('#room-living-room .mag-label')`)) as { x: number; y: number; w: number; h: number };
  const labelText = await page.textContent('#room-living-room .mag-label');
  const halo = Math.max(0, ...(outline['box-shadow'] ?? '').split(',').map((s) => Number((s.match(/(\d+(?:\.\d+)?)px\s*(?:rgba?|$)/) ?? [])[1] ?? 0)));
  const pad = 10;
  const dHover = dEStats(await raw(hover), await raw(rest), (x, y) => {
    const inOutline =
      x >= outlineRect.x - pad && x <= outlineRect.x + outlineRect.w + pad && y >= outlineRect.y - pad && y <= outlineRect.y + outlineRect.h + pad;
    const inLabel = x >= labelRect.x - 4 && x <= labelRect.x + labelRect.w + 4 && y >= labelRect.y - 4 && y <= labelRect.y + labelRect.h + 4;
    const inDots = false;
    return y > headH && !inOutline && !inLabel && !inDots;
  });
  evidence.outline_1280 = {
    outline_css: outline,
    halo_px_from_box_shadow: halo,
    label_text: labelText?.trim(),
    dE00_outside_outline_and_label_vs_rest: dHover,
    note: 'the marks of the other products are on in this state (pointer moved), so dots of 6 px count in "outside"; the alpha-edge distance waits for the alpha layers',
  };
  await page.mouse.move(2, 2);
  await sleep(3300);

  // focus mode: the approach, the look, the strip after 100 + 200 ms, a variant, the return and the landing
  await page.evaluate(
    `window.__te = []; for (const ev of ['transitionstart', 'transitionend']) document.querySelector('#room-living-room .mag-strip').addEventListener(ev, (e) => window.__te.push([e.type + ':' + e.propertyName, performance.now()]))`,
  );
  const fps = page.evaluate(`window.__ev.frames(1700)`);
  const resp = page.evaluate(`window.__ev.firstChange('#room-living-room .mag-frame', 'transform', 2000)`);
  const tClick = (await page.evaluate('performance.now()')) as number;
  await vase.click();
  const responseMs = (await resp) as number | null;
  await sleep(700);
  await shot(page, 'desk-focus-approach', 'the approach to the vase, mid-way (1.6 s, --e-approach): the camera moves, the room still whole');
  await page.waitForFunction(`document.querySelector('#room-living-room .mag-stage').dataset.focus === 'on'`, null, { timeout: 8000 });
  const stripIn = page.evaluate(`window.__ev.sample('#room-living-room .mag-strip', 'opacity', 600)`);
  await sleep(650);
  const stripSamples = (await stripIn) as [number, string][];
  const frameTimes = (await fps) as number[];
  await shot(
    page,
    'desk-focus-on',
    'focus mode: the room uniformly soft and a third of a stop darker, the vase sharp and lifted; the variant strip with the credit, "הוספה לסל" and "בחירה"',
  );
  const evs2 = await events(page);
  const start = atLast(evs2, 'M0:focus:start')!;
  const stop = atLast(evs2, 'M0:focus:camera:stop')!;
  const uiIn = atLast(evs2, 'M0:focus:ui:in')!;
  const stripOp = stripSamples.map(([t, v]) => [t - uiIn, Number(v)] as [number, number]);
  const stripFull = stripOp.find(([, o]) => o >= 0.99)?.[0] ?? null;
  const look = (await page.evaluate(
    `(() => { const soft = document.querySelector('#room-living-room .mag-soft'); const sharp = document.querySelector('#room-living-room .mag-sharp'); return { soft: soft && getComputedStyle(soft).filter, sharp: sharp && getComputedStyle(sharp).filter, sharpMask: sharp && (getComputedStyle(sharp).maskImage || getComputedStyle(sharp).webkitMaskImage || '').slice(0, 80), scale: getComputedStyle(document.querySelector('#room-living-room .mag-frame')).transform }; })()`,
  )) as Record<string, string>;
  // a variant by the keyboard: the credit dissolves (300 ms), the picture stays (the swap waits for the layers)
  await page.keyboard.press('ArrowLeft');
  await sleep(400);
  await shot(
    page,
    'desk-focus-variant-2',
    'the second variant chosen by the arrow key: the thumb ring moves, the credit dissolves; the picture waits for the final layers',
  );
  const checked = await page.locator('#room-living-room .mag-thumb[aria-checked="true"]').getAttribute('data-i');
  const stripCredit = (await page.textContent('#room-living-room .mag-strip-credit'))?.trim();
  // the return: Esc; the strip goes in 150 ms, the camera returns on --e-land over 1.8 s, the landing is the frame at rest
  const stripOut = page.evaluate(`window.__ev.sample('#room-living-room .mag-strip', 'opacity', 400)`);
  await page.keyboard.press('Escape');
  const outSamples = (await stripOut) as [number, string][];
  await sleep(500);
  await shot(page, 'desk-focus-return', 'the return, mid-way (1.8 s, --e-land)');
  await page.waitForFunction(`!document.querySelector('#room-living-room .mag-stage').dataset.focus`, null, { timeout: 8000 });
  await sleep(150);
  const evs3 = await events(page);
  const uiOut = atLast(evs3, 'M0:focus:ui:out')!;
  const retStart = atLast(evs3, 'M0:return:start')!;
  const landed = atLast(evs3, 'M0:landed')!;
  const outOp = outSamples.map(([t, v]) => [t - uiOut, Number(v)] as [number, number]);
  const outGone = outOp.find(([, o]) => o <= 0.01)?.[0] ?? null;
  const te = (await page.evaluate('window.__te')) as [string, number][];
  const teInStart = te.find(([p, at]) => p === 'transitionstart:opacity' && at >= uiIn - 1 && at < uiOut)?.[1] ?? null;
  const teIn = te.find(([p, at]) => p === 'transitionend:opacity' && at > uiIn && at < uiOut)?.[1] ?? null;
  const teOutStart = te.find(([p, at]) => p === 'transitionstart:opacity' && at >= uiOut - 1)?.[1] ?? null;
  const teOut = te.find(([p, at]) => p === 'transitionend:opacity' && at > uiOut)?.[1] ?? null;
  const focused = await page.evaluate(`document.activeElement && document.activeElement.dataset.slot`);
  // the landing: the marks are off again only after the idle; the keyboard focus (back on the mark, recorded above)
  // shows its ring and the marks (:focus-within), so it is released for the pixel comparison with the rest frame
  await page.evaluate('document.activeElement && document.activeElement.blur()');
  await page.mouse.move(2, 2);
  await sleep(3300);
  const landedShot = await shot(page, 'desk-focus-landed', 'after the landing: the frame at rest again, pixel for pixel');
  const dLand = dEStats(await raw(landedShot), await raw(rest), (_x, y) => y > headH);
  const landedTransform = await page.evaluate(`document.querySelector('#room-living-room .mag-frame').style.transform`);
  const headOn = await page.getAttribute('#mag-head', 'data-on');
  evidence.focus_1280 = {
    response_first_frame_ms: responseMs === null ? null : r1(responseMs),
    click_to_focus_start_ms: r1(start - tClick),
    approach_ms: r1(stop - start),
    ui_wait_after_camera_stop_ms: r1(uiIn - stop),
    strip_opacity_1_after_ui_in_ms: stripFull === null ? null : r1(stripFull),
    strip_out_gone_ms: outGone === null ? null : r1(outGone),
    strip_in_transitionend_ms: teIn === null ? null : r1(teIn - uiIn),
    strip_in_start_latency_ms: teInStart === null ? null : r1(teInStart - uiIn),
    strip_in_duration_ms: teInStart === null || teIn === null ? null : r1(teIn - teInStart),
    strip_out_start_latency_ms: teOutStart === null ? null : r1(teOutStart - uiOut),
    strip_out_duration_ms: teOutStart === null || teOut === null ? null : r1(teOut - teOutStart),
    strip_out_transitionend_ms: teOut === null ? null : r1(teOut - uiOut),
    return_ms: r1(landed - retStart),
    ui_out_to_return_start_ms: r1(retStart - uiOut),
    look,
    variant_after_arrow: checked,
    strip_credit_after_arrow: stripCredit,
    focus_back_on_mark: focused,
    head_after_landing: headOn,
    landed_transform: landedTransform,
    dE00_landed_vs_rest: dLand,
    approach_frame_ms: {
      p50: r1(pct(frameTimes, 50)),
      p95: r1(pct(frameTimes, 95)),
      p99: r1(pct(frameTimes, 99)),
      max: r1(frameTimes.reduce((m, f) => Math.max(m, f), 0)),
      dropped_over_25ms: frameTimes.filter((t) => t > 25).length,
      n: frameTimes.length,
      note: 'headless SwiftShader at 1280×800: a floor; the phone trace needs a real phone',
    },
  };

  // the keyboard loop (check 17): Tab to a mark → Enter → arrows → Enter chooses → the focus is back on the mark; Esc
  await page.evaluate(`document.querySelector('#room-living-room .mag-mark[data-slot="vase"]').focus()`);
  await page.keyboard.press('Enter');
  await page.waitForFunction(`document.querySelector('#room-living-room .mag-stage').dataset.focus === 'on'`, null, { timeout: 8000 });
  await sleep(400);
  const focusedThumb = await page.evaluate(`document.activeElement && document.activeElement.className`);
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('ArrowLeft');
  await page.keyboard.press('ArrowRight');
  await sleep(350);
  const idx = await page.locator('#room-living-room .mag-thumb[aria-checked="true"]').getAttribute('data-i');
  await shot(page, 'desk-focus-ring-thumb', 'the keyboard in focus mode: the 2 px ring on the chosen thumb');
  await page.keyboard.press('Enter');
  await page.waitForFunction(`!document.querySelector('#room-living-room .mag-stage').dataset.focus`, null, { timeout: 8000 });
  const backOn = await page.evaluate(`document.activeElement && document.activeElement.dataset.slot`);
  const landedEv = [...(await events(page))].reverse().find((e) => e.name === 'M0:landed')?.detail;
  await page.keyboard.press('Enter');
  await page.waitForFunction(`document.querySelector('#room-living-room .mag-stage').dataset.focus === 'on'`, null, { timeout: 8000 });
  await page.keyboard.press('Escape');
  await page.waitForFunction(`!document.querySelector('#room-living-room .mag-stage').dataset.focus`, null, { timeout: 8000 });
  const backOn2 = await page.evaluate(`document.activeElement && document.activeElement.dataset.slot`);
  evidence.keyboard_loop_1280 = {
    thumb_focused_on_open: focusedThumb,
    variant_after_arrows: idx,
    enter_chooses: landedEv,
    focus_back_after_choose: backOn,
    focus_back_after_escape: backOn2,
  };

  // the price in the three places (check 23): the wall label, the strip and the story credits for the vase
  await page.mouse.move(640, 420);
  await vase.hover();
  await sleep(300);
  const labelDetail = (await page.textContent('#room-living-room .mag-label .mag-credit-detail'))?.trim();
  const storyDetail = (await page.textContent('#story-living-room .mag-credit[data-slot="vase"] .mag-credit-detail'))?.trim();
  await vase.click();
  await page.waitForFunction(`document.querySelector('#room-living-room .mag-stage').dataset.focus === 'on'`, null, { timeout: 8000 });
  await sleep(400);
  const stripDetail = (await page.textContent('#room-living-room .mag-strip .mag-credit-detail'))?.trim();
  const thumbAria = await page.locator('#room-living-room .mag-thumb').first().getAttribute('aria-label');
  const price = (s?: string) => s?.match(/\u2066₪\u00a0[\d,]+(?:\.\d\d)?\u2069/)?.[0] ?? null;
  evidence.price_consistency = {
    label: labelDetail,
    story: storyDetail,
    strip: stripDetail,
    thumb_aria: thumbAria,
    same_price: price(labelDetail) !== null && price(labelDetail) === price(storyDetail) && price(labelDetail) === price(stripDetail),
    ltr_isolated: /\u2066₪\u00a0[\d,]+\u2069/.test(storyDetail ?? ''),
  };
  await page.keyboard.press('Escape');
  await page.waitForFunction(`!document.querySelector('#room-living-room .mag-stage').dataset.focus`, null, { timeout: 8000 });
  await ctx.close();
}

// the clean room at 1920×1080: the 1920 w rendition is drawn 1:1, so the comparison with the encoded file is decode-only
async function cleanRoom1920(): Promise<void> {
  const ctx = await ctxOf(1920, 1080);
  const page = await open(ctx);
  await goTo(page, '#room-living-room');
  await page.mouse.move(2, 2);
  await sleep(3200);
  const png = await shot(page, 'desk1920-living-rest', 'the living room at rest at 1920×1080 (the 1920 rendition 1:1)');
  const src = (await page.evaluate(`document.querySelector('#room-living-room .mag-pic img').currentSrc`)) as string;
  const rect = (await page.evaluate(`window.__ev.rect('#room-living-room .mag-pic img')`)) as { x: number; y: number; w: number; h: number };
  const file = join(DIST, src.replace(ORIGIN, ''));
  const img = sharp(file);
  const meta = await img.metadata();
  const s = Math.max(rect.w / meta.width!, rect.h / meta.height!);
  const dw = Math.round(meta.width! * s);
  const dh = Math.round(meta.height! * s);
  const pos = ((await page.evaluate(`getComputedStyle(document.querySelector('#room-living-room .mag-pic img')).objectPosition`)) as string)
    .split(' ')
    .map((v) => parseFloat(v) / 100);
  const ox = Math.round((rect.w - dw) * (pos[0] ?? 0.5));
  const oy = Math.round((rect.h - dh) * (pos[1] ?? 0.5));
  const ref = await sharp(await img.resize(dw, dh).toBuffer())
    .extract({ left: -ox, top: -oy, width: Math.round(rect.w), height: Math.round(rect.h) })
    .raw()
    .toBuffer({ resolveWithObject: true });
  const shotRaw = await raw(png);
  const headH = parseFloat((await page.evaluate(`window.__ev.token('--head-h')`)) as string) || 64;
  const refImg = { data: ref.data, w: ref.info.width, h: ref.info.height };
  const d = dEStats(shotRaw, refImg, (_x, y) => y > headH, 3);
  evidence.clean_room_rest_1920 = {
    source: src.replace(ORIGIN, ''),
    drawn: { scale: r1(s * 1000) / 1000, dw, dh, ox, oy },
    dE00_vs_encoded_frame: d,
    note: 'the screenshot against the encoded frame decoded by sharp: decoder and colour-management differences only; the final check is against the composite of the layers (qa)',
  };
  await ctx.close();
}

// =====================================================================================================================
// 3. reduced motion, the pan, the dining room, the states, the focus rings, fonts, the scale, the grid, credits
// =====================================================================================================================
async function reducedMotion(): Promise<void> {
  const ctx = await ctxOf(1280, 800, true);
  const page = await open(ctx);
  await goTo(page, '#room-living-room');
  await sleep(300);
  const transforms = page.evaluate(`window.__ev.sample('#room-living-room .mag-frame', 'transform', 900)`);
  await page.evaluate(`window.__mag.openFocus('M0', 'cushions')`);
  await page.waitForFunction(`document.querySelector('#room-living-room .mag-stage').dataset.focus === 'on'`, null, { timeout: 5000 });
  const ts = (await transforms) as [number, string][];
  const distinct = new Set(ts.map(([, v]) => v)).size;
  const evs = await events(page);
  const dur = (await page.evaluate(`getComputedStyle(document.querySelector('#room-living-room .mag-frame')).transitionDuration`)) as string;
  await sleep(300);
  await shot(page, 'desk-reduced-focus', 'reduced motion: focus mode reached by a 300 ms dissolve, nothing moved');
  await page.evaluate(`window.__mag.cancelFocus('M0')`);
  await page.waitForFunction(`!document.querySelector('#room-living-room .mag-stage').dataset.focus`, null, { timeout: 5000 });
  const evs2 = await events(page);
  evidence.reduced_motion = {
    approach_ms: r1(atLast(evs, 'M0:focus:camera:stop')! - atLast(evs, 'M0:focus:start')!),
    return_ms: r1(atLast(evs2, 'M0:landed')! - atLast(evs2, 'M0:return:start')!),
    frame_transition_duration: dur,
    distinct_transform_values_during_approach: distinct,
    note: 'two values (before, after) = one cut inside the dissolve, no animated transform',
  };
  await ctx.close();
}

async function panAndDining(): Promise<void> {
  const ctx = await ctxOf(1280, 800);
  const page = await open(ctx);
  await goTo(page, '#room-dining-room');
  await page.mouse.move(2, 2);
  await sleep(3200);
  await shot(page, 'desk-dining-rest', 'the dining room D1 at rest');
  await goTo(page, '#mag-pan');
  await page.waitForFunction('window.__mag && window.__mag.pan.ready === true', null, { timeout: 90_000 });
  await sleep(200);
  await shot(page, 'desk-pan-0', 'the P-D pan block, frame 1 (the registered test clip of 2026-11-02)');
  const fps = page.evaluate(`window.__ev.frames(1500)`);
  const t0 = (await page.evaluate('performance.now()')) as number;
  await page.getByRole('button', { name: 'נגינה' }).click();
  await sleep(700);
  await shot(page, 'desk-pan-mid', 'the pan mid-way, constant speed between the ramps');
  await page.waitForFunction('!window.__mag.pan.playing', null, { timeout: 20_000 });
  const frameTimes = (await fps) as number[];
  await shot(page, 'desk-pan-end', 'the pan at its last frame (D2 of the test clip)');
  const samples = (await page.evaluate('window.__mag.pan.samples')) as { t: number; p: number }[];
  const evs = await events(page);
  const play = atLast(evs, 'pan:play')!;
  const end = atLast(evs, 'pan:end')!;
  let mono = true;
  for (let i = 1; i < samples.length; i++) if (samples[i]!.p < samples[i - 1]!.p) mono = false;
  // the speed profile: the frame rate (frames per second of clip time) in the middle 40% vs the ramps
  const mid = samples.filter((s) => s.p > 0.3 * 83 && s.p < 0.7 * 83);
  const speed = mid.length > 2 ? r1(((mid.at(-1)!.p - mid[0]!.p) / (mid.at(-1)!.t - mid[0]!.t)) * 1000) : null;
  const canvasBox = (await page.evaluate(
    `(() => { const c = document.querySelector('.mag-pan-canvas'); return { w: c.width, h: c.height, cw: c.clientWidth, ch: c.clientHeight }; })()`,
  )) as Record<string, number>;
  await page.getByRole('button', { name: 'חזרה' }).click();
  await page.waitForFunction('!window.__mag.pan.playing', null, { timeout: 20_000 });
  evidence.pan = {
    play_ms: r1(end - play),
    click_to_play_event_ms: r1(play - t0),
    samples: samples.length,
    monotonic: mono,
    mid_speed_frames_per_s: speed,
    nominal_frames_per_s_at_constant: r1(84 / 1.4 / (1 - 0.15 / 2 - 0.3 / 2)),
    canvas: canvasBox,
    frame_ms: {
      p50: r1(pct(frameTimes, 50)),
      p95: r1(pct(frameTimes, 95)),
      p99: r1(pct(frameTimes, 99)),
      max: r1(frameTimes.reduce((m, f) => Math.max(m, f), 0)),
      dropped_over_25ms: frameTimes.filter((t) => t > 25).length,
      n: frameTimes.length,
    },
    scale:
      'the frames are drawn by SequencePlayer.draw at the size fixed once by fit(): scale 1.000 along the whole clip (web/src/engine/sequence.ts); no transform on the canvas',
  };
  await ctx.close();
}

async function statesAndRings(): Promise<void> {
  const ctx = await ctxOf(1280, 800);
  const page = await open(ctx);
  await goTo(page, '#states-title');
  await sleep(300);
  const st = (await page.evaluate(`window.__ev.rect('.mag-states')`)) as { x: number; y: number; w: number; h: number };
  const clip = { x: 0, y: Math.max(0, st.y - 60), width: 1280, height: Math.min(800, st.h + 120) };
  await shot(page, 'desk-states-rest', 'the states block at rest: primary, secondary, link, the field, the unavailable product', clip);
  await page.hover('#st-primary');
  await sleep(250);
  await shot(page, 'desk-states-hover', 'hover on the primary button (ink-press, 120 ms)', clip);
  await page.mouse.down();
  await sleep(120);
  await shot(page, 'desk-states-press', 'press on the primary button (80 ms)', clip);
  await page.mouse.up();
  await sleep(300);
  await shot(page, 'desk-states-added', 'after the press: "נוסף לסל" in the same button, no toast', clip);
  await page.focus('#st-email');
  await sleep(250);
  await shot(page, 'desk-states-focus-field', 'the field focused: the 2 px ring', clip);
  await page.fill('#st-email', 'לא אימייל');
  await page.keyboard.press('Enter');
  await sleep(250);
  await shot(page, 'desk-states-error', 'the error state: the message under the field, the field marked', clip);
  await page.click('#st-loading');
  await sleep(400);
  await shot(page, 'desk-states-loading', 'the loading state: "רגע…" and the 1 px progress hairline, no spinner', clip);
  await sleep(1400);
  // the focus rings along the Tab order (check 16)
  await page.evaluate('window.scrollTo(0, 0)');
  await page.keyboard.press('Tab');
  const ring: { el: string; outline: string; offset: string; shadow: string; inView: boolean }[] = [];
  for (let i = 0; i < 40; i++) {
    const r = (await page.evaluate(
      `(() => { const el = document.activeElement; if (!el || el === document.body) return null; const cs = getComputedStyle(el); const b = el.getBoundingClientRect(); const sc = el.closest('.mag-scroller'); const sb = sc ? sc.getBoundingClientRect() : { left: 0, top: 0, right: innerWidth, bottom: innerHeight }; const o = parseFloat(cs.outlineOffset) || 0; const w = parseFloat(cs.outlineWidth) || 0; const inView = b.left - o - w >= sb.left - 0.5 && b.right + o + w <= sb.right + 0.5 && b.top - o - w >= sb.top - 0.5 && b.bottom + o + w <= sb.bottom + 0.5; return { el: (el.id ? '#' + el.id : el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]) + (el.dataset.slot ? '[' + el.dataset.slot + ']' : ''), outline: cs.outlineWidth + ' ' + cs.outlineStyle + ' ' + cs.outlineColor, offset: cs.outlineOffset, shadow: cs.boxShadow.slice(0, 60), inView }; })()`,
    )) as { el: string; outline: string; offset: string; shadow: string; inView: boolean } | null;
    if (!r) break;
    ring.push(r);
    if (r.el === '#mag-enter') await shot(page, 'desk-ring-invite', 'the ring on the invitation (Tab)');
    if (r.el.startsWith('button.mag-mark') && !shots.some((s) => s.name === 'desk-ring-mark'))
      await shot(page, 'desk-ring-mark', 'the ring on a mark (Tab into the room)');
    await page.keyboard.press('Tab');
  }
  evidence.focus_rings_1280 = {
    tab_stops: ring.length,
    rings: ring,
    all_2px: ring.every((r) => r.outline.startsWith('2px')),
    all_in_view: ring.every((r) => r.inView),
  };

  // fonts (check 18), the scale and the line length (19), justify and letter-spacing
  await page.evaluate('document.fonts.ready');
  const fonts = (await page.evaluate(
    `[...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family + ' ' + f.weight + ' ' + (f.unicodeRange || '').slice(0, 16))`,
  )) as string[];
  const fontCheck = (await page.evaluate(
    `({ frl300: document.fonts.check('300 16px "Frank Ruhl Libre"'), frl500: document.fonts.check('500 16px "Frank Ruhl Libre"'), as300: document.fonts.check('300 16px Assistant'), as400: document.fonts.check('400 16px Assistant'), as600: document.fonts.check('600 16px Assistant'), heb: document.fonts.check('400 16px Assistant', 'שלום') })`,
  )) as Record<string, boolean>;
  const families = (await page.evaluate(
    `(() => { const out = {}; for (const el of document.querySelectorAll('body *')) { if (!el.textContent || !el.textContent.trim() || el.children.length) continue; const cs = getComputedStyle(el); if (cs.display === 'none') continue; const f = cs.fontFamily.split(',')[0].replace(/"/g, '').trim(); out[f] = (out[f] || 0) + 1; } return out; })()`,
  )) as Record<string, number>;
  const sizes = (await page.evaluate(
    `(() => { const out = {}; for (const el of document.querySelectorAll('main *, header *')) { if (!el.textContent || !el.textContent.trim() || el.children.length) continue; const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') continue; const k = cs.fontSize + '/' + cs.lineHeight + ' ' + cs.fontWeight + ' ' + cs.fontFamily.split(',')[0].replace(/"/g, ''); out[k] = (out[k] || 0) + 1; } return out; })()`,
  )) as Record<string, number>;
  const tokens = (await page.evaluate(
    `['--t-display','--t-h1','--t-h2','--t-h3','--t-lead','--t-body','--t-credit','--t-detail','--t-cap','--t-run','--t-btn','--t-input','--t-brand'].map((t) => t + ': ' + window.__ev.token(t))`,
  )) as string[];
  const lines = (await page.evaluate(
    `[...document.querySelectorAll('.mag-lead, #story-living-room .mag-cap')].slice(0, 4).map((p) => { const cs = getComputedStyle(p); const lh = parseFloat(cs.lineHeight); const n = Math.max(1, Math.round(p.getBoundingClientRect().height / lh)); return { cls: p.className.split(' ')[0], chars_per_line: Math.round(p.textContent.trim().length / n), lines: n, width: Math.round(p.getBoundingClientRect().width), align: cs.textAlign, letterSpacing: cs.letterSpacing }; })`,
  )) as unknown[];
  const justify = (await page.evaluate(
    `[...document.querySelectorAll('body *')].filter((el) => getComputedStyle(el).textAlign === 'justify').length`,
  )) as number;
  const inputSize = (await page.evaluate(`getComputedStyle(document.getElementById('st-email')).fontSize`)) as string;
  const spacing = (await page.evaluate(
    `[...new Set([...document.querySelectorAll('main *')].filter((el) => el.textContent && /[\\u0590-\\u05FF]/.test(el.textContent) && !el.children.length).map((el) => getComputedStyle(el).letterSpacing))]`,
  )) as string[];
  evidence.type_1280 = {
    fonts_loaded: fonts,
    font_check: fontCheck,
    families_in_use: families,
    computed_sizes: sizes,
    scale_tokens: tokens,
    line_length: lines,
    justify_count: justify,
    input_font_size: inputSize,
    hebrew_letter_spacing: spacing,
  };

  // the grid overlay (check 20)
  await page.evaluate(`document.body.dataset.grid = '1'`);
  await goTo(page, '#story-living-room');
  await sleep(300);
  await shot(page, 'desk-grid-story', 'the story page with the 12-column grid overlay at 1280');
  const grid = (await page.evaluate(
    `(() => { const g = document.querySelector('#story-living-room .mag-grid'); const cs = getComputedStyle(g); const cols = cs.gridTemplateColumns.split(' ').map(parseFloat); const gr = g.getBoundingClientRect(); const gap = parseFloat(cs.columnGap); const edges = []; let x = gr.left + parseFloat(cs.paddingLeft); for (const c of cols) { edges.push(x, x + c); x += c + gap; } const main = document.querySelector('#story-living-room .mag-col-main').getBoundingClientRect(); const near = (v) => Math.min(...edges.map((e) => Math.abs(e - v))); return { cols: cols.length, col_w: Math.round(cols[0] * 10) / 10, gap, margin: parseFloat(cs.paddingLeft), main_left_off: Math.round(near(main.left) * 10) / 10, main_right_off: Math.round(near(main.right) * 10) / 10, margin_token: window.__ev.token('--margin') }; })()`,
  )) as Record<string, number | string>;
  evidence.grid_1280 = grid;
  await page.evaluate(`delete document.body.dataset.grid`);

  // credits (check 21): the format, nothing on the picture but the marks, "temporary" only in the footer
  const credits = (await page.evaluate(`[...document.querySelectorAll('.mag-credits .mag-credit-detail')].map((e) => e.textContent.trim())`)) as string[];
  const format = /^(?:[^·]+ · )?(?:[^·]+ ס״מ · )?\u2066₪\u00a0[\d,]+(?:\.\d\d)?\u2069(?: · המלאי אינו זמין כעת)?$|^ממתינה למוצר$/;
  const onPicture = (await page.evaluate(
    `[...document.querySelectorAll('.mag-stage *')].filter((el) => { const cs = getComputedStyle(el); return cs.display !== 'none' && cs.visibility !== 'hidden' && parseFloat(cs.opacity) > 0 && !el.closest('.mag-strip') && !el.closest('.mag-mark') && !el.closest('.mag-label') && !el.matches('.mag-frame, .mag-scroller, .mag-pic, img, picture, source, .mag-outline, .mag-label, .mag-close, .mag-strip'); }).map((el) => el.tagName + '.' + el.className)`,
  )) as string[];
  const temp = (await page.evaluate(
    `[...document.querySelectorAll('body *')].filter((el) => !el.children.length && /זמני|בדיקה/.test(el.textContent || '') && el.getClientRects().length > 0 && getComputedStyle(el).opacity !== '0' && !el.closest('.mag-foot')).map((el) => el.tagName + '.' + el.className + ': ' + el.textContent.trim().slice(0, 50))`,
  )) as string[];
  evidence.credits = {
    count: credits.length,
    bad_format: credits.filter((c) => !format.test(c)),
    sample: credits.slice(0, 4),
    elements_on_picture_besides_marks: onPicture,
    temporary_marks_outside_footer: temp,
  };
  await ctx.close();
}

// contrast (check 14) and the headline over the picture (check 15), desktop and phone
async function contrastRun(w: number, h: number, tag: string): Promise<void> {
  const ctx = await ctxOf(w, h);
  const page = await open(ctx);
  await page.waitForFunction('document.body.classList.contains("is-invite")', null, { timeout: 20_000 });
  await sleep(800);
  const pairs: Record<string, unknown> = {};
  const colorOf = async (sel: string, prop = 'color') =>
    parseRgb((await page.evaluate(`getComputedStyle(document.querySelector('${sel}')).${prop}`)) as string);
  // text over the picture: the cover line, the brand and the running head on H0, measured on the pixels behind them
  const bands: Record<string, unknown> = {};
  for (const sel of ['.mag-cover-title', '.mag-brand', '.mag-invite-btn']) {
    const rect = (await page.evaluate(`window.__ev.rect('${sel}')`)) as { x: number; y: number; w: number; h: number };
    const col = await colorOf(sel);
    await page.evaluate(`document.querySelector('${sel}').style.visibility = 'hidden'`);
    await sleep(50);
    const png = await page.screenshot();
    await page.evaluate(`document.querySelector('${sel}').style.visibility = ''`);
    const img = await raw(png);
    bands[sel] = {
      text: `rgb(${col[0]},${col[1]},${col[2]})`,
      region: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.w), h: Math.round(rect.h) },
      ...contrastOnRegion(img, rect, [col[0], col[1], col[2]]),
    };
  }
  // the top band (64 px) over each frame, at rest: L* at the 5th percentile
  const headH = parseFloat((await page.evaluate(`window.__ev.token('--head-h')`)) as string) || 64;
  const bandL: Record<string, unknown> = {};
  for (const [id, sel] of [
    ['H0', '#cover'],
    ['M0', '#room-living-room'],
    ['D1', '#room-dining-room'],
  ] as const) {
    await goTo(page, sel);
    await page.evaluate(`document.querySelectorAll('#mag-head > *').forEach((e) => (e.style.visibility = 'hidden'))`);
    await sleep(900);
    const png = await page.screenshot({ clip: { x: 0, y: 0, width: w, height: headH } });
    await page.evaluate(`document.querySelectorAll('#mag-head > *').forEach((e) => (e.style.visibility = ''))`);
    const img = await raw(png);
    const ink = await colorOf('#mag-head');
    bandL[id] = contrastOnRegion(img, { x: 0, y: 0, w, h: headH }, [ink[0], ink[1], ink[2]]);
  }
  await goTo(page, '#story-living-room');
  await sleep(300);
  const bg = await colorOf('.mag-paper', 'backgroundColor');
  const paperL = lum(bg[0], bg[1], bg[2]);
  for (const [name, sel, prop] of [
    ['h2 on paper', '.mag-h2', 'color'],
    ['lead on paper', '.mag-lead', 'color'],
    ['credit detail on paper', '.mag-credit-detail', 'color'],
    ['caption on paper', '#story-living-room .mag-cap', 'color'],
    ['link on paper', '.mag-link', 'color'],
    ['secondary button text', '.mag-btn-secondary', 'color'],
    ['secondary button border (3:1)', '.mag-btn-secondary', 'borderTopColor'],
    ['field border (3:1)', '#st-email', 'borderTopColor'],
    ['error text', '#st-email-err', 'color'],
  ] as const) {
    const c = await colorOf(sel, prop);
    pairs[name] = r1(contrast(lum(c[0], c[1], c[2]), paperL) * 10) / 10;
  }
  const pb = await colorOf('.mag-btn-primary', 'backgroundColor');
  const pc = await colorOf('.mag-btn-primary', 'color');
  pairs['primary button text on its ink'] = r1(contrast(lum(pc[0], pc[1], pc[2]), lum(pb[0], pb[1], pb[2])) * 10) / 10;
  await page.focus('#st-email');
  const ring = await colorOf('#st-email', 'outlineColor');
  pairs['focus ring on paper (3:1)'] = r1(contrast(lum(ring[0], ring[1], ring[2]), paperL) * 10) / 10;
  evidence[`contrast_${tag}`] = { on_paper: pairs, text_over_picture_p5: bands, head_band_L_p5: bandL, paper: `rgb(${bg[0]},${bg[1]},${bg[2]})` };
  await ctx.close();
}

// =====================================================================================================================
// 4. the phone: 400×800 (the brief: phone-first), the window, the cushions close-up (FOC2), the strip, the pan
// =====================================================================================================================
async function phone(): Promise<void> {
  const ctx = await ctxOf(400, 800);
  const page = await open(ctx);
  await page.waitForFunction('document.body.classList.contains("is-invite")', null, { timeout: 20_000 });
  await goTo(page, '#toc');
  await sleep(400);
  await shot(page, 'phone-toc', 'the contents on the phone: the rooms, the unavailable styles "בגיליונות הבאים"');
  await goTo(page, '#room-living-room');
  await sleep(3200);
  const scroller = (await page.evaluate(
    `(() => { const s = document.querySelector('#room-living-room .mag-scroller'); const f = s.querySelector('.mag-frame'); return { scrollLeft: s.scrollLeft, frameW: f.offsetWidth, viewW: s.clientWidth, u0: s.scrollLeft / f.offsetWidth, u1: (s.scrollLeft + s.clientWidth) / f.offsetWidth }; })()`,
  )) as Record<string, number>;
  await shot(
    page,
    'phone-living-rest',
    'the living room on the phone at rest: the frame at full height, the view on the Bible window (u 0.567–0.905), the sides by a swipe',
  );
  await page.touchscreen.tap(200, 300);
  await sleep(350);
  await shot(page, 'phone-living-marks', 'the marks after a touch');
  const marks = (await page.evaluate(`window.__ev.rects('#room-living-room .mag-mark')`)) as { x: number; y: number; w: number; h: number; slot: string }[];
  const visible = marks.filter((m) => m.x + m.w > 0 && m.x < 400);
  await sleep(3000);
  // the cushions close-up (FOC2): a reframe on the phone
  const fps = page.evaluate(`window.__ev.frames(1700)`);
  await page.evaluate(`window.__mag.openFocus('M0', 'cushions')`);
  await page.waitForFunction(`document.querySelector('#room-living-room .mag-stage').dataset.focus === 'on'`, null, { timeout: 8000 });
  const frameTimes = (await fps) as number[];
  await sleep(500);
  await shot(page, 'phone-focus-cushions', 'the cushions close-up on the phone (FOC2): the strip at the bottom with the credit, the thumbs and "בחירה"');
  const stripRect = (await page.evaluate(`window.__ev.rect('#room-living-room .mag-strip')`)) as { x: number; y: number; w: number; h: number };
  const thumbs = (await page.evaluate(`window.__ev.rects('#room-living-room .mag-thumb')`)) as { w: number; h: number }[];
  const evs = await events(page);
  await page.evaluate(`window.__mag.cancelFocus('M0')`);
  await page.waitForFunction(`!document.querySelector('#room-living-room .mag-stage').dataset.focus`, null, { timeout: 8000 });
  const back = (await page.evaluate(`document.querySelector('#room-living-room .mag-scroller').scrollLeft`)) as number;
  evidence.phone = {
    window: scroller,
    marks_visible_in_window: visible.map((m) => m.slot),
    min_mark_size: Math.min(...marks.map((m) => Math.min(m.w, m.h))),
    approach_ms: r1(atLast(evs, 'M0:focus:camera:stop')! - atLast(evs, 'M0:focus:start')!),
    ui_wait_ms: r1(atLast(evs, 'M0:focus:ui:in')! - atLast(evs, 'M0:focus:camera:stop')!),
    strip: { h: r1(stripRect.h), thumb_min: Math.min(...thumbs.map((t) => Math.min(t.w, t.h))) },
    scroll_restored_after_return: back === scroller.scrollLeft,
    approach_frame_ms: { p50: r1(pct(frameTimes, 50)), p95: r1(pct(frameTimes, 95)), p99: r1(pct(frameTimes, 99)), n: frameTimes.length },
  };
  await goTo(page, '#story-living-room');
  await sleep(300);
  await page.evaluate(`document.body.dataset.grid = '1'`);
  await shot(page, 'phone-grid-story', 'the story on the phone with the 4-column grid overlay, 24 px margins');
  const grid = (await page.evaluate(
    `(() => { const g = document.querySelector('#story-living-room .mag-grid'); const cs = getComputedStyle(g); const cols = cs.gridTemplateColumns.split(' ').map(parseFloat); const main = document.querySelector('#story-living-room .mag-col-main').getBoundingClientRect(); const gr = g.getBoundingClientRect(); return { cols: cols.length, margin: parseFloat(cs.paddingLeft), main_left: Math.round(main.left), main_right_gap: Math.round(innerWidth - main.right), grid_left: Math.round(gr.left) }; })()`,
  )) as Record<string, number>;
  await page.evaluate(`delete document.body.dataset.grid`);
  evidence.grid_400 = grid;
  const lines = (await page.evaluate(
    `[...document.querySelectorAll('.mag-lead')].slice(0, 2).map((p) => { const cs = getComputedStyle(p); const lh = parseFloat(cs.lineHeight); const n = Math.max(1, Math.round(p.getBoundingClientRect().height / lh)); return { chars_per_line: Math.round(p.textContent.trim().length / n), lines: n, fontSize: cs.fontSize }; })`,
  )) as unknown[];
  evidence.type_400 = { line_length: lines, input_font_size: await page.evaluate(`getComputedStyle(document.getElementById('st-email')).fontSize`) };
  await goTo(page, '#states-title');
  await sleep(300);
  await shot(page, 'phone-states', 'the states block on the phone');
  await goTo(page, '#room-dining-room');
  await sleep(1200);
  await shot(page, 'phone-dining-rest', 'the dining room on the phone, the view on its window (u 0.33–0.67)');
  await goTo(page, '#mag-pan');
  await page.waitForFunction('window.__mag && window.__mag.pan.ready === true', null, { timeout: 90_000 });
  await sleep(200);
  await shot(page, 'phone-pan-0', 'the pan block on the phone (the mobile variant of the clip)');
  await ctx.close();
}

// =====================================================================================================================
// 5. the code checks: no spinners, the motion tokens, the curves, no scale on hover/press, no push
// =====================================================================================================================
function codeChecks(): void {
  const css = readFileSync(sitePath('web/src/test-page/magazine.css'), 'utf8');
  const ts = readFileSync(sitePath('web/src/test-page/main.ts'), 'utf8');
  const html = readFileSync(sitePath('tools/test-page/index.template.html'), 'utf8');
  const forbidden = ['spinner', 'shimmer', 'backdrop-filter', 'rotate(', 'bounce', 'pulse', 'parallax', 'infinite'];
  const hits: Record<string, number> = {};
  for (const f of forbidden)
    hits[f] =
      (css.match(new RegExp(f.replace('(', '\\('), 'g')) ?? []).length +
      (ts.match(new RegExp(f.replace('(', '\\('), 'g')) ?? []).length +
      (html.match(new RegExp(f.replace('(', '\\('), 'g')) ?? []).length;
  // durations: every transition/animation in the CSS uses a token; literal ms outside :root
  // the tokens live on .mag (the page's scope), from its opening brace to the first closing one
  const rootStart = css.indexOf('.mag {');
  const root = css.slice(rootStart, css.indexOf('\n}', rootStart));
  const body = css.replace(root, '');
  const literalMs = [...body.matchAll(/\b(\d+(?:\.\d+)?)m?s\b/g)].map((m) => m[0]).filter((m) => /ms$|s$/.test(m));
  const transitions = [...css.matchAll(/(?:transition|animation)\s*:\s*([^;]+);/g)].map((m) => m[1]!.replace(/\s+/g, ' ').trim());
  const nonToken = transitions.filter((t) => !/none/.test(t) && !/var\(--d-/.test(t));
  const beziers = [...css.matchAll(/cubic-bezier\(([^)]+)\)/g)].map((m) => m[1]!.split(',').map(Number));
  const badCurves = beziers.filter((b) => b[1]! < 0 || b[1]! > 1 || b[3]! < 0 || b[3]! > 1);
  const hoverScale = [...css.matchAll(/:(?:hover|active)[^{]*\{[^}]*scale\(/g)].length;
  const jsLiterals = [...ts.matchAll(/wait\((\d+)\)/g)].map((m) => Number(m[1]));
  const jsFallbacks = [...ts.matchAll(/ms\('(--[\w-]+)', (\d+)\)/g)].map((m) => `${m[1]}=${m[2]}`);
  const tokensCss = [...root.matchAll(/(--[dt]-[\w-]+):\s*(\d+)ms/g)].map((m) => `${m[1]}=${m[2]}`);
  const TABLE_71 = [
    '--d-press',
    '--d-micro',
    '--d-ui-out',
    '--d-ui-in',
    '--d-mark-in',
    '--d-mark-out',
    '--t-mark-idle',
    '--d-swap',
    '--d-page-out',
    '--d-page-in',
    '--d-develop',
    '--d-style',
    '--d-approach',
    '--d-return',
    '--d-walk',
    '--d-pan',
  ];
  const tokensNotIn71 = tokensCss.map((x) => x.split('=')[0]!).filter((n) => !TABLE_71.includes(n));
  const fallbackMismatch = jsFallbacks.filter((f) => !tokensCss.includes(f));
  const push = (ts.match(/scale\(/g) ?? []).length;
  evidence.code = {
    forbidden_hits: hits,
    css_transitions: transitions.length,
    css_transitions_without_token: nonToken,
    css_literal_durations_outside_root: [...new Set(literalMs)],
    cubic_beziers: beziers.map((b) => b.join(',')),
    curves_with_y_outside_0_1: badCurves,
    scale_in_hover_or_active_rules: hoverScale,
    js_literal_waits_ms: jsLiterals,
    js_literal_waits_note: 'the cover beats of art direction §8.1 (+200 brand, +400 cover line, +800 invitation) and the fonts ceiling (800 ms)',
    js_token_fallbacks_mismatching_css: fallbackMismatch,
    css_tokens: tokensCss,
    css_tokens_not_in_table_71: tokensNotIn71,
    css_tokens_not_in_table_71_note:
      '--d-ui-wait is the "100 ms after the camera stops" of the --d-ui-in row; --d-paper-hold and --d-paper-in are the paper transition of §6.3 (hold 200 ms, dissolve 400 ms), not yet rows of the 7.1 table',
    scale_calls_in_main_ts: push,
    scale_calls_note: 'focus mode only (the approach transform); the pan path draws the frames at scale 1.000 (SequencePlayer.fit once)',
    ui_transitions_over_200ms: transitions.filter((t) => /--d-(develop|approach|return|swap|paper-in|page-in|mark-out)/.test(t)),
    ui_transitions_over_200ms_note:
      'the picture (develop 600, approach 1600, return 1800, swap 300, paper-in 400, page-in 320) and the marks going (600) are not interface fades; every interface fade is ≤ 200 ms',
  };
}

// the pan clip's last frame against the D1 frame (check 5 for this clip; the walk into M0 waits for the new M0 and T-E0)
async function panLanding(): Promise<void> {
  const last = sitePath('web/public/media/test/p-d/1920/0084.webp');
  const d1 = sitePath('web/public/media/test/D1/1920.webp');
  const first = sitePath('web/public/media/test/p-d/1920/0001.webp');
  if (!existsSync(last) || !existsSync(d1) || !existsSync(first)) return;
  const a = await sharp(first).resize(1920, 1080).raw().toBuffer({ resolveWithObject: true });
  const b = await sharp(d1).resize(1920, 1080).raw().toBuffer({ resolveWithObject: true });
  evidence.pan_first_frame_vs_d1 = {
    ...dEStats({ data: a.data, w: 1920, h: 1080 }, { data: b.data, w: 1920, h: 1080 }, undefined, 4),
    note: 'the test clip starts on its own D1 (graded v2 geometry), not on the D1 v3 frame of the spread: that is why the pan is a labelled block and not the walk between the spreads',
  };
}

// =====================================================================================================================
const t0 = Date.now();
codeChecks();
await panLanding();
await coverRun(1280, 800, 'desk');
await coverRun(400, 800, 'phone');
await throttledOpening();
await livingDesktop();
await cleanRoom1920();
await reducedMotion();
await panAndDining();
await statesAndRings();
await contrastRun(1280, 800, '1280');
await contrastRun(400, 800, '400');
await phone();
await browser.close();
server.close();

evidence.problems = problems;
evidence.notes = notes;
evidence.shots = shots;
evidence.run = { at: new Date().toISOString(), seconds: Math.round((Date.now() - t0) / 1000), browser: 'Chromium headless, SwiftShader, DPR 1' };
writeFileSync(join(OUT, 'evidence.json'), JSON.stringify(evidence, null, 1));
const md = [
  '# Evidence of the test page (measured headless, Chromium + SwiftShader)',
  '',
  `Run ${evidence.run && (evidence.run as { at: string }).at}; ${shots.length} screenshots under screens/. The figures per check are in evidence.json; README.md maps them to the 25 checks of art direction §10.`,
  '',
  '## Screenshots',
  ...shots.map((s) => `- \`screens/${s.name}.png\`: ${s.caption}`),
  '',
  '## Problems',
  ...(problems.length ? problems.map((p) => `- ${p}`) : ['- none (no page errors, no console errors)']),
  '',
];
writeFileSync(join(OUT, 'evidence.md'), md.join('\n'));
console.log(`evidence → ${OUT} (${shots.length} screenshots, ${problems.length} problems, ${Math.round((Date.now() - t0) / 1000)} s)`);
if (problems.length) process.exitCode = 1;
