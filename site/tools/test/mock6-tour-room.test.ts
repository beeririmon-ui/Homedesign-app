/**
 * MOCK6 (2026-11-25): tools/make-tour-room.ts on a wheel of many options, with a fixture of ten. The kids' art sets
 * (FB12, ten a room) are not rendered yet, so the fixture is a tiny render folder made here (numbered squares, no art),
 * built into a temporary folder (HD_TOUR_MEDIA, HD_TOUR_GENERATED), never into the site's media:
 *  - the gate still holds (the layers in order give the folder's composite to the pixel);
 *  - ten options are a patch file each (product, and one shadow for the options that share it to the byte), not on the
 *    atlas pages, and the slot says `lazy` (the page loads a patch only when its option is chosen);
 *  - two or three options stay on the frame's atlas pages (MOCK6: no pages of their own), and thirteen are refused.
 */
import sharp from 'sharp';
import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterAll, describe, expect, it } from 'vitest';
import { GENERATED, sitePath } from '../lib/paths';

const W = 192;
const H = 108;
const work = mkdtempSync(join(tmpdir(), 'mock6-wheel-'));
afterAll(() => rmSync(work, { recursive: true, force: true }));
const shop = existsSync(join(GENERATED, 'catalog.tour-rooms.full.json'));

type Sq = { x: number; y: number; s: number; rgb: [number, number, number] };
const PLATE: [number, number, number] = [200, 190, 180];
async function png(file: string, sq: Sq | null, alpha: boolean) {
  const ch = alpha ? 4 : 3;
  const buf = Buffer.alloc(W * H * ch);
  if (!alpha) for (let i = 0; i < W * H; i++) buf.set(PLATE, i * 3);
  if (sq)
    for (let y = sq.y; y < sq.y + sq.s; y++)
      for (let x = sq.x; x < sq.x + sq.s; x++) {
        const i = (y * W + x) * ch;
        buf.set(sq.rgb, i);
        if (alpha) buf[i + 3] = 255;
      }
  await sharp(buf, { raw: { width: W, height: H, channels: ch } })
    .png()
    .toFile(file);
}
const white = async (file: string) =>
  sharp({ create: { width: W, height: H, channels: 3, background: { r: 255, g: 255, b: 255 } } })
    .png()
    .toFile(file);

/** a render folder of a lamp and a wheel of `n` options (numbered squares at one place), and its tour config */
async function fixture(n: number): Promise<string> {
  const dir = join(work, `folder-${n}`);
  mkdirSync(dir, { recursive: true });
  await png(join(dir, 'plate.png'), null, false);
  await white(join(dir, 'shadow.png'));
  const lamp: Sq = { x: 20, y: 20, s: 20, rgb: [50, 60, 70] };
  await png(join(dir, 'lamp.png'), lamp, true);
  const art = (k: number): Sq => ({ x: 100, y: 40, s: 30, rgb: [20 + k * 20, 200 - k * 15, 90] });
  for (let k = 0; k < n; k++) await png(join(dir, `art-${k + 1}.png`), art(k), true);
  // the folder's composite: the plate, the lamp, the wheel's first option (every alpha 255, no shadow)
  const truth = Buffer.alloc(W * H * 3);
  for (let i = 0; i < W * H; i++) truth.set(PLATE, i * 3);
  for (const q of [lamp, art(0)]) for (let y = q.y; y < q.y + q.s; y++) for (let x = q.x; x < q.x + q.s; x++) truth.set(q.rgb, (y * W + x) * 3);
  await sharp(truth, { raw: { width: W, height: H, channels: 3 } })
    .png()
    .toFile(join(dir, 'truth.png'));
  const layers = [
    { slot: 'lamp', product: 'lamp-fixture', z: 10, layer: 'lamp.png', shadow: 'shadow.png' },
    { slot: 'art', product: 'art-fixture-1', z: 20, layer: 'art-1.png', shadow: 'shadow.png' },
    ...Array.from({ length: n - 1 }, (_, k) => ({
      slot: 'art',
      product: `art-fixture-${k + 2}`,
      z: 20,
      default: false,
      layer: `art-${k + 2}.png`,
      shadow: 'shadow.png',
    })),
  ];
  writeFileSync(
    join(dir, 'manifest.json'),
    JSON.stringify({ id: `fixture-wheel-${n}`, canvas: [W, H], frame_box: [0, 0, W, H], compose: 'plate.png; per layer in z order', layers, light: [] }),
  );
  const cfg = join(work, `fixture-${n}.json`);
  writeFileSync(
    cfg,
    JSON.stringify({
      room: `fixture-wheel${n}`,
      group: `fixture-wheel${n}`,
      style: 'warm-modern',
      name_he: 'הדגמה',
      layers: dir,
      manifest: 'manifest.json',
      truth: 'truth.png',
      plan: 'docs/house-plan.json',
      camera: 'K-boy',
      room_plan: 'boy',
      shell: 'kids',
      slots_file: 'data/slots/kids.json',
      sample: 'art',
      prints: [],
      slots: {
        lamp: { card: null, kind: 'wall', name_he: 'מנורה', depth_m: 2 },
        art: { card: null, kind: 'wall', name_he: 'הדגמה', depth_m: 3 },
      },
    }),
  );
  return cfg;
}
const out = { media: join(work, 'media'), gen: join(work, 'generated') };
function build(cfg: string): { ok: boolean; log: string } {
  try {
    const log = execFileSync(sitePath('node_modules/.bin/tsx'), [sitePath('tools/make-tour-room.ts'), cfg], {
      cwd: sitePath(),
      env: { ...process.env, HD_TOUR_MEDIA: out.media, HD_TOUR_GENERATED: out.gen },
      stdio: 'pipe',
      encoding: 'utf8',
    });
    return { ok: true, log };
  } catch (e) {
    const x = e as { stdout?: string; stderr?: string };
    return { ok: false, log: `${x.stdout ?? ''}${x.stderr ?? ''}` };
  }
}
type Built = {
  sample: string;
  atlas: Record<string, { product: { src: string }[]; shadow: { src: string }[] }>;
  slots: { id: string; src: string; lazy?: boolean; shadows?: number[]; atlas_opts?: unknown; options: { position: number }[] }[];
};

describe.skipIf(!shop)('MOCK6: make-tour-room on a wheel of many options (a fixture of ten)', () => {
  it('ten options: the gate holds, a patch file each, one shared shadow, `lazy`, nothing of the wheel on the atlas', { timeout: 60_000 }, async () => {
    const r = build(await fixture(10));
    expect(r.ok, r.log).toBe(true);
    expect(r.log).toContain('the order gives truth.png to the pixel');
    const d = JSON.parse(readFileSync(join(out.gen, 'tour.fixture-wheel10.warm-modern.json'), 'utf8')) as Built;
    const art = d.slots.find((s) => s.id === 'art')!;
    expect(art.options).toHaveLength(10);
    expect(art.lazy).toBe(true);
    expect(art.atlas_opts).toBeUndefined();
    expect(art.shadows).toEqual(Array(10).fill(1));
    const at = join(out.media, 'tour/fixture-wheel10/warm-modern');
    for (const w of [1920, W]) {
      for (let k = 1; k <= 10; k++) expect(existsSync(join(at, 'slots/art', `${k}.product.${w}.webp`)), `${k} at ${w}`).toBe(true);
      expect(existsSync(join(at, 'slots/art', `1.shadow.${w}.webp`))).toBe(true);
      for (let k = 2; k <= 10; k++) expect(existsSync(join(at, 'slots/art', `${k}.shadow.${w}.webp`))).toBe(false);
      // the lamp alone on the atlas pages
      expect(d.atlas[String(w)]!.product).toHaveLength(1);
    }
    // a patch is the option's own pixels (the tenth's colour at the square's middle)
    const { data, info } = await sharp(join(at, 'slots/art', `10.product.${W}.webp`))
      .raw()
      .toBuffer({ resolveWithObject: true });
    const mid = ((info.height >> 1) * info.width + (info.width >> 1)) * info.channels;
    expect(Math.abs(data[mid]! - (20 + 9 * 20))).toBeLessThanOrEqual(3);
    expect(data[mid + 3]).toBe(255);
    // the phone's first load: the chosen option's patch, not the ten
    expect(r.log).toMatch(/a phone's first load \d+ KB in 6 files/);
  });

  it('three options stay on the frame’s own atlas pages (no pages of their own); thirteen are refused', { timeout: 60_000 }, async () => {
    const r3 = build(await fixture(3));
    expect(r3.ok, r3.log).toBe(true);
    const d = JSON.parse(readFileSync(join(out.gen, 'tour.fixture-wheel3.warm-modern.json'), 'utf8')) as Built;
    const art = d.slots.find((s) => s.id === 'art')!;
    expect(art.lazy).toBeUndefined();
    expect((art.atlas_opts as Record<string, unknown[]>)['1920']).toHaveLength(3);
    expect(d.atlas['1920']!.product.map((p) => p.src)).toEqual(['tour/fixture-wheel3/warm-modern/atlas.product.1']);
    expect(existsSync(join(out.media, 'tour/fixture-wheel3/warm-modern/sample.product.1920.webp'))).toBe(false);
    const r13 = build(await fixture(13));
    expect(r13.ok).toBe(false);
    expect(r13.log).toContain('has 13 options, not 2 to 12');
  });
});

/**
 * MOCK6, option (a) of data/leads/cards-kids-after-reg-2026-11-25.md 5.1: a `mirror_of` copy of a card of the shared
 * pool (data/products/pool/: no room, no slot, so never a valid card) takes its original's economics. The three CJ-L2
 * copies were hidden ("no price") before; built here into .generated/catalog.vitest-mock6.*.json.
 */
describe('MOCK6: mirror_of to a pool original (the CJ-L2 copies)', () => {
  it('the bath’s and the work room’s travertine tray and the dining floor vase are priced as their pool originals', { timeout: 60_000 }, () => {
    const COPIES = {
      'vanity-tray-cj-travertine-organic-tray-24': 'pool-cj-travertine-organic-tray-24',
      'desk-tray-cj-travertine-organic-tray-24': 'pool-cj-travertine-organic-tray-24',
      'floor-vase-cj-wabi-sabi-floor-vase-white': 'pool-cj-wabi-sabi-floor-vase-white',
    };
    const list = join(work, 'copies.json');
    writeFileSync(list, JSON.stringify({ points: Object.keys(COPIES).map((product) => ({ product })) }));
    execFileSync(
      process.execPath,
      ['--import', 'tsx', 'tools/build-catalog.ts', '--rooms=living-room', `--products=${list}`, '--out=vitest-mock6', '--lenient'],
      {
        cwd: sitePath(),
        stdio: 'pipe',
      },
    );
    const full = JSON.parse(readFileSync(join(GENERATED, 'catalog.vitest-mock6.full.json'), 'utf8')) as {
      products: { card_id?: string; price_agorot: number; price_source: string; room: string }[];
      hidden: { id: string; reason: string }[];
    };
    const econ = (JSON.parse(readFileSync(sitePath('../data/economics/products.json'), 'utf8')) as { products: Record<string, { retail_ils?: number }> })
      .products;
    for (const [copy, pool] of Object.entries(COPIES)) {
      expect(full.hidden.find((h) => h.id === copy)).toBeUndefined();
      const p = full.products.find((x) => x.card_id === copy)!;
      expect(p, copy).toBeTruthy();
      expect(p.price_source).toBe('studio');
      expect(p.price_agorot).toBe(econ[pool]!.retail_ils! * 100);
    }
  });
});
