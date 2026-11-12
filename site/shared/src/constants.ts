/** zod-free constants, safe to import from browser code (keeps zod out of the web bundle). */

/** Israeli mobile or landline, digits with optional dashes/spaces, or +972. */
export const IL_PHONE = /^(?:\+972[-\s]?|0)(?:[23489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}$/;
export const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Order numbers are digits only, no prefix (ART6, 2026-11-03): ten digits, the first never 0. */
export const ORDER_ID = /^[1-9]\d{9}$/;

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

/**
 * The customer's words (ART6, 2026-11-03; site art direction §9.5): "התקבלה · בהכנה · נשלחה · נמסרה". The supplier is
 * never named: an order that went to the supplier is "בהכנה".
 * S16 (QA S11–S12 ה1, S13–S14 ה7): an order stuck on a supplier error is said honestly, in neutral words.
 * S17 (master-designer, docs/proposals/wm-phase2-r5-eye-2026-11-11.md §7): no fifth status. The order is still being
 * prepared; what changed is the pace, not the step. So supplier_error is "בהכנה" on the progress line, with one line
 * under it (`ORDER_DELAY_HE`), and "עדיין בהכנה" where there is no room for the line (`ORDER_DELAY_SHORT_HE`).
 */
export const ORDER_STATUS_HE: Record<OrderStatus, string> = {
  pending_payment: 'ממתינה לתשלום',
  paid: 'התקבלה',
  payment_failed: 'התשלום נכשל',
  canceled: 'בוטלה',
  sent_to_supplier: 'בהכנה',
  supplier_error: 'בהכנה',
  shipped: 'נשלחה',
  delivered: 'נמסרה',
  refunded: 'זוכתה',
};

/**
 * S17 (§7): the line under the progress line of an order in supplier_error: no supplier, no fault, nothing asked of the
 * customer. The designer's third sentence ("אם מועד המסירה ישתנה, נעדכן אותך במייל.") is a promise: it goes in only
 * when the shop really sends that email. Today it sends the customer none (lib/notify is the owner's new-order alert
 * only), so it is left out.
 */
export const ORDER_DELAY_HE = 'ההכנה נמשכת יותר מהרגיל. אנחנו כבר מטפלים בזה, ואין צורך לעשות דבר.';
/** S17 (§7): the short form, only where the line has no room (a row of a list of orders, an alert) */
export const ORDER_DELAY_SHORT_HE = 'עדיין בהכנה';

/** The four steps of a paid order, in order, and the step each status has reached (null: not on the line). */
export const ORDER_STEPS_HE = ['התקבלה', 'בהכנה', 'נשלחה', 'נמסרה'] as const;
export function orderStep(status: OrderStatus): number | null {
  switch (status) {
    case 'paid':
      return 0;
    case 'sent_to_supplier':
    case 'supplier_error':
      return 1;
    case 'shipped':
      return 2;
    case 'delivered':
      return 3;
    default:
      return null;
  }
}
