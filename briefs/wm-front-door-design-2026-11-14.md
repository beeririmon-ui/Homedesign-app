# Brief: the front door, and closing the open design points of the transition pilot (master-designer, 2026-11-14)

## Why
The owner tried MOCK3 and answered the pilot question. Rule FB4 in `docs/studio-rules-digest.md` (EFF1.6). His words:

> "אוקי אין קפיצות, אבל סרטון התנועת מצלמה מהדלת אל הסלון ומהסלון לחדר אחר זה כל החוויה שאני מדמיין ואיננו..אני רוצה שנבדוק שאנחנו מבינים אחד את השני בואי ניצור את דלת הכניסה ואז את סרטון המעבר מהדלת אל הסלון ומהסלון אל חדר השינה"

What this decides:
- **The transition pilot is approved, option (ב):** the arrival and the bedroom, staged, cap 9,900 (`docs/proposals/wm-arrival-entrance-to-living-2026-11-13.md` §7).
- **He asks for the front door itself.** The pilot proposal told him the door is not seen. He answered "let's create the front door". The manager's reading: he imagines a real picture of the house's door, from which the camera sets out. That is option (ד) in your `docs/proposals/wm-entrance-hall-architecture-2026-11-13.md` §4, which you recommended to leave out of the pilot. It is now in. Its cost goes to the owner as question DOOR1 before any credit is spent on it; your design is the 0-token step that comes first.
- **The purpose of this round is to check that the owner and the studio speak the same language.** He will see each step early: your description of the door, then the still, then the raw clip.

## Inputs
- `docs/studio-rules-digest.md` (FB2, FB3, FB4; U5, U10, U14; DIR2; TR1, TR2).
- `docs/house-plan.json`: `O-front-door` (hall exterior wall, plane X 3.60–3.95, Y 7.80–8.80, Z 0–2.40), `porch` (covered entrance court, X 3.95–7.60, Y 6.55–9.60, open to the south), cameras H0, H0x, M0, MB0, transitions T-E0, T-CM.
- Your documents: `docs/proposals/wm-entrance-hall-architecture-2026-11-13.md`, `docs/proposals/wm-master-bedroom-architecture-2026-11-13.md`.
- motion-agent's plan: `docs/proposals/wm-arrival-entrance-to-living-2026-11-13.md` (§2 the three requests to you, §7 what changes in the bedroom plan, §8).
- The warm-modern Design Bible and the empty living room plate you already cite (`base.png`).
- `.claude/skills/interior-design-rules/`.

## Part A. The front door (the main part)
Write `docs/proposals/wm-front-door-2026-11-14.md`. Design only what the camera will see; no full facade.

1. **The door and its setting, in warm-modern.** The door leaf (wood, proportions, handle, any glazing or side light), the surround, the threshold, the court's floor, the wall strip and the soffit that fall in the frame, the house number or a light only if they earn their place. What from the Nordic plan stays as geometry and what changes with the style (DIR2). The fluted bathroom window that faces the court: in the frame or out, and how it looks if in.
2. **The light.** Time of day and direction consistent with the living room plate, so that the walk from the court into the house reads as one moment.
3. **The opening frame: camera D0.** Position, heading, lens (U14), shift, what sits on each third, and the margins. This is the first thing a visitor to the site sees; on a phone it is shown whole in a 16:9 window about 220 px tall, so the door must read at that size.
4. **The move from the door to the living room: a storyboard.** From D0 through the door, then to the approved dolly H0x → M0. The known problems, each with your decision:
   - the turn from the door's direction to the dolly's heading is about 80° (U5);
   - video models struggle with a door that swings open. Say what the visitor should see (the door opening by itself, an already open door with the hall's light behind it, a cut on the dark of the door, or another idea) and which key frames (stills) that needs. Prefer the version with the best chance to look like one continuous walk.
   - the length: T-E0 alone is 3.0–3.4 s (U10). Say how long the whole arrival from the door may run, and mark it as a change that needs the owner's approval after he sees the result.
   Give one recommended storyboard and at most one alternative. motion-agent turns it into the technical plan and the verified cost.
5. **What happens to H0.** With a door shot, is H0 (yaw 12) still a resting frame of the tour ("כניסה" in the panel), a frame the camera only passes, or not needed in the pilot? H0x is needed in every case, as the first frame of the dolly clip. Say which stills the pilot needs, in the order to render them, so that nothing rendered is thrown away.
6. **Prompt-ready descriptions** for the door still(s), and **your rejection list** for them, like the one you wrote for the hall plate.
7. **The plan registration** (a new camera and a new transition), as a proposal only. It goes to the owner after he sees the pilot, together with 1.3.7 and 1.3.8.
8. **A short description for the owner, in plain Hebrew** (5–8 lines, no codes): what he will see when the site opens and when he presses "לסלון". The manager shows it to him before the still is rendered.

## Part B. Closing the open points of T-E0 (short)
In your own `docs/proposals/wm-entrance-hall-architecture-2026-11-13.md`, as dated additions:
1. motion-agent asks that the lens shift change during the pan (in code) and not during the dolly, so H0x is rendered with M0's shift (0.47, 0.50). Confirm or refuse; if confirmed, update the two values that change (the opening at the end of the pan, the left margin).
2. motion-agent asks that H0x be built from H0 (one pair, consistent). Confirm or give the order you want, given Part A.5.
3. Your question 1 (an empty entrance as the plate) is closed by the manager with your default (א): shell only.
4. Read TR2 as the manager recorded it: constant speed forbids slowing in mid-route; an ease at the landing on M0 is allowed. Say if the design objects.

## Part C. The corridor, as seen from the bedroom (short)
motion-agent found that the corridor is visible through the bedroom door for almost all of the slide of T-CM. Write a short architecture record (materials, floor, wall, the portal, the light, and what must be empty) in `docs/proposals/wm-corridor-architecture-2026-11-14.md`, enough to render the still MB-in without invention. Not a full corridor design; that belongs to the round after the pilot.

## Acceptance
- Every number is either taken from `docs/house-plan.json` or marked as a projection to be checked on the clay.
- Nothing contradicts a binding document; where the door needs a change in one (a new camera, the arrival's length), it is listed as a proposal for the owner.
- No binding document is edited. No product is invented: what is not for sale is not drawn as a product.
- Open questions for the owner: at most one, with your default. Everything else you decide.

## Fixed rules
- 0 tokens. No var2, no commits, no keys.
- Return a short Hebrew summary: the door in three lines, the storyboard, the stills needed and their order, your answers to Part B, and the text for the owner (A.8) in full.
