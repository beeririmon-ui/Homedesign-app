# Brief: the ledge planter in B1, warm-modern bath (render-agent, 2026-11-25)

## Why
FB11 asks for 20 products per room. The bath is at 18. Its plan (`docs/proposals/wm-house-20-2026-11-19.md`, 2.4, 2.6 row 5, line 10 in 7.3) adds a ledge planter in B1 "when found". The AE photo check passed card 228781 on the right SKU:
- `…577`, "large brown round";
- 13.2 × 11.8 cm;
- mottled matte stoneware in taupe-sand, L\* 59, C\* 13.5, h 71;
- `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/picks/ae-round-photo-check.json`, item 24.

This is one product added to a frame the owner already approved (AP3-HOUSE2). var2 is connected again.

## The task
- **The frame:** B1, in `assets/renders/bath/warm-modern/b1-2026-11-19/`. Read its README, `jobs.json`, `b1-checks.json` and `tools/`.
- **What:** one crop edit (nano-banana-2 2K, 400) adding the planter at `ledge-planter`:
  - **Where:** (4.27, 10.06), Z +0.05, as the third item on the toilet shelf, after the candle and the diffuser.
  - **Size:** ⌀ 13.2 × H 11.8 cm, from the SKU, which is inside the spec of ⌀ 11–14 × H 11–14.
  - **Colour and material:** match the SKU photo (`picks/img/ec6f0117_S9e694dfe6c4a41c2ae70ea37ed682668a.jpg`), matte, with no glaze shine.
  - **The plant:** a small, low succulent or trailing green filler inside the pot. Green comes only from plants. The plant isn't sold and isn't counted.
- **References:** you may upload the SKU photo to var2 as a reference, as with the kids' cars. **Never paste supplier pixels into a layer.**
- **The method:** follow the house's method.
  - Use a crop edit around an enlarged placeholder; it holds place and size best.
  - Cut a layer with alpha and a contact shadow one z below.
  - Apply the WM-G1 black point.
  - RND2: 0 pixels outside the masks.
  - Rebuild `b1-defaults.png`, `b1-variant-mat-beige.png` and the frames.
- **The budget:** 400. Up to 800 if one retry is needed. Run `var2_estimate_cost` before each send, and update `jobs.json` after it.
  - If var2 asks to re-authenticate, stop and report. Never ask for a code.

## Outputs
- The new layer and shadow.
- The rebuilt defaults, variant and frames.
- An updated README, `b1-checks.json`, `jobs.json`, the bath entries in `assets/manifest.json`, and a `qa-sheet-planter.jpg` at ×2 of the shelf region.
- The new count: 19 in the room.

## Acceptance
- The planter's size within ±5% of 13.2 × 11.8 against the clay scale.
- Colour on the lit half within ΔE00 ≤ 6 of the SKU photo.
- No other pixel changes outside its mask and shadow.
- Black point within WM-G1.

## Fixed rules
- Don't touch `data/`. A separate agent is syncing the card to `…577`.
- Don't touch binding documents, other rooms, or `site/`.
- Never run `git stash`, `git checkout`, `git reset` or `commit`.
- In `assets/manifest.json`, touch only the bath entries, and re-read the file before writing.
- Disk is tight (about 1.9 GB). Keep `raw/` small, and delete scratch when done.
- Return a short Hebrew summary: what was done, the money, the measures, and the QA regions.
