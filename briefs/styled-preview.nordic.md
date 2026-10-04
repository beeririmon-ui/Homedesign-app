# בריף רינדור: תצוגת סטיילינג, סלון נורדי (B, ‏v4.1)

> master-designer, 2026-10-04. גרסה 1.0. ל-render-agent.
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
