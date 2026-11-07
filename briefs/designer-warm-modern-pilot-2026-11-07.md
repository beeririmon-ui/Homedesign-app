# Brief: preparing the warm-modern tool pilot (master-designer, 2026-11-07)

**The owner (2026-11-07), on your proposal `docs/proposals/tool-shells-and-qa-items-2026-11-07.md`. All recorded in `status/decisions.json` and studio rules ז:**
- **ARC1, against your recommendation: in the tool, a style may change openings and sills.** Examples are floor-to-ceiling glazing, a ribbon window, and double doors to a balcony. Each change is recorded in the house plan for that style and gets its own clay and transitions.
- **ARC2: no.** The tool's light stays the same in every style. Time of day exists only in the story frames.
- **TS1: the warm-modern living-room tool pilot, now.** The approved estimate is 8,400, up to 10,000. With ARC1 the cost rises, so anything over 10,000 needs a new owner approval.
- **EDR1: rug passes** in Nordic A and warm modern. render-agent does them; not your task.

**The stages in `CLAUDE.md` still hold for a new style.**
- Approval 1 is the Design Bible.
- Approval 2 is the products: 3 per slot, with a scene brief.
- Only after both comes any paid render.
- The warm-modern Bible today is a draft (`docs/design-bible/warm-modern-brief-draft.md` 0.2, "requires owner approval").

So this brief prepares approvals 1 and 2 for the warm-modern living room together, so that the owner can answer both in one sitting.

## Task 1: the warm-modern Design Bible 1.0, living room first (`docs/design-bible/warm-modern.md`, a new file)
- **Build on:** the draft; your story concept §3.2 in the creative review; Bible 1.9's structure, with its "story" and "tool" chapters; and the editorial frames `warm-modern-A-ed4.png` (QA: "almost").
- **The tool chapter covers:**
  - **architecture per ARC1:** the living room's openings as they should be in warm modern. Window shape and size, steel-framed glazing or not, sill height, reveals, ceiling height and finish, floor, walls, built-in details.
  - **cameras:** keep M0 1.2's camera position unless an opening change truly needs another. If so, say so and why.
  - **light:** the tool's fixed light (ARC2).
  - **palette and materials;** the forbidden list.
- **The story chapter:** the story frame, camera, light and density rules for warm modern, following Bible 1.9's story chapter.
- **The house plan:** add a dated warm-modern living-room section to `docs/house-plan.md` and `.json` (version 1.3.1). Give the changed openings and sills as numbers, in the same axes as the plan. Then list what in `data/slots/living-room.json` is affected: for example, the sill slot when the sill changes. **Do not edit the slots file.** Write a proposal for it, `docs/proposals/warm-modern-living-room-slots-2026-11-07.md`.

## Task 2: products for the warm-modern living room (approval 2 material)
- For every slot in frame at the tool's living-room camera, rank the candidates from `data/products/`, warm-modern score ≥ 7. Pick 3 per slot: a default and two variants. Give the card id, score, price per the card, and one line why.
- Where the catalog has fewer than 3, say so. Name the slots that need sourcing. Sourcing is blocked without keys (blocker B22).
- The fixed furniture: sofa, table, armchair. Keep the Nordic ones, or name warm-modern ones from the catalog. Say which, and why.
- **A scene brief:** `briefs/scene-warm-modern-living-room-2026-11-07.md`, the same shape as the Nordic scene brief (find it in `briefs/` or `docs/`).

## Task 3: the pilot plan with the real cost
In your proposal file, turn the TS1 estimate into a step plan with the ARC1 changes. For each step give the agent, the model and the tokens:
1. clay with the new openings (render-agent, 0 tokens);
2. a shell render with the shell-lock check (seedream-5-pro, per M0S1);
3. the fixed furniture composite and its shadow;
4. one slot with 3 variants as layers;
5. two poses;
6. two transition videos (motion-agent).

Show the total against the 10,000 cap. If the total goes over 10,000, say which step to cut or defer to stay within it, and give the full-cost alternative as an owner question.

## Fixed rules
- New files, plus the house-plan 1.3.1 section.
- No renders, no var2, no commits.
- Don't touch studio rules or `CLAUDE.md`.

Return a short Hebrew summary:
- the Bible's 3–5 key lines;
- the opening changes as numbers;
- the slot table (default plus two per slot, and the gaps);
- the fixed furniture;
- the pilot plan with its total;
- owner questions, each with a recommendation.
