/**
 * S10 evidence (QA on the warm-modern layers, finding 1): the engine composes this house at its native width (2720) from
 * the web files it serves, and resamples the composed room once on display. This rebuilds that composition from the same
 * files (the base AVIF the browser takes, the WebP layers, the manifest's blend: base × shadow, then the set over it,
 * straight alpha) and compares it with the approved display file composite-set-X-v3-graded-v3c.png: at 2720, and after
 * one resize of both to the display widths (linear, as the GL sampler). Per set: p99.9 and max of the largest channel
 * difference inside the set's region, and outside it.
 *
 *   npx tsx tools/check-house.ts [out.json]
 */
import sharp from 'sharp';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

type Box = [number, number, number, number];
const m = JSON.parse(readFileSync(sitePath('tools/house/living-room.warm-modern.json'), 'utf8')) as {
  pilot: string;
  approved: { composites: Record<string, string> };
  sets: { id: string }[];
};
const house = JSON.parse(readFileSync(join(GENERATED, 'house.living-room.warm-modern.json'), 'utf8')) as {
  scene: {
    native: number;
    base: { src: string }[];
    slots: Record<string, { product: { rect: Box; src: string[] }; shadow: { rect: Box; src: string[] } | null }>;
  };
};
const N = house.scene.native;
const H = Math.round((N * 1530) / 2720);
const slot = Object.values(house.scene.slots)[0]!;
const raw = async (img: sharp.Sharp, ch: 3 | 4) => (await img.toColourspace('srgb')[ch === 3 ? 'removeAlpha' : 'ensureAlpha']().raw().toBuffer()) as Buffer;
const file = (src: string, ext: string) => join(MEDIA_OUT, `${src}.${N}.${ext}`);

const pct = (a: number[], p: number) => {
  if (!a.length) return 0;
  const s = Float64Array.from(a).sort();
  return s[Math.min(s.length - 1, Math.floor(p * s.length))]!;
};
async function compare(a: Buffer, b: Buffer, region: Uint8Array, w: number, h: number) {
  const ins: number[] = [];
  const out: number[] = [];
  for (let i = 0; i < w * h; i++) {
    const d = Math.max(Math.abs(a[i * 3]! - b[i * 3]!), Math.abs(a[i * 3 + 1]! - b[i * 3 + 1]!), Math.abs(a[i * 3 + 2]! - b[i * 3 + 2]!));
    (region[i] ? ins : out).push(d);
  }
  return {
    region: { p999: pct(ins, 0.999), max: ins.reduce((x, y) => Math.max(x, y), 0), px: ins.length },
    outside: { p999: pct(out, 0.999), max: out.reduce((x, y) => Math.max(x, y), 0) },
  };
}

const report: Record<string, unknown> = { native: N };
const base = await raw(sharp(file(house.scene.base[0]!.src, 'avif')), 3);
for (const [i, s] of m.sets.entries()) {
  const out = Buffer.from(base);
  const region = new Uint8Array(N * H);
  const place = async (src: string, rect: Box, shadow: boolean) => {
    const img = await raw(sharp(file(src, 'webp')), 4);
    const meta = await sharp(file(src, 'webp')).metadata();
    const x0 = Math.round(rect[0] * N);
    const y0 = Math.round(rect[2] * H);
    for (let y = 0; y < meta.height!; y++)
      for (let x = 0; x < meta.width!; x++) {
        const k = (y * meta.width! + x) * 4;
        const o = (y0 + y) * N + x0 + x;
        const a = img[k + 3]! / 255;
        if (shadow) {
          if (img[k]! < 255 || img[k + 1]! < 255 || img[k + 2]! < 255) region[o] = 1;
          for (let c = 0; c < 3; c++) out[o * 3 + c] = Math.round((out[o * 3 + c]! * img[k + c]!) / 255);
        } else if (a > 0) {
          region[o] = 1;
          for (let c = 0; c < 3; c++) out[o * 3 + c] = Math.round(out[o * 3 + c]! * (1 - a) + img[k + c]! * a);
        }
      }
  };
  if (slot.shadow) await place(slot.shadow.src[i]!, slot.shadow.rect, true);
  await place(slot.product.src[i]!, slot.product.rect, false);
  const approved = await raw(sharp(repoPath(m.pilot, m.approved.composites[s.id]!)), 3);
  const row: Record<string, unknown> = { [`at ${N}`]: await compare(out, approved, region, N, H) };
  for (const w of [1920, 1280, 800]) {
    const h = Math.round((w * 1530) / 2720);
    const rs = (b: Buffer) => sharp(b, { raw: { width: N, height: H, channels: 3 } }).resize(w, h, { kernel: 'linear' });
    const r = await sharp(Buffer.from(region.map((v) => v * 255)), { raw: { width: N, height: H, channels: 1 } })
      .resize(w, h, { kernel: 'linear' })
      .extractChannel(0)
      .raw()
      .toBuffer();
    row[`once at ${w}`] = await compare(
      await raw(rs(out), 3),
      await raw(rs(approved), 3),
      Uint8Array.from(r, (v) => +(v > 0)),
      w,
      h,
    );
  }
  report[`set ${s.id}`] = row;
  console.log(`set ${s.id}: ${JSON.stringify(row)}`);
}
if (process.argv[2]) writeFileSync(process.argv[2], JSON.stringify(report, null, 1));
