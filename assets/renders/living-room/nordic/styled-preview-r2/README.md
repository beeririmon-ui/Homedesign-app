# תצוגת סטיילינג, סבב 2 (סלון נורדי, v4.1)

> **תצוגה מקדימה עם מוצרים זמניים. לא אישור 2, לא נכס לאתר.**
> render-agent, 2026-10-04 עד 2026-10-06. בריף: `briefs/styled-preview.nordic.md` סעיף 10 (כולל נספח 10.8). בסיס: `m0/pilot-v4.1/m0-pilot-b-graded.png`.
> **נתיב:** התיקייה הזו (`styled-preview-r2/`) והרשומות ב-`assets/prompts/styled-preview-r2.nordic/` הן לפי הוראת המנהל. סעיף 10.9 בבריף מציין נתיב אחר (`styled-preview/round-2/`).

## קבצים
| קובץ | מה |
| --- | --- |
| `step-a.png` … `step-d.png` | תוצר כל שלב: 2752×1548 (מ-2752×1536, Lanczos, בלי חיתוך), **אחרי נעילת צבע** (10.4). זה הקובץ שהועלה לשלב הבא |
| `styled-preview.png` | הסופי: step-d אחרי גריידינג גלובלי אחד (`grade.py`) |
| `compare.jpg` | סבב 1 מול סבב 2 |
| `raw/step-*.jpg` | מה ש-var2 החזיר. `raw/step-*-check.json`: מדידות לפני ואחרי הנעילה. `raw/final-check.json`: מדידות הסופי ובדיקת המנורות |
| `raw/step-a-take1-rejected.*` | ניסיון A ראשון, נדחה |
| `raw/refs/bowl-ivory-crop.png` | רפרנס הקערה (חיתוך מתמונת ספק, ראו למטה) |
| `check.py`, `grade.py` | מדידה, נעילת צבע וגריידינג |

## מודל, עלות ומזהים
מודל: var2 nano-banana-2, image-to-image, 2K, 16:9, בלי seed. הערכה מראש (`var2_estimate_cost`): 400 לקריאה, 2,000 לחמש קריאות.

| שלב | רפרנסים | placeholder_id | task_id | קישור | קרדיטים |
| --- | --- | --- | --- | --- | --- |
| A ניסיון 1 (נדחה) | 4 | 36132b83-74a4-42fc-9290-7fc3d76e6db9 | 9306e5a0dc7e91a34de79339e44dafef | https://www.var2.ai/image/36132b83-74a4-42fc-9290-7fc3d76e6db9 | 400 |
| A ניסיון 2 (הניסיון החוזר, נבחר) | 4 | 0b1d7e78-264a-4d8c-9d92-e3f01a0daf2e | 600433eba934bc20c614ed427ef02d74 | https://www.var2.ai/image/0b1d7e78-264a-4d8c-9d92-e3f01a0daf2e | 400 |
| B | 4 | 5f60861e-4c70-48cb-8ba5-0b9e281b00a6 | 7451e7a3740a34e0821a63e193adcb72 | https://www.var2.ai/image/5f60861e-4c70-48cb-8ba5-0b9e281b00a6 | 400 |
| C | 3 | 38ad083d-2df9-4faf-ab47-fcde1dcafacb | 6d1bf2af5f99bf26014754daa4a05f5a | https://www.var2.ai/image/38ad083d-2df9-4faf-ab47-fcde1dcafacb | 400 |
| D | 3 | 077e4980-ea27-4d15-b4a8-f6f001654131 | 2998ca2a0d59013ebd727e920225a6bd | https://www.var2.ai/image/077e4980-ea27-4d15-b4a8-f6f001654131 | 400 |
| גריידינג | — | — | — | — | 0 |
| **סה"כ** | | | | | **2,000 (בדיוק התקרה)** |

כל קלט הועלה דרך `var2_request_upload` ו-PUT, וה-sha256 של ההורדה זהה למקומי (step-a, step-b, step-c ורפרנס הקערה). הבסיס הוא ההעלאה מסבב 1, וה-sha256 שלו נבדק מחדש. URL-ים מלאים ברשומות.

**הניסיון החוזר נוצל בשלב A.** ניסיון 1 מחק את שולחן הקפה ובנה את הספה מחדש, גדולה בערך פי 1.3 ומוזזת קדימה, כך שכל השלבים הבאים היו נבנים על גאומטריה שבורה. ניסיון 2 נשלח **עם אותו פרומפט בדיוק**, עוד לפני שהמנהל ביקש לתקן את הפרומפט. ההודעה הגיעה אחרי שהקריאה כבר נשלחה. לכן לא נשאר תקציב לניסיון חוזר ב-C, וגם לא למדריך המיקום.

## בחירת רפרנסים (נספח 10.8, "לבחור")
| עמדה | נבחר | למה |
| --- | --- | --- |
| sofa-cover | `390a0e53..._trans.jpeg` | בז' על ספה שלמה, כיסוי נפרד לכל כרית, התקריב הגדול ביותר של הבד. ברירת המחדל (`aa791f9d`) מראה את הגוון האפור-בהיר |
| table-runner | `2320a973....jpg` | תקריב של הראנר בירוק-אפור עם הפרנזים המסוקסים. ברירת המחדל (`2736eed6`) מראה את הגוון הבז' |
| accent-sconces | ברירת המחדל `6cca2b06....jpg` | כיפה על קיר עם הילה, בלי חוט |
| bowl | **חיתוך** של `1cce1dd5....jpg` (תיבה 70,436–548,660 והגדלה ×2) | אף אחת מ-10 התמונות לא מראה את הקערה בשנהב המנומר לבד. ברירת המחדל (`7b0ee726`) מראה את הגוון האפור המסולסל (Natural). החיתוך מבודד את ערימת הקערות השנהב עם שפת החימר. זו סטייה מ"URL כמו שהוא", ולכן היא נרשמת כאן |

## שינויי פרומפט (באישור המנהל: "fix the prompt accordingly (record the change)")
- **A ו-B:** מילה במילה.
- **C ו-D:** **רק אחוזי הפריים** הוחלפו, כי שלב B שינה את המסגור (זום-אאוט קל והזזה שמאלה). המספרים המקוריים היו שולחים את פלטת מנורת הקיר לתוך הווילון ואת הטרוורטין השמאלי לתוך התמונה. כל שאר המילים כמו בבריף.
  - C: `60% to 67%` → `56% to 63%` (תלויה); `Plate on the left wall at 12% of the frame width` → `Plate on the left wall just left of the front curtain stack, at 4% of the frame width`; `56-58% and 82-84%` → `46-48% and 82-84%` (טרוורטין); `shade at 86% to 92%` → `83% to 90%` (מנורת רגל).
  - D: `about 33%` → `about 24%` (אגרטל); `66% to 73%` → `63% to 67%` (פמוטים); `46% to 56%` → `43% to 52%` (פוף).

ספירה ב-`len()` (הכול ASCII): **A 2300, B 3153, C 3101 (במקור 3064), D 2568**. כולם מתחת ל-3,800 ול-4,000.

## נעילת צבע (10.4), לפני → אחרי (H/S/L)
| שלב | קיר אחורי (0.69, 0.22) | מושב הכורסה (0.31, 0.75) | שטיח (0.60, 0.93) | הגברים ליניאריים R,G,B |
| --- | --- | --- | --- | --- |
| A | 23.7/26.2/90.3 → 33.0/24.7/89.8 | 19.4/15.1/83.0 → 27.8/14.5/82.5 | 30.6/48.5/77.7 → 32.5/47.2/77.2 | [0.9861, 1.0058, 0.9861] |
| B | 30.0/28.6/87.4 → 33.0/27.9/87.1 | 23.7/15.9/83.9 → 27.8/15.6/83.7 | 30.8/31.7/80.3 → 32.4/31.2/80.1 | [0.9933, 1.0028, 0.9935] |
| C | 26.2/24.5/80.3 → 33.0/23.3/79.5 | 21.5/16.2/79.5 → 31.3/15.4/78.7 | 28.0/30.6/75.9 → 32.2/29.4/75.2 | [0.9787, 1.0093, 0.9788] |
| D | 26.5/23.5/79.6 → 33.0/22.5/78.9 | 24.3/16.5/80.0 → 33.7/15.8/79.3 | 28.3/31.8/76.0 → 32.2/30.7/75.3 | [0.98, 1.0087, 0.9796] |

הנעילה הופעלה בכל שלב. ב-A הקיר יצא ב-H 23.7 (מחוץ ל-26–40). ב-B, ב-C וב-D הכורסה יצאה ב-H<25 עם S>15. בכל המקרים הקיר חזר ל-H 33.0. **הסחף הוורוד נעצר:** השטיח נשאר ב-H 32–34 (בסבב 1: 15.6). בשלב A נקודת השטיח היא עדיין פרקט.

## גריידינג סופי (0 קרדיטים)
`grade.py`:
1. איזון לבן גלובלי: הקיר האחורי ל-H 35, הגברים [0.9966, 1.0014, 0.9966].
2. חשיפה **+0.2 סטופ**, בתקרה.
3. כתף בהבהרות, k 0.7.
4. עקומת S עדינה, mix 0.12.
5. נקודת שחור 0.125.

בלי רוויה ובלי תיקון מקומי.

| נקודה (H/S/L) | יעד 10.4 | סופי | סבב 1 סופי |
| --- | --- | --- | --- |
| קיר אחורי | 32–40 / 15–28 / 86–92 | 35.6/31.6/86.4 | 23.4/13.0/85.0 |
| מושב הכורסה | H 25–60, S≤15 | 36.8/21.3/86.1 | 12.2/23.9/90.6 |
| שטיח | H 30–45 | 33.7/36.7/81.4 | 25.2/44.8/87.3 |
| חלון L p50 / p99 | הבהיר ביותר | 90.8 / 96.5 (שאר הפריים p99.5: 96.1) | |

**פערים:**
- S של הקיר (31.6) ושל הכורסה (21.3) מעל היעד. כבר ב-step-d אחרי הנעילה הכורסה הייתה ב-S 15.8. החשיפה ונקודת השחור מעלות את S של HSL ליד הלבן, וגם בלי עקומת S יוצא 20.5. לא תוקן מקומית.
- החלון עדיין הבהיר ביותר, אבל בהפרש קטן (p99 96.5 מול 96.1).

## S1–S16 לפי שלב
מיקומים כחלק מהפריים (u, v), נמדדו על רשת אחוזים. **התיבות ב-10.6 נכתבו לפי מסגור הבסיס, ומ-B המסגור השתנה.** לכן ב-S7/S14 אני מודד בעיקר מול הניסוח היחסי.

| | A | B | C | D |
| --- | --- | --- | --- | --- |
| **S1 גאומטריה** | **בגבול:** השולחן, הכורסה, החלון והפינה במקום (הזזה ≤0.0044). **אבל הספה גדלה:** u כ-0.49–0.90 מול 0.52–0.84 בבסיס | **נכשל:** מסגור חדש. הפינה זזה מ-0.431 ל-0.396 בערך, משקוף החלון מ-0.19 ל-0.15, והכול קטן מעט (זום-אאוט). נשמר כי לא היה תקציב | עובר מול B (בעין, אותו מסגור) | עובר מול C |
| **S2 רהיטים קבועים** | **נכשל חלקית:** הכורסה והשולחן זהים. הספה: אותו טיפוס (3+3 כריות, משענות track), אבל רחבה יותר, והכיסוי עם חצאית עד הרצפה מסתיר את רגלי האלון | ממשיך את A | ממשיך | ממשיך |
| **S3 פריטים קודמים** | — | עובר | עובר | עובר |
| **S4 נאמנות** | ראו טבלת הנאמנות | | | |
| **S5 בלי פריטים זרים** | עובר | עובר | עובר (השקע התבקש) | **נכשל:** הנרות **דולקים** (בפרומפט: "No candle flames") |
| **S6 בלי טקסט** | עובר | עובר | עובר | עובר |
| **S7/S14 מיקום וקנה מידה** | — | תמונה: u 0.506–0.797, ‏v 0.228–0.461; השורה כ-80% מרוחב הספה (יעד כ-75%) ✓. המרווח מעל גב הספה כ-0.07 (יעד: חצי גובה מסגרת, כ-0.12) ✗. סל: u 0.825–0.915, ‏v 0.64–0.83; השפה בגובה המושב, גדול מעט ✗. **שטיח:** הפינה השמאלית-קדמית ב-(0.16, 0.92), וכל ארבע רגלי הכורסה עליו (כמו בסבב 1) ✗. ראנר בשליש השמאלי, שטוח, נופל קדימה עם פרנזים ✓ | תלויה: u 0.52–0.61, ‏v 0.12–0.23, כ-0.4 מאורך השולחן (יעד ⅓). התחתית בקו ראש המסגרות, בלי פס קיר ביניהם ✗ (אבל קטנה וגבוהה בהרבה מסבב 1, ולא מסתירה הדפס). אהיל מנורת הקיר כשליש מרוחב הכורסה ✓, אבל מעל הווילון ולא מעל הכורסה ✗. מנורת רגל: אהיל u 0.825–0.895 ✓ | פוף u 0.375–0.52, ‏v 0.80–0.98, ראשו מתחת למשטח ✓. אגרטל ✓ (ראו S13). פמוטים u 0.555–0.60 ✗ (יעד 0.63–0.67). קערה u 0.61–0.68, כ-36 ס"מ מול 21 ✗ |
| **S8/S10 אור, מנורות** | — | — | **חלקי:** כל המנורות דולקות וחמות, וזוג הטרוורטין עם הילה ברורה (L 87.6 ו-85.4 מול קיר 83.6 ו-80.1). אהיל מנורת הרגל +8.3 L מעל הקיר, ומנורת הקיר +8.6. **התלויה: L 82.8 מול קיר 86.3**, כלומר זוהרת בגוון אבל לא בהירה מהקיר ✗. השלוליות על הספה, הכורסה והשולחן עדינות מאוד. החלון הבהיר ביותר בהפרש קטן | נשמר |
| **S9 נעילת צבע** | עובר אחרי נעילה | עובר | עובר | עובר. בסוף: H ✓, S ✗ (ראו גריידינג) |
| **S11 מנורת הקיר** | — | — | **נכשל:** כבל שחור ארוך יורד כ-0.3 מגובה הפריים לשקע שליד השיפולים, עם לולאה. לא לרצפה, אבל רחוק מ"6–12 ס"מ לשקע צמוד" | נשמר |
| **S12 (C21) שולחן מול כריות** | — | — | — | **נכשל קל:** הפמוט הגבוה עומד מול הפינה הימנית-תחתונה של כרית המרווה. שאר הכריות והשמיכה פנויות. שיפור גדול מול סבב 1 |
| **S13 (C22)** | — | — | טרוורטין שמאל u 0.445–0.47: כ-0.04 מהתמונה ✓, אבל צמוד לקצה עלוות הזית (פחות מ-0.02) ✗. ימין u 0.855–0.89: 0.06 מהתמונה ✓, 0.08 מעל אהיל מנורת הרגל ✓, אבל לא מעל קצה הספה (שמסתיימת ב-0.81) ✗ | אגרטל על האדן במרכז הכנף האחורית (u כ-0.22–0.28), רחוק מהעמוד ומהזית, והוא הפריט היחיד על האדן ✓ |
| **S15 כיסוי הספה** | **נכשל:** גוון ובד ✓ (בז' סלאב מט, בלי ברק, כיסוי לכל כרית), אבל חצאית עד הרצפה, **רגלי האלון לא נראות**, והמשענות מעוגלות ונפוחות | | | |
| **S16** | — | — | טרוורטין: אין חוט, תקע או שקע ✓ | **נכשל:** שני הפמוטים עומדים **על הראנר**, ואין 25 ס"מ של אלון חשוף |

## נאמנות למוצר
| עמדה | תואם | סטה |
| --- | --- | --- |
| sofa-cover (שניל, Beige) | גוון בז'-גרייג' (L כ-76), סלאב מט, כיסוי נפרד לכל כרית מושב וגב, בלי ברק | חצאית עד הרצפה, רגליים מוסתרות, הספה גדולה מהמקור. הגזרה "רפויה" יותר מהמוצר, שבתמונות שלו צמוד יותר עם גומי |
| שמיכה (מוסלין) | ופל, קמטוטים, פרנזים, לבן חם, נפילה טובה על המשענת | — |
| כריות | מרווה ✓, פחם סלאב ✓, לבנה בפינה ✓ | הבוקלה נראית יותר כסריגה עדינה מאשר לולאות. המרווה לא מוטה |
| rug | קרם-שיבולת שועל, פסים טון-על-טון, **לא ורוד** | גדול שמאלה, כמו בסבב 1 |
| framed-art D | שלושת ההדפסים בדיוק ובסדר הנכון, מסגרות שחורות דקות | נמוך מעט מעל הספה |
| curtains | פשתן שיבולת שועל עם סלאב, מוט שחור, נוגע ברצפה | ערימות רחבות, לא צרות |
| table-runner (Light Green) | ירוק-אפור עמום, פרנזים מסוקסים, נופל מעבר לשפה הקדמית | הפמוטים עומדים עליו |
| planter + olive | סל קש עם ידיות, עץ אוורירי, חצץ | — |
| basket | יוטה מגולגל, ידיות לולאה, ריק | גדול מעט |
| pendant 40 | דלעת שטוחה עם קפלים, לבן חם, כבל שחור | כ-0.4 מאורך השולחן, ונמוך מעט |
| wall-sconce | פלטה שחורה, זרוע מתקפלת, אהיל פשתן מחודד | **כבל ארוך לשקע נמוך**, הפוך מהבקשה |
| accent-sconces (טרוורטין 15) | כיפה מטרוורטין נקבובי, הילה חמה על הקיר, בלי חוט | מנורה ימין רחוקה מהתמונה |
| floor-lamp | עמוד שחור, תוף פשתן (גנרי, כמו שהבריף ביקש) | — |
| vase (Large 32) | לבן חם, מט, טקסטורה. ענפי אקליפטוס | **צורה:** כדורית-רחבה ולא כד עם פה קטן. **טקסטורה:** "מרוקעת" ולא מקומטת. נאמנות חלקית |
| candle-holders | טרוורטין בהיר, רגל וגביע, נרות עמוד 15 ו-10 | **נרות דולקים**; עומדים על הראנר |
| bowl (Large White) | שנהב מנומר | עמוקה ועגולה ולא חרוטית-רחבה, בלי שפת חימר נראית, **כ-36 ס"מ מול 21** |
| pouf | סריגה עבה, לבן-טבעי, עגול | — |

## מה המשתמש ביקש ומה הושג
| בקשה | מצב |
| --- | --- |
| האגרטל עובר מהשולחן לאדן החלון, כדי שהכריות לא יוסתרו | **הושג.** האגרטל על האדן, והכריות כמעט פנויות (רק הפמוט הגבוה נוגע בפינת כרית המרווה) |
| כיסוי ספה מלא ועוד שמיכה | **הושג חלקית.** כיסוי מלא בגוון ובבד של המוצר, והשמיכה במקומה. אבל עם חצאית עד הרצפה, רגליים מוסתרות, והספה גדלה |
| מנורת הקיר: אותו מוצר, כבל קצר לשקע צמוד, בלי כבל לרצפה | **לא הושג.** אותו מוצר ✓, ואין כבל עד הרצפה ✓, אבל הכבל ארוך (כ-40–50 ס"מ) לשקע שליד השיפולים |
| זוג מנורות טרוורטין קטנות משני צדי התמונה, מחווטות | **הושג ברובו.** זוג, דולקות, עם הילה ובלי חוט. הימנית רחוקה מדי מהתמונה, והשמאלית צמודה לעץ |
| אור חם יותר של 15:00, מנורות דולקות בבירור | **הושג ברובו.** חם יותר, והאהילים וההילות דולקים (מנורת הקיר ומנורת הרגל +8 L מעל הקיר). השלוליות עדינות, והתלויה לא בהירה מהקיר במדידה |
| ראנר, קערה ופמוטים על השולחן, בלי להסתיר כריות | **הושג חלקית.** שלושתם על השולחן. אבל הפמוטים עומדים על הראנר, הנרות דולקים, והקערה גדולה פי 1.7 |
| מחזיק העיתונים וקישוט הקיר נשארים ריקים | **הושג.** שתי העמדות האלה ריקות בתצוגה, כי עוד אין להן מוצר |

## הפרומפטים, מילה במילה (כפי שנשלחו)
### A (2300 תווים, מהבריף כמו שהוא). תמונות: 1 בסיס, 2 sofa-cover, 3 boucle, 4 sage, 5 throw
```text
Edit image 1, a finished photograph of a Scandinavian living room. Keep everything exactly as it is: camera, framing, walls, corner, window, cornice, skirting, oak floor, light, exposure, and the coffee table and armchair in the same position, size, colour and fabric. The sofa keeps exactly its position, size, low straight shape, square track arms, three seat and three back cushions and its visible oak legs. Only change what is listed below. Images 2-5 are product references: copy each product faithfully and take nothing else from them; ignore their rooms, furniture, props, labels and text.

1. SOFA SLIPCOVER (image 2): dress the whole sofa in the slipcover from image 2: a warm light greige-oatmeal linen-look fabric with an irregular slub weave, as in image 2, soft and dry to the eye. Relaxed tailored fit that follows the sofa's straight lines: square arms stay square, soft natural creases at the corners and along the front, a separate cover on each seat and back cushion, like image 2. The hem is tucked neatly just below the sofa frame, so the oak legs stay fully visible. Matte, no shine, no stretch look, no tight wrapping, no skirt, no elastic or hooks visible.

2. THROW (image 5): the warm white multi-layer cotton muslin throw, 150 x 200 cm, small waffle grid, natural crinkle, short frayed fringe. Loosely folded over the top of the right armrest, flowing across the front half of the right seat cushion and spilling over the seat edge in two or three deep soft folds. About the right fifth of the sofa. No label.

3. CUSHIONS, exactly three: Image 3: warm white looped boucle, 50 x 50 cm, upright at the left end in the corner of the arm and back cushion. Image 4: muted sage knitted chenille with a fine basket texture, 45 x 45 cm, in front of the boucle cushion, overlapping its lower right corner, tilted about 10 degrees. Charcoal linen-look slub lumbar, 30 x 50 cm, at the right end on the back half of the seat against the back cushion, just behind the throw and not covered by it. All plump, soft natural creases, matte.

Colour: walls warm white, creamy, never pink, lilac or grey. Natural colour, just below full saturation. Light unchanged; new items get soft shadows falling right and slightly toward the camera.

Do not add anything else. No text, logos or labels.
```

### B (3153 תווים, מהבריף כמו שהוא). תמונות: 1 step-a, 2 rug, 3 framed-art, 4 curtains, 5 table-runner
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, floor, daylight, exposure and white balance, and every item already in the room (dressed sofa, throw, three cushions, coffee table, armchair) in the same position, size, colour and folds. Only add the items below. Images 2-5 are product references (the planter and basket are described in words only): copy each faithfully and take nothing else from them; ignore their rooms, furniture, lamps, plants, people and text.

1. RUG (image 2): wool braided flat-weave rug, warm cream with heathered oatmeal yarns in soft tone-on-tone bands, never pink, square corners, no fringe, flat, matte. Under the coffee table, long side parallel to the sofa; the sofa's front legs on it, its back legs on the parquet. Its front-left corner is beside the armchair at 27% of the frame width and 89% of its height: only the armchair's two front legs stand on the rug. Its right edge passes a hand's width right of the sofa's right front leg. The front edge runs out of the bottom of the frame.

2. FRAMED ART (image 3): the three prints from image 3, same order, each 50 x 70 cm portrait in a thin matte black frame, 6 cm gaps. Each frame is about three quarters of one sofa seat cushion wide; the row is about three quarters of the sofa's width, centred above the sofa at 60% to 79% of the frame width and 28% to 51% of its height. The bottom of the frames is about half a frame height above the sofa back. Matte, no glare, no text.

3. CURTAINS (image 4): semi-sheer oatmeal hemp-linen with visible slub, pinch pleats on a slim matte black rod just below the cornice, drawn open into two narrow soft stacks beside the window, never over the glass, just touching the floor.

4. PLANTER: a natural honey-coloured woven seagrass belly basket with two small handles, 35 cm wide and 37 cm high, on the vertical corner line at 43% of the frame width, clear of the armchair, holding a young olive tree about 165 cm tall with an airy crown of silvery sage leaves, pale gravel, no soil.

5. BASKET: cylindrical coiled jute-rope basket, natural colour, two rope loop handles, empty. On the parquet just right of the sofa's right end with a narrow gap, at 86% to 92% of the frame width and 67% to 80% of its height. Its rim is a little below the sofa seat; it is about half as wide as a seat cushion is deep. The rug edge passes in front of its foot.

6. TABLE RUNNER (image 5): the muted grey-sage linen-look runner from image 5 with a fine knotted fringe at both ends, 33 cm wide and 122 cm long, matte slub weave, flat and thin, laid across the width of the coffee table in its left third, its centre line about 30 cm in from the table's left end, at a right angle to the table's long side. It drapes evenly over the front and back edges in soft straight folds, ending well above the rug. Nothing stands on it. The rest of the table top stays bare oak.

Colour: walls warm white, creamy, never pink, lilac or grey. Light unchanged; soft shadows to the right. No sun patches, no leaf shadows.

Do not add anything else: no lamps, mirrors, books or objects on surfaces. No text, logos or labels.
```

### C (3101 תווים, אחוזי פריים מותאמים). תמונות: 1 step-b, 2 pendant, 3 wall-sconce, 4 travertine
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, window, curtains, and every item already in the room, unchanged in position, size, colour and shape. Only add the items below and change the light as described. Images 2-4 are product references: copy each faithfully and take nothing else from them; ignore their rooms, beds, people and text. Image 2 may be a dimension drawing: ignore its lettering and lines.

1. PENDANT (image 2): closed pleated warm white fabric lantern, flat pumpkin form, dense fine pleats, matte. It is small: its width is about one third of the coffee table's length, narrower than one sofa seat cushion. It hangs above the centre of the coffee table, high: the whole lantern is in the top fifth of the image, at 56% to 63% of the frame width, and its bottom is well above the top edge of the frames, with a band of clear wall between them about as tall as the lantern itself. A thin black cord rises straight out of the top of the frame.

2. WALL LAMP (image 3): the black swing-arm wall lamp with an oatmeal linen tapered shade. Plate on the left wall just left of the front curtain stack, at 4% of the frame width and 37% of its height; the shade is small, about one third of the armchair's width, above and behind the armchair. Directly below the plate, a small flush square wall socket in the same warm white as the wall; a short straight black cord, a few centimetres, runs from the bottom of the plate into a plug in that socket. No cord below the socket, nothing running to the floor.

3. TRAVERTINE WALL LIGHTS (image 4): a matching pair of the small round domed wall lights from image 4, each dome 15 cm across and 12 cm deep, in honed warm light travertine with natural pores, matte. On the back wall, one on each side of the framed prints, each above one end of the sofa, at 46-48% and 82-84% of the frame width; the top of each lamp level with the top of the frames. Each is small, about a quarter of one frame's width. They are wired into the wall: no cords, no sockets, no plugs.

4. FLOOR LAMP: slim matte black pole floor lamp with an oatmeal linen drum shade as wide as the basket, just right of the sofa's right end behind the basket; shade at 83% to 90% of the frame width and 38% to 46% of its height; base hidden by the basket.

Light: late winter afternoon, about 3 pm, north-facing window, no direct sun. Daylight from the window is soft and slightly warmer, the room a little dimmer away from the window; the window stays the brightest area. All lamps are switched on and clearly lit with warm 2700 K light: shades glow from within; a warm pool on the right end of the sofa, a warm pool on the armchair's shoulder and seat, a soft warm wash on the centre of the coffee table; each travertine dome glows softly and leaves a small warm ring of light on the wall around it, as in image 4, not reaching the frames. No lamp shadows, no visible bulbs, no glare, flare or beams. Walls warm white, creamy, never pink, lilac or grey.

Do not add anything else: no wall decor, mirrors or extra lamps. No text, logos or labels.
```

### D (2568 תווים, אחוזי פריים מותאמים). תמונות: 1 step-c, 2 vase, 3 candle-holders, 4 bowl (חיתוך)
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, the late-afternoon light, every lit lamp and its glow, exposure, white balance, and every item already in the room, unchanged in position, size, colour and shape. Only add the items below. Images 2-4 are product references: copy each faithfully and take nothing else from them; ignore their backgrounds, flowers, props and text.

1. VASE ON THE WINDOW SILL (image 2): the textured stoneware vase from image 2, 32 cm tall and 16 cm wide, a soft jar shape with a small mouth, warm white, matte, with a fine crinkled stone-like texture and a smooth rim, about one sixth of the window opening's height. It stands on the window sill in the middle of the back casement, at about 24% of the frame width, its foot on the sill, clear of the mullion and of the olive tree. In it: three or four slender eucalyptus stems with round silvery sage leaves, airy, leaning slightly left, reaching about twice the vase's height. Its face is softly lit by the room and reads as matte textured ceramic, not a dark silhouette; the window behind it stays brighter. Nothing else on the sill.

2. CANDLE HOLDERS (image 3): two light travertine pedestal holders, 7 cm wide and 11 cm tall, each with an unlit warm white pillar candle 7 cm wide, one 15 cm and one 10 cm tall, flat tops and short white wicks. On the coffee table, standing in the gap between the left cushions and the charcoal lumbar cushion as seen from the camera, at 63% to 67% of the frame width; they must not overlap any cushion or the throw.

3. BOWL (image 4): the wide shallow stoneware bowl from image 4, 21 cm across and 5 cm high, warm ivory with fine dark speckles, a thin raw clay rim and a small foot ring, soft low sheen only, empty, in front of and right of the candle holders, forming a triangle with them. Nothing is placed on the linen runner in the left third of the table, and the bare oak between the runner and the candle holders stays empty.

4. POUF: round chunky-knit cotton pouf in natural off-white, a flat ball 45 cm wide and 36 cm high, plump, on the rug in front of the armchair at 43% to 52% of the frame width; its top below the lower edge of the table top.

Light unchanged. New items: soft shadows falling right and slightly toward the camera, short soft contact shadows. No candle flames. Walls warm white, never pink.

Do not add anything else: no magazine holder, magazines, books, trays, cups, fruit or extra flowers. The front-left corner under the wall lamp stays bare parquet. No text, logos or labels.
```

## הערות להמשך
1. **שלב A הוא נקודת התורפה:** "dress the whole sofa" עם רפרנס של ספה שלמה גורם למודל לבנות את הספה מחדש. בסבב הבא כדאי:
   - רפרנס של **בד בלבד** (תקריב), ולא של ספה.
   - ניסוח של "change only the fabric".
   - איסור מפורש על חצאית עד הרצפה.
2. **מסגור:** גם עם "Keep camera, framing" המודל עשה זום-אאוט ב-B. אפשר להוסיף מדריך מיקום כבר בניסיון הראשון, או לבדוק עם gpt-image-2.
3. **מנורת הקיר:** המודל מצייר את הכבל של מוצר plug-in כמו בתמונת הספק. כדאי:
   - מדריך מיקום עם השקע מסומן.
   - ניסוח כמותי: "socket directly touching the bottom of the plate".
4. **שולחן:** "No candle flames" לא נשמר כשהמנורות דולקות. וגם "nothing on the runner" לא נשמר בלי מסכה.
5. **תקציב:** 400 לקריאה עם ניסיון חוזר אחד לא מספיקים לארבעה שלבים משורשרים, כשכל שלב יכול לשבור את הקודם.
