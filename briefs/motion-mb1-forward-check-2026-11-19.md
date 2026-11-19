# Brief: is MB1 reachable from MB0 moving forward? (motion-agent, 2026-11-19, 0 tokens)

## Why
MB1 is the bedroom's second frame, approved by the owner: a camera at the foot of the bed at (1.60, 21.20), h 1.20, 24 mm, three-quarter view (chapter 13 of `docs/proposals/wm-master-bedroom-render-2026-11-17.md`; `docs/proposals/wm-house-20-2026-11-19.md` 1.2 and 1.5). Before its plate is rendered (650+), the designer asked for a check that the move MB0 → MB1 can be a glide and a forward turn under FB8: the camera always faces forward like walking and never goes backwards, with α ≤ 45° at cruise. The transition clips themselves come at the very end, when every room is ready (FB11). This is only a geometry check, so the camera is right before money is spent.

## The task (0 tokens)
- **From the plan:** using `docs/house-plan.json`, the bedroom clay in `assets/blockout/house/framing/wm-master-2026-11-17/` and the route rules in chapter 11 of `docs/proposals/wm-tour-route-2026-11-17.md`, find a path MB0 → MB1, and the reverse MB1 → MB0 or MB1 → corridor, that:
  - keeps the forward rule;
  - doesn't pass through furniture;
  - keeps a sane speed.
- **If MB1's position or yaw blocks that:** propose the smallest change, in position, yaw or lens, that makes it work, and say what the frame loses or gains.
- **Make a clay strip:** 6–8 frames of the path, in the scratchpad, as evidence.

## Outputs
- A short section in chapter 13 of the bedroom render document? No: write `docs/proposals/wm-mb1-forward-check-2026-11-19.md` with the verdict, the path, the numbers and any proposed camera change.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's documents.
- Return a short Hebrew summary: pass, or the proposed change.
