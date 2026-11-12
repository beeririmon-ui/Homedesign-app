/**
 * QA S21 (my S19 tool, now S21 vs S20), ה14: "הדפס במרקם" and negation. materialHe of my copy (tools/lib/hebrew.ts at f33cfe42) on:
 *   (1) my 16 denials of S17 (the brief's 6 and my 10), and my 6 claims;
 *   (2) new denials, as a supplier or a translator writes them (abbreviations, spec-sheet values, typographic marks);
 *   (3) new claims that must stay, and claims the clause rule gives up on purpose ("says the less");
 *   (4) every material text of every card under data/products, read by S17's materialHe (a988b099, my S17 copy) and by
 *       this one: what changed.
 * Run from the copy's site/: tsx <this>.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { materialHe, claimsTexture } from '../build-s21/site/tools/lib/hebrew';
import { materialHe as materialHeS17 } from '../../qa20/build-s20/site/tools/lib/hebrew';

const T = 'הדפס במרקם';
const deny17 = [
  'non-textured print',
  'smooth print (no texture)',
  'nontextured printed canvas',
  'printed poster, not embossed',
  'print without any texture',
  'Print, NO TEXTURE',
  'print with no embossed texture',
  'printed, no raised or embossed texture',
  'print; neither textured nor embossed',
  "print (isn't textured)",
  'flat print, texture: none',
  'texture-free print',
  'print, no 3D texture',
  'print with no visible texture',
  'printed panel, lacks texture',
  'print without embossed or textured finish',
];
const denyNew = [
  'print w/o texture',
  'printed canvas w/o embossing',
  'print, texture-less',
  'print, texture: N/A',
  'printed poster, Texture: Smooth',
  'print, texture: flat',
  'Printed: Yes; Embossed: N',
  'print, Textured: False',
  'print, isnt textured',
  'print, doesnt have texture',
  'print, isn’t textured', // a typographic apostrophe
  'print ‒ not textured', // a figure dash between spaces
  'printed poster (texture? no)',
  'PRINT, NOT TEXTURED',
  'print; non‑textured', // a non-breaking hyphen
  'printed canvas: untextured',
  'print with zero texture',
  'print – no embossing', // an en dash between spaces
  'הדפס, ללא מרקם (printed, texture: none)',
  'print, embossing: none',
];
const claim17 = [
  'printed embossed film',
  'textured print, no gloss',
  'embossed print, not framed',
  'print with raised texture, no frame',
  'non-slip backing, textured print',
  'textured canvas print (not glossy)',
];
const claimNew = [
  'textured canvas print',
  '3D embossed print',
  'unframed embossed print',
  'printed embossed film / texture painting',
  'Painting material: embossed film, printed',
  'frameless textured print',
];
// the clause rule gives these up on purpose (a negation in the same clause): the shop says the less
const lessOnPurpose = ['non-fading embossed print', 'textured print that is not glossy', 'embossed print without frame', 'non-slip textured print'];

const row = (s: string) => `${JSON.stringify(s)} → ${materialHe(s) ?? 'null'}`;
let missed17 = 0;
let missedNew = 0;
let lost17 = 0;
let lostNew = 0;
const missedList: string[] = [];
console.log('(1) my S17 denials (must not read "הדפס במרקם"):');
for (const s of deny17) {
  const bad = materialHe(s) === T;
  if (bad) missed17++;
  console.log(`  ${bad ? 'MISS' : 'ok  '} ${row(s)}`);
}
console.log('(2) new denials (must not read "הדפס במרקם"):');
for (const s of denyNew) {
  const bad = materialHe(s) === T;
  if (bad) {
    missedNew++;
    missedList.push(s);
  }
  console.log(`  ${bad ? 'MISS' : 'ok  '} ${row(s)}`);
}
console.log('(3a) claims (must stay "הדפס במרקם"):');
for (const s of [...claim17, ...claimNew]) {
  const lost = materialHe(s) !== T;
  if (lost) claim17.includes(s) ? lost17++ : lostNew++;
  console.log(`  ${lost ? 'LOST' : 'ok  '} ${row(s)}`);
}
console.log('(3b) claims the clause rule gives up on purpose (says the less):');
for (const s of lessOnPurpose) console.log(`  ${materialHe(s) === T ? 'kept' : 'less'} ${row(s)}`);

// (4) every card's material texts, S17 vs now
const cards: { id?: string; materials?: unknown }[] = [];
const walk = (d: string): void => {
  for (const n of readdirSync(d)) {
    const p = join(d, n);
    if (statSync(p).isDirectory()) walk(p);
    else if (n.endsWith('.json'))
      try {
        cards.push(JSON.parse(readFileSync(p, 'utf8')));
      } catch {
        /* not a card */
      }
  }
};
walk('../data/products');
let texts = 0;
const changed: string[] = [];
const claims: string[] = [];
for (const c of cards) {
  if (!Array.isArray(c.materials)) continue;
  for (const m of c.materials) {
    if (typeof m !== 'string') continue;
    texts++;
    const a = materialHeS17(m);
    const b = materialHe(m);
    if (a !== b) changed.push(`${c.id}: ${JSON.stringify(m)}: ${a} → ${b}`);
    if (b === T) claims.push(`${c.id}: ${JSON.stringify(m)}`);
    // a text with a texture word that the clause rule reads as a claim while a negation sits in another clause
    if (claimsTexture(m) && /\b(?:no|not|non|without|w\/o)\b/i.test(m) && b === T) claims.push(`  (negation elsewhere in it) ${c.id}`);
  }
}
console.log(`(4) cards: ${cards.length} files, ${texts} material texts; read differently from S20: ${changed.length}`);
for (const x of changed) console.log(`  ${x}`);
console.log(`    read "הדפס במרקם" now: ${claims.length}`);
for (const x of claims) console.log(`  ${x}`);
console.log(
  `QA ה14 (S21): S17 denials ${deny17.length - missed17}/${deny17.length} read right; new denials ${denyNew.length - missedNew}/${denyNew.length}` +
    (missedList.length ? ` (missed: ${missedList.map((s) => JSON.stringify(s)).join(', ')})` : '') +
    `; claims kept ${claim17.length - lost17}/${claim17.length} (S17) and ${claimNew.length - lostNew}/${claimNew.length} (new)`,
);

// ---------- S21, mine: 20 fresh denials (not in the brief: generalisation, reported) and claims the new readers could eat
const denyFresh = [
  'print, w/out texture',
  'print (no-texture)',
  'print; Texture - None',
  'print | Embossing: No',
  'print, Embossed: NO',
  'print, texture: none/flat',
  'textureless print',
  'print, non textured',
  'print, not-embossed',
  'print, no textures',
  'print, texture: nil',
  'print, Embossed? N/A',
  'print — texture: n/a',
  'print, doesn’t have any texture',
  'print, has no texture at all',
  'print, texture 0',
  'print, Texture=false',
  'print, Textured: no.',
  'print, embossing-free',
  'print, texture: —',
];
const claimFresh = [
  'print, Texture: Embossed',
  'print, Embossed: Yes',
  'print, Textured: True',
  'print, texture: 3D raised',
  'print, Embossed: 0.3 mm depth',
  'textured print, flat frame',
  'print; Surface: textured; Back: smooth',
  'texture-rich embossed print',
  'print, Embossed: Y',
  'printed canvas, Texture: raised weave',
];
let freshMiss = 0;
let freshLost = 0;
console.log('(5) fresh denials (mine, S21; reported):');
for (const s of denyFresh) {
  const bad = materialHe(s) === T;
  if (bad) freshMiss++;
  console.log(`  ${bad ? 'MISS' : 'ok  '} ${row(s)}`);
}
console.log('(6) fresh claims (mine, S21; a new reader must not eat them; reported):');
for (const s of claimFresh) {
  const lost = materialHe(s) !== T;
  if (lost) freshLost++;
  console.log(`  ${lost ? 'LOST' : 'ok  '} ${row(s)}`);
}
console.log(`QA21 fresh: denials ${denyFresh.length - freshMiss}/${denyFresh.length} read right; claims kept ${claimFresh.length - freshLost}/${claimFresh.length}`);
