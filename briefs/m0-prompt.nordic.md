# פרומפט מאסטר M0 — סלון נורדי (מעטפת ורהיטים קבועים)

> master-designer. גרסה 1.1, 2026-10-03 (גרסה 1.0 מ-2026-10-02). נגזר מ-`briefs/motion-direction.nordic.md` 1.2.
> **מקור הנתונים:** כל מידה, חומר, צבע ומיקום לקוחים מ-`docs/design-bible/nordic.md` (1.2), `docs/skeleton-spec.md` (עדכון 2026-10-03) ו-`data/slots/living-room.json`. מ-Astra נלקחו ניסוחים בלבד (`briefs/astra/motion-direction-review.md`).
> **מה ב-M0:** מעטפת החדר ו-3 הרהיטים הקבועים בלבד. אין מוצרים מתחלפים, אין אביזרים (ענפים, עץ, נרות, עיתונים), אין שטיח ואין מנורות.
> **מתי מריצים (אושר 2026-10-03):** המשתמש אישר את הגאומטריה (הצעות 7.7 ו-7.8, ותלויה ב-2.05) ואת רינדור M0 **עכשיו, לפני אישור 2**: מעטפת ורהיטים קבועים בלבד. שום שכבת מוצר לא מרונדרת לפני אישור 2.
> **בלוק-אאוט:** motion-agent בונה אותו במקביל, לפי סעיפים 2–3. הקואורדינטות בסעיף 2 תואמות את השלד. ב-1.1 תוקנו שתי שורות בטבלת 2.1 (כורסה ואהיל התלויה), ונוספה בדיקת משיק בין הכורסה לספה (סעיף 2.1).

---

## 1. בקצרה
| פרמטר | ערך |
| --- | --- |
| מודל ראשי | **nano-banana-2**, image-to-image, 4K. תמונת הקלט היא רינדור ה-clay של הבלוק-אאוט (סעיף 3) |
| גרסה חלופית | אותו מודל, טקסט בלבד (סעיף 5), אם הבלוק-אאוט לא מוכן או לא מחזיק. אפשר גם ריצת השוואה אחת ב-gpt-image-2 בפיילוט, אבל לא לנכס הסופי, כי הוא לא מגיע ל-4K |
| יחס גובה-רוחב | **16:9** |
| רזולוציה | 4K ב-16:9 (3840×2160, או ה-4K שהמודל מחזיר ב-16:9), אחר כך topaz ×2 (כ-7680×4320), ואז הקטנה ל-**6144×3456** (6K, לפי השלד) |
| רפרנסים | **רק** רינדור ה-clay של הבלוק-אאוט, באותו יחס ובאותה מצלמה. בלי תמונות מוצר, כי לרהיטים הקבועים אין כרטיסים. **אסור לצרף** את רינדורי הבדיקה הקודמים (`room-white`, `hall` וכו'), כי יש בהם כתמי שמש, גוון ורוד ופריסה אחרת. בלי לוח דוגמיות צבע: המודל נוטה "להדביק" אותו לתמונה |
| ניסיונות | פיילוט ב-2K: 2 ניסיונות עם בלוק-אאוט ו-1 טקסט בלבד. אחר כך 3 ניסיונות ב-4K במסלול שניצח |
| עלות משוערת | **כ-2,850 קרדיטים** (טווח 2,850–3,700). פירוט בסעיף 9 |
| תיעוד | הפרומפט, תמונת הקלט, ההגדרות והתוצאה נשמרים ב-`assets/prompts/m0.nordic/`, כי אין seed במודל הזה |

---

## 2. גאומטריה: מקור לבלוק-אאוט, לפרומפט ול-QA
**מערכת צירים** (מטרים): הראשית ברצפה, בנקודה שבה ציר החדר פוגש את הקיר האחורי. X ימינה, Y מהקיר האחורי לכיוון המצלמה, Z למעלה. ציר החדר הוא X=0, והוא עובר דרך מרכז הספה, מרכז התמונה העתידית, הפתח והמצלמה ("ציר הבית").

| רכיב | ערכים | מקור |
| --- | --- | --- |
| חדר | קיר שמאל X=−1.80, קיר ימין X=+1.90, קיר אחורי Y=0, קיר קדמי Y=6.90. תקרה Z=2.70 | תקרה: Bible. רוחב ועומק: שלד (אושר 2026-10-03) |
| פתח כניסה | בקיר הקדמי, X −0.45 עד +0.45, גובה 2.10. לא בפריים של M0 | שלד (אושר 2026-10-03) |
| חלון | בקיר השמאלי. הפתח ב-Y 0.60–2.40 (רוחב 180), ב-Z 0.45–2.35 (אדן 45, ראש ישר 235). שתי כנפיים, עמוד אמצעי של 6 ס"מ ב-Y=1.50, מסגרת עם פרופיל נראה של 6, אדן פנימי שבולט 4 | Bible ושלד |
| שיפולים | 8 ס"מ, בצבע הקיר | Bible |
| פרקט | לוחות ברוחב 20 ובאורך 180–220, **לאורך ציר Y** (מהמצלמה לקיר האחורי) | Bible. הכיוון: שלד (אושר 2026-10-03) |
| ספה | X −1.10 עד +1.10, Y 0.03–0.95. משענת 0.78, מושב 0.44, משענות יד 0.60 (רוחב 14). 4 רגליים בפינות, 5 ס"מ פנימה מהקצוות | Bible |
| שולחן קפה | מרכז (0, 1.72). Y 1.37–2.07, כלומר 42 ס"מ מהספה. 1.40×0.70, גובה 0.38, משטח 3 ס"מ. 4 רגליים בקוטר 5, שנסוגות 12 ס"מ מהקצה | Bible |
| כורסה | מרכז (−1.22, 2.90). **מסובבת 35°**: מכוונת ימינה (+X) ומוטה לכיוון השולחן. 0.72×0.78×0.76, מושב 0.40 | Bible 1.2 (אושר 2026-10-03) |
| נקודת תלייה | תקרה ב-(0, 1.72). לא בפריים (התקרה נראית רק עד Y≈1.43) | Bible ושלד (אושר 2026-10-03) |
| **מצלמה** | (0, 6.40, 1.20), מבט ל-−Y, ישרה (tilt 0, roll 0). 24 מ"מ ב-full frame (חיישן 36×20.25 ב-16:9). shift אנכי של כ-−2.9 מ"מ (ב-Blender: `shift_y` ≈ −0.080), מכוונן כך שקו התקרה יתפוס 8% מגובה הפריים | שלד (אושר 2026-10-03): המיקום, 120 ס"מ ו-24 מ"מ |

**מוצרים עתידיים (לא ב-M0, רק כשכבת בדיקה בבלוק-אאוט):** התמונה מרכזה ב-(0, 0, 1.475), במידות 1.55×1.00. אהיל התלויה ב-(0, 1.72), בקוטר 45, עם תחתית ב-2.05 וראש ב-2.32. פלטת מנורת הקיר ב-(−1.80, 2.88, 1.47). השטיח ב-X ±1.45 וב-Y 0.72–3.12. העציץ ב-(−1.45, 0.35). מנורת הרגל בערך ב-(1.35, 0.30). הפוף בערך ב-(0.95, 2.45).

### 2.1 איפה דברים נופלים בפריים (חישוב חור-סיכה, לבדיקת QA)
קואורדינטות יחסיות, x משמאל ו-y מלמעלה. הסבילות היא ±0.02 במסלול עם הבלוק-אאוט, ו-±0.05 בטקסט בלבד.

| רכיב | x | y |
| --- | --- | --- |
| רצועת התקרה (מעל הקיר האחורי) | 0.31–0.70 | 0.00–0.08 |
| קיר אחורי | 0.31–0.70 | 0.08–0.58 |
| קו האופק (גובה המצלמה) | — | 0.36 |
| ספה | 0.36–0.64 | 0.44–0.62 |
| שולחן קפה | 0.39–0.61 | 0.55–0.69 |
| כורסה (כולה) | 0.17–0.37 | 0.50–0.84 (1.1: תוקן מ-0.78. הפינה הקרובה, בערך (−1.33, 3.42), נוחתת ב-y 0.835) |
| פתח החלון | 0.20–0.29 | הראש 0.02–0.12 (נסוג), האדן 0.51–0.58 |
| קיר שמאל פנוי קדימה מהחלון (Y 2.40–4.00, כ-160 ס"מ) | 0.00–0.20 | — |
| קיר ימין, רציף וריק | 0.70–1.00 | — |
| רצפה ריקה בחזית | — | 0.84–1.00 בכל הרוחב; 0.79–1.00 מימין ל-x 0.37 |
| בדיקה: התמונה העתידית | 0.42–0.58 | 0.21–0.40 |
| בדיקה: אהיל התלויה | 0.47–0.53 | 0.06–0.15 (מעל התמונה, ברווח של כ-6%. 1.1: תוקן מ-0.07–0.14, שחושב רק על ציר האהיל ובלי הקוטר) |
| בדיקה: פלטת מנורת הקיר | 0.16 | 0.27 |

**ממצא לתלויה (אושר 2026-10-03: תחתית ב-2.05):** תנאי ה-5% בין האהיל לתמונה מתקיים רק כשתחתית האהיל לפחות ב-2.00 מ' (בתמונה בגובה 100, ובאהיל בקוטר 45–50, כשהנקודה הקובעת היא השפה האחורית של התחתית). בתחתית של 1.95 הרווח יורד לכ-3.7% (1.1: ב-1.0 נכתב 4.6%, בחישוב על ציר האהיל בלבד). ב-2.05 הרווח כ-6%.

**בדיקת משיק בין הכורסה לספה (1.1, ל-motion-agent ול-QA):** בחישוב, הפינה הקדמית של הכורסה (בערך (−0.69, 2.97)) והפינה השמאלית-קדמית של הספה (−1.10, 0.95) נופלות שתיהן ב-x≈0.365, בגבהים חופפים (y 0.57–0.62). בפריים הן עלולות "לגעת" זו בזו, וזה משיק שסותר את M0-07. זה לא שגיאה בקואורדינטות, אלא תוצאה שלהן. בבלוק-אאוט בודקים את ה-clay של M0: אם יש מגע או רווח קטן מ-0.01 מרוחב הפריים בין הצלליות, motion-agent לא משנה מיקום בעצמו, אלא מעביר ל-master-designer לפני כל רינדור.

**הערה על הקומפוזיציה:** ב-M0 לבדו המשקל נופל לשמאל (חלון וכורסה), והקיר הימני ריק. זה מכוון: מנורת הרגל, הסל, קישוט הקיר והפוף מאזנים אותו בסצנה המלאה. QA לא פוסל את M0 על חוסר איזון.

---

## 3. הבלוק-אאוט (תמונת הקלט)
- **מה:** מודל של קופסאות וגלילים במידות של סעיף 2. בספה רואים 3+3 כריות כקופסאות נפרדות, משענות "track" ו-4 רגליים. השולחן בצורת סופר-אליפסה עם 4 רגליים. בכורסה רואים מסגרת, משענות שטוחות וכריות. בחלון רואים כנפיים, עמוד ומסגרת. את השיפולים, האדן והפתח בקיר הקדמי מבנים, גם אם הם מחוץ לפריים.
- **חומרים:** clay אפור אחיד (בערך #BDBBB7), בלי טקסטורות. הרצפה מעט כהה יותר, כדי שקו הרצפה-קיר ייקרא.
- **אור:** שמיים מפוזרים שנכנסים **רק** דרך החלון (בלי שמש ובלי אור עולם מבחוץ, חוץ מהחזרה). כך כיוון הצל והדעיכה בתמונת הקלט כבר נכונים.
- **תוצרים:** כולם באותה מצלמה וביחס 16:9 ב-3840×2160: `m0.clay.png` (הקלט ל-var2), `m0.depth.exr` (עומק מטרי) ו-`m0.depth16.png`, `m0.lines.png` (קווי מתאר), `m0.camera.json`, `plan.png` (מבט על), ו-`m0.overlay.png` (שכבת הבדיקה של המוצרים העתידיים, ל-QA בלבד).
- **כלי:** Blender במצב headless (`bpy`) עם Cycles, או three.js. אין עלות בקרדיטים.
- **מבצע (2026-10-03):** motion-agent, במקביל להכנת M0. master-designer מאשר את ה-clay ואת שכבת הבדיקה לפני כל קרדיט, כולל בדיקת המשיק בין הכורסה לספה (סעיף 2.1).

---

## 4. הפרומפט הראשי (image-to-image על הבלוק-אאוט)
**תמונת קלט:** `m0.clay.png`. **יחס:** 16:9. **רזולוציה:** 2K בפיילוט, 4K בסופי.

```text
Use the attached grey clay render as the exact layout and camera. Keep every wall, the window opening, the floor and ceiling lines, the camera height, the lens, and the position, size and angle of all three furniture pieces exactly as they are in the render. Do not move, resize, add or remove anything. Only replace the clay with real materials and real daylight.

Photorealistic editorial interior photograph for an accessible-premium Nordic home brand: a quiet, believable residential living room on a bright winter morning, photographed in the manner of restrained Scandinavian architectural photography. Level camera, perfectly vertical lines, calm one-point perspective, generous empty floor and wall space, credible residential scale.

Architecture: ceiling height 2.70 m. Smooth matte painted walls and ceiling in warm off-white, target colour #F4F1EC, with a barely perceptible roller texture and no sheen. Slim 8 cm skirting boards painted the same colour as the walls. Pale whitewashed oiled oak plank floor, planks 20 cm wide and about 2 m long running from the camera toward the back wall, average tone #D6BF9E, matte, with natural non-repeating grain and fine seams.

One window only, in the left wall: a tall rectangular opening 180 cm wide and 190 cm high, sill at 45 cm, flat head at 235 cm. Two casements with a single slim 6 cm central mullion; no glazing bars, no transom, no arch. Slim painted wooden frame in warm off-white #F4F1EC with a 6 cm visible profile, and a shallow painted wooden inner sill. The window is bare: no curtains, no curtain rod, no blinds, nothing on the sill. Outside, a pale overcast sky and softly blurred bare winter trees.

Exactly three furniture pieces:
1. Sofa, centred against the back wall: a low, straight three-seat sofa, 220 cm wide, 92 cm deep, 78 cm back height, 44 cm seat height. Thin track arms, 14 cm wide and 60 cm high, with softly rounded 3 cm edges. Three separate seat cushions and three separate back cushions, with simple plain seams. Upholstered in a coarse-weave cotton-linen fabric with visible slub, matte, oatmeal, target #E6DCCB. Four round solid-oak legs with 15 cm visible, tapering from 4 cm to 2.5 cm, natural oil finish, target #C8A27A.
2. Coffee table, centred 42 cm in front of the sofa: a superellipse top (a soft rounded rectangle with straight sides), 140 x 70 cm, 3 cm thick, 38 cm high, solid oak, natural oil, matte, target #C8A27A. Four round 5 cm legs set back 12 cm from the edge, standing vertically. The tabletop is completely empty.
3. Armchair, on the left side of the room in front of the window and turned about 35 degrees toward the coffee table: a lounge chair with an exposed solid-oak frame, natural oil, matte, target #C8A27A, with flat 6 cm wooden armrests; 72 cm wide, 78 cm deep, 76 cm high, 40 cm seat. Upholstered seat and back cushions in mist-grey wool bouclé with small matte loops, target #D9D6D0. The armchair's cool neutral grey must read clearly different from the warm oatmeal of the sofa.

Camera: standing just inside the doorway on the room's centre axis, 6.4 m from the back wall, 1.20 m above the floor, perfectly level, full-frame 24 mm lens equivalent with vertical lens shift like an architectural tilt-shift lens. Verticals perfectly straight. The ceiling shows only as a thin band at the top of the frame. All three furniture pieces are complete and nothing touches the frame edges.

Light: 10:30 on a winter morning, bright sky with thin high cloud. Soft diffuse north light enters only through the left window and falls off gently across the room. The wall beside the window is the brightest wall, and the back-right corner is about half a stop darker, in one smooth continuous gradient with no patches. Broad soft shadows fall to the right and slightly toward the camera, with short, dark, delicate contact shadows under every leg and under the sofa. Warmth comes from the oak and the upholstery, not from the light. Neutral white balance at 5000 K: the walls read warm white, never pink, peach, yellow or blue. The window is the brightest area in the frame but is not blown out. No direct sun, no sun patches, no light beams, no leaf or window-frame shadows. No lamps and no artificial light.

Photographic finish: deep focus, with everything sharp from the nearest floor to the back wall. Restrained contrast with slightly lifted blacks, neutral warm mid-tones, natural colour slightly below full saturation. Crisp, believable material detail: woven fibres and slub in the sofa fabric, distinct loops in the bouclé, continuous oak grain, very subtle wall texture. No film grain, no vignette, no glow.

An empty, quiet room: bare walls, an empty tabletop, bare floor with no rug, and nothing else in the room.

Avoid: sunlight, sun patches, pink or orange cast, curtains, lamps, rugs, cushions, throws, plants, decor, artwork, extra furniture, mirrors, glass objects, text, people.
```

---

## 5. הגרסה החלופית (טקסט בלבד, בלי תמונת קלט)
מתי משתמשים בה: אם הבלוק-אאוט לא מוכן, אם המודל משאיר מראה של clay, או אם הוא מזיז רהיטים בפיילוט. הקומפוזיציה כתובה כאן במילים ובאחוזי פריים, כי אין תמונה שתחזיק אותה. ההצמדה לגאומטריה חלשה יותר, ולכן הסבילות ב-QA היא ±0.05.

```text
Photorealistic editorial interior photograph for an accessible-premium Nordic home brand: a quiet, believable residential living room on a bright winter morning, photographed in the manner of restrained Scandinavian architectural photography. Wide 16:9 frame, one-point perspective looking straight at the back wall, level camera, perfectly vertical lines, generous empty space, credible residential scale.

Room and camera: the room is 3.7 m wide with a 2.70 m ceiling. The camera stands just inside the doorway on the room's centre axis, 6.4 m from the back wall, 1.20 m above the floor, perfectly level, full-frame 24 mm lens equivalent with vertical lens shift (architectural tilt-shift lens), not tilted. Composition: the back wall fills the middle 40% of the frame width. The ceiling shows only as a thin band across the top 8% of the frame. The horizon sits about one third down the frame. The left wall recedes along the left side of the frame and the right wall along the right side, both straight and plumb. The bottom sixth of the frame is empty oak floor.

Architecture: smooth matte painted walls and ceiling in warm off-white, target colour #F4F1EC, with a barely perceptible roller texture and no sheen. Slim 8 cm skirting boards painted the same colour as the walls. Pale whitewashed oiled oak plank floor, planks 20 cm wide and about 2 m long running toward the back wall, average tone #D6BF9E, matte, with natural non-repeating grain. The right wall is completely plain, with no openings.

One window only, in the left wall, starting 60 cm from the back corner: a tall rectangular opening 180 cm wide and 190 cm high, sill at 45 cm, flat head at 235 cm. Two casements with a single slim 6 cm central mullion; no glazing bars, no transom, no arch. Slim painted wooden frame in warm off-white #F4F1EC with a 6 cm visible profile, and a shallow painted wooden inner sill. The window is bare: no curtains, no rod, no blinds, nothing on the sill. Outside, a pale overcast sky and softly blurred bare winter trees. In front of the window, toward the camera, at least 1.6 m of plain wall is visible.

Exactly three furniture pieces:
1. Sofa, centred against the back wall and on the centre line of the frame: a low, straight three-seat sofa, 220 cm wide, 92 cm deep, 78 cm back height, 44 cm seat height. Thin track arms, 14 cm wide and 60 cm high, with softly rounded 3 cm edges. Three separate seat cushions and three separate back cushions, with simple plain seams. Coarse-weave cotton-linen upholstery with visible slub, matte, oatmeal, target #E6DCCB. Four round solid-oak legs with 15 cm visible, tapering from 4 cm to 2.5 cm, natural oil, target #C8A27A.
2. Coffee table, centred 42 cm in front of the sofa: a superellipse top (a soft rounded rectangle with straight sides), 140 x 70 cm, 3 cm thick, 38 cm high, solid oak, natural oil, matte, target #C8A27A. Four round 5 cm legs set back 12 cm from the edge, standing vertically. The tabletop is completely empty.
3. Armchair, in the lower-left third of the frame, 3.5 m from the camera, just forward of the window, with its back toward the left wall and turned about 35 degrees toward the coffee table, fully in frame with clear space to the left edge: a lounge chair with an exposed solid-oak frame, natural oil, matte, target #C8A27A, with flat 6 cm wooden armrests; 72 cm wide, 78 cm deep, 76 cm high, 40 cm seat. Upholstered seat and back cushions in mist-grey wool bouclé with small matte loops, target #D9D6D0. Its cool neutral grey reads clearly different from the warm oatmeal of the sofa.
Clear floor runs between the armchair and the table. No piece overlaps another.

Light: 10:30 on a winter morning, bright sky with thin high cloud. Soft diffuse north light enters only through the left window and falls off gently across the room. The wall beside the window is the brightest wall, and the back-right corner is about half a stop darker, in one smooth gradient. Broad soft shadows fall to the right and slightly toward the camera, with short, dark, delicate contact shadows under every leg and under the sofa. Warmth comes from the oak and the upholstery, not from the light. Neutral white balance at 5000 K: the walls read warm white, never pink, peach, yellow or blue. The window is the brightest area but is not blown out. No direct sun, no sun patches, no light beams, no leaf or window-frame shadows. No lamps and no artificial light.

Photographic finish: deep focus, with everything sharp from the nearest floor to the back wall. Restrained contrast with slightly lifted blacks, neutral warm mid-tones, natural colour slightly below full saturation. Crisp, believable material detail: woven fibres and slub in the sofa fabric, distinct loops in the bouclé, continuous oak grain. No film grain, no vignette, no glow.

An empty, quiet room: bare walls, an empty tabletop, bare floor with no rug, and nothing else in the room.

Avoid: sunlight, sun patches, pink or orange cast, curtains, lamps, rugs, cushions, throws, plants, decor, artwork, extra furniture, mirrors, glass objects, text, people.
```

---

## 6. Negative prompt (משותף לשתי הגרסאות)
אם למודל אין שדה negative, השורה "Avoid:" שבסוף כל פרומפט מחליפה אותו. אם יש שדה, מכניסים אליו את הרשימה המלאה:

```text
direct sunlight, sun patches, sunbeams, god rays, golden-hour light, hard window-grid shadows, leaf shadows, dappled light, pink walls, peach cast, magenta tint, lilac tint, orange colour grading, teal-and-orange, yellowed whites, pure white walls, bluish or cold whites, dramatic cinematic lighting, bloom, glow, haze, fog, HDR look, HDR halos, excessive sharpening, film grain, vignette, shallow depth of field, bokeh, blurred furniture, waxy fabric, plastic-looking wood, printed wood grain, repeating textures, glossy surfaces, varnish shine, chrome, brass, gold, glass objects, mirrors, fisheye, stretched edges, ultra-wide distortion, tilted camera, converging verticals, keystone, dutch angle, warped architecture, curved walls, oversized room, huge empty hall, floating furniture, duplicated objects, extra furniture, altered furniture geometry, asymmetrical table, oval table with pointed ends, splayed or angled legs, hairpin legs, metal legs, turned legs, tufting, buttons, rolled arms, skirted sofa, chaise, sectional sofa, malformed chair frame, arched window, window grid, glazing bars, transom, French doors, second window, radiator, air conditioner, power outlets, light switches, ceiling light, pendant lamp, floor lamp, wall lamp, candles, curtains, curtain rod, blinds, rug, cushions, throw, blanket, plants, flowers, branches, vases, books, magazines, artwork, frames, sculptures, shelves, television, people, animals, text, logos, watermarks
```

---

## 7. אחרי שה-M0 מאושר: פירוק לשכבות השלד (לא חלק מהפרומפט)
השלד דורש מעטפת בלי רהיטים (z 0), שכבת רהיטים קבועים (z 40) ושכבת הצל שלהם (z 34).
1. **מעטפת ריקה:** עריכה ב-nano-banana-2 על M0 המאושר: `Remove the sofa, the coffee table and the armchair, together with their shadows. Keep every other pixel unchanged: same walls, floor, window, light and camera. Restore the floor and the skirting naturally where the furniture stood.` QA: ΔE ≤1 מחוץ לאזור הרהיטים והצל.
2. **רהיטים:** מסכה מהבלוק-אאוט (מיושרת ל-M0), או remove-background על M0, ואחר כך ניקוי ידני של קצוות הרגליים.
3. **צל:** ההפרש בין M0 למעטפת הריקה, בתוך המסכה המורחבת של הצל, נשמר כשכבת multiply. כך הוא תקף על כל שטיח.

---

## 8. תנאי קבלה ל-M0 (ל-qa-agent)
כל הבדיקות נעשות על ה-4K לפני ההגדלה, ושוב על ה-6K אחרי ההגדלה (בדיקות טקסטורה M0-24 עד M0-26). מדידות צבע: ממוצע של כתם בגודל 1% מרוחב הפריים, בלי הבהקים ובלי צללים, ב-HSL.

### גאומטריה ומצלמה
| # | תנאי | סף |
| --- | --- | --- |
| M0-01 | אנכיים (פינות קירות, מסגרת החלון, רגליים) | סטייה של ±0.5° לכל היותר |
| M0-02 | רצועת התקרה מעל הקיר האחורי | 6–10% מגובה הפריים |
| M0-03 | מיקומי הרכיבים מול הטבלה בסעיף 2.1 (שכבת overlay של הבלוק-אאוט) | ±0.02 (בגרסה החלופית ±0.05) |
| M0-04 | פרספקטיבה של נקודה אחת: קווי הרצפה והתקרה של הקירות הצדדיים נפגשים בנקודה אחת בגובה האופק, ב-x 0.48–0.52 | — |
| M0-05 | קנה מידה: היחס בין רוחב הספה לגובה המשענת (בחזית, במבט ישר) | 2.82, בסטייה של עד ±6%. בפריים, הרוחב של השפה הקדמית של השולחן הוא 0.80 מרוחב החזית של הספה, בסטייה של עד ±0.05 (בגלל הפרספקטיבה. בתוכנית 140/220 = 0.64) |
| M0-06 | הקיר השמאלי הפנוי קדימה מהחלון | לפחות 140 ס"מ (בבלוק-אאוט: 160). אין עליו כלום |
| M0-07 | אף רהיט לא נוגע בשולי הפריים, ושום רהיט לא מסתיר רהיט אחר או משיק לו (בדגש על הכורסה מול הפינה השמאלית-קדמית של הספה, ב-x≈0.365) | לפחות 0.05 מכל שוליים. בין צלליות של רהיטים לפחות 0.01 |
| M0-08 | הפתח, הקיר הקדמי ונקודת התלייה | לא בפריים |

### אדריכלות
| # | תנאי |
| --- | --- |
| M0-09 | חלון אחד בלבד, בקיר השמאלי. מלבן עם ראש ישר, שתי כנפיים ועמוד אמצעי אחד. בלי סורג, בלי אשנב, בלי קשת. מסגרת בלבן חם עם פרופיל דק. החלון ריק: בלי וילון, בלי מוט ובלי תריס |
| M0-10 | הקיר הימני רציף וריק. אין פתחים, שקעים, מתגים, מזגן או רדיאטור באף קיר |
| M0-11 | שיפולים בגובה כ-8 ס"מ, בצבע הקיר, רציפים וישרים (לא גליים, לא נקטעים) |
| M0-12 | פרקט בלוחות ברוחב כ-20 ס"מ, לאורך ציר החדר. התפרים ישרים ומתכנסים לנקודת המגוז. אין דוגמת עץ שחוזרת על עצמה בין לוחות סמוכים |

### רהיטים קבועים
| # | תנאי |
| --- | --- |
| M0-13 | **ספה:** ישרה ונמוכה, 3 כריות מושב ו-3 כריות גב נפרדות, משענות "track" דקות, 4 רגלי אלון עגולות ומתחדדות. בלי קפיטונאז', בלי חצאית ובלי משענות מגולגלות |
| M0-14 | **שולחן:** סופר-אליפסה (צלעות ישרות ופינות מעוגלות, לא אליפסה מחודדת). משטח דק, 4 רגליים עגולות וזקופות שנסוגות מהקצה. המשטח ריק |
| M0-15 | **כורסה:** משמאל, לפני החלון (קרובה לקיר יותר מהשולחן), מוטה לכיוון השולחן ב-25–40°. מסגרת אלון גלויה, משענות עץ שטוחות, ריפוד בוקלה עם לולאות נראות |
| M0-16 | בדיוק 3 רהיטים. אין שום חפץ נוסף בחדר, כולל שטיח, מנורה, צמח, תמונה או טקסטיל |

### אור
| # | תנאי | סף |
| --- | --- | --- |
| M0-17 | אין כתמי שמש, קרני אור, צללי עלים או צל של רשת החלון | אפס |
| M0-18 | כיוון הצל: ימינה ומעט לכיוון המצלמה, בכל הרהיטים. צללי הטלה רכים (פנומברה של 30% לפחות מגובה החפץ), וצל מגע כהה וקצר מתחת לכל רגל | — |
| M0-19 | דעיכה בקיר האחורי, רציפה ובלי כתם: ליד הפינה השמאלית, במרכז ובפינה הימנית | L 92–95 · 88–91 · 82–86 (כיוון, בסבילות של ±2) |
| M0-20 | החלון הוא האזור הבהיר ביותר. אין ערוץ RGB של 255 באף משטח. הצל הכהה ביותר (מתחת לספה) לא כהה מ-L 30 | L ≤97 בחלון |
| M0-21 | אין אור מלאכותי: אין זוהר, אין שלולית חמה ואין גוף תאורה | — |

### צבע
| # | תנאי | סף |
| --- | --- | --- |
| M0-22 | קירות ותקרה (5 נקודות: ליד החלון, מרכז, ימין, תקרה, קיר ימני) | H 25–55, S 8–45, L 89–97 (באזור המוצל לפי M0-19). אין H<25 (ורוד) ואין H 180–260 |
| M0-23 | ספה: H 30–45, S 20–45, L 78–90. כורסה: H 25–60 או S≤3, S 0–15, L 76–88. **ההבדל קריא:** הרוויה של הכורסה נמוכה לפחות ב-8 נקודות מזו של הספה. אלון (רגליים, שולחן, מסגרת): H 25–40, S 25–55, L 52–78. פרקט: ממוצע קרוב ל-#D6BF9E, בטווח האלון | — |

### חומר וריאליזם (ב-100%)
| # | תנאי |
| --- | --- |
| M0-24 | בארג הספה רואים קליעה וסלאב, לא משטח חלק. בבוקלה רואים לולאות נפרדות. באלון רואים סיבים רציפים שלא חוזרים |
| M0-25 | אין משטחי "שעווה", אין קצוות נמסים (רגליים, פינות כריות, מסגרת חלון), ואין רגליים כפולות או חסרות |
| M0-26 | אחרי topaz: ההגדלה לא ממציאה דוגמה בבד או בעץ, ואין הילות חידוד. אם יש, משווים ל-4K ומקטינים את עוצמת ההגדלה |

### טכני
| # | תנאי |
| --- | --- |
| M0-27 | 16:9. מאסטר 6144×3456 ועוד ה-4K המקורי. בלי גרעין (הגרעין נוסף בקוד, לפי הכיוון 2.5) |
| M0-28 | הפרומפט, תמונת הקלט, המודל וההגדרות שמורים ב-`assets/prompts/m0.nordic/` |
| M0-29 | אישור master-designer ואחר כך אישור המשתמש, לפני כל פריים אחר |

---

## 9. עלות M0 (בקרדיטים של var2)
| שלב | חישוב | קרדיטים |
| --- | --- | --- |
| בלוק-אאוט ורינדור clay, עומק וקווים | מקומי | 0 |
| פיילוט 2K, המסלול הראשי | 2 × nano-banana-2 2K (400) | 800 |
| פיילוט 2K, הגרסה החלופית | 1 × nano-banana-2 2K | 400 |
| M0 סופי | 3 × nano-banana-2 4K (450) | 1,350 |
| הגדלה | topaz ×2 | 300 |
| **סה"כ** | | **כ-2,850** |
| רזרבה (לא חובה) | ניסיון 4K רביעי (450), והשוואה אחת ב-gpt-image-2 בפיילוט (400) | עד 3,700 |
| פירוק לשכבות (סעיף 7, אחרי האישור) | 2 עריכות × 450, ועוד remove-background (50) | כ-950 |
