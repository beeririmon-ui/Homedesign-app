/**
 * Repo → catalog. The repo stays the source of truth (product cards, slots, house plan, economics);
 * this script derives what the site and the D1 seed need.
 *
 *   tsx tools/build-catalog.ts                  provisional mode (dev, preview, artifact)
 *   tsx tools/build-catalog.ts --strict-prices  production rule: a product without retail_ils is not shown
 *
 * Outputs (gitignored):
 *   .generated/catalog.public.json   browser-safe (no supplier, cost or margin)
 *   .generated/catalog.full.json     seed + admin only
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync, statSync } from 'node:fs';
import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { relative, join } from 'node:path';
import {
  ProductCardSchema,
  SlotsFileSchema,
  HotspotPointsSchema,
  SettingsFileSchema,
  ProductEconomicsFileSchema,
  FreightFileSchema,
  resolveShippingUsd,
  type FreightFile,
  PublicCatalogSchema,
  resolveSettings,
  recommendedRetailIls,
  unitEconomics,
  usdToCents,
  ilsToAgorot,
  type ProductCard,
  type Slot,
  type CatalogRoom,
  type CatalogSlot,
  type FullProduct,
  type HiddenProduct,
  type PublicCatalog,
  type FullCatalog,
  type ShippingOption,
  type ProductEconomics,
  sellQtyDefault,
  unitPriceEstimateIls,
  publicSafety,
} from '@hd/shared';
import { REPO, GENERATED, repoPath, sitePath } from './lib/paths';
import { materialsHe, colorNameHe, hasHebrew } from './lib/hebrew';

const STRICT = process.argv.includes('--strict-prices');
/** Rooms with a working room engine in this phase. Others are listed as "soon". */
const BUILT_ROOMS = new Set(['living-room']);
const STYLE = 'nordic';

type HousePlan = {
  rooms: { id: string; name_he: string; build: boolean; frames: string[] | null; slots_file: string | null }[];
  transitions: { id: string; from: string; to: string; reverse: boolean }[];
};

const readJson = (p: string): unknown => JSON.parse(readFileSync(p, 'utf8'));

function gitCommit(): string {
  try {
    const sha = execSync('git rev-parse --short HEAD', { cwd: REPO }).toString().trim();
    const dirty = execSync('git status --porcelain -- data docs/house-plan.json', { cwd: REPO }).toString().trim();
    return dirty ? `${sha}+dirty` : sha;
  } catch {
    return 'unknown';
  }
}

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? walk(p) : p.endsWith('.json') ? [p] : [];
  });
}

// ---------- inputs ----------
const house = readJson(repoPath('docs/house-plan.json')) as HousePlan;
const tempCoords = readJson(sitePath('tools/temp/living-room.nordic.json')) as {
  slots: Record<string, { boxes: number[][]; hotspot: [number, number]; visible?: boolean; zoom?: number[] }>;
};

const settingsPath = repoPath('data/economics/settings.json');
const productsEconPath = repoPath('data/economics/products.json');
const freightPath = repoPath('data/economics/freight-cj.json');
const settingsInput = existsSync(settingsPath) ? SettingsFileSchema.parse(readJson(settingsPath)) : null;
const freight: FreightFile | null = existsSync(freightPath) ? FreightFileSchema.parse(readJson(freightPath)) : null;
const productEcon: Record<string, ProductEconomics> = existsSync(productsEconPath) ? ProductEconomicsFileSchema.parse(readJson(productsEconPath)) : {};
const { settings, defaults_used } = resolveSettings(settingsInput);

/** Cards that fail data/product-card.schema.json are reported and skipped (data/ is not ours to fix). */
const invalidCards: { path: string; issues: string }[] = [];
const cards: { card: ProductCard; path: string }[] = walk(repoPath('data/products')).flatMap((p) => {
  const parsed = ProductCardSchema.safeParse(readJson(p));
  if (!parsed.success) {
    invalidCards.push({
      path: relative(REPO, p),
      issues: parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; '),
    });
    return [];
  }
  return [{ card: parsed.data, path: relative(REPO, p) }];
});

// ---------- rooms and slots ----------
const SLOT_FILE_FOR: Record<string, string> = { living: 'living-room' };
const roomIdOf = (houseId: string): string => SLOT_FILE_FOR[houseId] ?? houseId;

const fullProducts: FullProduct[] = [];
const hidden: HiddenProduct[] = [];
const rooms: CatalogRoom[] = [];
/** fixed-product slots (F3) without a product card yet */
const fixedWaiting: string[] = [];

/** The slot file's own hotspot: { u, v } (any frame), or the point of this frame in the newer { points } shape. */
function hotspotFromFile(slot: Slot, frame: string): CatalogSlot['hotspot'] {
  const h = slot.hotspot;
  if (!h || Array.isArray(h)) return null;
  const pts = HotspotPointsSchema.safeParse(h);
  if (pts.success) {
    const pt = pts.data.points.find((p) => p.frame === frame) ?? pts.data.points[0];
    return pt ? { u: pt.u, v: pt.v, provisional: pts.data.provisional === true, visible: pts.data.visible !== false } : null;
  }
  return typeof h.u === 'number' && typeof h.v === 'number' ? { u: h.u, v: h.v, provisional: false, visible: true } : null;
}

function frameBoxFromBoxes(boxes: number[][]): [number, number, number, number] | null {
  if (boxes.length === 0) return null;
  const u0 = Math.min(...boxes.map((b) => b[0]!));
  const u1 = Math.max(...boxes.map((b) => b[1]!));
  const v0 = Math.min(...boxes.map((b) => b[2]!));
  const v1 = Math.max(...boxes.map((b) => b[3]!));
  // Zoom target: the product fills ~60% of the screen (skeleton-spec, "מצלמות"), framed at 16:9.
  const aspect = 16 / 9;
  const w = (u1 - u0) / 0.6;
  const h = (v1 - v0) / 0.6;
  let fw = Math.max(w, (h * 1) / aspect);
  fw = Math.min(1, Math.max(fw, 0.18));
  const fh = Math.min(1, fw);
  const cu = (u0 + u1) / 2;
  const cv = (v0 + v1) / 2;
  const clamp = (c: number, size: number) => Math.min(1 - size / 2, Math.max(size / 2, c));
  const ucen = clamp(cu, fw);
  const vcen = clamp(cv, fh);
  const r = (x: number) => Math.round(x * 10000) / 10000;
  return [r(ucen - fw / 2), r(ucen + fw / 2), r(vcen - fh / 2), r(vcen + fh / 2)];
}

function shippingDays(c: ProductCard): [number, number] | null {
  const a = c.shipping?.days_min;
  const b = c.shipping?.days_max;
  return typeof a === 'number' && typeof b === 'number' ? [a, b] : null;
}

function productNotes(slot: Slot, fillerNames: string[], o: { wiredInSafety: boolean; packChoice: boolean }): string[] {
  const notes: string[] = [];
  if (fillerNames.length) notes.push(`בתמונה: ${fillerNames.join(', ')}. לא כלול במוצר.`);
  // the safety row says it when the card states power: wired
  if ((slot.id === 'accent-sconces' || slot.id === 'pendant') && !o.wiredInSafety) notes.push('דורשת התקנה על ידי חשמלאי.');
  if (slot.id === 'wall-sconce') notes.push('בתמונה: הכבל מקוצר ומחובר לשקע צמוד מתחת למנורה (קיצור כבל והתקנת שקע על ידי חשמלאי).');
  // with a set / single choice the picker says what a set holds
  if (slot.set_of && !o.packChoice) notes.push(`בתמונה: סט של ${slot.set_of} פריטים.`);
  return notes;
}

function buildProduct(card: ProductCard, path: string, roomId: string, slot: Slot, fillerNames: string[]): FullProduct | HiddenProduct {
  const econ = productEcon[card.id] ?? {};
  const cost = usdToCents(card.price.currency === 'USD' ? card.price.cost : NaN);
  if (!Number.isFinite(cost)) return { id: card.id, slot: slot.id, reason: `price.currency ${card.price.currency} is not USD` };
  const shipping = resolveShippingUsd(card.id, econ.shipping_cost_usd, freight, settings);
  const shippingFromDefault = shipping.source === 'default';
  const ship = usdToCents(shipping.usd);
  // units per sale: the studio's sell_qty, else the studio's own default rule (studio/build.py sell_qty_default)
  const qtyDefault = sellQtyDefault(card, slot.set_of);
  const sellQty = econ.sell_qty ?? qtyDefault.qty;
  const fulfillment = econ.fulfillment_source ?? 'dropship_cj';
  let retailIls = typeof econ.retail_ils === 'number' ? econ.retail_ils : null;
  let provisional = false;
  if (retailIls === null) {
    if (STRICT) return { id: card.id, slot: slot.id, reason: 'no retail_ils in data/economics/products.json' };
    retailIls = recommendedRetailIls({ cost_usd_cents: cost, shipping_usd_cents: ship, fx_usd_ils: settings.fx_usd_ils, sell_qty: sellQty }, settings);
    provisional = true;
    if (retailIls === null) return { id: card.id, slot: slot.id, reason: 'target margin unreachable with current settings' };
  }
  const retail = ilsToAgorot(retailIls);
  const materials = materialsHe(card.materials);
  const color = colorNameHe(card.colors.dominant_hex);
  const name_he = `${slot.name_he}${materials[0] ? ` ${materials[0]}` : ''}, ${color}`;
  const d = card.dimensions_cm ?? {};
  const dims = [d.width, d.depth, d.height].filter((x): x is number => typeof x === 'number');
  const description = [
    hasHebrew(card.texture) ? `${card.texture}.` : null,
    materials.length ? `חומרים: ${materials.join(', ')}.` : null,
    dims.length ? `מידות: ${dims.join(' × ')} ס"מ (לפי הספק, לא אומת).` : null,
  ]
    .filter(Boolean)
    .join(' ');
  const compare = typeof econ.compare_at_ils === 'number' && econ.compare_at_ils > retailIls ? ilsToAgorot(econ.compare_at_ils) : null;
  // P1: a set (sell_qty > 1) is also sold as one piece. Unit price from the studio, else an estimate (marked as such).
  const unitIls =
    sellQty > 1
      ? typeof econ.unit_retail_ils === 'number' && econ.unit_retail_ils > 0
        ? econ.unit_retail_ils
        : unitPriceEstimateIls(retailIls, sellQty)
      : null;
  const pack =
    unitIls === null ? null : { set_qty: sellQty, unit_price_agorot: ilsToAgorot(unitIls), unit_price_estimated: typeof econ.unit_retail_ils !== 'number' };
  const safety = publicSafety(card.safety);
  return {
    id: card.id,
    room: roomId,
    slot: slot.id,
    name_he,
    name_provisional: true,
    description_he: description || `${slot.name_he}.`,
    price_agorot: retail,
    compare_at_agorot: compare,
    price_provisional: provisional,
    materials_he: materials,
    dimensions_cm: { width: d.width ?? null, depth: d.depth ?? null, height: d.height ?? null },
    color_hex: card.colors.dominant_hex,
    shipping_days: shippingDays(card),
    notes_he: productNotes(slot, fillerNames, { wiredInSafety: safety?.power === 'wired', packChoice: pack !== null }),
    set_of: slot.set_of ?? null,
    variants: [{ id: `${card.id}:default`, label_he: 'ברירת מחדל' }],
    pack,
    safety,
    name_supplier: card.name,
    category: card.category ?? null,
    status: card.status,
    source_path: path,
    supplier: { name: card.supplier.name, url: card.supplier.product_url, sku: card.supplier.sku ?? null },
    // FR-I: the first supplier photo (one per product, size budget); tools/supplier-images.ts serves it from our media
    supplier_image: {
      url: card.images.urls.find((u) => /^https:\/\//.test(u)) ?? null,
      usage_rights: card.images.usage_rights,
      quality: card.images.quality,
    },
    cost_usd_cents: cost,
    shipping_usd_cents: ship,
    shipping_from_default: shippingFromDefault,
    shipping_source: shipping.source,
    sell_qty: sellQty,
    sell_qty_source: typeof econ.sell_qty === 'number' ? 'studio' : 'default',
    sell_qty_sure: typeof econ.sell_qty === 'number' || qtyDefault.sure,
    sell_qty_reason: typeof econ.sell_qty === 'number' ? null : qtyDefault.reason,
    unit_economics: pack
      ? unitEconomics(
          { retail_agorot: pack.unit_price_agorot, cost_usd_cents: cost, shipping_usd_cents: ship, fx_usd_ils: settings.fx_usd_ils, sell_qty: 1 },
          settings,
        )
      : null,
    fulfillment_source: fulfillment,
    fx_usd_ils: settings.fx_usd_ils,
    nordic_score: card.style_scores?.[STYLE]?.score ?? null,
    economics: unitEconomics(
      { retail_agorot: retail, cost_usd_cents: cost, shipping_usd_cents: ship, fx_usd_ils: settings.fx_usd_ils, sell_qty: sellQty },
      settings,
    ),
  };
}

for (const hr of house.rooms) {
  if (!hr.slots_file) continue;
  const roomId = roomIdOf(hr.id);
  const slotsPath = repoPath('data/slots', `${roomId}.json`);
  const built = BUILT_ROOMS.has(roomId) && existsSync(slotsPath);
  const exits = house.transitions
    .filter((t) => t.from.startsWith(`${hr.id} `) || (t.reverse && t.to.startsWith(`${hr.id} `)))
    .map((t) => {
      const forward = t.from.startsWith(`${hr.id} `);
      const target = (forward ? t.to : t.from).split(' ');
      return { transition: t.id, to_room: roomIdOf(target[0]!), to_frame: target[1] ?? '', reverse: !forward };
    })
    .filter((e) => e.to_room !== roomId);

  if (!built) {
    rooms.push({
      id: roomId,
      house_room_id: hr.id,
      name_he: hr.name_he,
      style: STYLE,
      frame: hr.frames?.[0] ?? '',
      slots_version: '',
      base_layers: [],
      light_slots: [],
      slots: [],
      exits,
      built: false,
    });
    continue;
  }

  const sf = SlotsFileSchema.parse(readJson(slotsPath));
  const slots: CatalogSlot[] = [];
  const frame = hr.frames?.[0] ?? sf.view ?? 'main';
  for (const slot of sf.slots) {
    // F3 (2026-10-10): a fixed piece of furniture sold as one product. Until its card exists there is nothing to open,
    // so the slot stays out of the room (no empty wheel, no mark on the sofa); the list below the room skips it too.
    if (slot.kind === 'fixed-product') {
      fixedWaiting.push(slot.id);
      continue;
    }
    const fillerNames = (sf.fillers ?? []).filter((f) => f.slot === slot.id).map((f) => f.name_he);
    // Only designer-scored, non-rejected cards of this slot qualify; best Nordic score first.
    const candidates = cards
      .filter(({ card, path }) => card.slot === slot.id && path.split('/').length === 4 && card.status !== 'rejected')
      .filter(({ card }) => typeof card.style_scores?.[STYLE]?.score === 'number')
      .sort((a, b) => b.card.style_scores![STYLE]!.score - a.card.style_scores![STYLE]!.score || a.card.id.localeCompare(b.card.id));
    const chosen: FullProduct[] = [];
    for (const { card, path } of candidates) {
      if (chosen.length === (sf.variants_required ?? slot.variants ?? 3)) break;
      const p = buildProduct(card, path, roomId, slot, fillerNames);
      if ('reason' in p) hidden.push(p);
      else chosen.push(p);
    }
    fullProducts.push(...chosen);
    const need = sf.variants_required ?? slot.variants ?? 3;
    const options = Array.from({ length: need }, (_, i) => {
      const p = chosen[i];
      return {
        position: i + 1,
        product_id: p?.id ?? null,
        placeholder: !p,
        label_he: p ? p.name_he : `וריאציה ${i + 1} · ממתינה למוצר`,
        is_default: i === 0,
      };
    });
    const temp = tempCoords.slots[slot.id];
    const fromFile = hotspotFromFile(slot, frame);
    const hotspot = fromFile ? fromFile : temp ? { u: temp.hotspot[0], v: temp.hotspot[1], provisional: true, visible: temp.visible !== false } : null;
    const zoomFromFile = Array.isArray(slot.zoom_frame) && slot.zoom_frame.length === 4 ? (slot.zoom_frame as [number, number, number, number]) : null;
    slots.push({
      id: slot.id,
      name_he: slot.name_he,
      category: slot.category ?? null,
      placement: slot.placement,
      z: slot.z ?? 0,
      set_of: slot.set_of ?? null,
      has_light: slot.has_light_layer === true,
      has_shadow: slot.has_shadow_layer !== false,
      fillers_he: fillerNames,
      hotspot,
      zoom_frame:
        zoomFromFile ??
        (temp
          ? frameBoxFromBoxes(
              temp.zoom
                ? [temp.zoom]
                : temp.boxes.length
                  ? temp.boxes
                  : [[temp.hotspot[0] - 0.04, temp.hotspot[0] + 0.04, temp.hotspot[1] - 0.06, temp.hotspot[1] + 0.06]],
            )
          : null),
      options,
    });
  }
  rooms.push({
    id: roomId,
    house_room_id: hr.id,
    name_he: hr.name_he,
    style: STYLE,
    frame,
    slots_version: sf.version,
    base_layers: sf.base_layers.map((b) => ({ id: b.id, z: b.z, blend: b.blend ?? 'normal' })),
    light_slots: sf.light_layers?.slots ?? [],
    slots: slots.sort((a, b) => a.z - b.z),
    exits,
    built: true,
  });
}

// Customer shipping fees come from settings (storefront); provisional until decision E1 is made.
const shippingProvisional = (['shipping_fee_economy_ils', 'shipping_fee_express_ils', 'free_shipping_threshold_ils'] as const).some((k) =>
  defaults_used.includes(k),
);
const shipping: ShippingOption[] = [
  {
    id: 'economy',
    label_he: 'משלוח חסכוני',
    price_agorot: ilsToAgorot(settings.shipping_fee_economy_ils),
    free_over_agorot: settings.free_shipping_threshold_ils === null ? null : ilsToAgorot(settings.free_shipping_threshold_ils),
    days_he: 'לפי המוצר, בדרך כלל 12–30 ימים',
    provisional: shippingProvisional,
    is_default: true,
  },
  {
    id: 'express',
    label_he: 'משלוח מהיר',
    price_agorot: ilsToAgorot(settings.shipping_fee_express_ils),
    free_over_agorot: null,
    days_he: 'בדרך כלל 7–14 ימים',
    provisional: shippingProvisional,
    is_default: false,
  },
];

const styles = [
  { id: 'nordic', name_he: 'נורדי', available: true },
  { id: 'boho', name_he: 'בוהו', available: false },
  { id: 'warm-modern', name_he: 'מודרני חם', available: false },
];

const publicProducts = fullProducts.map((p) => ({
  id: p.id,
  room: p.room,
  slot: p.slot,
  name_he: p.name_he,
  name_provisional: p.name_provisional,
  description_he: p.description_he,
  price_agorot: p.price_agorot,
  compare_at_agorot: p.compare_at_agorot,
  price_provisional: p.price_provisional,
  materials_he: p.materials_he,
  dimensions_cm: p.dimensions_cm,
  color_hex: p.color_hex,
  shipping_days: p.shipping_days,
  notes_he: p.notes_he,
  set_of: p.set_of,
  variants: p.variants,
  pack: p.pack,
  safety: p.safety,
}));

const base = {
  built_at: new Date().toISOString(),
  git_commit: gitCommit(),
  mode: (STRICT ? 'strict' : 'provisional') as 'strict' | 'provisional',
  styles,
  rooms,
  shipping,
  vat_rate: settings.vat_rate,
};
const version = createHash('sha256').update(JSON.stringify({ rooms, publicProducts, shipping })).digest('hex').slice(0, 12);

const publicCatalog: PublicCatalog = PublicCatalogSchema.parse({ version, ...base, products: publicProducts });
const fullCatalog: FullCatalog = {
  version,
  ...base,
  products: fullProducts,
  hidden,
  invalid_cards: invalidCards,
  economics: {
    settings,
    defaults_used,
    sources: {
      settings: settingsInput ? 'data/economics/settings.json' : null,
      products: Object.keys(productEcon).length ? 'data/economics/products.json' : null,
      freight: freight ? 'data/economics/freight-cj.json' : null,
    },
  },
};

mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'catalog.public.json'), JSON.stringify(publicCatalog, null, 1));
writeFileSync(join(GENERATED, 'catalog.full.json'), JSON.stringify(fullCatalog, null, 1));

const living = rooms.find((r) => r.id === 'living-room');
const placeholders = living ? living.slots.reduce((n, s) => n + s.options.filter((o) => o.placeholder).length, 0) : 0;
console.log(
  [
    `catalog ${version} (${base.mode})`,
    `  products shown: ${publicProducts.length} (provisional prices: ${fullProducts.filter((p) => p.price_provisional).length})`,
    `  hidden: ${hidden.length}${hidden.length ? ' · ' + hidden.map((h) => `${h.id}: ${h.reason}`).join('; ') : ''}`,
    `  living-room slots: ${living?.slots.length ?? 0}, placeholder options: ${placeholders}`,
    `  shipping cost source: ${['manual', 'cj', 'default'].map((k) => `${k} ${fullProducts.filter((p) => p.shipping_source === k).length}`).join(', ')}`,
    `  economics defaults used: ${defaults_used.length ? defaults_used.join(', ') : 'none'}`,
    `  supplier images (FR-I): ${fullProducts.filter((p) => p.supplier_image.url).length} with a url · usage rights ${['confirmed', 'unclear', 'none']
      .map((r) => `${r} ${fullProducts.filter((p) => p.supplier_image.usage_rights === r).length}`)
      .join(', ')}`,
    `  fixed-product slots waiting for a card (F3): ${fixedWaiting.length ? fixedWaiting.join(', ') : 'none'}`,
    `  invalid product cards skipped: ${invalidCards.length}${invalidCards.length ? ' · ' + invalidCards.map((c) => `${c.path} (${c.issues})`).join('; ') : ''}`,
  ].join('\n'),
);
