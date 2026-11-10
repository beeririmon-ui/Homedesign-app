# Brief: S12, fixes from QA S8–S10 (frontend-dev, 2026-11-10)

This continues the interface track, `briefs/site-interface-track-2026-11-07.md`, with the same working rules. It starts after S11.
- **The source:** `qa/reports/2026-11-10-site-track-qa-s8-s10.md` plus `.json`, and the tools, data and overlays in the folder of the same name. It was measured on `b0a71cd2`.
- **The verdict:** continue behind the flag.

## Required before launch
- **ת16: the invoice job issues two invoices for one order.** This happens with two concurrent runs, or after a crash between the provider call and the record.
  - **The fix:** a real idempotency key, `order_id`, held at the D1 level as a unique constraint or a claim row, *before* the provider call. Pass the same key to the provider as an idempotency key where the interface supports it.
  - **The vitest:** concurrent runs, and a crash simulated between the steps.
- **ת17: a missing, `mock` or misspelled provider variable in production turns on the mock invoice and mock supplier.** The order is then recorded as sent and invoiced when nothing happened.
  - **The fix:** in production, any value that isn't an explicit real provider fails closed, loudly. The order stays in its real state, never "submitted" or "invoiced".
  - Mock is allowed only when `ENVIRONMENT` is not production.
  - **Tests:** a config test for each provider variable.
- **ת21: "החדר שלך" draws the product as it is in the room, not the variant bought, and always in the Nordic living room.**
  - **The fix:** draw the house the item was bought in, and the variant bought, where a layer exists for it.
  - **Where there's no layer for the variant:** fidelity first. Don't draw a wrong colour. Show the product's card image for that variant instead, with a short line saying it isn't in the room yet.
  - **The e2e:** a beige cushion and the Pecan throw from the warm-modern house.

## Also high: ת15, the house switch cuts through black
- **The cause:** `ensureTargets()` in `gl.ts` throws away the previous composite when the composite width changes (1920 in the Nordic house, 2720 in the warm-modern one).
- **The fix:** keep both targets through the dissolve, or composite both houses at one width.
- **The e2e:** checks what is drawn at the midpoint: no black frame, and both houses visibly mixed. That's ת26 too.

## Medium
- **ת22:** in the set panel, the throw (₪169) is cut off at the bottom of the list at every width, and on the phone it's barely visible. The layout is yours. If the order or density needs a design call, take a default and list it for master-designer.
- **ת18:** a cancelled, unpaid order gets an invoice. The fix: invoice only orders in `paid`, re-checked inside the job.
- **ת19:** `INVOICE_PROVIDER=UNDECIDED` crashes a whole batch in the queue. The fix: fail per message, never per batch, and loudly.

## Low and small
- **ת20:** with Grow outside production, the mock webhook is still live. Close it unless the mock provider is active.
- **ת23:** a direct entry to the warm-modern house downloads 1.4 MB of the Nordic house. Close it together with S10 question 7, if S11 hasn't already. Check S11's README first.
- **ת24:** fix the inaccuracies in `docs/ops/deploy-runbook.md` per the report.
- **ת25:** "חזרה לסלון" on the empty checkout is 62×19. Bring it to at least 44 px.
- **ת26:** a test that is sensitive to load. Make it robust, without skipping it and without lengthening timeouts blindly.

## The base encoding: QA's verdict on S10 question 4
- **The threshold for any tool layer on the public site,** measured against the approved file on what the browser draws:
  - p99 ≤ 6 and p99.9 ≤ 10;
  - at most 0.2% of pixels above 8 levels;
  - ΔE00 p99 ≤ 3.5;
  - no defect visible at ×1.
- **For the warm-modern base,** use **AVIF q70**. It passes in every view: about 161 KB, and the house comes to about 350 KB on the phone.
- **Make the threshold a build check** for tool layers. Check the Nordic house against it too, and report the numbers without changing them unless they fail.

## Acceptance
- **All the checks:** typecheck, lint, format:check, vitest, e2e, a11y and budget.
- **New tests:** for ת15, ת16, ת17, ת18, ת19 and ת21.
- **Evidence:** in `qa/reports/2026-11-07-site-track/s12/`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
