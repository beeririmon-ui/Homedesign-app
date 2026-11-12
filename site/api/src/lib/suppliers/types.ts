export type SupplierOrderInput = {
  order_id: string;
  lines: { supplier_sku: string | null; product_id: string; qty: number }[];
  ship_to: { full_name: string; phone: string; email: string; city: string; street: string; house: string; apartment: string; zip: string };
  shipping_method: 'economy' | 'express';
};

/**
 * S13 (3.3, 6.3): what the supplier says about an order it has. `accepted`: it is being prepared; `shipped`: it left,
 * with a tracking number (and the supplier's tracking link, which the customer sees only when it is generic:
 * lib/shipments.ts `customerTrackingUrl`); `delivered`; `canceled`: the supplier canceled it (a cancellation we asked
 * for, confirmed). `cancel: 'refused'`: the supplier will not cancel (it is already packed or shipped).
 */
export type SupplierUpdate = {
  status: 'accepted' | 'shipped' | 'delivered' | 'canceled';
  tracking_number?: string | null;
  tracking_url?: string | null;
  cancel?: 'refused';
  at?: string;
};

/** S13: the supplier's answer to a cancellation request. `requested`: it will answer later (a SupplierUpdate). */
export type SupplierCancelOutcome = { outcome: 'canceled' | 'requested' | 'refused'; raw?: unknown };

/**
 * S16, QA ת35: the supplier refused the order, or the adapter refused before calling it (no key, no documentation, a line
 * without a SKU): nothing was created at the supplier. Any other failure (a timeout, a network or server error) may have
 * created the order, and the shipment then counts as sent until the supplier (or a person) says otherwise.
 */
export class SupplierRefused extends Error {
  constructor(
    public readonly code: string,
    message: string = code,
  ) {
    super(message);
    this.name = 'SupplierRefused';
  }
}

export interface SupplierClient {
  readonly id: string;
  /**
   * S17, QA ת48: true only when the adapter's documentation says the supplier refuses a second order with our order
   * number (or returns the first one). Then a send that may have reached it is sent again; otherwise it is asked first
   * (`findOrder`), or, when it cannot be asked, left to a person.
   */
  readonly dedupesByOrderId?: boolean;
  /** S14 (ת31): `signal` fires at the call's deadline; a client that calls out passes it to fetch */
  submitOrder(input: SupplierOrderInput, opts?: { signal?: AbortSignal }): Promise<{ supplier_order_id: string; raw: unknown }>;
  /** S13: asks the supplier to cancel an order it has; absent when the supplier has no such call (a person does it) */
  cancelOrder?(supplierOrderId: string): Promise<SupplierCancelOutcome>;
  /**
   * S16 (ת35): the supplier's order for our order number, null when it holds none; absent when the supplier cannot be
   * asked (a person checks at the supplier instead). `signal` fires at the call's deadline.
   */
  findOrder?(ourOrderId: string, opts?: { signal?: AbortSignal }): Promise<{ supplier_order_id: string } | null>;
  /** S13: the supplier's current state of an order (polled by the cron); null when there is no news */
  tracking?(supplierOrderId: string): Promise<SupplierUpdate | null>;
}
