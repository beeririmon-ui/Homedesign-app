# Brief: the door clay, and the first still, D0 (render-agent, 2026-11-14)

This continues `briefs/wm-entrance-clay-2026-11-14.md`. Your run stopped on the usage limit; what you made is saved (`assets/blockout/house/framing/wm-entrance-2026-11-14/`, commit `551a1796`).

## What changed while you were stopped
- **The owner approved the front door** (DOOR1, 2026-11-14: "כן לדלת"). The pilot's cap is 13,900 tokens in all (9,900 for the two transitions, 4,000 for the door). Rule FB4 in `docs/studio-rules-digest.md`.
- **master-designer designed the door and the route:** `docs/proposals/wm-front-door-2026-11-14.md`. Read §1–§3 (the door, the court, the light, camera D0), §5 (the stills and their order) and §6 (the prompt descriptions and his rejection list).
- **The manager chose storyboard S1:** the site opens on D0, facing the closed door in the covered court; the door opens in code; a straight walk from D0 to HD; a 65° turn in code from the stills HD and HDx; the approved dolly from HDx to M0. **H0 and H0x are not rendered in the pilot.**
- **motion-agent wrote the technical plan:** `docs/proposals/wm-arrival-from-door-2026-11-14.md`. §2 is its list of requirements from you (the clay, then the stills); §1 gives the 3:2 canvas for HD and HDx; §3 explains the threshold frame HT.
- **The owner sees the D0 still first,** as the check that the studio and he speak the same language. Nothing else is rendered with tokens before he has seen it.

## The order of this run
The door image is what the owner is waiting for, so it comes first.

**1. The court and the door in the clay (0 tokens).** The model as the designer's §1.1 and motion-agent's §2 describe it: the covered court, the door leaf in three states (closed, no leaf, open at 90°), the hidden study door as real geometry. Then **D0 in the three leaf states,** on the regular canvas, with the passes you already use.

**2. The check of D0 on the clay (0 tokens).** The table of the projected values in the designer's §3.2, value by value: his number, the clay's number, the difference. **The gate:** if the composition he describes does not hold on the clay (the door on the left third, the inner corner on the right third, the vanishing point inside the door, the leaf's rectangle), or a value is off by more than 0.02 of the frame, stop here, spend nothing, and report. The designer decides.

**3. The D0 still (tokens; approved).** The closed door.
- Locked on the clay as motion-agent's §2 "בסטילס" item 1 says (the leaf's rectangle, the outer opening, the two corners, the floor line, within 2 px), with the designer's prompt description and everything on his rejection list checked by you before you hand it back.
- `var2_estimate_cost` right before the send (SPEND2). The verified price is 650 for seedream-5-pro image-to-image at 2K; nano-banana-2 at 4K is 450. The choice is yours, by which locks on the clay.
- **The cap for this run: 1,300 tokens** (one render and at most one fix). If a second fix is needed, stop and report with what you have.
- The record and the prompt in the usual place for the warm-modern house, and the still itself next to them. Say in the summary exactly where the file is.

**4. The rest of the clay (0 tokens),** after the still is out: HD and HDx on the 3:2 canvas, HD57 (reserve, clay only), HT, and the 12 stations of clip 1 with the open leaf, with the measurement motion-agent asks for (what part of each station's frame the front wall and the opening to the living room take). HDx against the line of your existing stations (`b/S02`, `b/S03`), and `b/S11` against `base.png`, within 2 px.

**5. Finish the entrance run's README and selfcheck,** and write one README for the door folder. Under S1 the table of projected values for H0 is no longer urgent: keep it short.

**Not in this run:** D0o, HDx, HD, HT as stills; anything of the bedroom (MB0, MB-in and its stations wait until the arrival clip passes).

## Outputs
- `assets/blockout/house/framing/wm-door-2026-11-14/` (the clay frames, the passes, one contact sheet, `selfcheck.json`, `README.md`), and the script next to the other framing scripts.
- The D0 still, its prompt and its record.
- Working files in the scratchpad (EFF1).

## Fixed rules
- Tokens only for the D0 still, inside the cap above. No other `var2_create_*` or `var2_modify_*`.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Return a short Hebrew summary: the D0 table's largest differences and whether the gate passed; the still (path, model, tokens spent, what you checked against the rejection list, anything you are not sure of); what the stations of clip 1 show on the right side of the frame; what is still open.
