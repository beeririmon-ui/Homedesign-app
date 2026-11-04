# Brief: G1 on the M0 1.2 composites, the fix2 frames, CB-0 and grading v5 (qa-agent, 2026-11-04)

render-agent's latest zero-token round is in (board log 2026-11-04, the line "render-agent (M0 1.2 בקוד, ניקוי ארבעת התיקונים, גריידינג v5, CB-0)"; brief `briefs/render-m0-composite-and-cleanup-2026-11-04.md`). Per playbook §5.3 nothing is a reference until you ran G1.

## Scope
1. **M0 1.2 composites:** `assets/renders/living-room/nordic/v8/m0-v8b-r2-fix.png` (+ `-fix.json`, lock overlay), `assets/renders/poses/nordic/v8/pose-m0p-v8b-fix.png`, `pose-m0x-v8b-fix.png`, against the round-5b clays (`assets/blockout/house/framing/round5b/`). render-agent says the furniture now sits on the clay but the **room shell** is drawn in another perspective (back-wall floor line 20–66 px high, the sill ~45 px) in all four paid renders. Confirm or refute with your named-edge tool, and say whether any code correction of the shell is realistic (e.g. a per-region homography of the back wall and floor) or whether only a new render can fix it.
2. **The fix2 frames:** `b1-v7-r3-fix2`, `b2-v7-r3-fix2`, `pose-w0-in-v7-r2-fix2`, `pose-k-girl-0-v7-r2-fix2` (script `fix_v9.py`): G1.4, G1.1 for every moved or scaled object, G1.12 at 100% for seams and fill artefacts (render-agent reports two small light lumps right of the fern in B1, a soft rectangular floor patch right of the basket in B2). K-girl-0: settle whether its register is unstable (named lines within ±0.6 px, register +0.89%).
3. **CB-0 recomposed from B1 r3 fix2** (`pose-cb-0-v7-b1r3.png`, `-overlap.json`, script `recompose_cb0.py`): the overlap (0.06 px, ΔL 0.8 reported) and, above all, the seam at u ≈ 0.30 and the left part kept from the old CB-0.
4. **Grading v5** (`regrade-v5-summary.json`, 33 rows) against Bible 1.8.4, including the corridor targets (L* 72–75) at the points render-agent verified on the clay, and H0's hall wall (80.1 vs 75–78).

## Output
`qa/reports/2026-11-04-m0-fix2-cb0-g1.md` (Hebrew) and `.json` (same record shape as before), overlays under `qa/reports/2026-11-04-m0-fix2-cb0-g1/`. A verdict per frame with `may_reference` and `may_pan_endpoint`, and which transitions are now unblocked (T-CBath above all, V4/T-HW, P-B, T-E0/T-LD).

## Fixed rules
New files only; no edits to existing files; no commits; no var2, no installs, no network, no npm. Return a short summary in Hebrew: the verdict table, the M0 shell answer, and the unblocked transitions.
