/**
 * In-browser stand-in for the Worker API, used by the artifact preview (no server there).
 * Same contract as api/http.ts; prices come from the bundled catalog, state lives in localStorage
 * (wrapped in try/catch: storage can be unavailable), and payment is simulated by /mock-pay.
 */
import type { Cart, CheckoutRequest, OrderView, Pack } from '@hd/shared';
import { ORDER_STATUS_HE, type OrderStatus } from '@hd/shared/constants';
import { catalog } from '../catalog';
import { validateCheckout } from '../validate';
import { ApiError, type StoreApi } from './types';

type MockCart = { id: string; open: boolean; items: { variant_id: string; pack?: Pack; qty: number }[] };
type MockOrder = {
  id: string;
  token: string;
  session: string;
  status: OrderStatus;
  created_at: string;
  total_agorot: number;
  shipping_method: 'economy' | 'express';
  lines: OrderView['lines'];
};

const mem = new Map<string, string>();
const store = {
  get(k: string): string | null {
    try {
      return localStorage.getItem(k);
    } catch {
      return mem.get(k) ?? null;
    }
  },
  set(k: string, v: string): void {
    try {
      localStorage.setItem(k, v);
    } catch {
      mem.set(k, v);
    }
  },
};
const read = <T>(k: string, d: T): T => {
  try {
    return (JSON.parse(store.get(k) ?? 'null') as T) ?? d;
  } catch {
    return d;
  }
};
const write = (k: string, v: unknown) => store.set(k, JSON.stringify(v));
const rid = (n = 18) => [...crypto.getRandomValues(new Uint8Array(n))].map((b) => 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'[b % 56]).join('');
const delay = (ms = 120) => new Promise((r) => setTimeout(r, ms));

const variantIndex = new Map(catalog.products.flatMap((p) => p.variants.map((v) => [v.id, p] as const)));

function view(c: MockCart): Cart {
  // same rules as the Worker (api/src/lib/store.ts): the set by default, one piece only where the product has it
  const lines = c.items.flatMap((i) => {
    const p = variantIndex.get(i.variant_id);
    const pack: Pack = i.pack ?? 'set';
    if (!p || (pack === 'unit' && !p.pack)) return [];
    const price = pack === 'unit' ? p.pack!.unit_price_agorot : p.price_agorot;
    return [
      {
        variant_id: i.variant_id,
        product_id: p.id,
        name_he: p.name_he,
        pack,
        pack_qty: pack === 'unit' ? 1 : (p.pack?.set_qty ?? 1),
        qty: i.qty,
        unit_price_agorot: price,
        line_total_agorot: price * i.qty,
        price_provisional: p.price_provisional || (pack === 'unit' && p.pack!.unit_price_estimated),
      },
    ];
  });
  return { id: c.id, lines, subtotal_agorot: lines.reduce((s, l) => s + l.line_total_agorot, 0), count: lines.reduce((s, l) => s + l.qty, 0) };
}

function cartOr404(id: string): MockCart {
  const carts = read<Record<string, MockCart>>('hd.mock.carts', {});
  const c = carts[id];
  if (!c) throw new ApiError(404, 'cart_not_found');
  if (!c.open) throw new ApiError(409, 'cart_closed');
  return c;
}
function saveCart(c: MockCart) {
  const carts = read<Record<string, MockCart>>('hd.mock.carts', {});
  carts[c.id] = c;
  write('hd.mock.carts', carts);
}
const orders = () => read<Record<string, MockOrder>>('hd.mock.orders', {});

export const mockApi: StoreApi = {
  kind: 'mock',
  async createCart() {
    await delay();
    const c: MockCart = { id: rid(32), open: true, items: [] };
    saveCart(c);
    return view(c);
  },
  async getCart(id) {
    await delay(40);
    return view(cartOr404(id));
  },
  async setItem(cartId, variant_id, pack, qty) {
    await delay();
    const c = cartOr404(cartId);
    const p = variantIndex.get(variant_id);
    if (!p) throw new ApiError(404, 'variant_not_found', 'המוצר לא זמין.');
    if (!Number.isInteger(qty) || qty < 0 || qty > 20 || (pack !== 'set' && pack !== 'unit')) throw new ApiError(422, 'invalid_body');
    if (pack === 'unit' && !p.pack) throw new ApiError(422, 'pack_unavailable', 'המוצר הזה נמכר רק כסט.');
    const same = (i: MockCart['items'][number]) => i.variant_id === variant_id && (i.pack ?? 'set') === pack;
    const at = c.items.findIndex(same);
    if (qty === 0) c.items = c.items.filter((i) => !same(i));
    else if (at >= 0) c.items[at] = { variant_id, pack, qty };
    else c.items.push({ variant_id, pack, qty });
    saveCart(c);
    return view(c);
  },
  async checkout(req: CheckoutRequest) {
    await delay(300);
    if (Object.keys(validateCheckout(req)).length) throw new ApiError(422, 'invalid_body', 'חלק מהפרטים חסרים או לא תקינים.');
    const c = cartOr404(req.cart_id);
    const v = view(c);
    if (!v.lines.length) throw new ApiError(409, 'cart_empty', 'הסל ריק.');
    const ship = catalog.shipping.find((s) => s.id === req.shipping_method)!;
    const id = `HD-${rid(8).toUpperCase()}`;
    const o: MockOrder = {
      id,
      token: rid(32),
      session: `ms_${rid(18)}`,
      status: 'pending_payment',
      created_at: new Date().toISOString(),
      total_agorot: v.subtotal_agorot + (ship.free_over_agorot !== null && v.subtotal_agorot >= ship.free_over_agorot ? 0 : ship.price_agorot),
      shipping_method: req.shipping_method,
      lines: v.lines.map((l) => ({ name_he: l.name_he, pack: l.pack, pack_qty: l.pack_qty, qty: l.qty, line_total_agorot: l.line_total_agorot })),
    };
    write('hd.mock.orders', { ...orders(), [id]: o });
    c.open = false;
    saveCart(c);
    return { order_id: id, order_token: o.token, redirect_url: `/mock-pay/${o.session}` };
  },
  async getOrder(id, token) {
    await delay(80);
    const o = orders()[id];
    if (!o || o.token !== token) throw new ApiError(404, 'order_not_found');
    const view: OrderView = {
      id: o.id,
      status: o.status,
      status_he: ORDER_STATUS_HE[o.status],
      created_at: o.created_at,
      total_agorot: o.total_agorot,
      shipping_method: o.shipping_method,
      lines: o.lines,
    };
    return view;
  },
  mockPay: {
    async info(session) {
      const o = Object.values(orders()).find((x) => x.session === session);
      if (!o) throw new ApiError(404, 'session_not_found');
      return { order_id: o.id, total_agorot: o.total_agorot };
    },
    async complete(session, outcome) {
      await delay(400);
      const all = orders();
      const o = Object.values(all).find((x) => x.session === session);
      if (!o) throw new ApiError(404, 'session_not_found');
      // what the signed webhook + queue do on the server: paid, then handed to the supplier
      o.status = outcome === 'success' ? 'sent_to_supplier' : 'payment_failed';
      write('hd.mock.orders', all);
      return outcome === 'success' ? `/order/${o.id}/` : '/checkout/?failed=1';
    },
  },
};
