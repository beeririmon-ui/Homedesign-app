# K-girl, warm modern, stage one (2026-11-24)

render-agent. Brief: `briefs/wm-kids-stage1-render-2026-11-24.md`. Spec: `docs/proposals/wm-kids-rooms-render-2026-11-19.md` (ב.6, ch. ד). Status: **for QA again** after the recheck of `qa/reports/2026-11-24-kids-stage1` (after commit c4b811c0: K-G3 and K-G4, plus K-L7 and K-L1; all in code, 0 tokens; the section "Recheck fixes" below). K-G1 and K-G2 closed. Before the owner's approval 3. Not for the site before QA.

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
- **The prints set G1 (FB12, 2026-11-25), beside today's files:** the section "G1" below. `manifest.json` stays as it is (Type A); G1 has its own `manifest-g1.json`.

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

## Recheck fixes (2026-11-24, after c4b811c0; 0 tokens)
Before (c4b811c0) and after at x2: `kids-fixes-2.jpg` in this folder. Measured in `checks.json` → `K_fixes_2026_11_24` → `recheck`.
- **K-G3, the pen cup** (`tools/girl_from_boy.py pen-cup`, `recolour_cup2`). The colour held, but the cup read as a flat, glowing peach block. It is now built as follows:
  - **The pencils:** keyed against the boy's plate, which is the band they were drawn on (dE76 over 20 is pencil, under 6 is band). Their edges take the pencil's own colour, so they are clean and solid.
  - **The band between the pencils** is let go. The cup's shade, which the boy's layer carried there, goes into the cup's shadow layer.
  - **The shading** is the walnut's light in linear Y, not its figure. The front face is a line fitted to the walnut, flat here, because the walnut's brightening to the right is its satin. The right side face is at the walnut's ratio to the power 0.75. The lip has its own row profile.
  - **The grain** is the walnut's fine structure, scaled to the photo's: L* minus its 3 px blur, std 2.9 on the frame (3.07 on the layer), against the photo's 3.28 (it was 0.62).
  - **The faces:** on the frame, the thirds read L* 76.6 / 76.6 / 57.6 (they were 75.1 / 75.4), with the side face in the right third.
  - **No ring:** the outline keeps the cut's alpha, and the shadow is filled where the outline thinned. The wall left of the cup reads 53.8 at 0–4 px, 50.2 at 4–8 and 57.4 at 8–14 (it was 82 against 68).
  - **The colour:** lit half 78.2 / 11.9 / 29.5, dE00 0.02 against the photo.
- **K-G4, the throw's top end at the foot board** (`tools/kids_variants.py`): the hue weighting, which keeps the duvet between the fringe strands, now covers only the hanging end (the lower 45 % of the throw's rows). The lying top end (x 1260–1335) had been read as fringe. The patch against the throw beside it, in L*: V1 +10.9 → +0.4, V2 +17.7 → +0.5, V3 +4.8 → +0.7. The straight seam at x 1260 is gone. dE00 against the photos: V1 4.49, V2 4.28, V3 4.46.
- **K-L7** (`tools/kids_qa_fixes.py girl_edges girl`):
  - **The right cushion's right edge** is taken from the GB2 edit's corduroy: a median of 7 rows and a Gaussian of 2. The notch is filled, the grey wedge at its foot is cut, and the cushion's shadow is filled where the edge was cut back.
  - **The duvet's back edge** under the pair is smoothed (a median of 9 columns and a Gaussian of 2.5; notches inpainted, spikes cut).
- **K-L1, the window in the pillowcase layer** (`window_px girl`): 1,247 px within dE76 8 of the plate, over the window's clay ids, are let go. The pillow's shadow there is 1, so only the plate's own window shows. 506 px on those ids are left: small dark pieces of the head board and frame, joined to the pillow. The boy's standing pillow was not changed: there its shadow is not 1 under the window pixels, so the passed frame would have changed by up to dE 34; it was tried and restored.

## Regions for QA after the recheck (canvas px)
1. The pen cup (2230–2470, 740–920), at x1 and x2.
2. The throw's top end at the foot board in V1, V2 and V3 (1150–1390, 910–1060).
3. The right cushion's right edge and the duvet's back edge under the pair (960–1200, 700–950).

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

## G1, the prints set "painted bunnies" (FB12, 2026-11-25)
render-agent. Brief: `briefs/wm-fb12-girl-art-g1-2026-11-25.md`. Spec: `docs/proposals/wm-fb12-2026-11-25.md` ב.10.5. All in code, **0 tokens, no var2**.
**Status: stopped for the manager.** Two acceptance items fail in code as written (below). Nothing of today's is overwritten, and nothing is wired to the site.

### Files
- **The layer:** `layers/framed-prints/framed-prints-aliexpress-watercolour-bunny-nursery-prints-g1.png`.
  - It holds Type A's frames, rails and alpha as they are, and shares Type A's shadow.
  - A is B05 (colour 12), B is B04 (13) and C is B06 (11), all 30 x 42 unframed.
- **The frames:** `K-girl-defaults-g1` (V1), `K-girl-V2-g1` and `K-girl-V3-g1`, each with its `-frame`.
- **`manifest-g1.json`:** this room's manifest with G1 as the prints' default.
  - **Why a second manifest and not an entry:** the site's tour (`site/tools/tour/girl.warm-modern.json`) builds from `manifest.json` and checks it against `K-girl-defaults.png`. A G1 entry there would break that check, or would open a prints wheel.
  - **The rollback:** `manifest.json` (Type A), with every Type A file untouched.
- **`qa-sheet-g1.jpg`:** the wall at x2 (canvas px x2), before and after; then G1 with V2, V1 and V3 at x1 (1920).
- **`checks.json` → `G1_2026_11_25`.**
- **The tool:** `tools/g1_prints.py` (run it with `python3.12 -I ... all`). It calls the boy's `tools/kids_art.py place()` with its new options. The supplier's flat files stay in the scratchpad.

### The tool change (`kids_art.py`)
- `place()` takes each panel's own width and height (`sizes`), instead of a fixed 300 x 400.
- It also takes:
  - `panels`;
  - `paper_ref` (one paper for the set);
  - `quads` (the re-measured openings);
  - `edge="unmix"`;
  - `floor_L` (WM-G1);
  - `out` and `record`.
- All are off by default. `place boy` and `place girl` rebuild today's layers byte for byte (sha256 equal, manifest record equal; `checks.json` → `stage_one_byte_identical`).

### The method
- **The openings, re-measured (instruction 3):**
  - Each side is fitted to the paper's edge, subpixel (rms 0.04–0.10 px; C's right side 0.65).
  - The openings are back-projected through the camera.
  - **A and B are one size on the wall: 25.0 x 36.0 cm, ratio 0.695 and 0.693.**
  - The table's 0.75 and 0.80 were the quads' pixel ratios, which carry the perspective. Off the table: −7.3 % and −13.3 %.
  - **C:** stage one's quad was an axis-aligned box (the fallback). The frame leans about 10°, so the old box left the paper uncovered at the top right and made a seam at x 1443.
    - Now its top and sides are fitted.
    - Its bottom is behind the ledge's lip, so its ratio cannot be seen. It is the set's own 0.694, and 2.7–4.1 % of the opening hides under the lip (the clay: 1.5 of 36.4 cm). Off the table: +6.8 %.
  - All three are more than 3 % off, so the crops are recomputed.
- **The crops:**
  - Each keeps the table's centre, takes the largest rectangle of the rectified ratio inside the art, and takes only blank paper off.
  - A: 44, 0, 1455, 2030. B: 58, 19, 1437, 2011. C: 90, 33, 1486, 2041.
  - The subject margins are at least 4.5 %.
  - The panels are 278 x 400, 277 x 400 and 278 x 400, resized by area in linear light.
- **The light (instruction 4):** one paper for the set, B05's (lin 0.716 / 0.689 / 0.649). Each opening is lit by its own blank canvas, as in stage one. There is no reflection layer: the paper is matte, with no glass.
- **The edge:** within 2.5 px of an opening's edge, each pixel is split between the rail's colour and the lit paper, and only the paper's share takes the art. This leaves no paper line and no hard cut. Inside that rim, the pixel is the art.
- **WM-G1:** L' = 15 + L²/60 below L* 30.

### The measures (`checks.json` → `G1_2026_11_25`)
- **RND2:**
  - The alpha is identical to Type A's.
  - 0 px differ outside the openings grown by their 2.5 px rim.
  - Inside that rim, on the rails' side, 2,519 px change, by their paper share only: against the blank, dE76 p50 0.6–2.1, max 5.5. Stage one had changed 660 px outside the same openings.
  - All three frames equal `plate.png` outside every layer (0 px), and equal today's frames outside the openings (0 px).
  - Rebuilt without the swap, the compose chain gives today's three frames byte for byte.
- **dE00 per ink region against the flat file, in the file's light scale:** at most 2.65.
  - B05: fur 0.04, flowers 0.51, leaves 0.37.
  - B04: basket 0.11, ink 2.65 (the placing itself: 0.41; the rest is x1's resolution, since a 5 px ink line is under one panel cell).
  - B06: body 0.07.
- **The darkest ink:** L* 15.6 (B, the sepia; the file reaches 0). A is 15.8 and C 21.2.
- **The colour shares of the set:** see the failures below.
  - Pink: 0.45 % as seen and 0.76 % flat (at most 30 %).
  - Green: 0.03 / 0.49 % (at most 10 %).
  - Blue: 0 / 0 % (at most 3 %).
- **V1–V3:** each frame has RND2 0 against the plate and 0 against today's frame outside the openings. The black point p0.5 is 12.45, 12.42 and 12.46. The prints are identical in all three, and the plaster above the band is unchanged.
- **The highlights:** in C, 42 px of B06's white chest reach 255. This is the bright light on the shelf. It cannot be seen at x2.

### Failures (stopped here, per the brief: no var2)
1. **B06's ground "about 6–8 L\* below the other two": fails as written.**
   - **In the files:** the grounds are L\* 85.5 (B05), 81.9 (B04) and 83.6 (B06). So B06 is 1.9 below B05 and 1.7 above B04, not 6–8.
   - **In the scene:** with one paper, B06 keeps exactly that albedo (−1.9 / +1.6).
   - **As seen:** the scene lights C on the shelf about 12–17 L\* brighter than A and B, and the wall beside them reads the same way (plaster L\* about 91 by C, 78–87 by A, 74–81 by B). So B06 is seen at 91.2, against 80.2 and 73.1.
   - Meeting the number would mean darkening the product (fidelity) or the scene's light. Neither is done in code.
2. **Caramel at least 10 % (HSL H 20–35, C\* ≥ 15): fails.**
   - It is 9.3 % of the set as seen (the warm light adds to it) and 4.75 % on the flat panels.
   - Much of the set's warm brown is at H 35–45 (B05's fur, B06's body) or under C\* 15 (B04's basket, B06's body).
   - The designer's estimate of 15–20 % does not hold under this definition. Raising it would recolour the products.

### Regions for QA (canvas px)
1. C, the leaning frame: its top-right corner and its right rail (1415–1470, 145–200), and its lip (1320–1460, 320–375). This is the old quad's seam, now covered.
2. A's and B's rails, all four sides (1985–2175, 165–435 and 2225–2445, 125–420): no paper line, no halo.
3. B04's darkest sepia: the eyes and the basket's shaded weave (2270–2400, 205–350), at the L\* 15 floor.
4. B06's ground against A's and B's at x1, on the sheet (the failed item 1).

