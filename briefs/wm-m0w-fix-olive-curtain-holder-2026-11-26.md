# Brief: M0-W, three fixes from the owner (render-agent, 2026-11-26)

## The owner's words
> "העץ בעציץ נראה ממש מוזר כמו עלים מרחפים באוויר, אין ווילון, ומחזיק העיתונים חתוך"

The frame is `assets/renders/living-room/warm-modern/fb13-2026-11-25/default-frame-m0w.png`. The stack: `layers/manifest.json`, `plate-PW.png`, `hero-HW.png`. The README has the method and the light targets.

## The three fixes (in-context nano 2K edits on the hero, about 400 each)
1. **The olive tree in the ribbed planter.** It's filler, not sold. It must read as a real potted olive standard:
   - a believable trunk and branches that carry every leaf cluster, with no floating leaves;
   - dense, natural silvery-green foliage;
   - the same height and footprint;
   - its leaf shadow on the plaster consistent with the sun, 228°/15°.

   The planter is the product: keep it exactly.
2. **The curtain.** Add the linen curtain at the window, half-drawn, with the sun passing through the linen (proposal 3.1 styling).
   - Use the curtain product the living room uses (see the card in `data/products/living-room/` or the old manifest's curtain layer).
   - It must be visible in the frame: at the left glazing edge, at least 50% visible so it counts.
   - Don't cover the vase or the window bench.
3. **The newspaper holder** is cut by the bottom edge. Place it fully in the frame, at least 90% visible.
   - Put it on the floor where it reads as intended, for example beside the armchair or near the sofa's left end.
   - Keep F3 gaps, with no overlap with the basket, the planter or the table.
   - Keep it with its two newspapers, and with real contact shadows in the hero light.

## Then
- **Re-extract** the changed layers (curtain, holder, planter if touched) by the same method as the hero (base = plate, products cut from the hero, shadow and light as the hero/plate ratio).
- **Rebuild** `default-frame-m0w.png` under a new name (`-fix1`), with a new manifest. Keep the old one for rollback.
- **Checks:**
  - RND2 is 0 outside the edited regions;
  - the light targets hold;
  - every product is still true to its SKU.
- **The QA sheet:** `qa-sheet-m0w-fix1.jpg`, before and after at ×1, and ×2 of each fix.

## Fixed rules
- **Spend cap: 1,600** (up to 3 edits, plus one retry). Stage A stands at 3,900 of 6,500.
- **var2:** never ask for codes. If var2 asks for re-auth, stop and report.
- **Scope:** don't touch `data/`, `docs/`, `site/`, or other rooms. Another render-agent is working in the other rooms right now.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight; delete scratch.
- **Work economically.**
- **Your report:** a Hebrew summary of at most 8 lines.
