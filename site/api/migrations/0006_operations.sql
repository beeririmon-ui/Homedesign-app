-- S13, operations (briefs/site-s13-operations-2026-11-11.md; launch checklist 2.5, 3.3, 6.3):
--   1. supplier_shipments: the delivery states the supplier reports (accepted, shipped, delivered), the cancellation
--      request after the order went to the supplier, and `submitting`, the job's claim before it calls the supplier, so
--      a cancellation before the supplier and a submission can never both happen. SQLite cannot change a CHECK in place:
--      the table is rebuilt (nothing references it).
--   2. refunds: one row per refund, its id is the idempotency key. A refund is claimed in the same statement that checks
--      the order's paid amount, so the refunds of an order never add up to more than it paid, whatever runs at once. Its
--      credit note (the invoice provider) is claimed on the same row.
--   3. cancellations: one per order, before or after the supplier, with who asked and what the supplier answered.
--   4. invoices: "checked by a person" for a claim left `unresolved` (S12), with who and when.
--   5. notifications: the new-order alert, claimed once per order and kind.
--   6. audit_log: an index by subject, for the admin's order page.
CREATE TABLE supplier_shipments_new (
  id                 TEXT PRIMARY KEY,
  order_id           TEXT NOT NULL REFERENCES orders(id),
  supplier           TEXT NOT NULL,
  fulfillment_source TEXT NOT NULL DEFAULT 'dropship_cj',
  status             TEXT NOT NULL CHECK (status IN ('queued', 'submitting', 'submitted', 'accepted', 'failed', 'shipped', 'delivered', 'cancel_requested', 'canceled')),
  supplier_order_id  TEXT,
  tracking_number    TEXT,
  tracking_url       TEXT,
  attempts           INTEGER NOT NULL DEFAULT 0,
  last_error         TEXT,
  request_json       TEXT,
  response_json      TEXT,
  created_at         TEXT NOT NULL,
  updated_at         TEXT NOT NULL,
  shipped_at         TEXT,
  delivered_at       TEXT,
  UNIQUE (order_id, supplier)
);
INSERT INTO supplier_shipments_new (id, order_id, supplier, fulfillment_source, status, supplier_order_id, tracking_number, tracking_url,
  attempts, last_error, request_json, response_json, created_at, updated_at)
SELECT id, order_id, supplier, fulfillment_source, status, supplier_order_id, tracking_number, tracking_url,
  attempts, last_error, request_json, response_json, created_at, updated_at
FROM supplier_shipments;
DROP TABLE supplier_shipments;
ALTER TABLE supplier_shipments_new RENAME TO supplier_shipments;
CREATE INDEX supplier_shipments_status ON supplier_shipments (status, updated_at);

CREATE TABLE refunds (
  id                 TEXT PRIMARY KEY,
  order_id           TEXT NOT NULL REFERENCES orders(id),
  kind               TEXT NOT NULL CHECK (kind IN ('full', 'partial')),
  amount_agorot      INTEGER NOT NULL CHECK (amount_agorot > 0),
  reason             TEXT NOT NULL DEFAULT '',
  -- claimed: counted against the paid amount while the provider is asked; refused: the provider refused, nothing moved,
  -- and it no longer counts; unresolved: a person checks the provider (it can neither be asked nor deduplicates)
  state              TEXT NOT NULL CHECK (state IN ('claimed', 'refunded', 'refused', 'unresolved')),
  provider           TEXT NOT NULL,
  provider_refund_id TEXT,
  requested_by       TEXT NOT NULL,
  claimed_at         TEXT NOT NULL,
  attempts           INTEGER NOT NULL DEFAULT 1 CHECK (attempts >= 1),
  completed_at       TEXT,
  last_error         TEXT,
  credit_state       TEXT NOT NULL DEFAULT 'pending' CHECK (credit_state IN ('pending', 'claimed', 'issued', 'not_needed', 'unresolved')),
  credit_note_id     TEXT,
  credit_claimed_at  TEXT,
  credit_issued_at   TEXT,
  credit_error       TEXT
);
CREATE INDEX refunds_order ON refunds (order_id, claimed_at);

CREATE TABLE cancellations (
  order_id      TEXT PRIMARY KEY REFERENCES orders(id),
  stage         TEXT NOT NULL CHECK (stage IN ('before_payment', 'before_supplier', 'after_supplier', 'after_payment_late')),
  state         TEXT NOT NULL CHECK (state IN ('requested', 'canceled', 'refused')),
  reason        TEXT NOT NULL DEFAULT '',
  requested_by  TEXT NOT NULL,
  requested_at  TEXT NOT NULL,
  resolved_at   TEXT,
  refund_id     TEXT
);

ALTER TABLE invoices ADD COLUMN checked_by TEXT;
ALTER TABLE invoices ADD COLUMN checked_at TEXT;

CREATE TABLE notifications (
  kind        TEXT NOT NULL,
  order_id    TEXT NOT NULL REFERENCES orders(id),
  state       TEXT NOT NULL CHECK (state IN ('claimed', 'sent', 'failed')),
  provider    TEXT NOT NULL,
  attempts    INTEGER NOT NULL DEFAULT 1,
  claimed_at  TEXT NOT NULL,
  sent_at     TEXT,
  last_error  TEXT,
  PRIMARY KEY (kind, order_id)
);

CREATE INDEX audit_log_subject ON audit_log (subject, id);
CREATE INDEX orders_created ON orders (created_at);
