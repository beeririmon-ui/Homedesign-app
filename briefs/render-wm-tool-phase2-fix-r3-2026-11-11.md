# Brief: warm-modern tool phase 2, fix pass R3 (render-agent, 2026-11-11)

**Background:** the reserve passes R1/R2 ran at 1,300. See `assets/renders/living-room/warm-modern/phase2-2026-11-10/`: `jobs-reserve.json`, `work-reserve/fidelity-r12.json`, `layers/manifest-r12.json` and `phase2-reserve-r12-sheet.jpg`, plus the prompts in `assets/prompts/warm-modern-phase2-2026-11-10/`.
- **Passed:** the curtains (geometry; the colour is partial), the magazine holder (Orange), and the bowl (provisional position, pending WM-T2).
- **Failed:**
  - **the planter:** drawn about ×1.36 the card, with a 57 cm rim against 42, and 48 cm tall against 35.5;
  - **the basket:** placed away from the plan's (−1.62, 0.78), and a bit large;
  - **the pendant:** hung about 11 cm low. The bottom of the shade is at ~1.79–1.80 against the owner's 1.90 (V7Q7 b).

**The approval:** the manager approves a targeted fix pass under SPEND2 (the owner, 2026-11-10: "את יכולה לנצל עוד מהקרדיט של var2 במידת הצורך"). Up to 650 per pass, and **at most two passes, 1,300 in total**.

## The passes
- **R3a (650):** the planter and basket together, the basket **in front of** the planter.
  - Use the exact clay place-holders from the cards (rim 42, height 35.5), at the plan's positions.
  - Give one card crop per product.
- **R3b (650):** the pendant alone, at the plan's X/Y.
  - The shade bottom at 1.90 per V7Q7 b, 50 cm per the card.
  - Use a place-holder at the right height.
- **The order:** run R3a first. Run R3b only after R3a's result is clear, so you can apply what you learned.
- **If a pass fails again:** stop and report, and don't run a third. A size miss may be scaled in code; a placement miss may not.
- **The cheaper option:** grok segment-edit is allowed only if you're confident it can shift an object, given the P6b lesson that it didn't change shape. Otherwise, seedream.

## Acceptance
- **As in the phase 2 brief:**
  - one layer per product, cut from the graded composite;
  - one v3c grade;
  - swap-diff 0 outside the product and its shadow;
  - recomposite p99.9 ≤2 and max ≤6;
  - the lock holds;
  - fidelity in shape, colour, proportions, size and position.
- **The output:**
  - new files in the same folder;
  - a new layers manifest version;
  - a full default scene sheet with set B, all 12 defaults (the bowl marked provisional);
  - a separate JSON with asset manifest entries for the manager.

## Fixed rules
- Run `var2_estimate_cost` before each job.
- If var2 asks for authentication, stop and report.
- Supplier images stay in the scratchpad and in var2 only.
- New files only. No commits.
- Return a short Hebrew summary: tokens, fidelity per product, numbers, and your honest read.
