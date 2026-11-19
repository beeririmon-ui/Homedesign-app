# Brief: the hall's first products, HT2 and HDx2 (render-agent, hall, 2026-11-19)

## Why
The owner wants at least 20 products for sale in every tour room (FB11). Today the entrance hall shows almost none. master-designer's plan is in chapter 4 of `docs/proposals/wm-house-20-2026-11-19.md`, and chapter 8 overrides it. Under that plan, the HT2 product pass and the HDx2 wall light can go now. The HE frame waits for the 1.3.9 registration and for sourcing lines 15, 20 and 22.

## The products (all passed the photo check; chapter 8.1 gives the right SKUs)
- **The wall light:** `wall-sconce-aliexpress-travertine-walnut-cylinder-332886-hall`, **version A (…270), the smooth cylinder** (8.2), lit with its up-and-down beams on the stone wall.
- **The walnut pegs:** `wall-hooks-cj-walnut-block-peg-set-of-4`, ordered by code `CJJJJTJT09286-Black`, on the stone at Y 7.25–7.65 and Z 1.60–1.66 (6.7).
- **The waffle throw:** `bench-throw-cj-cotton-waffle-blanket-150x200`, Khaki. Use the new fold of about 37×40×7–8, which leaves about 40 cm of walnut bare on the bench. QA checks that the thickness reads 7–9 cm in the frame.
- **The basket:** `basket-cj-jute-cotton-rope-cylinder-30-hall`, in **cream, `CJYD195774302BY`, not jute**. Render it from the SKU photo only; gallery images 5–8 show a different basket. It goes under the seat, centred at Y 7.10.

## The task (chapter 4.7, rows 3 and 4)
1. **HT2,** as islands (nano mask edits, one or two): the wall light with its beams, the pegs, the throw and the basket. Do this on the approved still in `assets/renders/hall/warm-modern/hall-2026-11-18/ht2.png`, which passed QA. Keep the bench, the stone and the light untouched outside the masks (RND2), and keep the black point and the grade from `levels.json` and `tools/tone.py`.
2. **HDx2:** carry the wall light over from HT2 in code, by a homography on the stone plane, if it passes at ×2. Otherwise one nano edit. The right lamp is missing for now (line 15). That's a known and accepted temporary asymmetry.
3. **D0:** no change.
4. **Layers and shadows** per RND2, with the light layers in screen and shadows one z below.

The arrival must not break. The products are layers that appear only at rest and lift before any move. The clips that passed QA stay as they are.

## Inputs
- The hall stills folder and its README.
- The SKU photos in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`, with `picks/house20-photo-check.json`. Read them with `python3.12 -I`, and never copy them into the repo.
- The cards in `data/products/entrance/`.

## Money
- **The plan:** about 400–800, or 1,200 at most.
- **Before every send:** `var2_estimate_cost`.
- **If it runs over 1,200:** stop and report.
- If var2 asks for re-auth, stop and report. Never ask for codes.

## Outputs
- `assets/renders/hall/warm-modern/hall-products-2026-11-19/`:
  - `ht2-products.png` and `-frame.png`;
  - `hdx2-products.png` and `-frame.png`;
  - `layers/`, `shadows/`, `light/` and a manifest;
  - `jobs.json`;
  - a README with the money, the count and the regions for QA.
- The prompts go in `assets/prompts/`, and `assets/manifest.json` is updated.

## Fixed rules
- No commits, no keys. Supplier images stay in the scratchpad.
- Don't edit a binding document, `data/`, or the approved hall stills themselves.
- **Another render-agent is working on the bedroom MB1.** Don't touch its files.
- **The disk is tight** (about 2GB free). Keep scratch files small, and delete them when done.
- Return a short Hebrew summary: the money, the products added, what was done in code, and the regions for QA.
