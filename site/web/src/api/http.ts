import type { Cart, CheckoutRequest, CheckoutResponse, OrderView, WaitlistRequest } from '@hd/shared';
import { ApiError, type StoreApi } from './types';

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, {
      ...init,
      headers: { accept: 'application/json', ...(init.body ? { 'content-type': 'application/json' } : {}), ...(init.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, 'network', 'אין חיבור לשרת. בדקו את החיבור ונסו שוב.');
  }
  const body = (await res.json().catch(() => ({}))) as { error?: string; message_he?: string };
  if (!res.ok) throw new ApiError(res.status, body.error ?? 'error', body.message_he);
  return body as T;
}

/**
 * S21, QA ת63 (3): the cart's writes go with `keepalive`, so a page that unloads while one is on its way (the back
 * button, a typed address, a closed tab) does not cut it off: the server still makes the cart and adds the line. A move
 * to the cart or the checkout also waits for it (state/cart.ts `leaveFor`), so the next page reads it.
 */
const KEEP: RequestInit = { keepalive: true };

export const httpApi: StoreApi = {
  kind: 'http',
  createCart: () => call<Cart>('/cart', { method: 'POST', ...KEEP }),
  getCart: (id) => call<Cart>(`/cart/${encodeURIComponent(id)}`),
  setItem: (cartId, variant_id, pack, qty, house) =>
    call<Cart>(`/cart/${encodeURIComponent(cartId)}/items`, { method: 'PUT', body: JSON.stringify({ variant_id, pack, qty, house }), ...KEEP }),
  checkout: (req: CheckoutRequest) => call<CheckoutResponse>('/checkout', { method: 'POST', body: JSON.stringify(req) }),
  getOrder: (id, token) => call<OrderView>(`/orders/${encodeURIComponent(id)}`, { headers: { 'x-order-token': token } }),
  waitlist: async (req: WaitlistRequest) => {
    await call<{ ok: true }>('/waitlist', { method: 'POST', body: JSON.stringify(req) });
  },
};
