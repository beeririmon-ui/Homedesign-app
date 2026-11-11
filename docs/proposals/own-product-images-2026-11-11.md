# הצעה: תמונות מוצר משלנו במקום תמונות הספק · 2026-11-11

> **master-designer.** ההחלטה המבוקשת: IMG1 (הבעלים).
> **הקלט:**
> - **המחקר:** `docs/research/supplier-image-rights-2026-11-11.md` (מחקר, לא ייעוץ משפטי).
> - **האתר:** `qa/reports/2026-11-07-site-track/s15/README.md` ו-`data/rights-check-public.json`: ‏39 מתוך 39 המוצרים הציבוריים מאבדים את תמונת הספק, ו-5 נשארים בלי שום תמונה.
> - **השערים:** `docs/ops/quality-gate-g-ed-2026-11-07.md` (‏G-ED.2–G-ED.18) ו-`docs/ops/quality-gates-2026-11-02.md` (‏G1.1, ‏G1.2, ‏G2.11, ‏G4.16).
> - **המתכון:** `docs/render-recipe-story-v1-2026-11-07.md` (מחירים, מודלים, וכלל "הייחוס לא נשמר בריפו").
> - **הכיוון האומנותי של האתר:** `docs/site-art-direction-2026-11-02.md` §9.1 ו-§9.3 (תמונת סטודיו בגלגל, בסל וב"עוד בעמדה הזו"; שלוש קבוצות אפשרויות בדף המוצר).
> - **השלד:** `docs/skeleton-spec.md`, ‏"תמונות לגלגל הווריאציות: PNG שקוף בסגנון סטודיו, 2K".
> - **הקטלוג:** `site/.generated/catalog.public.json`, ‏`supplier-images.json`, ו-`data/selections/living-room.warm-modern.json`.
> - **הפריימים:** `assets/renders/editorial-phase-b-2026-11-06/nordic-A-ed4.png`, ‏`nordic-B-fin.png`, ‏`warm-modern-A-ed9.png` (‏2720×1530).
>
> **הצעה בלבד.** לא רונדר דבר, לא נקרא var2, לא שונו כרטיסים או מסמכים מחייבים, ואין commit. שום הוצאה לפני תשובת הבעלים.

## 0. השורה התחתונה
- **הבנייה הציבורית כבר נקייה משפטית** (S15): אף תמונת ספק לא נשלחת. מה שחסר הוא איכות ושלמות:
  - 5 דפים בלי שום תמונה;
  - בשאר 34 הדפים התמונה היחידה היא שכבת הכלי הנורדי, שהיא זמנית (`styled-preview-r2`) ובמוצרים קטנים גם ברזולוציה נמוכה.
- **ערכת התמונות, מינימלית:**
  - לכל מוצר שתי תמונות: **"בחדר"** (P1), תקריב באור הבית, ו**"סטודיו"** (P2), PNG שקוף בגוון האמיתי.
  - **"חומר"** (P3) רק לטקסטיל גדול.
  - **"גוון"** (P4) רק לגוונים שהמעצב סימן.
  - כל השאר (תמונות ממוזערות, גלגל, סל, סט, OG) נגזר בקוד ב-0 טוקנים.
- **השיטה:**
  - תמונות הספק הן חומר עזר פנימי בלבד: גזורות למוצר עצמו, בגיליון ייחוס, ותמיד כ-reference.
  - הן אף פעם לא תמונת הבסיס של עריכה. הבסיס הוא תמיד שלנו: פריים סיפור שלנו, פלטה ריקה שלנו, או תמונת ה-P2 שלנו.
  - הזוויות, האור והקיפול הם "זוויות הבית", שנקבעו כאן מראש.
  - QA מוסיף חמש בדיקות של "אין קומפוזיציה של ספק" (§6).
- **העלות** (טוקני var2):

  | | מסלול gpt (P2 ב-600) | מסלול nano (P2 ב-300) |
  | --- | --- | --- |
  | הנורדי, 39 מוצרים | 38,400 | 26,700 |
  | המודרני החם, 17 מוצרים משלו ו-6 גוונים | 15,450 | 10,350 |
  | עודף ה-A/B בפיילוט (הענף שלא נבחר) | 900 | 1,800 |
  | **סה"כ** | **54,750** | **38,850** |
  | רזרבת תיקונים (מעבר seedream ב-650 לכל ~10 תמונות; המנהל משחרר) | עד 8,450 | עד 8,450 |

  הפיילוט מכריע בין שני המסלולים.
- **הפיילוט, 3 מוצרים:**
  - שמיכת המוסלין (טקסטיל), אגרטל האבנית המקומט (קרמיקה), וזוג מנורות הטרוורטין (מנורה).
  - **3,950 טוקנים, ועוד רזרבה של עד 2,000.**
  - מכריע גם את המודל ל-P1 ול-P2, ואם מותר לייצר גוון בעריכה.
- **שאלות לבעלים:** IMG1a–IMG1f (§8).

## 1. מה כל מוצר צריך
### 1.1 איפה תמונת המוצר מופיעה
| מקום | גודל | היום, בבנייה הציבורית | בהצעה |
| --- | --- | --- | --- |
| דף המוצר, הגלריה | 4:5, עד ~640 CSS (‏1,280 פיקסלים ב-2x); בטלפון מקצה לקצה | שכבת הכלי מהחדר, או משבצת ניטרלית (5 דפים) | P1, ‏P2, ‏P3 (כשיש), ‏P4 של הגוון שנבחר |
| גלגל הווריאציות | 52×52 (§9.1) | שכבת הכלי | נגזר מ-P2 |
| שורת סל | 64×80 (§9.3) | שכבת הכלי | נגזר מ-P2 |
| "עוד בעמדה הזו" | 64 | שכבת הכלי | נגזר מ-P2 |
| שורה ב"החדר שלך" | 64×80 | משבצת ניטרלית (התמונה של הספק מוסתרת) | נגזר מ-P2 או מ-P4 |
| קרדיטים בסיפור החדר, ‏OG, ‏`Product.image` | שונה | שכבת הכלי או כלום | P1, חיתוך בקוד |

### 1.2 ערכת התמונות
| | שם | מה רואים | פורמט | מי צריך | איך |
| --- | --- | --- | --- | --- | --- |
| **P1** | **בחדר** | תקריב של המוצר בחדר, באור של הבית. זה גם תקריב שכבה 2 (פרט) של הסיפור, ולכן נספר ב-G-ED.18 | ‏4:5, ‏2K; ‏50–85 מ"מ, בגובה המוצר, עומק שדה רדוד; המוצר תופס 50–65% מהגובה, על קו שליש (‏G4.16) | כל מוצר ציבורי | עריכה של חיתוך מפריים סיפור שלנו (§2.4) |
| **P2** | **סטודיו** | המוצר לבד, בדיוק היחידות שנמכרות (זוג הוא שתיים), בלי מילוי, באור ניטרלי. הלקוח רואה בו את הגוון האמיתי | PNG שקוף, ‏4:5, ‏2K (כמו בשלד). האתר מניח אותו על הנייר ‎#F4F1EC, עם צל מגע מהאלפא | כל מוצר ציבורי. מוצר שמשותף לשני בתים: P2 אחד | §2.3 |
| **P3** | **חומר** | מאקרו של החומר: אריג, פרנזים, קליעה, סלאב | ‏1:1, ‏2K, על נייר | רק טקסטיל שהממד הארוך שלו מעל 60 ס"מ (וילון, שמיכה, כיסוי, שטיח, ראנר, מקרמה 50×70) | עריכה של חיתוך 100% מה-P2 שלנו |
| **P4** | **גוון** | אותו P2, באפשרות צבע אחרת של הספק | כמו P2 | רק גוון שהמעצב סימן ("גוונים לסגנון", קבוצה 2 ב-§9.1). בנורדי עד 1 למוצר. במודרני החם: הגוונים שבסטים | עריכה של ה-P2 שלנו, עם תמונת ה-SKU כייחוס צבע (§2.4) |

**למה P3 רק בטקסטיל גדול:**
- **ב-P2 של 2K, מוצר עד 60 ס"מ מקבל 27–50 פיקסלים לס"מ.** זה מספיק כדי לקרוא בוקלה, שניל, נקבוביות טרוורטין וקמטים באבנית, גם ב-P1.
- **שמיכה של 150×200 או שטיח של 230×330 מקבלים 5–10 פיקסלים לס"מ,** והחומר לא נקרא בכלל.

### 1.3 מה לא מייצרים (מינימום)
- **גוון מחוץ לפלטה** (קבוצה 3, "עוד אפשרויות מהספק"):
  - בלי תמונה. מופיעים דוגמית ושם.
  - בגלריה מופיעה השורה: "בתמונות: {הגוון שבחדר}. הגוון שבחרתם מוצג בדוגמית."
  - הנוסח לא מבטיח תמונה עתידית (כלל 5 של המעצב).
- **אפשרות מידה:** בלי תמונה. המידות כתובות בדף.
  - רשות: שרטוט מידות בקוד מתוך הכרטיס (0 טוקנים).
- **אפשרות שהיא עיצוב אחר** (הדפס אחר, דגם מקרמה 2, ‏21 הסגנונות האחרים ברישום של מנורת הטרוורטין המחורצת):
  - לא מוצעת עד שיש לנו תמונה שלה (שאלה IMG1c).
  - אם הבעלים רוצה, כל אחת היא P2 חדש ב-600.
- **P2 דולק למנורות:** לא. האור נראה ב-P1.
- **P2 לכל בית:** לא. יש סטודיו אחד למותג. הבית נכנס דרך הנייר ודרך P1.

## 2. השיטה: נאמנות בלי הקומפוזיציה של הספק
### 2.1 העקרונות
1. **תמונת ספק היא ייחוס פנימי לנאמנות:** צורה, צבע, פרופורציה, ספירה וחומר. היא לא מתפרסמת ולא נשמרת בריפו (מתכון §2).
2. **הבסיס תמיד שלנו.** בשום קריאה לא נכנסת תמונת ספק כ-`image_url` של עריכה, כלומר כתמונה שהקומפוזיציה שלה נשמרת. הבסיס הוא אחד מאלה:
   - **ל-P1:** חיתוך מפריים סיפור שלנו, במצב "מבחן סופי" ומעלה.
   - **ל-P2 במסלול nano:** הפלטה הריקה שלנו (§2.3).
   - **ל-P3 ול-P4:** ה-P2 המאושר שלנו.
   - **ל-P2 במסלול gpt:** אין בסיס. רק טקסט, וגיליון הייחוס כ-reference.
3. **הקומפוזיציה נקבעת לפני שמסתכלים על הספק.**
   - זוויות הבית, האור, הקיפול והמסגור כתובים כאן (§2.3), בתאריך הזה, לכל קטגוריה.
   - זה גם מה שמראה שהבחירה שלנו עצמאית.
4. **הפרומפט אוסר להעתיק מפורשות:** "Do not reproduce the camera angle, background, lighting, props, styling or arrangement of any reference image."
5. **כל תמונה ציבורית נרשמת ברשומת מקור** (§2.6). תמונה בלי רשומה לא עולה.

### 2.2 גיליון הייחוס (render-agent, ‏0 טוקנים, בתיקיית הסשן בלבד)
- **מה נכנס:** 2–4 תמונות של הכרטיס, מזוויות שונות. אחת מהן היא תמונת ה-SKU שבחדר.
  - כל אחת **גזורה למוצר בלבד**: בלי רקע, בלי חפצים, בלי ידיים, בלי אריזה, בלי טקסט.
  - כל אחת מוקטנת לאותו גובה, על אפור שטוח ‎#808080, עם רווח של 16 פיקסלים, ובלי שום כיתוב.
  - **תמונה שיש עליה סימן מים, לוגו או טקסט על המוצר עצמו לא נכנסת.** לא מסירים סימני מים (המחקר §5, המלצה 4).
  - **טבלת מידות של הספק לא נכנסת**, כי יש בה טקסט. המספרים עוברים לפרומפט.
- **דוגמית צבע:** ריבוע של 256 פיקסלים משטח מואר ושטוח של המוצר, מתמונת ה-SKU. היא משמשת לצבע בלבד, ובלי קפלים.
- **ייחוס מרקם** (ל-P3): ריבוע מאזור חד של המרקם, לקנה מידה ולמבנה בלבד.
- **ההעלאה:** דרך `var2_upload_asset`.
  - הכתובות לא נשמרות בריפו ולא משותפות.
  - ב-`jobs.json` נרשם רק אינדקס התמונה בכרטיס (`images.urls[i]` או `options.skus[j].image`).
- **מה גיליון הייחוס שובר:** אין בו קומפוזיציה אחת של ספק שאפשר "להמשיך". המודל מקבל את המוצר מכמה כיוונים, והקומפוזיציה מגיעה מהפרומפט שלנו.

### 2.3 הסטודיו של הבית (P2)
- **רקע:**
  - **במסלול gpt:** שקוף (background: transparent).
  - **במסלול nano:** "פלטה ריקה" שאנחנו מייצרים בקוד: ‏‎#F4F1EC שטוח, 1638×2048. אחריה `remove-background`.
- **אור:**
  - מקור גדול ורך משמאל למצלמה, ‏45° הצידה ו-30° למעלה. זה ההד של חלון הבית משמאל.
  - מילוי מימין, בערך 1.5 סטופ חלש יותר.
  - בלי אור גב ובלי צבע באור.
  - **איזון לבן ניטרלי, 5000K.** P2 הוא תמונת הצבע האמיתי. החום של הבית בא ב-P1.
  - מט נשאר מט.
- **מסגור:**
  - 4:5.
  - המוצר, או היחידות של הסט, ממלאים 80% מהממד המגביל, במרכז, בלי לגעת בשוליים.
  - חריג: הכבל של תלויה יוצא מלמעלה.
- **בלי חפצים, בלי מילוי ובלי טקסט.** בדיוק מה שנמכר: זוג הוא שתי יחידות, וסט הוא כל הפריטים.
- **צל:**
  - בקוד, מהאלפא: טשטוש של 2% מגובה המוצר, היסט של 1% ימינה, ‏`multiply` ב-‎#3A3A3A ב-18%.
  - לפריטים תלויים ולפריטי קיר אין צל.
- **זוויות הבית** (נקבעו כאן, ‏2026-11-11):

  | קטגוריה | עדשה | מצלמה | סידור |
  | --- | --- | --- | --- |
  | כלים וחפצים על משטח (אגרטל, עציץ, סל, מחזיק עיתונים, פוף, פמוטים) | 85 מ"מ | בגובה 55–60% מגובה החפץ, מבט מטה 8–10°, חזיתי | עומד ישר |
  | קערות | 85 מ"מ | מבט מטה 30°, כדי שהפנים ייקרא | |
  | מנורות קיר | 85 מ"מ | בגובה מרכז הגוף, מסובב 30° משמאל, כדי שהבליטה תיקרא | זוג: שתיים זו ליד זו, ברווח 10 ס"מ |
  | קישוט קיר ותמונות | 85 מ"מ | חזיתי, בגובה המרכז | תלוי ישר. שלישייה ברווחים שווים |
  | תלויות | 85 מ"מ | 10° מתחת לקו המשווה של האהיל, מבט מעט למעלה | הכבל נחתך בשוליים העליונים, בלי כיפת התקרה |
  | מנורות רצפה | 50 מ"מ | בגובה 100, חזיתי | המנורה כולה |
  | כריות | 85 מ"מ | חזיתי, ‏10° מעל | עומדות, רפויות, בלי "קיפוח". סט: זו ליד זו |
  | שמיכות וכיסויים | 50 מ"מ | מבט מטה 35°, מסובב 30° | **"קיפול הבית":** לשלוש לאורך ואז לחצי, ופינה עליונה מקופלת לאחור כדי שהפרנזים והשוליים ייראו |
  | כיסוי ספה מחויט | 50 מ"מ | שלושת-רבעים | על צללית ספה פשוטה, נמוכה ובלי פרטים. הספה לא נמכרת |
  | וילונות | 50 מ"מ | חזיתי | זוג יריעות תלויות ממוט נסתר, הנפילה כולה עד המכפלת, שלושה קפלים רכים בכל יריעה |
  | שטיחים | 50 מ"מ | מלמעלה, ‏90° | השטיח כולו, השוליים ישרים |
  | ראנרים | 50 מ"מ | מלמעלה | באלכסון על הפריים, שני הקצוות בפנים |

### 2.4 P1, ‏P3 ו-P4: עריכה של מה שכבר שלנו
- **P1:**
  - **הבסיס:** חיתוך 4:5 ברזולוציה המקורית מפריים סיפור במצב "מבחן סופי" ומעלה, סביב המקום של המוצר.
  - **מוצר שאינו בשום פריים:** סביב המקום שתוכנית הבית או ה-Bible נותנים לו. המוצר "מוחלף" או "מונח" שם בעריכה, כמו במעבר ממוקד.
  - **הפרומפט:** "re-photograph the same scene as a close-up", ‏G4.16, ושמירה על האור, השעה והחומרים של הפריים.
  - **המילוי:** כמו בחדר (ענף באגרטל, נרות, עיתונים). בדף נכתב "בתמונה: … לא כלול".
- **P3:**
  - **הבסיס:** חיתוך 1:1 ב-100% מה-P2 המאושר, מונח על נייר, באזור המספר ביותר (פינת פרנזים, שפת קליעה).
  - **הפרומפט:** מאקרו 100 מ"מ, ואור גוֹרף משמאל ב-20°. אותו צבע, אותו קיפול.
  - **הייחוס:** ריבוע המרקם, לקנה מידה בלבד.
- **P4:**
  - **בדיקה מוקדמת (המעצב ו-render-agent, ‏0 טוקנים):**
    - משווים את תמונת ה-SKU של הגוון לתמונת ה-SKU שבחדר.
    - **עריכה מותרת רק כשהבנייה זהה:** אותו אריג, אותם פרנזים, אותו עובי ואותה צורה.
    - **אם הבנייה שונה,** זה P2 חדש (600, באישור המנהל).
    - הסיבה: G2.11 מחייב, "הווריאציה היא מוצר אמיתי … לא צביעה מחדש של ברירת המחדל".
  - **הבסיס:** ה-P2 שלנו, על ‎#808080.
  - **הייחוס:** תמונת ה-SKU הגזורה ודוגמית הצבע שלו.
  - **אחרי העריכה:** מחילים מחדש את האלפא של ה-P2. הגאומטריה לא השתנתה, ו-QA בודק את זה.
  - **אין צביעה מחדש בקוד** ל-P4. זה בדיוק מה ש-G2.11 אוסר.

### 2.5 מה כבר יש לנו ב-0 טוקנים
- **פריימי הסיפור (‏2720×1530):** הערך האמיתי שלהם הוא כבסיס ל-P1. חיתוך ישיר כמעט אף פעם לא מגיע לרזולוציה של דף מוצר. מדדתי:
  - השמיכה בנורדי A: כ-640×370 פיקסלים.
  - האגרטל במודרני החם A ‏(ed9): כ-150×260.
  - מנורת הטרוורטין בנורדי A: כ-34×75.
  - P1 לפי G4.16 בגודל 1080×1350 צריך מוצר בגובה 675 פיקסלים לפחות בפריים. זה קורה רק לפריט גדול וקרוב (שטיח, ספה).
- **שכבות הכלי:**
  - **בבנייה הציבורית:** הן כבר התמונה היחידה של 34 מוצרים. הן נשארות **תמונות ממוזערות זמניות** עד שיש P2, בתנאי שהצד הארוך של המוצר בשכבה הוא לפחות 160 פיקסלים.
  - **השכבות הנורדיות זמניות** (`styled-preview-r2`). לכן לא חותכים מהן שום נכס קבוע.
  - **השכבות והקומפוזיטים של המודרני החם (v3c, ‏AP3-WM) מאושרים.** חיתוך של שלושת סטי הכריות על הספה הוא מועמד ל-P1 ב-0 טוקנים. QA מודד, ואם לא עובר, P1 לכל סט עולה 250.
- **נורדי B:** סל הלבד (`magazine-holder-felt-log-basket`) "נאמן" שם, ולכן יש בסיס מוכן ל-P1 של אחד מחמשת הדפים הריקים.
- **בקוד:**
  - כל התמונות הממוזערות (52, ‏64×80, ‏OG);
  - תמונת סט (ה-P2 של הפריטים על נייר, לגלגל של המודרני החם);
  - צל המגע;
  - שרטוט מידות;
  - הפלטה הריקה;
  - גיליונות הייחוס.

### 2.6 רשומת המקור
- **הקובץ:** `assets/product-images/<card-id>/manifest.json`. זה קובץ חדש, לא מסמך מחייב ולא שינוי בכרטיס.
- **לכל תמונה נרשמים:**
  - הסוג (P1–P4) וה-SKU;
  - המודל;
  - הפרומפט (או ה-hash שלו);
  - תמונת הבסיס שלנו (נתיב בריפו);
  - רשימת הייחוסים (אינדקסים בכרטיס);
  - הטוקנים;
  - פסק ה-QA ונתיב הדוח;
  - `own: true`.
- **האתר:** בדיקת `check:rights` של S15 מתרחבת: תמונה שלנו עולה רק עם `own: true` ופסק QA "עבר". זה עבור frontend-dev.

## 3. המודל והמחיר לכל סוג תמונה
**המחירים:**
- **מהבריף:** seedream-5-pro 2K ‏650, ‏nano-banana-pro ‏250, ‏gpt-image-2 2K ‏600, ו-gpt-image-2-5 עם רקע שקוף.
- **מהמתכון:** gpt-image-2-5 2K ‏600, ‏nano-banana-2 4K ‏450.
- **מ-`docs/var2-models.md`:** ‏remove-background ‏50.
- **הנחה:** gpt-image-2-5 עם רקע שקוף מתומחר כמו ה-2K, כלומר 600.
- **לפני כל אצווה** render-agent מריץ `var2_estimate_cost`, ועוצר בסטייה של יותר מ-10% (SPEND2).

| סוג | ראשי | חלופה | למה |
| --- | --- | --- | --- |
| **P2 סטודיו** | **gpt-image-2-5, ‏2K, רקע שקוף: ‏600** | **nano-banana-pro על הפלטה הריקה, ועוד remove-background: ‏250+50 = 300.** הפיילוט מכריע (A/B) | **בעד gpt:** <br>• אלפא מקורי, כמו בשלד ("PNG שקוף"), בלי צעד חיתוך ובלי הילה בשוליים רכים (פרנזים, בוקלה, סיבים). <br>• הוא היה הנאמן יותר מבין השניים בשתי הבדיקות שלנו (נורדי A ‏8/6/2 מול 8/3/5; מודרני חם 7/3/1 מול 4/2/5). <br>**בעד nano:** <br>• חצי מחיר. <br>• כשיש אובייקט אחד, nano שומר צורה ומרקם (מתכון §1). <br>• הבסיס הוא פלטה שלנו, כלומר עריכה של תמונה שלנו. <br>**ההכרעה:** אם שניהם עוברים את כל הקריטריונים בשלושת המוצרים, עוברים ל-nano וחוסכים כ-15,900 ב-53 ה-P2 שנשארים |
| P2 של סט רב-פריטי שנכשל בספירה | gpt-image-2, ‏2K: ‏600, ועוד remove-background ‏50 | — | עד 15 ייחוסים, והיענות גבוהה לפרומפט ארוך (`docs/var2-models.md`) |
| **P1 בחדר** | **nano-banana-pro, ‏2K, עריכה: ‏250** | nano-banana-2, ‏4K: ‏450 (המודל של המתכון לתקריבים) | עקביות זהות חזקה בעריכה, ולכן החדר והאור של הבסיס נשמרים. החלופה היא למקרה שה-2K מאבד חומר. הפיילוט בודק את הראשי, והחלופה רצה רק בכשל |
| **P3 חומר** | **nano-banana-pro, ‏2K, עריכה: ‏250** | — | עריכה של חיתוך שלנו. רק "קרוב יותר ובאור גורף" |
| **P4 גוון** | **nano-banana-pro, עריכה: ‏250** | P2 חדש (600), כשהבנייה שונה | שומר את הגאומטריה של ה-P2 שלנו, ומחליף רק צבע לפי תמונת ה-SKU |
| **תיקון** | seedream-5-pro, ‏2K, על חיתוך עם מסכה: ‏650 | — | כלי הנאמנות של המתכון (§3). רק על כשל QA, ובשחרור של המנהל |
| **לא בשימוש** | | | <br>• **seedream כבסיס:** יקר, והוא כלי התיקון. <br>• **flux:** לא נבדק. <br>• **topaz ו-recraft upscale:** ממציאים מרקם, וזה סיכון ל-G-ED.3 |

## 4. הספירה והעלות
### 4.1 מחיר ליחידה
| | gpt | nano |
| --- | --- | --- |
| P1 | 250 | 250 |
| P2 | 600 | 300 |
| P3 | 250 | 250 |
| P4 (גוון) | 250 | 250 |
| **מוצר רגיל (P1+P2)** | **850** | **550** |
| **טקסטיל גדול (P1+P2+P3)** | **1,100** | **800** |

### 4.2 הבית הנורדי: 39 המוצרים הציבוריים
- **"ב":** ברירת המחדל בעמדה.
- **שלב:** פ = פיילוט, ‏0 = הדפים הריקים, ‏1א = ברירות המחדל, ‏1ב = שאר האפשרויות, ‏1ג = גוונים (P4).
- **סימון הגוונים:** זמני. המעצב מאשר כל גוון על תמונת ה-SKU מול טווחי ה-Bible לפני הרינדור. גוון שלא עובר יורד, ולא מוחלף.

| # | עמדה | מוצר (מזהה הקטלוג) | P1 | P2 | P3 | P4 (הגוון המסומן) | טוקנים (gpt) | שלב |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | curtains | ב · `curtains-japanese-linen-half-shade-j35b9` | 1 | 1 | 1 | 1 (טבעי, ‎#D9CDB8) | 1,350 | 1א, 1ג |
| 2 | framed-art | ב · `framed-art-morandi-triptych-sage-mjyac` | 1 | 1 | — | — (IMG1c, ‏IMG1e) | 850 | 1א |
| 3 | wall-decor | ב · `wall-decor-macrame-dowel-4hx2b` (50×70) | 1 | 1 | 1 | — | 1,100 | **0** (P2, ‏P3), 1א (P1) |
| 4 | wall-decor | `wall-decor-macrame-diamond-dowel-small-ej8ww` | 1 | 1 | — | — (דגם 2: ‏IMG1c) | 850 | **0** (P2), 1ב (P1) |
| 5 | accent-sconces | ב · `accent-sconces-indoor-stone-wall-lamp-eavr7` | 1 | 1 | — | — (גוון האור: טקסט) | 850 | **פ** |
| 6 | accent-sconces | `accent-sconces-ribbed-travertine-half-cylinder-sw668` | 1 | 1 | — | — (21 סגנונות אחרים: ‏IMG1c) | 850 | 1ב |
| 7 | wall-sconce | ב · `wall-sconce-black-swing-arm-fabric-wom7h` | 1 | 1 | — | — | 850 | 1א |
| 8 | wall-sconce | `wall-sconce-travertine-dome-alt-mpd0t` | 1 | 1 | — | — | 850 | 1ב |
| 9 | wall-sconce | `wall-sconce-travertine-dome-pull-gyglx` | 1 | 1 | — | — | 850 | 1ב |
| 10 | vase | ב · `vase-textured-white-stoneware-w90r9` | 1 | 1 | — | — (מידות) | 850 | **פ** |
| 11 | vase | `vase-coarse-sand-white-tall-hye4v` | 1 | 1 | — | — | 850 | 1ב |
| 12 | vase | `vase-white-plum-hand-thrown-karts` | 1 | 1 | — | — | 850 | 1ב |
| 13 | rug | ב · `rug-braided-wool-natural-jzzjv` | 1 | 1 | 1 | — | 1,100 | 1א. ה-P1 סוגר את ה"חלקית" (Q-ED4) |
| 14 | floor-lamp | ב · `floor-lamp-black-drum-linen-uaeow` | 1 | 1 | — | — | 850 | 1א |
| 15 | planter | ב · `planter-seagrass-belly-msbbq` | 1 | 1 | — | — | 850 | 1א |
| 16 | planter | `planter-seagrass-belly-jyyuu` | 1 | 1 | — | — | 850 | 1ב. אם sourcing מאשר שזה אותו מוצר כמו #15, ה-P2 משותף ו-600 נחסכים |
| 17 | planter | `planter-cement-ribbed-belly-64nmq` | 1 | 1 | — | 1 (האחר מבין אפור ובז') | 1,100 | 1ב, 1ג |
| 18 | sofa-cover | ב · `sofa-cover-cotton-muslin-fringe-0iz5d` | 1 | 1 | 1 | — (גווני המודרני החם: ב-4.3) | 1,100 | **פ** |
| 19 | sofa-cover | `sofa-cover-washed-hemp-throw-g8qc5` | 1 | 1 | 1 | 1 (Tea Green, אם הוא בטווח המרווה) | 1,350 | 1ב, 1ג |
| 20 | sofa-cover | `sofa-cover-linen-feel-chenille-slipcover-l9ue3` | 1 | 1 | 1 | 1 (אפור בהיר, אם הוא בטווח הערפל) | 1,350 | 1ב, 1ג |
| 21 | cushions | ב · `cushions-boucle-teddy-d7wrb` (בחדר: לבן) | 1 | 1 | — | 1 (תה חלב; גם סט A) | 1,100 | 1א, 1ג |
| 22 | cushions | `cushions-knitted-chenille-bean-green-4z66l` (בחדר: מרווה) | 1 | 1 | — | 1 (בז', ‎#D9CBB3) | 1,100 | 1ב, 1ג |
| 23 | cushions | `cushions-textured-boucle-throw-pillow-7ryhq` (בחדר: בז') | 1 | 1 | — | 1 (פחם, נשא ההדגשה) | 1,100 | 1ב, 1ג |
| 24 | basket | ב · `basket-jute-rope-cylinder-6wing` | 1 | 1 | — | — | 850 | 1א |
| 25 | basket | `basket-cotton-rope-white-oz7y4` | 1 | 1 | — | — | 850 | 1ב |
| 26 | basket | `basket-seagrass-belly-jesuk` | 1 | 1 | — | — | 850 | 1ב |
| 27 | magazine-holder | ב · `magazine-holder-felt-log-basket-c59b4` | 1 | 1 | — | 1 (האפור השני) | 1,100 | **0** (P2), 1א (P1, הבסיס נורדי B), 1ג |
| 28 | magazine-holder | `magazine-holder-arch-iron-cane-ema28` | 1 | 1 | — | — | 850 | **0** (P2), 1ב (P1) |
| 29 | magazine-holder | `magazine-holder-felt-snap-bucket-fg4zg` | 1 | 1 | — | 1 (אפור בהיר) | 1,100 | **0** (P2), 1ב (P1), 1ג |
| 30 | table-runner | ב · `table-runner-linen-look-sage-fringe-9vndw` | 1 | 1 | 1 | 1 (בז') | 1,350 | 1א, 1ג |
| 31 | table-runner | `table-runner-ben-white-linen-look-22xdb` | 1 | 1 | 1 | — | 1,100 | 1ב |
| 32 | table-runner | `table-runner-linen-look-triangle-end-zy6bg` | 1 | 1 | 1 | 1 (לבן שמנת או חאקי, זה שלא בחדר) | 1,350 | 1ב, 1ג |
| 33 | bowl | ב · `bowl-speckled-ivory-wide-bowl-1491s` | 1 | 1 | — | — | 850 | 1א |
| 34 | bowl | `bowl-reactive-white-rimmed-plate-jeo2t` | 1 | 1 | — | — | 850 | 1ב |
| 35 | candle-holders | ב · `candle-holders-travertine-pedestal-5hc18` (זוג) | 1 | 1 | — | — | 850 | 1א |
| 36 | pouf | ב · `pouf-cotton-knit-ball-cover-mlo5s` | 1 | 1 | — | 1 (אפור בהיר, אם הוא בטווח הערפל) | 1,100 | 1א, 1ג |
| 37 | pendant | ב · `pendant-pleated-pumpkin-lantern-94iy6` | 1 | 1 | — | — | 850 | 1א |
| 38 | pendant | `pendant-silk-pumpkin-lantern-ttc1x` | 1 | 1 | — | — | 850 | 1ב |
| 39 | pendant | `pendant-tiered-fabric-drum-cjkd4` | 1 | 1 | — | — | 850 | 1ב |
| | | **סה"כ** | **39** | **39** | **9** | **12** | **38,400** | 99 תמונות |

**במסלול nano: ‏26,700** (‏39 × 300 פחות).

### 4.3 הבית המודרני החם
- **מתי:** כשהבית עולה לציבור, והחנות מקבלת את המוצרים שלו (S15, שאלה 3; ‏ת43).
- **המוצרים:** רק המוצרים שנמכרים או מוצגים ב-PRE1 באותו רגע.
- **16 המוצרים המשותפים:** כבר מכוסים ב-4.2. מתווספים להם רק הגוונים שבסטים.

| # | עמדה | כרטיס | P1 | P2 | P3 | טוקנים (gpt) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | curtains | ב · `curtains-aliexpress-beige-linen-sheer-curtains-554205` | 1 | 1 | 1 | 1,100 |
| 2 | curtains | `curtains-aliexpress-linen-blend-s-fold-180502` | 1 | 1 | 1 | 1,100 |
| 3 | framed-art | ב · `framed-art-aliexpress-frameless-minimalist-wall-art-631735` (IMG1e) | 1 | 1 | — | 850 |
| 4 | framed-art | `framed-art-aliexpress-modern-minimalist-neutral-gallery-802995` (IMG1e) | 1 | 1 | — | 850 |
| 5 | accent-sconces | ב · `accent-sconces-aliexpress-travertine-cylinder-walnut-choice` | 1 | 1 | — | 850 |
| 6 | accent-sconces | `accent-sconces-cj-travertine-block-updown-8x16` | 1 | 1 | — | 850 |
| 7 | vase | `vase-cj-charcoal-carved` | 1 | 1 | — | 850 |
| 8 | floor-lamp | ב · `floor-lamp-cj-pleated-walnut-stem-158` | 1 | 1 | — | 850 |
| 9 | cushions, סט B | `cushions-cj-wide-stripe-corduroy-light-green` (Camel) | 0 (סט) | 1 | — | 600 |
| 10 | cushions, סט B | `cushions-cj-linen-look-charcoal` (Beige 30×50) | 0 (סט) | 1 | — | 600 |
| 11 | cushions, סט C | `cushions-cj-corduroy-patchwork` (Dark Coffee) | 0 (סט) | 1 | — | 600 |
| 12 | cushions, סט C | `cushions-cj-linen-look-ivory` (Light Beige Gray) | 0 (סט) | 1 | — | 600 |
| 13 | magazine-holder | ב · `magazine-holder-cj-gunmetal-leather-strap` (Orange, קוניאק) | 1 | 1 | — | 850 |
| 14 | bowl | ב · `bowl-cj-matte-black-bowl-20` | 1 | 1 | — | 850 |
| 15 | bowl | `bowl-cj-glutinous-white-belly-bowl-21` | 1 | 1 | — | 850 |
| 16 | candle-holders | `candle-holders-cj-ceramic-pedestal-tray` | 1 | 1 | — | 850 |
| 17 | candle-holders | `candle-holders-aliexpress-matte-black-iron-pillar-set2` | 1 | 1 | — | 850 |
| | **17 מוצרים** | | **13** | **17** | **2** | **13,950** |
| | **P4 של מוצרים משותפים, בגווני הסטים** | שמיכת המוסלין: Pecan (בפיילוט), ‏Flax brown, ‏Clay. ‏Teddy: ‏Light brown. השניל: ‏"21 Camel" (מוצג כטאופ). הבוקלה: Oatmeal 50×50, אם הוא שונה מהבז' שבחדר | | | | **6 × 250 = 1,500** (‏Pecan נכלל בפיילוט) |
| | **P1 לשלושת הסטים** | חיתוך מהקומפוזיטים המאושרים A, ‏B ו-C (‏v3c). QA מודד | | | | **0**, או עד 750 אם חיתוך נכשל |
| | **תמונת סט לגלגל** | ה-P2 של ארבעת הפריטים על נייר, בקוד | | | | **0** |
| | **סה"כ המודרני החם** | | | | | **15,450** (‏+750 מותנה). ב-nano: ‏10,350 |

### 4.4 הסיכום והסדר
| שלב | מה | gpt | nano | מתי |
| --- | --- | --- | --- | --- |
| **פיילוט** | 3 מוצרים, עם A/B ב-P2 (§5) | **3,950** (+ עד 2,000 רזרבה) | אותו דבר | עכשיו, באישור IMG1a |
| **0: הדפים הריקים** | P2 לחמשת המוצרים בלי תמונה, ו-P3 למקרמה 50×70 | 3,250 | 1,750 | מיד אחרי הפיילוט. חוסם `HD_PUBLIC=1` |
| **1א: ברירות המחדל הנורדיות** | P1+P2 (+P3) ל-13 ברירות המחדל שנשארו, ו-P1 לשתי ברירות המחדל משלב 0 | 12,300 | 8,400 | אחרי 0. אלה המוצרים שבסט החדר ובסיפור |
| **1ב: שאר האפשרויות הנורדיות** | 21 מוצרים | 17,050 | 11,650 | אחרי 1א |
| **1ג: גוונים נורדיים** | 12 × P4 | 3,000 | 3,000 | אחרי 1ב, או יחד איתו |
| **2: המודרני החם** | 4.3, בלי Pecan (נעשה בפיילוט) | 15,200 (+750) | 10,100 (+750) | כשהבית עולה לציבור |
| **סה"כ** | | **54,750** | **38,850** | |
| **רזרבת תיקונים** | seedream, ‏650 לכל ~10 תמונות (כ-129 תמונות אחרי הפיילוט) | עד 8,450 | עד 8,450 | המנהל משחרר, לכל מקרה |

> **החשבון:**
> - **הפיילוט (3,950)** כולל:
>   - את חלקו של הנורדי: 2,800, כלומר P1+P2 לשלושת המוצרים ו-P3 לשמיכה;
>   - את ה-P4 של Pecan: 250;
>   - את הענף של ה-A/B שלא ייבחר: 900 במסלול gpt, או 1,800 במסלול nano.
> - **לכן:**
>   - **gpt:** ‏38,400 (הנורדי) + 15,450 (המודרני החם) + 900 = 54,750.
>   - **nano:** ‏26,700 + 10,350 + 1,800 = 38,850.
> - הטבלה ב-§0 מציגה את אותם סכומים לפי בית.

**מה חוסך בלי לפגוע:**
- **המסלול הזול (nano):** כ-16,000, אם הפיילוט מראה שהוא נאמן באותה מידה.
- **P1 הוא גם תקריב שכבה 2 של הסיפור.** המתכון תמחר "6 תקריבים לחדר בסגנון", כ-2,700. כל P1 שנעשה כאן לא נעשה שוב בסיפור.
- **P2 הוא גם "תמונת הגלגל" של השלד** (54 תמונות לסלון). כשהכלי הנורדי ירונדר מחדש (DIR2), לא מייצרים תמונות גלגל בנפרד.
- **P1 רק לברירות מחדל** (IMG1b, חלופה): חוסך 5,250 בשלב 1ב. לא מומלץ: דף של אפשרות ציבורי בדיוק כמו דף של ברירת מחדל.
- **#15 ו-#16 הם אולי אותו מוצר:** אם כן, נחסכים 600.

## 5. הפיילוט: 3 מוצרים
### 5.1 למה דווקא אלה
| | מוצר | למה הוא מספר את הסיפור |
| --- | --- | --- |
| **טקסטיל** | `sofa-cover-cj-cotton-muslin-fringe` (ציבורי: `…-0iz5d`). ‏SKU שבחדר: White 150×200 ‏(`CJYD205807526ZA`) | <br>• ברירת מחדל בנורדי, ובשלושת סטי המודרני החם (Pecan, ‏Flax, ‏Clay). <br>• שמיכה גדולה: בודקת את P3. <br>• בודקת פרנזים, קמט וגוון לבן שנקרא שנהב. <br>• בודקת P4: ל-Pecan מחיר ותמונות אחרים מה-White, ולכן ייתכן שהבנייה שונה. זה בדיוק המקרה של G2.11 ושל "21 Camel" |
| **קרמיקה** | `vase-cj-textured-white-stoneware` (‏`…-w90r9`). ‏SKU: ‏Large 32×16 ‏(`CJJT312391803CX`) | <br>• ברירת מחדל בשני הבתים. <br>• המרקם המקומט הוא החומר כולו. <br>• הכרטיס מזהיר שתמונות הספק אולי מרונדרות. <br>• "נאמן" במודרני החם A, ולכן יש בסיס מוכן ל-P1 |
| **מנורה** | `accent-sconces-aliexpress-indoor-stone-wall-lamp` (‏`…-eavr7`). ‏SKU: ‏16 ס"מ, ‏3000K ‏(`12000043242375290`), זוג | <br>• ברירת מחדל בנורדי. <br>• הייחוסים הטובים ביותר בעמדה: 10 תמונות חדות ומידות ידועות (‏Ø6.5 × 16, בליטה כ-9). <br>• קטנה, ולכן בודקת את הנטייה של המודל להגדיל מנורות פי 1.3–3 (Bible 1.9). <br>• דולקת ב-P1 (אלומה למעלה ולמטה). <br>• זוג ב-P2, ולכן בודקת ספירה. <br>• אינה בשום פריים, ולכן בודקת "החלפה" בתוך חיתוך שלנו |

**לא נבדק בפיילוט:**
- שטיח מלמעלה;
- הדפס (IMG1e);
- P3 של כרית בגודל בינוני.

הכלל ל-P3 (מעל 60 ס"מ בלבד) נבחן בעקיפין: אם ה-P2 של האגרטל קורא את המרקם ב-100%, הכלל מחזיק.

### 5.2 מה מייצרים, ובכמה
| # | תמונה | מודל | בסיס | טוקנים |
| --- | --- | --- | --- | --- |
| 1–3 | P2-A לשלושת המוצרים | gpt-image-2-5, ‏2K, שקוף | אין (טקסט וגיליון) | 1,800 |
| 4–6 | P2-B לשלושת המוצרים | nano-banana-pro, ועוד remove-background | הפלטה הריקה שלנו | 900 |
| 7 | P1 שמיכה | nano-banana-pro | `nordic-A-ed4.png`, חיתוך ‎[1650, 450, 2450, 1450]‎ | 250 |
| 8 | P1 אגרטל | nano-banana-pro | `warm-modern-A-ed9.png`, חיתוך ‎[1600, 560, 2160, 1260]‎ | 250 |
| 9 | P1 מנורה | nano-banana-pro | `nordic-A-ed4.png`, חיתוך ‎[900, 230, 1460, 930]‎. שם יושבת היום מנורת הבלוק, והיא מוחלפת | 250 |
| 10 | P3 שמיכה | nano-banana-pro | חיתוך 1:1 ב-100% מה-P2 של השמיכה שנבחר | 250 |
| 11 | P4 שמיכה, Pecan ‏(`CJYD205807508HS`) | nano-banana-pro | ה-P2 של השמיכה על ‎#808080 | 250 |
| | **בסיס** | | | **3,950** |
| | **רזרבה** (המנהל משחרר) | <br>• עד 3 × nano-banana-2 4K ל-P1 שנכשל (1,350). <br>• מעבר seedream אחד (650) | | **עד 2,000** |

**החיתוכים:**
- בפיקסלים של הפריים המקורי, ‏x0, y0, x1, y1.
- render-agent מתאים ±5% למסכת המוצר ורושם.
- QA מאשר שהמוצר "נאמן" בפריים הזה לפני השימוש.

### 5.3 הייחוסים
גיליונות לפי §2.2. בתיקיית הסשן בלבד, ונרשמים ב-`jobs.json` לפי אינדקס.

- **שמיכה:**
  - **R1:** תמונת ה-SKU ‏White (`images.urls[0]`).
  - **R2–R3:** שתי תמונות הכרטיס שבהן הפרנזים והקמט הכי ברורים. render-agent בוחר ורושם.
  - **דוגמית:** מצד מואר של R1.
  - **ל-P4:** תמונת ה-SKU ‏Pecan, גזורה, ועוד דוגמית.
- **אגרטל:**
  - **R1:** תמונת ה-SKU ‏Large (‏`02d028bc…_trans.jpeg`).
  - **R2–R3:** שתי תמונות שמראות את תבליט הקמטים ואת השפה והפה.
  - **דוגמית:** מהצד המואר של R1.
- **מנורה:**
  - **R1–R3:** שלוש התמונות החדות באור חם: חזית, צד עם לוחית הגב והבליטה, ותמונה דולקת (גזורה למנורה בלבד).
  - **לא נכנסות:** תמונה 4 (אפרפרה, באור קר) ושתי טבלאות המידות. המספרים עוברים לפרומפט.

### 5.4 הפרומפטים (מדויקים)
**בלוק הסטודיו** (קבוע בכל P2; ‏`[STUDIO]` למטה):
```
Light: one large soft light from camera-left, 45° to the side and 30° above, with a gentle fill from the right about 1.5 stops darker; neutral daylight white balance (5000 K) so the colours read true; soft, no hard shadows, no shine; matte surfaces stay matte.
Fidelity: the reference sheet shows the product only. Match it exactly: shape, proportions, colour, material, texture and number of pieces. Do not reproduce the camera angle, background, lighting, props, styling, folding or arrangement of any reference image. No text, no logo, no label, no watermark, no people.
```

**P2-A, שמיכה** (gpt-image-2-5, ‏2K, ‏4:5, ‏background transparent):
```
Studio product photograph for a design-magazine catalogue, isolated on a fully transparent background: no floor, no wall, no surface, no props.
Product: exactly one cotton muslin throw, 150 × 200 cm, in its "white" colourway: a warm ivory off-white (#EEE8DD, shadows in the folds around #E2D9CB), not pure white, not grey. Multi-layer cotton muslin with a small waffle grid and an all-over soft crinkle, matte. A short frayed fringe, about 2–4 cm long, on the edges exactly as in the reference sheet. No visible sewn label.
Arrangement: folded in thirds lengthwise and then in half, lying flat; the front corner of the top layer is turned back to show the fringe along two edges and the soft folded edges. Relaxed, not ironed, not stiff.
Camera: 50 mm, looking down at 35°, turned 30° so the fold reads in three-quarter view. The whole folded throw is in frame and fills 80% of the frame width, centred, nothing touching the edges. 4:5 vertical.
[STUDIO]
```

**P2-A, אגרטל:**
```
Studio product photograph for a design-magazine catalogue, isolated on a fully transparent background: no floor, no surface, no props, no branches.
Product: exactly one stoneware vase, 32 cm tall and 16 cm at its widest, mouth about 9 cm across: its height is twice its width. Its silhouette is exactly the soft jar shape in the reference sheet. The whole body carries a fine crinkled relief like crumpled paper or weathered stone, creases about 1–2 cm apart, low relief; the rim is smooth and untextured. Off-white, warm-neutral (#EEECE8; shadows in the creases around #DEDBD5), not cool white, not pure white. Matte unglazed stoneware. Empty.
Camera: 85 mm, at 60% of the vase's height, looking down 8°, so the rim reads as a thin ellipse. The vase stands upright, verticals straight, centred, filling 80% of the frame height. 4:5 vertical.
[STUDIO]
```

**P2-A, מנורה:**
```
Studio product photograph for a design-magazine catalogue, isolated on a fully transparent background: no wall, no surface, no props.
Product: exactly two identical wall lamps (a pair), switched off, side by side with a 10 cm gap, both turned the same way. Each lamp is one honed travertine cylinder, 6.5 cm in diameter and 16 cm tall (2.5 times as tall as it is wide), vertical, pale warm beige (#D9C7A3) with open pores and soft horizontal banding of natural stone, matte, not polished and not resin-smooth; it is mounted on the small dark walnut-toned wooden wall plate exactly as in the reference sheet (its shape and its size relative to the cylinder), about 9 cm deep in total. Light openings at the top and bottom of the cylinder; no bulb visible; no cable, no switch.
Camera: 85 mm, at the lamps' centre height, turned 30° from the left so the depth from the wall plate reads. The pair fills 80% of the frame width, centred. 4:5 vertical.
[STUDIO]
```

**P2-B (nano-banana-pro):**
- **תמונת הבסיס:** הפלטה הריקה שלנו.
- **הפרומפט:** אותם בלוקי Product, ‏Arrangement, ‏Camera ו-[STUDIO], עם שני שינויים:
  - **השורה הראשונה מוחלפת ב:** `Edit this image: place on this empty studio paper exactly one … (as below). Keep the paper's colour and evenness; a soft short contact shadow under the product only.`
  - **ובמנורה:** `the pair stands upright on the paper as if hung on an invisible wall; no shadow`.
- **אחר כך:** ‏remove-background.

**P1, שמיכה** (בסיס: חיתוך מ-`nordic-A-ed4.png`):
```
Edit this photograph. Re-photograph the same corner of the same living room as a close-up of the ivory muslin throw draped over the right arm of the sofa: 85 mm lens, camera at the height of the sofa arm, about 1.5 m away and a little from the left; shallow depth of field (about f/2.8): the throw fully sharp, the room behind it soft.
Keep the room exactly as in this photograph: the low February sun from the window on the left and its diagonal stripes of light, the warm white wall, the cream sofa, the charcoal cushion, the white bowl, the colours and the time of day. Add nothing else; no second throw.
The throw: exactly one cotton muslin throw in warm ivory (#EEE8DD), multi-layer muslin with a small waffle grid and soft crinkle, a short frayed fringe about 2–4 cm long on its edges, matte; it hangs over the arm in soft folds with the fringed edge visible. It matches the reference sheet exactly in weave, crinkle, fringe and colour.
Framing: the throw fills 50–65% of the frame height, its centre on the right third line, nothing important touching the edges. 4:5 vertical.
No people, no readable text, no logos. Do not reproduce the composition of the reference images.
```

**P1, אגרטל** (בסיס: חיתוך מ-`warm-modern-A-ed9.png`):
```
Edit this photograph. Re-photograph the same scene as a close-up of the white crinkled vase on the walnut coffee table: 85 mm lens, camera at the height of the vase's shoulder, about 1.2 m away; shallow depth of field (about f/2.8): the vase sharp from rim to foot, the sofa and cushions behind it soft.
Keep the room exactly: the low golden evening sun from the glazing on the left, the bouclé sofa, the walnut table, the olive branch in the vase, the colours and the time of day. Add nothing else; no second vase.
The vase: exactly one stoneware vase, 32 cm tall and 16 cm wide, mouth about 9 cm (height twice the width), the soft jar silhouette of the reference sheet; fine crinkled relief over the whole body, creases about 1–2 cm apart; smooth rim; off-white #EEECE8 on its lit side, matte. It matches the reference sheet exactly.
Framing: the vase fills 50–65% of the frame height, on the left third line, nothing touching the edges. 4:5 vertical.
No people, no readable text, no logos. Do not reproduce the composition of the reference images.
```

**P1, מנורה** (בסיס: חיתוך מ-`nordic-A-ed4.png`, סביב מנורת הקיר שמשמאל להדפסים):
```
Edit this photograph. Re-photograph the same wall as a close-up of the wall lamp to the left of the framed prints: 85 mm lens, camera at the lamp's height, about 1 m from the wall and a little from the left; shallow depth of field: the lamp fully sharp, the olive tree and the room soft.
Keep the room exactly: the warm white plaster wall and its soft hand-trowelled texture, the low February sun from the window on the left, the colours and the time of day. Add nothing else.
Replace the wall lamp in this photograph with exactly one lamp from the reference sheet: one honed travertine cylinder, 6.5 cm in diameter and 16 cm tall (2.5 times as tall as it is wide), vertical, pale warm beige #D9C7A3 with open pores and soft horizontal banding, matte, on its small dark walnut-toned wooden wall plate, about 9 cm off the wall. It is switched on: warm 2700 K light leaves the top and bottom openings and washes the wall in two soft beams, each about 25 cm long and no wider than 20 cm, with soft edges, running out of the frame; the stone itself is not burnt out; no bulb visible, no cable.
Framing: the lamp body fills 50–65% of the frame height, on the left third line. 4:5 vertical.
No people, no readable text, no logos. Do not reproduce the composition of the reference images.
```

**P3, שמיכה** (בסיס: חיתוך 1:1 ב-100% מה-P2 הנבחר, בפינה המקופלת, מונח על ‎#F4F1EC):
```
Edit this photograph. Re-photograph this exact corner of the folded throw as a macro detail: 100 mm macro lens, the camera closer and square-on to the fabric, f/8 so the whole frame is sharp. Light: the same soft light from the left, lowered to a raking angle of about 20° so the waffle grid and the crinkle cast tiny shadows. Keep the colour exactly (warm ivory #EEE8DD), keep the fold and the fringe where they are, keep the paper behind the fringe. The waffle grid, crinkle and fringe match the texture reference in scale: the fringe is about [N] grid cells long. Add nothing. 1:1.
```
`[N]` נמדד על ייחוס המרקם על ידי render-agent, ונכתב כמספר לפני השליחה.

**P4, שמיכה Pecan:**
- **רק אחרי הבדיקה המוקדמת:** תמונת ה-SKU ‏Pecan מראה אותו מוסלין ופל, אותם פרנזים ואותו עובי כמו ה-White.
- **אם לא:** עוצרים. זה P2 חדש, באישור המנהל.
```
Edit this photograph. Change the throw to the "Pecan" colourway shown in the colour reference: the same product in its warm mid-brown. Keep everything else exactly: the shape, the folds, the turned-back corner, the waffle grid, the crinkle, the fringe (same yarn, same colour as the cloth), the light and the shadows. Only the colour of the fabric changes, to match the colour reference on its lit side. The grey background stays as it is.
```

### 5.5 תנאי הקבלה
**לכל תמונה בפיילוט:** "אין קומפוזיציה של ספק" (C1–C5, ‏§6), בלי טקסט, מותג או סימן מים, ופסק עין כתוב של המעצב.

| תמונה | עובר כש… |
| --- | --- |
| **P2, שמיכה** | <br>• שמיכה אחת. <br>• פרנזים באותם שוליים כמו בתמונת ה-SKU, באורך של 4–8% מרוחב הקיפול (2–4 ס"מ מ-50). <br>• אין תווית. <br>• ופל וקמט נקראים ב-100%. <br>• **צבע** (חציון בצד המואר של השכבה העליונה): ‏L* ‏89–95, ‏C* ‏3–9, ‏h ‏70–100. ‏ΔL* עד 6 מול הצד המואר של תמונת ה-SKU. <br>• **אלפא:** ברצועה של 1–4 פיקסלים מחוץ לאלפא אין הילה. ‏ΔE00 עד 2 בהרכבה על ‎#F4F1EC ועל ‎#3A3A3A. קצות הפרנזים נשארים חצי-שקופים (G2.3, ‏G2.5). <br>• 2K מקורי, חד ב-100% |
| **P2, אגרטל** | <br>• אגרטל אחד, ריק. <br>• **פרופורציות:** ‏H/D ‏2.0 ±10%. פה/קוטר 0.56 ±15%. גובה הכתף (הרוחב המרבי) מול תמונת ה-SKU ±10%. <br>• שפה חלקה. <br>• קמטים על כל הגוף, במרווח של 3–6% מהגובה. <br>• **צבע:** ‏L* ‏90–95, ‏C* עד 5, ‏h ‏60–100. לא כחלחל (H ‏180–260 אסור ב-Bible). <br>• אנכיים ישרים (±0.5°) |
| **P2, מנורה** | <br>• **בדיוק 2 יחידות.** בכל אחת גליל אחד ולוחית גב אחת. <br>• **פרופורציות:** ‏H/D ‏2.46 ±10%. צורת הלוחית ויחס הגודל שלה לגליל כמו בייחוס. <br>• נקבוביות ופסים נקראים ב-100%. <br>• **צבע:** ‏L* ‏76–85, ‏C* ‏11–20, ‏h ‏70–95. לא אפור. <br>• בלי נורה, בלי כבל |
| **P1, שלושתן** | <br>• G-ED.2–G-ED.5: "כן" למוצר. <br>• G-ED.6–G-ED.7: אין כפיל, אין סט מדומה. <br>• G-ED.10–G-ED.12: <br>&nbsp;&nbsp;◦ אין HDR; <br>&nbsp;&nbsp;◦ שרוף עד 1% חוץ מהחלון, על הגולמי; <br>&nbsp;&nbsp;◦ L* באחוזון 1 לפחות 8. <br>• G-ED.13: האור של הפריים נקרא (נורדי: שמש פברואר; המודרני החם: ערב זהוב). <br>• G4.16: ‏50–65% מהגובה, על קו שליש, בלי משיקים. <br>• החדר מזוהה כחדר של הבסיס: אותו קיר, אותם חומרים, ואין מוצר חדש |
| **P1, מנורה, בנוסף** | <br>• דולקת. <br>• שתי אלומות רכות, כל אחת עד פי 1.9 מגובה הגוף ועד פי 1.25 מגובה הגוף ברוחב. זה כלל ה-Bible: עד 30 ו-20 ס"מ. <br>• הגוף לא שרוף (G-ED.12): הנקבוביות נקראות ואין ערוץ ≥254 על האבן |
| **P3, שמיכה** | <br>• אותו צבע כמו ה-P2: ‏ΔE00 עד 4 בצד המואר. <br>• יחס אורך הפרנזים לתא הוופל ±20% מול ייחוס המרקם. <br>• אין דוגמה חדשה. <br>• חד ב-100% |
| **P4, ‏Pecan** | <br>• הבדיקה המוקדמת עברה. <br>• **הגאומטריה לא זזה:** ‏IoU של צללית המוצר מול ה-P2 לפחות 0.99, לפני שהאלפא מוחל מחדש. מחוץ למוצר, על האפור, אין שינוי מעל 2 רמות. <br>• **צבע** מול הצד המואר של תמונת ה-SKU ‏Pecan: ‏Δh עד 8°, ‏ΔL* עד 6, ‏ΔC* עד 5. <br>• **המרקם נשמר:** סטיית התקן של L* בפס הגבוה בתוך ±15% מה-P2. <br>• **G2.11:** גיליון זה-לצד-זה של תמונת ה-SKU וה-P4, ופסק כתוב של QA ושל המעצב: "אותו SKU" |

### 5.6 סדר העבודה, ומה הפיילוט מכריע
1. **render-agent, ‏0 טוקנים:**
   - גיליונות ייחוס;
   - הפלטה הריקה;
   - הבדיקה המוקדמת של Pecan;
   - `var2_estimate_cost`.
2. **P2-A ו-P2-B לשלושת המוצרים** (2,700).
3. **QA, סבב 1, על ה-P2:** נאמנות ו-C1–C5. המעצב שופט את העין.
4. **P1 ×3, ‏P3, ‏P4** (1,250), על ה-P2 שנבחר.
5. **QA, סבב 2.** תיקון רק מהרזרבה, ובשחרור של המנהל.
6. **frontend-dev, ‏0 טוקנים:** דף מוצר לבדיקה מאחורי הדגל, עם שלוש הערכות. הוא כולל את התמונות הממוזערות הנגזרות ואת הדוגמיות בקבוצה 3.
7. **הבעלים:** רואה את שלושת הדפים ואת הגיליון.

**מה יוצא מהפיילוט:**
- **D1, המודל ל-P2:**
  - nano, אם שניהם עוברים בכל השלושה.
  - אחרת, זה שעובר.
  - אם שניהם נכשלים בקטגוריה, נכתב לה כלל (למשל gpt-image-2 לסטים).
- **D2, המודל ל-P1:** ‏nano-banana-pro, או החלופה ב-4K לפי קטגוריה.
- **D3, ‏P4 בעריכה:** מותר, או P2 לכל גוון. זה משנה את 1ג ואת הגוונים של המודרני החם.
- **D4:** הספים של C3, מכוילים.
- **D5:** מכאן יוצא גם מפרט "הסטודיו של הבית" הסופי (§2.3), שעובר לשלד. זה שינוי במסמך מחייב, ולכן באישור הבעלים.

**התוצרים:**
- `assets/product-images/pilot-2026-11-11/<card-id>/` ובה:
  - `p2-a.png`, ‏`p2-b.png`, ‏`p1.png`, ‏`p3.png`, ‏`p4-pecan.png`;
  - `jobs.json`, ‏`manifest.json`.
- `qa/reports/<date>-own-images-pilot.md` ו-`.json`.
- גיליון ההשוואה מול תמונות הספק הוא ראיה פנימית של QA. הוא לא עולה לאתר.

## 6. מה QA בודק
**הסדר:** כמו ב-G-ED ‏§4. קודם סבב 1, אחריו תיקונים, אחריו סבב 2, אחריו עין המעצב, ואז הבעלים בפיילוט ובגיליון לכל שלב.

**הכלל:** תמונה עולה לאתר רק עם "עבר" ורשומת מקור (§2.6), כי "נכס שלא עבר QA לא נכנס לאתר".

| # | בדיקה | על | המקור |
| --- | --- | --- | --- |
| Q1 | **צללית, ספירה ופרופורציה:** P2 ב-±10% (אין לו תירוץ של פרספקטיבה). P1 ב-±15% | P1–P4 | G-ED.2, ‏G-ED.4 (העקרונות של G1.1 ו-G1.3) |
| Q2 | **צבע, חומר ודוגמה:** <br>• **P2 ו-P4:** באור ניטרלי, מול הצד המואר של תמונת ה-SKU ומול ה-hex של הכרטיס. כשהם סותרים, התמונה קובעת (הלקח של "21 Camel"). <br>• **P1:** מול שכן ניטרלי באור הסצנה | P1–P4 | G-ED.3 (‏G1.2) |
| Q3 | **פסק לכל מוצר:** כן / חלקית / לא. **רק "כן" עולה** | כל תמונה | G-ED.5 |
| Q4 | **הגוון הוא ה-SKU:** גיליון של SKU מול P4 | P4 | G2.11 (מחייב) |
| Q5 | **אין כפיל, אין סט מדומה, אין טקסט, אין מותג, אין "אסור"** | P1 (ועל ‏P2–P4: טקסט וסימן מים) | G-ED.6, ‏G-ED.7, ‏G-ED.14–G-ED.16 |
| Q6 | **מעקות הגריידינג, סיפור האור ומסגור התקריב** | P1 | G-ED.10–G-ED.13, ‏G4.16 |
| Q7 | **טכני:** <br>• הילה באלפא ושוליים רכים; <br>• 2K מקורי, בלי הגדלה; <br>• חד ב-100%; <br>• הצל בקוד בכיוון הבית | P2, ‏P4 | G2.3, ‏G2.5 (הסף: הצעה) |
| Q8 | **כיסוי:** טבלת "מוצר × פריים" מתעדכנת. P1 שעבר נספר כתקריב. מוצר מקבל "מאושר לאתר" רק כשהכיסוי שלו שלם | הסט | G-ED.18 |
| **C1** | **הקלטים:** <br>• לפי `jobs.json`, אין תמונת ספק כבסיס (`image_url`) בשום קריאה. <br>• הבסיס הוא נתיב שלנו בריפו. <br>• QA פותח את גיליון הייחוס: מוצרים בלבד, בלי רקע, חפצים, טקסט או סימני מים | כל תמונה | חדש. המחקר §5ג |
| **C2** | **חמשת המרכיבים, מול כל תמונת ספק של הכרטיס** (‏`images.urls` ותמונות ה-SKU): <br>(1) זווית: ‏yaw וגובה בתוך 10°. <br>(2) מסגור: מרכז התיבה בתוך 10% מהפריים, וגודל בתוך 15%. <br>(3) רקע ומשטח. <br>(4) כיוון האור ואופיו. <br>(5) סטיילינג: חפצים, מילוי, וסידור הקיפול או הנפילה. <br>**עובר:** לכל היותר 2 מתוך 5 תואמים לתמונה אחת, ו-(5) אף פעם לא תואם בטקסטיל | כל תמונה | חדש. "אותה זווית, קומפוזיציה ורקע" (המחקר §5ג) |
| **C3** | **סידור קפלים מועתק** (טקסטיל בלבד): <br>• אחרי יישור תיבת המוצר, IoU של מפת הקצוות בתוך המוצר, מול כל תמונת ספק, מתחת ל-0.35. <br>• **הכיול בפיילוט:** אותו מדד בין זוגות של תמונות ספק של אותו מוצר. התמונה שלנו לא דומה לתמונת ספק יותר מהחציון של הזוגות | P2, ‏P3, ‏P4 של טקסטיל | חדש. הסף: הצעה |
| **C4** | **שאריות:** אין רפאים של סימן מים, אין שבר של טקסט או לוגו, אין יד, אין אריזה, ואין חפץ של הספק (אותו ענף, אותו ספר) | כל תמונה | חדש |
| **C5** | **רשומת מקור שלמה** (§2.6) | כל תמונה | חדש |

C1–C5 הן תוספת לשער. לכן qa-agent כותב אותן כשער קצר G-IMG, רק אחרי אישור הבעלים (IMG1b). עד אז הן חלות על הפיילוט כ"הצעה".

## 7. סיכונים, ומה ההצעה לא פותרת
- **הדפסים ותמונות קיר** (`framed-art`: מורנדי הנורדית, ‏631735, ‏802995, וגם השלישייה הגאומטרית של RND3):
  - **התמונה של הדפס היא היצירה עצמה.** צילום או רינדור שלנו לא פותר את זכויות האמן בהדפס. זה נכון כבר היום, גם בפריימים ובכלי.
  - **ההמלצה:** היתר בכתב מהמוכר להציג את העיצוב, והשאלה הזו נכנסת לייעוץ עם עורך הדין שהמחקר המליץ עליו (IMG1e).
- **זכויות עיצוב וסימני מסחר במוצר עצמו:** מחוץ להיקף המחקר. מוצרי הבית גנריים, ו-G-ED.15 נשאר.
- **מעמד זכויות היוצרים בתמונה שנוצרה ב-AI:** לא נבדק (המחקר §5ג). זה משפיע על ההגנה על הנכסים שלנו, לא על הסיכון שנפר.
- **העלאת תמונות ספק ל-var2 כייחוס:** שימוש פנימי. הכתובות לא נשמרות ולא משותפות. זה כמו היום (מתכון §2).
- **פער בין הקטלוג לסיפור בנורדי:** בנורדי A מופיעות מנורת הבלוק, תלויית המשי המחורצת והשלישייה הגאומטרית, אבל בחנות הנורדית ברירות המחדל אחרות.
  - P1 של מוצר שאינו בפריים נעשה כ"החלפה" בחיתוך.
  - אם החנות תיושר לסיפור, רשימת ה-P1 מתעדכנת.
  - זה בשביל המנהל. אין צורך בהחלטה כאן.
- **הפריימים שהם בסיס ל-P1 הם "מבחן סופי", לא "מאושר לאתר".** אם פריים ייעשה מחדש, ה-P1 שנגזרו ממנו נבדקים שוב. ה-P2, ה-P3 וה-P4 לא תלויים בבית, ולא נפגעים.

## 8. שאלות לבעלים
| # | השאלה | ההמלצה | מה כל תשובה אומרת |
| --- | --- | --- | --- |
| **IMG1a** | **הפיילוט:** 3 מוצרים, ‏3,950, ועוד רזרבה של עד 2,000 שהמנהל משחרר | **כן** | **לא:** אין תמונות משלנו. 5 דפים נשארים ריקים, ו-`HD_PUBLIC=1` חסום (או שהם מוסתרים) |
| **IMG1b** | **ערכת התמונות והשער:** <br>• P1+P2 לכל מוצר ציבורי; <br>• P3 רק לטקסטיל מעל 60 ס"מ; <br>• P4 רק לגוון שהמעצב סימן (בנורדי עד 1 למוצר); <br>• C1–C5 נכנסות כשער G-IMG | **כן** | **חלופה זולה:** P1 רק לברירות המחדל (‎−5,250). לא מומלצת |
| **IMG1c** | **אפשרויות בלי תמונה:** <br>• **גוון מחוץ לפלטה:** דוגמית ושם בלבד, עם השורה "בתמונות: {הגוון שבחדר}…". <br>• **עיצוב אחר** (הדפס אחר, דגם מקרמה 2, הסגנונות האחרים של מנורה): לא מוצע עד שיש לו תמונה שלנו. <br>זה מצמצם את "כל האפשרויות של הספק בדף המוצר" (חוקי הסטודיו ג, ‏2026-10-11) רק בעיצובים | **כן** | **אם רוצים עיצוב מסוים:** ‏+600 לכל אחד, כ-P2 |
| **IMG1d** | **חמשת הדפים הריקים:** שלב 0 מיד אחרי הפיילוט. אם `HD_PUBLIC=1` מגיע קודם, הם מוסתרים מהבנייה הציבורית (0 טוקנים) | **כן** | **השקה עם משבצת ניטרלית:** לא עומד ברף א.1 |
| **IMG1e** | **הדפסים:** <br>• היתר בכתב מהמוכר להצגת העיצוב (הבעלים שולח, ד.8); <br>• השאלה נכנסת לייעוץ עם עורך דין לקניין רוחני; <br>• עד אז, בלי P2 להדפסים | **כן** | **בלי היתר:** ההדפסים נשארים כמו היום (בחדר בלבד), עם אותה חשיפה |
| **IMG1f** | **ההיקף אחרי הפיילוט:** <br>• **שלבים 0 ו-1א עכשיו:** ‏15,550 (gpt) או 10,150 (nano). <br>• **1ב ו-1ג:** אחריהם. <br>• **המודרני החם:** כשהוא עולה לציבור. <br>לכל שלב `var2_estimate_cost` ודיווח | **כן** | **הכול בבת אחת:** עד 54,750 + 8,450, לפני שיש נתונים מהשלבים הראשונים |

## 9. מה זה אומר לשאר הסוכנים (0 טוקנים, אחרי IMG1)
- **render-agent:**
  - גיליונות ייחוס, פלטה ריקה, `jobs.json` ו-`manifest.json` בכל אצווה;
  - חיתוכי בסיס עם תיבה רשומה;
  - הבדיקה המוקדמת לכל P4.
- **qa-agent:**
  - C1–C5;
  - כיול C3 בפיילוט;
  - עדכון טבלת G-ED.18;
  - G-IMG אחרי IMG1b.
- **frontend-dev:**
  - **הגלריה:** P1 (עם "הדמיה"), ‏P2, ‏P3, ו-P4 לפי האפשרות שנבחרה.
  - **התמונות הממוזערות:** כולן מ-P2.
  - **סט:** תמונת סט בקוד.
  - **צל:** צל מגע בקוד.
  - **קבוצה 3:** דוגמית בלבד, עם השורה של IMG1c.
  - **`check:rights`:** מקבל `own: true` עם פסק "עבר".
  - **S15 שאלה 2(א):** נסגרת. אין משבצת ניטרלית כשיש P2.
- **sourcing-agent:** לבדוק אם `planter-seagrass-belly-msbbq` ו-`…-jyyuu` הם אותו מוצר.
- **המעצב:** אישור כל גוון מסומן על תמונת ה-SKU, לפני 1ג.
