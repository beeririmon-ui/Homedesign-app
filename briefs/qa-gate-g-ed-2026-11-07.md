# Brief: the G-ED gate for story frames (qa-agent, 2026-11-07)

**The owner (2026-11-07) adopted CR1–CR9.** The source is `docs/creative-review-2026-11-06.md` §5; the decision is CR in `status/decisions.json`, and studio rules ז has it under "הכיוון החדש מאומץ". The adopted changes:
- CR9: a new gate, G-ED, for story frames: fidelity per visible product, grading guardrails, and the owner's eye. G1 stays for the tool.
- DIR1: the site opens on story frames.
- DIR2: each style is its own house, also in the tool.

You have effectively run this gate three times already. Your earlier reports are the basis:
- `qa/reports/2026-11-06-editorial-test-fidelity.md`
- `qa/reports/2026-11-06-editorial-phase-b-fidelity.md`
- `qa/reports/2026-11-07-editorial-fin2-ed4-country.md`

## Task
Write the gate as a document: `docs/ops/quality-gate-g-ed-2026-11-07.md` (Hebrew) plus `.json`, in the shape of `docs/ops/quality-gates-2026-11-02.*`. Number the checks G-ED.1, G-ED.2 and so on. For each check give what is measured, how, the tool or crop, and pass/fail. Cover at least these:
1. **Product fidelity per visible product, against its card:**
   - silhouette, colour, material, proportion, scale, count of parts (rings, legs, tassels);
   - the faithful / partial / no table with card ids;
   - which products must be "faithful" for the frame to pass: the starring products of §3.7, and anything with a hotspot.
2. **No invented sellable products**, and the "imitation set" rule: an unsold item that reads as part of our product's set fails. The country cups are the example.
3. **Masks:** after a targeted pass or a code fix, nothing changed outside the masks (your diff tool, `qa/reports/2026-11-07-editorial-fin2-ed4-country/tools/diffs.py`). No seams, halos or flat fill at 100% and ×4.
4. **Grading guardrails (CR5):**
   - no HDR look and no orange-teal;
   - clipped highlights at most 1% of the frame, the window excepted;
   - the style's light story is readable;
   - all judged by eye with these rails, not L targets.
5. **No readable text, no brand or design copies, the forbidden list.**
6. **The hotspot check:** every product that will carry a hotspot is visible enough to touch on a phone. Propose the threshold.
7. **Verdict states:** "not yet", "almost", "final test" (shown to the owner), and "approved for the site". The last needs G-ED passed plus the owner's explicit approval. Note: nothing goes on the site without QA (CLAUDE.md).
8. **Who runs what and when** in the recipe's order: base frame → QA → code fixes → targeted passes → QA → owner.

Then map the seven current frames to the states, using your 2026-11-07 report. Keep it to one line each.

## Fixed rules
New files only, no edits to existing files, no commits, no var2, no network. Return a short Hebrew summary: the list of checks in one line each, the verdict states, and the mapping of the seven frames.
