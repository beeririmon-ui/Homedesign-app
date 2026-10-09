export type SupplierOrderInput = {
  order_id: string;
  lines: { supplier_sku: string | null; product_id: string; qty: number }[];
  ship_to: { full_name: string; phone: string; email: string; city: string; street: string; house: string; apartment: string; zip: string };
  shipping_method: 'economy' | 'express';
};

export interface SupplierClient {
  readonly id: string;
  submitOrder(input: SupplierOrderInput): Promise<{ supplier_order_id: string; raw: unknown }>;
}
