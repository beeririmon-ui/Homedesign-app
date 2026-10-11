/** Supplier options on the product page (2026-10-11), rendered to HTML as the prerender does. */
import { describe, it, expect } from 'vitest';
import { h } from 'preact';
import { renderToString } from 'preact-render-to-string';
import type { PublicProduct } from '@hd/shared';
import { OptionPicker } from '../src/components/OptionPicker';
import { variantView, variantPackPrice, defaultVariantId } from '../src/variants';
import { lineLabelHe } from '../src/pages/lineLabel';

const sizes = ['30x50', '40x40', '45x45', '50x50', '55x55', '60x60', '65x65', '70x70', '80x80'];
const p: PublicProduct = {
  id: 'cushion',
  room: 'living-room',
  slot: 'cushions',
  name_he: 'כרית',
  name_provisional: true,
  description_he: '',
  price_agorot: 8900,
  compare_at_agorot: null,
  price_provisional: true,
  materials_he: [],
  dimensions_cm: { width: null, depth: null, height: null },
  color_hex: '#D9CBB3',
  shipping_days: [6, 15],
  notes_he: [],
  set_of: null,
  variants: [],
  pack: null,
  safety: null,
  // compact, as the catalog ships it (shared/src/options.ts): beige 45×45 (the room's), beige 60×60, black 45×45
  options: {
    axes: [
      {
        id: 'color',
        name_he: 'צבע',
        values: [
          ['beige', "בז'", '#D9CBB3'],
          ['black', 'שחור', '#1E1E1E'],
        ],
      },
      { id: 'size', name_he: 'מידה', values: sizes.map((s) => [s, `${s.replace('x', '×')} ס"מ`, null] as [string, string, null]) },
    ],
    v: [
      [0, 2],
      [0, 5],
      [1, 2],
    ],
    p: [8900, 11900, 8900],
    room: 0,
    off: [],
    pv: true,
    px: [],
    u: null,
    d: [null, [8, 18], null],
  },
};
const ROOM = 'cushion:beige+45x45';
const BIG = 'cushion:beige+60x60';
const BLACK = 'cushion:black+45x45';

describe('option picker', () => {
  it("starts on the room's option: a colour fieldset with swatches, and a select for a long list", () => {
    expect(defaultVariantId(p)).toBe(ROOM);
    const html = renderToString(h(OptionPicker, { p, value: defaultVariantId(p), onChange: () => {}, id: 'o' }));
    expect(html).toContain('<fieldset class="opt-axis"><legend class="opt-legend">צבע: <span class="opt-current">בז\'</span></legend>');
    expect(html).toMatch(/<input type="radio" name="o-color" value="beige" checked/);
    expect(html).toContain('class="opt-values is-swatches"');
    expect(html).toContain('<label class="opt-legend" for="o-size">מידה</label>');
    // sizes that do not exist in beige are disabled, the room's is selected
    expect(html).toContain('<option value="50x50" disabled>50×50 ס&quot;מ (לא זמין בבחירה הזו)</option>');
    expect(html).toContain('<option value="60x60">60×60 ס&quot;מ</option>');
    expect(html).toContain('<option selected value="45x45">');
    expect(html).not.toContain('חזרה לאפשרות שבחדר');
  });

  it('another option: its own price and days, and a line that names the room’s option', () => {
    const html = renderToString(h(OptionPicker, { p, value: BIG, onChange: () => {}, id: 'o' }));
    expect(html).toContain("בחדר מוצגת האפשרות בז', 45×45 ס&quot;מ.");
    const v = variantView(p, BIG)!;
    expect(variantPackPrice(v, 'set')).toBe(11900);
    expect(v.shipping_days).toEqual([8, 18]);
    expect(v.option_he).toBe('בז\', 60×60 ס"מ');
    expect(variantView(p, BLACK)!.shipping_days).toEqual([6, 15]); // null = the product's days
    expect(variantView(p, 'nope')).toBeNull();
  });

  it('the cart line names the option and the pack', () => {
    expect(lineLabelHe({ pack: 'set', pack_qty: 1, option_he: 'שחור, 45×45 ס"מ' })).toBe('שחור, 45×45 ס"מ');
    expect(lineLabelHe({ pack: 'unit', pack_qty: 1, option_he: 'שחור' })).toBe('שחור, יחידה אחת');
    expect(lineLabelHe({ pack: 'set', pack_qty: 2 })).toBe('סט של 2');
  });
});
