# Brief: a three-model test for the living-room shell (render-agent, 2026-11-05)

**The owner (2026-11-05, decision M0S1):** "ניסוי קטן ב-3 מודלים, עד 1,600". QA found (`qa/reports/2026-11-04-m0-fix2-cb0-g1.md`, the M0 shell section) that in all four paid M0 1.2 renders gpt-image-2-5 drew the room shell from another camera position: floor line −16…−46 px, sill −28…−31, the back wall's vanishing point moved; a single homography leaves 5–18 px and a back-wall homography misses the window wall by 27–32 px (parallax). Code can't fix it. The furniture and the triptych are already correct in code (`m0-v8b-r2-fix2`).

## The goal
A shell that sits on the round-5b clay (`assets/blockout/house/framing/round5b/M0.png`) within the G1.4 lock for a master (0.5% of the frame; the named lines of QA's tool), so that the existing furniture composite and the triptych can be laid on it. The furniture in the new render doesn't matter much: your code composite replaces it.

## The test (one attempt per model, `var2_estimate_cost` before each; stop if any estimate differs from the price below)
| # | Model | Why | Price |
|---|---|---|---|
| 1 | `seedream-5-pro` 2K, `aspect_ratio: auto` | its catalog note: "edits that should keep the source framing — aspect_ratio=auto matches the input image"; up to 10 inputs | 650 |
| 2 | `nano-banana-2` 2K | had the best clay lock in recipe test A ("C 4.5: excellent lock, grey dead room"); light and life now come from the v8 prompt and grading v5 | 350 |
| 3 | `gpt-image-2-5` 2K sunburst | only if 1 and 2 both fail the shell lock, with the new prompt below | 600 |
**Cap: 1,600.** Running 1+2 costs 1,000; 3 only if needed (1,600 total).

## The prompt
Start from `m0-v8b-r2.txt` and put the shell first: the clay is the camera; walls, floor line, cornice, window, sill and door stay exactly on the clay's lines (list them with their u/v from the clay checks); "do not move the camera, do not change the perspective or the horizon, do not widen the view". Keep the TR3 defaults, Bible 1.8.4 light (winter daylight; the back wall L 90–94; the window wall L 80–88), the hero furniture and the rest per slots 1.6, and the triptych's place empty or as on the clay (it goes in by code). Adjust the syntax per model (character limits, reference counts). The wall round (`wall-decor-cj-corn-husk-round-38`, RND3 test default) may go into the same pass with its card images as a reference: render-agent's spec in `m0-v8b-r2-fix2.json` (`pending_wall_decor`).

## Acceptance and composite
1. For each result: lock_v2 (edges v3) with QA's named lines on the **shell only** (floor line, cornice, sill, window, door, corner), the vanishing point of the back wall, the furniture ratios (for information), grading v5. A contact sheet `assets/renders/house-nordic-m0-model-test-sheet-2026-11-05.jpg` (clay | each model | lock overlays).
2. If one passes the shell lock: lay the furniture composite and the triptych on it in code (`fix_m0_12.py`, `art_m0_12.py`), as `m0-1-2-shell-<model>-fix.png` with its record, and the wall round if it came out right. Then M0p and M0x from the new M0 by your existing route (cropped references), **only within the 1,600 cap**; otherwise list them as the next step.
3. If none passes: stop and report the numbers per model; no further attempts.

## Fixed rules
- If the var2 MCP requires authentication, stop and report; never ask for codes or tokens.
- New files only, no commits.
- Return a short Hebrew summary: tokens per job and in total, the shell-lock numbers per model with pass/fail, the composite result, and the sheet path.
