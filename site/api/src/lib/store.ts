/** D1 queries shared by the routes. Prepared statements only; never string-built SQL with input. */
import type { Cart, CartLine, Pack } from '@hd/shared';
import { HttpError, nowIso } from './http';

const CART_TTL_DAYS = 30;
export const CART_ID = /^[A-Za-z0-9_-]{24,64}$/;

type LineRow = {
  variant_id: string;
  product_id: string;
  name_he: string;
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

/** Prices always come from D1. Lines whose product is no longer visible are dropped from the view. */
export async function readCart(db: D1Database, id: string): Promise<Cart> {
  const { results } = await db
    .prepare(
      `SELECT ci.variant_id, p.id AS product_id, p.name_he, ci.pack, ci.qty, p.retail_agorot, p.unit_retail_agorot,
              p.unit_price_estimated, p.sell_qty, p.price_provisional
       FROM cart_items ci
       JOIN product_variants v ON v.id = ci.variant_id AND v.active = 1
       JOIN products p ON p.id = v.product_id AND p.visible = 1 AND p.retail_agorot IS NOT NULL
       WHERE ci.cart_id = ?
       ORDER BY ci.added_at`,
    )
    .bind(id)
    .all<LineRow>();
  // a single-piece line whose product no longer has a unit option is dropped, like an unavailable product
  const lines: CartLine[] = results.flatMap((r) => {
    const unit = r.pack === 'unit';
    const price = unit ? r.unit_retail_agorot : r.retail_agorot;
    if (price === null) return [];
    return [
      {
        variant_id: r.variant_id,
        product_id: r.product_id,
        name_he: r.name_he,
        pack: r.pack,
        pack_qty: unit ? 1 : r.sell_qty,
        qty: r.qty,
        unit_price_agorot: price,
        line_total_agorot: price * r.qty,
        price_provisional: r.price_provisional === 1 || (unit && r.unit_price_estimated === 1),
      },
    ];
  });
  return {
    id,
    lines,
    subtotal_agorot: lines.reduce((s, l) => s + l.line_total_agorot, 0),
    count: lines.reduce((s, l) => s + l.qty, 0),
  };
}

export async function setCartItem(db: D1Database, cartId: string, variantId: string, pack: Pack, qty: number): Promise<void> {
  const now = nowIso();
  if (qty === 0) {
    await db.prepare('DELETE FROM cart_items WHERE cart_id = ? AND variant_id = ? AND pack = ?').bind(cartId, variantId, pack).run();
  } else {
    const row = await db
      .prepare(
        `SELECT p.unit_retail_agorot FROM product_variants v JOIN products p ON p.id = v.product_id
         WHERE v.id = ? AND v.active = 1 AND p.visible = 1 AND p.retail_agorot IS NOT NULL`,
      )
      .bind(variantId)
      .first<{ unit_retail_agorot: number | null }>();
    if (!row) throw new HttpError(404, 'variant_not_found', 'המוצר לא זמין.');
    // only a set (sell_qty > 1) has a single-piece option
    if (pack === 'unit' && row.unit_retail_agorot === null) throw new HttpError(422, 'pack_unavailable', 'המוצר הזה נמכר רק כסט.');
    await db
      .prepare(
        `INSERT INTO cart_items (cart_id, variant_id, pack, qty, added_at) VALUES (?, ?, ?, ?, ?)
         ON CONFLICT(cart_id, variant_id, pack) DO UPDATE SET qty = excluded.qty`,
      )
      .bind(cartId, variantId, pack, qty, now)
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
