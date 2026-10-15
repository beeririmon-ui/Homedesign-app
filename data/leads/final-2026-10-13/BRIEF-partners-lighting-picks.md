# Picks from our two lighting partners: Studio Mabua and Studio Vayehi (2026-10-15)

Both studios replied that they're interested (`docs/suppliers/outreach/replies/`). The owner wants to talk with them seriously.
- He needs to know **which of their products we want, for which room, slot and style.**
- The art director works out the margins separately.

## Input
- **The catalogue:** `data/leads/final-2026-10-13/partners-lighting-catalog-2026-10-15.json`.
  - Every product with its sizes, prices, materials and colours.
  - Local images (absolute paths under `.../scratchpad/partners/`). **Look at the images.** You can Read them.
- **Slots:** `data/slots/<room>.json`. Look at the lighting slots (category "lighting"): envelope, placement, electrical and set_of.
- **What's still missing per style:** `data/leads/final-2026-10-13/coverage.json` → `remaining.<style>`.
- **Style rules:**
  - Nordic: `docs/design-bible/nordic.md`, `docs/design-bible/nordic-dining.md`. Note the lighting section, which forbids brass, glass, opaque metal and arcs.
  - The other styles: `docs/design-bible/<style>-brief-draft.md`.
  - `.claude/skills/interior-design-rules/`. Use the skill.
- **Binding rules:** `docs/studio-rules.md`.
  - ה.14 (masterpiece and price tiers): every room in every style has at least one "wow" piece. Handmade pieces from an Israeli maker are explicitly allowed as masterpieces (ג.4).
  - ה.11: prefer 40% margin, but lower is allowed when no equally beautiful option reaches it.
  - The lighting rules: ד.3, ד.5, and the 2026-10-14 entries in ז.

## What to decide
1. **For each product (and size or colour), and for each lighting slot where it could go:**
   - the style fit, 1–10, for each of the six styles, judged from the image;
   - the envelope fit: yes, borderline (±5 cm), or no. Say which size option fits.
2. **Its role:**
   - `fills-gap`: a style needs this slot (`remaining`);
   - `upgrade`: better than the current picks;
   - `masterpiece`: the room's wow piece for that style.
   - Be selective: a masterpiece must truly be the most beautiful object in that room.
3. **A short list per studio:** the 4–8 products we would actually ask them for, ranked. For each, give the slot(s), the style(s), the size and colour, and one line on why.
4. **What to ask them to make or adapt:** for example a smaller size for an envelope, a colour, or a shade for a different slot.

## Output (write only this; no commits)
- `docs/suppliers/lighting-partners-picks-2026-10-15.md`, in Hebrew:
  - one table per studio: product (and link), size and colour, room/slot, styles (score), role, envelope fit, why;
  - the short list per studio;
  - the adaptation requests.
- `data/leads/final-2026-10-13/partners-lighting-picks-2026-10-15.json`, the same content:
  `{"studios": [{"name": "", "picks": [{"slug": "", "size": "", "color": "", "slot": "<room>/<slot>", "style_fit": {"nordic": 0, ...}, "role": "fills-gap|upgrade|masterpiece", "envelope": "yes|borderline|no", "why_he": ""}], "shortlist": ["slug"], "adapt_requests_he": [""]}]}`.
  You can't run a parser, so check the brackets carefully.

Return a short Hebrew summary:
- the short list per studio;
- which gaps and masterpieces they cover;
- what to ask them to adapt.
