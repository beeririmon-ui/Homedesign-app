# Brief: the clay for the final entrance, and the final D0 still (render-agent, 2026-11-16)

## Why
The owner chose the entrance from the "middle" concepts (ENT2, "מ3 או מ2"); the manager's choice is M3 with M2's stone door wall, no sidelight (FB6 and the ENT2 line in `docs/studio-rules-digest.md`). master-designer wrote the final spec: **chapter 11 of `docs/proposals/wm-entrance-magazine-2026-11-15.md`**. It is your source for everything below. **The owner sees the D0 still before anything else is rendered.**

## The order
**1. The clay (0 tokens).** Build chapter 11.2 into the door clay (`assets/blockout/house/framing_wm_door.py`, output next to `assets/blockout/house/framing/wm-door-2026-11-14/` in a new folder `wm-door-2026-11-16/`):
- outside: the stone door wall with its joint grooves, the stone reveals, the reeded leaf with real walnut albedo, the planter and the built-in bench on the right wall, the herbs as a volume, the lit wall light, the doormat, the sun (azimuth about 228°, altitude about 21°) and an olive tree out of frame whose shadow falls on the right wall;
- inside: the stone panel on the far wall and the light slot that replaces RL-hall;
- then re-render D0 in its three leaf states, HD, HDx (3:2 canvas, as in motion-agent's `docs/proposals/wm-arrival-from-door-2026-11-14.md` §1), HT and the 12 stations of clip 1, with the passes you already make.
- **The gate:** the geometry does not move. The stone face stays at X 3.95; the leaf's rectangle (motion-agent's u 0.2441–0.4224, v 0.0997–0.8603) within 2 px. Check the designer's projections in chapter 11 (the light, the bench, the planter, the sun patch) against the clay: a table, his number, the clay's, the difference. If something in his spec does not hold on the clay, stop before spending and report.

**2. The final D0 still (tokens; approved).**
- Image-to-image from the clay only, with the designer's prompt and rejection list (chapter 11.3–11.4). No concept image as a reference.
- Locked on the clay as before (the leaf's rectangle, the outer opening, the corners, the floor line, within 2 px).
- **The cap for this run: 1,300 tokens** (one render and at most one fix, the fix only for an item on the rejection list). `var2_estimate_cost` before each send.
- The model is your choice: the one that locks best on the clay at magazine quality. This is the site's first frame, so quality first; if two models are close, the cheaper (nano-banana-2 at 2K–4K is 350–420; seedream-5-pro 2K is 650).
- Output: `assets/renders/hall/warm-modern/door-2026-11-16/` (the master, a graded copy if the grade needs it, the lock record, `jobs.json`, a short `README.md` with the rejection-list check at ×1, and anything you are not sure of). Prompts in `assets/prompts/warm-modern-door-2026-11-16/`.

**Not in this run:** D0o, HT, HDx, HD as stills; anything of the bedroom.

## Manager's decision you need
The lit wall light and the doormat are drawn in the still as generic items, without a hotspot or a "buy" button until they have product cards (designer's chapter 11). That is accepted for the pilot.

## Fixed rules
- Tokens only for the D0 still, inside the cap.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document. Working files in the scratchpad (EFF1).
- Return a short Hebrew summary: whether the clay gate passed (and the largest differences), the still (path, model, tokens, the rejection-list check, what you are unsure of), and what is still open.
