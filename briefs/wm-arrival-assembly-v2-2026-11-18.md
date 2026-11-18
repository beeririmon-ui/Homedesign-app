# Brief: the arrival v2, assembled from the real frames (motion-agent, 2026-11-18)

## Why
The owner approved the route, then FB8 (flowing, a bit faster, always facing forward), then rendering the arrival from animatic v2, 0–14 s ("מאשר את שניהם", 2026-11-18). The four new stills passed QA (`qa/reports/2026-11-18-arrival-stills/README.md`): HT2 (the bench), HDx2 (the console), HC (the corridor) and HC130 (the bridge), in `assets/renders/hall/warm-modern/hall-2026-11-18/`. Clips 1a and 2 passed QA earlier, the door, 1b and the turns are in code, and M0 with reveal B is approved. Now the whole arrival is real, with no clay in it. The owner sees it before anything goes to the site.

## The work (0 tokens, no var2 calls)
1. **The pastes, in code:**
   - the bench from HT2 into clip 1a, into 1b and into HD's strip (HD2 exists);
   - the console and the bench corner from HDx2 into the first metre of clip 2.
   Use the method you specified in §11/§12/§13 of `docs/proposals/wm-arrival-from-door-2026-11-14.md` and used in the animatic. Run the border self-check in the style of `repair_right_wall.py check` on each paste.
2. **The turns at HX, from the real stills:** HD → HC130 → HC (left), the rest of 0.8 s on HC, then HC → HC130 → HD → HDx2 (right). Clip 2 starts in the last 20° of the turn. Run the hole check on the real stills. The front door leaf is closed and out of frame in HC130 and HC.
3. **The timeline of chapter 11.1** of `docs/proposals/wm-tour-route-2026-11-17.md`, as built in v2: cruise 1.5 m/s, the eases, the turn rates, the single rest. That's about 11.7 s from the click to M0, and 13.9 s with reveal B.
4. **The label anchors:** use QA's corrected anchors for HC (ARR-M1), not the ones in `hc-lock.json`:
   - bath `[0.3944, 0.4114]`;
   - laundry `[0.4252, 0.4335]`;
   - bedroom `[0.4618, 0.5298]`, centre 0.496.
   Record them in your export.
5. **The walk test** on the assembled arrival, the forward check (α as in v2), and the exposure along the route.
6. **The export:**
   - desktop and phone previews, with the rough interface overlay as in the animatic (the labels, the skip button, the mini-map);
   - also a clean version without the overlay, for the frontend;
   - a frame bank or sequence, per your export tool;
   - a README with the segments, the timecodes and what QA should look at.

## Outputs
- `assets/video/transitions/warm-modern/arrival-v2/`: the previews (desktop and phone, with and without the overlay), the README, the walk JSON and the self-check JSONs.
- A dated section in your proposal document.
- Working files go in the scratchpad. Delete the banks when done.

## Fixed rules
- 0 tokens. No var2. No commits, no keys.
- Don't edit a binding document, `data/`, or another agent's stills or documents. `hc-lock.json` is render-agent's file: use QA's anchors in your export and don't edit it.
- Return a short Hebrew summary:
  - the paths and lengths;
  - each paste's self-check;
  - the hole check;
  - the walk test and the forward check;
  - what QA should look at, with frame ranges.
