# Brief: S13, operations: running the shop day to day (frontend-dev, 2026-11-11)

This continues the interface track, `briefs/site-interface-track-2026-11-07.md`, with the same working rules. S12 is done and committed at `b94c5bc1`; see `qa/reports/2026-11-07-site-track/s12/README.md`.

The source is the launch checklist, `qa/reports/2026-11-10-site-track/launch-checklist.md`. This sprint takes the items that are yours and need no owner account or keys: 2.5, 3.3, 6.2, 6.3, plus the room-JS budget. Everything stays behind flags and mocks.

## The tasks
1. **The room-JS budget comes first:** S12 left the room at 78.2/80 KB.
   - Split the order page ("החדר שלך") and anything else that isn't on the room's first paint into its own chunks.
   - The goal is ≤ 74 KB, so the next features have room.
   - Don't raise the budget.
2. **Order operations (6.3):**
   - **An admin screen** behind the existing Admin API and Cloudflare Access, in Hebrew and RTL. Use the existing design system; it only needs to be clear.
     - **The list:** orders with status, filters and search by public id.
     - **An order page:**
       - items with house and variant;
       - the payment, invoice and supplier states, from the audit_log;
       - the `unresolved` invoice state from S12, with a "checked by a person" action that is logged.
   - **The cancellation procedure:**
     - **Before it's sent to the supplier:** cancel plus a refund through the payment interface (mock).
     - **After it's sent:** a cancellation request to the supplier (mock) and a clear status.
     - Every action is logged in the audit_log, with who did it.
   - **A new-order alert:** an interface only (`NOTIFY_PROVIDER`), with a mock that writes to a log. The provider (email or Telegram) is the owner's decision later. Don't build a real channel.
3. **Refunds (2.5):**
   - full and partial refunds through the provider interface, with a mock;
   - idempotent, like the S12 invoices;
   - a credit note through the invoice interface (mock);
   - never more than what was paid.
4. **Delivery tracking for the customer (3.3):**
   - **The statuses:** "התקבלה", "בהכנה", "נשלחה" (with a tracking number), "נמסרה". They come from the supplier interface (mock).
   - **Where they show:** on the order page the customer has, behind the order's public link and verification, the same as today.
   - **The supplier's link:** the shipment link may be shown only if it's generic, with no supplier name. Otherwise show the number only.
5. **Monitoring (6.2):**
   - **A `/healthz` endpoint:** checks D1 and the queue, and returns no secrets and no internal details.
   - **Structured error logging in the Worker:**
     - log rows in Workers Logs format, with an error id;
     - the customer sees a short message with that id;
     - no PII in the logs: no address, phone, email or full name.
   - **The uptime clock** is an external service. List it in the runbook as an owner step; don't build it.

## Acceptance
- **All the checks:** typecheck, lint, format:check, vitest, e2e, a11y, budget, and the check-config and encoding checks from S12.
- **New tests:**
  - the cancellation states (before and after sending);
  - an idempotent refund that never goes above what was paid;
  - the delivery statuses;
  - no PII in a log row;
  - `/healthz` with no internal details;
  - access to admin without permission returns 403.
- **The public build:** stays free of supplier names (public-scan) and of admin code.
- **Evidence:** in `qa/reports/2026-11-07-site-track/s13/`, with admin screens at 1280 and the customer's order page at 400.
- **Update** `docs/ops/deploy-runbook.md` and the launch checklist with the new status.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- No contact with any supplier or external service.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
