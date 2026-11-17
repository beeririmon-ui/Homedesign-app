# Brief: the four stills inside the entrance, D0o, HDx, HD, HT (render-agent, 2026-11-17)

## Why
The owner approved the final door still (DOOR2, 2026-11-17: "מאושרת"): `assets/renders/hall/warm-modern/door-2026-11-16/d0.png`, as it is. The next step of the pilot is the four stills inside the entrance, which the arrival clips run between (storyboard S1: D0 → door opens in code → clip 1a to HT → clip 1b to HD → the 65° turn in code from HD to HDx → clip 2 to `base.png`).

## Your sources
- **What each still shows, and its rejection list:** chapter 11.5 of `docs/proposals/wm-entrance-magazine-2026-11-15.md` (11.5.1–11.5.7). It replaces the older descriptions in `docs/proposals/wm-front-door-2026-11-14.md` §6 and §10 where they differ.
- **The light levels:** chapter 11.9 there (the convention in 11.9.1, the measurable target per still and the seams in the table of 11.9.3, the new sentence for the D0o prompt). A level multiplier only in D0o, inside its mask, up to ±1/4.
- **The technical requirements:** motion-agent's `docs/proposals/wm-arrival-from-door-2026-11-14.md` §2 ("בסטילס", items 1–7): the D0o mask is the leaf rectangle and every pixel outside it is copied back from D0 (0 levels), with no leaf in the image; HDx and HD on the 3:2 canvas (2496×1664, frame at [71.11, 170.00, 2424.89, 1494.00]); HDx seeded from `base.png` through M0's depth (`site/tools/transitions/seeds.py hdx`); HD's right 28% is HDx projected (`seeds.py hd`), with the seam tone within 3%; HT built from HDx and `base.png` wherever they cover; the 16:9 frame of each still cut with `seeds.py frame`.
- **The clay:** `assets/blockout/house/framing/wm-door-2026-11-16/` (D0-open/none, HDx, HD, HT and their passes; README).

## The order and the money
- **Order:** D0o → HDx → HD → HT (each depends on the one before it).
- **Cap for this run: 2,600 tokens** (four stills). One fix is allowed only for a rejection-list item visible at ×1–×2 or a level outside the 11.9.3 band by more than 1/3 stop; the hard cap is then **3,250**. Nothing beyond that: stop and report. After 2,600 here the pilot keeps 7,100, and the three clips and the bedroom need about 6,160; every token you save here goes to the reserve.
- **The model is your choice per still.** seedream-5-pro 2K (650) is the one with lock evidence on our clay. nano-banana-2 (350–420) is cheaper; you may try it where the still is mostly a projection (HD from HDx, HT from HDx and `base.png`) if you judge it will lock, but a failed try counts against the cap. `var2_estimate_cost` before every send (SPEND2).

## Outputs
- `assets/renders/hall/warm-modern/hall-2026-11-17/`: per still, the master (D0o on D0's canvas; HDx and HD on the 3:2 canvas), the 16:9 frame cut for the video model (1920×1080), the lock record against the clay, the level measurement against 11.9.3; `jobs.json`; a short `README.md` with the rejection-list check at ×1 per still, the seams (D0o against D0, HD against HDx), and anything you are not sure of.
- Prompts in `assets/prompts/warm-modern-hall-2026-11-17/` (sent text next to the designer's verbatim text if you have to shorten it to var2's 4,000 characters).
- Update `assets/manifest.json` with the new entries. Working files in the scratchpad (EFF1).

## Fixed rules
- Tokens only for these four stills, inside the cap. No clip, nothing of the bedroom.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Return a short Hebrew summary: per still the path, model, tokens, whether it locked, its level against 11.9.3 and the rejection-list result; the seams; the total spent; what is still open.
