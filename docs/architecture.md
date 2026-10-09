# ארכיטקטורה: חנות מותאמת (אפשרות ג')

עודכן: 2026-10-09 · frontend-dev · המשתמש בחר באפשרות ג' מתוך `docs/tech-proposal.md`.
סימון **(לא אומת)** = מידע שלא נבדק מול הספק, הרשות או עורך דין, ויש לבדוק אותו לפני ההשקה.

## 1. סטאק, ומה השתנה מול ההצעה

| שכבה | בחירה | למה |
| --- | --- | --- |
| אתר | Vite 7 + TypeScript + **Preact** (עם signals) | ‏10KB במקום כ-45KB של React. אותו JSX, ו-SSR פשוט עם `preact-render-to-string`. כל ה-JS של האתר הוא 38KB אחרי gzip. |
| מנוע החדר | **WebGL2 בכתיבה ישירה** (shader אחד לקומפוזיציה, shader אחד לתצוגה) ו-Canvas2D כגיבוי | ב-OGL אין צורך: הקומפוזיציה היא quads עם blend של multiply ו-screen ופרלקסה לפי מפת עומק. בלי תלות, ופחות מ-300 שורות. |
| גלגל וריאציות | CSS 3D (perspective) עם פיזיקה של גרירה, תאוצה והצמדה (`engine/wheel-physics.ts`) | רץ על ה-compositor של הדפדפן, נגיש (radiogroup), ואפשר להפעיל אותו במקלדת. |
| שרת | **Cloudflare Worker** אחד (Hono 4) שמגיש את האתר הסטטי (Workers Static Assets) ואת ה-API מאותו origin | בלי CORS. בקשות לנכסים הסטטיים לא מפעילות את ה-Worker (חוץ מ-`/api/*`, ‏`/mock-pay/*` ו-`/order/*`). |
| נתונים | **D1** (SQLite) | הזמנות, עגלות, לקוחות, ותמונת מצב של הקטלוג. |
| מדיה | ‏`web/public/media` עכשיו, ו-**R2** מאחורי דומיין משנה בהמשך | שמות הקבצים כבר סופיים, ולכן המעבר ל-R2 הוא שינוי של `MEDIA_BASE` בלבד. |
| תורים | **Cloudflare Queues** | העברת הזמנה ששולמה לספק, עם ניסיונות חוזרים ו-DLQ. |
| הגבלת קצב | Workers Rate Limiting binding | עגלה: 60 בדקה. קופה: 10 בדקה לכל לקוח. |

**מה השתנה מול ההצעה:**
1. Preact במקום React.
2. WebGL2 ישיר במקום OGL.
3. Worker אחד במקום Pages ו-Worker נפרדים.
4. מנוע החדר מתחיל לרוץ רק כשהמשתמש מראה כוונה: עכבר מעל החדר, נגיעה, פוקוס או נקודה חמה. עד אז מוצגת תמונת ה-poster שעברה prerender, והיא אותה קומפוזיציה של ברירת המחדל. כך הטעינה הראשונה לא דורשת GPU.
5. הצעה א' המליצה על Shopify. המשתמש בחר בחנות מותאמת, ולכן הקופה, ההזמנות והחשבוניות אצלנו, והסליקה בדף מתארח.

## 2. SEO בעברית
- **Prerender בזמן build** (`web/scripts/prerender.ts`):
  - נוצר HTML מלא לכל עמוד ציבורי: בית, חדר, כל מוצר מוצג ועמודי המידע. העמודים בעברית, עם `lang="he" dir="rtl"`, ‏`<title>`, תיאור, canonical, ‏og ו-JSON-LD (‏Product, ‏BreadcrumbList, ‏ItemList).
  - נוצרים גם `sitemap.xml` ו-`robots.txt`.
  - אחרי הטעינה הלקוח עושה hydrate לעמוד.
- **אין `Offer` ב-JSON-LD כשהמחיר זמני.** מנוע חיפוש לא יאנדקס מחיר שלא מוכרים בו.
- עגלה, קופה ועמוד הזמנה מסומנים `noindex`.
- `ORIGIN` ב-`web/src/head.ts` הוא `example.co.il` עד שייבחר דומיין.
- SSR דינמי ב-Worker לא נדרש כרגע: הקטלוג משתנה רק ב-build.

## 3. מבנה הריפו (`site/`, npm workspaces)
```
site/
  shared/   סכמות zod, טיפוסי API, תמחור (pricing.ts), חתימת webhook, כסף
  api/      Worker (Hono): routes/, lib/ (store, payments, suppliers, fulfillment, access), migrations/, scripts/seed.ts
  web/      Preact: engine/ (מנוע שכבות, מצלמה, GL, רצפי פריימים), components/, pages/, state/, styles/, scripts/prerender.ts
  tools/    build-catalog (ריפו → קטלוג), make-temp-assets, check-budget, finalize/check-artifact, screens-artifact, lighthouse
  e2e/      Playwright: flow, perf, a11y
  .generated/  (gitignored) catalog.public.json, catalog.full.json, scene.*.json, seed.sql
  dist-artifact/ (gitignored) תצוגה מקדימה כ-Artifact
```

## 4. מודל הנתונים (D1, ‏`api/migrations/0001_init.sql`)
**מקור האמת לקטלוג הוא הריפו:**
- `data/products/**`
- `data/slots/*.json`
- `data/economics/*.json`
- `docs/house-plan.json`

`tools/build-catalog.ts` בונה מהם קטלוג, ו-`api/scripts/seed.ts` כותב אותו ל-D1. הסקריפט אידמפוטנטי ולא נוגע בטבלאות המסחר. מוצר שיצא מהקטלוג נשאר ב-D1 עם `visible=0`, כי הזמנות מפנות אליו.

| טבלה | עיקר |
| --- | --- |
| `products` | ‏`retail_agorot` (מחיר לצרכן **כולל מע"מ**), ‏`cost_usd_cents`, ‏`shipping_usd_cents`, ‏`shipping_source` (manual/cj/default), ‏**`sell_qty`** (יחידות ספק לכל יחידה שנמכרת), ‏`fx_usd_ils_at_import` (**השער בזמן הייבוא**), ‏`price_provisional`, ‏`visible` |
| `product_variants` | ‏**`fulfillment_source`** (‏`dropship_cj` / ‏`il_3pl`), ‏`stock_qty` (ל-3PL), ‏`supplier_sku` |
| `economics_settings` | שורה אחת: שער, מע"מ, סליקה (אחוז וסכום קבוע), שמורת החזרות, CAC, אריזה, פריטים בהזמנה, מקדם משלוח משולב, שיטת משלוח לחישוב, **דמי משלוח ללקוח (חסכוני ומהיר)** ו-**סף משלוח חינם** |
| `v_product_economics` (view) | הכנסה נטו, עלות נחיתה, עמלות, שמורה, אריזה, תרומה, מרווח, תרומה אחרי CAC ו-`meets_target`. הנוסחה זהה ל-`shared/src/pricing.ts`, ובדיקה משווה ביניהן. |
| `customers`, `carts`, `cart_items` | עגלה מזוהה במזהה אקראי, ותוקפה 30 יום |
| `orders` | סכומים בתמונת מצב: ‏`subtotal`, ‏`shipping`, ‏`total`, ‏`vat`, ‏`vat_rate`, ‏`fx_usd_ils_at_order`. גם `token_hash` (הקונה רואה את ההזמנה רק עם הטוקן), ספק תשלום, session ושדות חשבונית |
| `order_items` | תמונת מצב של מחיר, עלות, משלוח, `unit_sell_qty` ו-`fulfillment_source`, לחישוב **רווח אמיתי לכל הזמנה** |
| `payment_events` | כל webhook, ייחודי לפי (provider, event id), עם hash של הגוף |
| `supplier_shipments` | שורה לכל (הזמנה, ספק). הזמנה היברידית מתפצלת למשלוח מ-CJ ולמשלוח מ-3PL. כוללת סטטוס, מספר הזמנה אצל הספק, מעקב, ניסיונות ושגיאה |
| `audit_log` | מי שינה מה ומתי: webhook, תור או מנהל |

**כללים:**
- כל סכום כסף הוא מספר שלם באגורות או בסנטים.
- **מוצר בלי `retail_ils` לא מוצג בפרודקשן.** `npm run catalog:strict` משמיט אותו.
- ב-dev, ב-preview וב-Artifact מוצג מחיר מומלץ, ומסומן "מחיר זמני".

## 5. תמחור ורווחיות (מיושר לסטודיו)
הסטודיו (`studio/`, ‏Artifact של back-office) הוא המקום שבו המשתמש עורך מחירים, משלוח והנחות. `studio/apply_edits.py` מסנכרן את העריכות לריפו, ומשם לאתר:

```
studio (db) ──apply_edits.py──▶ data/economics/settings.json   {economics:{usd_ils, vat_pct, card_pct, card_fixed_ils, returns_pct,
                                                                 cac_ils, packaging_ils, target_margin_pct, items_per_order,
                                                                 bundle_factor, shipping_method}, budget, storefront?}
                            └──▶ data/economics/products.json   {products:{<id>:{retail_ils, compare_at_ils, shipping_cost_usd,
                                                                 sell_qty?, fulfillment_source?}}}
data/economics/freight-cj.json (הצעות משלוח של CJ)
        ──build-catalog.ts──▶ catalog.full.json ──seed.ts──▶ D1 (products, economics_settings)
```

**הנוסחה זהה לנוסחה של הסטודיו** (`econCalc`). לכל יחידה, R = מחיר כולל מע"מ:

| שדה | חישוב |
| --- | --- |
| נטו | R ÷ (1 + מע"מ) |
| עלות נחיתה | (עלות + משלוח) בדולר × `sell_qty` × שער |
| עמלות | R × אחוז סליקה + סכום קבוע |
| שמורה | נטו × אחוז החזרות |
| תרומה | נטו − עלות נחיתה − עמלות − שמורה − אריזה |
| מרווח | תרומה ÷ נטו |
| אחרי שיווק | תרומה − CAC ÷ פריטים בהזמנה |

**הנוסחה ממומשת בשלושה מקומות, ובדיקות מוודאות שהם מסכימים:**
- `shared/src/pricing.ts`
- ה-view ב-D1
- הסטודיו

**משלוח לחישוב העלות:** הערך הראשון שקיים מהרשימה:
1. ידני, מהסטודיו.
2. `freight-cj.json`, לפי שיטת המשלוח שבהגדרות.
3. ברירת מחדל.

כרגע כל 26 המוצרים המוצגים מקבלים את המשלוח מ-CJ.

**ברירות המחדל הן של הסטודיו:**

| הגדרה | ברירת מחדל |
| --- | --- |
| שער | 3.7 |
| מע"מ | 18% |
| סליקה | 2% ועוד ₪1.2 |
| החזרות | 5% |
| CAC | ₪40 |
| יעד מרווח | 35% |
| פריטים בהזמנה | 1.4 |

כל ערך שנלקח מברירת המחדל נרשם ב-`defaults_used` ומוצג ב-admin.

**שימו לב:** מחקר הפולפילמנט חישב לפי שער של ₪3.0. את השער בפועל מעדכנים בסטודיו.

**הזמנה אמיתית:** `GET /api/admin/orders/:id` מחזיר רווח גולמי לפי תמונת המצב של העלויות והשער בזמן ההזמנה.

## 6. Admin API (יחליף את שכבת ה-patch של הסטודיו)
**היום (קריאה בלבד, מאחורי Cloudflare Access):**
- `GET /api/admin/overview`
- `GET /api/admin/orders?status=`
- `GET /api/admin/orders/:id` (כולל מרווח)
- `GET /api/admin/products` (מתוך `v_product_economics`)
- `GET /api/admin/supplier-shipments`
- `GET /api/admin/economics`

**השלב הבא (לא בנוי):**
- **כתיבה:**
  - `PATCH /api/admin/products/:id/economics` (‏retail_ils, ‏compare_at_ils, ‏shipping_cost_usd, ‏sell_qty)
  - `PATCH /api/admin/variants/:id` (‏fulfillment_source, ‏stock_qty)
  - `PUT /api/admin/settings/economics`
  - `PUT /api/admin/settings/storefront`
  - `POST /api/admin/orders/:id/{resend-to-supplier,cancel,refund}`
- כל כתיבה נרשמת ב-`audit_log` עם המייל מ-Access.
- **הריפו נשאר מקור האמת:** `GET /api/admin/export` מחזיר את השינויים בפורמט של `data/economics/*.json`, כמו ש-`apply_edits.py` כותב היום. הסטודיו יקרא ויכתוב דרך ה-API הזה במקום ה-db של ה-Artifact.

## 7. API
| נתיב | מה |
| --- | --- |
| `GET /api/health` | גרסת הקטלוג |
| `GET /api/catalog/prices?ids=` | מחירים חיים מ-D1. התיאורים עצמם נבנים לתוך האתר. |
| `GET /api/catalog/rooms/:room` | עמדות ואפשרויות |
| `POST /api/cart` · ‏`GET /api/cart/:id` · ‏`PUT /api/cart/:id/items` | עגלה. המחיר תמיד מ-D1, לעולם לא מהלקוח. |
| `POST /api/checkout` | אימות (zod), חישוב משלוח לפי ההגדרות, תמונת מצב של עלויות, יצירת session אצל ה-PSP, והחזרת `redirect_url` לדף התשלום המתארח |
| `POST /api/webhooks/payment/:provider` | **חתום** (‏HMAC-SHA256 עם חותמת זמן וחלון של 5 דקות). אידמפוטנטי לפי event id. בודק שהסכום תואם. רק כאן הזמנה הופכת ל-`paid`, ורק אז נשלחת הודעה לתור. |
| Queue consumer | `paid` ← הזמנה אצל הספק (‏CJ, או mock). רק שורות של `dropship_cj` נשלחות, בכמות של qty × sell_qty. עד 5–8 ניסיונות ואחריהם DLQ ו-`supplier_error`. |
| `GET /api/orders/:id` | סטטוס לקונה. דורש header ‏`x-order-token`. |
| `/api/admin/*` | ראו סעיף 6 |
| `/mock-pay/*` | דף תשלום מדומה. קיים רק כש-PAYMENT_PROVIDER=mock ומחוץ לפרודקשן. |

החזרה מדף התשלום לא משנה את סטטוס ההזמנה. עמוד ההזמנה בודק את הסטטוס מחדש כל כמה שניות.

## 8. תשלומים וחשבוניות
- **דף תשלום מתארח של PSP ישראלי (Grow, ‏Cardcom או PayPlus).** פרטי האשראי לא עוברים דרכנו, ולכן אין PCI scope מעבר ל-SAQ A **(לא אומת)**.
- הממשק `lib/payments/types.ts` כולל `createSession` ו-`verifyWebhook`. כרגע ממומש רק mock.
- **מה צריך לבדוק מול כל אחד מהם (לא אומת):**
  - דמי מסוף ועמלה
  - תשלומים
  - Bit, ‏Apple Pay ו-Google Pay
  - חתימת webhook
  - דף תשלום בעברית ונגיש
  - זיכוי דרך API
- **חשבונית מס:** דרך Morning (חשבונית ירוקה) או iCount, אחרי `paid`, כ-job בתור **(לא אומת)**. אם ה-PSP מפיק חשבונית בעצמו (ל-Grow ול-PayPlus יש מודולים כאלה, **לא אומת**), אפשר לוותר על שירות נפרד.

## 9. מודל משלוח והספקה (היברידי, החלטה E1 פתוחה)
- **ספק המשלוח נקבע לכל וריאציה** ב-`product_variants.fulfillment_source`:
  - **עכשיו:** כולן `dropship_cj`.
  - **בהמשך:** מוצר שנמכר ביותר מ-20–30 יחידות בחודש עובר ל-`il_3pl`. משנים את השדה ב-`data/economics/products.json`, או דרך ה-admin.
  - **הזמנה מעורבת** מתפצלת ב-`supplier_shipments` לשתי שורות.
  - **מתאם ל-3PL** עוד לא נבנה, כי עוד לא נבחר מחסן.
- **דמי משלוח ללקוח** מוגדרים בהגדרות ולא בקוד:
  - חסכוני: ₪29.
  - מהיר: ₪59.
  - **משלוח חסכוני חינם מעל ₪299.**
  - אלה ערכים זמניים לפי המחקר: חנויות בארץ גובות ₪10–30, וחינם מעל ₪199–349. השרת מחשב אותם מחדש, והם נכללים בבסיס המע"מ.
  - אפשר לשנות אותם בבלוק `storefront` ב-`settings.json`. בסטודיו עוד אין להם שדה.
- **סיכון: תקרת הפטור ממע"מ ביבוא אישי היא $75.** חבילה של יותר מ-$75 מחויבת במע"מ אצל הלקוח, ובדרופשיפינג נוצר כפל מע"מ. בהמשך יתווסף פיצול הזמנה או אזהרה בקופה. לבדוק מול רואה חשבון **(לא אומת)**.

## 10. אבטחה
- **סודות רק ב-`wrangler secret put <NAME> --env preview|production`.**
  - `api/.dev.vars.example` מכיל שמות בלבד.
  - `.dev.vars` המקומי נוצר אוטומטית עם סוד אקראי ל-mock. הוא ב-gitignore.
  - אין סוד בקוד, ב-`wrangler.jsonc` או בצ'אט.
- **CSP קשיח** (`web/public/_headers`):
  - `script-src 'self'`, בלי inline. ‏`style-src-attr` מותר רק לסגנונות inline של המנוע.
  - `frame-ancestors 'none'`, ‏`form-action 'self'`.
  - ה-API מחזיר `default-src 'none'`.
  - גם HSTS, ‏nosniff, ‏Referrer-Policy, ‏Permissions-Policy ו-COOP.
- **הגבלת קצב** בעגלה ובקופה. גודל גוף הבקשה מוגבל. כל הקלט עובר zod. כל שאילתה היא prepared statement.
- **Admin מאחורי Cloudflare Access:**
  - ה-Worker מאמת בעצמו את ה-JWT: חתימת RS256 מול JWKS, ‏aud, ‏iss ו-exp.
  - עקיפה מקומית (`ADMIN_DEV_BYPASS`) עובדת רק ב-`development`.
- **Webhook:**
  - חתימה וחותמת זמן.
  - אידמפוטנטיות.
  - בדיקת סכום.
  - טוקן ההזמנה נשמר כ-hash בלבד.

## 11. רשימת השקה בישראל (הכול **לא אומת** משפטית עד שעורך דין יבדוק)
- [ ] **נגישות:**
  - האתר בנוי לפי ת"י 5568 ו-WCAG 2.1 AA.
  - בכל CI רצים axe (אפס הפרות, במצב בהיר ובכהה) ו-Lighthouse a11y 100.
  - **הצהרת נגישות** קיימת כטיוטה ב-`/accessibility/`. חסרים פרטי רכז הנגישות ובדיקה ידנית עם קורא מסך (NVDA ו-VoiceOver).
- [ ] **הגנת הצרכן:**
  - ביטול עסקה תוך 14 יום.
  - דמי ביטול: 5% או ₪100, הנמוך מביניהם.
  - פרטי העוסק בדף.
  - טיוטות ב-`/returns/` וב-`/terms/`.
- [ ] **פרטיות (תיקון 13):**
  - מדיניות פרטיות (טיוטה ב-`/privacy/`).
  - צמצום מידע.
  - הסכמה נפרדת לדיוור (כבר בקופה, לא מסומנת מראש).
  - נוהל אבטחת מידע.
  - בירור אם יש חובת רישום מאגר.
- [ ] **מע"מ וחשבוניות:**
  - עוסק מורשה.
  - חשבונית מס לכל הזמנה.
  - 18% על כל המחיר, כולל המשלוח שנגבה מהלקוח.
  - בדיקה מול רואה חשבון של כפל מע"מ מעל $75.
- [ ] **בטיחות מוצר:**
  - CE לתאורה ולחשמל.
  - EN71 למוצרי ילדים.
  - IP44 לתאורה בחדר רחצה.
  - **אישור תקן ישראלי למנורות (ת"י 20 / 900 / 61558).** לפי המחקר הדרישה חלה גם ביבוא אישי.
  - החלטה S2 פתוחה. ההמלצה: לא להעלות מנורה בלי תעודה.
- [ ] תקנון, פרטי קשר ושם העסק בכל עמוד. עמוד "מי אנחנו".
- [ ] דומיין, ‏SPF ו-DKIM למיילים (אישור הזמנה וחשבונית).

## 12. סביבות
| סביבה | מה צריך | איך |
| --- | --- | --- |
| **מקומית** | **שום חשבון** | `cd site && npm install && npm run dev`. רצים Vite (5180) ו-wrangler dev (8787) עם D1 מקומי, תשלום mock וספק mock. אפשר גם `npm run build && npm run preview` (8788). |
| **Artifact** | בלי | `npm run preview:artifact` בונה את `site/dist-artifact/`. ה-API מדומה בדפדפן, והמנהל מפרסם את התיקייה. |
| **Preview / Production** | **חשבון Cloudflare של המשתמש** | ראו למטה. |

**מה המשתמש צריך לעשות (פעם אחת). לא שולחים מפתחות בצ'אט:**
1. לפתוח חשבון Cloudflare. מספיק Workers Paid ב-$5 לחודש, כי Queues דורשים אותו **(לא אומת)**.
2. במחשב שלו: `npx wrangler login`. זו התחברות בדפדפן, ולא מעבירים אף מפתח.
3. להריץ:
   - `npx wrangler d1 create homedesign-preview`
   - `npx wrangler d1 create homedesign`
   - `npx wrangler queues create supplier-orders-preview`, וכן `supplier-orders`, וה-DLQ של כל אחד.
   
   מזהי ה-D1 שמודפסים אינם סודיים. מעתיקים אותם ל-`api/wrangler.jsonc` במקום `REPLACE_WITH_...`.
4. ליצור ב-Zero Trust ‏Access application ל-`/api/admin/*`, ולהעתיק את ה-AUD ואת team domain ל-vars.
5. סודות, בטרמינל של המשתמש בלבד: `npx wrangler secret put PAYMENT_WEBHOOK_SECRET --env preview`. אותו דבר ל-`PAYMENT_API_KEY`, ‏`CJ_API_KEY` ו-`INVOICE_API_KEY` כשיהיו.
6. Deploy: `npm run build && npx wrangler deploy --env preview -c api/wrangler.jsonc`. ל-CI אין deploy במכוון.

## 13. שערי CI (`.github/workflows/site-ci.yml`)
| שער | איפה | סטטוס מקומי (2026-10-09) |
| --- | --- | --- |
| טעינה ראשונה ≤ 3MB במובייל | `tools/check-budget.ts` (סטטי) + `e2e/perf.spec.ts` (מדידה ב-Pixel 7) | עובר: 0.48MB עד הופעת החדר, 1.87MB עד שהמנוע מרכיב את החדר |
| 60fps | `e2e/perf.spec.ts` | **נמדד בלבד**: headless מרנדר WebGL בתוכנה (SwiftShader), ולכן השער נאכף רק עם `HD_GPU=1` על מכונה עם GPU |
| אפס הפרות axe | `e2e/a11y.spec.ts`, ‏18 בדיקות בבהיר ובכהה | עובר |
| Lighthouse a11y 100, ‏perf ≥ 90 במובייל | `tools/lighthouse.ts` | a11y 100 בכל העמודים. perf: בית, מוצר וקופה 97–99. **בעמוד החדר 78–89, בשונות גבוהה (LCP מדומה 2.9–5.2 שניות).** |

## 14. החלטות פתוחות למשתמש
| החלטה | המלצה |
| --- | --- |
| **סולק (PSP)** | **Grow (Meshulam)**: דף מתארח, Bit ו-Apple Pay, ומודול חשבוניות שעשוי לחסוך שירות נפרד. חלופה: PayPlus. לבקש הצעות משלושתם **(לא אומת)**. |
| **חשבוניות** | אם ל-PSP יש חשבונית מס מובנית, להשתמש בה. אחרת **Morning**: API פשוט ומוכר לרואי חשבון **(לא אומת)**. |
| **דומיין** | ‏`.co.il` בשם המותג, אחרי שהשם ייבחר (`docs/brand-names.md`). לרשום דרך registrar מוכר ולנהל את ה-DNS ב-Cloudflare. |
| **חשבון Cloudflare** | חשבון על שם העסק, עם Workers Paid ו-2FA. המשתמש מתחבר ב-`wrangler login` במחשב שלו. |
| **E1 משלוח** | היברידי (כבר מתוכנן בסכמה). לאשר דמי משלוח ₪29, מהיר ₪59, חינם מעל ₪299, או לעדכן. |
| **S2 תעודות** | כן: לא מעלים מנורה בלי CE ואישור תקן ישראלי. |
