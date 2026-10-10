# צנרת סורסינג "פעם אחת"

המטרה: אף פריט של ספק לא נבדק פעמיים, ואף קריאת API לא מתבזבזת. כל סוכן סורסינג (sourcing-agent, ובדיקות של master-designer או qa שפותחות פריט) עובד רק דרך הכלים כאן. מקור: `docs/suppliers/access-and-pipeline-2026-10.md`, חלק 2.

## הקבצים
| קובץ | מה הוא |
| --- | --- |
| `data/sources/seen.json` | המרשם: כל פריט שנבדק. מפתח `cj:<pid>` או `aliexpress:<id>`. נשמר בריפו |
| `data/sources/<source>/<id>.json` | מטמון התשובות הגולמיות, עם `fetched_at` לכל חלק (product, freight) |
| `data/sources/<source>/queries/` | מטמון תוצאות חיפוש (7 ימים) |
| `~/.cache/sourcing/budget-<date>.json` | מונה התקציב היומי המשותף. **לא בריפו** |
| `registry.py` | בדיקה והוספה במרשם |
| `budget.py` | התקציב: מצב, בדיקה, ורישום שימוש חיצוני |
| `cache.py` | המטמון |
| `gaps.py` | תור העדיפויות: אילו עמדות חסרות מועמדים |
| `cj_source.py` | הייבואן של CJ: עוטף את `scripts/cj.py` עם המרשם, התקציב והמטמון |
| `aliexpress_source.py` | כיסוי דק ל-`scripts/ae/ds.py` (הלקוח האמיתי, 2026-10-10): search / image / product / freight / card / check / mark. בלי AE_DS_APP_KEY ו-AE_DS_APP_SECRET מדפיס "not configured" |
| `google_vision_source.py` | שלד. רק בודק אם משתנה הסביבה קיים ומדפיס "not configured" |
| `build_seen.py` | בונה מחדש את המרשם מהכרטיסים ומקובצי `data/leads/**`. בטוח להרצה חוזרת: ממזג ולא מוחק |

## החוק
1. **לפני שפותחים פריט, בודקים במרשם.** `cj_source.py product` עושה את זה לבד, ומדלג על כל מה שכבר נראה. אל תקראו ל-`scripts/cj.py` ישירות.
2. **אחרי שמחליטים, רושמים.** פריט שנפתח נרשם אוטומטית כ-`seen`. אם נדחה: `mark --status rejected` עם סיבה קצרה וברורה. אם נכתב לו כרטיס: `mark --status card --card-id <id>`.
3. **התקציב משותף לכל הסוכנים.** עוצרים ב-80% מהמכסה היומית (40,000 מתוך 50,000 נקודות ב-CJ), ובתקרת הריצה (ברירת מחדל: 5,000 נקודות ו-150 קריאות). קוד יציאה 3 = עצירת תקציב. לא עוקפים אותה.
4. **מפתחות רק מ-env.** אף פעם לא מדפיסים, קוראים או כותבים את `~/.cache/cj/token.json`. רק `scripts/cj.py` נוגע בו.

## מצבים במרשם
| status | מה זה | מה עושים |
| --- | --- | --- |
| `card` | יש כרטיס ב-`data/products` | לא פותחים. קוראים את הכרטיס (`card_ids`) |
| `rejected` | נפתח ונדחה | לא פותחים לעולם. חריג: סיבה של מחיר או משלוח בלבד, אחרי 90 יום (`recheck_after`) |
| `seen`, `opened: true` | נפתח ולא נכתב כרטיס | לא פותחים. קוראים את הסיבה ואת המטמון |
| `seen`, `opened: false` | רק הוזכר ברשימה או בקובץ לידים | מותר לפתוח, אחרי קריאת ההערה |

`--force` פותח בכל זאת. משתמשים בו רק עם סיבה, וכותבים אותה בסיכום הסבב.

## איך עובדים בסבב
```bash
# 0. אילו עמדות הכי חסרות (מודפס לפי עדיפות)
python3 scripts/sourcing/gaps.py --top 20            # --room living-room  --json  --write

# 1. כמה תקציב נשאר היום
python3 scripts/sourcing/budget.py status
export SOURCING_RUN_ID=round9-living                 # שם לריצה, לתקרת הריצה

# 2. חיפוש. כל תוצאה מסומנת registry=skip/warn/open; --hide-seen מסתיר את מה שכבר נבדק
python3 scripts/sourcing/cj_source.py --hide-seen list "linen" --category <id>
python3 scripts/sourcing/cj_source.py search "travertine sconce"

# 3. קודם הרצה יבשה: מה ידולג, מה ייקרא מהמטמון, ומה יעלה נקודות
python3 scripts/sourcing/cj_source.py --dry-run product <pid1> <pid2> <pid3>
# ואז באמת (רק מה שלא נבדק נקרא מ-CJ)
python3 scripts/sourcing/cj_source.py product <pid1> <pid2> --slot living-room/rug
python3 scripts/sourcing/cj_source.py freight <vid> --to IL

# 4. רושמים את ההחלטה
python3 scripts/sourcing/cj_source.py mark <pid> --status rejected --reason "brass base, 52 cm" --slot living-room/floor-lamp
python3 scripts/sourcing/cj_source.py mark <pid> --status card --card-id <card-id> --reason "card <card-id>"

# בדיקה בלי קריאה (pid, vid או sku)
python3 scripts/sourcing/cj_source.py check 2608020808091620300 CJYD2915383
```
- שימוש ב-API שנעשה מחוץ לצנרת (למשל wrapper ישן) נרשם כדי שהתקרות יישארו נכונות: `python3 scripts/sourcing/budget.py record cj 2870 "rounds 6-8"`.
- עלויות CJ (נקודות): `search` (listV2) ‏50, ‏`product` ‏10, ‏`freight` ‏10, ‏`image` ‏1,000. העלות של `list` ושל Sourcing לא פורסמה, ולכן נספרת כ-50.
- `image` עדיין לא מחובר. `source` (בקשת Sourcing ל-CJ) מחובר מ-2026-10-10 ונשלח רק עם `--approved "<מזהה ההחלטה>"` (למשל AC1). כל בקשה נרשמת במרשם כ-`cj-sourcing:<cjSourcingId>` ובמטמון `data/sources/cj-sourcing/`; הסטטוס נבדק ב-`source-status <id> ...` (עד 100 בקריאה, 50 נקודות). **מגבלה (אומתה 2026-10-10): 5 בקשות Sourcing ביום גם ב-API** (הבקשה השישית נדחית, קוד 1600000). תור של בקשות: `source-batch data/leads/cj/sourcing-requests-<date>.json --approved "<החלטה>" --count 5` שולח את הרשומות במצב `pending` ומעדכן את הקובץ.
- מטמון טרי לא עולה כלום: מוצר 30 יום, משלוח 14 יום, חיפוש 7 ימים.
- בסיכום הסבב כותבים: כמה קריאות ונקודות (מ-`budget.py status`), וכמה פריטים דולגו בזכות המרשם.

## תור העדיפויות (`gaps.py`)
`priority = (6 − candidates) × room_weight × style_match − penalty`
- `candidates`: כרטיסים שלא נדחו לעמדה, ועוד 0.5 לכל כרטיס בתיקייה משותפת שהעמדה מפנה אליה בשדה `shared`. כרטיס עם ציון סגנון נמוך מ-6 (`--min-score`) לא נספר.
- `room_weight`: סלון 3, פינת אוכל 2, השאר 1.
- `penalty`: ‏0.25 לכל פריט שנפתח לעמדה ב-14 הימים האחרונים בלי כרטיס (עד 3).

## מקור חדש
מקור חדש (AliExpress, Vision) מקבל אותו CLI ואותו שימוש במרשם, בתקציב ובמטמון כמו `cj_source.py`. המפתחות נכנסים רק בהגדרות הסביבה של Claude, אף פעם לא בצ'אט. עד אז השלד מדפיס "not configured" ולא שואל על מפתחות.
