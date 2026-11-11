# Brief: S17, fixes from QA S15–S16 (frontend-dev, 2026-11-11)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same working rules. S16 is done (`43cee016`). The source is `qa/reports/2026-11-11-site-track-qa-s15-s16.md` plus `.json`, with its tools, data and overlays. Both S15 and S16 pass.

## Recommended before the public flag
- **ת45: `check:rights` must work by content, not by path.**
  - **Hash:** the hash of every file derived from a supplier image (shop and story, every width), and of every source in the cache.
  - **Pixels:** a pixel check (dHash 16×16, Hamming ≤ 24) on every image and every data: URI in the public `dist`.
  - **Hosts:** fail on any URL to a supplier image host taken from the cards.
  - **`make-story`:** applies the rights rule before the story ever goes public.
  - **Prove it:** with QA's mutations R2–R4 and R6. Its tool is `qa/reports/2026-11-11-site-track-qa-s15-s16/tools/rights-scan.mjs`.
- **QA note ה5, the magazine holders in the public build:** with no image, hide the "בתמונה: עיתונים במחזיק. לא כלול במוצר." note. Also hide any "חומרים: …, לא צוין" field. A rule for every product: don't show a field whose value is unknown.

## Before real suppliers
- **ת46:**
  - When the order is known: strip its customer values from every log message, in Latin and Hebrew, case-insensitive, with phones by digits only.
  - Otherwise, in production: log the error name and code only.
  - Extend `PHONE_RE` to 972 and 00972.
  - `errorCode` takes `code` only from our own classes.
- **ת48:** in `processSupplierJob`, when `reach = 'maybe'`:
  - ask first (`findOrder`): if found, mark submitted; if not, send;
  - for a provider that can't be asked: resend only if the adapter documents dedup by our order number; otherwise leave it to a person.

## Small
- **ת47:** `submitting` past the lease counts as a failure for `/healthz`.
- **ת49:** use `npx --no-install tsx` (or a local path) with a fixed `build.cwd`. In the runbook: never set a provider via `--var` or a secret.
- **QA note ה1:** correct the 30-minute explanation in the S16 README (the sixth delivery is skipped).
- **QA note ה3:** a negation test, so "non-textured" or "no texture" is never read as "הדפס במרקם".

## The delay copy (master-designer, `docs/proposals/wm-phase2-r5-eye-2026-11-11.md` §7)
- **No fifth status.** The order stays on "בהכנה" in the progress line, with one line under it: "ההכנה נמשכת יותר מהרגיל. אנחנו כבר מטפלים בזה, ואין צורך לעשות דבר."
- **The short version:** "עדיין בהכנה".
- **The third sentence** ("אם מועד המסירה ישתנה, נעדכן אותך במייל.") goes in **only** if an email is really sent. Today none is, so leave it out and note it.

## Acceptance
- All the checks pass.
- New tests for ת45 (with the mutations), ת46, ת47 and ת48, and the negation test.
- The evidence goes in `qa/reports/2026-11-07-site-track/s17/`.

## Fixed rules
- No commits, no var2, no keys.
- **No network beyond npm,** and never `npx` without `--no-install`.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
