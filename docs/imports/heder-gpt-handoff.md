# HEDER — העברת Backend ל־Claude Code

תאריך: 28.09.2026. מבוסס על הקוד והמחקר השמורים בפרויקט, לא על בדיקה חדשה מול הספקים ולא על ייצוא מסד הייצור.

## מה מקבלים

הארכיון המצורף מכיל את קוד הפרויקט הנוכחי, כולל Backend, Frontend, תמונות המוצרים, חומרי ההדמיה, קבצי המחקר, migrations וקובץ הנעילה. `source/` הוא עותק מצב העבודה בפועל, כולל עבודת הפנורמה שטרם פורסמה. `CLAUDE-CODE-START.md` הוא פרומפט פתיחה מוכן. `SOURCE-MANIFEST.json` כולל נתיבים, גדלים ו־SHA-256. `SNAPSHOT.json` מתעד commit, ענף ושינויים מקומיים.

לא נכללים: מפתחות, קובצי סביבה אמיתיים, credentials, היסטוריית Git, node_modules, תוצרי build, מסד הנתונים החי או מצב מקומי של Wrangler. זהו קוד להמשך פיתוח, לא גיבוי תפעולי מלא של השירות החי. לא בוצע שינוי באתר במסגרת ההעברה.

## הכיוון המוצרי המחייב

חנות עיצוב בעברית וב־RTL בשם חדר / HEDER. חוויה במסך מלא; לחיצה על מוצר בתוך החלל פותחת דף מוצר ברור עם תמונת המקור, וריאנט, תכולה, מידות ומקור. כל פריט דקורציה מלבד הספה ושולחן הקפה צריך להיות מוצר אמיתי מזוהה. כרגע מתמקדים בסלון בוהו אחד עם 14 מוצרים; הדרישה היא לפחות 12 מוצרים מובחנים בסצנה. הסגנון הנורדי הוא מעבר סגנון נפרד, לא החדר הבא באותו סיור.

המעצב קובע את המיקום לפי היררכיה, קומפוזיציה, משקל חזותי, תאורה, קנה מידה, מרחב שלילי ושימושיות. המשתמש בוחר מה להשאיר או להוסיף; הוא אינו אמור לגרור סימונים למקומות שרירותיים. יחס הזהב וקומפוזיציה משולשת הם כלים אפשריים ולא נוסחה כפויה. תוספת יכולה לחייב שינוי בהרכב כולו.

המשתמש דחה איכות שנראית כמו משחק מחשב. העדכון האחרון: לשמור את גרסת התלת־ממד ולפתח בנפרד חוויה צילומית, תמונה רחבה עם שני אזורי מבט וגלילה חלקה אופקית ומעט אנכית. רפרנס הסגנון המחייב: `public/images/boho.png`. היעד צילום מגזין יוקרתי; אסור לתאר המחשה שנוצרה ב־AI כתצלום מדויק של מוצר יצרן. תמונת הספק היא מקור האמת למוצר.

## מצב נוכחי: מה קיים ומה לא

| תחום | מצב בפועל |
|---|---|
| אתר ואינטראקציות | קיימים; דפי מוצר, סימונים, החלפת סגנון, סל ניסיון ומסך ניהול |
| מסד נתונים | Cloudflare D1, חמש טבלאות, שתי migrations |
| קטלוג | 18 רשומות seed בסך הכול, מהן 14 מוצרי בוהו; מקורות ותמונות שמורים |
| תהליך AI | קוד לשלוש קריאות אמיתיות ל־OpenAI Responses API, אך ללא חיבור מאומת והרצה חיה מוכחת |
| יצירת הדמיה באפליקציה | לא מחוברת; `renderingConnected:false` קבוע |
| מיקום אוטומטי ושינוי סצנה | אין חיבור בין פלט הסוכנים לגאומטריה, לתמונה או לסימונים |
| מחקר בזמן הפיתוח | בוצע ונשמר בקבצים; אין להסיק ממנו שסוכן שרת רץ |
| תשלום, הזמנה וספקים | אינם מחוברים; אין checkout, webhook תשלום או יצירת הזמנת ספק |
| אישור מכירה | חסרים אימותי וריאנטים, מלאי, משלוח לישראל, מחיר סופי ותכולה |

הסוכנים הם שלבים סדרתיים עם פרומפטים שונים, לא צוות אוטונומי שממשיך ברקע. הלקוח מפעיל כל שלב בבקשת HTTP נפרדת. שמירת בקשת עיצוב במסך אינה מפעילה אותם אוטומטית.

## אירוח וגרסאות

- אתר: https://heder-studio-pilot.beeririmon.chatgpt.site
- פרויקט Sites: `appgprj_6ab51b4516788191a7489b2104dc6c09`.
- האתר היה מוגדר פרטי לבעלים לפי מצב העבודה האחרון; מדיניות הגישה לא נבדקה מחדש במשימת הייצוא.
- פרסום מוצלח אחרון שתועד: 27.09.2026, commit `7a6a43b55a56d6c6cd66a9c151d28d6e43dd6551`.
- HEAD מקומי: `705f2fb`, שיפור גילוי מוצרי התלת־ממד. נשמר גם בענף `archive/boho-3d`.
- ענף העבודה: `feature/boho-photo-slide`. כולל שינויים מקומיים שטרם עברו commit/פרסום.
- קוד הפנורמה כלול בחבילה; בדיקת ממשק בדפדפן לא הושלמה בגלל מגבלת שימוש בכלי. אין לטעון שזו גרסה מאומתת.
- חבילת ההעברה אינה מעניקה גישת פריסה לחשבון Sites או למסד הייצור. סביבת Claude יכולה לעבוד על העותק; לפריסה צריך להגדיר יעד וגישה בנפרד.

## מחסנית וקבצים מרכזיים

Node >=22.13.0; pnpm 11.25.0 לפי packageManager; React 19.2.6; TypeScript 5.9.3; Vinext 1.0.0-beta.5; Vite 8.0.13; Cloudflare Workers; Drizzle ORM 0.45.2; SQLite/D1; Zod 3.25.76. שימור `pnpm-lock.yaml` עדיף על שדרוג תלות אוטומטי. קיים next 16.3.4 אך סביבת הבנייה היא Vinext/Workers, לא שרת Next רגיל.

| קובץ | אחריות |
|---|---|
| `app/api/studio/route.ts` | seed, קריאת מצב, שמירת בקשת עיצוב וביקורת כללים |
| `app/api/design/route.ts` | אימות, cache, נעילת שלב ותזמור קריאת מודל |
| `lib/design-engine.ts` | שלבים, פרומפטים מלאים, schema, ולידציה וקריאת OpenAI |
| `lib/design-brief.ts` | עקרונות עיצוב ודרישות קלט/פלט |
| `app/api/cart/route.ts` | סל לפי זהות המשתמש |
| `app/chatgpt-auth.ts` | קריאת זהות מכותרות המועברות על ידי Sites |
| `db/raw.ts` | גישה ישירה ל־env.DB; זה המסלול בשימוש ב־API |
| `db/index.ts` | עטיפת Drizzle נוספת |
| `db/schema.ts`, `drizzle/` | schema ושתי migrations |
| `app/design-team.tsx` | מפעיל research → design → review דרך הדפדפן |
| `app/studio.tsx` | קריאות API, בחירת מוצרים, ניהול וסל |
| `.openai/hosting.json`, `vite.config.ts` | binding בשם DB, ללא R2 פעיל |

## בסיס הנתונים

| טבלה | שדות |
|---|---|
| products | id PK; name, style, category, url, supplier, price, details, shipping TEXT NOT NULL; image TEXT nullable |
| rooms | id PK; name, image TEXT; revision INTEGER default 1 |
| placements | id PK; room_id FK rooms; product_id FK products; x,y INTEGER |
| jobs | id PK; agent, room_id, status, input, output, created_at TEXT; revision INTEGER |
| cart | id PK; owner, product_id FK products, variant TEXT; quantity INTEGER default 1 |

`input` ו־`output` הם מחרוזות; חלק מפלטי jobs הם JSON וחלק טקסט רגיל. אין enum בבסיס הנתונים לסטטוס. סטטוסים בשימוש: `awaiting_connection`, `running`, `completed`, `failed`. בחינת AI יכולה להיות completed ובכל זאת להחזיר `verdict:blocked`.

אין טבלאות users, roles, orders, payments, supplier_quotes, assets או research_cache נפרדת. אין owner לחדרים ול־jobs: אלו משותפים לכל מי שיכול לגשת לאפליקציה. רק cart מבודד לפי משתמש. נתוני מחיר הם טקסט לתצוגה, לעיתים טווח של משפחת מוצרים, לא סכום לחיוב. placements אינה מכילה מודל תלת־ממד, rotation, scale או פוליגונים.

Migrations: `0000_third_multiple_man.sql` יוצרת products/rooms/placements/jobs; `0001_worried_cable.sql` מוסיפה cart. GET studio מבצע seed עם INSERT OR IGNORE; אין upsert כללי של קטלוג מעודכן. יש תיקונים נקודתיים לתמונת המקרמה ולתמונת חדר בוהו הישנה. לכן שינוי קוד הקטלוג אינו מעדכן אוטומטית רשומה קיימת במסד.

## חוזי API בפועל

### GET /api/studio

מבצע seed ומחזיר `{products, rooms, placements, jobs, cart}`. jobs מוגבלים ל־40 האחרונים; cart מסונן לפי המשתמש המזוהה. `Cache-Control:no-store`. אין בדיקת התחברות מחייבת במסלול עצמו. שגיאת תשתית: 503. המשמעות בפריסה ציבורית: נתוני jobs ו־input עלולים להיות חשופים; כרגע מעטפת האתר הפרטית היא חלק מההגנה.

### POST /api/studio

דורש משתמש; Origin זר נדחה אם הכותרת קיימת, אך היעדרה מותר. room חייב להיות nordic/boho/dining.

שמירה: `{action:"save",room:"boho",revision:1,items:["SKU"],instructions:"..."}`. עד 20 IDs ייחודיים שקיימים בקטלוג; אפס מוצרים מותר. אי־התאמת revision מחזירה 409. מגדיל revision ושומר job מסוג awaiting_connection עם productIds, instructions עד 2000 תווים וה־brief. אינו מעדכן placements, אינו מפעיל AI ואינו מחליף תמונה.

ביקורת: `{action:"audit",room:"boho"}`. סופרת JOIN של placements למוצרים ושומרת טקסט של בדיקת כללים, לא הרצת AI. בגלל שהשמירה אינה כותבת placements, הביקורת יכולה לדווח אפס גם כשהממשק מציג מוצרים. הצלחה מחזירה שוב את מצב הסטודיו; 400 קלט, 401 זהות, 403 Origin, 404 חדר, 409 גרסה, 503 שגיאה כללית.

### GET /api/design

דורש משתמש. מחזיר `{configured:boolean,model:string,renderingConnected:false}`. configured אומר רק שהוגדר מפתח, לא שבוצעה קריאת API מוצלחת.

### POST /api/design

גוף: `{room:"boho",stage:"research"|"design"|"review",instructions:"",items:["SKU"],retry?:true}`. דורש משתמש ו־Origin שווה בדיוק ל־origin של כתובת הבקשה, כולל נוכחות הכותרת. בבדיקת curl יש לשלוח Origin תואם ו־session תקין.

מגבלות נוכחיות: הוראות עד 2000 תווים, 1–12 IDs ייחודיים, כולם קיימים במסד וכולם כלולים ב־`roomProductIds[room]`. **זה חסם ממשי:** הממשק שולח 14 מוצרי בוהו, בעוד השרת מגביל ל־12 והמיפוי הישן מאשר רק 3 מוצרי בוהו.

הקשר למודל: room, revision, instructions, designerBrief, רשומות products ו־reference מתוך sceneProducts; `measuredRoomGeometry:null`. אינו שולח בפועל תמונות כקלט חזותי למודל — כתובות ומידע עוברים כחלק מ־JSON טקסטואלי.

הצלחה: `{result:{report,sources,responseId,model,usage},cached:boolean}`. שגיאות: 401/403; 503 AI_NOT_CONFIGURED; 400 קלט/מיפוי; 404 חדר; 409 שלב חסר, חסם קודם או נעילה; 502 כשל ספק/פענוח/ולידציה. JSON פגום מטופל כיום כ־502 ולא 400.

### POST /api/cart

הוספה: `{action:"add",productId:"SKU",variant:"מחרוזת מדויקת מתוך variants"}`. הסרה: `{action:"remove",id:"cart-row-id"}`. מזהה שורה מורכב מ־userId:productId:variant. הוספה חוזרת מגדילה quantity עד 99; הסרה מוחקת שורה של אותו משתמש בלבד. מחזיר `{cart:[...]}`. 400 קלט, 401 זהות, 403 Origin זר, 503 תשתית. אין שינוי כמות ישיר, סיכום חיוב, הזמנה או תשלום. רשימת variants היא רשימת ממשק, לא הוכחת SKU של וריאנט ספק.

## מערכת הסוכנים והימנעות מחישוב חוזר

הפרומפטים המלאים נמצאים ב־`lib/design-engine.ts`, ללא צורך לשחזר אותם מהתיאור כאן.

1. research: אימות כל listing/וריאנט מול מקורות ספק, מידות, חומר, תכולה, זהות צילום ואספקה לישראל. מחויב להשתמש ב־web_search; עד 5 tool calls. חסר מידע הנדרש למכירה → blocked.
2. design: מקבל דוח חוקר, קובע מיקום/הסרה/הזזה, מייצר brief באנגלית. רק ספה ושולחן קפה יכולים להיות גנריים. אינו טוען שנוצרה תמונה.
3. review: קריאת מודל נפרדת עם תפקיד מבקר; מקבל דוחות קודמים. בודק תכנית בלבד, לא תמונה מרונדרת. חוסם מקור/וריאנט/אספקה לא מאומתים.

כל השלבים משתמשים באותו model המוגדר ב־OPENAI_MODEL; ברירת המחדל בקוד gpt-4.1. אין provider של Anthropic. שימוש ב־Claude Code לפיתוח אינו מחליף את ספק ה־AI של המוצר ואינו מספק מפתח API למוצר.

קריאת POST ל־`https://api.openai.com/v1/responses`, עם store:false, timeout 110 שניות, max_output_tokens 6500, JSON Schema strict. מחקר מבקש מקורות web_search ומחייב מקור HTTPS אחד לפחות ופריט web_search_call. זו בדיקת מבנה, לא הוכחה אוטומטית שכל מקור תומך בכל עובדה. אין תמיכת vision פעילה או אימות מלא של כל claim.

report: summary עד 12000 תווים; verdict ready/blocked; blockers עד 30; decisions עד 20, כל החלטה מכילה productId/decision/reason; renderPrompt עד 16000. ולידציה דוחה IDs לא מורשים, חסר כיסוי לכל המוצרים, ready יחד עם blockers. היא אינה אוסרת החלטות כפולות לאותו ID, ואינה כופה ברמת קוד renderPrompt ריק כשהדוח חסום — אלו כרגע הוראות פרומפט.

Fingerprint: SHA-256 של `{version:2,context,model,date:UTC-day}`. מזהה job הוא `ai-{hash}-{stage}`. הקשר כולל revision, brief, instructions ומוצרים ממוינים מהמסד. אותה בקשה באותו יום יכולה להשתמש מחדש בתוצאה. שינוי revision/הוראות/יום/מודל/manifest גורר מחקר מחדש, גם אם פרטי הספק לא השתנו. זו אינה עדיין מערכת cache נפרדת לכל מוצר לאורך זמן.

השלב הבא דורש שכל קודמיו עם אותו hash יהיו completed ולא blocked. INSERT OR IGNORE משמש נעילה אטומית. job running בן יותר מ־150 שניות מסומן failed כאשר מגיע ניסיון נוסף; אין watchdog ברקע. retry:true מוחק failed ומאפשר ניסיון חדש. אין תור עבודה עמיד, scheduler או חידוש תהליך לאחר סגירת הדפדפן. כשל לאחר חיוב ספק ולפני שמירת התוצאה עלול לגרום לחיוב נוסף בניסיון הבא.

## הרשאות וסודות

`getChatGPTUser()` סומך על כותרות `oai-authenticated-user-id` ו־`oai-authenticated-user-email` שמעטפת Sites מוסיפה. הוא אינו מאמת חתימה או JWT בעצמו. בפריסה מחוץ ל־Sites אסור לסמוך על כותרות שהלקוח יכול לשלוח: צריך session/auth אמיתי או gateway מהימן שמסיר ומחליף אותן.

בסביבת portable, plugin הפיתוח מדמה משתמש רק ב־loopback ומסיר כותרות זהות נכנסות. כניסה מקומית: `/signin-with-chatgpt?return_to=/`. זהו mock לפיתוח בלבד. בייצור, נתיבי sign-in/out/callback שייכים למעטפת Sites. `app/admin/page.tsx` אינו אוכף תפקיד admin בצד שרת; התחברות אינה שקולה להרשאת עריכה.

סודות דרושים לחיבור הקיים: `OPENAI_API_KEY`, ובאופן אופציונלי `OPENAI_MODEL`. `.env.example` מכיל placeholders בלבד. ב־Workers הקוד קורא מ־env, לא ישירות process.env; יש לוודא שהסודות מוזרקים ל־Worker binding בפועל. DB הוא binding ולא DATABASE_URL. R2 אינו מוגדר כרגע; התמונות סטטיות ב־public. לא מצורפים סודות או גישת מסד חי.

## מאגר המחקר והמוצרים

`lib/boho-sources.json` הוא מקור מחקר הבוהו המרכזי: supplier URL, תמונת ספק מקומית וכתובת מקור כשנשמרה, SKU, dimensions, price, visible_shape_color ו־appearance_verified. הדגל האחרון מציין בחינה חזותית היסטורית; אינו אישור מלאי, שילוח או התאמה מסחרית.

`lib/boho-products.ts` מוסיף שמות עבריים, חומרים, תכולה ומיפוי key↔SKU. `lib/catalog.ts` בונה initialProducts ו־variants. `lib/catalog-research.json`, `docs/nordic-product-review.md` ו־`app/catalog-research.tsx` מכילים מחקר נוסף, מועמדים שנדחו ופערים. חלק מהמסמכים הישנים מתארים שלב של 2–3 מוצרים; אין לתת להם לדרוס את הדרישה העדכנית ל־14.

## פערים לתיקון לפי סדר עדיפות

1. **איחוד manifest של חדר ומוצרים.** ה־Frontend משתמש ב־bohoProducts, ה־AI במיפוי roomProductIds ישן, placements במסד במסלול שלישי, והתמונה/3D מחזיקים מיקומים נוספים. להגדיר מקור אמת אחד לגרסת חדר: SKU, וריאנט, מקורות, מופעי מוצר, מיקום וחיבור לנכס הדמיה. לתקן את מגבלת 12 ואת המיפוי ל־14 לפני ניסיון AI.
2. **זהות והרשאות.** אם יוצאים מ־Sites, להוסיף auth אמיתי; להגדיר בעלות/תפקידי עריכה לחדרים ול־jobs ולהגן על GET studio. לחזק עקביות Origin וולידציית בקשות. לא להפוך את האתר לציבורי עם הנחות ההרשאה הקיימות.
3. **גרסאות ושמירה.** בדיקת revision נעשית SELECT ואז UPDATE בלי תנאי revision ב־UPDATE; שתי בקשות יכולות לעבור את הבדיקה על אותה גרסה. צריך compare-and-swap/מנגנון אטומי שגם מבטיח ש־job נוצר רק עבור שינוי מוצלח.
4. **מחקר פעם אחת.** לפצל cache מוצר/וריאנט ממטמון תכנון חדר; לשמור checkedAt, evidence, expiry/revalidation reason וסטטוס לכל עובדה. שינוי קומפוזיציה לא צריך להפעיל מחדש מחקר לכל המוצרים. מחירי ספק/מלאי כן דורשים רענון לפי מדיניות מוגדרת.
5. **AI אמיתי ומדיד.** להגדיר סוד בצד שרת, לבצע הרצה קטנה מאומתת, לשמור usage/cost/status, rate limits ותקציב. להוציא קריאות ארוכות לתור עמיד עם polling/streaming, idempotency ותיעוד ניסיונות. חמש קריאות חיפוש עשויות לא להספיק ל־14 ספקים/פריטים — לבחון מול תוצאות, לא להכריז מראש על השלמת מחקר.
6. **דוח מול נכס.** להוסיף סכמת plan עם מופעי מוצר וקנה מידה מותנה בראיות; תמיכה בקלט חזותי; שירות יצירת תמונה; אחסון נכסים; בדיקת התאמה חזותית לכל מוצר; hotspot polygons מהתמונה המאושרת. review הנוכחי אינו בודק פיקסלים.
7. **הפרדת טיוטה מפרסום.** גרסת חדר נוכחית, candidate נפרד, סטטוס בדיקת נאמנות, אישור ורק אז החלפה אטומית. אם יצירה או בדיקה נכשלת — להשאיר את התמונה המאושרת.
8. **קטלוג בר־מכירה.** exact supplier variant, מידות מוצר ולא אריזה, מחיר במטבע מוגדר, תכולה, כמות, ישראל/משלוח/מכס לפי בדיקה נפרדת, זכויות תמונות והסדר אספקה. מקורות retail כמו IKEA ו־Cox & Cox אינם אינטגרציית dropshipping.
9. **מסחר אחרי אימות.** orders/order_items, snapshots של מחיר/וריאנט, תשלום עם webhooks ו־idempotency, מלאי והזמנת ספק; אלו הצעות להמשך ולא חלק מהמימוש הנוכחי.

פער נוסף בנעילת AI: לאחר סימון running ישן כ־failed וניסיון מחדש, העובד הישן עשוי עדיין לכתוב completed לאותו jobId. מומלץ token ייחודי לכל ניסיון וכתיבה מותנית בבעלות הנעילה. ה־fingerprint אינו כולל owner, ולכן תוצאות/הוראות משותפות בין משתמשים כאשר ההקשר זהה. כמו כן context לא כולל את כתובת תמונת החדר עצמה; צריך לכלול asset hash/גרסת תמונה כאשר ההדמיה הופכת לחלק מהתכנון.

## התחלה מקומית ב־Claude Code

לחלץ את ה־ZIP, לפתוח את תיקיית השורש שבה המסמך ו־source, ולתת ל־Claude לקרוא את `CLAUDE-CODE-START.md`.

להתחיל בשימור הקוד ובדיקת סביבת Node/packageManager. README בפרויקט הוא ברובו starter ויש בו הוראות npm מיושנות; המקור העדכני הוא package.json וקובץ pnpm-lock.yaml. `install:ci` הנוכחי הוא wrapper לסביבת Linux המנוהלת ולא פקודת התקנה ניידת מומלצת ל־macOS/Windows.

פקודות פתיחה מוצעות, מתוך source, עם pnpm 11.25.0 זמין:

```sh
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit
pnpm run build
```

אין צורך לשחזר `.sites-runtime/execution-profile.json`: בהיעדרו נבחר portable. ייתכן שתידרש התאמת כלי הסביבה במחשב החדש; הפקודות לא הורצו מחדש על מחשב חיצוני. אין למחוק lockfile כדי לעקוף שגיאת התקנה.

לאחר build נוצרת `dist/server/wrangler.json`. להקמת מסד מקומי **חדש בלבד**, להחיל את שתי migrations בסדר הזה:

```sh
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_third_multiple_man.sql
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0001_worried_cable.sql
pnpm run dev
```

אין להריץ שוב את CREATE TABLE על מסד שכבר עבר migration. שרת portable מתחיל בדרך כלל ב־http://localhost:5173. לבקר במסלול הכניסה המקומית לעיל ואז לטעון את הסטודיו כדי לבצע seed. `pnpm run start` מפעיל preview של Worker בנוי, אך אינו מדמה כניסה; לבדיקה אינטראקטיבית ראשונית להשתמש ב־dev.

לפריסה חדשה ב־Cloudflare יש ליצור משאבים בבעלות המשתמש ולהחליף placeholder DB ID/תצורת auth; אין להתייחס ל־.openai/hosting.json כאישור לפרוס לפרויקט הקיים. עבור Node hosting אחר יש להתאים את גישת cloudflare:workers ואת D1, ולא רק להחליף פקודת build. אין צורך לבצע מעבר ספק תשתית כדי להתחיל לקרוא ולשפר את הקוד.

## בדיקות קבלה מומלצות להמשך

- מסד ריק + migrations + GET studio נותנים 18 מוצרים ושלושה IDs של חדרים ללא כפילויות.
- כל 14 מוצרי בוהו עוברים validation של manifest; מוצר מומצא ווריאנט לא קיים נדחים.
- משתמש אחד אינו קורא או משנה מידע פרטי של אחר; משתמש ללא הרשאת עיצוב אינו מפעיל jobs בתשלום.
- שתי שמירות עם revision זהה: אחת בלבד מצליחה.
- שתי בקשות AI זהות: רק קריאת ספק אחת; blocked עוצר; cached אינו מחייב שוב; retry אינו מאפשר לעובד ישן לדרוס ניסיון חדש.
- היעדר key מחזיר 503 עם AI_NOT_CONFIGURED; UI אינו מציג הצלחה מדומה.
- כשל render אינו מחליף תמונה; כל hotspot בגרסה מאושרת פותח את ה־SKU/וריאנט הנכון.
- תיקון תיאור/מחיר בלבד אינו יוצר תמונה מחדש.

## גבולות האימות בהעברה

נבדקו קובצי המקור, התאמת ה־API לנתונים, מצב Git, תכולת החבילה ויישום שתי migrations ב־SQLite זמני. לא בוצעו כאן קריאות מודל בתשלום, רענון ספקים, ייצוא מסד חי, התקנה בסביבת Claude או פריסה חדשה. בדיקות קוד/ויזואליות קודמות מפורטות ב־docs; הן אינן מהוות אימות להרצת מודל או לאיכות WebGL על מכשיר משתמש.

## רשימת 14 מוצרי הבוהו שנאספו

הנתונים הבאים מועתקים מהמחקר השמור. המחירים ההיסטוריים אינם הצעת מחיר עדכנית. קישורי הספק המלאים ותמונותיו כלולים גם ב־lib/boho-sources.json וב־public/images/products.

| key | SKU | ספק | מידות שנשמרו | מחיר היסטורי |
|---|---|---|---|---|
| sofa | CJYD219350401AZ | CJdropshipping | 3-seat length range 190–230 cm; measure sofa before selection | USD 6.18–11.74 product-family range |
| woodwall | CJYD218133201AZ | CJdropshipping | 8 cm square variant; full dimensions unknown | USD 13.76–15.75 family range |
| beigetable | CJSN243818901AZ | CJdropshipping | Unknown (only package dimensions published) | USD 14.26–31.84 family range |
| pleatedfloor | CJSN166907901AZ | CJdropshipping | Unknown | USD 9.02–24.19 family range |
| curtains | CJYD190543801AZ | CJdropshipping | Supplier format codes 5263 / 5272 / 5284 / 5295 / 52108; units unverified | USD 6.47–9.15 family range |
| tasselrunner | CJZW127706201AZ | CJdropshipping | 30×120 cm selected; 180/220/280 cm lengths also listed | USD 1.89–3.98 family range |
| rattanmag | 1745793 | Cox & Cox | H31 × W42 × D25 cm | GBP 40 |
| cushion | CJZT189401901AZ | CJdropshipping | 45×45 cm | USD 1.78–2.90 family range |
| brownevase | CJYD219421101AZ | CJdropshipping | Unknown | USD 7.60 |
| bohorug | CJFU28588360001 | CJdropshipping | 72×108 in (182.88×274.32 cm), pile 0.14 in | USD 89.60 |
| macrame | CJJJYSSZ00116-Khaki | CJdropshipping | 40×80 cm from prior catalog; not reverified in extracted text | USD 9.92–10.54 family range |
| bohobasket | 603.221.73 | IKEA Israel | Diameter25 × H32 cm, folded height18 cm | ILS 59 |
| incense | CJYD205731501AZ | CJdropshipping | Unknown; package 150x150x100mm is not product dimension | USD 3.52; white variant exact SKU unverified |
| candle | CJSD163486901AZ | CJdropshipping | Unknown; package 100x80x80mm is not product dimension | USD 0.63–0.65 family range |

דגשים: כיסוי הספה נמכר ללא ספה; הציפית ללא מילוי; הווילונות פוליאסטר במראה פשתן; מנורת השולחן היא הגרסה הקטנה בתמונת הספק; SKU הלבן למעמד הקטורת לא אומת; נר ומקלות קטורת אינם מובטחים בתכולה. החומר באגרטל החום מופיע בסתירה במטא־נתוני הספק.
