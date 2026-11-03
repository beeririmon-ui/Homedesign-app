# Brief: the accumulated site and economics fixes (frontend-dev, 2026-11-03)

The owner answered the decisions meeting today (`status/decisions-meeting-2026-11-03.md`; the answers are in `status/decisions.json` and in `docs/studio-rules.md` ה.15, ו.9 and the ז log of 2026-11-03). This brief is the commerce-truth and interface part. The test page in the magazine language (art direction §12) is the next brief, after this one is in.

## The answers
- **SITE1 = now:** the fixes that accumulated since 2026-10-20 (78 cards outside the schema, 2 failing site tests, 5 economics gaps between the site and the studio), plus a floor for the derived prices.
- **NL1:** the wabi-sabi cushion's price becomes ₪89 (it loses ₪8.56 in the 30×50 size at ₪69). Find the card through `data/economics/no-loss-report-2026-10-20.md`.
- **NL2:** a product whose no-loss price is more than 2× the high Israeli comparison, or that ships express only, is shown as "המלאי אינו זמין כעת" with the waiting list (PRE1); the no-loss price stays in the card; it is not sold until a cheaper source exists.
- **R6Q2:** `kids/step-stool`, `living-room/pouf` and `bath/shower-stool` are shown as "המלאי אינו זמין כעת" (PRE1), like AU2, and leave the readiness counter.
- **ART3:** no dark mode at launch: remove the dark theme and the moon button.
- **ART6:** order statuses "התקבלה · בהכנה · נשלחה · נמסרה" (never "הועברה לספק"); the order number in digits only, no "HD" prefix.
- **ART7:** "בוהו בקרוב" and "מודרני חם בקרוב" leave the room image; the unavailable styles appear only in the contents, captioned "בגיליונות הבאים".

## Read first
- `status/decisions.json`: SITE1 (its context lists the five economics gaps), NL1, NL2, NL3, R6Q2, PRE1, AU2, ART3, ART6, ART7.
- `data/economics/no-loss-audit-2026-10-20.md`, `no-loss-report-2026-10-20.md`, `scripts/economics/no_loss.py`, `data/economics/settings.json`, `studio/build.py`.
- `docs/ops/quality-gates-2026-11-02.md`: gates G6 (performance), G7 (accessibility), G8 (commerce truth) and the gaps section (the player's push zoom and pre-decode, the site checks QA could not run, the derived-SKU finding: 1,115 derived SKUs of 120 products lose at the headline price).
- `docs/site-art-direction-2026-11-02.md` §6 (the interface states, the order language) for the wording of ART6 and ART7.
- `site/README.md` (the test scripts) and `data/product-card.schema.json`.

## Tasks
1. **Schema:** make the 78 cards pass `data/product-card.schema.json`, by fixing the cards when the data is wrong and the validator when the schema is wrong; list which was which.
2. **The two failing site tests:** fix them.
3. **Economics parity, site = studio:** multi-unit shipping by the combined-parcel formula, not linear; no silent $17 default when a shipping line is missing (mark the card instead); no 40% provisional price for cards without a line; the cheap-option price (skuRetail) must not lose; the "יקר מהשוק" label in `build.py`.
4. **The derived-price floor:** every SKU and variant price the site shows is at least its own no-loss price. Extend `scripts/economics/no_loss.py --check` to the derived SKUs so the gate G8.1 has evidence, and run it: the output file goes under `qa/reports/2026-11-03-site/`.
5. **NL1, NL2, R6Q2** as above. NL2 is a display rule in the build, driven by the comparison data in the card and the shipping lines; it never changes the stored price.
6. **ART3, ART6, ART7** as above, in the site's own language (tokens from `site/web/src/styles/`).
7. **The player:** remove the "push" zoom the current player adds, and pre-decode the frames before a transition plays (the gates audit names both). Keep it minimal; no new dependencies.
8. **Run the site's checks** (`typecheck`, `test`, `lint`, and `e2e`/`a11y`/`budget` where they run offline) and save the outputs under `qa/reports/2026-11-03-site/` with a short `README.md` (what ran, what passed, the failing lines). If `node_modules` is missing, `npm ci` from the lockfile is allowed if the network allows it; don't add or upgrade a dependency, and report if the install is blocked.

## Fixed rules
- No commits. Don't touch `assets/renders/`, the prompts, the slots' product lists, or any binding document.
- Any change to a price other than NL1 is a question, not an edit.
- Return a short summary in Hebrew: what passed and what failed in the site checks (with the evidence paths), the schema fixes count by kind, the economics gaps closed, and anything that remains.
