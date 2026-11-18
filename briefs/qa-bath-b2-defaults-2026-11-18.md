# Brief: QA on the warm-modern bathroom B2, stage one (qa-agent, 2026-11-18)

## Why
The owner approved the bath picks (HOUSE2). render-agent rendered B2 on the plate that passed QA:
- **The defaults:** seedream, 650, with the sprig fixed by one nano edit at 400.
- **The linen hand-towel variant:** nano at 400, rebuilt on the caramel geometry with the SKU colour.
- **The layers:** products, shadows and light.

After the designer's rulings, several fixes followed in code (0 tokens):
- product sizes brought back to the clay;
- the caramel tone matched to the SKU photo;
- the ring scaled to its SKU size, with the towel refitted;
- the two sconce washes balanced to 0.90.

This is the frame the owner sees for approval 3, so this is the full QA of stage one. It covers the products against the real products, the layers and the frame as a whole.

## Inputs
- **The renders:** `assets/renders/bath/warm-modern/stage1-2026-11-17/`:
  - `b2-defaults.png` and `-frame.png`, `b2-variant-linen.png` and `-frame.png`;
  - `layers/`, `shadows/`, `light/` and `layers/manifest.json`;
  - `b2-defaults-checks.json`, `b2-defaults-compose.json`, `plate-grade.json`;
  - `jobs.json`, and the README (sections "סבב 4" and "תיקון 0א": render-agent's notes for QA).
- **The spec:** master-designer's `docs/proposals/wm-bath-render-2026-11-17.md`:
  - chapter 0א (all the rulings, including "הכרעות על ברירות המחדל של B2", the ring, the washes, the conditions for QA);
  - chapter 5 (the sample slot), chapters 7–9 (the brief, the rejection list, what QA checks).
- **The products:** the cards in `data/products/bath/` and `data/products/planter/`, as listed in `data/selections/bath.warm-modern.json`. The SKU photos are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/` (supplier images: read them there, never copy them into the repo).
- **The plate's QA:** `qa/reports/2026-11-17-bath-plate/`.

## What to check (0 tokens)
1. **Fidelity to each product:** shape, colour (R5 method), material and size against the clay and the card, for every product in the frame.
   - The products: the sconce pair (Style B 8×8×16), the curtain, the niche set, the soap dispenser, the cup, the vase, the planter, the ring (16 cm) and the caramel towel 2pc.
   - Repeat for the linen variant.
   - A product that doesn't match is a failure, whatever its beauty.
2. **The rejection list** (chapter 8), with the designer's accepted deviations in 0א (the sprig, the towel length, the curtain width, the short beam, the pothos, the curtain against the niche at 0.003).
3. **The composition numbers** the designer's rulings require: the curtain against the corner, the ring diameter ±5%, the towel against the vanity ≥ 0.025, no towel in the air or gap at the ring, and the wash ratio 0.8–1.25.
4. **The layers (RND2):**
   - every layer composited over the plate reproduces `b2-defaults.png`;
   - nothing outside the masks differs from the plate;
   - each product's shadow is one z below it;
   - the light layer in screen mode at z 90;
   - swapping caramel for linen changes only the towel;
   - the grade curve was applied through `grade_plate.py apply`.
5. **At ×1–×2 as a frame:** cutout edges (the pothos leaves, the towel, the ring), halos, a thin highlight line over the sconce blocks, the planter base and its shadow, the small dark points at the vase base, the light line at the linen towel's lower left, and the ring base's top edge. Does it read as the same house as the living room, the hall and the bedroom, at the level of the magazine frame (FB5)?

## Outputs
- `qa/reports/2026-11-18-bath-b2/README.md`: pass or fail per item, with numbers. Evidence images in the same folder only when needed; scripts go in the scratchpad.
- Low findings go to `status/backlog-low.md` (EFF1.1).
- A status line: "עבר QA (שלב 1; לבעלים לאישור 3; לא לאתר לפני רישום 1.3.9)", or the blocking findings.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- Return a short Hebrew summary: the five items, pass or fail with numbers, and whether B2 stage one passed QA.
