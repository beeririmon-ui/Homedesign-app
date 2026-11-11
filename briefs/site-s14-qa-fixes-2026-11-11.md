# Brief: S14, fixes from QA S11–S12 (frontend-dev, 2026-11-11)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same working rules. S13 is done; see `qa/reports/2026-11-07-site-track/s13/README.md`. The source is `qa/reports/2026-11-11-site-track-qa-s11-s12.md` plus `.json`, with its tools, data and overlays. Of ת7–ת26, 19 of 20 are closed.

## Required before launch
- **ת27:** the floor lamp is sold correctly, but the supplier order carries the generic product SKU (`CJYD2247544`) instead of the regular variant's SKU (`CJYD224754407GT`).
  - **The fix:** the supplier line always carries the variant SKU, never the product's.
  - **Check every product** with sale exclusions or a single SKU.
  - **The vitest:** on the supplier lines.
- **ת28:** in "החדר שלך", when one order holds two options of the same slot, the second isn't drawn and doesn't appear in the list, even though the caption says "מה שהזמנת".
  - **The fix:** every line in the order appears in the list.
  - **The picture:** draw one option per slot, and say clearly which one is drawn and which other options were ordered.
  - **The e2e:** cover this case.

## High
- **ת29:** a direct entry to the warm-modern house shows an empty sofa, without the cushions and throw, until the first touch.
  - **The fix:** set B is drawn from the first paint.
  - **The poster:** it's the approved set B composite.
- **ת30, blocks `HD_PUBLIC=1`:** the poster fails the encoding threshold. QA's recommendation, measured in the browser, is in the report §4.
  - **Nordic:** `shell.1280` and `shell.1920` in AVIF q80.
  - **Warm modern:** 1280 at q90, 400@1 at q80, and 2720 at q85.
  - **The 1920 desktop poster for warm modern:** no lossy setting passes. Take a solution that passes without serving 1.45 MB, for example serving the 2720 at q85 on desktop too, or something else you measure. Report the numbers.

## Small
- **ת31:** the 10-minute lease is shorter than a supplier call that hangs. Fix it per the report.
- **ת32:** in CI, `npm run typecheck` runs before `.generated` exists. Fix the order so CI passes on a clean copy.
- **ת33:** the public page of the Morandi triptych shows an internal English sourcing note as its description. The fix:
  - never show `notes` publicly;
  - add a build check that fails on Latin in a public description;
  - give the product a neutral Hebrew description from the card's data, or no description at all.

## Acceptance
- All the checks pass.
- New tests for ת27, ת28, ת29, ת30 and ת33.
- The evidence goes in `qa/reports/2026-11-07-site-track/s14/`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
