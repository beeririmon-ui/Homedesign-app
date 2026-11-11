/**
 * The customer's shipping fee of a method for a subtotal, from the bundled catalog. Mirrors shared/src/pricing.ts
 * customerShippingAgorot (the server recomputes it from D1). Its own module (S13): the cart and the checkout are chunks.
 */
import { catalog } from '../catalog';

export type Method = 'economy' | 'express';

export function shippingFor(method: Method, subtotal: number): number {
  const s = catalog.shipping.find((x) => x.id === method);
  if (!s) return 0;
  return s.free_over_agorot !== null && subtotal >= s.free_over_agorot ? 0 : s.price_agorot;
}
