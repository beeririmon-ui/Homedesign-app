# Brief: concept images for the three "middle" entrance variants (render-agent, 2026-11-15)

## Why
The owner saw the first concepts (`assets/renders/hall/warm-modern/concepts-2026-11-15/`) and said: "עכשיו הדלת מפוארת מידי..משהו באמצע אולי?" (FB6 in `docs/studio-rules-digest.md`). master-designer wrote three variants in the middle: chapter 10, "הכיוון האמצעי", in `docs/proposals/wm-entrance-magazine-2026-11-15.md`. The owner chooses from these images. They are for his choice only: not for the site, not locked, not keyframes.

## What to make
Three text-to-image concept images, 16:9, from the designer's prompts **as written** (copy them exactly):
1. **M1 "הזית בשביל":** the prompt in §10.4.8.
2. **M2 "קיר האבן":** the prompt in §10.5.8.
3. **M3 "הספסל הבנוי":** the prompt in §10.6.8.

## Model and money
- **flux-2, 1K, 16:9,** the same model as the first round, so the owner compares like with like. `var2_estimate_cost` before each send (live price today: 250 an image).
- **Cap for this run: 750 tokens.** One retry is allowed only for an image that breaks an item of the designer's rejection lists (§10.8 or the variant's own list), and the hard cap is then 1,000.
- No image-to-image, no references to supplier images, no other var2 call.

## Outputs
- `assets/renders/hall/warm-modern/concepts-middle-2026-11-15/`: `M1.jpg`, `M2.jpg`, `M3.jpg`; one contact sheet with the three in a row, labelled in Hebrew with the variant's name (right to left: M1, M2, M3), and **a second sheet that puts them on a scale:** D0 (`assets/renders/hall/warm-modern/door-2026-11-14/d0.png`) at one end, A-out and B-out (`assets/renders/hall/warm-modern/concepts-2026-11-15/`) at the other, M1–M3 between, so the owner sees where each sits; `jobs.json`; a short `README.md` (per image: what matches the designer's description, what the model invented or inflated, and how it reads at phone size 390×220).
- Working files in the scratchpad (EFF1).

## Fixed rules
- Tokens only for these images, inside the cap above.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Return a short Hebrew summary: the tokens spent, the paths (the three images and the two sheets), and one line per image on how close it is to the designer's description and whether it looks "in the middle".
