/**
 * qa-agent, 2026-11-10 (S8-S10): the warm-modern house in the room engine, in Chromium, on the isolated copy of b0a71cd2.
 * Written for this round; it imports nothing from the site's tests.
 *  1. the wheel: the order of the sets (labels and radios), the default (the engine's selection, aria-checked), the
 *     arrow keys (RTL), at 1280×720 and 400×800
 *  2. the set panel: per set, the pieces, their names, options, prices and buttons; PRE1 on the Oatmeal 50×50
 *  3. the swap-diff, my own: every pair of sets (B↔A, A↔C, B↔C), screenshots of the stage after an instant swap, and the
 *     changed pixels counted outside the union of both sets' footprint (layer alpha > 0, or shadow < 255 in any channel),
 *     projected with the engine's camera; at dilation 0, 1 and 3 device px, at 1280×720, 1920×1080, 400×800 @1 and 390×844 @3
 *  4. the house switch: rAF samples of the canvas and poster boxes and transforms, the page's own timestamps
 *     (__hdHouseSwitch), and a CDP screencast of the stage to time the dissolve from what is painted (1 % to 99 % of the
 *     change), at full and reduced motion
 *  5. the old draft address (301 and its target), and every link from the warm-modern story into the tool
 *  6. entering at ?style=warm-modern: what is fetched (the Nordic poster?), and what the stage shows before the house
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node house-browser.mjs
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const COPY = process.env.QA_COPY;
const require = createRequire(join(COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const OV = join(OUT, 'overlays');
const house = JSON.parse(readFileSync(join(COPY, '.generated/house.living-room.warm-modern.json'), 'utf8'));
const HOUSE = '/rooms/living-room/?style=warm-modern';
const SLOT = house.room.slots[0].id;
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'],
});
const res = { base: BASE, run_at: new Date().toISOString() };
const ctxOf = (w, h, o = {}) =>
  browser.newContext({ locale: 'he-IL', viewport: { width: w, height: h }, deviceScaleFactor: o.dpr ?? 1, isMobile: !!o.mobile, hasTouch: !!o.mobile, reducedMotion: o.reduced ? 'reduce' : 'no-preference', extraHTTPHeaders: { 'cf-connecting-ip': '203.0.113.82' } });
const engine = (p) => p.evaluate(() => { const e = window.__hdEngine; return e ? { ready: e.ready, cam: { ...e.cam }, vp: { ...e.vp }, sel: e.getSelection(), compWidth: e.compWidth } : null; });
async function ready(p, url = HOUSE) {
  await p.goto(BASE + url, { waitUntil: 'load' });
  await p.locator('section.stage[data-house="warm-modern"]').waitFor({ timeout: 20000 });
  await p.locator(`button.hotspot[data-slot="${SLOT}"]`).waitFor({ state: 'attached', timeout: 20000 });
  const box = await p.locator('section.stage').boundingBox();
  await p.mouse.click(box.x + 20, box.y + box.height / 2);
  for (let i = 0; i < 80; i++) { const e = await engine(p); if (e?.ready) return e; await p.waitForTimeout(250); }
  throw new Error('engine not ready');
}

// ---------- 1 + 2: the wheel and the set panel ----------
res.wheel = [];
for (const [w, h] of [[1280, 720], [400, 800]]) {
  const ctx = await ctxOf(w, h);
  const p = await ctx.newPage();
  const e0 = await ready(p);
  const r = { viewport: `${w}x${h}`, default_selection: e0.sel, sets: [] };
  await p.locator(`button.hotspot[data-slot="${SLOT}"]`).focus();
  await p.keyboard.press('Enter');
  const dialog = p.getByRole('dialog');
  await dialog.waitFor({ timeout: 15000 });
  await p.waitForTimeout(600);
  const radios = dialog.getByRole('radio');
  r.radio_labels = await radios.evaluateAll((els) => els.map((e) => e.getAttribute('aria-label')));
  r.checked_on_open = await radios.evaluateAll((els) => els.findIndex((e) => e.getAttribute('aria-checked') === 'true') + 1);
  for (let i = 0; i < 3; i++) {
    if (i > 0) { await p.keyboard.press('ArrowLeft'); await p.waitForTimeout(900); }
    const s = await dialog.evaluate((d) => ({
      checked: [...d.querySelectorAll('[role="radio"]')].findIndex((e) => e.getAttribute('aria-checked') === 'true') + 1,
      label: d.querySelector('[role="radio"][aria-checked="true"]')?.getAttribute('aria-label'),
      items: [...d.querySelectorAll('.set-item')].map((li) => ({
        variant: li.getAttribute('data-variant'),
        name: li.querySelector('.set-name')?.textContent.trim(),
        option: li.querySelector('.specs')?.textContent.trim(),
        price: (li.querySelector('.set-buy')?.textContent.match(/₪\s?[\d,.]+|[\d,.]+\s?₪/) ?? [null])[0],
        buttons: li.querySelectorAll('button').length,
        oos: /המלאי אינו זמין כעת/.test(li.textContent),
      })),
      note: d.querySelector('.set-note')?.textContent.replace(/\s+/g, ' ').trim() ?? null,
      add_set: d.querySelector('#add-set')?.textContent.replace(/\s+/g, ' ').trim() ?? null,
    }));
    s.engine_selection = (await engine(p)).sel;
    r.sets.push(s);
    await p.screenshot({ path: join(OV, `wheel-${w}-step${i + 1}.png`) });
  }
  res.wheel.push(r);
  await ctx.close();
}

// ---------- 3: the swap-diff ----------
const lo = house.scene.widths.lo;
const sc = house.scene.slots[SLOT];
async function footprint(n) {
  const out = [];
  for (const [set, shadow] of [[sc.product, false], [sc.shadow, true]]) {
    if (!set) continue;
    // the engine composes from the 2720 files (native); the footprint from the same files
    const f = join(COPY, 'web/public/media', `${set.src[n - 1]}.${house.scene.native ?? lo}.webp`);
    const { data, info } = await sharp(f).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
    const on = new Uint8Array(info.width * info.height);
    for (let i = 0; i < on.length; i++) on[i] = shadow ? +(data[i * 4] < 255 || data[i * 4 + 1] < 255 || data[i * 4 + 2] < 255) : +(data[i * 4 + 3] > 0);
    out.push({ rect: set.rect, w: info.width, h: info.height, on });
  }
  return out;
}
const feet = [await footprint(1), await footprint(2), await footprint(3)];
res.swap = [];
for (const v of [
  { w: 1280, h: 720, dpr: 1 },
  { w: 1920, h: 1080, dpr: 1 },
  { w: 400, h: 800, dpr: 1, mobile: true },
  { w: 390, h: 844, dpr: 3, mobile: true },
]) {
  const ctx = await ctxOf(v.w, v.h, v);
  const p = await ctx.newPage();
  await ready(p);
  await p.evaluate(() => document.querySelectorAll('.stage-ui, .hotspots, .stage-temp-note, .outlines, .stage-back, .stage-vignette').forEach((el) => (el.style.visibility = 'hidden')));
  await p.mouse.move(0, 0);
  await p.waitForTimeout(3500);
  const canvas = p.locator('canvas.room-canvas');
  const shot = async (pos) => {
    await p.evaluate(([id, n]) => window.__hdEngine.setSelection(id, n, 0), [SLOT, pos]);
    await p.waitForTimeout(500);
    return sharp(await canvas.screenshot()).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  };
  const shots = [await shot(1), await shot(2), await shot(3), await shot(1)];
  const e = await engine(p);
  const W = shots[0].info.width, H = shots[0].info.height;
  const cb = await canvas.boundingBox();
  const k = W / cb.width;
  const fw = Math.max(e.vp.w, e.vp.h * house.scene.aspect) * e.cam.z;
  const fh = fw / house.scene.aspect;
  const masks = {};
  const maskFor = (i, j, dil) => {
    const key = `${i}${j}${dil}`;
    if (masks[key]) return masks[key];
    const m = new Uint8Array(W * H);
    for (const lay of [...feet[i], ...feet[j]]) {
      const [u0, u1, v0, v1] = lay.rect;
      // every source pixel's footprint on screen (its corners), so a pixel bigger than a screen pixel leaves no hole
      for (let y = 0; y < lay.h; y++)
        for (let x = 0; x < lay.w; x++) {
          if (!lay.on[y * lay.w + x]) continue;
          const ua = u0 + (x / lay.w) * (u1 - u0), ub = u0 + ((x + 1) / lay.w) * (u1 - u0);
          const va = v0 + (y / lay.h) * (v1 - v0), vb = v0 + ((y + 1) / lay.h) * (v1 - v0);
          const xa = Math.floor((e.vp.w / 2 + (ua - e.cam.cu) * fw) * k) - dil, xb = Math.ceil((e.vp.w / 2 + (ub - e.cam.cu) * fw) * k) - 1 + dil;
          const ya = Math.floor((e.vp.h / 2 + (va - e.cam.cv) * fh) * k) - dil, yb = Math.ceil((e.vp.h / 2 + (vb - e.cam.cv) * fh) * k) - 1 + dil;
          for (let Y = Math.max(0, ya); Y <= Math.min(H - 1, yb); Y++) for (let X = Math.max(0, xa); X <= Math.min(W - 1, xb); X++) m[Y * W + X] = 1;
        }
    }
    return (masks[key] = m);
  };
  const r = { viewport: `${v.w}x${v.h}@${v.dpr}`, canvas_px: [W, H], engine: { cam: e.cam, vp: e.vp, compWidth: e.compWidth }, pairs: [] };
  // the same selection twice (1 → … → 1): the engine's own noise floor
  {
    let d = 0, n = 0;
    for (let i = 0; i < W * H * 3; i++) { const x = Math.abs(shots[0].data[i] - shots[3].data[i]); if (x > d) d = x; if (x) n++; }
    r.repeat_B_vs_B = { max: d, channels_changed: n };
  }
  const NAMES = house.sets.map((s) => s.id);
  for (const [i, j] of [[0, 1], [1, 2], [0, 2]]) {
    const pr = { pair: `${NAMES[i]}↔${NAMES[j]}` };
    const a = shots[i].data, b = shots[j].data;
    for (const dil of [0, 1, 3]) {
      const m = maskFor(i, j, dil);
      let out0 = 0, out2 = 0, worst = 0, inside = 0, masked = 0;
      const where = [];
      for (let n = 0; n < W * H; n++) {
        const d = Math.max(Math.abs(a[n * 3] - b[n * 3]), Math.abs(a[n * 3 + 1] - b[n * 3 + 1]), Math.abs(a[n * 3 + 2] - b[n * 3 + 2]));
        if (m[n]) { masked++; if (d > 2) inside++; continue; }
        if (d > 0) { out0++; if (where.length < 12) where.push([n % W, Math.floor(n / W), d]); }
        if (d > 2) out2++;
        if (d > worst) worst = d;
      }
      pr[`dil${dil}`] = { changed_outside_gt0: out0, changed_outside_gt2: out2, worst_outside: worst, changed_inside_gt2: inside, mask_share: +(masked / (W * H)).toFixed(4), first_outside: where };
    }
    // a picture of the difference: |a-b| ×8 in red, the dil-0 footprint's edge in green
    const m0 = maskFor(i, j, 0);
    const vis = Buffer.alloc(W * H * 3);
    for (let n = 0; n < W * H; n++) {
      const d = Math.max(Math.abs(a[n * 3] - b[n * 3]), Math.abs(a[n * 3 + 1] - b[n * 3 + 1]), Math.abs(a[n * 3 + 2] - b[n * 3 + 2]));
      const g = (a[n * 3] + a[n * 3 + 1] + a[n * 3 + 2]) / 9;
      const edge = m0[n] && ((n % W > 0 && !m0[n - 1]) || (n % W < W - 1 && !m0[n + 1]) || (n >= W && !m0[n - W]) || (n < W * (H - 1) && !m0[n + W]));
      vis[n * 3] = Math.min(255, g + d * 8);
      vis[n * 3 + 1] = edge ? 255 : g;
      vis[n * 3 + 2] = g;
    }
    await sharp(vis, { raw: { width: W, height: H, channels: 3 } }).jpeg({ quality: 82 }).toFile(join(OV, `swap-diff-${v.w}x${v.h}@${v.dpr}-${NAMES[i]}${NAMES[j]}.jpg`));
    r.pairs.push(pr);
  }
  res.swap.push(r);
  await ctx.close();
}

// ---------- 4: the house switch ----------
res.switch = [];
for (const reduced of [false, true]) {
  for (const dir of ['nordic→warm-modern', 'warm-modern→nordic']) {
    const ctx = await ctxOf(1280, 720, { reduced });
    const p = await ctx.newPage();
    const start = dir.startsWith('nordic') ? '/rooms/living-room/' : HOUSE;
    await p.goto(BASE + start, { waitUntil: 'load' });
    await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 20000 });
    const sb = await p.locator('section.stage').boundingBox();
    await p.mouse.click(sb.x + 20, sb.y + sb.height / 2);
    for (let i = 0; i < 80 && !(await engine(p))?.ready; i++) await p.waitForTimeout(250);
    if (dir.startsWith('warm')) await p.waitForTimeout(500);
    // warm the next house's chunk and layers once (a first visit is timed separately below: press → end)
    await p.waitForTimeout(1500);
    const camBefore = (await engine(p)).cam;
    // screencast of the painted frames
    const cdp = await ctx.newCDPSession(p);
    const frames = [];
    cdp.on('Page.screencastFrame', async (f) => {
      frames.push({ t: f.metadata.timestamp, data: f.data });
      await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => undefined);
    });
    await p.evaluate(() => {
      window.__qa = [];
      const q = (s) => document.querySelector(s);
      const t0 = performance.now();
      const loop = () => {
        const c = q('canvas.room-canvas'), po = q('img.poster'), st = q('section.stage');
        const bx = (el) => { if (!el) return null; const b = el.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((x) => Math.round(x * 10) / 10).join(','); };
        window.__qa.push({ t: performance.now(), canvas: bx(c), poster: bx(po), stage: bx(st), ct: c ? getComputedStyle(c).transform : null, pt: po ? getComputedStyle(po).transform : null, co: c ? getComputedStyle(c).opacity : null, po_op: po ? getComputedStyle(po).opacity : null, house: st?.dataset.house });
        if (performance.now() - t0 < 4000) requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    });
    await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 70, everyNthFrame: 1, maxWidth: 640, maxHeight: 360 });
    await p.waitForTimeout(300);
    const wallPress = Date.now() / 1000;
    const target = dir.startsWith('nordic') ? 'warm-modern' : 'nordic';
    await p.locator(`.segmented button[data-house="${target}"]`).click();
    await p.waitForTimeout(3600);
    await cdp.send('Page.stopScreencast');
    const samples = await p.evaluate(() => window.__qa);
    const sw = await p.evaluate(() => window.__hdHouseSwitch ?? null);
    const camAfter = (await engine(p)).cam;
    const url = p.url().replace(BASE, '');
    await ctx.close();
    // the dissolve from the painted frames: each frame's mean |difference| to the last frame, normalised by the first
    const dec = [];
    for (const f of frames) {
      const { data, info } = await sharp(Buffer.from(f.data, 'base64')).resize(320, 180, { fit: 'fill' }).removeAlpha().raw().toBuffer({ resolveWithObject: true });
      dec.push({ t: f.t, px: data, w: info.width });
    }
    let painted = null;
    if (dec.length > 2) {
      const last = dec.at(-1).px, first = dec[0].px;
      // only the stage's area (the frame is the whole viewport: the stage is the top of the page)
      const dist = (a) => { let s = 0; for (let i = 0; i < a.length; i++) s += Math.abs(a[i] - last[i]); return s / a.length; };
      const d0 = dist(first);
      const prog = dec.map((f) => ({ t: f.t, p: d0 ? 1 - dist(f.px) / d0 : 1 }));
      const t1 = prog.find((x) => x.p > 0.01)?.t, t99 = prog.find((x) => x.p > 0.99)?.t;
      painted = { frames: dec.length, mean_frame_gap_ms: Math.round(((dec.at(-1).t - dec[0].t) / (dec.length - 1)) * 1000), press_to_1pct_ms: t1 ? Math.round((t1 - wallPress) * 1000) : null, from_1_to_99_pct_ms: t1 && t99 ? Math.round((t99 - t1) * 1000) : null, progress: prog.map((x) => [Math.round((x.t - wallPress) * 1000), +x.p.toFixed(3)]) };
    }
    const boxes = { canvas: [...new Set(samples.map((s) => s.canvas))], poster: [...new Set(samples.map((s) => s.poster))], stage: [...new Set(samples.map((s) => s.stage))], canvas_transform: [...new Set(samples.map((s) => s.ct))], poster_transform: [...new Set(samples.map((s) => s.pt))], canvas_opacity: [...new Set(samples.map((s) => s.co))] };
    res.switch.push({ reduced, dir, page_timestamps: sw ? { dissolve_ms: Math.round(sw.end - sw.start), press_to_end_ms: Math.round(sw.end - sw.asked) } : null, painted, boxes, same_camera: JSON.stringify(camBefore) === JSON.stringify(camAfter), url_after: url, rAF_samples: samples.length });
  }
}

// ---------- 5: the old draft address and the story's links ----------
{
  const r = await fetch(`${BASE}/story/living-room/warm-modern/tool/`, { redirect: 'manual' });
  const r2 = await fetch(`${BASE}/story/living-room/warm-modern/tool`, { redirect: 'manual' });
  const r3 = await fetch(`${BASE}/story/living-room/warm-modern/tool/?from=x`, { redirect: 'manual' });
  const t = await fetch(`${BASE}/rooms/living-room/?style=warm-modern`);
  res.draft_redirect = {
    trailing_slash: { status: r.status, location: r.headers.get('location') },
    no_slash: { status: r2.status, location: r2.headers.get('location') },
    with_query: { status: r3.status, location: r3.headers.get('location') },
    target_status: t.status,
  };
  const ctx = await ctxOf(1280, 900);
  const p = await ctx.newPage();
  await p.goto(`${BASE}/story/living-room/warm-modern/`, { waitUntil: 'load' });
  res.story_links = await p.evaluate(() => [...document.querySelectorAll('a')].filter((a) => /עצב בעצמך|לעיצוב|לנסות בחדר|tool/.test(a.textContent + a.getAttribute('href'))).map((a) => ({ text: a.textContent.replace(/\s+/g, ' ').trim().slice(0, 50), href: a.getAttribute('href') })));
  res.story_links_all_to_engine = res.story_links.every((l) => /^\/rooms\/living-room\/\?style=warm-modern/.test(l.href));
  await ctx.close();
}

// ---------- 6: entering at the house's address ----------
for (const [w, h, mobile] of [[1280, 720, false], [400, 800, true]]) {
  const ctx = await ctxOf(w, h, { mobile });
  const p = await ctx.newPage();
  const got = [];
  p.on('response', async (q) => { if (/\/media\//.test(q.url())) got.push({ url: q.url().replace(BASE, ''), bytes: Number(q.headers()['content-length'] ?? 0) || (await q.body().catch(() => Buffer.alloc(0))).length }); });
  await p.goto(BASE + HOUSE, { waitUntil: 'load' });
  await p.waitForTimeout(200);
  const early = await p.evaluate(() => ({ pending: document.querySelector('section.stage')?.classList.contains('house-pending'), house: document.querySelector('section.stage')?.dataset.house, poster: document.querySelector('img.poster')?.currentSrc }));
  await p.locator('section.stage[data-house="warm-modern"]').waitFor({ timeout: 20000 });
  await p.waitForTimeout(4000);
  const late = await p.evaluate(() => ({ house: document.querySelector('section.stage')?.dataset.house, poster: document.querySelector('img.poster')?.currentSrc }));
  await p.screenshot({ path: join(OV, `house-entry-${w}.png`) });
  const nordicMedia = got.filter((g) => !g.url.includes('/house/'));
  res[`entry_${w}`] = { early, late, media_total_kb: +(got.reduce((s, g) => s + g.bytes, 0) / 1024).toFixed(1), nordic_media: nordicMedia.map((g) => `${g.url} ${(g.bytes / 1024).toFixed(1)} KB`), house_media: got.filter((g) => g.url.includes('/house/')).map((g) => `${g.url} ${(g.bytes / 1024).toFixed(1)} KB`) };
  await ctx.close();
}

await browser.close();
writeFileSync(join(OUT, 'data/house-browser.json'), JSON.stringify(res, null, 1));
const brief = {
  wheel: res.wheel.map((r) => ({ vp: r.viewport, default: r.default_selection, radios: r.radio_labels, checked_on_open: r.checked_on_open, steps: r.sets.map((s) => `${s.checked}:${s.label} sel=${JSON.stringify(s.engine_selection)} add=${s.add_set}`) })),
  set_b: res.wheel[0].sets[0].items,
  swap: res.swap.map((r) => ({ vp: r.viewport, repeat: r.repeat_B_vs_B, pairs: r.pairs.map((p) => `${p.pair} d0:${p.dil0.changed_outside_gt0}/${p.dil0.changed_outside_gt2} max${p.dil0.worst_outside} d1:${p.dil1.changed_outside_gt0}/${p.dil1.changed_outside_gt2} max${p.dil1.worst_outside} d3:${p.dil3.changed_outside_gt0} in:${p.dil0.changed_inside_gt2} share:${p.dil0.mask_share}`) })),
  switch: res.switch.map((s) => ({ ...s, painted: s.painted && { ...s.painted, progress: undefined } })),
  draft_redirect: res.draft_redirect,
  story_links: res.story_links,
  entry_1280: res.entry_1280,
  entry_400: res.entry_400,
};
console.log(JSON.stringify(brief, null, 1));
