# Brief: G1 again on the four fixed retakes and on grading v4 (qa-agent, 2026-11-04)

Your G1 of 2026-11-03 (`qa/reports/2026-11-03-retakes-g1.md`, §11) named code fixes for the four v8 retakes and grading fixes. render-agent applied them at 0 tokens (board log 2026-11-04, three render-agent lines; commits d1dba18f, b4589aa4 and the W0-in affine after it). Per playbook §5.3 a frame becomes a reference only after you ran G1 on it.

## Scope
- **The four fixes:** `assets/renders/bath/nordic/v7/b1-v7-r3-fix*`, `b2-v7-r3-fix*`, `assets/renders/poses/nordic/v7/pose-k-girl-0-v7-r2-fix*`, `pose-w0-in-v7-r2-fix*` (the `-fix.png`, `-fix.json`, `-lock-fix.json`, `-graded-fix-v4.png`, `-measurements-fix-v4.json`, overlays). Script: `assets/renders/house-nordic-v7-2026-11-02/fix_v8.py`.
- **Grading v4:** `regrade-v4-summary.json` (30 rows) and the `*-graded-v4.png` files, against Bible 1.8.3 (`docs/design-bible/nordic.md`).
- **render-agent's two disputes of your findings:** B2 r3 vanity right side and mirror head as measurement artefacts (parallel edges; a sloped line against the reflected ceiling), and the W0-in chair top (clay line at 835, not 800). Settle each with your named-edge tool.

## What to measure
1. G1.4 with your four measures, including named edges, on each fix; G1.1/G1.3 fidelity for every scaled or moved object (the prints and doll in K-girl-0, the basket, brush and plinth area in B1, the pen cup in W0-in, the baskets and the mirror corner in B2) against their boxes ±15%; G1.12 at 100% for seams, halos and fill artefacts left by the code edits.
2. Grading v4 against Bible 1.8.3: confirm or refute "13 of 30 pass in full", with your own points; wall hue after the masked correction (no halos at the masks); C* absolute; the window wall; C0 on S1's stops and the C0/S1' pair (G1.14).
3. The pan pairs that the fixes unblock: B1 r3 fix ↔ B2 r3 fix (P-B), K-girl ↔ K-girl-0 r2 fix (T-CGirl), W0 ↔ W0-in r2 fix (T-HW, video endpoint), and whether B1 r3 fix may serve as the source for re-composing CB-0 (T-CBath).
4. A verdict per fix: pass for the test, fail (criterion and number), or cannot measure; `may_reference` and `may_pan_endpoint`.

## Output
`qa/reports/2026-11-04-retakes-fixes-g1.md` (Hebrew) and `.json` (same record shape as on 11-03), overlays under `qa/reports/2026-11-04-retakes-fixes-g1/`.

## Fixed rules
- New files only; no edits to existing files; no commits; no var2, no installs, no network, no npm. `python3.12 -I` for Pillow, `~/.venvs/motion/bin/python` for OpenCV.
- Return a short summary in Hebrew: the pass/fail table for the four fixes, your verdict on grading v4, the two disputes settled, and which transitions are now unblocked.
