# Brief: FB16, the house light pass: every room at the same hour as the new living room (render-agent, 2026-11-26)

## The decision
The owner approved it (FB16-B, `docs/studio-rules.md`): expected 800, cap 2,000. The spec is `docs/proposals/wm-fb16-house-light-2026-11-26.md`. Follow its per-frame table and its method exactly.

## The task
1. **The two outside plates** named in the spec: the afternoon view through the west and east windows, consistent with M0-W. No products in them.
2. **In code, for every frame in the table except M0-W** (D0 stays as it is):
   - Replace the outside.
   - Add the window glow and the lamp glow.
   - Apply one grade for the house.
   - Start from each room's latest frame: the `-fb15` manifests where they exist, otherwise the current one.
   - Work as layers over the whole stack, so every wheel variant gets the same light.
   - Never redraw a product.
3. **Write new names** (suffix `-fb16`) and new manifests. Don't overwrite earlier files.
4. **Run per room:** the pasted test, RND2 outside the changed regions, and the black point per the spec.
5. **Make one sheet,** `assets/renders/house-light-fb16.jpg`: every room's frame at ×1 in one grid, plus the M0-W hero if it exists by then. It shows the house reads as one hour.

## Fixed rules
- **Spend cap 2,000.** Stop and report before going over.
- **var2:** never ask for codes. If var2 asks for re-auth, stop and report.
- **Don't touch:** `data/`, `docs/`, `site/`, the M0-W folder, or the arrival masters.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight, about 1.2 GB; delete scratch after each room.
- **Work economically:** short tool outputs, and don't re-read long documents.
- **Your report:** a Hebrew summary of at most 8 lines.
