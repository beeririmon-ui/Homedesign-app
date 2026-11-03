# Brief: gate G1 on the v8 retakes and the grading v3 (qa-agent, 2026-11-03)

render-agent delivered four paid retakes in recipe v8 and re-graded all v7 frames to the Bible's targets (board log 2026-11-03, "render-agent (ריטייקים v7 במתכון v8 + גריידינג v3)"). Per playbook §5.3 nothing is a reference until you ran G1 on it. This is that check.

## Scope
1. **The four retakes:** `assets/renders/work/nordic/v7/`? No: the poses are in `assets/renders/poses/nordic/v7/pose-w0-in-v7-r2*` and `pose-k-girl-0-v7-r2*`; the bath frames in `assets/renders/bath/nordic/v7/b1-v7-r3*` and `b2-v7-r3*` (raw in `raw/`, graded-v3, lock-v2 records and overlays, boxes-v3). Clays: `assets/blockout/house/framing/round4/` and `round4/r3-2026-11-03/` for B1/B2. Job records: `assets/renders/house-nordic-v7-2026-11-02/job-*.json`, `jobs-retakes-2026-11-03.json`. Prompts: `assets/prompts/**/…-v8.txt`.
2. **Grading v3** of the 22 v7 frames and the 4 code fixes (`*-graded-v3.png`, `*-measurements-v3.json`, `assets/renders/house-nordic-v7-2026-11-02/regrade-v3-summary.json`), against Bible 1.8 (`docs/design-bible/nordic.md`: B1 two targets, the lit wall next to the window L 90–94 and the window wall L 80–88; black 12–15; roll-off; B4 chroma near white; B5 the hall 2/3 stop below the living room).

## What to measure
- **G1.4 lock with scale**, with your own tools (`qa/reports/2026-11-02-v7-g1/tools/`, `pan_reproject.py register/check`), independently of render-agent's `lock_v2.py`; compare your numbers with its `*-lock-v2.json` and say where they differ.
- **Exposure and light** against Bible 1.8, per frame, independently of `regrade-v3-summary.json`; confirm or refute "25 of 26 on target, 24 of 26 pass".
- **The forbidden list, the window, the overscan** (3% where §6.4 of the transitions render plan requires it).
- **Density** under the test rule (studio rules ב.11: every slot with an approved product filled; empty slots listed as sourcing tasks) and, as a second column, an estimate under the new rule V7Q6 (ב.13, `docs/proposals/density-count-rule-2026-11-03.md`); the implementation of V7Q6 in the clay selfcheck is a separate task, say what it needs.
- **Fidelity** of the new bath products (the sea-grass floor planter, the matte black brush) against their cards' images and sizes, and the invented object render-agent reports in B1 r3 (a limestone plinth under the basket): confirm and measure.
- **The pan participants:** W0-in vs W0, K-girl-0 vs K-girl, B1 r3 vs B2 r3 and vs CB-0: `check` in the overlap, 2 px per strip.
- **The products baked in**, with stock unverified marked (G8.6).
- Also, quickly: the site evidence folder `qa/reports/2026-11-03-site/` exists and `python3.12 -I scripts/economics/no_loss.py --check-derived` reproduces 0 losing (G8.1/G8.2); don't run npm.

## Output
- `qa/reports/2026-11-03-retakes-g1.md` (Hebrew) and `qa/reports/2026-11-03-retakes-g1.json` (one record per frame: `frame`, `criteria[]` with `id`, `value`, `threshold`, `pass`, `verdict`, `may_reference`, `products_unverified[]`), overlays under `qa/reports/2026-11-03-retakes-g1/`.
- A verdict per retake: pass for the test, fail (criterion and number), or cannot measure; and whether it may serve as a reference or a pan endpoint.

## Fixed rules
- New files only; no edits to existing files; no commits; no var2, no installs, no network. `python3.12 -I` for Pillow, `~/.venvs/motion/bin/python` for OpenCV.
- Return a short summary in Hebrew: a pass/fail table for the four retakes, your verdict on the grading v3 claim, and what blocks the transitions.
