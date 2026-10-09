/** zod-free constants, safe to import from browser code (keeps zod out of the web bundle). */

/** Israeli mobile or landline, digits with optional dashes/spaces, or +972. */
export const IL_PHONE = /^(?:\+972[-\s]?|0)(?:[23489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}$/;
export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export const ORDER_STATUSES = [
  'pending_payment',
  'paid',
  'payment_failed',
  'canceled',
  'sent_to_supplier',
  'supplier_error',
  'shipped',
  'delivered',
  'refunded',
] as const;
export type OrderStatus = (typeof ORDER_STATUSES)[number];

export const ORDER_STATUS_HE: Record<OrderStatus, string> = {
  pending_payment: 'ממתינה לתשלום',
  paid: 'שולמה',
  payment_failed: 'התשלום נכשל',
  canceled: 'בוטלה',
  sent_to_supplier: 'הועברה לספק',
  supplier_error: 'בטיפול',
  shipped: 'נשלחה',
  delivered: 'נמסרה',
  refunded: 'זוכתה',
};
