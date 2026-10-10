import type { Cart, CheckoutRequest, CheckoutResponse, OrderView, Pack } from '@hd/shared';

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
  setItem(cartId: string, variant_id: string, pack: Pack, qty: number): Promise<Cart>;
  checkout(req: CheckoutRequest): Promise<CheckoutResponse>;
  getOrder(id: string, token: string): Promise<OrderView>;
  /** In-browser hosted-page simulator (artifact only). */
  mockPay?: {
    info(session: string): Promise<{ order_id: string; total_agorot: number }>;
    complete(session: string, outcome: 'success' | 'fail'): Promise<string>;
  };
}
