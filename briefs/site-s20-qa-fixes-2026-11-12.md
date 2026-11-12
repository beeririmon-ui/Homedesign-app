# Brief: S20, fixes from QA S18 (frontend-dev, 2026-11-12)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same rules. It starts after S19. The source is `qa/reports/2026-11-12-site-track-qa-s18.md` plus `.json`, with its tools and data. S18 passes with conditions.

## Before the public flag
- **ת57:** with `EMAIL_PROVIDER=UNDECIDED`:
  - `/api/waitlist` refuses with a clear status and stores nothing;
  - `/api/checkout` never records newsletter consent;
  - check both builds;
  - add API tests.
- **ת61, the contact route:** today "כתבו לנו" and the "אין גישה" line lead nowhere, because the site has no contact details.
  - **Build a single config-driven contact block**, using `CONTACT_EMAIL` and optionally `CONTACT_PHONE`, both placeholders until the owner decides (CONTACT1).
  - **Without contact details:** the block hides, and every "כתבו לנו" line becomes honest copy that offers no contact. List those strings for master-designer.
  - **Add a build check:** the public build fails if the legally required business contact is missing when `HD_PUBLIC=1`. Make it a warning behind the flag. Put the legal requirement in the runbook, as research, not legal advice.

## Before the story goes public
- **ת56:** the story sheet still promises "בדף המוצר אפשר לבקש עדכון כשהוא חוזר" on 4 items. Gate it by `EMAIL_PROVIDER` like the rest, and widen the gate and the e2e to cover story data.

## Before master-designer edits the copy file
- **ת58:** widen the definition of a promise, using QA's 48 lines and 16 forms, including "נשלח אליכם", "בתיבת הדואר", SMS/וואטסאפ without a verb, a curly-apostrophe "We’ll", "notified", "תקבלו חשבונית מס." and "המייל… בדרך".
- **ת59:** the false positives: honest lines like "שנשלחת אלינו באימייל" and "נעדכן את המדיניות" must pass. Remove "עדכנו אותנו" from the list.
- **ת60:** the scanner's blind spots:
  - text split across spans, JSX or templates (scan rendered text, not just source);
  - `value` and `aria-roledescription`;
  - non-ld JSON, including story data;
  - CSS;
  - JS outside `assets/`;
  - skipped chunks;
  - `shared/src` strings served by the Worker.

## With EMAIL1
- **ת62:** split the single switch into capabilities: `order_confirmation`, `shipping_update`, `delay_notice` and `invoice_email`. Each line returns only when its capability is real.

## Acceptance
- All the checks pass.
- New tests for ת56–ת60 and ת62.
- QA's mutations from S18 are caught.
- The evidence goes in `qa/reports/2026-11-07-site-track/s20/`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- Never `npx` without `--no-install`.
- Return a short Hebrew summary.
