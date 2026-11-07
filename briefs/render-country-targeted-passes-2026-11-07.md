# Brief: the paid round after the code fixes: two passes in modern country, two rug passes (render-agent, 2026-11-07)

**The owner (2026-11-07, MC1):** "שני המעברים, ~1,300". These run after your zero-token code fixes. The base is `assets/renders/editorial-phase-b-2026-11-06/modern-country-A-fix1.png`, or whatever name your code-fix round gave it.

The source of both passes is QA, `qa/reports/2026-11-07-editorial-fin2-ed4-country.md` §2 (modern country) and §5:

| # | Area | What is wrong | Target | Model | ≈ tokens |
|---|---|---|---|---|---|
| 1 | The table, one crop with a mask | The bowl `bowl-cj-speckled-ivory-wide-bowl-21` is too deep. The runner `table-runner-cj-linen-look-sage-fringe` is about ×1.4 wide (≈457 px vs the bowl's 195; 45–48 cm vs the card's 33) | The bowl as an open "hat", as in ED4 Mediterranean (height/diameter ≈0.24). The runner at 33 cm against the bowl's scale; keep its fringe and the sage-grey linen look | seedream-5-pro 2K on the crop | 650 |
| 2 | The sill, one crop with a mask | The clay vase was drawn as a different amphora | From the card's crop: a tall egg with no neck, grooves, no handle and no holes | seedream-5-pro 2K on the crop | 650 |
| | | | | **Total** | **≈1,300 (cap)** |

## The route (as in ED4)
1. Run `var2_estimate_cost` before each pass, and stop if it differs from 650 by more than 10%.
2. For references, use the card crops (uploaded first) and the crop of our frame.
3. Composite back in code with an object mask:
   - nothing changes outside the masks (report px changed outside: 0);
   - match grain and light, with a contact shadow;
   - the cups stay as your code fix left them, with a plain glaze; they must not turn back into a set with the bowl.
4. One attempt per pass. If a pass fails, say why and stop; no second attempt.

## Output
- `modern-country-A-mc1.png` next to the base.
- `mc1.json` with the jobs, prices, masks and px changed.
- Before/after crops in `mc1-before-after/`.
- Add the frame to the ED4 sheet, or make a small `mc1-sheet.jpg`.

## Part 2: the rug passes (EDR1, the owner, 2026-11-07: "מעבר לכל אחד, ~1,300")
This part was added after the owner's answer. QA (2026-11-06 phase B and 2026-11-07) found the same rug drawn wrong in two frames. The card is `rug-cj-braided-wool-natural`: a flat braided wool rug in natural colour. Its braid rows must be readable, it must have no pile, and it must lie flat and low.

| # | Frame (base) | What is wrong | Model | ≈ tokens |
|---|---|---|---|---|
| 3 | Nordic A, `nordic-A-ed4.png` | The rug has a pile with fine tonal lines; it is not a flat braid | seedream-5-pro 2K on the rug crop, with a mask | 650 |
| 4 | Warm modern, `warm-modern-A-ed5.png` (your code-fix output; else `-ed4`) | The rug has tonal cream ribs and is too thick | seedream-5-pro 2K on the rug crop, with a mask | 650 |

Same route as above:
- Use the card crop as the reference.
- The furniture legs and anything standing on the rug stay as they are. Mask around them, or rebuild their contact shadows in code.
- Outside the masks, 0 px change.

Outputs: `nordic-A-ed5.png` and `warm-modern-A-ed6.png` (or the next suffix), recorded in the same `mc1.json` under a "rugs" key, with crops in `mc1-before-after/`.

**The cap for the whole round (parts 1 and 2): 2,600.**

## Fixed rules
- If var2 requires authentication, stop and report; never ask for codes or tokens.
- New files only, no commits.
- Test only, not for the site.
- Return a short Hebrew summary: tokens per job and total, the px numbers, and your honest read at 100%.
