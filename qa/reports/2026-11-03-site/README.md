# בדיקות האתר אחרי תיקוני 2026-11-03 (SITE1, NL1, NL2, R6Q2, ART3, ART6, ART7)

> frontend-dev · הבריף: `briefs/site-fixes-2026-11-03.md`. הכל רץ מקומית, בלי commit. `node_modules` היה חסר והותקן מ-`package-lock.json` (`npm ci`, הרשת אפשרה). ‏Playwright עם ה-Chromium שב-`/opt/pw-browsers`. הדפדפן הוא headless SwiftShader, ולכן זמני הפריימים ב-`e2e/perf.spec.ts` הם דיווח ולא מדידת מכשיר (G6.5, G6.7).

## מה רץ, ומה יצא

| בדיקה | פקודה | תוצאה | הקובץ |
| --- | --- | --- | --- |
| לפני התיקונים (baseline) | `typecheck`, `test`, `lint` | typecheck נכשל רק על קבצי `.generated` חסרים (לפני `npm run catalog`); ‏vitest: 62 עברו, **1 נכשל** (70 כרטיסים מחוץ לפול לא עוברים את הסכמה), 1 דולג (ההתאמה ל-`sell_qty_default` של הסטודיו, כי `studio/dist/data.json` חסר); lint עבר | `baseline/*.log` |
| typecheck | `npm run typecheck` | **עבר** (tsc בכל ה-workspaces; הסכמה שנוצרה מעודכנת) | `typecheck.log` |
| vitest | `npm test` | **עבר: 72 בדיקות, 0 נכשלו, 0 דולגו** (6 קבצים). שתי הבדיקות שנכשלו ב-20.10 עוברות: הסכמה (ראו "הסכמה" למטה) וההתאמה ל-`sell_qty_default` של הסטודיו, שרצה הפעם על `studio/dist/data.json` שנבנה ב-`python3.12 -I studio/build.py --offline` (אותם כללים, אותו סדר, על הכרטיסים האמיתיים) | `test.log` |
| lint | `npm run lint` | **עבר** (ESLint, typescript-eslint, jsx-a11y strict, 0 אזהרות) | `lint.log` |
| prettier | `npm run format:check` | **עבר** | `format-check.log` |
| build + budget | `npm run build` (קטלוג ← מדיה זמנית ← תמונות ספק ← Vite ← prerender ← Worker dry-run ← `budget`) | עבר. JS ‏74.9 KB gzip (עד 80), CSS ‏6.6 KB (עד 15), טעינה ראשונה של הסלון במובייל 551 KB (עד 3 MB) | `build.log` |
| a11y | `npm run a11y` (axe, WCAG 2.0/2.1 A+AA, בהיר בלבד אחרי ART3; כולל הגלגל הפתוח, דף מוצר עם אפשרויות, סל מלא וקופה עם שגיאות) | **עבר: 11 בדיקות, 0 הפרות** | `a11y.log` |
| e2e | `npm run e2e` (flow, perf, swap-diff, hotspots, options; ‏Playwright מריץ `npm run preview` בעצמו) | **עבר: 21 בדיקות, 0 נכשלו** (3.3 דקות). ‏perf: טעינה ראשונה של הסלון במובייל עד שהחדר מורכב 1.68 MB (עד 3 MB), רק T-E0 נטען מראש; זמני פריימים ב-SwiftShader (דיווח בלבד, בלי GPU): זום p95 ‏650 ms, גלגל p95 ‏183 ms. הזרימה המלאה עוברת עם מספר הזמנה בספרות בלבד והסטטוס "התקבלה / בהכנה" (ART6). הריצה כותבת מחדש את ראיות ההחלפה והנקודות ב-`assets/qa/swap-diff/` ו-`assets/qa/hotspots/` (כך הבדיקות בנויות); הקבצים האלה השתנו בעץ העבודה | `e2e.log` |
| no-loss, הכותרת (G8.1) | `python3.12 -I scripts/economics/no_loss.py --check` | 0 כשלי אינווריאנט, 0 מוצרים מפסידים במחירם (464 מוצרים) | `no-loss-checks.txt` |
| no-loss, המחירים הנגזרים (G8.2) | `no_loss.py --check-derived` (חדש) | 7,546 תרחישים נגזרים (אפשרות, יחידה מהסט); 721 מהם מועלים על ידי רצפת האתר (ההעלאה הגדולה ₪2,470, שטיח הצמר הקלוע); **0 מפסידים במחיר האתר** | `no-loss-checks.txt`, ‏`no-loss-audit.json` ‏(`derived_check`) |
| no-loss על פלט האתר (G8.2) | `no_loss.py --check-site site/.generated/catalog.full.json` (חדש) | קטלוג c8c79161b619: 39 מוצרים (3 לא נמכרים, PRE1), 477 מחירים נבדקו מול נוסחת הסטודיו על עלות הנחיתה של האתר, 45 מהם רצפה; **0 מפסידים**; 0 מחירים של הסטודיו שמפסידים | `no-loss-checks.txt`, ‏`no-loss-audit.json` ‏(`site_check`) |

## מה נבדק ולא רץ

- `npm run lighthouse` צריך שרת preview חי ו-Chrome מלא; לא רץ (G6.8 נשאר ללא ראיה חדשה).
- `studio/tests/smoke_products.py` דורש `playwright` לפייתון, שלא מותקן; שינוי התוויות ב-`studio/build.py` נבדק בבנייה (`--offline`, יציאה 0) ובקריאה.

## מצב הקטלוג אחרי התיקונים (`npm run catalog`)

- 39 מוצרים מוצגים בסלון (18 עמדות, 15 אפשרויות ממתינות למוצר). 
- **מוסתרים עם סיבה (לא עוד מחיר זמני של 40% ולא $17):** 7 בלי שום מקור מחיר (לא בקובץ התמחור, לא בכרטיס, לא בליקוט): `curtains-aliexpress-linen-blend-s-fold-180502`, ‏`accent-sconces-aliexpress-travertine-cylinder-walnut-choice`, ‏`accent-sconces-cj-travertine-block-updown-8x16`, ‏`wall-sconce-cj-travertine-cube-updown-12`, ‏`vase-cj-black-matte-stoneware-jar-30`, ‏`cushions-cj-chenille-check-milky-white`, ‏`pendant-cj-silk-ribbed-pumpkin-40`; 2 בלי שורת משלוח (ביקורת no-loss תמחרה אותם מהערכה בהערות הכרטיס, לסטודיו אין קו): `curtains-aliexpress-cotton-linen-texture-translucent`, ‏`...-091154`.
- **לא נמכרים (PRE1):** `framed-art-cj-morandi-triptych-sage` ו-`rug-cj-braided-wool-natural` (אקספרס בלבד, NL2); `pouf-cj-cotton-knit-ball-cover` (העמדה living-room/pouf בהמתנה, R6Q2). מעל פי 2 מההשוואה: 0 בסלון.
- שורות המשלוח: CJ ‏33, ‏Zendrop ‏3, התשובה השמורה של הספק 2, המק"ט בכרטיס 1; ברירת מחדל 0.
- 81 מחירי אפשרויות הועלו לרצפת "לא מפסיד" שלהן; 0 מחירים ידניים של הסטודיו מפסידים בקריאת האתר.
- 68 כרטיסי טיוטה (DS API) מנויים בשם ולא מוצגים; 8 כרטיסי פול (בעיה ידועה).
