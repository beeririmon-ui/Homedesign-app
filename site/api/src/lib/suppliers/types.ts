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

export interface SupplierClient {
  readonly id: string;
  submitOrder(input: SupplierOrderInput): Promise<{ supplier_order_id: string; raw: unknown }>;
  /** S13: asks the supplier to cancel an order it has; absent when the supplier has no such call (a person does it) */
  cancelOrder?(supplierOrderId: string): Promise<SupplierCancelOutcome>;
  /** S13: the supplier's current state of an order (polled by the cron); null when there is no news */
  tracking?(supplierOrderId: string): Promise<SupplierUpdate | null>;
}
