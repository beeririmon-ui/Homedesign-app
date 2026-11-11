-- S16 (QA S13–S14):
--   1. supplier_shipments.reach (ת35): whether a call of ours may have reached the supplier while we hold no supplier
--      order id. 'none': no call reached it as far as we know (never called, or every failure was a refusal before or
--      at the supplier's door); 'maybe': a submit failed in a way that may have created the order (a call that timed out,
--      a network or server error), and a later refusal never turns it back; 'checked': the supplier was asked by our
--      order number (or a person checked at the supplier) and holds no order. A shipment that is 'failed' with 'maybe',
--      or of an order in supplier_error with 'none', counts as sent: no silent refund.
--   2. supplier_shipments.failing_since (ת39): the first failed submit of the current run of failures; NULL once one
--      succeeds. /healthz reads it ("degraded" past 30 minutes).
--   3. refunds.in_flight_until (ת36): the lease of the call to the payment provider that is running now; NULL when no
--      call is running. A request for the same refund while it is set (and not past) is 409 in_progress, whatever the
--      provider; past it (a crash mid-call), the provider is asked before any second call.
ALTER TABLE supplier_shipments ADD COLUMN reach TEXT NOT NULL DEFAULT 'none' CHECK (reach IN ('none', 'maybe', 'checked'));
ALTER TABLE supplier_shipments ADD COLUMN failing_since TEXT;
ALTER TABLE refunds ADD COLUMN in_flight_until TEXT;
