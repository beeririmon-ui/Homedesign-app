# Brief: QA on the assembled arrival v2 (qa-agent, 2026-11-18)

## Why
motion-agent assembled the whole arrival from real frames, with no clay: the door in code, clip 1a with the bench pasted from HT2, 1b in code, the turns at HX through HC130 to HC with a 0.8 s rest, the turn back, clip 2 with the console pasted from HDx2, and the landing on M0 with reveal B. It is 11.68 s from the click to M0 and 13.88 s with the reveal and the hold, at 0 tokens. The parts passed QA one by one: clips 1a and 2, and the four stills. Now the whole runs in motion, with the pastes and the turns as new work. The owner sees it before the frontend wires it in.

EFF1.2: check what is new (the pastes, the turns, the joins, the labels), plus anything a visitor would notice at ×1. Don't repeat the parts' own QA unless a number looks wrong.

## Inputs
- **The folder:** `assets/video/transitions/warm-modern/arrival-v2/`:
  - the four mp4s (desktop 60 fps and phone 30 fps, each `.ui` and `.clean`);
  - the README (segments, timecodes, QA frame ranges);
  - `segments.json`, `camera.json`, `exposure.json`, `walk.json`, the three `selfcheck-*.json`, `look-contact.jpg`.
- **The proposal:** chapter 14 of `docs/proposals/wm-arrival-from-door-2026-11-14.md`.
- **The route and timeline:** chapter 11.1 of `docs/proposals/wm-tour-route-2026-11-17.md`.
- **The stills:** `assets/renders/hall/warm-modern/hall-2026-11-18/`, and their QA in `qa/reports/2026-11-18-arrival-stills/`.
- **The earlier clip QA:** `qa/reports/2026-11-17-clip1a/` and `qa/reports/2026-11-17-clip2/`.

## What to check (0 tokens), at ×1 and quarter speed, on the desktop clean master (60 fps frame numbers)
1. **The bench in 1a (90–219 at ×1, 127–211 at ×2).** motion-agent records:
   - the outer line over its 12-level threshold in 26 bank frames, the worst at 33 (in HT2 itself it's 4.9);
   - a thin light halo in the gap between the legs (169–211).
   Judge whether a visitor would notice. If yes, say whether code can fix it.
2. **1b into the left turn (264–282),** and **the HC130 corner (290–322, 435–462):** no flicker, no swimming, no step.
3. **The rest on HC (357–404) in the `.ui` version:** the labels sit on the right doors with QA's corrected anchors. The bath is at 0.3944–0.4114, the bedroom centred at 0.496, and the laundry has no label.
4. **Clip 2's entry with the console (506–546):** the hole fill (2.8% before, 0.005% after) leaves no visible patch. The console and bench corner hold.
5. **The landing and reveal B (702–785).**
6. **The whole at ×1:**
   - the walk test (1a: WALK, LOCAL FAIL as before; 1b: NOT A WALK as approved; clip 2: WALK);
   - the forward check (α ≤ 2.3° at cruise);
   - the exposure (the largest step 0.015 stop);
   - does it read as one flowing walk into a lived-in house (FB7, FB8), not a zoom?
7. **The phone version:** a spot check that it matches the desktop, at its frame numbers (÷2).

## Outputs
- `qa/reports/2026-11-18-arrival-v2/README.md`: pass or fail per item, with numbers and frames. Evidence images only when needed; scripts in the scratchpad.
- Low findings go to `status/backlog-low.md`.
- A status line: "עבר QA" (temporary, for the owner; not for the site yet), or the blocking findings with frame ranges. Mark whether code can fix each, since the pilot has 8 tokens left.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- Return a short Hebrew summary: the seven items, pass or fail with numbers, and whether the arrival passed QA.
