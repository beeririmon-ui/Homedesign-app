# Brief: S22, fixes from QA S20 (frontend-dev, 2026-11-12)

This continues the interface track, `briefs/site-interface-track-2026-11-07.md`, with the same working rules. It starts **after S21** (`briefs/site-s21-qa-fixes-2026-11-12.md`). Read S21's README first: `qa/reports/2026-11-07-site-track/s21/README.md`.
- **The source:** `qa/reports/2026-11-12-site-track-qa-s20.md` plus `.json`, and the tools, data and screens in the folder of the same name. It was measured on `8828cab9`.
- **The verdict:** S20 passes. ת57 and ת61 are closed. Five new findings, all low or low-medium.
- **QA's tools are yours to reuse:** `tools/phrase-probe-s20.mts`, `tools/mut-s20.sh`, `tools/contact-gate.mjs`, `tools/caps-matrix.mts`. Run them against your build as the acceptance for each item below.

## Before the designer edits the copy file: ת67, the promise definition
QA's fresh list (not in any fixture) caught 25/40 promises, 20/24 of the direct forms, and had 3 false positives in 40 honest lines.
- **Misses to close:**
  - "מספר מעקב" as the object of sending or receiving: N15 "עם יציאת החבילה יישלח מספר מעקב", N16 "תקבלו את מספר המעקב…";
  - "מעודכנים" with "נשמור" or "נשאיר": N17;
  - "תשלח" when the subject is a message or reminder: N24;
  - two-word labels: "חשבונית במייל", "עדכונים ב-SMS", "אישור במייל", "התראות בוואטסאפ" (X13 in a manifest `short_name`, X17). The two-word exemption holds only when the second word is a field name.
- **False positives to close:**
  - a "X: Y" heading before a negation is a label, not a promise (K34 "דיוור שיווקי: האתר לא שולח דיוור.", K36, Y3);
  - negation in the English rules too (K37 "We do not have a newsletter.").
- **Keep QA's fresh list as an external check,** not in the fixture. Write your own second fresh list for the evidence, and report both numbers honestly. The B-group misses (spam, catalogue, "לדעת ראשונים", "Get updates", push, etc.) are a stretch goal: close what you can without new false positives, and list the rest.

## Before `HD_PUBLIC=1`: ת69, dummy contact values
The public build accepts dummy values that aren't RFC 2606: `example.co.il`, `shop@hd-test.co.il` with `03-1234567` (your own S20 test address and the example in the error message), `email@domain.com`, `info@yourdomain.co.il`, `test@test.co.il`.
- **The fix:**
  - a blocklist of our own test values (every address and phone in the repo's tests, fixtures and docs) and of common dummies (domain/yourdomain/test@test/example.* in any TLD, 03-1234567, 050-0000000 and similar);
  - the public build stops on any of them; behind the flag, a warning (today example.com gives no warning behind the flag);
  - **ה25:** `check-config` applies the same rule, so deploy can't pass with a sample address either.
- The real value comes only from the owner (CONTACT1). Never put a real address or phone in the repo.

## ת71, the scanner
- `rendered()` reads `.join(" ")` (and any fixed separator) and `.concat()` as joined text (X15, X16).
- Write in the gate's header that binary metadata (WebP XMP, X11) is not covered, and why: the customer never reads it.

## ת68, the needs check (cheap now, needed with EMAIL1)
- `needs:"any"` only for a line that implies no capability. Today the invoice line passes with any provider (N7).
- Widen IMPLIES: "תתאחר"/"איחור", "קבלה", "שוב במלאי"/"חוזר למלאי", "הטבות"/"הנחות" (N2, N4, N5, N6).
- Check groups and lines across all 64 capability combinations, so a group split only by pairs is caught (N8b: "עדכנו אותי כשחוזר" shown with no submit button).

## ת70, the story sheet link (with EMAIL1, before the story is public)
The sheet links to the story's item page (`/story/…/p/<id>/`), which has no waitlist form. When `back_in_stock` is real, the line "בדף המוצר אפשר לבקש עדכון" returns and points to a page with no form.
- **The fix:** link to the product page `/p/<id>/`, which has the form; or render the same waitlist group on the story item page. Take the simpler one and say which.
- **The e2e:** with a `back_in_stock` test provider, follow the link from the sheet and reach a working form.
- Don't write new copy. If a line has to change, take a default from the existing copy file and list it for master-designer.

## Small, layout: ה23
- With contact details, on a short page the contact block shows twice (in the content and in the footer). Show it once.
- On "אין גישה" at 400, the contact line sits tight against the error box. Give it the system's spacing.
- Take a default and list it for master-designer.

## Not in this sprint
- ה24 (the interim email copy for `order_confirmation` only) waits for EMAIL1 and the designer.

## Acceptance
- **All the checks:** typecheck, lint, format:check, vitest, e2e, a11y, budget, check:config, check:rights, check:promises, and the encoding gate.
- **New tests:** for ת67 (on QA's fresh list as an external file, and your own), ת68 (the 64 combinations), ת69 (each dummy value in public and behind the flag, and in check-config), ת70 (the e2e), ת71 (join and concat mutations).
- **No regression** on S18's mutations (Q0–Q35, SM1–SM6) or on the site's honest lines (0 findings in every build).
- **Evidence:** in `qa/reports/2026-11-07-site-track/s22/`, with a README, the numbers per item, and screens of ה23 at 1280 and 400.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm. Every `npx` with `--no-install`.
- No real contact details, names or phone numbers in any file.
- If your context runs low, stop where the checks are green and write a "where I stopped" section.
- Return a short Hebrew summary.
