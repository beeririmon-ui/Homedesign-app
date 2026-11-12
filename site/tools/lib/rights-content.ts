/**
 * S17, QA ת45: the image-rights gate by content, not by path (tools/check-image-rights.ts).
 *
 * The S15 gate knew a supplier picture only by its path (media/products/<id>/…). The same picture under another name
 * (R2), a hotlink to the supplier's CDN (R3), an inlined data: URI (R4) or the story's own re-encoded copies (R6) passed
 * it. Here a supplier picture is known by what it is:
 *
 * - **The ledger (bytes):** every pipeline that writes a file from a supplier picture records the file's sha256, with
 *   the product and the card's rights: tools/supplier-images.ts (the shop's photos and option pictures, and every cached
 *   original it read) and tools/make-story.ts (the story's copies, every width). The gate also hashes every file of the
 *   cache itself, listed or not.
 * - **Pixels:** a 16×16 difference hash (dHash, 256 bits) of every supplier picture (each cached original, and the
 *   largest width of each derived picture), against every raster of the build and every data: URI in its text files.
 *   Hamming ≤ 24 of 256 is a match (QA's threshold). A small copy (the story's 160 px) loses dHash bits in the flat
 *   white of a product photo: 9 of the story's 321 copies are 25–40 bits away from their picture (QA's own scan found
 *   them by its second test, the 32×32 grey difference). So a near miss (Hamming ≤ 48) is also a match when the mean
 *   absolute difference of the 32×32 grey images is ≤ 3 of 255 (those 9: 0.2–1.9). MAD alone is not used: a product
 *   layer of the room (a small product on white) is 5.5 from a supplier's photo on white.
 * - **Hosts:** the hosts the cards' pictures come from (`images.urls`, an option's `image`) and their registrable domains
 *   (alicdn.com, cjdropshipping.com, zendrop.com): a URL on one anywhere in the build is a hotlink.
 *
 * A picture whose card's rights are `confirmed` may ship; every other one (unclear, none, or a cached file no ledger
 * names) may not. dHashes are cached by sha256 in .cache/rights-dhash.json, so a second build hashes only new files.
 */
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, statSync, writeFileSync } from 'node:fs';
import { dirname, extname, join, relative } from 'node:path';
import sharp from 'sharp';
import { shipsPublicly, type Rights } from './image-rights';

/** where a supplier-derived file came from */
export type LedgerSource = 'shop' | 'story' | 'cache';
export type LedgerEntry = {
  /** the file, relative to site/ (web/public/media/…, .cache/supplier-images/…) */
  file: string;
  sha256: string;
  /** the card id (the cache's originals) or the product's public id (the media files) */
  product: string;
  rights: Rights;
  source: LedgerSource;
  /** the picture this file is one width of (products/<id>/photo, story/products/<id>/<key>); the original for the cache */
  picture: string;
  width?: number;
};
export type Ledger = { generated_at: string; source: LedgerSource | 'shop+cache'; entries: LedgerEntry[] };

/** the ledgers, one per pipeline */
export const LEDGER_SHOP = 'rights/shop.json';
export const LEDGER_STORY = 'rights/story.json';

export const sha256 = (b: Buffer | Uint8Array): string => createHash('sha256').update(b).digest('hex');

export function writeLedger(file: string, ledger: Ledger): void {
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, JSON.stringify(ledger, null, 1));
}
export function readLedger(file: string): Ledger | null {
  return existsSync(file) ? (JSON.parse(readFileSync(file, 'utf8')) as Ledger) : null;
}

// ---------------------------------------------------------------- pixels

/** QA's threshold: a raster within 24 of 256 bits of a supplier picture is that picture */
export const PIXEL_MAX_HAMMING = 24;
/** a near miss of the dHash … */
export const NEAR_MAX_HAMMING = 48;
/** … is a match when the 32×32 grey images differ by at most this much on average (0–255) */
export const NEAR_MAX_MAD32 = 3;

/** what the pixel check compares: the dHash (64 hex) and the 32×32 grey image (1024 bytes) */
export type Fingerprint = { dhash: string; grey: Buffer };

/**
 * The fingerprint of an image (null: not an image sharp can read). Oriented as the pipelines orient (EXIF), flattened
 * on white, grey. The dHash: 17×16, a bit per pair of neighbours in a row (left darker than right).
 */
export async function fingerprint(buf: Buffer | Uint8Array): Promise<Fingerprint | null> {
  try {
    const base = sharp(buf, { failOn: 'none', animated: false }).rotate().flatten({ background: '#ffffff' }).greyscale();
    const [g, grey] = await Promise.all([
      base.clone().resize(17, 16, { fit: 'fill' }).raw().toBuffer(),
      base.clone().resize(32, 32, { fit: 'fill' }).raw().toBuffer(),
    ]);
    if (g.length < 17 * 16 || grey.length < 1024) return null;
    const bytes = new Uint8Array(32);
    for (let y = 0; y < 16; y++)
      for (let x = 0; x < 16; x++) {
        const i = y * 16 + x;
        if (g[y * 17 + x]! < g[y * 17 + x + 1]!) bytes[i >> 3]! |= 1 << (7 - (i & 7));
      }
    return { dhash: Buffer.from(bytes).toString('hex'), grey: grey.subarray(0, 1024) };
  } catch {
    return null;
  }
}
/** the dHash alone */
export const dhash = async (buf: Buffer | Uint8Array): Promise<string | null> => (await fingerprint(buf))?.dhash ?? null;

/** the mean absolute difference of two 32×32 grey images (0–255) */
export function mad32(a: Buffer, b: Buffer): number {
  let s = 0;
  for (let i = 0; i < 1024; i++) s += Math.abs(a[i]! - b[i]!);
  return s / 1024;
}

const POP = new Uint8Array(256).map((_, i) => {
  let n = 0;
  for (let v = i; v; v >>= 1) n += v & 1;
  return n;
});
/** the number of differing bits of two hashes of the same length (hex) */
export function hamming(a: string, b: string): number {
  let d = 0;
  for (let i = 0; i < a.length; i += 2) d += POP[parseInt(a.slice(i, i + 2), 16) ^ parseInt(b.slice(i, i + 2), 16)]!;
  return d;
}

/** fingerprints by sha256, kept between builds (.cache/rights-dhash.json) */
export class DhashCache {
  private map = new Map<string, Fingerprint | null>();
  private dirty = false;
  constructor(private readonly file?: string) {
    if (file && existsSync(file))
      try {
        for (const [k, v] of Object.entries(JSON.parse(readFileSync(file, 'utf8')) as Record<string, string | null>)) {
          if (v === null) this.map.set(k, null);
          else {
            const [d, g] = v.split(':');
            // an entry of an older shape is computed again
            if (d && g) this.map.set(k, { dhash: d, grey: Buffer.from(g, 'base64') });
          }
        }
      } catch {
        /* a broken cache is rebuilt */
      }
  }
  async of(buf: Buffer | Uint8Array, sha = sha256(buf)): Promise<Fingerprint | null> {
    if (this.map.has(sha)) return this.map.get(sha)!;
    const f = await fingerprint(buf);
    this.map.set(sha, f);
    this.dirty = true;
    return f;
  }
  save(): void {
    if (!this.file || !this.dirty) return;
    mkdirSync(dirname(this.file), { recursive: true });
    // another run (a test, a second build) may read it meanwhile: written whole, then moved into place
    const tmp = `${this.file}.${process.pid}.tmp`;
    const out = Object.fromEntries([...this.map].map(([k, v]) => [k, v ? `${v.dhash}:${v.grey.toString('base64')}` : null]));
    writeFileSync(tmp, JSON.stringify(out));
    renameSync(tmp, this.file);
    this.dirty = false;
  }
}

// ---------------------------------------------------------------- hosts

/** the registrable domain of a host: the last two labels, three under a two-letter country's second level (co.il) */
export function registrableDomain(host: string): string {
  const p = host.toLowerCase().split('.');
  const n = p.length >= 3 && p[p.length - 1]!.length === 2 && /^(?:co|com|net|org|gov|ac)$/.test(p[p.length - 2]!) ? 3 : 2;
  return p.slice(-n).join('.');
}

/** The hosts a card's pictures come from: `images.urls`, an option's `image`, a variant's `supplier_image_url`. */
export function cardPictureHosts(cards: unknown[]): string[] {
  const hosts = new Set<string>();
  const add = (u: unknown) => {
    if (typeof u !== 'string') return;
    const m = /^(?:https?:)?\/\/([a-z0-9.-]+)/i.exec(u.trim());
    if (m) hosts.add(m[1]!.toLowerCase());
  };
  const walk = (o: unknown, key: string): void => {
    if (Array.isArray(o)) for (const v of o) walk(v, key);
    else if (o && typeof o === 'object') for (const [k, v] of Object.entries(o)) walk(v, k);
    else if (/^(?:urls|image|images|supplier_image_url|image_url|photo|photos)$/i.test(key)) add(o);
  };
  for (const c of cards) walk(c, '');
  return [...hosts].sort();
}

/** every card under data/products (a slot's folder of cards) */
export function readCards(dir: string): unknown[] {
  const out: unknown[] = [];
  const walk = (d: string): void => {
    for (const n of readdirSync(d)) {
      const p = join(d, n);
      if (statSync(p).isDirectory()) walk(p);
      else if (n.endsWith('.json'))
        try {
          out.push(JSON.parse(readFileSync(p, 'utf8')));
        } catch {
          /* not a card */
        }
    }
  };
  if (existsSync(dir)) walk(dir);
  return out;
}

/** A pattern for a URL (or a bare mention) of one of these hosts, or of any host under their registrable domains. */
export function hostPattern(hosts: string[]): RegExp | null {
  const domains = [...new Set(hosts.map(registrableDomain))].sort();
  if (!domains.length) return null;
  const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return new RegExp(`(?<![a-z0-9-])(?:[a-z0-9-]+\\.)*(?:${domains.map(esc).join('|')})(?![a-z0-9-])`, 'gi');
}

// ---------------------------------------------------------------- the supplier set

export type SupplierPicture = { picture: string; product: string; rights: Rights | 'unknown'; file: string; dhash: string; grey: Buffer };
export type SupplierSet = {
  /** sha256 → what it is (a file that may not ship wins over one that may) */
  bySha: Map<string, { file: string; product: string; rights: Rights | 'unknown'; source: LedgerSource }>;
  /** one dHash per picture that may not ship */
  pixels: SupplierPicture[];
  hosts: string[];
  stats: { ledger_entries: number; cached_originals: number; unlisted_cached: number; withheld_files: number; pictures: number };
};

const RASTER = new Set(['.webp', '.avif', '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tif', '.tiff', '.bin']);

/**
 * The supplier set: every ledger entry, every file of the cache (an original no ledger names counts as not shippable),
 * and a dHash per picture whose rights are not confirmed (the cached original and the largest derived width).
 */
export async function supplierSet(o: { site: string; ledgers: Ledger[]; cacheDir: string; hosts: string[]; dhashes: DhashCache }): Promise<SupplierSet> {
  const bySha: SupplierSet['bySha'] = new Map();
  const put = (sha: string, v: { file: string; product: string; rights: Rights | 'unknown'; source: LedgerSource }) => {
    const have = bySha.get(sha);
    if (!have || (shipsPublicly(have.rights as Rights) && !shipsPublicly(v.rights as Rights))) bySha.set(sha, v);
  };
  const entries = o.ledgers.flatMap((l) => l.entries);
  for (const e of entries) put(e.sha256, { file: e.file, product: e.product, rights: e.rights, source: e.source });
  // every original in the cache, by its own bytes (the ledger may be older than the cache)
  let cached = 0;
  let unlisted = 0;
  const cacheFiles = existsSync(o.cacheDir) ? readdirSync(o.cacheDir).filter((n) => !n.startsWith('.')) : [];
  const cacheRows: { file: string; sha: string; buf: Buffer }[] = [];
  for (const n of cacheFiles) {
    const file = join(o.cacheDir, n);
    if (!statSync(file).isFile()) continue;
    const buf = readFileSync(file);
    const sha = sha256(buf);
    cached++;
    if (!bySha.has(sha)) {
      unlisted++;
      put(sha, { file: relative(o.site, file), product: 'unknown', rights: 'unknown', source: 'cache' });
    }
    cacheRows.push({ file: relative(o.site, file), sha, buf });
  }
  // the pictures that may not ship: the original, and the largest width of each derived one
  const largest = new Map<string, LedgerEntry>();
  for (const e of entries) {
    if (shipsPublicly(e.rights) || e.source === 'cache') continue;
    const have = largest.get(e.picture);
    if (!have || (have.width ?? 0) < (e.width ?? 0)) largest.set(e.picture, e);
  }
  const pixels: SupplierPicture[] = [];
  for (const e of largest.values()) {
    const path = join(o.site, e.file);
    if (!existsSync(path)) continue;
    const h = await o.dhashes.of(readFileSync(path), e.sha256);
    if (h) pixels.push({ picture: e.picture, product: e.product, rights: e.rights, file: e.file, ...h });
  }
  for (const c of cacheRows) {
    const what = bySha.get(c.sha)!;
    if (shipsPublicly(what.rights as Rights)) continue;
    const h = await o.dhashes.of(c.buf, c.sha);
    if (h) pixels.push({ picture: c.file, product: what.product, rights: what.rights, file: c.file, ...h });
  }
  return {
    bySha,
    pixels,
    hosts: o.hosts,
    stats: {
      ledger_entries: entries.length,
      cached_originals: cached,
      unlisted_cached: unlisted,
      withheld_files: [...bySha.values()].filter((v) => !shipsPublicly(v.rights as Rights)).length,
      pictures: pixels.length,
    },
  };
}

// ---------------------------------------------------------------- the scan

export type ContentFinding = {
  /** the build's file (relative to dist), with the data: URI's number when it is one */
  where: string;
  how: 'bytes' | 'pixels' | 'data-uri bytes' | 'data-uri pixels' | 'host';
  what: string;
  product?: string;
  hamming?: number;
  mad32?: number;
};
export type ScanStats = {
  files: number;
  rasters: number;
  data_uris: number;
  text_files: number;
  nearest: { where: string; picture: string; hamming: number; mad32: number | null }[];
  /** the smallest 32×32 grey difference of a near miss that is not a match (the margin of the second test) */
  nearest_by_grey: { where: string; picture: string; hamming: number; mad32: number }[];
};

const TEXT_EXT = /\.(?:html?|js|mjs|cjs|css|json|xml|txt|webmanifest|svg|map|md)$/i;
/** extensionless files a static host reads (_headers, _redirects) are text too */
const isText = (rel: string) => TEXT_EXT.test(rel) || !extname(rel);
const DATA_URI = /data:([a-z0-9.+/-]*)((?:;[a-z0-9=._-]+)*);base64,([A-Za-z0-9+/]{16,}={0,2})/gi;

/**
 * Every file of a build against the supplier set: equal bytes, a raster or a data: URI within the pixel threshold of a
 * picture that may not ship, and any URL on a supplier picture host. `skip` leaves files out (behind the flag: none).
 */
export async function scanBuild(
  dist: string,
  set: SupplierSet,
  dhashes: DhashCache,
  opts: { files?: string[]; maxHamming?: number } = {},
): Promise<{ findings: ContentFinding[]; stats: ScanStats }> {
  const max = opts.maxHamming ?? PIXEL_MAX_HAMMING;
  const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
  const files = (opts.files ?? walk(dist).map((f) => relative(dist, f))).map((f) => f.split('\\').join('/')).sort();
  const hostRe = hostPattern(set.hosts);
  const findings: ContentFinding[] = [];
  const stats: ScanStats = { files: files.length, rasters: 0, data_uris: 0, text_files: 0, nearest: [], nearest_by_grey: [] };
  const withheld = (sha: string) => {
    const v = set.bySha.get(sha);
    return v && !shipsPublicly(v.rights as Rights) ? v : null;
  };
  const near = async (where: string, buf: Buffer, sha: string, how: 'pixels' | 'data-uri pixels') => {
    const h = await dhashes.of(buf, sha);
    if (!h) return;
    stats.rasters++;
    // the nearest by dHash; a near miss confirmed by the 32×32 grey difference is a match too
    let best: { d: number; p: SupplierPicture; m: number | null } | null = null;
    let grey: { d: number; p: SupplierPicture; m: number } | null = null;
    for (const p of set.pixels) {
      const d = hamming(h.dhash, p.dhash);
      const m = d <= NEAR_MAX_HAMMING ? mad32(h.grey, p.grey) : null;
      const match = d <= max || (m !== null && m <= NEAR_MAX_MAD32);
      if (!match && m !== null && (!grey || m < grey.m)) grey = { d, p, m };
      const bestMatch = best && (best.d <= max || (best.m !== null && best.m <= NEAR_MAX_MAD32));
      if (!best || (match && !bestMatch) || (match === !!bestMatch && d < best.d)) best = { d, p, m };
    }
    if (!best) return;
    if (grey) stats.nearest_by_grey.push({ where, picture: grey.p.picture, hamming: grey.d, mad32: Number(grey.m.toFixed(1)) });
    stats.nearest.push({ where, picture: best.p.picture, hamming: best.d, mad32: best.m === null ? null : Number(best.m.toFixed(1)) });
    if (best.d <= max || (best.m !== null && best.m <= NEAR_MAX_MAD32))
      findings.push({
        where,
        how,
        what: `looks like ${best.p.picture} (${best.p.product}, rights: ${best.p.rights}; dHash ${best.d}/256${best.m === null ? '' : `, 32×32 grey ${best.m.toFixed(1)}`})`,
        product: best.p.product,
        hamming: best.d,
        mad32: best.m === null ? undefined : Number(best.m.toFixed(2)),
      });
  };
  for (const rel of files) {
    const buf = readFileSync(join(dist, rel));
    const sha = sha256(buf);
    const w = withheld(sha);
    if (w) findings.push({ where: rel, how: 'bytes', what: `the same bytes as ${w.file} (${w.product}, rights: ${w.rights})`, product: w.product });
    else if (RASTER.has(extname(rel).toLowerCase()) || /^image\//.test(sniff(buf))) await near(rel, buf, sha, 'pixels');
    if (!isText(rel)) continue;
    stats.text_files++;
    const text = buf.toString('utf8');
    if (hostRe)
      for (const m of text.matchAll(hostRe)) {
        findings.push({
          where: rel,
          how: 'host',
          what: `a URL on a supplier picture host: ${m[0]} (…${text.slice(Math.max(0, m.index - 30), m.index + m[0].length + 30).replace(/\s+/g, ' ')}…)`,
        });
      }
    let k = 0;
    for (const m of text.matchAll(DATA_URI)) {
      k++;
      stats.data_uris++;
      const bytes = Buffer.from(m[3]!, 'base64');
      const where = `${rel} (data: URI #${k}, ${bytes.length} B)`;
      const s = sha256(bytes);
      const wd = withheld(s);
      if (wd) {
        findings.push({ where, how: 'data-uri bytes', what: `the same bytes as ${wd.file} (${wd.product}, rights: ${wd.rights})`, product: wd.product });
        continue;
      }
      // an inlined SVG may itself carry a picture or a hotlink: one level down
      if (/svg/i.test(m[1]!)) {
        const inner = bytes.toString('utf8');
        if (hostRe) for (const x of inner.matchAll(hostRe)) findings.push({ where, how: 'host', what: `a URL on a supplier picture host inside an inlined SVG: ${x[0]}` });
        for (const x of inner.matchAll(DATA_URI)) {
          const b = Buffer.from(x[3]!, 'base64');
          if (withheld(sha256(b))) findings.push({ where, how: 'data-uri bytes', what: 'a supplier picture inside an inlined SVG' });
          else await near(`${where} (inner)`, b, sha256(b), 'data-uri pixels');
        }
        continue;
      }
      await near(where, bytes, s, 'data-uri pixels');
    }
  }
  stats.nearest.sort((a, b) => a.hamming - b.hamming);
  stats.nearest = stats.nearest.slice(0, 10);
  stats.nearest_by_grey.sort((a, b) => a.mad32 - b.mad32);
  stats.nearest_by_grey = stats.nearest_by_grey.slice(0, 10);
  return { findings, stats };
}

/** a file's type by its first bytes (a picture under another extension is still a picture) */
function sniff(b: Buffer): string {
  if (b.length < 12) return '';
  if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
  if (b[0] === 0x89 && b.toString('latin1', 1, 4) === 'PNG') return 'image/png';
  if (b.toString('latin1', 0, 4) === 'RIFF' && b.toString('latin1', 8, 12) === 'WEBP') return 'image/webp';
  if (b.toString('latin1', 4, 8) === 'ftyp' && /avi[fs]|heic|mif1/.test(b.toString('latin1', 8, 12))) return 'image/avif';
  if (b.toString('latin1', 0, 3) === 'GIF') return 'image/gif';
  return '';
}
