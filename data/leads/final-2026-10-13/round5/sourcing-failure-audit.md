# ביקורת כשלי הליקוט (2026-10-17)

לפי `BRIEF-sourcing-failure-audit.md`.
- **מצב הנתונים:** כל המספרים נמדדו אחרי סבב 5c (commit e05f0127, כיסוי 57.0%).
- **מה נעשה:** ניתוח בלבד. לא נכתבו כרטיסים, ולא נערכו תוצאות, עמדות, מסמכים מחייבים או סקריפטים.
- **חיפושים:** ב-CJ רצו 30 חיפושים (run-id `audit`, ‏1,500 נקודות, 30 קריאות). המטמון נבדק בחינם.
- **קבצים נלווים:** הפירוט המלא, עם מזהים, ב-`sourcing-failure-audit.json`. התיקון המוצע לספירה: `coverage-fix.patch`.

## 1. השורה התחתונה
- **המצב:** ‏438 מתוך 769 עמדות-סגנון מכוסות (57.0%). כדי להגיע ל-80% בכל סגנון חסרות **180**: נורדי 18, מודרני חם 21, ג'פנדי 29, ים-תיכוני 30, כפרי 42, בוהו 40.
- **הספירה לא מפספסת כיסוי. היא מנפחת אותו מעט.** אחרי תיקון הבאגים: ‏429 (55.8%). בנורדי, עם 23 עמדות on-hold שלא נספרות היום, הכיסוי הוא 54.5% ולא 64.2%.
- **הבעיה מבנית:**
  - מתוך 331 עמדות-הסגנון הפתוחות, ב-229 אין אף אפשרות.
  - ב-164 לא נמצא אף מוצר בהתאמה 7 ומעלה, אפילו לא כזה שנחסם.
  - החוקים הקטנים ומילות החיפוש מסבירים חלק קטן.
- **בלי החלטות של המשתמש, אף סגנון לא מגיע ל-80%.** גם אם מקבלים את F1, F3, F5 ו-F6 במלואם, על הספירה המתוקנת:

| סגנון | מתוקן | עם F3, F6 ו-F5 | ועוד F1 | יעד 80% | יעד בלי 8 העמדות של F2 |
| --- | --- | --- | --- | --- | --- |
| נורדי | 67 | 70 | 78 | 88 | 81 |
| מודרני חם | 81 | 84 | 91 | 106 | 100 |
| ג'פנדי | 75 | 86 | 92 | 106 | 100 |
| ים-תיכוני | 76 | 79 | 89 | 106 | 100 |
| כפרי | 65 | 77 | 79 | 106 | 100 |
| בוהו | 65 | 77 | 86 | 106 | 100 |

**כל הממצאים, לפי הרווח המשוער:**

| # | ממצא | רווח משוער (עמדות-סגנון) | סוג | מי מחליט |
| --- | --- | --- | --- | --- |
| F1 | כיסוי שקיים בבית ולא נספר: חנויות ישראליות, סטודיו שותפים, שטיחי בוטיק | **52** (מוכן רק אחרי מחיר סוחר) | חוק | המשתמש |
| F2 | 8 עמדות פתוחות בכל הסגנונות, בלי אף מוצר 7+ | **37** בשווי יעד (47 פתוחות) | עמדה | המשתמש |
| F3 | סף 7: לקבל 6.5 כאפשרות השלישית | **14** (עד 31) | סף | המשתמש |
| F4 | מילות חיפוש ועומק חיפוש | **~10** (5–15) | חיפוש | המנהל |
| F9 | הצעת 5c: פריטי רצפה כבדים מספק ישראלי | **9** (תקרה 47) | חוק | המשתמש |
| F6 | מעטפת המידות | **~8** (5–15) | חוק | המשתמש (המעצב מציע) |
| F5 | המרשם: "אין משלוח לישראל" לפי SKU אחד | **~5** (3–10) | באג | המנהל |
| F10 | הצעת 5c: להרחיב את מעטפות וילון המקלחת, מדף הספרים ומתלה היתדות | **0–1** (תקרה 9) | חוק | המשתמש |
| F7 | אין מוצר מפסיד (ה.13) ומשלוח כבד | **0** לפי החוקים (15 אם מקלים) | חוק | המשתמש |
| F8 | באגים בספירה: כפילות ליסטינג, צירי צבע, on-hold | **‎−9** (מתקן את נקודת המוצא) | באג | המנהל |

## 2. הממצאים

### F1. כיסוי שקיים בבית ולא נספר (חוק, המשתמש)
- **מה לא בסדר:** `pct_ready` סופר רק דרופשיפינג.
  - חנויות ישראליות (`il-*`) נספרות רק ב-`pct_any`.
  - סטודיו השותפים (`partners-lighting-picks-2026-10-15.json`) והשטיחים (`rugs-il-boutique`, `rugs-il-online`) לא נספרים בכלל.
- **ההוכחה:**
  - `il-*` סוגר 32 עמדות-סגנון (`pct_any` הוא 61.1%, מול 57.0% ב-`pct_ready`).
  - השותפים סוגרים 11, מהן 8 מעבר ל-il, בעיקר תלויות בים-תיכוני ובבוהו.
  - שטיחי הבוטיק סוגרים 14 ושטיחי האונליין 19. קרפטים: 0 (פוליאסטר, ג.0, 2026-10-16).
  - ביחד: **52** עמדות-סגנון. לפי סגנון: בוהו 13, ג'פנדי 11, ים-תיכוני 11, נורדי 8, מודרני חם 7, כפרי 2.
  - 23 מתוך 48 עמדות-השטיח הפתוחות נסגרות רק כך.
- **התיקון (החלטה):** אחת משתי אפשרויות.
  - המדד ל-80% הוא `pct_any`, עם סימון "דורש מחיר סוחר".
  - או פותחים עכשיו פנייה לספקי השטיחים והתאורה, למרות ז.00 (2026-10-12), שקובע שפניות מחכות לאתר עובד.

### F2. עמדות שלא שוות חיפוש (עמדה, המשתמש)
- **מה לא בסדר:** 36 עמדות פתוחות בכל הסגנונות. ב-8 מהן ההתאמה הגבוהה ביותר שנמצאה, בכל סגנון, נמוכה מ-7, אחרי 8–28 מוצרים שנבדקו לכל עמדה (פרק 4).
- **ההוכחה:**
  - 8 העמדות האלה הן 47 עמדות-סגנון פתוחות, כמעט כולן ב-0 אפשרויות.
  - עוד 21 עמדות-סגנון פתוחות הן בעמדות שנראות רק במעבר, בלי נקודת מוצר: `hall/runner-rug`, `master/rug`, `bath/ceiling-light`, `hall/ceiling-light`, `master/pendant`, `master/basket`.
- **התיקון:** המשתמש מחליט לכל אחת מ-8 העמדות:
  - להוציא אותה מהמונה;
  - להפוך אותה לרהיט קבוע (הצעת המעצב Q4, ש-R5Q4 דחה);
  - או להעביר אותה לספק ישראלי.

  הוצאה מהמונה מורידה את היעד ב-6 סגירות בכל סגנון וב-7 בנורדי, כלומר 37 בשווי יעד. בכל מקרה, לא לחפש בהן שוב בסין.

### F3. סף ההתאמה (סף, המשתמש)
- **מה לא בסדר:** בעמדות הפתוחות יש 933 התאמות של מוצר לסגנון בציון 6–6.9, ב-247 עמדות-סגנון.
- **ההוכחה:**
  - אם 6.5 נספר: 65 עמדות-סגנון נסגרות.
  - אם 6.5 נספר רק כאפשרות שלישית, כשיש כבר שתיים 7+: ‏31 נסגרות, מהן 14 עם כרטיס קיים.
  - דירוג מחדש לא יעזור. בביקורת המעצב של סבב 5 נשארו 121 ציונים, 61 ירדו ו-5 עלו. אף ציון לא עבר מתחת ל-7 ל-7 ומעלה, ו-22 ירדו מתחת ל-7.
  - ב-213 מתוך 293 עמדות-הסגנון הפתוחות בחמשת הסגנונות אין מפרט מעצב בחבילה (`designer_spec_he` ריק). הצוות ניחש את ההתאמה בלי מפרט.
- **התיקון:**
  - להתיר מוצר 6.5 כאפשרות השלישית בלבד, באישור המעצב מול תמונה.
  - הסף כתוב ב-`FIT = 7.0` (`final_round_coverage.py`) וב-`data/catalog/final/BRIEF.md`, שורה 40: "a pick needs ≥ 7".
  - למעצב: מפרט של 2 שורות ו-3 שאילתות לכל עמדה פתוחה בכל סגנון (93 עמדות).

### F4. מילות החיפוש ועומק החיפוש (חיפוש, המנהל)
הפירוט בפרק 3. הרווח קטן, כי רוב העמדות שנבדקו ב-0 אפשרויות, וכל אחת צריכה 3 בכל סגנון. סבב 5c הגיע לאותה מסקנה: כ-2,000 מודעות נסרקו, 55 נפתחו, ו-3 הפכו לכרטיסים.

### F9. הצעת 5c: פריטי רצפה כבדים מספק ישראלי (חוק, המשתמש)
- **מה מוצע:** עציצים, אגרטל רצפה, שרפרפים, פוף ומעמד מטריות.
- **ההוכחה:**
  - ב-11 העמדות האלה יש 47 עמדות-סגנון פתוחות: נורדי 6, מודרני חם 8, ג'פנדי 10, ים-תיכוני 7, כפרי 8, בוהו 8.
  - 9 מהן כבר ב-2 אפשרויות, וכל אחת נסגרת באפשרות ישראלית אחת. ב-5 מהן כבר יש מוצר ישראלי (il-decor), שנספר ב-F1.
    - `bath/floor-planter`: מודרני חם, כפרי, בוהו;
    - `living-room/planter`: מודרני חם;
    - `hall/planter`: ים-תיכוני, בוהו;
    - `corridor/gallery-stool`: כפרי, בוהו;
    - `hall/umbrella-stand`: כפרי.
  - 38 האחרות צריכות 2–3 אפשרויות בכל סגנון.
  - כל 111 המועמדים שחסומים בהפסד הם מסבב 5, אחרי תמחור לפי שווי בישראל. ב-AliExpress המשלוח לרהיט הוא $76–200 (5c).
- **ההערכה:** הכיוון נכון: ב-AliExpress העמדות האלה לא ייסגרו. הרווח הקרוב הוא 9 (מתוכם 4 מעבר ל-F1), והתקרה 47. אבל זה דורש פנייה ומחיר סוחר, וז.00 (2026-10-12) קובע שפניות מחכות לאתר עובד.
- **ההמלצה:** המשתמש מאשר פנייה לספק ישראלי אחד של עציצים ושרפרפים. עד אז, פריטים כאלה מוצגים לפי PRE1/LK1.

### F6. מעטפת המידות (חוק, המשתמש; המעצב מציע)
- **מה לא בסדר:** 59 מועמדים 7+ חסומים רק במידות.
- **ההוכחה:**
  - הקלה תסגור 15 עמדות-סגנון, ועד 32 אם מקלים גם כשיש חוסם נוסף.
  - רוב החריגות מעל 10% ולא "כמה ס"מ". למשל:
    - קערה בגובה 5–5.7 מול 7–11 (`round5-ceramics`, ‏1392716043398549504);
    - מנורת שולחן בגובה 28 מול 45–55 (`round5-lighting`, ‏4001162414673).
  - 31 מועמדים 7+, ב-28 עמדות-סגנון, מחכים ל"לבדוק בפריים" או להחלטת מעטפת. למשל: "ההרחבה של הבוהו (עד 18, בליטה 25) עדיין לא אושרה" (1005009708965037, 1005012258778712).
  - **מעטפות קשיחות:**
    - `kids/rug`: ‏140×200 בדיוק;
    - `kids/bookshelf`: אורך 80;
    - `corridor/runner-rug`: ‏680–710;
    - `bath/ceiling-light`: גובה 6–10.
  - החוק: ז.00, 2026-10-17 (`docs/studio-rules.md`, שורה 207): "חריגה של עד כ-10% ... נרשמת 'גבולי, לבדוק בפריים', והמעצב מחליט".
- **התיקון:**
  1. המעצב מכריע מיד ב-31 המקרים.
  2. המעצב מציע טווח במקום ערך בודד ב-`kids/rug` וב-`kids/bookshelf`.
  3. המשתמש מאשר, כי העמדות הן מסמך מחייב.

### F5. המרשם: "אין משלוח לישראל" לפי SKU אחד (באג, המנהל)
- **מה לא בסדר:** ב-`data/sources/seen.json` יש 605 פריטים שנדחו עם הסיבה `no shipping to IL (DELIVERY_SERVICE_EXCEPTION)`, רובם מ-2026-10-11 ו-12. אבל השגיאה הזו שייכת ל-SKU, לא למוצר.
- **ההוכחה:**
  - ב-560 מהפריטים נבדק SKU אחד בלבד.
  - ב-44 מתוך 45 הפריטים שבהם נבדקו שני SKU או יותר, SKU אחר כן נשלח.
  - כל 6 הנדחים שבהם נרשמה התאמה 7–8 נשלחים בפועל ב-SKU אחר, וזה כבר במטמון:
    - 1005001597545859 ($1.99)
    - 1005008146923658 ($8.70)
    - 1005009402783790 ($20.31)
    - 1005009977558012 ($24.09)
    - 1005013006042182 ($1.99)
    - 1005008257879951 ($66.74)
  - 597 נדחו לפני שדורגו לסגנון.
  - **ליד טוב שלא הפך לכרטיס:** 4 כוסות ראטן ב-`aliexpress-work` (בוהו 7.0, מרווח 17–48%). מאז 2026-10-13 הן מסומנות "reviewed, not chosen". אחת מהן, 1005013248832816, ב-48% ובלי שום חוסם, והן סוגרות את `boho:work/desk-organizer`.
- **התיקון:**
  1. לרשום DELIVERY_SERVICE_EXCEPTION כבעיה של SKU.
  2. לבדוק SKU אחר מהמטמון (חינם).
  3. לדרג את 597 הנדחים לפני כל חיפוש חדש.
  4. לכתוב כרטיס לכוס 1005013248832816.

### F10. הצעת 5c: להרחיב את מעטפות וילון המקלחת, מדף הספרים לילדים ומתלה היתדות (חוק, המשתמש)
- **מה מוצע:** וילון 180×200 על מוט גבוה, או נפילה קצרה מ-255–265; מדף ספרים של 40–50 במקום 80; ומתלה יתדות של 40–50 במקום 60–80.
- **ההוכחה:** בשלוש העמדות פתוחות רק 9 עמדות-סגנון.
  - **וילון מקלחת** (פתוח בכפרי ובבוהו):
    - בבוהו, 1005009938333899 (8.0, נפילה מקסימלית 210) נותן אפשרות 1 מתוך 3.
    - 1005009330407914 (8.0) חסום גם ברוחב 140 ובהפסד.
    - בכפרי (יש 1) יש רק 1005005780741547, ב-6.5.
    - **סוגר 0.**
  - **מדף ספרים** (פתוח בכל 6 הסגנונות):
    - 2410141005261605400 (42 ס"מ, נורדי 7) מעלה את הנורדי ל-2.
    - 1005007471139220 (50 ס"מ, כפרי 7) מעלה את הכפרי ל-1.
    - **סוגר 0.**
  - **מתלה יתדות** (פתוח רק בבוהו, ויש 1):
    - 1565638804562784256 (8.0, ‏40–50, אבל בליטה מעל 8).
    - 1376442157082218496 (7.5, ‏40 ס"מ, לא נפתח).
    - **סוגר 1, ורק אם מוותרים גם על הבליטה.**
  - **כרית הספסל:** אין היום מועמד 7+ שחסום רק בעובי (3–5 מול 8–10 בשוק, לפי 5c).
- **ההערכה:** רווח של 0–1 היום, ותקרה של 9 אחרי חיפוש חדש בשוק הרחב יותר. וילון המקלחת יורד ממסילת התקרה עד הרצפה (nordic.md 1.6, `data/slots/bath.json`), ולכן וילון 180×200 משנה גם את הרינדור.
- **ההמלצה:** לשנות רק את מדף הספרים (זוג של 40–50 בכל קומה), כי העמדה פתוחה בכל 6 הסגנונות. בוילון ובמתלה השינוי לא שווה את השינוי במסמך המחייב.

### F7. אין מוצר מפסיד (ה.13) ומשלוח כבד (חוק, המשתמש)
- **מה לא בסדר:** 50 מועמדים 7+ חסומים רק בהפסד. הקלה הייתה סוגרת 15 עמדות-סגנון: שרפרף הגלריה, תלויות ראטן, מנורות רצפה ותקרה, עציץ רצפה.
- **ההוכחה:** כל 111 החסומים בהפסד באים מקבצי `round5*`, שתומחרו כבר לפי השווי בישראל. כלומר, ההפסד "מול מחיר העמדה הישן" כבר טופל, ומה שנשאר הוא הפסד אמיתי.
- **התיקון:**
  - להשאיר את ה.13 (`docs/studio-rules.md`, שורה 170).
  - מוצרים כאלה יכולים להופיע לפי PRE1/LK1 עם "המלאי אינו זמין כעת", ולהיספר במדד נפרד. הם לא "מוכנים".
  - המסלול האמיתי עבורם הוא F9.

### F8. באגים בספירה (באג, המנהל)
**מה לא בסדר:** הספירה מנפחת את הכיסוי.

**ההוכחה, לפי הסדר שבבריף:**
- **כרטיסים שהספירה לא רואה:** 116 כרטיסים לא מוזכרים באף קובץ תוצאות או חבילה. רק 11 מהם 7+ בעמדה פתוחה, וכולם נפסלו בכוונה בהרכב, על הפסד או מעטפת. למשל: `rug-cj-braided-wool-natural` (‎−137.9%), `pouf-cj-cotton-knit-ball-cover` (‎−63.6%). רווח: 0.
- **מפתחות עמדה:** 0 אי-התאמות מתוך 951 מפתחות ב-39 קבצי תוצאות. אין `dining/...` ואין `entrance/...`.
- **צירי וריאציה:** ב-31 כרטיסים יש צבעים בציר בשם `other` (למשל "Dark German Gray", "Large Size Palegreen"). התיקון מוסיף עמדה אחת: `modern-country:dining-room/bowl`.
- **אותו ליסטינג נספר כמה פעמים באותה עמדה:**
  - הסיבה: עותקים עם סיומת `-master` או `-work`, ותאומי מידה של אותו ליסטינג.
  - דוגמאות: `pendant-cj-silk-pumpkin-lantern` בשלושה כרטיסים; `...554205` לצד `...554205-work`.
  - התיקון מוריד **10** עמדות-סגנון מתחת ל-3, בעיקר תלויות בנורדי ובמודרני החם.
- **חבילות 2026-10-13:**
  - הן תואמות להרכבים (2026-10-11) ולקטלוגים (2026-10-12), שלא השתנו מאז.
  - אבל 23 עמדות on-hold בנורדי לא נספרות בכלל, אף ש-PR1 אושר ו-LK1/PRE1 הוחלטו.
  - 5 מהן כבר עם 3 אפשרויות.
- **בחירות על כרטיסים שנדחו:** 7 בחירות קיימות מצביעות על כרטיסים במצב `rejected`. למשל, `candle-holders-cj-ceramic-pedestal-tray` בשלוש עמדות במודרני החם. עד 4 עמדות-סגנון בסיכון.
- **ניחושים שלא עברו ביקורת:** 34 עמדות-סגנון מכוסות נשענות רק על ניחוש של הצוות. בשיעור ההורדה של סבב 5 (40 מתוך 183, ‏22%), כ-7 מהן צפויות להיפתח.

**התיקון:** להחיל את `coverage-fix.patch`, שעושה ארבעה דברים:
- כל ליסטינג נספר פעם אחת בעמדה;
- צבעים בצירי `other`, `finish` ו-`set` נספרים;
- `variants_fit: 0` נספר כ-1;
- בנורדי, שדה דיווח שכולל את עמדות ה-on-hold.

בנוסף, להעביר את 34 העמדות לביקורת מעצב.

**התוצאה בהעתק של הסקריפט:** ‏438 ל-429 (57.0% ל-55.8%):

| סגנון | לפני | אחרי |
| --- | --- | --- |
| נורדי | 64.2% | 61.5% (54.5% עם on-hold) |
| מודרני חם | 64.4% | 61.4% |
| ג'פנדי | 58.3% | 56.8% |
| ים-תיכוני | 57.6% | 57.6% |
| כפרי | 48.5% | 49.2% |
| בוהו | 50.0% | 49.2% |

### חוקים קטנים: הם לא הסיבה
- **מה סיווגתי:** כל מועמד 7+ שנחסם בעמדה פתוחה: 262 מוצרים ב-121 עמדות-סגנון, לפי הקובץ האחרון של כל מוצר.
- **"סוגר לבד":** כמה עמדות-סגנון מגיעות ל-3 אם מקלים רק בחוק הזה.

| חוק | מועמדים 7+ (כל החוסמים) | חסום רק בו | סוגר לבד | איפה |
| --- | --- | --- | --- | --- |
| CE ‏220–240V | 29 | 8 | 2* | ד.3 S2B, שורה 133 |
| IP44 | 21 | 0 | 0 | ד.5, שורה 136 |
| EN71 | 1 | 0 | 0 | ד.4, שורה 135 |
| סיבים טבעיים (שטיחים) | 2 | 0 | 0 | ג.0, 2026-10-16, שורה 98 |
| אותו מראה בכמה ליסטינגים | 17 | 4 | 1 | interior-design-rules, שורה 39 |
| סט / קו אחד | 18 | 2 | 0 | `dining-room.json`: condiment-set ו-sink-set (set_of 3) |
| תקרת כרטיסים / "כבר מלא" | 7 | 4 | 2** | BRIEF-round5-massive, שורה 120 |
| צבע אסור ב-Bible | 0 | 0 | 0 | פועל דרך הציון (פרק 4) |

\* אחת מהן אמיתית: `boho:master/pendant` (CJ ‏2507150418081621400, ‏7.5) מחכה ל-CE DoC מבקשת התקנים.

\*\* שתי הסגירות של "כבר מלא" הן מנורות קפלים מאותה משפחה, שהמעצב איחד לאפשרות אחת. בפועל: 0.

**חוקים שפועלים דרך הציון ולא דרך הדחייה:**
- **זכוכית שקופה:** אסורה בנורדי (`nordic.md`, שורה 77), בג'פנדי (55), בים-תיכוני (31) ובמודרני החם (82). ב-CJ, ‏12 מתוך 19 תוצאות "cold kettle set" (קנקן וכוס) הן זכוכית. זו אחת הסיבות ש-`master/bedside-carafe` פתוחה בכל הסגנונות.
- **"קו אחד"** במלח-פלפל-שמן ובסט הכיור: מטחנות טובות נפסלות כי אין קנקן מאותו קו (1005006395087307). יש תקדים להקלה: ג.5, "כריות: מותר לשלב מכמה ספקים".

**במרשם (5,318 דחיות):**

| סיבה | דחיות |
| --- | --- |
| התאמה נמוכה | 754 |
| "אין משלוח" (ראו F5) | 659 |
| הפסד | 420 |
| SKU או תמונה | 338 |
| פלסטיק | 235 |
| מידות | 225 |
| צבע או גימור | 201 |
| סיב סינתטי | 125 |
| CE | 43 |
| IP44 | 6 |
| EN71 | 6 |

## 3. מילות החיפוש

### מה היה לא בסדר
- **תבנית "<סגנון> <מוצר>" ב-AliExpress:**
  - 2,408 מתוך 4,514 החיפושים (53%) הם בתבנית הזו (למשל "travertine pedal bin bathroom 5l matte").
  - רק 28% מהתוצאות שלהם לא הופיעו קודם, מול 41% בשאר החיפושים. החיפוש מתעלם ממילת הסגנון ומחזיר את אותם רבי-מכר.
- **עומק:** רוב החיפושים עצרו בעמוד הראשון.
  - ב-AliExpress נקראו 3,449 עמודים ראשונים, 981 שניים ו-84 שלישיים. בעמוד 2 היו 45% מוצרים חדשים, ובעמוד 3 ‏53%, מול 30% בעמוד 1.
  - ב-CJ נקרא כמעט רק עמוד 1 (798 מתוך 799).
- **משפטים ארוכים:** שני המקורות מתאימים מילים ב-OR.
  - ב-AliExpress, חציון התוצאות הוא 3,596 בשאילתה של 1–2 מילים, ו-32,582 בשאילתה של 7 מילים ומעלה.
  - ב-CJ, רק 14% מהכותרות מכילות את כל המילים בשאילתה של 3–4 מילים, ו-5% בשאילתה של 5 מילים ומעלה. מילת סגנון או מידה מוסיפה רעש ולא מצמצמת.
- **המטמון לא נוצל:**
  - `cache_search.py` לא קורא את רשימות החיפוש של CJ (`data/sources/cj/queries`): ‏12,277 מוצרים, ו-12,155 מהם לא נפתחו ולא במרשם.
  - ב-AliExpress נפתחו 7,025 מתוך 30,473 המוצרים שהופיעו ברשימות (23%).
- **שמות סחר שחסרו:**
  - `hall/storage-boxes`: אף שאילתה עם "sundries" או "desktop storage", מתוך 56 חיפושי סלים וקופסאות ב-CJ;
  - `master/nightstand-tray`: אף שאילתה עם "storage tray" או "jewelry tray";
  - `dining-room/kitchen-runner`: שאילתת "floor mat" אחת;
  - `corridor/gallery-stool`: שאילתת "shoe changing stool" אחת;
  - `dining-room/canisters`: אף שאילתה עם "storage tank", השם של המוכרים ב-CJ.
- **מקור אחד:**
  - `work/wall-sconce` ו-`work/desk-lamp` לא חופשו ב-CJ (10 עמדות-סגנון), אבל ב-CJ רוב המנורות נכשלות ב-CE בכל מקרה.
  - 32 עמדות לא חופשו ב-Zendrop, אבל Zendrop נתן רק 9 מתוך 460 כרטיסים.
- **בלי מפרט:** ב-213 מתוך 293 עמדות-הסגנון הפתוחות בחמשת הסגנונות אין מפרט מעצב בחבילה. לכן השאילתות שם גנריות, ומילת הסגנון היא הדבר היחיד שמשתנה.

### הבדיקה: 10 עמדות, כל אחת פתוחה ב-5–6 סגנונות
- **מטמון:** 46 שאילתות של 1–3 מילים בהעתק של `cache_search` שכולל גם את רשימות CJ. נמצאו 591 מוצרים שלא נפתחו ולא במרשם, במחיר שמתחת לתקרה ועם חומר מתאים בכותרת.
- **CJ:** ‏30 שאילתות חדשות, 1,500 נקודות. חזרו 558 תוצאות, מהן 381 שלא נראו מעולם. 132 מהן מתאימות לפי הכותרת.
- **הסתייגות:** "מתאים לפי כותרת" הוא מסנן גס. זה תור לפתיחה, לא כרטיסים.

| עמדה | השאילתות שעבדו | לידים לדוגמה (CJ אלא אם צוין) | שורה תחתונה |
| --- | --- | --- | --- |
| dining-room/canisters | ceramic storage tank; tea caddy | 1456069102794838016 Nordic Ceramic Sealed Storage Tank With Lid ‏$8.64; 2412251226571625200 Ceramic Large Sealed Jar ‏$7.96; 1396294575580123136 Black Pottery Tea Caddy Matte | עובד. אבל משקל קרמיקה (2 ק"ג לסט) הוא החוסם הקודם |
| hall/storage-boxes | desktop storage basket linen; sundries basket | 1381551249844998144 Pure Color Linen Large Storage Basket ‏$2.11; 1369168178923573248 Foldable Cotton Linen Storage Basket; AE 4000162528005 Seagrass Storage Box with Lid ‏$7.06 | עובד. צריך לבדוק מידות (26–34 × 20–30 × 20–35) |
| dining-room/kitchen-runner | kitchen floor mat cotton; cotton linen floor mat | 1572427688730701824 Long Cotton Linen Floor Mat ‏$4.20; 2411140737391610900 Linen Kitchen Floor Mat ‏$3.02–31.25; 1371347474668720128 Cotton Linen Woven Tassel Floor Mat | עובד. "floor mat" הוא שם הקטגוריה אצל המוכרים |
| dining-room/tableware-set | steak plate ceramic; western food plate; ceramic tableware set household | 2409020614081628900 Japanese Coarse Pottery Plate ‏$3.18; 1502881349227786240 Stoneware Nordic Western Plate ‏$5.46 | עובד. 37 לידים |
| dining-room/sink-set | dish soap bottle ceramic | 1403252071494455296 Ceramic Hand Soap Bottle; AE 1005011569360598 Travertine Soap Dispenser + Tray | חלקי: מתקנים כן, מברשת ומגש מאותו קו לא |
| master/bedside-carafe | cold kettle ceramic (במטמון) | 1416638802935549952 Cold Kettle Ceramic Set ‏$11.38; 1421275775662952448 Japanese Ceramic Cold Kettle ‏$4.79; 1393764594727653376 (מטמון) ‏$3.51 | "cold kettle" הוא השם הנכון, אבל 12 מתוך 19 זכוכית (אסורה ב-4 סגנונות) |
| bath/bin | press type trash can | רוב התוצאות פלסטיק או חשמליות | חלש |
| living-room/pouf | footstool round; knitted footstool | קטיפה ועור מלאכותי | לא עובד |
| corridor/gallery-stool | solid wood low stool | שרפרפים נמוכים (20–30) ושרפרפי בר | לא עובד: המידה 42–46 נדירה |
| work/magazine-holder | (אין) | 0–1 חדשים | מוצה |

**המסקנה:** מילים של המוכרים מוצאות לידים חדשים ב-6 מתוך 10 העמדות. אבל ב-4 הנותרות החוסם הוא המפרט (מידה, חומר, משקל), לא המילים. שיעור ההמרה ההיסטורי מפתיחה לכרטיס הוא 4–5% (399 כרטיסים מתוך 9,545 פתיחות). לכן הרווח הצפוי מ-F4 הוא 5–15 עמדות-סגנון.

### השאילתות המתוקנות לכל עמדה פתוחה
- **AliExpress:** בלי מילת סגנון, 2–4 מילים, עמודים 1–3, `sortBy=orders`.
- **CJ:** ‏1–3 מילים, בלי מילת סגנון.
- **לפני כל קריאה:** לעבור על המטמון, כולל רשימות CJ.

הרשימה לפי עמדה נמצאת גם ב-JSON (`corrected_queries`).

| עמדה | חדרים (עמדות-סגנון פתוחות) | AliExpress | CJ |
| --- | --- | --- | --- |
| rug | living-room, work, master, kids (24) | jute rug; cotton woven rug; wool rug handmade | jute rug; cotton woven rug |
| wall-sconce | living-room, kids, work, hall, bath (19) | wall lamp swing arm; wall lamp fabric shade | wall lamp; swing arm lamp |
| floor-lamp | living-room, master (12) | floor lamp fabric shade; tripod floor lamp wood | floor lamp fabric |
| magazine-holder | work, living-room (12) | magazine rack; newspaper basket; magazine holder floor | magazine rack; newspaper basket |
| runner-rug | corridor, hall (12) | jute runner; cotton runner rug; kilim runner | jute runner; cotton floor mat long |
| pendant | work, living-room, master, kids (10) | rattan lampshade; fabric lampshade; paper lampshade | lampshade; bamboo pendant |
| planter | hall, living-room, master, work (10) | plant pot ceramic large; seagrass plant basket | flower pot large; plant basket |
| bedside-carafe | master (6) | cold kettle ceramic; ceramic water jug cup; stoneware pitcher cup | cold kettle ceramic; ceramic water jug |
| bookshelf | kids (6) | picture ledge shelf; floating book shelf kids; wall shelf 80cm | wall book shelf; picture ledge |
| ceiling-light | bath (6) | moisture proof ceiling lamp; opal ceiling light IP44 | IP44 ceiling light; moisture proof ceiling lamp |
| desk-chair | kids (6) | children chair solid wood; kids study chair | children chair wood |
| dining-rug | dining-room (6) | jute rug; cotton woven rug; wool rug handmade | jute rug; cotton woven rug |
| doll-pram | kids (6) | doll stroller wooden; doll pram | doll stroller; doll pram |
| floor-vase | dining-room (6) | floor vase ceramic; tall vase 50cm | floor vase; large vase ceramic |
| gallery-stool | corridor (6) | shoe changing stool; small stool solid wood; rush seat stool | solid wood low stool; shoe changing stool |
| kitchen-runner | dining-room (6) | kitchen floor mat cotton; long floor mat linen; cotton runner rug | cotton linen floor mat; kitchen floor mat cotton |
| picture-lights | corridor (6) | picture light; painting light; mirror headlight | mirror headlight; picture lamp |
| pouf | living-room (6) | pouf cover; footstool round; knitted pouf | footstool round; pouf |
| shower-stool | bath (6) | bath stool teak; shower bench bamboo | bath stool; shower stool wood |
| skateboard | kids (6) | skateboard blank deck; cruiser skateboard | skateboard; maple skateboard |
| step-stool | dining-room (6) | step stool wood; small stool solid wood | wooden step stool; solid wood low stool |
| storage-boxes | hall (6) | sundries basket lid; clothes storage basket; desktop storage basket | desktop storage basket linen; sundries storage basket |
| table-lamp | hall (6) | ceramic table lamp; bedside lamp ceramic | ceramic table lamp |
| towel-ladder | bath (6) | blanket ladder; towel rack ladder | towel rack floor; blanket ladder |
| bin | bath (5) | pedal bin; press type trash can; bamboo trash can lid | pedal trash can; press type trash can |
| canisters | dining-room (5) | storage tank ceramic; tea caddy; sealed jar ceramic | ceramic storage tank; tea caddy stoneware |
| condiment-set | dining-room (5) | pepper grinder wood; oil cruet ceramic; salt pepper mill set | pepper grinder; oil bottle ceramic |
| desk-lamp | work (5) | ceramic table lamp; mushroom lamp | ceramic table lamp |
| desk-organizer | kids, work (5) | pen holder ceramic; pen holder rattan; pen container wood | pen holder; pencil cup ceramic |
| shelf-boxes | work (5) | storage box lid seagrass; linen storage box; desktop storage basket | desktop storage basket; storage box linen |
| sink-set | dining-room (5) | dish soap dispenser; sponge holder; soap dispenser set tray | dish soap bottle ceramic; sponge holder |
| tableware-set | dining-room (5) | coarse pottery plate; western food plate; dinner plate set | steak plate ceramic; western food plate |
| utensil-crock | dining-room (5) | utensil holder ceramic; chopsticks holder | utensil holder; chopsticks holder |
| floor-planter | bath (4) | seagrass plant basket; belly basket | seagrass plant basket; plant basket woven |
| ledge-planter | bath (4) | succulent pot ceramic; small flower pot | small flower pot; succulent pot |
| roman-blind | kids (4) | roman blind linen; roman shade custom | roman blind |
| bowl | dining-room (3) | coarse pottery bowl; fruit bowl stoneware; rattan fruit bowl | fruit bowl ceramic; coarse pottery bowl |
| candle-holders | living-room (3) | candlestick ceramic; pillar candle holder; candle plate | candlestick; pillar candle holder |
| desk-tray | work (3) | wooden tray; acacia tray; storage tray wood | wooden tray; storage tray |
| framed-art | living-room, work (3) | canvas print abstract; art print minimalist; poster print set | canvas painting abstract; poster print |
| herb-pots | dining-room (3) | terracotta pot saucer; flower pot ceramic small | flower pot terracotta; succulent pot |
| open-shelf-ceramics | dining-room (3) | coarse pottery jug; ceramic pitcher | coarse pottery pot; ceramic jug |
| sofa-cover | living-room (3) | sofa towel; bedspread cotton; throw blanket large | sofa towel; throw blanket cotton |
| toilet-brush | bath (3) | toilet brush ceramic; toilet brush holder | toilet brush set; toilet brush ceramic |
| umbrella-stand | hall (3) | umbrella bucket; umbrella holder | umbrella stand; umbrella bucket |
| wall-decor | living-room (3) | wall hanging woven; macrame wall hanging; wall plate decor | wall hanging; macrame |
| accent-sconces | living-room (2) | travertine wall lamp; stone wall light up down; ceramic wall lamp small | travertine wall lamp; stone wall light |
| bench-cushion | hall (2) | bench cushion linen; long seat cushion; tatami cushion custom | bench cushion; long seat cushion |
| bench-pad | dining-room (2) | bench cushion linen; long seat cushion; tatami cushion custom | bench cushion; long seat cushion |
| bookends | work (2) | book stopper wood; bookend metal | bookend; book stopper |
| candle | bath (2) | ceramic candle jar; candle cup ceramic | ceramic candle cup; candle jar |
| dining-pendant | dining-room (2) | rattan lampshade; bamboo lampshade; paper lampshade | rattan lampshade; bamboo pendant |
| doll | kids (2) | waldorf doll; rag doll cotton | cloth doll; rag doll |
| nightstand-tray | master (2) | storage tray; jewelry tray wood; travertine tray | storage tray; jewelry tray |
| shower-curtain | bath (2) | fabric shower curtain long; waffle shower curtain | shower curtain linen; waffle shower curtain |
| storage-basket | bath (2) | sundries basket; storage basket rectangular | sundries storage basket; storage basket |
| toilet-paper-stand | bath (2) | toilet paper holder stand; roll holder floor | toilet paper stand; roll holder |
| toothbrush-cup | bath (2) | mouthwash cup ceramic; gargle cup | mouthwash cup; gargle cup |
| towel-ring | bath (2) | towel ring; towel holder ring | towel ring |
| waste-basket | work (2) | waste paper basket; wastebasket woven | paper basket; wastebasket rattan |
| bath-towels | bath (1) | waffle towel cotton; turkish towel | waffle bath towel; cotton bath towel |
| ceiling-lights | corridor (1) | flush ceiling lamp fabric; paper lantern ceiling | ceiling lamp fabric; lantern ceiling light |
| framed-prints | kids (1) | kids art print; nursery poster | poster print; canvas painting |
| mug-set | dining-room (1) | coarse pottery mug; stoneware mug | coarse pottery cup; stoneware mug |
| paper-towel-holder | dining-room (1) | paper towel holder wood; roll holder stand | paper towel holder; roll holder |
| reed-diffuser | bath (1) | aromatherapy bottle ceramic; fireless aroma bottle | aromatherapy bottle; reed diffuser bottle |
| shower-dispensers | bath (1) | lotion bottle ceramic; shampoo bottle set | lotion bottle ceramic; shampoo dispenser |
| soap-dispenser | bath (1) | lotion bottle ceramic; soap dispenser ceramic | lotion bottle; soap dispenser ceramic |
| soft-toy | kids (1) | plush bunny; soft toy rabbit | plush rabbit; plush toy |
| table-runner | living-room (1) | table flag; table runner linen | table flag; table runner cotton |
| tea-towel | dining-room (1) | kitchen towel linen; tea towel cotton | tea towel; kitchen towel |
| toy-cars | kids (1) | wooden car toy; alloy car model | wooden car toy |
| vanity-sconces | bath (1) | mirror headlight; IP44 wall lamp | mirror headlight; bathroom wall lamp |
| vanity-vase | bath (1) | bud vase ceramic; mini vase | mini vase ceramic |
| wall-hooks | hall (1) | wall hook wood; coat hook wooden | wall hook; coat hook wood |

## 4. כמעט-התאמות ועמדות שלא שוות חיפוש

### כמעט-התאמות (ציון 6–6.9 בעמדה פתוחה)
- **ההיקף:** 933 התאמות של מוצר לסגנון, ב-247 עמדות-סגנון. 300 מהן בציון 6.5, ב-144 עמדות-סגנון.
- **כמה היו נסגרות:**
  - אם כל ה-6–6.9 נספר: 160 עמדות-סגנון.
  - אם רק 6.5: ‏65.
  - אם רק כרטיסים קיימים בציון 6–6.9: ‏53.
- **למה הן לא הגיעו ל-7:** לפי מה שכתוב ב-`why_he` של השורות בציון 6.5 (שורה יכולה להיכנס לכמה סיבות):

  | סיבה | שורות |
  | --- | --- |
  | מידה או מעטפת | 134 |
  | גוון | 87 |
  | חומר (פוליאסטר, זכוכית, ראטן במקום עץ) | 72 |
  | מחיר או משלוח | 68 |
  | תמונה או איכות | 33 |
  | צורה או סגנון | 30 |
  | גימור | 19 |

  כלומר, שינוי קטן במפרט (מידה או גוון) יכול להכניס חלק מהן.

**14 עמדות-סגנון עם 2 אפשרויות, שנסגרות בכרטיס קיים בציון 6.5** (לבדיקת המעצב מול תמונה):

| סגנון | עמדה | הכרטיס | מה חסר ל-7 |
| --- | --- | --- | --- |
| בוהו | bath/reed-diffuser | vanity-vase-aliexpress-sand-oat-bud-vase-g-series | התאמה בין עמדות; 8.1% במחיר ₪69 |
| בוהו | bath/vanity-vase | vanity-vase-aliexpress-sand-oat-bud-vase-g-series | זיגוג חולי, מרווח 8–19% |
| בוהו | work/waste-basket | basket-cj-jute-cotton-rope-cylinder-30-work | רחב ב-4 ס"מ |
| ג'פנדי | bath/toilet-brush | toilet-brush-cj-fluted-ceramic-holder-black-handle | טרקוטה-חום, רחב ב-1 ס"מ, 6.7% |
| ג'פנדי | kids/roman-blind | roman-blind-aliexpress-modern-cotton-linen-farbic-488628 | קודי צבע בלי שם |
| ג'פנדי | work/desk-tray | nightstand-tray-cj-ebony-rounded-rect-25x18 | עובי 1.5 מול 2 |
| ים-תיכוני | dining-room/paper-towel-holder | paper-towel-holder-aliexpress-1pc-bamboo-paper-towel-316063 | במבוק; גובה 28.5 מול 30–34 |
| כפרי | bath/floor-planter | planter-zendrop-seagrass-belly-38x34 | גבולי, ‏±7% |
| כפרי | bath/ledge-planter | herb-pots-cj-fern-print-terracotta-pot-11-pair | 4.5% מתחת לגובה |
| כפרי | hall/bench-cushion | bench-cushion-aliexpress-custom-bench-cushion-chenille-743098 | מידה רק בהזמנה מיוחדת |
| כפרי | kids/pendant | pendant-aliexpress-rustic-woven-pendant-light-200914-kids | ראטן |
| כפרי | work/bookends | bookends-aliexpress-bamboo-bookends-897382 | במבוק |
| כפרי | work/desk-tray | desk-tray-cj-acacia-organic-tray-30x20 | 2 ס"מ מעבר לרוחב |
| נורדי | work/shelf-boxes | basket-cj-jute-cotton-rope-cylinder-30-work | סלים עגולים במקום קופסאות |

עוד 17 עמדות-סגנון נסגרות בליד 6.5 בלי כרטיס (רשימה ב-JSON, `third_option_at_6_5`), אבל חלק מהלידים חסומים גם במחיר או במידה.

### עמדות שלא שוות חיפוש
36 עמדות פתוחות בכל הסגנונות. בשמונה מהן אין אף מוצר 7+ בשום סגנון:

| עמדה | עמדות-סגנון פתוחות | מוצרים שנבדקו | הציון הגבוה | מה מיוחד בה |
| --- | --- | --- | --- | --- |
| kids/skateboard | 6 | 8 | 4.0 | תקן EN 13613 או EN71; דק טבעי בלי גרפיקה, 70–80×19–21 |
| corridor/runner-rug | 6 | 17 | 6.0 | 58–65 × 680–710 מסיב טבעי, לפי אורך. בסין רוב הראנרים פוליאסטר. מידה מותאמת 60×700 יש רק אצל ספק ישראלי |
| kids/desk-chair | 6 | 13 | 6.0 | רהיט: מושב 40–43, גב 70–74, בטיחות ילדים, משלוח כבד |
| kids/doll-pram | 6 | 28 | 6.0 | EN 71-1/2/3 + CE (ת"י 562); עגלת עץ 30–34×45–50×45–52 |
| bath/towel-ladder | 6 | 14 | 6.5 | 130–135 ס"מ, נפחי. המעצב הציע רהיט קבוע (Q4) |
| dining-room/floor-vase | 6 | 18 | 6.5 | קרמיקה 50–65 ס"מ, כבד, מפסיד במשלוח בודד |
| hall/runner-rug | 6 | 13 | 6.5 | 70–80 × 250–270 מסיב טבעי. נראה רק במעבר. יש 3 ראנרים טבעיים אצל ספק ישראלי |
| work/rug | 6 | 17 | 6.5 | 160–180 × 200–220 מסיב טבעי. 5 מתוך 17 המוצרים נפסלו על סיב סינתטי. יש 3 שטיחים אצל ספק ישראלי |

**28 העמדות האחרות** פתוחות בכל הסגנונות, ובכל אחת יש לפחות מוצר 7+, כך שהן לא מתות. החוסמים בהן הם מעטפת, הפסד או תקן:
- shower-stool, picture-lights, kitchen-runner, kids/rug, kids/wall-sconce, dining-rug, kids/bookshelf, hall/planter;
- pouf, work/magazine-holder, tableware-set, bedside-carafe, hall/table-lamp, living-room/rug, master/rug, living-room/wall-sconce;
- condiment-set, gallery-stool, step-stool, hall/storage-boxes, canisters, sink-set, living-room/magazine-holder;
- bath/ceiling-light, bath/bin, master/floor-lamp, utensil-crock, living-room/floor-lamp.

המספרים לכל אחת מהן נמצאים ב-JSON (`dead_slots`).
