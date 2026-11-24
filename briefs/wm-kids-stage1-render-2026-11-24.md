# Brief: the warm-modern boy's and girl's rooms, stage one (render-agent, 2026-11-24)

## Why
The owner approved both kids' rooms (AP2-NEW, 2026-11-20, in the digest), including the boy's olive band, an approved exception to "green only from plants", for warm-modern only. They are part of the whole house at 20+ products per room (FB11). This is stage one: for each room, the empty room, the defaults that passed the photo check, and the sample slot with its variants. After QA, the owner sees them for approval 3.

## The spec (read in this order; later overrides earlier)
1. **`docs/proposals/wm-kids-rooms-render-2026-11-19.md`:**
   - **chapter ד overrides א–ג**, especially ד.2 (the corrected defaults), ד.4 (the sample slot), ד.5 (the counts) and ד.8 (what changes in the render);
   - the render plans are א.6 and ב.6, and the rejection lists are א.7 and ב.7.
2. The kids' chapters in `docs/design-bible/warm-modern.md` (1.1), including the safety rules (ד.7).
3. **The method and the same house:** the house plan (`docs/house-plan.json`) and the clay method of the other rooms under `assets/blockout/house/framing/`. The approved stills of the bedroom, the work room and the living room are the references for material and light.
4. **The products:**
   - the cards, synced: the default SKU and `room_variants` "warm-modern.kids-boy" / "warm-modern.kids-girl" give the exact variant;
   - the SKU photos in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/new-rooms-photo-check.json` and `picks/ap2-sheets.json`. Read them with `python3.12 -I`, and never copy them into the repo.

## The task
1. **The clay** of K-boy and K-girl. The two rooms are siblings with the same shell and differ in the band, the palette and the objects. Save the clay in `assets/blockout/house/framing/wm-kids-2026-11-24/`.
2. **The plates:** render K-boy with seedream. Derive K-girl from it if the plan allows it (the designer budgeted the girl's room on the boy's plate). Otherwise give K-girl its own plate. Use the WM-G1 black point.
3. **The defaults** that passed the photo check, as mask edits and layers per RND2. Use crop edits around enlarged placeholders: the kitchen found they keep place and size much better. Leave the gap slots empty. Fix sizes and colours in code against the card and the photo.
4. **The sample slot:** the folded throw, in 3 variants per room per ד.4. Use colour-only variants in code where the listing photos are recolours of one scene.
5. **The safety rules in the frame:** no small loose parts within reach, no cord near the bed, and the sill empty.
6. **The checks:**
   - RND2 is 0 outside the masks;
   - shadows sit one z below their product;
   - light layers use screen;
   - the black point is within WM-G1.
   - Count once per room, and also by V7Q6.

## Money
- **The plan:** about 5,050–9,700 for both rooms (א.6 and ב.6). Aim for the low end by sharing the shell.
- **Before every send:** `var2_estimate_cost`.
- **Stop:** report above 9,700.
- **Fixes:** only what's visible at ×1–×2, or a mismatch with the product (EFF1).
- If var2 asks for re-auth, stop and report. Never ask for codes. **Write `jobs.json` after every send,** so a restart can't lose the ledger.

## Outputs
- `assets/renders/boy/warm-modern/stage1-2026-11-24/` and `assets/renders/girl/warm-modern/stage1-2026-11-24/`, each with:
  - the plate;
  - the defaults and their frame;
  - the variants;
  - `layers/`, `shadows/`, `light/` and a manifest;
  - `jobs.json`;
  - a README with the money, the count, the code fixes and the regions for QA.
- The prompts go in `assets/prompts/`, and `assets/manifest.json` is updated (additions only).

## Fixed rules
- No commits, no keys. Supplier images stay in the scratchpad.
- Don't edit a binding document or `data/`.
- Never run `git stash`, `git checkout` or `git reset`.
- **The disk is tight** (about 2.7GB free). Keep scratch files small, delete them as you go, and avoid large `.npy` files.
- **Save your work as you go.** The container and the rate limits have stopped agents before.
- Return a short Hebrew summary: the money, the count per room, what was done in code, and the regions for QA.
