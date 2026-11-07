# מרשם QA, גרסה 7: סעיף master

**qa-agent · 2026-11-07**

- **הקובץ:** `qa/reports/ged-register-2026-11-07-r7.json`, ‏version 7. הוא מחליף את v6.
- **הבונה:** `qa/reports/2026-11-07-ged-master-mb1/tools/build.py`. הוא מאמת גם את הסעיף החדש: ‏bad = [].
- **מה השתנה:** נוסף רק סעיף `master`. הפריימים והתקריבים כמו ב-v6.

| master | מצב | כן / חלקית / לא |
| --- | --- | --- |
| nordic-MB-A | not_yet | 3 / 4 / 4 |
| warm-modern-MB-A | not_yet | 7 / 4 / 1 |

- **הפירוט:** `qa/reports/2026-11-07-ged-master-mb1.md`.
- **האתר:** לא קורא את הסעיף (`checkRegister` בודק את frames ואת closeups בלבד). אלה פריימי בדיקה, לא לאתר.
