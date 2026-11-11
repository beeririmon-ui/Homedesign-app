/**
 * S12, QA S8–S10 §4 (S10 question 4): the tool-layer encoding threshold, checked on the build as the browser draws it.
 * QA's method (qa/reports/2026-11-10-site-track-qa-s8-s10/tools/base-quality.mjs): the same page is drawn twice per view,
 * once with the layer's requests answered by the approved pixels (the encoder's own resize, lossless) and once by the
 * file the build made, and the two canvases are compared (tools/lib/encoding.ts: p99 ≤ 6, p99.9 ≤ 10, ≤ 0.2% above 8
 * levels, ΔE00 p99 ≤ 3.5), at QA's five views.
 *  - **warm-modern:** the base (AVIF, and the WebP fallback), and the default set's product layer inside its own area.
 *  - **Nordic:** the base (AVIF and the WebP fallback). Its product layers are temporary recolours with no approved file
 *    to measure against (the preview render until the final layers pass QA).
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect } from '@playwright/test';
import sharp from 'sharp';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { VIEWS, failures, measure, type Measure } from '../tools/lib/encoding';
import { capture, crop, file, fulfil, within, type Answer, type Box } from './encoding-capture';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const REPO = resolve(SITE, '..');

// ---------- the approved pixels ----------
const wm = JSON.parse(readFileSync(resolve(SITE, 'tools/house/living-room.warm-modern.json'), 'utf8')) as {
  pilot: string;
  layers_dir: string;
  approved: { composites: Record<string, string> };
  sets: { id: string }[];
  slot: { id: string };
};
const lay = join(REPO, wm.pilot, wm.layers_dir);
const LAYERED = existsSync(join(lay, 'base.png'));
const wmBase = LAYERED ? join(lay, 'base.png') : join(REPO, wm.pilot, wm.approved.composites[wm.sets[0]!.id]!);
const house = JSON.parse(readFileSync(resolve(SITE, '.generated/house.living-room.warm-modern.json'), 'utf8')) as {
  scene: { aspect: number; slots: Record<string, { product: { rect: Box; src: string[] } }> };
};
const temp = JSON.parse(readFileSync(resolve(SITE, 'tools/temp/living-room.nordic.json'), 'utf8')) as { source_manifest_id: string };
const assets = JSON.parse(readFileSync(resolve(REPO, 'assets/manifest.json'), 'utf8')) as { assets: { id: string; path: string }[] };
const nordicSource = resolve(REPO, assets.assets.find((a) => a.id === temp.source_manifest_id)!.path);

const refCache = new Map<string, Promise<Buffer>>();
/** the encoder's input at that width, as a lossless PNG (make-house: removeAlpha + resize; make-temp-assets: resize) */
function reference(source: string, width: number, removeAlpha: boolean): Promise<Buffer> {
  const key = `${source}@${width}`;
  let p = refCache.get(key);
  if (!p) {
    const img = sharp(source);
    refCache.set(key, (p = (removeAlpha ? img.removeAlpha() : img).resize({ width }).png({ compressionLevel: 1 }).toBuffer()));
  }
  return p;
}
/** the default set's product layer, losslessly: make-house's cut of the approved set, at the layer's width */
async function productReference(width: number): Promise<Buffer> {
  const src = LAYERED ? join(lay, `cushions-set-${wm.sets[0]!.id}.png`) : join(REPO, wm.pilot, wm.approved.composites[wm.sets[0]!.id]!);
  const rect = house.scene.slots[wm.slot.id]!.product.rect;
  const W = 2720;
  const H = 1530;
  const cut = {
    left: Math.round(rect[0] * W),
    top: Math.round(rect[2] * H),
    width: Math.round((rect[1] - rect[0]) * W),
    height: Math.round((rect[3] - rect[2]) * H),
  };
  return sharp(src).ensureAlpha().extract(cut).resize({ width }).png({ compressionLevel: 1 }).toBuffer();
}

const fmt = (m: Measure) => `${m.p99}/${m.p999}/${m.max} · ${(m.over8 * 100).toFixed(2)}% · ΔE ${m.de00_p99}`;
const evidence: Record<string, Record<string, Measure & { pass: boolean }>> = {};
const note = (layer: string, view: string, m: Measure) => ((evidence[layer] ??= {})[view] = { ...m, pass: failures(m).length === 0 });

test.describe('the tool-layer encoding threshold (S12, QA S8–S10 §4), as the browser draws it', () => {
  test.describe.configure({ timeout: 600_000 });

  test('warm-modern: the base (AVIF q70 and its WebP fallback) and the default set’s layer meet it in every view', async ({ browser }) => {
    const BASE = /\/media\/house\/living-room\/warm-modern\/M0\/base\/shell\.(\d+)\.(avif|webp)$/;
    const PRODUCT = /\/media\/house\/living-room\/warm-modern\/M0\/slots\/[a-z-]+\/1\.product\.(\d+)\.webp$/;
    const refBase: Answer = async (r, m) => fulfil(r, await reference(wmBase, Number(m[1]), true), 'image/png');
    const refProduct: Answer = async (r, m) =>
      fulfil(
        r,
        await productReference(Math.round(Number(m[1]) * (house.scene.slots[wm.slot.id]!.product.rect[1] - house.scene.slots[wm.slot.id]!.product.rect[0]))),
        'image/png',
      );
    // the WebP fallback: the engine asks for the AVIF where the browser decodes it; here it is answered with the WebP
    const webpBase: Answer = async (r, m) => fulfil(r, file(`house/living-room/warm-modern/M0/base/shell.${m[1]}.webp`), 'image/webp');
    const url = '/rooms/living-room/?style=warm-modern';
    const bad: string[] = [];
    for (const v of VIEWS) {
      const ref = await capture(
        browser,
        url,
        v,
        [
          [BASE, refBase],
          [PRODUCT, refProduct],
        ],
        wm.slot.id,
      );
      const avif = await capture(browser, url, v, [[PRODUCT, refProduct]], wm.slot.id);
      const m = measure(ref.data, avif.data, false);
      note('warm-modern base, AVIF', v.id, m);
      for (const f of failures(m)) bad.push(`base AVIF ${v.id}: ${f}`);
      if (v.id === '1920@1' || v.id === '400@3') {
        const webp = await capture(
          browser,
          url,
          v,
          [
            [BASE, webpBase],
            [PRODUCT, refProduct],
          ],
          wm.slot.id,
        );
        const mw = measure(ref.data, webp.data, false);
        note('warm-modern base, WebP fallback', v.id, mw);
        for (const f of failures(mw)) bad.push(`base WebP ${v.id}: ${f}`);
        // the product layer, inside the set's own area (its residual is diluted to nothing over the whole frame)
        const prod = await capture(browser, url, v, [[BASE, refBase]], wm.slot.id);
        const box = within(ref, house.scene.slots[wm.slot.id]!.product.rect, house.scene.aspect);
        const mp = measure(crop(ref.data, ref.w, box), crop(prod.data, prod.w, box), false);
        note('warm-modern set B layer (WebP near-lossless 60)', v.id, mp);
        for (const f of failures(mp)) bad.push(`set layer ${v.id}: ${f}`);
      }
      console.log(`encoding warm-modern ${v.id}: base AVIF ${fmt(m)}`);
    }
    write();
    expect(bad, bad.join('\n')).toEqual([]);
  });

  test('Nordic: its base (AVIF q70 and its WebP fallback) meets it in every view (its layers are temporary)', async ({ browser }) => {
    const BASE = /\/media\/rooms\/living-room\/nordic\/M0\/base\/shell\.(\d+)\.(avif|webp)$/;
    const refBase: Answer = async (r, m) => fulfil(r, await reference(nordicSource, Number(m[1]), false), 'image/png');
    const webpBase: Answer = async (r, m) => fulfil(r, file(`rooms/living-room/nordic/M0/base/shell.${m[1]}.webp`), 'image/webp');
    const bad: string[] = [];
    for (const v of VIEWS) {
      const ref = await capture(browser, '/rooms/living-room/', v, [[BASE, refBase]], 'vase');
      const enc = await capture(browser, '/rooms/living-room/', v, [], 'vase');
      expect(enc.w).toBe(ref.w);
      const m = measure(ref.data, enc.data, false);
      note('Nordic base (temporary), AVIF', v.id, m);
      for (const f of failures(m)) bad.push(`base AVIF ${v.id}: ${f}`);
      if (v.id === '1920@1' || v.id === '400@3') {
        const webp = await capture(browser, '/rooms/living-room/', v, [[BASE, webpBase]], 'vase');
        const mw = measure(ref.data, webp.data, false);
        note('Nordic base (temporary), WebP fallback', v.id, mw);
        for (const f of failures(mw)) bad.push(`base WebP ${v.id}: ${f}`);
      }
      console.log(`encoding nordic ${v.id}: base AVIF ${fmt(m)}`);
    }
    write();
    expect(bad, bad.join('\n')).toEqual([]);
  });
});

function write() {
  const dir = process.env.HD_EVIDENCE_DIR;
  if (!dir) return;
  mkdirSync(dir, { recursive: true });
  const path = join(dir, 'encoding.json');
  const prev = existsSync(path) ? (JSON.parse(readFileSync(path, 'utf8')) as { layers: typeof evidence }).layers : {};
  writeFileSync(path, JSON.stringify({ threshold: 'p99 ≤ 6, p99.9 ≤ 10, ≤ 0.2% above 8 levels, ΔE00 p99 ≤ 3.5', layers: { ...prev, ...evidence } }, null, 1));
}
