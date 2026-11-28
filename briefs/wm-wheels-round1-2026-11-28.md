# Brief: warm-modern wheels, round 1 (render-agent, 2026-11-28)

## The decision
- **FB28:** the owner wants a wheel for most products in the end.
- **FB29:** "אני מאשר את ההוצאות בשביל להשלים את הגלגלים כמו שצריך".
- **Approved:** round 1 of `docs/proposals/wm-wheels-plan-2026-11-28.md`, section 5.1. That's 12 wheels, expected 17,840, **cap 22,300**. The conditional +320 for the living-room art is included if its contact-sheet check passes.

## The task
**Follow the plan exactly.** The wheels and options per room are in section 3, the method in 5.4, and the order in 6: by the route, living → kitchen → bath → bedroom → work → boy. The girl's room has no wheel in round 1.

1. **Before any spend on a room, make its contact sheet** (plan section 7.1, 0 tokens).
   - Use the SKU photos from `site/.cache/supplier-images/`, or the card URLs. Keep them in your scratch folder and read them with `python3.12 -I`.
   - Supplier pixels never go into a layer or a committed file.
   - An option that fails (it isn't what the card says, it's too close to another option, or it's in landscape where portrait is needed) is dropped and listed.
2. **In the room:**
   - nano-banana-2 2K in-context edits on the hero crop, with registration and tone calibration, cut in code. This is the M0-W cushion-wheel pipeline (`tools/wheel/`).
   - RND2 is 0 outside the slot's region.
   - Lamps: the light and the wash on the wall are done in code, as in FB15/FB16.
   - Use the room's FB16 grade.
3. **Studio stills (FB20 and FB29):** the same cream seamless look, light, angle and fill as `assets/renders/wheel-studio/warm-modern/`.
   - One still per option, the default included.
   - Write each still to that folder's `manifest.json`, with the same schema.
   - **New in FB29:**
     - **no halo or feathered rim:** several FB20 stills (the lamps, the cushions) show a light rim around the object. Fix your pipeline so none does, and re-cut those existing stills in code (0 tokens) if you can;
     - the product is whole, never hidden by anything;
     - textiles are folded;
     - true to the card.
4. **Per room, write a layers manifest for the new wheels** next to the room's current one, in the format frontend-dev reads (see the M0-W `manifest-wheel*.json`). frontend-dev is adding support for several wheels in one frame in parallel.

## The gates
- your own eye on each wheel, at ×1 and ×2, against the SKU;
- RND2;
- no pasted look (`scan_edge_bleed.py` and `pasted_test.py`).

## Outputs
- the layers, the manifests and the studio stills;
- a per-room QA sheet in your scratch folder;
- one line per room in `docs/proposals/wm-wheels-plan-2026-11-28.md`, section 9, "בוצע" (create it);
- the spend in a jobs file.

## Fixed rules
- **Spend:** cap 22,300. Stop and report before going over.
- **var2:** never ask for codes. If re-auth is needed, stop and report.
- **Scope:** don't touch `data/`, `docs/` except the plan's section 9, or `site/`.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Your report, after each room:** at most 4 lines, with the spend so far, your eye check and the QA sheet path.
