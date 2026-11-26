# Brief: MOCK8, one site round that brings in everything new (frontend-dev, 2026-11-26)

## Why
Several approved pieces are ready. Bring them all into the tour in one round (EFF2). Design C, behind `HD_PUBLIC=0`.

## What to bring in
1. **The living room's cushion wheel:** `assets/renders/living-room/warm-modern/fb13-2026-11-25/layers/manifest-wheel.json`, sets B (default), A and C. Remove the "no wheel" exception for the living room. Re-pin.
2. **The studio stills in every wheel:** `assets/renders/wheel-studio/warm-modern/` (`manifest.json` maps each variant to its card and SKU). They feed the `studio` field of your RingWheel contract. The dining pendant V2 has no still: keep the fallback. The work-room print close-up stays preview-only (rights).
3. **The house light (FB16):** every room's `manifest*-fb16.json` and `*-fb16-frame.png`. Apply the Lab grade (`fb16.frames.<id>.grade`) on the stack as render-agent described, so each room matches its fb16 frame. The pixel gate is against the fb16 frames.
4. **The hall:** `assets/renders/hall/warm-modern/hall-products-2026-11-19/hdx2-products-fb19-frame.png`, the new living room through the opening.
5. **The arrival:** use `assets/video/transitions/warm-modern/arrival-fb19/` as far as it's final. K-A2, from the door to HT2, is approved and good. The rest of the walk (the turn and the clip into M0-W) is still being made. Until then, after K-A2 use the current code transition into the living room. Make swapping in the final sequence a one-line change, and scroll-scrubbed:
   - the walk advances with gentle scroll impulses and inertia (a small push plays a stretch, then eases to a stop);
   - 2–3 small scrolls reach the living room;
   - the last frame hands over pixel-exactly to the room frame;
   - with reduced motion, it plays as a short fade.

## Outputs
- `site/dist-artifact/` rebuilt, with `check-artifact` passing (at most 255 files). Don't publish it.
- A walkthrough video, at most 15 MB, 1280×720: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock8/walkthrough.mp4`. It shows the door, the scroll walk, the living room, the cushion wheel with studio stills, and two more rooms.
- A short "MOCK8" section in `site/README.md`.

## Checks
typecheck, lint, vitest, and e2e for mock7 plus a new mock8 spec. Both builds.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- **Don't edit** `data/`, binding docs or render folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Disk:** it's tight, about 700 MB. Clean up.
- **Work economically.**
- **Your report:** a Hebrew summary of at most 8 lines.
