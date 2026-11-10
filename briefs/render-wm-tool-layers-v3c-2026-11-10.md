# Brief: the warm-modern tool's layers in the v3c grade (render-agent, 2026-11-10)

**Background:**
- Phase 1 of the warm-modern tool pilot is approved: owner approval 3 (AP3-WM), recorded in `status/decisions.json`, and QA in `qa/reports/2026-11-07-pilot-phase1-v3c-verify.md`.
- What passed is the **v3c display files**: `shell-furniture-v3-graded-v3c.png` and `composite-set-{A,B,C}-v3-graded-v3c.png`.
- The site needs them as **separate layers** for the tool: a base, plus a swappable cushion layer per set.
- The existing layers (`layers/cushions/set-*.png`, `fixed-furniture.png`, `fixed-furniture-shadow.png`) are from before the v3c grade, and the site currently shows an old draft.

## The task, code only (0 tokens)
Folder: `assets/renders/living-room/warm-modern/pilot-phase1-2026-11-07/`. Build `layers-v3c/` there:
1. **`base.png`:** the shell, the fixed furniture and their shadow, in the v3c grade. This is the approved `shell-furniture-v3-graded-v3c.png` itself, or something identical to it.
2. **`cushions-set-{A,B,C}.png`:** RGBA layers in the v3c grade. Each holds the products of its set (the cushions, the throw) and the set's shadow on the base.
   - A shadow that only darkens may be a separate layer (`cushions-set-X-shadow.png`, multiply) or part of the alpha. Your choice; describe it in the manifest.
3. **`manifest.json`:**
   - the layer order and the blend of each layer;
   - the size;
   - the default set, **B**, per `data/selections/living-room.warm-modern.json`;
   - the card ids of each set's products;
   - the source of each file.

Choose the method yourself. The natural one is to cut from the approved composites with the masks (`masks/`, `cushion-polys.json`), so you don't grade each layer separately. Grading a layer before compositing it gives a different result at soft edges and in shadows.

## Acceptance
- **Recompositing:** base + set X, in the manifest's order and blend, reproduces `composite-set-X-v3-graded-v3c.png`.
  - The pixel difference is at most 2 levels per channel at p99.9 and at most 6 at the maximum, for each of the three sets.
  - Report the numbers.
- **Swap-diff:** set A ↔ B ↔ C changes 0 pixels outside the union of the masks and shadows of the two sets.
- **The verification script:** keep it in the folder, so QA can run it again.
- **Not in scope:** web encoding (WebP/AVIF, sizes) is frontend-dev's.

## Fixed rules
- **No var2.**
  - It currently requires authentication, and this task doesn't need it anyway.
  - If you think something can't be done without a paid pass, stop and report.
- New files only. Don't change the approved files, and no commits.
- Return a short Hebrew summary: the method, the recompositing numbers, the swap-diff, and any trouble you met.
