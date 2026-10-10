# גישה לעוד מקורות וצנרת סורסינג "פעם אחת"

> תאריך: 2026-10-09. מחקר בלבד: לא נרשמתי לשום דבר, לא פניתי לאף אחד ולא עקפתי חסימות.
> **אומת** = נבדק בדף רשמי או ב-API רשמי בתאריך הזה. **לא אומת** = מקור משני או בלי מקור.
> נתונים מכונה: `data/suppliers/access-options.json`. ערוצים זולים, סוכני 1688 ותעריפי משלוח לישראל נמצאים ב-`deep-research-2026-10.md`, ולא חוזרים כאן.

## רשימת משימות למשתמש (לפי השפעה חלקי מאמץ)

**כלל לכל המפתחות:** מגדירים אותם רק בהגדרות הסביבה של Claude (תפריט הסביבה בשורת הכותרת של הסשן > Edit > Network secrets או משתני סביבה). סשן חדש קולט אותם. אף פעם לא מדביקים מפתח בצ'אט.

| # | משימה | זמן שלך | עלות | אישור | תלוי ב- | מה זה פותח |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **לאשר שהסוכנים ישלחו בקשות Sourcing ל-CJ דרך ה-API.** אין הרשמה: המפתח הקיים כבר כולל את `/product/sourcing/create` | דקה | 0 | מיידי | – | CJ מחפש בשבילנו מוצר לפי תמונה וקישור (1688, AliExpress, אמזון) ומעלה אותו לקטלוג, עם קווי המשלוח לישראל שכבר עובדים |
| 2 | **AliExpress Open Platform, אפליקציית Dropshipping:** חשבון ב-[openservice.aliexpress.com](https://openservice.aliexpress.com) > פרופיל כ-**Individual** > App Console > Create > ‏"Dropshipping Developer (Individual/Corporation)" > Apply, עם הנימוק מסעיף 1.2. אחרי האישור: Create App, ואז `AE_DS_APP_KEY` ו-`AE_DS_APP_SECRET`. **בוצע 2026-10-10:** האפליקציה קיימת (סטטוס Test, Callback ‏`https://127.0.0.1/callback`). הלקוח: `scripts/ae/` (‏`scripts/ae/README.md`); נשאר: הרשאה ראשונה לפי `status/handoff.md`, ואחרי שהכל עובד Apply Online | 30–45 דק' | 0 | הפרופיל אושר 2026-10-10 | Callback ‏`https://127.0.0.1/callback` מספיק (ה-code נקרא משורת הכתובת); עוסק רק אם נרשמים כ-Corporation | כל הקטלוג של AliExpress: חיפוש, **חיפוש לפי תמונה**, פרטים, משלוח לישראל, תעודות, והזמנה |
| 3 | **AliExpress, אפליקציית Affiliates** (באותו חשבון): להצטרף ל-[AliExpress Portals](https://portals.aliexpress.com) ולקבל Tracking ID, ואז Create > ‏"Affiliates Developer (Individual)". משתנים: `AE_AFF_APP_KEY`, ‏`AE_AFF_APP_SECRET`, ‏`AE_AFF_TRACKING_ID` | 20 דק' | 0 | לא אומת (1–3 ימים לפי מקור משני) | אולי אתר או ערוץ (לא אומת) | קריאה בלבד: חיפוש, פרטים, SKU ומשלוח לפי מדינה. מכסה נפרדת מאפליקציית ה-DS |
| 4 | **Google Cloud Vision (Web Detection):** פרויקט > להפעיל Cloud Vision API > לחבר כרטיס חיוב > מפתח API מוגבל ל-Vision בלבד > `GOOGLE_VISION_API_KEY` | 15 דק' | 1,000 בדיקות בחודש חינם, אחר כך $3.50 לאלף | מיידי | – | חיפוש הפוך לפי תמונה: איפה עוד נמכר אותו מוצר. זה הבסיס ל"מצא זול יותר" |
| 5 | **DSers + DSers MCP:** הרשמה ב-[dsers.com](https://www.dsers.com/pricing). ה-MCP דורש **Advanced ‏($19.90 לחודש, 14 ימי ניסיון)**. מוסיפים את כתובת ה-MCP כמחבר מותאם ב-[claude.ai/customize/connectors](https://claude.ai/customize/connectors) (כניסת OAuth, בלי מפתח) ופותחים סשן חדש | 20 דק' | 0 ב-14 הימים הראשונים | מיידי | כנראה חנות Shopify או Wix לייבוא ולהזמנות. לחיפוש בלבד: לא אומת | חיפוש ספקים, פרטים, הצעות משלוח, **חיפוש תמונה בין פלטפורמות** ו-Supplier Optimizer |
| 6 | (מ-deep-research) אישור לבקש הצעות מחיר מ-3 סוכני 1688 ומ-OneStop | – | 0 | 1–3 ימים | אישור לפנות | מחירי מפעל. אין API |
| 7 | CJ Plus ‏($15.99 לחודש, לא אומת) **רק אם** נגיע לתקרת בקשות ה-Sourcing היומית | 5 דק' | 15.99 | מיידי | – | עוד 10 בקשות ביום |
| 8 | Alibaba.com Open Platform | שעה+ | לא אומת | לא אומת | **עוסק רשום** | נתוני ספקי B2B (לא דחוף) |
| 9 | TinEye API ‏(5,000 בדיקות ב-$200, מחיר מ-2015) **רק אם** Vision לא מספיק | 10 דק' | 200$ | מיידי | – | התאמות כפולות מדויקות |

**לא לעשות עכשיו:** AutoDS, ‏Zendrop, ‏Spocket ו-Syncee עובדים דרך חנות Shopify, ‏Wix או Woo מחוברת, ואין להם API פומבי. החנות שלנו מותאמת אישית (Preact ו-Worker), ולכן הם לא מוסיפים לנו נתונים. חוזרים אליהם רק אם תתקבל החלטה על פלטפורמת חנות. **Bing Visual Search** הוצא משימוש ב-11.08.2025. ל-**Google Lens** אין API רשמי, ו"API של Lens" מצד שלישי הוא גירוד, שאסור לפי הכללים שלנו.

### תלויות בהחלטות W1–W4
| החלטה | מה מחכה לה |
| --- | --- |
| W1 סולק, W2 חשבוניות | שום מקור נתונים. רק הזמנות אמיתיות (DS order, ‏CJ order) |
| W3 דומיין | Callback URL נקי לאפליקציית AliExpress. אפשר גם בלעדיו |
| W4 ‏Cloudflare | Worker קטן כ-Callback URL שמחליף את ה-code ב-token (חלופה ל-W3) |
| עוסק (מתוך foundation-review) | נדרש רק ל-Alibaba.com Open Platform ולרישום AliExpress כ-Corporation |
| פלטפורמת חנות (לא החלטה פתוחה כרגע) | AutoDS, ‏Zendrop, ‏Spocket, ‏Syncee ושימוש מלא ב-DSers |

---

## 1. אפשרויות גישה: פירוט ואימות

### 1.1 ‏CJ: מה כבר פתוח ולא ניצלנו (אומת)
בדקתי את `/setting/get` בחשבון שלנו ב-2026-10-09. מכסה של **1,000 קריאות ביום לכל endpoint**, ‏`qpsLimit` של 100. ברשימה גם `/product/sourcing/create`, ‏`/product/sourcing/queryList` ו-`/product/queryProductsByImage`.
- **מערכת נקודות** (בתוקף מ-1.6.2026 לנרשמים חדשים, ומ-1.7.2026 לוותיקים): ‏**50,000 נקודות ביום** (מתאפס ב-00:00 UTC), ועוד 100 נקודות לכל $1 של ההזמנה הגבוהה ב-3 החודשים האחרונים. עלות לקריאה: ‏`listV2` ‏50, ‏`product/query` ‏10, ‏`freightCalculate` ‏10, ‏**חיפוש תמונה 1,000**. כלומר, עד 1,000 חיפושים ביום, **או** 50 חיפושי תמונה ([Points](https://developers.cjdropshipping.com/en/api/api2/standard/points.html)).
- **Sourcing ב-API:** ‏`POST /product/sourcing/create` עם `productName` ו-`productImage` (חובה), ואופציונלית `productUrl`, ‏`price` ו-`remark`. התשובה מחזירה `cjSourcingId`. בודקים סטטוס ב-`GET /product/sourcing/queryList?sourceIds=…` (עד 100 בקריאה) ([Product API](https://developers.cjdropshipping.com/en/api/api2/api/product.html)). באתר, למשתמש חינמי יש 5 בקשות ביום, ו-CJ עונה תוך 24 שעות. **לא אומת** אם אותה תקרה חלה גם ב-API.
- **חיפוש לפי תמונה:** דורש רמת חשבון 3 ומעלה, ובפחות מזה מקבלים 401. לא בדקתי, כדי לא לבזבז נקודות.
- עוד endpoints שלא ניצלנו: ‏`/product/variant/query` עם `countryCode` (מלאי לפי מדינה), ‏`/product/productComments`, ו-Webhooks לשינויי מוצר ומלאי. ה-Webhooks יחליפו בדיקה חוזרת של מחירים.

### 1.2 ‏AliExpress Open Platform (אומת מתיעוד רשמי)
מקור: ה-API הציבורי של אתר התיעוד ב-openservice.aliexpress.com (המסמכים 1358–1365 ורשימת ה-API), נבדק ב-2026-10-09.
**עדכון 2026-10-10: הלקוח מומש ב-`scripts/ae/` (‏`client.py`, ‏`auth.py`, ‏`ds.py`; תיעוד `scripts/ae/README.md`), לפי [Signature algorithm (1386)](https://openservice.aliexpress.com/doc/doc.htm#/?docId=1386), ‏[HTTP request sample (1385)](https://openservice.aliexpress.com/doc/doc.htm#/?docId=1385), ‏[API endpoint URLs (1369)](https://openservice.aliexpress.com/doc/doc.htm#/?docId=1369), ‏[Authorize your APP (1590)](https://openservice.aliexpress.com/doc/doc.htm#/?docId=1590) ו-SDK ה-Java הרשמי. החתימה אומתה מול הדוגמה הרשמית (`scripts/ae/test_sign.py`). הפרטים למטה נשארים כרקע.**
- **ארבע קטגוריות אפליקציה:** ‏Commercial Developer (ספק תוכנה, "not for dropshipping"), ‏Seller-inhouse, ‏**Dropshipping Developer (Individual/Corporation)** ו-**Affiliates Developer (Individual/Corporation)**. ‏**יחידים יכולים להגיש.** אפשר רק אפליקציה אחת לכל קטגוריה ([Register an application](https://openservice.aliexpress.com/doc/doc.htm?nodeId=27493&docId=118729#/?docId=1361)).
- **שלבים:** יוצרים חשבון AEOP (אימייל, אימות והסכם מפתחים). משלימים פרופיל ומעלים מסמכים, וצוות AliExpress מאשר את הפרופיל. מגישים בקשה לקטגוריה עם Reason, ואפשר לצרף קובץ כמו תוכנית עסקית. אחרי שהבקשה מאושרת יוצרים App עם Callback URL. ה-App Key וה-Secret מופיעים ב-App Overview. קבוצות הרשאות API שאינן פעילות דורשות בקשה נפרדת ([Become a developer](https://openservice.aliexpress.com/doc/doc.htm?nodeId=27493&docId=118729#/?docId=1362), ‏[API permission](https://openservice.aliexpress.com/doc/doc.htm?nodeId=27493&docId=118729#/?docId=1359)).
- **קריטריוני אישור:** **לא פורסמו.** בהסכם ה-API כתוב ש"מפתח" יכול להיות "entity or individual" שהגיש בקשה תקפה ועמד בדרישות אימות והגנת מידע ([הסכם](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202201220006_10755.html), ‏2022). לא מצאתי חסימה לישראל. **לא אומת.** הרשימה של "6 מדינות בלבד" ב-Elfsight מתייחסת לאפליקציות מוכרים, לא לדרופשיפינג.
- **נימוק מוצע לבקשה (באנגלית, להדבקה):** *"Internal sourcing tool for our own Israeli home-décor store. We search products, check freight to IL and specs, and place dropshipping orders for our customers with our AliExpress buyer account. No data resale, no third-party sellers."*
- **שיטות Dropshipper:** ‏`aliexpress.ds.text.search`, ‏`aliexpress.ds.image.searchV2`, ‏`aliexpress.ds.product.get`, ‏`aliexpress.ds.product.specialinfo.get` (תעודות), ‏`aliexpress.ds.freight.query`, ‏`aliexpress.logistics.buyer.freight.calculate`, ‏`aliexpress.ds.category.get`, ‏`aliexpress.ds.feed.itemids.get`, ‏`aliexpress.ds.order.create`, ‏`aliexpress.ds.order.tracking.get`.
- **שיטות Affiliate:** ‏`aliexpress.affiliate.product.query`, ‏`productdetail.get`, ‏`product.sku.detail.get`, ‏`product.shipping.get`, ‏`product.smartmatch`, ‏`category.get`, ‏`hotproduct.query`.
- **הרשאה:** OAuth 2.0 בשיטת "code for token": ‏`https://api-sg.aliexpress.com/oauth/authorize?response_type=code&force_auth=true&redirect_uri=…&client_id=…`, ואז `/auth/token/create` ו-`/auth/token/refresh`. ה-Gateway ‏`api-sg.aliexpress.com/sync` נגיש מהקונטיינר (HTTP 200). זה לא חסום כמו האתר.
- **מגבלת קצב:** לא מופיעה בתיעוד הציבורי. היא נקבעת לפי קטגוריית האפליקציה ומוצגת בקונסול (תיעוד 1361). ב-FAQ של `ds.product.get` (תיעוד 1790): ‏QPS כולל 500 לחיבור, 1–2% שגיאות ויסות, לישון 1–2 שניות ולנסות שוב. בסטטוס Test הטוקן תקף יום אחד (refresh יומיים); אחרי Apply Online 30 / 60 יום (תיעוד 1590). המכסה היומית של Test **לא אומתה**; `budget.py` מגביל ל-5,000 קריאות ביום עד שיועתק הערך מהקונסול.
- **זכויות תמונה:** לא מוגדרות. נשארים עם `usage_rights: unclear`, כמו היום.

#### 1.2.1 (טכני) איך מטפלים ב-token בלי להדביק אותו בצ'אט
**הוחלט ומומש (2026-10-10):** בלי Worker ובלי token בצ'אט. ‏`python3 scripts/ae/auth.py url` מדפיס את כתובת ההרשאה; המשתמש מאשר בדפדפן שלו, הדפדפן מופנה ל-`https://127.0.0.1/callback?code=...` (הדף לא נטען), וה-code מועתק משורת הכתובת אל `python3 scripts/ae/auth.py code <code>` באותו סשן (רצוי סשן על המחשב של המשתמש, שבו יש גם את משתני הסביבה). הטוקן נשמר ב-`~/.cache/ae/token.json` (‏chmod 600, מחוץ לריפו) ומתרענן אוטומטית. השלבים המדויקים: `status/handoff.md`, "AliExpress API: הרשאה ראשונה". האפשרויות הקודמות (Worker ב-Cloudflare, ‏`AE_DS_REFRESH_TOKEN`) לא נדרשות.

### 1.3 אגרגטורים וסוכנים
| שירות | מה פותח | הרשמה ודרישות | עלות | API | ישראל | אימות |
| --- | --- | --- | --- | --- | --- | --- |
| **DSers** | AliExpress, ולפי הדף ב-Shopify גם Alibaba ו-1688. חיפוש תמונה בין פלטפורמות, Supplier Optimizer | חינם עד 3,000 מוצרים; **MCP מ-Advanced** | ‏0 / ‏19.90 / ‏49.90 / ‏499.90 | **MCP רשמי** (‏60 כלים: search, ‏detail, ‏freight quotes, ‏orders); ‏Open API ב-dsers.dev (הדומיין לא נפתר) | לפי AliExpress | [תמחור](https://www.dsers.com/pricing) אומת; כתובת ה-MCP לא עקבית ב-[Glama](https://glama.ai/mcp/servers/ch8774ox9z) (‏`ai.dsers.com/mcp` מחזיר 401, כלומר דורש OAuth) |
| **AutoDS** (ישראלית) | ייבוא מספקים רבים. ‏Product Finding Hub ‏($14.97) | חנות מחוברת | ‏19.9–49.9 + תוספות | אין | לפי ספק | [תמחור](https://www.autods.com/pricing/) חלקי |
| **Zendrop** | מעל מיליון מוצרים, ‏5–20 בקשות sourcing בחודש | Shopify או Wix | ‏49 / ‏79 | אין | לא בטבלה ("Other Countries") | [Help](https://support.zendrop.com/en/articles/9981459-understanding-zendrop-pricing-plans-a-complete-guide) |
| **Spocket** | ספקים מארה"ב ואירופה | חנות | ‏39.99–299.99 | לא נמצא | לא אומת | משני |
| **Syncee** | מרקטפלייס ספקים | חנות | ‏39.99–99.99 | לא נמצא ל-Retailer | מסנן מדינה (directory.md) | משני |
| **CJ Sourcing** | ראו 1.1 | קיים | ‏0 | **כן** | כן | אומת |
| **Sup, ‏HyperSKU, ‏BuckyDrop, ‏Eprolo, ‏Sourcinbox, ‏NicheDropshipping, ‏Wiio, ‏Dropshipman** | סוכן אנושי שמביא הצעת מחיר. ‏BuckySync ‏($9.90) מחפש לפי תמונה רק ב-1688. ‏Eprolo מציין "API" בלי תיעוד | בעיקר דרך חנות Shopify או Woo | ‏0–19.90 | אין API ציבורי | אף אחד לא מפרסם קו לישראל (deep-research) | Shopify listings |

### 1.4 סיטונאות ו-B2B
- **Alibaba.com Open Platform:** יש רישום מפתח, בקשת אפליקציה ובקשת הרשאות, "לשותפים עסקיים". ה-Gateway ‏`openapi-api.alibaba.com/rest` נגיש. התיעוד נטען רק ב-JS, ולכן **לא אומת**. דורש עוסק. עדיפות נמוכה.
- **1688:** לא מצאתי API לקונים מחו"ל. הדרך היא סוכנים (deep-research).
- **Made-in-China:** אין API רשמי. יש רק scrapers, שאסורים אצלנו.

### 1.5 כלי מחקר וחיפוש הפוך לפי תמונה
| כלי | מצב | עלות | הערה |
| --- | --- | --- | --- |
| **Google Cloud Vision, ‏Web Detection** | פעיל | ‏1,000 בחודש חינם, אחר כך $3.50 לאלף ([pricing](https://cloud.google.com/vision/pricing)) | מחזיר עמודים ותמונות דומות. משם ממשיכים רק דרך API רשמי (AliExpress או CJ) |
| ‏**AliExpress `ds.image.searchV2`** | פעיל אחרי אישור | ‏0 | הדרך הכי ישירה למצוא את אותו מוצר זול יותר ב-AliExpress |
| ‏**CJ `queryProductsByImage`** | רמה 3 ומעלה | ‏1,000 נקודות לקריאה | בתוך הקטלוג של CJ |
| **TinEye API** | פעיל | מ-$200 ל-5,000 (הפוסט מ-2015) | עדיפות נמוכה |
| **Bing Visual Search** | **הוצא משימוש** ב-11.08.2025 ([Microsoft](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement)) | – | – |
| **Google Lens** | אין API רשמי | – | לא משתמשים |
| **Sell The Trend** | ‏NEXUS אוסף נתונים מאמזון, AliExpress ו-CJ. בערך $29.97–39.97 (לא אומת) | – | בלי API. כלי טרנדים, לא מקור לעיצוב |
| **AutoDS Product Hub** | ‏$14.97 | – | דורש חנות |

### 1.6 ישראל
לא מצאתי פלטפורמת דרופשיפינג ישראלית לבית עם פיד או API. ‏AutoDS ו-Importify ישראליות, אבל הן כלי ייבוא ולא ספקים. ‏DropShipISR עובד רק עם WooCommerce (directory.md). ‏OneStop ויבואני שטיחים מופיעים ב-deep-research וב-directory.md. אחרי שאפליקציית ה-DS תאושר, כדאי לבדוק אם `ds.text.search` מחזיר מוכרים עם מחסן בישראל. ‏FindNiche מציג מוצרי AliExpress "shipped from Israel" (**לא אומת**).

---

## 2. הצעה: צנרת סורסינג "פעם אחת"

### 2.1 מבנה נתונים
```
data/sources/
  <supplier>/raw/<native_id>.json      # תשובת ה-API המלאה, כמו שהיא, עם fetched_at, endpoint ו-params
  <supplier>/offers.jsonl              # רשומת Offer מנורמלת, שורה לכל הצעה
  products.json                        # Product: קבוצת Offers של אותו מוצר פיזי
  seen.json                            # מרשם "נראה / נדחה" (2.2)
  budget.json                          # מונה מכסות ותקציב לכל ספק וליום
  queue.json                           # תור עדיפויות שנוצר מחדש בכל ריצה (2.4)
```
**Offer** (הצעה אחת של ספק אחד):
`{offer_id:"<supplier>:<native_id>[:<vid>]", supplier, native_id, vid, url, title, price:{cost,currency}, freight_il:[{line,cost,days_min,days_max,checked_at}], dims_cm, weight_kg, materials, colors_raw, images:[url], image_phash:[…], certs, rating, orders, fetched_at, raw_ref, ttl_days}`

המיפוי לכרטיס לפי `data/product-card.schema.json`: ‏`supplier.name / product_url / sku ← supplier / url / native_id`. ‏`price ← price`. ‏`shipping ← freight_il` (הקו הזול שעבר את הכללים). ‏`dimensions_cm`. ‏`images.urls`. השדות העיצוביים (colors.hex, ‏visual_weight, ‏style_scores) נשארים אצל sourcing-agent ו-master-designer. **הסכמה לא משתנה.** הכרטיס מקבל רק `supplier.sku` ו-`product_url` של ההצעה שנבחרה. הקישור בין כרטיס להצעות נשמר ב-`products.json` (`card_id ↔ [offer_id]`).

**Product** (מוצר פיזי אחד, כמה ספקים):
`{product_key, card_id|null, offers:[offer_id], best_offer, match:{method:"phash|title|dims", score}}`
התאמה בין הצעות: (1) **pHash** של התמונה הראשית במרחק Hamming של 8 ומטה מתוך 64. (2) דמיון כותרת (token-set) של 0.6 ומעלה. (3) מידות בסטייה של עד 10%. צריך pHash, ועוד אחד משני האחרים. התאמה גבולית מסומנת `needs_review` ולא מתמזגת אוטומטית.

### 2.2 מרשם "נראה / נדחה" (`seen.json`)
```
{"<supplier>:<native_id>": {"first_seen":"…","last_checked":"…","state":"seen|carded|rejected|shortlisted",
  "slot":"living-room/vase","reason":"chrome pump; shipping 6×","by":"sourcing-agent|master-designer|qa","phash":"…"}}
```
- **כלל:** לפני כל קריאת `product` או `freight`, הייבואן בודק את המרשם. ‏`rejected` לא נבדק שוב לעולם, אלא אם ה-`reason` הוא מחיר או משלוח וחלפו 90 יום. ‏`seen` עם raw טרי (בתוך ה-TTL: ‏30 יום למחיר, 14 יום למשלוח) נקרא מהמטמון בלי קריאה לספק.
- **מילוי ראשוני:** ‏154 הכרטיסים הקיימים ב-`data/products` (מצב `carded`), והפסילות מקובצי `data/leads/**` (מצב `rejected`, עם הסיבה). למשל, ב-round7 בוזבזה קריאה על מוצר שכבר היה לו כרטיס. המרשם היה חוסך אותה.
- **pHash גם במרשם:** פריט שנדחה אצל CJ נדחה אוטומטית גם כשהוא מופיע ב-AliExpress, אם הסיבה עיצובית ולא מחיר.

### 2.3 ייבואן אחד לכל מקור, עם אותו CLI
‏`scripts/cj.py` (קיים), ‏`scripts/aliexpress.py`, ‏`scripts/vision.py`, ובהמשך גם `scripts/dsers` דרך MCP. כולם עם אותן פקודות:
```
search "<q>" [--page N --size N] [--category ID]
image  <image_url|path>                     # חיפוש לפי תמונה
product <native_id>
freight <native_id|vid> [--to IL] [--qty 1]
source  <image_url> --name "<n>" [--url U]  # בקשת Sourcing (CJ בלבד)
```
- פלט JSON אחיד (Offer), ו-`--raw` מחזיר את התשובה המקורית.
- מודול משותף `scripts/sourcing_common.py`: נרמול ל-Offer, כתיבת raw, בדיקה ועדכון של `seen.json`, ו-**`budget.json`**: מונה קריאות ונקודות לכל ספק וליום (CJ: נקודות לפי הטבלה; Vision: 1,000 בחודש), מגבלת קצב, ועצירה ב-80% מהמכסה עם הודעה. הוא מחליף את ה-wrapper הזמני שכל סוכן כותב מחדש (round7).
- מפתחות רק מ-env. טוקנים נשמרים ב-`~/.cache/<supplier>/`, כמו ב-CJ.

### 2.4 תור עדיפויות לפי פערים
`scripts/sourcing_queue.py` קורא את `data/slots/*.json`, סופר כרטיסים לכל עמדה (כמו `slot-gaps`), ומחשב:
`priority = (target(6) − candidates) × room_weight(living=3, dining=2, other=1) × (style_tags_match) − recent_attempts_penalty`
לכל עמדה בתור יש **search spec** קבוע (מילות מפתח, קטגוריה, מידות, חומרים אסורים, מתוך `search-specs` ו-Design Bible). הריצה עוברת על התור עד שהתקציב היומי נגמר, ומדלגת על עמדות שהגיעו ל-6 מועמדים. הסדר בכל עמדה: חיפוש ב-CJ, אחר כך ב-AliExpress, ואם עדיין חסר: בקשת Sourcing ל-CJ עם תמונת רפרנס.

### 2.5 בסטודיו: הצעות לכל מוצר ו"מצא זול יותר"
- בכרטיס מוצר מתווספת לשונית **"ספקים"** (קוראת מ-`products.json` ומ-`offers.jsonl`): טבלה של ספק, מחיר, משלוח לישראל (קו וימים), עלות נחיתה, מידות, התאמה (pHash ו-score) ותאריך בדיקה. ההצעה שנבחרה מסומנת.
- **"מצא זול יותר":** לחיצה מוסיפה בקשה ל-`queue.json` (סוג `find_cheaper`, עם `card_id`). בריצה הבאה הסוכן מריץ על התמונה הראשית: ‏AliExpress `ds.image.searchV2`, ‏CJ `queryProductsByImage` אם יש נקודות, ו-Vision Web Detection. רק מועמדים שעוברים התאמה (2.1) נכנסים כ-Offers. אם לא נמצא כלום, נשלחת בקשת Sourcing ל-CJ. לחיצה בסטודיו לא קוראת ל-API ישירות, כדי שהתקציב והמרשם יישארו במקום אחד.
- (הצעה בלבד. לא נגעתי ב-`studio/`.)

### 2.6 סדר ביצוע מוצע
1. `sourcing_common.py` ‏+ ‏`seen.json` ממולא מהקיים ‏+ ‏`budget.json`, והתאמת `cj.py` (בלי תלות במשתמש).
2. ‏`sourcing_queue.py`.
3. ‏`aliexpress.py` ‏(אחרי משימות 2–3).
4. ‏`vision.py` ופקודת `find_cheaper` ‏(אחרי משימה 4).
5. לשונית ספקים בסטודיו (frontend-dev).

## מקורות (נבדקו 2026-10-09)
- CJ: ‏[Product API](https://developers.cjdropshipping.com/en/api/api2/api/product.html), ‏[Points](https://developers.cjdropshipping.com/en/api/api2/standard/points.html), ‏[Limits](https://developers.cjdropshipping.com/en/api/start/limit.html), ‏[תוכניות (משני)](https://www.channelwill.com/Apps/cjdropshipping), ‏[Sourcing 24h](https://cjdropshipping.com/article-details/8)
- AliExpress: ‏[Overview](https://openservice.aliexpress.com/doc/doc.htm?nodeId=27493&docId=118729#/?docId=1358), ‏[Register app](https://openservice.aliexpress.com/doc/doc.htm?nodeId=27493&docId=118729#/?docId=1361), ‏[Become a developer](https://openservice.aliexpress.com/doc/doc.htm?nodeId=27493&docId=118729#/?docId=1362), ‏[API reference](https://openservice.aliexpress.com/doc/api.htm), ‏[הסכם API](https://terms.alicdn.com/legal-agreement/terms/suit_bu1_aliexpress/suit_bu1_aliexpress202201220006_10755.html), ‏[Elfsight (משני)](https://elfsight.com/blog/how-to-get-and-use-aliexpress-api-key/), ‏[Strackr, affiliate (משני)](https://strackr.com/blog/aliexpress-affiliate-program)
- DSers: ‏[Pricing](https://www.dsers.com/pricing), ‏[MCP ב-Glama](https://glama.ai/mcp/servers/ch8774ox9z), ‏[Shopify](https://apps.shopify.com/dsers)
- ‏[AutoDS](https://www.autods.com/pricing/), ‏[PricingSaaS](https://pricingsaas.com/companies/autods), ‏[Zendrop pricing](https://support.zendrop.com/en/articles/9981459-understanding-zendrop-pricing-plans-a-complete-guide), ‏[Zendrop shipping](https://support.zendrop.com/en/articles/8487356-zendrop-shipping-times-by-country), ‏[Spocket (משני)](https://toolradar.com/tools/spocket/pricing), ‏[Syncee](https://apps.shopify.com/syncee-1), ‏[BuckySync](https://apps.shopify.com/buckysync), ‏[Sourcinbox](https://apps.shopify.com/sourcinbox), ‏[HyperSKU](https://apps.shopify.com/hypersku), ‏[Eprolo](https://apps.shopify.com/eprolo), ‏[Sup](https://pickyourapp.com/de/products/sup-dropshipping-2)
- ‏[Google Vision pricing](https://cloud.google.com/vision/pricing), ‏[TinEye pricing (2015)](https://blog.tineye.com/new-image-search-pricing/), ‏[Bing retirement](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement), ‏[Sell The Trend](https://www.sellthetrend.com/compare/sell-the-trend-vs-autods)
- ‏[1688 (WorldFirst)](https://www.worldfirst.com/uk/blog/international-transactions/how-to-buy-from-1688/), ‏[Importify](https://yourstory.com/companies/importify)
