# Brief: concept images for the three entrance directions (render-agent, 2026-11-15)

## Why
The owner rejected the door still (FB5 in `docs/studio-rules-digest.md`): "simple and boring, nothing to do with a design magazine", and then "the building itself is really simple". master-designer wrote three architectural directions: `docs/proposals/wm-entrance-magazine-2026-11-15.md` (A "חצר הזית", recommended; B "מראת המים"; C "הפנס"). **The owner chooses a direction from concept images** before anything is locked on a clay or rendered as a final still. These images are for that choice only: not for the site, not locked, not keyframes.

## What to make
Four text-to-image concept images, 16:9, each from the designer's prompt **as written** (copy it exactly; don't improve it):
1. **A, outside:** the prompt under §3.9 (the paragraph that starts "Architectural editorial photograph for a leading interior design magazine").
2. **A, inside:** the second paragraph under §3.9 ("Same house and materials, inside the entrance hall…").
3. **B, outside:** the first paragraph under §4.9.
4. **C, outside:** the first paragraph under §5.9.

(The insides of B and C wait: the owner sees them only if he leans to B or C.)

## Model and money
- **Cap for this run: 1,200 tokens** (about 300 an image). One image per prompt. If an image clearly ignores its prompt (wrong building type, people, text, a sky where the prompt forbids it), one retry for that image is allowed, and the run's hard cap is then 1,400. Nothing beyond that.
- Choose the model for magazine-grade photorealism and long-prompt adherence at 1K–2K within the cap: candidates by today's catalog are flux-2 (1K 250), nano-banana-2 (1K 300, 2K 350), gpt-image-2 (1K 400; strongest on long prompts). Use one model for all four, so the comparison is fair. `var2_estimate_cost` before each send (SPEND2).
- No image-to-image, no references to supplier images, no var2 call other than these.

## Outputs
- `assets/renders/hall/warm-modern/concepts-2026-11-15/`: the four images (`A-out`, `A-in`, `B-out`, `C-out`), one contact sheet (2×2, labelled A/B/C with the direction's name), `jobs.json` (model, parameters, tokens, task ids, the prompt file used) and a short `README.md`.
- In the README, for each image, in two or three lines: what matches the designer's description, and what the model changed or invented (so the manager can tell the owner what is concept only). Also how each reads at phone size (390×220): look at a downscaled copy.
- Working files in the scratchpad (EFF1).

## Fixed rules
- Tokens only for these images, inside the cap above.
- No commits, no keys. Don't edit a binding document, `data/`, or another agent's document.
- Return a short Hebrew summary: the model, the tokens spent, the four paths and the contact sheet's path, and one line per image on how close it is to the designer's description.
