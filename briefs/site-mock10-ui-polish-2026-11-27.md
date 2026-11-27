# Brief: MOCK10, a premium, high-tech, flowing UI, plus the "play" icon fix (frontend-dev, 2026-11-27)

## The owner's words on MOCK9 (FB26, `docs/studio-rules.md`)
> "הממשק ממש לא נוח, והוא גם לא נראה כזה הייטקי ומעוצב ונקי כמו שדיברנו. הוא צריך להיות יותר הייטקי, יותר מעוצב, עם הנפשות נעימות ואיזשהו פייד, לא מסגרות ברורות מדי, וצריך להיות יותר בפינה. ומשום מה אני רואה בהתחלה סימן של פליי, שזה לא אמור להיות... הכל צריך להיות מעוצב ברמות, גם האתר וגם הכפתורים וגם הבאנרים, ומאוד חלק וזורם."

Also: "המעברונים... סתם זום ואז פייד". Real walking clips for legs 2–6 come separately. **First check that leg 1 really plays in the published artifact** (https://claude.ai/artifact/6uXxzHDMN49mwdBF7KnLav, built from `site/dist-artifact`). If it falls back to the code zoom, find out why and fix it: autoplay policy, `playsinline` and `muted`, sandboxed iframe limits, MIME type, or the size of the mp4.

## What to build (design C base, behind `HD_PUBLIC=0`)
1. **No play icon, ever.**
   - Every video element: `muted`, `playsinline`, `autoplay` where needed, `preload`, no controls, and a `poster` equal to the first frame. Hide the native overlay play buttons (WebKit pseudo-elements).
   - If a play can be blocked, the UI stays visually still on the poster, with no system icon, and starts on the first user gesture.
   - Test it in Chromium headless with the autoplay policy that requires a gesture, and on an emulated iPhone.
2. **The opening.**
   - From the very first frame it's designed: the door frame, the logo intro, then the scroll cue.
   - No flashes, no layout shift, no default browser UI.
   - A refined scroll cue, for example a thin animated line or chevron, low-contrast.
3. **The controls UI: high-tech, minimal, corner-anchored.**
   - The route banner, room navigation, cart and menu move into a compact corner cluster. The image is the hero.
   - No visible boxes or strong borders: soft gradients, fades, hairlines at most, gentle translucency.
   - Pleasant micro-animations (eased opacity and position, 200–400 ms) for hover, appear and change.
   - On phone: one compact corner control that expands. Thumb-friendly.
   - The product dots: subtle, elegant, with a gentle pulse on idle.
   - The product card and the wheel: floating, borderless, with soft edges and fade in and out.
   - **The feel to aim for:** a luxury interiors brand crossed with a high-end product site. Precise, quiet and smooth.
4. **Comfort:** clear affordances. A first-time visitor understands within 2 seconds how to move on (the route) and how to see a product.
5. **Keep everything from MOCK9:** the route logic, leg 1, the wheel, the studio stills and the logo.

## Outputs
- `site/dist-artifact/` rebuilt, with `check-artifact` passing.
- A walkthrough video, at most 15 MB, 1280×720, at `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock10/walkthrough.mp4`. It starts from a cold load: the opening, the scroll walk, the living room, a product, the wheel, and "הלאה" to the kitchen on leg 1.
- Phone screens at 400: the opening, the room with the corner control closed and then open, and a product.
- A short "MOCK10" section in `site/README.md`, including the cause and the fix of the play icon, and whether leg 1 plays in the artifact.

## Checks
typecheck, lint, vitest, e2e mock9 plus a new mock10 spec (including a test that no video ever shows controls or a play overlay). Both builds.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- **Don't edit** `data/`, binding docs or render folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Disk:** it's tight; clean up.
- **Work economically.**
- **Your report:** a Hebrew summary of at most 8 lines.
