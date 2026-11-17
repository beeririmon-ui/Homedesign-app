# Brief: QA on clip 2 after the code repair (qa-agent, 2026-11-17)

## Why
Clip 2 (the dolly HDx → M0, kling-3-omni, take 1) had a defect at the right edge: a free-standing column that leans up to 18.7° and a glass façade where the living room's right wall and the dining opening should be (frames 30–72 of the raw clip). The manager chose a 0-token code repair first. motion-agent repainted that strip from the clay geometry (`site/tools/transitions/repair_right_wall.py`) and reports that it holds at ×1, but it judged from stills at 100% and from time metrics, not from watching the motion. If the repair fails, the next step is a second take for 1,296 tokens, which needs the owner's approval (CLIP2-R, open). So your verdict decides whether we spend.

EFF1.2: check only what changed (the repaired region and the two new walk-test checks). Everything else in the clip (the walk, exposure, the end locks, the HDx corner) passed motion-agent's checks and is not repeated unless a number looks wrong.

## Inputs
- The folder: `assets/video/transitions/warm-modern/clip2-hdx--m0/`. Read its `README.md` first ("על מה להסתכל (QA)" and "מה עוד נשאר").
  - Repaired previews: `preview-desktop.1920.60fps.mp4`, `preview-phone.1080.30fps.mp4`.
  - Before the repair: `preview-*.unrepaired.mp4`.
  - `repair.json`, `walk.json` (take 1), `walk.repaired.json`, `look-repair-before-after-f24-80.jpg`, `look-repair-right-edge-f24-80.jpg`.
- The plan: `docs/house-plan.json` (the living room's right wall and the dining opening), the clay `assets/blockout/house/framing/wm-entrance-2026-11-14/` (stations).
- The end frames: `assets/renders/hall/warm-modern/hall-2026-11-17/hdx-frame.png` and `assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png`.
- The tools: `site/tools/transitions/walk_test.py` (checks 5 and 6 are new), `repair_right_wall.py`.

## What to check (0 tokens)
1. **In motion, at ×1 (the decisive item).** Desktop frames 40–110 and phone frames 20–55, at real speed and at quarter speed. Extract the frames with ffmpeg. Look for anything a visitor would notice:
   - an edge that swims, flickers or jumps at the repair's border (the clip's near jamb against the repainted wall, around frames 40–75);
   - a baseboard, floor joint or ceiling line that breaks or steps at the border;
   - a texture or tone mismatch between the repaired plaster and the model's plaster;
   - the dining opening (frames 78–92): a straight vertical jamb, nothing that reads as glass, a window or furniture.
   Compare with the `.unrepaired` previews to be sure the defect is gone.
2. **Geometry.** Spot-check two or three frames: is the repaired corner and the dining opening where `docs/house-plan.json` puts them, through the walk-test camera? Within a few px is enough.
3. **The walk test.** Rerun `walk_test.py` on the repaired bank, or on frames you extract from the desktop preview if the bank is not reachable, and confirm the verdict WALK and checks 5 and 6 as reported (check 5: 0 of 37 frames; check 6: one frame, b37, under the limit of 2). Confirm checks 5 and 6 fail on take 1, so we know they catch the defect.
4. **Light.** By the clay, the repaired right wall (it faces the windows) is about 13% brighter than the back wall. Say whether it reads naturally at ×1. Don't measure it against a design target; if it looks wrong, say so and it goes to master-designer.
5. **The residue motion-agent lists** (a light notch under the baseboard in bank 133–139; one mirrored floor board; the repaired plaster slightly smoother): visible at ×1–×2 at preview size, or not?

## Outputs
- `qa/reports/2026-11-17-clip2/README.md`: pass or fail per item, with numbers and the frames you looked at. Evidence images in the same folder only when needed; scripts and extracted frames in the scratchpad.
- Low findings go to `status/backlog-low.md` (EFF1.1), not into a fix.
- A status line for the clip: "עבר QA" (temporary preview, not for the site yet) or the blocking finding with frame numbers.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's document or tool.
- Return a short Hebrew summary: the five items, pass or fail with numbers, and whether clip 2 passed QA.
