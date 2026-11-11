# Brief: warm-modern tool phase 2, passes 4' and 5', plus colour fixes in code (render-agent, 2026-11-11)

**The background:**
- **The checkpoint passed:**
  - QA: `qa/reports/2026-11-11-wm-tool-phase2-checkpoint.md`;
  - the designer's eye: `docs/proposals/wm-phase2-checkpoint-eye-2026-11-11.md`. **Read it whole.** It holds the order, the numeric targets and the instructions for you.
- **The R4 code fixes are done:** `layers/manifest-r4.json`. QA is checking the changed regions in parallel.

**The approval:** PH2-WM (the owner, up to 9,740). Phase 2 so far is 4,550; these two passes are 1,300.

## 0. Colour fixes in code first (0 tokens)
- **The curtains:** recolour toward the card's cream, per the designer's §3.
  - Change a* and b* only, with hue 85–95.
  - Target a median C* of 5.5–7.5, today 15.1, and at least 0.5 above the plaster beside it.
  - L* doesn't change.
- **The magazine holder's thin rods:** silver as in the card photo, not black. The tubes stay glossy black, as a documented exception (pending the owner's WM-M1).

## 1. Pass 4' (650)
- **The vase:** re-render the default at the plan point.
  - **First, a clay check at 0 tokens:** choose one point for all three vases, from the three candidate points within 0.10 of the slot, per the designer's §2.
  - **The size:** 32×16 per the card.
- **Curtains 2.**
- **Framed art 2.**
- **Accent sconces 2.**

## 2. Pass 5' (650), after 4' is clear
- **The planter, whole:** the card's opening, ribs and colour, per the designer's §6. This breaks the dependency on the basket.
- **Vase 2:** at the point chosen in 4'.
- **Accent sconces 3.**
- **Pendant 2:** use `canopy_cut()` from `fix_r4.py` for the canopy.

## Method (the lessons so far)
- **Inputs:** use photographic placeholders. That means the product's own earlier render, or the card-sized clay box, fitted in code to the clay box at the card size and the plan position. The model re-renders the material, light and contact. No finished layer is moved in code. The manager accepted this method (R3).
- **References:** one card crop per product. Supplier images are references only and never kept as composition. Keep them in the scratchpad and var2 only.
- **Products per pass:** 3–4 at most.
- **Before each job:** run `var2_estimate_cost`. If a pass fails, report it and don't run a third pass. A size miss may be scaled in code; a placement miss may not.
- **The shadow recipe bug** you found (`extract.shadow_one`): use the sRGB ratio in the new layers, as you did in R4. Don't rewrite the old layers.

## Acceptance (as before)
- **Each layer:**
  - one layer per product, cut from the graded composite;
  - one v3c grade;
  - swap-diff 0 outside each product and its shadow;
  - recomposite p99.9 ≤2 and max ≤6;
  - the lock holds;
  - fidelity in shape, colour, proportions, size and position.
- **Variants:** each variant swaps with every variant of the other slots.
- **The output:**
  - a new layers manifest version (`manifest-r5.json`) with its verify script;
  - a sheet showing each slot's variants on the default scene with set B;
  - crops;
  - asset manifest entries in a separate JSON.

## Fixed rules
- If var2 asks for authentication, stop and report.
- New files only. No commits.
- Return a short Hebrew summary: the tokens, the fidelity per product, the numbers, and your honest read.
