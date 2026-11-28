# Brief: MOCK12, several wheels per room, and studio pictures everywhere outside the room (frontend-dev, 2026-11-28)

## The owner's words (FB29, `docs/studio-rules.md`)
> "בדף שמחוץ לתצוגה בחדר של המוצר יהיה תמונה שהיא לא חתוכה כמו שעכשיו... שיראה כמו צילום של המוצר מחדש... שיראה טוב גם בגלגל וגם בתצוגת מוצרים למטה... עכשיו זה נראה כזה כמו עם פדר, חיתוך פדר מסביב... וגם... משהו מסתיר אותו, אז הוא חתוך".

## What to build (design C, behind `HD_PUBLIC=0`)
1. **Several wheels in one frame** (plan `docs/proposals/wm-wheels-plan-2026-11-28.md`, section 7.2).
   - Each slot that has options gets its own RingWheel from its product mark.
   - The choices of all wheels compose together on the stack.
   - In a room's second frame (MB1, B1), show the default until it has its own layers.
   - render-agent is rendering round 1 now and will write per-room wheel manifests next to the current ones (the M0-W `manifest-wheel*.json` format). Read those when they appear, and make a new room's wheels a one-line config change.
2. **Studio pictures everywhere outside the room:** the product strip below the room, the wheel, and the product card or page.
   - Use the studio still from `assets/renders/wheel-studio/warm-modern/manifest.json` wherever one exists for the product.
   - Never a feathered crop of the room render.
   - Until a product has a still, keep the current fallback, but make it clean: no feathered rim, and no crop that is cut by an occluder (use the supplier photo or the slot's name instead, whichever the current rules allow).
   - Write the list of products still on the fallback to `site/.generated/studio-missing.json`. The designer is making the full stills list.
3. **The look of a studio picture in the strip and the wheel:**
   - the cream background, as a rounded tile or a circle in the wheel;
   - soft edges, no hard box;
   - it must read well on design C's dark UI.

## Outputs
- `site/dist-artifact/` rebuilt, with `check-artifact` passing and the batches listed.
  - **Build offline:** run `tools/supplier-images.ts` only with `--offline`, with no network downloads. A new product without a cached photo gets the fallback.
- Phone screens at 400 and a desktop screenshot: the strip with studio pictures, and two wheels open in one room. Save them to `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock12/`.
- A short "MOCK12" section in `site/README.md`.

## Checks
typecheck, lint, vitest, e2e mock10 and mock11, plus a new mock12 spec (two wheels in a frame compose; the strip uses studio pictures; no feathered crop). Both builds.

## Fixed rules
- 0 tokens, no var2, no commits, no keys, no network downloads.
- **Don't edit** `data/`, binding docs or render folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Your report:** a Hebrew summary of at most 8 lines.
