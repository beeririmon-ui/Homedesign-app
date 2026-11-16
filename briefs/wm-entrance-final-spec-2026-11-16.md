# Brief: the final entrance, M3 with M2's stone wall (master-designer, 2026-11-16)

## Why
The owner looked at the three "middle" concepts (`assets/renders/hall/warm-modern/concepts-middle-2026-11-15/`) and answered ENT2: "מ3 או מ2". The manager's choice, recorded under FB6 in `docs/studio-rules-digest.md`:
- **M3 "הספסל הבנוי" is the base:** D0's camera and opening, so storyboard S1 and the clay stay; the reeded walnut door, the built-in plaster bench stepping up into a planter of lavender and rosemary, the doormat, the lit wall light, the low winter sun with olive-leaf shadow (§10.6 of `docs/proposals/wm-entrance-magazine-2026-11-15.md`).
- **From M2, the door wall in honed limestone** in long flat courses with fine recessed joints (§10.5). The side walls stay lime plaster, so the sun and the leaf shadow still fall on plaster.
- **No sidelight** next to the door: it would widen `O-front-door` in the plan. If you think the stone wall needs it, say so and why; the manager decides.
- **The owner sees the final D0 still before anything else is rendered,** and can still ask for pure M3 or pure M2.

## What to write (0 tokens)
A dated chapter 11, "הכניסה הסופית: מ3 עם קיר האבן", in `docs/proposals/wm-entrance-magazine-2026-11-15.md`:
1. **The spec of the D0 frame,** short and exact: the door wall (stone, the courses, where the cladding stops at the corners and at the ceiling, how the door's reveal is finished in stone), the door, the bench and the planter (position, length, height, the top, what grows, how much of the bench stays free to sit on: the concept planted it end to end), the doormat, the wall light (position; it is a future product slot), the window on the left wall, the floor, the light. Mark each object as architecture, landscape, or a future product slot.
2. **The changes the clay needs,** as a list render-agent can build: the stone cladding's thickness and how it changes the reveal, the bench and planter geometry, the light's position. Everything as a projection to check on the clay.
3. **The prompt for the final D0** (image-to-image on the clay, English), and **the rejection list** for it. Learn from the concepts: the model inflated or dropped things (it planted the whole bench, dropped the sun on M2, added sky and neighbours' roofs on M1).
4. **What the camera sees inside under M3** (your §10.6 says the hall's roof light becomes a light slot along the far wall): updated descriptions and rejection lists for D0o, HT, HD and HDx, replacing those in `docs/proposals/wm-front-door-2026-11-14.md` §10 where they differ. The turn must not open on a blank wall.
5. **The plan registration proposal** for this entrance (what changes in `docs/house-plan.json`), for the owner after he sees the pilot.

## Inputs
- `docs/studio-rules-digest.md` (FB5, FB6 and the ENT2 line, DL1).
- `docs/proposals/wm-entrance-magazine-2026-11-15.md` (§10.5, §10.6, §10.8–10.9).
- The concepts: `assets/renders/hall/warm-modern/concepts-middle-2026-11-15/` (M2, M3, README).
- The clay and its README: `assets/blockout/house/framing/wm-door-2026-11-14/`.
- `docs/proposals/wm-front-door-2026-11-14.md` (§1–§6, §10), `docs/proposals/wm-arrival-from-door-2026-11-14.md` (motion-agent's requirements for the stills, §2).
- `.claude/skills/interior-design-rules/`.

## Acceptance
- render-agent can build the clay and render D0 from this chapter alone.
- Every number is from the plan or marked as a projection for the clay.
- No binding document is edited; plan changes are proposals. No question to the owner.

## Fixed rules
- 0 tokens. No var2, no commits, no keys.
- Return a short Hebrew summary: the D0 frame in five lines, the clay changes, your answer on the sidelight, and anything render-agent must not miss.
