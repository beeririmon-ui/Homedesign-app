/** Client-side checks that mirror shared/src/api.ts (CheckoutRequestSchema), without shipping zod to the browser. */
import type { CheckoutRequest } from '@hd/shared';
import { EMAIL, IL_PHONE } from '@hd/shared/constants';

export type FieldErrors = Partial<Record<'full_name' | 'email' | 'phone' | 'city' | 'street' | 'house' | 'zip' | 'terms', string>>;

export function validateCheckout(r: CheckoutRequest): FieldErrors {
  const e: FieldErrors = {};
  const t = (s: string | undefined) => (s ?? '').trim();
  if (t(r.customer.full_name).length < 2) e.full_name = 'נא למלא שם מלא.';
  if (!EMAIL.test(t(r.customer.email))) e.email = 'נא למלא כתובת אימייל תקינה, למשל name@example.com.';
  if (!IL_PHONE.test(t(r.customer.phone))) e.phone = 'נא למלא מספר טלפון ישראלי, למשל 050-1234567.';
  if (t(r.address.city).length < 2) e.city = 'נא למלא עיר.';
  if (t(r.address.street).length < 2) e.street = 'נא למלא רחוב.';
  if (t(r.address.house).length < 1) e.house = 'נא למלא מספר בית.';
  if (t(r.address.zip) && !/^\d{7}$/.test(t(r.address.zip))) e.zip = 'מיקוד הוא 7 ספרות (אפשר להשאיר ריק).';
  if (r.consents.terms !== true) e.terms = 'כדי להמשיך יש לאשר את התקנון ואת מדיניות הביטולים.';
  return e;
}
