/**
 * S12 (S11 question 2), on the real cards: a set of distinct SKUs is made of its parts' SKUs, one of each, at the size
 * chosen; the supplier order carries those, never 3 × print 1. A set whose card does not name its parts is refused and
 * listed for sourcing (the build writes .generated/sets-composition.json).
 */
import { describe, expect, it } from 'vitest';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { loadLineData, setComposition } from '../lib/lines';
import { repoPath } from '../lib/paths';

type Card = {
  id: string;
  options: { default_sku: string; axes: { id: string; values: { id: string }[] }[]; skus: { id: string; values: Record<string, string> }[] };
};
const walk = (d: string): string[] =>
  readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : f.endsWith('.json') ? [join(d, f)] : []));
const cards = new Map<string, Card>();
for (const f of walk(repoPath('data/products'))) {
  try {
    const c = JSON.parse(readFileSync(f, 'utf8')) as Card;
    if (typeof c.id === 'string') cards.set(c.id, c);
  } catch {
    /* not a card */
  }
}
const sets = loadLineData({
  labels: repoPath('data/catalog/option-labels-he.json'),
  names: repoPath('data/catalog/names-he.json'),
  story: repoPath('data/story/story.json'),
  exclusions: repoPath('data/catalog/sale-exclusions.json'),
}).sets;
const TRIPTYCH = 'framed-art-aliexpress-minimal-geometric-triptych-prints';
const MEDITERRANEAN = 'framed-art-aliexpress-mediterranean-wabi-sabi-poster-802890';

describe('the sets of distinct SKUs (S12)', () => {
  it('the Nordic triptych: at every size, prints 1, 2 and 3 of that size, three different SKUs from the card', () => {
    const c = cards.get(TRIPTYCH)!;
    const set = sets[TRIPTYCH]!;
    const axis = c.options.axes.find((a) => a.id === set.axis);
    const own = c.options.skus.filter((s) => s.values[set.axis] === '1');
    expect(own).toHaveLength(4);
    for (const s of own) {
      const r = setComposition(set, axis, c.options.skus, s, 3);
      expect(r.incomplete, s.id).toBeNull();
      const want = ['1', '2', '3'].map((p) => c.options.skus.find((x) => x.values[set.axis] === p && x.values.size === s.values.size)!.id);
      expect(r.skus).toEqual(want);
      expect(new Set(r.skus).size).toBe(3);
    }
    // the room's set (50×70): 12000039454944614, ‑618 and ‑622
    const room = c.options.skus.find((s) => s.id === c.options.default_sku)!;
    expect(setComposition(set, axis, c.options.skus, room, 3).skus).toEqual(['12000039454944614', '12000039454944618', '12000039454944622']);
  });

  it('the Mediterranean print: eight prints on the card, and which three make the set is not named: not sold, for sourcing', () => {
    const c = cards.get(MEDITERRANEAN)!;
    const set = sets[MEDITERRANEAN]!;
    const room = c.options.skus.find((s) => s.id === c.options.default_sku)!;
    const r = setComposition(
      set,
      c.options.axes.find((a) => a.id === set.axis),
      c.options.skus,
      room,
      3,
    );
    expect(r.skus).toBeNull();
    expect(r.incomplete).toMatch(/8 values on "color".*which 3 make the set is not named/);
    // once sourcing names the three (story.json set_axes `parts`), the set is their SKUs at the size chosen
    const named = setComposition(
      { ...set, parts: ['03', '05', '08'] },
      c.options.axes.find((a) => a.id === set.axis),
      c.options.skus,
      room,
      3,
    );
    expect(named.incomplete).toBeNull();
    expect(new Set(named.skus).size).toBe(3);
  });

  it('a card with one SKU for every print, or a print missing at a size, is never a set', () => {
    const axis = { values: [{ id: '1' }, { id: '2' }, { id: '3' }] };
    const set = { axis: 'color', note_he: '' };
    const s = (id: string, color: string, size = 'm') => ({ id, values: { color, size } });
    expect(setComposition(set, axis, [s('A', '1'), s('A', '2'), s('A', '3')], s('A', '1'), 3).incomplete).toMatch(/share a SKU/);
    expect(setComposition(set, axis, [s('A', '1'), s('B', '2'), s('C', '3', 'l')], s('A', '1'), 3).incomplete).toMatch(/no SKU for color=3 at size=m/);
    expect(setComposition(set, axis, [s('A', '1'), s('B', '2'), s('C', '3')], s('A', '1'), 2).incomplete).toMatch(/which 2 make the set/);
  });
});
