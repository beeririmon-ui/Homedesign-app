# Brief: S15, copy, SEO per house, and public honesty (frontend-dev, 2026-11-11)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same working rules. S14 is done (`a8104956`). QA on S13–S14 is running in parallel on that commit; its findings come into the next sprint.

## The tasks
1. **Apply master-designer's copy:** `docs/proposals/your-room-copy-2026-11-11.md` §1–§4, in full.
   - "החדר שלך" on the order page.
   - The caption describes only the picture, and the list opens with "בהזמנה, ולא בהדמיה:".
   - `max-width: 26rem` on the caption and the list.
   - **The logic change:** "עם מה שהזמנתם, בגוונים שבחרתם" appears only when the list is empty.
   - **The set panel:**
     - the set names: "סט קאמל ופקאן", "סט לבן חם ותה חלב", "סט קפה כהה וחימר";
     - "כריות ושמיכה" as a display override only;
     - "3 סטים";
     - the "אינו זמין כעת" note, and the partial button.
   - **Display overrides** for "(סט)" and "וריאציות" in the Nordic house too. `data/slots` doesn't change.
   - `intro_he` and `alt_he` per the file. `status_he` never public.
   - **The tests:** update `your-room.spec` and `s14-catalog.test.ts` to the new texts.
2. **The Morandi description:** use `description_he` from `data/catalog/names-he.json` (v1.2, a new top-level map). It wins over the composed description.
3. **SEO per house:**
   - **The titles and meta descriptions:** per §4.
   - **The bug:** the canonical of `?style=warm-modern` points to the Nordic page, and the ItemList lists Nordic products.
   - **The fix:** each house gets its own canonical and its own ItemList.
   - **If a separate URL per house is needed for a clean canonical:** take your default (S11 question 4 raised the same thing) and list it.
4. **Public honesty (designer §5):**
   - **`hebrew.ts`:** stop claiming "הדפס במרקם" for every print. Only say it when the card says it.
   - **The meta description of a product page:** cut it at a word boundary, never mid-word.
   - **Images with `usage_rights: unclear`:**
     - **The rule:** in the `HD_PUBLIC=1` build, no supplier image with unclear rights is shipped. This is an owner launch item, "supplier image rights".
     - **The fix:** a build check that fails if one would ship, and a neutral placeholder in its place.
     - **Behind the flag:** nothing changes.
     - **Report:** how many products this affects.

## Acceptance
- All the checks pass, with the new or updated tests.
- The evidence goes in `qa/reports/2026-11-07-site-track/s15/`.
- In the README, list how many public products lose their image under the rights rule.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
