# פרומפט מאסטר M0 — סלון נורדי (מעטפת ורהיטים קבועים)

> master-designer. **גרסה 2.0, 2026-10-04: גאומטריה B** (החלטת משתמש 2026-10-03: "B נראה הכי הגיוני..בא נתקדם איתה"). מחליפה את 1.0–1.3 (מבט ישר בחדר 3.70×6.90), שנשמרות ב-git. **גרסה 2.1, 2026-10-04:** אזור שמאל L2 (אישור משתמש: "מאושר"): אדן 0.75, כורסה ב-(−1.27, 2.82) בגובה 70; ה-[L] הוחלף בטקסט קבוע (`review-designer.md` 8.7).
> **מקור הנתונים:** `docs/design-bible/nordic.md` 1.3.1, ‏`docs/skeleton-spec.md` (עדכון ד'), ‏`data/slots/living-room.json` 1.2.1, ‏`assets/blockout/living-room/v4-spec.json` v4.1. לקחי הפיילוט הראשון: `assets/renders/living-room/nordic/m0/pilot/README.md`.
> **מה ב-M0:** מעטפת ו-3 רהיטים קבועים בלבד. אין מוצרים מתחלפים, אביזרים, שטיח או מנורות.
> **חסימה:** **אין קרדיטים עד ש-master-designer בודק את ה-clay של v4.1** (כל הבדיקות החוסמות עוברות, כולל C5 מול האדן). ה-clay של v4 L2 נכשל ב-C5 ולא משמש קלט.

## 1. בקצרה
| פרמטר | ערך |
| --- | --- |
| מודל | nano-banana-2, image-to-image על ה-clay של v4.1 (L2). גרסה חלופית: טקסט בלבד (סעיף 5) |
| יחס ורזולוציה | 16:9. **var2 מחזיר 2752×1536 (וב-4K כנראה 5504×3072), יחס 1.792.** מחזירים ל-16:9 בשינוי גודל לא אחיד (0.8% אופקית), **לא בחיתוך**: התוכן מתוח לכל המסגרת, וכך היישור מול ה-clay מדויק. אחר כך topaz ×2 והקטנה ל-6144×3456 |
| אורך פרומפט | **מגבלה של var2: ‏4,000 תווים.** שני הפרומפטים כאן עד 3,900 (בדיקה לפני שליחה, לפי מונה תווים; אם עובר, מקצרים את "Finish" ולא שום מידה) |
| רפרנסים | רק ה-clay, בלי רינדורים קודמים ובלי לוח דוגמיות |
| ניסיונות | פיילוט 2K: 2 עם clay ו-1 טקסט. אחר כך 3 ב-4K במסלול שניצח |
| תיעוד | `assets/prompts/m0.nordic/` (פרומפט, קלט עם sha256, מודל, מזהים, קרדיטים) |

## 2. גאומטריה (מקור לבלוק-אאוט, לפרומפט ול-QA)
מערכת צירים ומשוואות ההטלה: `v4-spec.json` (`conventions`). X ימינה, Y מהקיר האחורי למצלמה, Z למעלה.

| רכיב | ערך |
| --- | --- |
| חדר | קיר שמאל X=−2.30, ימין X=+2.50, אחורי Y=0, קדמי Y=6.20, תקרה 3.00. כרכוב 10, שיפולים 15, בצבע הקיר |
| פתח כניסה | קיר קדמי, X 0.95–2.15, ‏2.40, דלת כפולה פתוחה. לא בפריים |
| חלון | קיר שמאל, Y 0.90–2.70, **אדן 0.75** (היה 0.45), ראש 2.70. ספי עומק 0.35, מסגרת במישור החיצוני (X −2.65), עמוד 6 ס"מ ב-Y 1.80, אדן פנימי צבוע |
| פרקט | לוחות 25 ס"מ באורך 3–4 מ', לאורך Y |
| ספה | X −0.90…+1.30, ‏Y 0.03–0.95 (220×92, משענת 0.78, מושב 0.44, משענות 0.60/14) |
| שולחן | מרכז (0.20, 1.72), ‏140×70×38 |
| כורסה | **(−1.27, 2.82)**; ‏25° (`yaw_deg=-25`), משענות עד +0.3525. 72×78, **גובה 70**, מושב 40: כרית גב באורך 0.345 (ראש 0.690), עמודי גב 0.39 (ראש 0.642) |
| מצלמה | (1.25, 5.55, 1.20), מסובבת 25° שמאלה, 24 מ"מ (חיישן 36×20.25), ‏tilt 0, roll 0, ‏shift_x ‎−0.020, ‏shift_y ‎−0.0225 → ‏(u0, v0) = (0.52, 0.46). הפינה האחורית-שמאלית ב-u 0.431 (0.61 = סימן הפוך) |

### 2.1 איפה דברים נופלים בפריים (חור-סיכה, נבדק מול selfcheck של B)
| רכיב | u | v |
| --- | --- | --- |
| פינה אחורית-שמאלית (אנכי) | 0.431 | — |
| רצועת תקרה | טריז: 0.133 בפינה, 0.070 מעל התמונה, כ-0 בשפה הימנית | — |
| קיר החלון | 0–0.431, גלוי עד Y 3.74 | — |
| פתח החלון (מישור הקיר) | 0.191–0.374 | ראש 0.025–0.149, אדן 0.553–0.591 |
| עמוד החלון (מישור המסגרת) | 0.259–0.266 | — |
| ספה | 0.521–0.840 | 0.548–0.799 |
| שולחן | 0.512–0.762 | — |
| כורסה | 0.190–0.387 | 0.622–0.906; כל הגב ≥0.02 מתחת לקו האדן |
| בדיקה (overlay בלבד): תמונה / תלויה | 0.598–0.792 / 0.595–0.673 | 0.281–0.512 / 0.052–0.174 |
| בדיקה: עציץ (כלי) / קישוט קיר | 0.410–0.452 / 0.508–0.563 | — / 0.353–0.461 |
| בדיקה: פוף / מחזיק עיתונים | 0.463–0.558 / 0.060–0.137 | 0.756–0.947 / 0.720–0.899 |
| בדיקה: סל / אהיל מנורת רגל | 0.862–0.924 / 0.856–0.917 | 0.667–0.797 / 0.381–0.460 |
| בדיקה: מנורת קיר | 0.118 | 0.372 |

**קומפוזיציה:** מבט פינתי. שמאל: קיר החלון, האור והכורסה. ימין: קיר הספה, והתמונה על קו השליש (u≈0.695). ב-M0 לבד הימין העליון ריק (התמונה והתלויה עוד לא שם). זה מכוון, ו-QA לא פוסל על איזון.

## 3. הבלוק-אאוט (תמונת הקלט)
לפי `v4-spec.json`. clay אפור אחיד, רצפה מעט כהה יותר, אור שמיים דרך החלון בלבד. ‏3840×2160: ‏`m0-clay.png`, עומק, קווים, מצלמה, `plan.png` ו-overlay. master-designer מאשר את ה-clay (כולל בדיקות C4–C17) לפני כל קרדיט.

## 4. הפרומפט הראשי (image-to-image על ה-clay; 2.1: כ-3,500 תווים, ספירה לפי מילים ורווחים, כולל שורות ריקות)
```text
Use the attached grey clay render as the exact layout and camera. Keep every wall, the corner, the window opening and its deep reveals, cornice, skirting, floor and ceiling lines, camera height, lens and angle, and the position, size and angle of the three furniture pieces exactly as in the render. Move, resize, add or remove nothing. Only replace the clay with real materials and real daylight.

Photorealistic editorial interior photograph, top design-magazine quality: a classic Copenhagen apartment living room on a bright winter morning, restrained Scandinavian style. Two-wall corner view, level camera, perfectly vertical lines, calm generous space, credible residential scale.

Architecture: 3.0 m ceiling with a simple one-step 10 cm cornice. Smooth matte mineral paint on walls and ceiling, warm off-white #F4F1EC, faint hand-made movement, no sheen. 15 cm skirting in the wall colour. Oiled oak plank floor, planks 25 cm wide and 3-4 m long, warm pale honey oak #D6BF9E, matte, natural non-repeating grain; clearly warm wood, not grey, not grey-washed.

One tall window in the left wall: rectangular with a flat head, 180 cm wide, sill at 75 cm and head as in the render, set in 35 cm deep painted reveals with a painted off-white inner sill, not wood. Two casements, one slim 6 cm mullion, slim off-white frame; no glazing bars, transom or arch. Bare: no curtains, rod or blinds. Outside: a pale, softly blurred winter garden with layered bare trees.

Exactly three furniture pieces:
1. Sofa against the back wall, right of the corner: low straight three-seater, 220 x 92 cm, 78 cm back, 44 cm seat, thin 14 cm track arms, three seat and three back cushions, coarse cotton-linen with visible slub, matte oatmeal #E6DCCB, four tapering round solid-oak legs #C8A27A.
2. Coffee table 42 cm in front of the sofa: superellipse top with straight sides, 140 x 70 x 38 cm, 3 cm top, oiled solid oak #C8A27A, four round 5 cm vertical legs set back 12 cm. Top empty.
3. Armchair in front of the window, seen in side profile, facing right toward the table: lounge chair with an exposed oiled oak frame in the same light natural oak #C8A27A as the table, flat 6 cm armrests ending above the front legs; 72 x 78 cm, 70 cm high with a low back, its top below the window sill, 40 cm seat; mist-grey wool boucle cushions #D9D6D0 with small loops, clearly cooler than the sofa.

Light: 10:30 winter morning, thin high cloud, soft north light only through the left window, one smooth gradient across the room. Bright, airy, high-key exposure: walls read light warm white, the wall beside the window brightest, the far right of the back wall at most half a stop darker. The window is the brightest area but not blown out. Broad soft shadows fall right and slightly toward the camera. Contact shadows under legs and under the sofa are short, soft and open, never black. Neutral 5000 K: walls warm white, never grey, pink, yellow or blue. No sun patches, beams, leaf or frame shadows. No lamps.

Finish: deep focus, all sharp. Gentle contrast, slightly lifted blacks, natural colour just below full saturation; the oak keeps its warmth. Crisp detail: sofa slub, boucle loops, continuous oak grain. No film grain, vignette or glow.

Empty, quiet room: bare walls and floor, nothing else.

Avoid: grey or dull floor, dim or greyish walls, black shadows, sunlight, pink or orange cast, curtains, lamps, rugs, cushions, throws, plants, decor, artwork, extra furniture, mirrors, glass objects, text, people.
```

**מה השתנה מול הפיילוט הראשון (ולמה):** (1) **חשיפה:** הקירות יצאו L 78–80 במקום 89–95. נוספו "bright, airy, high-key", ‏"light warm white", ‏"never grey" ו-"dim or greyish walls" ב-Avoid. בלי מספרי L בתוך הפרומפט, כי המודל לא מודד L. (2) **פרקט:** יצא ב-S 16–19 במקום כ-40. נוספו "warm pale honey oak", ‏"clearly warm wood, not grey" ו-"grey or dull floor" ב-Avoid, וגם "the oak keeps its warmth" בגימור. (3) **צל מגע:** יצא L 11 מתחת לספה (הסף 30). ‏"short, dark, delicate" הוחלף ב-"short, soft and open, never black", ונוסף "black shadows" ב-Avoid. (4) **מסגרת הכורסה** יצאה כהה מהשולחן: "the same light natural oak as the table". (5) **אדן אלון** בניסיון b: "painted off-white inner sill, not wood". (6) **אורך:** כ-3,550 תווים, במקום 4,961.
**אם אחרי 2 ניסיונות החשיפה עדיין נמוכה (L<86 ליד החלון):** מותר גריידינג גלובלי אחד בפוסט, בתוך כללי Bible "גריידינג": הרמת אמצעים ובהירים עד +0.5 סטופ, נקודת שחור L 12–15 ורוויה לא מעל הטבעי. בלי תיקון מקומי ובלי לגעת בגאומטריה. הפעולה נרשמת ב-`assets/prompts/m0.nordic/`.

## 5. הגרסה החלופית (טקסט בלבד; 2.1: כ-3,480 תווים, אותה ספירה; סבילות QA ±0.05)
ב-2.1 ה-[L] הוחלף בטקסט של L2, ושיעורי הכורסה עודכנו (19%–39%, גובה 70).
```text
Photorealistic editorial interior photograph, top design-magazine quality: a classic Copenhagen apartment living room on a bright winter morning, restrained Scandinavian style. Wide 16:9 two-wall corner view, level camera at 1.20 m, full-frame 24 mm with architectural shift, perfectly vertical lines, credible residential scale.

Composition: the camera stands in the front-right of a 4.8 x 6.2 m room with a 3.0 m ceiling, turned 25 degrees left. The back-left corner is a vertical line at 43% of the frame width. Left of it, the window wall recedes toward the camera; right of it, the back wall runs past the right edge. The ceiling is a thin wedge, about 13% deep at the corner, 7% above the sofa, nearly nothing at the right edge. Horizon at 46% down.

Architecture: simple one-step 10 cm cornice. Smooth matte mineral paint, warm off-white #F4F1EC, faint hand-made movement. 15 cm skirting in the wall colour. Oiled oak planks 25 cm wide, 3-4 m long, running front to back so they converge toward the corner; warm pale honey oak #D6BF9E, matte, non-repeating grain, clearly warm, not grey.

One tall window in the left wall, 90 cm from the corner: 180 cm wide, flat head at 270 cm, sill at 75 cm, the armchair back clearly below the sill. It spans 19% to 37% of the frame width, its head close to the top edge but inside the frame. 35 cm deep painted reveals, painted off-white inner sill, not wood. Two casements, one slim 6 cm mullion, slim off-white frame; no bars, transom or arch. Bare: no curtains, rod or blinds. Outside: pale, softly blurred winter garden with layered bare trees.

Exactly three furniture pieces, nothing overlapping:
1. Sofa against the back wall, spanning 52% to 84% of the frame width, its seat front at 80% down: low straight three-seater, 220 x 92 cm, 78 cm back, thin 14 cm track arms, three seat and three back cushions, coarse slubby cotton-linen, matte oatmeal #E6DCCB, tapering oak legs #C8A27A.
2. Coffee table 42 cm in front of it, spanning 51% to 76%: superellipse top with straight sides, 140 x 70 x 38 cm, oiled oak #C8A27A, four round vertical legs set back 12 cm. Top empty.
3. Armchair in the lower-left, in front of the window, seen in side profile facing right toward the table, between 19% and 39% of the width, at least 5% above the bottom edge, with clear floor between it and the sofa: lounge chair with an exposed oak frame in the same light oak as the table, flat 6 cm armrests ending above the front legs, 72 x 78 cm, 70 cm high with a low back; mist-grey wool boucle cushions #D9D6D0, clearly cooler than the sofa.

Light: 10:30 winter morning, thin high cloud, soft north light only through the left window, one smooth gradient. Bright, airy, high-key exposure: walls light warm white, brightest beside the window, the far right of the back wall at most half a stop darker. Window brightest but not blown out. Soft shadows fall right and slightly toward the camera; contact shadows short, soft and open, never black. Neutral 5000 K: walls never grey, pink, yellow or blue. No sun patches, beams or leaf shadows. No lamps.

Finish: deep focus, gentle contrast, lifted blacks, colour just below full saturation, oak keeps its warmth. Crisp slub, boucle loops, oak grain. No grain, vignette or glow.

Empty, quiet room: nothing else.

Avoid: grey floor, dim or greyish walls, black shadows, sunlight, pink or orange cast, curtains, lamps, rugs, cushions, plants, decor, artwork, extra furniture, mirrors, glass, text, people.
```

## 6. Negative (אם יש שדה)
כמו ב-1.3, ועוד: `grey floor, desaturated wood, underexposed room, dim walls, crushed black shadows, low ceiling, small room, one-point perspective, centred composition, curtains`. בלי `arched window` ו-`ceiling light` כפולים.

## 7. פירוק לשכבות (אחרי האישור)
כמו ב-1.3, סעיף 7. QA: ΔE ≤1 מחוץ לאזור הרהיטים והצל.

## 8. תנאי קבלה ל-M0 (qa-agent)
מדידות צבע: כתם בגודל 1% מרוחב הפריים, ב-HSL, אחרי החזרה ל-16:9.
| # | תנאי | סף |
| --- | --- | --- |
| M0-01 | אנכיים (פינה, מסגרות, רגליים) | ±0.5° |
| M0-02 | רצועת תקרה מעל התמונה, וכרכוב רציף | 0.07 ±0.01. הטריז יורד לכיוון השפה הימנית |
| M0-03 | מיקומים מול 2.1 | ±0.02 (טקסט ±0.05) |
| M0-04 | שתי נקודות מגוז: הפינה האחורית-שמאלית אנכית ב-u 0.431. קווי הרצפה, השיפולים והכרכוב של כל קיר מתכנסים בעקביות | ±0.01 |
| M0-05 | קנה מידה: ספה/משענת בחזית 2.82 ±6%. רוחב השולחן בפריים חלקי רוחב הספה | 0.78 ±0.05 |
| M0-06 | ראש החלון בפריים; קיר החלון גלוי עד Y≈3.74 | ≥0.010 מהשפה העליונה |
| M0-07 | רהיטים: ≥0.05 מהשוליים; אין משיקים בין רהיטים, ובין רהיט לקו אדריכלי (פינה, עמוד, משקוף, אדן, ערימת וילון), לפי `tangent_rule` ב-v4-spec | ≥0.02 |
| M0-08 | הפתח, הקיר הקדמי ונקודת התלייה | לא בפריים |
| M0-09 | חלון אחד, מלבן, ראש ישר, 2 כנפיים ועמוד, ספי עומק צבועים, אדן צבוע (לא עץ), בלי וילון | — |
| M0-10 | אין שקעים, מתגים, רדיאטור או מזגן | — |
| M0-11 | שיפולים כ-15 ס"מ וכרכוב פשוט, בצבע הקיר, רציפים | — |
| M0-12 | לוחות ברוחב כ-25 ס"מ, ארוכים, מתכנסים לכיוון הפינה, בלי חזרות | — |
| M0-13 עד M0-16 | ספה, שולחן, כורסה ו"בדיוק 3 רהיטים", כמו ב-1.3. הכורסה בפרופיל, פונה ימינה, ומסגרת האלון שלה בגוון השולחן | — |
| M0-17 | אין שמש, קרניים או צללי עלים | אפס |
| M0-18 | צל ימינה ומעט לכיוון המצלמה, רך. צל מגע קצר ורך | — |
| M0-19 | דעיכה: קיר החלון ליד החלון / הקיר האחורי ליד הפינה · מאחורי הספה (u 0.69) · הקצה הימני (u 0.97) | L 92–95 · 88–91 · 82–86 (±2) |
| M0-20 | החלון הבהיר ביותר, ‏L ≤97. אין 255 במשטחים. **הצל הכהה ביותר (מתחת לספה) ≥ L 30** | — |
| M0-21 | אין אור מלאכותי | — |
| M0-22 | קירות ותקרה (5 נקודות) | H 25–55, S 8–45, **L 89–97** (באזור המוצל לפי M0-19) |
| M0-23 | ספה H 30–45, S 20–45, L 78–90. כורסה S 0–15, L 76–88, פחות רוויה מהספה ב-8 לפחות. אלון (גם מסגרת הכורסה) H 25–40, S 25–55, L 52–78. **פרקט: H 30–40, S 30–45, L 68–78** (היעד #D6BF9E, ‏35/40/73) | — |
| M0-24 עד M0-26 | חומר וריאליזם, כמו ב-1.3 | — |
| M0-27 | 16:9 אחרי שינוי גודל לא אחיד מ-2752×1536 (או 5504×3072). מאסטר 6144×3456, בלי גרעין | — |
| M0-28 | תיעוד מלא ב-`assets/prompts/m0.nordic/`, כולל אורך הפרומפט בתווים | ≤3,900 |
| M0-29 | אישור master-designer ואז המשתמש | — |

**פיילוט 2K:** ניסיון שבו M0-19, M0-20 או M0-22 נכשלים ביותר מ-4 נקודות L, או שבו הפרקט ב-S<26, נפסל גם אם הגאומטריה מושלמת.

## 9. עלות
| שלב | קרדיטים |
| --- | --- |
| בלוק-אאוט v4 (שלושה ווריאנטים) ו-v4.1 (L2) | 0 |
| פיילוט 2K חדש: 2 עם clay ו-1 טקסט (400 כל אחד) | 1,200 |
| M0 סופי: 3 × 4K (450) | 1,350 |
| topaz ×2 | 300 |
| **סה"כ** | **כ-2,850** (רזרבה עד 3,700). פירוק לשכבות אחרי האישור: כ-950 |
