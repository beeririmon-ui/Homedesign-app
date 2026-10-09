-- D1 schema v1. Money is INTEGER minor units: *_agorot (ILS), *_usd_cents (USD).
-- Catalog tables are written only by the seed (repo = source of truth). Order tables are written only by the API.
PRAGMA foreign_keys = ON;

-- ---------- catalog (seeded from the repo) ----------
CREATE TABLE catalog_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE economics_settings (
  id                     TEXT PRIMARY KEY CHECK (id = 'current'),
  fx_usd_ils             REAL    NOT NULL CHECK (fx_usd_ils > 0),
  vat_rate               REAL    NOT NULL CHECK (vat_rate >= 0 AND vat_rate < 1),
  payment_fee_rate       REAL    NOT NULL CHECK (payment_fee_rate >= 0 AND payment_fee_rate < 1),
  payment_fee_fixed_agorot INTEGER NOT NULL DEFAULT 0,
  returns_reserve_rate   REAL    NOT NULL CHECK (returns_reserve_rate >= 0 AND returns_reserve_rate < 1),
  cac_agorot             INTEGER NOT NULL DEFAULT 0,
  target_margin_rate     REAL    NOT NULL CHECK (target_margin_rate >= 0 AND target_margin_rate < 1),
  default_shipping_usd_cents INTEGER NOT NULL DEFAULT 0,
  defaults_used          TEXT    NOT NULL DEFAULT '[]',   -- JSON list of settings that fell back to provisional defaults
  imported_at            TEXT    NOT NULL,
  source                 TEXT
);

CREATE TABLE rooms (
  id            TEXT PRIMARY KEY,
  house_room_id TEXT NOT NULL,
  name_he       TEXT NOT NULL,
  style         TEXT NOT NULL,
  frame         TEXT NOT NULL,
  slots_version TEXT NOT NULL,
  built         INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE slots (
  room_id     TEXT NOT NULL REFERENCES rooms(id),
  id          TEXT NOT NULL,
  name_he     TEXT NOT NULL,
  category    TEXT,
  placement   TEXT NOT NULL,
  z           REAL NOT NULL,
  set_of      INTEGER,
  has_light   INTEGER NOT NULL DEFAULT 0,
  has_shadow  INTEGER NOT NULL DEFAULT 1,
  hotspot     TEXT,           -- JSON {u,v,provisional,visible}
  zoom_frame  TEXT,           -- JSON [u0,u1,v0,v1]
  PRIMARY KEY (room_id, id)
);

CREATE TABLE products (
  id                     TEXT PRIMARY KEY,           -- product card id
  room_id                TEXT NOT NULL,
  slot_id                TEXT NOT NULL,
  name_he                TEXT NOT NULL,
  name_provisional       INTEGER NOT NULL DEFAULT 1,
  name_supplier          TEXT NOT NULL,
  category               TEXT,
  description_he         TEXT NOT NULL DEFAULT '',
  status                 TEXT NOT NULL CHECK (status IN ('candidate', 'selected', 'rejected')),
  source_path            TEXT NOT NULL,              -- data/products/... in the repo
  supplier_name          TEXT NOT NULL,
  supplier_url           TEXT NOT NULL,
  supplier_sku           TEXT,
  cost_usd_cents         INTEGER NOT NULL CHECK (cost_usd_cents >= 0),
  shipping_usd_cents     INTEGER NOT NULL CHECK (shipping_usd_cents >= 0),
  shipping_from_default  INTEGER NOT NULL DEFAULT 0, -- 1 = no shipping_cost_usd yet, settings default used
  fx_usd_ils_at_import   REAL    NOT NULL,
  retail_agorot          INTEGER CHECK (retail_agorot IS NULL OR retail_agorot > 0),  -- consumer price incl. VAT
  compare_at_agorot      INTEGER,
  price_provisional      INTEGER NOT NULL DEFAULT 0,
  visible                INTEGER NOT NULL DEFAULT 0, -- shown on the site: has a retail price and sits in a slot option
  data_json              TEXT NOT NULL DEFAULT '{}', -- materials, dimensions, colours, notes (public fields)
  catalog_version        TEXT NOT NULL,
  updated_at             TEXT NOT NULL
);
CREATE INDEX products_slot ON products (room_id, slot_id);

CREATE TABLE product_variants (
  id          TEXT PRIMARY KEY,                       -- '<product id>:<variant>'
  product_id  TEXT NOT NULL REFERENCES products(id),
  label_he    TEXT NOT NULL,
  supplier_sku TEXT,
  active      INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX product_variants_product ON product_variants (product_id);

CREATE TABLE slot_options (
  room_id     TEXT NOT NULL,
  slot_id     TEXT NOT NULL,
  style       TEXT NOT NULL,
  position    INTEGER NOT NULL,
  product_id  TEXT REFERENCES products(id),
  placeholder INTEGER NOT NULL DEFAULT 0,
  is_default  INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (room_id, slot_id, style, position)
);

-- Unit economics per visible product, with the current settings. Mirrors shared/src/pricing.ts (tests compare both).
CREATE VIEW v_product_economics AS
SELECT
  p.id, p.slot_id, p.name_he, p.status, p.visible, p.price_provisional, p.shipping_from_default,
  p.retail_agorot,
  p.cost_usd_cents, p.shipping_usd_cents, p.fx_usd_ils_at_import,
  CAST(ROUND(p.retail_agorot / (1 + s.vat_rate)) AS INTEGER) AS net_agorot,
  CAST(ROUND((p.cost_usd_cents + p.shipping_usd_cents) * p.fx_usd_ils_at_import) AS INTEGER) AS cogs_agorot,
  CAST(ROUND(p.retail_agorot * s.payment_fee_rate + s.payment_fee_fixed_agorot) AS INTEGER) AS payment_fee_agorot,
  CAST(ROUND(ROUND(p.retail_agorot / (1 + s.vat_rate)) * s.returns_reserve_rate) AS INTEGER) AS returns_reserve_agorot,
  CAST(ROUND(p.retail_agorot / (1 + s.vat_rate)) AS INTEGER)
    - CAST(ROUND((p.cost_usd_cents + p.shipping_usd_cents) * p.fx_usd_ils_at_import) AS INTEGER)
    - CAST(ROUND(p.retail_agorot * s.payment_fee_rate + s.payment_fee_fixed_agorot) AS INTEGER)
    - CAST(ROUND(ROUND(p.retail_agorot / (1 + s.vat_rate)) * s.returns_reserve_rate) AS INTEGER) AS contribution_agorot,
  s.cac_agorot,
  s.target_margin_rate
FROM products p
JOIN economics_settings s ON s.id = 'current'
WHERE p.retail_agorot IS NOT NULL;

-- ---------- commerce (written by the API) ----------
CREATE TABLE customers (
  id                 TEXT PRIMARY KEY,
  email              TEXT NOT NULL,
  phone              TEXT NOT NULL,
  full_name          TEXT NOT NULL,
  marketing_consent  INTEGER NOT NULL DEFAULT 0,
  marketing_consent_at TEXT,
  created_at         TEXT NOT NULL
);
CREATE INDEX customers_email ON customers (email);

CREATE TABLE carts (
  id          TEXT PRIMARY KEY,
  status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'converted', 'expired')),
  created_at  TEXT NOT NULL,
  updated_at  TEXT NOT NULL,
  expires_at  TEXT NOT NULL
);

CREATE TABLE cart_items (
  cart_id     TEXT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  variant_id  TEXT NOT NULL REFERENCES product_variants(id),
  qty         INTEGER NOT NULL CHECK (qty > 0 AND qty <= 20),
  added_at    TEXT NOT NULL,
  PRIMARY KEY (cart_id, variant_id)
);

CREATE TABLE orders (
  id                 TEXT PRIMARY KEY,                 -- human-friendly, e.g. HD-7KQ2M9
  token_hash         TEXT NOT NULL,                    -- sha256 of the order access token given to the buyer
  cart_id            TEXT REFERENCES carts(id),
  customer_id        TEXT NOT NULL REFERENCES customers(id),
  status             TEXT NOT NULL CHECK (status IN ('pending_payment','paid','payment_failed','canceled','sent_to_supplier','supplier_error','shipped','delivered','refunded')),
  currency           TEXT NOT NULL DEFAULT 'ILS',
  subtotal_agorot    INTEGER NOT NULL,
  shipping_method    TEXT NOT NULL CHECK (shipping_method IN ('economy', 'express')),
  shipping_agorot    INTEGER NOT NULL,
  total_agorot       INTEGER NOT NULL,
  vat_agorot         INTEGER NOT NULL,
  vat_rate           REAL NOT NULL,
  fx_usd_ils_at_order REAL NOT NULL,
  address_json       TEXT NOT NULL,
  terms_accepted_at  TEXT NOT NULL,
  payment_provider   TEXT NOT NULL,
  payment_session_id TEXT,
  paid_at            TEXT,
  invoice_provider   TEXT,
  invoice_number     TEXT,
  invoice_url        TEXT,
  created_at         TEXT NOT NULL,
  updated_at         TEXT NOT NULL
);
CREATE INDEX orders_status ON orders (status, created_at);
CREATE UNIQUE INDEX orders_payment_session ON orders (payment_session_id);

CREATE TABLE order_items (
  order_id              TEXT NOT NULL REFERENCES orders(id),
  line                  INTEGER NOT NULL,
  product_id            TEXT NOT NULL,
  variant_id            TEXT NOT NULL,
  name_he               TEXT NOT NULL,                 -- snapshot
  qty                   INTEGER NOT NULL CHECK (qty > 0),
  unit_price_agorot     INTEGER NOT NULL,              -- snapshot, incl. VAT
  unit_cost_usd_cents   INTEGER NOT NULL,              -- snapshot for real margin per order
  unit_shipping_usd_cents INTEGER NOT NULL,
  supplier_sku          TEXT,
  PRIMARY KEY (order_id, line)
);

CREATE TABLE payment_events (
  id                 TEXT PRIMARY KEY,
  provider           TEXT NOT NULL,
  provider_event_id  TEXT NOT NULL,
  order_id           TEXT,
  type               TEXT NOT NULL,
  amount_agorot      INTEGER,
  signature_ok       INTEGER NOT NULL,
  body_sha256        TEXT NOT NULL,
  received_at        TEXT NOT NULL,
  processed_at       TEXT,
  outcome            TEXT,
  UNIQUE (provider, provider_event_id)
);

CREATE TABLE supplier_orders (
  id                 TEXT PRIMARY KEY,
  order_id           TEXT NOT NULL REFERENCES orders(id),
  supplier           TEXT NOT NULL,
  status             TEXT NOT NULL CHECK (status IN ('queued','submitted','accepted','failed','shipped','canceled')),
  supplier_order_id  TEXT,
  tracking_number    TEXT,
  tracking_url       TEXT,
  attempts           INTEGER NOT NULL DEFAULT 0,
  last_error         TEXT,
  request_json       TEXT,
  response_json      TEXT,
  created_at         TEXT NOT NULL,
  updated_at         TEXT NOT NULL,
  UNIQUE (order_id, supplier)
);

CREATE TABLE audit_log (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  at         TEXT NOT NULL,
  actor      TEXT NOT NULL,      -- Access email, 'system', 'webhook:<provider>'
  action     TEXT NOT NULL,
  subject    TEXT,
  detail     TEXT
);
