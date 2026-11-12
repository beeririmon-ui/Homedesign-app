/** S17, QA ה5: a field whose value is unknown is not shown; a note about the picture only beside a picture. */
import { describe, expect, it } from 'vitest';
import { isKnown, knownValues, visibleNotes } from '../src/pages/productNotes';

describe('ה5: the product page’s fields and notes', () => {
  const notes = ['בתמונה: עיתונים במחזיק. לא כלול במוצר.', 'דורשת התקנה על ידי חשמלאי.', 'בתמונה: סט של 3 פריטים.'];
  it('a page without a picture leaves out every note about the picture, and keeps the others', () => {
    expect(visibleNotes(notes, false)).toEqual(['דורשת התקנה על ידי חשמלאי.']);
    expect(visibleNotes(notes, true)).toEqual(notes);
  });
  it('a value that says it is unknown is no value; a list of them hides the field', () => {
    for (const v of ['לא צוין', 'חומר לא צוין', 'לא ידוע', 'החומר לא מצוין.', 'unknown', 'N/A', '—', '', '  ']) expect(isKnown(v), v).toBe(false);
    for (const v of ['לבד', 'מתכת', 'הדפס במרקם', 'עור (לא אמיתי)']) expect(isKnown(v), v).toBe(true);
    expect(knownValues(['לבד', 'חומר לא צוין', 'מתכת'])).toEqual(['לבד', 'מתכת']);
    expect(knownValues(['לא צוין'])).toEqual([]);
  });
});
