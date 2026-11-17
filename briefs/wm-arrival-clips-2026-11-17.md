# Brief: the arrival clips from the door to the living room (motion-agent, 2026-11-17)

## Why
The owner approved the final door (DOOR2, 2026-11-17) and said: "נצא לרינדור התנועה". render-agent is now rendering the four stills inside the entrance (D0o → HDx → HD → HT; `briefs/wm-hall-stills-2026-11-17.md`, output `assets/renders/hall/warm-modern/hall-2026-11-17/`). The clips run between those stills, so the work comes in two phases.

## Phase A, now (0 tokens)
Bring your prepared prompts and jobs (`assets/prompts/transitions.warm-modern/`, your `docs/proposals/wm-arrival-from-door-2026-11-14.md`) up to the final entrance, without waiting for the stills:
1. **Clip 1 in two parts (HT adopted, 2026-11-15):** 1a D0o → HT and 1b HT → HD, each with its own prompt, duration and job. The door is already open in both; the leaf is drawn in code.
2. **The final entrance (chapter 11 of `docs/proposals/wm-entrance-magazine-2026-11-15.md`):** what changes in the prompts per 11.5.8 (the stone edge on the right of the opening that grows to about half the wall at HD; the light line at the top of the opening, leaving the frame by about 2.2 m from D0; the left wall in clip 2's first frames is stone, not plaster; replace "plain plaster edge"), and what the camera sees inside per 11.5.1–11.5.6 (the stone panel on the far wall, the light slot that replaces RL-hall).
3. **The dining glimpse:** the [DINING] paragraph in clip 2 (master-designer's §10 of `docs/proposals/wm-front-door-2026-11-14.md`), with no extra still.
4. **The walk test** (`site/tools/transitions/walk_test.py`, the clay `assets/blockout/house/framing/wm-door-2026-11-16/` and its `c1` stations): the events of 11.1.10 in its table; id 50 excluded between 1.0 and 1.8 m; the herbs leave the frame in the window 2.15–2.40 m (11.9.4).
5. **The turn:** the HD ← HDx seam locks on the stone joints, not only on tone (11.5.8).
6. **Light (11.9.6):** the prompts' exposure lines stay ("exposure locked, the court bright, the hall 2/3 stop under it"). The drop of about 0.6 in the frame mean in clip 1a and the rise in clip 2 are intended, and `assemble.py`'s exposure tracking must not flatten them.
7. **Live prices:** `var2_estimate_cost` for each job as written (free). If a price moved, say so.

Write the changes into your prompt files and `jobs.json` (dated), and add a short dated section to your proposal document listing what changed. Then stop and report: Phase B starts only on the manager's word, after the stills are back and checked.

## Phase B, later (tokens; the manager sends the go and the cap)
The planned order: clip 2 (HDx → `base.png`) first, the walk test on it, then 1a and 1b, then the raw arrival assembled (door in code, clip 1a, 1b, the turn, clip 2, reveal B) for the owner. The planned spend is about 3,564 (4 s 1,296; 4 s 1,296; 3 s 972 at kling-3-omni 1080p). The bedroom is not in this brief.

## Fixed rules
- Phase A: 0 tokens. No var2 call other than `var2_estimate_cost`.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document. Don't touch `assets/renders/hall/warm-modern/hall-2026-11-17/` (render-agent is writing there). Working files in the scratchpad (EFF1).
- Return a short Hebrew summary: what changed in each prompt, the walk-test table's new rows, the live prices and durations per clip, and anything in the stills you will need that the stills brief may not give you (so the manager can pass it to render-agent before it finishes).
