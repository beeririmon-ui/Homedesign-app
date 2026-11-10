/** D1 queries shared by the routes. Prepared statements only; never string-built SQL with input. */
import type { Cart, CartLine, Pack } from '@hd/shared';
import { HttpError, nowIso } from './http';

const CART_TTL_DAYS = 30;
export const CART_ID = /^[A-Za-z0-9_-]{24,64}$/;

type LineRow = {
  variant_id: string;
  product_id: string;
  name_he: string;
  option_he: string | null;
  pack: Pack;
  qty: number;
  retail_agorot: number;
  unit_retail_agorot: number | null;
  unit_price_estimated: number;
  sell_qty: number;
  price_provisional: number;
};

export async function createCart(db: D1Database, id: string): Promise<void> {
  const now = new Date();
  const expires = new Date(now.getTime() + CART_TTL_DAYS * 86_400_000);
  await db
    .prepare('INSERT INTO carts (id, status, created_at, updated_at, expires_at) VALUES (?, ?, ?, ?, ?)')
    .bind(id, 'open', now.toISOString(), now.toISOString(), expires.toISOString())
    .run();
}

export async function openCartOr404(db: D1Database, id: string): Promise<void> {
  if (!CART_ID.test(id)) throw new HttpError(404, 'cart_not_found');
  const row = await db.prepare('SELECT status, expires_at FROM carts WHERE id = ?').bind(id).first<{ status: string; expires_at: string }>();
  if (!row) throw new HttpError(404, 'cart_not_found');
  if (row.status !== 'open' || row.expires_at < nowIso()) throw new HttpError(409, 'cart_closed');
}

/**
 * A variant's prices: its own when it is a supplier option with a price (migration 0002), else the product's.
 * Used by every query that prices a cart line, so the cart, the checkout and the order agree.
 */
export const VARIANT_PRICE_SQL = `COALESCE(v.retail_agorot, p.retail_agorot) AS retail_agorot,
       CASE WHEN v.retail_agorot IS NULL THEN p.unit_retail_agorot ELSE v.unit_retail_agorot END AS unit_retail_agorot,
       COALESCE(v.unit_price_estimated, p.unit_price_estimated) AS unit_price_estimated,
       COALESCE(v.price_provisional, p.price_provisional) AS price_provisional`;

/**
 * Prices always come from D1. A line is sold when its variant is active and not a part of a set (ת9), and its product
 * is visible, priced and available (PRE1); a single piece needs a unit price. ת8: the line's name is the variant's base
 * name (without a colour) and its option is the Hebrew labels, so nothing in the line contradicts what was bought.
 * ת11: with `prune`, a line no longer sold is removed from the cart and counted on it (the cart says so, never charges
 * it); `pruned` is how many this read removed.
 */
export async function readCart(db: D1Database, id: string, opts: { prune?: boolean } = {}): Promise<Cart & { pruned: number }> {
  const { results } = await db
    .prepare(
      `SELECT ci.variant_id, ci.pack, ci.qty, p.id AS product_id, COALESCE(v.line_name_he, p.name_he) AS name_he,
              v.option_label_he AS option_he, p.sell_qty,
              ${VARIANT_PRICE_SQL},
              CASE WHEN v.id IS NOT NULL AND v.active = 1 AND v.set_part = 0 AND v.set_incomplete IS NULL AND p.visible = 1
                        AND p.retail_agorot IS NOT NULL AND p.availability = 'available' THEN 1 ELSE 0 END AS sold
       FROM cart_items ci
       LEFT JOIN product_variants v ON v.id = ci.variant_id
       LEFT JOIN products p ON p.id = v.product_id
       WHERE ci.cart_id = ?
       ORDER BY ci.added_at`,
    )
    .bind(id)
    .all<LineRow & { sold: number }>();
  const lines: CartLine[] = [];
  const dead: { variant_id: string; pack: Pack }[] = [];
  for (const r of results) {
    const unit = r.pack === 'unit';
    const price = unit ? r.unit_retail_agorot : r.retail_agorot;
    // a single-piece line whose product no longer has a unit option is dropped, like an unavailable product
    if (!r.sold || price === null) {
      dead.push({ variant_id: r.variant_id, pack: r.pack });
      continue;
    }
    lines.push({
      variant_id: r.variant_id,
      product_id: r.product_id,
      name_he: r.name_he,
      option_he: r.option_he,
      pack: r.pack,
      pack_qty: unit ? 1 : r.sell_qty,
      qty: r.qty,
      unit_price_agorot: price,
      line_total_agorot: price * r.qty,
      price_provisional: r.price_provisional === 1 || (unit && r.unit_price_estimated === 1),
    });
  }
  if (opts.prune && dead.length)
    await db.batch([
      ...dead.map((d) => db.prepare('DELETE FROM cart_items WHERE cart_id = ? AND variant_id = ? AND pack = ?').bind(id, d.variant_id, d.pack)),
      db.prepare('UPDATE carts SET removed_lines = removed_lines + ?, updated_at = ? WHERE id = ?').bind(dead.length, nowIso(), id),
    ]);
  const removed = (await db.prepare('SELECT removed_lines FROM carts WHERE id = ?').bind(id).first<{ removed_lines: number }>())?.removed_lines ?? 0;
  return {
    id,
    lines,
    subtotal_agorot: lines.reduce((s, l) => s + l.line_total_agorot, 0),
    count: lines.reduce((s, l) => s + l.qty, 0),
    ...(removed ? { removed } : {}),
    pruned: opts.prune ? dead.length : 0,
  };
}

export async function setCartItem(db: D1Database, cartId: string, variantId: string, pack: Pack, qty: number, house: string | null = null): Promise<void> {
  const now = nowIso();
  if (qty === 0) {
    await db.prepare('DELETE FROM cart_items WHERE cart_id = ? AND variant_id = ? AND pack = ?').bind(cartId, variantId, pack).run();
  } else {
    const row = await db
      .prepare(
        `SELECT ${VARIANT_PRICE_SQL}, v.set_part, v.set_incomplete FROM product_variants v JOIN products p ON p.id = v.product_id
         WHERE v.id = ? AND v.active = 1 AND p.visible = 1 AND p.retail_agorot IS NOT NULL AND p.availability = 'available'`,
      )
      .bind(variantId)
      .first<{ unit_retail_agorot: number | null; set_part: number; set_incomplete: string | null }>();
    if (!row) throw new HttpError(404, 'variant_not_found', 'המוצר לא זמין.');
    // ת9: a part of a set of distinct SKUs (one print of a triptych) is not sold on its own
    if (row.set_part === 1) throw new HttpError(422, 'set_part', 'הפריט הזה נמכר רק כחלק מהסט.');
    // S12 (S11 question 2): a set whose card does not name the SKUs of its parts is not sold: never N × one of them
    if (row.set_incomplete !== null) throw new HttpError(422, 'set_unavailable', 'הסט הזה עוד לא זמין להזמנה.');
    // only a set (sell_qty > 1) has a single-piece option, and a set of distinct SKUs has none (ת9, SET1)
    if (pack === 'unit' && row.unit_retail_agorot === null) throw new HttpError(422, 'pack_unavailable', 'המוצר הזה נמכר רק כסט.');
    await db
      .prepare(
        `INSERT INTO cart_items (cart_id, variant_id, pack, qty, added_at, house) VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(cart_id, variant_id, pack) DO UPDATE SET qty = excluded.qty, house = COALESCE(excluded.house, cart_items.house)`,
      )
      .bind(cartId, variantId, pack, qty, now, house)
      .run();
  }
  await db.prepare('UPDATE carts SET updated_at = ? WHERE id = ?').bind(now, cartId).run();
}

export type ShippingOptionRow = { id: 'economy' | 'express'; price_agorot: number };

export async function shippingOptions(db: D1Database): Promise<ShippingOptionRow[]> {
  const row = await db.prepare("SELECT value FROM catalog_meta WHERE key = 'shipping_options'").first<{ value: string }>();
  return row ? (JSON.parse(row.value) as ShippingOptionRow[]) : [];
}

export async function economics(db: D1Database) {
  const s = await db.prepare("SELECT * FROM economics_settings WHERE id = 'current'").first<{
    fx_usd_ils: number;
    vat_rate: number;
    payment_fee_rate: number;
    payment_fee_fixed_agorot: number;
    returns_reserve_rate: number;
    cac_agorot: number;
    target_margin_rate: number;
    default_shipping_usd_cents: number;
    packaging_agorot: number;
    items_per_order: number;
    shipping_fee_economy_agorot: number;
    shipping_fee_express_agorot: number;
    free_shipping_threshold_agorot: number | null;
    defaults_used: string;
    imported_at: string;
  }>();
  if (!s) throw new HttpError(503, 'catalog_not_seeded');
  return s;
}
