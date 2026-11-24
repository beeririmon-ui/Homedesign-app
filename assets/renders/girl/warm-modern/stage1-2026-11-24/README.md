# K-girl, warm modern, stage one (2026-11-24)

render-agent. Brief: `briefs/wm-kids-stage1-render-2026-11-24.md`. Spec: `docs/proposals/wm-kids-rooms-render-2026-11-19.md` (ב.6, ch. ד). Status: **for QA again** after the fixes of `qa/reports/2026-11-24-kids-stage1` (K-G1 to K-G4, all in code; the section "QA fixes" below). Before the owner's approval 3. Not for the site before QA.

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
3 sends, **1,200**: GB1, GB1b and GB2, at 400 each. The QA fixes of this room cost 0 (all code).

GB1b was a second send. GB1 drew a squat basket, about 40 x 22 cm with side cut-out handles. The card is 40 x 45, and the photo shows two long rope loop handles.

## Count
- **Manager's count: 12.**
- **V7Q6: 9.** The blind, the bookends and the duvet are under 50% visible in the clay.

## Checks (`checks.json`, `plate-compose.json`)
- RND2: 0 px outside, in the defaults, V2 and V3. V2 and V3 differ from the defaults only inside the throw.
- Every shadow is one z below its product (14 layers). The light layer is screen.
- WM-G1: p0.5 = 12.45 on the frame and 12.37 on the plate (after the QA fixes).
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

## QA fixes (2026-11-24, after `qa/reports/2026-11-24-kids-stage1`; 0 tokens)
Measured in `checks.json` → `K_fixes_2026_11_24` and `plate-compose.json` → `K-G1_K-G2`; before and after at x2 in `assets/renders/boy/warm-modern/stage1-2026-11-24/kids-fixes.jpg`.
- **K-G1, the band's white halo (`tools/girl_plate.py`).** The band is no longer the boy's band times k: k clipped near the bed. It is now painted per column and per channel with the light the boy's plate carries there, as a ratio: (the girl's plaster over the line / #ECE5DA) / (the boy's band top), times the boy's band luminance, times #E8D5CC. A soft shoulder keeps it under the plaster. Band pixels with all three channels over 245: 128,967 before, 0 after. Band L* p99: 91.4 under the plaster's 94.9 (it was 100). The implied albedo per column: dE00 p5/p50/p95 0.19 / 0.48 / 1.07 against #E8D5CC. The band is darker than the plaster in all 462 columns, and its plaster texture is kept. The pillow's shade stays near the right pillow (hue lit / shade 41.9 / 50.1).
- **K-G2, the olive from the boy.**
  - The band is painted by what is drawn olive, not by the clay's id: the desk's back and front legs, the chair, the foot board's edge, and the band's edge under the sill.
  - The reveal's step below 1.25 (`reveal_fix`) is fixed, and so are the reveal's and the skirting's corner lines (2,863 px, a*/b* to the reveal's own neutral).
  - The pen cup's and the bookends' greenish rims are cleaned (1,132 px).
  - Band pixels at h 70–110 in the plate: 0. QA's measure on the frame (h 95–135, C* > 6, below the line, outside the products): 31,140 px before, 55 after (specks of a few px). At the products' soft edges (alpha under 0.5), 665 px at h 70–110 remain: the blend of a product's own colour with the band.
- **K-G3, the pen cup (`tools/girl_from_boy.py`, code only):** the beech is built from the walnut cup's light, not its grain, with no gloss and contrast compressed to 0.6. The olive between the pencils is let go. Lit half 78.3 / 11.8 / 29.5 against the photo's 78.2 / 11.9 / 29.5: dE00 0.13 (it was 8.3, brass).
- **K-G4, the throw (`tools/kids_variants.py`):** each variant's lit half (R5, the upper 40 %) is set to its photo. Deep Chestnut is set to the boy's own lit L*, carried by the two rooms' light ratio (1.075 in Y) less 3: target 50.5, drawn 51.3. dE00 against the photos: V1 Linen Brown 5.13, V2 Deep Chestnut 5.08, V3 Pink 4.81 (they were 19.0 / 19.9 / 18.6). V3 stays inside ב.4's HSL limits.
- **K-L2, the smudges under the sill (`tools/kids_qa_fixes.py islands girl`):** the pillow layer's and the bedding layer's pieces cut off from their body are let go (11 + 2 pieces, 1,045 px), and the pillow's shade under them is filled.
- **K-L5:** the ruffled pillowcases are set 5 L* lower (`L_shift` in the GB1 cut).
- **Not touched:** K-L4 (the bunny's size, the designer's).

## Regions for QA after the fixes (canvas px)
1. The band near the bed and the pillows (880–1500, 560–900): no halo; the pillow's shade.
2. The band round the desk, the chair and the foot board (1400–2450, 600–1260): no olive.
3. The pen cup (2210–2450, 740–890): matte beech.
4. The throw V1–V3 (990–1330, 930–1250).
5. Under the sill (520–700, 800–900).

## Regions for QA in the first round (canvas px, 2720x1530)
1. The plaster above the band reads HSL H 31.5; the rule is 32–40. This is the blush band's bounce in the clays' ratio, not paint.
2. Faint grey smudges on the band under the sill (580–660, 815–850). They came from the GB1 edit, and the GB2 edit kept part of them.
3. The bunny's ear tips (650–720, 710–760): a soft edge on a wall of nearly the same colour.
4. The throw's top end at the foot board (1190–1330, 935–1005): it was joined by texture.
5. The basket's right handle over the throw (1000–1040, 1080–1120).
6. The duvet's back edge against the wall in the corner (880–1120, 860–950).
7. The standing pillow placed in the corner (725–960, 735–890), not against the head board as in the clay.
