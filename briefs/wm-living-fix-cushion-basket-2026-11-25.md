# Brief: living room, two defects the owner found (render-agent, 2026-11-25)

## The owner's words
The owner zoomed into the Olia frame (set B) and found two defects:
> "מאחורי הכרית יש כמו כתם שחור וגם הסל נראה מונח אקראית ומאחוריו וסביבו כמו הצללה לא נכונה..משהו נראה פה לא טוב..למה?"

His screenshots:
- `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/owner/owner-cushion-defect.jpg`
- `/tmp/claude-0/-home-user-homedesign-app/1b393486-20a3-508a-a0b0-d78a98b7d2b6/scratchpad/owner/owner-basket-defect.jpg`

The frame is `assets/renders/living-room/warm-modern/phase2-2026-11-10/default-frame-fb12s1-set-B.png`, built from `layers/manifest-fb12s1.json`.

## The two defects
1. **Behind the left caramel cushion,** where it meets the sofa back, there's a dark charcoal patch. It reads as a black stain.
2. **The jute basket by the olive tree:**
   - It looks dropped at random: it stands in front of the pot and overlaps it.
   - Around it, and behind it on the wall, there's a box of wrong shading, with a ghost of the skirting line. It reads as a pasted patch.

## The task
1. **Diagnose first.** Find which layer each defect comes from: the cushion, its shadow, the plate or the basket. Find which round made it. Say in one line why our checks (RND2, verify) didn't catch it.
2. **Fix in code first (0 tokens).**
   - **The cushion:** remove the dark patch. Use the sofa back from the plate, or the correct shadow.
   - **The basket:** the wrong background inside its mask. Cut the layer tighter, or replace the background pixels with the plate. Then re-cut its contact shadow with the frozen recipe.
   - **The basket's placement:** if it still looks random, say where it should stand (for example, beside the pot with a gap, not overlapping). Fix it in code if a shift within the floor homography does it.
3. **Pay only if code can't pass ×2:** one nano 4K edit (450) per defect. What's left of the FB12 cap is 1,550. Ask before more.
4. **Scan the whole room for the same kind of fault.**
   - **The check:** for every layer in `manifest-fb12s1.json`, compare a 6–10 px band just inside the alpha edge against the plate under it (luminance and hue). A big step is a carried background.
   - **The output:** a table of the layers that fail, worst first.
   - **Fixing:** fix the ones visible at ×1–×2. Low ones go to `status/backlog-low.md`.
   - **Keep the script.** QA will use it in every room.
5. **Rebuild** the defaults A, B and C, and the frames. Fix every set where the defect appears, not only B.

## Acceptance
- At ×1 and ×2 in A, B and C:
  - no dark patch behind the cushion;
  - no box or halo around the basket;
  - the basket stands on the floor with a believable contact shadow.
- RND2: 0 outside the changed regions. WM-G1 holds.
- `qa-sheet-living-fix.jpg`: before and after at ×2, for each defect and each set.

## Fixed rules
- **var2:** never ask for codes. If var2 asks for re-auth, stop and report.
- **Scope:** don't touch `data/`, `docs/`, `site/`, other rooms or the arrival masters.
- **Git:** never `git stash`, `checkout`, `reset` or `commit`.
- **Disk:** it's tight; delete scratch.
- **The report (EFF2):** a Hebrew summary of at most 12 lines:
  - the cause of each defect, in plain words;
  - the fix;
  - the spend;
  - the scan's results.
