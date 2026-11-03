# Brief: the test page in the magazine language (frontend-dev, 2026-11-03)

The owner approved the art direction today: ART1–ART7, FOC1–FOC3, TR1–TR2 (`status/decisions.json`; studio rules ו.9 and the ז log of 2026-11-03). `docs/site-art-direction-2026-11-02.md` is now the basis for everything the customer sees (א.6), and its §12 is your build order. Bible 1.8 (`docs/design-bible/nordic.md`) carries the final typography and interface sections.

## What to build
The Nordic test page of brief `briefs/nordic-house-render-2026-10-24.md` §8.1 and §9, in the art direction's language, phone-first:
1. **Cover (H0)** with the brand placeholder "הבית" (ART5) and the designed loading (art direction §8).
2. **Contents** instead of a nav bar; the unavailable styles as "בגיליונות הבאים" (ART7).
3. **The living-room spread (M0):** full-bleed frame, a clean room at rest (ו.4), the hotspots, the credit line per product (name · material · size · price), the variant strip in focus mode, focus mode per `docs/focus-mode-spec-2026-11-02.md` (uniform softness, dim and lift as display-only, 300 ms in-place dissolve, the return on the landing curve, pixel-exact landing; §1.4 and §4.4 updated today for the new M0), one cushions close-up on the phone (FOC2).
4. **One more spread** (the dining room D1) and the walk between them with the player as it is after today's fixes: the code pan where `pan_reproject.py` registered (P-D passed; see `assets/renders/transitions/README.md`), constant speed (TR2), no push zoom; where no clip exists, the art direction's paper transition, never a fake walk.
5. **Interface motion:** the tokens of §6.1 and §7.1, ≤200 ms fade only, reduced-motion behaviour; the forbidden list of §7 (no bounce, no pulsing dots, no spinners, no parallax).
6. **States:** hover, focus, press, loading, empty, error in the same language; focus rings as designed; WCAG AA and ת"י 5568 (ו.3).

## Images
Temporary only: the current `*-graded-v3.png` frames (M0 r2 for the living room until the new-camera M0 exists; D1 v7). None of them passed QA; label the page "בדיקה, תמונות זמניות" and keep the asset paths in one manifest so the swap to QA'd assets is one change (`site/web/...` per your structure). Never present a non-QA'd frame as final.

## Acceptance
- The 25 checks of art direction §10, each with evidence under `qa/reports/2026-11-03-site-test-page/` (screenshots at 1280 and 400, measured durations, contrast, fps where measurable headless; say what needs a real phone).
- The site's own checks green (typecheck, test, lint, a11y, e2e, budget), outputs in the same folder.
- No new dependencies. No edits to binding documents, prompts, renders or slots.

## Fixed rules
- No commits. Return a short summary in Hebrew: what the page has, the §10 checks passed/failed with evidence paths, and what waits (assets, the new M0, transitions).
