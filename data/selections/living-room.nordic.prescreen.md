# סינון ראשוני של לידים: סלון נורדי

> master-designer, 2026-09-28. **זה לא הדירוג הסופי ולא בחירת וריאציות.** הסינון נעשה רק לפי מה שכתוב בלידים (כותרת, URL, snippet_facts, fit_notes, concerns), מול `docs/design-bible/nordic.md` (גרסה 1.0), `docs/brand-brief.md` וחוקי העיצוב. אף ליד לא אומת: מחיר, מידות, צבע אמיתי, תמונות ומשלוח לישראל עדיין לא ידועים.
>
> **איך קוראים את ההחלטות:** `verify-first (n)` = בודקים ראשון, לפי הסדר n. `verify-if-needed (n)` = בודקים רק אם ה-verify-first לא נתנו 3 וריאציות טובות, לפי הסדר n. `drop` = הכותרת או התקציר כבר סותרים את ה-Design Bible, או שזה לא סוג המוצר של העמדה.
>
> **בדיקות חובה בכל דף מוצר, בכל העמדות:** משלוח לישראל וזמן משלוח; מספר הזמנות וביקורות (brand-brief: מוצר סדרתי עם הרבה הזמנות); תמונות אמיתיות של לקוחות (לאימות גוון מול טווחי HSL וברק מט); שאין "made to order" או הדפס לפי הזמנה; ושהמחיר מתאים ל"פרימיום נגיש" בלי שהמוצר ייראה זול בתקריב.

## 1. סיכום לפי עמדה

| עמדה | verify-first | verify-if-needed | drop | סה"כ | לא-drop |
| --- | --- | --- | --- | --- | --- |
| vase | 3 | 5 | 0 | 8 | 8 |
| basket | 3 | 3 | 4 | 10 | 6 |
| candle-holders | 1 | 5 | 2 | 8 | 6 |
| magazine-holder | 1 | 3 | 4 | 8 | **4** |
| framed-art | 3 | 7 | 2 | 12 | 10 |
| wall-decor | 3 | 7 | 2 | 12 | 10 |
| curtains | 3 | 3 | 1 | 7 | 6 |
| floor-lamp | 2 | 7 | 0 | 9 | 9 |
| rug | 2 | 5 | 0 | 7 | 7 |
| sofa-cover | 4 | 5 | 1 | 10 | 9 |
| cushions | 4 | 4 | 2 | 10 | 8 |
| **סה"כ** | **29** | **54** | **18** | **101** | **83** |

## 2. החלטות לפי עמדה

### vase — אגרטל
| lead_id | החלטה | נימוק |
| --- | --- | --- |
| vase-aliexpress-narrow-mouth-luxury | verify-first (1) | צללית בקבוק מותרת, קרמיקה, וגרסאות בז' ואפור בשני גדלים באותו ליסטינג (אם יאומת, יש כאן אולי שתי וריאציות מספק אחד). |
| vase-aliexpress-beige-travertine | verify-first (2) | טרוורטין בהיר מותר במפורש ומוסיף חומר שאינו קרמיקה; לוודא גימור מושחז ולא מלוטש. נספר במכסת "עד 2 פריטי אבן" בחדר. |
| vase-aliexpress-plain-minimalist | verify-first (3) | קרמיקה ו-"Plain" מתאימים לצללית פשוטה; הגוון לא ידוע. |
| vase-aliexpress-coral-beige-matte | verify-if-needed (1) | החומר והגוון מושלמים (קרמיקה מט בז'), אבל "Coral" מרמז על צורה מסועפת או פיגורטיבית, שנוגדת את כלל הצלליות. |
| vase-aliexpress-minimalist-large-table | verify-if-needed (2) | קרמיקה מינימליסטית, אבל "Large/Unique/Trendy" בלי צבע ומידה, וסיכון לחריגה מגובה 35. |
| vase-aliexpress-europe-minimalist-flower | verify-if-needed (3) | קרמיקה מינימליסטית בלי שום נתון צבע או צורה. |
| vase-aliexpress-black-white-minimalist | verify-if-needed (4) | פחם מותר באגרטל, אבל "Black and White" עלול להיות ניגוד גרפי או שחור טהור; החומר לא ידוע. |
| vase-aliexpress-wedding-nordic-living-room | verify-if-needed (5) | אין חומר, צבע או מידה; מיקוד ב"חתונה" מרמז על קישוטיות. אחרון בתור. |

### basket — סל
| lead_id | החלטה | נימוק |
| --- | --- | --- |
| basket-aliexpress-seagrass-nordic-style | verify-first (1) | קש ים טבעי עם ידיות קלועות מאותו חומר: בדיוק מה שהעמדה דורשת. |
| basket-aliexpress-rattan-large-handle | verify-first (2) | ראטן, גדול, עם ידית; לוודא שזה ראטן טבעי ולא PE, ושהצללית גלילית או בטן רחבה. |
| basket-aliexpress-seagrass-straw-rattan-woven | verify-first (3) | כל שלושת החומרים מותרים; הכותרת חתוכה ואין צורה או מידה. |
| basket-aliexpress-seagrass-planter-hamper-sml | verify-if-needed (1) | קש ים בשלוש מידות (L עשויה להתאים), אבל $4.16, "מתקפל" ועציץ תלוי: סיכון גבוה למראה זול ורך מדי. |
| basket-aliexpress-rattan-flower-belly-basket | verify-if-needed (2) | צללית בטן רחבה מתאימה, אבל 2 הזמנות בלבד (נוגד את ה-brand-brief), משווק כסל גינה, והגרסה בכותרת שחורה. |
| basket-aliexpress-water-hyacinth-round | verify-if-needed (3) | עגול וטבעי, אבל יקינטון מים לא ברשימת החומרים הסגורה של העמדה. שימוש בו מחייב חריגה כתובה (ראו התלבטויות). |
| basket-aliexpress-water-hyacinth-metal-frame | drop | ארגז מלבני עם שלד מתכת: לא צללית גלילית או בטן רחבה, והחומר לא ברשימה. |
| basket-aliexpress-water-hyacinth-set2 | drop | סט של 2 ארגזים מלבניים: צללית וכמות לא מתאימות לעמדה. |
| basket-aliexpress-cotton-rope-basket-55x35 | drop | המידה 55 בכותרת חורגת גם מגובה מקסימלי 50 וגם מקוטר מקסימלי 45. (חבל כותנה כחומר רצוי מאוד; ראו המלצות חיפוש.) |
| basket-aliexpress-luanqi-rattan-seagrass-woven | drop | "Picnic Basket / Organizer Box": סוג מוצר וצללית של סל פיקניק ולא סל רצפה. |

### candle-holders — פמוטים
| lead_id | החלטה | נימוק |
| --- | --- | --- |
| candle-holders-aliexpress-retro-plain-ceramic | verify-first (1) | קרמיקה פשוטה; לבדוק ש-"Retro" לא אומר צבע רווי או זיגוג מבריק, ושיש שני גבהים. |
| candle-holders-aliexpress-ceramic-candlestick-nordic | verify-if-needed (1) | קרמיקה נורדית, אבל הדף החזיר "not found" פעם אחת; קודם לבדוק שהוא חי. |
| candle-holders-aliexpress-floriddle-single | verify-if-needed (2) | פריט בודד בלי חומר; שווה רק אם באותה סדרה יש גובה שני (הפרש של 5 ס"מ ומעלה). |
| candle-holders-aliexpress-iron-art-table | verify-if-needed (3) | מתכת היא אולי שחור מט מותר, אבל "Iron Art" מרמז על פיסוליות; גימור וכמות לא ידועים. |
| candle-holders-aliexpress-euro-architectural-ceramic | verify-if-needed (4) | קרמיקה, אבל "Architectural" מרמז על עמוד קלאסי או עיטור. |
| candle-holders-aliexpress-geometric-small-ceramic | verify-if-needed (5) | קרמיקה, אבל גאומטרי ו"Crafts" רחוק מצלליות רכות; סיכון לגרסאות צבועות. |
| candle-holders-aliexpress-iron-hollowed-trio | drop | סט של 3 (העמדה: 2 בדיוק), מחורר ומקושט ("handicraft"): נוגד את הכמות ואת איסור הקישוטים. |
| candle-holders-aliexpress-3d-geometric-metal | drop | צללית תלת-ממדית גאומטרית של אירועים ("Wedding") נוגדת את הצלליות האורגניות הרכות; $6.81 לא מתאים לפרימיום. |

### magazine-holder — מחזיק עיתונים
| lead_id | החלטה | נימוק |
| --- | --- | --- |
| magazine-holder-aliexpress-plated-wire-faux-leather-standing | verify-first (1) | הליד היחיד שהוא עומד-רצפה, מתכת ועור. שני תנאים: ש-"plated" הוא שחור מט ולא זהב או כרום, ושהעור נקרא כרצועה ולא כגוף (ראו התלבטויות). |
| magazine-holder-aliexpress-plated-wire-faux-leather-premium | verify-if-needed (1) | כנראה אותו דגם; לבדוק יחד עם הקודם, ואם הוא זהה להשאיר אחד. |
| magazine-holder-aliexpress-nordic-iron-trapezoidal-floor-rack | verify-if-needed (2) | ברזל, עומד-רצפה, מחיר ברמה המתאימה, אבל "רב-שכבתי / מדף ספרים" מרמז שהוא גבוה ורחב מהמעטפת (35–55 × 30–45). |
| magazine-holder-aliexpress-vintage-floor-brown-minimalist | verify-if-needed (3) | עומד-רצפה ומינימלי, אבל הדף אולי הוסר, ובחום בלי אלמנט פחם חובה. |
| magazine-holder-aliexpress-wrought-iron-menu-stand | drop | מעמד תפריט או תווים: סוג מוצר אחר (כן עומד), לא מחזיק עיתונים רצפתי. |
| magazine-holder-aliexpress-office-desk-iron | drop | מעמד שולחני למשרד ("Office Desk", "Display Shelf"): לא עומד-רצפה. |
| magazine-holder-aliexpress-table-round-leather-desktop | drop | "Table / Desktop" מפורש: שולחני ולא עומד-רצפה. |
| magazine-holder-aliexpress-pu-leather-elegant-organizer | drop | גוף מעור PU, בלי מתכת שחורה: עור מותר רק בידיות ורצועות, והחומר לא ברשימת העמדה. |

### framed-art — תמונה ממוסגרת
| lead_id | החלטה | נימוק |
| --- | --- | --- |
| framed-art-aliexpress-bw-abstract-with-frame-set3 | verify-first (1) | "with Frame" מפורש, מופשט, שחור-לבן (אלמנט פחם), שלישייה. לבדוק מסגרת שחור מט או אלון, שחור לא טהור, ומידה 50×70. |
| framed-art-spocket-scandi-artwork-set3 | verify-first (2) | מגיע ממוסגר עם אופציה של מסגרת שחורה (נשא פחם), שלישייה. התוכן לא ידוע; לוודא שזה לא הדפס לפי הזמנה. |
| framed-art-aliexpress-line-geometric-set | verify-first (3) | קו מופשט בשחור-לבן, וזמין כשלישייה. ההכרעה תלויה ב-"Posters": אם אין אופציית מסגרת, drop. |
| framed-art-aliexpress-foggy-forest-3piece | verify-if-needed (1) | תוכן נוף ערפילי מותר ושלישייה, אבל מסגרת לא ידועה ואין אלמנט פחם מובטח (חובה). |
| framed-art-aliexpress-line-drawing-poster | verify-if-needed (2) | רישום קו מותר, אבל פוסטר בלי מסגרת ידועה; לוודא שהקו לא מצייר פנים או גוף (אסור). |
| framed-art-aliexpress-flower-bw-minimalism | verify-if-needed (3) | שחור-לבן, אבל פוסטר, ופרח מצויר ולא בהכרח "בוטני בקו". |
| framed-art-cj-abstract-geometric | verify-if-needed (4) | ספק CJ ותוכן מופשט, אבל קנבס בלי מסגרת ידועה ובלי צבע. |
| framed-art-aliexpress-foggy-forest-poster | verify-if-needed (5) | תוכן מותר, אבל פוסטר בלי מסגרת ובלי מידה. |
| framed-art-aliexpress-misty-forest-single | verify-if-needed (6) | תוכן מותר, אבל $1.49 מרמז על פוסטר קטן בלי מסגרת, רחוק מ-100×150. |
| framed-art-cj-canvas-painting-living-room | verify-if-needed (7) | כותרת גנרית לחלוטין; אחרון בתור. |
| framed-art-spocket-set3-neutral | drop | "gold" מופיע במפורש בפלטת ההדפס; זהב אסור בסגנון. |
| framed-art-aliexpress-botanical-eucalyptus-set3 | drop | בוטני בצבעי מים ("Boho", ירוק) ולא בוטני בקו, כנראה פוסטר בלי מסגרת: נוגד את התוכן המותר. |

### wall-decor — קישוט קיר
| lead_id | החלטה | נימוק |
| --- | --- | --- |
| wall-decor-aliexpress-rattan-seagrass-round | verify-first (1) | ראטן וקש ים, עגול, פריט בודד: מתאים לפורמט קוטר 50–90. |
| wall-decor-aliexpress-seagrass-basket-set5 | verify-first (2) | קש ים, 5 צלחות (מספר אי-זוגי); לבדוק שההרכב נכנס ל-60–110 × 50–100. |
| wall-decor-aliexpress-rattan-plate-single-de | verify-first (3) | צלחת ראטן בודדת עגולה; לבדוק קוטר ומשלוח לישראל (חנות de). |
| wall-decor-aliexpress-seagrass-tray-de | verify-if-needed (1) | קש ים, אולי פריט בודד; מידה ומספר פריטים לא ידועים. |
| wall-decor-aliexpress-macrame-cotton-beige-tapestry | verify-if-needed (2) | מקרמה כותנה בז' מותרת, אבל "Ethnic / Tassel" נוטה לבוהו; לבדוק מידה ואורך גדילים. |
| wall-decor-aliexpress-seagrass-ornament-vi | verify-if-needed (3) | קש ים, כל השאר לא ידוע (חנות vi). |
| wall-decor-spocket-macrame-pendant | verify-if-needed (4) | מקרמה בגוונים טבעיים, בלי מידה. |
| wall-decor-aliexpress-seagrass-set7-de | verify-if-needed (5) | אי-זוגי, אבל 7 חורג מ"3 או 5". מחייב נימוק כתוב, ו-7 פריטים במעטפת 110 ס"מ יהיו קטנים מדי. |
| wall-decor-aliexpress-macrame-wood-stick-tapestry | verify-if-needed (6) | מקרמה עם מוט עץ, אבל "Large / Wedding Background" מרמז על חריגה מהמעטפת. |
| wall-decor-spocket-macrame-home-heart | verify-if-needed (7) | אין שום נתון; לוודא שאין צורת לב. אחרון בתור. |
| wall-decor-aliexpress-rattan-basket-set6 | drop | סט של 6: מספר זוגי, והרינדור חייב להראות את כל מה שנמכר, ולכן אי אפשר להציג 5 מתוך 6. |
| wall-decor-aliexpress-macrame-cotton-door-curtain | drop | וילון דלת או רקע לחתונה: סוג מוצר ופרופורציה שלא מתאימים לעמדה. |

### curtains — וילונות
| lead_id | החלטה | נימוק |
| --- | --- | --- |
| curtains-aliexpress-napearl-cotton-linen-tulle-beige-ready-made | verify-first (1) | כותנה-פשתן, בז' אחיד, חצי-שקוף, מותג סדרתי ומוכן: עונה על כל הדרישות; לוודא מידה 130–150 × 250–260. |
| curtains-aliexpress-linen-look-beige-sheer-tulle | verify-first (2) | בז', שקוף-למחצה, לסלון; לבדוק בתקריב שהמראה של הפשתן משכנע ולא מבריק. |
| curtains-aliexpress-japanese-gauze-cotton-linen-texture | verify-first (3) | גזה חצי-שקופה בטקסטורת כותנה-פשתן; לוודא ש-"Rainbow" הוא שם חוט ולא גוון צבעוני. |
| curtains-aliexpress-faux-linen-sheer-extra-long-custom | verify-if-needed (1) | שקוף, עם בחירת אורך שיכולה להתאים ל-255, אבל "Custom Made" (לוודא שזה לא בהזמנה אישית) וטקסטורת faux. |
| curtains-aliexpress-cotton-linen-semi-blackout-flax-voile | verify-if-needed (2) | החומר טוב, אבל "Semi-blackout" נוגד מעבר אור של 30–60%; רק אם יש אופציית voile נפרדת. |
| curtains-aliexpress-white-tulle-sheer-linen-cheap | verify-if-needed (3) | "Cheap" בכותרת וסיכון ללבן טהור; מתאים רק כגיבוי. |
| curtains-aliexpress-japanese-striped-beige-light-filtering | drop | "Striped design" מפורש: דוגמאות בווילון אסורות. |

### floor-lamp — מנורת רגל
> לכל המנורות: לבדוק 220–240V ותקע, וטמפרטורת צבע 2700K. ראו התלבטויות לגבי תקינה בישראל.

| lead_id | החלטה | נימוק |
| --- | --- | --- |
| floor-lamp-aliexpress-drum-fabric-led | verify-first (1) | אהיל תוף מבד ומנורת רגל נורדית פשוטה; הגוון, הגוף והגובה לא ידועים. |
| floor-lamp-aliexpress-cloth-shadowless | verify-first (2) | מנורת רגל מינימלית עם אהיל בד; לוודא שאין מצבי LED צבעוניים. |
| floor-lamp-aliexpress-pleated-fabric | verify-if-needed (1) | אהיל קפלים מבד, אבל "Bedside / Night Light" מרמז על מנורה קטנה. |
| floor-lamp-aliexpress-tripod-mushroom-vintage | verify-if-needed (2) | טריפוד מותר, אבל אהיל פטרייה ו-"Postmodern" עלולים לצאת מהצלליות ומחומרי האהיל. |
| floor-lamp-aliexpress-medieval-spanish-adjustable | verify-if-needed (3) | ייתכן ש-"Medieval" הוא תרגום שגוי של mid-century ושזה עמוד אנכי מתכוונן לגובה, כלומר לא קשת. אבל "Replica of … Designer" הוא העתק של עיצוב מוגן (התלבטות). |
| floor-lamp-aliexpress-cole-cestita-wood | verify-if-needed (4) | גוף עץ, אבל "Bedside" מרמז על מנורה קטנה, והשם הוא של עיצוב מוכר (העתק; התלבטות). |
| floor-lamp-aliexpress-wood-table-floor-hybrid | verify-if-needed (5) | עץ, אבל לא ברור אם זו מנורת שולחן או רגל; "Creative / Personality" מרמז על צורה חריגה. |
| floor-lamp-cj-ins-wind-nordic | verify-if-needed (6) | ספק CJ, אבל בלי חומר, אהיל, גובה או גוון. |
| floor-lamp-aliexpress-black-iron-art-standing | verify-if-needed (7) | שחור מתאים, אבל לא מוזכר אהיל בד (סיכון לנורה חשופה) ו-"Art" מרמז על פיסוליות. |

### rug — שטיח
> לאף ליד אין חומר בתקציר. "Luxury carpet" באליאקספרס הוא לרוב פוליאסטר עם ברק, ולכן בדיקת החומר והברק בתקריב היא השער הראשון.

| lead_id | החלטה | נימוק |
| --- | --- | --- |
| rug-aliexpress-modern-grey-carpet-200x300 | verify-first (1) | 200×300 בטווח ואפור (מועמד לאפור ערפל); לבדוק שהאפור לא כחלחל ושהבהירות L≥60. |
| rug-aliexpress-scandinavian-gray-large | verify-first (2) | סקנדינבי, אפור, "Simple"; המידה לא ידועה. |
| rug-aliexpress-nordic-luxury-200x300 | verify-if-needed (1) | מידה מדויקת, בלי גוון וחומר; "Luxury" הוא סיכון לברק. |
| rug-aliexpress-light-luxury-nordic-minimalist | verify-if-needed (2) | "Light" אולי בהיר, בלי מידה, חומר וגוון. |
| rug-aliexpress-scandinavian-luxury-minimalist | verify-if-needed (3) | כותרת נורדית בלבד, בלי נתונים. |
| rug-aliexpress-european-luxury-200x300 | verify-if-needed (4) | מידה מדויקת, אבל "European Luxury" עלול להיות דוגמה קלאסית או מדליון. |
| rug-aliexpress-washable-8x10-abstract-fluff | verify-if-needed (5) | מידה בטווח, אבל "Abstract" (דוגמה) ו-"Fluff" (סיב גבוה) הם שני דגלים אדומים. אחרון בתור. |

### sofa-cover — שמיכה על הספה
> לכל הלידים: הגוון חייב להיות לבן חם בבהירות L 93–97, מרווה, או לבן חם עם נימור. **בז', אפור ושיבולת שועל אסורים** (נעלמים על הספה). "Knitted" באליאקספרס הוא לרוב אקריליק, ולכן לבדוק הרכב.

| lead_id | החלטה | נימוק |
| --- | --- | --- |
| sofa-cover-aliexpress-inya-waffle-embossed-solid | verify-first (1) | ופל בגוון אחיד, מותג סדרתי עם מבחר גוונים: הסיכוי הגבוה ביותר ללבן חם וגם למרווה. |
| sofa-cover-aliexpress-waffle-nordic | verify-first (2) | ופל לספה, כמו שה-Bible ממליץ לטקסטורה. |
| sofa-cover-aliexpress-wool-blend-nordic | verify-first (3) | תערובת צמר מותרת במפורש; מבדל טקסטורה מול הופל. |
| sofa-cover-aliexpress-inyahome-tassel | verify-first (4) | סריגה עם גדילים: טקסטורה שלישית מבדלת; גדילים עד 5 ס"מ. |
| sofa-cover-aliexpress-tassel-solid-fringe-large | verify-if-needed (1) | גוון אחיד עם פרנזים, אבל "Large" עלול לחרוג מ-130–150 × 170–200. |
| sofa-cover-aliexpress-nordic-shawl-solid | verify-if-needed (2) | גוון אחיד וסריגה, בלי שום נתון נוסף. |
| sofa-cover-aliexpress-lightweight-decorative-knitted | verify-if-needed (3) | "Lightweight" עלול להיראות דק ושטוח בתקריב. |
| sofa-cover-aliexpress-summer-boho-embossed | verify-if-needed (4) | גוון אחיד עם הבלטה, אבל מתויג "Boho". |
| sofa-cover-aliexpress-waffle-plaid-multicolor | verify-if-needed (5) | 150×200 וכותנה טובים, ו-"light green" אולי מרווה, אבל בז' ואפור אסורים כאן ו-"Plaid" עלול להיות משבצות. |
| sofa-cover-aliexpress-cotton-throw-46x60 | drop | 117×152 לפי הכותרת, קטן מהמעטפת 130–150 × 170–200. |

### cushions — כריות
> שלושה סטים כאלה לא קיימים כמוצר מוכן. כל וריאציה תורכב משילוב כיסויים, עדיף מאותו מוכר (ראו התלבטויות).

| lead_id | החלטה | נימוק |
| --- | --- | --- |
| cushions-aliexpress-green-corduroy-solid | verify-first (1) | הליד היחיד שעשוי לשאת את המרווה, שהיא חובה בכל סט; לוודא S בטווח 8–22 ולא ירוק בקבוק. |
| cushions-aliexpress-scandinavian-heavy-cotton-linen-solid | verify-first (2) | כותנה-פשתן כבד, אחיד, סקנדינבי; מקור אפשרי ללבן חם, פחם ומרווה. |
| cushions-aliexpress-cotton-linen-30x50-nordic | verify-first (3) | בדיוק במידת הכרית השלישית (30×50); לבחור לבן חם או פחם. |
| cushions-aliexpress-textured-boucle-18in-solid | verify-first (4) | בוקלה כטקסטורה שנייה בסט (עד 1 בסט); 45×45 קצת קטן, ולכן לחפש 50×50. |
| cushions-aliexpress-corduroy-multisize-generic | verify-if-needed (1) | קורדרוי, יש 50×50, אבל הגוונים לא ידועים. |
| cushions-aliexpress-nordic-linen-pstripes | verify-if-needed (2) | פשתן טבעי; פסים מותרים רק כדוגמה יחידה בסט, ו"natural" עלול להיות שיבולת שועל (אסור על הספה). |
| cushions-aliexpress-solid-color-multisize-waist | verify-if-needed (3) | 50×50 זמין, אבל בלי חומר (סיכון לפוליאסטר גנרי). |
| cushions-aliexpress-corduroy-solid-35-50x70 | verify-if-needed (4) | קורדרוי, אבל המידות (35×35, 50×70) לא מתאימות להרכב הסט. |
| cushions-aliexpress-corduroy-beige-40x40 | drop | בז' מפורש (בטקסטיל על הספה מותר רק לבן חם L 93–97) וגם 40×40 קטן מדי. |
| cushions-aliexpress-rust-olive-corduroy-striped | drop | "Rust" מחוץ לפלטה, פסים ו-"Boho/Farmhouse". |

## 3. עמדות חלשות והמלצות לסבב החיפוש הבא

**מתחת ל-6 לידים שאינם drop:** רק magazine-holder (4). בנוסף, ארבע עמדות עברו את הסף אבל חלשות בפועל: candle-holders (6, מהם verify-first אחד), rug (אין חומר באף ליד, ואין אף ליד בהיר או בשיבולת שועל), floor-lamp (2 verify-first) ו-basket (אין חלופה לראטן וקש).

### magazine-holder (קריטי: נשא פחם חובה)
- **סוגי מוצר:** סל חוט מתכת שחור מט עם ידית עץ; סל או טוטה מלבד בגוון פחם (עומד על הרצפה, 40–50 ס"מ); מתלה עומד משלד מתכת שחורה עם "ערסל" קנבס או לבד פחם; מתלה עץ בהיר עם רצועת עור שחור.
- **ניסוחים (AliExpress / CJ):** "felt magazine basket grey floor", "felt storage basket charcoal handle", "black wire magazine basket wooden handle", "iron wire storage basket black floor magazine", "metal magazine rack floor black canvas sling", "wooden magazine holder floor leather handle", "newspaper storage basket felt standing".
- חשוב: "felt storage basket" ו-"wire basket" הם קטגוריות גדולות בהרבה מ-"magazine rack" באליאקספרס, ולכן הן המקור הסביר לתוצאות.

### candle-holders
- **סוגי מוצר:** זוג פמוטי קרמיקה מט בשני גבהים; פמוטי טרוורטין; פמוטי עץ אלון לנר צר; פמוטי מתכת שחורה מט דקים; זוג פליז מוברש (החומר היחיד שבו פליז מותר).
- **ניסוחים:** "ceramic candlestick holder matte set of 2 tall short", "stoneware taper candle holder nordic", "travertine candle holder taper", "wooden candlestick holder oak taper", "black metal taper candle holder minimalist", "brushed brass candlestick set 2 different height", "concrete candle holder nordic".
- טיפ: ליסטינג אחד עם אופציות גובה (S/M/L) נחשב זוג אם קונים שתי מידות שונות בהפרש של 5 ס"מ לפחות.

### rug
- **סוגי מוצר:** שטיח שטוח מכותנה או כותנה-יוטה; שטיח ברבר בקרם (וריאציה אחת עד 30 מ"מ); שטיח צמר-כותנה שטוח בשיבולת שועל עם קווים דקים בפחם; שטיח לבן חם טון-על-טון.
- **ניסוחים:** "cotton flatweave rug 200x300 cream", "jute wool rug rectangle 200x300 natural", "berber rug cream 200x300 low pile", "wool rug beige 240x340 flat", "scandinavian rug cream thin stripe", "kilim rug cream plain flat".
- להוסיף ל-sourcing-agent: לכתוב חומר מהתקציר בכל ליד, ולהחריג בכוונה "imitation cashmere", "silk-like" ו-"crystal velvet" (כולם מבריקים).

### floor-lamp
- **ניסוחים:** "floor lamp linen shade wood pole", "tripod floor lamp wood fabric shade 160cm", "floor lamp black metal linen drum shade E27", "ceramic base floor lamp fabric shade", "floor lamp oak straight pole pleated shade".

### basket (גיוון חומרי ולא כמות)
- כל הלידים שנשארו הם ראטן או קש ים. כדאי להביא חלופה של חבל כותנה או חבל נייר בגודל נכון: "cotton rope basket 40x45 handle natural", "paper rope basket large floor", "jute basket 40cm handle natural".

### curtains (בדיוק 6)
- "linen sheer curtain pinch pleat 140x260", "cotton linen voile curtain wave fold", "sheer curtain oatmeal linen texture ready made", "grey linen sheer curtain warm" (לווריאציה באפור ערפל).

## 4. מבט על החדר כולו

### שילובים שכבר נראים מבטיחים
- **מסלול ברירת מחדל אפשרי:** וילון NAPEARL בז' + שטיח אפור 200×300 + שמיכת ופל לבנה-חמה (Inya) + סט כריות כותנה-פשתן לבן חם עם קורדרוי מרווה + סל קש ים + קישוט קיר עגול מראטן + אגרטל בקבוק בז' + שלישייה מופשטת בשחור-לבן במסגרת שחורה. יוצא חדר מואר, עם פחם בתמונה, מרווה בכריות ובענפים, וסיבים טבעיים משני צדי החדר.
- **טקסטורות:** יש פוטנציאל לגיוון אמיתי: ופל וסריגה (שמיכה), קורדרוי ובוקלה ופשתן (כריות), קש ים וראטן (סל, קיר), טרוורטין וקרמיקה (שולחן קפה), גזה פשתן (וילון). זה הרבה מעבר למינימום של 3.
- **האיזון:** הסל וקישוט הקיר מימין (סיבים חמים) מול החלון והכורסה משמאל. אם הווריאציות של הסל בקש ים, עדיף שקישוט הקיר יהיה בראטן או במקרמה, כדי ששני הפריטים לא ייראו כמו אותו סל פעמיים.
- **שולחן הקפה:** אגרטל טרוורטין עם פמוטי קרמיקה יוצרים שילוב אבן וקרמיקה נקי. אבל פמוטי טרוורטין ביחד עם אגרטל טרוורטין ממצים את מכסת "עד 2 פריטי אבן".

### סיכונים לחדר כולו
1. **חוסר בפחם (הסיכון הגדול):** ה-Bible מחייב פחם בשני נשאים, framed-art ו-magazine-holder. מחזיק העיתונים כמעט ריק, ובלעדיו הפחם נשען על התמונה לבד, וכלל "הדגשה מופיעה פעמיים" נופל בכל שילוב. גיבויים חלקיים: כרית פחם (לא בכל סט), פמוט מתכת שחורה, בסיס מנורה שחור. אלה לא מובטחים בכל שילוב.
2. **מרווה תלויה בליד אחד:** רק ליד כריות אחד (green-corduroy) הוא מועמד מרווה מפורש, והמרווה חובה בכל 3 סטי הכריות. אם הוא ייצא ירוק רווי, העמדה נתקעת. צריך לחפש כיסויי כרית במרווה כבר בסבב הבא.
3. **יותר מדי בז' או אפור על הספה:** רוב הלידים לטקסטיל על הספה לא מציינים גוון, והמוכרים מציעים בעיקר בז' ואפור. אלה אסורים כאן, ובאימות צריך לבחור רק לבן חם בבהירות L 93–97 או מרווה.
4. **ראטן וקש:** כרגע ראטן וקש מופיעים רק בסל ובקיר, וזה תקין. סל כותנה או חבל נייר יפחית את החזרה. שטיח יוטה ייחשב "הפריט הנוסף" היחיד שמותר.
5. **שטיח:** כל הלידים עם גוון הם אפורים, ואין חומר באף אחד. שטיח אפור מתחת לכורסה בבוקלה אפור ערפל עלול לבלוע אותה. צריך לפחות וריאציה אחת בלבן חם או בשיבולת שועל עם טקסטורה (כלל הניגוד מול הספה: L≥6 או דוגמה).
6. **מראה זול וסינתטי:** "Luxury carpet", "knitted blanket", "faux leather" ו-"faux linen" הם לרוב פוליאסטר ואקריליק. במיצוב פרימיום נגיש, התקריב של הטקסטיל הוא המקום שבו החדר יכול להיראות זול. צריך לדרוש מהמוכרים תמונות של לקוחות.
7. **לבן טהור ושחור טהור:** "White" בווילון ו-"Black and White" בתמונה ובאגרטל הם סיכון ל-#FFFFFF או לשחור טהור, ששניהם אסורים.

## התלבטויות שדורשות את המשתמש
1. **"Handmade / Handwoven" בפריטי סיבים טבעיים:** כמעט כל קישוטי הקיר מראטן ומקש ים, וחלק מהסלים, מתויגים handmade, כי זו שיטת הייצור שלהם גם בייצור סדרתי. האם מוצר קטלוג סדרתי עם הרבה הזמנות, שכתוב עליו handwoven, מותר? אם לא, עמדת wall-decor כמעט מתרוקנת. בסינון הזה לא פסלתי על המילה לבד.
2. **עור מלאכותי במחזיק העיתונים:** ב-Bible, עור מותר רק בידיות ורצועות ובגימור מט. במתלה מחוט וערסל עור, העור הוא חלק ניכר מהגוף. האם לאשר חריגה אם הערסל בפחם מט, או לחפש רק חוט, לבד ועץ?
3. **יקינטון מים (water hyacinth) בסל:** נראה כמו קש ים, אבל לא ברשימת החומרים הסגורה. הוספה לרשימה היא שינוי ב-Bible ומחייבת אישור.
4. **העתקים של מנורות מעצבים:** שני לידים מציגים את עצמם כהעתק של עיצוב מוכר. זה סיכון משפטי ומיתוגי, גם אם הצללית מתאימה. להמשיך או לפסול?
5. **חשמל בישראל:** מנורות מאליאקספרס מגיעות לרוב עם תקע אירופאי או אמריקאי ובלי תו תקן ישראלי. כדאי להחליט מראש מה המדיניות: מתאם, תקע ישראלי, או ויתור על מנורות חשמליות מדרופשיפינג.
6. **כריות כסט מורכב:** אין סטים מוכנים. להרכיב סט משני או שלושה מוכרים, או לדרוש מוכר אחד לכל סט? מוכר אחד פשוט יותר לעקביות ולמשלוח.
