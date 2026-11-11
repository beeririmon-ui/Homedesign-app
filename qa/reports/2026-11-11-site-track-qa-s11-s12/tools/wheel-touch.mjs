/**
 * qa-agent, 2026-11-11 (ת7 at b94c5bc1): the wheel after a REAL touch drag. Not synthetic pointer events dispatched on
 * the element (the e2e's way): CDP Input.dispatchTouchEvent, so the browser's own touch pipeline runs (touch-action:
 * pan-y on the stage, gesture detection, the pointer events the browser makes from the touches, page scrolling).
 * For each house (Nordic, warm-modern) × 390×844@3, 400×860@1, 720×1100@2 (phone, phone, tablet), mobile + touch:
 *   1. a real tap on the stage starts the engine;
 *   2. real horizontal drags (touchStart → 8 touchMoves → touchEnd) pan the room toward the slot's mark until it is
 *      well inside the screen; the camera's u and the stage's scrollLeft are recorded after each;
 *   3. the old way (scrollLeft / scrollBy on the stage) is tried once: must stay 0;
 *   4. a real tap on the mark; the wheel must open wholly inside the visual viewport, its chosen card on screen, the
 *      canvas at x≈0, and the screen must be the lit room (mean and spread of the whole glass, and of the dialog area);
 *   5. a real vertical drag scrolls the page down (the page, not the stage), a visible mark is tapped: the same checks;
 *   6. the wheel is closed: the stage is still unscrolled.
 * Screens of every opened wheel to overlays/.
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node wheel-touch.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';

const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'],
});
const HOUSES = [
  { name: 'nordic', url: '/rooms/living-room/', slot: 'vase' },
  { name: 'warm-modern', url: '/rooms/living-room/?style=warm-modern', slot: 'cushions' },
];
const SIZES = [
  { w: 390, h: 844, dpr: 3 },
  { w: 400, h: 860, dpr: 1 },
  { w: 720, h: 1100, dpr: 2 },
];
const res = [];
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function touchDrag(cdp, from, to, steps = 8, stepMs = 16) {
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x: from.x, y: from.y, id: 1 }] });
  for (let k = 1; k <= steps; k++) {
    await sleep(stepMs);
    const x = from.x + ((to.x - from.x) * k) / steps;
    const y = from.y + ((to.y - from.y) * k) / steps;
    await cdp.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [{ x, y, id: 1 }] });
  }
  await sleep(stepMs);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await sleep(120);
}
async function touchTap(cdp, x, y) {
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y, id: 2 }] });
  await sleep(60);
  await cdp.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
}
const state = (p, slot) =>
  p.evaluate((s) => {
    const st = document.querySelector('section.stage');
    const m = document.querySelector(`button.hotspot[data-slot="${s}"]`);
    const r = m?.getBoundingClientRect();
    const vv = window.visualViewport;
    return {
      cu: window.__hdEngine?.cam?.cu ?? null,
      ready: !!window.__hdEngine?.ready,
      stage_scroll: st ? [st.scrollLeft, st.scrollTop] : null,
      page_scroll: [scrollX, scrollY],
      vv: vv ? { x: vv.offsetLeft, y: vv.offsetTop, w: vv.width, h: vv.height, scale: vv.scale } : null,
      mark: r ? { x: r.left, y: r.top, w: r.width, h: r.height, vis: getComputedStyle(m).visibility, op: getComputedStyle(m).opacity } : null,
    };
  }, slot);

async function judge(p, size, label) {
  const dlg = p.getByRole('dialog');
  let open = false;
  try {
    await dlg.waitFor({ state: 'visible', timeout: 12000 });
    open = true;
  } catch {
    open = false;
  }
  await sleep(1400);
  const geo = await p.evaluate(() => {
    const d = document.querySelector('[role="dialog"]');
    const c = document.querySelector('[role="radio"][aria-checked="true"]');
    const cv = document.querySelector('canvas.room-canvas');
    const st = document.querySelector('section.stage');
    const vv = window.visualViewport;
    const box = (e) => {
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: +r.left.toFixed(1), y: +r.top.toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1) };
    };
    return {
      dialog: box(d),
      chosen: box(c),
      canvas: box(cv),
      stage: box(st),
      stage_scroll: st ? [st.scrollLeft, st.scrollTop] : null,
      vv: vv ? { x: vv.offsetLeft, y: vv.offsetTop, w: vv.width, h: vv.height } : { x: 0, y: 0, w: innerWidth, h: innerHeight },
    };
  });
  const v = geo.vv;
  const inside = (b) => !!b && b.x >= v.x - 0.5 && b.y >= v.y - 0.5 && b.x + b.w <= v.x + v.w + 0.5 && b.y + b.h <= v.y + v.h + 0.5;
  const png = await p.screenshot();
  const img = sharp(png);
  const meta = await img.metadata();
  const whole = await img.clone().greyscale().stats();
  let dstat = null;
  if (geo.dialog) {
    const k = meta.width / size.w;
    const left = Math.max(0, Math.round(geo.dialog.x * k));
    const top = Math.max(0, Math.round(geo.dialog.y * k));
    const width = Math.min(meta.width - left, Math.round(geo.dialog.w * k));
    const height = Math.min(meta.height - top, Math.round(geo.dialog.h * k));
    if (width > 10 && height > 10) dstat = (await img.clone().extract({ left, top, width, height }).greyscale().stats()).channels[0];
  }
  const name = `wheel-touch-${label}.jpg`;
  await sharp(png).resize({ width: Math.min(meta.width, 720) }).jpeg({ quality: 80 }).toFile(join(OUT, 'overlays', name));
  const r = {
    open,
    ...geo,
    dialog_inside: inside(geo.dialog),
    chosen_inside: inside(geo.chosen),
    glass_mean: +whole.channels[0].mean.toFixed(1),
    glass_sd: +whole.channels[0].stdev.toFixed(1),
    dialog_mean: dstat ? +dstat.mean.toFixed(1) : null,
    dialog_sd: dstat ? +dstat.stdev.toFixed(1) : null,
    shot: name,
  };
  r.pass = open && r.dialog_inside && r.chosen_inside && Math.abs((geo.canvas?.x ?? 99) - 0) < 1 && geo.stage_scroll?.[0] === 0 && r.dialog_mean > 90 && r.dialog_sd > 12 && r.glass_mean > 60;
  return r;
}

for (const h of HOUSES)
  for (const size of SIZES) {
    const label = `${h.name}-${size.w}`;
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: size.w, height: size.h }, deviceScaleFactor: size.dpr, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    const cdp = await ctx.newCDPSession(p);
    const out = { house: h.name, size, steps: [] };
    try {
      await p.goto(`${BASE}${h.url}`, { waitUntil: 'load' });
      await p.locator(`button.hotspot[data-slot="${h.slot}"]`).waitFor({ state: 'attached', timeout: 30000 });
      const sb = await p.locator('section.stage').boundingBox();
      const y = Math.round(sb.y + Math.min(sb.height, size.h - sb.y) * 0.55);
      // no tap to start: a tap on a product opens its wheel (by design). The first real drag is the intent that starts
      // the engine; it goes away from the mark, so at least one drag comes back toward it
      out.rest = await state(p, h.slot);
      const away = out.rest.mark && out.rest.mark.x + out.rest.mark.w / 2 < size.w / 2 ? -1 : 1;
      const xa = Math.round(size.w / 2 - away * size.w * 0.2);
      await touchDrag(cdp, { x: xa, y }, { x: xa + away * Math.round(size.w * 0.4), y: y + 2 });
      for (let i = 0; i < 120 && !(await p.evaluate(() => window.__hdEngine?.ready)); i++) await sleep(250);
      await sleep(800);
      out.dialog_after_first_drag = await p.evaluate(() => document.querySelector('[role="dialog"]')?.getAttribute('aria-labelledby') ?? null);
      out.start = await state(p, h.slot);
      await touchDrag(cdp, { x: xa, y }, { x: xa + away * Math.round(size.w * 0.4), y: y + 2 });
      out.steps.push({ dir: away, after: await state(p, h.slot) });
      // real drags toward the mark
      for (let i = 0; i < 18; i++) {
        const s = await state(p, h.slot);
        const m = s.mark;
        if (m && m.x > 50 && m.x + m.w < size.w - 50) break;
        // the mark is to the left (x < 50): drag the room to the right (finger left → right), and the other way
        const dir = !m || m.x < 50 ? 1 : -1;
        const x0 = Math.round(size.w / 2 - dir * size.w * 0.2);
        await touchDrag(cdp, { x: x0, y }, { x: x0 + dir * Math.round(size.w * 0.4), y: y + 2 });
        out.steps.push({ dir, after: await state(p, h.slot) });
      }
      // the old way: the stage's own scroll
      out.tried_stage_scroll = await p.evaluate(() => {
        const st = document.querySelector('section.stage');
        st.scrollBy({ left: -360, behavior: 'instant' });
        st.scrollLeft = -360;
        return [st.scrollLeft, st.scrollTop];
      });
      await sleep(200);
      // the marks show after a touch; tap the slot's mark for real
      const before = await state(p, h.slot);
      out.before_tap = before;
      const m = before.mark;
      await touchTap(cdp, Math.round(m.x + m.w / 2), Math.round(m.y + m.h / 2));
      out.after_pan = await judge(p, size, `${label}-after-pan`);
      // close
      const close = p.getByRole('button', { name: 'סגירה וחזרה לחדר בלי שינוי' });
      if (await close.count()) await close.click();
      await p.getByRole('dialog').waitFor({ state: 'detached', timeout: 8000 }).catch(() => undefined);
      await sleep(1200);
      out.after_close = await state(p, h.slot);
      // a real vertical drag (the page scrolls down), then a visible mark
      await touchDrag(cdp, { x: Math.round(size.w * 0.5), y: Math.round(size.h * 0.8) }, { x: Math.round(size.w * 0.5), y: Math.round(size.h * 0.55) }, 10, 16);
      await sleep(600);
      await touchTap(cdp, Math.round(size.w * 0.5), Math.round(size.h * 0.45)).catch(() => undefined);
      await sleep(300);
      out.page_scrolled = await state(p, h.slot);
      const vis = await p.evaluate((W) => {
        const vv = window.visualViewport;
        const top = (vv?.offsetTop ?? 0) + 70;
        const bottom = (vv?.offsetTop ?? 0) + (vv?.height ?? innerHeight) - 20;
        return Array.from(document.querySelectorAll('button.hotspot'))
          .map((b) => ({ s: b.dataset.slot, r: b.getBoundingClientRect(), v: getComputedStyle(b).visibility, d: b.disabled }))
          .map(({ s, r, v, d }) => ({ s, x: r.left, y: r.top, w: r.width, h: r.height, v, d }))
          .find((b) => b.v === 'visible' && !b.d && b.y > top && b.y + b.h < bottom && b.x > 10 && b.x + b.w < W - 10);
      }, size.w);
      out.scrolled_mark = vis ?? null;
      if (vis) {
        await touchTap(cdp, Math.round(vis.x + vis.w / 2), Math.round(vis.y + vis.h / 2));
        out.after_page_scroll = await judge(p, size, `${label}-page-scrolled`);
      }
    } catch (e) {
      out.error = String(e).slice(0, 400);
    }
    res.push(out);
    console.log(
      label,
      JSON.stringify({
        moved_u: [out.start?.cu, ...out.steps.map((x) => x.after.cu && +x.after.cu.toFixed(3)), out.before_tap?.cu],
        dialog_after_first_drag: out.dialog_after_first_drag,
        stage_scroll_tried: out.tried_stage_scroll,
        after_pan: out.after_pan && { pass: out.after_pan.pass, dialog: out.after_pan.dialog, mean: out.after_pan.dialog_mean, sd: out.after_pan.dialog_sd, glass: out.after_pan.glass_mean },
        page: out.page_scrolled?.page_scroll,
        after_page_scroll: out.after_page_scroll && { pass: out.after_page_scroll.pass, dialog: out.after_page_scroll.dialog, mean: out.after_page_scroll.dialog_mean },
        error: out.error,
      }),
    );
    await ctx.close();
  }
await browser.close();
writeFileSync(join(OUT, 'data/wheel-touch.json'), JSON.stringify(res, null, 1));
