# Brief: P6b, the caramel pillowcases in the warm-modern master bedroom (render-agent, 2026-11-10)

**The owner (2026-11-10, SPEND2):** "את יכולה לנצל עוד מהקרדיט של var2 במידת הצורך". So this pass no longer waits for SPEND1 week 3.

**The source:** `qa/reports/2026-11-10-ged-master-fix4.md`.
- **The problem:** the caramel pillowcases on `warm-modern-MB-A-fix4.png` carry flanges. The card is a plain envelope pillowcase.
- **The fix:** P6b, plus one code fix: the dark spot in the gap between the pillowcases, at x ≈ 2000–2060 and y ≈ 760–812. Continue the gap lines up to the top of the pillow.

## The inputs (prepared earlier)
In `assets/renders/master/editorial-2026-11-07/warm-modern/`:
- `raw/P6b-input.png` (1320×566), `raw/P6b-mask.png`, `raw/P6b-protect.png`, `raw/P6b-mask-overlay.jpg`.
- The prompt: `assets/prompts/master-editorial-2026-11-07/P6b-wm-caramel-pillowcases.txt`.
- Reference 1: a crop of the pillowcase card (find it where P6 took it, in `mb1-fix*.json`). Supplier images are uploaded to var2 as references only, and never committed.

## The model
1. **First, a check at 0 cost:** grok-imagine-image-2 `segment-map` is free. See whether it gives clean segments for the two pillowcases.
   - **If it does:** `segment-edit` on those segments only, about 250 tokens. Every other pixel stays untouched.
   - **If it doesn't, or the result fails:** seedream-5-pro i2i 2K on the prepared crop, 650 tokens. Remember the lesson: seedream returns its own aspect ratio, so the crop has to be in a native ratio.
2. **The cap for this pass:** 900 in total (one grok attempt plus one seedream, or a single seedream). Run `var2_estimate_cost` before each job.

## Acceptance
- **Compositing:** in code. 0 px change outside the mask; check it with a diff.
- **The pillowcases:** plain envelopes, with no flange, border or flat strip. The colour stays caramel, matching the card, ΔE00 ≤ 5 against the card's swatch.
- **Kept unchanged:** the bouclé lumbar cushion, the cream pillows behind, the duvet and the gap. Check at 100% and ×4.
- **The spot in the gap:** fixed.
- **The output:** `warm-modern-MB-A-fix5.png` plus `mb1-fix5.json` (jobs, tokens, model, diff numbers) plus a before/after sheet.

## Fixed rules
- If var2 asks for authentication, stop and report. Never ask for codes.
- New files only, no commits.
- Return a short Hebrew summary: tokens per job and the total, the diff numbers, and your honest read.
