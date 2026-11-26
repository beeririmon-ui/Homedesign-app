# Brief: FB16, one hour for the whole warm-modern house: the house light spec (master-designer, 2026-11-26)

## The owner's words (FB16, `docs/studio-rules.md`)
> "השמש שקיעה טיפה דרמטי מידי..מעט פחות , ולשים לב שבשאר החדרים זה אותה שעה"

- **The living room (M0-W, direction B):** the sun is toned down by about a third, to a calm late winter afternoon, not a sunset. render-agent has these targets: plaster in sun L 88–92, plaster in shade L 74–80, a white-gold patch, soft edges.
- **Every other room** must read as the same hour.

## Inputs
- Your proposal `docs/proposals/wm-fb13-living-wow-2026-11-25.md`, 3.1 and section 4.
- The concepts: `assets/renders/living-room/warm-modern/fb13-2026-11-25/concepts/concepts-sheet.jpg`.
- render-agent's prep README in `assets/renders/living-room/warm-modern/fb13-2026-11-25/`: the sun needs the flipped compass, and the D0 yard is then in shade.
- `docs/house-plan.json` and `docs/house-plan.md`: the compass, the rooms, the windows.
- The Bible (`docs/design-bible/`).
- Each room's current defaults: the `-fb13prep` frames under `assets/renders/<room>/warm-modern/`.

## The task: one short spec, "the house at 15:40"
1. **The sun for the whole house:** azimuth and elevation under the compass M0-W needs. Say exactly what changes in the plan (the compass flip), as a list for the manager to register.
2. **Per room and frame** (D0, HT2, HDx2, D1, D2, W0, MB0, MB1, B1, B2, boy, girl):
   - Does direct sun enter? If so, through which window, where the patch falls (wall or floor, roughly), and how strong it is relative to M0-W.
   - Which lamps are on.
   - The exposure and white balance targets (plaster L in shade, black point, warmth).
   - What shows outside the window, consistent with M0-W.
3. **The method per room, cheapest first:**
   - a light layer in code over the whole stack (sun patch and lamp glow from the clay, one grade), so every wheel variant gets the same light;
   - a full-frame relight edit only where code can't do it; say why, with the cost.
4. **The entrance and D0.** D0 was approved by the owner with its own sun. Say what the cheapest honest fix is (for example a grade, or a softer ambient, without re-rendering the door), and what must be re-fed after M0-W.
5. **An order of work and one cost line:** expected and cap.

## Output
- `docs/proposals/wm-fb16-house-light-2026-11-26.md`, tight: a table, not prose.
- A Hebrew summary of at most 8 lines.

## Fixed rules
- 0 tokens. A proposal only; edit no binding document.
- Product fidelity first: no method that redraws products.
