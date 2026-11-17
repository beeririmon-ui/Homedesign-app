# Brief: clip 1a, strip repair round 3 (motion-agent, 2026-11-17)

## Why
QA round 2 (`qa/reports/2026-11-17-clip1a/README.md`, section "סבב 2"): M1, M2 and M3 are closed. One new medium finding, C1A-M4. Between bank 142 and 143 the bench under the living-room window, and the bottom of the window, change look all at once: a grey box with a dark shadow line at its base in 142, and cream with no shadow in 143 (HT). That's 5.39 L* mean after motion alignment, against 0.58–0.76 in the neighbouring steps, in x 1826–1914, y 621–801. It stands out because the camera has almost stopped (C1A-L3). The manager saw it at ×1 (`r2-m4-bench-pop-f141-143-x1.jpg`). QA's likely cause: HT doesn't supply the bench there, perhaps because of the armchair box exclusion, so it comes from base.png until the end lock.

## The work (0 tokens, no var2)
1. **C1A-M4:** make the bench and the bottom of the window match HT through the whole repaired range. Take everything that HT sees, and that frame 143 shows, from HT, the same way the left pane is taken in M3. If HT truly can't supply part of it, cross-fade that part to HT over about 10 frames, never in one step.
2. **C1A-L4, with it:** the bright band at the right edge in bank 122 (x 1892–1919, full height, L* 68.8 against 41.5 and 48.9 in the frames on either side), and the +8.8 L* tone step at the handover from the model's jamb.
3. **The self-check, on the frames:** the step-to-step change in the bench region (x 1826–1914, y 621–801) across 128–143, after motion alignment. No step may stand out against its neighbours (target under about 1.5 L*). Check the M1–M3 numbers didn't move.
4. The walk test and the end lock, as before.
5. **Outputs:** the repaired `bank-preview.1920.30fps.mp4`, a look image for 138–143 at ×1 and ×3 (bench region), and `repair.json`, `selfcheck.strip.json` and the README updated (re-check range: bank 128–143 and the join into 1b). Re-cut the animatic's 1a frames, keeping the same file names.

## Fixed rules
- 0 tokens. No var2. No commits, no keys. Don't edit a binding document, `data/`, or another agent's document (QA's report and the backlog are QA's).
- Working files go in the scratchpad. Delete the bank when done.
- Return a short Hebrew summary: M4 and L4 with numbers, the walk test and end lock, and whether the animatic was re-cut.
