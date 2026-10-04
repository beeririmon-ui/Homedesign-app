# M0 סלון נורדי: פיילוט 2K על בלוק-אאוט v4.1 (חלופה B, ‏L2)

render-agent, 2026-10-04. לפי `briefs/m0-prompt.nordic.md` 2.1 (סעיפים 4, 5, 8, 9). מעטפת ושלושה רהיטים קבועים בלבד, בלי מוצרים ובלי וילונות (M0-09). **לא הורץ 4K.** פיילוט בלבד: לא עבר QA ולא נכנס לאתר.

## קבצים
| קובץ | מה |
| --- | --- |
| `m0-pilot-a.png` | ‏image-to-image מה-clay, ניסיון 1 (2752×1548) |
| `m0-pilot-b.png` | ‏image-to-image מה-clay, ניסיון 2 (אותו פרומפט ואותו קלט) |
| `m0-pilot-text.png` | טקסט בלבד (סעיף 5) |
| `m0-pilot-b-graded.png` | **תוספת, 0 קרדיטים:** ‏b אחרי גריידינג גלובלי אחד, לפי ההיתר בסעיף 4 של הבריף (ראו למטה) |
| `compare.jpg` | ‏clay ‏\| ‏a ‏\| ‏b ‏\| ‏text (5150×770) |
| `raw/*.jpg` | הקבצים כפי ש-var2 החזיר (JPEG, ‏2752×1536) |
| `measurements.json`, `measurements-summary.json` | כל המדידות. הסקריפטים: `measure.py`, `grade.py` |
| `assets/prompts/m0.nordic/m0-pilot-v4.1-{a,b,text,b-graded}.json` | רשומות שחזור |

**החזרה ל-16:9:** שינוי גודל לא אחיד מ-2752×1536 ל-2752×1548 (‏Lanczos, ‏+0.78% אנכית, שקול ל-0.8% אופקית), בלי חיתוך.

## מודל, הגדרות ועלות
| | a | b | text |
| --- | --- | --- | --- |
| מודל / סוג | nano-banana-2 / image-to-image | nano-banana-2 / image-to-image | nano-banana-2 / text-to-image |
| קלט | `m0-clay-4k.png` ‏3840×2160, ‏sha256 `d8c69da8…8df3` | אותו קלט | — |
| רזולוציה / יחס | 2K / 16:9 | 2K / 16:9 | 2K / 16:9 |
| image_refs, negative, seed | אין (אין למודל seed ואין שדה negative; סעיף 6 נכנס דרך שורת Avoid) | | |
| placeholder_id | `c8534226-747b-4a84-be67-92ae292c0375` | `808bdb7c-ddd5-4806-8d78-fd413b7d2206` | `a24bcd58-729e-4e03-a949-1ecaa5bb613d` |
| task_id | `d84a1f5ad74084b411a6c456a2ef2446` | `6b5a9b7a01317fcf1e95122edcad53e6` | `cadb1410c4b042ce47be6245531d6a0e` |
| קישור | https://www.var2.ai/image/c8534226-747b-4a84-be67-92ae292c0375 | https://www.var2.ai/image/808bdb7c-ddd5-4806-8d78-fd413b7d2206 | https://www.var2.ai/image/a24bcd58-729e-4e03-a949-1ecaa5bb613d |
| קרדיטים | 400 | 400 | 400 |

- קלט ב-var2 (הועלה דרך `var2_request_upload` ו-PUT; ה-sha256 של הקובץ שהורד בחזרה זהה למקומי): https://cqfxzynnlzsxugtwrsex.supabase.co/storage/v1/object/public/generated-images/09acbcfd-5936-4b44-9775-f842f767bcef/914cb5d6-7fb6-4752-93a7-a3a8b8e5de4e.png
- ‏URL מלא של כל תוצאה ברשומות ה-JSON.
- **הערכה מראש (`var2_estimate_cost`): ‏1,200. בפועל: ‏1,200 קרדיטים** (‏3 × 400). התקציב היה 1,200, וסף העצירה 1,300.

## הפרומפטים, מילה במילה
נשלחו **כפי שהם בבריף 2.1, בלי קיצור**: ‏**i2i ‏3,495 תווים**, ‏**text ‏3,482 תווים** (ספירה של `len()` בפייתון, כולל שורות ריקות; כולם ASCII). שניהם מתחת ל-3,900 (M0-28) ולמגבלת var2 של 4,000.

### a ו-b (image-to-image, ‏3,495 תווים)
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

### text (טקסט בלבד, ‏3,482 תווים)
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

## בדיקה עצמית (זו לא QA)
**שיטה:** כל המדידות על ה-PNG אחרי החזרה ל-16:9 (2752×1548). **גאומטריה:** הזזה מקומית מול ה-clay (‏`m0-clay-4k.png`, מוקטן לאותו גודל) לפי התאמת קצוות (קורלציה של גרדיאנט, חיפוש ±14 פיקסלים) בכל אזור. **צבע:** ממוצע כתם ברוחב 1% מהפריים (0.4% לרגל ולמסגרת הכורסה), ב-HSL ‏(H במעלות, ‏S ו-L באחוזים). **פרקט:** חציון של האזור u 0.42–0.98, ‏v 0.87–0.99. **צל מגע:** האזור u 0.52–0.84, ‏v 0.74–0.83 (מתחת לספה), ‏median 3×3. **כורסה מול האדן:** בכל עמודה ב-u 0.25–0.29, הקצה התחתון של האדן מול הקצה העליון של כרית הגב. ‏fw = יחידות רוחב פריים (‏v כפול 9/16), כמו ב-`m0-selfcheck.json`.

### גאומטריה מול ה-clay (‏du / dv, חלק מהפריים)
| אזור | a | b | text |
| --- | --- | --- | --- |
| כל הפריים | 0.000 / +0.002 | 0.000 / +0.002 | אין התאמה (corr 0.07) |
| פינה וכרכוב | 0.000 / +0.004 | 0.000 / +0.004 | אין התאמה |
| חלון | 0.000 / +0.001 | 0.000 / +0.001 | אין התאמה |
| ספה / שולחן / כורסה | 0.000 / +0.002 (כולם) | 0.000 / +0.002 (כולם) | אין התאמה |
| רצועת תקרה | 0.000 / +0.003 | ‎−0.001 / +0.005 | — |
| רצפה ושיפולים מימין | 0.000 / +0.003 | 0.000 / +0.003 | — |

**text, הערכה מהתמונה (±0.01):** פינה ב-u ≈0.49 (צפוי 0.431, סטייה 0.06), חלון כ-0.09–0.34 (צפוי 0.191–0.374), ספה כ-0.51–0.92 (צפוי 0.521–0.840), שולחן כ-0.45–0.73 (צפוי 0.512–0.762), כורסה כ-0.11–0.31 (צפוי 0.190–0.387), רצועת תקרה בפינה כ-0.17 (צפוי 0.133). הכורסה בעיצוב אחר (מסגרת אלכסונית). **נכשל ב-M0-03 גם בסבילות ±0.05.**

### כורסה מול האדן (C5 / M0-07: גב הכורסה ≥0.02 fw מתחת לאדן)
| | הנקודה הצפופה | קצה תחתון של האדן (v) | ראש הכרית (v) | רווח |
| --- | --- | --- | --- | --- |
| clay (מפרט) | — | — | 0.622 | ‏0.0226 fw |
| a | u 0.270–0.275 | 0.576 | 0.622 | ‏0.0465 v = **‏0.026 fw ✓** |
| b | u 0.270 | 0.576 | 0.612 | ‏0.0362 v = **‏0.020 fw ✓ (על הגבול)**. הכרית יצאה כ-1 ס"מ בפריים (0.010 v) גבוהה מה-clay |
| text | u 0.245–0.255 | כ-0.597 | כ-0.597 | **‏0 ✗** (הגב נוגע בקו האדן) |

### צבע ואור (HSL)
| נקודה | יעד | a | b | text | **b אחרי גריידינג** |
| --- | --- | --- | --- | --- | --- |
| קיר החלון, מול החלון (0.10, 0.30) | ‏L 92–95 (M0-19) | ‏29/14/**61** | ‏29/15/**66** | בתוך החלון | ‏29/25/**79** |
| קיר החלון, ליד החלון (0.405, 0.30) | ‏L 92–95 | ‏28/14/**68** | ‏30/14/**72** | ‏31/12/68 | ‏30/26/**85** |
| קיר אחורי ליד הפינה (0.467, 0.385) | ‏L 92–95 | ‏28/12/**76** | ‏29/13/**80** | ‏31/14/65 | ‏29/27/**91** |
| קיר אחורי מאחורי הספה (0.69, 0.22 / 0.42) | ‏L 88–91 | **74 / 75** | **80 / 83** | 77 / 85 | **91 / 92** |
| קיר אחורי, קצה ימני (0.97, 0.31) | ‏L 82–86 | **66** | **72** | 75 | **84 ✓** |
| תקרה (0.55, 0.04) | ‏H 25–55, ‏S 8–45, ‏L 89–97 | ‏25/11/**80** | ‏29/11/**84** | ‏30/7/80 | ‏29/24/**93 ✓** |
| ספה, גב / חזית מושב | ‏H 30–45, ‏S 20–45, ‏L 78–90 | ‏31/21/70, ‏31/23/71 | ‏31/19/71, ‏29/20/68 | ‏34/17/75, ‏32/17/68 | ‏31/34/83, ‏29/33/81 ✓ |
| כורסה, בוקלה מושב / גב | ‏S 0–15, ‏L 76–88, ‏S נמוך מהספה ב-8+ | ‏24/8/57, ‏28/10/51 | ‏24/9/67, ‏29/11/53 | ‏30/16/59, ‏30/19/66 | ‏24/14/80, ‏29/15/66 |
| אלון, שולחן | ‏H 25–40, ‏S 25–55, ‏L 52–78 | ‏32/34/77 ✓ | ‏30/39/74 ✓ | ‏32/19/79 | ‏30/63/84 ✗ (S ו-L מעל) |
| אלון, רגל הכורסה (0.4%) | אותו טווח | ‏30/15/49 | ‏30/16/53 | ‏29/15/61 | ‏30/22/66 |
| **פרקט (חציון)** | ‏H 30–40, ‏S 30–45, ‏L 68–78 | ‏31/**24.8**/57 | ‏31/**29.5**/64 | ‏31/30/52 | ‏31/**45.0**/**76.5** ✓ |
| **צל מגע מתחת לספה** (מינימום / אחוזון 1) | ‏L ≥30 | **4.5 / 7.8** | **3.5 / 6.1** | 0.8 / 4.7 | **15.9 / 18.5** |
| (לייחוס: ה-clay באותו אזור) | | 3.1 / 8.4 | | | |
| **חלון** (חציון / אחוזון 99 / מקסימום) | ‏L ≤97, אין 255 במשטחים | ‏92 / 99.6 / 100 | ‏91 / 99.8 / 100 | ‏87 / 99.8 / 100 | ‏96 / 98.3 / 98.3 |
| פיקסלים עם ערוץ 255: בחלון / מחוצה לו | 0 מחוץ לחלון | 3,811 / 76 | 36,102 / 1,212 | 12,269 / 22,275 | 0 / 0 |

### טבלת התנאים
✓ עובר · ✗ נכשל · ~ גבולי או לא ניתן לבדוק בפיילוט

| # | תנאי | a | b | text | b אחרי גריידינג |
| --- | --- | --- | --- | --- | --- |
| M0-01 | אנכיים ±0.5° | ✓ (בעין, נעול ל-clay) | ✓ | ✓ | ✓ |
| M0-02 | רצועת תקרה 0.07 ±0.01 | ✓ (כ-0.073) | ✓ (כ-0.075) | ✗ | ✓ |
| M0-03 | מיקומים ±0.02 | ✓ (≤0.004) | ✓ (≤0.005) | ✗ (עד 0.08, גם ±0.05 נכשל) | ✓ |
| M0-04 | פינה ב-u 0.431 ±0.01, התכנסות עקבית | ✓ | ✓ | ✗ (0.49) | ✓ |
| M0-05 | קנה מידה, שולחן/ספה 0.78 ±0.05 | ✓ (0.78, כמו ה-clay) | ✓ | ~ (כ-0.70) | ✓ |
| M0-06 | ראש החלון בפריים, קיר החלון עד Y≈3.74 | ✓ | ✓ | ✓ | ✓ |
| M0-07 | שוליים ≥0.05; בלי משיקים (≥0.02) | ✓ (תחתית 0.094; אדן 0.026 fw) | ✓ (אדן 0.020 fw, על הגבול) | ✗ (הכורסה נוגעת באדן) | ✓ |
| M0-08 | פתח, קיר קדמי, נקודת תלייה לא בפריים | ✓ | ✓ | ✓ | ✓ |
| M0-09 | חלון אחד, 2 כנפיים ועמוד, ספים ואדן צבועים, בלי וילון | ✓ | ✓ | ✓ (אבל עם משקוף מעוטר) | ✓ |
| M0-10 | אין שקעים, מתגים, רדיאטור | ✓ | ✓ | ✓ | ✓ |
| M0-11 | שיפולים וכרכוב בצבע הקיר, רציפים | ✓ | ✓ | ✓ | ✓ |
| M0-12 | לוחות 25 ס"מ, ארוכים, מתכנסים, בלי חזרות | ✓ | ✓ | ✓ | ✓ |
| M0-13–16 | ספה, שולחן, כורסה, בדיוק 3; כורסה בפרופיל ומסגרת בגוון השולחן | ~ (מסגרת הכורסה כהה וקרה מהשולחן: ‏L 49/S 15 מול 77/34) | ~ (‏L 53/S 16 מול 74/39; בעין קרוב יותר) | ✗ (כורסה בעיצוב אחר) | ~ |
| M0-17 | אין שמש, קרניים או צללי עלים | ~ (כתם אור עם קצה מוגדר על הרצפה מימין לשולחן, נקרא כמו שמש רכה) | ✓ (כתם רך) | ✓ | ✓ |
| M0-18 | צל ימינה ולכיוון המצלמה, רך; צל מגע קצר ורך | ✓ / ✗ (כהה) | ✓ / ✗ (כהה) | ✓ / ✗ | ✓ / ✗ |
| M0-19 | דעיכה 92–95 · 88–91 · 82–86 | ✗ (61–76 · 74–75 · 66) | ✗ (66–80 · 80–83 · 72) | ✗ | ~ (קיר החלון 79–85 ✗; פינה 91, ספה 91–92, ימין 84 ✓) |
| M0-20 | חלון ≤97, אין 255 במשטחים, צל ≥30 | ✗ (100; צל 4.5) | ✗ (100; 1,212 פיקסלים מחוץ לחלון; צל 3.5) | ✗ | ~ (חלון 98.3, אפס 255; צל 16 ✗) |
| M0-21 | אין אור מלאכותי | ✓ | ✓ | ✓ | ✓ |
| M0-22 | קירות ותקרה L 89–97 | ✗ (61–80) | ✗ (66–84) | ✗ | ~ (פינה, ספה, תקרה ✓; קיר החלון ✗) |
| M0-23 | ספה, כורסה, אלון, פרקט | ✗ (ספה L 70; פרקט S 24.8) | ✗ (ספה L 68–71; פרקט L 64) | ✗ | ~ (ספה ✓, פרקט ✓, שולחן S 63 ✗) |
| M0-24–26 | חומר וריאליזם | ✓ | ✓ (הכי נקי: שזירה בספה, לולאות בוקלה, סיבי אלון) | ✓ | ✓ |
| M0-27 | ‏16:9 אחרי שינוי גודל, בלי גרעין | ✓ (2K בלבד) | ✓ | ✓ | ✓ |
| M0-28 | תיעוד מלא, פרומפט ≤3,900 | ✓ (3,495) | ✓ (3,495) | ✓ (3,482) | ✓ |
| M0-29 | אישור master-designer ומשתמש | ממתין | ממתין | ממתין | ממתין |

**כלל הפסילה של הפיילוט** (M0-19/20/22 ביותר מ-4 נקודות L, או פרקט S<26): ‏**a נפסל** (קירות, ופרקט S 24.8). ‏**b הגולמי נפסל** על חשיפה (קירות 66–84), אבל הפרקט שלו עובר (S 29.5). ‏**text נפסל** על גאומטריה וחשיפה.

## הגריידינג של b (תוספת, 0 קרדיטים)
הבריף (סעיף 4) מתיר, אם אחרי 2 ניסיונות החשיפה עדיין נמוכה: גריידינג גלובלי אחד, הרמה עד +0.5 סטופ, נקודת שחור L 12–15, ורוויה לא מעל הטבעי, בלי תיקון מקומי. הוחל על b בלבד: לינארי, **‏+0.45 סטופ**, כתף רכה בבהירים (מעל 0.70 לינארי, תקרה 0.985, לפי הערוץ המקסימלי כדי לשמור גוון), חזרה ל-sRGB, נקודת שחור 0.12 (‏L 12). אין שינוי ברוויה. הגאומטריה לא נגעה. רשומה: `assets/prompts/m0.nordic/m0-pilot-v4.1-b-graded.json`, קוד: `grade.py`.

**מה זה פותר:** הקיר האחורי (91–92), הקצה הימני (84), התקרה (93), הספה (81–83) והפרקט (‏H 31, ‏S 45, ‏L 76.5) נכנסים לטווח. החלון כבר לא שרוף (אפס פיקסלים 255).
**מה לא:** (1) **קיר החלון** (79–85 במקום 92–95). זה הקיר שבו נמצא החלון, והאור פוגע בו בזווית חדה, לכן פיזיקלית הוא כהה מהקיר האחורי. גם ב-clay זה כך (‏L 64.7 בקיר החלון מול 77.6 בקיר האחורי). **נראה שהיעד של M0-19 לקיר החלון לא תואם את הפיזיקה של המצלמה הזו, ו-master-designer צריך להחליט עליו.** (2) **צל המגע מתחת לספה** (16 במקום ≥30). זה הרווח של 15 ס"מ מתחת לבסיס הספה, וגם ב-clay הוא ‏L 3. בלי תיקון מקומי אי אפשר להגיע ל-30. (3) **HSL S של השולחן** עולה ל-63, כי ב-HSL הרוויה מתנפחת כשהבהירות עולה, גם בלי שינוי בכרומה. בעין השולחן לא רווי מדי. (4) החלון ב-98.3 (הסף 97): אפשר להוריד את התקרה של הכתף ל-0.96.

## המלצה
1. **המסלול המנצח: image-to-image מה-clay. ‏b הוא הבסיס.** הגאומטריה נעולה ל-clay (סטייה ≤0.005), החומרים הכי נקיים, האור רך, בלי כתם שמש, הפרקט חם (‏S 29.5 גולמי), והכורסה מתחת לאדן (0.020 fw, על הגבול). ‏a נעול באותה מידה, אבל כהה יותר, הפרקט שלו אפרפר (S 24.8), יש בו כתם אור שנראה כמו שמש, ומסגרת הכורסה כהה מהשולחן. ‏text יפה, אבל זה חדר אחר (פינה ב-0.49, כורסה אחרת ונוגעת באדן). לא להשתמש בו.
2. **להציג למשתמש את `m0-pilot-b-graded.png`** (לצד `compare.jpg`). זו התמונה הקרובה ביותר לרף "מגזין עיצוב".
3. **שתי החלטות ל-master-designer לפני 4K:** יעד ה-L של קיר החלון (M0-19), וסף צל המגע ≥30 מתחת לספה (גם ה-clay ב-L 3). החשיפה הגולמית של nano-banana-2 נמוכה ב-כ-0.5 סטופ בשני הפיילוטים (גם בקודם), כך שגריידינג גלובלי צריך להיות שלב קבוע בתהליך, ולא חריג.
4. **ב-4K:** אותו פרומפט, ולבדוק בכל ניסיון את הכורסה מול האדן. ב-b הכרית עלתה ב-0.010 v, ונשאר רווח של 0.020 fw בלבד.
