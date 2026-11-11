/**
 * qa-agent, 2026-11-11 (ת29 at a8104956): a direct entry to the warm-modern house (/rooms/living-room/?style=warm-modern),
 * what the browser paints from the very first frame, with JavaScript on (CDP screencast from before navigation, every
 * frame) and off, on a desktop and two phones, and once on a throttled network. No pointer, no touch, no focus.
 *
 * For each painted frame, the sofa's cushion area (the house's swap rectangle, through the poster's cover fit) is compared
 * with two references painted by the same browser in the same layout: the poster answered with the approved set-B
 * composite (lossless PNG), and with the base without the set (the empty sofa of S11–S12). A frame is "B" when it is
 * much closer to B, "empty" when closer to the base, "blank" when the area is flat paper. Also: every media request in
 * the first 8 s (any Nordic file, any base shell?), and the page's HTML (poster in it, no house-pending).
 *
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_REPO=<copy root> QA_OUT=<qa folder> node first-paint.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const COPY = process.env.QA_COPY;
const REPO = process.env.QA_REPO;
const OUT = process.env.QA_OUT;
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');

const wm = JSON.parse(readFileSync(join(COPY, 'tools/house/living-room.warm-modern.json'), 'utf8'));
const house = JSON.parse(readFileSync(join(COPY, '.generated/house.living-room.warm-modern.json'), 'utf8'));
const RECT = house.scene.slots.cushions.product.rect; // u0,u1,v0,v1 of the frame
const def = house.sets.find((s) => s.position === 1)?.id ?? 'B';
const B_SRC = join(REPO, wm.pilot, wm.approved.composites[def]);
const BASE_SRC = join(REPO, wm.pilot, wm.layers_dir, 'base.png');
const URL_WM = '/rooms/living-room/?style=warm-modern';
const POSTER_RE = /\/media\/house\/living-room\/warm-modern\/M0\/poster\/default\.(\d+)\.(avif|webp)$/;
const png = async (src, w) => sharp(src).removeAlpha().resize({ width: w }).png({ compressionLevel: 1 }).toBuffer();

const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'],
});

async function ctxFor(v, js = true) {
  const ctx = await browser.newContext({
    locale: 'he-IL',
    viewport: { width: v.w, height: v.h },
    deviceScaleFactor: v.dpr,
    isMobile: v.dpr > 1,
    hasTouch: v.dpr > 1,
    javaScriptEnabled: js,
    extraHTTPHeaders: { 'cf-connecting-ip': '203.0.113.231' },
  });
  ctx.setDefaultTimeout(120000);
  return ctx;
}
/** the cushion rectangle in CSS px of the viewport, from the poster's box and its cover fit */
async function region(p) {
  return p.evaluate((R) => {
    const i = document.querySelector('img.poster');
    if (!i) return null;
    const b = i.getBoundingClientRect();
    const cs = getComputedStyle(i);
    const nw = i.naturalWidth || 16;
    const nh = i.naturalHeight || 9;
    const s = cs.objectFit === 'cover' ? Math.max(b.width / nw, b.height / nh) : Math.min(b.width / nw, b.height / nh);
    const dw = nw * s;
    const dh = nh * s;
    const [px, py] = cs.objectPosition.split(' ').map((t) => (t.endsWith('%') ? parseFloat(t) / 100 : 0.5));
    const ox = b.left + (b.width - dw) * px;
    const oy = b.top + (b.height - dh) * py;
    const x0 = Math.max(b.left, ox + R[0] * dw), x1 = Math.min(b.right, ox + R[1] * dw);
    const y0 = Math.max(b.top, oy + R[2] * dh), y1 = Math.min(b.bottom, oy + R[3] * dh);
    return { x0, x1, y0, y1, box: [b.left, b.top, b.width, b.height], fit: cs.objectFit, pos: cs.objectPosition, src: i.currentSrc || i.src };
  }, RECT);
}
/** RGB of a viewport image's region, resampled to the region's CSS size */
async function crop(buf, r, cssW) {
  const meta = await sharp(buf).metadata();
  const k = meta.width / cssW;
  const left = Math.max(0, Math.round(r.x0 * k)), top = Math.max(0, Math.round(r.y0 * k));
  const width = Math.min(meta.width - left, Math.round((r.x1 - r.x0) * k)), height = Math.min(meta.height - top, Math.round((r.y1 - r.y0) * k));
  const w = Math.max(8, Math.round(r.x1 - r.x0)), h = Math.max(8, Math.round(r.y1 - r.y0));
  const { data } = await sharp(buf).removeAlpha().extract({ left, top, width, height }).resize(w, h, { fit: 'fill' }).raw().toBuffer({ resolveWithObject: true });
  return data;
}
const mad = (a, b) => {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += Math.abs(a[i] - b[i]);
  return s / a.length;
};
const sd = (a) => {
  let m = 0;
  for (const x of a) m += x;
  m /= a.length;
  let v = 0;
  for (const x of a) v += (x - m) ** 2;
  return Math.sqrt(v / a.length);
};

/** a reference shot: the page with the poster answered by a lossless PNG of `src`, the stage UI hidden */
async function refShot(v, src, js = true) {
  const ctx = await ctxFor(v, js);
  const p = await ctx.newPage();
  await p.route(POSTER_RE, async (route) => {
    const m = POSTER_RE.exec(new URL(route.request().url()).pathname);
    await route.fulfill({ status: 200, contentType: 'image/png', body: await png(src, Number(m[1])), headers: { 'cache-control': 'no-store' } });
  });
  await p.goto(`${BASE}${URL_WM}`, { waitUntil: 'load' });
  if (js)
    await p.waitForFunction(() => {
      const i = document.querySelector('img.poster');
      return i && i.complete && i.naturalWidth > 0;
    });
  await p.waitForTimeout(js ? 500 : 1500);
  const r = await region(p);
  const shot = await p.screenshot();
  await ctx.close();
  return { r, shot };
}

const VIEWS = [
  { id: '1280@1', w: 1280, h: 720, dpr: 1 },
  { id: '400@1', w: 400, h: 800, dpr: 1 },
  { id: '390@3', w: 390, h: 844, dpr: 3 },
];
const res = { base: BASE, url: URL_WM, refs: { B: B_SRC.replace(REPO, ''), empty: BASE_SRC.replace(REPO, '') }, html: null, runs: [] };

// the page's HTML as the Worker serves it
{
  const html = await (await fetch(`${BASE}${URL_WM}`, { headers: { 'cf-connecting-ip': '203.0.113.232' } })).text();
  const img = /<img[^>]*class="[^"]*poster[^"]*"[^>]*>/.exec(html)?.[0] ?? null;
  res.html = {
    poster_tag: img,
    srcset_poster_default: /poster\/default\./.test(img ?? ''),
    house_pending: /house-pending/.test(html),
    nordic_refs: (html.match(/\/media\/rooms\/living-room\/nordic\/[^"' )]+/g) ?? []).slice(0, 5),
    base_shell_refs: (html.match(/warm-modern\/M0\/base\/shell[^"' )]+/g) ?? []).slice(0, 5),
    title: /<title>([^<]*)<\/title>/.exec(html)?.[1] ?? null,
  };
  console.log('html', JSON.stringify(res.html));
}

for (const v of VIEWS) {
  const cssW = v.w;
  const refs = {};
  for (const js of [true, false]) {
    const rb = await refShot(v, B_SRC, js);
    const re = await refShot(v, BASE_SRC, js);
    refs[js] = { bB: await crop(rb.shot, rb.r, cssW), bE: await crop(re.shot, re.r, cssW), r: rb.r };
  }
  for (const mode of ['js', 'nojs', ...(v.id === '390@3' ? ['js-throttled'] : [])]) {
    const { bB, bE } = refs[mode !== 'nojs'];
    const sep = mad(bB, bE);
    const ctx = await ctxFor(v, mode !== 'nojs');
    const p = await ctx.newPage();
    const media = [];
    p.on('request', (rq) => {
      const u = new URL(rq.url());
      if (u.pathname.startsWith('/media/')) media.push({ t: Date.now(), path: u.pathname });
    });
    const frames = [];
    let cdp = null;
    if (mode !== 'nojs') {
      cdp = await ctx.newCDPSession(p);
      if (mode === 'js-throttled') {
        await cdp.send('Network.enable');
        await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
      }
      cdp.on('Page.screencastFrame', async (f) => {
        frames.push({ t: Date.now(), data: Buffer.from(f.data, 'base64') });
        try {
          await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId });
        } catch {
          /* closed */
        }
      });
      await cdp.send('Page.startScreencast', { format: 'png', everyNthFrame: 1, maxWidth: v.w * v.dpr, maxHeight: v.h * v.dpr });
    }
    const t0 = Date.now();
    await p.goto(`${BASE}${URL_WM}`, { waitUntil: 'load' });
    await p.waitForTimeout(mode === 'js-throttled' ? 9000 : 6000);
    const r = await region(p);
    const engine = mode === 'nojs' ? false : await p.evaluate(() => !!window.__hdEngine);
    const canvasOpacity = mode === 'nojs' ? null : await p.evaluate(() => (document.querySelector('canvas.room-canvas') ? getComputedStyle(document.querySelector('canvas.room-canvas')).opacity : 'none'));
    const last = await p.screenshot();
    if (cdp) await cdp.send('Page.stopScreencast').catch(() => undefined);
    const classify = async (buf) => {
      const c = await crop(buf, r, cssW);
      const dB = mad(c, bB);
      const dE = mad(c, bE);
      if (sd(c) < 4) return { k: 'blank', dB: +dB.toFixed(2), dE: +dE.toFixed(2) };
      return { k: dB < dE * 0.5 ? 'B' : dE < dB * 0.5 ? 'empty' : 'other', dB: +dB.toFixed(2), dE: +dE.toFixed(2) };
    };
    const seq = [];
    let savedOther = false;
    for (const f of frames) {
      const c = await classify(f.data);
      seq.push({ ms: f.t - t0, ...c });
      if (c.k === 'other' && !savedOther) {
        savedOther = true;
        await sharp(f.data).jpeg({ quality: 80 }).toFile(join(OUT, 'overlays', `t29-${mode}-${v.id.replace('@', 'x')}-first-other-${f.t - t0}ms.jpg`));
      }
    }
    const fin = await classify(last);
    const firstImage = seq.find((s) => s.k !== 'blank') ?? null;
    const row = {
      view: v.id,
      mode,
      separation_B_vs_empty: +sep.toFixed(2),
      frames: seq.length,
      kinds: seq.reduce((a, s) => ((a[s.k] = (a[s.k] ?? 0) + 1), a), {}),
      first_non_blank: firstImage,
      first_B_ms: seq.find((x) => x.k === 'B')?.ms ?? null,
      dark_or_other_ms: seq.filter((x) => x.k === 'other').map((x) => x.ms),
      any_empty: seq.some((s) => s.k === 'empty') || fin.k === 'empty',
      final: fin,
      poster_src: r?.src?.split('/').slice(-1)[0] ?? null,
      engine_started: engine,
      canvas_opacity: canvasOpacity,
      media: [...new Set(media.map((m) => m.path))],
      nordic_requests: media.filter((m) => m.path.includes('/rooms/living-room/nordic/')).length,
      base_requests: media.filter((m) => /\/M0\/base\//.test(m.path)).map((m) => m.path.split('/').slice(-1)[0]),
    };
    res.runs.push(row);
    await sharp(last).jpeg({ quality: 82 }).toFile(join(OUT, 'overlays', `t29-${mode}-${v.id.replace('@', 'x')}.jpg`));
    console.log('run', v.id, mode, JSON.stringify({ ...row, media: row.media.length }));
    await ctx.close();
  }
}
await browser.close();
writeFileSync(join(OUT, 'data/first-paint.json'), JSON.stringify(res, null, 1));
