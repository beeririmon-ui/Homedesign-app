# Brief: a new place for the jute basket in the warm-modern living room (master-designer, 2026-11-25)

## Why
The owner says the basket by the olive tree "נראה מונח אקראית".

Today it stands in front of the olive pot and overlaps it. render-agent checked every floor point between the pot, the sofa arm and the rug corner: none gives a believable gap (`assets/renders/living-room/warm-modern/phase2-2026-11-10/README.md`, the lfix section).

## The task
1. **Choose where the basket goes in M0, or decide it leaves the default.**
   - **Where to look:** the current frame is `default-frame-lfix-set-B.png` in that folder.
   - **What to keep:** the room's balance (`interior-design-rules` skill), and the Bible's rules.
   - **Options:**
     - another floor spot, for example by the floor lamp, beside the armchair, or under the window bench;
     - holding throws or magazines;
     - moving it to another room.
   - **The count:** the room count must not drop. If it leaves the living room, say where it goes.
2. **For the render,** give render-agent:
   - the exact floor position (x, y in metres in the room's floor frame, as in the slots and the Olia fit), plus the angle;
   - whether it holds something;
   - what it must not touch;
   - the reason in one line.
3. **Change nothing else in the room.**

## Output
- A short section, **"lfix, מקום הסל"**, at the end of `docs/proposals/wm-fb12-2026-11-25.md`.
- A Hebrew summary of at most 6 lines.

## Fixed rules
- 0 tokens. Proposal only. No binding documents.
