/**
 * qa-agent S15: my own cases for the material words (tools/lib/hebrew.ts) and the meta cut (shared/src/meta-text.ts).
 * Run inside the copy: npx tsx tools/qa1516/copy-probe.ts
 */
import { materialHe } from '../lib/hebrew';
import { metaDescription } from '../../shared/src/meta-text';

const mats = [
  'printed embossed film',
  'canvas print',
  'non-textured print',
  'smooth print (no texture)',
  'print on canvas, untextured',
  'textured canvas painting',
  'oil painting on canvas',
  'hand-painted canvas',
  'embossed metal, printed label',
  'printed cotton, textured weave',
  'print (material not stated - possibly textured)',
  'giclee print with texture coating',
];
for (const m of mats) console.log(`material: ${JSON.stringify(m)} → ${materialHe(m)}`);

const metas: string[] = [
  // a sentence of 150, then another: cut after the first
  `${'א'.repeat(20)} ${'בבב '.repeat(32)}סוף. ועוד משפט ארוך שלא נכנס בכלל לתיאור המטא של הדף הזה.`,
  // one sentence of 200 with no full stop: last whole word + …
  `${'מילה '.repeat(40)}אחרונה`,
  // a size with a dot and a number: 1.5 is not an end
  `מנורה בגובה 1.5 מ' עם אהיל פשתן, וכבל של 2.5 מ'. ${'עוד טקסט '.repeat(20)}`,
  // abbreviation ס"מ. as an end
  `שולחן 40×60 ס"מ. ${'מילים נוספות '.repeat(15)}`,
  // a word longer than 155 (no space)
  'א'.repeat(170),
  // an ellipsis word boundary exactly at 155
  `${'abcd '.repeat(31)}efgh ijkl`,
  // Hebrew geresh and a question mark
  `האם זה עובד? ${'כן, זה עובד היטב בבית '.repeat(8)}`,
];
for (const t of metas) {
  const m = metaDescription(t);
  const norm = t.replace(/\s+/g, ' ').trim();
  const prefix = m.endsWith('…') ? norm.startsWith(m.slice(0, -1)) : norm.startsWith(m);
  const after = m.endsWith('…') ? norm[m.length - 1] : norm[m.length];
  console.log(`meta: in ${norm.length} → out ${m.length}; prefix ${prefix}; next char ${JSON.stringify(after ?? '(end)')}; ends ${JSON.stringify(m.slice(-12))}`);
}
