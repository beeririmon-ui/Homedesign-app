# Brief: a priced plan for real transition clips across the whole warm-modern house (motion-agent, 2026-11-26)

## Why
The owner wants the site with transitions now (FB17, `docs/studio-rules.md`):
- **MOCK7 (in progress):** frontend-dev is building code 2.5D transitions between rooms.
- **Your job:** the plan for real camera-move clips between all rooms. It goes to the owner as one priced proposal. Nothing is rendered without approval.

## Inputs
- the route: `docs/proposals/wm-tour-route-2026-11-17.md`; and `docs/house-plan.json` (1.3.9 and 1.3.9a);
- the earlier price list: `assets/prompts/transitions.warm-modern/route-prices-2026-11-17.json`, including the ×1.71 history margin;
- the clips that exist: `assets/video/transitions/warm-modern/`;
- **the frames:** each room's latest frame (the `-fb15` defaults; the living room becomes M0-W in `assets/renders/living-room/warm-modern/fb13-2026-11-25/`, with a new camera of 35 mm at 1.05 m);
- the house light: `docs/proposals/wm-fb16-house-light-2026-11-26.md`, one hour for the whole house.

## The task (0 tokens)
1. **The list of transitions** in route order, from the door to the last room and back, including the return paths the tour needs. For each:
   - from and to;
   - the length in metres and seconds;
   - the method:
     - kling clip from the two stills;
     - a code 2.5D move on depth;
     - a code turn.
   - **Prefer code where it reads as real.** Real clips go where a doorway or a long walk must feel physical.
2. **The cost per clip, and in total:** expected and cap, at the live price (use `var2_estimate_cost` only if available; otherwise last week's list), with the margin.
3. **What's reusable:** the existing door, 1a, 1b and turn clips. Clip 2 is replaced (the old table, the old camera).
4. **Depth maps for code transitions,** at 0 tokens: write a depth map for every room frame that has none, from its clay where possible. Save it next to each frame as `depth-fb17.png`, and list them. frontend-dev will use them.
5. **The order of work,** so the owner sees the first real clips quickly: the entrance into the living room (M0-W) first.

## Outputs
- `docs/proposals/wm-transitions-house-2026-11-26.md`: a table, short.
- The depth maps, plus a list in the proposal.
- A Hebrew summary of at most 8 lines, with the total expected cost and the cap.

## Fixed rules
- 0 tokens: no var2 generation; cost estimates only.
- **Don't touch:** `data/`, `docs/` (other than your proposal), `site/`, or existing render files. Depth maps go in new files.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight, about 1.2 GB.
- **Work economically.**
