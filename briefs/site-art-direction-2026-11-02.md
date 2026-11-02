# Brief: the site's art direction, in design-magazine language (master-designer, 2026-11-02)

**The owner (2026-11-02):** "נוודא שהתהליך עומד בכל הסטנדרטים , שיצא האתר הכי מדהים ומרהיב ומעוצב ובשפת מגזין עיצוב הרמה הכי גבוהה שאפשר, שהממשק והמעברים יהיו וואוו ברמות הכי גבוהות שיש"

Recorded in studio rules א.6: the א.1 bar now covers everything the customer sees, not only the renders. That includes the typography, grid, layout, interface, transitions and micro-interactions, on phone and desktop.

## The task
Write the site's art direction: one design language that makes the whole site read like a top design magazine, and makes the interface and the motion "wow". **This is a proposal for owner approval, not a binding document.** Don't edit any binding document; anything that changes the Bible or the skeleton spec goes in as a question, with the proposed text.

## Read first
- `docs/studio-rules.md`: א (the bar, א.6 is new), ו (site, interface, motion; ו.4 hotspots, ו.5 swap and focus mode, ו.6 transitions), ג.3.
- `docs/brand-brief.md` and `docs/brand-names.md`.
- `docs/skeleton-spec.md`: principles, user flow, animations, performance targets.
- `docs/design-bible/nordic.md`: "טיפוגרפיה וממשק" (a preliminary proposal, to be finalized at the site stage, which is now), "גריידינג ותנועה", the light chapter.
- `docs/focus-mode-spec-2026-11-02.md` (§3.4 minimal interface, §4 the return).
- `briefs/nordic-house-render-2026-10-24.md` §8.1 (smooth, phone-first, high-tech playback) and §9.
- `docs/transitions-plan-2026-11-02.md` and `docs/transitions-render-plan-2026-11-02.md` (the player and format questions).
- **The current site, as it looks today:** every image in `site/screens/` (the artifact flow at 1280 and 400, the product gallery in light and dark, the hotspots, the variants and the transition sheets). The styles are in `site/web/src/styles/`, and the components in `site/web/src/components/`, if you need the exact values.

## Output: `docs/site-art-direction-2026-11-02.md`, in Hebrew
1. **The bottom line**, in at most 8 points.
2. **A critique of the current screens** against א.1 and א.6:
   - What reads as a template or generic e-commerce, and what is already at magazine level.
   - The **top 10 fixes**, ranked by impact. Each fix names the screen file it comes from.
3. **The editorial language:** 5–7 principles.
   - References are described by their qualities only: pacing, white space, how image and text meet, credit lines, restraint.
   - Name a public magazine or site only as an example of a quality.
   - Never propose copying a specific existing design or brand (Bible: "העתק של עיצוב מוכר" is forbidden). The result must be our own.
4. **Typography:**
   - Finalize the Bible's preliminary section as a proposal: the families, a scale for desktop and phone, the Hebrew–Latin pairing, numerals and prices (₪ 1,290), captions and product credits, line lengths in RTL.
   - Use Google Fonts with Hebrew support only.
   - Every change against the Bible is a question, with a recommendation.
5. **Grid and layout:**
   - Desktop and phone; margins and white space.
   - How the full-bleed room frames live together with the editorial text and the interface.
   - Full RTL. The phone is the main canvas (§8.1).
6. **The interface:**
   - The header and navigation.
   - The hotspots (ו.4: a clean room at rest).
   - The variant strip in focus mode.
   - The "magazine credit" for a product (name, material, size, price).
   - The cart and checkout.
   - All states (hover, focus, press, loading, empty, error) in the same language.
   - **Accessibility is part of the design:** WCAG AA and ת"י 5568 (ו.3), with contrast, focus rings that look editorial, and keyboard and touch targets.
7. **Interface motion:**
   - Duration and easing tokens, tied to the Bible's curves, §8.1 and the focus-mode spec.
   - The micro-interactions.
   - What is forbidden, for example: bounce, the "push" zoom the current player adds, pulsing dots, overdone parallax, spinners.
   - Reduced-motion behaviour.
8. **The opening:**
   - The first seconds on the phone: from the opening frame to the hall and the first room (§8.1, "מפריים הטלפון של הפתיחה לפריים של התצוגה").
   - The brand reveal.
   - Loading that is designed, not a spinner.
9. **The shop pages in the same language:**
   - The product page as an editorial spread: the render, the supplier photo, the material story, dimensions, shipping and price.
   - The style switcher and the room "story".
   - The cart, checkout and the order page.
10. **A "wow" acceptance checklist for the interface:** 15–25 checks that qa-agent and frontend-dev can apply. Make each one measurable where possible (sizes, contrast, durations, fps); where it is a judgment call, say who judges and against what.
11. **Questions for the owner**, with a recommendation, plus the proposed text of any Bible or skeleton change.

## Acceptance
- Every rule you cite names its source (a document and section). Every number either has a source or is marked "הצעה".
- Nothing in it contradicts a binding document without being raised as a question.
- Concrete enough that frontend-dev can build a test page from it without guessing: tokens, sizes, durations.

## Fixed rules
- New file only. Don't edit any existing file. No commits.
- No renders and no var2 calls. Don't touch the render-agent's in-progress folders (`assets/renders/*/nordic/v7/`, `assets/blockout/house/framing/round4/`).
- Return a short summary in Hebrew: the bottom line, the top 3 fixes, and the questions for the owner.
