# Brief: S11, fixes from QA S6–S7 (frontend-dev, 2026-11-10)

This continues the interface track, `briefs/site-interface-track-2026-11-07.md`, with the same working rules. The source is `qa/reports/2026-11-10-site-track-qa-s6-s7.md` plus `.json`, and the tools and data are in the folder of the same name. It starts after S10. Don't touch the S10 work beyond what these fixes need.

## Required before launch
- **ת7: the wheel opens off screen on the phone and tablet.**
  - After scrolling the room sideways and touching a product (for example the vase), the screen goes black at 400, 390 and 720.
  - Your own S6 evidence (`phone-3-wheel.png`) shows it.
  - **The fix:** the wheel and its scrim open inside the visible viewport whatever the room's scroll position. Use the visual viewport, not the scroll container's coordinates.
  - **The e2e:** opens the wheel **after a sideways scroll**, at 390, 400 and 720, in the Nordic house and the warm-modern house. It checks that the wheel is fully inside the viewport and visible, not just a dark layer.
- **ת8: the line name carries a colour that contradicts what was bought.**
  - **The rule (manager's decision):** a line = **the base name without colour** + **the Hebrew option label**.
  - **The data:** master-designer is writing it now:
    - `data/catalog/option-labels-he.json` (`labels[card_id][option][supplier value]`);
    - `base_name_he` in `data/catalog/names-he.json`.
  - **The wiring:** read both in `build-catalog.ts`. Use them in the cart, the checkout, the order snapshot (`order_items.name_he`) and the invoice.
  - **If the files aren't there yet:** build the mechanism with a fallback (the existing name), and an e2e on the 9 variants listed in the report that turns on when the data exists.
- **ת9: the server sells a single print from the triptych (₪69), against SET1.**
  - **The fix:** the server refuses (422) any SKU that is part of a set and isn't sold on its own, according to the card and the selection.
  - **Check the rest:** go over every other set (SET1: set by default, single unit as an option only where the card allows it).
  - **The vitest:** add a test for it.

## Medium
- **ת10:** remove the `name_he` override from the corduroy dot in ed8 (`data/story/story.json` or wherever it's built), so the §11/§13 name, or master-designer's new one, wins.
- **ת11:** a product that stops being sold after it was added to the cart disappears without a notice.
  - Show a quiet notice in the cart: "פריט אחד כבר לא זמין והוסר".
  - Keep the honest behaviour: no charge.
- **ת12:** the 245 English labels are closed by the same mechanism as ת8.
  - Add a build check that fails if a public label contains Latin letters, apart from units if any.
  - It turns on once master-designer's file exists.

## Small
- **ת13:** the story cart is still called "סל הבדיקה". Make it the regular site cart name.
- **ת14:** the table of contents has no "חזרה לסיפור", because the tool rejects `from=/story/`. Allow the internal story index (`/story/`) as a valid origin.

## Acceptance
- **All the checks:** typecheck, lint, format:check, vitest, e2e, a11y and budget.
- **New tests:** for ת7, ת8, ת9 and ת14.
- **Evidence in `qa/reports/2026-11-07-site-track/s11/`:** a README, the phone screens of the wheel after scrolling, and the cart and the order with the new names.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
