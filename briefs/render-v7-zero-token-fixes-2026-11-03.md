# Brief: zero-token fixes and recipe v8 after the v7 reviews (render-agent, 2026-11-03)

Two reviews of your v7 set are in:
- master-designer: `docs/render-v7-review-2026-11-02.md` (verdicts §1, the four broken locks §2, zero-token jobs §7, retakes §8).
- qa-agent, gate G1: `qa/reports/2026-11-02-v7-g1.md` (method §1, exposure §4, lock and scale §5, fidelity §6, fixes §10) with `qa/reports/2026-11-02-v7-g1.json`, the overlays and the tools under `qa/reports/2026-11-02-v7-g1/`.

The paid retakes wait for the owner's answers (V7Q1–V7Q4 in `status/decisions.json`). This brief is everything that costs **0 var2 tokens** and does not depend on those answers.

## Tasks
1. **A scale-aware lock metric.** Your `clay_lock` reported M0 as locked while the sofa was 1.20–1.23× the clay. QA's measure that worked: `pan_reproject.py register` + ECC on tiles + the edges of the fixed furniture (QA §5, tools in `qa/reports/2026-11-02-v7-g1/tools/`). Adopt it as the lock check in your pipeline (`process.py` or its successor), with the thresholds of gate G1.4 (`docs/ops/quality-gates-2026-11-02.md`): 0.5% of the frame for a master, 2 px per strip for a frame that takes part in a pan. Re-run it on all 22 v7 frames and write one record per frame next to the existing measurements (`*-lock-v2.json`). Don't overwrite the old files.
2. **Grading.** QA §4: the window p99 lands at 97.4–97.6 against the 97 ceiling in 7 frames because of the order of the S-curve and the roll-off in `process_v7`; and B2's exposure sample point fell on the mirror. Fix both in the pipeline, re-grade the v7 frames into new files (`*-v7-graded-v2.png`), and record the measured values. Keep the +0.2 stop ceiling: V7Q4 (grading to the Bible's target) is still an owner question.
3. **The designer's zero-token fixes** (review §7), written as new files next to the originals (`*-v7-fix.png`), each with a short note of what changed and how:
   - K-boy: the window view without snow.
   - K-girl: the doll at the slot's size (today 1.4×).
   - W0: the desk, shelf and chair heights (about 0.035 high).
   - K-boy-0: the sage band must not wrap the near wall (Bible: band only on the east and north walls).
   - M0: the size fix in code (sofa, coffee table, pendant) as the base for the one paid pass in review §2.1. This is conditional on V7Q1 = (a); if the owner picks a new camera, it is discarded. Do it last.
   - Not now: the H0 door view (it copies the final M0, which doesn't exist yet).
4. **Recipe v8, as a proposal** in `docs/render-recipe-nordic-v8-2026-11-03.md`: from your own lesson (a whole master as reference copies its framing) and QA §10: no whole master as a reference; cropped hard references for the fixed furniture; a stronger clay-lock paragraph; the reference order per the wow pass; and the new lock metric as the acceptance check. Mark everything that changes the recipe doc (`docs/render-recipe-nordic-2026-10-24.md`) as a proposal.
5. **Mask support.** Check through the var2 MCP (`var2_list_models`, 0 tokens) whether any model accepts a mask or a masked edit at 2K, for the M0 fix pass (`assets/prompts/recipe-v5.nordic/m0-v7-r3-masked.txt`). Report the model, the price and the constraints; don't run a job.

## Fixed rules
- **No paid var2 job.** 0 tokens. If something needs a render, list it under "waits for the owner".
- New files only: don't overwrite any v7 frame, measurement or prompt. The pipeline scripts you own (`process*.py`, `tone_r4.py`, `framing_r4.py`, the house-nordic-v7 scripts) you may change, with the old behaviour kept under a flag or a copy.
- No commits. No edits to binding documents.
- Return a short summary in Hebrew: the new lock numbers per frame, the grading result, which fixes are done, the v8 proposal in 5 lines, and the mask-model answer.
