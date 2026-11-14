# Brief: the arrival from the front door, technical plan and zero-token preparation (motion-agent, 2026-11-14)

## Why
The owner approved the transition pilot and the front door (rule FB4 in `docs/studio-rules-digest.md`, EFF1.6):
- **TR-P1 = (ב):** the arrival and the bedroom, staged, cap 9,900.
- **DOOR1 = yes:** the door still(s) and the clip that enters through the door, cap 4,000 more. **The pilot's cap is 13,900 tokens in all.**
- He confirmed the picture: the site opens facing the house's door; a press on "לסלון" enters through the door and the camera walks inside the house until it stops on the empty living room; then the light line brings the products.
- The purpose of the round is to check that the owner and the studio speak the same language. He sees the door still first, and the raw clip before it is connected to the site.

master-designer designed the door and the route: `docs/proposals/wm-front-door-2026-11-14.md`. **The manager chose storyboard S1** (the door opens in code; a straight walk from D0 through the door to HD; a 65° turn in code from the stills HD and HDx; the approved dolly from HDx to M0). S2 stays as the fallback the designer describes. The two departures from the rules (the 65° turn against U5, the length against U10) go to the owner after he sees the result; the versions inside the rules (a cut at HD; the fast version) are switches from the same assets.

## Inputs
- `docs/studio-rules-digest.md` (FB2–FB4; U5, U10, U14; TR1, TR2).
- `docs/proposals/wm-front-door-2026-11-14.md` (all of it; §4, §5 and §9 are addressed to you).
- `docs/proposals/wm-entrance-hall-architecture-2026-11-13.md` §8 (the designer's answers B1–B5 to your requests) and `docs/proposals/wm-corridor-architecture-2026-11-14.md`.
- Your plan: `docs/proposals/wm-arrival-entrance-to-living-2026-11-13.md`.
- `docs/house-plan.json`.
- render-agent is building the entrance clay now (`briefs/wm-entrance-clay-2026-11-14.md`, output in `assets/blockout/house/framing/wm-entrance-2026-11-14/`): H0, H0x in both shifts, and 12 stations along the dolly line to M0, with depth. Use what is there when you reach the animatic; the court, D0, HD and HDx clays come in its next run.

## Part A. The technical plan for S1
Write `docs/proposals/wm-arrival-from-door-2026-11-14.md` (short; it updates your plan and does not repeat it):
1. **The door opening in code:** the layers and what each still must give (the designer's §4.3). What frontend-dev needs.
2. **Clip 1,** D0o with the open leaf → HD (4.94 m): the model, the length, the prompt's intent, the walk test's numbers for this clip.
3. **The 65° turn in code from HD and HDx.** Check that it works: the overlap between the two stills, the two different shifts, the seam in mid-turn, and **the canvas and overscan that HD and HDx must be rendered with.** If the two stills are not enough, say so now (the designer's reserve is a third still, HD57). This item decides what render-agent renders, so write it first.
4. **Clip 2,** HDx → `base.png` (3.87 m): the same method as your plan; what changes with the shorter run. It also serves the first leg of the bedroom transition, played backwards.
5. **The whole arrival:** the timeline at about 7.3 s and the fast version at about 5.5 s from the same frames; the version with a cut at HD; the landing (TR2 as recorded: no slowing in mid-route, an ease at the landing is allowed).
6. **The format for the site:** the frame counts and weights for the longer arrival, on the phone and on the desktop, against your §5; what is loaded before the press and what streams.
7. **The requirements from render-agent's stills and clay,** as one list: canvases, overscan, passes, stations (where and how many).

## Part B. The verified cost
With `var2_estimate_cost` (free), one table for S1: every still and clip of the first round, the retries you would want in reserve, and the total against the cap of 13,900 (9,900 for the two transitions, 4,000 for the door). Say plainly if the first round or a sensible reserve does not fit. Also the bedroom stage (MB0 plate, MB-in still, the clip MB-in → MB0) as you priced it, updated if clip 2 changes anything.

## Part C. The zero-token preparation (your §8)
1. The depth map of the warm-modern M0.
2. The tools: the walk test, the assembly (end locks, resampling, grading, the turn and the door in code), the export to frame sequences.
3. The clay animatic of the part that already has clay (the dolly line to M0), and of the rest when its clay exists. Say what waits.
4. The prompts and the work records in `assets/prompts/transitions.warm-modern/`, ready to send, each starting with `var2_estimate_cost`.

## Acceptance
- Item A.3 states clearly: two stills are enough, or a third is needed, with the reason and the evidence (a test on the clay or on synthetic frames).
- Every price in Part B comes from a live estimate, with the model and the parameters.
- The tools are tested on a clay walk and on a dissolve, as your plan says.
- Nothing contradicts a binding document beyond the two departures already listed for the owner.

## Fixed rules
- **0 tokens in this run:** no `var2_create_*`, no `var2_modify_*`. `var2_estimate_cost` and `var2_list_models` are free and allowed.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document. Working files in the scratchpad (EFF1).
- Return a short Hebrew summary: the answer to A.3 first, the requirements for render-agent, the cost table, what is ready, and what waits for what.
