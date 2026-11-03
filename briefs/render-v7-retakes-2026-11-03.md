# Brief: the paid v7 retakes and the test-page grading (render-agent, 2026-11-03)

The owner answered the decisions meeting (`status/decisions-meeting-2026-11-03.md`; answers in `status/decisions.json`, studio rules ב.10–12 and the ז log of 2026-11-03). Your zero-token round of today (lock v2, grading v2, the four code fixes, recipe v8) is committed.

## The answers
- **V7Q1 = (b):** a new living-room camera, one metre closer. **M0 is not in this brief.** master-designer is writing house plan 1.2 now; you get a separate brief for the new clay and the M0, M0p, M0x renders. The composite `m0-v7-r2-fix.png` is discarded (keep the files, don't use them).
- **V7Q2 = yes:** every other camera stays.
- **V7Q3 = yes:** B1 and B2 get the two 6.5 products for the test: the sea-grass floor planter (`floor-planter-aliexpress-seagrass-straight-planter-basket-30`, 30×30, with a fern) and the matte black brush (`toilet-brush-aliexpress-matte-black-steel-cylinder-245996`, 8×38). Positions per the designer's review §5.3.
- **V7Q4 = yes, BIB1 = all six:** the test page is graded to the Bible's exposure targets, not the +0.2 stop ceiling.
- **TR3 = all four:** no snow; the master-bath opening as an empty lit passage; transition-only products empty; no floor lamp in M0.
- **Recipe v8 is in effect for this round** (your proposal `docs/render-recipe-nordic-v8-2026-11-03.md`: no whole master as a reference, cropped hard references with sizes and u/v in the prompt line, the SCALE paragraph, lock_v2 at G1.4 as the acceptance check, grading order v2). It is still marked a proposal in the docs; log every job as "v8".

## Tasks
1. **Grading to the Bible targets (0 tokens).** Add a flag to `process_v8.py` that grades to the targets instead of the ceiling: the lit wall next to the window at the Bible's L target (today's "אור" chapter), the window wall at L 80–88 (BIB1 B1), black point 12–15, the v2 roll-off, zero clipped pixels, no saturation shift near white (B4), the hall 2/3 stop darker than the living room (B5). master-designer is writing these into Bible 1.8 in parallel; use the numbers as stated in `status/decisions.json` BIB1 and the current Bible. Re-grade all 22 v7 frames and the four accepted fixes (K-boy, K-girl, W0, K-boy-0 `-fix.png`) into `*-graded-v3.png` (+ `-frame-v3`, `-graded-os6-v3` where the frame has overscan), `*-measurements-v3.json`, and `regrade-v3-summary.json` with the measured L per target and the stop delta from v2.
2. **Four paid retakes, recipe v8, one attempt each,** in this order, with `var2_estimate_cost` before every job and a stop if a job is not 600:
   - **W0-in r2** from `assets/prompts/poses-v7.nordic/pose-w0-in-v7-r2.txt` (W0 crops instead of the master; the plant as in W0).
   - **K-girl-0 r2** from `assets/prompts/poses-v7.nordic/pose-k-girl-0-v7-r2.txt` (crops; the near wall per the Bible: band only on the east and north walls).
   - **B1 r3** from `assets/prompts/recipe-v5.nordic/b1-v7-r3.txt` with the two products above.
   - **B2 r3** from `assets/prompts/recipe-v5.nordic/b2-v7-r3.txt`, with B1 r3 as a cropped reference (never the whole frame).
   Rewrite each prompt into the v8 form as a new file next to it (`*-v8.txt`), keeping the designer's content and the TR3 defaults; verify each prompt carries "no snow" and the other TR3 defaults.
3. **Acceptance per frame:** `lock_v2` at the G1.4 thresholds (0.5% of the frame for a master; 2 px per strip after register for a pan participant, W0-in and K-girl-0 and both bath frames are pan participants), the furniture-edge ratios, the window p99, the forbidden list, the product boxes (±15%). Write `<id>-r2-lock-v2.json` / `<id>-r3-lock-v2.json`, the overlays, the measurements and the graded-v3 files, and one contact sheet of the four new frames next to their predecessors (`assets/renders/house-nordic-retakes-sheet-2026-11-03.jpg`).
4. **A second attempt** only when lock_v2 fails on scale or position, at most one in total across the four, from the reserve. A second scale failure goes to the v8 route (code composite + one image-to-image pass) **only in your next brief**, not now.
5. **Budget: 2,400 for the four jobs + 600 reserve = 3,000 maximum.** Record every job in `assets/renders/house-nordic-v7-2026-11-02/jobs.json` (append) or a new `jobs-retakes-2026-11-03.json`, with the price.

## Fixed rules
- If the var2 MCP answers "requires authentication", stop and report; the owner re-authorizes in the connector settings. Never ask for codes or tokens.
- New files only: no v7 frame, prompt, measurement or binding document is overwritten. Your pipeline scripts may change with the old behaviour kept under a flag.
- No commits. Manifest entries are fine.
- Return a short summary in Hebrew: tokens per job and in total, lock_v2 numbers per new frame with pass/fail, the grading-v3 result (L per target, how many frames now meet the Bible), and what waits for the owner or for house plan 1.2.
