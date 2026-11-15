# Brief: the entrance at magazine level, three directions (master-designer, 2026-11-15)

## Why
The owner rejected the door still (rule FB5 in `docs/studio-rules-digest.md`):

> "זאת הדלת הכי פשוטה ולא מעוצבת ..לא קשור למגזין עיצוב..תמונה פשוטה ומשעממת ...זה לא הכוון שלנו"

The rejected still: `assets/renders/hall/warm-modern/door-2026-11-14/d0.png`. It is faithful to your design and well made. The direction is what failed: a plain walnut leaf in a blank plaster wall, an empty court, flat overcast light, about 78% of the frame bare plaster, nothing in front, nothing alive, no glow.

**The bar** is the warm-modern magazine frame the owner already knows: `site/web/public/media/story/living-room/warm-modern/A/1280.webp`. Look at it before anything else. It has low golden sun raking across textured plaster, an olive tree's shadow on the wall, lamps glowing warm, a sculptural niche, layered depth, rich materials and a view. The other warm-modern editorial frames are in `assets/renders/editorial-phase-b-2026-11-06/` (`warm-modern-A-*`).

The walk you designed (storyboard S1: the door opens, a straight walk in, a 65° turn, the approved dolly to M0) is not in question. The owner has not commented on it. The look is what must change.

## Inputs
- `docs/studio-rules-digest.md` (FB2–FB5, DIR2, U-rules, TR1, TR2).
- The magazine frame above, and `docs/design-bible/` for warm-modern if it exists (check; otherwise the warm-modern editorial prompts in `assets/prompts/`).
- Your `docs/proposals/wm-front-door-2026-11-14.md` (including your §10), and `docs/proposals/wm-entrance-hall-architecture-2026-11-13.md`.
- `docs/house-plan.json` (`porch`, `O-front-door`, the hall).
- The door clay: `assets/blockout/house/framing/wm-door-2026-11-14/` (D0, HT, HD, HDx, the stations of clip 1).
- motion-agent's plan, for what each direction costs in motion: `docs/proposals/wm-arrival-from-door-2026-11-14.md`.
- **A second opinion runs in parallel:** astra (GPT) writes `briefs/astra/wm-entrance-magazine.md`. If it exists when you have your own draft, read it and take what is good, crediting it. Don't wait for it.
- `.claude/skills/interior-design-rules/`.

## What to write
`docs/proposals/wm-entrance-magazine-2026-11-15.md`:

1. **What made D0 boring, in five lines.** Name the causes, so the next frame doesn't repeat them.
2. **Three distinct directions for the arrival.** Each must be a magazine opening spread, not three versions of one idea. For each:
   - **The idea, in one line,** and a short name the owner will remember.
   - **The door,** as the hero: material, size, how it opens (a pivot door, for example, changes what the opening does in code; say so), the hardware.
   - **The architecture in the frame:** the wall surfaces and their textures, the court's floor, any built element (a bench in stone, a niche, a screen, a canopy, a glazed side panel showing the warm interior). If a direction needs the porch or the door to change from `docs/house-plan.json`, say exactly what changes. That is a proposal for the owner.
   - **What lives in the frame:** planting (a tree in the ground, a planting bed), light fittings, objects. Mark each as architecture, landscape, or a future product slot (sellable later). Nothing generic drawn as if for sale.
   - **The light,** and how it carries into the walk. The walk ends on the tour's living room plate (`assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/base.png`), which is lit differently from the magazine frame. Say how each direction stays believable from the door to that plate: the same light, a light that changes as you go inside (sun outside, the plate's soft light inside), or a plate re-grade (say what it would cost to redo; the manager doubts it is worth it now).
   - **The camera:** D0 as it is, or moved (say where, and what it does to the walk in S1).
   - **What the camera sees inside** in that direction: the threshold, the far wall of the hall at HD during the turn (today a blank wall with the hidden study door), the view to the living room. If the hall needs a feature to avoid a dull turn (a light slot, a niche, a material change, a window to a garden), it is architecture, and it must not contradict the walk to M0.
   - **A prompt-ready description for a concept image** (English, one paragraph, at D0's framing, 16:9) and a five-line rejection list.
   - **Cost and risk,** in a line: what in the clay changes, what stills change, what is hard for the video model.
3. **Your recommendation,** and why it is the strongest opening for a site the owner will show to furniture, rug and lighting stores.
4. **What survives** from the work so far (the clay, HT, HD, HDx descriptions, the dining glimpse) under each direction.

## Acceptance
- Three directions that a person can tell apart in a thumbnail.
- Each one would sit next to the magazine frame without looking poorer.
- Every change to a binding document is listed as a proposal for the owner. No binding document is edited.
- No question to the owner: he will choose from the concept images.

## Fixed rules
- 0 tokens. No var2, no commits, no keys.
- Return a short Hebrew summary: the three directions in two lines each (with their names), your recommendation, and the three concept prompts.
