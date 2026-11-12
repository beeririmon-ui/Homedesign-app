/**
 * qa-agent, S15 (2026-11-11): my own byte-level scan of a public build (HD_PUBLIC=1) for any supplier picture.
 *
 *   node rights-scan.mjs <public dist> <supplier set dir> <cache dir> <cards dir> <out.json>
 *
 * The supplier set: every file the flag build writes under media/products (product photos and option pictures, every
 * width) plus every cached original the build downloaded (.cache/supplier-images/*.bin). Then, over every file of the
 * public dist:
 *   1. bytes: the sha256 of the file equals a supplier file's;
 *   2. containment: a 48-byte signature from the middle of each supplier file found anywhere inside a dist file;
 *   3. data: URIs in text files decoded, and checked by 1 and 4;
 *   4. pixels: every raster image (webp, avif, jpg, png, gif, and the decoded data: URIs) reduced to a 16×16 grey
 *      difference hash and compared with every supplier picture's (Hamming ≤ 24 of 256 flags it for a look, with a
 *      32×32 mean absolute difference as the second test);
 *   5. text: any reference to media/products/, any URL on a host the cards' pictures come from (alicdn, cjdropshipping,
 *      zendrop, aliexpress, …), every og:image / twitter:image / JSON-LD image named, and where it points.
 * Sharp comes from the copy's node_modules (NODE_PATH).
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join, relative, extname } from 'node:path';
import { createRequire } from 'node:module';
const sharp = createRequire((process.env.NODE_PATH ?? '').split(':')[0] + '/../package.json')('sharp');

const [DIST, SUPDIR, CACHE, CARDS, OUT] = process.argv.slice(2);
const walk = (d) => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
const sha = (b) => createHash('sha256').update(b).digest('hex');
const RASTER = new Set(['.webp', '.avif', '.jpg', '.jpeg', '.png', '.gif']);
const TEXT = /\.(html|js|mjs|css|json|xml|txt|webmanifest|svg|map)$/i;

async function dhash(buf) {
  try {
    const g = await sharp(buf, { failOn: 'none', animated: false }).flatten({ background: '#ffffff' }).greyscale().resize(17, 16, { fit: 'fill' }).raw().toBuffer();
    const bits = [];
    for (let y = 0; y < 16; y++) for (let x = 0; x < 16; x++) bits.push(g[y * 17 + x] < g[y * 17 + x + 1] ? 1 : 0);
    const small = await sharp(buf, { failOn: 'none', animated: false }).flatten({ background: '#ffffff' }).greyscale().resize(32, 32, { fit: 'fill' }).raw().toBuffer();
    const meta = await sharp(buf, { failOn: 'none' }).metadata();
    return { bits, small, w: meta.width, h: meta.height };
  } catch (e) {
    return null;
  }
}
const ham = (a, b) => a.reduce((n, v, i) => n + (v !== b[i] ? 1 : 0), 0);
const mad = (a, b) => {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += Math.abs(a[i] - b[i]);
  return s / a.length;
};

// ---- the supplier set
const supFiles = [...walk(SUPDIR).filter((f) => RASTER.has(extname(f).toLowerCase())), ...walk(CACHE).filter((f) => f.endsWith('.bin'))];
const supByHash = new Map();
const supSigs = [];
const supHashes = [];
for (const f of supFiles) {
  const b = readFileSync(f);
  supByHash.set(sha(b), f);
  if (b.length > 400) supSigs.push({ f, sig: b.subarray(Math.floor(b.length / 2), Math.floor(b.length / 2) + 48) });
}
// pixel hashes: one per picture (the flag build's largest width of each, and every cached original)
const byPicture = new Map();
for (const f of supFiles) {
  const key = f.startsWith(SUPDIR) ? relative(SUPDIR, f).replace(/\.\d+\.(webp|avif)$/, '') : f;
  const w = Number(/\.(\d+)\.(webp|avif)$/.exec(f)?.[1] ?? 1e9);
  if (!byPicture.has(key) || byPicture.get(key).w < w) byPicture.set(key, { f, w });
}
for (const { f } of byPicture.values()) {
  const h = await dhash(readFileSync(f));
  if (h) supHashes.push({ f, ...h });
}

// ---- the card hosts (where supplier pictures live)
const hosts = new Set();
for (const f of walk(CARDS).filter((x) => x.endsWith('.json'))) {
  const t = readFileSync(f, 'utf8');
  for (const m of t.matchAll(/https?:\/\/([a-z0-9.-]+)\/[^"\s]*\.(?:jpe?g|png|webp|avif|gif)/gi)) hosts.add(m[1].toLowerCase());
}
const hostRe = new RegExp(`(?:${[...hosts].map((h) => h.replace(/\./g, '\\.')).join('|')}|alicdn\\.com|cjdropshipping\\.com|zendrop\\.com|aliexpress\\.(?:com|us|ru))`, 'gi');

// ---- the public dist
const distFiles = walk(DIST);
const res = {
  dist: DIST,
  dist_files: distFiles.length,
  supplier_set: { files: supFiles.length, pictures: supHashes.length, card_picture_hosts: hosts.size },
  bytes_equal: [],
  contained: [],
  data_uris: { count: 0, images: 0, flagged: [] },
  pixel_flagged: [],
  pixel_nearest: [],
  text: { media_products_refs: [], supplier_host_urls: [], og_images: [], jsonld_images: [] },
  rasters_checked: 0,
};
const rasters = [];
for (const f of distFiles) {
  const rel = relative(DIST, f);
  const b = readFileSync(f);
  if (supByHash.has(sha(b))) res.bytes_equal.push({ rel, supplier: relative(SUPDIR, supByHash.get(sha(b))) });
  for (const s of supSigs) if (b.includes(s.sig)) res.contained.push({ rel, supplier: s.f.startsWith(SUPDIR) ? relative(SUPDIR, s.f) : s.f });
  if (RASTER.has(extname(f).toLowerCase())) rasters.push({ rel, buf: b });
  if (TEXT.test(f)) {
    const t = b.toString('utf8');
    for (const m of t.matchAll(/media\/products\/[^"'\s)]*/g)) res.text.media_products_refs.push({ rel, ref: m[0].slice(0, 120) });
    for (const m of t.matchAll(hostRe)) res.text.supplier_host_urls.push({ rel, host: m[0], at: t.slice(Math.max(0, m.index - 40), m.index + 60) });
    for (const m of t.matchAll(/<meta[^>]+(?:property|name)="(?:og:image|twitter:image)[^"]*"[^>]*>/g)) res.text.og_images.push({ rel, tag: m[0] });
    for (const m of t.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
      try {
        const walkLd = (o) => {
          if (Array.isArray(o)) return o.forEach(walkLd);
          if (o && typeof o === 'object')
            for (const [k, v] of Object.entries(o)) {
              if (k === 'image') for (const u of [v].flat()) res.text.jsonld_images.push({ rel, image: String(u) });
              else walkLd(v);
            }
        };
        walkLd(JSON.parse(m[1]));
      } catch {
        /* not JSON */
      }
    }
    for (const m of t.matchAll(/data:image\/[a-z0-9.+-]+;base64,([A-Za-z0-9+/=]{40,})/g)) {
      res.data_uris.count++;
      const buf = Buffer.from(m[1], 'base64');
      if (supByHash.has(sha(buf))) res.data_uris.flagged.push({ rel, how: 'bytes', supplier: supByHash.get(sha(buf)) });
      rasters.push({ rel: `${rel} (data: URI #${res.data_uris.count}, ${buf.length} B)`, buf, data: true });
      res.data_uris.images++;
    }
  }
}
// pixels
for (const r of rasters) {
  const h = await dhash(r.buf);
  if (!h) continue;
  res.rasters_checked++;
  let best = null;
  for (const s of supHashes) {
    const d = ham(h.bits, s.bits);
    if (!best || d < best.d) best = { d, s };
  }
  if (!best) continue;
  const m = mad(h.small, best.s.small);
  const row = { rel: r.rel, nearest: best.s.f.startsWith(SUPDIR) ? relative(SUPDIR, best.s.f) : best.s.f, hamming256: best.d, mad32: Number(m.toFixed(1)) };
  res.pixel_nearest.push(row);
  if (best.d <= 24 || m <= 6) res.pixel_flagged.push(row);
}
res.pixel_nearest.sort((a, b) => a.hamming256 - b.hamming256);
res.pixel_nearest = res.pixel_nearest.slice(0, 12);
res.verdict =
  res.bytes_equal.length + res.contained.length + res.data_uris.flagged.length + res.pixel_flagged.length + res.text.media_products_refs.length + res.text.supplier_host_urls.length === 0
    ? 'clean: 0 supplier pictures (bytes, containment, data URIs, pixels, paths, hosts)'
    : 'SUPPLIER PICTURE FOUND';
writeFileSync(OUT, JSON.stringify(res, null, 1));
console.log(
  `rights-scan ${DIST}: ${res.verdict}\n  dist files ${res.dist_files}, rasters checked ${res.rasters_checked} (data URIs ${res.data_uris.images}); supplier set ${supFiles.length} files / ${supHashes.length} pictures, ${hosts.size} card hosts\n  bytes ${res.bytes_equal.length}, contained ${res.contained.length}, data-URI ${res.data_uris.flagged.length}, pixels ${res.pixel_flagged.length}, media/products refs ${res.text.media_products_refs.length}, supplier-host URLs ${res.text.supplier_host_urls.length}; og/twitter images ${res.text.og_images.length}; JSON-LD images ${res.text.jsonld_images.length} (${[...new Set(res.text.jsonld_images.map((x) => x.image.replace(/^https?:\/\/[^/]+/, '').split('/').slice(0, 3).join('/')))].join(', ')})\n  nearest: ${res.pixel_nearest
    .slice(0, 3)
    .map((r) => `${r.rel} ~ ${r.nearest} (h ${r.hamming256}, mad ${r.mad32})`)
    .join('; ')}`,
);
