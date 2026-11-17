# Brief: QA on the warm-modern master bedroom plate MB0 (qa-agent, 2026-11-17)

## Why
render-agent rendered the empty plate of the warm-modern master bedroom, MB0 (seedream-5-pro, one take, 650). Three global code steps followed:
- the lock;
- the bed wall's falloff evened by half, so the plaster matches `base.png` (a gap of 2.7 L*);
- WM-G1, which raised the black point from 8 to 12.5. The curve is recorded in `plate-compose.json`.

The plate is the base the product and light layers will sit on. The products wait for owner approval 2. The bathroom plate taught us to check the black point first (BP-M1).

EFF1.2: check the plate only. This is its first QA, so the whole plate is in scope.

## Inputs
- **The renders:** `assets/renders/master/warm-modern/stage1-2026-11-17/` (`plate.png`, `plate-frame.png`, the raw take, `plate-compose.json`, `jobs.json`, and the README with render-agent's notes).
- **The clay:** `assets/blockout/house/framing/wm-master-2026-11-17/` (MB0-plate with its depth, ids and edges, the lock target, `selfcheck.json`, README).
- **The spec:** master-designer's `docs/proposals/wm-master-bedroom-render-2026-11-17.md`:
  - chapter 1 (the architecture), chapter 2 (the fixed furniture), and 6.2–6.4 (the camera, the frame, the light);
  - chapter 7 (the rejection list) and chapter 9 (what QA checks);
  - chapter 12 overrides where it differs.
- **The plan:** `docs/house-plan.json`, room "master", camera MB0.
- **The house references:**
  - `assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png` (the plaster, the floor, the bronze);
  - the bathroom plate `assets/renders/bath/warm-modern/stage1-2026-11-17/plate.png` and its QA report `qa/reports/2026-11-17-bath-plate/`;
  - the door stone `assets/renders/hall/warm-modern/door-2026-11-16/d0.png`, for the sill.

## What to check (0 tokens)
1. **The lock to the clay:** the bed, the headboard, the nightstands, the window, the rounded corner, the floor line and the skirting. Say where the residual is above 2 px.
2. **The rejection list (chapter 7)**, item by item, including the three code steps: no visible seam or halo from the falloff evening.
3. **The tone against the house:**
   - the plaster, the floor, the walnut and the sill stone, with ΔE00 against the references;
   - the black point (target 11–14, as on the bathroom plate);
   - whether it reads as the same house as the living room, the hall and the bathroom at ×1.
   render-agent flags three things. Judge whether each is visible at ×1–×2, and whether it's a defect or a designer call:
   - the walnut figure on the headboard is horizontal and flowing; chapter 2 asked for vertical;
   - the sill's edge is rock-faced and reads about 6 cm thick, not 4;
   - the floor right of the bed is darker than `base.png` (ΔE00 4.1, chroma only 1.5–2.3).
4. **Product slots:** nothing in the plate that will clash with a product slot. The sconce positions are clear plaster, the space above the bed is free for the future picture, the nightstand tops are clear, and so are the sill and the curtain area.

## Outputs
- `qa/reports/2026-11-17-master-plate/README.md`: pass or fail per item, with numbers. Evidence images only when needed; scripts go in the scratchpad.
- Low findings go to `status/backlog-low.md` (EFF1.1).
- A status line: "עבר QA" (the plate only; not for the site until the 1.3.9 registration and approval 3), or the blocking finding.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- Return a short Hebrew summary: the four items, pass or fail with numbers, and whether the plate passed QA.
