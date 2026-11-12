# Brief: R7, the table group, the true curtain lengths, the planter, and passes 6'–7' (render-agent, 2026-11-12)

**The owner's answers (2026-11-12)** are applied to the binding docs: `docs/proposals/owner-answers-applied-2026-11-12.md`. Read it whole, especially §1 (WM-T2), §6 (curtains) and §8 (planter).

The new versions:
- **Slots:** `data/slots/living-room.json` 1.9.4.
- **House plan:** 1.3.6.
- **The Bible:** `docs/design-bible/warm-modern.md` 1.0.2.
- **The selection:** `update_2026_11_12`.

**Start from** R6's manifest, `layers/manifest-r6.json`, once it exists.

**The approval:**
- **6' and 7':** these steps are part of PH2-WM (up to 9,740). Phase 2 so far is 5,850, and these two passes are 1,300.
- **The code work:** 0 tokens.

## A. Code, 0 tokens
1. **The planter (§8):**
   - darken it with one factor in linear light, **k = 0.78** (allowed range 0.72–0.84);
   - **the targets:**
     - the planter's median 6–10 L* darker than the wall beside it;
     - the shoulder at 74–79;
   - the 0.8% strip above the basket is accepted as a documented tangency.
2. **The true curtain lengths (§6):**
   - the hem 12 cm above the floor for the default (180502) and curtain 2 (554205), at 270;
   - the hem 22 cm above the floor for curtain 3, at 260;
   - the top of the fabric at 2.82;
   - above the stone bench, the excess is folded back along the glazing;
   - **follow** the pixel lines, the hem, the shadow and the QA conditions in §6 exactly.
3. **The table group (§1):**
   - first run `step0_clay_checks.py` with the bodies of **all** the bowl and candle-holder variants at the new coordinates. Nothing may fall below 0.02. If something does, use the levers already approved in §1.4;
   - then move the rendered defaults (the travertine candle holders and the bowl) to the new coordinates **in code**, per the numbers in §1.5;
   - **note:** this is an owner-approved slot change. The geometry comes from the plan and the defaults already rendered. Re-light the contact shadows with the frozen recipe.

## B. Passes 6' and 7' (650 each)
- **6':**
  - bowl 2;
  - candle holders 2;
  - vase 3.
- **7':**
  - bowl 3;
  - candle holders 3;
  - **curtain 3 in Linen,** SKU `CJYD218713946TG`, 200×260 with hooks, rendered at its true length.
- **The iron candles:** 15 and 18 cm, not 20 (§1).

## Method (as in R3–R5)
- **Placeholders:** photographic placeholders fitted to the clay boxes. No finished layer moves in code, except the table-group defaults in A.3, which is the owner-approved slot change.
- **References:** one card crop per product, used as a reference only.
- **Passes:** 3–4 products per pass, and no third pass.
- **The shadow recipe:** frozen.
- **Before each job:** run `var2_estimate_cost`.

## Acceptance (as before)
- **The layers:**
  - one v3c grade;
  - swap-diff 0;
  - recomposite p99.9 ≤2 and max ≤6;
  - the full cross of combinations;
  - the lock;
  - fidelity in shape, colour, size and position.
- **The output:**
  - `manifest-r7.json` plus its verify script;
  - a sheet of all the variants;
  - crops;
  - asset manifest entries.

## Fixed rules
- If var2 asks for authentication, stop and report.
- New files only. No commits.
- Return a short Hebrew summary.
