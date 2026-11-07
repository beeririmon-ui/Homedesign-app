# Brief: the warm-modern living-room clay (render-agent, 2026-11-07, step 1 of the TS1 pilot)

**The owner (2026-11-07) approved three things:**
- **TS1:** the warm-modern living-room tool pilot.
- **ARC1:** a style may change openings and sills in the tool.
- **WMB1:** the warm-modern Bible 1.0 and house plan 1.3.1 are binding.

**Still pending:**
- **WMP2, the products (approval 2).** The owner has comments that aren't in yet. So this step is the clay only, at 0 tokens. **No paid render in the pilot until I say so.**

## Inputs
- `docs/house-plan.md` and `.json` 1.3.1, §0א, "warm-modern living room":
  - glazing Y 0.75–2.85, width 2.10, sill 0.45, head 2.70, reveals 0.35, three fields of 0.70;
  - the limestone bench X −2.30…−1.90, Y 0.75–2.85, H 0.45;
  - a recessed curtain track at 2.82, with stacks at Y 0.60–0.75 and 2.85–3.00;
  - a rounded corner of R 0.15;
  - a 3.00 ceiling with a shadow gap;
  - the sconce plate 0.17 from the front stack.
- `data/slots/living-room.json` 1.9, `by_style.warm-modern`. It sets:
  - the vase on the bench at (−2.42, 1.35, 0.45);
  - the basket at (−1.62, 0.78);
  - the runner, wall decor, sofa cover and pouf empty;
  - the fixed furniture: the same footprints, and the armchair in the Nordic geometry (WM-F1).
- `docs/design-bible/warm-modern.md` 1.0, the tool chapter: the cameras unchanged, and M0 1.2's camera.
- Your round-5b clay pipeline: `assets/blockout/house/framing/` and `round5b/` (M0, M0p, M0x, clay_checks_r5b.py).

## Output
- `assets/blockout/house/framing/warm-modern-r1/`, containing:
  - M0.png, M0p.png and M0x.png;
  - plan.json;
  - the clay checks (`clay-checks-2026-11-07.json`), with the same named lines as round 5b plus the new ones: the glazing head, the bench edge, the rounded corner and the curtain track;
  - overlays, and a sheet of Nordic round 5b against warm modern r1 per camera.
- Report two checks the designer asked for:
  - whether the vase on the bench touches or is tangent to the back of the armchair at M0 1.2 (F-rules; give the gap in px and in the frame's %);
  - whether the stacks and the planter clear the new glazing.

## Fixed rules
- 0 tokens, no var2. New files only, no commits.
- If a house-plan number doesn't fit the room's geometry, stop and say which one.
- Return a short Hebrew summary: what was built, the clay checks, the two checks and the sheet path.
