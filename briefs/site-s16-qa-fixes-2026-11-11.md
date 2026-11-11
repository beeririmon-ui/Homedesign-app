# Brief: S16, fixes from QA S13–S14 (frontend-dev, 2026-11-11)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same working rules. S15 is done (`4112dad7`).

**The source:** `qa/reports/2026-11-11-site-track-qa-s13-s14.md` plus `.json`, with its tools, data and overlays. QA measured `a8104956`, before S15. Check each finding against the current tree, because S15 may already have touched some of them.

## Before the admin goes live
- **ת34:**
  - **`readJson`:** the MIME essence must be exactly `application/json`.
  - **Admin actions:** require a same-site Origin or `Sec-Fetch-Site: same-origin`, or a service token for the studio.
  - **The runbook:** add the Access cookie's `SameSite=Lax` to `docs/ops/deploy-runbook.md`.
  - **A vitest:** a cross-site `text/plain; charset=application/json` request is refused.

## Before real suppliers or payments
- **ת35:** a delivery whose last call may have reached the supplier, or an order in `supplier_error`, counts as "sent". Cancellation then asks the supplier first by our order number, or takes the "after the supplier" path, or is left to a person. Never a silent full refund.
- **ת36:** in `resume()`, a claim younger than the lease returns 409, for every kind of provider, as the invoice job does. After the lease, ask the provider.
- **ת38:** log supplier errors by code only, or strip the customer's own values (name, address) from any message. The full text stays in D1.

## Before mailing customers
- **ת39:**
  - **A log row:** every failed supplier send writes one.
  - **`/healthz`:** returns "degraded" when a paid order has been failing at the supplier for more than N minutes. Choose N and say why.
  - **The customer:** sees `supplier_error` honestly, not as "בהכנה" (QA note ה7). Use neutral wording, and list it for master-designer.

## Before `HD_PUBLIC=1`
- **ת41:** leave the 39 old redirects that carry a supplier name out of the public `_redirects`.

## Before the warm-modern house goes public
- **ת43:**
  - **The WebP fallback:** WebP q95 (669 KB), per QA's ruling, with the engine loading at idle in browsers without AVIF.
  - **A budget line:** for a browser without AVIF.

## Small
- **ת37:** a `try/catch` around decoding a malformed tracking link. The order page and the cart show `message_he` on errors, as the checkout does.
- **ת40:** write `claim_lost` when the run that took over has already recorded the result.
- **ת42:** a second cancel while waiting returns the state, without another supplier call.
- **ת44:** the "no lazy page in the room entry" check works by content (the Vite manifest, or a marker string per page), not by file name.
- **QA note ה7:**
  - a deploy without `check-config` must be impossible (CI and runbook);
  - the exclusions doc must point to the real test file.
- **QA note ה1:** a small inline set-B placeholder on the stage, so it isn't dark while the poster loads. Keep it within budget.

## Acceptance
- All the checks pass.
- New tests for ת34, ת35, ת36, ת38, ת39, ת41, ת43 and ת44.
- The evidence goes in `qa/reports/2026-11-07-site-track/s16/`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
