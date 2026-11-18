# Brief: QA on the warm-modern master bedroom MB0, stage one (qa-agent, 2026-11-18)

## Why
The owner approved the bedroom picks (HOUSE2). render-agent built MB0 with the defaults on the plate that passed QA, through rounds 3–7, 3,700 tokens in all. The bed is styled as in the magazine frame fix6: pillows leaning on the headboard, the throw over the front half (designer 12.7). Many fixes were done in code. The Pecan throw stays from r4, with its fringed ends hidden under the duvet's sides (manager: hidden by styling, not missing). The sample slot is the throw, in three variants: Pecan (default), Flax brown (one mask edit, then a hue correction) and Clay (in code). This is the frame the owner sees for approval 3, so this is the full QA of stage one.

## Inputs
- **The renders:** `assets/renders/master/warm-modern/stage1-2026-11-17/`:
  - `mb0-defaults.png` and `-frame.png`, and `mb0-variant-throw-flax.png` and `mb0-variant-throw-clay.png` with their frames;
  - `layers/`, `shadows/`, `light/`, `layers/manifest.json`;
  - `mb0-defaults-compose.json`, `mb0-throw-variants.json`, `plate-compose.json`, `plate-gain-field.png`;
  - `mb0-defaults-qa-sheet.jpg`, `jobs.json`;
  - the README, rounds 3–7, with render-agent's notes for QA and the canvas regions.
- **The spec:** master-designer's `docs/proposals/wm-master-bedroom-render-2026-11-17.md`. Chapter 12 overrides the rest, in particular 12.2, 12.3, 12.6–12.9. Also chapter 7 (the rejection list, as amended by 12.7) and chapter 9 (what QA checks).
- **The products:** the cards in `data/products/master/` (and the pool cards chapter 12 names). The SKU photos are supplier images in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`. Read them there and never copy them into the repo.
- **The plate's QA:** `qa/reports/2026-11-17-master-plate/`. The bath's stage-one QA is a method reference: `qa/reports/2026-11-18-bath-b2/`.

## What to check (0 tokens)
1. **Fidelity to each product:** shape, colour (R5 method, on lit areas) and size against the clay and the card, for every product in the frame and for each throw variant.
   - The products: the bedding V1, the Caramel Pairs pillowcases, the Milk Tea cushion, the Pecan throw, the travertine cone sconces (on), the candle holders (a pair, 11 cm, matte travertine), the walnut tray, the bottle, the sill vase, the curtains and the floor lamp (shade 43, base about 26, brass).
   - The designer accepted the duvet tone by eye (12.9). Check only that it isn't neutral grey or white.
2. **The rejection list,** as amended by 12.7–12.9:
   - the lamp-pole exception was cancelled, because the base is now visible;
   - the curtain falls in front of the sill;
   - the dish slot is empty;
   - no picture above the bed.
3. **The composition** of 6.3 as amended in 12.6:
   - the curtain against the nightstand ≥ 0.02 at sill height;
   - the shade's distance from the margin and from the right cone;
   - the count (about 8).
4. **The layers (RND2):**
   - recompositing reproduces each output exactly;
   - nothing outside the masks differs from the plate;
   - shadows one z below their product;
   - the light layers in screen;
   - swapping the throw changes only the throw;
   - MP-I1 and MP-I2 are respected;
   - the black point is within WM-G1 for each variant.
5. **At ×1–×2 as a frame:**
   - the round-6 regions: the fold band, the grid filtered out, the duvet drop and its seam and corners, the throw's soft front fold;
   - the Flax and Clay variants: no "painted" look, and the weave and fold shadow readable;
   - edges and halos;
   - whether it reads as the same house as the living room, the hall and the bathroom, at the magazine level (FB5), and lived-in (FB6).

## Outputs
- `qa/reports/2026-11-18-master-mb0/README.md`: pass or fail per item, with numbers. Evidence images only when needed; scripts in the scratchpad.
- Low findings go to `status/backlog-low.md`.
- A status line: "עבר QA (שלב 1; לבעלים לאישור 3; לא לאתר לפני רישום 1.3.9)", or the blocking findings. Mark which need a model, and note that the run's budget is spent, so a model fix is a question for the manager.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- Return a short Hebrew summary: the five items, pass or fail with numbers, and whether MB0 stage one passed QA.
