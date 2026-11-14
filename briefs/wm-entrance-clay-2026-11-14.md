# Brief: the clay of the warm-modern entrance and the T-E0 stations (render-agent, 2026-11-14)

## Why
The owner approved the transition pilot (rule FB4 in `docs/studio-rules-digest.md`, EFF1.6): the camera walk from the entrance to the living room, and then the bedroom. Before a token is spent on the stills, the geometry is locked on a clay. This run is the 0-token step. **No var2 call that costs tokens in this run.**

## Inputs
- `docs/studio-rules-digest.md` (FB2–FB4, U14, TR1, TR2).
- `docs/house-plan.json`: cameras H0, H0x, M0; transition T-E0 (a 13° pan at H0, then the 4.85 m dolly through `O-entry-living`).
- `docs/proposals/wm-entrance-hall-architecture-2026-11-13.md` (master-designer): §1.1 says what stays from the Nordic geometry and what changes in warm-modern; §7 "הערות לבריף הפיילוט" lists what you need. Values marked "(הטלה)" are projections that this clay must check; **the clay wins.**
- `docs/proposals/wm-arrival-entrance-to-living-2026-11-13.md` (motion-agent): §2 the end frames, §8 what motion-agent needs from you.
- The existing blockout: `assets/blockout/house/build_house.py`, `assets/blockout/house/framing_wm_r4.py`, the Nordic hall clay `assets/blockout/house/framing/round2/H-B-lit.png`, the warm-modern M0 clay you made for the living room.
- The empty living room plate the designer cites as `base.png`: `assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png` (check that this is the plate the tour uses).

## What to make
1. **The warm-modern entrance as a clay, structure only:** the shell as the designer's §1.1 and §2 describe it (the lined opening to the living room with no door leaf, no cornice, no architrave, no furniture, no object), with the empty living room seen through the opening.
2. **Three frames from the H0 point,** on the same canvas as `base.png` (2720×1530, the camera frame at [77.49, 43.43, 2642.51, 1486.57]):
   - `H0` (yaw 12, shift 0.52 / 0.46);
   - `H0x-a` (yaw 25, shift 0.52 / 0.46, the plan's value);
   - `H0x-b` (yaw 25, shift 0.47 / 0.50, M0's shift: motion-agent asked for the shift to change in the pan; the designer is deciding now, so make both).
   Each with a lit clay, a depth pass (16-bit, metric, the scale written in the README) and an object-id or edge pass if the script gives one cheaply.
3. **12 stations along the dolly,** from H0x to M0 at even distance (station 0 = H0x, station 11 = M0), heading constant, for both shift variants if the cost is a loop; otherwise for variant b, and say so. Lit clay and depth for each.
4. **The check of the designer's projected values:** a table, value by value (the opening's u range, the corner, the opening's centre, the head of the opening, the left margin, and the rest marked "(הטלה)" in his document): his number, the clay's number, the difference.
5. **The seam with M0:** station 11 against the existing warm-modern M0 clay and against `base.png`: edges within 2 px. Report the largest offset and where.

## Outputs
- `assets/blockout/house/framing/wm-entrance-2026-11-14/` with the frames, the passes, a contact sheet (one JPG), `selfcheck.json` and a short `README.md` (the camera values used, the depth scale, the table of item 4, the seam of item 5, anything the designer or motion-agent must know).
- The script next to the other framing scripts, so that the run can be repeated.
- Working files in the scratchpad (EFF1).

## Acceptance
- Cameras exactly as `docs/house-plan.json`; verticals vertical (U14).
- Station 11 matches M0 within 2 px.
- Nothing in the entrance clay that the designer's document excludes.
- The README states plainly every place where the clay disagrees with a document.

## Fixed rules
- 0 tokens: no `var2_create_*`, no `var2_modify_*`. `var2_estimate_cost` and `var2_list_models` are free and allowed.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- If the porch and the front door are easy to add to the model as plain structure (plan values `porch` and `O-front-door`), say so in the README but don't build an exterior frame yet: the designer is designing the door now, and its camera does not exist.
- Return a short Hebrew summary: what was made, the table's largest differences, the seam, and what is still open.
