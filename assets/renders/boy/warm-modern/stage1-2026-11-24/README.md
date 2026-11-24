# K-boy, warm modern, stage one (2026-11-24)

render-agent. Brief: `briefs/wm-kids-stage1-render-2026-11-24.md`. Spec: `docs/proposals/wm-kids-rooms-render-2026-11-19.md` (ch. ד over א-ג). Status: **for QA** (before the owner's approval 3). Not for the site before QA.

## Contents
- `plate.png` and `plate-frame.png`: the empty room (seedream-5-pro 2K + `tools/compose_plate_kids.py`).
- `layers/`, `shadows/`, `light/`: 13 default products (ד.2), each in its own layer per RND2. `manifest.json` gives the z order and the compose rule.
- `K-boy-defaults*.png`, `K-boy-V2*.png`, `K-boy-V3*.png`: the frames. The sample slot is the folded throw: V1 Deep Chestnut, V2 Coffee, V3 Green.
- `checks.json`, `qa-sheet.jpg`, and `jobs.json` (the var2 ledger).

## Money
6 sends, **2,650**: the plate (650) and 5 crop edits at 400 (PB3, PB4, PB5, PB1, PB2). Every send was priced first with `var2_estimate_cost`.

## Count
- **Manager's count: 13.**
- **V7Q6: 11.** The blind and the bookends are under 50% visible in the clay.

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

## Regions for QA (canvas px, 2720x1530)
1. The top of the mullion under the blind (600–650, 280–295): a 3 px grey cap.
2. Frame C and the books (1080–1590, 110–620): a faint ragged shadow rim at x3.
3. Frame A, inner bottom-right (~2160, 410): a 2–3 px dark dot.
4. The cars: 2 of the set's 3 are drawn (the set of 4 counts once).
5. The bear (740–880, 720–960): its position is u 0.26–0.31 against the spec box's 0.20–0.24. Its mask is a little wide (to x 964).
6. The fringe's ends (910–1260, 1180–1260): tips inpainted in code; check at x2.
7. The basket: drawn about 67 px nearer than the clay, inside the spec box.
8. V1 Deep Chestnut after the photo match: greyer (C* 4.9 at L* 22).
