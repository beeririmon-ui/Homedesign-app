# Brief: the IMG1 throw P2 v3, one code fix (render-agent, 2026-11-12, 0 tokens)

**The source:** `qa/reports/2026-11-12-img1-throw-fixed-v2.md` plus `.json`, and the folder `qa/reports/2026-11-12-img1-throw-fixed-v2/`, including its tools `edge_loss_2d.py`, `gimg6_segments.py`, `decontam_v2.py` and `specks_v2.py`.

**The folder:** `assets/renders/products/img1-pilot-2026-11-12/`. v2 is `sofa-cover-cj-cotton-muslin-fringe/p2-nano-fixed-v2.png` (ee131b02), built by `tools/fix_throw_nano_v2.py`. Read `source-record.json` and `jobs.json`.

**v2 passes 5 of 6.** What fails is edge loss in the top corner: p99 of 15.2 px per edge point and 20 px per row, against a limit of 12.75. The 10 px erosion wipes out whole thin threads. Two thread tips that are certainly product were lost, about 18 px each. There's also a 5 px step and grey ghosts at the edges of the crop box.

## The fix, in a new file `tools/fix_throw_nano_v3.py`
Leave v1 and v2 and their tools untouched.
1. **Inside the corner crop:** a pixel that's product keeps the alpha it had before the crop.
   - "Product" means at least 5 L* above the local paper envelope, and connected to the body.
   - Do it in the matte step, before the colour step and the speck step.
   - In QA's simulation this gives a p99 of 2.0 per point and 12.3 per row, and item 4 stays at 75.5%.
2. **The crop region:** set it by distance from the contour, with a transition of at least 20 px, instead of a rectangle. No step and no ghosts.
3. **Item 3 in the corner:** ΔE00 to the fabric may return to about 3.02, which is on the line. Either leave those gaps half-open, or show that they're within 3.
4. **Optional:** in the fullres file, clear the detached 3 px piece at alpha 255 at (1635,1618).

## Acceptance (QA's tools, reported per segment)
- edge loss p99 ≤ half a cell (12.75 px) in every segment, measured both per point and per row;
- every segment ≥ 50% in G-IMG 6;
- decontamination ≥ 95% away from the background;
- 0 specks;
- fidelity unchanged (ΔE00 ≤ 3, the waffle reads);
- a rebuild from the raw identical across two runs;
- a new sha256 in `source-record.json`, with `qa_verdict` "partial (QA throw-fixed-v2), pending QA re-check".

## Fixed rules
- 0 tokens, no var2, no commits.
- Supplier images aren't needed here.
- Return a short Hebrew summary with the numbers.
