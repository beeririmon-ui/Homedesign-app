# Brief: code fixes on the four v8 retakes, and the grading fixes (render-agent, 2026-11-04)

qa-agent ran G1 on your four retakes and on grading v3: `qa/reports/2026-11-03-retakes-g1.md` (§2 verdicts, §4 grading, §6 fidelity, §11 fixes) and `.json`, with the overlays and tools in `qa/reports/2026-11-03-retakes-g1/`. All four fail, all four now frame the clay, and the remaining gaps are local. This brief is everything that costs **0 var2 tokens**. M0 1.2 is a separate brief and waits for master-designer.

## Tasks
1. **Code fixes per QA §11.1,** with your `fix_v7.py` precedents (mattes, scale about the contact line, hole fills, a `-fix.json` per frame with what, how and the numbers):
   - **B1 r3:** remove the invented plinth under the basket and lower the basket 172 px to the floor (smooth wall behind, tiled floor below); scale the brush ×0.73 about its base. This is the reference candidate: aim for every named line within ±5 px after the fix.
   - **K-girl-0 r2:** the prints ×0.6 and the doll ×0.5–0.6 about its seat, as in the K-girl fix.
   - **W0-in r2:** lower the desk top, the drawer and the side panels 39–46 px onto the clay lines, as in the W0 fix (+0.036 H).
   - **B2 r3:** the basket ×0.85, the storage basket ×0.8, remove the object in the mirror corner. The vanity's right side (−43 px) and the mirror head: try in code; if a code fix would be visible, say so and leave it for the paid route.
   Files: `<id>-fix.png`, `-fix.json`, `-graded-fix-v4.png` (+ frame/os6), `-measurements-fix-v4.json`, `-lock-fix.json`, overlays. Never overwrite the retake files.
2. **Grading v4** (`process_v8.py`, new flag; v3 behaviour kept): QA §4 and §11.2. Wall hue after the lift reported and corrected by a masked hue correction on the walls when H > 40 (your pipeline has it from the M0 work; the sofa, oak and glass untouched); B4 as an absolute value, C* ≤ 7 on the wall patch; the window wall L 80–88 as a measurement point in every frame that has one (K-boy, K-girl, W0, MB0, M0); **C0 back to S1's stops** (no corridor number in the Bible; BIB2 is open); CB-0 measured on a white wall, not the limestone. Re-grade the 22 v7 frames, the 4 earlier fixes and the 4 new fixes into `*-graded-v4.png` and `regrade-v4-summary.json`, with per frame: L at each target, H, C*, black, window p99, and pass/fail against Bible 1.8.2.
3. **lock_v2 improvements from QA §3:** add QA's named-edge measure (`qa/reports/2026-11-03-retakes-g1/tools/edges_direct.py`) to your lock check, so the desk top in W0-in is measured and peaks on legs or parallel edges are not reported as furniture ratios. Re-run on the four fixed frames.
4. **What still needs a paid pass after the code fixes,** per frame, with the reason and the v8 route (composite + one image-to-image pass, 600). Don't run it.

## Fixed rules
- **No paid var2 job.** New files only; pipeline scripts may change with the old behaviour under a flag. No commits.
- Return a short summary in Hebrew: per fixed frame the named-edge and lock numbers before and after; the grading-v4 table (how many frames pass Bible 1.8.2 in full, and what still fails); and the paid passes that remain, with cost.
