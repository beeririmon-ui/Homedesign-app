# Brief: MOCK11, the real route legs 2–5 in the site (frontend-dev, 2026-11-27)

## Why
The owner's words on the code transitions (FB26): "סתם זום ואז פייד… צריך להיות מעברון של ממש הליכה". Motion-agent has now built real first-person walking legs with the `room-transitions` skill. Each one lands pixel-exactly on the next room's display frame:
- leg 2, kitchen D1 → bath B1;
- leg 3, bath → bedroom MB0;
- leg 4, MB0 → boy;
- leg 5, boy → girl.

Leg 6 (girl → work) waits for an owner decision.

## What to build (design C, behind `HD_PUBLIC=0`)
1. **Drop in legs 2–5.**
   - Each is one line in `site/tools/tour/route.json`: `assets/video/transitions/warm-modern/route-fb21/leg{2,3,4,5}/final`.
   - Encode as you did leg 1 in MOCK9: 1920@60 and 1080@30 mp4, H.264 High, faststart, with a poster from the first frame.
   - Size limits: desktop at most about 8 MB per leg, phone at most 2.5 MB.
   - **Do legs 2, 4 and 5 first.** Motion-agent is still trimming leg 3's ending (code only). Encode leg 3 last, after I tell you its `final/` is done.
2. **A leg with no clip (now leg 6):** use the designed soft fade through warm light, about 450 ms, the same as going back, instead of the MOCK7 zoom push. The owner rejected "zoom then fade".
3. **Chained jumps:** jumping 2 or more stations ahead plays the real legs chained at ×2–×3, skipping the ease frames between legs (the manifests' `fast_forward`). Check that the pace reads as one continuous walk, with no flash or pause at the joins.
4. **The seams:** every leg's last frame must hand over to the room's display frame (with the FB16 grade) with no visible jump. The first frame must match the room you leave. Measure it and report the worst seam.
5. **Preload:** only the leg you can reach from the current room, as in MOCK9. Phones get the 1080 files.
6. Keep everything from MOCK10: the corner UI, no play icon, the gesture unlock, the wheel and the logo.

## Outputs
- `site/dist-artifact/` rebuilt, with `check-artifact` passing.
  - The Artifact limits: at most 255 files and 64 MB per publish, 511 files and 256 MB per version, and at most 15 MB per binary file.
  - If the total is over 60 MB, list the files for a second publish batch. The second batch should hold only the new leg files.
- A walkthrough video, at most 15 MB, 1280×720: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock11/walkthrough.mp4`.
  - It goes from the living room to the girl's room by "הלאה" at each station.
  - Then one jump back to the living room, and a jump ahead of 3 stations.
- A short "MOCK11" section in `site/README.md`.

## Checks
typecheck, lint, vitest, e2e mock9 and mock10, plus a new mock11 spec (the real legs play; a null leg fades; a chained jump). Both builds.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- **Don't edit** `data/`, binding docs or render or video folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Disk:** about 500 MB free. Delete `site/web/dist` and your temp files when done.
- **Work economically.**
- **Your report:** a Hebrew summary of at most 8 lines.
