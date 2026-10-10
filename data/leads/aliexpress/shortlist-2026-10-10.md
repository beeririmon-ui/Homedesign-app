# רשימת AliExpress לפתיחה בסשן המקומי (2026-10-10)

> sourcing-support, דפי חיפוש בלבד (`aliexpress.com/w/wholesale-<keywords>.html`), לפי studio-rules ד.6 (בלי עקיפת חסימות) ו-ז.00. **דפי המוצר לא נפתחו**: הכותרת, המחיר והמשלוח הם מה שדף החיפוש מראה, ולא יותר. ציון ההתאמה (1–10) הוא ניחוש מהכותרת והמחיר בלבד, מול `docs/design-bible/nordic.md` ו-`nordic-dining.md`. עד 2 דפי חיפוש לעמדה, 12 תוצאות בכל דף (זה מה שהשרת מחזיר בלי JS).
> הפריטים רשומים ב-`data/sources/seen.json` כ-`aliexpress:<item_id>`, סטטוס `seen`, ‏`opened: false`. הנתונים המובנים: `shortlist-2026-10-10.json`.
> **מזהים:** דף החיפוש מחזיר קישורים בצורת `aliexpress.us/item/<id>` (מזהים שמתחילים ב-3256/2255/2251). לפתוח אותם כמו שהם; אם הדפדפן מפנה ל-`aliexpress.com` עם מזהה אחר (1005...), לרשום את שניהם בכרטיס. פריט אחד (sink-set) הגיע מדף חבילה עם מזהה 1005... מתוך `productIds`.
> נבדק מול המרשם: אף אחד מ-90 הפריטים לא הופיע קודם (כולל מול 187 הלידים הישנים של AliExpress מ-2026-09-28).

## מה לעשות עם כל פריט (בדפדפן של המשתמש)
1. לפתוח את הקישור, לוודא **משלוח לישראל** (עלות וימים, שתי אפשרויות: חסכוני ומהיר).
2. לרשום מחיר אמיתי לווריאציה הרלוונטית, **מידות מלאות, חומר, גוון** (HEX מהתמונות), ותמונות מכמה זוויות.
3. מנורות: CE, ‏220–240V, סוג החיבור (מחווט/תקע), לא העתק של דגם מוכר.
4. אם עובר את הסינון הקשיח של `.claude/agents/sourcing-agent.md`: כרטיס ב-`data/products/<slot>/` (או `data/products/dining/<slot>/`), ו-`registry.py add aliexpress:<id> --status card --card-id <id>`. אם נדחה: `--status rejected --reason "..."`.

## סיכום לפי עמדה

| חדר | עמדה | ברשימה | ציון מרבי | חיפושים | הערכה |
| --- | --- | --- | --- | --- | --- |
| living-room | cushions | 6 | 7 | boucle-cushion-cover-50x50; sage-green-linen-cushion-cover | טוב |
| living-room | curtains | 8 | 7 | sheer-linen-curtain-280cm; linen-sheer-curtain-custom-wave | טוב |
| living-room | candle-holders | 6 | 6 | travertine-candle-holder; stone-pillar-candle-holder | בינוני |
| living-room | bowl | 2 | 4 | matte-ceramic-bowl-decorative-shallow; nordic-ceramic-decorative-bowl | חלש |
| living-room | accent-sconces | 8 | 8 | travertine-wall-lamp; travertine-wall-lamp (SortType=total_tranpro_desc) | טוב |
| living-room | pouf | 4 | 6 | knitted-cotton-pouf-ottoman; chunky-knit-pouf-round | בינוני |
| living-room | rug | 5 | 5 | wool-flatweave-rug-240x300; flat-weave-cotton-rug-living-room | בינוני |
| living-room | floor-lamp | 0 | - | floor-lamp-linen-drum-shade-black; nordic-floor-lamp-fabric-shade | אין תוצאה |
| dining-room | table-runner | 2 | 5 | linen-table-runner-35x140; washed-linen-table-runner-natural | חלש |
| dining-room | centerpiece-vase | 9 | 7 | matte-ceramic-vase-nordic-white | טוב |
| dining-room | candle-holders | 8 | 7 | black-ceramic-pillar-candle-holder; matte-black-metal-pillar-candle-holder | טוב |
| dining-room | floor-vase | 6 | 7 | large-floor-vase-ceramic-60cm; tall-ceramic-floor-vase-white | טוב |
| dining-room | kitchen-sconce | 7 | 8 | ceramic-wall-lamp-kitchen-nordic; wall-sconce-linen-shade | טוב |
| dining-room | sink-set | 7 | 6 | ceramic-soap-dispenser-dish-brush-tray-set; dish-soap-dispenser-ceramic-tray | בינוני |
| dining-room | utensil-crock | 4 | 6 | stoneware-utensil-holder-crock; ceramic-utensil-holder-kitchen-white (ריק/חסום) | בינוני |
| dining-room | cutting-boards | 5 | 5 | oak-cutting-board-wood-handle; white-oak-cutting-board (ריק/חסום) | בינוני |
| dining-room | herb-pots | 3 | 5 | ceramic-herb-pot-saucer-white-matte; white-ceramic-planter-with-saucer-small (ריק/חסום) | חלש |

## living-room / cushions — כריות (סט של 4 כיסויים, 45–50; לפי ה-Bible: לבן חם / מרווה / פחם, לא שיבולת שועל על הספה)

חיפושים: `wholesale-boucle-cushion-cover-50x50.html`; `wholesale-sage-green-linen-cushion-cover.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Textured Boucle Throw Pillow Covers Accent Solid Pillow Cases Couch Cushion Case for Chair Sofa Bedroom Living Room Home Decor | 7.17 | `3256806985105007` | [פתח](https://www.aliexpress.us/item/3256806985105007.html) | - | 250 sold | 7 | בוקלה חלקה ומט, הכי נמכרת מבין תוצאות הבוקלה; הגוונים לא בכותרת (רק 1 בוקלה בסט) |
| 2 | Boucle Pillow Covers Textured Striped Couch Cushion Covers Soft Decorative Pillowcase Sofa Chair Bedroom Living Room Home Decor | 4.75 | `3256809704342481` | [פתח](https://www.aliexpress.us/item/3256809704342481.html) | - | 6 sold | 6 | בוקלה עם פסים (מותרת דוגמה אחת בסט); הגוונים לא בכותרת |
| 3 | 40x40 45x45 50x50 Solid Color Jacquard Pillow Cover for Sofa Office Waist Cushion Cover Home Decorative Pillowcase Decoration | 1.09 | `3256810456027784` | [פתח](https://www.aliexpress.us/item/3256810456027784.html) | - | 3,000+ sold | 6 | חלק, ז'קארד טון-על-טון, המידות 45/50 בכותרת; לבדוק ברק |
| 4 | Corduroy Pillow Cover 40X40 45X45 50x50 30x50 CM Soft Plush Flannel Cushion Cover Fluffy Couch Pillow Case for Sofa Living Room | 1.09 | `3256810369976148` | [פתח](https://www.aliexpress.us/item/3256810369976148.html) | - | 1,000+ sold | 6 | קורדרוי מט מותר ב-Bible; 'plush flannel' בכותרת מחייב בדיקת ברק; כולל 30x50 |
| 5 | Cotton Linen Sofa Cushion Cover Decoration Throw Pillow Cover Waist Pillowcase Pillows for Sofa Bed Chair Couch Decorative | 25.11 | `3256812390972386` | [פתח](https://www.aliexpress.us/item/3256812390972386.html) | Free shipping | - | 5 | כותנה-פשתן; גוון לא בכותרת; מחיר גבוה לכיסוי |
| 6 | Aesthetic L-Light G-Green F-Fresh S-Style Cushion Cover Cushion Covers Natural Linen Breathable Sofa Bedroom Decor Pillowcase | 4.93 | `3256812625300543` | [פתח](https://www.aliexpress.us/item/3256812625300543.html) | Delivery: Oct 16 - 22 | 9 sold | 5 | פשתן בירוק בהיר, מועמד לכרית המרווה החובה; ייתכן שמודפס |

**הערה:** שני הדפים מלאים בהדפסים, בקטיפה ובפריטי חג; הבוקלה והקורדרוי הם התוצאות היחידות שמתאימות. אין עדיין כרית מרווה ודאית. הבריף ביקש גם 'שיבולת שועל', אבל ה-Bible אוסר שיבולת שועל ואפור ערפל על הספה (כלל הניגוד), ולכן לא חיפשתי אותה.

## living-room / curtains — וילונות (פשתן שקוף, 140 × 278–282, לבן חם / שיבולת שועל / אפור ערפל; גם לפינת האוכל, פאנל אחד)

חיפושים: `wholesale-sheer-linen-curtain-280cm.html`; `wholesale-linen-sheer-curtain-custom-wave.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Cotton and Linen Texture Translucent Curtains for Bedroom Living Room with UV Protection Sheer Curtain Window Screen Yarn Custom | 7.72 | `3256811998576912` | [פתח](https://www.aliexpress.us/item/3256811998576912.html) | - | 178 sold | 7 | כותנה-פשתן עם טקסטורה, חצי שקוף, מידה מותאמת (אפשר 280) |
| 2 | Linen Sheer Curtains Custom Cotton and Linen Texture Translucent Curtains for Bedroom Living Room with UV Protection Sheer Curtain Window Screen Yarn Custom | 5.35 | `3256808664091154` | [פתח](https://www.aliexpress.us/item/3256808664091154.html) | - | 700+ sold | 7 | אותה משפחה, הכי נמכרת; מידה מותאמת |
| 3 | Custom Size White Tulle Beige Linen Look Sheer Curtians S Wave for Living Room Bedroom Luxury Modern Elegant Modern Villa Drape | 0.99 | `3256810570758345` | [פתח](https://www.aliexpress.us/item/3256810570758345.html) | - | 291 sold | 7 | בז' במראה פשתן, קפלי גל (S wave), מידה מותאמת; כנראה פוליאסטר, לבדוק טקסטורה |
| 4 | Modern Beige Natural Linen Like Tulle Living Room Flax Sheer Curtains for Bedroom Voile Window S Folds Custom Size Drapes | 31.50 | `3256805238071479` | [פתח](https://www.aliexpress.us/item/3256805238071479.html) | Free shipping | 54 sold | 7 | בז' פשתן-למראה, קפלי S, מידה מותאמת; מחיר מלא לפאנל |
| 5 | Modern Elegant Linen Sheer Yarn Curtains for Living Room Bedroom Balcony Gauze Window Cotton-linen Yarn Tulle | 5.41 | `3256812815929324` | [פתח](https://www.aliexpress.us/item/3256812815929324.html) | - | 96 sold | 6 | פשתן-כותנה שקוף; מידות לא בכותרת |
| 6 | 310cm Height Custom Made Sheer Solid Color Linen Window Living Room Tulle Finished Custom Curtain | 13.12 | `3256809921299937` | [פתח](https://www.aliexpress.us/item/3256809921299937.html) | Free shipping | - | 6 | גובה 310 מותאם, פשתן חלק; צריך 278–282 |
| 7 | 350cm Height Custom Made 270CM Length Sheer Curtain Solid Color Curtain Window Living Room Tulle Curtain Finished Curtain | 21.84 | `3256808128419857` | [פתח](https://www.aliexpress.us/item/3256808128419857.html) | - | 77 sold | 6 | מותאם לגובה; לוודא אורך 280 וטקסטורת פשתן |
| 8 | 1pc Japanese linen sheer curtain windproof breathable semi dark bedroom living room partition curtain Mosquito prevention | 4.83 | `3256809090221001` | [פתח](https://www.aliexpress.us/item/3256809090221001.html) | - | 900+ sold | 5 | פשתן יפני שקוף; 'semi dark' מרמז על בד כבד יותר; מידות לא בכותרת |

**הערה:** תוצאה טובה: רוב הפריטים במידה מותאמת (custom), כך ש-280 אפשרי. לבדוק בדף: פשתן אמיתי או פוליאסטר במראה פשתן, מעבר אור, וסוג התלייה (גל/לולאות; בלי עיניות כרום).

## living-room / candle-holders — פמוטים (זוג, טרוורטין/אבן, לנר עמוד 7 ס"מ, מחזיק עד 12 ס"מ)

חיפושים: `wholesale-travertine-candle-holder.html`; `wholesale-stone-pillar-candle-holder.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Designer Luxury Stone Candle Holder, French Style Travertine & Marble Pillar, Vintage Natural Sculptural Decor for Dining Table | 19.83 | `3256810519991816` | [פתח](https://www.aliexpress.us/item/3256810519991816.html) | - | 1 sold | 6 | טרוורטין, 'pillar' בכותרת, מחיר סביר; לוודא שזה לנר עמוד 7 ס"מ וגובה עד 12 |
| 2 | Rustic Marble Block Candle Holder Vintage Travertine Candlestick for Christmas Decoration | 30.16 | `3256810087304990` | [פתח](https://www.aliexpress.us/item/3256810087304990.html) | Free shipping | 7 sold | 6 | בלוק טרוורטין (צורה מותרת); 'candlestick' עלול להיות לטייפר |
| 3 | Luxury Marble Candle Holder Retro Travertine Pillar Candlestick For H Living Room Home Decor Non-slip Stable Desk Decoration | 40.11 | `3256812300909012` | [פתח](https://www.aliexpress.us/item/3256812300909012.html) | - | - | 6 | טרוורטין לנר עמוד לפי הכותרת; מחיר גבוה יותר |
| 4 | Natural Marble Candle Holder Vintage Travertine Candlesticks for Home Decorations | 29.67 | `3256809678294632` | [פתח](https://www.aliexpress.us/item/3256809678294632.html) | - | 1 sold | 5 | טרוורטין טבעי; סוג הנר לא ברור |
| 5 | Natural Marble Candle Holders for Pillar Candle Luxury Candlestick for Table Centerpieces Coffee Table Fireplace Mantel | 83.48 | `3256810096092169` | [פתח](https://www.aliexpress.us/item/3256810096092169.html) | - | 3 sold | 5 | לנר עמוד במפורש; יקר, ושיש עלול להיות מלוטש (אסור) |
| 6 | Vintage Candle Holder Ins Cave Stone Candle Table Home Model Room Living Room Desktop Soft Decoration Creative Oral Tape Holder | 23.36 | `3256812015499356` | [פתח](https://www.aliexpress.us/item/3256812015499356.html) | - | - | 4 | אבן 'מערה' במראה wabi-sabi; החומר והמידות לא ברורים |

**הערה:** יש טרוורטין, אבל הרוב 'candlestick' (לטייפר, אסור) או יקר. לבדוק בדף: משטח שטוח/שקע רדוד לנר 7 ס"מ, גובה המחזיק עד 12, ושנמכר כזוג או שאפשר להזמין 2.

## living-room / bowl — קערה נמוכה (קרמיקה מט, קוטר 16–24, גובה 5–9)

חיפושים: `wholesale-matte-ceramic-bowl-decorative-shallow.html`; `wholesale-nordic-ceramic-decorative-bowl.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Household Ceramic Bowls, Kitchen Utensils, Salad Bowls, White Slanted Mouth Bowls, Desserts, Buffet, Side Dishes, Tableware | 13.74 | `3256812961556931` | [פתח](https://www.aliexpress.us/item/3256812961556931.html) | Delivery: Oct 16 - 21 | - | 4 | קרמיקה לבנה, פה משופע; כלי שולחן (כנראה זיגוג מבריק), קוטר לא ידוע |
| 2 | Japanese-Style Ceramic Oak Shallow Plate Restaurant Vintage Western Cuisine Plate round Steak Dessert Plate | 33.92 | `3256806739667318` | [פתח](https://www.aliexpress.us/item/3256806739667318.html) | Free shipping | 18 sold | 4 | צלחת עמוקה-רדודה בסגנון יפני; 'oak' כנראה גוון זיגוג; יקר, קוטר לא ידוע |

**הערה:** תוצאה חלשה בשני הדפים (כלי אוכל, קערות חתול, הדפסים). רק שני פריטים גבוליים. להמשיך דרך CJ/Zendrop או חיפוש בדפדפן של המשתמש עם מילים כמו 'stoneware fruit bowl matte'.

## living-room / accent-sconces — זוג מנורות קיר טרוורטין (10–14 × 12–18, מחווטות, CE, 220–240V)

חיפושים: `wholesale-travertine-wall-lamp.html`; `wholesale-travertine-wall-lamp (SortType=total_tranpro_desc).html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Indoor Stone Wall Lamp Travertine Sconce Light Hardwired With E27 Bulb for Bedroom Living Room | 49.15 | `3256807415537790` | [פתח](https://www.aliexpress.us/item/3256807415537790.html) | - | 333 sold | 8 | טרוורטין, מחווט (hardwired) ו-E27 בכותרת: בדיוק דרישת העמדה; לוודא CE ו-220–240V |
| 2 | Wabi Sabi Yellow Marble Wall Lamp Led Bedside Japan Bedroom Living Room Wall Light Travertine Stair Corridor Decor Sconce | 39.92 | `3256807290245107` | [פתח](https://www.aliexpress.us/item/3256807290245107.html) | Delivery: Oct 16 - 22 | 1,000+ sold | 6 | הכי נמכרת בקטגוריה; 'yellow' עלול להיות חם מדי מול שנהב; לבדוק אם LED מובנה או E27 |
| 3 | Wabi Sabi Yellow Marble Wall Lamp Led Bedside Japan Bedroom Living Room Wall Light Travertine Stair Corridor Decor Sconce | 36.42 | `3256808817161320` | [פתח](https://www.aliexpress.us/item/3256808817161320.html) | - | 900+ sold | 6 | אותו דגם אצל מוכר שני (מקור שני לכלל FR-D) |
| 4 | Wabi Sabi Yellow Marble Wall Lamp Led Bedside Japan Bedroom Living Room Wall Light Travertine Stair Corridor Decor Sconce | 42.01 | `3256809412711276` | [פתח](https://www.aliexpress.us/item/3256809412711276.html) | - | 500+ sold | 6 | אותו דגם אצל מוכר שלישי |
| 5 | Yellow Travertine Wabi Sabi Black Stone Retro Wall Lamp E27 Bedside Home Decor Light for Bedroom Living Room Corridor | 42.35 | `3256808314259008` | [פתח](https://www.aliexpress.us/item/3256808314259008.html) | Delivery: Oct 16 - 22 | 255 sold | 6 | E27; פרט אבן שחורה (פחם עד 10% מותר); לבדוק חיווט |
| 6 | Yellow Travertine Stone Japanese Style Wabi-Sabi Wall Lights Bedroom Dinning Room Wall Lamp Designer Retro Outdoor Wall Sconces | 25.94 | `3256806665832846` | [פתח](https://www.aliexpress.us/item/3256806665832846.html) | - | 238 sold | 6 | הזולה; מתאימה גם לחוץ (גוף אטום); מידות לא בכותרת |
| 7 | Natural Stone Room Decor Wall Lamp Classical Wall Lights Bedroom Led Sconce Yellow Travertine Home Decorations Lighting Fixtures | 48.04 | `3256812962122929` | [פתח](https://www.aliexpress.us/item/3256812962122929.html) | - | 131 sold | 6 | טרוורטין; 'classical' עלול להיות צורה מעוטרת |
| 8 | Wabi Sabi Travertine Wall Light Natural Stone LED Wall Sconce Lamp Living Room Hallway Bedroom Bedside Aisle Stair Home Deocr | 64.54 | `3256809843434389` | [פתח](https://www.aliexpress.us/item/3256809843434389.html) | - | 25 sold | 5 | טרוורטין; LED (לבדוק אם נורה מתחלפת); מעט מכירות |

**הערה:** הקטגוריה הכי עשירה: עשרות מנורות טרוורטין, רובן בגוון 'yellow travertine'. מועדף 3256807415537790 (מחווט + E27 בכותרת). פסלתי מהכותרת: דגמים עם עץ אגוז ושרשרת משיכה (מנורות קריאה, לא גוף אבן נקי), דגם עם אהיל זכוכית, ודגמי 'Duo' למראה (אולי למקלחת). לבדוק בדף: מידות (10–14 × 12–18), בליטה 7–12, CE, 220–240V, חיבור לקופסה בקיר.

## living-room / pouf — פוף (כותנה סרוגה, קוטר 42–45, גובה 35–36)

חיפושים: `wholesale-knitted-cotton-pouf-ottoman.html`; `wholesale-chunky-knit-pouf-round.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Round Pouf Ottoman Cotton Knit Foot Stool Boho Floor Seat 20"x14.5" Living Room Bedroom Home Office, Customized | 51.62 | `3256812731089635` | [פתח](https://www.aliexpress.us/item/3256812731089635.html) | Free shipping | - | 6 | כותנה סרוגה; 50×37 ס"מ: הקוטר מעל 45, 'customized' אולי מאפשר 45; הגובה 37 בגבול |
| 2 | 11 Colors Sofa Cushion Knitted Woolen Round Cushion POUF Indoor Decorations With Inner | 53.82 | `2255800342684091` | [פתח](https://www.aliexpress.us/item/2255800342684091.html) | - | 9 sold | 6 | צמר סרוג עם מילוי, 11 גוונים; המידות לא בכותרת |
| 3 | OTAUTAU Cotton Linen Beanbag Ottoman Footrest Cover for Bean Bag Chair Small Round Footstool Corner Seat Stool Pouf JD001 | 1.09 | `3256803915489749` | [פתח](https://www.aliexpress.us/item/3256803915489749.html) | - | 247 sold | 5 | כיסוי כותנה-פשתן בלי מילוי (מותר בתנאי תמונות ממולא); מידות לא בכותרת |
| 4 | 45x20cm Japanese Style Meditation Cushion Homestay Tatami Moroccan Pouf Cover Unstuffed Ottoman Luxury Cotton Footstool Futon | 27.01 | `3256811762215747` | [פתח](https://www.aliexpress.us/item/3256811762215747.html) | Free shipping | - | 4 | קוטר 45 נכון, אבל גובה 20 נמוך מדי (דרוש 35–36) |

**הערה:** תוצאה חלשה: הדפים מלאים בבין-בגים, בשרפרפי אחסון ובכריות מדיטציה נמוכות. הפריט הראשון הוא היחיד שסרוג וגבוה מספיק, אבל רחב ב-5 ס"מ.

## living-room / rug — שטיח (צמר/כותנה בקליעה שטוחה, 200–240 × 290–340, בהיר)

חיפושים: `wholesale-wool-flatweave-rug-240x300.html`; `wholesale-flat-weave-cotton-rug-living-room.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Luxury Woven Sisal Rug Minimalist Carpet for Living Room Bedroom Entryway Non Slip Home Decoration | 128.33 | `3256812098237494` | [פתח](https://www.aliexpress.us/item/3256812098237494.html) | Free shipping | 2 sold | 5 | סיזל ארוג (סיב טבעי מותר, חוק ג.5); מידות לא בכותרת |
| 2 | Handwoven Pure Cotton Rug Antique Style Kitchen Absorbent Floor Mat Home Study Tassel Carpet Bedroom by the Bed | 54.74 | `3256812175255972` | [פתח](https://www.aliexpress.us/item/3256812175255972.html) | Free shipping | 2 sold | 5 | כותנה ארוגה ביד, קליעה שטוחה; פרנזים (עד 8 ס"מ) ומידות לבדיקה |
| 3 | Cotton Linen Woven Carpet Solid Color Handmade Study Room Floor Mats Modern Round Carpets Bedroom Living Room Area Rug | 34.12 | `3256808692218189` | [פתח](https://www.aliexpress.us/item/3256808692218189.html) | - | 3 sold | 4 | כותנה-פשתן חלק; הכותרת מזכירה עגול (אסור), לבדוק אם יש מלבן 240×300 |
| 4 | Cotton Linen Weave Carpet for Living Room Kitchen Area Rugs Bedroom Bedside Floor Mat Water Absorbent | 16.98 | `3256812245074067` | [פתח](https://www.aliexpress.us/item/3256812245074067.html) | - | 3 sold | 4 | אריג כותנה-פשתן; לפי המחיר כנראה מידות קטנות |
| 5 | Large Size Carpet for Living Room Nordic Solid Sofa Coffee Table Dirt-resistant Floor Mat Light Luxury High-end Bedroom | 175.10 | `3256807986413440` | [פתח](https://www.aliexpress.us/item/3256807986413440.html) | - | 44 sold | 4 | גדול וחלק; החומר לא בכותרת (כנראה פוליאסטר רך) |

**הערה:** תוצאה חלשה: 'flatweave' ו-240x300 לא נתפסים בחיפוש; הרוב שטיחים מודפסים או קטנים. המידה לא מופיעה באף כותרת. שטיח כנראה צריך מקור אחר (ספק ישראלי, לפי ד.1).

## living-room / floor-lamp — מנורת אהיל (מתכת שחורה, אהיל פשתן תוף 35–38, 220–240V)

חיפושים: `wholesale-floor-lamp-linen-drum-shade-black.html`; `wholesale-nordic-floor-lamp-fabric-shade.html`

_אין פריטים ברשימה._

**הערה:** אין תוצאה: שני הדפים החזירו אהילים להחלפה ומנורות קשת/פטרייה/פליז. לא שורשרתי כלום. פריט אהיל שימושי אם נחליט על בסיס נפרד: 3256810271379988 ‏Oatmeal Linen Drum Lamp Shade ($14.16) — לא נרשם.

## dining-room / table-runner — ראנר (פשתן, 33–38 × 135–145)

חיפושים: `wholesale-linen-table-runner-35x140.html`; `wholesale-washed-linen-table-runner-natural.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Luxe Linen Antique Style Table Runner - Various Lengths available Elegant Dining Decor | 1.09 | `3256811391297603` | [פתח](https://www.aliexpress.us/item/3256811391297603.html) | - | 4 sold | 5 | ראנר פשתן חלק במגוון אורכים; גוון ורוחב לא בכותרת |
| 2 | 30cm Width Jute Linen Vintage Natural Table Runner Burlap Rustic Khaki Party Country Wedding Decoration Home Party Chair Decor | 1.09 | `3256806761268500` | [פתח](https://www.aliexpress.us/item/3256806761268500.html) | - | 89 sold | 4 | יוטה-פשתן טבעי; רוחב 30 מתחת למינימום 33, מרקם גס |

**הערה:** תוצאה חלשה: כמעט הכול מודפס (סתיו, חג מולד, חיות). מילות המפתח 'linen table runner' ב-AliExpress תופסות בעיקר פוליאסטר מודפס. הכרטיס מ-Zendrop (2902397) נשאר הטוב ביותר.

## dining-room / centerpiece-vase — אגרטל מרכזי (קרמיקה מט, גובה 20–28, קוטר 9–16, לא פחם)

חיפושים: `wholesale-matte-ceramic-vase-nordic-white.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1PC -Ceramic vase, round matte vase, minimalist Nordic Bohemian vase, home decoration | 6.07 | `3256807071050757` | [פתח](https://www.aliexpress.us/item/3256807071050757.html) | - | 12 sold | 7 | קרמיקה מט מינימליסטית; גובה לא בכותרת (דרוש 20–28) |
| 2 | Nordic Morandi Matte Ceramic Vase Minimalist Ins Flower Vase for Dried Cotton Eucalyptus Home Table Decor Ornament | 14.10 | `3256809956724885` | [פתח](https://www.aliexpress.us/item/3256809956724885.html) | - | 5 sold | 7 | מט בגווני מורנדי (עמומים, בפלטה); גובה לא בכותרת |
| 3 | Nordic Matte Ceramic Vase for Pampas Grass Dried Flower Home Decor Zen Living Room Office Desktop Table Bathroom Decoration Gift | 22.23 | `3256804234725093` | [פתח](https://www.aliexpress.us/item/3256804234725093.html) | Free shipping | 19 sold | 7 | קרמיקה מט נורדית; משלוח חינם |
| 4 | Modern Minimalist White Ceramic Matte Flower Vase Decorative Vase for Dried Flower Centerpiece Art Crafts Home Table Decoration | 5.11 | `2255800578472233` | [פתח](https://www.aliexpress.us/item/2255800578472233.html) | - | 19 sold | 7 | לבן מט, 'centerpiece' בכותרת; מחיר נמוך |
| 5 | Matte Ceramic Round Vase, 5.9", Natural Beige White | 17.80 | `3256812546177570` | [פתח](https://www.aliexpress.us/item/3256812546177570.html) | Delivery: Oct 16 - 21 | 3 sold | 6 | מט בז'-לבן; 5.9 אינץ' (15 ס"מ) כנראה נמוך מ-20, לבדוק אם זה הקוטר |
| 6 | CAPIRON Ceramic Coral Vase Nordic Art Beige Matte Container for Flower Pampas Grass Living Room Tabletop Centerpieces Decoration | 4.90 | `3256805710401837` | [פתח](https://www.aliexpress.us/item/3256805710401837.html) | - | 122 sold | 6 | בז' מט, נמכר היטב; צורת 'coral' עלולה להיות פיסולית מדי |
| 7 | CAPIRON Ceramic Matte Vase Set of 2 for Pampas Grass Dried Flower Modern Nordic Accessories Home Decoration Tabletop Interior | 12.96 | `3256806773816086` | [פתח](https://www.aliexpress.us/item/3256806773816086.html) | - | 47 sold | 6 | סט של 2 מט; מתאים גם ל-open-shelf-ceramics אם המידות מתאימות |
| 8 | Matte White Ceramic Vase Decoration Living Room Flower Arrangement, Light Luxury Water Nourishing Retro Creative Floral Ware | 16.25 | `3256810457185236` | [פתח](https://www.aliexpress.us/item/3256810457185236.html) | - | 7 sold | 6 | לבן מט; 'light luxury' מרמז על פרט מבריק, לבדוק |
| 9 | Ceramic Vase Decoration Home Decorative Vases For Flowers 25.8CM Vintage Handmade Ceramics & Pottery For Living Room | 26.33 | `3256807056730844` | [פתח](https://www.aliexpress.us/item/3256807056730844.html) | - | 13 sold | 6 | 25.8 ס"מ בתוך 20–28; מראה כד-יד; נמצא בחיפוש אגרטל רצפה |

**הערה:** תוצאה טובה בדף אחד (לא נדרש שני). לבדוק בדף: גובה 20–28, קוטר 9–16, פה צר, זיגוג מט, לא אותו מוצר כמו ברירת המחדל של הסלון.

## dining-room / candle-holders — פמוטים (זוג, פחם חובה: קרמיקה/מתכת שחורה מט, לנר עמוד)

חיפושים: `wholesale-black-ceramic-pillar-candle-holder.html`; `wholesale-matte-black-metal-pillar-candle-holder.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CuteLife Nordic Black Ceramic Decorative Candlestick Tealight Candelabra Big Candle Holder Ornaments Home Table Base For Candle | 14.45 | `3256811647185429` | [פתח](https://www.aliexpress.us/item/3256811647185429.html) | - | 1 sold | 7 | קרמיקה שחורה (פחם חובה), 'big candle' = נר עמוד; לבדוק שאין כוס לטי-לייט בלבד |
| 2 | Decorative Table Centerpiece Candle Holder, Set of 2 Matte Black Iron Candle Stand for Pillar Scented Flameless Ball Candles | 2.43 | `3256811847480845` | [פתח](https://www.aliexpress.us/item/3256811847480845.html) | - | 3 sold | 7 | זוג, ברזל שחור מט, לנר עמוד: בדיוק המבנה של העמדה; לבדוק קוטר המשטח (9–14) |
| 3 | Modern simple black geometric ceramic candlestick ornament living room romantic candlelight dinner creative dining table soft de | 13.70 | `3256812660419517` | [פתח](https://www.aliexpress.us/item/3256812660419517.html) | - | - | 6 | קרמיקה שחורה גאומטרית; לבדוק שזה לנר עמוד ולא לטייפר |
| 4 | Round Ceramic Pillar Candle Holder (Stoneware) - Table Centerpiece For Wedding Decor Christmas Dinner Party Supplies | 1.09 | `3256810068062684` | [פתח](https://www.aliexpress.us/item/3256810068062684.html) | - | 7 sold | 6 | אבנית לנר עמוד; הגוון לא בכותרת (דרוש פחם) |
| 5 | Nordic Black and White Ceramic Candle Candlestick ornaments Shooting Props Romantic Candlelight Dinner Decorations | 12.66 | `3256805576228227` | [פתח](https://www.aliexpress.us/item/3256805576228227.html) | - | 2 sold | 5 | קרמיקה בשחור/לבן; סוג הנר לא ברור |
| 6 | Luxury Cylinder Ceramic Candle Holders Wholesale Pillar Candle Container Large Small Concrete Candle Stand Home Art Crafts Decor | 18.23 | `3256807835816207` | [פתח](https://www.aliexpress.us/item/3256807835816207.html) | Free shipping | 8 sold | 5 | גליל קרמיקה/בטון לנר עמוד; 'container' עלול לעטוף את הנר (אסור מעל 3 ס"מ) |
| 7 | 2pcs 2 Pack Pillar Candle Holder Stable Base Matte Black Taper Candle Holder Vintage Iron Base With Handle Metal Candle Stand | 4.97 | `3256812713786818` | [פתח](https://www.aliexpress.us/item/3256812713786818.html) | - | 1 sold | 5 | זוג שחור מט לנר עמוד; עם ידית (סגנון chamberstick) וגם לטייפר |
| 8 | 3Pcs Matte Black Hourglass Candle Holders Funnel-Shaped Pillar Candlestick Set for Romantic Dinner Wedding Home Table Decor | 14.64 | `3256811824621859` | [פתח](https://www.aliexpress.us/item/3256811824621859.html) | - | - | 5 | שחור מט על רגל (pedestal) לנר עמוד; סט של 3 וגבהים לא ידועים (עד 12) |

**הערה:** תוצאה סבירה: יש קרמיקה שחורה וברזל שחור מט לנר עמוד. פסלתי מהכותרת: מחזיקי 'pin' (קוץ מתכת חשוף), קנדלברות, זהב, פלסטיק.

## dining-room / floor-vase — אגרטל רצפה (גובה 50–65, קוטר 25–32)

חיפושים: `wholesale-large-floor-vase-ceramic-60cm.html`; `wholesale-tall-ceramic-floor-vase-white.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Tall Ceramic Vase for Dried Flowers Minimalist Design Elegant White Floor Vase for Pampas Grass Living Room Decor | 37.75 | `3256813144317414` | [פתח](https://www.aliexpress.us/item/3256813144317414.html) | - | - | 7 | אגרטל רצפה לבן מינימליסטי; גובה לא בכותרת (דרוש 50–65) |
| 2 | CAPIRON Zen Ceramic Vase for Home Decoration Floor Flowerpot Nordic Interior Centerpiece Living Room Decoration Accessories | 17.94 | `3256808800994217` | [פתח](https://www.aliexpress.us/item/3256808800994217.html) | Free shipping | 105 sold | 7 | זן/נורדי, נמכר היטב, משלוח חינם; גובה לבדיקה |
| 3 | Floor Vase Classic White Ceramic Vase Arts and Crafts Decor Flower Vase Creative Gift Household Decoration ZM807 | 25.34 | `3256801653747791` | [פתח](https://www.aliexpress.us/item/3256801653747791.html) | - | 13 sold | 6 | אגרטל רצפה לבן; 'classic' עלול להיות צורה מעוטרת |
| 4 | Plain Embryo Art Vase Home Decoration Home Decoration Ceramic Flower | 18.73 | `3256809351896285` | [פתח](https://www.aliexpress.us/item/3256809351896285.html) | Free shipping | 3 sold | 6 | גוף לא מזוגג (מט); מידות לא בכותרת |
| 5 | Jingdezhen Floor-standing Ceramic Large Flower Vase for Floral Arrangement Simple European-style Living Room Modern Home Decor | 47.49 | `3256809906925054` | [פתח](https://www.aliexpress.us/item/3256809906925054.html) | - | 8 sold | 5 | גדול לרצפה; 'European-style' מג'ינגדז'ן כנראה מזוגג מבריק |
| 6 | Large Natural Woven Rattan Floor Vase Bohemian Style Eco-Friendly Living Room Centerpiece Standing Planter for Home Decor | 22.08 | `3256813133531477` | [פתח](https://www.aliexpress.us/item/3256813133531477.html) | - | 1 sold | 4 | ראטן: מותר רק כפריט הסיב הטבעי היחיד בחדר, לא כברירת מחדל; בוהו |

**הערה:** הדף הראשון היה רעש (ווים, מחזיקי כוסות); הדף השני הביא 5 אגרטלי רצפה לבנים. הגובה לא מופיע באף כותרת.

## dining-room / kitchen-sconce — מנורת קיר במטבח (אהיל 14–20, בליטה עד 20, מחווטת, CE)

חיפושים: `wholesale-ceramic-wall-lamp-kitchen-nordic.html`; `wholesale-wall-sconce-linen-shade.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Conical Linen Shade Black Metal Bracket Contemporary Neutral Fabric Wall Sconce Beige Linen Wall Lamp for Hotel Bedroom Decor | 37.45 | `3256812137993644` | [פתח](https://www.aliexpress.us/item/3256812137993644.html) | - | 5 sold | 8 | קונוס פשתן בז' על זרוע שחורה: וריאציה 2 של ה-Bible כלשונה; לבדוק בליטה עד 20, CE, 220–240V |
| 2 | Japanese Wabi Sabi Wall Lamp Linen Lampshade LED Wall Sconce Homestay Dining Room Bedroom Corridor Adorn Illumination Wall Light | 21.95 | `3256812232495919` | [פתח](https://www.aliexpress.us/item/3256812232495919.html) | Free shipping | - | 6 | אהיל פשתן; LED (לבדוק אם נורה מתחלפת) והזרוע לא ידועה |
| 3 | Creative Iron LED Wall Lamp Nordic Medieval Cream Style Interior Decoration Light Ceramic Lampshade Bedside Lamp Study Corridor | 3.93 | `3256812314069085` | [פתח](https://www.aliexpress.us/item/3256812314069085.html) | - | 1 sold | 5 | אהיל קרמיקה בקרם (וריאציה 1); 'medieval' מרמז על עיטור, והמחיר חשוד |
| 4 | IWHD White Ceramic LED Wall Lights Staircase Kitchen Study Modern Style Copper Up Down Rotate Pull Chain Switch Bedside Lamp | 45.24 | `3256812975702342` | [פתח](https://www.aliexpress.us/item/3256812975702342.html) | - | 4 sold | 4 | קרמיקה לבנה, אבל נחושת ושרשרת משיכה (מתכת רק בשחור/לבן חם) |
| 5 | Japanese Ceramic Wall Light With Switch Nordic Brass Loft LED Sconce Home Decor For Bedroom Wall Lamp Fixture Indoor Luminaire | 38.61 | `3256804529142990` | [פתח](https://www.aliexpress.us/item/3256804529142990.html) | - | 18 sold | 4 | אהיל קרמיקה; פליז אסור במטבח |
| 6 | White Porcelain Led Wall Lamp Nordic Simplified Brass Bedroom Bedside Aisle Wandlamp Retro Translucent Ceramics Bathroom Light | 54.27 | `2251832768063608` | [פתח](https://www.aliexpress.us/item/2251832768063608.html) | - | 25 sold | 4 | פורצלן שקוף-למחצה יפה; פליז אסור; לשקול למקלחת (IP44?) |
| 7 | Vintage Mid-Wall Lamp Retro Wooden Wall Sconce with Green Linen Shade Home Decor Bedroom Living Room E27 Base | 103.12 | `3256811825444085` | [פתח](https://www.aliexpress.us/item/3256811825444085.html) | Free shipping | 10 sold | 4 | עץ + אהיל פשתן, E27; ירוק רק אם בטווח המרווה; יקר |

**הערה:** פריט אחד מצוין (3256812137993644: קונוס פשתן על זרוע שחורה). רוב השאר IWHD עם נחושת/פליז ושרשרת משיכה, שפסולים במטבח. לבדוק: בליטה עד 20, CE, 220–240V, חיווט לנקודה בקיר.

## dining-room / sink-set — סט ליד הכיור (מתקן 17–21, מברשת עם ידית עץ, מגש 15–22; קרמיקה/אבן/עץ, בלי פלסטיק)

חיפושים: `wholesale-ceramic-soap-dispenser-dish-brush-tray-set.html`; `wholesale-dish-soap-dispenser-ceramic-tray.html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Luxury Irregular Soap Dispenser with Press handle Ceramic Dispenser Dispenser with Stainless steel Tray Bathroom Accessory | 5.61 | `3256812066933865` | [פתח](https://www.aliexpress.us/item/3256812066933865.html) | Delivery: Oct 16 - 22 | 4 sold | 6 | מתקן קרמיקה עם מגש; מגש פלדה (לבדוק מט); בלי מברשת. הופיע גם ב-$0.99 בחיפוש השני |
| 2 | Modern kitchen accessories Soap Dispenser Set Liquid hand soap dispenser pump bottle brushes Holds and Stores Sponges Scrubbers | 12.33 | `1005005197587317` | [פתח](https://www.aliexpress.com/ssr/300000512/BundleDeals2?productIds=1005005197587317:12000032099599728) | Delivery: Oct 16 - 22 | 600+ sold | 5 | סט מטבח עם מתקן ומברשת, נמכר היטב; החומר לא בכותרת (חשד לפלסטיק). הקישור הוא דף חבילה, המזהה מ-productIds; הופיע גם ב-$4.69 |
| 3 | Ceramic Liquid Soap Dispenser Pump Bottle Refillable Lotion Container Bathroom Accessories Set for Home Sink | 7.89 | `3256813142060535` | [פתח](https://www.aliexpress.us/item/3256813142060535.html) | - | - | 5 | מתקן קרמיקה לכיור; בלי מגש ומברשת |
| 4 | 3Pcs Ceramic Bathroom Set Portable Toothbrush Holder Shampoo Bottle Dispenser Bamboo Tray Kit Bathroom Accessories | 27.12 | `3256812435658390` | [פתח](https://www.aliexpress.us/item/3256812435658390.html) | Free shipping | 2 sold | 5 | קרמיקה + מגש במבוק (עץ מותר); סט אמבטיה, הכוס יכולה לשמש למברשת |
| 5 | Nordic Ceramic Bathroom Lotion Bottle Press Hand Sanitizer Bottle Mouthwash Cup Toothbrush Holder Black Liquid Soap Dispenser | 11.17 | `3256805826713154` | [פתח](https://www.aliexpress.us/item/3256805826713154.html) | Free shipping | 53 sold | 5 | קרמיקה בשחור (חוזר על הברז השחור); סט אמבטיה |
| 6 | Ceramic Hand Sanitizer Dispenser Shampoo Shower Gel Bottle Santa Press Soap Dispenser Household Ceramic Storage Tray Shelf | 19.91 | `3256806732983608` | [פתח](https://www.aliexpress.us/item/3256806732983608.html) | Free shipping | - | 4 | קרמיקה עם מגש; הכותרת לא ברורה ('Santa') |
| 7 | Retro Ceramic Bathroom Accessory Set Soap Dish with Drainage Lotion Dispenser Toothbrush Holder Household Vanity Organizer | 27.01 | `3256811980722776` | [פתח](https://www.aliexpress.us/item/3256811980722776.html) | Free shipping | - | 4 | סט קרמיקה רטרו; סגנון וגוון לא ברורים |

**הערה:** אין סט מטבח מלא (מתקן + מברשת עץ + מגש) במראה הנכון. יש מתקני קרמיקה עם מגש; המברשת עם ידית עץ תצטרך חיפוש נפרד ('wooden dish brush natural bristle').

## dining-room / utensil-crock — כלי לכלי עץ (אבנית מט, 16–20 × 12–14)

חיפושים: `wholesale-stoneware-utensil-holder-crock.html`; `wholesale-ceramic-utensil-holder-kitchen-white (ריק/חסום).html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | French Style Ceramic Kitchen Utensil Holder Chopstick Storage Bucket | 25.04 | `3256811648868911` | [פתח](https://www.aliexpress.us/item/3256811648868911.html) | - | 1 sold | 6 | כלי קרמיקה לכלי מטבח; גוון ומידות לא בכותרת (דרוש 16–20 × 12–14) |
| 2 | Rough Pottery Draining Chopstick Holder with Drip Tray Vintage Cutlery Drain Rack Wide Opening Cylindrical Chopstick Storage Box | 19.10 | `3256812210330392` | [פתח](https://www.aliexpress.us/item/3256812210330392.html) | - | 12 sold | 5 | חרס גס במרקם יד (טוב); חורי ניקוז ומגש טפטוף לא נדרשים |
| 3 | Rough Pottery Draining Chopstick Holder Vintage with Drip Tray Cutlery Drain Rack Rustic Style Well-ventilated | 19.35 | `3256812213987373` | [פתח](https://www.aliexpress.us/item/3256812213987373.html) | - | 1 sold | 5 | אותה משפחה אצל מוכר שני |
| 4 | Ceramic Chopstick Tube Tableware Storage Bottle Chopstick Cage Drain Rack Chopsticks Basket Storage Organizer Storage Holder | 25.18 | `3256808083004039` | [פתח](https://www.aliexpress.us/item/3256808083004039.html) | - | 7 sold | 4 | צינור קרמיקה; 'drain rack' מרמז על חורים |

**הערה:** הדף הראשון הביא חרס גס עם ניקוז ו-'Le Creuset' (העתקי מותג, נפסלו). הדף השני חזר ריק (חסום?). חסר כלי אבנית חלק בלבן חם/שיבולת שועל.

## dining-room / cutting-boards — קרשי חיתוך (זוג, אלון/אפר, 42–48 ו-34–40 גובה, רוחב 20–26)

חיפושים: `wholesale-oak-cutting-board-wood-handle.html`; `wholesale-white-oak-cutting-board (ריק/חסום).html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Wooden Cutting Board with Handle Kitchen Household Serving Board Wooden Cheese Board Charcuterie Board for Bread Fruit Plates | 8.90 | `3256808220072680` | [פתח](https://www.aliexpress.us/item/3256808220072680.html) | Delivery: Oct 16 - 22 | 352 sold | 5 | קרש עם ידית (וריאציה מותרת), נמכר היטב; סוג העץ לא בכותרת (דרוש אלון/אפר) |
| 2 | High-Quality Wooden Cutting Board 16x10x1 in, Thick Wooden Chopping Board with Deep Juice Groove & Built-in Handle, Easy to Clean Deli Platter and Butcher Block for Kitchen Meat, Vegetables, Cheese | 12.77 | `3256813079857505` | [פתח](https://www.aliexpress.us/item/3256813079857505.html) | Free shipping | - | 5 | 40.6×25.4×2.5 מתאים לקרש הקטן (34–40 × 20–26); סוג העץ לא בכותרת |
| 3 | Wood Kitchen Chopping Board for Cutting Meat Vegetables Fruits with Handle Serving Tray | 10.62 | `3256813138951623` | [פתח](https://www.aliexpress.us/item/3256813138951623.html) | - | - | 5 | קרש עם ידית; סוג עץ ומידות לא בכותרת |
| 4 | Wood Kitchen Chopping Board for Cutting Meat Vegetables Fruits with Handle Serving Tray | 10.52 | `3256813127355177` | [פתח](https://www.aliexpress.us/item/3256813127355177.html) | - | - | 5 | אותו דגם אצל מוכר שני |
| 5 | Round Wooden Chopping Board Cutting Kitchen Supplies Boards Accessories Large Kitchens Wood Accessory Items Cutting Board Large | 12.45 | `3256810535246999` | [פתח](https://www.aliexpress.us/item/3256810535246999.html) | - | 13 sold | 5 | עגול (וריאציה מותרת); סוג העץ לא בכותרת |

**הערה:** אין 'oak' באף כותרת; הרוב אקציה/טיק/אגוז (כהים, מחוץ לטווח האלון). שורשרו רק קרשים שסוג העץ שלהם לא ידוע. הדף השני ('white oak') חזר ריק (חסום?). כנראה מקור אירופי (S7, ליטא) או ישראלי עדיף.

## dining-room / herb-pots — עציצי תבלינים (2, קרמיקה מזוגגת מט עם צלחת, 10–12)

חיפושים: `wholesale-ceramic-herb-pot-saucer-white-matte.html`; `wholesale-white-ceramic-planter-with-saucer-small (ריק/חסום).html`

| # | כותרת | מחיר $ | מזהה | קישור | משלוח | נמכרו | התאמה | סיבה |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Ceramic Planter Pot with Bamboo Tray Succulent Plant Round Desktop Pot Small Bonsai Pots Green Planters Creative Flowerpots | 1.09 | `3256807989828860` | [פתח](https://www.aliexpress.us/item/3256807989828860.html) | - | 27 sold | 5 | עציץ קרמיקה עגול עם מגש במבוק; קוטר/גובה (10–12) וגוון לא בכותרת |
| 2 | Japanese Style Ceramic Flower Pot with Bamboo Tray, Elegant Planter for Succulent, Bonsai, Cactus Plants Minimalist Garden Decor | 1.09 | `3256809655217665` | [פתח](https://www.aliexpress.us/item/3256809655217665.html) | - | 11 sold | 5 | מינימליסטי עם מגש במבוק; מידות לא בכותרת |
| 3 | Oval Shaped Ceramic White Succulent Planter Pot with Bamboo Tray, Ceramic Cactus Plant Holder, Home Office Table Desk Decoration | 13.13 | `2251832608581976` | [פתח](https://www.aliexpress.us/item/2251832608581976.html) | - | 38 sold | 4 | לבן עם מגש, אבל אליפטי (העמדה מצפה לשני עציצים עגולים קטנים) |

**הערה:** עציצים קטנים עם מגש במבוק במחיר נמוך, בלי מידות בכותרת. הדף השני חזר ריק (חסום?). צלחת קרמיקה (לפי ה-Bible) לא נמצאה; מגש במבוק הוא חלופה לבדיקה עם המעצב.

## דפים שחזרו ריקים (לא נוסו שוב, לפי ד.6)
- `wholesale-ceramic-utensil-holder-kitchen-white.html`
- `wholesale-white-oak-cutting-board.html`
- `wholesale-white-ceramic-planter-with-saucer-small.html`

שלושתם היו האחרונים ברצף של 13 דפים, ולכן כנראה האטה/חסימה זמנית ולא דף ריק באמת. אפשר לנסות אותם בדפדפן של המשתמש.

## נפסלו מהכותרת (לא נרשמו במרשם)
- cushions: קטיפה/טדי (3256808872951409), בוקלה עם חום כהה ב-$43 (3256811983903811), כל ההדפסים בחיפוש המרווה.
- candle-holders (סלון): טייפר בשני חורים (3256806161705184, 3256812719786521, 3256811493801082), שיש ירוק (3256812202863942), גל S כפול (3256811851541747), זכוכית.
- accent-sconces: עם עץ אגוז ושרשרת (3256811467536843, 3256810542148961, 3256811681250021, 3256809473987911, 3256812034577838), אהיל זכוכית (3256807774012931), Duo למראה (3256808935211834, 3256809745159336).
- pouf: ריפוד PU/קש (2251832730700938), $284 (3256812861136947), צמר כבש (3256810170089206), בין-בגים OTAUTAU.
- rug: ראנר צר פסים (3256812113033764; אולי ל-kitchen-runner), שטיחים מודפסים/חלודה.
- floor-lamp: קשת (3256812817613686), כדורית (3256805545682940), פטרייה (3256806795781184), פליז $932 (3256812037311878).
- candle-holders (אוכל): קוץ מתכת חשוף (3256813066192352, 3256812511991334), קנדלברה (3256811834733686, 3256806660262090), זהב/פלסטיק.
- kitchen-sconce: זרוע ארוכה (3256809337072019), צבעוני (3256810287267944), RGB, תקרה/תלויות.
- utensil-crock: 'Le Creuset' (3256813085707431, 3256813075028830, 3256813084381711: העתקי מותג), מעמד כפות (3256812275526436).
- cutting-boards: אקציה (3256809533048588, 3256813063343228), טיק (3256807158559197, 3256808566849794, 3256812191165891), אגוז (3256808015177403).
- herb-pots: דוגמת שיש (3256803275887884), צלחת בלבד (3256805824203844).
