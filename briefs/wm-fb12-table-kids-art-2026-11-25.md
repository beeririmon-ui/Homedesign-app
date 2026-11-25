# Brief: FB12, a new living-room coffee table, and kids' art as a many-option wheel (master-designer, 2026-11-25)

## The owner's words (FB12, 2026-11-25, in `docs/studio-rules.md`)
> "רק השולחן בסלון קצת כבד, וקצת נראה ממודל מידי ומכונתי, נחליף שולחן בבקשה. בחדרי הילדים יחסית נחמד, הייתי מחליף את התמונות למשהו שמתאים לילדים, ואולי בסקרול שיהיו הרבה אופציות להחלפה להתאמה עבור ההעדפה של הילדים"

The owner also wants faster progress (AP3-KIDS). Keep this to one tight document.

## Part 1: the living-room coffee table (warm-modern M0)
**Today:** a dark walnut oval slab on two thick drum bases. The owner reads it as too heavy, and too modelled and machine-smooth. See `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock5/screens/1280-living-room.png` and the living-room render and layers under `assets/renders/living-room/warm-modern/`.

**What to decide:**
1. **The direction.** A lighter, crafted, real-material table that reads as made by hand, not CG-smooth. Visual weight down. Keep the room's language (warm-modern Bible), the rug, the sofa and the pouf position.
   - Say what reads as "machine": the perfect radius, the uniform dark finish with no grain, the two identical drums.
   - Say what fixes it. For example: a thinner top with a visible end grain or a live-but-calm edge, a lighter or mid-tone wood or travertine with honest texture, slender legs or an open base, an irregular-organic but quiet top. Your call.
2. **The spec for sourcing:** size range against the slot box, height, material, tone (L\*), and what to reject.
3. **The candidates.**
   - First check the existing cards: `data/products/coffee-table/` (two rejected), any `coffee-table` cards in `data/products/living-room/`, and the pool.
   - New candidates come from a sourcing run after you (Israeli stores first; CJ in the parallel CJ session).
4. **The render path and cost.**
   - Is the table a product layer, or is it in the base plate of M0?
   - Does it appear in the arrival v2 video (`assets/video/transitions/warm-modern/arrival-v2/`), whose last frame lands on M0? If the table is in the arrival's frames, say what that means: a layer over the landing frame, or a motion re-render. Prefer the cheapest path that keeps the landing seamless.
   - Estimate the var2 cost (price list: nano 2K 400, 4K 450; seedream 2K 650).
5. **The sample-slot wheel.** If it fits, the new table can be the living room's wheel with 3 variants.

## Part 2: kids' art, child-appropriate, as a many-option wheel
**Today:**
- the boy's room has black-and-white botanical prints A, B and C;
- the girl's room has colourful flower prints;
- both rooms' wheel is the folded throw, V1–V3.

See `assets/renders/boy|girl/warm-modern/stage1-2026-11-24/` and the kids proposal `docs/proposals/wm-kids-rooms-render-2026-11-19.md`, chapter ד.

**What to decide:**
1. **The direction.** Child-appropriate art inside "the parents' house at a child's scale" and the warm-modern Bible.
   - For example: gentle animals, letters or numbers, simple landscapes, shapes, in each room's palette (the olive band #A8A88E for the boy, the clay pink #E8D5CC for the girl).
   - No cartoon licences or characters, no neon, nothing that breaks the house.
   - Say what stays (the frames, the ledge shelves, the sizes) and what changes (the art).
2. **The wheel.** The owner wants many options so a child can choose. The art becomes the kids' wheel slot.
   - Target 8–12 options per room. Say whether each option swaps one print or the whole set of three (A+B+C), and which is clearer for a parent.
   - Say whether the throw stays as a second wheel or goes back to a fixed default.
   - Note that a wheel change is a slot-file change (`data/slots/kids.json`). It's approved in spirit by FB12; the manager will register it.
3. **The rights (PR1).** Art is sold only with stated image rights and a full-resolution flat file. Say what sourcing must find: print shops with a commercial licence, Israeli illustrators (listed only, no contact), or CJ posters with rights stated. Otherwise the art is `unclear` and stays ×1 only.
4. **The render path and cost.** The frames face the camera almost front-on, and the earlier prints A, B and C were placed in code. Say whether all options can be placed in code at 0 tokens (perspective warp into the frame's inner rectangle, the glass/no-glass look, light and black point per WM-G1), or what needs var2. Keep fidelity: the art shown must be the art sold.
5. **The site.** The wheel UI must handle 8–12 options; MOCK5's wheel shows 3. Write one line for frontend-dev on what's needed.

## Outputs
- **A proposal:** `docs/proposals/wm-fb12-2026-11-25.md`. It holds both parts, each with a direction, a spec, candidates from existing cards, a render path with cost, and what's needed from sourcing, render, motion and frontend.
- **Two sourcing line tables,** ready to paste into a brief: the coffee table, and kids' art (per room, with the number of options).
- **A short list of owner questions,** only if something truly blocks. The default is to proceed.

## Fixed rules
- 0 tokens.
- Edit no binding document. Proposal only.
- Use the `interior-design-rules` skill, and keep to the Bible's rejection list.
- Return a short Hebrew summary covering:
  - the table direction and how you'll render it;
  - the kids' art direction and the wheel;
  - the costs;
  - what sourcing needs.
