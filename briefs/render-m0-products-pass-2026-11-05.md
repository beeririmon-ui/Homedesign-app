# Brief: M0 1.2, one product pass on the seedream frame (render-agent, 2026-11-05)

**Decision:** M0S2 = (a), owner, 2026-11-05 (studio rules ז; review `docs/render-m0-1-2-review-2026-11-05.md` §6).

**Correction 2026-11-06 (master-designer; brief `briefs/designer-shelf-styles-holder-2026-11-06.md`, Task 1):**
- **Magazine holder moved** to (−0.54, 2.52), box [0.335, 0.421, 0.848, 1.0]. At (−0.95, 1.90) it covered the lower ~38% of the basket (reference 2). The basket does not move.
- **Pouf box** at filled height 36 is [0.905, 1.0, 0.956, 1.0], not v 0.915.
- **Boxes are in uv only.** The px column is removed: its values did not match the canvas (render-agent's finding). Convert with x = u×2736, y = v×1539 if you need pixels.
- **Reference 2** must be rebuilt with the holder proxy at the new point before paying.

**Geometry:**
- House plan 1.2.5: `cameras.M0.frame_est_1_2.products_back_1_2_5` (holder, pouf box), and `products_back_1_2_4` for the basket, floor lamp and pouf point.
- `data/slots/living-room.json` 1.8.

**Budget:**
- seedream-5-pro image-to-image: **650 tokens**.
- Reserve 650, only if the lock fails, and only with the manager's approval.

**Rules:** no other render, no commit.

## Input
- **Base image:** `assets/renders/living-room/nordic/v9/m0-1-2-shell-seedream-fix.png`, the composite before grading (2736×1539). Not the graded v5.
- **Clay reference:** `assets/blockout/house/framing/round5b/M0.png`.
  - Add the four product proxies at their plan points before using it as reference 2.
  - Proxies: holder 45×32×40, basket Ø35×39 with handles, floor lamp with a Ø36 drum on a pole about 152 high, and a Ø45 ball about 36 high.

## What goes in (one pass, all together)
Boxes are [u0, u1, v0, v1] on the 16:9 frame, in uv only (0–1 on each axis). The reference image for each product is the card's `images.urls[0]` unless stated.

| Slot | Card (test default) | Reference image | Plan point and size | Box (uv) | Notes |
| --- | --- | --- | --- | --- | --- |
| magazine-holder | `magazine-holder-cj-felt-log-basket` (7.0) | `…/2026/02/11/05/4f328aff-…_fine.jpeg` | **(−0.54, 2.52)** on the rug, in front of the gap between the armchair and the coffee table's front-left corner (1.2.5). 45×32×40 charcoal felt, light-wood handles, cognac tabs. **Long side pointing at the camera** (along the 25° line of sight). 3 fillers: folded magazines with no readable text | **[0.335, 0.421, 0.848, 1.0]** | Top rim whole (back-top at v 0.848); the body is **cut decisively** by the bottom edge (~55% of the holder visible). 0.026 below the basket's bottom: the two must not touch or line up. ~0.02 from the armchair's right contour, ~0.02 from the table's front-left corner. Does not touch the runner |
| basket | `basket-cj-jute-rope-cylinder` (8.5) | `…16d626dd-…_trans.jpeg` | (−1.70, 0.75), off the rug, in the back-left corner. Straight jute-rope cylinder Ø35, body 39, rope loop handles +9 | [0.350, 0.401, 0.686, 0.822] | Free-standing on the floor, its base fully visible: the planter is **empty** in the test (no pot, no olive tree). 0.03 right of the back curtain stack, 0.068 left of the sofa's left arm, below the wall round (does not touch it) |
| floor-lamp | `floor-lamp-cj-black-drum-linen` (6.5, **test only, not approved for sale**) | `…/2025/08/05/06/fbdc89df-…jpg` | Base (1.52, 0.20). Straight matte-black pole, round base ≤26. **Oat linen drum shade Ø36, about 25 high, bottom about 1.25, top about 1.55** | shade [0.885, 0.949, 0.389, 0.484], base at about v 0.881 | **Lit:** the shade glows from inside at L 93–97, H 35–45, with a soft warm pool (radius up to 70) on the sofa's right end and the throw. No visible cast shadow. **No visible cable** (it runs behind the base to the back wall). 2700 K |
| pouf | `pouf-cj-cotton-knit-ball-cover` (7.5, **test only, not approved for sale**) | `…0cf1414b-…jpg` (pick the natural-cotton colour) | (1.45, 2.00) on the rug. Chunky-knit ball in natural warm-white cotton, Ø45, filled height 36 (assumed) | **[0.905, 1.0, 0.956, 1.0]** | **A corner crop**: only its back-top shows, from v 0.956 down. It leaves through the right **and** bottom edges. At least 0.02 below the floor-lamp base. Clear of the sofa's front-right leg and the cover hem |

**Fix in the same pass: the runner, to its card** `table-runner-cj-linen-look-sage-fringe` (7.0; reference `…2736eed6-…jpg`):
- **What it is:** a flat sage-grey linen-look runner, **33 wide × 122 long**, with **short knotted tassel fringes (about 3–5 cm) at both ends**.
- **How it lies:** across the table's width in its left third, centre line 28–35 cm from the table's left end. It hangs over both long edges by about 26 cm, so the front fringe shows below the table's front edge.
- **What's wrong today:** the composite runner has no fringe and the wrong drape.
- **Its area:** keep it inside the clay runner box [0.496, 0.604, 0.767, 0.846], extended down to the front overhang. Nothing lies on it.

## What must not move (lock)
Everything else in the base image stays as it is, pixel for pixel:
- walls, window, curtains, vase, pendant, the travertine pair;
- **the triptych** (three different prints) and **the wall round**;
- sofa, cover, cushions, throw, armchair, coffee table, candle holders, bowl, rug.

**Accept:**
- `lock_v2` against the clay: shift ≤2 px, max edge ≤9.6 px.
- Outside the four product boxes and the runner's area: mean |Δ| ≤2 per channel. No new object anywhere else.
- No sun patch, no snow in the window.
- The wall sconce is **not** added: it stays transition-only.

## Prompt core (to adapt to the model's format)
> Edit this photograph of a Nordic living room. Keep every existing object, wall, light and shadow exactly as it is.
> Add only these four products, matched to their reference photos and at the exact positions and sizes marked in reference 2:
> 1. a charcoal felt magazine basket with light-wood handles, standing on the rug in the foreground between the armchair and the coffee table's front-left corner, its long side pointing at the camera, cut by the bottom edge, well below and in front of the jute basket, with three folded plain magazines in it;
> 2. a straight jute-rope cylinder basket with rope loop handles, in the back-left corner left of the sofa, off the rug;
> 3. a floor lamp with a thin matte-black pole and a round oat-linen drum shade right of the sofa, glowing softly with a warm 2700 K light pool on the sofa's right end, no visible cable;
> 4. a chunky-knit natural cotton pouf, only its top showing in the bottom-right corner, cut by the frame.
>
> Replace the runner on the coffee table with a sage linen runner, 33 cm wide, crossing the table's width in its left third, with short knotted tassel fringes at both ends hanging over the edges.
>
> Winter daylight from the left window, soft, no sun. Matte materials. No text.

## After the pass (0 tokens, render-agent)
1. Run `lock_v2` and the seam check.
2. Grade with the corrected chain from the review §4 (fixes 1–5), not v5. Mask: walls, floor, glass and products from the clay index, with the four new products included in the product mask (≤ +0.2 stop vs raw).
3. QA, using the clay boxes of the four ±15%:
   - floor-lamp shade glow ≥6 L above the wall;
   - pool on the sofa visible;
   - charcoal holder L 25–35;
   - jute basket in the oak range (H 25–40, S 25–55).
4. Hand the sheet to master-designer: v5 / the pass ungraded / the pass graded.
