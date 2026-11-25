# Brief: kids' art, picking sets for the wheel from the existing cards (master-designer, 2026-11-25)

## Why
FB12: the owner wants child-appropriate art in the kids' rooms, with many options in the wheel. Your proposal `docs/proposals/wm-fb12-2026-11-25.md` sets the rules:
- ב.3, the art spec;
- ב.4, one option is a whole set A+B+C, with 10 per room and at least 8;
- ב.5, the rights;
- ב.6, the render path in code;
- ב.7, the existing cards yield 4–6 sets per room.

Sourcing found no Israeli artist with stated rights (`data/leads/fb12-2026-11-25.md` §2). So this round builds the wheel from the existing AE cards only. All of it is `unclear`: ×1 only, "עוד לא במכירה", allowed in the preview.

## Inputs
The contact sheets have one image per design, with a number and the exact design value from the card:
- `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/kids-art-review/sun-rainbow-sheet-1-of-3.jpg`, `-2-of-3.jpg`, `-3-of-3.jpg` (S01–S33):
  - S01–S07 are pictures;
  - S08–S33 are the letters A–Z.
- `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/kids-art-review/bunny-sheet-1-of-2.jpg`, `-2-of-2.jpg` (B01–B23).
  - Only 30×42 unframed.
  - The agent marked 9 images as landscape (B01, B02, B17–B23). Check whether the print itself is landscape, or only the photo.
- `.../scratchpad/kids-art-review/index.json`: per number, the SKU ids by size, and the pixel size.
- The rooms today:
  - `assets/renders/boy/warm-modern/stage1-2026-11-24/K-boy-defaults.png`;
  - `assets/renders/girl/warm-modern/stage1-2026-11-24/K-girl-defaults.png`;
  - the frame quads A, B and C in each room's `manifest.json`.
  - All three frames are portrait.
- The Bible `docs/design-bible/` (warm-modern), and the kids proposal `docs/proposals/wm-kids-rooms-render-2026-11-19.md`, ch. ד.

## The task
1. **Screen every design** against ב.3 and the Bible.
   - Give each one a keep or reject, with a one-line reason.
   - Reject letters, text and names, faces drawn as cartoons, dressed bunnies, bears in cartoon style, neon, and anything landscape-only (ב.6: no paid frame change).
2. **Build the sets per room.**
   - As many as honestly pass, up to 10 per room, at least 4 if possible.
   - Each set is A+B+C, from one card. Give the design numbers and the unframed SKU id for each panel.
   - Say which designs can repeat across sets, and which room each set suits (olive band #A8A88E for the boy, clay pink #E8D5CC for the girl).
   - Order them per ב.4. The first is the default.
3. **Check each panel's source image for use in code** (ב.6).
   - Is it flat art, or a mockup with a frame and props?
   - What's the usable art rectangle in pixels?
   - Does it reach about 240 px per panel (×1) and about 480 px (×2)?
   - Mark any that are ×1 only.
4. **Each set against the throw V1–V3** in that room: one line, with any pairing to avoid (ב.4).
5. **If fewer than 4 sets pass in a room,** say so plainly, and say what sourcing must bring (CJ or a new AE seller).

## Outputs
A new section, **"ב.9 הסטים מהקיים (2026-11-25)"**, at the end of part ב of `docs/proposals/wm-fb12-2026-11-25.md`. It holds:
- the screening table;
- the sets per room, in order;
- the source-image check;
- the pairing notes;
- a ready-to-paste table for render-agent: room, set number, panel A/B/C → design number, image path, and crop rectangle if needed.

## Fixed rules
- 0 tokens. Edit no binding document. Change only the proposal file.
- Use the `interior-design-rules` skill.
- Supplier images stay in the scratchpad. Don't copy them anywhere.
- Return a short Hebrew summary:
  - the number of sets per room, and the default for each;
  - what was rejected and why, in one line;
  - whether it's enough, or what sourcing must bring.
