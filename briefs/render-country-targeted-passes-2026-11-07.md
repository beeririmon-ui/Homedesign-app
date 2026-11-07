# Brief: two targeted passes in modern country (render-agent, 2026-11-07)

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

## Fixed rules
- If var2 requires authentication, stop and report; never ask for codes or tokens.
- New files only, no commits.
- Test only, not for the site.
- Return a short Hebrew summary: tokens per job and total, the px numbers, and your honest read at 100%.
