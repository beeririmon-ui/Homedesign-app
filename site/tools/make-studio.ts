/**
 * MOCK2 (2026-11-13), FB1: the wheel shows the product on its own, and our own studio picture comes first where one
 * exists and passed QA. This writes that picture, for the tour's wheel and the room tool's:
 *
 *   web/public/media/tour/studio/<product id>.<w>.webp   the studio image on transparency, longest side CARD px
 *   .generated/studio-images.json                        { width, products: { <product id>: { src, w, h } } } — the
 *                                                        browser's manifest, and nothing more: a card id carries the
 *                                                        supplier's name in it, and nothing the site serves may
 *                                                        (e2e/public-scan.spec.ts)
 *   .generated/studio-images.sources.json                which pilot picture each one came from, for the record
 *
 * The source is render-agent's own-image pilot (IMG1): `assets/renders/products/<pilot>/source-record.json`. Only an
 * image whose record says QA passed is used, and only when the file on disk still has the sha256 the verdict was bound
 * to (the record's own rule: "a QA verdict holds for that sha only"). Nothing else is read, and no supplier picture is
 * ever copied (studio rules: supplier images are internal references).
 *
 * The files live under media/tour/ on purpose: a public build deletes that folder (web/vite.config.ts), and the browser
 * only looks for them behind the flag (web/src/studio.ts). The pilot's images are still waiting for the designer's
 * written eye, so they are not on the public site yet.
 */
import sharp from 'sharp';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { GENERATED, MEDIA_OUT, repoPath } from './lib/paths';

/** the wheel's card: the longest side of the picture, in CSS px × 2 */
export const CARD = 360;
const PILOTS = ['assets/renders/products/img1-pilot-2026-11-12'];

type Record_ = {
  images: { card: string; type: string; file: string | null; own?: boolean; qa_verdict?: string; file_sha256?: string }[];
};
type Full = { products: { id: string; card_id?: string }[] };

const read = <T>(f: string): T => JSON.parse(readFileSync(f, 'utf8')) as T;
const sha = (f: string) => createHash('sha256').update(readFileSync(f)).digest('hex');
/** the record's verdict for a picture that passed QA; anything else (partial, failed, not reviewed) is not used */
const passed = (v: string | undefined): boolean => !!v && /^yes\s*\/\s*passed/.test(v);

const full = read<Full>(join(GENERATED, 'catalog.story.full.json'));
const productOfCard = new Map<string, string>();
for (const p of full.products) productOfCard.set(p.card_id ?? p.id, p.id);
// the shop's own catalog as well (a card the story does not carry)
for (const p of read<Full>(join(GENERATED, 'catalog.full.json')).products)
  if (!productOfCard.has(p.card_id ?? p.id)) productOfCard.set(p.card_id ?? p.id, p.id);

const REL = 'tour/studio';
const OUT = join(MEDIA_OUT, REL);
mkdirSync(OUT, { recursive: true });

type Entry = { src: string; w: number; h: number };
const products: Record<string, Entry> = {};
/** the record of where each picture came from; read by people, never bundled into the site */
const sources: Record<string, { card: string; file: string; sha256: string }> = {};
const skipped: string[] = [];
for (const pilot of PILOTS) {
  const recordFile = repoPath(pilot, 'source-record.json');
  if (!existsSync(recordFile)) continue;
  for (const img of read<Record_>(recordFile).images) {
    if (!img.file || !img.own) continue;
    if (!passed(img.qa_verdict)) {
      skipped.push(`${img.card} ${img.type}: ${(img.qa_verdict ?? 'no verdict').slice(0, 60)}`);
      continue;
    }
    const file = repoPath(img.file);
    if (!existsSync(file)) {
      skipped.push(`${img.card} ${img.type}: the file is gone`);
      continue;
    }
    if (img.file_sha256 && sha(file) !== img.file_sha256) {
      skipped.push(`${img.card} ${img.type}: the file changed since QA passed it`);
      continue;
    }
    const id = productOfCard.get(img.card);
    if (!id) {
      skipped.push(`${img.card}: no product in the catalog`);
      continue;
    }
    // P1 is the product in a room; P2 is the product on its own, which is what a wheel card is
    if (img.type !== 'P2') continue;
    // trimmed to the product and scaled so its longest side is CARD, on transparency
    const trimmed = await sharp(file).ensureAlpha().trim({ threshold: 1 }).toBuffer({ resolveWithObject: true });
    const m = await sharp(trimmed.data).metadata();
    const scale = CARD / Math.max(m.width!, m.height!);
    const w = Math.max(1, Math.round(m.width! * scale));
    const h = Math.max(1, Math.round(m.height! * scale));
    const out = join(OUT, `${id}.${CARD}.webp`);
    mkdirSync(dirname(out), { recursive: true });
    await sharp(trimmed.data).resize(w, h).webp({ quality: 88, alphaQuality: 100, effort: 5 }).toFile(out);
    products[id] = { src: `${REL}/${id}.${CARD}`, w, h };
    sources[id] = { card: img.card, file: img.file, sha256: img.file_sha256 ?? sha(file) };
  }
}

mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'studio-images.json'), JSON.stringify({ width: CARD, products }, null, 1));
writeFileSync(join(GENERATED, 'studio-images.sources.json'), JSON.stringify({ date: new Date().toISOString().slice(0, 10), pilots: PILOTS, sources }, null, 1));
console.log(
  `studio: ${Object.keys(products).length} own product pictures that passed QA (${Object.values(sources)
    .map((p) => p.card)
    .join(', ')})${skipped.length ? `; not used: ${skipped.length} (${skipped.slice(0, 3).join(' | ')})` : ''}`,
);
