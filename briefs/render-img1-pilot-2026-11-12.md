# Brief: IMG1, the pilot of our own product images (render-agent, 2026-11-12)

**The owner (2026-11-12, IMG1):** "8.כן רק שיהיה נאמן למקור". The pilot is approved: **3,950 tokens, plus a reserve of up to 2,000, released only with the manager's approval.** **Fidelity to the real product comes first.** An image that's beautiful but not faithful is rejected (CLAUDE.md).

**The plan is binding:** master-designer's `docs/proposals/own-product-images-2026-11-11.md`. Read it whole, especially:
- §2, the method: fidelity without the supplier's composition;
- §5, the pilot:
  - 5.2, what to make;
  - 5.3, the references;
  - 5.4, **the exact prompts**;
  - 5.5, the acceptance criteria;
  - 5.6, the order of work and what the pilot decides.

## The 3 products (§5.1)
- **The muslin throw:** P1 in the room, White. In the pilot also P4 in Pecan.
- **The crinkled stoneware vase.**
- **The pair of travertine lamps, eavr7:** P1 lit.

## What the pilot decides (§5.6)
- **The P2 model:** an A/B between gpt-image-2-5 transparent and nano-banana-pro plus remove-background.
- **The P1 model:** nano-banana-pro, with nano-banana-2 4K as the fallback.
- **Whether P4 by edit is allowed for Pecan.**

## Firm rules on supplier images (`docs/research/supplier-image-rights-2026-11-11.md`)
- **Internal reference only.** A supplier image goes in only as an internal reference sheet: the product cut out, with no background and no text, from several angles (§2.2).
- **Never the base.** A supplier image is never the base image of an edit, and its composition is never kept.
- **Where it lives:** supplier images stay in the scratchpad and in var2 only, and are never committed.
- **P1:** an edit of a crop of **our own** story frame or tool layer only.

## Price and acceptance
- **Before each job:** run `var2_estimate_cost`.
  - **gpt-image-2-5 transparent:** the designer assumed 600 at 2K. Confirm it.
  - **If an estimate is off by more than 10%,** stop and report.
- **Acceptance per image:** §5.5, with its numeric targets.
  - **QA's new checks C1–C5 (§6),** "no supplier composition", get their inputs from you. Record, per image, its base and the references it used (§2.6, the source record).
- **The output:** `assets/renders/products/img1-pilot-2026-11-12/`, with:
  - the images;
  - `jobs.json` (prices, models and references);
  - `source-record.json` (§2.6);
  - an A/B sheet for P2;
  - crops at 100%.

## Fixed rules
- If var2 asks for authentication, stop and report. Never ask for codes.
- New files only. No commits.
- Return a short Hebrew summary: the tokens per job, fidelity per image, the A/B result, and your honest read.
