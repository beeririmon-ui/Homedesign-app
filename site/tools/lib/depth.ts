/**
 * MOCK7 (2026-11-26): a room's depth for the tour's transitions (2.5D, in code), as the page reads it: a small grey
 * picture of how near each point is (near = white, far = black), 192 × 108, inlined in the room's data as a data URI
 * (no file of its own: the Artifact's 255 files stay as they are). The push between two rooms moves the near parts more
 * than the far ones (web/src/tour/gl.ts, PUSH), so a coarse map is enough; it is blurred a little on purpose, so the
 * parallax bends round an edge instead of tearing it.
 *
 * Two encodings exist in the repository (read only, never changed here):
 *   `inv16`   motion-agent's room depth (assets/renders/living-room/warm-modern/depth.json, m0w-depth.png): uint16,
 *             near = bright, linear in 1/depth between the room's near and far; 0 = no surface (the view out)
 *   `m5000`   the framing blockouts (assets/blockout/house/framing/<room>/<frame>-depth.png, their README): uint16, the
 *             planar depth in metres × 5000; 65535 = nothing (the sky, the view out)
 */
import sharp from 'sharp';
import { repoPath } from './paths';

export type DepthCfg = { file: string; encoding: 'inv16' | 'm5000' };
export const DEPTH_SIZE = [192, 108] as const;

/** the quantile `q` of the values that pass `keep` (a coarse histogram: enough for a near and a far) */
function quantile(v: Float32Array, q: number, keep: (x: number) => boolean): number {
  const xs: number[] = [];
  for (let i = 0; i < v.length; i += 7) if (keep(v[i]!)) xs.push(v[i]!);
  xs.sort((a, b) => a - b);
  return xs.length ? xs[Math.min(xs.length - 1, Math.max(0, Math.floor(q * xs.length)))]! : 1;
}

/** the room's nearness map, as a WebP data URI (and how many points had no surface) */
export async function nearness(cfg: DepthCfg): Promise<{ uri: string; empty: number }> {
  const { data, info } = await sharp(repoPath(cfg.file)).extractChannel(0).raw({ depth: 'ushort' }).toBuffer({ resolveWithObject: true });
  const n = info.width * info.height;
  const u16 = new Uint16Array(data.buffer, data.byteOffset, n);
  const near = Buffer.alloc(n);
  let empty = 0;
  if (cfg.encoding === 'inv16') {
    for (let i = 0; i < n; i++) {
      if (!u16[i]) empty++;
      near[i] = Math.round((u16[i]! / 65535) * 255);
    }
  } else {
    // planar metres; the room's own near and far (2% and 98% of its surfaces), so every room uses the whole range
    const d = new Float32Array(n);
    for (let i = 0; i < n; i++) d[i] = u16[i]! >= 65535 || !u16[i] ? 0 : u16[i]! / 5000;
    const dn = quantile(d, 0.02, (x) => x > 0);
    const df = quantile(d, 0.98, (x) => x > 0);
    const a = 1 / Math.max(0.05, dn);
    const b = 1 / Math.max(dn + 0.05, df);
    for (let i = 0; i < n; i++) {
      if (!d[i]) {
        empty++;
        near[i] = 0;
        continue;
      }
      near[i] = Math.round(Math.min(1, Math.max(0, (1 / d[i]! - b) / (a - b))) * 255);
    }
  }
  const [w, h] = DEPTH_SIZE;
  const webp = await sharp(near, { raw: { width: info.width, height: info.height, channels: 1 } })
    .resize(w, h, { fit: 'fill', kernel: 'cubic' })
    .blur(0.8)
    .webp({ quality: 82, effort: 6 })
    .toBuffer();
  return { uri: `data:image/webp;base64,${webp.toString('base64')}`, empty: empty / n };
}
