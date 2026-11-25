# Brief: FB12, the girl's prints become set G1 "painted bunnies", in code (render-agent, 2026-11-25)

## Why
The owner asked for child-appropriate prints in the kids' rooms (FB12). The designer screened the existing cards; see `docs/proposals/wm-fb12-2026-11-25.md`, ב.10.
- **The girl's room:** one set passed, G1. It replaces today's colourful flower prints (Type A) as the default.
- **The boy's room:** no set passed. It stays as it is; don't touch it.
- **G2:** rejected. The manager follows the designer: S02 is a cartoon toy bear.

All of this is 0 tokens, in code, with the existing tool.

## The task
Follow ב.10.5 exactly. It is the paste table and the 7 instructions.
1. **The three panels:**
   - **A:** B05;
   - **B:** B04;
   - **C:** B06.
   - The flat source images are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/kids-art-review/raw/`. Read them with `python3.12 -I`, from a script outside that folder.
   - Crop per the table. Re-measure the openings first (instruction 3).
2. **The tool:**
   - Extend `assets/renders/boy/warm-modern/stage1-2026-11-24/tools/kids_art.py` so `place()` takes each panel's own width and height, instead of a fixed 300×400 (instruction 2).
   - Keep the old behaviour as the default, so the boy's room rebuilds byte-identical. Prove it.
3. **The light:** one paper reference for the whole set, B05's paper (instruction 4).
4. **The outputs** in `assets/renders/girl/warm-modern/stage1-2026-11-24/`, with new names. Don't overwrite today's files; keep them for rollback.
   - the new framed-prints layer;
   - `K-girl-defaults-g1.png`, plus its `-frame`;
   - `K-girl-V2-g1.png` and `K-girl-V3-g1.png`, plus their frames;
   - a manifest entry or a `manifest-g1.json`, whichever the README convention says;
   - the README and checks updated.
5. **The checks** (instructions 5–6), in the script:
   - RND2 is 0 outside the three quads;
   - ΔE00 ≤ 3 per ink region against the source;
   - caramel at least 10%, pink at most 30%, green at most 10%, blue at most 3%;
   - each of V1–V3.
6. **A QA sheet,** `qa-sheet-g1.jpg`: the wall at ×2 before and after, and G1 with V2, V1 and V3 at ×1.

## Acceptance
- No seam or halo at the frame edges at ×2.
- The paper reads as paper, matte, with no glass.
- B06's taupe ground stays taupe, about 6–8 L\* below the other two.
- The darkest ink is at L\* 15 or more (WM-G1).
- **If code can't pass,** stop and report with crops. No var2.

## Fixed rules
- 0 tokens, no var2.
- Don't touch `data/`, `docs/`, `site/`, or the living-room or boy render folders (only the tool file, as above).
- Supplier images never go into the repo. Only the warped panels inside the layer, as with today's prints.
- Never `git stash`, `checkout`, `reset` or `commit`.
- The disk is tight (about 1.6 GB). Delete scratch.
- Return a short Hebrew summary: what was done, the measures, the regions for QA, and anything that failed.
