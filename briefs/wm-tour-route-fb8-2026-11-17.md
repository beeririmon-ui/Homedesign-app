# Brief: the route after FB8 — flowing, a bit faster, always facing forward (master-designer, 2026-11-17)

## Why
The owner watched the route animatic (`assets/video/animatic/route-2026-11-17/`, README with segments) and approved the direction (ROUTE1, answered). They added FB8, now in `docs/studio-rules.md` and the digest:

> "אוקיי, נחמד הסרטון, אבל זה צריך להיות יותר זורם, פחות מעצב, כאילו יותר פלואנט, יותר בזרימה. אבל כן, אהבתי את מה שאני רואה. כן, בואי נתקדם עם הכיוון. רוצה עוד וריאציה? זה גם צריך להיות טיפה ליותר מהיר, וגם שלא ילך אחורה הפריים, אלא תמיד עם הפנים קדימה, כמו הליכה. זה גם לזכור."

The manager reads it as follows:
1. The route stands: the hall junction, the look-around, the living room, the kitchen seen from the living room, and no cuts between rooms.
2. **Flowing:** no stop-and-start between segments. "פחות מעצב" is read as "פחות עוצר"; it may be a transcription.
3. **A bit faster.**
4. **A standing rule for the whole tour: the camera never travels backwards.** It always faces forward, like walking. Head turns and pans are allowed. This rules out the corridor retreat (ROUTE-Q1 (a)) and clip 2 played in reverse. Every return is a turn and a forward walk.
5. Before any spend, another animatic made to FB8 (motion-agent, 0 tokens). It's based on the straight arrival inside the cap (ROUTE1 option 1, the manager's default), unless you show that something else is needed for "flowing".

## What to write (0 tokens)
Add chapter 11, "FB8", to your document `docs/proposals/wm-tour-route-2026-11-17.md`. Keep it short and concrete, giving motion-agent numbers it can build from:
1. **The arrival as one flowing movement.** Where the camera keeps moving and where it only slows, and the one place it rests (and why there). Say how the look-around fits into that: for example, the head turns left to the corridor while the walk eases into the junction, and turns right toward the living room as the walk resumes. Say what happens to the hall buttons on the first arrival and on a return to the hall. Give the new pace: cruise speed, ease-in and ease-out, turn rates, rest length, and the total from D0 to the M0 reveal. Today it is about 22 s with stops.
2. **Forward-only for the whole house.**
   - **The living room → the bedroom wing and back:** how the visitor turns around in the living room and walks forward to the hall, into the corridor, through the door, and into each room (the master bedroom, the children's rooms, the bathroom, the work room). Say where a turn in place happens and how big it is.
   - **The kitchen-dining:** from M0, the pan to M0x and the walk through the double door.
   - For every new still or clip this needs, give its station, its yaw and its job. Mark what goes away: HE, the retreat clips HE → C0 and C0 → MB-in, and clip 2 in reverse.
3. **What the house plan's corridor transitions (T-HC, T-CBoy, T-CGirl, T-CBath, T-CM), written as retreats, become.** It's a proposal for the 1.3.9 registration, with the other chapter 9 items. Don't edit `docs/house-plan.*`.
4. **The owner rule as a check:** one line per transition in the house, saying it faces forward (yes/no) and where it turns.

## Inputs
- FB7 and FB8, TR2, U5, U10 in `docs/studio-rules-digest.md`.
- Your document (all of it, especially chapters 1, 2.3–2.6, 4 and 8).
- The animatic README: `assets/video/animatic/route-2026-11-17/README.md`.
- The price items: `assets/prompts/transitions.warm-modern/route-prices-2026-11-17.json`.
- `docs/house-plan.json` ("transitions", "rail", "cameras").

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document or another agent's document.
- **Note:** F3 (`data/slots/hall.json`, the bench and console) says the render stays as designed and a matching model is sourced. So the bench and console are rendered to your spec now, and sourcing runs in parallel. Adjust your 2.2 note on re-rendering if you agree, or say why not.
- Return a short Hebrew summary: the flowing arrival in a few lines with its total length, the forward-only route through the house, the list of new and dropped stills and clips, and anything that needs the owner.
