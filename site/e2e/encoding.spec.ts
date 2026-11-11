/**
 * S12, QA S8–S10 §4 (S10 question 4): the tool-layer encoding threshold, checked on the build as the browser draws it.
 * QA's method (qa/reports/2026-11-10-site-track-qa-s8-s10/tools/base-quality.mjs): the same page is drawn twice per view,
 * once with the layer's requests answered by the approved pixels (the encoder's own resize, lossless) and once by the
 * file the build made, and the two canvases are compared (tools/lib/encoding.ts: p99 ≤ 6, p99.9 ≤ 10, ≤ 0.2% above 8
 * levels, ΔE00 p99 ≤ 3.5), at QA's five views.
 *  - **warm-modern:** the base (AVIF, and the WebP fallback), and every set's product layer (A, B and C, S14) inside its
 *    own area, in every view.
 *  - **Nordic:** the base (AVIF and the WebP fallback). Its product layers are temporary recolours with no approved file
 *    to measure against (the preview render until the final layers pass QA).
 *  - **S14, QA S11–S12 ת30 (§4): the poster at rest,** in both houses and the four views, as the page rests on it before
 *    the engine starts (a phone: until the first touch): the built file (AVIF, and the WebP fallback) against the
 *    approved pixels the poster stands for (the warm-modern house: its default composition, composite-set-B, ת29).
 *    S16, QA ת43: the warm-modern poster's WebP fallback (lossy q95) is exempt from the threshold by QA's ruling, and
 *    held to the fallback bound (tools/lib/encoding.ts FALLBACK_BOUND); the Nordic fallback still meets the threshold.
 * The numbers go to the evidence when HD_EVIDENCE_DIR is set.
 */
import { test, expect, type Page } from '@playwright/test';
import sharp from 'sharp';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { VIEWS, failures, fallbackFailures, measure, type Measure } from '../tools/lib/encoding';
import { capture, capturePoster, crop, file, fulfil, within, type Answer, type Box } from './encoding-capture';

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
  scene: { aspect: number; slots: Record<string, { product: { rect: Box; src: string[] } }>; poster?: { src: string; widths: number[] } };
};
/** ת29: what the warm-modern poster stands for, the approved default composition */
const wmComposite = join(REPO, wm.pilot, wm.approved.composites[wm.sets[0]!.id]!);
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
/** a set's product layer (by its position on the wheel), losslessly: make-house's cut of the approved set, at the layer's width */
async function productReference(width: number, position = 1): Promise<Buffer> {
  const id = wm.sets[position - 1]!.id;
  const src = LAYERED ? join(lay, `cushions-set-${id}.png`) : join(REPO, wm.pilot, wm.approved.composites[id]!);
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

  const BASE = /\/media\/house\/living-room\/warm-modern\/M0\/base\/shell\.(\d+)\.(avif|webp)$/;
  const PRODUCT = /\/media\/house\/living-room\/warm-modern\/M0\/slots\/[a-z-]+\/(\d)\.product\.(\d+)\.webp$/;
  const refBase: Answer = async (r, m) => fulfil(r, await reference(wmBase, Number(m[1]), true), 'image/png');
  const rect = () => house.scene.slots[wm.slot.id]!.product.rect;
  const refProduct: Answer = async (r, m) => fulfil(r, await productReference(Math.round(Number(m[2]) * (rect()[1] - rect()[0])), Number(m[1])), 'image/png');

  test('warm-modern: the base (AVIF q70 and its WebP fallback) meets it in every view', async ({ browser }) => {
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
      }
      console.log(`encoding warm-modern ${v.id}: base AVIF ${fmt(m)}`);
    }
    write();
    expect(bad, bad.join('\n')).toEqual([]);
  });

  // S14 (QA ת30): every set on the wheel, not only the default, and in every view, not only two
  for (const [i, set] of wm.sets.entries())
    test(`warm-modern: set ${set.id}'s layer (WebP near-lossless 60) meets it inside its own area, in every view`, async ({ browser }) => {
      const url = '/rooms/living-room/?style=warm-modern';
      const choose = async (page: Page) => {
        await page.evaluate(([slot, pos]) => window.__hdEngine!.setSelection(slot as string, pos as number, 0), [wm.slot.id, i + 1] as const);
        await expect.poll(() => page.evaluate((slot) => window.__hdEngine!.getSelection()[slot], wm.slot.id)).toBe(i + 1);
      };
      const bad: string[] = [];
      for (const v of VIEWS) {
        const answers = (product: boolean): [RegExp, Answer][] => [[BASE, refBase], ...(product ? ([[PRODUCT, refProduct]] as [RegExp, Answer][]) : [])];
        const ref = await capture(browser, url, v, answers(true), wm.slot.id, choose);
        const enc = await capture(browser, url, v, answers(false), wm.slot.id, choose);
        // inside the set's own area (its residual is diluted to nothing over the whole frame)
        const box = within(ref, rect(), house.scene.aspect);
        const mp = measure(crop(ref.data, ref.w, box), crop(enc.data, enc.w, box), false);
        note(`warm-modern set ${set.id} layer (WebP near-lossless 60)`, v.id, mp);
        for (const f of failures(mp)) bad.push(`set ${set.id} ${v.id}: ${f}`);
        console.log(`encoding warm-modern set ${set.id} ${v.id}: ${fmt(mp)}`);
      }
      write();
      expect(bad, bad.join('\n')).toEqual([]);
    });

  test('Nordic: its base (AVIF: q80 at 1280 and 1920, the posters, S14; q70 at 2752; and the WebP fallback) meets it in every view (its layers are temporary)', async ({
    browser,
  }) => {
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

// ---------- S14, QA ת30 (§4): the poster at rest ----------
test.describe('the poster at rest meets the threshold (S14, QA S11–S12 ת30 §4), in both houses and the four views', () => {
  test.describe.configure({ timeout: 600_000 });
  const POSTER_VIEWS = VIEWS.filter((v) => !v.zoom);
  const HOUSES = [
    {
      name: 'warm-modern',
      url: '/rooms/living-room/?style=warm-modern',
      re: /\/media\/(house\/living-room\/warm-modern\/M0\/poster\/default)\.(\d+)\.(avif|webp)$/,
      source: wmComposite,
      removeAlpha: true,
    },
    {
      name: 'nordic',
      url: '/rooms/living-room/',
      re: /\/media\/(rooms\/living-room\/nordic\/M0\/base\/shell)\.(\d+)\.(avif|webp)$/,
      source: nordicSource,
      removeAlpha: false,
    },
  ];
  for (const h of HOUSES)
    test(`${h.name}: the poster the page rests on (AVIF and the WebP fallback)`, async ({ browser }) => {
      if (h.name === 'warm-modern') expect(house.scene.poster?.src, 'ת29: the warm-modern poster is its default composition').toMatch(/\/poster\/default$/);
      const ref: Answer = async (r, m) => fulfil(r, await reference(h.source, Number(m[2]), h.removeAlpha), 'image/png');
      const webp: Answer = async (r, m) => fulfil(r, file(`${m[1]}.${m[2]}.webp`), 'image/webp');
      const bad: string[] = [];
      for (const v of POSTER_VIEWS) {
        const R = await capturePoster(browser, h.url, v, [[h.re, ref]]);
        const A = await capturePoster(browser, h.url, v, []);
        const W = await capturePoster(browser, h.url, v, [[h.re, webp]]);
        // at rest: no engine ran, and the three drawings are of the same file width
        for (const c of [R, A, W]) expect(c.engine, `${h.name} ${v.id}: the engine started at rest`).toBe(false);
        expect(A.file.replace(/\.\w+$/, '')).toBe(R.file.replace(/\.\w+$/, ''));
        expect([A.w, A.h]).toEqual([R.w, R.h]);
        const ma = measure(R.data, A.data, false);
        const mw = measure(R.data, W.data, false);
        note(`${h.name} poster at rest, AVIF (${A.file})`, v.id, ma);
        note(
          `${h.name} poster at rest, WebP fallback (${A.file.replace(/avif$/, 'webp')})${h.name === 'warm-modern' ? ' [exempt: fallback bound]' : ''}`,
          v.id,
          mw,
        );
        for (const f of failures(ma)) bad.push(`${h.name} poster AVIF ${v.id} (${A.file}): ${f}`);
        // S16, QA ת43: the warm-modern fallback is exempt from the threshold (QA's ruling), held to the fallback bound
        for (const f of h.name === 'warm-modern' ? fallbackFailures(mw) : failures(mw)) bad.push(`${h.name} poster WebP ${v.id}: ${f}`);
        console.log(`encoding ${h.name} poster ${v.id} (${A.file}): AVIF ${fmt(ma)} · WebP ${fmt(mw)}`);
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
