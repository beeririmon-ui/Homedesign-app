# Brief: apply section 13.11 to MB0, in code (render-agent, bedroom, 2026-11-18)

## Why
master-designer ruled on the FB10 additions in section 13.11 of `docs/proposals/wm-master-bedroom-render-2026-11-17.md`. All the fixes are in code, at 0 tokens. QA's findings on the FB10 additions (`qa/reports/2026-11-18-master-fb10/README.md`) come with this brief. Fix any blocking finding in the same pass.

## The fixes (13.11)
1. **The planter (5ד):** keep Beige Large, SKU CJJT154204209IR, the same SKU as the living room. Use the living room's R5 rule against the wall ring at the same rows (y about 1050–1280):
   - the pot median 6–10 L* below the wall (aim for 8);
   - C* no more than the plaster C* + 1.5;
   - hue within ±10° of the plaster;
   - ribs and speckle visible at ×2.
2. **The ficus crown:**
   - **5ג:** C* ×0.80, and L* +3 in the mid-tones.
   - **Point 3:** remove the mirror beyond x 2641. Refill with leaves cloned from the crown interior (x 2470–2600), unmirrored, rotated ±15–25° and scaled 0.9–1.1. The fallback is a strip shift with a softened seam.
3. **The magazine holder:**
   - **5ב:** shift 40 px left, with its shadow.
   - **Point 4:** blank the cover text. Fill each cover with its own paper tone. Keep the page edges and one soft "photo" block per cover, with no letters, logo or faces.
4. **The dark shelf vase (5א):** remove the branch and its shadow. The plate shows through underneath.
5. **The dish:** 1.8 cm is accepted. No change.

Don't touch the sizes, the art placement, the carafe, the dish or the bedding.

## Inputs
- `assets/renders/master/warm-modern/stage1-2026-11-17/`, with `tools/fb10_compose.py`, the README FB10 chapter, and `layers/manifest.json`.
- The planter SKU photo: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/` (the file for 564d83ce, listed in `picks/manifest.json`). Read it with `python3.12 -I`, and never copy it into the repo.

## Outputs
- The same files, re-derived:
  - the defaults;
  - the frame;
  - the three throw variants;
  - the layers;
  - the manifests.
- **A README section "13.11":** the numbers per fix, RND2, the black point per variant (WM-G1), and the QA regions that changed.

## Acceptance
- RND2 is 0.
- Nothing outside the touched layers differs from the current output.
- The black point is within WM-G1 for all three variants.
- The planter numbers meet the R5 targets.
- No mirrored pattern remains at the crown edge.
- No text remains on the magazines.

## Fixed rules
- 0 tokens, no var2 sends, no commits, no keys.
- Supplier images stay in the scratchpad.
- Return a short Hebrew summary: the numbers per fix and the regions for QA.

## Manager's notes after QA (2026-11-18), which override the numbers above where they differ
- **The planter:** QA measured the pot about 15 L* below the wall ring at the same rows. The target is 8, so it must be **lightened** by about 7 L*, not darkened. The R5 rule decides, not an absolute L*. Chroma and hue are already in range; keep them there.
- **The magazine holder:** the right tube reaches x 2666, past the frame edge, so a 40 px shift leaves it only 0.006 from the edge. Apply the designer's intended margin: **47–60 px inside the frame edge, which is a shift of about 72–85 px.** Keep a clear overlap with the lamp base. If that shift hides the lamp base or crowds the planter, stop and report the numbers instead of choosing.
- QA's FB10 report: `qa/reports/2026-11-18-master-fb10/README.md`. Its other findings, MF-L1 and MF-L2, are low and stay in the backlog. Don't fix them now.
