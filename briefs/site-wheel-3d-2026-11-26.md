# Brief: the 3D product wheel (frontend-dev, 2026-11-26)

## The owner's words (FB20, `docs/studio-rules.md`)
> "המוצרים יופיעו בעיגולים, אבל הם יזוזו על גלגל תלת-ממדי, שאתה גולל ימינה שמאלה... במבט של 30-45 מעלות על הגלגל. וברגע שאתה בוחר מוצר, ההתקהות של החדר מתבהרת חזרה, המוצר מוטמע, ורואים את המוצר בסביבה... בגלגל [השמיכה] מקופלת, וכשלוחצים עליה רואים אותה מונחת על הספה... עיקרון לכל המוצרים"

## What to build (in MOCK7, design C, behind `HD_PUBLIC=0`)
1. **The wheel as a real 3D carousel.**
   - **The ring:** the options are circular cards on a ring, seen from 30–45° above, with the ring's front arc nearest the viewer. Cards in front are larger and sharper; cards behind recede, dim slightly and blur.
   - **Movement:** drag, swipe, wheel or keys rotate the ring left and right, with inertia and a gentle snap to the nearest card.
   - **Scale:** it works for 3 to 12 options. It replaces today's arc and the scroll-snap carousel.
   - **Tech:** CSS 3D transforms or WebGL, your call. 60 fps on a mid phone; respect `prefers-reduced-motion`.
2. **The selection moment.**
   - While the wheel is open, the room is dimmed.
   - On select, the dim lifts smoothly back to full brightness as the product's layer appears in the room, with a soft cross-fade of the in-room patch, so you see it in place.
   - Fine-tune the timing so it feels like a reveal, about 600–900 ms.
3. **The data contract for studio thumbnails.** Each option carries two images:
   - `studio`: the product as sold, for example a folded throw, on a uniform studio backdrop;
   - `in_room`: the layer or patch already used.

   Until the studio renders exist, fall back to today's thumbnail. Give the field a clear name and document it in `site/README.md`.
4. **The living room's wheel:** the cushion sets B, A and C as they land, from `assets/renders/living-room/warm-modern/fb13-2026-11-25/` (render-agent is producing A and C now). If they aren't there yet, use the kitchen or bedroom wheel for the demo.

## Outputs
- The code. A short clip at most 15 s, 1280×720, at `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/wheel3d/clip.mp4`, showing open, rotate, select and reveal.
- Screens at 1280 and 400.

## Checks
typecheck, lint, vitest, and the mock7 e2e (updated for the new wheel).

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- **Don't edit** `data/`, binding docs or render folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Disk:** it's tight; clean up.
- **Work economically.**
- **Your report:** a Hebrew summary of at most 8 lines.
