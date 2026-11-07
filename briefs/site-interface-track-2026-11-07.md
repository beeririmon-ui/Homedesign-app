# Brief: the interface track, a continuous workstream (frontend-dev, 2026-11-07)

**The owner (2026-11-07):** "יש עוד המון עבודה על הממשק עצמו ואנחנו נתקעים מלא". The new working rule is studio rules ז, "זרימה בלי עצירות": a question never stops the work. It goes into the queue with a recommendation, and everything else continues. The interface doesn't wait for renders. It works with temporary frames and switches to final assets only after QA (`CLAUDE.md`, stage 4).

## The binding spec
- `docs/skeleton-spec.md` 2.0, chapter "שלוש שכבות וזרימת האתר":
  - layer 1 is the story;
  - layer 2 is the detail;
  - layer 3 is "עצב בעצמך";
  - the flow is story → "קנה את המראה" → the tool;
  - a style switch is a cut between houses in the story and a soft transition in the tool.
- Studio rules א.6 (the whole site at magazine level), ו (the site, interface and motion), and ו.5 as updated (no swapping in story frames).
- The G-ED gate (`docs/ops/quality-gate-g-ed-2026-11-07.md`): which frames may appear, and in what state.

## The track: sprints, each ending in green checks and evidence for QA
**S1, layer 1 as real routes behind the flag.** Grow `/test/story/` into the real structure:
- a story index (rooms × styles);
- one page per room and style, generated from one data file: frames, story lines, hotspots, product lists, QA state;
- the QA-state gate you built;
- only "final test" and "almost" frames;
- typographic placeholders for room/style pairs that have no frame yet, never an unapproved frame;
- everything behind `HD_PUBLIC=0` until assets pass "approved for the site".

**S2, layer 2, "הפרט", the product page.** Card images (temporary supplier images where cached), options, price from the pricing code, "בחדר הזה" links back to the story frames that show the product, and a deep link into the tool at its slot.
- Close-ups are what G-ED.18 needs, so build the slot for a close-up image, even while it is empty.

**S3, story → tool.** Enter the tool from a story frame in the same room and style. Use the Nordic tool for now.
- Plan the per-style house of DIR2. The warm-modern tool shell is coming from the pilot. Prepare the style switch as a soft transition between two houses.

**S4, the shop.**
- "קנה את המראה": add the whole look, or the products one by one.
- The cart and the mock checkout.
- PRE1 and MED1: one wheel option may be "המלאי אינו זמין כעת" while the other two are in stock. Show this clearly and never sell it.
- Products without a price are listed without an add button.

**S5, the magazine design system.**
- Typography, grid, rhythm, motion and micro-interactions to א.6.
- Navigation, empty and error states, and performance budgets.
- WCAG 2.1 AA, RTL Hebrew, and phone first.

Order: S1 → S2 → S4 → S3 → S5 is a suggestion. Reorder if dependencies say so, and tell me why.

## How you work
- **Decide within your authority, and keep going.** If a choice is reversible, take your best recommendation as the default, note it, and continue.
- **Questions don't block.** List each one at the end of your sprint summary, with a recommendation and what currently runs on the default. I put them in the owner's queue.
- **Design questions** (layout, type, crops) are master-designer's. List them the same way; don't wait.
- **No commits.** I commit after each sprint. If your run is interrupted, the work in the tree is picked up as WIP.
- No var2, no keys, no supplier contact, no network beyond npm.
- The repo's full checks pass at the end of each sprint: typecheck, lint, format:check, test, e2e, a11y, budget.
- **Evidence goes in `qa/reports/2026-11-07-site-track/s<N>/`:** README, screens at 400 and 1280, and timings.

## After each sprint
Return a short Hebrew summary:
- what was built and how to open it;
- the check results and the weights;
- questions with your defaults;
- the next sprint.

Then continue to the next sprint unless I say otherwise.

## Open items from your last report, to fold in
- **The runner card's `default_sku`** is 33×183, but the owner's selection uses 33×122. master-designer is fixing the card; read the card, don't hard-code it.
- **Seven products have no price** and **11 cards have no cached image.** Keep the honest empty states.
