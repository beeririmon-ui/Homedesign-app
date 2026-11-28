/**
 * MOCK12 (2026-11-28, briefs/site-mock12-wheels-studio-2026-11-28.md): tools/make-tour-room.ts on the fixture frame of
 * two wheels (tools/make-fixture-wheels.ts: numbered swatches, no product), built into a temporary folder
 * (HD_TOUR_MEDIA, HD_TOUR_GENERATED) with a studio of its own (HD_WHEEL_STUDIO), never into the site's media:
 *  - two wheels in one frame, one from `default: false` layers and one from a wheel manifest next to the room's (the
 *    M0-W `<key>.wheel` format), each on the frame's atlas pages, a place an option; the gate holds;
 *  - FB29: a product an occluder cuts is marked `cut` (the page names it, never shows the cut); a whole one is not;
 *  - a product's studio picture is found by its variant, on the frame's studio sheet; one without has none;
 *  - and a card's rim (tools/lib/cards.ts): the matte's 4 px feather becomes a one-pixel edge of the product's colour.
 */
import sharp from 'sharp';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { GENERATED, sitePath } from '../lib/paths';
import { hardenRim } from '../lib/cards';

const work = mkdtempSync(join(tmpdir(), 'mock12-wheels-'));
afterAll(() => rmSync(work, { recursive: true, force: true }));
const shop = existsSync(join(GENERATED, 'catalog.tour-rooms.full.json'));
const tsx = sitePath('node_modules/.bin/tsx');

type Opt = { position: number; variant?: string; cut?: string; studio?: { src: string; sprite: number[]; source: string } | null; card: { src: string } };
type Built = {
  sample?: string;
  wheels?: string[];
  atlas: Record<string, { product: { src: string }[] }>;
  slots: { id: string; atlas?: unknown; atlas_opts?: Record<string, { product: number[]; shadow: number[] }[]>; shadows?: number[]; options: Opt[] }[];
};

describe.skipIf(!shop)('MOCK12: two wheels in a frame, the room’s cuts and the studio pictures (make-tour-room)', () => {
  it('builds the fixture frame of two wheels: both on the atlas, the hidden picture cut, a studio still by variant', { timeout: 120_000 }, async () => {
    execFileSync(tsx, [sitePath('tools/make-fixture-wheels.ts'), '--no-build'], { cwd: sitePath(), stdio: 'pipe' });
    // a studio of its own: one still, for the square's second option
    const still = join(work, 'still.webp');
    await sharp({ create: { width: 64, height: 64, channels: 3, background: { r: 241, g: 232, b: 220 } } })
      .webp()
      .toFile(still);
    const studio = join(work, 'studio.json');
    writeFileSync(studio, JSON.stringify({ variants: [{ variant: 'fx-square-2', room: 'work', slot: 'fx-square', webp: still, products: [] }] }));
    const out = { media: join(work, 'media'), gen: join(work, 'generated') };
    const log = execFileSync(tsx, [sitePath('tools/make-tour-room.ts'), join(GENERATED, 'fixtures/wheels2/fixture-wheels2.warm-modern.json')], {
      cwd: sitePath(),
      env: { ...process.env, HD_TOUR_MEDIA: out.media, HD_TOUR_GENERATED: out.gen, HD_WHEEL_STUDIO: studio },
      stdio: 'pipe',
      encoding: 'utf8',
    });
    expect(log).toContain('the order gives truth.png to the pixel');
    expect(log).toContain('wheels: fx-square (3), fx-disc (3)');
    const d = JSON.parse(readFileSync(join(out.gen, 'tour.fixture-wheels2.warm-modern.json'), 'utf8')) as Built;
    expect(d.wheels).toEqual(['fx-square', 'fx-disc']);
    expect(d.sample).toBe('fx-square');
    const slot = (id: string) => d.slots.find((s) => s.id === id)!;
    for (const id of ['fx-square', 'fx-disc']) {
      const s = slot(id);
      expect(s.options.map((o) => o.variant)).toEqual([1, 2, 3].map((k) => `${id}-${k}`));
      expect(s.atlas).toBeUndefined();
      // a place each on the frame's own atlas pages, three distinct places
      const places = s.atlas_opts!['1280']!.map((p) => p.product.join(','));
      expect(new Set(places).size).toBe(3);
      expect(s.shadows).toEqual([1, 1, 1]);
    }
    // the wheel manifest's options are its sets' (B's layers), in its order
    // FB29: the picture behind the box is cut by it; the box, the square and the disc are whole
    expect(slot('fx-picture').options[0]!.cut).toBe('occluded');
    for (const id of ['fx-box', 'fx-square', 'fx-disc']) for (const o of slot(id).options) expect(o.cut, `${id} ${o.position}`).toBeUndefined();
    // the studio still: the square's second option only, on the frame's studio sheet
    const st = slot('fx-square').options.map((o) => o.studio ?? null);
    expect(st[0]).toBeNull();
    expect(st[2]).toBeNull();
    expect(st[1]!.source).toBe('studio');
    expect(st[1]!.src).toBe('tour/fixture-wheels2/warm-modern/studio.512');
    expect(existsSync(join(out.media, 'tour/fixture-wheels2/warm-modern/studio.512.webp'))).toBe(true);
    expect(log).toMatch(/outside the room \(FB29\): 1 studio, \d+ cut clean, 1 by name \(cut by the room: fx-picture:1 occluded\)/);
  });
});

/**
 * FB29 ("עם פדר, חיתוך פדר מסביב"): a layer's matte fades over about 4 px of the room it was cut from. A synthetic layer
 * of that kind — a square of the product's colour, its rim a 4 px ramp of alpha over the wall's colour — through the
 * tool's own hardening: a one-pixel edge, and the edge's colour the product's, not the wall's.
 */
describe('MOCK12 (FB29): a card has no feathered rim (tools/lib/cards.ts hardenRim)', () => {
  const N = 40;
  const PRODUCT: [number, number, number] = [120, 70, 40];
  const WALL: [number, number, number] = [230, 225, 215];
  const px = Buffer.alloc(N * N * 4);
  // the solid product in 12..27, a 4 px feather round it (alpha 0.8 → 0.2), its colour the wall's as it fades
  for (let y = 0; y < N; y++)
    for (let x = 0; x < N; x++) {
      const d = Math.max(0, 12 - x, x - 27, 12 - y, y - 27);
      const a = d === 0 ? 1 : d <= 4 ? 1 - d * 0.2 : 0;
      const i = (y * N + x) * 4;
      for (let k = 0; k < 3; k++) px[i + k] = d === 0 ? PRODUCT[k]! : Math.round(PRODUCT[k]! * a + WALL[k]! * (1 - a));
      px[i + 3] = Math.round(a * 255);
    }
  const ring = (b: Buffer) => {
    let part = 0;
    // a pixel one can see through and see (alpha 16–254): a ring of alpha 0.04 of the product's own colour is neither
    for (let i = 0; i < N * N; i++) if (b[i * 4 + 3]! >= 16 && b[i * 4 + 3]! < 255) part++;
    return part / (4 * 16);
  };
  it('the 4 px feather becomes a one-pixel edge, and the edge takes the product’s colour', () => {
    expect(ring(px)).toBeGreaterThan(3.5);
    const out = hardenRim(px, N, N);
    expect(ring(out)).toBeLessThanOrEqual(1.5);
    // the first ring outside the product (alpha 0.8 in the layer, its colour a fifth wall) is now opaque and the product's
    const i = (20 * N + 11) * 4;
    expect(out[i + 3]).toBe(255);
    for (let k = 0; k < 3; k++) expect(Math.abs(out[i + k]! - PRODUCT[k]!)).toBeLessThanOrEqual(2);
    // what was mostly wall (alpha 0.2–0.4) is gone
    expect(out[(20 * N + 8) * 4 + 3]).toBe(0);
    expect(out[(20 * N + 9) * 4 + 3]).toBeLessThan(16);
  });
  it('a thin thing (a cord of alpha 0.6) keeps its core', () => {
    const cord = Buffer.alloc(N * N * 4);
    for (let y = 0; y < N; y++) cord.set([40, 40, 40, 153], (y * N + 20) * 4);
    const out = hardenRim(cord, N, N);
    for (let y = 0; y < N; y++) expect(out[(y * N + 20) * 4 + 3]).toBeGreaterThan(128);
  });
});
