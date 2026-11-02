# Clay סבב 4: מאסטרי v7 ופוזות המעבר (2026-11-02)

render-agent · לפי `docs/render-wow-pass-2026-11-02.md` §4.1 (המעצב), `docs/transitions-plan-2026-11-02.md` §3 (מסלול R) והוראות המנהל (overscan ו-shift מ-motion-agent, ‏`docs/transitions-render-plan-2026-11-02.md`). ‏Blender 4.2 (bpy), ‏Cycles CPU, ‏seed 7, ‏OIDN. ‏**0 טוקנים של var2.** סבב 3 (`../round3/`) לא נגע: `framing_r4.py` מייבא את `framing_r3.py` ולא משנה אותו.

## איך מריצים
```
cd assets/blockout/house
python3 framing_r4.py --group A --frames all --res 3840 --samples 16 --pose-samples 10                     # M0, D1, D2, MB0, ילדים, מקלחת, W0 + פוזות A
python3 framing_r4.py --group B --frames all --res 3840 --samples 16 --pose-samples 10 --living-boost 6.0  # H0, C0 + H0x, H0e, S1', R2m, MB-in
python3 tone_r4.py --frames M0,D1,...        # חשיפה לכל קבוצה, איזון לבן במקלחת, roll-off לזכוכית, selfcheck.json
python3 framing/round4/summarize_r4.py       # הטבלה למטה
```
הקבוצות נפרדות כי הרמת הסלון (`--living-boost`) היא שינוי אור בסצנה: ב-A הסלון כמו בסבב 3, ב-B חלון הסלון ×6 כדי שהנוף מהכניסה ומהמסדרון יהיה הבהיר ביותר.

## קבצים
| קובץ | מה יש בו |
| --- | --- |
| `<frame>.png` | 11 המאסטרים (clay סופי, אחרי `tone_r4.py`) |
| `poses/<pose>.png` | פוזות המעבר. ‏S1' נשמר כ-`S1prime.png` (בלי גרש בשם קובץ) |
| `overlays/`, `poses/overlays/` | שלישים ו-est מול מדידה, כמו בסבב 3 |
| `selfcheck.json` | לכל still: מצלמה, צורות-המקום, מנורות, תיבות פיקסלים (`boxes`, ב-uv של הקנבס), קריאות קירות לפני/אחרי (`wall_patches`, `wall_patches_render`), החשיפה הסופית והנימוק (`post`), ‏overscan, ‏p99 בחלונות, מאזן הכניסה/סלון |
| `selfcheck-render-A.json`, `selfcheck-render-B.json` | מה ש-`framing_r4.py` מדד ברינדור עצמו (חשיפת רינדור ‎+1.35) |
| `plan.json` | גרסה 1.1: רשימות צורות-המקום של סבב 3 עם שינויי v7, 12 הפוזות, ‏overscan |
| `summarize_r4.py` | הטבלה בקובץ הזה |

ה-EXR של כל still (הקומפוזיט לפני ה-view transform, half float) נשמר ב-scratchpad (`r4-exr/`), לא בריפו.

## מה השתנה מול סבב 3
1. **חשיפה (+1 סטופ בערך):** סבב 3 רונדר ב-‎+0.35. כאן כל still נשמר כ-EXR, ו-`tone_r4.py` מחיל את אותו AgX Medium High Contrast בחשיפה שמביאה את קיר הייחוס שבכותרת ה-v7 ל-L ‏86.5 בערך (טווח 85–90), מוגבלת ל-‎+0.5…‎+1.5 סטופ מעל סבב 3. חשיפה היא כפל ליניארי לפני ה-view transform, ולכן זה זהה לרינדור בחשיפה הזו. **חשיפה אחת לכל קבוצת מצלמה** (M0+M0p+M0x; ‏D1+D2+PD-35; ‏B1+B2+CB-0; ‏H0+H0x+H0e; ‏C0+S1'+R2m; ‏MB0+MB-in; ‏K-boy+K-boy-0; ‏K-girl+K-girl-0; ‏W0+W0-in), כך שאין קפיצת חשיפה בתוך pan או פוזה (תוכנית המעברים 1.5).
2. **H0 ו-C0:** "קירות הכניסה והמסדרון כמו שהם" (כותרות h0-v7, c0-v7), והסלון מורם: ‏`--living-boost 6.0` (נמדד בבדיקות עשן: 1.0 → 0.16 סטופ, 2.0 → 0.26, 5.0 → 0.50, בתצוגה). התוצאה בטבלה.
3. **מקלחת ניטרלית:** איזון לבן בפוסט (grey world על הטונים האמצעיים של B1, 80 % מהתיקון, הבהירות נשמרת), אותם gains ל-B1, ‏B2 ו-CB-0; אור החלון ×4.5 (סבב 3: ×3) כדי שיהיה גרדיאנט משמאל ב-B2.
4. **glass roll-off:** כתף tanh מעל 0.88 לכל ערוץ (תקרה ~0.96), כך שהזכוכית ב-p99 ‏≤ 95.5.
5. **שינויי v7 ב-clay (כותרות הפרומפטים):** ‏M0 בלי wall-decor ובלי מנורת הרגל ובלי האור שלה, זוג הטרוורטין כשתי קוביות 12 ס"מ; ‏H0 ו-C0 בלי מעמד המטריות (גם בנוף); ‏K-boy ו-K-girl בלי הווילון הרומאי; ‏W0 בלי תומכי הספרים, העציץ D38×H34 והצמח עד 1.30 **בפינה ליד החלון** (‎−1.95, 6.70, לפי `data/slots/work.json`, כמו בסבב 3; ריצה ראשונה שמה אותו בטעות ב-(‎−0.20, 6.62) בתוך השולחן, תוקן ורונדר מחדש); ‏D1 פנס 50 שטוח (אליפסואיד 50×30), תחתית 1.50.
6. **overscan (בקשת motion-agent דרך המנהל, 20:27 UTC):** כל still שמשתתף ב-pan של 21° ומעלה רונדר עם כ-3 % נוספים בכל צד: אותה מצלמה, אותו מוקד בפיקסלים, וה-16:9 הוא החיתוך המרכזי. ‏3840×2160 → **4072×2290**, תיבת הפריים x ‏116–3956, ‏y ‏65–2225 (0.0302 / 0.0301 לכל צד). הקנבס נשאר 16:9 כדי שמודל התמונה יקבל את היחס שהוא מרנדר; ה-"16:9 + 6 % גובה" של motion-agent הוא הקנבס חתוך לרוחב הפריים (`-graded-os6.png` בתוצרי v7). חל על: ‏D2, ‏B1, ‏B2, ‏K-boy, ‏K-girl, ‏M0p, ‏M0x, ‏PD-35, ‏K-boy-0, ‏K-girl-0, ‏CB-0. **לא חל על M0 ו-D1:** ה-clay וה-job שלהם נשלחו ב-16:9 לפני הבקשה; פער ה-pan שם נשאר ל-inpainting.
7. **shift של הפוזות (motion-agent §2):** ‏PD-35 ב-0.52/0.46; ‏K-boy-0, ‏K-girl-0, ‏CB-0 ב-0.50/0.46 (שינוי ה-shift עובר ל-pan בקוד). שאר הפוזות לפי טבלת תוכנית המעברים.
8. **דגימות:** 16 למאסטרים ו-10 לפוזות (סבב 3: 36), עם OIDN. ה-clay הוא מדריך למודל שעובד ב-2K; בבדיקה ב-960px ההבדל בין הגדרות הדגימה לא נראה בעין.
9. **R2m:** לא רונדר ולא הולבש. לפי motion-agent הוא נחוץ רק לניסיון חוזר של V6, ולכן ריצת הפוזות של B כללה רק את H0x, ‏H0e, ‏S1' ו-MB-in. אפשר לרנדר אותו בכל עת: `--group B --frames R2m --living-boost 6.0`, ‏0 טוקנים.

## תוצאות
<!-- TABLE -->
| still | file | camera (x, y, z), yaw, u0/v0 | canvas | samples | exposure (round 3 = +0.35) | reference patch: target -> L | glass p99 | lamps lit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M0 | framing/round4/M0.png | (1.25, 5.55, 1.2), 25, 0.52/0.46 | 3840x2160 (no overscan: sent before the request) | 16 | +1.438 (+1.088 stop) | 86.5 -> 86.5 | frame 95.5 | living/accent-sconces, living/pendant, living/wall-sconce |
| D1 | framing/round4/D1.png | (2.8, 3.8, 1.1), -56, 0.52/0.43 | 3840x2160 (no overscan: sent before the request) | 16 | +1.712 (+1.362 stop) | 86.5 -> 86.5 | 95.5 | kitchen-dining/dining-pendant, kitchen-dining/led-niche, kitchen-dining/led-shelves |
| D2 | framing/round4/D2.png | (2.8, 3.8, 1.1), -91, 0.52/0.43 | 4072x2290 (overscan 3 %) | 16 | +1.712 (+1.362 stop) | group PD (set by D1) | frame 95.0 | kitchen-dining/led-niche, kitchen-dining/led-shelves |
| H0 | framing/round4/H0.png | (2.877, 9.039, 1.2), 12, 0.52/0.46 | 3840x2160 | 16 | +0.395 (+0.045 stop) | 89.0 -> 89.0 | frame 94.7 | hall/wall-sconce, living/accent-sconces, living/pendant, living/wall-sconce |
| C0 | framing/round4/C0.png | (2.397, 17.11, 1.2), 0, 0.5/0.46 | 3840x2160 | 16 | +0.376 (+0.026 stop) | 87.1 -> 87.1 | 73.0 | corridor/ceiling-lights, living/accent-sconces, living/pendant, living/wall-sconce |
| MB0 | framing/round4/MB0.png | (-0.7, 21.05, 1.05), 0, 0.5/0.46 | 3840x2160 | 16 | +1.256 (+0.906 stop) | 86.5 -> 86.5 | 95.5 | master/bedside-sconces |
| K-boy | framing/round4/K-boy.png | (1.1, 13.0, 1.0), 33, 0.52/0.44 | 4072x2290 (overscan 3 %) | 16 | +0.85 (+0.5 stop) | 86.5 -> 88.9 | 95.5 | none |
| K-girl | framing/round4/K-girl.png | (1.1, 16.63, 1.0), 33, 0.52/0.44 | 4072x2290 (overscan 3 %) | 16 | +0.85 (+0.5 stop) | 86.5 -> 88.8 | 95.5 | none |
| B1 | framing/round4/B1.png | (3.8, 13.2, 1.15), -22, 0.52/0.46 | 4072x2290 (overscan 3 %) | 16 | +0.885 (+0.535 stop) | 87.0 -> 87.0 | 95.5 | bath/shower-downlight, bath/vanity-sconces, bath/wall-sconce |
| B2 | framing/round4/B2.png | (3.8, 13.2, 1.15), -57, 0.52/0.46 | 4072x2290 (overscan 3 %) | 16 | +0.885 (+0.535 stop) | group CB (set by B1) | frame 94.2 | bath/shower-downlight, bath/vanity-sconces |
| W0 | framing/round4/W0.png | (-0.825, 9.85, 1.1), 0, 0.5/0.46 | 3840x2160 | 16 | +1.44 (+1.09 stop) | 86.5 -> 86.5 | 95.5 | none |
| H0x | framing/round4/poses/H0x.png | (2.877, 9.039, 1.2), 25, 0.52/0.46 | 3840x2160 | 10 | +0.395 (+0.045 stop) | group H0 (set by H0) | frame 94.5 | hall/wall-sconce, living/accent-sconces, living/pendant, living/wall-sconce |
| H0e | framing/round4/poses/H0e.png | (2.877, 9.039, 1.2), 0, 0.5/0.46 | 3840x2160 | 10 | +0.395 (+0.045 stop) | group H0 (set by H0) | frame 94.7 | hall/wall-sconce, living/accent-sconces, living/pendant, living/wall-sconce |
| M0p | framing/round4/poses/M0p.png | (1.25, 5.55, 1.2), 0, 0.52/0.46 | 4072x2290 (overscan 3 %) | 10 | +1.438 (+1.088 stop) | group M0 (set by M0) | 95.5 | living/accent-sconces, living/pendant, living/wall-sconce |
| M0x | framing/round4/poses/M0x.png | (1.25, 5.55, 1.2), -35, 0.52/0.46 | 4072x2290 (overscan 3 %) | 10 | +1.438 (+1.088 stop) | group M0 (set by M0) | 95.5 | kitchen-dining/dining-pendant, kitchen-dining/led-niche, kitchen-dining/led-shelves, living/accent-sconces, living/pendant, living/wall-sconce |
| PD-35 | framing/round4/poses/PD-35.png | (2.8, 3.8, 1.1), -35, 0.52/0.46 | 4072x2290 (overscan 3 %) | 10 | +1.712 (+1.362 stop) | group PD (set by D1) | 95.5 | kitchen-dining/dining-pendant, kitchen-dining/led-niche, kitchen-dining/led-shelves |
| W0-in | framing/round4/poses/W0-in.png | (-0.825, 8.55, 1.1), 0, 0.5/0.46 | 3840x2160 | 10 | +1.44 (+1.09 stop) | group W0 (set by W0) | frame 87.6 | none |
| S1prime | framing/round4/poses/S1prime.png | (2.641, 13.0, 1.2), 0, 0.5/0.46 | 3840x2160 | 10 | +0.376 (+0.026 stop) | group C0 (set by C0) | frame 91.5 | corridor/ceiling-lights, living/accent-sconces, living/pendant, living/wall-sconce |
| R2m | not rendered | | | | | | | |
| K-boy-0 | framing/round4/poses/K-boy-0.png | (1.1, 13.0, 1.0), 0, 0.5/0.46 | 4072x2290 (overscan 3 %) | 10 | +0.85 (+0.5 stop) | group Kb (set by K-boy) | frame 85.5 | none |
| K-girl-0 | framing/round4/poses/K-girl-0.png | (1.1, 16.63, 1.0), 0, 0.5/0.46 | 4072x2290 (overscan 3 %) | 10 | +0.85 (+0.5 stop) | group Kg (set by K-girl) | frame 85.5 | none |
| CB-0 | framing/round4/poses/CB-0.png | (3.8, 13.2, 1.15), 0, 0.5/0.46 | 4072x2290 (overscan 3 %) | 10 | +0.885 (+0.535 stop) | group CB (set by B1) | 95.5 | bath/shower-downlight, bath/vanity-sconces, bath/wall-sconce |
| MB-in | framing/round4/poses/MB-in.png | (2.45, 21.05, 1.2), 0, 0.5/0.46 | 3840x2160 | 10 | +1.256 (+0.906 stop) | group MB0 (set by MB0) | frame 94.1 | corridor/ceiling-lights, living/accent-sconces, living/pendant, living/wall-sconce, master/bedside-sconces |

H0 balance (display-referred, as round 3 measured it): living back wall through the door L 89.0, hall wall above the console L 74.1, living - hall = 0.57 stop (round 3: 0.4; target 0.5-0.9: pass).
<!-- /TABLE -->

## מה פתוח
- ‏M0 ו-D1 בלי overscan (ראו 6).
- ‏R2m לא רונדר (ראו 9).
- ה-clay נשאר בהיר ושטוח יחסית (AgX על לבן-על-לבן); הקונטרסט נכתב בפרומפט.
