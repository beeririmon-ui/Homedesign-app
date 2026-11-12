# Brief: S18, honest promises on the order page (frontend-dev, 2026-11-12)

This continues the interface track (`briefs/site-interface-track-2026-11-07.md`), with the same rules. S17 is done; see `qa/reports/2026-11-07-site-track/s17/README.md`, question 3.

## The problem
- **The promise:** the order page says "אישור וחשבונית מס יישלחו לאימייל. נעדכן כשההזמנה יוצאת למשלוח." and "שלחנו לאימייל".
- **The reality:** the site sends the customer no email at all today. That's a false promise.
- **The principle:** the same as the designer's email sentence in `docs/proposals/wm-phase2-r5-eye-2026-11-11.md` §7. We never promise what we don't do.

## The task
1. **Find every email or SMS promise** in the public and customer-facing text: order, checkout, cart, terms pages, FAQ, and the accessibility statement if relevant.
2. **Replace each promise with an honest line** tied to what exists today. For example: "אישור ההזמנה ומצבה מופיעים בדף הזה. כדאי לשמור את הקישור." The tax invoice is shown or downloadable from the page once it's issued, if that exists; if not, say nothing.
   - **Design the strings behind a flag** (`EMAIL_PROVIDER`, `UNDECIDED` today), so the email lines come back automatically when an email provider is connected.
3. **Add a build check:** with `EMAIL_PROVIDER=UNDECIDED`, no public string may promise an email.
4. **List the final strings** in the README for master-designer's review. The strings are master-designer's to word, so put them in one place where they can be changed without touching code.

## Acceptance
- All the checks pass.
- A test that fails when an email promise shows with no provider.
- The evidence goes in `qa/reports/2026-11-07-site-track/s18/`.

## Fixed rules
- No commits, no var2, no keys, no network beyond npm.
- Never `npx` without `--no-install`.
- Return a short Hebrew summary.
