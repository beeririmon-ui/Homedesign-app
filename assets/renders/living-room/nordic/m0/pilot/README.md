# M0 סלון נורדי: פיילוט 2K (מעטפת ורהיטים קבועים)

render-agent, 2026-10-03. לפי `briefs/m0-prompt.nordic.md` 1.3, סעיף 9 (פיילוט בלבד). **לא הורץ שום 4K.** הנכסים כאן הם פיילוט: הם לא עברו QA ולא נכנסים לאתר.

## קבצים
| קובץ | מה |
| --- | --- |
| `m0-pilot-a.png` | image-to-image מהבלוק-אאוט, ניסיון 1 |
| `m0-pilot-b.png` | image-to-image מהבלוק-אאוט, ניסיון 2 (אותו פרומפט, אותו קלט) |
| `m0-pilot-text.png` | טקסט בלבד (סעיף 5) |
| `m0-pilot-compare.jpg` | השוואה: clay, ‏a, ‏b, ‏text (5144×780) |
| `raw/*.jpg` | הקבצים המקוריים כפי ש-var2 החזיר (JPEG). ה-PNG הם המרה ישירה, בלי שינוי פיקסלים |
| `assets/prompts/m0.nordic/m0-pilot-*.json` | רשומת שחזור לכל ניסיון: פרומפט, מודל, הגדרות, קלט (כולל sha256), מזהי var2 וקרדיטים |

## מודל, הגדרות ועלות
| | a | b | text |
| --- | --- | --- | --- |
| מודל | nano-banana-2 | nano-banana-2 | nano-banana-2 |
| סוג | image-to-image | image-to-image | text-to-image |
| קלט | `m0-clay-4k.png` (3840×2160, sha256 `c0eb4f2b…6a59`) | אותו קלט | — |
| רזולוציה / יחס | 2K / 16:9 | 2K / 16:9 | 2K / 16:9 |
| image_refs, negative, seed | אין (למודל אין seed ואין שדה negative; סעיף 6 נכנס דרך שורת Avoid) | | |
| placeholder_id | `c28c3bb4-a186-4879-b79a-c5b6dda3acfa` | `784840c2-ef5a-40f6-8ba3-26b52922b7d9` | `c67b4793-a6bb-44c8-93ab-c60ca8c6c0f3` |
| task_id | `2539f796a08aba276c7110b10b38c916` | `1710a290af8ddcb977bd0eef3ce12e2c` | `c2e7c24bb47f96b842ae5c8b4beee505` |
| קישור var2 | https://www.var2.ai/image/c28c3bb4-a186-4879-b79a-c5b6dda3acfa | https://www.var2.ai/image/784840c2-ef5a-40f6-8ba3-26b52922b7d9 | https://www.var2.ai/image/c67b4793-a6bb-44c8-93ab-c60ca8c6c0f3 |
| קרדיטים | 400 | 400 | 400 |

- קלט ב-var2: https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/5d604879-7f7d-421f-9005-2fb20bc271b2.png
- תוצאות (JPEG): ‏a ‏`…/nano2-2539f796a08aba276c7110b10b38c916-0-1791061954126-846ec905.jpg`, ‏b ‏`…/nano2-1710a290af8ddcb977bd0eef3ce12e2c-0-1791061911619-5c94b2c9.jpg`, ‏text ‏`…/nano2-c2e7c24bb47f96b842ae5c8b4beee505-0-1791061919064-9c43cd30.jpg` (אותה תיקייה כמו הקלט). URL מלא בקבצי ה-JSON.
- **הערכה מראש (`var2_estimate_cost`): 1,200. בפועל: 1,200 קרדיטים** (3 × 400). בתוך התקציב (1,200, סף עצירה 1,300).

### שתי סטיות שחשוב לדעת
1. **הפרומפט קוצר.** בכלי `var2_create_image` יש מגבלה של 4,000 תווים לפרומפט. הפרומפט בסעיף 4 הוא 4,961 תווים, ובסעיף 5 5,301. קיצרתי ניסוחים בלבד (למשל "for an accessible-premium Nordic home brand", "5.6 m from the front of the sofa", חזרות בפסקת הגימור), ושמרתי כל מידה, צבע, חומר והוראת אור. בגרסה הטקסטואלית "the framed picture's centre … (54%)" הפך ל-"the sofa centre sits at 54% of the width", כי אין תמונה ב-M0. **לפני ה-4K, master-designer צריך לאשר נוסח מקוצר רשמי בבריף** (אני לא שיניתי את הבריף).
2. **הפלט אינו 16:9 מדויק:** ‏var2 מחזיר 2752×1536 (יחס 1.792 ולא 1.778). התוכן מתוח לכל המסגרת: אחרי שינוי גודל לא אחיד ל-16:9, היישור מול ה-clay מדויק (dx=0). לכן את המאסטר מחזירים ל-16:9 בשינוי גודל (0.8% אופקית) ולא בחיתוך. כנראה שגם ה-4K יחזור ב-5504×3072, וזה צריך להיכנס לתהליך.

## הפרומפטים, מילה במילה (כפי שנשלחו)
### a ו-b (image-to-image)
```text
Use the attached grey clay render as the exact layout and camera. Keep every wall, the window opening, floor and ceiling lines, camera height, lens, and the position, size and angle of all three furniture pieces exactly as in the render. Move, resize, add or remove nothing. Only replace the clay with real materials and real daylight.

Photorealistic editorial interior photograph: a quiet, believable Nordic living room on a bright winter morning, restrained Scandinavian architectural style. Level camera, perfectly vertical lines, calm one-point perspective, generous empty floor and wall space, credible residential scale.

Architecture: ceiling 2.70 m. Smooth matte painted walls and ceiling in warm off-white #F4F1EC, barely perceptible roller texture, no sheen. Slim 8 cm skirting painted the wall colour. Pale whitewashed oiled oak plank floor, planks 20 cm wide, about 2 m long, running from the camera toward the back wall, average tone #D6BF9E, matte, natural non-repeating grain, fine seams.

One window only, in the left wall: rectangular opening 180 cm wide, 190 cm high, sill at 45 cm, flat head at 235 cm. Two casements, one slim 6 cm central mullion; no glazing bars, no transom, no arch. Slim painted wooden frame in warm off-white #F4F1EC, 6 cm profile, shallow painted wooden inner sill. Bare window: no curtains, rod or blinds, nothing on the sill. Outside: pale overcast sky, softly blurred bare trees.

Exactly three furniture pieces:
1. Sofa, centred against the back wall: low, straight three-seat sofa, 220 cm wide, 92 cm deep, 78 cm back, 44 cm seat. Thin track arms 14 cm wide, 60 cm high, softly rounded 3 cm edges. Three separate seat and three separate back cushions, plain seams. Coarse-weave cotton-linen with visible slub, matte, oatmeal #E6DCCB. Four round solid-oak legs, 15 cm visible, tapering 4 to 2.5 cm, natural oil, #C8A27A.
2. Coffee table, centred 42 cm in front of the sofa: superellipse top (soft rounded rectangle with straight sides), 140 x 70 cm, 3 cm thick, 38 cm high, solid oak, natural oil, matte, #C8A27A. Four round 5 cm vertical legs set back 12 cm from the edge. Tabletop completely empty.
3. Armchair, left side in front of the window, turned about 25 degrees toward the coffee table: lounge chair with exposed solid-oak frame, natural oil, matte, #C8A27A, flat 6 cm oak armrests ending directly above the front legs; 72 wide, 78 deep, 76 high, 40 cm seat. Seat and back cushions in mist-grey wool boucle with small matte loops, #D9D6D0. Its cool grey must read clearly different from the warm oatmeal sofa.

Camera: inside the room on its centre axis, 6.05 m from the back wall, 1.20 m high, perfectly level, full-frame 24 mm with architectural lens shift. Verticals straight. Ceiling only a thin band at the top. All furniture complete, nothing touches the frame edges.

Light: 10:30 winter morning, bright sky with thin high cloud. Soft diffuse north light enters only through the left window and falls off gently across the room. The wall beside the window is brightest; the back-right corner about half a stop darker, one smooth gradient, no patches. Broad soft shadows fall right and slightly toward the camera; short dark contact shadows under every leg. Warmth from oak and upholstery, not the light. Neutral 5000 K white balance: walls warm white, never pink, peach, yellow or blue. Window is the brightest area, not blown out. No direct sun, sun patches, beams, leaf or window-frame shadows. No lamps, no artificial light.

Finish: deep focus, sharp from nearest floor to back wall. Restrained contrast, slightly lifted blacks, natural colour slightly below full saturation. Crisp detail: sofa weave and slub, distinct boucle loops, continuous oak grain. No grain, vignette or glow.

Empty, quiet room: bare walls and floor, nothing else.

Avoid: sunlight, sun patches, pink or orange cast, curtains, lamps, rugs, cushions, throws, plants, decor, artwork, extra furniture, mirrors, glass objects, text, people.
```

### text (טקסט בלבד)
```text
Photorealistic editorial interior photograph: a quiet, believable Nordic living room on a bright winter morning, restrained Scandinavian architectural style. Wide 16:9 frame, one-point perspective straight at the back wall, level camera, perfectly vertical lines, generous empty space, credible residential scale.

Room and camera: room 3.7 m wide, ceiling 2.70 m. Camera inside the room on its centre axis, 6.05 m from the back wall, 1.20 m high, level, full-frame 24 mm with architectural lens shift, not tilted. The back wall fills about 40% of the frame width, slightly right of centre; the sofa centre sits at 54% of the width. Ceiling only a thin band across the top 9-10% of the frame. Horizon just under 40% down. Left wall recedes along the left side, right wall along the right quarter, both plumb. Bottom tenth of the frame is empty oak floor.

Architecture: smooth matte walls and ceiling in warm off-white #F4F1EC, barely perceptible roller texture, no sheen. Slim 8 cm skirting in the wall colour. Pale whitewashed oiled oak plank floor, planks 20 cm wide, about 2 m long, running toward the back wall, average #D6BF9E, matte, non-repeating grain. Right wall completely plain, no openings.

One window only, in the left wall, starting 60 cm from the back corner: rectangular opening 180 cm wide, 190 cm high, sill 45 cm, flat head 235 cm. Two casements, one slim 6 cm central mullion; no glazing bars, transom or arch. Slim off-white #F4F1EC wooden frame, 6 cm profile, shallow painted inner sill. Bare: no curtains, rod or blinds. Outside: pale overcast sky, softly blurred bare trees. At least 1.4 m of plain wall visible in front of the window, toward the camera.

Exactly three furniture pieces:
1. Sofa centred against the back wall: low straight three-seater, 220 wide, 92 deep, 78 cm back, 44 cm seat. Thin track arms 14 cm wide, 60 high, rounded 3 cm edges. Three separate seat and three back cushions, plain seams. Coarse cotton-linen with visible slub, matte oatmeal #E6DCCB. Four round tapering solid-oak legs, 15 cm visible, #C8A27A.
2. Coffee table centred 42 cm in front of the sofa: superellipse top (rounded rectangle, straight sides), 140 x 70 cm, 3 cm thick, 38 cm high, oiled solid oak #C8A27A, matte. Four round 5 cm vertical legs set back 12 cm. Top empty.
3. Armchair in the lower-left third, about 3.2 m from the camera, just forward of the window, back toward the left wall, turned about 25 degrees toward the coffee table, fully in frame with clear space to the left edge and a clear gap to the sofa: lounge chair with exposed oiled solid-oak frame #C8A27A, flat 6 cm oak armrests ending directly above the front legs; 72 wide, 78 deep, 76 high, 40 cm seat. Cushions in mist-grey wool boucle with small loops, #D9D6D0, clearly cooler than the oatmeal sofa.
Clear floor between armchair and table. No piece overlaps another.

Light: 10:30 winter morning, thin high cloud. Soft diffuse north light enters only through the left window, falling off gently. Wall beside the window brightest; back-right corner about half a stop darker, one smooth gradient. Broad soft shadows fall right and slightly toward the camera; short dark contact shadows under every leg. Neutral 5000 K: walls warm white, never pink, peach, yellow or blue. Window brightest, not blown out. No direct sun, sun patches, beams, leaf or frame shadows. No lamps, no artificial light.

Finish: deep focus, all sharp. Restrained contrast, slightly lifted blacks, colour slightly below full saturation. Crisp detail: sofa weave and slub, boucle loops, continuous oak grain. No grain, vignette or glow.

Empty, quiet room: bare walls and floor, nothing else.

Avoid: sunlight, sun patches, pink or orange cast, curtains, lamps, rugs, cushions, throws, plants, decor, artwork, extra furniture, mirrors, glass objects, text, people.
```

## בדיקה עצמית מול 29 תנאי הקבלה (סעיף 8)
**איך נמדד:** כל תמונה הוקטנה ל-16:9 ‏(1920×1080), וחושבה הזזה מקומית מול ה-clay, בהתאמת קצוות (correlation של גרדיאנט, חיפוש ±12 פיקסלים) בכל אזור. הרווח בין הכורסה לספה נמדד מקצוות אנכיים ב-2752 פיקסלים. הצבעים נמדדו כממוצע של כתם ברוחב 1% מהפריים, ב-HSL (‏H במעלות, ‏S ו-L באחוזים). זו בדיקה עצמית של render-agent ולא QA. הבדיקות של M0-24 עד M0-27 נעשו ב-2K ולא ב-4K/6K.

**סטייה מקומית מה-clay (חלק מהפריים):**
| אזור | a: ‏dx / dy | b: ‏dx / dy | text |
| --- | --- | --- | --- |
| כל הפריים | 0.000 / +0.002 | 0.000 / +0.002 | אין התאמה (corr 0.07) |
| קירות ופינות | 0.000 / +0.001 | 0.000 / +0.001 | אין התאמה |
| ספה | 0.000 / +0.001 | 0.000 / +0.001 | אין התאמה |
| שולחן | 0.000 / +0.001 | 0.000 / +0.001 | אין התאמה |
| כורסה | 0.000 / +0.002 | 0.000 / +0.002 | אין התאמה |
| חלון | 0.000 / +0.001 | 0.000 / +0.001 | החלון בקיר האחורי |

**רווח בין הכורסה לספה (סף בפיילוט ≥0.015, ב-M0-07 ≥0.02):** ‏clay ‏0.0229 · ‏**a ‏0.0233** · ‏**b ‏0.0233** · ‏text: ‏כ-0.10, אבל בפריסה אחרת לגמרי.

**צבע (HSL):**
| נקודה | יעד | a | b | text |
| --- | --- | --- | --- | --- |
| קיר אחורי: שמאל / מרכז / ימין (עמודות, חציון) | ‏L 92–95 / 88–91 / 82–86 | 72 / 80 / 71 (שיא 85 ב-x 0.45) | 70 / 79 / 70 (שיא 85) | 70 / 67 / 63 |
| תקרה / קיר ימני | ‏H 25–55, ‏S 8–45, ‏L 89–97 | ‏27,9,80 / 26,9,80 | ‏28,8,78 / 29,8,80 | ‏28,13,73 / 33,10,77 |
| ספה (גב / מושב) | ‏H 30–45, ‏S 20–45, ‏L 78–90 | ‏30,17,75 / 30,15,74 | ‏31,14,74 / 31,13,75 | ‏33,16,64 / 30,14,70 |
| כורסה, בוקלה (מושב) | ‏S 0–15, ‏L 76–88; ‏S נמוך מהספה ב-8 לפחות | ‏30,7,57 (הפרש S: 8–10) | ‏29,6,63 (הפרש S: 7–8) | ‏29,9,48 |
| אלון, שולחן | ‏H 25–40, ‏S 25–55, ‏L 52–78 | ‏32,29,62 | ‏33,27,60 | ‏31,28,59 |
| אלון, מסגרת הכורסה | אותו טווח | ‏29,19,44 (כהה יותר מהשולחן) | ‏28,18,41 | — |
| פרקט | קרוב ל-#D6BF9E ‏(35,40,73) | ‏30,19,68 | ‏29,16,71 | ‏27,17,65 |
| חלון (שמיים) | ‏L ≤97 | 95 | 98 | 100 |
| פיקסלים עם ערוץ 255 | אפס במשטחים | 2,613, כולם בתוך פתח החלון | 8,987, ‏3 מחוץ לפתח החלון | 50,241 |
| הצל הכהה ביותר מתחת לספה | ‏L ≥30 | ‏L 11 (קו המגע) | ‏L 11 | — |

### טבלת התנאים
✓ עובר · ✗ נכשל · ~ גבולי או לא ניתן לבדוק בפיילוט

| # | תנאי | a | b | text | הערה |
| --- | --- | --- | --- | --- | --- |
| M0-01 | אנכיים ±0.5° | ✓ | ✓ | ✓ | ב-a וב-b הפינות והרגליים יושבות על קווי ה-clay |
| M0-02 | רצועת תקרה 6–10% | ✓ | ✓ | ✗ | ‏a/b: ‏0.095 כמו ה-clay. ‏text: כ-0.11 |
| M0-03 | מיקומים ±0.02 (text ±0.05) | ✓ | ✓ | ✗ | ‏a/b: סטייה מקסימלית 0.002. ‏text: פריסה אחרת |
| M0-04 | נקודת מגוז ב-x 0.52–0.56 | ✓ | ✓ | ✗ | ‏a/b: הקווים הצדדיים על קווי ה-clay (0.54) |
| M0-05 | קנה מידה (2.82 ±6%, שולחן/ספה 0.80 ±0.05) | ✓ | ✓ | ✗ | ‏a/b: הגאומטריה של ה-clay נשמרה. ‏text: הספה ארוכה ונמוכה יותר |
| M0-06 | קיר פנוי ≥140 ס"מ לפני החלון; ראש החלון ≥0.010 | ✓ | ✓ | ✗ | ‏text: החלון בקיר האחורי |
| M0-07 | שוליים ≥0.05; כורסה–ספה ≥0.02 | ✓ | ✓ | ~ | ‏a/b: ‏0.0233. ‏text: אין משיק, אבל לא בפריסה |
| M0-08 | פתח, קיר קדמי, נקודת תלייה לא בפריים | ✓ | ✓ | ✓ | |
| M0-09 | חלון אחד, ראש ישר, 2 כנפיים, עמוד, מסגרת בלבן חם, אדן צבוע, ריק | ✓ | ✗ | ✗ | ‏a: עומד (יש ידיות חלון, לא אסורות). ‏b: **אדן מעץ אלון ולא צבוע** (‏Bible: אדן מעץ צבוע). ‏text: בקיר האחורי |
| M0-10 | קיר ימין ריק, אין שקעים, מתגים או רדיאטור | ✓ | ✓ | ✓ | |
| M0-11 | שיפולים כ-8 ס"מ, בצבע הקיר, רציפים | ✓ | ✓ | ✓ | |
| M0-12 | פרקט ברוחב 20 לאורך הציר, מתכנס, בלי חזרות | ✓ | ✓ | ~ | ‏a/b: לוחות רחבים, ישרים ומתכנסים. ‏text: מתכנס לנקודה אחרת |
| M0-13 | ספה: ישרה, 3+3 כריות, track, רגלי אלון מתחדדות | ✓ | ✓ | ✓ | |
| M0-14 | שולחן סופר-אליפסה, רגליים זקופות ונסוגות, ריק | ✓ | ✓ | ✗ | ‏text: אליפסה מחודדת עם קורות חיבור |
| M0-15 | כורסה משמאל לפני החלון, 20–30°, מסגרת גלויה, משענות מסתיימות מעל הרגליים, בוקלה | ✓ | ✓ | ~ | ‏a/b: הגאומטריה של ה-clay. ‏text: כורסה אחרת (רגליים משופעות), והמשענות בולטות מעט |
| M0-16 | בדיוק 3 רהיטים, בלי חפצים | ✓ | ✓ | ✓ | |
| M0-17 | אין כתמי שמש, קרני אור או צללי רשת | ✓ | ✓ | ✓ | |
| M0-18 | צל ימינה ומעט קדימה, רך, צל מגע מתחת לרגליים | ~ | ~ | ~ | צללים רכים וצל מגע יש. הצל המוטל חלש מאוד, וקשה לקבוע את כיוונו ב-2K |
| M0-19 | דעיכה בקיר האחורי: ‏L 92–95 / 88–91 / 82–86 | ✗ | ✗ | ✗ | חשוך בכ-10–15 נקודות L. השיא ב-x 0.45 ולא ליד הפינה השמאלית |
| M0-20 | החלון הבהיר ביותר, ‏L ≤97, אין 255 במשטחים, צל ≥L 30 | ~ | ✗ | ✗ | ‏a: חלון 95; ה-255 רק בשמיים; קו המגע מתחת לספה ב-L 11. ‏b: חלון 98, ו-3 פיקסלים של 255 מחוץ לפתח |
| M0-21 | אין אור מלאכותי | ✓ | ✓ | ✓ | |
| M0-22 | קירות ותקרה: ‏H 25–55, ‏S 8–45, ‏L 89–97 | ✗ | ✗ | ✗ | ‏H ו-S בטווח (אין ורוד ואין כחול). ‏L ‏78–80, נמוך מהיעד |
| M0-23 | ספה, כורסה, אלון ופרקט בטווחים; כורסה פחות רוויה ב-8 | ✗ | ✗ | ✗ | ספה: ‏S 15–17 ו-L 74–75, מעט מתחת. כורסה: L נמוך. מסגרת הכורסה כהה מהשולחן. הפרקט אפור וחיוור (S 16–19 במקום כ-40). ב-a ההפרש ברוויה 8–10 (עובר בקושי), ב-b ‏7–8 |
| M0-24 | בד עם קליעה וסלאב, לולאות בוקלה, סיבי אלון | ✓ | ✓ | ✓ | ב-2K. ‏a: הקליעה בספה נראית מעט "מודפסת". ‏b: טבעית יותר |
| M0-25 | אין שעווה, קצוות נמסים, או רגליים כפולות או חסרות | ✓ | ✓ | ✓ | ‏a/b: מתחת לגב הכורסה רואים רצועה כהה (חלק מהמבנה), לבדיקה ב-4K |
| M0-26 | אחרי topaz | ~ | ~ | ~ | לא רלוונטי בפיילוט |
| M0-27 | ‏16:9, מאסטר 6K, אין גרעין | ~ | ~ | ~ | אין גרעין. הפלט 2752×1536 ולא 16:9 מדויק; אין 6K בפיילוט |
| M0-28 | הפרומפט, הקלט, המודל וההגדרות שמורים | ✓ | ✓ | ✓ | `assets/prompts/m0.nordic/` |
| M0-29 | אישור master-designer ומשתמש | ~ | ~ | ~ | ממתין |

**מראה clay:** אין, בשלושתם. החומרים ריאליסטיים (פשתן, בוקלה, אלון, טיח), והגוונים הם לא אפור של clay.
**חלון ואור לפי ה-Bible:** ב-a וב-b יש חלון מלבני עם ראש ישר, 2 כנפיים, עמוד, מסגרת לבנה חמה, בלי וילון, ובחוץ שמיים מעוננים ועצים חשופים. האור מפוזר, בלי שמש ובלי מנורות. ב-b האדן מאלון (✗), ומחוץ לחלון יש מעט שלג. **ההבדל העיקרי מה-Bible הוא החשיפה:** החדר כהה בכ-1/2 סטופ מהיעד (קירות ב-L ‏78–80 ולא 89–95), והפרקט אפור ולא דבש חיוור.

## המלצה ל-4K
**המסלול שמנצח הוא image-to-image מהבלוק-אאוט** (a/b). הגאומטריה נשמרה כמעט בדיוק (≤0.002), והרווח בין הכורסה לספה 0.023, כמו בתכנון. מסלול הטקסט בלבד **נפסל**: החלון עבר לקיר האחורי, השולחן הוא אליפסה מחודדת, והמצלמה והפריסה לא תואמות.
**בין שני הניסיונות a עדיף:** האדן צבוע כנדרש, החלון לא שרוף (L 95), ואין 255 מחוץ לפתח החלון.

**כל ניסיון נכשל באותם תנאים (M0-19, ‏M0-22, ‏M0-23).** את רובם אפשר לפתור בגריידינג מבוקר (חשיפה +0.4 עד +0.5 סטופ בטונים הבהירים, והרמת השחורים), או בתיקון הפרומפט לפני ה-4K. הצעות לתיקון הפרומפט, ל-master-designer (לא יושמו, כי מדובר בשינוי בבריף):
1. נוסח מקוצר רשמי עד 4,000 תווים לסעיף 4 (בסיס: הנוסח שלמעלה).
2. חשיפה: "bright, airy exposure: walls read L 92–95 near the window".
3. פרקט: "warm pale honey oak #D6BF9E, not grey, not white-washed grey".
4. מסגרת הכורסה: "the armchair's oak frame is the same light natural oak #C8A27A as the coffee table".
5. אדן החלון: "painted off-white sill, not wood".

אם המלצה מאושרת: 3 ניסיונות 4K במסלול image-to-image (3 × 450 = 1,350 קרדיטים, לפי הבריף). עוצר כאן עד אישור.
