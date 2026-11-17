# Brief: the route drawing, the animatic and the prices (motion-agent, 2026-11-17)

## Why
The owner pushed back on the arrival (FB7). master-designer wrote the new route for the whole house: `docs/proposals/wm-tour-route-2026-11-17.md`. Read §0 and §2, and work from §6 and §7. The hall becomes a junction, HX at (2.462, 8.15), where the visitor stops and looks around. The corridor is seen from there. The kitchen-dining is seen from the living room (M0x). There are no cuts between rooms. Before any token is spent, the owner sees one drawing and one animatic and answers two questions (§8: ROUTE-Q1, ROUTE-Q2). Your job is to make those two things and to price what is new.

## The work (0 tokens; the only var2 call allowed is `var2_estimate_cost`)
1. **The drawing**, exactly as §6 specifies, drawn from `docs/house-plan.json` (1.1 geometry; never from `docs/proposals/house-plan/`). Use the stations, cones, route lines, buttons and status colours given in §6. Hebrew labels, right to left. Check that every room and opening sits on the plan's coordinates. The designer's colours: green means rendered and passed QA; orange means clip 1a, which hasn't passed QA yet.
2. **The animatic**, as §7.2 specifies: (a) the recommended arrival, (b) the same with the straight walk (the real clip 2, re-timed), and (c) living room → master bedroom in both corridor grammars (Q1 (a) and (b)), in clay.
   - Use real frames wherever they exist: D0, the door in code, clip 1a, 1b in code, HD, HDx, clip 2, M0, the existing reveal.
   - Use clay where the thing is new: HC, HC130, HT2/HDx2 with the bench and console, the arc walk, the bedroom wing. Label every clay segment "clay" in the corner, with a running timecode.
   - Use clip 1a as rendered, with its end lock, and mark it "1a, before QA".
   - Include the sample interface (labels on openings, direction tabs, the live mini-map with a view cone) as a rough overlay, enough for the owner to understand it. It doesn't need to be frontend-quality.
   - Format: 16:9, desktop and phone, about 45 s in all. Keep it under 25 MB per file.
3. **The look-around in code:** run the hole check for HC and HC130 from HX on the clay (§2.4). Say whether HC130 is needed.
4. **The prices:** use `var2_estimate_cost` for every new item in §2.7 and §4.4, as you would write each job: the stills (HT2, HDx2, HD strip, HC, HC130 if needed; the bedroom wing HE, C0, MB-in, MB0) and the clips (clip 2 take 2 with the arc; HE → C0, C0 → MB-in, MB-in → MB0). Give the total for each owner option (Q1 a/b × Q2 a/b/c) against the 2,658 left in the pilot. Say which of the edits to HT2/HDx2/HD can be done in code (mask paste from a single generated object) and which need a model.
5. **Clip 1a, ready for QA:** rebuild its bank with the end locks (the median shift was 6.6 px, p95 12.6). Say whether the lock holds and what QA should look at (frame ranges).

## Outputs
- **The drawing:** `docs/proposals/wm-tour-route-2026-11-17/route-plan.png` (and the script that draws it, under `site/tools/transitions/`).
- **The animatic:** `assets/video/animatic/route-2026-11-17/` (desktop and phone mp4, with a README listing the segments and their timecodes).
- **The prices:** a dated section added to your proposal document `docs/proposals/wm-arrival-from-door-2026-11-14.md`, and a JSON at `assets/prompts/transitions.warm-modern/route-prices-2026-11-17.json`.
- **Clip 1a:** an updated README in `assets/video/transitions/warm-modern/clip1a-d0o--ht/`.
- Working files go in the scratchpad. The disk allowance is limited, so delete banks when done.

## Fixed rules
- 0 tokens. No sends to var2 (only `var2_estimate_cost`). No commits, no keys.
- Don't edit a binding document, `data/`, the designer's document, or another agent's stills.
- Return a short Hebrew summary: the drawing and animatic paths and lengths, the hole check, the price table per owner option, whether clip 1a's lock holds, and anything in the designer's route that doesn't hold geometrically.
