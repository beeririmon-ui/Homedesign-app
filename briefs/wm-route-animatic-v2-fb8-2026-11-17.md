# Brief: animatic v2 to FB8, and the updated prices (motion-agent, 2026-11-17)

## Why
The owner liked the route animatic and approved the direction (ROUTE1). They asked for another variation (FB8, in `docs/studio-rules.md` and the digest): more flowing with no stop-and-start, a bit faster, and **never travelling backwards, always facing forward like walking** (a standing rule for the whole tour). master-designer wrote chapter 11 "FB8" in `docs/proposals/wm-tour-route-2026-11-17.md` (11.1–11.6). Build to it. The owner sees v2 before any token is spent.

## The work (0 tokens; the only var2 call allowed is `var2_estimate_cost`)
1. **Animatic v2**, two parts, desktop and phone, 16:9, under 25 MB per file:
   - **(a) The flowing arrival (11.1):** from the click on D0 to the M0 reveal, about 11.9 s.
     - The door opens and the walk starts before the leaf finishes. The head turns left toward the corridor at the end of 1b. The only rest is 0.8 s on HC, with the door names. Then 155° to the right, with clip 2 starting in the last 20° of the turn.
     - Cruise 1.5 m/s, a 0.6 s ease-in, the eases and turn rates as given, and the landing on M0.
     - Use real frames wherever they exist: D0, the door in code, clip 1a (repaired, passed QA), 1b in code, HD, HDx, clip 2 (passed QA, re-timed), and M0 with reveal B. Use clay for HC130, HC, the bench and the console, as in v1.
     - No hall buttons on the first arrival: labels on the openings and a "דלג" (skip) button.
   - **(b) The living room → the master bedroom, forward only (11.2):** about 18 s, clay.
     - The 180° turn in the living room past the opening to the kitchen, the walk to the hall, the bend of about 25° at the junction, the corridor, the door, and around the foot of the bed to MB0.
     - If the doc's route doesn't hold geometrically anywhere (for example which opening the walk from the living room goes through), say so, and build the closest version that holds.
   - The rough interface as in v1: the live mini-map with the view cone, the labels on the openings, and the destination name. Keep the timecode and the "clay" label on clay segments.
   - Name the files `route-animatic-v2.desktop.1920.30fps.mp4` and `route-animatic-v2.phone.1080.30fps.mp4`, in `assets/video/animatic/route-2026-11-17/`. Keep v1. Add a v2 section to the README with the segments and their timecodes.
2. **The forward check (11.5) as a measurement:** for each segment of v2, the largest angle between the direction of travel and the view direction while moving (α ≤ 45° at cruise, never 90° or more in motion). Put it in the README.
3. **The prices:** add the items in 11.3 to `assets/prompts/transitions.warm-modern/route-prices-2026-11-17.json` under a dated "fb8" key, using live `var2_estimate_cost` for each new still and clip: M0x, M0s, M0b, MBf, MB0; M0p and MBn if your check says they're needed; the clips LH, HM and MBa. Give the arrival total (expected 2,600, inside the 2,658 left) and the bedroom-wing total as a separate budget. Mark the dropped items. Add a short dated section to your proposal document.
4. **Anything the designer's numbers miss in the clay:** the holes in the turns (HC130 is still needed?), the jamb clearances at 1.5 m/s, and whether 1.5 m/s reads as walking or as zoom on the real clip 2. Say what you'd change.

## Fixed rules
- 0 tokens. No sends to var2 (only `var2_estimate_cost`; if var2 isn't connected, say so and leave the prices for later). No commits, no keys.
- Don't edit a binding document, `data/`, the designer's document, or another agent's stills.
- Working files go in the scratchpad. Delete the clay and banks when done, and say what you deleted.
- Return a short Hebrew summary: the v2 paths and lengths, the forward check per segment, the prices (arrival, and the bedroom wing separately), and anything in chapter 11 that doesn't hold.
