/**
 * S11 (QA S6–S7 ת8, ת9, ת12; the manager's sale decisions), on the real data files: the line rule on the nine variants
 * QA found, no Latin in a public label, the sale exclusions and the sets of distinct SKUs. Each check turns on once its
 * file exists (master-designer's labels and names, the manager's exclusions).
 */
import { describe, expect, it } from 'vitest';
import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { hasLatin, latinLabels, lineOf, loadLineData, saleOf, type LineData } from '../lib/lines';
import { repoPath } from '../lib/paths';

type Card = {
  id: string;
  options?: {
    default_sku: string;
    axes: { id: string; values: { id: string; label_he: string }[] }[];
    skus: { id: string; values: Record<string, string> }[];
  } | null;
};
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : f.endsWith('.json') ? [join(d, f)] : []));
const cards = new Map<string, Card>();
for (const f of walk(repoPath('data/products'))) {
  try {
    const c = JSON.parse(readFileSync(f, 'utf8')) as Card;
    if (typeof c.id === 'string' && !cards.has(c.id)) cards.set(c.id, c);
  } catch {
    /* not a card */
  }
}
const PATHS = {
  labels: repoPath('data/catalog/option-labels-he.json'),
  names: repoPath('data/catalog/names-he.json'),
  story: repoPath('data/story/story.json'),
  exclusions: repoPath('data/catalog/sale-exclusions.json'),
};
const data: LineData = loadLineData(PATHS);
const card = (id: string) => {
  const c = cards.get(id);
  if (!c) throw new Error(`no card ${id}`);
  return c;
};

describe('ת8: the line is the base name without a colour · the Hebrew option labels', () => {
  // QA's eight variants and the designer's ninth (the corduroy of ת10), as docs/proposals/names-labels-he-2026-11-10.md
  const NINE: [string, string[], string][] = [
    ['cushions-cj-washed-cotton-frayed', ['50x50', 'white'], 'ציפית כרית כותנה רחוצה עם שוליים פרומים · 50×50 ס"מ, לבן'],
    ['cushions-cj-washed-cotton-frayed', ['50x50', 'earthy-orange'], 'ציפית כרית כותנה רחוצה עם שוליים פרומים · 50×50 ס"מ, טרקוטה'],
    ['cushions-cj-washed-cotton-frayed', ['30x50', 'moss-green'], 'ציפית כרית מותן כותנה רחוצה עם שוליים פרומים · 30×50 ס"מ, ירוק טחב'],
    ['sofa-cover-cj-washed-hemp-throw', ['150x200', 'raw-jute-color'], 'שמיכת קנבוס רחוצה · 150×200 ס"מ, חום יוטה'],
    ['sofa-cover-cj-cotton-muslin-fringe', ['150x200', 'flax-brown'], 'שמיכת מוסלין כותנה עם פרנזים · 150×200 ס"מ, חום פשתן'],
    ['cushions-cj-boucle-teddy', ['milk-tea-color', '50x50'], 'ציפית כרית בוקלה · תה חלב, 50×50 ס"מ'],
    ['cushions-cj-boucle-teddy', ['white', '50x50'], 'ציפית כרית בוקלה · לבן חם, 50×50 ס"מ'],
    ['planter-cj-seagrass-belly', ['yellow', '35x37-cm'], 'סל-עציץ בטן מקש ים · דבש, 35×37 ס"מ'],
    ['cushions-cj-wide-stripe-corduroy-light-green', ['camel'], 'ציפית כרית קורדרוי בדוגמת שיבולים · קאמל'],
  ];
  it.runIf(existsSync(PATHS.labels) && existsSync(PATHS.names))('the nine variants QA found read as what was bought', () => {
    for (const [id, values, want] of NINE) {
      const c = card(id);
      const sku = c.options!.skus.find((k) => [...Object.values(k.values)].sort().join() === [...values].sort().join());
      expect(sku, `${id} sells ${JSON.stringify(values)}`).toBeTruthy();
      expect(lineOf(data, c, sku!.values, 'fallback').line).toBe(want);
    }
  });
  it('without the designer’s files the card’s own label and the product’s name stand (the fallback)', () => {
    const bare: LineData = { labels: null, base: {}, optionNames: {}, exclusions: [], sets: {} };
    const c = card('cushions-cj-boucle-teddy');
    const sku = c.options!.skus.find((k) => k.id === c.options!.default_sku)!;
    const l = lineOf(bare, c, sku.values, 'ציפית כרית בוקלה, לבן חם');
    expect(l.base).toBe('ציפית כרית בוקלה, לבן חם');
    expect(l.label).toBe(c.options!.axes.map((a) => a.values.find((v) => v.id === sku.values[a.id])!.label_he).join(', '));
  });
  it('an option with its own name is the base of its line (option_names_he)', () => {
    const c = card('cushions-cj-linen-look-charcoal');
    const sku = c.options!.skus.find((k) => k.values.style === 'pillowcase');
    expect(sku).toBeTruthy();
    expect(lineOf(data, c, sku!.values, 'x').base).toBe('ציפית כרית במראה פשתן');
  });
});

describe('ת12: no Latin in a public label', () => {
  it.runIf(existsSync(PATHS.labels))("every label of the designer's file is Hebrew (a unit after a number, 3000K, aside)", () => {
    const bad: string[] = [];
    for (const [id, axes] of Object.entries(data.labels ?? {}))
      for (const [axis, values] of Object.entries(axes))
        for (const [v, label] of Object.entries(values)) if (hasLatin(label)) bad.push(`${id} ${axis}=${v}: ${label}`);
    expect(bad).toEqual([]);
  });
  it.runIf(existsSync(PATHS.labels))('every key of the labels is a value of its card (the same keys the SKU carries)', () => {
    const missing: string[] = [];
    for (const [id, axes] of Object.entries(data.labels ?? {})) {
      const c = cards.get(id);
      if (!c?.options) {
        missing.push(`${id}: no card with options`);
        continue;
      }
      for (const [axis, values] of Object.entries(axes))
        for (const v of Object.keys(values)) if (!c.options.axes.find((a) => a.id === axis)?.values.some((x) => x.id === v)) missing.push(`${id} ${axis}=${v}`);
    }
    expect(missing).toEqual([]);
  });
  it('the build check finds an English label, an English axis and an English line, and lets a unit pass', () => {
    const pub = {
      products: [
        {
          id: 'p',
          variants: [{ id: 'p:a', label_he: 'ברירת מחדל' }],
          options: {
            axes: [
              {
                id: 'color',
                name_he: 'צבע',
                values: [['a', 'Flax brown', null] as [string, string, string | null], ['b', 'אור לבן חם 3000K', null] as [string, string, string | null]],
              },
              { id: 'size', name_he: 'Size', values: [['s', '45×45 ס"מ', null] as [string, string, string | null]] },
            ],
          },
        },
      ],
    };
    const full = { products: [{ id: 'p', variants_full: [{ id: 'p:a', label_he: 'צבע: א', option_label_he: '(Wear Rod)', line_name_he: 'כרית' }] }] };
    expect(latinLabels(pub, full).map((x) => x.text)).toEqual(['Flax brown', 'Size', '(Wear Rod)']);
    expect(hasLatin('4000 K, 6000K')).toBe(false);
    expect(hasLatin('Raw Jute Color')).toBe(true);
  });
});

describe("the manager's sale decisions: exclusions and sets (ת9)", () => {
  it.runIf(existsSync(PATHS.exclusions))('every exclusion names a card, an axis and values it has, and keeps the room’s own SKU', () => {
    expect(data.exclusions.length).toBeGreaterThan(0);
    for (const e of data.exclusions) {
      const c = card(e.card_id);
      const axis = c.options?.axes.find((a) => a.id === e.axis);
      expect(axis, `${e.card_id} has the axis ${e.axis}`).toBeTruthy();
      for (const v of e.sell_only)
        expect(
          axis!.values.some((x) => x.id === v),
          `${e.card_id} ${e.axis}=${v}`,
        ).toBe(true);
      const dflt = c.options!.skus.find((k) => k.id === c.options!.default_sku)!;
      expect(saleOf(data, e.card_id, dflt.values, null).excluded, `${e.card_id}: the room's SKU is sold`).toBeNull();
    }
  });
  it.runIf(existsSync(PATHS.exclusions))('the floor lamp sells only the regular lamp; the travertine lamp and the black bowl only what is identified', () => {
    const sold = (id: string) =>
      card(id)
        .options!.skus.filter((k) => !saleOf(data, id, k.values, null).excluded)
        .map((k) => Object.values(k.values).join('+'));
    expect(sold('floor-lamp-cj-pleated-walnut-stem-158')).toEqual(['3color-floor-lamp']);
    expect(sold('accent-sconces-cj-ribbed-travertine-half-cylinder-wood-bracket')).toEqual(['type-b']);
    expect(sold('bowl-cj-matte-black-bowl-20')).toEqual(['12style']);
    expect(sold('accent-sconces-cj-travertine-block-updown-8x16').sort()).toEqual(['type-b+indoor', 'type-b+outdoor']);
  });
  it('the two triptychs are sets: the default SKU’s print is the set, the other prints its parts, never sold alone', () => {
    for (const id of ['framed-art-aliexpress-minimal-geometric-triptych-prints', 'framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890']) {
      const set = data.sets[id];
      expect(set, `${id} is a set`).toBeTruthy();
      const c = card(id);
      expect(c.options!.axes.some((a) => a.id === set!.axis)).toBe(true);
      const own = c.options!.skus.find((k) => k.id === c.options!.default_sku)!.values[set!.axis]!;
      const parts = c.options!.skus.filter((k) => saleOf(data, id, k.values, own).set_part);
      const sets = c.options!.skus.filter((k) => !saleOf(data, id, k.values, own).set_part);
      expect(sets.every((k) => k.values[set!.axis] === own)).toBe(true);
      expect(parts.length).toBe(c.options!.skus.length - sets.length);
      expect(parts.length).toBeGreaterThan(0);
      // the set's line does not name one print
      const line = lineOf(data, c, sets[0]!.values, 'x');
      expect(line.label ?? '').not.toMatch(/הדפס \d/);
    }
  });
});
