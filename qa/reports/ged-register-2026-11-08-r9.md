# מרשם QA, גרסה 9: סעיף master, סבב תיקון 1

**qa-agent · 2026-11-08**

- **הקובץ:** `qa/reports/ged-register-2026-11-08-r9.json`, ‏version 9. הוא מחליף את v8.
- **הבונה:** `qa/reports/2026-11-08-ged-master-fix1/tools/build.py`. ‏bad = [].
- **מה השתנה:** רק סעיף `master`. הפריימים, התקריבים והכלי כמו ב-v8.

| master | מצב | כן / חלקית / לא |
| --- | --- | --- |
| nordic-MB-A-fix1 (חדש) | not_yet | 6 / 5 / 0 |
| warm-modern-MB-A-fix1 (חדש) | not_yet | 8 / 4 / 0 |
| nordic-MB-A | not_yet (הוחלף) | 3 / 4 / 4 |
| warm-modern-MB-A | not_yet (הוחלף) | 7 / 4 / 1 |

- **החלפות:** `master_superseded_by` מפנה את MB-A ל-fix1. השדה `superseded_by` של הפריימים לא השתנה.
- **הפירוט:** `qa/reports/2026-11-08-ged-master-fix1.md`.
- **האתר:** לא קורא את הסעיף הזה.
