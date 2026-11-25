# Brief: FB12 stage 0, a clean M0 plate without the coffee table (render-agent, 2026-11-25)

## Why
The owner asked to replace the living-room coffee table (FB12, `docs/studio-rules.md`). The designer's proposal is `docs/proposals/wm-fb12-2026-11-25.md`, part א (read א.5–א.7 fully). It picks path R:
- the old table, which today is a fixed piece baked into `base.png`, leaves the plate and the walk;
- the new table becomes a product layer that enters in reveal B.

This brief is stage 0 only, **in code, 0 tokens**. Paid steps (the 450 fallbacks and the new table) wait for the owner's FB12-T answer, per SPEND2.

## The task
1. **The clean plate.** Remove the old table and its contact shadow from M0's `base.png`, the one the r9 manifest uses (find it under `assets/renders/living-room/warm-modern/`).
   - **The floor:** fill the parquet along the board lines, using the floor homography.
   - **The sofa:** fill the lower strip of the sofa front and the plinth from the sides.
   - **The mask:** the fixed-furniture mask (fa) becomes the sofa and armchair only.
   - **The result:** a new plate file with a new sha. Don't overwrite the old one; keep it for rollback.
2. **The rug under the table.** In the rug layer, fill the area the old table hid. The rug layer has no pixels there today. Synthesise it on the rug plane from the visible rug, in the same light. The new table and its shadow will cover part of it later.
3. **The bowl and candlesticks** stand on the old table today (z 65). Until the new table exists:
   - Mark them, in the manifest, as hidden in the defaults for the preview. Don't delete their layers.
   - Say how the defaults read without them.
4. **Rebuild** the M0 defaults from the clean plate. RND2 must be 0 outside the old table's region, its shadow and the rug fill.

## Acceptance
- **At ×1–×2:** no seam, smear or repeated pattern on the parquet, rug or sofa front.
- **Board lines** continue straight through the filled area, measured against the homography.
- **Black point** within WM-G1.
- **RND2:** 0 outside the changed regions.
- **If code can't pass ×2,** stop and report with crops. Don't send to var2. The 450 fallback waits for FB12-T.

## Outputs
- the clean plate, the rug fill layer, and the rebuilt defaults and frame;
- a `qa-sheet-fb12-stage0.jpg` at ×2 of the table region, before and after;
- an updated README, checks and manifest, plus the living-room entries in `assets/manifest.json` (re-read it before writing);
- a note for motion-agent: the clean plate's path and sha, and the floor homography, which it uses to erase the table from HDx2 and clip 2 of the arrival.

## Fixed rules
- 0 tokens, no var2.
- Don't touch `data/`, binding documents, `site/`, the arrival masters, or other rooms.
- Never `git stash`, `checkout`, `reset` or `commit`.
- The disk is tight (about 1.8 GB). Keep scratch small and delete it.
- Return a short Hebrew summary: what was done, the measures, the regions for QA, and the note for motion.
