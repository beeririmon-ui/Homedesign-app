# Brief: R6, code fixes after QA R5 and the designer's eye (render-agent, 2026-11-12, 0 tokens)

**The sources:**
- QA: `qa/reports/2026-11-11-wm-tool-phase2-r5.md` plus `.json`, with its crops and tools.
- The designer's eye: `docs/proposals/wm-phase2-r5-eye-2026-11-11.md`.
- **The folder:** `assets/renders/living-room/warm-modern/phase2-2026-11-10/`. Start from `layers/manifest-r5.json`.

## The fixes, all in code, with no var2
1. **The default curtains move to 180502** (the designer's decision): flip the manifest and recompose the default scenes for sets B, A and C. 554205 drops to variant 2.
2. **Curtain 554205 (now variant 2):** recolour it to the designer's new targets, which are **relative to 180502 under the same mask, including L*** (§1 of the eye doc). QA notes that target 4 was measured on a ring that is 23% curtain; use a clean wall ring.
3. **The default vase and vase 2:**
   - re-cut both from the raw renders, because the cut lost the lit side, about 21% of the width;
   - recolour vase 2's a* and b* toward the card's neutral charcoal, per the designer's §6.
4. **Pendant 2:**
   - re-cut the ceiling canopy as a whole disc centred on the cord (`canopy_cut()`);
   - clean the polygonal right contour;
   - remove the brown dot on the cord;
   - **make the cord black, as on the card**;
   - clean the stripes on the paper in code. The 40 SKU photo shows no rings, so it should read smooth pleats.
5. **Framed art 2:** fix the stepped seams on all six rails, and remove the three white dots in the black of print 1.
6. **The magazine holder's rods:** clean the dark lower edge seen at ×2.
7. **Not now:**
   - **the planter's colour:** waiting on the designer, because the pre-approved darkening would be 25–29 L*;
   - **the true curtain lengths:** waiting on the designer's instruction, which is on its way;
   - **the table group:** waiting on the new coordinates in the slots file.

## Acceptance
- **Each layer:**
  - one v3c grade;
  - the frozen shadow recipe (`shadow_one`);
  - swap-diff 0;
  - recomposite p99.9 ≤2 and max ≤6;
  - the full cross of combinations passes.
- **The output:**
  - `layers/manifest-r6.json` plus its verify script;
  - before/after crops at 100% and ×4;
  - a sheet;
  - asset manifest entries in a separate JSON.

## Fixed rules
- No var2, no commits.
- New files only.
- Return a short Hebrew summary with the numbers.
