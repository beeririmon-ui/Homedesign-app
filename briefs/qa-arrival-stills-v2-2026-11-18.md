# Brief: QA on the four new arrival stills, HT2, HDx2, HC, HC130 (qa-agent, 2026-11-18)

## Why
The owner approved rendering the arrival from animatic v2: the walk into the hall, a stop with the head turned to the corridor (HC), then right toward the living room. render-agent made four stills, 2,650 tokens, which leaves the pilot 8:
- **HDx2:** a nano mask edit adding the console.
- **HC:** seedream, magazine-grade.
- **HT2:** the bench built in code from the clay faces, after nano failed twice.
- **HC130:** the bridge, built in code from the HD and HC seeds, after nano drew a room into the gap.

master-designer accepted all four (chapter 12.7 of `docs/proposals/wm-tour-route-2026-11-17.md`) and restated HC's light targets to fit the light slot's physics. Then three code steps followed:
- the WM-G1 tone on HC;
- the tone on the console drum in HDx2;
- HC130 rebuilt from the toned HC.

No model fix is affordable now, so a finding that only a model can fix becomes a budget question to the owner (400 or 650).

## Inputs
- **The stills:** `assets/renders/hall/warm-modern/hall-2026-11-18/`:
  - `ht2`, `hdx2`, `hc` and `hc130` (`.png` and `-frame.png`), each with its `-lock.json`;
  - `hd2.png`, `hc-raw.png`, `hc-grade.json`, `hdx2-console-grade.json`, `sources/`;
  - `levels.json`, `jobs.json`, `tools/tone.py`;
  - the README (render-agent's notes for QA).
- **The spec:** chapter 12 (12.1–12.6 per still, the seams in 12.5) and 12.7 (the rulings and restated targets, including 12.7.1 for HC's light) of `docs/proposals/wm-tour-route-2026-11-17.md`. The light convention is in chapter 11.9 of `docs/proposals/wm-entrance-magazine-2026-11-15.md`.
- **The clay:** `assets/blockout/house/framing/wm-hall-2026-11-18/` and `assets/blockout/house/framing_wm_hall_2026_11_18.py`.
- **The approved neighbours:** `assets/renders/hall/warm-modern/hall-2026-11-17/` (`ht`, `hd`, `hdx`) and the bath plate's QA for the tone method (`qa/reports/2026-11-17-bath-plate/`, round 3).

## What to check (0 tokens)
1. **HT2:**
   - the bench reads as the designed bench (80 long, slab ends, open between) at ×1 and ×2;
   - its lock to the clay faces;
   - the seat's walnut hue against the lining (Δh +0.9°, C*/L* 33% lower);
   - the level exception inside the bench mask;
   - nothing outside the mask differs from HT.
2. **HDx2:**
   - the console after the drum tone (p2 12.65, front −0.74);
   - no pixel changed in the opening and the living room;
   - the bench corner from code matches HT2 and HD2.
3. **HC:**
   - the full rejection list (12.3) with the light of 12.7.1;
   - the black point in 11–14;
   - the bedroom door centred (0.503), and the brightest inside the portal by median;
   - the laundry door as an open walnut-lined opening (the corridor canon);
   - at ×2, the label anchors in `hc-lock.json`, where the laundry edge and the bath's far jamb were matched on the same line (0.425): say which match is right.
4. **HC130:**
   - the seams with HC (0.25%) and HD2 (0.18%);
   - the hidden-door anchor (−0.50);
   - no step inside a surface;
   - it reads as a plausible wall at ×1, with no smearing from the code build.
5. **Across the arrival, as stills:** the levels and seams of 12.5 between HT2 → HD2 → HC130 → HC and HD → HDx2. The turn itself is checked after motion-agent assembles it.

## Outputs
- `qa/reports/2026-11-18-arrival-stills/README.md`: pass or fail per still, with numbers. Evidence images in the same folder only when needed; scripts go in the scratchpad.
- Low findings go to `status/backlog-low.md`.
- A status line per still: "עבר QA" (temporary, not for the site yet), or the blocking finding. Mark which findings need a model (a budget question) and which code can fix.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- Return a short Hebrew summary: the five items, pass or fail with numbers, and whether each still passed.
