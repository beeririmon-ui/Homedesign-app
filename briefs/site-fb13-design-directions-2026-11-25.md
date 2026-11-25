# Brief: FB13, raise the level of the site and tour design: three directions to pick from (frontend-dev, 2026-11-25)

## The owner's words (FB13, `docs/studio-rules.md`)
> "את האתר והסיור גם נתחיל במקביל ..משהו צריך לעלות רמה בעיצוב האתר..שיהיה הייטק חדשני מגזיני מעוצב ונקי"

The goal (CLAUDE.md): a high-tech virtual tour at a level not seen before. The transitions, the close-up, the wheel and the product highlight must all be "wow".

## Today
MOCK6 is behind `HD_PUBLIC=0`. Screens are in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock6/screens/`. The code is in `site/web/src/` (tour, components, styles/tokens.css).

## The task
1. **Three distinct visual directions** for the whole experience. Each one covers:
   - the landing / door;
   - the top bar and room navigation;
   - product dots and the product highlight;
   - the product card and close-up;
   - the many-option wheel;
   - the cart;
   - typography, colour and motion language.

   **The brief:** high-tech, innovative, magazine-like, designed and clean. For example: one editorial (big serif, white space, captions like a magazine spread); one high-tech (glass, thin lines, data-like labels, precise motion); one hybrid. Your call. They must really differ.
2. **For each direction:**
   - a rationale of 3–5 lines;
   - real screens built in the site code behind a query flag (`?design=a|b|c`), using the current renders. No fake products or art.
   - **Screens, at 1280:** the door/landing, the living room with dots, the product close-up with the wheel open, and the room navigation. **At 400:** the living room, and the product card.
   - Hebrew RTL, and accessible (contrast and focus).
3. **One short motion clip per direction,** at most 15 s and 4 MB, 1280×720: a dot opens into the close-up and the wheel. Recorded with Playwright, no var2.

## Outputs
- Screens and clips in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/fb13-site/<a|b|c>/`.
- `docs/proposals/site-fb13-design-directions-2026-11-25.md`: the three directions, their rationale, and which you recommend.
- The code behind the flag. The default look and all existing tests stay unchanged.

## Checks (EFF2)
typecheck, lint and vitest only. No full e2e, artifact build or a11y suite in this round.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- Fonts: self-hosted or Google Fonts only.
- **Don't edit** `data/`, binding documents or render folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- The disk is tight; delete what you don't hand over.
- **Your report:** a Hebrew summary of at most 12 lines: the three directions in one line each, your recommendation, and the file paths.
