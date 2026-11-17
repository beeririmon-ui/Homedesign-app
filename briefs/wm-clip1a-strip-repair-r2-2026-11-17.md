# Brief: clip 1a, strip repair round 2 (motion-agent, 2026-11-17)

## Why
QA failed clip 1a on three medium findings, all in the code repair (`qa/reports/2026-11-17-clip1a/README.md`, and its JSON and evidence images). The melt is gone and both end locks hold. Everything else passed: the band right of the walnut, the start lock, the herbs, the geometry, the walk test and exposure. The fix stays in code, 0 tokens. No second take.

## The three findings (bank frames)
1. **C1A-M1, 123–124:** the right jamb's black outline is still there. At 123 it runs the full height (1,065 of 1,080 rows, L* 18 against 71), and at 124 patches remain. Your selfcheck measured at the wrong x. Erase it at its real x. QA suggests starting the jamb's exit at 122.
2. **C1A-M2, 130–140:** sharp grey shards in the ceiling and in a floor triangle under the armchair (L* 33–38 against a ceiling at 81.5). They flicker between even and odd frames. In the projection, discard whatever is stretched across a depth jump, and fill from the next source instead of inpainting.
3. **C1A-M3, 136–141:** a dark, curving seam runs through the window and the birch (the birch NCC drops from 0.97 to 0.31). Take the whole window from one source (HT), and keep the seam outside the glass.

Also, in the clip README, correct the line saying the outline is erased up to 125, and the two numbers QA lists (C1A-I4).

## The work (0 tokens, no var2 calls at all)
1. Fix M1, M2 and M3 in `repair_strip_1a.py`.
2. **Self-check at the right places:** measure the outline at the jamb's real x per frame, look for shards (dark, sharp regions in the ceiling and floor of the strip, and even/odd flicker), and check the birch NCC across 134–143. Check the numbers against the frames, not only the code's idea of where things are.
3. The walk test and the end lock, as before.
4. **Outputs** in `assets/video/transitions/warm-modern/clip1a-d0o--ht/`:
   - the repaired `bank-preview.1920.30fps.mp4`, replacing the current one (keep `bank-preview.unrepaired...` as it is);
   - new before-and-after look images for 120–143 at 100%;
   - `repair.json` and `selfcheck.strip.json` updated;
   - the README updated, with the QA frame ranges for the re-check: bank 120–143 only.
5. **Re-cut the animatic's 1a segment** with the fixed bank (the same 16 frames, 213–228). Keep the same file names.

## Fixed rules
- 0 tokens. No var2. No commits, no keys.
- Don't edit a binding document, `data/`, or another agent's document or tool (QA's report and the backlog are QA's).
- Working files go in the scratchpad. Delete the bank when done.
- Return a short Hebrew summary: per finding what you did and its number, the walk test and the end lock, and whether the animatic was re-cut.
