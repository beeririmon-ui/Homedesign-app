/** Request/response contracts shared by the Worker API, the web client and the in-browser mock. */
import { z } from 'zod';
import { IL_PHONE, ORDER_STATUSES } from './constants';
import { PACKS } from './packs';

export { IL_PHONE, ORDER_ID, ORDER_STATUSES, ORDER_STATUS_HE, ORDER_STEPS_HE, orderStep, type OrderStatus } from './constants';

/** a house of the room engine: a style id (S12, ת21) */
export const HOUSE_ID = z.string().regex(/^[a-z][a-z-]{0,39}$/);

export const CartItemInputSchema = z.object({
  variant_id: z.string().min(1).max(160),
  /** set or single piece (P1); a product without a unit option accepts only 'set' */
  pack: z.enum(PACKS).default('set'),
  qty: z.number().int().min(0).max(20),
  /** S12, ת21: the house the line was added in (the room engine's style), for "החדר שלך"; absent off the engine */
  house: HOUSE_ID.optional(),
});

export const CartLineSchema = z.object({
  variant_id: z.string(),
  product_id: z.string(),
  name_he: z.string(),
  /** the supplier option chosen on the product page ("בז', 45×45 ס"מ"); null for a product without options */
  option_he: z.string().nullable(),
  pack: z.enum(PACKS),
  /** pieces in one of this line's sale units: the set size for 'set' (1 when not sold as a set), 1 for 'unit' */
  pack_qty: z.number().int().min(1),
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
  /**
   * S11, QA ת11: lines whose product stopped being sold after they were added (PRE1, a variant no longer offered): the
   * server removed them, never charged them, and the cart says so ("פריט אחד כבר לא זמין והוסר"). Absent: none.
   */
  removed: z.number().int().min(0).optional(),
});
export type Cart = z.infer<typeof CartSchema>;

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

export const OrderViewSchema = z.object({
  id: z.string(),
  status: z.enum(ORDER_STATUSES),
  status_he: z.string(),
  created_at: z.string(),
  total_agorot: z.number().int(),
  shipping_method: z.enum(['economy', 'express']),
  lines: z.array(
    z.object({
      name_he: z.string(),
      /** S8: the public ids (the order page draws "החדר שלך" from them) */
      product_id: z.string().optional(),
      variant_id: z.string().optional(),
      /** S12, ת21: the house the line was bought in; null when it was bought off the room engine (a product page, a story) */
      house: z.string().nullable().optional(),
      pack: z.enum(PACKS),
      pack_qty: z.number().int().min(1),
      qty: z.number().int(),
      line_total_agorot: z.number().int(),
    }),
  ),
});
export type OrderView = z.infer<typeof OrderViewSchema>;

export const ApiErrorSchema = z.object({ error: z.string(), message_he: z.string().optional() });

/** "עדכנו אותי כשחוזר" (PRE1): one email, for one product or one slot on hold. Nothing else is collected. */
export const WaitlistRequestSchema = z
  .object({
    email: z.email().max(120),
    product_id: z.string().min(1).max(160).optional(),
    room: z.string().min(1).max(40).optional(),
    slot: z.string().min(1).max(60).optional(),
  })
  .refine((v) => v.product_id || (v.room && v.slot), { message: 'a product or a room and a slot' });
export type WaitlistRequest = z.infer<typeof WaitlistRequestSchema>;
export const WaitlistResponseSchema = z.object({ ok: z.literal(true) });
