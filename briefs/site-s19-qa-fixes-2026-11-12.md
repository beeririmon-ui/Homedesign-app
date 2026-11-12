# Brief: S19, fixes from QA S17 (frontend-dev, 2026-11-12)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same rules. It starts after S18. The source is `qa/reports/2026-11-12-site-track-qa-s17.md` plus `.json`, with its tools (`mut-rights.mjs`, `fp-scan.mts`, `fp-rule-alt.mts`, `an-browser.mjs`, `negation-probe.ts`).

## The items
- **ת50, before the warm-modern house or any small-product layer goes public:** the near-miss rule B applies only when both images have a mean ink ≥ 4 (32×32 grey).
  - **Prove it with QA's numbers:** 321/321 and 10/10 still caught, and the 126 false matches drop to 0. Use `fp-scan.mts` over all of `assets/renders`.
- **ת55, before a real analytics token:** the cart and checkout always load as a full document, never as an in-site navigation. That way the Cloudflare script is never present while the customer types their details.
  - **An e2e:** the in-site path room → product → cart → checkout shows no beacon on cart and checkout.
- **ת51:**
  - also hash the flipped image;
  - trim borders before hashing;
  - keep a fixed list of supplier image domains next to the hosts from the cards (including `aliexpress-media.com`);
  - normalise a data: URI broken across lines.
- **ת52:**
  - log redaction respects word boundaries;
  - never touch `error_id`, `order_id`, the event or the path;
  - for email, redact only the local part and the full address.
- **ת53:** `errorCode` takes a snake_case prefix and an error name only from our own classes, or from `orderLog` in those rows.
- **ת54:** `failing_since` follows the dead claim, or `supplier_error` with reach "maybe" is degraded immediately.
- **QA note ה8:** "במרקם" only when there's no negation word in the sentence, plus a build list of every "הדפס במרקם" with the source text.
- **Update the launch checklist** with QA's proposed lines for 6.1, 1.5 and 6.2.

## Acceptance
- All the checks pass.
- New tests for ת50–ת55 and ה8.
- The evidence goes in `qa/reports/2026-11-07-site-track/s19/`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- Never `npx` without `--no-install`.
- Return a short Hebrew summary.
