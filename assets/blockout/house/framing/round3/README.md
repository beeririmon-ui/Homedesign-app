# Clay סבב 3: פריימי המאסטר לשלב B (2026-10-25)

render-agent · לפי `briefs/nordic-house-render-2026-10-24.md` סעיף 7 ו-`docs/rooms-render-plan-2026-10-25.md` סעיפים 2–3 (master-designer). ‏Blender 4.2 (bpy), ‏Cycles CPU, ‏seed 7, ‏**3840×2160**, ‏36 דגימות עם OIDN. ‏**0 טוקנים של var2.** סבב 2 (`../round2/`) לא השתנה: הקוד שלו רק מיובא. לא שונה שום מסמך מחייב.

## איך מריצים
```
cd assets/blockout/house
python3 framing_r3.py --plan framing/round3/plan.json --frames all --res 3840 --samples 36 --hall-roof 1.6
python3 framing_r3.py --plan framing/round3/plan.json --frames H0,C0 --res 960 --samples 12 --out /tmp/x   # בדיקה מהירה
python3 framing/round3/summarize.py                                                                       # טבלת selfcheck
```
`framing_r3.py` בונה את הסצנה המשולבת של סבב 2 (`framing_r2.build_r2`: תוכנית 1.1 + ה-picks H-B, C-B, W-A, MB-A + ילדים, מקלחת ומטבח של סבב 2 + תוספות S11/S12) ומשנה אותה לפי `plan.json`. ‏`plan.json` נגזר מכותרות ה-`#` של הפרומפטים (`plan_from_headers.py`) ומסעיף 3 של תוכנית הרינדור, ובו לכל פריים: צורות-המקום, המנורות הדולקות, ומה נראה מחדרים שכנים.

## קבצים
| קובץ | מה יש בו |
| --- | --- |
| `<frame>.png` | ‏11 פריימים ב-3840×2160: ‏D1, ‏D2, ‏H0, ‏C0, ‏MB0, ‏K-boy, ‏K-girl, ‏B1, ‏B2, ‏W0 ו-**M0** (clay של M0 v6 עם צורות-מקום, הבחירה הראשונה של המעצב; `living-room/m0-clay-4k.png` נשאר הגיבוי) |
| `overlays/<frame>.png` | שלישים, גיבורים, ו-est מול מדידה |
| `selfcheck.json` | לכל פריים: מצלמה (ערכי 1.1.x מול סבב 2), צורות-המקום שהוצגו, מנורות, est מול מדידה, משיקים (F3), כללי המעצב, צפיפות F10, **תיבות פיקסלים של כל פריט** (`boxes`, לבדיקת ±15% של כל מוצר בטיוטה ולאזורי נעילת ה-clay), **קריאות L של קירות, תקרה ורצפה** (`wall_patches`), מאזן הכניסה מול הסלון (H0), מעבר המראה F8 (B1, ‏B2) |
| `plan.json` | רשימת צורות-המקום, המנורות והנוף לכל פריים (גרסה 1.2) |
| `round2-vs-round3.jpg` | סבב 2 מול סבב 3 לכל פריים |
| `plan_from_headers.py`, `summarize.py` | עזרים |

## מה השתנה מול סבב 2
1. **מצלמות:** ערכי `docs/house-plan.json` 1.1.2 ‏(`cameras`), נבדקו מול המצלמות של סבב 2: זהות בכל 10 הפריימים (`selfcheck.cameras`). ‏M0 לפי `m0-camera.json` ‏(1.25, 5.55, 1.20; ‏yaw 25; ‏u0 0.52, ‏v0 0.46).
2. **רזולוציה 3840×2160** במקום 2048×1152, כדי שנעילת ה-clay תימדד מול רזולוציית הפלט (2K ומעלה).
3. **אלבדו ניטרלי:** כל צורות-המקום בפלטת ה-clay של M0 ‏(`build_alts.PAL`: טקסטיל ‎#D9D2C7, אהיל ‎#E4DFD7, חפץ ‎#C3BCB1, קישוט ‎#C8C2B9) במקום האפורים החמים לכל עמדה של סבב 2 (189 מש). בלוק הצבע בחדרי הילדים (G-K4) הוא מדרגה אפורה ניטרלית ‎#CFCAC3 (הצבע מגיע מהפרומפט). **המנורות ב-2700K אבל כפי שמצלמה מאוזנת ל-4600K רואה אותן:** ‏(1.0, 0.74, 0.45) ליניארי במקום (1.0, 0.56, 0.25) של סבב 2. זה מוריד את הגוון האפרסקי שעבר לטיוטת h0-A ואת הכתום של המקלחת.
4. **צורות-מקום רק למוצרים שברשימת הפריים** (תוכנית הרינדור סעיף 3), **במידות הכרטיס** ולא במקסימום המעטפת (פנס 50×36, ראנר 40×140, אגרטל 26.5, צלחות ברזל + נרות 7×15 / 7×10, כרית ספסל 130×35×3, מטחנות 15, קערה 21×6.4, ערימת צלחות 28, ספלים 9, מעמד נייר 13×31, צנצנות 11 בגבהים 22/18/14, מגבת 22×33, שטיח 230×220, ראנר 60×280; כניסה: תמונה 45×55, כלי 26.5, מגש סגלגל 22×9.5, קוביית בד 15, כרית 110×35×3, שמיכה 33×33, סל 30×26, דלי 19×49; מסדרון: 3 ריבועים 40×40 במרכז Z 1.45, פנסי נייר 40×22 בתחתית 2.45; הורים: 2 × 50×50, מנורות 24×20, אגרטל אדן 8.5×24.7, כיסוי עציץ 35×37, אגרטל 11×24.5 על השידה, צלוחית 9.5×3, פמוטים 7×11, כרית מותן 30×50; ילדים: 2 מדפים 41.9 בכל שורה, 2 כריות 40, בובה 30, סל 35×39, מכוניות 9×5; מקלחת: מנורות 13×16, שטיחון 40×60, מעמד 65, נר 9×9.8, בקבוקים 7.5×16.5, כוס 8×11, אגרטלון 7.6×12.8, סל 43×33×19, מגבת ידיים 38×55; עבודה: שטיח 170, סל 30, פח 25×30, סלי לבד 30×24.5×15, תומכים 10.5×13, כלי עפרונות 8×11 על השולחן; סלון: שלישייה 3×50×70 ברווח 6, שטיח 230×330, אגרטל 31 על האדן, שקע העיצוב מתחת למנורת הקיר, קערה 21). עמדות ריקות: בלי צורה **ובלי האור שלהן** (מנורת השולחן בכניסה, מנורת הקיר במטבח, מנורת הרגל בהורים, התלויה ומנורת הזרוע בילדים, שלוש המנורות בעבודה, פסי מנורות התמונה במסדרון).
5. **מנורות דולקות רק מרשימת הפריים:** ‏D1 פנס + LED מדפים ונישה; ‏D2 ‏LED בלבד; ‏H0 קוביית הבד; ‏C0 שני הפנסים; ‏MB0 זוג מנורות הקיר; ‏B1/B2 מנורת B1, זוג המראה ו-downlight המקלחון ב-4 W; ‏K-boy, ‏K-girl, ‏W0: אף מנורה (אור יום בלבד); ‏M0: תלויה, מנורת רגל, מנורת קיר וזוג הטרוורטין (מקורות אור חדשים, כי ל-clay של M0 לא היו).
6. **הסלון שנראה מ-H0 ומ-C0 הוא ה-clay של M0 v6** עם צורות-המקום שלו ועם המנורות דולקות; הכניסה שנראית מ-C0 היא ה-H0 שנבנה כאן (תמונה, כלי, מגש, דלי). שאר החדרים השכנים: מעטפת ורהיטים קבועים בלבד.
7. **הכניסה כ-2/3 סטופ מתחת לקיר האחורי של הסלון:** חלון הגג של הכניסה ×1.6 (`--hall-roof`), נמדד ב-`light_balance` של H0 (בקיר הגיבור דרך הדלת מול הקיר הקדמי מעל הקונסולה). במקלחת: אור השטח שמחוץ לחלון המחורץ ×3 (`--bath-window`), כפי שהתוכנית מבקשת (הקיר לידו ולא החשיפה הגלובלית).
8. **תיקוני 1.1.x** על צורות-המקום שנשארו: סל הילדים ב-(‎−0.62, 11.58) חתוך בנחישות, התמונות של הילדה ירדו 5 ס"מ, וילון המקלחת אסוף ב-(5.30, 11.15) (הקפלים ממורכזים ב-5.34 כדי שהחפיפה עם קו הפינה ב-B2 תהיה ≥0.03), קבוצת הרצפה במקלחת (מעמד 4.50, פח 4.64, מברשת 4.70/10.30; לא ברשימה), שטיח האוכל X ‏3.45–5.75, מנורת הקיר ומוט הווילון בעבודה (6.65 / 7.00), תלויית העבודה (לא ברשימה). ועוד תיקוני משיקים שהתוכנית ביקשה: ספלים 4 ס"מ מהשוליים הימניים, פמוטים 5 ס"מ ל-‎−X, השמיכה בהורים מתחת לכריות (קו החלטי), עציץ ההורים 1.45→1.48, סל הכניסה בגובה 26, סל ופח בעבודה (‎−1.35, 6.60) ו-(‎−0.30, 6.70), שמיכת הילדים מ-X ‎−0.88, הבובה 30 ס"מ (חוצה את קו האדן בבירור), דלי המטריות 3.42→3.47.

## תוצאות
מ-`selfcheck.json` דרך `summarize.py` (הריצה הסופית):

| frame | room | L (r2) | placeholders | generic | lamps on | est > 0.02 | edge tangents | obj. tangents | designer rules failing | runtime |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| D1 | kitchen-dining | 197.4 (192.0) | 13 | - | dining-pendant, led-niche, led-shelves | curtain stack u (pixels, incl. rod), pendant_v (top 1.78 .. bottom 1.50, centre), table_top_u (pixels incl. legs) | dining chairs (fixed, window side) left 0.0174 | bench-pad/dining chairs (fixed, window side) gap 0.0062; bench-pad/dining table 160x85 (fixed) overlap 0.0156; dining bench (fixed)/dining chairs (fixed, window side) gap 0.0193; dining bench (fixed)/dining table 160x85 (fixed) overlap 0.0156; candle-holders/dining chairs (fixed, window side) overlap 0.0234; candle-holders/curtains gap 0.0114; dining chairs (fixed, window side)/curtains overlap 0.0234; dining chairs (fixed, window side)/centerpiece-vase gap 0.0176; dining chairs (fixed, window side)/window W-dining gap 0.0039; dining-rug/kitchen-runner gap 0.0157; dining table 160x85 (fixed)/kitchen-runner overlap 0.0156 | none | 935 s |
| D2 | kitchen-dining | 178.2 (184.5) | 11 | - | led-niche, led-shelves | coffee niche u (front Y 4.55 / 5.20) | dining bench (fixed) bottom 0.019 | bench-pad/dining table 160x85 (fixed) overlap 0.0234; dining bench (fixed)/dining table 160x85 (fixed) overlap 0.0234; dining-rug/kitchen-runner gap 0.0195; dining table 160x85 (fixed)/kitchen-runner overlap 0.0234 | none | 968 s |
| H0 | hall | 174.6 (162.4) | 24 | - | wall-sconce, accent-sconces, floor-lamp, pendant, wall-sconce | none | none | basket/bench-cushion gap 0.018 | none | 1122 s |
| C0 | corridor | 190.6 (186.8) | 21 | - | ceiling-lights, accent-sconces, floor-lamp, pendant, wall-sconce | none | none | none | none | 2251 s |
| MB0 | master | 193.3 (204.1) | 12 | sill-vase, trinket-dish | bedside-sconces | bed_head_v (headboard top Z 1.15) | none | curtains/nightstands 45 gap 0.002 | none | 956 s |
| K-boy | boy | 151.9 (166.0) | 9 | - | none | roman-blind bottom v (Z 1.85 at the jamb), mattress_v (bedding top 0.50 at the front: far / near corner), toy-basket_v (pixels), paint line v (Z 1.25: corner / desk) | none | cushions/bedspread gap 0.0161; bedding/toy-basket overlap 0.0234; toy-basket/bedspread overlap 0.0117; soft-toy/window W-boy overlap 0.0039 | skateboard covers the front-left desk le | 904 s |
| K-girl | girl | 150.3 (172.3) | 10 | - | none | roman-blind bottom v (Z 1.85 at the jamb), mattress_v (bedding top 0.50 at the front: far / near corner), framed-prints_u (pixels), toy-basket_v (pixels), paint line v (Z 1.25: corner / desk) | none | cushions/bedspread gap 0.0161; bedding/toy-basket overlap 0.0273; toy-basket/bedspread overlap 0.0039; soft-toy/window W-girl overlap 0.0039 | doll-pram covers the front-left desk leg | 792 s |
| B1 | bath | 170.3 (139.2) | 8 | - | shower-downlight, vanity-sconces, wall-sconce | wc + ledge u (pixels), shower east wall u (X 5.20 .. corner), curtain stack u (pixels) | none | window W-bath/bath WC + limestone ledge (fixed) gap 0.0137 | curtain stack vs the SE corner line (B1, | 931 s |
| B2 | bath | 149.1 (136.7) | 9 | - | shower-downlight, vanity-sconces | curtain stack u (pixels) | none | none | curtain stack vs the SE corner line: ove | 921 s |
| W0 | work | 178.2 (199.7) | 8 | desk-organizer | none | none | none | basket/rug gap 0.0156; basket/desk chair gap 0.0137; rug/waste-basket gap 0.0098 | none | 788 s |
| M0 | | not rendered | | | | | | | | |

D1 wall patches L: {'hero_wall_high': 89.7, 'kitchen_wall': 73.1, 'ceiling': 71.3, 'floor_centre': 68.0}
D2 wall patches L: {'hero_wall_high': 76.4, 'hero_wall_mid': 68.3, 'tall_units': 69.6, 'ceiling': 69.2, 'floor_centre': 68.8}
H0: living - hall = 0.4 stops (pass False); QA point (0.35,0.40) - facing wall = 9.5 L
H0 wall patches L: {'hero_wall_mid': 70.7, 'living_vista': 80.1, 'ceiling': 74.3, 'floor_centre': 58.2}
C0 wall patches L: {'hero_wall_mid': 87.1, 'right_wall': 78.5, 'ceiling': 68.0, 'floor_centre': 71.7}
MB0 wall patches L: {'hero_wall_mid': 78.2, 'wainscot': 72.5, 'ceiling': 80.3, 'floor_centre': 47.4}
K-boy wall patches L: {'hero_wall_mid': 73.7, 'paint_block': 69.8, 'ceiling': 66.7, 'floor_centre': 35.8}
K-girl wall patches L: {'hero_wall_mid': 73.6, 'paint_block': 69.9, 'ceiling': 66.8, 'floor_centre': 36.1}
B1 wall patches L: {'hero_wall_high': 74.7, 'hero_wall_mid': 72.6, 'limestone_shower': 67.9, 'wall_beside_window': 81.8, 'ceiling': 72.4, 'floor_centre': 62.5}
B1 mirror F8: pass non-wall []
B2 wall patches L: {'ceiling': 70.7, 'floor_centre': 21.4}
B2 mirror F8: pass non-wall []
W0 wall patches L: {'hero_wall_high': 75.7, 'hero_wall_mid': 75.4, 'ceiling': 75.8, 'floor_centre': 68.4}

cameras identical to round 2: {'D1': True, 'D2': True, 'H0': True, 'C0': True, 'MB0': True, 'K-boy': True, 'K-girl': True, 'B1': True, 'B2': True, 'W0': True, 'M0': False}

### הערות על הסבב הסופי (3840×2160, 36 דגימות)
- **M0 לא רונדר בסבב 3.** הריצה הראשית (D1 → M0) נעצרה באמצע K-girl בהשהיית הסשן (2026-10-25 ~14:50 UTC) והופעלה מחדש ל-K-girl, B1, B2, W0 בלבד; המנהל הנחה שטיוטת M0 משתמשת ב-`assets/blockout/living-room/m0-clay-4k.png` (כותרת `m0-v6.txt` ביקשה clay עם צורות-מקום). ‏`python3 framing_r3.py --plan framing/round3/plan.json --frames M0 --res 3840 --samples 36 --hall-roof 1.6 --no-sheet` משלים אותו (~17 דקות, 0 טוקנים).
- **מאזן הכניסה (H0):** הסלון דרך הדלת גבוה מקיר הכניסה מעל הקונסולה ב-0.4 סטופ (יעד 0.5–0.9; `pass_2_3_stop` False), ומנקודת ה-QA (0.35, 0.40) ב-9.5 L מעל הקיר שמולה (יעד ≥ 8, עובר). מול הקיר מימין לקונסולה ההפרש הוא ~0.65 סטופ. ניסוי חוזר עם חלון הגג ×1.35 (`extra/H0-hallroof-1.35.png`, ‏0.43 סטופ) הזיז את קיר הכניסה פחות מ-1 L: ב-4K חלון הגג אינו המנוף; הכניסה מוארת בעיקר מגלישת הסלון דרך הפורטל וממנורת הקובייה. בדיקות העשן ב-960px הראו רגישות גדולה בהרבה (×1.6 → 0.72), כנראה הבדל בדגימת הטלאים ברזולוציה נמוכה. לא תוקן; מועמד לסבב הבא: `--living-boost` (להעלות את קיר הסלון לכיוון L 88–90 כמו ב-M0) במקום לכבות את הכניסה.
- **המטבח (D1/D2):** הטיוטות של gpt-image-2-5 ציירו את קו המשטח והמדפים 0.02–0.04 מגובה הפריים מעל קווי ה-clay בשתי דגימות של D2 (ב-D1 נעול). ה-clay עצמו לא השתנה; לבדיקת המעצב אם גובה המצלמה 1.1 במטבח (מול 1.2 בשאר) הוא הסיבה.

### כרטיס הטוקנים של שלב B (var2, gpt-image-2-5 sunburst 2K)
‏10 עבודות × 600 = **6,000 טוקנים** (d1, d2, d2-r2, h0-B, c0, mb0, k-boy, k-girl, m0-v6, m0-v6-r2); תקרה 12,000. היתרה בחשבון ירדה ל-360, ולכן **k-girl-r2, b1, b2 ו-w0 לא נשלחו** (צריך 600 לעבודה; 2,400 להשלמה). ה-clay של B1, B2 ו-W0 מוכן ומועלה ל-var2 (`assets/renders/house-nordic-2026-10-25/jobs.json` → `clay`).


## מה נשאר פתוח
- ‏D1: הכיסא בצד החלון 0.017 מהשוליים השמאליים והפסים הדקים בין הספסל, הכרית, הכיסאות והשולחן הם רהיטים קבועים שאין לי סמכות להזיז (תיקוני 1.1.x לרהיטים דורשים את המעצב).
- ‏MB0: הווילון מול השידה השמאלית (0.002) נובע ממיקום החלון והשידה הקבועה; לא תוקן.
- ‏B1/B2: החלון מול מדף האסלה (0.014) והמראה מול הארון (0.02) הם מעטפת. ערימת הווילון מול קו הפינה ב-B2: חפיפה 0.027 (יעד ≥ 0.03; הקפלים כבר הוזזו פעמיים, 5.31 → 0.0215, 5.33 → 0.0246, 5.34 → 0.0272); עוד 2–3 ס"מ ל-+X יסגרו את זה בסבב הבא.
- כללי המעצב "הסקייטבורד / העגלה מכסים את רגל השולחן" נכשלים כי העמדות ריקות בטיוטה הזו (AU2), לא תקלה.
