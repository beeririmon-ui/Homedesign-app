# בריף רינדור: תצוגת סטיילינג, סלון נורדי (B, ‏v4.1)

> master-designer, 2026-10-04. גרסה 1.0. ל-render-agent. **גרסה 2.0 (אותו יום): סעיף 10 "סבב 2" מחליף את סעיפים 1–8 לסבב הבא**; סעיפים 1–9 נשארים כתיעוד של סבב 1.
> **מה זה:** תצוגה מקדימה של התצוגה הראשית עם מוצרים זמניים, כדי שהמשתמש ישפוט כמה החדר מעוצב ומושך (בעקבות ההערה "החדר מרגיש אנמי וריק... הספה נראית פשוטה ואנמית").
> **מה זה לא:** לא אישור 2, לא בחירת וריאציות, לא שכבה סופית ולא נכס לאתר. התוצר לא עובר QA לשכבות ולא נכנס לאתר. אף כרטיס לא מסומן `selected`.
> מקורות: `docs/design-bible/nordic.md` 1.3.1, `assets/blockout/living-room/v4-spec.json` v4.1 (+ `v4.1/overlay.png`), `data/slots/living-room.json`, `briefs/m0-prompt.nordic.md` 2.1, `data/selections/living-room.nordic.ranking.md`, הכרטיסים ב-`data/products/`.

---

## 1. מסלול

- **מודל:** var2 ‏nano-banana-2, ‏image-to-image (עריכה), ‏2K, ‏16:9.
- **בסיס:** `assets/renders/living-room/nordic/m0/pilot-v4.1/m0-pilot-b-graded.png` (2752×1548). להעלות דרך `var2_request_upload`, לאמת sha256 של ההורדה מול המקומי, ולהשתמש ב-URL שחזר.
- **שרשור:** כל שלב מקבל כקלט את התוצר המאושר של השלב הקודם (תמונה 1), ועוד תמונות רפרנס של המוצרים (תמונות 2 ואילך, בסדר שבפרומפט). אם var2 מחזיר 2752×1536, מחזירים ל-2752×1548 כמו בפיילוט (Lanczos, בלי חיתוך) **לפני** שמעלים לשלב הבא.
- **רפרנסים:** בדיוק ה-URL-ים שבטבלה בסעיף 3, כפי שהם בכרטיס, בסדר שבפרומפט. בלי רפרנסים נוספים.
- **פרומפטים:** מילה במילה מסעיף 6. כל אחד מתחת ל-3,800 תווים (לספור ב-`len()` לפני השליחה ולרשום).

## 2. תקציב

| שלב | תוכן | רפרנסים | קרדיטים |
| --- | --- | --- | --- |
| A | טקסטיל גדול על הספה ועל הרצפה: שטיח, שמיכה, 3 כריות | 5 | 400 |
| B | קיר וחלון: תמונה ממוסגרת, וילונות, עציץ ועץ הזית | 3 | 400 |
| C | תאורה ופינה ימנית: תלויה, מנורת קיר, מנורת רגל, סל. **המנורות נדלקות כאן** | 4 | 400 |
| D | שולחן הקפה והחזית: אגרטל וענפים, 2 פמוטים ונרות, פוף | 3 | 400 |
| רזרבה | ניסיון חוזר אחד, לשלב אחד בלבד | — | 400 |
| **סך הכול** | | | **1,600 + 400 = 2,000 (תקרה)** |

- לפני כל קריאה: `var2_estimate_cost`. **עוצרים** אם הסכום המצטבר יעבור 2,000.
- **למה 4 שלבים:** עד 5 רפרנסים בקריאה, כדי שהמודל לא "יערבב" מוצרים. החלוקה לפי אזורים בפריים ולפי תלות: הטקסטיל הגדול קודם (הוא משנה את הספה, את הרצפה ואת האיזון), אחר כך הקירות, אחר כך האור (כדי שהשלב האחרון יקבל את הזוהר החם על השולחן), והפריטים הקטנים בסוף, כדי שלא יימחקו או ישתנו בשלבים הבאים.
- **גריידינג (0 קרדיטים):** אם התוצר הסופי כהה מהבסיס, מותר גריידינג גלובלי אחד בשיטת `grade.py` (עד +0.5 סטופ, נקודת שחור L 12–15, בלי שינוי רוויה, בלי תיקון מקומי). לא מתקנים אזורים בנפרד.

## 3. המוצרים הזמניים (מוצר אחד לכל עמדה)

usage_rights בכל הכרטיסים הוא `unclear` (לא `none`). ‏**כל המוצרים כאן זמניים.** מוצר מסומן ⚠ הוא מתחת ל-7 או חסום בשער (חשמל או תמונות), ומשמש רק בתצוגה הזו, כי בלעדיו החדר לא נשפט נכון.

| עמדה | כרטיס | וריאנט | רפרנס לרינדור (מהכרטיס) | שלב |
| --- | --- | --- | --- | --- |
| rug | `data/products/rug/rug-cj-braided-wool-natural.json` (8.0) | **Square 230×330**, vid 2408230550421607700 (לא 200×300: עומק 200 לא עומד בכלל הרגליים בחדר) | https://oss-cf.cjdropshipping.com/product/2024/08/23/03/fc394992-638e-4235-abef-3731f45e02c7_trans.jpeg | A |
| sofa-cover | `data/products/sofa-cover/sofa-cover-cj-cotton-muslin-fringe.json` (8.0) | White 150×200, vid 2512040550081634900 | https://oss-cf.cjdropshipping.com/product/2025/12/04/05/857d7708-21e9-471c-a853-aabde32fe3ee.jpg (תמונת הווריאנט White, אומתה מול נתוני CJ) | A |
| cushions (1) | `data/products/cushions/cushions-cj-boucle-teddy.json` (8.5) | White 50×50, vid 2502072129321603700 | https://cf.cjdropshipping.com/quick/product/635be4cd-9b07-4238-bb0f-e709154b4740.jpg | A |
| cushions (2) | `data/products/cushions/cushions-cj-knitted-chenille-bean-green.json` (8.0) | 45×45 Bean Green, vid 2604070817141625000 | https://oss-cf.cjdropshipping.com/product/2026/04/07/08/8281f262-bc9c-4a77-9def-5be4d642a1ac.jpg | A |
| cushions (3) | `data/products/cushions/cushions-cj-linen-look-charcoal.json` (7.5) | Dark Grey 30×50, vid 1394921394533437440 | https://cf.cjdropshipping.com/1621409051190.jpg | A |
| framed-art ⚠ | `data/products/framed-art/framed-art-cj-morandi-triptych-sage.json` (6.5) | סגנון D 50×70, vid 2502230640411605000 | https://cf.cjdropshipping.com/quick/product/304d6cc7-3840-4582-af46-f2182133a2c9.jpg (תמונת הווריאנט D) | B |
| curtains ⚠ | `data/products/curtains/curtains-cj-japanese-linen-half-shade.json` (7.5, בתנאי) | Linen, ‏4 Hook (קפלי צביטה), vid 2411080726501623400 | https://cf.cjdropshipping.com/quick/product/344cc9f0-af5d-4b68-8959-a34e7830868b.jpg | B |
| planter ⚠ | `data/products/planter/planter-cj-seagrass-belly.json` (7.0) | Yellow 35×37, vid 1449351417306419200 | https://cf.cjdropshipping.com/1614673413923.jpg | B |
| pendant ⚠ | `data/products/pendant/pendant-cj-pleated-pumpkin-lantern-40.json` (8.5, חסום CE) | 40cm, vid 2601130233171624900 | https://oss-cf.cjdropshipping.com/product/2026/01/13/02/24c1901a-8dff-4184-a4bb-a4d5a066924b_trans.jpeg (תמונת הווריאנט 40: שרטוט המידות) | C |
| wall-sconce ⚠ | `data/products/wall-sconce/wall-sconce-cj-black-swing-arm-fabric.json` (7.0, חסום CE) | Type A EU, vid 2412050322241626600, אהיל פשתן | https://cf.cjdropshipping.com/quick/product/da5268c7-1a46-48a9-b61c-e54cff44a516.jpg (התמונה עם אהיל הפשתן) | C |
| floor-lamp ⚠ | `data/products/floor-lamp/floor-lamp-cj-black-drum-linen.json` (6.5, חסום) | 3Color Lamp-Black, vid 2508050616231611900 | https://oss-cf.cjdropshipping.com/product/2025/08/05/06/fbdc89df-9c40-4528-9989-0eb259135e9c.jpg | C |
| basket | `data/products/basket/basket-cj-jute-rope-cylinder.json` (8.5) | Large, vid 1708421287648956416 | https://cf.cjdropshipping.com/16d626dd-b2ac-4e75-895b-bedd311c32a7_trans.jpeg | C |
| vase | `data/products/vase/vase-cj-textured-white-stoneware.json` (8.5) | Large 32, vid 2609030743251617702 | https://cf.cjdropshipping.com/quick/product/5cdbca5f-e2d4-42b3-9baa-ef3ea8b2691f.jpg | D |
| candle-holders | `data/products/candle-holders/candle-holders-cj-travertine-pedestal.json` (8.5) | 2 × Small 70×110, vid 1781965542291677184 | https://cf.cjdropshipping.com/quick/product/d4def2f1-fdf6-44bc-a65c-9a90ad47f840.jpg | D |
| pouf ⚠ | `data/products/pouf/pouf-cj-cotton-knit-ball-cover.json` (7.5) | Original Cotton 50×50, vid 2512291109531603100 | https://cf.cjdropshipping.com/quick/product/0cf1414b-ec97-479f-9de6-835c3275be19.jpg | D |
| wall-decor | **לא מוצג** | — | — | — |
| table-runner | **לא מוצג** | — | — | — |
| magazine-holder | **לא מוצג** | — | — | — |

### למה כל בחירה (שורה לכל אחד)
- **rug:** המועמד היחיד, וטוב: צמר קלוע שטוח, פסים טון-על-טון שמבדילים אותו מהספה. ה-230×330 קרוב למעטפת (240×290); ברינדור עוקבים אחרי קו ה-overlay.
- **sofa-cover (לפי בקשת המשתמש לנוכחות):** המוסלין הרב-שכבתי עם גריד הופל הוא הבד היחיד הכשר שיש לו **משקל ונפילה אמיתיים**: הוא נופל בקפלים עמוקים ורכים (ראו תמונות הספק), והפרנזים הקצרים נותנים קצה חי. הנוכחות נבנית מנפח ומקפלים, ולא מצבע. **מגבלה:** הוא לבן-שנהב (L כ-90–92) על ספה ב-L כ-85, ולכן הניגוד בגוון עדין. הכריות (מרווה ופחם) והסטיילינג הנדיב נושאים את הניגוד. החלופה בצבע (קנבוס במרווה) חסומה, ראו סעיף 9.
- **cushions:** סט A מהדירוג: שלוש טקסטורות (לולאות, שניל בקליעת סל, פשתן סלאב) ושלושה גוונים (לבן חם, מרווה, פחם). זה הניגוד החזק ביותר שאפשר לתת לספה בתוך ה-Bible.
- **framed-art ⚠:** מוקד החדר. בלעדיו הקיר האחורי ריק וההערכה של המשתמש תהיה שגויה. סגנון D הוא הקרוב ביותר לפלטה, עם מסגרות שחורות (פחם). חסרים פספרטו, והירוק כהה מהמרווה. זמני בלבד.
- **curtains ⚠:** פשתן אמיתי עם סלאב, חצי-שקוף. בחרתי **Linen (שיבולת שועל)** ולא Light Beige: מסגרת רכה וחמה סביב החלון מוסיפה נוכחות לקיר השמאלי בלי להחשיך. **פער:** אורך המוצר 260, והמוט ב-282 דורש 275–285. בתצוגה מרנדרים לפי ה-Bible (נוגע ברצפה).
- **planter ⚠:** המוצר האמיתי היחיד שעומד במידות (35×37) ובגוון. ה-Bible מתיר וריאציה אחת בקש ים, וזה ממלא את ההיתר "פריט נוסף". ברירת המחדל לפי ה-Bible היא אבנית לבנה, ואין לה מועמד.
- **pendant ⚠:** פנס קפלים שטוח, וריאציה 3 ב-Bible. חסום ב-CE, ומשמש רק כדי להראות את משולש האור.
- **wall-sconce ⚠:** זרוע מתקפלת שחורה עם אהיל פשתן, וריאציה 2 ב-Bible. חסום ב-CE, והמשלוח יקר.
- **floor-lamp ⚠ (6.5, חריגה מנומקת):** מתחת ל-7, ויש לו תמונה אחת. נכנס כי מנורת הרגל היא הקודקוד הימני במשולש הגבוה ובמשולש האור, ובלעדיה הצד הימני נשאר "קר". מרנדרים צללית גנרית תואמת (עמוד שחור ותוף פשתן), במידות העמדה.
- **basket:** הדירוג הגבוה בעמדה, צללית גלילית נקייה, וסיבים טבעיים בצד הימני.
- **vase + candle-holders:** הזוג הגבוה בדירוג. מכסת האבן (2) מתמלאת בפמוטים, והאגרטל מקרמיקה.
- **pouf ⚠:** סריגה עבה בלבן חם (וריאציה 1 ב-Bible). **פער:** הכיסוי 50 ס"מ והעמדה ב-B דורשת קוטר 42–45 וגובה 35–36. בתצוגה מרנדרים 45×36, ו-qa בודק את הרווח מתחתית השולחן (C11).

### עמדות שלא מוצגות, ולמה
| עמדה | למה | איך בתצוגה |
| --- | --- | --- |
| wall-decor | המועמד היחיד (מקרמה 50×70, ‏6.5) חורג מהמעטפת ב-B (עד 55×55) והוא בוהו מובהק | **מושמט.** הקיר בין העץ לתמונה נשאר ריק. זה אוויר, לא חוסר |
| table-runner | אין מועמד כשר (4.0 נפסל; ראנר המאגר קצר מ-140 ולא נכנס) | **מושמט.** השליש השמאלי של השולחן נשאר אלון חשוף |
| magazine-holder | סל הלבד (7.0) הוא 45×32, והמעטפת בפינה 30×20: הוא היה נוגע בערימת הווילון ובשוליים | **מושמט.** כבל מנורת הקיר יורד עד השיפולים |

לא משתמשים בשום מוצר גנרי במקום המושמטים, כדי שהמשתמש לא יתאהב במוצר שלא קיים.

## 4. הסטיילינג (מה הופך את החדר למגזיני)

**הרעיון:** "בוקר חורף, מישהו קם מהספה לפני דקה". סדר, אבל לא סטרילי. הנוכחות באה מנפח, משכבות טקסטיל ומשלוש נקודות אור חם, ולא מעוד חפצים.

1. **הספה (מוקד הנוכחות):** השמיכה לא מקופלת לריבוע. היא מונחת בנדיבות על משענת היד הימנית ונופלת בקפלים עמוקים על חצי המושב הקדמי, עם פרנזים שגולשים מעבר לשפת המושב. כך נוצר אלכסון רך שמשבר את הקו הישר של הספה. בצד השמאלי שתי כריות בשכבות: בוקלה לבנה 50 מאחור בפינה, ושניל מרווה 45 לפניה, חופפת ומוטה. בצד הימני כרית מותן בפחם, נשענת על הגב מאחורי השמיכה. הפחם מימין והמרווה משמאל מותחים את הספה לרוחבה ונותנים לה "מסגרת". אין "חבטת קראטה" בכריות: נפוחות, עם קמטים טבעיים.
2. **שכבות על הרצפה:** אלון, שטיח צמר קלוע, ספה בשיבולת שועל, מוסלין לבן ובוקלה. חמש טקסטורות מלמטה למעלה באותו טווח חם, עם פחם ומרווה כנקודות.
3. **שולחן הקפה:** קבוצה אחת של שלושה בשליש הימני, במשולש גבהים: ענפים (עד 60 מעל השולחן), אגרטל 32, נר 15, נר 10. שני השלישים השמאליים ריקים לגמרי (מרכז ריק לשלולית התלויה).
4. **העץ והחלון:** הווילונות פתוחים לערימות צרות, החלון חשוף. עץ הזית בפינה מחבר בין קיר החלון לקיר האחורי ומחזיר את המרווה לשמאל.
5. **אור:** 10:30, יום חורף בהיר, החלון הוא המקור הראשי והבהיר ביותר. שלוש המנורות **דולקות בעוצמה נמוכה** (2700K) לפי ה-Bible: זוהר באהיל ושלוליות קטנות, בלי צל. זו ה"היגה" שהמשתמש לא ראה בפיילוט הריק, והיא חלק גדול מהתחושה "מזמין".
6. **אסור:** ספרים (החלטת משתמש), מגשים, כוסות, פירות, עיתונים, פרחים נוספים, שמיכה שנייה, כריות נוספות.

**בדיקת פלטה בסצנה:** פחם פעמיים ומעלה (מסגרות וקווי התמונה, כרית, מוט הווילון, זרוע מנורת הקיר, עמוד מנורת הרגל). מרווה ארבע פעמים (כרית, תמונה, עץ, ענפים). סיבים טבעיים משני הצדדים (עציץ קש ים משמאל, סל יוטה מימין).

## 5. מיקום בפריים (u = רוחב, v = גובה, 0–1 מהפינה השמאלית-עליונה; לפי v4-spec ‏v4.1)

| פריט | איפה |
| --- | --- |
| ספה (קבועה) | u 0.521–0.840, ‏v 0.548–0.799 |
| שולחן (קבוע) | u 0.512–0.762 |
| תמונה (שלישייה) | u 0.598–0.792, ‏v 0.281–0.512; תחתית לפחות 0.03 מעל גב הספה |
| תלויה | u 0.595–0.673, ‏v 0.052–0.174 |
| מנורת קיר | פלטה ב-(0.118, 0.372) |
| עציץ | כלי ב-u 0.410–0.452, על קו הפינה (u 0.431); לפחות 0.02 מהכורסה |
| מנורת רגל | אהיל u 0.856–0.917, ‏v 0.381–0.460; עמוד u 0.886; הבסיס מוסתר מאחורי הסל |
| סל | u 0.862–0.924, ‏v 0.667–0.797; לפחות 0.02 מהספה; שפת השטיח עוברת לפני תחתיתו |
| פוף | u 0.463–0.558, ‏v 0.756–0.947; החלק העליון לפחות 0.02 מתחת לתחתית משטח השולחן |
| שטיח | לפי `v4.1/overlay.png`: פינה שמאלית-קדמית בערך (0.27, 0.89), שפה אחורית מתחת לרגליים הקדמיות של הספה, השפה הקדמית יוצאת מתחתית הפריים |
| וילונות | ערימה קדמית עד u כ-0.203, ערימה אחורית בצד הפינה, מוט ב-282 ס"מ |

## 6. הפרומפטים (מילה במילה)

### שלב A: שטיח, שמיכה, כריות
תמונות: 1 = הבסיס, 2 = rug, ‏3 = sofa-cover, ‏4 = boucle, ‏5 = sage chenille, ‏6 = charcoal.
```text
Edit image 1, a finished photograph of a Scandinavian living room. Keep everything in it exactly as it is: camera, framing, walls, corner, window, cornice, skirting, oak floor, light direction, exposure and white balance, and the sofa, coffee table and armchair in the same position, size, colour and fabric. Move, resize or restyle nothing. Only add the items listed below. Images 2-6 are product references: copy each product faithfully (shape, proportions, colour, weave, edges) and take nothing else from them; ignore their rooms, people, furniture, props, labels and text.

1. RUG (image 2): wool braided flat-weave rug, 230 x 330 cm, warm cream with heathered oatmeal yarns in soft tone-on-tone bands, square corners, no fringe, completely flat, matte. It lies under the coffee table, long side parallel to the sofa. Its back edge passes under the sofa, so the sofa's front legs stand on the rug and its back legs on the parquet. The front-left corner sits beside the armchair at about 27% of the frame width and 89% of its height, with the armchair's front legs about 14 cm on the rug. The front edge runs out of the bottom of the frame. The right edge runs from just right of the sofa's right front leg down toward the bottom-right of the frame; the parquet to the right of the sofa end stays clear. Bands follow the floor perspective. Crisp edge, faint soft contact line, warm parquet visible around it.

2. THROW (image 3): the warm white multi-layer cotton muslin throw from image 3, 150 x 200 cm, small waffle grid with natural crinkle, short frayed fringe on all edges, matte, soft and heavy enough to fall in deep folds. Styled at the right end of the sofa: loosely folded in half, laid over the top of the right armrest with only a short fringed edge hanging outside the arm, then flowing across the front half of the right seat cushion and spilling over the front edge of the seat in two or three deep, soft folds. Generous and relaxed, not flat, not ironed, about the right fifth of the sofa. No visible label.

3. CUSHIONS, exactly three:
- Image 4: warm white looped boucle cover, 50 x 50 cm, knife edge, plump. Upright at the left end, leaning into the corner of the left armrest and the back cushion, turned slightly toward the room.
- Image 5: muted sage knitted chenille cover with a fine basket texture, 45 x 45 cm, plump. In front of the boucle cushion, overlapping its lower right corner, tilted about 10 degrees.
- Image 6: charcoal linen-look slub lumbar cover, 30 x 50 cm, plump. At the right end, standing on the back half of the seat against the right back cushion, just behind the throw; it is not covered by the throw.
All three full and soft with gentle natural creases, no chop dents, matte.

Light: the same 10:30 winter daylight from the left window as image 1. Every new item gets soft shadows falling right and slightly toward the camera and short, soft contact shadows, never black. No new light sources. Natural colour, just below full saturation.

Do not add anything else: no books, extra blankets, trays, plants, lamps, art, curtains, decor or extra cushions. No text, logos or labels.
```

### שלב B: תמונה, וילונות, עציץ ועץ זית
תמונות: 1 = תוצר A, ‏2 = framed-art, ‏3 = curtains, ‏4 = planter.
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, floor, daylight, exposure and white balance, and every piece of furniture and textile already in the room (sofa, coffee table, armchair, rug, throw, three cushions) in the same position, size, colour and folds. Move, resize or restyle nothing. Only add the items listed below. Images 2-4 are product references: copy each product faithfully and take nothing else from them; ignore their rooms, furniture, lamps, plants, people and text.

1. FRAMED ART (image 2): the three framed abstract prints from image 2, exactly as designed and in the same left-to-right order: sage arches above a dotted arch and a small sage dot; beige, sage and pale grey brush blocks; a sage organic shape with thin dark circular lines. Each print 50 x 70 cm portrait in a thin matte black frame, hung in a row with 6 cm gaps, 162 cm wide in total, on the back wall centred above the sofa, the centre of the row 147 cm above the floor. The row spans about 60% to 79% of the frame width and 28% to 51% of its height; its bottom is clearly above the sofa back. Flat, level, following the wall's perspective. Matte print, no glare, no reflections, no text, no signature. A thin soft daylight shadow under each frame.

2. CURTAINS (image 3): two panels of semi-sheer hemp-linen in natural oatmeal, strong visible slub, matte, daylight glowing through. Pinch-pleat heading on a slim matte black rod, mounted 12 cm below the cornice and 20 cm wider than the window opening on each side. Both panels are drawn open into narrow soft stacks, one beside the window's back jamb near the corner and one beside its front jamb, covering the wall and the edge of the reveal but never the glass. They fall straight in soft vertical folds and just touch the floor. The glass, the mullion and the garden view stay fully visible.

3. PLANTER WITH OLIVE TREE (image 4): the natural woven seagrass belly basket from image 4, 35 cm wide and 37 cm high, warm honey colour, herringbone weave, used as a floor pot in the back-left corner of the room. Its centre sits exactly on the vertical corner line at about 43% of the frame width, close to the walls, just right of the armchair with a clear narrow gap between them. In it: a young olive tree with one slender grey-brown trunk, about 165 cm tall including the pot, and an airy medium-density crown about 70 cm wide of narrow silvery sage-green leaves. The crown fills the corner between the back curtain stack and the wall left of the sofa, and stays clear of the framed art. Pale gravel top-dressing, no visible soil, no saucer.

Light: the same 10:30 winter daylight from the left window as image 1. New items cast soft shadows falling right and slightly toward the camera. No sun patches, no leaf shadows, no new light sources.

Do not add anything else: no lamps, mirrors, extra plants, shelves, wall decor, books or objects on surfaces. No text, logos or labels.
```

### שלב C: תלויה, מנורת קיר, מנורת רגל, סל; הדלקת המנורות
תמונות: 1 = תוצר B, ‏2 = pendant, ‏3 = wall-sconce, ‏4 = floor-lamp, ‏5 = basket.
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, floor, window, curtains, daylight direction, exposure and white balance, and every item already in the room (sofa, coffee table, armchair, rug, throw, cushions, framed art, olive tree in its basket), unchanged in position, size, colour and shape. Only add the items below. Images 2-5 are product references: copy each faithfully and take nothing else from them; ignore their rooms, beds, people and text. Image 2 is a dimension drawing: ignore its lettering, lines and arrows.

1. PENDANT (image 2): closed pleated fabric lantern, a flat pumpkin form 40 cm wide and 25 cm high, dense fine vertical pleats gathered into soft segments, warm white, matte. Not the egg-shaped model. A thin black cord rises straight up and out of the top edge of the frame. It hangs above the centre of the coffee table, its bottom 2.20 m above the floor, at about 60% to 67% of the frame width and 5% to 17% of its height, with clear wall between it and the framed art.

2. WALL LAMP (image 3): plug-in swing-arm wall lamp: small rectangular matte black wall plate, folding two-section matte black arm, tapered drum shade in oatmeal linen with a visible weave. On the left wall near the camera, the plate at about 12% of the frame width and 37% of its height, 1.47 m above the floor. The arm reaches about 40 cm out from the wall; the shade sits above and behind the armchair, well above its back. A black fabric cord falls straight down from the plate to the skirting, no loops.

3. FLOOR LAMP (image 4): slim straight matte black pole floor lamp with an oatmeal linen drum shade 36 cm wide and 30 cm high, 155 cm tall overall. It stands just right of the sofa's right end, close to the back wall; the shade at about 86% to 92% of the frame width and 38% to 46% of its height, touching neither the wall nor the frame edge. Its base is hidden behind the basket.

4. BASKET (image 5): cylindrical coiled-rope basket in natural jute colour, 35 cm wide, 39 cm body, two rope loop handles rising about 9 cm. On the parquet just right of the sofa's right end with a narrow clear gap, in front of the lamp base, at about 86% to 92% of the frame width and 67% to 80% of its height. The rug's edge passes in front of its foot, with the basket's own soft contact shadow on the parquet. Empty.

Lighting: still a bright 10:30 winter morning lit by the window, which stays the brightest area in the frame. Switch on all three lamps at a low, cosy level with warm 2700 K light: each shade glows softly from within; the floor lamp leaves a small warm pool on the right end of the sofa; the wall lamp a small warm pool on the armchair's back and seat; the pendant a faint warm wash on the centre of the coffee table. The lamps cast no visible shadows, no bulb is visible from the camera, no glare, flare, halos or beams. Daylight shadows stay as in image 1.

Do not add anything else. No text, logos or labels.
```

### שלב D: אגרטל וענפים, פמוטים ונרות, פוף
תמונות: 1 = תוצר C, ‏2 = vase, ‏3 = candle-holders, ‏4 = pouf.
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, daylight, the three lit lamps and their glow, exposure, white balance, and every item already in the room, unchanged in position, size, colour and shape. Only add the items below. Images 2-4 are product references: copy each faithfully and take nothing else from them; ignore their backgrounds, flowers, props and text.

Coffee table: one group of exactly three objects in the right third of the table top, standing on the bare oak. The left two thirds of the table stay completely empty.
1. VASE (image 2): the textured stoneware vase from image 2, 32 cm tall and 16 cm wide, a soft jar shape with a small mouth, warm white, matte, with a fine crinkled stone-like texture all over and a smooth rim. At the back of the group, toward the sofa, about 20 cm in from the table's right end. In it: four or five slender olive branches with narrow silvery sage-green leaves, loose and airy, the tallest about 60 cm above the table top, leaning slightly left; they may pass lightly in front of the lower edge of the framed art.
2. CANDLE HOLDERS (image 3): two identical light travertine pedestal holders, a cone foot with a small cup on top, 7 cm wide and 11 cm tall, honed matte, natural pores and soft horizontal veins. In front of and slightly right of the vase, 8 cm apart, forming a triangle with it. Each holds an unlit warm white pillar candle 7 cm wide with smooth straight sides, a flat top with a crisp edge and a short upright white wick: a 15 cm candle in the holder nearer the vase, a 10 cm candle in the other. The heights step down: branches, vase, tall candle, short candle.

3. POUF (image 4): round chunky-knit cotton pouf in natural off-white, a flat ball 45 cm wide and 36 cm high, plump and firmly filled, thick knit texture, rounded top. On the rug in front of the armchair and left of the coffee table, at about 46% to 56% of the frame width and 76% to 95% of its height. Its top stays below the lower edge of the table top behind it; clear rug between it and the armchair, the table and the bottom edge of the frame.

Light: unchanged. The new items catch the window light from the left, with soft shadows falling right and slightly toward the camera and short soft contact shadows; the pendant adds only a faint warm glow on the table. No candle flames.

Do not add anything else: no books, trays, bowls, cups, fruit, magazines, table runner or extra flowers. No text, logos or labels.
```

## 7. תנאי קבלה

**בכל שלב (render-agent בודק לפני שממשיך; אם נכשל, ניסיון חוזר אחד מהרזרבה, ואם גם הוא נכשל עוצרים ומדווחים):**
| # | תנאי | איך |
| --- | --- | --- |
| S1 | **גאומטריה לא זזה:** הפינה, החלון, הכרכוב, הספה, השולחן והכורסה בהזזה של עד 0.005 מול הבסיס (ועד 0.01 באזור מקומי) | אותה שיטה כמו ב-`measure.py` (קורלציית גרדיאנט, ±14 פיקסלים), מול `m0-pilot-b-graded.png` |
| S2 | **הרהיטים הקבועים לא השתנו:** צורה, גוון ובד של הספה, השולחן והכורסה (כולל הכורסה מתחת לאדן) | בעין, ובדגימת HSL של 3 נקודות מה-README |
| S3 | **פריטים מהשלבים הקודמים לא זזו ולא השתנו** | השוואה בעין, צד לצד |
| S4 | **נאמנות למוצר** ככל האפשר: צללית, פרופורציות, טקסטורה וגוון, מול הרפרנס | בעין, כל מוצר מול הרפרנס שלו; לרשום פער |
| S5 | **אין שום פריט שלא ברשימה:** בלי ספרים, פרחים, מגשים, כוסות, כריות נוספות, מראות, אנשים | ספירה |
| S6 | **אין טקסט, לוגו או תווית** (כולל התווית של השמיכה והאותיות מהשרטוט של התלויה) | בעין, בזום |
| S7 | **מיקום:** כל פריט חדש בתוך ±0.02 מהטבלה בסעיף 5 | מדידה על התמונה |
| S8 | **אור:** החלון נשאר הבהיר ביותר; צללים ימינה ולכיוון המצלמה; בלי צל ממנורות; בלי כתמי שמש | בעין, ובשלב C גם L של הקיר ליד החלון לא יורד |

**על התוצר הסופי (בנוסף):**
- הקבוצה על השולחן: בדיוק 3 פריטים בשליש הימני, ופס ריק במרכז.
- הפוף מתחת לתחתית משטח השולחן (C11), ולא נוגע בכורסה.
- הסל לא נוגע בספה (C14), ובסיס מנורת הרגל מוסתר.
- התמונה לא נוגעת בגב הספה (C9), והתלויה לא חופפת את התמונה (C8).
- הענפים, העץ והכרית במרווה, ולא בירוק רווי או כהה.

## 8. תוצרים ותיעוד
- `assets/renders/living-room/nordic/styled-preview/` (תיקייה חדשה): `step-a.png`, ‏`step-b.png`, ‏`step-c.png`, ‏`step-d.png` (‏2752×1548), ‏`raw/` (כפי ש-var2 החזיר), ‏`styled-preview.png` (הסופי, אחרי גריידינג אם נעשה), ‏`compare.jpg` (הבסיס מול הסופי), ו-`README.md` עם מודל, קרדיטים, task_id, placeholder_id, אורך כל פרומפט ותוצאות S1–S8.
- רשומות שחזור: `assets/prompts/styled-preview.nordic/step-{a,b,c,d}.json` (פרומפט מלא, URL-ים של הבסיס ושל כל רפרנס, הגדרות).
- **סימון חובה ב-README ובכל הצגה למשתמש:** "תצוגה מקדימה עם מוצרים זמניים. לא אישור 2, לא נכס לאתר."
- בלי 4K ובלי שכבות.

## 9. מה לא בבריף (החלטות של המשתמש, לא של render-agent)
- **שמיכה במרווה:** `sofa-cover-cj-washed-hemp-throw` (Tea Green) הייתה נותנת לספה נוכחות בצבע, אבל התמונות שלה כנראה שאולות, ולכן אי אפשר לרנדר אותה נאמנה. אם המשתמש רוצה לראות את הכיוון, אפשר לעשות וריאנט "קונספט, לא מוצר" של שלב A (עוד 400 קרדיטים, מעבר לתקרה) רק באישור מפורש.
- **הפוף, הווילון והשטיח:** המידות בתצוגה הן לפי ה-Bible ולא לפי המוצר (פוף 45 מול 50, וילון 280 מול 260, שטיח 230×330 במקום 240×290). צריך מוצרים מתאימים לפני אישור 2.

---

## 10. סבב 2 (גרסה 2.0, 2026-10-04)

> **מקור:** הערות המשתמש על `assets/renders/living-room/nordic/styled-preview/styled-preview.png`, מילה במילה: "הכד על השולחן מסתיר את הכריות שהן מוצר חשוב, הייתי מזיז אותו מתחת לחלון. חסר כיסוי ספה מעוצב לכל הספה חוץ מהכיסוי שבפינה, ממנורת קיר יוצא כבל עד הרצפה שנראה לא טוב עדיף שיהיה שקע צמוד למען העיצוב, התאורה קצת חיוורת, חסר מחזיק העיתונים, ואולי הייתי מוסיף עוד מנורות קיר טרוורטין קטנות"; ועל מנורת הקיר: "פשוט לשנות את אורך הכבל..זה הגיוני לא צריך מנורה חדשה". והערות render-agent ב-README של סבב 1.
> **מסמכים:** Design Bible נורדי **1.4**, ‏`data/slots/living-room.json` **1.3**, ‏`assets/blockout/living-room/v4-spec.json` (תוספות 1.4 בעמדות, ב-expected וב-C21–C22).
> **עדיין תצוגה מקדימה עם מוצרים זמניים. לא אישור 2, לא נכס לאתר.**

### 10.1 מה משתנה מול סבב 1
| # | שינוי | מה render-agent עושה |
| --- | --- | --- |
| 1 | **האגרטל עובר לאדן החלון** (הכנף האחורית). על השולחן נשארים שני פמוטים ונכנסת קערה נמוכה | שלב D. שום דבר על השולחן לא חופף כרית או את השמיכה (C21) |
| 2 | **כיסוי מלא לספה** (slipcover רפוי-מחויט, שיבולת שועל/פשתן). השמיכה נשארת, עכשיו בתוך סט הכריות | שלב A, מהבסיס הריק |
| 3 | **מנורת הקיר: אותו מוצר, כבל קצר לשקע צמוד.** שקע עיצובי בלבן חם בגוון הקיר, 18 ס"מ מתחת למרכז הפלטה; הכבל יורד ישר 6–12 ס"מ לתקע. **אין כבל לרצפה** | שלב C |
| 4 | **זוג מנורות קיר קטנות מטרוורטין** משני צדי התמונה, דולקות, הארת קיר למעלה ולמטה | שלב C |
| 5 | **אור חם יותר:** 15:00 בחורף, איזון לבן 4600K, המנורות **נראות דולקות** עם שלוליות | שלב C ונעילת צבע בכל שלב |
| 6 | **מחזיק עיתונים** בפינה השמאלית-קדמית | שלב D |
| 7 | **תיקונים מסבב 1:** תלויה קטנה וגבוהה, תמונה/שטיח/סל/אהיל מנורת הקיר בגודל הנכון, קבוצת השולחן לא במרכז, נעילת צבע נגד הסחף הוורוד | בכל שלב, סעיפים 10.4–10.5 |

### 10.2 תנאי התחלה (חוסם)
סבב 2 מתחיל **רק אחרי** ש-sourcing-agent מחזיר כרטיסים לפי `data/leads/cj/search-specs-2026-10-04.md`, ו-master-designer בוחר מוצר זמני לכל אחת מהעמדות החדשות ומוציא **נספח 10.8** עם ה-URL-ים והתיאורים שממלאים את הסוגריים המרובעים בפרומפטים. בלי מוצר אמיתי לכיסוי הספה ולמנורות הטרוורטין לא מרנדרים אותם (לא מוצר גנרי, כדי שהמשתמש לא יתאהב במוצר שלא קיים). מחזיק העיתונים והקערה: אם אין מועמד כשר, מושמטים ונרשמים ב-README, והסבב ממשיך.

### 10.3 מסלול ותקציב
- **בסיס:** שוב `m0/pilot-v4.1/m0-pilot-b-graded.png` (לא step-d של סבב 1): הספה מתלבשת מחדש, והתלויה, התמונה, השטיח והסל צריכים להיבנות מחדש בגודל הנכון. עריכה של step-d לא תקטין אותם באמינות.
- **ארבעה שלבים, עד 5 רפרנסים בכל אחד:**

| שלב | תוכן | רפרנסים | קרדיטים |
| --- | --- | --- | --- |
| A | כיסוי ספה, 3 כריות, שמיכה | 5 | 400 |
| B | שטיח, תמונה, וילונות, עציץ ועץ, סל | 5 | 400 |
| C | תלויה, מנורת קיר (ושקע), מנורת רגל, זוג טרוורטין; **אור אחר הצהריים והדלקת המנורות** | 4 (+1 מדריך מיקום בניסיון חוזר) | 400 |
| D | אגרטל על האדן, 2 פמוטים, קערה, פוף, מחזיק עיתונים | 5 | 400 |
| רזרבה | ניסיון חוזר אחד | — | 400 |
| **סה"כ** | | | **2,000 (תקרה, כמו בסבב 1)** |

- `var2_estimate_cost` לפני כל קריאה; עוצרים לפני שהמצטבר עובר 2,000.
- **ניסיון חוזר ראשון בשלב C** (אם התלויה שוב גדולה או נמוכה): מוסיפים תמונה 5 = **מדריך מיקום**: תוצר B עם מלבנים שקופים-למחצה בצבעים שונים (בלי טקסט) על התיבות מסעיף 10.6, ובפרומפט: "Image 5 is a placement guide only: put each item inside its box; never draw the boxes or their colours."

### 10.4 נעילת צבע (נגד הסחף הוורוד) — חובה בכל שלב
1. **בפרומפט** (בכל שלב, כבר כתוב בפרומפטים): "walls warm white, creamy, never pink, lilac or grey".
2. **אחרי כל שלב, לפני ההעלאה לשלב הבא:** מודדים את 4 הנקודות מה-README של סבב 1 (קיר אחורי (0.69, 0.22), קיר אחורי ימין (0.97, 0.31), מושב הכורסה (0.31, 0.75), שטיח (0.60, 0.93) מ-B ואילך). אם הקיר האחורי יצא מ-H 26–40 או שהכורסה ב-H<25 עם S>15: **איזון לבן גלובלי בלבד** (הגברים ליניאריים לערוצים, בלי שינוי בהירות, בשיטת שלב 1 של `grade.py`) שמחזיר את הקיר האחורי ל-H 30–36. **אני מאשר את האיזון הגלובלי הזה** (החריגה שהתבקשה בסבב 1). בלי תיקון מקומי, בלי אופרטור רוויה.
3. **יעדים בסוף:** קיר אחורי H 32–40 / S 15–28 / L 86–92; הכורסה H 25–60, ‏S≤15; השטיח H 30–45 (שיבולת שועל, לא ורדרד); הכיסוי בטווח של כרטיס המוצר.
4. רושמים את כל המדידות, לפני ואחרי, ב-README.

### 10.5 אור ומצב רוח
- **15:00, אחר צהריים מאוחר באמצע החורף,** חלון צפוני: בלי שמש ישירה, בלי כתמי שמש. השמיים בהירים-רכים, אור היום חם מעט יותר מבסבב 1 ונמוך ב-⅓ סטופ בעומק החדר, כך שהמנורות קוראות. **החלון עדיין הבהיר ביותר.** הצללים מהחלון: ימינה ומעט לכיוון המצלמה, רכים.
- **המנורות נראות דולקות:** האהילים זוהרים מבפנים (חמים, לא לבנים); שלולית חמה ברורה על הקצה הימני של הספה (מנורת הרגל, רדיוס כ-70), על הכתף והמושב של הכורסה (מנורת הקיר, כ-55), ועל מרכז השולחן (התלויה, כ-50). זוג הטרוורטין: פס אור רך וצר למעלה ולמטה על הקיר, לא נוגע במסגרות. **אין צל ממנורות, אין הילות, אין קרניים, אין נורה גלויה.**
- **גריידינג סופי (0 קרדיטים):** איזון לבן גלובלי (10.4), חשיפה עד ‎+0.2 סטופ (לא יותר; בסבב 1 החשיפה ונקודת השחור הגבוהה עשו את החדר "חלבי"), נקודת שחור L 12–13, עקומת S עדינה. בלי רוויה, בלי תיקון מקומי.

### 10.6 מיקום וקנה מידה (u, v; בסוגריים: ניסוח יחסי לפרומפט)
המודל מגדיל פריטים קטנים (README סבב 1, הערה 2). לכן בכל פריט: גם אחוזי פריים וגם **קנה מידה יחסי לרהיט קבוע**.

| פריט | תיבה | ניסוח יחסי |
| --- | --- | --- |
| תלויה | [0.595, 0.673, 0.052, 0.174] | רוחבה כשליש מאורך שולחן הקפה, צרה מכרית מושב אחת; תחתיתה גבוהה מעל ראש המסגרות, והקיר הפנוי ביניהם גבוה בערך כמו התלויה עצמה; כולה בחמישית העליונה של התמונה |
| תמונה | [0.598, 0.792, 0.281, 0.512] | כל מסגרת ברוחב כשלושה רבעים מכרית מושב; השורה כשלושה רבעים מרוחב הספה; תחתית המסגרות כחצי גובה מסגרת מעל גב הספה |
| טרוורטין שמאל / ימין | [0.562, 0.578, 0.332, 0.368] / [0.822, 0.840, 0.309, 0.352] | כל מנורה ברוחב כרבע ממסגרת אחת; הקצה העליון בקו העליון של המסגרות; כל אחת מעל קצה של הספה |
| מנורת קיר | פלטה (0.118, 0.372); שקע (0.117, 0.431) | אהיל קטן, ברוחב כשליש מרוחב הכורסה; השקע קטן, ריבוע בגוון הקיר, מתחת לפלטה |
| מנורת רגל | אהיל [0.856, 0.917, 0.381, 0.460] | האהיל ברוחב הסל |
| סל | [0.862, 0.924, 0.667, 0.797] | שפת הסל מעט מתחת לגובה מושב הספה; ברוחב כחצי מעומק כרית מושב |
| שטיח | פינה שמאלית-קדמית (0.27, 0.89) | רק שתי הרגליים הקדמיות של הכורסה עליו; שפתו הימנית עוברת מעט מימין לרגל הקדמית-ימנית של הספה |
| אגרטל על האדן | גוף [0.317, 0.337, 0.489, 0.560], ענפים u 0.286–0.352, עד v 0.427 | הגוף בגובה כשישית מגובה פתח החלון; עומד באמצע הכנף האחורית, לא נוגע בעמוד האמצעי ולא בעלוות הזית |
| פמוטים | בעמודה u 0.66–0.73 | ברווח שבין הכריות השמאליות לכרית המותן, במבט מהמצלמה |
| קערה | מרכז כ-(0.712, 0.72) | נמוכה, לפני הפמוטים ומימינם |
| פוף | [0.463, 0.558, 0.756, 0.947] | ראשו מתחת לשפה התחתונה של משטח השולחן |
| מחזיק עיתונים | [0.060, 0.137, 0.720, 0.899] | ראשו בערך בגובה מושב הכורסה; צמוד לקיר השמאלי, מתחת למנורת הקיר |

### 10.7 הפרומפטים (מילה במילה; את [הסוגריים] ממלא נספח 10.8)

#### שלב A: כיסוי ספה, כריות, שמיכה
תמונות: 1 בסיס, 2 sofa-cover, 3 boucle, 4 sage chenille, 5 muslin throw.
```text
Edit image 1, a finished photograph of a Scandinavian living room. Keep everything exactly as it is: camera, framing, walls, corner, window, cornice, skirting, oak floor, light, exposure, and the coffee table and armchair in the same position, size, colour and fabric. The sofa keeps exactly its position, size, low straight shape, square track arms, three seat and three back cushions and its visible oak legs. Only change what is listed below. Images 2-5 are product references: copy each product faithfully and take nothing else from them; ignore their rooms, furniture, props, labels and text.

1. SOFA SLIPCOVER (image 2): dress the whole sofa in the slipcover from image 2: [SLIPCOVER: colour, fabric, weave]. Relaxed tailored fit that follows the sofa's straight lines: square arms stay square, soft natural creases at the corners and along the front, separate covers on each seat and back cushion. The hem ends just below the sofa frame, so the oak legs stay fully visible. Matte, no shine, no stretch look, no skirt.

2. THROW (image 5): the warm white multi-layer cotton muslin throw, 150 x 200 cm, small waffle grid, natural crinkle, short frayed fringe. Loosely folded over the top of the right armrest, flowing across the front half of the right seat cushion and spilling over the seat edge in two or three deep soft folds. About the right fifth of the sofa. No label.

3. CUSHIONS, exactly three: Image 3: warm white looped boucle, 50 x 50 cm, upright at the left end in the corner of the arm and back cushion. Image 4: muted sage knitted chenille with a fine basket texture, 45 x 45 cm, in front of the boucle cushion, overlapping its lower right corner, tilted about 10 degrees. Charcoal linen-look slub lumbar, 30 x 50 cm, at the right end on the back half of the seat against the back cushion, just behind the throw and not covered by it. All plump, soft natural creases, matte.

Colour: walls warm white, creamy, never pink, lilac or grey. Natural colour, just below full saturation. Light unchanged; new items get soft shadows falling right and slightly toward the camera.

Do not add anything else. No text, logos or labels.
```
(בשלב A אין רפרנס לכרית הפחם, כדי לא לעבור 5. הכרית ממשיכה את התיאור; אם היא יוצאת לא נאמנה, הניסיון החוזר מחליף את תמונה 3 בכרית הפחם, והבוקלה מתוארת במילים.)

#### שלב B: שטיח, תמונה, וילונות, עציץ ועץ, סל
תמונות: 1 תוצר A, ‏2 rug, ‏3 framed-art, ‏4 curtains, ‏5 planter. (הסל עובר לכאן מ-C, בתיאור מילולי בלבד, כי הוא נאמן היטב בסבב 1; אם יוצא לא נאמן, הניסיון החוזר מחליף את תמונה 4.)
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, floor, daylight, exposure and white balance, and every item already in the room (dressed sofa, throw, three cushions, coffee table, armchair) in the same position, size, colour and folds. Only add the items below. Images 2-5 are product references: copy each faithfully and take nothing else from them; ignore their rooms, furniture, lamps, plants, people and text.

1. RUG (image 2): wool braided flat-weave rug, warm cream with heathered oatmeal yarns in soft tone-on-tone bands, never pink, square corners, no fringe, flat, matte. Under the coffee table, long side parallel to the sofa; the sofa's front legs on it, its back legs on the parquet. Its front-left corner is beside the armchair at 27% of the frame width and 89% of its height: only the armchair's two front legs stand on the rug. Its right edge passes a hand's width right of the sofa's right front leg. The front edge runs out of the bottom of the frame.

2. FRAMED ART (image 3): the three prints from image 3, same order, each 50 x 70 cm portrait in a thin matte black frame, 6 cm gaps. Each frame is about three quarters of one sofa seat cushion wide; the row is about three quarters of the sofa's width, centred above the sofa at 60% to 79% of the frame width and 28% to 51% of its height. The bottom of the frames is about half a frame height above the sofa back. Matte, no glare, no text.

3. CURTAINS (image 4): semi-sheer oatmeal hemp-linen with visible slub, pinch pleats on a slim matte black rod just below the cornice, drawn open into two narrow soft stacks beside the window, never over the glass, just touching the floor.

4. PLANTER (image 5): the honey seagrass belly basket, 35 cm wide, on the vertical corner line at 43% of the frame width, clear of the armchair, holding a young olive tree about 165 cm tall with an airy crown of silvery sage leaves, pale gravel, no soil.

5. BASKET: cylindrical coiled jute-rope basket, natural colour, two rope loop handles, empty. On the parquet just right of the sofa's right end with a narrow gap, at 86% to 92% of the frame width and 67% to 80% of its height. Its rim is a little below the sofa seat; it is about half as wide as a seat cushion is deep. The rug edge passes in front of its foot.

Colour: walls warm white, creamy, never pink, lilac or grey. Light unchanged; soft shadows to the right. No sun patches, no leaf shadows.

Do not add anything else: no lamps, mirrors, books or objects on surfaces. No text, logos or labels.
```

#### שלב C: מנורות, אור אחר הצהריים
תמונות: 1 תוצר B, ‏2 pendant, ‏3 wall-sconce, ‏4 accent-sconces. (מנורת הרגל במילים, כמו בסבב 1, כי הצללית שלה גנרית ממילא.)
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, window, curtains, and every item already in the room, unchanged in position, size, colour and shape. Only add the items below and change the light as described. Images 2-4 are product references: copy each faithfully and take nothing else from them; ignore their rooms, beds, people and text. Image 2 may be a dimension drawing: ignore its lettering and lines.

1. PENDANT (image 2): closed pleated warm white fabric lantern, flat pumpkin form, dense fine pleats, matte. It is small: its width is about one third of the coffee table's length, narrower than one sofa seat cushion. It hangs above the centre of the coffee table, high: the whole lantern is in the top fifth of the image, at 60% to 67% of the frame width, and its bottom is well above the top edge of the frames, with a band of clear wall between them about as tall as the lantern itself. A thin black cord rises straight out of the top of the frame.

2. WALL LAMP (image 3): the black swing-arm wall lamp with an oatmeal linen tapered shade. Plate on the left wall at 12% of the frame width and 37% of its height; the shade is small, about one third of the armchair's width, above and behind the armchair. Directly below the plate, a small flush square wall socket in the same warm white as the wall; a short straight black cord, a few centimetres, runs from the bottom of the plate into a plug in that socket. No cord below the socket, nothing running to the floor.

3. TRAVERTINE WALL LIGHTS (image 4): a matching pair of [ACCENT: shape, size] in honed light travertine with visible pores, matte. On the back wall, one on each side of the framed prints, each above one end of the sofa, at 56-58% and 82-84% of the frame width; the top of each lamp level with the top of the frames. Each is small, about a quarter of one frame's width. No cords.

4. FLOOR LAMP: slim matte black pole floor lamp with an oatmeal linen drum shade as wide as the basket, just right of the sofa's right end behind the basket; shade at 86% to 92% of the frame width and 38% to 46% of its height; base hidden by the basket.

Light: late winter afternoon, about 3 pm, north-facing window, no direct sun. Daylight from the window is soft and slightly warmer, the room a little dimmer away from the window; the window stays the brightest area. All lamps are switched on and clearly lit with warm 2700 K light: shades glow from within; a warm pool on the right end of the sofa, a warm pool on the armchair's shoulder and seat, a soft warm wash on the centre of the coffee table; each travertine lamp throws a soft narrow wash up and down the wall, not touching the frames. No lamp shadows, no visible bulbs, no glare, halos or beams. Walls warm white, creamy, never pink, lilac or grey.

Do not add anything else. No text, logos or labels.
```

#### שלב D: אגרטל על האדן, פמוטים, קערה, פוף, מחזיק עיתונים
תמונות: 1 תוצר C, ‏2 vase, ‏3 candle-holders, ‏4 bowl, ‏5 magazine-holder. (הפוף במילים, כמו בסבב 1.)
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, the late-afternoon light, every lit lamp and its glow, exposure, white balance, and every item already in the room, unchanged in position, size, colour and shape. Only add the items below. Images 2-5 are product references: copy each faithfully and take nothing else from them; ignore their backgrounds, flowers, props and text.

1. VASE ON THE WINDOW SILL (image 2): [VASE: description], about one sixth of the window opening's height. It stands on the window sill in the middle of the back casement, at about 33% of the frame width, its foot on the sill, clear of the mullion and of the olive tree. In it: three or four slender eucalyptus stems with round silvery sage leaves, airy, leaning slightly left, reaching about twice the vase's height. Its face is softly lit by the room and reads as matte textured ceramic, not a dark silhouette; the window behind it stays brighter. Nothing else on the sill.

2. CANDLE HOLDERS (image 3): two light travertine pedestal holders, 7 cm wide and 11 cm tall, each with an unlit warm white pillar candle 7 cm wide, one 15 cm and one 10 cm tall, flat tops and short white wicks. On the coffee table, standing in the gap between the left cushions and the charcoal lumbar cushion as seen from the camera, at 66% to 73% of the frame width; they must not overlap any cushion or the throw.

3. BOWL (image 4): [BOWL: description], low, in front of and right of the candle holders, forming a triangle with them. The left half of the table stays empty bare oak.

4. POUF: round chunky-knit cotton pouf in natural off-white, a flat ball 45 cm wide and 36 cm high, plump, on the rug in front of the armchair at 46% to 56% of the frame width; its top below the lower edge of the table top.

5. MAGAZINE HOLDER (image 5): [HOLDER: description], holding three upright A4 magazines in matte warm white, oatmeal and light grey covers with no text. On the parquet in the front-left corner, against the left wall under the wall lamp, facing the camera, at 6% to 14% of the frame width and 72% to 90% of its height; its top about at the height of the armchair seat.

Light unchanged. New items: soft shadows falling right and slightly toward the camera, short soft contact shadows. No candle flames. Walls warm white, never pink.

Do not add anything else: no books, trays, cups, fruit or extra flowers. No text, logos or labels.
```

### 10.8 נספח מוצרים (יוצא אחרי ה-sourcing)
טבלה כמו בסעיף 3 לכל עמדה חדשה (sofa-cover, accent-sconces, vase אם מוחלף, bowl, magazine-holder), עם הטקסט לכל [סוגריים]. העמדות שלא השתנו משתמשות באותם מוצרים ו-URL-ים כמו בסעיף 3.

### 10.9 תנאי קבלה (S1–S8 מסבב 1 בתוקף, ובנוסף)
| # | תנאי | איך |
| --- | --- | --- |
| S9 | **נעילת צבע:** אחרי כל שלב הקיר האחורי ב-H 26–40 לפני תיקון ו-30–36 אחרי; בסוף 32–40 / S 15–28; הכורסה H≥25, ‏S≤15; השטיח H 30–45 | דגימה בנקודות 10.4, רישום ב-README |
| S10 | **המנורות נראות דולקות:** כל אהיל בהיר מהקיר שסביבו ב-L≥3 ובגוון חם; שלוליות נראות על הספה, על הכורסה ועל השולחן; פס אור משתי מנורות הטרוורטין; החלון עדיין הבהיר ביותר | בעין, ו-L בדגימה |
| S11 | **מנורת הקיר:** שקע בלבן חם מתחת לפלטה, כבל ישר קצר, **שום כבל מתחת לשקע** | בעין, בזום |
| S12 | **C21:** שום פריט על השולחן לא חופף כרית או את השמיכה | בעין |
| S13 | **C22:** הטרוורטין ≥0.02 מהתמונה ומאהיל מנורת הרגל; האגרטל וענפיו ≥0.02 מהעמוד האמצעי ומעלוות הזית; רק האגרטל על האדן | מדידה |
| S14 | **קנה מידה:** התלויה, התמונה, הסל, אהיל מנורת הקיר והשטיח בתוך ±0.02 מהתיבות ב-10.6 (בסבב 1 כולם נכשלו כאן) | מדידה |
| S15 | **כיסוי הספה:** הקווים הישרים והמשענות הריבועיות של הספה נשמרו, רגלי האלון גלויות, בלי ברק ובלי מראה מתיחה; הגוון והבד כמו בכרטיס | בעין, מול הרפרנס |

**תוצרים:** `assets/renders/living-room/nordic/styled-preview/round-2/` (אותו מבנה כמו בסבב 1), ‏`compare-r1-r2.jpg` (סבב 1 מול סבב 2), רשומות ב-`assets/prompts/styled-preview.nordic/round-2/`.
