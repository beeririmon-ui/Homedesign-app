# Brief: the warm-modern work room, stage one (W0) (render-agent, 2026-11-20)

## Why
The owner approved this room's design and picks (AP2-NEW, 2026-11-20, in the digest) as part of the whole house at 20+ products per room (FB11). This is stage one in CLAUDE.md terms: the empty room, the defaults, and the sample slot with its variants. After QA, the owner sees it for approval 3.

## The spec (read in this order; later overrides earlier)
1. `docs/proposals/wm-work-render-2026-11-19.md`: all chapters, with **chapter 10 (after the photo check) overriding 1–9**. The render plan is chapter 6, as amended by 10.7. The rejection list is chapter 7.
2. `docs/design-bible/warm-modern.md`: the house language. master-designer is entering this room's chapter in parallel; the proposal in chapter 1 of the document is the approved text.
3. The house plan and the clay method: `docs/house-plan.json`, and the bedroom's and bath's clay folders under `assets/blockout/house/framing/`.
4. The SKU photos in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/new-rooms-photo-check.json` and `picks/ap2-sheets.json` (the final defaults per room). Read them with `python3.12 -I`, and never copy them into the repo.
5. The cards in `data/products/`. The cards were synced today: the default SKU and `room_variants` "warm-modern.<room>=<sku>" give the exact variant to render.

## The task
1. **The clay** (W0), from the plan and the document's chapter 2. Save it in `assets/blockout/house/framing/wm-work-2026-11-20/`.
2. **The plate:**
   - seedream, with the approved living room and hall stills as references for material and light, so it's the same house;
   - WM-G1 black point;
   - MP-I1 and MP-I2 if needed, as in the bedroom.
3. **The defaults** that passed the photo check, as mask edits and layers per RND2. Leave the gap slots empty; they come later as a pass, once sourced. Fix sizes and colours in code against the card and the photo, as was done in B1 and MB1.
4. **The sample slot:** the framed art above the desk (386242 works 08, 01 and 02, composed in code). Do colour-only variants in code where they stay true to the SKU photo.
5. **The checks:**
   - RND2 is 0 outside the masks;
   - shadows sit one z below their product;
   - light layers use screen;
   - the black point is within WM-G1.
   - Count the products the manager's way: once per room, where biggest. Give the V7Q6 count too.

## Money
- **The plan:** about 3,050 (2,650–4,100); stop above 4,100.
- **Before every send:** `var2_estimate_cost`.
- **Fixes:** only what's visible at ×1–×2, or a mismatch with the product (EFF1).
- If var2 asks for re-auth, stop and report. Never ask for codes.

## Outputs
- `assets/renders/work/warm-modern/stage1-2026-11-20/`:
  - the plate;
  - the defaults and their frames;
  - the variants;
  - `layers/`, `shadows/`, `light/` and a manifest;
  - `jobs.json`;
  - a README with the money, the count, the code fixes and the regions for QA.
- The prompts go in `assets/prompts/`, and `assets/manifest.json` is updated (additions only).

## Fixed rules
- No commits, no keys. Supplier images stay in the scratchpad.
- Don't edit a binding document or `data/`.
- **Another render-agent is working on another new room in parallel.** Touch only your own folders.
- **Never run `git stash`, `git checkout` or anything else that touches files outside your folders.**
- **The disk is tight** (about 2GB free). Keep scratch files small, and delete them when done.
- Return a short Hebrew summary: the money, the count, what was done in code, and the regions for QA.
