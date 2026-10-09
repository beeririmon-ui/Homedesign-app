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
  "status": z.enum(["candidate","selected","rejected"]),
  "notes": z.string().nullable().optional(),
}).describe("כרטיס מוצר אחד. sourcing-agent ממלא הכל חוץ מ-style_scores; master-designer ממלא את style_scores ואת status.");

export type ProductCard = z.infer<typeof ProductCardSchema>;
