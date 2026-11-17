# Brief: the tour as a walk through one house (master-designer, 2026-11-17)

## Why
The owner saw clip 2 (the dolly from the middle of the entrance hall into the living room) and pushed back (FB7, 2026-11-17, in `docs/studio-rules.md`). In short:
- It looks as if the front door opens straight into the living room. They didn't see the door open.
- It reads as a zoom, not a tour.
- There must be an entrance hall right after the door.
- The visitor has to understand where the kitchen, the corridor, the bedrooms and the bathroom are, so that every later clip, from the living room to the next room, makes sense.
- "אני מקווה שחשבת על הכל פה... זה נראה שלא."

**Part of this is presentation.** The owner saw only the last segment, without the door, the walk in, or the hall. But part is real:
- Storyboard S1 (`docs/proposals/wm-front-door-2026-11-14.md`) walks from the door to HD and turns straight to the living room. The visitor never stops in the hall and never sees the corridor opening.
- The pilot's living room → bedroom transition was planned with a cut instead of the corridor (board, 2026-11-14).
- The house plan does define the whole graph. The hall H0 is the hub, with T-E0 to the living room, T-HC to the corridor (then T-CBoy, T-CGirl, T-CBath, T-CM), T-HW to the work room, and T-LD from the living room to the kitchen-dining (`docs/house-plan.json` "transitions", "rail"; `docs/house-plan.md` §5–6). The arrival just doesn't use it.

No tokens go to clips until the owner approves the route you propose.

## What to write (0 tokens)
A new document, `docs/proposals/wm-tour-route-2026-11-17.md`, in Hebrew, short and concrete:
1. **The route through the whole house, as the visitor experiences it.** For each stop (the door, the hall, the living room, the kitchen-dining, the corridor, each bedroom, the bathroom, the work room), say what the visitor sees, and which openings to other rooms are visible from it. The rule to aim for: every transition leaves through an opening the visitor has already seen, and arrives in a place that the previous view showed or pointed to.
2. **The arrival, redesigned, from what exists.**
   - The door opens, visibly.
   - The visitor walks in and **stops in the hall**. Decide what they see there, and whether a slow look around from a fixed point shows the corridor to the bedrooms and the bathroom on one side and the living room on the other. A pure rotation can be done in code from stills, without the video model; motion-agent is reporting what it can show and what stills it needs.
   - The buttons appear in the hall, one per direction.
   - Then into the living room. Say how the dolly should feel so it reads as walking and not as a zoom: pace, height, an arc, a foreground passing by, a pause. Some of this may need a new take; flag it.
   - **Reuse first:** D0, D0o, HT, HD and HDx are approved or QA-passed (`assets/renders/hall/warm-modern/`), and clip 2 passed QA. Say what stays, what changes and what is new.
3. **The kitchen-dining:** how the visitor learns where it is. Can they see it from the living room through the open double door O-living-dining? Is that view in M0 or M0x?
4. **The bedrooms and the bathroom:** the route from the living room back through the hall into the corridor (T-HC, the corridor rail H0e → S1' → C0). Is a cut acceptable anywhere, and where not?
5. **Orientation in the interface** (for frontend-dev, 0 tokens): for example a small floor plan with "you are here" and the next rooms, labels on openings, button names and places. Keep it in the "high-tech" language of TOUR1, not a real-estate floor plan.
6. **A drawing for the owner:** specify a single annotated floor-plan image (rooms, openings, the route, the stops, where each button appears, what's already rendered). motion-agent will draw it from `docs/house-plan.json`, so give exact content, not artwork.
7. **What the owner sees before any spend:** a clay animatic of the new arrival (0 tokens, motion-agent's tools), plus the drawing.
8. **Owner questions:** at most two, each with options and your recommendation.

## Inputs
- `docs/studio-rules-digest.md` (TOUR1, TOUR2, FB4–FB7, DL1, U5, U10, EFF1).
- `docs/house-plan.md` (§5 direction, light and movement; §6.1–6.8) and `docs/house-plan.json` ("rooms", "openings", "transitions", "rail", "cameras").
- `docs/proposals/wm-front-door-2026-11-14.md` (S1, S2), `docs/proposals/wm-entrance-magazine-2026-11-15.md` (chapter 11, the final entrance), `docs/proposals/wm-arrival-from-door-2026-11-14.md` (motion-agent's plan, §1–§10).
- `docs/proposals/wm-corridor-architecture-2026-11-14.md`.
- The stills: `assets/renders/hall/warm-modern/door-2026-11-16/d0.png`, `assets/renders/hall/warm-modern/hall-2026-11-17/` (d0o, ht, hd, hdx *-frame.png).
- Clip 2's README: `assets/video/transitions/warm-modern/clip2-hdx--m0/README.md`.
- The magazine frame (FB5): `site/web/public/media/story/living-room/warm-modern/A/1280.webp`.

## Acceptance
- The owner can read the route in two minutes. It answers each of FB7's points by name.
- Every new image or clip is listed with its job and why it's needed. motion-agent will price them, so don't guess prices.
- Nothing contradicts an approved decision without saying so.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document (`docs/house-plan.*`, `docs/studio-rules*`, `docs/skeleton-spec.md`, `data/`) or another agent's document.
- Return a short Hebrew summary: the route in one line per stop, the redesigned arrival, orientation in the interface, what's new against what's reused, and your owner questions.
