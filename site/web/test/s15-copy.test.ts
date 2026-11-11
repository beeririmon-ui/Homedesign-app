/**
 * S15: master-designer's copy (docs/proposals/your-room-copy-2026-11-11.md) where it is logic: the set panel's note and
 * button (§2 rows 10–13), the wheel's count (§2 row 4, §5), and the meta description cut at a sentence, never in the
 * middle of a word (§5).
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { META_DESCRIPTION_MAX, metaDescription } from '@hd/shared/meta-text';
import { lineName, splitLineName } from '@hd/shared/lines';
import { NOT_FOR_SALE_HE, setButtonHe, setItemsLabelHe, setNoteHe, wheelCountHe } from '../src/set-copy';

const NAMES = fileURLToPath(new URL('../../../data/catalog/names-he.json', import.meta.url));

describe('the set panel (§2)', () => {
  it('the note says what a piece not sold now does to the button; the piece’s row says it is out of stock', () => {
    expect(setNoteHe(1)).toBe('פריט אחד מהסט אינו זמין כעת, ולכן הסט נכנס לסל בלעדיו.');
    expect(setNoteHe(2)).toBe('2 פריטים מהסט אינם זמינים כעת, ולכן הסט נכנס לסל בלעדיהם.');
    expect(setNoteHe(1)).not.toMatch(/במלאי|:/);
  });
  it('the button: the same verb whole or partial, "מתוך" when a piece is not sold now', () => {
    expect(setButtonHe(4, 4)).toBe('הסט כולו לסל');
    expect(setButtonHe(3, 4)).toBe('הסט לסל, 3 מתוך 4 פריטים');
  });
  it('the count over the wheel: "סטים" in a house of sets, "גרסאות" elsewhere, never the studio’s "וריאציות"', () => {
    expect(wheelCountHe(3, true)).toBe('3 סטים');
    expect(wheelCountHe(3, false)).toBe('3 גרסאות');
    expect(setItemsLabelHe(4)).toBe('בסט 4 פריטים');
    expect(NOT_FOR_SALE_HE).toBe('עוד לא במכירה');
  });
});

describe('the meta description (§5): whole sentences, never a cut word', () => {
  it('a text that fits is kept whole', () => {
    expect(metaDescription('כרית.')).toBe('כרית.');
    expect(metaDescription('  שתי   מילים. ')).toBe('שתי מילים.');
  });
  it('the Morandi triptych: its two first sentences, whole, inside the limit (§3)', () => {
    const d = (JSON.parse(readFileSync(NAMES, 'utf8')) as { description_he: Record<string, string> }).description_he['framed-art-cj-morandi-triptych-sage']!;
    expect(d.length).toBeGreaterThan(META_DESCRIPTION_MAX);
    const m = metaDescription(d);
    expect(m).toBe(d.split('. ').slice(0, 2).join('. ') + '.');
    // §3 counts 130; the string is 126 characters: either way inside the 155
    expect(m.length).toBeLessThanOrEqual(META_DESCRIPTION_MAX);
    expect(d.startsWith(m)).toBe(true);
  });
  it('a number or a size is not the end of a sentence', () => {
    const t = `${'א'.repeat(120)} 1.5 ס"מ, 40×60. ${'ב'.repeat(60)}.`;
    expect(metaDescription(t)).toBe(`${'א'.repeat(120)} 1.5 ס"מ, 40×60.`);
  });
  it('one sentence longer than the limit: cut at the last whole word, with an ellipsis', () => {
    const words = Array.from({ length: 40 }, (_, i) => `מילה${i}`).join(' ');
    const m = metaDescription(`${words}.`);
    expect(m.length).toBeLessThanOrEqual(META_DESCRIPTION_MAX);
    expect(m.endsWith('…')).toBe(true);
    const kept = m.slice(0, -1).split(' ');
    // every word kept is a whole word of the text
    for (const w of kept) expect(words.split(' ')).toContain(w);
  });
  it('never in the middle of a word, for any length', () => {
    const text = 'סלון מודרני חם: קירות טיח, ספת בוקלה, שולחן קפה מאגוז וספסל אבן בחלון, באור חורף של אחר הצהריים ובשעות הערב המוקדמות כשהאור נמוך וחם מאוד';
    for (let max = 20; max < text.length; max += 7) {
      const m = metaDescription(text, max);
      expect(m.length, `${max}`).toBeLessThanOrEqual(max);
      expect(m.endsWith('…'), `${max}`).toBe(true);
      const cut = m.slice(0, -1);
      expect(text.startsWith(cut), `${max}`).toBe(true);
      // the cut ends a word: what follows it in the text is a space or a mark, never a letter
      expect(text.charAt(cut.length), `${max}`).toMatch(/[\s,;:·–-]/);
    }
  });
});

describe('"החדר שלך" names a piece by its base name (§1.1 rows 3, 9)', () => {
  it('an order keeps the joined line name; it splits back at the first " · "', () => {
    const name = lineName('שמיכת מוסלין כותנה עם פרנזים', '150×200 ס"מ, פקאן');
    expect(splitLineName(name)).toEqual({ base: 'שמיכת מוסלין כותנה עם פרנזים', label: '150×200 ס"מ, פקאן' });
    expect(splitLineName('אגרטל אבנית מקומט')).toEqual({ base: 'אגרטל אבנית מקומט', label: '' });
  });
});
