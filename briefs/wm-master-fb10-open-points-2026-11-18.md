# Brief: the bedroom FB10, four open points (master-designer, 2026-11-18)

## Why
render-agent added the FB10 products to MB0. There are now 19 for sale (chapter 13 of `docs/proposals/wm-master-bedroom-render-2026-11-17.md`). It left four points for you. QA is checking the additions in parallel.

## Inputs
- **The FB10 chapter** in `assets/renders/master/warm-modern/stage1-2026-11-17/README.md`: the table, and "פתוח".
- **The frames:** `mb0-defaults-frame.png` and `fb10/fb10-qa-sheet.jpg` in that folder.
- **The cards:**
  - the planter card in `data/products/planter/` or `data/products/master/`;
  - the travertine dish card.
- **The SKU photos:** `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/img/`.
- `docs/design-bible/warm-modern.md`.

## What to decide (0 tokens)
1. **The planter tone.** The Beige listing has no photo of its own, and the listing photo is grey (L* 54, b* 4). render-agent chose a warm greige (L* 64, a* 2.5, b* 9.5). Decide:
   - keep it;
   - give a target;
   - or say the card needs a different colour option or SKU.
   Remember the rule: fidelity before beauty.
2. **The dish height.** The card gives none; 1.8 cm was assumed (the photo reads 1.5–2). Accept or correct.
3. **The ficus crown beyond x 2641,** outside the frame, which is mirrored from the edit. Does it matter for motion (the MB0 approach clips), and if so, what should be there?
4. **The fake text on the magazines** in the holder. Keep it unreadable, blank it, or use our own covers later? The holder is for sale; the magazines are filler.
5. **One look at the whole frame** for balance and "taking the stage": anything to move or rescale in code before the owner sees it?

## Outputs
A dated section "13.11 FB10: הכרעות על התוספות" in `docs/proposals/wm-master-bedroom-render-2026-11-17.md`, with one ruling per point and any code fix for render-agent, with numbers.

## Fixed rules
- 0 tokens, no var2, no commits, no keys. Don't edit a binding document, `data/`, or another agent's files.
- Return a short Hebrew summary: the five rulings.
