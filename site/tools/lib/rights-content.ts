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
 * S19, QA S17:
 * - **ת50, the ink guard:** the near miss is a match only when both 32×32 grey images carry ink (mean of 255 − grey ≥ 4).
 *   Without it a near-blank picture (a layer that is mostly transparent, a white canvas, a thin lamp on white) is 2–3
 *   from another near-blank picture: 124 of our own warm-modern layers matched one supplier photo of a thin floor lamp.
 * - **ת51:** each supplier picture is also hashed mirrored (left-right), and every picture, ours and theirs, is also
 *   hashed with its uniform margins trimmed (a padded copy, a copy in a frame or a border, a letterboxed card, a crop
 *   that only cuts margin). A fixed list of supplier picture domains (`SUPPLIER_IMAGE_DOMAINS`) stands beside the cards'
 *   hosts (aliexpress-media.com, which no card names). A data: URI is read as a browser reads it: CSS escapes and line
 *   continuations, percent escapes, character references and whitespace inside it are removed before it is decoded.
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
/** … is a match when the 32×32 grey images differ by at most this much on average (0–255) … */
export const NEAR_MAX_MAD32 = 3;
/** … and (S19, QA ת50) both carry at least this much ink: the mean of 255 − grey over the 32×32 image */
export const NEAR_MIN_INK = 4;

/** what the pixel check compares: the dHash (64 hex) and the 32×32 grey image (1024 bytes) */
export type Fingerprint = { dhash: string; grey: Buffer };
/**
 * S19, QA ת51: the forms a picture is hashed in. `mirrored` is flipped left-right; `trimmed` has its uniform margins
 * (white, transparent, a border of one colour, then the white inside it) cut away first. A picture without margins has
 * no trimmed form (null): its plain form is its trimmed form.
 */
export type Variant = 'plain' | 'mirrored' | 'trimmed' | 'trimmed-mirrored';
export const VARIANTS: readonly Variant[] = ['plain', 'mirrored', 'trimmed', 'trimmed-mirrored'];

/** the dHash and the 32×32 grey image of a grey picture already decoded (raw, one channel) */
async function hashRaw(img: sharp.Sharp): Promise<Fingerprint | null> {
  // greyscale on the way out too: a one-channel raw input would otherwise come out as three channels (sRGB)
  const [g, grey] = await Promise.all([
    img.clone().resize(17, 16, { fit: 'fill' }).greyscale().raw().toBuffer(),
    img.clone().resize(32, 32, { fit: 'fill' }).greyscale().raw().toBuffer(),
  ]);
  if (g.length < 17 * 16 || grey.length < 1024) return null;
  const bytes = new Uint8Array(32);
  for (let y = 0; y < 16; y++)
    for (let x = 0; x < 16; x++) {
      const i = y * 16 + x;
      if (g[y * 17 + x]! < g[y * 17 + x + 1]!) bytes[i >> 3]! |= 1 << (7 - (i & 7));
    }
  return { dhash: Buffer.from(bytes).toString('hex'), grey: grey.subarray(0, 1024) };
}

/**
 * The fingerprint of an image (null: not an image sharp can read). Oriented as the pipelines orient (EXIF), flattened
 * on white, grey. The dHash: 17×16, a bit per pair of neighbours in a row (left darker than right).
 */
export async function fingerprint(buf: Buffer | Uint8Array): Promise<Fingerprint | null> {
  try {
    return await hashRaw(sharp(buf, { failOn: 'none', animated: false }).rotate().flatten({ background: '#ffffff' }).greyscale());
  } catch {
    return null;
  }
}
/** the dHash alone */
export const dhash = async (buf: Buffer | Uint8Array): Promise<string | null> => (await fingerprint(buf))?.dhash ?? null;

/** S19 (ת51): a margin pixel differs from the margin's colour by at most this much (JPEG noise on white) */
const TRIM_THRESHOLD = 8;
/** the version of the trim and the variants, in the cache's keys */
const TRIM_VERSION = 't5';
/**
 * S19, QA ת51: the box inside a grey picture's uniform margins, or null when there is nothing to trim (less than 2% of
 * the area) or nothing left (a blank picture, a dot under 12 px or 4% of a side, or what is left carries no ink).
 * As an image editor trims: from each side inward, a row or a column goes while it is the colour at the corner of what
 * is left (99.5% of its pixels within 8 of it), so the trim stops at the first line with content in it and never cuts
 * into a picture whose own background is near the frame's colour. Up to three passes, each from the new corner: a frame
 * or a border, then the white inside it. A margin on some sides only (padding onto a 4:3 canvas, a letterbox) goes too.
 */
export function trimBox(g: Uint8Array, w: number, h: number): { left: number; top: number; width: number; height: number } | null {
  let x0 = 0;
  let y0 = 0;
  let x1 = w - 1;
  let y1 = h - 1;
  const near = (v: number, bg: number) => v - bg <= TRIM_THRESHOLD && bg - v <= TRIM_THRESHOLD;
  const row = (y: number, bg: number) => {
    let off = 0;
    const most = Math.floor((x1 - x0 + 1) * 0.005);
    for (let x = x0; x <= x1; x++) if (!near(g[y * w + x]!, bg) && ++off > most) return false;
    return true;
  };
  const col = (x: number, bg: number) => {
    let off = 0;
    const most = Math.floor((y1 - y0 + 1) * 0.005);
    for (let y = y0; y <= y1; y++) if (!near(g[y * w + x]!, bg) && ++off > most) return false;
    return true;
  };
  for (let pass = 0; pass < 3; pass++) {
    const bg = g[y0 * w + x0]!;
    const before = [x0, y0, x1, y1];
    while (y0 <= y1 && row(y0, bg)) y0++;
    while (y1 >= y0 && row(y1, bg)) y1--;
    while (x0 <= x1 && y0 <= y1 && col(x0, bg)) x0++;
    while (x1 >= x0 && y0 <= y1 && col(x1, bg)) x1--;
    // all of it one colour: on the first pass a blank picture; later, a box of one colour (what is left is the box)
    if (y0 > y1 || x0 > x1) {
      if (pass === 0) return null;
      [x0, y0, x1, y1] = before as [number, number, number, number];
      break;
    }
    if (x0 === before[0] && y0 === before[1] && x1 === before[2] && y1 === before[3]) break;
  }
  const width = x1 - x0 + 1;
  const height = y1 - y0 + 1;
  if (width * height >= 0.98 * w * h) return null;
  if (width < Math.max(12, w * 0.04) || height < Math.max(12, h * 0.04)) return null;
  // what is left must carry ink (ת50's measure): a blank canvas inside a frame is no picture
  let ink = 0;
  for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) ink += 255 - g[y * w + x]!;
  if (ink / (width * height) < NEAR_MIN_INK) return null;
  return { left: x0, top: y0, width, height };
}

/** S19 (ת51): the variants of an image, from one decode (null: not an image, or a variant it does not have) */
export async function fingerprintVariants(buf: Buffer | Uint8Array, want: readonly Variant[]): Promise<Partial<Record<Variant, Fingerprint | null>>> {
  const out: Partial<Record<Variant, Fingerprint | null>> = {};
  if (want.includes('plain')) out.plain = await fingerprint(buf);
  const rest = want.filter((v) => v !== 'plain');
  if (!rest.length) return out;
  try {
    const { data, info } = await sharp(buf, { failOn: 'none', animated: false })
      .rotate()
      .flatten({ background: '#ffffff' })
      .greyscale()
      .raw()
      .toBuffer({ resolveWithObject: true });
    const c = info.channels;
    const W = info.width;
    const H = info.height;
    const g = c === 1 ? new Uint8Array(data.buffer, data.byteOffset, W * H) : Uint8Array.from({ length: W * H }, (_, i) => data[i * c]!);
    const box = rest.some((v) => v.startsWith('trimmed')) ? trimBox(g, W, H) : null;
    // the crop and the mirror on the grey pixels themselves, then the same resizes as the plain fingerprint
    const crop = (b: NonNullable<typeof box>) => {
      const o = new Uint8Array(b.width * b.height);
      for (let y = 0; y < b.height; y++) o.set(g.subarray((b.top + y) * W + b.left, (b.top + y) * W + b.left + b.width), y * b.width);
      return o;
    };
    const mirror = (x: Uint8Array, w: number, h: number) => {
      const o = new Uint8Array(w * h);
      for (let y = 0; y < h; y++) for (let i = 0; i < w; i++) o[y * w + i] = x[y * w + (w - 1 - i)]!;
      return o;
    };
    const hash = (x: Uint8Array, w: number, h: number) =>
      hashRaw(sharp(Buffer.from(x.buffer, x.byteOffset, x.byteLength), { raw: { width: w, height: h, channels: 1 } }));
    for (const v of rest) {
      if (v === 'mirrored') out[v] = await hash(mirror(g, W, H), W, H);
      else if (!box) out[v] = null;
      else {
        const t = crop(box);
        out[v] = await hash(v === 'trimmed' ? t : mirror(t, box.width, box.height), box.width, box.height);
      }
    }
  } catch {
    for (const v of rest) out[v] = null;
  }
  return out;
}

/** the mean absolute difference of two 32×32 grey images (0–255) */
export function mad32(a: Buffer, b: Buffer): number {
  let s = 0;
  for (let i = 0; i < 1024; i++) s += Math.abs(a[i]! - b[i]!);
  return s / 1024;
}
/** S19 (ת50): the ink of a 32×32 grey image: the mean of 255 − grey (0 on white, 255 on black) */
export function inkOf(grey: Buffer): number {
  let s = 0;
  for (let i = 0; i < 1024; i++) s += 255 - grey[i]!;
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
/** the same on bytes (the scan compares thousands of pairs per picture) */
export function hammingBytes(a: Uint8Array, b: Uint8Array): number {
  let d = 0;
  for (let i = 0; i < a.length; i++) d += POP[a[i]! ^ b[i]!]!;
  return d;
}

/** a fingerprint ready to compare: its dHash as bytes and its ink */
export type Prepared = Fingerprint & { bits: Uint8Array; ink: number };
export const prepare = (f: Fingerprint): Prepared => ({ ...f, bits: Uint8Array.from(Buffer.from(f.dhash, 'hex')), ink: inkOf(f.grey) });

/**
 * The pixel rule (S17, ת45; S19, ת50) on two fingerprints: A, within the dHash threshold; B, a near miss whose 32×32 grey
 * images differ by at most 3 on average, when both carry ink (a near-blank picture is no evidence of anything).
 */
export function pixelRule(
  a: Prepared,
  b: Prepared,
  max = PIXEL_MAX_HAMMING,
  o: { inkForA?: boolean } = {},
): { d: number; m: number | null; rule: 'A' | 'B' | null } {
  const d = hammingBytes(a.bits, b.bits);
  const m = d <= NEAR_MAX_HAMMING ? mad32(a.grey, b.grey) : null;
  const inked = a.ink >= NEAR_MIN_INK && b.ink >= NEAR_MIN_INK;
  if (d <= max && (!o.inkForA || inked)) return { d, m, rule: 'A' };
  if (m !== null && m <= NEAR_MAX_MAD32 && inked) return { d, m, rule: 'B' };
  return { d, m, rule: null };
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
  /**
   * S19 (ת51): the variants of a picture, computed together when any is missing. The plain one keeps its old key (the
   * sha256), so the fingerprints of earlier builds stay; the others are keyed by the sha256, the variant and the version
   * of the trim (a change to the trim computes them again).
   */
  async variants(buf: Buffer | Uint8Array, sha: string, want: readonly Variant[]): Promise<Partial<Record<Variant, Fingerprint | null>>> {
    const key = (v: Variant) => (v === 'plain' ? sha : `${sha}:${v}:${TRIM_VERSION}`);
    const missing = want.filter((v) => !this.map.has(key(v)));
    if (missing.length) {
      const got = await fingerprintVariants(buf, missing);
      for (const v of missing) this.map.set(key(v), got[v] ?? null);
      this.dirty = true;
    }
    return Object.fromEntries(want.map((v) => [v, this.map.get(key(v)) ?? null]));
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

/**
 * S19, QA ת51: the supplier picture domains the gate knows whatever the cards name. A card names the host of its own
 * pictures (ae01.alicdn.com…), but a supplier serves the same picture from other hosts: QA's hotlink to
 * ae-pic-a1.aliexpress-media.com passed, because no card names that domain (it appears 290k times in data/).
 */
export const SUPPLIER_IMAGE_DOMAINS: readonly string[] = ['alicdn.com', 'aliexpress-media.com', 'aliexpress.com', 'cjdropshipping.com', 'zendrop.com'];
/** the hosts the gate looks for: the cards' picture hosts and the fixed supplier domains */
export const pictureHosts = (cards: unknown[]): string[] => [...new Set([...cardPictureHosts(cards), ...SUPPLIER_IMAGE_DOMAINS])].sort();

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

export type SupplierPicture = Prepared & {
  picture: string;
  product: string;
  rights: Rights | 'unknown';
  file: string;
  /** S19 (ת51): the form of the picture this fingerprint is of (plain, mirrored, trimmed, trimmed and mirrored) */
  variant: Variant;
};
export type SupplierSet = {
  /** sha256 → what it is (a file that may not ship wins over one that may) */
  bySha: Map<string, { file: string; product: string; rights: Rights | 'unknown'; source: LedgerSource }>;
  /** one fingerprint per picture that may not ship, and per variant of it (S19, ת51) */
  pixels: SupplierPicture[];
  hosts: string[];
  stats: {
    ledger_entries: number;
    cached_originals: number;
    unlisted_cached: number;
    withheld_files: number;
    pictures: number;
    /** S19 (ת51): the fingerprints compared: each picture plain and mirrored, and trimmed when it has margins */
    fingerprints: number;
  };
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
  let pictures = 0;
  const add = async (buf: Buffer, sha: string, p: { picture: string; product: string; rights: Rights | 'unknown'; file: string }) => {
    const v = await o.dhashes.variants(buf, sha, VARIANTS);
    if (!v.plain) return;
    pictures++;
    for (const k of VARIANTS) {
      const f = v[k];
      if (f) pixels.push({ ...p, ...prepare(f), variant: k });
    }
  };
  for (const e of largest.values()) {
    const path = join(o.site, e.file);
    if (!existsSync(path)) continue;
    await add(readFileSync(path), e.sha256, { picture: e.picture, product: e.product, rights: e.rights, file: e.file });
  }
  for (const c of cacheRows) {
    const what = bySha.get(c.sha)!;
    if (shipsPublicly(what.rights as Rights)) continue;
    await add(c.buf, c.sha, { picture: c.file, product: what.product, rights: what.rights, file: c.file });
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
      pictures,
      fingerprints: pixels.length,
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
  /** S19: the rule that matched (A: the dHash; B: the near miss with ink), and the forms compared */
  rule?: 'A' | 'B';
  variant?: string;
};
type Near = { where: string; picture: string; hamming: number; mad32: number | null; variant?: string };
export type ScanStats = {
  files: number;
  rasters: number;
  data_uris: number;
  text_files: number;
  nearest: Near[];
  /** the smallest 32×32 grey difference of a near miss that is not a match (the margin of the second test) */
  nearest_by_grey: (Near & { mad32: number })[];
  /** S19 (QA S17): the same two, over the files `opts.elsewhere` says are not supplier copies by design */
  nearest_elsewhere: Near[];
  nearest_by_grey_elsewhere: (Near & { mad32: number })[];
};

const TEXT_EXT = /\.(?:html?|js|mjs|cjs|css|json|xml|txt|webmanifest|svg|map|md)$/i;
/** extensionless files a static host reads (_headers, _redirects) are text too */
const isText = (rel: string) => TEXT_EXT.test(rel) || !extname(rel);

/** a data: URI's head; its body is read by `dataUris` */
const DATA_URI_HEAD = /data:([a-z0-9.+/-]*)((?:;[a-z0-9=._-]+)*);base64,/gi;
/** the body as the file holds it: base64, and what a browser removes before decoding (S19, ת51) */
const BODY_LOOSE =
  /(?:[A-Za-z0-9+/=]|\\(?:\r\n|[\n\r\f])|\\[0-9a-fA-F]{1,6}(?:\r\n|[ \t\n\r\f])?|\\[^\n\r\f0-9a-fA-F]|%[0-9a-fA-F]{2}|&#[xX][0-9a-fA-F]{1,6};|&#\d{1,7};|&(?:plus|sol|equals);|[ \t\n\r\f])*/y;
const BASE64_RUN = /^[A-Za-z0-9+/]{16,}={0,2}/;
/**
 * S19, QA ת51: every data: URI of a text, its base64 as a browser decodes it. R15 split a data: URI in CSS with escaped
 * line breaks ("\" and a newline: a line continuation inside a CSS string), and the gate's pattern stopped at the first
 * break. Now the body is read past CSS escapes and line continuations, percent escapes (a data: URL is percent-decoded
 * first), numeric character references and whitespace (forgiving base64), and then decoded. The strict run (the body up
 * to the first other character) is kept as well, so nothing the gate found before is lost to a word after the URI.
 */
export function dataUris(text: string): { mime: string; b64: string; index: number }[] {
  const out: { mime: string; b64: string; index: number }[] = [];
  for (const m of text.matchAll(DATA_URI_HEAD)) {
    const at = m.index + m[0].length;
    BODY_LOOSE.lastIndex = at;
    const loose = BODY_LOOSE.exec(text)?.[0] ?? '';
    const strict = /^[A-Za-z0-9+/]*={0,2}/.exec(loose)?.[0] ?? '';
    const decoded = loose
      .replace(/\\(?:\r\n|[\n\r\f])/g, '')
      .replace(/\\([0-9a-fA-F]{1,6})(?:\r\n|[ \t\n\r\f])?/g, (_, h: string) => String.fromCodePoint(Math.min(parseInt(h, 16), 0x10ffff)))
      .replace(/\\([^\n\r\f0-9a-fA-F])/g, '$1')
      .replace(/%([0-9a-fA-F]{2})/g, (_, h: string) => String.fromCharCode(parseInt(h, 16)))
      .replace(/&#[xX]([0-9a-fA-F]{1,6});/g, (_, h: string) => String.fromCodePoint(Math.min(parseInt(h, 16), 0x10ffff)))
      .replace(/&#(\d{1,7});/g, (_, d: string) => String.fromCodePoint(Math.min(Number(d), 0x10ffff)))
      .replace(/&plus;/g, '+')
      .replace(/&sol;/g, '/')
      .replace(/&equals;/g, '=')
      .replace(/[ \t\n\r\f]/g, '');
    const read = BASE64_RUN.exec(decoded)?.[0];
    const bodies = new Set([BASE64_RUN.exec(strict)?.[0], read].filter((x): x is string => !!x));
    for (const b64 of bodies) out.push({ mime: m[1]!, b64, index: m.index });
  }
  return out;
}

/** the gate's fingerprints of a picture of the build: plain, and trimmed when it has margins (S19, ת51) */
export type Mine = { plain: Prepared; trimmed: Prepared | null };
export type PixelVerdict = { d: number; m: number | null; rule: 'A' | 'B' | null; p: SupplierPicture; mine: 'plain' | 'trimmed' };
/**
 * S19: a picture against the supplier fingerprints, every form of it against every form of each: the best match (the
 * nearest by dHash among the matches), else the nearest; and the smallest grey difference of a near miss that is not a
 * match (the margin of rule B). Exported so QA's scans read the gate's own rule.
 * The plain picture against the plain one is QA's rule as approved (A; B with ink). A mirrored or trimmed form is
 * evidence only of a picture with content: there both A and B need ink on both sides (a near-blank picture is a few
 * bits from the mirror of another near-blank one).
 */
export function nearestPicture(
  mine: Mine,
  pixels: SupplierPicture[],
  max = PIXEL_MAX_HAMMING,
  only?: (p: SupplierPicture) => boolean,
): { best: PixelVerdict | null; grey: PixelVerdict | null } {
  let best: PixelVerdict | null = null;
  let grey: PixelVerdict | null = null;
  const forms: ['plain' | 'trimmed', Prepared][] = [['plain', mine.plain]];
  if (mine.trimmed) forms.push(['trimmed', mine.trimmed]);
  for (const p of pixels) {
    if (only && !only(p)) continue;
    for (const [k, f] of forms) {
      const r = pixelRule(f, p, max, { inkForA: k !== 'plain' || p.variant !== 'plain' });
      const v: PixelVerdict = { ...r, p, mine: k };
      if (!r.rule && r.m !== null && (!grey || r.m < grey.m!)) grey = v;
      if (!best || (r.rule && !best.rule) || (!!r.rule === !!best.rule && r.d < best.d)) best = v;
    }
  }
  return { best, grey };
}
const formsOf = (v: PixelVerdict) =>
  v.mine === 'plain' && v.p.variant === 'plain' ? undefined : `${v.mine === 'trimmed' ? 'this trimmed' : 'this'} vs the picture ${v.p.variant}`;

/**
 * Every file of a build against the supplier set: equal bytes, a raster or a data: URI within the pixel threshold of a
 * picture that may not ship, and any URL on a supplier picture host. `skip` leaves files out (behind the flag: none).
 */
export async function scanBuild(
  dist: string,
  set: SupplierSet,
  dhashes: DhashCache,
  opts: { files?: string[]; maxHamming?: number; elsewhere?: (where: string) => boolean } = {},
): Promise<{ findings: ContentFinding[]; stats: ScanStats }> {
  const max = opts.maxHamming ?? PIXEL_MAX_HAMMING;
  const walk = (d: string): string[] => readdirSync(d).flatMap((n) => (statSync(join(d, n)).isDirectory() ? walk(join(d, n)) : [join(d, n)]));
  const files = (opts.files ?? walk(dist).map((f) => relative(dist, f))).map((f) => f.split('\\').join('/')).sort();
  const hostRe = hostPattern(set.hosts);
  const findings: ContentFinding[] = [];
  const stats: ScanStats = {
    files: files.length,
    rasters: 0,
    data_uris: 0,
    text_files: 0,
    nearest: [],
    nearest_by_grey: [],
    nearest_elsewhere: [],
    nearest_by_grey_elsewhere: [],
  };
  const elsewhere = opts.elsewhere ?? (() => true);
  const withheld = (sha: string) => {
    const v = set.bySha.get(sha);
    return v && !shipsPublicly(v.rights as Rights) ? v : null;
  };
  const near = async (where: string, buf: Buffer, sha: string, how: 'pixels' | 'data-uri pixels') => {
    const v = await dhashes.variants(buf, sha, ['plain', 'trimmed']);
    if (!v.plain) return;
    stats.rasters++;
    const { best, grey } = nearestPicture({ plain: prepare(v.plain), trimmed: v.trimmed ? prepare(v.trimmed) : null }, set.pixels, max);
    if (!best) return;
    const variant = formsOf(best);
    const g = grey ? { where, picture: grey.p.picture, hamming: grey.d, mad32: Number(grey.m!.toFixed(1)), variant: formsOf(grey) } : null;
    const n = { where, picture: best.p.picture, hamming: best.d, mad32: best.m === null ? null : Number(best.m.toFixed(1)), variant };
    if (g) stats.nearest_by_grey.push(g);
    stats.nearest.push(n);
    if (elsewhere(where)) {
      if (g) stats.nearest_by_grey_elsewhere.push(g);
      stats.nearest_elsewhere.push(n);
    }
    if (best.rule)
      findings.push({
        where,
        how,
        what: `looks like ${best.p.picture}${variant ? ` (${variant})` : ''} (${best.p.product}, rights: ${best.p.rights}; dHash ${best.d}/256${best.m === null ? '' : `, 32×32 grey ${best.m.toFixed(1)}`}; rule ${best.rule})`,
        product: best.p.product,
        hamming: best.d,
        mad32: best.m === null ? undefined : Number(best.m.toFixed(2)),
        rule: best.rule,
        ...(variant ? { variant } : {}),
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
    for (const d of dataUris(text)) {
      k++;
      stats.data_uris++;
      const bytes = Buffer.from(d.b64, 'base64');
      const where = `${rel} (data: URI #${k}, ${bytes.length} B)`;
      const s = sha256(bytes);
      const wd = withheld(s);
      if (wd) {
        findings.push({ where, how: 'data-uri bytes', what: `the same bytes as ${wd.file} (${wd.product}, rights: ${wd.rights})`, product: wd.product });
        continue;
      }
      // an inlined SVG may itself carry a picture or a hotlink: one level down
      if (/svg/i.test(d.mime)) {
        const inner = bytes.toString('utf8');
        if (hostRe)
          for (const x of inner.matchAll(hostRe))
            findings.push({ where, how: 'host', what: `a URL on a supplier picture host inside an inlined SVG: ${x[0]}` });
        for (const x of dataUris(inner)) {
          const b = Buffer.from(x.b64, 'base64');
          if (withheld(sha256(b))) findings.push({ where, how: 'data-uri bytes', what: 'a supplier picture inside an inlined SVG' });
          else await near(`${where} (inner)`, b, sha256(b), 'data-uri pixels');
        }
        continue;
      }
      await near(where, bytes, s, 'data-uri pixels');
    }
  }
  stats.nearest = stats.nearest.sort((a, b) => a.hamming - b.hamming).slice(0, 10);
  stats.nearest_by_grey = stats.nearest_by_grey.sort((a, b) => a.mad32 - b.mad32).slice(0, 10);
  stats.nearest_elsewhere = stats.nearest_elsewhere.sort((a, b) => a.hamming - b.hamming).slice(0, 5);
  stats.nearest_by_grey_elsewhere = stats.nearest_by_grey_elsewhere.sort((a, b) => a.mad32 - b.mad32).slice(0, 5);
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
