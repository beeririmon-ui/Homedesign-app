# K-boy, warm modern, stage one (2026-11-24): incomplete, stopped on var2 re-auth

render-agent. Brief: `briefs/wm-kids-stage1-render-2026-11-24.md`. Spec: `docs/proposals/wm-kids-rooms-render-2026-11-19.md` (ch. ד over א-ג).

## Status
var2 asked for re-authorization in the middle of the stage. Per the brief, I stopped and reported. No code was asked for and no auth flow was started.

| Part | State |
| --- | --- |
| Clay K-boy, K-boy-plate, -shell, -bed (`assets/blockout/house/framing/wm-kids-2026-11-24/`) | done |
| `plate.png`, `plate-frame.png` (seedream-5-pro 2K + code) | for QA |
| PB3-window: roman blind 868827, silk pumpkin 30 + light | for QA |
| PB4-shelf: ledge pair x2 + books, print C frame | for QA |
| PB5-desk: prints A and B, walnut bookends, pen cup, cars | for QA |
| PB1-bed: stripe set, linen pillowcases, Deep Chestnut throw, jute basket | cut not finished, not for QA |
| PB2-nest: corduroy cushion pair, bear | not sent (gap) |
| Throw variants V2 Coffee, V3 Green; `kids_checks.py` | not run (they depend on PB1) |

## Money (`jobs.json`)
5 sends, 2,250: plate 650, plus 4 crop edits at 400. The girl's room: 0.

## Count (clay, ד.2 defaults)
Manager's count: 13 products. V7Q6: 9 (the blind is under 50% visible, and sets count once). In layers now: 11 of 13. The cushions and the bear are missing (PB2).

## Code fixes
- Plate: one-house shifts against MB0 (oak a*b* +3.2/+7.3; limestone -2.8/-8.0 to #D8C8AE). Band to #A8A88E: dE00 2.49 after the fix. WM-G1 toe: p0.5 went from 3.35 to 11.5.
- Pendant (`tools/fix_pendant.py`): drawn 1.25x the card. Scaled 0.809 to 30 cm, matte opening (no ring), straight cord, screen light rebuilt.
- Blind: the hem trimmed off the mullion top (`_clean_blind`).
- Prints A, B and C: the art is placed by homography, lit by the canvas (`tools/kids_art.py`).
- Black frame corners in the clay are repainted before upload (`kids_crop.py prep`).

## Open on PB1 (code only, 0 tokens)
- The throw's top, where it lies on the mattress, still sits in the bedding layer. A dotted pale line shows at that seam. The split is `_bed_masks` in `tools/kids_cut.py`.
- The fringe reads about 4 cm. The card says 2-3 cm, and MB1 failed on fringes before.

## Regions for QA (canvas px, 2720x1530)
1. The mullion top under the blind, about (600-650, 280-295): a 3 px grey cap.
2. Frame C and the books, (1080-1590, 110-620): a faint ragged shadow rim at x3.
3. Frame A, inner bottom-right, about (2160, 410): a 2-3 px dark dot.
4. The cars (1690-2580, 50-940): only 2 of the 3 cars in the card are drawn (the set of 4 counts once).
5. The pendant and its glow (750-900, 0-460).

## Next
`kids_cut.py cut PB1-bed`, after fixing the throw split and trimming the fringe. Then PB2-nest (est. 400), `kids_variants.py boy` and `kids_checks.py boy`.
