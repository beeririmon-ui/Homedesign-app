/**
 * frontend-dev, S19 (2026-11-12), ת51: QA's pixel study (qa/reports/2026-11-12-site-track-qa-s17/tools/mut-pixels.mts) on
 * the live tree. The same 78 originals (every third supplier original in the cache, plain), the same 25 changes, against
 * the set a PUBLIC build has. Two columns: the S17 rule as QA re-implemented it (plain against plain: A, or B without
 * the ink guard), and the gate's rule now (site/tools/lib/rights-content.ts `nearestPicture`: the ink guard, the
 * mirrored and trimmed forms). Caught = a match with a picture of the same product.
 *
 *   tsx mut-pixels.mts <site dir> <out.json>
 */
import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { createRequire } from "node:module";
import {
  DhashCache,
  LEDGER_SHOP,
  NEAR_MAX_HAMMING,
  NEAR_MAX_MAD32,
  PIXEL_MAX_HAMMING,
  hamming,
  mad32,
  nearestPicture,
  prepare,
  readLedger,
  sha256,
  supplierSet,
} from "../../../../../site/tools/lib/rights-content";

const [SITE_ARG, OUT] = process.argv.slice(2);
const SITE = resolve(SITE_ARG!);
const sharp = createRequire(join(SITE, "package.json"))(
  "sharp",
) as typeof import("sharp");
const dh = new DhashCache(
  join(process.env.QA_CACHE ?? "/tmp", "s19-mut-dhash.json"),
);
const shop = readLedger(join(SITE, ".generated", LEDGER_SHOP))!;
const set = await supplierSet({
  site: SITE,
  ledgers: [shop],
  cacheDir: join(SITE, ".cache/supplier-images"),
  hosts: [],
  dhashes: dh,
});
const originals = set.pixels
  .filter((p) => p.variant === "plain" && p.file.startsWith(".cache/"))
  .filter((_, i) => i % 3 === 0);

type M = (b: Buffer, w: number, h: number) => Promise<Buffer>;
const S = (b: Buffer) => sharp(b, { failOn: "none" }).rotate();
const MUT: Record<string, M> = {
  "resize 50% (webp q80)": (b, w) =>
    S(b)
      .resize(Math.round(w / 2))
      .webp({ quality: 80 })
      .toBuffer(),
  "resize 25% (jpeg q60)": (b, w) =>
    S(b)
      .resize(Math.round(w / 4))
      .jpeg({ quality: 60 })
      .toBuffer(),
  "thumbnail 160 px (webp)": (b) =>
    S(b).resize(160).webp({ quality: 70 }).toBuffer(),
  "thumbnail 96 px (jpeg q50)": (b) =>
    S(b).resize(96).jpeg({ quality: 50 }).toBuffer(),
  "recompress jpeg q35": (b) => S(b).jpeg({ quality: 35 }).toBuffer(),
  "recompress avif q30": (b) => S(b).avif({ quality: 30 }).toBuffer(),
  "crop 5% each side": (b, w, h) =>
    S(b)
      .extract({
        left: Math.round(w * 0.05),
        top: Math.round(h * 0.05),
        width: Math.round(w * 0.9),
        height: Math.round(h * 0.9),
      })
      .toBuffer(),
  "crop 10% each side": (b, w, h) =>
    S(b)
      .extract({
        left: Math.round(w * 0.1),
        top: Math.round(h * 0.1),
        width: Math.round(w * 0.8),
        height: Math.round(h * 0.8),
      })
      .toBuffer(),
  "crop left third off": (b, w, h) =>
    S(b)
      .extract({
        left: Math.round(w / 3),
        top: 0,
        width: w - Math.round(w / 3),
        height: h,
      })
      .toBuffer(),
  "crop to the top half": (b, w, h) =>
    S(b)
      .extract({ left: 0, top: 0, width: w, height: Math.round(h / 2) })
      .toBuffer(),
  "crop a centre square 60%": (b, w, h) => {
    const s = Math.round(Math.min(w, h) * 0.6);
    return S(b)
      .extract({
        left: Math.round((w - s) / 2),
        top: Math.round((h - s) / 2),
        width: s,
        height: s,
      })
      .toBuffer();
  },
  "pad onto a white 4:3 canvas": (b, w, h) =>
    S(b)
      .extend({
        left: Math.round(w * 0.2),
        right: Math.round(w * 0.2),
        top: 0,
        bottom: Math.round(h * 0.1),
        background: "#ffffff",
      })
      .toBuffer(),
  "grey 3% border": (b, w) =>
    S(b)
      .extend({
        top: Math.round(w * 0.03),
        bottom: Math.round(w * 0.03),
        left: Math.round(w * 0.03),
        right: Math.round(w * 0.03),
        background: "#bbbbbb",
      })
      .toBuffer(),
  "flip left-right": (b) => S(b).flop().toBuffer(),
  "flip upside-down": (b) => S(b).flip().toBuffer(),
  "rotate 3°": (b) => S(b).rotate(3, { background: "#ffffff" }).toBuffer(),
  "brightness +8%": (b) => S(b).modulate({ brightness: 1.08 }).toBuffer(),
  "brightness −10%": (b) => S(b).modulate({ brightness: 0.9 }).toBuffer(),
  "hue +20°": (b) => S(b).modulate({ hue: 20 }).toBuffer(),
  "saturation ×1.3": (b) => S(b).modulate({ saturation: 1.3 }).toBuffer(),
  "warm tint": (b) => S(b).tint({ r: 255, g: 236, b: 210 }).toBuffer(),
  grayscale: (b) => S(b).grayscale().toBuffer(),
  "gamma 1.4": (b) => S(b).gamma(1.4).toBuffer(),
  "blur σ1.5": (b) => S(b).blur(1.5).toBuffer(),
  "a text watermark": (b, w, h) =>
    S(b)
      .composite([
        {
          input: Buffer.from(
            `<svg width="${w}" height="${h}"><text x="5%" y="55%" font-size="${Math.round(h / 8)}" fill="rgba(0,0,0,0.35)" font-family="sans-serif">HOME · DESIGN</text></svg>`,
          ),
        },
      ])
      .toBuffer(),
};

const rows: Record<
  string,
  {
    n: number;
    old: number;
    now: number;
    now_by: Record<string, number>;
    dhash_median: number;
    missed_examples: string[];
  }
> = {};
const t0 = Date.now();
for (const [name, f] of Object.entries(MUT)) {
  let old = 0;
  let now = 0;
  const by: Record<string, number> = {};
  const ds: number[] = [];
  const missed: string[] = [];
  for (const p of originals) {
    const buf = readFileSync(join(SITE, p.file));
    const meta = await sharp(buf, { failOn: "none" })
      .rotate()
      .toBuffer({ resolveWithObject: true });
    let out: Buffer;
    try {
      out = await f(buf, meta.info.width, meta.info.height);
    } catch {
      continue;
    }
    const v = await dh.variants(out, sha256(out), ["plain", "trimmed"]);
    if (!v.plain) continue;
    // the S17 rule: plain against plain, A or B without the ink guard
    let o = false;
    let own = 999;
    for (const q of set.pixels) {
      if (q.product !== p.product || q.variant !== "plain") continue;
      const d = hamming(v.plain.dhash, q.dhash);
      own = Math.min(own, d);
      if (
        d <= PIXEL_MAX_HAMMING ||
        (d <= NEAR_MAX_HAMMING && mad32(v.plain.grey, q.grey) <= NEAR_MAX_MAD32)
      )
        o = true;
    }
    const { best } = nearestPicture(
      {
        plain: prepare(v.plain),
        trimmed: v.trimmed ? prepare(v.trimmed) : null,
      },
      set.pixels,
      PIXEL_MAX_HAMMING,
      (q) => q.product === p.product,
    );
    ds.push(own);
    if (o) old++;
    if (best?.rule) {
      now++;
      const k = `${best.rule} ${best.mine} vs ${best.p.variant}`;
      by[k] = (by[k] ?? 0) + 1;
    } else if (missed.length < 3) missed.push(`${p.product} (dHash ${own})`);
  }
  ds.sort((x, y) => x - y);
  rows[name] = {
    n: ds.length,
    old,
    now,
    now_by: by,
    dhash_median: ds[Math.floor(ds.length / 2)] ?? -1,
    missed_examples: missed,
  };
  console.error(
    `${name}: S17 ${old}/${ds.length} → now ${now}/${ds.length} (${((Date.now() - t0) / 1000).toFixed(0)}s)`,
  );
  dh.save();
}
dh.save();
writeFileSync(
  OUT!,
  JSON.stringify(
    { originals: originals.length, public_set: set.stats, rows },
    null,
    1,
  ),
);
console.log(
  `S19 mut-pixels (${originals.length} originals, every third of the cache; caught = a match with the same product): S17 rule → now`,
);
for (const [k, r] of Object.entries(rows))
  console.log(
    `  ${k.padEnd(28)} ${String(r.old).padStart(3)}/${r.n} → ${String(r.now).padStart(3)}/${r.n}  ${JSON.stringify(r.now_by)}`,
  );
