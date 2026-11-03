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

## תשובות הסכמה SCH1 ו-SCH2 (המשך, 2026-11-03)

> הבעלים ענה על שתי שאלות הסכמה (`status/decisions.json` ‏SCH1, ‏SCH2; חוקי הסטודיו ז, 2026-11-03), והתשובות הן האישור לשנות את `data/product-card.schema.json`. זה השינוי היחיד במסמך מחייב.

**מה השתנה**
- **הסכמה 1.2** (`data/product-card.schema.json`): ‏`placement` כולל עכשיו `sill` (אדן חלון, כמו בקובצי ה-slots). רשומה ב-`safety.certificates` חייבת `url` או `source: "seller-claim"` (‏`anyOf`). בלי קישור, המקור חובה, וההערה המתוארכת נשארת. נוספה שורת changelog.
- **SCH2:** שלושת כרטיסי האגרטל שהעברתי ל-`window` חזרו ל-`sill`: ‏`vase-aliexpress-vintage-distressed-clay-vase-589009`, ‏`vase-cj-black-matte-stoneware-jar-30`, ‏`vase-cj-matte-frosted-tapered-28`. ההערה בכל כרטיס עודכנה.
- **SCH1, בניגוד להמלצה שלי:** שמונה הרשומות שהסרתי שוחזרו מההערות שהשארתי, כ-`{"name": "CE (seller attribute)", "verified": false, "source": "seller-claim"}`. הכרטיסים: bath/ceiling-light ‏086617, ‏entrance/table-lamp ‏045552, ‏entrance/wall-sconce ‏915640, ‏kids/doll ‏664801, ‏kids/pendant ‏200914-kids, ‏kids/soft-toy ‏999497, ‏kids/toy-cars ‏975232, ‏work/desk-lamp ‏045552. כולם כרטיסי טיוטה, ואף אחד מהם לא מוצג באתר היום.
- **התצוגה, בניסוח ישר:** אצלנו תעודה בלי מסמך היא תמיד "טענת המוכר, אין מסמך", ואף פעם לא "מאומת". זה נכון גם כשבכרטיס כתוב `verified: true`.
  - באתר (`site/shared/src/safety.ts`): ‏`verified` דורש קישור, ו-`seller_claim: true` לכל רשומה בלי קישור או עם המקור. שורת הבטיחות מציגה "CE (seller attribute): טענת המוכר, אין מסמך", בלי קישור.
  - בסטודיו (`studio/build.py`, ‏`studio/src/index.html`): מצב התקן `seller-claim` עם השבב "טענת המוכר, אין מסמך", באותו צבע של "לא מאומת".
- **מחולל ה-zod** (`site/shared/scripts/gen-product-card-schema.ts`) מתרגם `anyOf` ל-`.refine`. הקובץ `product-card.gen.ts` נוצר מחדש. גם המאמת של הסטודיו (`studio/apply_edits.py validate`) בודק עכשיו `anyOf`.

**מה רץ, ומה יצא**

| בדיקה | תוצאה | הקובץ |
| --- | --- | --- |
| typecheck | **עבר** (כולל `gen-product-card-schema.ts --check`) | `sch-typecheck.log` |
| בדיקות הסכמה (vitest, ‏`-t "schema\|product card\|SCH1\|seller\|sill"`) | **עבר: 7 בדיקות.** הקובץ שנוצר מעודכן, כל קובצי ה-slots עוברים, וכל כרטיס מחוץ לפול עובר או שהוא טיוטה שחסרים לה רק שדות הטיוטה. נוספה בדיקה ל-SCH1: טענת מוכר לא מאומתת לעולם, והסכמה דוחה תעודה שאין לה לא קישור ולא מקור | `sch-schema-test.log` |
| ‏`npm test` | **עבר: 73 בדיקות, 0 נכשלו** | `sch-test.log` |
| כל הכרטיסים מול הסכמה, במאמת של הסטודיו | סכמה 1.2: ‏413 תקינים, **0 פגומים**, 68 טיוטות, 8 בפול (בעיה ידועה). ‏`sill` בשלושה כרטיסים, ‏`seller-claim` בשמונה | `sch-studio-validate.txt` |
| ‏`npm run build` (כולל budget) | **עבר, יציאה 0.** ‏JS של עמוד החדר 75.3 KB מתוך 80, ‏CSS ‏6.6 מתוך 15, טעינה ראשונה של הסלון במובייל 567.6 KB מתוך 3 MB | `sch-build.log` |
| ‏`no_loss.py --check-site` | קטלוג d72fce7a37f7: ‏39 מוצרים (3 לא נמכרים), 477 מחירים, 45 ברצפה, **0 מפסידים** | `sch-no-loss-check-site.txt` |
| בניית הסטודיו (`studio/build.py --offline`) | יציאה 0. ‏16 רשומות `seller-claim` ב-`data.json`: מצב ומובאה לכל אחד מ-8 הכרטיסים | `sch-studio-build.txt` |

**אחרי זה:**
- ‏`npm run format:check` נכשל על `site/shared/test/shared.test.ts`, הבדיקה החדשה של SCH1. הקובץ עבר `prettier --write`, וההרצה החוזרת עוברת (`qa/reports/2026-11-03-site-test-page/format-check.log`).
- הבנייה המלאה, ‏typecheck, ‏test, ‏lint, ‏a11y ו-e2e רצו שוב אחרי עמוד הבדיקה, וכולן עברו. הפלטים ב-`qa/reports/2026-11-03-site-test-page/`.
