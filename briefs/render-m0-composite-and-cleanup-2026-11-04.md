# Brief: M0 1.2 in code, and the cleanup of the four fixes (render-agent, 2026-11-04)

Two results came in today:
- **Your M0 1.2 renders** (board log 2026-11-04): 2,400 tokens, no frame passes lock_v2; the model enlarged the sofa ×1.19–1.3 and the table ×1.07–1.18 in every attempt, while the corner, window, armchair and pendant are close. This is the same bias as v6, v7 and v8: words and cut-outs don't fix it, code does (B1 r3 and W0-in r2 now pass lock_v2 after code fixes).
- **QA's G1 on your four code fixes** (`qa/reports/2026-11-04-retakes-fixes-g1.md` and `.json`): B1 r3 and W0-in r2 are locked; what fails is fill patches, one proportion, and global affines. QA confirmed you were right on the B2 vanity, the mirror head and the W0-in chair.

The M0 budget is spent. This brief is **0 var2 tokens**.

## Tasks
1. **M0 1.2 composite in code** on the reserve render `m0-v8b-r2` (the closest): the sofa group scaled about its floor-contact line to the round-5b clay box (about ×0.84), the coffee-table group about its near legs (about ×0.93), the holes filled as in `fix_v7.py` (wall rows, skirting and floor rows, rug texture), the contact shadows moved with the pieces. Then **M0p** (sofa about ×0.77) and **M0x** (one vertical affine, about 32 px). For each: `-fix.png`, `-fix.json`, lock_v2 (edges v3), the edge ratios, grading v4, and a 100% look at every seam before you call it done. Report honestly where a seam would need the one paid image-to-image pass (v8 route, 600 each); don't run it.
2. **The four fixes, per QA §§ (0 tokens):**
   - **B1 r3 fix:** re-fill the rectangular patches in the curtain linen above the fern (column-wise from the untouched folds, the linen's high-pass texture); the brush holder to the card's proportion (holder about 38% of the brush height, not 64%).
   - **W0-in r2 fix:** clean the dark-green clumps in the sea-grass basket weave and the dark rectangle in the skirting by the basket's base.
   - **K-girl-0 r2 fix:** one vertical affine to close the ~+0.9% stretch.
   - **B2 r3 fix:** the same global affine as B1 (scale +0.64/+0.74%); re-fill the light rectangle on the wall and the lumps in the limestone ledge by the planter. **Don't shrink the storage basket**: QA confirmed it is within ±15%.
3. **Grading fixes:**
   - The living-room wall target per **Bible 1.8: L 90–94** (your pipeline still judges M0/M0p against 92–95 from Bible 1.0). Re-grade M0 1.2 and M0p accordingly.
   - **C0 and S1'** to Bible 1.8.4 (BIB2): corridor walls L* 72–75, measured on the right wall at C0 plan (3.10, 15.80, 1.30) ≈ frame (0.86, 0.37) and S1' plan (3.10, 11.80, 1.30) ≈ frame (0.76, 0.36); the designer projected these with an assumed u0 0.50 for S1': **verify both points on the clay first** and report the real frame coordinates. The view at the corridor's end must stay the brightest point.
   - The protected areas in D1 as a silhouette mask instead of boxes (QA §4; ΔE 1.5–2.5 step at the box edges).
   - Write `regrade-v5-summary.json` with pass/fail against Bible 1.8.4 per frame.
4. **CB-0 from B1 r3 fix** (T-CBath): only after task 2 for B1 passes your own lock_v2 and a 100% look; recompose CB-0 from it with `pan_reproject.py` and report the overlap (pixels and ΔL) against the 2 px / ΔL ≤ 1 threshold.

## Fixed rules
- **No var2 calls.** New files only; pipeline scripts may change with the old behaviour under a flag. No commits.
- Return a short summary in Hebrew: M0/M0p/M0x lock and edge numbers after the composite and an honest seam verdict; the four fixes after cleanup; the grading-v5 table; CB-0's overlap; and the paid passes still needed, with cost.
