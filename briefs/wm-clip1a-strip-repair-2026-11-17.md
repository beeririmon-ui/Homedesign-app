# Brief: clip 1a, the code repair of the strip past the walnut edge (motion-agent, 2026-11-17)

## Why
Clip 1a (D0o + leaf → HT, kling-3-omni, take 1, 1,296 spent) is used in every arrival option the owner is choosing between (ROUTE1). Your rebuilt bank holds the start lock and most of the end lock, but fails in one strip: right of the walnut edge, where the living room shows through the opening (about x 1580–1740 of 1920). The model drew a wall with no window; HT has the window with the birches. The lock melts one into the other in bank frames 130–141, and it shows at ×1 (`assets/video/transitions/warm-modern/clip1a-d0o--ht/README.md`, "הבנק עם נעילות הקצוות"; `look-endlock-right-f126-143.jpg`).

The manager accepts your proposed fix. It costs 0 tokens and comes before QA.

## The work (0 tokens, no var2 calls at all)
1. **The repair.** From the frame where the living room enters behind the right jamb (about bank frame 118, 3.16 m), replace the strip past the walnut edge with HT carried back through the clay depth. Put the window on its frame plane, as in 1b. Take the mask from the clay id in each camera. The window must be identical from the first frame it shows, with no melt.
   - Fallback, only if the projection leaves holes or swims: a local dissolve in the strip only. Say which one you used.
2. **The border self-check.** Run a check in the style of `repair_right_wall.py check` on the repair's border: no flashing outline, no tab, no seam, and no step in the jamb or floor line. Checks 5 and 6 can't see seams painted from the same source, which is why this is needed.
3. **The walk test** on the repaired bank (route clip1a, as before). Confirm the end lock: the last frame identical to HT.
4. **The outputs** in `assets/video/transitions/warm-modern/clip1a-d0o--ht/`:
   - `bank-preview.1920.30fps.mp4` replaced by the repaired version, with frame numbers; keep the unrepaired one as `bank-preview.unrepaired.1920.30fps.mp4`;
   - a before-and-after look image for frames 118–143 at 100%;
   - `repair.json` and the self-check JSON;
   - an updated README: what changed, the numbers, and the frame ranges for QA. Keep only what QA needs to look at.
5. **Optionally**, if it takes under 10 minutes: re-cut the animatic's 1a segment (3.9–7.6 s) with the repaired bank, keeping the same timecodes and the same file names. If it would take longer, skip it and say so.

## Inputs
- The clip folder and its README, `walk.json`, `bank.json`.
- `assets/renders/hall/warm-modern/hall-2026-11-17/ht-frame.png` (and the HT canvas), the D0o still.
- The clay: `assets/blockout/house/framing/wm-entrance-2026-11-14/` and render-agent's `framing_wm_door_final.py` (import it, don't edit it).
- Your tools under `site/tools/transitions/` (`assemble.py`, `walk_test.py`, `repair_right_wall.py`, `turn_door.py`).

## Fixed rules
- 0 tokens. No var2. No commits, no keys.
- Don't edit a binding document, `data/`, or another agent's document or stills.
- Working files go in the scratchpad. Delete the bank when done and say what you deleted.
- Return a short Hebrew summary: which fix, the self-check numbers, the walk test and the end lock, the QA frame ranges, and whether the animatic was re-cut.
