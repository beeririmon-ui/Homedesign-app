# תצוגת סטיילינג, סלון נורדי (B, v4.1)

> **תצוגה מקדימה עם מוצרים זמניים. לא אישור 2, לא נכס לאתר.**
> render-agent, 2026-10-04. בריף: `briefs/styled-preview.nordic.md` 1.0. בסיס: `m0/pilot-v4.1/m0-pilot-b-graded.png`.

## קבצים
| קובץ | מה |
| --- | --- |
| `step-a.png` … `step-d.png` | תוצר כל שלב, 2752×1548 (מ-2752×1536 של var2, Lanczos, בלי חיתוך) |
| `styled-preview.png` | הסופי: step-d אחרי גריידינג גלובלי אחד |
| `before-after.jpg` | המאסטר הריק מול התצוגה המעוצבת |
| `raw/step-*.jpg` | מה ש-var2 החזיר. `raw/step-*-check.json` מדידות. `raw/rejected/step-c-take2.jpg` הניסיון החוזר שנדחה |
| `check.py`, `grade.py` | מדידה וגריידינג |
| `assets/prompts/styled-preview.nordic/` | רשומות שחזור: step-a..d, styled-preview-graded |

## מודל, עלות ומזהים
מודל: var2 nano-banana-2, image-to-image, 2K, 16:9, בלי seed (המודל לא חושף). הערכה מראש (`var2_estimate_cost`): 400 לקריאה.

| שלב | רפרנסים | placeholder_id | task_id | קישור | קרדיטים |
| --- | --- | --- | --- | --- | --- |
| A | 5 | 03e850a1-0053-486d-b224-d9e9a188d634 | 51faaefe468cf7bc498388a6d31b5b70 | https://www.var2.ai/image/03e850a1-0053-486d-b224-d9e9a188d634 | 400 |
| B | 3 | 24282c05-2a99-40a2-9357-9a9e1f114a4f | d5d9c0528b42b12f6fedbccca3ec2bd6 | https://www.var2.ai/image/24282c05-2a99-40a2-9357-9a9e1f114a4f | 400 |
| C (נבחר, ניסיון 1) | 4 | f0c1df25-6811-4b3d-8e1e-400ef23e0c82 | 982aa22f0eaff976d636df25b7232fba | https://www.var2.ai/image/f0c1df25-6811-4b3d-8e1e-400ef23e0c82 | 400 |
| C ניסיון חוזר (נדחה) | 4 | bc92ecc5-0f97-44cd-8621-2742424c0604 | 5b957fa74d1ea993e4ec6a112c034732 | https://www.var2.ai/image/bc92ecc5-0f97-44cd-8621-2742424c0604 | 400 |
| D | 3 | 46172937-6cfb-47a4-b85c-17738bf704a9 | 2bd04c912dfd98da4fe8440dc48835a7 | https://www.var2.ai/image/46172937-6cfb-47a4-b85c-17738bf704a9 | 400 |
| גריידינג | — | — | — | — | 0 |
| **סה"כ** | | | | | **2,000 (בדיוק התקרה)** |

כל קלט הועלה דרך `var2_request_upload` ו-PUT, וה-sha256 של ההורדה חזרה זהה למקומי (בסיס, step-a, step-b, step-c). URL-ים מלאים ברשומות ה-JSON. הרפרנסים הם ה-URL-ים מהבריף, כפי שהם, בסדר שבפרומפט.

## גריידינג (קריאה אחת, גלובלית)
`grade.py`: (1) **איזון לבן גלובלי** (הגברים ליניאריים R 0.928, G 1.027, B 0.988, בלי שינוי בהירות) שמחזיר את הכרומטיות של כתם הקיר האחורי לזו של המאסטר; (2) חשיפה +0.21 סטופ; (3) כתף הבהרות כמו בפיילוט; (4) נקודת שחור 0.12. בלי אופרטור רוויה, בלי תיקון מקומי.
**חריגה שצריך לאשר:** הבריף מתיר חשיפה ונקודת שחור בלבד. הוספתי איזון לבן גלובלי, כי ארבע העריכות המשורשרות צברו הטיה ורודה (גוון הקיר האחורי ירד מ-28.7° ל-3.0°, הכורסה ל-357°). בלי זה החדר נראה ורוד ולא נורדי. אם לא מאשרים, הרצה של `grade.py` בלי שלב 1 מפיקה את הגרסה הצמודה לבריף.

| נקודה (H/S/L) | מאסטר | step-d | סופי |
| --- | --- | --- | --- |
| קיר אחורי (0.69, 0.22) | 28.7/26.9/90.5 | 3.0/17.4/81.2 | 23.4/13.0/85.0 |
| קיר אחורי ימין (0.97, 0.31) | 29.7/25.1/84.6 | 14.1/27.9/81.7 | 28.9/27.1/86.7 |
| גב הספה (0.70, 0.60) | 30.9/34.2/83.4 | 19.5/38.4/80.3 | 29.5/39.4/85.1 |
| מושב הכורסה (0.31, 0.75) | 23.8/14.5/79.9 | 356.7/31.1/87.4 | 12.2/23.9/90.6 |
| חלון L p50 / p99 | 95.9 / 98.4 | 96.5 / 99.6 | 94.7 / 96.1 |
| שטיח (0.60, 0.93) | (פרקט) | 15.6/53.1/85.6 | 25.2/44.8/87.3 |

הכורסה והשטיח נשארים מעט ורדרדים גם אחרי הגריידינג (הסטייה שם מקומית, ולא תיקנתי מקומית).

## S1–S8 לפי שלב
הזזות מול המאסטר (קורלציית גרדיאנט, ±14 פיקסלים), du/dv כחלק מהפריים. הקורלציה יורדת משלב לשלב כי נוספים פריטים, ולכן המדד העיקרי הוא ההזזה של אזורי הרהיטים והמסגרת.

| | A | B | C | D |
| --- | --- | --- | --- | --- |
| **S1 גאומטריה** | עובר. מסגרת dv 0.0019, פינה du 0.0044, ספה/שולחן/כורסה ≤0.0019 | עובר בגבול. מסגרת dv 0.0032; פינה dv 0.009 ו-חלון dv -0.0065, אבל זה הווילון והמוט שנכנסו לאזור המדידה. בעין הפינה, הכרכוב, החלון והקורה האמצעית במקום | עובר בגבול. מסגרת/ספה/שולחן dv 0.0045 | **נכשל בגבול.** הזזה אנכית גלובלית מצטברת dv 0.0058 (מסגרת, ספה, כורסה), שולחן 0.0065. בעין השולחן והספה במקומם (השוואה צד לצד) |
| **S2 רהיטים קבועים** | עובר. צורה ובד זהים; גוון זז ~4° לוורוד | עובר. סחף גוון ממשיך (כורסה H 6°) | עובר בצורה, סחף גוון (גב ספה 22.6°) | עובר בצורה; גוון: ראו גריידינג |
| **S3 פריטים קודמים** | — | עובר | עובר (השטיח מוורד) | עובר; הכרית במרווה מוסתרת חלקית מאחורי האגרטל |
| **S4 נאמנות** | ראו טבלה למטה | ראו למטה | ראו למטה | ראו למטה |
| **S5 בלי פריטים זרים** | עובר | עובר (חצץ בעציץ לפי הבריף) | עובר | עובר |
| **S6 בלי טקסט** | עובר (אין תווית בשמיכה) | עובר | עובר (אין אותיות מהשרטוט) | עובר |
| **S7 מיקום ±0.02** | **נכשל:** פינת השטיח ב-(0.17, 0.91) במקום (0.27, 0.89); השטיח גדול שמאלה, כל ארבע רגלי הכורסה עליו. שמיכה וכריות במקום | **נכשל:** השלישייה ב-u 0.53–0.86, v 0.24–0.47 (בריף 0.598–0.792, 0.281–0.512): גדולה בערך פי 1.4 וזזה שמאלה. עציץ: מרכז ~0.45 (בריף 0.431). וילון קדמי רחב, לא ערימה צרה | **נכשל:** תלויה ב-u ~0.51–0.63, v ~0.19–0.32 (בריף 0.595–0.673, 0.052–0.174), גדולה ונמוכה ו**מסתירה את ראש ההדפס השמאלי (C8 נכשל)**. מנורת קיר: פלטה ב-u ~0.02–0.05 (בריף 0.118), אהיל גדול. מנורת רגל: אהיל ~0.86–0.93, ~0.33–0.42 (גבוה מעט). סל ~0.855–0.94, ~0.69–0.88, גדול מהמפרט; לא נוגע בספה, בסיס המנורה מוסתר | **נכשל:** קבוצת השולחן במרכז-שמאל (u ~0.57–0.70), לא בשליש הימני; אין פס ריק במרכז. פוף ב-u ~0.385–0.525 (בריף 0.463–0.558), החלק העליון בערך בקו תחתית משטח השולחן (C11 בגבול), לא נוגע בכורסה |
| **S8 אור** | עובר | עובר | חלקי. החלון הבהיר ביותר; המנורות "דולקות" רק בקושי (זוהר חלש באהילים, בלי שלוליות אור), בלי צל ממנורות | עובר |

**ניסיון חוזר:** נוצל על שלב C (תלויה שמסתירה את התמונה, ענקית). שני הניסיונות נכשלו באותה צורה, כלומר זו בעיה בפרומפט או במודל, ולא דגימה רעה. בניסיון החוזר גם הסל עמד על השטיח ונגע בשמיכה, ובסיס מנורת הרגל נראה, ולכן נבחר ניסיון 1. ב-D לא נשאר תקציב לניסיון חוזר.

## נאמנות למוצר (מול הרפרנס)
| עמדה | מה תואם | מה סטה |
| --- | --- | --- |
| rug | קליעה שטוחה עבה, פסים טון-על-טון, בלי פרנזים, פינות ישרות | הגוון מוורד (קרם-ורדרד במקום קרם-שיבולת שועל) גם אחרי הגריידינג; גדול שמאלה מהמעטפת |
| sofa-cover | גריד ופל, קמטוטים, פרנזים קצרים, לבן חם, נפילה בקפלים עמוקים על המשענת ועל המושב: מצוין | כמעט כלום. גולש מעט עד הרצפה |
| cushions (בוקלה) | לולאות, לבן חם, 50, זקופה בפינה | — |
| cushions (שניל מרווה) | מרווה עמומה, טקסטורת סל | לא מוטה ב-10°; ב-D מוסתרת חלקית מאחורי האגרטל |
| cushions (פחם) | פחם, סלאב, כרית מותן | — |
| framed-art | שלושת ההדפסים בדיוק כמו בעיצוב ובסדר הנכון, מסגרות שחורות דקות | גודל ~70×100 במקום 50×70; התלויה מסתירה את ראש ההדפס השמאלי |
| curtains | פשתן חצי-שקוף עם סלאב, מוט שחור דק, נוגע ברצפה, הזכוכית פנויה | גוון אפור-טאופ ולא שיבולת שועל; הלוח הקדמי רחב (לא ערימה צרה); הכיווץ נראה כמו קפלי עיפרון יותר מקפלי צביטה |
| planter | סל קש ים בצורת בטן, ידיות, אריגה, דבש טבעי | — (עץ הזית יפה ואוורירי, במרווה) |
| pendant | צורת דלעת שטוחה עם קפלים צפופים, לבן חם, כבל שחור, בלי אותיות | **בערך פי 1.6 מ-40 ס"מ**, תלוי נמוך מדי, חופף את התמונה |
| wall-sconce | פלטה שחורה, זרוע מתקפלת, אהיל פשתן מחודד, כבל יורד ישר | אהיל גדול מהמוצר; ממוקם קרוב לשולי הפריים |
| floor-lamp | עמוד שחור דק, תוף פשתן | צללית גנרית (כמו שהבריף ביקש); גבוה מעט |
| basket | חבל יוטה מגולגל, גלילי, שתי ידיות לולאה, ריק | גדול מ-35 ס"מ ביחס לספה |
| vase | צורת כד עם פה קטן, טקסטורת אבן מקומטת, לבן חם: תואם היטב | במרכז השולחן ולא בשליש הימני; הענפים צפופים יותר מ"4–5 ענפים" |
| candle-holders | טרוורטין בהיר עם נקבוביות, רגל ושקע, נרות לא דולקים 15 ו-10 | הצללית מעט יותר מחודדת מהרפרנס (שהוא עמודי יותר) |
| pouf | סריגה עבה, לבן-טבעי (לא הירוק של התמונה), עגול ומלא | זז שמאלה; גובה בגבול מול תחתית השולחן |

## הפרומפטים, מילה במילה
ספירה ב-`len()` בפייתון (כולם ASCII, כולל שורות ריקות): A 3129, B 2957, C 2961, D 2488. כולם מתחת ל-3,800 (בריף) ול-4,000 (var2). הניסיון החוזר של C נשלח עם אותו פרומפט בדיוק.

### A (3129 תווים). תמונות: 1 בסיס, 2 rug, 3 sofa-cover, 4 boucle, 5 sage, 6 charcoal
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

### B (2957 תווים). תמונות: 1 step-a, 2 framed-art, 3 curtains, 4 planter
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, floor, daylight, exposure and white balance, and every piece of furniture and textile already in the room (sofa, coffee table, armchair, rug, throw, three cushions) in the same position, size, colour and folds. Move, resize or restyle nothing. Only add the items listed below. Images 2-4 are product references: copy each product faithfully and take nothing else from them; ignore their rooms, furniture, lamps, plants, people and text.

1. FRAMED ART (image 2): the three framed abstract prints from image 2, exactly as designed and in the same left-to-right order: sage arches above a dotted arch and a small sage dot; beige, sage and pale grey brush blocks; a sage organic shape with thin dark circular lines. Each print 50 x 70 cm portrait in a thin matte black frame, hung in a row with 6 cm gaps, 162 cm wide in total, on the back wall centred above the sofa, the centre of the row 147 cm above the floor. The row spans about 60% to 79% of the frame width and 28% to 51% of its height; its bottom is clearly above the sofa back. Flat, level, following the wall's perspective. Matte print, no glare, no reflections, no text, no signature. A thin soft daylight shadow under each frame.

2. CURTAINS (image 3): two panels of semi-sheer hemp-linen in natural oatmeal, strong visible slub, matte, daylight glowing through. Pinch-pleat heading on a slim matte black rod, mounted 12 cm below the cornice and 20 cm wider than the window opening on each side. Both panels are drawn open into narrow soft stacks, one beside the window's back jamb near the corner and one beside its front jamb, covering the wall and the edge of the reveal but never the glass. They fall straight in soft vertical folds and just touch the floor. The glass, the mullion and the garden view stay fully visible.

3. PLANTER WITH OLIVE TREE (image 4): the natural woven seagrass belly basket from image 4, 35 cm wide and 37 cm high, warm honey colour, herringbone weave, used as a floor pot in the back-left corner of the room. Its centre sits exactly on the vertical corner line at about 43% of the frame width, close to the walls, just right of the armchair with a clear narrow gap between them. In it: a young olive tree with one slender grey-brown trunk, about 165 cm tall including the pot, and an airy medium-density crown about 70 cm wide of narrow silvery sage-green leaves. The crown fills the corner between the back curtain stack and the wall left of the sofa, and stays clear of the framed art. Pale gravel top-dressing, no visible soil, no saucer.

Light: the same 10:30 winter daylight from the left window as image 1. New items cast soft shadows falling right and slightly toward the camera. No sun patches, no leaf shadows, no new light sources.

Do not add anything else: no lamps, mirrors, extra plants, shelves, wall decor, books or objects on surfaces. No text, logos or labels.
```

### C (2961 תווים). תמונות: 1 step-b, 2 pendant, 3 wall-sconce, 4 floor-lamp, 5 basket
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, floor, window, curtains, daylight direction, exposure and white balance, and every item already in the room (sofa, coffee table, armchair, rug, throw, cushions, framed art, olive tree in its basket), unchanged in position, size, colour and shape. Only add the items below. Images 2-5 are product references: copy each faithfully and take nothing else from them; ignore their rooms, beds, people and text. Image 2 is a dimension drawing: ignore its lettering, lines and arrows.

1. PENDANT (image 2): closed pleated fabric lantern, a flat pumpkin form 40 cm wide and 25 cm high, dense fine vertical pleats gathered into soft segments, warm white, matte. Not the egg-shaped model. A thin black cord rises straight up and out of the top edge of the frame. It hangs above the centre of the coffee table, its bottom 2.20 m above the floor, at about 60% to 67% of the frame width and 5% to 17% of its height, with clear wall between it and the framed art.

2. WALL LAMP (image 3): plug-in swing-arm wall lamp: small rectangular matte black wall plate, folding two-section matte black arm, tapered drum shade in oatmeal linen with a visible weave. On the left wall near the camera, the plate at about 12% of the frame width and 37% of its height, 1.47 m above the floor. The arm reaches about 40 cm out from the wall; the shade sits above and behind the armchair, well above its back. A black fabric cord falls straight down from the plate to the skirting, no loops.

3. FLOOR LAMP (image 4): slim straight matte black pole floor lamp with an oatmeal linen drum shade 36 cm wide and 30 cm high, 155 cm tall overall. It stands just right of the sofa's right end, close to the back wall; the shade at about 86% to 92% of the frame width and 38% to 46% of its height, touching neither the wall nor the frame edge. Its base is hidden behind the basket.

4. BASKET (image 5): cylindrical coiled-rope basket in natural jute colour, 35 cm wide, 39 cm body, two rope loop handles rising about 9 cm. On the parquet just right of the sofa's right end with a narrow clear gap, in front of the lamp base, at about 86% to 92% of the frame width and 67% to 80% of its height. The rug's edge passes in front of its foot, with the basket's own soft contact shadow on the parquet. Empty.

Lighting: still a bright 10:30 winter morning lit by the window, which stays the brightest area in the frame. Switch on all three lamps at a low, cosy level with warm 2700 K light: each shade glows softly from within; the floor lamp leaves a small warm pool on the right end of the sofa; the wall lamp a small warm pool on the armchair's back and seat; the pendant a faint warm wash on the centre of the coffee table. The lamps cast no visible shadows, no bulb is visible from the camera, no glare, flare, halos or beams. Daylight shadows stay as in image 1.

Do not add anything else. No text, logos or labels.
```

### D (2488 תווים). תמונות: 1 step-c, 2 vase, 3 candle-holders, 4 pouf
```text
Edit image 1. Keep everything in it exactly as it is: camera, framing, architecture, daylight, the three lit lamps and their glow, exposure, white balance, and every item already in the room, unchanged in position, size, colour and shape. Only add the items below. Images 2-4 are product references: copy each faithfully and take nothing else from them; ignore their backgrounds, flowers, props and text.

Coffee table: one group of exactly three objects in the right third of the table top, standing on the bare oak. The left two thirds of the table stay completely empty.
1. VASE (image 2): the textured stoneware vase from image 2, 32 cm tall and 16 cm wide, a soft jar shape with a small mouth, warm white, matte, with a fine crinkled stone-like texture all over and a smooth rim. At the back of the group, toward the sofa, about 20 cm in from the table's right end. In it: four or five slender olive branches with narrow silvery sage-green leaves, loose and airy, the tallest about 60 cm above the table top, leaning slightly left; they may pass lightly in front of the lower edge of the framed art.
2. CANDLE HOLDERS (image 3): two identical light travertine pedestal holders, a cone foot with a small cup on top, 7 cm wide and 11 cm tall, honed matte, natural pores and soft horizontal veins. In front of and slightly right of the vase, 8 cm apart, forming a triangle with it. Each holds an unlit warm white pillar candle 7 cm wide with smooth straight sides, a flat top with a crisp edge and a short upright white wick: a 15 cm candle in the holder nearer the vase, a 10 cm candle in the other. The heights step down: branches, vase, tall candle, short candle.

3. POUF (image 4): round chunky-knit cotton pouf in natural off-white, a flat ball 45 cm wide and 36 cm high, plump and firmly filled, thick knit texture, rounded top. On the rug in front of the armchair and left of the coffee table, at about 46% to 56% of the frame width and 76% to 95% of its height. Its top stays below the lower edge of the table top behind it; clear rug between it and the armchair, the table and the bottom edge of the frame.

Light: unchanged. The new items catch the window light from the left, with soft shadows falling right and slightly toward the camera and short soft contact shadows; the pendant adds only a faint warm glow on the table. No candle flames.

Do not add anything else: no books, trays, bowls, cups, fruit, magazines, table runner or extra flowers. No text, logos or labels.
```

## הערות להמשך (לא בוצעו)
1. **סחף צבע בשרשור:** כל עריכה מוסיפה הטיה ורודה. בעבודה סופית עדיף פחות שלבים משורשרים, או לנעול צבע מול המאסטר אחרי כל שלב.
2. **קנה מידה:** המודל מגדיל פריטים קטנים (תלויה, אהילים, סל, תמונות). מידות בס"מ ובאחוזי פריים לא מספיקות; כנראה צריך קנה מידה יחסי ("רוחב התלויה כשליש מרוחב השולחן") או מסכה/סקיצת מיקום.
3. **תלויה מול התמונה:** בשני הניסיונות התלויה ירדה לגובה התמונה. כדאי לנסח מחדש (למשל "the pendant's bottom is above the top edge of the frames") או להזיז את התמונה.
