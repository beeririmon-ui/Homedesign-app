# Brief: QA on the warm-modern bathroom plate B2 (qa-agent, 2026-11-17)

## Why
render-agent rendered the empty plate of the warm-modern bathroom, frame B2 (the vanity wall): seedream-5-pro, one take, 650 tokens, and three code steps (a lock warp, the left strip rebuilt as plaster, the bronze tone pulled to the house bronze-espresso). It is the base that the product and light layers will sit on, so its geometry and tone have to be right before any product is rendered on it. The products wait for owner approval 2.

EFF1.2: check the plate only. This is its first QA, so the whole plate is in scope, but nothing else.

## Inputs
- **The renders:** `assets/renders/bath/warm-modern/stage1-2026-11-17/`: `plate.png`, `plate-frame.png`, `raw/plate-r1.png`, `jobs.json`, and the README with render-agent's notes for QA.
- **The clay:** `assets/blockout/house/framing/wm-bath-2026-11-17/`: `B2-plate` with its depth, ids and edges, `lock-target.json`, `selfcheck.json`, and the README.
- **The spec:** master-designer's `docs/proposals/wm-bath-render-2026-11-17.md`, chapter 1 (the architecture), 7.2–7.5 and 7.8 (the camera, the composition, the architecture in frame, the light), chapter 8 (the rejection list) and chapter 9 (what QA checks).
- **The plan:** `docs/house-plan.json`, room "bath", camera B2 from CB.
- **The house references:** `assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png` (the plaster and the bronze) and the door stone in `assets/renders/hall/warm-modern/door-2026-11-16/d0.png`.

## What to check (0 tokens)
1. **The lock to the clay:** the joints, the vanity, the mirror, the niche, the shower walls and the floor line, against `lock-target.json`. Say where the residual is above 2 px.
2. **The rejection list (chapter 8)**, item by item. Pay particular attention to the three code steps: no seam or tone step at the rebuilt left strip, and the bronze reads as bronze-espresso.
3. **The tone:** the plaster against `base.png`, the stone against the door stone, and the walnut against the house walnut. Say whether it reads as the same house at ×1. render-agent flags three things:
   - the plaster right of the mirror is L* 80.6, because the lamps are off in the plate;
   - the stone hue is 32.5–34, slightly under 35–42;
   - an extra vertical joint in the shower's east wall.
   Judge whether each is visible at ×1–×2.
4. **Product slots:** nothing in the plate that will clash with a product slot. The sconce positions are clear plaster, the niche is empty, the ring position is clear, and nothing is drawn where the curtain will hang.

## Outputs
- `qa/reports/2026-11-17-bath-plate/README.md`: pass or fail per item, with numbers. Evidence images only when needed; scripts in the scratchpad.
- Low findings go to `status/backlog-low.md` (EFF1.1).
- A status line: "עבר QA" (the plate, not for the site until the 1.3.9 registration and approval 3), or the blocking finding.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- Return a short Hebrew summary: the four items, pass or fail with numbers, and whether the plate passed QA.
