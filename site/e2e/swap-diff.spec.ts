/**
 * Variant swap QA (docs/studio-rules.md ו.5): switching a product's variant may change nothing outside the product's
 * own shape. Measured in the browser, on what the user sees, for every slot and every variant, both at rest and in the
 * zoomed wheel view:
 *
 *   1. screenshot of the composed room with variant 1, then with variant n (no UI on top, camera fixed);
 *   2. the product silhouette = alpha > 0.5 of variant 1 ∪ variant n (the layers the engine draws), mapped to the
 *      screen through the engine's camera, dilated by 3 px of the layer (at rest that is 3 screen px; zoomed in, one
 *      layer pixel covers several screen pixels and the dilation scales with it);
 *   3. CIEDE2000 between the two screenshots; every pixel outside the silhouette must stay below ΔE 1.
 *
 * Diff maps (red = change outside the silhouette, amber = change inside, cyan = silhouette edge) and before/after
 * crops are written to assets/qa/swap-diff/ with a report.json, for review by eye.
 */
import { test, expect, type Page } from '@playwright/test';
import sharp from 'sharp';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const OUT = resolve(SITE, '../assets/qa/swap-diff');
const MEDIA = resolve(SITE, 'web/public/media');
const LAYER_PX = 3;
const MAX_DE = 1;

type Box = [number, number, number, number];
type Scene = { aspect: number; widths: { lo: number }; slots: Record<string, { product: { rect: Box; src: string[] } | null }> };
type Catalog = { rooms: { id: string; slots: { id: string; zoom_frame: Box | null; options: unknown[] }[] }[] };

const scene = JSON.parse(readFileSync(resolve(SITE, '.generated/scene.living-room.nordic.json'), 'utf8')) as Scene;
const catalog = JSON.parse(readFileSync(resolve(SITE, '.generated/catalog.public.json'), 'utf8')) as Catalog;
const living = catalog.rooms.find((r) => r.id === 'living-room')!;

type Raw = { data: Buffer; w: number; h: number; c: number };
const rawOf = async (input: Buffer | string): Promise<Raw> => {
  const { data, info } = await sharp(input).ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  return { data, w: info.width, h: info.height, c: info.channels };
};
const alphaCache = new Map<string, Raw>();
async function layerAlpha(src: string): Promise<Raw> {
  let r = alphaCache.get(src);
  if (!r) alphaCache.set(src, (r = await rawOf(resolve(MEDIA, `${src}.${scene.widths.lo}.webp`))));
  return r;
}

// ---------- colour difference (CIEDE2000 on sRGB → Lab D65) ----------
function lab(r8: number, g8: number, b8: number): [number, number, number] {
  const lin = (c: number) => {
    c /= 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  };
  const r = lin(r8);
  const g = lin(g8);
  const b = lin(b8);
  const x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047;
  const y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
  const f = (t: number) => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 / 116) * t + 16 / 116);
  return [116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))];
}
export function deltaE2000(a: [number, number, number], b: [number, number, number]): number {
  const [L1, a1, b1] = a;
  const [L2, a2, b2] = b;
  const rad = Math.PI / 180;
  const C1 = Math.hypot(a1, b1);
  const C2 = Math.hypot(a2, b2);
  const Cm = (C1 + C2) / 2;
  const G = 0.5 * (1 - Math.sqrt(Math.pow(Cm, 7) / (Math.pow(Cm, 7) + Math.pow(25, 7))));
  const a1p = (1 + G) * a1;
  const a2p = (1 + G) * a2;
  const C1p = Math.hypot(a1p, b1);
  const C2p = Math.hypot(a2p, b2);
  const h = (x: number, y: number) => (x === 0 && y === 0 ? 0 : (Math.atan2(y, x) / rad + 360) % 360);
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
  const Lpm = (L1 + L2) / 2;
  const Cpm = (C1p + C2p) / 2;
  let hpm = h1p + h2p;
  if (C1p * C2p !== 0) hpm = Math.abs(h1p - h2p) > 180 ? (h1p + h2p + (h1p + h2p < 360 ? 360 : -360)) / 2 : (h1p + h2p) / 2;
  const T =
    1 - 0.17 * Math.cos((hpm - 30) * rad) + 0.24 * Math.cos(2 * hpm * rad) + 0.32 * Math.cos((3 * hpm + 6) * rad) - 0.2 * Math.cos((4 * hpm - 63) * rad);
  const dTheta = 30 * Math.exp(-Math.pow((hpm - 275) / 25, 2));
  const Rc = 2 * Math.sqrt(Math.pow(Cpm, 7) / (Math.pow(Cpm, 7) + Math.pow(25, 7)));
  const Sl = 1 + (0.015 * Math.pow(Lpm - 50, 2)) / Math.sqrt(20 + Math.pow(Lpm - 50, 2));
  const Sc = 1 + 0.045 * Cpm;
  const Sh = 1 + 0.015 * Cpm * T;
  const Rt = -Math.sin(2 * dTheta * rad) * Rc;
  return Math.sqrt(Math.pow(dLp / Sl, 2) + Math.pow(dCp / Sc, 2) + Math.pow(dHp / Sh, 2) + Rt * (dCp / Sc) * (dHp / Sh));
}

// ---------- page helpers ----------
async function startEngine(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await page.goto('/rooms/living-room/');
  await expect(page.locator('button.hotspot:visible').first()).toBeVisible({ timeout: 20_000 });
  // nothing on top of the room: the measurement is the composed picture only
  // (CSP: no inline <style>; element styles are allowed)
  await page.evaluate(() =>
    document
      .querySelectorAll<HTMLElement>('.hotspots, .stage-ui, .stage-temp-note, .stage-vignette, .stage-loading')
      .forEach((el) => el.style.setProperty('display', 'none', 'important')),
  );
  await page.locator('.stage').dispatchEvent('pointerdown');
  await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 20_000 });
}

type View = { cam: { cu: number; cv: number; z: number }; vp: { w: number; h: number }; box: { x: number; y: number; width: number; height: number } };

async function setView(page: Page, zoom: Box | null): Promise<View> {
  return page.evaluate(async (zoomBox) => {
    const e = window.__hdEngine as unknown as {
      cam: View['cam'];
      vp: View['vp'];
      zoomToBox(b: number[], d: number, o: { durationMs: number; reserve: number }): Promise<void>;
      zoomOut(d: number): Promise<void>;
    };
    if (zoomBox) await e.zoomToBox(zoomBox, 0.4, { durationMs: 0, reserve: e.vp.h > 520 ? 0.44 : 0.36 });
    else await e.zoomOut(0);
    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    const r = document.querySelector('canvas.room-canvas')!.getBoundingClientRect();
    return { cam: { ...e.cam }, vp: { ...e.vp }, box: { x: r.x, y: r.y, width: r.width, height: r.height } };
  }, zoom);
}

async function select(page: Page, slot: string, n: number) {
  await page.evaluate(
    async ([s, k]) => {
      await window.__hdEngine!.setSelection(s as string, k as number, 0);
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
    },
    [slot, n],
  );
}

async function shot(page: Page, v: View): Promise<Raw> {
  const png = await page.screenshot({ clip: v.box, animations: 'disabled', caret: 'hide' });
  return rawOf(png);
}

/** Silhouette (alpha > 0.5 of either layer) in screen pixels, dilated. */
async function silhouette(v: View, rect: Box, srcs: string[], w: number, h: number): Promise<Uint8Array> {
  const fw = Math.max(v.vp.w, v.vp.h * scene.aspect);
  const fh = fw / scene.aspect;
  const DILATE = Math.ceil(LAYER_PX * Math.max(1, (fw * v.cam.z) / scene.widths.lo) * (w / v.vp.w));
  const layers = await Promise.all(srcs.map(layerAlpha));
  const m = new Uint8Array(w * h);
  const sx = v.vp.w / w;
  const sy = v.vp.h / h;
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const u = v.cam.cu + ((x + 0.5) * sx - v.vp.w / 2) / (fw * v.cam.z);
      const t = v.cam.cv + ((y + 0.5) * sy - v.vp.h / 2) / (fh * v.cam.z);
      if (u < rect[0] || u >= rect[1] || t < rect[2] || t >= rect[3]) continue;
      for (const l of layers) {
        const lx = Math.min(l.w - 1, Math.floor(((u - rect[0]) / (rect[1] - rect[0])) * l.w));
        const ly = Math.min(l.h - 1, Math.floor(((t - rect[2]) / (rect[3] - rect[2])) * l.h));
        if (l.data[(ly * l.w + lx) * l.c + 3]! > 127) {
          m[y * w + x] = 1;
          break;
        }
      }
    }
  // dilate (square, DILATE px) in two separable passes
  const tmp = new Uint8Array(w * h);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let on = 0;
      for (let k = -DILATE; k <= DILATE && !on; k++) on = m[y * w + Math.min(w - 1, Math.max(0, x + k))]!;
      tmp[y * w + x] = on;
    }
  const out = new Uint8Array(w * h);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      let on = 0;
      for (let k = -DILATE; k <= DILATE && !on; k++) on = tmp[Math.min(h - 1, Math.max(0, y + k)) * w + x]!;
      out[y * w + x] = on;
    }
  return out;
}

type Result = { slot: string; option: number; view: string; outside_px: number; outside_max_de: number; inside_px: number; map: string };

async function compare(a: Raw, b: Raw, mask: Uint8Array, file: string): Promise<Omit<Result, 'slot' | 'option' | 'view' | 'map'>> {
  const { w, h, c } = a;
  const map = Buffer.alloc(w * h * 3);
  let outside = 0;
  let inside = 0;
  let maxDe = 0;
  let bx0 = w;
  let bx1 = 0;
  let by0 = h;
  let by1 = 0;
  for (let i = 0; i < w * h; i++) {
    const o = i * c;
    const de =
      a.data[o] === b.data[o] && a.data[o + 1] === b.data[o + 1] && a.data[o + 2] === b.data[o + 2]
        ? 0
        : deltaE2000(lab(a.data[o]!, a.data[o + 1]!, a.data[o + 2]!), lab(b.data[o]!, b.data[o + 1]!, b.data[o + 2]!));
    const g = Math.round(((a.data[o]! + a.data[o + 1]! + a.data[o + 2]!) / 3) * 0.35);
    let px: [number, number, number] = [g, g, g];
    if (mask[i]) {
      const x = i % w;
      const y = (i - x) / w;
      bx0 = Math.min(bx0, x);
      bx1 = Math.max(bx1, x);
      by0 = Math.min(by0, y);
      by1 = Math.max(by1, y);
      const edge = !mask[i - 1] || !mask[i + 1] || !mask[i - w] || !mask[i + w];
      if (edge) px = [0, 200, 220];
      if (de >= MAX_DE) {
        inside++;
        px = [255, 190, 60];
      }
    } else if (de >= MAX_DE) {
      outside++;
      maxDe = Math.max(maxDe, de);
      const k = Math.min(1, de / 8);
      px = [Math.round(140 + 115 * k), 20, 30];
    }
    map[i * 3] = px[0];
    map[i * 3 + 1] = px[1];
    map[i * 3 + 2] = px[2];
  }
  mkdirSync(OUT, { recursive: true });
  await sharp(map, { raw: { width: w, height: h, channels: 3 } })
    .png()
    .toFile(resolve(OUT, `${file}.diff.png`));
  // before | after crop around the product (with 40 px of the room around it), for the eye
  if (bx1 > bx0) {
    const pad = 40;
    const left = Math.max(0, bx0 - pad);
    const top = Math.max(0, by0 - pad);
    const width = Math.min(w, bx1 + pad) - left;
    const height = Math.min(h, by1 + pad) - top;
    const crop = (r: Raw) =>
      sharp(r.data, { raw: { width: r.w, height: r.h, channels: r.c as 4 } })
        .extract({ left, top, width, height })
        .png()
        .toBuffer();
    const [ca, cb] = await Promise.all([crop(a), crop(b)]);
    await sharp({ create: { width: width * 2 + 8, height, channels: 3, background: '#000' } })
      .composite([
        { input: ca, left: 0, top: 0 },
        { input: cb, left: width + 8, top: 0 },
      ])
      .png()
      .toFile(resolve(OUT, `${file}.before-after.png`));
  }
  return { outside_px: outside, outside_max_de: Math.round(maxDe * 100) / 100, inside_px: inside };
}

test.describe('variant swap changes nothing outside the product shape', () => {
  test.skip(({ browserName }) => browserName !== 'chromium');
  test.setTimeout(240_000);

  test('every slot, every variant, at rest and zoomed (1280 × 720)', async ({ page }) => {
    await startEngine(page, 1280, 720);
    const results: Result[] = [];
    for (const zoomed of [false, true]) {
      for (const slot of living.slots) {
        const layer = scene.slots[slot.id]?.product;
        if (!layer || slot.options.length < 2) continue;
        const v = await setView(page, zoomed ? slot.zoom_frame : null);
        await select(page, slot.id, 1);
        const before = await shot(page, v);
        for (let n = 2; n <= slot.options.length; n++) {
          await select(page, slot.id, n);
          const after = await shot(page, v);
          await select(page, slot.id, 1);
          const mask = await silhouette(v, layer.rect, [layer.src[0]!, layer.src[n - 1] ?? layer.src[0]!], before.w, before.h);
          const name = `${slot.id}.${n}.${zoomed ? 'zoom' : 'rest'}`;
          const r = await compare(before, after, mask, name);
          results.push({ slot: slot.id, option: n, view: zoomed ? 'zoom' : 'rest', ...r, map: `assets/qa/swap-diff/${name}.diff.png` });
        }
      }
    }
    writeFileSync(
      resolve(OUT, 'report.json'),
      JSON.stringify({ measured_at: new Date().toISOString(), viewport: '1280x720', dilate_layer_px: LAYER_PX, max_delta_e: MAX_DE, results }, null, 1),
    );
    const bad = results.filter((r) => r.outside_px > 0).map((r) => `${r.slot} #${r.option} (${r.view}): ${r.outside_px} px, max ΔE ${r.outside_max_de}`);
    expect(bad, `changes outside the product shape:\n${bad.join('\n')}`).toEqual([]);
  });
});
