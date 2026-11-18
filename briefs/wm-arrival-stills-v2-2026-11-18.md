# Brief: the four new stills of the arrival, HT2, HDx2, HC, HC130 (render-agent, 2026-11-18)

## Why
The owner approved the route (ROUTE1) and FB8: flowing, a bit faster, always facing forward. On 2026-11-18 they approved rendering the arrival from animatic v2, 0–14 s: "מאשר את שניהם". The hall becomes a station: the visitor walks in, the head turns left toward the corridor (HC), then right toward the living room, and the walk continues. These four stills are the new frames that make it real. Every other frame on the way (D0, D0o, HT, HD, HDx, clips 1a and 2, M0) is approved or passed QA.

## Your sources
- **The descriptions:** master-designer's chapter 12 of `docs/proposals/wm-tour-route-2026-11-17.md`:
  - 12.1–12.4 for each still: what it shows, the English text, the light targets and the rejection list;
  - 12.5 for the seams across the arrival;
  - 12.6 for the notes to the manager.
- **The bench and the console:** spec 2.2 (walnut #6B4A33, matte oil, nothing on them). Under F3 they are plan B: fixed, with no hotspot.
- **The light:** chapter 11.9 of `docs/proposals/wm-entrance-magazine-2026-11-15.md`, as chapter 12 restates it.
- **The motion constraints:** motion-agent's chapter 13 of `docs/proposals/wm-arrival-from-door-2026-11-14.md` and the v2 README in `assets/video/animatic/route-2026-11-17/`. HC130 is needed. The front door leaf is closed and out of frame in HC130 and HC.
- **The existing stills:** `assets/renders/hall/warm-modern/hall-2026-11-17/` (`ht.png`, `hdx.png`, `hd.png`, their frames and lock records). The clay is in `assets/blockout/house/framing/wm-door-2026-11-16/` and render-agent's `framing_wm_door_final.py`. motion-agent added the bench and the console to the clay in its animatic; reuse its geometry.

## The order (chapter 12)
1. **The clay:** add the bench and the console as 2.2 specifies, and the views HC (HX, yaw 180) and HC130 (HX, yaw 130). Before sending HC, delete the dark clay object at HC's left margin (X 3.49, Y 9.62), or the model will draw an object there.
2. **HT2:** a mask edit of `ht.png`, adding only the bench and its contact shadow. Every pixel outside the mask is copied back from HT. HT2 is the bench's only source.
3. **HD's bottom strip, in code** from HT2.
4. **HDx2:** a mask edit of `hdx.png`, adding only the console from u 0.82 out of the right margin. The bench corner comes from code. The opening and the living room are untouched.
5. **HC:** a new view from the clay. The bedroom door is centred at u 0.50 ±0.01.
6. **HC130:** the bridge, seeded from its overlap with HD and HC. It comes last.

## Money
- **The pilot cap:** 13,900. 11,242 is spent, which leaves **2,658** for this run. List prices are 4 × 650 = 2,600.
- **Use nano-banana-2 (about 400) for the two mask edits (HT2, HDx2) if it holds the lock.** That leaves room for one fix; past hall stills cost 1.7× list in fixes. Choose the model per still, and price each with `var2_estimate_cost` first (SPEND2).
- **A fix is allowed only for something visible at ×1–×2** or a rejection-list item.
- **Any send that would take the total past 2,658: stop and report.** The owner is asked first.

## Outputs
- `assets/renders/hall/warm-modern/hall-2026-11-18/`:
  - per still, the master on its canvas, the 16:9 frame and the lock record against the clay;
  - the light measurement against 11.9;
  - `jobs.json`;
  - a README with the rejection-list result and what QA should look at.
- Prompts in `assets/prompts/warm-modern-hall-2026-11-18/`.
- Update `assets/manifest.json`. Working files go in the scratchpad (EFF1).

## Fixed rules
- Tokens only for these four stills, inside 2,658. No clips, nothing of the bedroom or the bathroom.
- If var2 asks for re-authorisation, stop and report. Never ask for codes.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document or stills.
- Return a short Hebrew summary:
  - per still: the path, model, tokens, lock, level against 11.9 and the rejection-list result;
  - the seams;
  - the total;
  - what is still open.
