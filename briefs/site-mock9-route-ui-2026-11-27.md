# Brief: MOCK9, the guided route plus a refined, minimal UI, for the warm-modern site (frontend-dev, 2026-11-27)

## The owner's words
- **FB21:** "מסלול מודרך... בנר עדין כזה שמדגיש את המסלול הבא, שלוחצים חץ הלאה... כמו גלילה כזאת של חדרים, אבל לפי סדר ברור. ואז אם הולכים 2 תחנות קדימה, זה רץ מהר יותר המעברון".
- **FB19:** "העיצוב של האתר, של כל המודלים וכל הבאנרים, בעצם שיהיו מינימליסטים, חצי שקופים, עדינים, כאילו שהפונט יהיה ראוי... לוגו... שיהיה גם בהתחלה, ואז הוא עולה הצידה ימינה למעלה, בעדינות, ונהיה קטן".
- **2026-11-27:** "בוא נתקדם לאתר עם המודרני החם".

## What to build (design C, behind `HD_PUBLIC=0`)
1. **The guided route.** The order is living → kitchen (D1) → bath (B1) → bedroom (MB0) → boy → girl → work.
   - **A delicate route banner:** semi-transparent, minimal. It shows the current station and highlights the next one, with a "הלאה" arrow, plus a slim station strip in clear order that scrolls like a rail of rooms. Tapping a station further ahead travels there.
   - **Leg 1 is real:** `assets/video/transitions/warm-modern/route-fb21/leg1/final/` (manifest, ease frames marked). It's scroll-scrubbable like the arrival, and "הלאה" plays it.
   - **Legs 2–6 don't exist yet.** Use the best code transition you have as a placeholder, behind the same interface, so each real leg drops in with one line.
   - **Jumping ahead 2+ stations** plays the legs chained at ×2–×3, skipping the ease frames between legs.
   - **Going back:** a designed soft fade through the light, about 450 ms. No reverse video.
2. **The UI refinement pass.** Everywhere: the product card, the wheel panel, the banners, menus and the cart.
   - Minimal, semi-transparent (frosted only if it stays crisp and clean), and delicate.
   - Typography: a fitting font pairing for Hebrew, a serif for display and a clean sans for UI. Keep self-hosted fonts.
   - Calm spacing; nothing heavy or boxy.
   - It must read premium and editorial on phone and desktop.
3. **The logo intro.** There's no brand name yet, so use a placeholder wordmark, "הבית", as a component that's easy to swap.
   - On first load it appears centred, large and elegant.
   - Then it rises gently to the top right and shrinks into the header.
   - It plays once per session; with reduced motion it is static.
4. **Keep all MOCK8 content:** the arrival, the cushion wheel, the studio stills, the FB16 light.

## Outputs
- `site/dist-artifact/` rebuilt, with `check-artifact` passing (at most 255 files).
- A walkthrough video, at most 15 MB, 1280×720: `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock9/walkthrough.mp4`. It shows the logo intro, the scroll walk, the living room, the route banner, "הלאה" playing leg 1 into the kitchen, a jump ahead 2 stations, and the refined product card and wheel.
- Phone screens at 400: the route banner, and the product card.
- A short "MOCK9" section in `site/README.md`.

## Checks
typecheck, lint, vitest, and e2e for mock8 plus a new mock9 spec. Both builds.

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- **Don't edit** `data/`, binding docs or render folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Disk:** it's tight, about 600 MB; clean up.
- **Work economically.**
- **Your report:** a Hebrew summary of at most 8 lines.
