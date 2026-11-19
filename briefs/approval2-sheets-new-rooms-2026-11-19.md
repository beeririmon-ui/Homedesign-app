# Brief: clean approval-2 sheets for the four new rooms (general agent, 2026-11-19)

## Why
The owner approves the product picks (approval 2) from picture sheets. The photo-check sheets of earlier today mix defaults, alternatives and items that failed. The designers have now fixed the final picks:
- **The kitchen and dining:** chapter 10 of `docs/proposals/wm-kitchen-dining-render-2026-11-19.md`.
- **The work room:** chapter 10 of `docs/proposals/wm-work-render-2026-11-19.md`.
- **The boy's and girl's rooms:** chapter ד of `docs/proposals/wm-kids-rooms-render-2026-11-19.md`.

These chapters override the earlier ones in each document.

## The task (0 tokens)
Build one clean sheet per room in `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/`:
- `ap2-kitchen-dining.jpg`;
- `ap2-work.jpg`;
- `ap2-boy.jpg`;
- `ap2-girl.jpg`.

Each sheet has, in Hebrew:
1. **A header:** the room's name, one line on its language from the chapter, and the count ("X מוצרים נבחרו, ועוד Y חסרים לליקוט = Z").
2. **"המוצרים":** a tile for each final default product for sale, using its SKU photo from `picks/img/` (`picks/manifest.json` maps them). The tile shows the product name in Hebrew, the price as in the card, and a small mark when the product repeats another room's.
   - Only products that passed or that the designer ruled on.
   - No failed items.
   - The fixed furniture (not for sale) is not shown as a tile.
3. **"הגלגל":** the sample slot's variants, side by side.
4. **"חסר, לליקוט":** a short text list of the gaps, one line each.
5. **A footer:** "תמונות ספקים, לבעלים בלבד; לא לשיתוף".

Keep the layout calm and readable on a phone: about 1440 px wide, with tiles of at least 260 px. Fetch nothing new. If a default's image is not in `picks/img/`, show the tile with "אין צילום" and list it in your summary.

## Outputs
- The four sheets.
- `picks/ap2-sheets.json`: per room, the default list, the variants and the gaps, as used.
- Nothing in the repo.

## Fixed rules
- Supplier images stay in the scratchpad. Run Python that reads them with `python3.12 -I`.
- No repo edits, no commits, no keys, no var2, and no contact with anyone.
- Return a short Hebrew summary: the count per room, and anything missing or unclear.
