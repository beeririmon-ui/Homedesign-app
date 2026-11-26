# Brief: FB15, fix the "pasted" look in the other warm-modern rooms (render-agent, 2026-11-26)

## The decision
The owner wants a complete warm-modern house, with every room at the level of the new living room (FB13, FB14, FB15 in `docs/studio-rules.md`). The designer's audit is `docs/proposals/wm-fb13-living-wow-2026-11-25.md`, section 4: the table and the rule "the edit is the final pixels, no refit after it".

Another render-agent is rendering the new living room right now in `assets/renders/living-room/warm-modern/fb13-2026-11-25/`. **Don't touch the living room or the entrance** (the entrance waits for the new living room).

## Inputs
- Section 4 of the proposal: per room, what reads pasted and the cheapest fix.
- The shared finish and the pasted test: `assets/renders/tools/finish/` (README), and `pasted-test-2026-11-25.tsv`.
- Each room's current defaults, manifest and `-fb13prep` frame under `assets/renders/<room>/warm-modern/`.

## The task, in this order (strongest first)
1. **Bath B1:** two crop edits at clay size, the floor group and the sill group (800).
2. **Work W0:** the floor strip with the newspaper holder (400); the stone lamp's shadow from the clay, in code; the palm, 400 only if code doesn't hold.
3. **Master MB1:** two crop edits, the floor lamp and the front group with the ficus (800); the shelf in code.
4. **Master MB0:** shelf shadows by the light direction, and the white dots, in code; one edit for the right group (400).
5. **Kitchen D1:** one crop edit of the table group (400); the shelf by the finish.
6. **Kitchen D2, boy, girl:** code only (warm balance, the halo, the finish). The girl's rope basket (400) only if budget remains at the end.
7. **Lamps:** where G1.10 fails (MB0, MB1), the lamps read as lit. Do it inside the edit that covers them, or as a screen layer in code.

## Rules for every edit
- **nano 2K (400), a crop edit in context.** The edit's pixels are final: no scaling, shifting or recolouring of a product afterwards.
- **Fidelity:** each product still matches its SKU (shape, colour, size ±5%). Use SKU references from the cards; supplier photos stay in the scratchpad.
- **RND2:** 0 outside the edited regions. Black point per WM-G1. Product counts unchanged.
- **Then** the shared finish, and the pasted test before and after, per room.
- **New names** (suffix `-fb15`), with new manifests. Don't overwrite; keep today's files for rollback.

## Outputs
- Per room: the layers, the defaults frame, the manifest, a `qa-sheet-fb15.jpg` (before and after at ×1, and ×2 of each edited region), and the README and checks.
- `assets/manifest.json` (re-read before writing; another agent is writing to it too).
- A table: room, what was done, the spend, and the pasted score before and after.

## Fixed rules
- **Spend cap: 3,400.** One retry per edit, inside the cap. If the cap won't cover the list, finish the strong rooms first (1–3), then stop and report.
- **var2:** never ask for codes. If var2 asks for re-auth, stop and report.
- **Scope:** don't touch `data/`, `docs/`, `site/`, the living room, the entrance, or the arrival masters.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's very tight, about 1.4 GB, and shared with another agent. Delete scratch after every room.
- **Your report:** a Hebrew summary of at most 12 lines: per room, what was fixed, the spend, and what still reads pasted.
