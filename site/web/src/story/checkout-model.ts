/**
 * The story's test checkout (/story/checkout/ → /story/order/), the pure part: the shipping the site charges (the
 * catalog's methods: economy free over its threshold, express always paid), the totals, the site's own field checks
 * (../validate.ts, the same messages as /checkout/), and the test order the browser keeps. Nothing is charged and
 * nothing reaches a supplier; the order keeps only what its confirmation shows (no e-mail, no phone, no address).
 */
import type { Cart, CheckoutRequest } from '@hd/shared';
import { validateCheckout, type FieldErrors } from '../validate';
import type { KeyValue } from './story-cart';

export type ShippingMethod = { id: 'economy' | 'express'; label_he: string; price_agorot: number; free_over_agorot: number | null; days_he: string };
export type CheckoutForm = {
  full_name: string;
  email: string;
  phone: string;
  city: string;
  street: string;
  house: string;
  apartment: string;
  zip: string;
  notes: string;
  terms: boolean;
  shipping: ShippingMethod['id'];
};
export type TestOrder = {
  id: string;
  at: string;
  first_name: string;
  city: string;
  shipping_he: string;
  lines: { name_he: string; option_he: string | null; qty: number; line_total_agorot: number }[];
  subtotal_agorot: number;
  shipping_agorot: number;
  total_agorot: number;
};

export function shippingFor(methods: ShippingMethod[], id: ShippingMethod['id'], subtotal: number): number {
  const m = methods.find((x) => x.id === id) ?? methods[0];
  if (!m) return 0;
  return m.free_over_agorot !== null && subtotal >= m.free_over_agorot ? 0 : m.price_agorot;
}
export function totals(methods: ShippingMethod[], id: ShippingMethod['id'], cart: Cart | null) {
  const subtotal = cart?.subtotal_agorot ?? 0;
  const shipping = subtotal ? shippingFor(methods, id, subtotal) : 0;
  const economy = methods.find((m) => m.id === 'economy');
  const toFree = economy?.free_over_agorot != null && subtotal < economy.free_over_agorot ? economy.free_over_agorot - subtotal : null;
  return { subtotal, shipping, total: subtotal + shipping, toFree };
}
/** the site's checks, on the form as the request the site would send */
export function errorsOf(f: CheckoutForm): FieldErrors {
  const req: CheckoutRequest = {
    cart_id: 'story-test-cart',
    customer: { full_name: f.full_name, email: f.email, phone: f.phone },
    address: { city: f.city, street: f.street, house: f.house, apartment: f.apartment || undefined, zip: f.zip || undefined, notes: f.notes || undefined },
    shipping_method: f.shipping,
    consents: { terms: f.terms as true, marketing: false },
  } as CheckoutRequest;
  return validateCheckout(req);
}

const ORDERS = 'hd.story.orders';
/** a test order's number: T and seven digits, never the site's own form (ten digits, constants ORDER_ID) */
export const orderId = (rand: () => number = Math.random): string => `T${String(Math.floor(rand() * 9_000_000) + 1_000_000)}`;
export function placeOrder(store: KeyValue, f: CheckoutForm, methods: ShippingMethod[], cart: Cart, now = new Date(), rand?: () => number): TestOrder {
  const t = totals(methods, f.shipping, cart);
  const order: TestOrder = {
    id: orderId(rand),
    at: now.toISOString(),
    first_name: f.full_name.trim().split(/\s+/)[0] ?? '',
    city: f.city.trim(),
    shipping_he: methods.find((m) => m.id === f.shipping)?.label_he ?? '',
    lines: cart.lines.map((l) => ({ name_he: l.name_he, option_he: l.option_he, qty: l.qty, line_total_agorot: l.line_total_agorot })),
    subtotal_agorot: t.subtotal,
    shipping_agorot: t.shipping,
    total_agorot: t.total,
  };
  // the last five test orders, in this browser only
  const all = [order, ...readOrders(store)].slice(0, 5);
  try {
    store.set(ORDERS, JSON.stringify(all));
  } catch {
    /* kept for the confirmation through the address only */
  }
  return order;
}
export function readOrders(store: KeyValue): TestOrder[] {
  try {
    const x = JSON.parse(store.get(ORDERS) ?? '[]') as unknown;
    return Array.isArray(x) ? (x.filter((o) => o && typeof (o as TestOrder).id === 'string' && Array.isArray((o as TestOrder).lines)) as TestOrder[]) : [];
  } catch {
    return [];
  }
}
