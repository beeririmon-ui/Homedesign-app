# טיוטת פנייה: Syncee (פלטפורמת דרופשיפינג, הונגריה)

> טיוטה בלבד, 2026-10-10. **המשתמש נרשם ושולח, לא הסוכנים** (חוקי הסטודיו ד.7–ד.8). אושר: S4.
> מקור הפרטים: `data/suppliers/directory.json` (id: `syncee`), `docs/suppliers/rug-curtains-research.md` §ב.
> Syncee היא פלטפורמה, לא ספק. הצעד הראשון הוא **סינון חינמי בתוך החשבון**, ורק אחריו פנייה לספקים ספציפיים דרך הפלטפורמה.

## ערוץ
| ערוץ | פרט | הערה |
| --- | --- | --- |
| **הרשמה חינמית (Free plan)** | https://syncee.com/ | אימייל וסיסמה בלבד. **לא להזין אמצעי תשלום** |
| מחירים | https://syncee.com/pricing/ | לקריאה בלבד |
| פנייה לספק | מתוך דף הספק בפלטפורמה (כפתור יצירת קשר / בקשת אישור) | לא אומת איך בדיוק נראה הכפתור |
| תמיכת Syncee | צ'אט או טופס בתוך החשבון | **כתובת ייעודית לא נאספה**; המדריך מציין רק את דף הבית |

## צעדי המשתמש (לפני כל פנייה)
1. נרשמים בתוכנית Free.
2. ב-Marketplace מסננים: **Shipping to = Israel**, ‏Supplier location = Europe (ואחר כך גם UK/US).
3. מחפשים לפי הפערים: `linen curtain`, `table runner`, `ceramic vase`, `candle holder`, `storage basket`, `wooden tray`, `canister`, `tea towel`, `bath mat`.
4. לכל ספק רלוונטי רושמים בטבלה (מעבירים לסוכן הליקוט): שם ספק, קישור, מוצר, מחיר סיטונאי, זמן ועלות משלוח לישראל, האם נדרש אישור ספק.
5. רק לספקים שעברו את הסינון שולחים את ההודעה למטה.
6. **לא משלמים מנוי** (מ-$39.99 לחודש) עד שנמצאו 2–3 מוצרים מתאימים והחנות מוכנה.

**לא לבחור ספקי הדפסה לפי הזמנה (POD)** — נפסל ב-S5.

## מה המשתמש ממלא
- [Business name] (שם המותג עוד לא נקבע)
- [Full name]
- [Website] (או "launching [month]")
- [Supplier name]
- [Product names / links]

## הודעה א: לספק בתוך Syncee (אנגלית)

**Subject:** Retailer from Israel: dropshipping terms

Hello [Supplier name],

I am [Full name] from [Business name], a curated online home-decor store in Israel, launching with a Nordic-style collection. We are interested in [Product names / links].

Could you please confirm:
1. **Israel:** Do you dropship to end customers in Israel, in neutral packaging with no prices or invoice in the parcel?
2. **Minimum order:** Is there any minimum order or minimum monthly volume?
3. **Shipping to Israel:** Cost and delivery time to Israel, economy and express, and who handles customs.
4. **Product data:** Do you keep stock and prices updated through Syncee, and can you also provide a CSV or API feed? May we use your images?
5. **Price list:** Your wholesale prices and recommended retail prices for the range.
6. **Samples:** Can we order one unit of each item as a sample?
7. **Returns:** Your policy for returns and damaged items.
8. **Certificates (for information):** CE declarations for any lighting (220–240 V), EN 71 for children's items.

Thank you,
[Full name], [Business name] · [Website]

## הודעה ב: לתמיכת Syncee, רק אם הסינון לא ברור (אנגלית)

Hello, we are an Israeli online home-decor retailer on the Free plan. Is the "Shipping to: Israel" filter reliable, i.e. does it show only suppliers that currently ship to Israel? Which plan do we need to contact suppliers and import products to a custom (non-Shopify) store, and is a CSV export or API available on that plan? Thank you.

## הערות פנימיות (לא לשלוח)
- **יעד עלות** (עלות נחיתה כולל משלוח ומכס, לפני מע"מ; `data/economics/market-prices.md` §3): זוג וילונות כ-₪86 (₪179); ראנר כ-₪62 (₪129); אגרטל גדול כ-₪146 (₪299); פמוט כ-₪43 (₪89); סלסלה כ-₪33 (₪69); צנצנת כ-₪23 (₪49).
- האתר שלנו הוא חנות מותאמת (חוקי הסטודיו ו.2), ולכן שאלת האינטגרציה בלי Shopify חשובה.
