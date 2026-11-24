# K-girl, warm modern, stage one (2026-11-24)

render-agent. Brief: `briefs/wm-kids-stage1-render-2026-11-24.md`. Spec: `docs/proposals/wm-kids-rooms-render-2026-11-19.md` (ב.6, ch. ד). Status: **for QA** (before the owner's approval 3). Not for the site before QA.

## Contents
- **The plate** (`plate.png`, `plate-frame.png`): made in code from the boy's plate (`tools/girl_plate.py`).
  - The other surfaces take the ratio of the two plate clays, which carries the bounce light of the new band.
  - The band is #E8D5CC on each wall.
  - The skirting is in the band's paint.
- **From the boy, in code** (`tools/girl_from_boy.py`): the blind, the pendant and its light, the shelf, prints A, B and C with the Type A art, the bookends, and the pen cup in Beech.
- **Her own edits:**
  - GB1: the duvet, the pillowcases and the throw.
  - GB1b: the basket redrawn on GB1's own edit.
  - GB2: the cushions and the bunny.
- **The frames:** `K-girl-defaults*`, `K-girl-V2*`, `K-girl-V3*`. The throw: V1 Linen Brown, V2 Deep Chestnut, V3 Pink.
- `checks.json`, `qa-sheet.jpg` and `jobs.json`.

## Money
3 sends, **1,200**: GB1, GB1b and GB2, at 400 each.

GB1b was a second send. GB1 drew a squat basket, about 40 x 22 cm with side cut-out handles. The card is 40 x 45, and the photo shows two long rope loop handles.

## Count
- **Manager's count: 12.**
- **V7Q6: 9.** The blind, the bookends and the duvet are under 50% visible in the clay.

## Checks (`checks.json`, `plate-compose.json`)
- RND2: 0 px outside, in the defaults, V2 and V3. V2 and V3 differ from the defaults only inside the throw.
- Every shadow is one z below its product (14 layers). The light layer is screen.
- WM-G1: p0.5 = 12.35 on the frame and 12.39 on the plate.
- **One house:** every surface is within dE00 2.6 of the boy's plate; the only difference is the band's bounce. Each material is within dE00 3.0 of MB0, except bronze at 3.04, which is the boy's own.
- The band: dE00 0.21 against #E8D5CC (east wall, defaults frame). In the plate, east 0.21 and north 0.18.
- V3 Pink: HSL (19.0, 38.5, 75.6), inside ב.4's limits after a 4% ease of chroma.
- Safety: nothing stands on the sill. The standing pillow and the bunny's ears cover the slab only from in front. The pendant has no cord near the bed.

## Code fixes (0 tokens)
- **The pillows:** the model moved them, propping the standing pillow about 100 px towards the corner. They are cut where drawn. A pillow pixel is either lighter than the band or less pink than it, and GrabCut refines the edge. The wall the edit re-lit or smudged is left out.
- **The standing pillow's shade on the corner** is kept as its shadow layer (a 90 px band).
- **The throw:** cut by hue, then joined by texture where its lit top is as light as the duvet.
- **The fringe:** about 5.5 cm drawn, cut in code to 2.75 cm.
- **The basket:** taken from GB1b. Its handle loops and its handle tips over the throw are handled.
- **The bunny:** her ears are kept, with the outline closed and filled.
- **V1 Linen Brown** is moved to the SKU photo (dE00 about 4.8 → 0.6).

## Regions for QA (canvas px, 2720x1530)
1. The plaster above the band reads HSL H 31.5; the rule is 32–40. This is the blush band's bounce in the clays' ratio, not paint.
2. Faint grey smudges on the band under the sill (580–660, 815–850). They came from the GB1 edit, and the GB2 edit kept part of them.
3. The bunny's ear tips (650–720, 710–760): a soft edge on a wall of nearly the same colour.
4. The throw's top end at the foot board (1190–1330, 935–1005): it was joined by texture.
5. The basket's right handle over the throw (1000–1040, 1080–1120).
6. The duvet's back edge against the wall in the corner (880–1120, 860–950).
7. The standing pillow placed in the corner (725–960, 735–890), not against the head board as in the clay.
