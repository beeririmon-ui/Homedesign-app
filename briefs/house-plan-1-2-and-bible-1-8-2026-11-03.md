# Brief: house plan 1.2 (the living-room camera) and Bible 1.8 (master-designer, 2026-11-03)

The owner answered the decisions meeting today (`status/decisions-meeting-2026-11-03.md`; the answers are in `status/decisions.json` and in `docs/studio-rules.md` ב.10–12, ה.15, ו.9 and the ז log of 2026-11-03). Three of the answers change binding documents, and the owner's answer is the approval those documents need. You make the edits.

## The answers that matter here
- **V7Q1 = (b), against the recommendation:** the living-room camera M0 moves one metre closer, 24 mm, at (0.83, 4.64, 1.20), as you proposed in `docs/render-v7-review-2026-11-02.md` §9 (V7Q1). The wall lamp and the basket leave the frame. The code composite `m0-v7-r2-fix.png` is discarded.
- **V7Q2 = yes:** every other main frame stays at 24 mm and in place.
- **BIB1 = all six** (B1–B6, text in `status/decisions.json`), **FOC1 = all four** (ש1–ש4, `docs/focus-mode-spec-2026-11-02.md` §7), **ART1 = yes** (typography, `docs/site-art-direction-2026-11-02.md` §4 and §11), **ART2 = yes** (secondary button as an ink outline, control borders #8A847B, error #9A3B2E, §11), **ART3** (no dark mode at launch), **ART5** ("הבית" as the placeholder until a name is chosen).
- **V7Q5 = (b) now, plus (c):** the test rule is already written in studio rules ב.11. You propose the revised counting rule.
- **TR3 = all four, RND2 = yes, V7Q3 = yes to both:** already in studio rules ב.12; nothing for you to edit, but keep the Bible consistent with them where it speaks (snow, the master-bath opening, the floor lamp, the triptych).

## Task A: house plan 1.2
Edit `docs/house-plan.json` and `docs/house-plan.md` to version 1.2, changelog entry "1.2 (2026-11-03): user decision V7Q1 (b), living-room camera one metre closer".
1. **Camera M0:** location (0.83, 4.64, 1.20), lens 24, yaw as today (25° left) unless you justify a change in the changelog; recompute u0/v0 and the frame checks. State, with the projection constants of the plan (`u = u0 + 0.6667 x/d`, `v = v0 + 1.1852 (Hc−Z)/d`), where the sofa, coffee table, armchair, rug, pendant, window and the dining opening now land in the frame, and what leaves it (the wall lamp, the basket, anything else).
2. **The poses at M0:** M0p (yaw 0, end of P0) and M0x (yaw −35, end of P1) move with the camera. Check that the pans P0 and P1 still cover what they must (the dining opening in M0x) from the new position; adjust the yaws only if needed, and say so.
3. **The transitions:** T-E0 (the dolly from H0 through O-entry-living now ends at the new M0: new length, the same heading rule), T-LD (starts at the new M0), and any other segment that names M0. Keep the play-time rules of the plan.
4. **The hall door view:** what H0 sees through the living-room door must agree with the new M0 frame (the H0 door view is rendered from the final M0). Note what changes.
5. **Focus-mode close-ups** (vase 50 mm, cushions 35 mm per `docs/focus-mode-spec-2026-11-02.md`): if the plan holds their camera positions, update them to the new M0; if it doesn't, say where they live.
6. **Slots:** list the slot changes `data/slots/living-room.json` will need (visibility, the wall lamp and basket as transition-only or hidden, anything that moves). **Don't edit the slots file**; the list goes in your summary and in the plan's changelog as "pending".
7. Everything else in the plan stays unchanged (V7Q2). Record "approved, unchanged" cameras as they are.

## Task B: Bible 1.8
Edit `docs/design-bible/nordic.md` to version 1.8 with a changelog entry per decision (date and decision id):
- **BIB1 B1–B6** in the light and grading chapters, with the exact texts you proposed (the recipe and verdict documents of 2026-10-24 hold them). B1: a separate brightness target of L 80–88 for the window wall; the lit wall next to the window keeps its target. State both numbers explicitly: render-agent grades the test page to them today (V7Q4).
- **FOC1 ש1–ש4** in the grading-and-motion chapter (uniform room softness ~0.5% of the width, the view up to 1.2%; dim and lift as display-only; the cushions close-up at 35 mm, height 1.10; the return on the landing curve).
- **ART1** in "טיפוגרפיה וממשק": the final section per the art direction §4 (families unchanged, the full scale for desktop and phone, body weight 400, the product credit line, captions, numerals and prices "₪ 1,290" with tabular figures, line lengths, inputs from 16).
- **ART2** interface colours; **ART3** (no dark mode at launch) where the Bible mentions themes; **ART5** the brand placeholder "הבית" only if the Bible names the brand.
- The camera section: M0 is the one exception to "24 mm from the plan's position": still 24 mm, one metre closer (house plan 1.2).
- If a Bible sentence now contradicts TR3 (snow in windows, the floor lamp in M0) or RND2, fix the sentence and log it.

## Task C: the revised density-count rule (V7Q5 c)
Write `docs/proposals/density-count-rule-2026-11-03.md`: a proposal for the owner (not a Bible edit). Start from what the eye sees in v7 (QA's count in `qa/reports/2026-11-02-v7-g1.md` §7): for example a surface group counted as one item, a distance-scaled size threshold, or minimums per frame type. Give the numbers for every v7 frame under your rule next to the current rule, and a recommendation. End with the question text for `status/decisions.json` (id V7Q6).

## Fixed rules
- Edit only `docs/house-plan.json`, `docs/house-plan.md` and `docs/design-bible/nordic.md`, each with a changelog line. New files only otherwise. No slots, no prompts, no renders, no commits.
- Don't change anything the owner didn't approve. Anything beyond the answers above is a question in your summary.
- Return a short summary in Hebrew: the new M0 numbers and what leaves the frame, the list of plan changes, the Bible changes by section, the pending slot changes, and any question.
