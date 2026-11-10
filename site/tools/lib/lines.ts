/**
 * S11, QA S6–S7 ת8 / ת9 / ת12 and the manager's sale decisions. Pure rules over the designer's and the manager's data;
 * tools/build-catalog.ts applies them, tools/test/lines.test.ts checks them on the real files.
 *
 * - **The line (ת8, manager's decision):** a line in the cart, the checkout, the order and the invoice is the base name
 *   without a colour (`base_name_he`, data/catalog/names-he.json; or the option's own name, story.json `option_names_he`)
 *   · the Hebrew option labels (data/catalog/option-labels-he.json) in the card's axis order, joined with ", ".
 * - **Labels (ת12):** a public label is Hebrew; the only Latin allowed is a unit after a number (3000K).
 * - **What is sold:** an exclusion list (data/catalog/sale-exclusions.json: on an axis, only the identified values), and
 *   sets of distinct SKUs (story.json `set_axes`: the triptychs), sold as the set only: the other values of the set's
 *   axis are parts of it, never sold alone, and the set has no single-piece option (ת9, SET1).
 */
import { existsSync, readFileSync } from 'node:fs';
import { lineName } from '@hd/shared/lines';

export type LabelsFile = { labels: Record<string, Record<string, Record<string, string>>> };
export type NamesFile = { base_name_he?: Record<string, string>; frame_names_he?: Record<string, Record<string, string>> };
export type Exclusion = { card_id: string; axis: string; sell_only: string[]; why: string };
/**
 * A set of distinct SKUs (story.json `set_axes`). `parts`, when given, names the values of the axis that make the set
 * (sourcing names them when the card has more prints than the set); without it every value of the axis is a part.
 */
export type SetAxis = { axis: string; note_he: string; parts?: string[] };
export type LineData = {
  /** labels[card][axis][value], or null before the designer's file exists (the fallback is the card's own label) */
  labels: LabelsFile['labels'] | null;
  base: Record<string, string>;
  optionNames: Record<string, Record<string, string>>;
  exclusions: Exclusion[];
  sets: Record<string, SetAxis>;
};

const readIf = <T>(p: string): T | null => (existsSync(p) ? (JSON.parse(readFileSync(p, 'utf8')) as T) : null);

export function loadLineData(paths: { labels: string; names: string; story: string; exclusions: string }): LineData {
  const story = readIf<{ option_names_he?: Record<string, Record<string, string>>; set_axes?: Record<string, SetAxis> }>(paths.story) ?? {};
  return {
    labels: readIf<LabelsFile>(paths.labels)?.labels ?? null,
    base: readIf<NamesFile>(paths.names)?.base_name_he ?? {},
    optionNames: story.option_names_he ?? {},
    exclusions: readIf<{ exclusions: Exclusion[] }>(paths.exclusions)?.exclusions ?? [],
    sets: story.set_axes ?? {},
  };
}

/** The Hebrew label of a value (the designer's), else the card's own label. */
export function optionLabel(d: Pick<LineData, 'labels'>, card: string, axis: string, value: string, fallback: string): string {
  return d.labels?.[card]?.[axis]?.[value] ?? fallback;
}

/** The line's base name for a variant: the option's own name (option_names_he), else the product's base, else `fallback`. */
export function lineBase(d: Pick<LineData, 'base' | 'optionNames'>, card: string, values: Record<string, string>, fallback: string): string {
  const own = d.optionNames[card];
  if (own) for (const [a, v] of Object.entries(values)) if (own[`${a}:${v}`]) return own[`${a}:${v}`]!;
  return d.base[card] ?? fallback;
}

/** "base · labels" (the rule, @hd/shared/lines); the base alone when there is no label. */
export { lineName };

type CardLike = { id: string; options?: { axes: { id: string; values: { id: string; label_he: string }[] }[] } | null };
/**
 * A variant's line: its base (lineBase), its Hebrew labels in the card's axis order (a set's own axis aside: which print
 * of a triptych is not a choice), and the two joined by the rule.
 */
export function lineOf(d: LineData, card: CardLike, values: Record<string, string>, fallback: string): { base: string; label: string | null; line: string } {
  const set = d.sets[card.id];
  const label =
    (card.options?.axes ?? [])
      .filter((a) => a.id !== set?.axis)
      .map((a) => {
        const v = a.values.find((x) => x.id === values[a.id]);
        return v ? optionLabel(d, card.id, a.id, v.id, v.label_he) : '';
      })
      .filter(Boolean)
      .join(', ') || null;
  const base = lineBase(d, card.id, values, fallback);
  return { base, label, line: lineName(base, label) };
}

export type Sale = { excluded: string | null; set_part: boolean };
/**
 * Whether a variant is offered: `excluded` names why not (the exclusion list); `set_part` is a print of a triptych other
 * than the set's own (the default SKU's value on the set's axis): part of the set, not sold on its own.
 */
export function saleOf(d: Pick<LineData, 'exclusions' | 'sets'>, card: string, values: Record<string, string>, setValue: string | null): Sale {
  const ex = d.exclusions.find((e) => e.card_id === card && values[e.axis] !== undefined && !e.sell_only.includes(values[e.axis]!));
  const set = d.sets[card];
  return {
    excluded: ex ? `sale-exclusions: ${ex.axis}=${values[ex.axis]} (${ex.why})` : null,
    set_part: !!set && setValue !== null && values[set.axis] !== setValue,
  };
}

/** Latin letters in a public label, a unit after a number (3000K, 4000 K) excepted. */
export const hasLatin = (s: string): boolean => /[A-Za-z]/.test(s.replace(/\d+\s*K\b/g, ''));

type PublicLike = {
  products: {
    id: string;
    variants: { id: string; label_he: string }[];
    options: { axes: { id: string; name_he: string; values: [string, string, string | null][] }[] } | null;
  }[];
};
type FullLike = { products: { id: string; variants_full?: { id: string; label_he: string; option_label_he: string | null; line_name_he?: string }[] }[] };

/** Every public label (and line) with Latin in it: the build check of ת12. */
export function latinLabels(pub: PublicLike, full?: FullLike): { product: string; where: string; text: string }[] {
  const out: { product: string; where: string; text: string }[] = [];
  const add = (product: string, where: string, text: string | null | undefined) => {
    if (text && hasLatin(text)) out.push({ product, where, text });
  };
  for (const p of pub.products) {
    for (const v of p.variants) add(p.id, `variant ${v.id}`, v.label_he);
    for (const a of p.options?.axes ?? []) {
      add(p.id, `axis ${a.id}`, a.name_he);
      for (const [id, label] of a.values) add(p.id, `${a.id}=${id}`, label);
    }
  }
  for (const p of full?.products ?? [])
    for (const v of p.variants_full ?? []) {
      add(p.id, `line ${v.id}`, v.line_name_he);
      add(p.id, `option ${v.id}`, v.option_label_he);
      add(p.id, `label ${v.id}`, v.label_he);
    }
  return out;
}

export type SetComposition = { skus: string[]; incomplete: null } | { skus: null; incomplete: string };
type SkuLike = { id: string; values: Record<string, string> };
/**
 * S12 (S11 question 2): the supplier SKUs a set is made of, one of each: for the set's SKU `sku`, the SKU of every part
 * (a value of the set's axis) with the same values on the other axes (the size chosen). The set is sold only when the
 * card names exactly `size` distinct SKUs for it; otherwise `incomplete` says what sourcing has to name. Never N × one SKU.
 */
export function setComposition(set: SetAxis, axis: { values: { id: string }[] } | undefined, skus: SkuLike[], sku: SkuLike, size: number): SetComposition {
  const values = axis?.values.map((v) => v.id) ?? [];
  const parts = set.parts ?? (values.length === size ? values : null);
  if (!parts)
    return {
      skus: null,
      incomplete: `the card has ${values.length} values on "${set.axis}" (${values.join(', ')}) for a set of ${size}: which ${size} make the set is not named`,
    };
  if (parts.length !== size) return { skus: null, incomplete: `${parts.length} parts named for a set of ${size}` };
  if (!parts.includes(sku.values[set.axis] ?? ''))
    return { skus: null, incomplete: `the set's own SKU ${sku.id} is not one of its parts (${parts.join(', ')})` };
  const out: string[] = [];
  for (const part of parts) {
    const match = skus.filter((s) => s.values[set.axis] === part && Object.entries(sku.values).every(([a, v]) => a === set.axis || s.values[a] === v));
    if (match.length !== 1) {
      const other = Object.entries(sku.values)
        .filter(([a]) => a !== set.axis)
        .map(([a, v]) => `${a}=${v}`)
        .join(', ');
      return { skus: null, incomplete: `${match.length ? 'more than one SKU' : 'no SKU'} for ${set.axis}=${part}${other ? ` at ${other}` : ''}` };
    }
    out.push(match[0]!.id);
  }
  if (new Set(out).size !== out.length) return { skus: null, incomplete: `the parts share a SKU (${out.join(', ')})` };
  return { skus: out, incomplete: null };
}
