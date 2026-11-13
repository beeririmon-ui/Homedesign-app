# Brief: MOCK3, the whole frame first and the folded controls (frontend-dev, 2026-11-13)

## Why
The owner tried MOCK2 (`briefs/site-mock2-smooth-wheel-2026-11-13.md`, done at `4fff7b24`) on his phone. His feedback is rules FB2 and FB3 in `docs/studio-rules-digest.md`, under EFF1.6. Read FB1, FB2 and FB3 first. In his words:
- "זה שכל הפריים זז כאילו שהוא גדול יותר מהמסך של הטלפון זה קצת בעייתי, אני חושב שהדבר הראשון שרואים זה כל הפריים, ואם הלקוח רוצה אז הוא יעשה זום אין."
- "החלונות מודלים שלמטה, הם מסתירים חלק מהמוצרים. אז אולי צריך להיות איזשהו מודל שהוא מתקפל… איזה ריבוע קטן למטה שיסמן את המשך הסיור… כדי שיהיה כמה שיותר נקי ולחוות את כל הבית בחוויה מלאה."
- He likes the light-line reveal (B): it stays the default.
- The transition clips between rooms are "עיקר החוויה". They are paid work and are not in this sprint, but this sprint builds the window they will play in.

## The design source
`docs/proposals/tour-whole-frame-phone-2026-11-13.md` (master-designer). Read all of it; it is the spec for this sprint: one 16:9 window in every phase, the bands above and below it, the product strip, zoom, the close-up and the wheel under the window, the folded "המשך הסיור" control and its panel, landscape, desktop, the switches and the strings. Where it differs from `docs/proposals/wow-tour-experience-2026-11-12.md` or from `docs/skeleton-spec.md`, build the new spec. The skeleton is updated after the owner approves the tour language.

## Scope, in order of priority
If your context runs low, finish a priority level, leave the checks green and the artifact build working, and write "where I stopped".

**P1. The phone, portrait (this is what the owner holds):**
1. The 16:9 window at full width with no crop, and the two bands (spec: "הפריסה בטלפון לאורך"). The door, the entry, the reveal, the style change and the close-up all happen inside the window.
2. The product strip under the window, filled together with the reveal (spec §2, §3), and the tap rules on the window (nearest marker, the ×2 zoom when two markers are close).
3. Zoom: pinch and the button, the limits, the return (spec §4).
4. The close-up inside the window, with the wheel in the lower band in place of the strip, and the larger centre card (spec §5). Nothing covers the product.
5. The folded control "המשך הסיור" and its panel: rooms, style, "קנה את המראה", "בקרה זמנית" last (spec §10, §6). The "copy report" button from MOCK2 stays inside "בקרה זמנית".

**P2. Desktop and landscape:**
6. Desktop: the window in contain, the 64 px band under it, the folded control (spec §9). The title, the counter and the controls no longer sit on the picture.
7. The rotated phone: the two rails, the wheel on the window's bottom edge, and the one quiet invitation to rotate (spec §8).
8. Tablet, as the spec says, if it falls out of the two layouts. Otherwise say what it does today.

**P3. Small items that ride along:**
9. The switches in "בקרה זמנית" (spec: "מתגים"). "מילוי וגרירה" is today's mode and must stay working. Build the others where they are cheap, and list the ones you left out.
10. The soft edge of the Nordic living room's temporary layers at 1920: the fix you found in MOCK2 (`silhouette()` in `site/tools/make-temp-assets.ts`). Approved by the manager. Re-run the gates that cover those files, and say in the README which media changed and that the public build is unchanged or how it changed.
11. Sharpness when zoomed on a phone: measure it at ×2 and ×2.5 (DPR 2.6 and 3), with two crops, against the same view composed from the 2720 layers. Don't ship 2720 to phones by default. If the difference is visible at ×2, propose the cheapest way to sharpen only what is in view at rest (loaded and uploaded in still frames, under the zero-counter rule), with its cost in memory, and build it only behind a switch.

## What must not regress (MOCK2)
- During every effect, old and new (the strip filling, the panel opening and closing, the wheel entering, zoom, the return): 0 decodes, 0 texture uploads, 0 shader compiles, 0 readbacks, 0 forced layouts. The spec's own rule: the window's size is measured only on load, resize and rotation.
- Overlays animate with transform and opacity only. No blur or filter over a large area.
- The settled frame stays pixel-exact to the plain composite, in the window, at ×1. The seam tests still pass.
- `prefers-reduced-motion`: opacity only.
- Budgets: first load ≤ 3 MB on the phone, room JS ≤ 80 KB (goal ≤ 74). The strip's images are the wheel's cards, already loaded; say what the strip adds.
- Everything stays behind `HD_PUBLIC=0`. The public build is unchanged, except what item 10 changes, and you say what that is.

## Accessibility
- The strip is the list for a screen reader; the markers on the window are decoration on the phone, as the spec says.
- The folded control is a button with a name and `aria-expanded`; focus moves in on open and back on close; Esc closes.
- Every touch target is at least 44×44 CSS px. Keyboard reaches everything on desktop.

## Acceptance
- **The repo's checks:** `npm run test:all`, check:config, check:rights, check:promises, the encoding gate, both builds, the budgets.
- **New tests:**
  - on the phone profile, at rest, nothing overlaps the window except the markers (bounding boxes), in portrait and in landscape;
  - the whole frame is visible at rest: the window's box is 16:9 and inside the viewport;
  - the zero-counter test covers the new effects;
  - the folded control: opens, closes in the four ways, focus returns;
  - the tap rules on the window, and a strip tile opening the same close-up as its marker;
  - zoom limits and the return to ×1.
- **A fresh `npm run preview:artifact`,** inside the size limits, for the manager to publish to the same page. Say which media files changed since MOCK2 (added, replaced, removed), as three lists of paths in a JSON file in the evidence folder.
- **Evidence:** `qa/reports/2026-11-07-site-track/mock3/` with a README (what the owner will see on his phone step by step, the counters, the weights, the sharpness measurement with its crops, the switches built and left out, what is temporary), and screenshots at 390×844 portrait, 844×390 landscape and 1440×900: the door, the room at rest, zoomed, the close-up with the wheel, and the panel open.
- **Working files in the scratchpad (EFF1).**

## Out of scope
- A real transition clip and its player (the next sprint, when the clips exist). The panel shows the bedroom as "בקרוב".
- The door's final design; the choice between the reveals; product studio shots; `status/backlog-low.md`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm. Every `npx` with `--no-install`.
- Don't edit `data/`, the selection, the slots file or any binding doc. Don't copy a supplier image anywhere.
- New copy: only the spec's strings. If you need one more, take a short default and list it for master-designer.
- Return a short Hebrew summary: what the owner will see on his phone, step by step; what you built at each priority level; the numbers; what is temporary; your open questions with the default you took.
