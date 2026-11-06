# Brief: the editorial-frame test (render-agent, 2026-11-06)

**The owner (2026-11-06):** "משהו בזה לא עובד... נכנסנו יותר מדי לתבנית ואיבדנו קצת מהקסם ומהיכולות של ה-AI... להקפיץ את זה באמת לרמת מגזין", then "אני ממש צריך את זה 10 פעמים יותר טוב עם כל המוצרים שאספנו שיהיה ברמה ממש גבוהה." **Decision ED1:** an editorial-frame test for the Nordic and the warm-modern living room, two models each, **up to 2,600 var2 tokens**.

The direction is master-designer's `docs/creative-review-2026-11-06.md`: read §1 (what went wrong), §2 and §2א (three layers; density "with all the products": 10–14 products per frame in 3–4 overlapping islands, three depth layers), §3 (the concept per style: Nordic and warm modern), §3.7 (the starring products per style, card ids) and §4.0 (the step ready to run, with the full English prompts and references).

## This is a different kind of job
- **No clay lock, no fixed camera, no 24 mm, no grading to targets, no density count.** The room's architecture, light, time of day, camera and styling follow the review's concept for the style. Let the model do what it is good at.
- **What stays strict:** the products. Every product shown must be faithful to its card (silhouette, colour, material, proportion); no invented products; no text; no brand copies; the forbidden list. Products enter as references (cropped product images from the cards and, for the Nordic hero furniture, crops from our frames), uploaded first.

## The jobs (estimate each; stop if an estimate differs by more than 10%)
| # | Style | Frame | Model | ≈ tokens |
|---|---|---|---|---|
| 1 | Nordic | A, the wide editorial frame (§4.0) | nano-banana-2, 2K | 400 |
| 2 | Nordic | A, the same brief | gpt-image-2-5, 2K sunburst | 600 |
| 3 | Nordic | B, the window-corner vignette (§4.0) | nano-banana-2, 2K | 400 |
| 4 | Warm modern | A, per §3 and §3.7 | nano-banana-2, 2K | 400 |
| 5 | Warm modern | A, the same brief | gpt-image-2-5, 2K sunburst | 600 |
| | | | **Total** | **≈2,400 (cap 2,600)** |
If nano-banana-2 can't take enough references for frame A, split the references across the most important products and say which were left out. No second attempts within this test.

## Light post-processing only
No grading to numbers. At most: a gentle overall exposure and white balance to taste, highlight roll-off so nothing clips, and nothing that flattens the light the model drew. Keep the raw files.

## Output
- Raw and lightly finished files under `assets/renders/editorial-test-2026-11-06/<style>/`, the prompts as files, the job records with prices.
- One sheet for the owner: `assets/renders/editorial-test-2026-11-06/sheet.jpg`, the five frames large, each labelled with style, frame, model; plus, small, the current Nordic M0 for comparison.
- A short product list per frame: which cards appear, and your own quick fidelity note per product (qa-agent does the formal check afterwards).

## Fixed rules
If var2 requires authentication, stop and report; never ask for codes or tokens. New files only, no commits. Test only, not for the site. Return a short Hebrew summary: tokens per job and total, your honest read of each frame, the product notes, and the sheet path.
