# Brief: warm-modern tool phase 2, the reserve passes R1 and R2 (render-agent, 2026-11-11)

**The background:** steps 0–3 of phase 2 ran at 1,950 tokens (`briefs/render-wm-tool-phase2-2026-11-10.md`).
- **The output:** `assets/renders/living-room/warm-modern/phase2-2026-11-10/`. Read in it:
  - `phase2-steps1-3-sheet.jpg`;
  - `layers/manifest.json`;
  - `jobs.json`;
  - `step0/f3-checks.json`;
  - `lock-and-grade-check.json`;
  - the prompts in `assets/prompts/warm-modern-phase2-2026-11-10/`.
- **What went in as layers:** the rug, vase, prints, accent sconces, candle holders and floor lamp.
- **What failed fidelity:** six defaults.
  - the curtains: twice too wide, covering glazing (WMC7);
  - the planter and basket: the basket beside the planter, not in front of it;
  - the magazine holder: taller than it is wide, while the card is 35×27.5;
  - the bowl: at the wrong end of the table;
  - the pendant: about 66 cm, while the card is 50.

**The manager approves the reserve, 1,300, within PH2-WM (the owner, 2026-11-10, up to 9,740).**

## The passes
The lesson from steps 2–3: seedream with 6 products and 8 references didn't hold the geometry. So: fewer products and fewer references per pass, on the current scene (base + the layers already in + set B).

| # | Products | Model | ≈ tokens |
|---|---|---|---|
| R1 | Curtains (inside the WMC7 envelope, never over glazing), planter + basket together (the basket **in front of** the planter, per the plan), magazine-holder | seedream-5-pro i2i 2K | 650 |
| R2 | The bowl (at the step-0 position (0.72, 1.94)) and the pendant (50 cm per the card, at its height in the plan) | seedream-5-pro i2i 2K | 650 |

## How
- **Place-holders:** hand the model your clay place-holders at the exact sizes and positions. Compute them from the cards and from house plan 1.3.5, the same way you did in step 0.
- **References:** one card crop per product.
- **Sizes and placement:** if the model still misses a size, you may scale in code (as you did with the sconces ×0.80 and the candle holders ×0.83). Any **placement** miss is a fidelity failure, not something to fix in code.
- **The magazine holder:**
  - render the **Orange** SKU (cognac straps) as the selection describes, not the Black on the card;
  - record the SKU in the manifest;
  - master-designer is confirming it in parallel.
- **Before each job:** run `var2_estimate_cost`, and stop if it differs by more than 10%.
- **If a pass fails again:** don't run a third. Report.

## Acceptance (unchanged from the phase 2 brief)
- Every product is its own layer, cut from the graded composite. One v3c grade.
- Swap-diff 0 outside the product and its shadow.
- Recomposite p99.9 ≤ 2, max ≤ 6.
- The shell lock holds.
- Fidelity to the card: shape, colour, proportions, size and position.
- **The output:** update the same `phase2-2026-11-10/` folder with new files only, and keep step 1–3 files as they are. Write a new layers manifest version and a full default scene sheet with set B (all 12 defaults). Put the manifest entries in a separate JSON for the manager.

## Fixed rules
- If var2 asks for authentication, stop and report.
- Supplier images stay in the scratchpad and var2 only.
- New files only. No commits.
- Return a short Hebrew summary: the tokens, fidelity per product, the numbers, and your honest read.
