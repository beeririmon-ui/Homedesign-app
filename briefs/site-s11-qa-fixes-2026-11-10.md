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

## Addendum, 2026-11-10: the names data is ready
master-designer's files are ready: `docs/proposals/names-labels-he-2026-11-10.md`. The manager checked them with a parser: they're valid, every key exists in the cards, and no label has Latin letters apart from "3000K".
- **The data:**
  - **`data/catalog/option-labels-he.json`:** `labels[card_id][axis id][value id]`, 629 labels across 69 cards. These are the same keys the SKU carries.
  - **`data/catalog/names-he.json`:**
    - **`base_name_he`:** a new top-level map, 65 names.
    - **`frame_names_he`:** the corduroy name.
    - **`t10`:** the location of the dot.
- **The line rule:** base name · the option labels in the order of the axes in the card.
- **14 products with a name the build composes itself:** compose it from the base name plus the default option's label.
- **ת10, two parts:**
  - remove `name_he` from the dot (points[5] of frame A in the warm-modern pair);
  - in that frame's `alt_he`, replace "בטאופ" with "בקאמל".
- **The white bouclé:** "לבן חם" everywhere, including the dot in warm modern and the set A label.
- **Manager's decisions, about what's sold:**
  - **The floor lamp with the walnut pole:** the two smart variants work only with a Chinese voice assistant, so they're not sold. The table variant is another product, so it's not sold either. Only the regular floor-lamp variant is sold.
  - **CJ's travertine lamp and the black bowl:** only identified variants are sold. Unidentified variants, the ones labelled "דגם א׳…ר׳", aren't offered until sourcing describes them.
  - **The Mediterranean print:** every SKU is a single print, but the product is shown as a triptych. Give it a set mechanism like the Nordic triptych, inside ת9: it isn't sold as a single print.
  - **Implementation:** these come from data (an exclusion list or a flag in the selection, your choice). They're checked in vitest, and nothing is hard-coded in components.

## Addendum 2, 2026-11-10: after S10
S10 is done: the warm-modern house in the engine, `?style=warm-modern`. Evidence: `qa/reports/2026-11-07-site-track/s10/`. Also add to S11:
- **S10 question 2:** names that clash with the shade, for example "מרווה" on a camel cushion, or "לבן שנהב" on a Pecan throw. They're resolved by the ת8 rule (base name · label). Apply it to the house's wheel and sets as well, and to the temporary composed name of set B's bouclé.
- **S10 question 7:** a direct entry to `?style=warm-modern` still downloads the Nordic poster for nothing. Fix it with a Worker rewrite or a prebuilt page per house, whichever is cheaper.
- **Dead code:** `toolRun` in `site/tools/screens-story.ts` and the `.st-td*` CSS in `story.css`.
- **Not in S11, defaults stand:**
  - the set names, question 1 (master-designer will review);
  - the throw at 150×200, question 3;
  - the full overscan canvas, question 6;
  - "לכניסה" without the movie, question 8;
  - the depth map, question 5 (phase 2 of the tool);
  - the base encoding threshold, question 4: QA decides it in the next site QA round. It blocks `HD_PUBLIC=1` only.
