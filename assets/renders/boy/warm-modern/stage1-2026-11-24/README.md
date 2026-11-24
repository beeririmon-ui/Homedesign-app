# K-boy, warm modern, stage one (2026-11-24)

render-agent. Brief: `briefs/wm-kids-stage1-render-2026-11-24.md`. Spec: `docs/proposals/wm-kids-rooms-render-2026-11-19.md` (ch. ד over א-ג). Status: **for QA again** after the fixes of `qa/reports/2026-11-24-kids-stage1` (K-B1, K-B2, K-B3; the section "QA fixes" below). Before the owner's approval 3. Not for the site before QA.

## Contents
- `plate.png` and `plate-frame.png`: the empty room (seedream-5-pro 2K + `tools/compose_plate_kids.py`).
- `layers/`, `shadows/`, `light/`: 13 default products (ד.2), each in its own layer per RND2. `manifest.json` gives the z order and the compose rule.
- `K-boy-defaults*.png`, `K-boy-V2*.png`, `K-boy-V3*.png`: the frames. The sample slot is the folded throw: V1 Deep Chestnut, V2 Coffee, V3 Green.
- `checks.json`, `qa-sheet.jpg`, and `jobs.json` (the var2 ledger).
- `kids-fixes.jpg`: before (the QA commit 1b062a0e) and after, at x2, one row per finding of both rooms (K-G1 to K-G4, K-L2, K-B1 to K-B3).

## Money
8 sends, **3,450**: the plate (650), 5 crop edits at 400 (PB3, PB4, PB5, PB1, PB2), and after QA 2 crop edits at 400 (PB5b-cars for K-B1, PB1b-stripes for K-B2). Every send was priced first with `var2_estimate_cost`. Both rooms: **4,650** of the 5,050 the QA round allowed (cap 9,700).

## Count
- **Manager's count: 13.**
- **V7Q6: 10** (was 11: the cars, now at the card's size, are under the V7Q6 size line). The blind and the bookends are under 50% visible in the clay.

## Checks (`checks.json`)
- RND2: 0 px outside every alpha, shadow and light, in the defaults, V2 and V3. V2 and V3 differ from the defaults only inside the throw.
- Every shadow sits one z below its product (15 layers). The light layer (the pendant) is screen.
- WM-G1: p0.5 = 11.58.
- The band: dE00 0.16 against #A8A88E, on both walls.
- The plaster above the band: HSL H 34.7.
- V3 Green: the fold is 52.7 L* from the band.
- Safety:
  - Nothing stands on the sill. The standing pillow covers the slab only from in front.
  - The pendant is high and has no cord near the bed. The blind has no cord.
  - The toys are soft, plus the 4-piece car set (ד.2).

## Code fixes (0 tokens)
- **Plate:**
  - Shifts against MB0 so the room matches the house: oak, and limestone to #D8C8AE.
  - **The band on each wall**, multiplied per channel in linear light to #A8A88E. The north band was off by dE00 7–9 because it was too dark; it was found during the girl's work.
  - **The skirting** in the band's paint (it was greener and more saturated).
  - The WM-G1 toe: p0.5 from 3.35 to 11.5.
- **PB3:** the pendant was drawn 1.25x the card. It is now scaled to 30 cm, with a matte opening, the cord and the light rebuilt. The blind's hem no longer sits on the mullion.
- **Prints A, B and C:** the art is placed by homography.
- **PB1:**
  - The throw is cut by its colour and lightness, so the whole throw, including its top on the mattress, is in one layer and the seam line is gone.
  - The basket is the clay's outline fitted to the edit: the model stood the card's basket about 67 px nearer, within the spec box. The basket layer no longer carries the duvet.
  - The fringe: about 4.1 cm drawn, cut in code to 2.75 cm (the strand tips are inpainted from the duvet between and below them).
  - White specks at the throw's edge are inpainted.
  - The duvet covers the plate's whole mattress.
  - The standing pillow layer is cleared off the wall.
- **PB2:** the bear was drawn about 100 px to the right of the clay, on the lying pillow. It is cut where it was drawn, with a solid edge (cream on cream).
- **Variants:**
  - V1 is moved to the SKU photo (dE00 7.0 → 1.1).
  - V2 and V3 are colour-only, made from V1.
  - The duvet seen between the fringe strands is not recoloured.

## QA fixes (2026-11-24, after `qa/reports/2026-11-24-kids-stage1`)
Code in `tools/kids_qa_fixes.py`; after `python3 kids_cut.py cut PB2-nest` run `python3 kids_qa_fixes.py chain boy`, after `cut PB5b-cars` run `cars boy`. Measured in `checks.json` → `K_fixes_2026_11_24`.
- **K-B1, the cars (edit PB5b, 400, the SKU photo #1 Car as its reference).** The edit drew the SKU's beetle: a round hole in the body, two wheels a side, one of the three turned. It drew them about 1.5x the card, so the code takes the cars from the edit against the empty plate and scales them as one group about their contact line (0.608) to the card: 7.8 x 5.0, 6.9 x 4.6 and 6.3 x 4.8 cm against 8.5 x 4.3 (0.150 cm/px; the photo's own outline is 0.61 high for its length, so the height sits about 15 % over the card's number). Their contact shade comes with them, on the desk top only. Lit half 69.4 / 24.1 / 57°, the SKU photo 72.4–72.9 / 22.7–30.4 / 54–58°. No supplier pixel is in the layer: the photo went to var2 as the edit's reference only, and the board stayed in the scratchpad.
- **K-B2, the duvet set's stripes (code first, rejected; then edit PB1b, 400).** The code route (a blur across and the photo's contrast) read out of focus at x2. The edit redrew the pattern only: wide, soft melange stripes about as wide as the gap. The bedding layer keeps its alpha (the geometry QA passed) and takes the edit where it is solid and no product above it is solid. The shadows the edit saw are divided out (linear), so the composite applies them once. The stripes' contrast is brought to the photo's with one gain (0.681): L* p5–p95 −10.3 … +8.8 against the photo's −10.5 … +7.5 (the same measure on the SKU photo: −10.1 … +7.4); it was −14.7 … +11.8.
- **K-B3, the nest (0 tokens).**
  - The pair and its shadow moved 108 px left. In QA's rows (y 720–800), the left cushion now overlaps the standing pillow by 61 px at least, 68 px median (0.02 is 51 px), and no plate shows in the old strip.
  - The pair's left edge was torn by the PB2 wall trim and now lay on the pillow. Its shade slivers on the strip are let go, the notches are filled out to a smooth envelope (14 px at most, inpainted from the cushion), and the bottom edge's 1 px stair is let go. Its shade on the pillow is softened and capped at 0.25.
  - Where the pair stood before, the bedding layer's pieces of the wall are let go (303 px).
  - **The bear's alpha (K-L1):** the duvet the PB2 cut carried round its feet is cut by GrabCut (1,862 px). Its outline's white fringe takes the bear's own colour (1,127 px). Its bottom (the undersides, the contact shade) takes the PB1b edit, so it meets the new stripes without a seam. Dark wall pixels in its alpha: 0 before and 2 after; the strip QA counted was already gone with the PB2 re-cut.
- **K-L6, the reveal (0 tokens, in `compose_plate_kids.py`):** the olive step below 1.25 on the window reveal is taken back to the reveal above the line, with a 4 px ramp (`reveal_fix`).
- **Not touched:** K-L3 (the ledges) and K-L4 (the soft toys' size, the designer's).

## Regions for QA after the fixes (canvas px)
1. The cars (1790–2030, 800–950): shape, size, contact shade.
2. The duvet set (300–1544, 597–1530): the stripes at x1–x2, and the seam round the throw, the basket and the bear.
3. The nest (690–1010, 700–960): the pair's left edge on the pillow, the bear's feet, and right of the pair (the lying pillow's corner now shows).

## Regions for QA in the first round (canvas px, 2720x1530)
1. The top of the mullion under the blind (600–650, 280–295): a 3 px grey cap.
2. Frame C and the books (1080–1590, 110–620): a faint ragged shadow rim at x3.
3. Frame A, inner bottom-right (~2160, 410): a 2–3 px dark dot.
4. The cars: 2 of the set's 3 are drawn (the set of 4 counts once).
5. The bear (740–880, 720–960): its position is u 0.26–0.31 against the spec box's 0.20–0.24. Its mask is a little wide (to x 964).
6. The fringe's ends (910–1260, 1180–1260): tips inpainted in code; check at x2.
7. The basket: drawn about 67 px nearer than the clay, inside the spec box.
8. V1 Deep Chestnut after the photo match: greyer (C* 4.9 at L* 22).
