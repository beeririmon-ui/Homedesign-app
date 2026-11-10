import type { Cart, CheckoutRequest, CheckoutResponse, OrderView, Pack, WaitlistRequest } from '@hd/shared';

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    public messageHe?: string,
  ) {
    super(code);
  }
}

export interface StoreApi {
  readonly kind: 'http' | 'mock';
  createCart(): Promise<Cart>;
  getCart(id: string): Promise<Cart>;
  /** `house`: the room engine's house the line is added in (S12, ת21: "החדר שלך" draws that house) */
  setItem(cartId: string, variant_id: string, pack: Pack, qty: number, house?: string): Promise<Cart>;
  checkout(req: CheckoutRequest): Promise<CheckoutResponse>;
  getOrder(id: string, token: string): Promise<OrderView>;
  /** "עדכנו אותי כשחוזר" (PRE1): one email for a product or a slot on hold */
  waitlist(req: WaitlistRequest): Promise<void>;
  /** In-browser hosted-page simulator (artifact only). */
  mockPay?: {
    info(session: string): Promise<{ order_id: string; total_agorot: number }>;
    complete(session: string, outcome: 'success' | 'fail'): Promise<string>;
  };
}
