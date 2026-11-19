# Brief: the bathroom's second frame, B1 (render-agent, bath, 2026-11-19)

## Why
The owner approved the bathroom and its second frame (AP3-HOUSE2, read as yes, and FB11, in the digest). The target is 20 products for sale in the room. B2 has 11 unique products. B1 adds 7 from existing cards that passed the photo check. var2 is connected again.

## The spec (read in this order; later overrides earlier)
1. `docs/proposals/wm-bath-render-2026-11-17.md`: chapters 0א and 12, and the "B1, after approval 3" row of the render table.
2. `docs/proposals/wm-house-20-2026-11-19.md`:
   - chapter 2 (2.2 B1 contents, 2.5 count, 2.6 render plan);
   - chapter 8, which overrides 0–7;
   - the manager's rulings in 6.6א.
3. The photo check: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/house20-photo-check.json` and the sheet beside it. The SKU photos are in `picks/img/`. Read them with `python3.12 -I`, and never copy them into the repo.

## The task
1. **The clay of B1,** from the bath clay already in `assets/blockout/house/framing/wm-bath-2026-11-17/`. The camera CB is at yaw −22, as in the house plan. It is not a new camera.
2. **The plate:** seedream, with B2 as the reference (same house, same light, same black point). Use the bath grade curve (`plate-grade.json`, `grade_plate.py`) and WM-G1.
3. **The defaults,** as layers per RND2:
   - the bath mat, Return Frame Khaki, the sample slot;
   - the toilet-paper stand;
   - the bin;
   - the brush;
   - the candle cup;
   - the reed diffuser;
   - the sill vase, black jar 30, neutral black and not warmed;
   - the B1 sconce lit, the same SKU as the mirror pair.
   
   The stool, the small print and the shelf planter are still gaps. Leave their places empty. They come as a later pass, once sourced.
4. **The sample slot:** the mat in 3 variants:
   - Khaki (the default);
   - Beige (it passed);
   - the third variant line from 8.6 if it exists, or else the closest card that passed.
   
   Colour-only variants may be done in code if they stay true to the SKU photo. Say which you did.
5. **The checks:**
   - RND2 is 0 outside the masks;
   - shadows sit one z below their product;
   - the black point is within WM-G1;
   - the same house as B2 at ×1.
   - Record the counts.

## Money
- **The plan:** about 3,300 at list prices (2.6), within HOUSE1, HOUSE2B and FB11.
- **Before every send:** `var2_estimate_cost`.
- **If it runs over 4,100:** stop and report.
- **Fixes:** only what is visible at ×1–×2, or a mismatch with the product (EFF1).

## Outputs
- `assets/renders/bath/warm-modern/b1-2026-11-19/`:
  - the clay;
  - the plate;
  - `b1-defaults.png` and `-frame.png`;
  - the variants;
  - `layers/`, `shadows/`, `light/` and a manifest;
  - `jobs.json`;
  - a README with the money table and the regions for QA.
- The prompts go in `assets/prompts/`, and `assets/manifest.json` is updated.

## Fixed rules
- No commits, no keys.
- Supplier images stay in the scratchpad.
- Don't edit a binding document or `data/`.
- If var2 asks for re-auth, stop and report. Never ask for codes.
- Return a short Hebrew summary: the money, the count in B1 and in the room, what was done in code, and the regions for QA.
