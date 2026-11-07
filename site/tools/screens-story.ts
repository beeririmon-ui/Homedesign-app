/**
 * Evidence for layer 1, the story (/story/, /story/<room>/<style>/; briefs/site-interface-track-2026-11-07.md S1), on
 * web/dist (Chromium headless + SwiftShader, so frame times are a floor, not a phone's):
 *   screens/       400×800 (touch) and 1280×800: the contents; the Nordic living room (the opening, the dots, the sheet,
 *                  after "הוספה לסל", the list, the second frame, the tool entry, the other houses, the cart); warm
 *                  modern; modern country ("almost"); boho (typographic); keyboard focus; reduced motion
 *   evidence.json  timings (the opening, the dots, the sheet), contrast (text on the frames and on paper), the first-load
 *                  weight (the contents and the Nordic page; DPR 1 and 3), axe (WCAG 2.0/2.1 A + AA) on every kind of
 *                  page, the real-routes check, and the public build (HD_PUBLIC=1) carrying no story and no test page
 *   evidence.md    the list of screenshots and problems
 *
 *   npm run screens:story [-- --out=qa/reports/…]     (after npm run build; serves web/dist itself)
 */
import { execFileSync } from 'node:child_process';
import { createServer } from 'node:http';
import { createReadStream, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, relative } from 'node:path';
import { gzipSync } from 'node:zlib';
import { chromium, type Browser, type BrowserContext, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import sharp from 'sharp';
import { repoPath, sitePath } from './lib/paths';

const PORT = 5198;
const ORIGIN = `http://127.0.0.1:${PORT}`;
const DIST = sitePath('web/dist');
const OUT = repoPath(process.argv.find((a) => a.startsWith('--out='))?.slice(6) ?? 'qa/reports/2026-11-07-site-track/s1');
const SHOTS = join(OUT, 'screens');
mkdirSync(SHOTS, { recursive: true });
const NORDIC = '/story/living-room/nordic/';
const WARM = '/story/living-room/warm-modern/';
const COUNTRY = '/story/living-room/modern-country/';
const BOHO = '/story/living-room/boho/';
/** every frame the gate lets in, by page */
const FRAMES = [
  [NORDIC, 'A'],
  [NORDIC, 'B'],
  [WARM, 'A'],
  [COUNTRY, 'A'],
] as const;
if (!existsSync(join(DIST, 'story/index.html')) || !existsSync(join(DIST, NORDIC, 'index.html'))) {
  console.error('web/dist/story/ is missing: run npm run build first.');
  process.exit(1);
}

// ---------- a static server for dist ----------
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

// page-side helpers as a string (tsx would inject a __name helper into a closure the page lacks)
const HELPERS = `
window.__ev = {
  lcp: [], paint: {},
  rect(sel) { const r = document.querySelector(sel).getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; },
  firstChange(sel, prop, timeout) { return new Promise((res) => { const el = document.querySelector(sel); const v0 = getComputedStyle(el)[prop]; const t0 = performance.now();
    const f = () => { const t = performance.now(); if (getComputedStyle(el)[prop] !== v0) res(t - t0); else if (t - t0 > timeout) res(null); else requestAnimationFrame(f); }; requestAnimationFrame(f); }); },
  transitions(sel, ms) { return new Promise((res) => { const el = document.querySelector(sel); const out = []; const t0 = performance.now();
    const on = (e) => { if (e.target === el) out.push([e.type, e.propertyName, Math.round(performance.now() - t0)]); };
    el.addEventListener('transitionstart', on); el.addEventListener('transitionend', on); setTimeout(() => res(out), ms); }); },
  frames(ms) { return new Promise((res) => { const out = []; let last = performance.now(); const t0 = last;
    const f = () => { const t = performance.now(); out.push(t - last); last = t; if (t - t0 < ms) requestAnimationFrame(f); else res(out.slice(1)); }; requestAnimationFrame(f); }); },
};
try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__ev.lcp.push({ t: e.startTime, size: e.size, el: e.element ? (e.element.className || e.element.tagName) : '' }); }).observe({ type: 'largest-contentful-paint', buffered: true }); } catch {}
try { new PerformanceObserver((l) => { for (const e of l.getEntries()) window.__ev.paint[e.name] = e.startTime; }).observe({ type: 'paint', buffered: true }); } catch {}
`;

const browser: Browser = await chromium.launch({
  executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--font-render-hinting=none'],
});
const evidence: Record<string, unknown> = {};
const problems: string[] = [];
const shots: { name: string; caption: string }[] = [];
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const r1 = (x: number) => Math.round(x * 10) / 10;
type Ev = { t: number; name: string; detail?: unknown };
const events = async (page: Page): Promise<Ev[]> => (await page.evaluate('window.__story.events')) as Ev[];
const at = (evs: Ev[], name: string): number | null => evs.find((e) => e.name === name)?.t ?? null;
const atLast = (evs: Ev[], name: string): number | null => [...evs].reverse().find((e) => e.name === name)?.t ?? null;

async function ctxOf(w: number, h: number, o: { reduced?: boolean; dpr?: number } = {}): Promise<BrowserContext> {
  const ctx = await browser.newContext({
    viewport: { width: w, height: h },
    deviceScaleFactor: o.dpr ?? 1,
    locale: 'he-IL',
    reducedMotion: o.reduced ? 'reduce' : 'no-preference',
    isMobile: w < 720,
    hasTouch: w < 720,
  });
  await ctx.addInitScript(HELPERS);
  return ctx;
}
async function open(ctx: BrowserContext, hash = '', path = NORDIC): Promise<Page> {
  const page = await ctx.newPage();
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() === 'error') problems.push(`console: ${m.text()}`);
  });
  await page.goto(`${ORIGIN}${path}${hash}`, { waitUntil: 'load' });
  return page;
}
async function shot(
  page: Page,
  name: string,
  caption: string,
  o: { full?: boolean; clip?: { x: number; y: number; width: number; height: number } } = {},
): Promise<Buffer> {
  const png = await page.screenshot({ fullPage: o.full ?? false, ...(o.clip ? { clip: o.clip } : {}) });
  writeFileSync(join(SHOTS, `${name}.png`), png);
  shots.push({ name, caption });
  return png;
}
const goTo = (page: Page, sel: string) => page.evaluate(`document.querySelector('${sel}').scrollIntoView({ behavior: 'instant', block: 'start' })`);
const settled = (page: Page, f = 'A') =>
  page.waitForFunction(`document.querySelector('#frame-${f}').classList.contains('is-title')`, null, { timeout: 20_000 });
/** a full-page screenshot loads every lazy picture first: a scroll to the end and back */
async function scrolled(page: Page): Promise<void> {
  await page.evaluate(
    `(async () => { for (let y = 0; y < document.body.scrollHeight; y += innerHeight / 2) { scrollTo(0, y); await new Promise((r) => setTimeout(r, 60)); } scrollTo(0, 0); })()`,
  );
  await page.waitForFunction(`[...document.images].every((i) => i.complete)`, null, { timeout: 15_000 });
  await sleep(300);
}

// ---------- colour maths: WCAG contrast of a text colour on the pixels under it ----------
const lum = (r: number, g: number, b: number): number => {
  const lin = (c: number) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
};
const contrast = (a: number, b: number) => (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
const rgb = (s: string): [number, number, number] => {
  const m = s.match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)/);
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : [0, 0, 0];
};
const pct = (xs: number[], p: number) => [...xs].sort((a, b) => a - b)[Math.min(xs.length - 1, Math.floor((p / 100) * xs.length))] ?? 0;
async function textOnPicture(page: Page, sel: string, band?: number): Promise<{ p5: number; min: number; text: string } | null> {
  const has = await page.evaluate(`!!document.querySelector('${sel}')`);
  if (!has) return null;
  const r0 = (await page.evaluate(`window.__ev.rect('${sel}')`)) as { x: number; y: number; w: number; h: number };
  // a label whose paper is a band of `band` px centred in its (taller) target: the text sits on that band
  const rect = band && r0.h > band ? { ...r0, y: r0.y + (r0.h - band) / 2, h: band } : r0;
  const col = rgb((await page.evaluate(`getComputedStyle(document.querySelector('${sel}')).color`)) as string);
  // the text alone is hidden (its colour and underline), so a label's own paper stays under it
  const hide = `document.querySelectorAll('${sel}, ${sel} *').forEach((e) => { e.style.setProperty('color', 'transparent', 'important'); e.style.setProperty('text-decoration-color', 'transparent', 'important'); })`;
  const show = `document.querySelectorAll('${sel}, ${sel} *').forEach((e) => { e.style.removeProperty('color'); e.style.removeProperty('text-decoration-color'); })`;
  await page.evaluate(hide);
  await sleep(60);
  const png = await page.screenshot();
  await page.evaluate(show);
  const { data, info } = await sharp(png).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const lt = lum(...col);
  const cs: number[] = [];
  for (let y = Math.max(0, Math.floor(rect.y)); y < Math.min(info.height, rect.y + rect.h); y++)
    for (let x = Math.max(0, Math.floor(rect.x)); x < Math.min(info.width, rect.x + rect.w); x++) {
      const i = (y * info.width + x) * 3;
      cs.push(contrast(lt, lum(data[i]!, data[i + 1]!, data[i + 2]!)));
    }
  return { p5: r1(pct(cs, 5) * 10) / 10, min: r1(Math.min(...cs) * 10) / 10, text: `rgb(${col.join(',')})` };
}
async function onPaper(page: Page, sel: string, prop = 'color', bgSel?: string): Promise<number | null> {
  const ok = await page.evaluate(`!!document.querySelector('${sel}')`);
  if (!ok) return null;
  const fg = rgb((await page.evaluate(`getComputedStyle(document.querySelector('${sel}')).${prop}`)) as string);
  const bg = rgb((await page.evaluate(`getComputedStyle(document.querySelector('${bgSel ?? 'body'}')).backgroundColor`)) as string);
  return r1(contrast(lum(...fg), lum(...bg)) * 10) / 10;
}

// ---------- the first load: the bytes the opening needs, as served (text gzip-compressed, media as is) ----------
async function firstLoad(w: number, h: number, dpr: number, tag: string, path = NORDIC): Promise<void> {
  const ctx = await ctxOf(w, h, { dpr });
  const page = await ctx.newPage();
  const got: { url: string; type: string; bytes: number; gz: number }[] = [];
  page.on('response', (res) => {
    const u = new URL(res.url());
    if (u.origin !== ORIGIN) return;
    let p = decodeURIComponent(u.pathname);
    if (p.endsWith('/')) p += 'index.html';
    const f = join(DIST, p);
    if (!existsSync(f) || statSync(f).isDirectory()) return;
    const bytes = statSync(f).size;
    const text = /\.(html|js|css|json|svg)$/.test(f);
    got.push({ url: p, type: extname(f).slice(1), bytes, gz: text ? gzipSync(readFileSync(f)).length : bytes });
  });
  const t0 = Date.now();
  await page.goto(`${ORIGIN}${path}`, { waitUntil: 'load' });
  if (path === NORDIC) await settled(page);
  await sleep(1500); // idle on the opening: what loads without a scroll
  const evs = await events(page);
  const paint = (await page.evaluate('window.__ev.paint')) as Record<string, number>;
  const lcp = (await page.evaluate('window.__ev.lcp')) as { t: number; el: string }[];
  const sum = (xs: typeof got) => xs.reduce((s, x) => s + x.gz, 0);
  const by = (re: RegExp) => got.filter((x) => re.test(x.url));
  evidence[`first_load_${tag}`] = {
    page: path,
    viewport: `${w}×${h} @${dpr}x`,
    total_kb: r1(sum(got) / 1024),
    html_kb: r1(sum(by(/\.html$/)) / 1024),
    js_kb: r1(sum(by(/\.js$/)) / 1024),
    css_kb: r1(sum(by(/\.css$/)) / 1024),
    fonts_kb: r1(sum(by(/\.woff2?$/)) / 1024),
    frames_kb: r1(sum(by(/\/media\/story\/(?!products\/).+\/m?\d+\.(avif|webp)$/)) / 1024),
    frame_files: by(/\/media\/story\/(?!products\/).+\/m?\d+\.(avif|webp)$/).map((x) => `${x.url} ${r1(x.bytes / 1024)} KB`),
    product_photos_kb: r1(sum(by(/\/media\/story\/products\//)) / 1024),
    product_photos: by(/\/media\/story\/products\//).length,
    requests: got.length,
    budget_kb: 3072,
    fcp_ms: Math.round(paint['first-contentful-paint'] ?? 0),
    lcp_ms: Math.round(lcp.at(-1)?.t ?? 0),
    lcp_el: lcp.at(-1)?.el ?? '',
    developed_ms: Math.round(at(evs, 'A:developed') ?? 0),
    title_ms: Math.round(at(evs, 'A:title') ?? 0),
    wall_ms: Date.now() - t0,
  };
  await ctx.close();
}

// the opening on a throttled phone (Fast-4G-like network, CPU ×4): when the LQIP, the frame and the title are there
async function throttledOpening(): Promise<void> {
  const ctx = await ctxOf(400, 800);
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', {
    offline: false,
    latency: 150,
    downloadThroughput: (4 * 1024 * 1024) / 8,
    uploadThroughput: (3 * 1024 * 1024) / 8,
  });
  await cdp.send('Emulation.setCPUThrottlingRate', { rate: 4 });
  await page.goto(`${ORIGIN}${NORDIC}`, { waitUntil: 'load' });
  await settled(page);
  await sleep(1000);
  const evs = await events(page);
  const paint = (await page.evaluate('window.__ev.paint')) as Record<string, number>;
  const lcp = (await page.evaluate('window.__ev.lcp')) as { t: number; el: string }[];
  evidence.opening_throttled_phone = {
    conditions: 'latency 150 ms, 4 Mbit/s down, CPU ×4, 400×800 @1x',
    fcp_ms: Math.round(paint['first-contentful-paint'] ?? 0),
    lcp_ms: Math.round(lcp.at(-1)?.t ?? 0),
    lcp_el: lcp.at(-1)?.el ?? '',
    lqip_ms: Math.round(at(evs, 'A:lqip') ?? 0),
    developed_ms: Math.round(at(evs, 'A:developed') ?? 0),
    title_ms: Math.round(at(evs, 'A:title') ?? 0),
    thresholds: 'art direction §8.1 / §10.9: LQIP ≤ 1.0 s, the frame sharp ≤ 2.0 s, LCP ≤ 2.5 s',
  };
  await ctx.close();
}

// ---------- one run per width: the screens and the timings ----------
async function run(w: number, h: number, tag: 'desk' | 'phone'): Promise<void> {
  const phone = tag === 'phone';
  const ctx = await ctxOf(w, h);
  // the contents
  const index = await open(ctx, '', '/story/');
  await sleep(900);
  await shot(index, `${tag}-0-contents`, `${w}: the contents (/story/): the living room's six houses, a frame only where QA let one in, type for the rest`);
  await scrolled(index);
  await shot(index, `${tag}-0b-contents-full`, `${w}: the whole contents, every room (the eight rooms without a pair: "בגיליונות הבאים")`, { full: true });
  const indexTiles = (await index.evaluate(
    `({ rooms: document.querySelectorAll('.st-room').length, next: document.querySelectorAll('.st-room.is-next').length, pictures: document.querySelectorAll('.st-tile-pic').length, typographic: document.querySelectorAll('.st-tile-type').length })`,
  )) as unknown;
  await index.close();
  const page = await open(ctx);
  await settled(page);
  await sleep(2400); // the first-entry hint has come and gone: the frame at rest
  await shot(page, `${tag}-1-opening`, `${w}: the Nordic living room, frame A at rest (no dot), the title and the story line, the test mark`);
  const restDots = (await page.evaluate(
    `[...document.querySelectorAll('#frame-A .mag-dot')].filter((d) => getComputedStyle(d).opacity !== '0').length`,
  )) as number;
  // the dots on movement (desktop) or on a touch (phone)
  const sel = '#frame-A .st-mark:not([hidden]) .mag-dot';
  const appear = page.evaluate(`window.__ev.firstChange('${sel}', 'opacity', 2000)`);
  const t0 = Date.now();
  if (phone) await page.touchscreen.tap(200, 200);
  else {
    await page.mouse.move(700, 430);
    await page.mouse.move(720, 440);
  }
  const appearMs = (await appear) as number | null;
  await sleep(320);
  await shot(
    page,
    `${tag}-2-dots`,
    `${w}: the dots after ${phone ? 'a touch' : 'the pointer moves'} (one per faithful product the ${phone ? '4:5 crop carries' : 'screen shows'})`,
  );
  const shown = (await page.evaluate(
    `[...document.querySelectorAll('#frame-A .st-mark')].filter((m) => m.offsetParent !== null && !m.hidden).map((m) => m.dataset.item)`,
  )) as string[];
  // gone 2.5 s after the last movement
  await page.waitForFunction(`document.querySelector('#frame-A .mag-stage').dataset.marks === 'off'`, null, { timeout: 8000 });
  const goneAfter = Date.now() - t0;
  // the sheet: a dot opens "קנה את המראה"
  const target = phone ? '#frame-A .st-mark[data-item="A-5"]' : '#frame-A .st-mark[data-item="A-6"]';
  const trans = page.evaluate(`window.__ev.transitions('#st-sheet', 900)`);
  // from the click's own time stamp to the first frame where the sheet is drawn (not Playwright's action overhead)
  const resp = page.evaluate(
    `new Promise((res) => { addEventListener('click', (e) => { const t0 = e.timeStamp; const f = () => { const d = document.querySelector('#st-sheet'); if (d.open && parseFloat(getComputedStyle(d).opacity) > 0) res(performance.now() - t0); else requestAnimationFrame(f); }; requestAnimationFrame(f); }, { capture: true, once: true }); })`,
  );
  if (phone) await page.locator(target).tap();
  else await page.locator(target).click();
  const respMs = (await resp) as number;
  const sheetTrans = (await trans) as [string, string, number][];
  await sleep(150);
  await shot(
    page,
    `${tag}-3-sheet`,
    `${w}: "קנה את המראה" from a dot: the card's photo, the name, the credit with the price, the action, the links and the browse`,
  );
  const focusOnName = (await page.evaluate(`document.activeElement && document.activeElement.id`)) as string;
  await page.locator('#st-add').click();
  await sleep(250);
  await shot(page, `${tag}-3b-added`, `${w}: after "הוספה לסל": the button says "נוסף לסל", the cart count in the top band is 1`);
  const count = (await page.evaluate(`document.querySelector('#st-cart-count').textContent`)) as string;
  const live = (await page.evaluate(`document.querySelector('#mag-live').textContent`)) as string;
  // contrast on the sheet (paper)
  const sheetContrast = {
    name: await onPaper(page, '#st-sheet-name', 'color', '#st-sheet'),
    detail: await onPaper(page, '#st-sheet-detail', 'color', '#st-sheet'),
    kicker: await onPaper(page, '#st-sheet-kicker', 'color', '#st-sheet'),
    caption: await onPaper(page, '#st-sheet-cap', 'color', '#st-sheet'),
    notes: await onPaper(page, '#st-sheet-notes', 'color', '#st-sheet'),
    link: await onPaper(page, '#st-try', 'color', '#st-sheet'),
    step: await onPaper(page, '#st-next', 'color', '#st-sheet'),
  };
  const closeTrans = page.evaluate(`window.__ev.transitions('#st-sheet', 600)`);
  await page.keyboard.press('Escape');
  await page.waitForFunction(`!document.querySelector('#st-sheet').open`, null, { timeout: 3000 });
  const closeT = (await closeTrans) as [string, string, number][];
  const backTo = (await page.evaluate(`document.activeElement && document.activeElement.dataset.item`)) as string;
  // an unpriced product (the pendant): a caption instead of the button
  await page.evaluate(`window.__story.openSheet('A-1')`);
  await sleep(350);
  await shot(page, `${tag}-3c-sheet-no-price`, `${w}: a product without a price yet (the pendant): the caption says so, no add button, no disabled button`);
  const why = (await page.evaluate(`document.querySelector('#st-why').textContent`)) as string;
  await page.evaluate(`window.__story.closeSheet()`);
  await sleep(300);
  // the list
  await goTo(page, '#list-A');
  await sleep(500);
  await shot(
    page,
    `${tag}-4-list`,
    `${w}: "כל המוצרים בתמונה" for Nordic A: the card photo or the colour swatch, the name (opens the sheet), the credit; the rug without a dot (QA: partly)`,
  );
  await scrolled(page);
  await shot(page, `${tag}-4b-list-full`, `${w}: the whole list section`, { full: true, clip: await sectionClip(page, '#list-A') });
  // the second frame, the tool entry and the other houses
  await goTo(page, '#frame-B');
  await page.waitForFunction(`document.querySelector('#frame-B').classList.contains('is-title')`, null, { timeout: 20_000 });
  await sleep(2200);
  await shot(page, `${tag}-5-second-frame`, `${w}: the story scroll, Nordic B (the window corner), at rest`);
  await goTo(page, '#tool');
  await sleep(500);
  await shot(page, `${tag}-6-tool`, `${w}: the way into the tool: "עצב בעצמך" opens the room engine (/rooms/living-room/)`);
  const toolHref = (await page.evaluate(`document.querySelector('#st-tool').getAttribute('href')`)) as string;
  await goTo(page, '#houses');
  await sleep(900);
  await shot(
    page,
    `${tag}-7-houses`,
    `${w}: "הסלון, בבתים אחרים": this house marked, three frames QA let in, three houses in type (their frames are still with QA)`,
  );
  // the cart dialog
  await page.locator('#st-cart-open').click();
  await sleep(350);
  await shot(page, `${tag}-9-cart`, `${w}: the test cart (an in-browser mock of the store API's cart)`);
  await page.keyboard.press('Escape');
  await sleep(250);
  const evs = await events(page);
  // the other houses: a cut to their own page
  const houses: Record<string, unknown> = {};
  for (const [path, name, caption] of [
    [WARM, `${tag}-8-warm-modern`, `${w}: warm modern, frame A (ED5, QA: final test), the draft mark`],
    [COUNTRY, `${tag}-8c-modern-country`, `${w}: modern country, frame A (MC1, QA: almost): the mark says "כמעט מוכן"`],
  ] as const) {
    await page.goto(`${ORIGIN}${path}`, { waitUntil: 'load' });
    await settled(page);
    await sleep(2400);
    await shot(page, name, caption);
    houses[path] = {
      mark: await page.evaluate(`document.querySelector('#frame-A .st-draft').textContent`),
      dots: await page.evaluate(`document.querySelectorAll('#frame-A .st-mark').length`),
      rows: await page.evaluate(`document.querySelectorAll('#list-A .st-credit').length`),
      no_dot_rows: await page.evaluate(`document.querySelectorAll('#list-A .st-no-dot').length`),
      cart_count_here: await page.evaluate(`document.querySelector('#st-cart-count').textContent`),
    };
    if (path === COUNTRY) {
      await goTo(page, '#list-A');
      await sleep(500);
      await shot(
        page,
        `${tag}-8d-modern-country-list`,
        `${w}: modern country's list: the clay vase and the bowl without a dot (QA: partly), the curtain as the option the frame shows`,
      );
    }
  }
  await page.goto(`${ORIGIN}${BOHO}`, { waitUntil: 'load' });
  await sleep(900);
  await shot(
    page,
    `${tag}-8e-boho-typographic`,
    `${w}: boho: QA has not let its frame in, so the page is type only: the concept, the story line, why there is no frame`,
  );
  await scrolled(page);
  await shot(page, `${tag}-8f-boho-full`, `${w}: the whole typographic page: the cover in type, the tool (the Nordic one, said so), the other houses`, {
    full: true,
  });
  houses[BOHO] = {
    stages: await page.evaluate(`document.querySelectorAll('.mag-stage').length`),
    images: await page.evaluate(`[...document.images].map((i) => i.currentSrc || i.src)`),
  };
  evidence[`run_${tag}`] = {
    contents: indexTiles,
    dots_visible_at_rest: restDots,
    dots_appear_ms: appearMs === null ? null : Math.round(appearMs),
    dots_shown: shown,
    dots_gone_after_ms: goneAfter,
    dots_hint: { on: at(evs, 'A:hint:on') !== null, off: at(evs, 'A:hint:off') !== null },
    sheet_response_ms: Math.round(respMs),
    sheet_in: sheetTrans,
    sheet_out: closeT,
    sheet_focus_on_open: focusOnName,
    focus_back_to: backTo,
    cart_count_after_add: count,
    live_region: live,
    no_price_caption: why,
    tool_href: toolHref,
    sheet_contrast_on_paper: sheetContrast,
    open_to_close_ms: Math.round((atLast(evs, 'sheet:close') ?? 0) - (at(evs, 'sheet:open:start') ?? 0)),
    other_houses: houses,
  };
  await ctx.close();
}
/** the whole section, in page coordinates (a full-page screenshot clipped to it) */
async function sectionClip(page: Page, sel: string): Promise<{ x: number; y: number; width: number; height: number }> {
  const r = (await page.evaluate(
    `(() => { const r = document.querySelector('${sel}').getBoundingClientRect(); return { y: r.y + scrollY, h: r.height, w: innerWidth }; })()`,
  )) as {
    y: number;
    h: number;
    w: number;
  };
  return { x: 0, y: Math.round(r.y), width: r.w, height: Math.round(r.h) };
}

// the keyboard: Tab from the top to the first dot, the dots show on focus, Enter, inside the sheet, Esc
async function keyboard(): Promise<void> {
  const ctx = await ctxOf(1280, 800);
  const page = await open(ctx);
  await settled(page);
  await sleep(2400);
  const stops: string[] = [];
  for (let i = 0; i < 12; i++) {
    await page.keyboard.press('Tab');
    const d = (await page.evaluate(
      `(() => { const a = document.activeElement; return a ? (a.dataset.item || a.id || a.textContent.trim().slice(0, 24)) : ''; })()`,
    )) as string;
    stops.push(d);
    if (/^A-\d+$/.test(d)) break;
  }
  await sleep(300);
  await shot(page, 'desk-k1-dot-focus', '1280: a dot in keyboard focus: every dot shows, the focused one has the double ring, the wall label says its credit');
  const ring = (await page.evaluate(
    `(() => { const cs = getComputedStyle(document.activeElement); return { outline: cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor, shadow: cs.boxShadow }; })()`,
  )) as unknown;
  await page.keyboard.press('Enter');
  await sleep(400);
  const inside: boolean[] = [];
  for (let i = 0; i < 10; i++) {
    await page.keyboard.press('Tab');
    inside.push(
      (await page.evaluate(`!document.activeElement || document.activeElement === document.body || !!document.activeElement.closest('#st-sheet')`)) as boolean,
    );
  }
  await page.locator('#st-add:visible, #st-next').first().focus();
  await sleep(100);
  await shot(page, 'desk-k2-sheet-focus', '1280: inside the sheet by keyboard (the page behind is inert)');
  await page.keyboard.press('Escape');
  await sleep(400);
  const back = (await page.evaluate(`document.activeElement && document.activeElement.dataset.item`)) as string;
  evidence.keyboard_1280 = { tab_stops_to_first_dot: stops, ring, tab_stays_in_sheet: inside.every(Boolean), esc_returns_to: back };
  await ctx.close();
}

// every dot on screen takes its own click (elementFromPoint at its centre), each frame at its start, 1280 and 1440;
// a dot under the top band would hand the click to the band (QA 2026-11-07, Nordic A's pendant)
async function hitTest(): Promise<void> {
  const out: Record<string, unknown> = {};
  for (const [w, h] of [
    [1280, 800],
    [1440, 900],
  ] as const) {
    const ctx = await ctxOf(w, h);
    const page = await open(ctx);
    await settled(page);
    for (const [path, f] of FRAMES) {
      if (!page.url().endsWith(path)) {
        await page.goto(`${ORIGIN}${path}`, { waitUntil: 'load' });
        await settled(page);
      }
      await goTo(page, `#frame-${f}`);
      await sleep(700);
      await page.evaluate(`window.__story.showMarks('${f}')`);
      await sleep(350);
      const hits = (await page.evaluate(
        `[...document.querySelectorAll('#frame-${f} .st-mark')].filter((m) => !m.hidden).map((m) => { const r = m.getBoundingClientRect(); const x = r.x + r.width / 2; const y = r.y + r.height / 2; const at = document.elementFromPoint(x, y); const d = at && at.closest('.st-mark'); return { item: m.dataset.item, y: Math.round(y), hit: d ? d.dataset.item : (at ? at.tagName + (at.id ? '#' + at.id : '') : null) }; })`,
      )) as { item: string; y: number; hit: string }[];
      const hidden = (await page.evaluate(
        `[...document.querySelectorAll('#frame-${f} .st-mark')].filter((m) => m.hidden).map((m) => m.dataset.item)`,
      )) as string[];
      out[`${w} ${path} ${f}`] = {
        shown: hits.length,
        missed: hits.filter((x) => x.hit !== x.item),
        hidden_by_crop_or_band: hidden,
        pendant: hits.find((x) => /-(1|2)$/.test(x.item) && x.y < 140) ?? null,
      };
      if (hits.some((x) => x.hit !== x.item))
        problems.push(`${w} ${path} ${f}: a dot does not take its click: ${JSON.stringify(hits.filter((x) => x.hit !== x.item))}`);
    }
    if (w === 1280) {
      await page.goto(`${ORIGIN}${NORDIC}`, { waitUntil: 'load' });
      await settled(page);
      await sleep(600);
      await page.evaluate(`window.__story.showMarks('A')`);
      await sleep(350);
      await shot(
        page,
        'desk-2b-pendant-dot',
        "1280: Nordic A, v0 0.10: the pendant's dot at the bottom of the shade, clear of the top band; the band's words on the label paper, the 0.35 scrim",
      );
      for (const [path, name, caption] of [
        [
          WARM,
          'desk-8b-warm-modern-dots',
          '1280: warm modern A ed5 (QA: final test), the dots: the right bouclé cushion now sells the square 50×50 milk-tea option (QA round 2, G-ED.4)',
        ],
        [COUNTRY, 'desk-8g-modern-country-dots', '1280: modern country A mc1 (QA: almost), the dots: five, none on the clay vase and the bowl (QA: partly)'],
      ] as const) {
        await page.goto(`${ORIGIN}${path}`, { waitUntil: 'load' });
        await settled(page);
        await sleep(700);
        await page.evaluate(`window.__story.showMarks('A')`);
        await sleep(350);
        await shot(page, name, caption);
      }
    }
    await ctx.close();
  }
  // the phone: Nordic B's throw on its hand-placed dot (the fold, not the armchair's seat), and warm modern ed5
  const ctx = await ctxOf(400, 800);
  const page = await open(ctx);
  await settled(page);
  for (const [path, f, name, caption] of [
    [
      NORDIC,
      'B',
      'phone-5b-nordic-B-dots',
      "400: Nordic B in the 4:5 crop at 0.62, the dots shown: the throw's dot on the fold (placed by hand), the vase, the holder, the rug",
    ],
    [WARM, 'A', 'phone-8b-warm-modern-dots', '400: warm modern A ed5 in the 4:5 crop at 0.56, the dots shown'],
    [
      COUNTRY,
      'A',
      'phone-8g-modern-country-dots',
      '400: modern country A mc1 in the 4:5 crop at 0.52, the dots shown (the fluted vase is outside the crop: listed only)',
    ],
  ] as const) {
    if (!page.url().endsWith(path)) {
      await page.goto(`${ORIGIN}${path}`, { waitUntil: 'load' });
      await settled(page);
    }
    await goTo(page, `#frame-${f}`);
    await sleep(700);
    await page.evaluate(`window.__story.showMarks('${f}')`);
    await sleep(350);
    await shot(page, name, caption);
  }
  await ctx.close();
  evidence.hit_test = out;
}

// reduced motion: the sheet fades, nothing rises; the title lines do not move
async function reduced(): Promise<void> {
  for (const [w, h, tag] of [
    [1280, 800, 'desk'],
    [400, 800, 'phone'],
  ] as const) {
    const ctx = await ctxOf(w, h, { reduced: true });
    const page = await open(ctx);
    await settled(page);
    const trans = page.evaluate(`window.__ev.transitions('#st-sheet', 700)`);
    await page.evaluate(`window.__story.openSheet('A-9')`);
    const t = (await trans) as [string, string, number][];
    await sleep(100);
    await shot(page, `${tag}-r1-reduced-sheet`, `${w}: reduced motion, the sheet open (a fade only)`);
    evidence[`reduced_${tag}`] = {
      sheet_transitions: t,
      sheet_transform: await page.evaluate(`getComputedStyle(document.querySelector('#st-sheet')).transform`),
      title_transform: await page.evaluate(`getComputedStyle(document.querySelector('#frame-A .st-title-line')).transform`),
      lqip_display: await page.evaluate(`getComputedStyle(document.querySelector('#frame-A .mag-lqip')).display`),
    };
    await ctx.close();
  }
}

// contrast: the text over the frames (desktop), the top band over each frame, the paper sections
async function contrastRun(w: number, h: number, tag: string): Promise<void> {
  const ctx = await ctxOf(w, h);
  const page = await open(ctx);
  await settled(page);
  await sleep(2400);
  const over: Record<string, unknown> = {};
  for (const [path, f] of FRAMES) {
    if (!page.url().endsWith(path)) {
      await page.goto(`${ORIGIN}${path}`, { waitUntil: 'load' });
      await settled(page);
    }
    await goTo(page, `#frame-${f}`);
    await page.waitForFunction(`document.querySelector('#frame-${f}').classList.contains('is-title')`, null, { timeout: 20_000 });
    await sleep(2300);
    const k = `${path.split('/')[3]} ${f}`;
    for (const part of ['.st-kicker', '.st-title', '.st-line', '.st-link', '.st-draft'])
      over[`${k} ${part}`] = await textOnPicture(page, `#frame-${f} ${part}`);
    over[`${k} top band (brand)`] = await textOnPicture(page, '#mag-head .mag-brand', 30);
    over[`${k} top band (nav: תוכן)`] = await textOnPicture(page, '#mag-head .st-nav > a', 30);
    over[`${k} top band (nav: עצב בעצמך)`] = await textOnPicture(page, '#mag-head .st-nav > a:nth-of-type(2)', 30);
    over[`${k} top band (nav: סל)`] = await textOnPicture(page, '#st-cart-open', 30);
  }
  await page.goto(`${ORIGIN}${NORDIC}#list-A`, { waitUntil: 'load' });
  await sleep(600);
  const paper = {
    'list h2': await onPaper(page, '#list-title-A', 'color', '#list-A'),
    'list name': await onPaper(page, '#list-A .mag-credit-name', 'color', '#list-A'),
    'list detail': await onPaper(page, '#list-A .mag-credit-detail', 'color', '#list-A'),
    'list caption': await onPaper(page, '#list-A .mag-cap', 'color', '#list-A'),
    'no-dot caption': await onPaper(page, '#list-A .st-no-dot', 'color', '#list-A'),
    'list name underline (3:1)': await onPaper(page, '#list-A .st-open .mag-credit-name', 'textDecorationColor', '#list-A'),
    'tool button text on its ink': await (async () => {
      const fg = rgb((await page.evaluate(`getComputedStyle(document.querySelector('#st-tool')).color`)) as string);
      const bg = rgb((await page.evaluate(`getComputedStyle(document.querySelector('#st-tool')).backgroundColor`)) as string);
      return r1(contrast(lum(...fg), lum(...bg)) * 10) / 10;
    })(),
    'houses caption': await onPaper(page, '#houses .st-tile .mag-cap', 'color', '#houses'),
    'houses style': await onPaper(page, '#houses .st-tile-style', 'color', '#houses'),
    'houses typographic tile title (on the second paper)': await onPaper(page, '#houses .st-tile-type .st-tile-title', 'color', '#houses .st-tile-type'),
  };
  await page.goto(`${ORIGIN}/story/`, { waitUntil: 'load' });
  await sleep(600);
  Object.assign(paper, {
    'contents room name': await onPaper(page, '#room-living-room .st-room-name', 'color', '#contents'),
    'contents room number': await onPaper(page, '#room-living-room .st-room-n', 'color', '#contents'),
    'contents next room (ink-2)': await onPaper(page, '.st-room.is-next .st-room-name', 'color', '#contents'),
    'contents next caption': await onPaper(page, '.st-room.is-next .mag-cap', 'color', '#contents'),
  });
  await page.goto(`${ORIGIN}${BOHO}`, { waitUntil: 'load' });
  await sleep(600);
  Object.assign(paper, {
    'typographic title': await onPaper(page, '#cover-title', 'color', '#cover'),
    'typographic status': await onPaper(page, '.st-type-status', 'color', '#cover'),
    'secondary button text': await onPaper(page, '#st-tool', 'color', '#tool'),
  });
  evidence[`contrast_${tag}`] = {
    text_over_frames_p5: over,
    on_paper: paper,
    rule: 'text ≥ 4.5:1 (large ≥ 3:1), measured at the 5th percentile of the pixels under the text, the text hidden',
  };
  await ctx.close();
}

// axe (WCAG 2.0/2.1 A + AA): the Nordic page at rest, the sheet open, the cart open; every other kind of page at rest;
// 1280 and 400
async function axe(): Promise<void> {
  const out: Record<string, string[]> = {};
  for (const [w, h] of [
    [1280, 800],
    [400, 800],
  ] as const) {
    const ctx = await ctxOf(w, h);
    const page = await open(ctx);
    const a = async (label: string) => {
      const r = await new AxeBuilder({ page } as unknown as ConstructorParameters<typeof AxeBuilder>[0])
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
        .analyze();
      out[`${w} ${label}`] = r.violations.map((v) => `${v.id} (${v.impact}): ${v.nodes.length} × ${v.nodes[0]?.target.join(' ')}`);
      if (r.violations.length) problems.push(`axe ${w} ${label}: ${out[`${w} ${label}`]!.join('; ')}`);
    };
    await settled(page);
    await sleep(1200); // the title lines and the brand have finished fading in
    await a(`${NORDIC} at rest`);
    await page.evaluate(`window.__story.openSheet('A-5')`);
    await sleep(400);
    await a(`${NORDIC} sheet open`);
    await page.evaluate(`window.__story.closeSheet()`);
    await sleep(300);
    await page.locator('#st-cart-open').click();
    await sleep(400);
    await a(`${NORDIC} cart open`);
    for (const path of ['/story/', WARM, COUNTRY, BOHO]) {
      await page.goto(`${ORIGIN}${path}`, { waitUntil: 'load' });
      if (path === WARM || path === COUNTRY) await settled(page);
      await sleep(1200);
      await a(`${path} at rest`);
    }
    await ctx.close();
  }
  evidence.axe = out;
}

// the real routes never carry the story frames: no file of dist outside story/ and test/ references them, and only the
// story pages load the story's own code
function realRoutes(): void {
  const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
  const storyPage = (f: string) => /^(story|test)\//.test(relative(DIST, f));
  const files = walk(DIST).filter((f) => /\.(html|js|css|json|xml|txt)$/.test(f) && !storyPage(f) && !relative(DIST, f).startsWith('assets/story-'));
  const hits = files
    .filter((f) =>
      /media\/story|media\/test\/story|editorial-phase-b|nordic-A-ed4|warm-modern-A-ed[45]|nordic-B-fin|modern-country-A-mc1/.test(readFileSync(f, 'utf8')),
    )
    .map((f) => relative(DIST, f));
  // the story entry's own assets are referenced only by the story pages
  const storyAssets = readdirSync(join(DIST, 'assets')).filter((f) => f.startsWith('story-'));
  const pagesRefStory = walk(DIST)
    .filter((f) => f.endsWith('.html') && !storyPage(f))
    .filter((f) => storyAssets.some((a) => readFileSync(f, 'utf8').includes(a)))
    .map((f) => relative(DIST, f));
  const sitemap = existsSync(join(DIST, 'sitemap.xml')) ? readFileSync(join(DIST, 'sitemap.xml'), 'utf8') : '';
  const storyPages = walk(join(DIST, 'story')).filter((f) => f.endsWith('index.html'));
  evidence.real_routes = {
    story_pages_in_this_build: storyPages.map((f) => `/${relative(DIST, dirname(f))}/`),
    files_referencing_story_media: hits,
    pages_loading_story_assets: pagesRefStory,
    sitemap_lists_story_or_test: /\/(story|test)\//.test(sitemap),
    every_story_page_noindex: storyPages.every((f) => /<meta name="robots" content="noindex, nofollow"/.test(readFileSync(f, 'utf8'))),
  };
  if (hits.length || pagesRefStory.length) problems.push(`the story leaks into real routes: ${[...hits, ...pagesRefStory].join(', ')}`);
}

// the public build (HD_PUBLIC=1): the client bundle into a scratch folder; it must hold no story, no test page and none
// of their media, and no file of it may name them
function publicBuild(): void {
  const dir = sitePath('.generated/public-check');
  rmSync(dir, { recursive: true, force: true });
  const t = Date.now();
  execFileSync('npx', ['vite', 'build', '--outDir', dir, '--emptyOutDir'], { cwd: sitePath('web'), env: { ...process.env, HD_PUBLIC: '1' }, stdio: 'pipe' });
  const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
  const all = walk(dir).map((f) => relative(dir, f));
  const leftovers = all.filter((f) => /^(story|test|media\/story|media\/test)\//.test(f) || /^assets\/(story|test)-/.test(f));
  const naming = all
    .filter((f) => /\.(html|js|css|json|xml|txt)$/.test(f))
    .filter((f) => /\/story\/|media\/story|media\/test|test\/story/.test(readFileSync(join(dir, f), 'utf8')))
    .slice(0, 20);
  evidence.public_build = {
    command: 'HD_PUBLIC=1 vite build --outDir .generated/public-check (the client bundle; the prerender adds only the real routes)',
    seconds: Math.round((Date.now() - t) / 1000),
    files: all.length,
    story_or_test_files: leftovers,
    files_naming_story_or_test: naming,
  };
  if (leftovers.length || naming.length) problems.push(`the public build carries the story or the test page: ${[...leftovers, ...naming].join(', ')}`);
  rmSync(dir, { recursive: true, force: true });
}

const t0 = Date.now();
realRoutes();
publicBuild();
await firstLoad(400, 800, 1, 'phone_400_dpr1');
await firstLoad(400, 800, 3, 'phone_400_dpr3');
await firstLoad(1280, 800, 1, 'desk_1280_dpr1');
await firstLoad(400, 800, 1, 'contents_phone_400_dpr1', '/story/');
await firstLoad(1280, 800, 1, 'contents_desk_1280_dpr1', '/story/');
await firstLoad(400, 800, 1, 'typographic_phone_400_dpr1', BOHO);
await throttledOpening();
await run(1280, 800, 'desk');
await run(400, 800, 'phone');
await keyboard();
await reduced();
await hitTest();
await contrastRun(1280, 800, '1280');
await contrastRun(400, 800, '400');
await axe();
await browser.close();
server.close();

evidence.problems = problems;
evidence.shots = shots;
evidence.run = { at: new Date().toISOString(), seconds: Math.round((Date.now() - t0) / 1000), browser: 'Chromium headless, SwiftShader' };
writeFileSync(join(OUT, 'evidence.json'), JSON.stringify(evidence, null, 1));
writeFileSync(
  join(OUT, 'evidence.md'),
  [
    '# Evidence of layer 1, the story (measured headless, Chromium + SwiftShader)',
    '',
    `Run ${(evidence.run as { at: string }).at}; ${shots.length} screenshots under screens/. The figures are in evidence.json; README.md reads them.`,
    '',
    '## Screenshots',
    ...shots.map((s) => `- \`screens/${s.name}.png\`: ${s.caption}`),
    '',
    '## Problems',
    ...(problems.length ? problems.map((p) => `- ${p}`) : ['- none (no page errors, no console errors)']),
    '',
  ].join('\n'),
);
console.log(`evidence → ${OUT} (${shots.length} screenshots, ${problems.length} problems, ${Math.round((Date.now() - t0) / 1000)} s)`);
if (problems.length) process.exitCode = 1;
