-- S12, fixes from QA S8–S10 (qa/reports/2026-11-10-site-track-qa-s8-s10.md) and the S11 addendum:
--   ת16: the tax invoice is claimed per order in D1 before the provider is called. One row per order (the PRIMARY KEY
--        is the idempotency key): only the run that inserts it calls the provider; a claim left without a result is
--        resolved by asking the provider, never by issuing again (api/src/lib/invoices).
--   S11 question 2: a set of distinct SKUs (the triptych) carries its composition, the supplier SKUs of its parts (one
--        each per set); a set whose card does not name them is refused (`set_incomplete`). The order line snapshots
--        what one unit sold is at the supplier, and the supplier order expands it (api/src/lib/fulfillment.ts).
--   ת21: the house a line was bought in ("החדר שלך" draws that house, and only the variant bought).
CREATE TABLE invoices (
  order_id            TEXT PRIMARY KEY REFERENCES orders(id),
  state               TEXT NOT NULL CHECK (state IN ('claimed', 'issued', 'unresolved')),
  provider            TEXT NOT NULL,
  idempotency_key     TEXT NOT NULL,
  provider_invoice_id TEXT,
  url                 TEXT,
  attempts            INTEGER NOT NULL DEFAULT 1 CHECK (attempts >= 1),
  claimed_at          TEXT NOT NULL,
  issued_at           TEXT,
  last_error          TEXT
);
-- an order the job invoiced before S12 (its audit row) is issued: the new job never issues it again
INSERT INTO invoices (order_id, state, provider, idempotency_key, provider_invoice_id, claimed_at, issued_at)
SELECT a.subject, 'issued', substr(a.actor, 9), a.subject, json_extract(a.detail, '$.invoice_id'), a.at, a.at
FROM audit_log a
WHERE a.id IN (SELECT MIN(id) FROM audit_log WHERE action = 'order.invoiced' GROUP BY subject)
  AND a.subject IN (SELECT id FROM orders);

ALTER TABLE product_variants ADD COLUMN set_skus_json TEXT;
ALTER TABLE product_variants ADD COLUMN set_incomplete TEXT;
ALTER TABLE order_items ADD COLUMN supplier_lines_json TEXT;
ALTER TABLE cart_items ADD COLUMN house TEXT CHECK (house IS NULL OR length(house) <= 40);
ALTER TABLE order_items ADD COLUMN house TEXT;
