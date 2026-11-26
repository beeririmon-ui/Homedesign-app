# Brief: MOCK7, the full tour in design C, with transitions (frontend-dev, 2026-11-26)

## Why
The owner (FB17, `docs/studio-rules.md`): "אני רוצה להתקדם כבר לתצוגת האתר עם המעברונים זה נגרר יותר מידי זמן".
- **Design:** C, "Projection". It's your recommendation from `docs/proposals/site-fb13-design-directions-2026-11-25.md`. The owner can switch later, so keep the `?design=` flags.
- **Transitions:** in code now, at 0 tokens. Real camera-move clips come later, after a priced plan.

## What to build (behind `HD_PUBLIC=0`)
1. **Design C as the preview's default look.** Keep `?design=0|a|b` working. Existing tests may change only where the look changes on purpose.
2. **Every room, from its latest frames:**
   - **Living room:** `assets/renders/living-room/warm-modern/phase2-2026-11-10/layers/manifest-basket.json`. That's Olia, the lfix fixes and the moved basket. **The old walnut table must never appear anywhere.** When the new M0-W hero lands, it replaces this; make that a one-line config swap.
   - **Girl:** `manifest-g1-fb15.json`.
   - **Boy, bath B1, work W0, master MB0 and MB1, kitchen D1 and D2:** their `-fb15` manifests (`manifest-fb15.json` / `layers/manifest-fb15.json`).
   - **Bath B2 and the entrance:** as in MOCK6.
   - **Update** `site/tools/tour/living-room.pin.json` for the new living-room files.
   - **Gate:** the pixel gate against each manifest's own defaults frame.
3. **Transitions between rooms, in code (2.5D):**
   - **The move:** a short camera push through depth. Depth maps where they exist (`assets/renders/**/depth*.png`, `m0w-depth.png`); otherwise a designed fallback, such as a directional push-blur with parallax on a few layers.
   - **Duration and style:** 0.8–1.4 s, and it must feel like moving through the house, not a slide dissolve. Respect `prefers-reduced-motion`.
   - **The order** follows the house route in `docs/proposals/wm-tour-route-2026-11-17.md`.
4. **The arrival:**
   - **Keep:** the existing clips from the door through the hall (`assets/video/transitions/warm-modern/`: `door-d0--d0o`, `clip1a`, `clip1b`, `turn-hd--hdx`).
   - **Don't use `clip2-hdx--m0`:** it shows the old table and the old camera. From HDx into the living room, use the code transition.
5. **The product data:** the new economics (`data/economics/products.json`, updated 2026-11-25) and the safety labels, as in MOCK6.

## Outputs
- `site/dist-artifact/` rebuilt, with `check-artifact` passing (at most 255 files). Don't publish it.
- **A walkthrough video, at most 15 MB, 1280×720:** `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/mock7/walkthrough.mp4`. It shows the door, the arrival, the living room, a product close-up with the wheel, then each room in route order with its transition.
- A short "MOCK7" section in `site/README.md`.

## Checks
- typecheck, lint, vitest, and e2e for mock7 (a new spec) plus mock6. Both builds.
- Full a11y: skip it this round (EFF2).

## Fixed rules
- 0 tokens, no var2, no commits, no keys.
- **Don't edit** `data/`, binding documents or render folders.
- **Never** `git stash`, `checkout` or `reset`. Never `npx` without `--no-install`. Don't run `playwright install`.
- **Disk:** it's tight, about 1.2 GB. Delete what you don't hand over.
- **Work economically:** short tool outputs, and don't re-read long documents.
- **Your report:** a Hebrew summary of at most 10 lines.
