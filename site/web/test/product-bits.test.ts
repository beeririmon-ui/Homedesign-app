/** Product page parts (P1 set / single piece, D9 standards row), rendered to HTML as the prerender does. */
import { describe, it, expect } from 'vitest';
import { h } from 'preact';
import { renderToString } from 'preact-render-to-string';
import type { PublicProduct } from '@hd/shared';
import { publicSafety } from '@hd/shared/safety';
import { PackPicker, packPrice } from '../src/components/PackPicker';
import { SafetyRow } from '../src/components/SafetyRow';
import { lineLabelHe } from '../src/pages/lineLabel';

const base: PublicProduct = {
  id: 'candles',
  room: 'living-room',
  slot: 'candle-holders',
  name_he: 'פמוטים',
  name_provisional: true,
  description_he: '',
  price_agorot: 34900,
  compare_at_agorot: null,
  price_provisional: true,
  materials_he: [],
  dimensions_cm: { width: null, depth: null, height: null },
  color_hex: '#ffffff',
  shipping_days: null,
  notes_he: [],
  set_of: null,
  variants: [{ id: 'candles:default', label_he: 'ברירת מחדל' }],
  pack: { set_qty: 2, unit_price_agorot: 19900, unit_price_estimated: true },
  safety: null,
};
const noop = () => undefined;

describe('set or single piece picker', () => {
  it('is a labelled radio group with the set checked by default and a price on each choice', () => {
    const html = renderToString(h(PackPicker, { p: base, value: 'set', onChange: noop, id: 'pk' }));
    expect(html).toContain('role="radiogroup"');
    expect(html).toContain('aria-labelledby="pk-label"');
    expect(html).toMatch(/id="pk-label"[^>]*>איך לקנות/);
    expect((html.match(/type="radio"/g) ?? []).length).toBe(2);
    expect(html).toMatch(/value="set" checked/);
    expect(html).toContain('סט של 2');
    expect(html).toContain('יחידה אחת');
    expect(html).toContain('349');
    expect(html).toContain('199');
    expect(html).toContain('מחיר משוער');
  });

  it('is not shown for a product sold as one unit', () => {
    expect(renderToString(h(PackPicker, { p: { ...base, pack: null }, value: 'set', onChange: noop, id: 'pk' }))).toBe('');
  });

  it('prices the chosen pack', () => {
    expect(packPrice(base, 'set')).toBe(34900);
    expect(packPrice(base, 'unit')).toBe(19900);
    expect(packPrice({ ...base, pack: null }, 'unit')).toBe(34900);
  });

  it('labels cart and order lines', () => {
    expect(lineLabelHe({ pack: 'set', pack_qty: 2 })).toBe('סט של 2');
    expect(lineLabelHe({ pack: 'unit', pack_qty: 1 })).toBe('יחידה אחת');
    expect(lineLabelHe({ pack: 'set', pack_qty: 1 })).toBe('');
  });
});

describe('standards and safety row', () => {
  it('shows the card claims under "תקנים ובטיחות"', () => {
    const html = renderToString(h(SafetyRow, { safety: publicSafety({ toy_standard: ['EN71', 'SI-562'], ce: true }) }));
    expect(html).toContain('<dt>תקנים ובטיחות</dt>');
    expect(html).toContain('תקן צעצועים EN 71 / ת&quot;י 562');
    expect(html).toContain('<li>CE</li>');
    expect(html).toContain('לפי הספק');
  });

  it('a wired lamp says it needs an electrician; IP44 says bathroom', () => {
    const html = renderToString(h(SafetyRow, { safety: publicSafety({ power: 'wired', ip_rating: 'IP44' }) }));
    expect(html).toContain('דורשת התקנה על ידי חשמלאי');
    expect(html).toContain('IP44, מתאים לחדר רחצה');
  });

  it('renders nothing without the field or without claims', () => {
    expect(renderToString(h(SafetyRow, { safety: null }))).toBe('');
    expect(renderToString(h(SafetyRow, { safety: publicSafety({ ce: false, toy_standard: [] }) }))).toBe('');
  });

  it('links a verified certificate (new window, announced)', () => {
    const html = renderToString(
      h(SafetyRow, { safety: publicSafety({ certificates: [{ name: 'CE DoC', url: 'https://example.com/ce.pdf', verified: true }] }) }),
    );
    expect(html).toContain('href="https://example.com/ce.pdf"');
    expect(html).toContain('נפתח בחלון חדש');
    expect(html).not.toContain('לפי הספק');
  });
});
