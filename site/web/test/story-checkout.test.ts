/**
 * The story's test checkout (web/src/story/checkout-model.ts): the site's shipping (economy free over its threshold),
 * the totals, the site's own field checks, and the test order the browser keeps (no e-mail, no phone, no address).
 */
import { describe, expect, it } from 'vitest';
import type { Cart } from '@hd/shared';
import { errorsOf, orderId, placeOrder, readOrders, shippingFor, totals, type CheckoutForm, type ShippingMethod } from '../src/story/checkout-model';
import { memoryStore } from '../src/story/story-cart';

const M: ShippingMethod[] = [
  { id: 'economy', label_he: 'משלוח חסכוני', price_agorot: 2900, free_over_agorot: 29900, days_he: '' },
  { id: 'express', label_he: 'משלוח מהיר', price_agorot: 5900, free_over_agorot: null, days_he: '' },
];
const cart = (subtotal: number): Cart => ({
  id: 'c',
  lines: [
    {
      variant_id: 'v',
      product_id: 'p',
      name_he: 'קערה',
      option_he: null,
      pack: 'set',
      pack_qty: 1,
      qty: 1,
      unit_price_agorot: subtotal,
      line_total_agorot: subtotal,
      price_provisional: true,
    },
  ],
  subtotal_agorot: subtotal,
  count: 1,
});
const form: CheckoutForm = {
  full_name: 'נועה כהן',
  email: 'noa@example.com',
  phone: '050-1234567',
  city: 'חיפה',
  street: 'הנמל',
  house: '12',
  apartment: '',
  zip: '',
  notes: '',
  terms: true,
  shipping: 'economy',
};

describe('the story test checkout', () => {
  it('charges the site shipping: economy free from its threshold, express always', () => {
    expect(shippingFor(M, 'economy', 7900)).toBe(2900);
    expect(shippingFor(M, 'economy', 29900)).toBe(0);
    expect(shippingFor(M, 'express', 99900)).toBe(5900);
    expect(totals(M, 'economy', cart(7900))).toEqual({ subtotal: 7900, shipping: 2900, total: 10800, toFree: 22000 });
    expect(totals(M, 'economy', null)).toEqual({ subtotal: 0, shipping: 0, total: 0, toFree: 29900 });
  });

  it('checks the fields with the site rules and messages', () => {
    expect(errorsOf(form)).toEqual({});
    const e = errorsOf({ ...form, full_name: 'נ', email: 'noa', phone: '123', terms: false, zip: '12' });
    expect(Object.keys(e).sort()).toEqual(['email', 'full_name', 'phone', 'terms', 'zip']);
    expect(e.phone).toContain('050-1234567');
  });

  it('keeps a test order in the browser with only what its confirmation shows, newest first, five at most', () => {
    const store = memoryStore();
    const o = placeOrder(store, form, M, cart(7900), new Date('2026-11-07T12:00:00Z'), () => 0.5);
    expect(o).toMatchObject({ id: 'T5500000', first_name: 'נועה', city: 'חיפה', subtotal_agorot: 7900, shipping_agorot: 2900, total_agorot: 10800 });
    const kept = JSON.stringify(readOrders(store));
    for (const secret of ['noa@example.com', '050-1234567', 'הנמל']) expect(kept).not.toContain(secret);
    for (let i = 0; i < 6; i++) placeOrder(store, form, M, cart(100), undefined, () => i / 10);
    expect(readOrders(store)).toHaveLength(5);
    expect(orderId(() => 0)).toMatch(/^T\d{7}$/);
  });
});
