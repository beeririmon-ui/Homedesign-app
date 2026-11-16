# Brief: the light levels for the entrance stills (master-designer, 2026-11-16)

## Why
render-agent built your chapter 11 into the clay and rendered the final D0 (`assets/renders/hall/warm-modern/door-2026-11-16/d0.png`, graded copy `d0-graded.png`). It passed every item of your rejection list 11.4. One item of 11.2 does not hold, and you said it comes back to you (11.2, item 19, "if two clash, it comes back to me"):
- In a display image, the shaded plaster at the level of `base.png` (L* about 89, locked exposure 0.75) and a sun patch 1.3–2.0 stops above it cannot both hold without clipping. Display headroom allows about 0.4 stop.
- render-agent calibrated the clay in scene-linear (sun 1.42 stops over shade, no clipping). The model in the still chose a real sun: 0.94 stop over shade in display terms, and so the shaded plaster sits **−0.87 stop under `base.png`** (your target was ±1/3).
- Inside, the clay gives D0o 0.39 (target 0.52 ±1/6) and HDx 0.68 (target 2/3), both only at slot strength 20, both at the edge.
- Also: the herbs came out narrower than your projection (u 0.586–0.750 against about 0.55–0.78; green 2.3% against about 4%).

The owner now has the D0 still for approval (DOOR2). Nothing else is rendered before he answers. The next stills (D0o, HT, HDx, HD per your 11.5) need your numbers.

## What to decide (0 tokens)
Add a dated section 11.9, "רמות האור בסטילס", to `docs/proposals/wm-entrance-magazine-2026-11-15.md`:
1. **The convention:** whether your levels apply in display terms or scene-linear, and the target for the shaded plaster against `base.png`. Say whether the D0 still as rendered (−0.87, sun 0.94) is accepted on light, or what at ×1 would need a fix.
2. **The ramp from D0 to M0,** still by still (D0, D0o, HT, HDx, HD, then `base.png`): the level of the reference surface in each, against `base.png`, so the walk reads as one house, one day (DL1), and the eye adapts without a jump at the threshold or the turn. Check it against motion-agent's requirements (`docs/proposals/wm-arrival-from-door-2026-11-14.md` §2: the court bright, the hall 2/3 stop under it).
3. **The herbs:** accept the narrower mass, or say what changes.
4. **One paragraph:** D0 against the magazine frame (`site/web/public/media/story/living-room/warm-modern/A/1280.webp`). It is brighter and cooler (a winter midday sun against a golden sunset). Is that right for the door, or should the stills inside carry the warmth? This is advice for the manager; the owner decides.

## Inputs
- The clay's README, the clash section: `assets/blockout/house/framing/wm-door-2026-11-16/README.md` (from "ההתנגשות"), and `selfcheck.json` there.
- The still's README with the measurement table: `assets/renders/hall/warm-modern/door-2026-11-16/README.md`.
- Your chapter 11 (11.1, 11.2 item 19, 11.5).
- `docs/proposals/wm-arrival-from-door-2026-11-14.md` §2; `docs/studio-rules-digest.md` (DL1, FB5, FB6).
- `assets/renders/living-room/warm-modern/base.png`.

## Acceptance
- render-agent can render D0o, HT, HDx and HD from 11.5 and 11.9 alone, with a measurable target for each still.
- No binding document is edited. No question to the owner.

## Fixed rules
- 0 tokens. No var2, no commits, no keys. Don't edit another agent's document.
- Return a short Hebrew summary: the convention and the shaded-plaster target, whether D0 is accepted on light, the ramp in one line per still, the herbs, and your paragraph on warmth.
