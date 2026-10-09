/** Request/response contracts shared by the Worker API, the web client and the in-browser mock. */
import { z } from 'zod';

export const CartItemInputSchema = z.object({
  variant_id: z.string().min(1).max(160),
  qty: z.number().int().min(0).max(20),
});

export const CartLineSchema = z.object({
  variant_id: z.string(),
  product_id: z.string(),
  name_he: z.string(),
  qty: z.number().int(),
  unit_price_agorot: z.number().int(),
  line_total_agorot: z.number().int(),
  price_provisional: z.boolean(),
});
export type CartLine = z.infer<typeof CartLineSchema>;

export const CartSchema = z.object({
  id: z.string(),
  lines: z.array(CartLineSchema),
  subtotal_agorot: z.number().int(),
  count: z.number().int(),
});
export type Cart = z.infer<typeof CartSchema>;

/** Israeli mobile or landline, digits with optional dashes/spaces, or +972. */
export const IL_PHONE = /^(?:\+972[-\s]?|0)(?:[23489]|5\d|7\d)[-\s]?\d{3}[-\s]?\d{4}$/;

export const CustomerSchema = z.object({
  full_name: z.string().trim().min(2).max(80),
  email: z.email().max(120),
  phone: z.string().trim().regex(IL_PHONE),
});

export const AddressSchema = z.object({
  city: z.string().trim().min(2).max(60),
  street: z.string().trim().min(2).max(80),
  house: z.string().trim().min(1).max(10),
  apartment: z.string().trim().max(10).optional().default(''),
  zip: z
    .string()
    .trim()
    .regex(/^(\d{7})?$/)
    .optional()
    .default(''),
  notes: z.string().trim().max(200).optional().default(''),
});

export const CheckoutRequestSchema = z.object({
  cart_id: z.string().min(8).max(80),
  customer: CustomerSchema,
  address: AddressSchema,
  shipping_method: z.enum(['economy', 'express']),
  consents: z.object({
    terms: z.literal(true),
    marketing: z.boolean().default(false),
  }),
});
export type CheckoutRequest = z.infer<typeof CheckoutRequestSchema>;

export const CheckoutResponseSchema = z.object({
  order_id: z.string(),
  order_token: z.string(),
  redirect_url: z.string(),
});
export type CheckoutResponse = z.infer<typeof CheckoutResponseSchema>;

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

export const OrderViewSchema = z.object({
  id: z.string(),
  status: z.enum(ORDER_STATUSES),
  status_he: z.string(),
  created_at: z.string(),
  total_agorot: z.number().int(),
  shipping_method: z.enum(['economy', 'express']),
  lines: z.array(z.object({ name_he: z.string(), qty: z.number().int(), line_total_agorot: z.number().int() })),
});
export type OrderView = z.infer<typeof OrderViewSchema>;

export const ApiErrorSchema = z.object({ error: z.string(), message_he: z.string().optional() });
