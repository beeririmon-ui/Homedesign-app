/**
 * QA S17, note ה3: "הדפס במרקם" and negation. materialHe of the copy (tools/lib/hebrew.ts at a988b099) on my own phrases:
 * the brief's denials, my new ones, and claims that must stay. Run from the copy's site/: tsx <this> (absolute path).
 */
import { materialHe } from '../build-s17/site/tools/lib/hebrew';
const deny = [
  'non-textured print',
  'smooth print (no texture)',
  'nontextured printed canvas',
  'printed poster, not embossed',
  'print without any texture',
  'Print, NO TEXTURE',
  // mine: a denial the pattern may not know
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
const claim = [
  'printed embossed film',
  'textured print, no gloss',
  'embossed print, not framed',
  'print with raised texture, no frame',
  'non-slip backing, textured print',
  'textured canvas print (not glossy)',
];
const row = (s: string) => `${JSON.stringify(s)} → ${materialHe(s) ?? 'null'}`;
console.log('denials (must not be "הדפס במרקם"):');
let bad = 0;
for (const s of deny) {
  const he = materialHe(s);
  if (he === 'הדפס במרקם') bad++;
  console.log(`  ${he === 'הדפס במרקם' ? 'MISS' : 'ok  '} ${row(s)}`);
}
console.log('claims (must stay "הדפס במרקם"):');
let lost = 0;
for (const s of claim) {
  const he = materialHe(s);
  if (he !== 'הדפס במרקם') lost++;
  console.log(`  ${he === 'הדפס במרקם' ? 'ok  ' : 'LOST'} ${row(s)}`);
}
console.log(`QA ה3: ${deny.length - bad}/${deny.length} denials read right, ${claim.length - lost}/${claim.length} claims kept`);
