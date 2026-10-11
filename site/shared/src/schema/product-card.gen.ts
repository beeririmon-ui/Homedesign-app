// GENERATED FILE. Do not edit by hand.
// Source: data/product-card.schema.json  ·  Generator: shared/scripts/gen-product-card-schema.ts
import { z } from 'zod';

export const ProductCardSchema = z.looseObject({
  "id": z.string().describe("<slot-id>-<supplier>-<short-name>"),
  "slot": z.string().describe("מזהה עמדה מתוך data/slots/<room>.json"),
  "name": z.string(),
  "category": z.string().optional(),
  "rooms": z.array(z.string()).optional(),
  "placement": z.enum(["floor","wall","window","surface","sofa","ceiling"]).optional(),
  "supplier": z.looseObject({
    "name": z.string(),
    "product_url": z.string(),
    "sku": z.string().nullable().optional(),
    "rating": z.number().nullable().optional(),
  }),
  "price": z.looseObject({
    "cost": z.number(),
    "currency": z.string(),
    "suggested_retail": z.number().nullable().optional(),
  }),
  "shipping": z.looseObject({
    "days_min": z.number().int().nullable().optional(),
    "days_max": z.number().int().nullable().optional(),
    "ships_to": z.array(z.string()).optional(),
  }).optional(),
  "dimensions_cm": z.looseObject({
    "width": z.number().nullable().optional(),
    "depth": z.number().nullable().optional(),
    "height": z.number().nullable().optional(),
  }).optional(),
  "colors": z.looseObject({
    "dominant_hex": z.string().regex(new RegExp("^#[0-9A-Fa-f]{6}$")),
    "secondary_hex": z.array(z.string().regex(new RegExp("^#[0-9A-Fa-f]{6}$"))).optional(),
    "temperature": z.enum(["warm","cool","neutral"]),
  }),
  "materials": z.array(z.string()),
  "texture": z.string().nullable().optional(),
  "finish": z.enum(["matte","satin","gloss"]).nullable().optional(),
  "visual_weight": z.enum(["light","medium","heavy"]),
  "lighting": z.looseObject({
    "color_temp_k": z.number().int().nullable().optional(),
    "light_type": z.enum(["direct","diffuse","mixed"]).nullable().optional(),
  }).nullable().describe("לגופי תאורה בלבד").optional(),
  "images": z.looseObject({
    "urls": z.array(z.string()),
    "quality": z.enum(["high","medium","low"]),
    "usage_rights": z.enum(["confirmed","unclear","none"]),
  }),
  "style_scores": z.record(z.string(), z.looseObject({
    "score": z.number().min(0).max(10),
    "reason": z.string(),
  })).describe("מפתח לכל סגנון (nordic, boho, warm-modern)").optional(),
  "safety": z.strictObject({
    "ce": z.boolean().nullable().describe("האם הספק מצהיר על CE").optional(),
    "ip_rating": z.string().nullable().describe("למשל IP44").optional(),
    "toy_standard": z.array(z.enum(["EN71","SI-562","EN13613"])).describe("תקני צעצועים ומוצרי ילדים; ריק = אין").optional(),
    "power": z.enum(["plug","wired","battery","usb","none"]).nullable().optional(),
    "plug_type": z.string().nullable().describe("למשל EU, IL, UK").optional(),
    "voltage": z.string().nullable().describe("למשל 220-240V").optional(),
    "certificates": z.array(z.strictObject({
      "name": z.string(),
      "url": z.string().regex(new RegExp("^https://")),
      "verified": z.boolean(),
    })).optional(),
    "source": z.string().describe("מאיפה המידע, למשל supplier listing או CJ API").optional(),
  }).describe("בטיחות ותקינה כפי שהספק מצהיר (Q2, 2026-10-10). אופציונלי. null = לא ידוע. toy_standard: מוצג בדף המוצר (D9)").optional(),
  "options": z.strictObject({
    "axes": z.array(z.strictObject({
      "id": z.enum(["size","length","width","color","pattern","finish","style","set","other"]),
      "name_he": z.string().min(1).describe("שם הציר בדף המוצר, למשל מידה, צבע"),
      "values": z.array(z.strictObject({
        "id": z.string().regex(new RegExp("^[a-z0-9][a-z0-9._-]*$")).describe("מזהה יציב בתוך הציר, למשל 200x260, beige"),
        "label_he": z.string().min(1).describe("מה שהלקוח רואה, למשל 200×260, בז'"),
        "label_src": z.string().describe("השם אצל הספק, כמו שהוא").optional(),
        "hex": z.string().regex(new RegExp("^#[0-9A-Fa-f]{6}$")).describe("בציר צבע: דוגמית הצבע").optional(),
      })).min(1),
    })).min(1).describe("צירי הבחירה, לפי הסדר שבדף המוצר. כל מזהה ציר מופיע פעם אחת"),
    "skus": z.array(z.strictObject({
      "id": z.string().min(1).describe("מזהה ה-SKU אצל הספק: AliExpress sku_id, ‏CJ variantSku, ‏Zendrop sku"),
      "values": z.partialRecord(z.enum(["size","length","width","color","pattern","finish","style","set","other"]), z.string()).describe("ציר → מזהה ערך: ערך אחד לכל ציר שב-axes"),
      "price": z.strictObject({
        "amount": z.number().min(0),
        "currency": z.string().regex(new RegExp("^[A-Z]{3}$")),
      }).describe("עלות ה-SKU אצל הספק, בלי משלוח"),
      "shipping_il": z.strictObject({
        "amount": z.number().min(0),
        "currency": z.string().regex(new RegExp("^[A-Z]{3}$")),
        "days": z.string().regex(new RegExp("^[0-9]+(-[0-9]+)?$")).nullable().describe("ימי אספקה, למשל 6-15").optional(),
      }).describe("משלוח לישראל של ה-SKU, כשיש מחיר משלו. בלי השדה: המשלוח של הכרטיס ועלות המשלוח שבסטודיו").optional(),
      "stock": z.number().int().min(0).nullable().describe("מלאי אצל הספק כשנקרא; null = לא ידוע").optional(),
      "image": z.string().regex(new RegExp("^https://")).nullable().describe("תמונת הספק של ה-SKU").optional(),
      "in_room": z.boolean().describe("true רק ב-default_sku: האפשרות שמוצגת בחדר").optional(),
    })).min(1).describe("כל צירוף שקיים אצל הספק. צירוף שלא מופיע כאן לא קיים, ודף המוצר לא מאפשר לבחור אותו"),
    "default_sku": z.string().min(1).describe("ה-SKU שבחדר (נאמנות) וברירת המחדל בדף המוצר; שווה ל-supplier.sku"),
    "source": z.enum(["api","manual"]),
  }).describe("כל האפשרויות של הספק (2026-10-11, חוקי הסטודיו ג, 'כל האפשרויות של הספק בדף המוצר'). אופציונלי ותוספתי: דף המוצר מציג את כל ה-SKU והלקוח בוחר, כל אחד עם מחיר ומשלוח משלו. החדר מציג רק את default_sku (in_room), אפשרות שקיימת אצל הספק. price ו-supplier.sku של הכרטיס נשארים של default_sku. source: api = נבנה מתגובת ה-API השמורה (backfill-options של ds.py ו-cj_source.py, נבנה מחדש בכל הרצה); manual = נכתב ביד, ואף סקריפט לא דורס אותו").optional(),
  "status": z.enum(["candidate","selected","rejected"]),
  "notes": z.string().nullable().optional(),
}).describe("כרטיס מוצר אחד. sourcing-agent ממלא הכל חוץ מ-style_scores; master-designer ממלא את style_scores ואת status. 2026-10-10: נוסף שדה safety אופציונלי (החלטת משתמש Q2). 2026-10-11: נוסף שדה options אופציונלי, כל האפשרויות של הספק (חוקי הסטודיו ג, 'כל האפשרויות של הספק בדף המוצר').");

export type ProductCard = z.infer<typeof ProductCardSchema>;
