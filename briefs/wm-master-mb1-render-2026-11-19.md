# Brief: the bedroom's second frame, MB1 (render-agent, bedroom, 2026-11-19)

## Why
The owner approved the bedroom's second frame (AP3-HOUSE2, read as yes, and FB11). The target is 20 or more products for sale in the room. From existing cards, the room reaches 22. motion-agent checked the camera against FB8. The camera passes, and the move MB0 → MB1 has a legal forward path (B). The clip comes at the very end with the other transitions (FB11). var2 is connected.

## The camera (the manager's ruling on the motion check)
- **Position and lens:** (1.60, 21.20), yaw 33.7, 24 mm.
- **Height Z 1.05, per U14, not 1.20.** The 1.20 in 13.8 is withdrawn, so no exception is needed. The frame keeps the bench, the rug and the right group (`scratchpad/mb1-check/mb1-height-compare.jpg`).
- **Tilt 0,** framed by shift only, with v0 0.418 (U14).
- **Canvas:** with overscan like MB0, because turns in place of 21° and more happen around it.
- The full numbers are in `docs/proposals/wm-mb1-forward-check-2026-11-19.md`.

## The spec (later overrides earlier)
1. `docs/proposals/wm-master-bedroom-render-2026-11-17.md`, chapter 13 (13.6–13.10 for MB1), and 13.11.
2. `docs/proposals/wm-house-20-2026-11-19.md`:
   - chapter 1 (1.2 the MB1 list, 1.3 the bench as plan B, 1.5 the render plan);
   - chapter 8;
   - 6.6א.
3. The MB0 render, for the products' look, sizes and tones as they passed QA: `assets/renders/master/warm-modern/stage1-2026-11-17/`, with its README and the QA reports `qa/reports/2026-11-18-master-mb0/` and `2026-11-18-master-fb10/`.
4. The SKU photos in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/manifest.json` and `house20-photo-check.json`. Read them with `python3.12 -I`, and never copy them into the repo.

## The task (as in 1.5)
1. **The clay** of MB1, from the bedroom clay in `assets/blockout/house/framing/wm-master-2026-11-17/`, at the camera above.
2. **The plate** (seedream), with MB0 as the reference: the shell, the bed, the nightstands, the shelf, and the walnut bench (plan B: drawn, fixed, not for sale), with the lamps off. Same house, same light, same black point (MP-I1, MP-I2, WM-G1).
3. **The layers (nano, mask edits):**
   - the bed textiles, identical to MB0: the bedding, the pillowcases, the cushion and the Pecan throw;
   - the right group: the lamp, the planter, the magazine holder (the 13.11 version), the carafe and the candle holders;
   - the wall group with blank canvases (the prints go in by code, as in MB0, and art A stays ×1 only);
   - the floor: the rug, the waffle throw on the bench and the basket under it.
4. **The checks:**
   - RND2 is 0 outside the masks;
   - shadows sit one z below their product;
   - the black point is within WM-G1;
   - every product matches its MB0 look and its SKU photo;
   - the same room as MB0 at ×1.
   - Record the count for the room, each product once, in the frame where it's biggest.

## Money
- **The plan:** about 3,050 at list prices, 2,650–4,100, within HOUSE1, HOUSE2B and FB11.
- **Before every send:** `var2_estimate_cost`.
- **If it runs over 4,100:** stop and report.
- **Fixes:** only what is visible at ×1–×2, or a mismatch with the product.

## Outputs
- `assets/renders/master/warm-modern/mb1-2026-11-19/`:
  - the clay;
  - the plate;
  - `mb1-defaults.png` and `-frame.png`;
  - `layers/`, `shadows/`, `light/` and a manifest;
  - `jobs.json`;
  - a README with the money table and the regions for QA.
- The prompts go in `assets/prompts/`, and `assets/manifest.json` is updated.

## Fixed rules
- No commits, no keys. Supplier images stay in the scratchpad.
- Don't edit a binding document or `data/`.
- **Another render-agent is working on the bath (B1) in parallel.** Don't touch its files.
- If var2 asks for re-auth, stop and report. Never ask for codes.
- Return a short Hebrew summary: the money, the room count, what was done in code, and the regions for QA.
