/**
 * S17, QA ה5 (the public build's magazine holders): what the product page says under its specs.
 *
 * - **A note about the picture** ("בתמונה: עיתונים במחזיק. לא כלול במוצר.") describes the picture beside it. A page with
 *   no picture (no render, and a supplier photo the public build withholds for its rights) leaves it out.
 * - **A value that says it is unknown** ("לא צוין", "לא ידוע") is no value: the field is not shown. The catalog already
 *   drops such values (tools/lib/hebrew.ts, and the build check in tools/build-catalog.ts); the page does it again, for
 *   every field it shows.
 */
const UNKNOWN = /^(?:(?:ה?חומר|ערך|צבע|מידה|מידות)\s+)?(?:לא\s+(?:צוין|מצוין|צויין|ידוע|ידועה|ברור|ברורה|מוגדר|הוגדר)|אינו\s+ידוע)\.?$|^(?:unknown|n\/?a|not stated|unspecified|\?+|[-–—]+)$/i;

/** a value worth a line: not empty, and not a value that says it is unknown */
export const isKnown = (v: string | null | undefined): v is string => !!v && !!v.trim() && !UNKNOWN.test(v.trim());

/** the values of a list field worth showing (an empty result hides the field) */
export const knownValues = (list: readonly string[]): string[] => list.filter(isKnown);

/** the product's notes as the page shows them: a note about the picture only when there is one */
export const visibleNotes = (notes: readonly string[], hasPicture: boolean): string[] =>
  notes.filter((n) => isKnown(n) && (hasPicture || !/^בתמונה(?=[:\s])/.test(n.trim())));
