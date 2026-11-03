-- Commerce truth (SITE1, 2026-11-03; docs/studio-rules.md ה.13, ה.15):
--   1. freight of a sale is the studio's combined parcel (unit + (q − 1) × max(0, unit − $3.72)), or the supplier's quote
--      for exactly the sale; the catalog now stores the sale's freight in shipping_usd_cents, so the view no longer
--      multiplies one piece's freight by sell_qty;
--   2. the shipping line can come from any of the studio's sources (no default figure any more), so shipping_source is
--      widened and shipping_from_default (always 0 now) leaves;
--   3. a product can be on the site without being sold (PRE1: "המלאי אינו זמין כעת"): availability + reason;
--   4. the no-loss facts of every price the site shows (the floor's evidence, gate G8.2);
--   5. the waiting list ("עדכנו אותי כשחוזר").
-- SQLite cannot change a CHECK in place: products is rebuilt. Commerce tables are untouched.
DROP VIEW v_product_economics;

CREATE TABLE products_new (
  id                     TEXT PRIMARY KEY,
  room_id                TEXT NOT NULL,
  slot_id                TEXT NOT NULL,
  name_he                TEXT NOT NULL,
  name_provisional       INTEGER NOT NULL DEFAULT 1,
  name_supplier          TEXT NOT NULL,
  category               TEXT,
  description_he         TEXT NOT NULL DEFAULT '',
  status                 TEXT NOT NULL CHECK (status IN ('candidate', 'selected', 'rejected')),
  source_path            TEXT NOT NULL,
  supplier_name          TEXT NOT NULL,
  supplier_url           TEXT NOT NULL,
  supplier_sku           TEXT,
  cost_usd_cents         INTEGER NOT NULL CHECK (cost_usd_cents >= 0),
  -- freight of the whole sale (sell_qty pieces) by the default line, USD cents
  shipping_usd_cents     INTEGER NOT NULL CHECK (shipping_usd_cents >= 0),
  -- freight of one piece by the same line (the single-piece sale, P1)
  unit_shipping_usd_cents INTEGER NOT NULL DEFAULT 0 CHECK (unit_shipping_usd_cents >= 0),
  shipping_source        TEXT    NOT NULL CHECK (shipping_source IN ('manual', 'cj', 'zendrop', 'aliexpress', 'card', 'cache', 'leads')),
  shipping_line          TEXT    NOT NULL DEFAULT '',
  sell_qty               INTEGER NOT NULL DEFAULT 1 CHECK (sell_qty >= 1),
  fx_usd_ils_at_import   REAL    NOT NULL,
  retail_agorot          INTEGER CHECK (retail_agorot IS NULL OR retail_agorot > 0),
  compare_at_agorot      INTEGER,
  price_provisional      INTEGER NOT NULL DEFAULT 0,
  price_source           TEXT    NOT NULL DEFAULT 'studio' CHECK (price_source IN ('owner', 'studio', 'initial-card', 'initial-leads')),
  unit_retail_agorot     INTEGER CHECK (unit_retail_agorot IS NULL OR unit_retail_agorot > 0),
  unit_price_estimated   INTEGER NOT NULL DEFAULT 0,
  -- the no-loss facts (studio rules ה.13): landed cost of the sale and the lowest price that does not lose
  landed_agorot          INTEGER NOT NULL DEFAULT 0,
  no_loss_agorot         INTEGER NOT NULL DEFAULT 0,
  -- PRE1: shown but not sold; reason: nl2-above-market, nl2-express-only, slot-on-hold
  availability           TEXT    NOT NULL DEFAULT 'available' CHECK (availability IN ('available', 'unavailable')),
  availability_reason    TEXT,
  visible                INTEGER NOT NULL DEFAULT 0,
  data_json              TEXT NOT NULL DEFAULT '{}',
  catalog_version        TEXT NOT NULL,
  updated_at             TEXT NOT NULL
);
INSERT INTO products_new (id, room_id, slot_id, name_he, name_provisional, name_supplier, category, description_he, status, source_path,
  supplier_name, supplier_url, supplier_sku, cost_usd_cents, shipping_usd_cents, unit_shipping_usd_cents, shipping_source, sell_qty,
  fx_usd_ils_at_import, retail_agorot, compare_at_agorot, price_provisional, unit_retail_agorot, unit_price_estimated, visible, data_json,
  catalog_version, updated_at)
SELECT id, room_id, slot_id, name_he, name_provisional, name_supplier, category, description_he, status, source_path,
  supplier_name, supplier_url, supplier_sku, cost_usd_cents,
  -- the old column held one piece's freight: the sale's by the combined parcel
  CAST(ROUND(shipping_usd_cents + (sell_qty - 1) * MAX(0, shipping_usd_cents - 372)) AS INTEGER), shipping_usd_cents,
  CASE WHEN shipping_source = 'default' THEN 'cj' ELSE shipping_source END, sell_qty,
  fx_usd_ils_at_import, retail_agorot, compare_at_agorot, price_provisional, unit_retail_agorot, unit_price_estimated,
  -- a row priced by the old default figure is not for sale until the next seed
  CASE WHEN shipping_source = 'default' THEN 0 ELSE visible END, data_json, catalog_version, updated_at
FROM products;
DROP TABLE products;
ALTER TABLE products_new RENAME TO products;
CREATE INDEX products_slot ON products (room_id, slot_id);

-- the option's own no-loss facts (the floor's evidence); NULL for a product without options (= the product's)
ALTER TABLE product_variants ADD COLUMN unit_shipping_usd_cents INTEGER CHECK (unit_shipping_usd_cents IS NULL OR unit_shipping_usd_cents >= 0);
ALTER TABLE product_variants ADD COLUMN landed_agorot INTEGER;
ALTER TABLE product_variants ADD COLUMN no_loss_agorot INTEGER;
ALTER TABLE product_variants ADD COLUMN price_floored INTEGER NOT NULL DEFAULT 0;

-- Unit economics per priced product, with the current settings. Mirrors shared/src/pricing.ts (tests compare both):
-- shipping_usd_cents is already the sale's freight (combined parcel or the supplier's quote for the sale).
CREATE VIEW v_product_economics AS
WITH b AS (
  SELECT
    p.id, p.slot_id, p.name_he, p.status, p.visible, p.availability, p.availability_reason, p.price_provisional, p.price_source,
    p.shipping_source, p.shipping_line,
    p.retail_agorot, p.cost_usd_cents, p.shipping_usd_cents, p.sell_qty, p.fx_usd_ils_at_import, p.landed_agorot, p.no_loss_agorot,
    CAST(ROUND(p.retail_agorot / (1 + s.vat_rate)) AS INTEGER) AS net_agorot,
    CAST(ROUND((p.cost_usd_cents * p.sell_qty + p.shipping_usd_cents) * p.fx_usd_ils_at_import) AS INTEGER) AS cogs_agorot,
    CAST(ROUND(p.retail_agorot * s.payment_fee_rate + s.payment_fee_fixed_agorot) AS INTEGER) AS payment_fee_agorot,
    s.packaging_agorot,
    CAST(ROUND(s.cac_agorot / s.items_per_order) AS INTEGER) AS cac_per_item_agorot,
    s.returns_reserve_rate, s.target_margin_rate
  FROM products p
  JOIN economics_settings s ON s.id = 'current'
  WHERE p.retail_agorot IS NOT NULL
), c AS (
  SELECT b.*,
    CAST(ROUND(b.net_agorot * b.returns_reserve_rate) AS INTEGER) AS returns_reserve_agorot
  FROM b
), d AS (
  SELECT c.*, c.net_agorot - c.cogs_agorot - c.payment_fee_agorot - c.returns_reserve_agorot - c.packaging_agorot AS contribution_agorot
  FROM c
)
SELECT d.*,
  CASE WHEN d.net_agorot > 0 THEN ROUND(CAST(d.contribution_agorot AS REAL) / d.net_agorot, 4) END AS margin_rate,
  d.contribution_agorot - d.cac_per_item_agorot AS contribution_after_cac_agorot,
  CASE WHEN d.net_agorot > 0 AND CAST(d.contribution_agorot AS REAL) / d.net_agorot >= d.target_margin_rate THEN 1 ELSE 0 END AS meets_target
FROM d;

-- "עדכנו אותי כשחוזר" (PRE1): one email per product or slot on hold; nothing else is collected (docs/site-art-direction §6.8)
CREATE TABLE waitlist (
  id          TEXT PRIMARY KEY,
  email       TEXT NOT NULL,
  product_id  TEXT,
  room_id     TEXT,
  slot_id     TEXT,
  created_at  TEXT NOT NULL,
  notified_at TEXT
);
CREATE INDEX waitlist_product ON waitlist (product_id, created_at);
CREATE INDEX waitlist_slot ON waitlist (room_id, slot_id, created_at);
