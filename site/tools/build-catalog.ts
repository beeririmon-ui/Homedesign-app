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
  resolveShipping,
  initialPrice,
  highestComparableIls,
  shipForQtyCents,
  unitShipFromSaleCents,
  landedAgorot,
  noLossRetailIls,
  type FreightFiles,
  type FreightSource,
  type ShippingResolution,
  PublicCatalogSchema,
  resolveSettings,
  unitEconomics,
  usdToCents,
  ilsToAgorot,
  isDraftCard,
  onlyDraftIssues,
  type Availability,
  type DraftCard,
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
  cardRoom,
  roomFromPath,
  sellQtyDefault,
  unitPriceEstimateIls,
  publicSafety,
  optionIssues,
  skuCostCents,
  skuShippingCents,
  skuRetail,
  optionVariantId,
  type CardOptions,
  type FullVariant,
  type PublicOptions,
} from '@hd/shared';
import { REPO, GENERATED, repoPath, sitePath } from './lib/paths';
import { materialsHe, colorNameHe } from './lib/hebrew';
import { loadLeadRecords } from './lib/leads';
import { cachedFreight } from './lib/freight-cache';
import { latinLabels, lineName, lineOf, loadLineData, optionLabel, saleOf, setComposition } from './lib/lines';
import { latinPublicText, publicDescription } from './lib/public-text';
import { cjProductOf, singleSku, supplierSkuIssues } from './lib/supplier-skus';
import { publicId, publicVariantId, slugIndex } from '@hd/shared/product-url';

const STRICT = process.argv.includes('--strict-prices');
/** Rooms with a working room engine in this phase. Others are listed as "soon". */
const BUILT_ROOMS = new Set(['living-room']);
/**
 * Rooms whose slots and products are built (the same pricing path for every room). Default: the built rooms. The test
 * page (tools/make-test-page.ts) asks for more with --rooms living-room,dining-room and writes elsewhere with --out <name>
 * (.generated/catalog.<name>.public.json); a room outside BUILT_ROOMS keeps built: false (no room engine, no room page).
 */
const argOf = (flag: string): string | undefined => process.argv.find((a) => a.startsWith(`${flag}=`))?.slice(flag.length + 1);
const PRODUCT_ROOMS = new Set((argOf('--rooms') ?? [...BUILT_ROOMS].join(',')).split(',').filter(Boolean));
const OUT_NAME = argOf('--out') ?? null;
/**
 * --products=<manifest>: also build every card a story frame shows (the story layer, tools/make-story.ts reads
 * data/story/story.json; the path is from the site folder), through the same pricing path, outside the rooms' slot options:
 * every { product } of every points array, wherever the manifest holds it. A card's slot is the living room's slot of the
 * same id when there is one (the story frames are living rooms so far), else its own room's. Several manifests are
 * comma separated (S10: tools/house/*.json, the houses' cushion sets, sold through the same shop).
 */
const EXTRA_PRODUCTS = argOf('--products') ?? null;
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
// design notes §11.4 (2026-11-08): the designer's names win over the name composed from slot, material and colour;
// the story's names table (§4) the same. A composed name is the fallback, and stays marked provisional
const namesPath = repoPath('data/catalog/names-he.json');
const designerNames: Record<string, string> = {
  ...((readJson(repoPath('data/story/story.json')) as { names_he?: Record<string, string> }).names_he ?? {}),
  ...(existsSync(namesPath) ? ((readJson(namesPath) as { names_he?: Record<string, string> }).names_he ?? {}) : {}),
};
// S15 (master-designer, docs/proposals/your-room-copy-2026-11-11.md §3): the shop's Hebrew description per card id
// (names-he.json 1.2, description_he) wins over the one composed from the card's texture, materials and dimensions
const designerDescriptions: Record<string, string> = existsSync(namesPath)
  ? ((readJson(namesPath) as { description_he?: Record<string, string> }).description_he ?? {})
  : {};
// S15 (§2 row 5, §5): the slot's name as the site shows it, over the binding name in data/slots (which does not change)
const displayFile = sitePath('tools/display-he.json');
const slotNamesHe: Record<string, string> = existsSync(displayFile)
  ? ((readJson(displayFile) as { slot_names_he?: Record<string, string> }).slot_names_he ?? {})
  : {};
// S11 (QA S6–S7 ת8, ת12, ת9; the manager's sale decisions): the line's base name and the Hebrew option labels
// (master-designer's), the sale exclusions (data/catalog/sale-exclusions.json) and the sets of distinct SKUs (story.json
// set_axes). Each file is optional: without it the card's own label and the product's name stand (tools/lib/lines.ts)
const LABELS_FILE = repoPath('data/catalog/option-labels-he.json');
const lineData = loadLineData({
  labels: LABELS_FILE,
  names: namesPath,
  story: repoPath('data/story/story.json'),
  exclusions: repoPath('data/catalog/sale-exclusions.json'),
});
let excludedVariants = 0;
let setParts = 0;
/** S12: the sets whose card does not name the SKUs of their parts: not sold, and a list for sourcing */
const setsNeedSkus: { card: string; variant: string; reason: string }[] = [];
const tempCoords = readJson(sitePath('tools/temp/living-room.nordic.json')) as {
  slots: Record<string, { boxes: number[][]; hotspot: [number, number]; visible?: boolean; zoom?: number[] }>;
};

const settingsPath = repoPath('data/economics/settings.json');
const productsEconPath = repoPath('data/economics/products.json');
const settingsInput = existsSync(settingsPath) ? SettingsFileSchema.parse(readJson(settingsPath)) : null;
/** every freight file the studio reads (build.py FREIGHT_FILES), in its order */
const freights: FreightFiles = {};
for (const src of ['cj', 'zendrop', 'aliexpress'] as FreightSource[]) {
  const f = repoPath('data/economics', `freight-${src}.json`);
  if (existsSync(f)) freights[src] = FreightFileSchema.parse(readJson(f));
}
const productEcon: Record<string, ProductEconomics> = existsSync(productsEconPath) ? ProductEconomicsFileSchema.parse(readJson(productsEconPath)) : {};
const { settings, defaults_used } = resolveSettings(settingsInput);
/** the final round's record per card (the studio's starting price and freight for a card without a pricing row) */
const leads = loadLeadRecords(REPO);

/**
 * Slots on hold (PRE1): the owner's AU2 list (data/leads/.../round5/excluded-slots.json) and R6Q2 (status/decisions.json,
 * its `blocks` once answered "yes"). Shown "המלאי אינו זמין כעת" with the waiting list; nothing in them is sold.
 */
const onHold = new Map<string, { decision: string; note_he: string }>();
{
  const au2 = repoPath('data/leads/final-2026-10-13/round5/excluded-slots.json');
  if (existsSync(au2)) {
    const d = readJson(au2) as { decision?: string; slots?: string[] };
    for (const k of d.slots ?? []) onHold.set(k, { decision: d.decision ?? 'AU2', note_he: 'המלאי אינו זמין כעת' });
  }
  const decisionsPath = repoPath('status/decisions.json');
  if (existsSync(decisionsPath)) {
    const d = readJson(decisionsPath) as { decisions?: { id: string; status?: string; answer?: { option?: string } | null; blocks?: string[] }[] };
    const r6q2 = d.decisions?.find((x) => x.id === 'R6Q2');
    if (r6q2 && r6q2.status !== 'open' && r6q2.answer?.option === 'yes')
      for (const k of r6q2.blocks ?? []) onHold.set(k, { decision: 'R6Q2', note_he: 'המלאי אינו זמין כעת' });
  }
}

/** Cards that fail data/product-card.schema.json are reported and skipped (data/ is not ours to fix). */
const invalidCards: { path: string; issues: string }[] = [];
/** Cards the DS API left unfilled (shared/src/card-draft.ts): not a schema bug, listed for the sourcing-agent, not shown. */
const draftCards: DraftCard[] = [];
/** The studio's own prices (the owner's, the pricing file's, a per-SKU price) that lose on the site's reading: reported, never raised. */
const studioLosing: { id: string; variant_id: string; price_agorot: number; no_loss_agorot: number }[] = [];
/** derived prices the floor raised (SITE1): evidence for gate G8.2 */
let flooredVariants = 0;
let flooredUnits = 0;
/** Cards whose `options` alone are broken: the product is shown without its options, and the problem is reported. */
const invalidOptions: { path: string; issues: string }[] = [];
const cards: { card: ProductCard; path: string }[] = walk(repoPath('data/products')).flatMap((p) => {
  const raw = readJson(p) as Record<string, unknown>;
  let parsed = ProductCardSchema.safeParse(raw);
  if (!parsed.success && parsed.error.issues.every((i) => i.path[0] === 'options')) {
    invalidOptions.push({ path: relative(REPO, p), issues: parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; ') });
    const { options: _dropped, ...rest } = raw;
    parsed = ProductCardSchema.safeParse(rest);
  } else if (parsed.success && parsed.data.options) {
    const issues = optionIssues(parsed.data.options);
    if (issues.length) {
      invalidOptions.push({ path: relative(REPO, p), issues: issues.join('; ') });
      const { options: _dropped, ...rest } = parsed.data;
      parsed = ProductCardSchema.safeParse(rest);
    }
  }
  if (!parsed.success) {
    const paths = parsed.error.issues.map((i) => i.path.join('.'));
    if (isDraftCard(raw) && onlyDraftIssues(paths)) {
      draftCards.push({ path: relative(REPO, p), fields: [...new Set(paths)] });
      return [];
    }
    invalidCards.push({
      path: relative(REPO, p),
      issues: parsed.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`).join('; '),
    });
    return [];
  }
  return [{ card: parsed.data, path: relative(REPO, p) }];
});

/** Cards whose own `room` (card schema 1.1, Q2) disagrees with their folder: the card's room is used, and this is reported. */
const roomVsFolder = cards.flatMap(({ card, path }) => {
  const folder = roomFromPath(path);
  return folder !== null && folder !== card.room ? [`${path} (room ${card.room}, folder ${folder})`] : [];
});

// ---------- rooms and slots ----------
const SLOT_FILE_FOR: Record<string, string> = { living: 'living-room', 'kitchen-dining': 'dining-room' };
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

const daysOf = (d: string | null | undefined): [number, number] | null => {
  const m = /^(\d+)(?:-(\d+))?$/.exec(d ?? '');
  return m ? [Number(m[1]), Number(m[2] ?? m[1])] : null;
};
/**
 * `public` is null when the options collapse to one sold row (the others excluded, or set parts): the product is sold as
 * `:default`, and `full` still holds that row, so the supplier is asked for that option's SKU (QA ת27), never the card's
 * product-level SKU.
 */
type OptionsBuild = { public: PublicOptions | null; full: FullVariant[] } | null;

/** The product's resolved shipping, in the two numbers every scenario needs: one piece's freight and the sale's. */
type Freight = { unit_cents: number; sale_cents: number; quoted_for_sale: boolean };
function freightOf(ship: Extract<ShippingResolution, { ok: true }>, sellQty: number): Freight {
  if (ship.quoted_for_sale) return { unit_cents: unitShipFromSaleCents(ship.usd_cents, sellQty), sale_cents: ship.usd_cents, quoted_for_sale: true };
  return { unit_cents: ship.usd_cents, sale_cents: shipForQtyCents(ship.usd_cents, sellQty), quoted_for_sale: false };
}
const landedOf = (costCents: number, shipCents: number, q: number) =>
  landedAgorot({ cost_usd_cents: costCents, shipping_usd_cents: shipCents, fx_usd_ils: settings.fx_usd_ils, sell_qty: q, shipping_quoted_for_sale: true });
const noLossOf = (landed: number) => ilsToAgorot(noLossRetailIls(landed / 100, settings));

/**
 * Every option of the supplier (card `options`) as variants with their own price: the room's SKU is the product
 * (its price, cost and shipping), the others go through the same economics (shared/src/options.ts). The public form is
 * compact (the catalog ships in the JS bundle); variant ids are derived from the value ids (optionVariantId).
 * No option is sold under its own no-loss price (SITE1): a derived price is floored there; a price the studio set by
 * hand (sku_retail_ils) is never raised, it is reported.
 */
function buildOptions(
  card: ProductCard,
  o: CardOptions,
  p: {
    retail: number;
    provisional: boolean;
    studioRetailIls: number | null;
    cost: number;
    freight: Freight;
    sellQty: number;
    pack: FullProduct['pack'];
    unitLanded: number | null;
    unitNoLoss: number | null;
    days: [number, number] | null;
    /** the product's name: the line's base when the designer has none (ת8 fallback) */
    name: string;
  },
  econ: ProductEconomics,
): OptionsBuild {
  const dflt = o.skus.find((s) => s.id === o.default_sku);
  if (!dflt || dflt.price.currency !== 'USD') return null;
  const dfltCents = usdToCents(dflt.price.amount);
  const valueOf = (axis: CardOptions['axes'][number], s: CardOptions['skus'][number]) => axis.values.find((v) => v.id === s.values[axis.id])!;
  // ת12: the designer's Hebrew label of a value, else the card's
  const labelOf = (axis: CardOptions['axes'][number], v: CardOptions['axes'][number]['values'][number]) =>
    optionLabel(lineData, card.id, axis.id, v.id, v.label_he);
  // ת9: a set of distinct SKUs (a triptych) is the default SKU's value on its axis; the other values are its parts
  const set = lineData.sets[card.id] ?? null;
  const setValue = set ? ((dflt.values as Record<string, string>)[set.axis] ?? null) : null;

  const full: FullVariant[] = [];
  const rows: {
    s: CardOptions['skus'][number];
    retail: number;
    provisional: boolean;
    unit: number | null;
    days: [number, number] | null;
    available: boolean;
  }[] = [];
  const n = p.sellQty;
  for (const s of o.skus) {
    const isDefault = s === dflt;
    if (s.price.currency !== 'USD') continue;
    const cost = isDefault ? p.cost : skuCostCents(p.cost, dfltCents, usdToCents(s.price.amount));
    // the supplier's own difference between this SKU and the room's moves both one piece's freight and the sale's
    const unitShip = isDefault ? p.freight.unit_cents : skuShippingCents(p.freight.unit_cents, dflt.shipping_il, s.shipping_il);
    const delta = unitShip - p.freight.unit_cents;
    const saleShip = isDefault
      ? p.freight.sale_cents
      : p.freight.quoted_for_sale
        ? Math.max(0, p.freight.sale_cents + n * delta)
        : shipForQtyCents(unitShip, n);
    const r = skuRetail(
      {
        is_default: isDefault,
        product_retail_agorot: p.retail,
        product_price_provisional: p.provisional,
        studio_retail_ils: p.studioRetailIls,
        sku_override_ils: econ.sku_retail_ils?.[s.id] ?? null,
        cost_usd_cents: cost,
        shipping_usd_cents: unitShip,
        default_cost_usd_cents: p.cost,
        default_shipping_usd_cents: p.freight.unit_cents,
        fx_usd_ils: settings.fx_usd_ils,
        sell_qty: n,
        strict: STRICT,
      },
      settings,
    );
    if (!r) continue; // strict build: an option without a studio price is not sold
    // the floor (SITE1): the option's own landed cost in the sale's units, and the lowest price that does not lose there
    const landed = isDefault ? landedOf(p.cost, p.freight.sale_cents, n) : landedOf(cost, saleShip, n);
    const noLoss = noLossOf(landed);
    const studioSet = isDefault || (typeof econ.sku_retail_ils?.[s.id] === 'number' && econ.sku_retail_ils[s.id]! > 0);
    let retail = r.retail_agorot;
    let floored = false;
    if (retail < noLoss) {
      if (studioSet) {
        if (!isDefault)
          studioLosing.push({
            id: card.id,
            variant_id: optionVariantId(
              card.id,
              o.axes.map((a) => s.values[a.id]!),
            ),
            price_agorot: retail,
            no_loss_agorot: noLoss,
          });
      } else {
        retail = noLoss;
        floored = true;
        flooredVariants++;
      }
    }
    // P1: one piece of a set, per option (the room's keeps the product's unit price), floored at one piece's own no-loss
    let unit: number | null = null;
    let unitLanded: number | null = null;
    let unitNoLoss: number | null = null;
    let unitFloored = false;
    if (p.pack) {
      if (isDefault) {
        unit = p.pack.unit_price_agorot;
        unitLanded = p.unitLanded;
        unitNoLoss = p.unitNoLoss;
      } else {
        unitLanded = landedOf(cost, unitShip, 1);
        unitNoLoss = noLossOf(unitLanded);
        unit = ilsToAgorot(unitPriceEstimateIls(retail / 100, n));
        if (unit < unitNoLoss) {
          unit = unitNoLoss;
          unitFloored = true;
          flooredUnits++;
        }
      }
    }
    const id = optionVariantId(
      card.id,
      o.axes.map((a) => s.values[a.id]!),
    );
    if (id.length > 160) throw new Error(`${card.id}: variant id longer than the cart accepts: ${id}`);
    const available = isDefault || s.stock === undefined || s.stock === null || s.stock > 0;
    // the manager's decisions: an excluded value is not offered; a print of a triptych other than the set's is part of it
    const sale = saleOf(lineData, card.id, s.values, setValue);
    if (sale.excluded && isDefault) throw new Error(`${card.id}: the room's SKU ${s.id} is excluded from sale (data/catalog/sale-exclusions.json)`);
    if (sale.excluded) excludedVariants++;
    if (sale.set_part) setParts++;
    // ת8: the line names what was bought (a set's own axis, which print, is not a choice, so it is not in the line)
    const line = lineOf(lineData, card, s.values, p.name);
    // S12 (S11 question 2): the set's parts at the supplier, one of each (the supplier order expands the set into them)
    const comp =
      set && !sale.set_part
        ? setComposition(
            set,
            o.axes.find((a) => a.id === set.axis),
            o.skus as { id: string; values: Record<string, string> }[],
            s as { id: string; values: Record<string, string> },
            n,
          )
        : null;
    if (comp?.incomplete)
      setsNeedSkus.push({
        card: card.id,
        variant: optionVariantId(
          card.id,
          o.axes.map((a) => s.values[a.id]!),
        ),
        reason: comp.incomplete,
      });
    full.push({
      id,
      label_he: o.axes.map((a) => `${a.name_he}: ${labelOf(a, valueOf(a, s))}`).join(', '),
      option_label_he: line.label,
      line_name_he: line.base,
      set_part: sale.set_part,
      set_skus: comp?.skus ?? null,
      set_incomplete: comp?.incomplete ?? null,
      sale_excluded: sale.excluded,
      supplier_sku: s.id,
      cost_usd_cents: cost,
      shipping_usd_cents: saleShip,
      unit_shipping_usd_cents: unitShip,
      retail_agorot: retail,
      unit_retail_agorot: unit,
      price_provisional: r.provisional,
      unit_price_estimated: p.pack ? (isDefault ? p.pack.unit_price_estimated : true) : false,
      price_floored: floored,
      unit_price_floored: unitFloored,
      landed_agorot: landed,
      no_loss_agorot: noLoss,
      unit_landed_agorot: unitLanded,
      unit_no_loss_agorot: unitNoLoss,
      active: available && !sale.excluded,
      in_room: isDefault,
      supplier_image_url: s.image && /^https:\/\//.test(s.image) ? s.image : null,
    });
    // not offered: neither on the product page nor on a story page (the server refuses it too: inactive, or a set part)
    if (sale.excluded || sale.set_part) continue;
    const days = daysOf(s.shipping_il?.days);
    rows.push({
      s,
      retail,
      provisional: r.provisional,
      unit,
      days: days && (!p.days || days[0] !== p.days[0] || days[1] !== p.days[1]) ? days : null,
      available,
    });
  }
  if (new Set(full.map((v) => v.id)).size !== full.length) throw new Error(`${card.id}: two options share a variant id`);
  if (rows.length < 2) return { public: null, full };
  // the room's option first in the variants (the default everywhere); the public list keeps the supplier's order
  full.sort((a, b) => Number(b.in_room) - Number(a.in_room));
  const axes = o.axes.map((a) => ({ a, values: a.values.filter((v) => rows.some((r) => r.s.values[a.id] === v.id)) }));
  const pv = rows.filter((r) => r.provisional).length * 2 >= rows.length;
  return {
    public: {
      axes: axes.map(({ a, values }) => ({
        id: a.id,
        name_he: a.name_he,
        values: values.map((v) => [v.id, labelOf(a, v), v.hex ?? null] as [string, string, string | null]),
      })),
      v: rows.map((r) => axes.map(({ a, values }) => values.findIndex((v) => v.id === r.s.values[a.id]))),
      p: rows.map((r) => r.retail),
      room: rows.findIndex((r) => r.s === dflt),
      off: rows.flatMap((r, i) => (r.available ? [] : [i])),
      pv,
      px: rows.flatMap((r, i) => (r.provisional !== pv ? [i] : [])),
      u: p.pack ? rows.map((r) => r.unit!) : null,
      d: rows.some((r) => r.days) ? rows.map((r) => r.days) : null,
    },
    full,
  };
}

function buildProduct(card: ProductCard, path: string, roomId: string, slot: Slot, fillerNames: string[]): FullProduct | HiddenProduct {
  const econ = productEcon[card.id];
  const lead = leads.get(card.id) ?? null;
  // units per sale: the studio's sell_qty, else the studio's own default rule (studio/build.py sell_qty_default)
  const qtyDefault = sellQtyDefault(card, slot, lead);
  const sellQty = econ?.sell_qty ?? qtyDefault.qty;
  // the cost of the whole sale from the pricing file (sale_cost_usd, 2026-10-18: a shade with its suspension set), per
  // unit sold; else the card's cost. The row's shipping_cost_usd is then shipping only (the studio reads it the same way)
  const saleCost = typeof econ?.sale_cost_usd === 'number' && econ.sale_cost_usd > 0 ? econ.sale_cost_usd : null;
  const cost = usdToCents(saleCost !== null ? saleCost / sellQty : card.price.currency === 'USD' ? card.price.cost : NaN);
  if (!Number.isFinite(cost)) return { id: card.id, slot: slot.id, reason: `price.currency ${card.price.currency} is not USD` };
  // the shipping line, in the studio's order; a product without one is not priced (no default figure, SITE1)
  const cjEntry = freights.cj?.products[card.id] as { pid?: string; vid?: string } | undefined;
  const ship = resolveShipping({ id: card.id, card, row: econ, freights, cache: cachedFreight(REPO, card, cjEntry), lead, sellQty });
  if (!ship.ok)
    return {
      id: card.id,
      slot: slot.id,
      reason: ship.reason === 'no_route' ? `no shipping to Israel (${ship.source})` : 'no shipping line in the studio, the card or the final round',
    };
  const freight = freightOf(ship, sellQty);
  // the price: the studio's (the owner's, the pricing file's), else the card's or the final round's starting price,
  // marked provisional; never a margin-target price (SITE1)
  const price0 = initialPrice(card, econ, lead);
  if (!price0) return { id: card.id, slot: slot.id, reason: 'no price: not in data/economics/products.json, the card or the final round' };
  if (STRICT && price0.source !== 'owner' && price0.source !== 'studio')
    return { id: card.id, slot: slot.id, reason: 'no retail_ils in data/economics/products.json' };
  const provisional = price0.source === 'initial-card' || price0.source === 'initial-leads';
  let retail = ilsToAgorot(price0.retail_ils);
  const landed = landedOf(cost, freight.sale_cents, sellQty);
  const noLoss = noLossOf(landed);
  if (retail < noLoss) {
    if (provisional)
      retail = noLoss; // a starting price that loses is floored like any derived price
    else if (!ship.express_only) {
      // an express-only product is not sold at all (NL2), so its headline is not a finding
      studioLosing.push({ id: card.id, variant_id: `${card.id}:default`, price_agorot: retail, no_loss_agorot: noLoss });
      if (STRICT)
        return { id: card.id, slot: slot.id, reason: `the studio's price ₪${price0.retail_ils} loses on the site's reading (no-loss ₪${noLoss / 100})` };
    }
  }
  const fulfillment = econ?.fulfillment_source ?? 'dropship_cj';
  const materials = materialsHe(card.materials);
  const color = colorNameHe(card.colors.dominant_hex);
  const named = designerNames[card.id];
  // ת8: the line names the default SKU by its Hebrew labels (a set's own axis aside); a product the designer has not
  // named takes its base name and that label (the line rule), else the name composed from slot, material and colour
  const set = lineData.sets[card.id] ?? null;
  const dfltSku = card.options?.skus.find((k) => k.id === card.options!.default_sku) ?? null;
  const dfltLine = lineOf(lineData, card, (dfltSku?.values ?? {}) as Record<string, string>, '');
  const dfltLabel = dfltSku ? (dfltLine.label ?? '') : '';
  const base = lineData.base[card.id] ?? null;
  // S15: the slot as the site names it (tools/display-he.json), never a catalog tag such as "(סט)"
  const slotName = slotNamesHe[`${roomId}/${slot.id}`] ?? slot.name_he;
  const name_he = named ?? (base ? lineName(base, dfltLabel) : `${slotName}${materials[0] ? ` ${materials[0]}` : ''}, ${color}`);
  const d = card.dimensions_cm ?? {};
  const dims = [d.width, d.depth, d.height].filter((x): x is number => typeof x === 'number');
  // S14, QA ת33: the card's data only (its texture when that is a public sentence, materials, dimensions), never its notes
  const description = publicDescription(card, materials, dims, '');
  const retailIls = retail / 100;
  const compare = typeof econ?.compare_at_ils === 'number' && econ.compare_at_ils > retailIls ? ilsToAgorot(econ.compare_at_ils) : null;
  // P1: a set (sell_qty > 1) is also sold as one piece. Unit price from the studio, else an estimate (marked as such),
  // floored at one piece's own no-loss price; the studio's unit price is never raised, only reported
  const unitLanded = sellQty > 1 ? landedOf(cost, freight.unit_cents, 1) : null;
  const unitNoLoss = unitLanded === null ? null : noLossOf(unitLanded);
  let unitIls: number | null = null;
  let unitEstimated = false;
  let unitFloored = false;
  // ת9 (SET1): a set of distinct SKUs (a triptych) has no single piece: one print is not sold on its own
  if (sellQty > 1 && !set) {
    if (typeof econ?.unit_retail_ils === 'number' && econ.unit_retail_ils > 0) {
      unitIls = econ.unit_retail_ils;
      if (ilsToAgorot(unitIls) < unitNoLoss!)
        studioLosing.push({ id: card.id, variant_id: `${card.id}:default/unit`, price_agorot: ilsToAgorot(unitIls), no_loss_agorot: unitNoLoss! });
    } else {
      unitIls = unitPriceEstimateIls(retailIls, sellQty);
      unitEstimated = true;
      if (ilsToAgorot(unitIls) < unitNoLoss!) {
        unitIls = unitNoLoss! / 100;
        unitFloored = true;
        flooredUnits++;
      }
    }
  }
  const pack = unitIls === null ? null : { set_qty: sellQty, unit_price_agorot: ilsToAgorot(unitIls), unit_price_estimated: unitEstimated };
  const safety = publicSafety(card.safety);
  const opts = card.options
    ? buildOptions(
        card,
        card.options,
        {
          retail,
          provisional,
          studioRetailIls: price0.source === 'owner' || price0.source === 'studio' ? price0.retail_ils : null,
          cost,
          freight,
          sellQty,
          pack,
          unitLanded,
          unitNoLoss,
          days: shippingDays(card),
          name: name_he,
        },
        econ ?? {},
      )
    : null;
  const defaultVariant: FullVariant = {
    id: `${card.id}:default`,
    label_he: 'ברירת מחדל',
    option_label_he: null,
    // one SKU sold (no options, or the others excluded): the line still names it, by the default SKU's labels
    line_name_he: lineOf(lineData, card, (dfltSku?.values ?? {}) as Record<string, string>, name_he).line,
    set_part: false,
    sale_excluded: null,
    // S14, QA ת27: the variant's SKU, never the supplier's product-level code (a CJ product of one variant: that variant's)
    supplier_sku: card.options ? (card.supplier.sku ?? null) : singleSku(card, cjProductOf(REPO, card)).sku,
    cost_usd_cents: cost,
    shipping_usd_cents: freight.sale_cents,
    unit_shipping_usd_cents: freight.unit_cents,
    retail_agorot: retail,
    unit_retail_agorot: pack?.unit_price_agorot ?? null,
    price_provisional: provisional,
    unit_price_estimated: pack?.unit_price_estimated ?? false,
    price_floored: false,
    unit_price_floored: unitFloored,
    landed_agorot: landed,
    no_loss_agorot: noLoss,
    unit_landed_agorot: unitLanded,
    unit_no_loss_agorot: unitNoLoss,
    active: true,
    in_room: true,
    supplier_image_url: null,
  };
  // QA ת27: options that collapse to one sold row are sold as `:default`, carrying that row's supplier SKU (and a set's
  // parts), never the card's product-level SKU: the supplier must be told which option to send
  const collapsed = opts && !opts.public ? (opts.full.find((v) => !v.sale_excluded && !v.set_part) ?? null) : null;
  if (collapsed) {
    defaultVariant.supplier_sku = collapsed.supplier_sku;
    defaultVariant.set_skus = collapsed.set_skus ?? null;
    defaultVariant.set_incomplete = collapsed.set_incomplete ?? null;
  }
  const variantsFull = opts?.public ? opts.full : [defaultVariant];
  // NL2 (2026-11-03): the no-loss price more than twice the highest Israeli comparable, or express only: not sold,
  // shown "המלאי אינו זמין כעת" with the waiting list (PRE1); the stored price stays. A slot on hold (AU2, R6Q2) too.
  const highest = highestComparableIls(econ);
  const hold = onHold.get(`${roomId}/${slot.id}`);
  const [availability, availabilityNote]: [Availability, string | null] = hold
    ? [{ status: 'unavailable', reason: 'slot-on-hold' }, `העמדה בהמתנה (${hold.decision}): ${hold.note_he}`]
    : ship.express_only
      ? [{ status: 'unavailable', reason: 'nl2-express-only' }, 'הספק שולח רק באקספרס; לא נמכר עד שיש מקור זול יותר (NL2)']
      : highest !== null && noLoss > ilsToAgorot(highest) * 2
        ? [
            { status: 'unavailable', reason: 'nl2-above-market' },
            `המחיר שלא מפסיד (₪${noLoss / 100}) גבוה מפי 2 מההשוואה הגבוהה בישראל (₪${highest}); לא נמכר עד שיש מקור זול יותר (NL2)`,
          ]
        : [{ status: 'available', reason: null }, null];
  return {
    id: card.id,
    room: roomId,
    slot: slot.id,
    name_he,
    name_provisional: !named && !base,
    description_he: designerDescriptions[card.id] ?? (description || `${slotName}.`),
    price_agorot: retail,
    compare_at_agorot: compare,
    price_provisional: provisional,
    materials_he: materials,
    dimensions_cm: { width: d.width ?? null, depth: d.depth ?? null, height: d.height ?? null },
    color_hex: card.colors.dominant_hex,
    shipping_days: shippingDays(card) ?? ship.days,
    notes_he: productNotes(slot, fillerNames, { wiredInSafety: safety?.power === 'wired', packChoice: pack !== null }),
    set_of: slot.set_of ?? null,
    variants: variantsFull.map((v) => ({ id: v.id, label_he: v.label_he })),
    pack,
    safety,
    options: opts?.public ?? null,
    availability,
    variants_full: variantsFull,
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
    shipping_usd_cents: ship.usd_cents,
    shipping_quoted_for_sale: ship.quoted_for_sale,
    shipping_source: ship.source,
    shipping_line: ship.line,
    price_source: price0.source,
    landed_agorot: landed,
    no_loss_agorot: noLoss,
    highest_comparable_agorot: highest === null ? null : ilsToAgorot(highest),
    availability_note_he: availabilityNote,
    sell_qty: sellQty,
    sell_qty_source: typeof econ?.sell_qty === 'number' ? 'studio' : 'default',
    sell_qty_sure: typeof econ?.sell_qty === 'number' || qtyDefault.sure,
    sell_qty_reason: typeof econ?.sell_qty === 'number' ? null : qtyDefault.reason,
    unit_economics: pack
      ? unitEconomics(
          { retail_agorot: pack.unit_price_agorot, cost_usd_cents: cost, shipping_usd_cents: freight.unit_cents, fx_usd_ils: settings.fx_usd_ils, sell_qty: 1 },
          settings,
        )
      : null,
    fulfillment_source: fulfillment,
    fx_usd_ils: settings.fx_usd_ils,
    nordic_score: card.style_scores?.[STYLE]?.score ?? null,
    economics: unitEconomics(
      {
        retail_agorot: retail,
        cost_usd_cents: cost,
        shipping_usd_cents: ship.usd_cents,
        fx_usd_ils: settings.fx_usd_ils,
        sell_qty: sellQty,
        shipping_quoted_for_sale: ship.quoted_for_sale,
      },
      settings,
    ),
  };
}

for (const hr of house.rooms) {
  if (!hr.slots_file) continue;
  const roomId = roomIdOf(hr.id);
  const slotsPath = repoPath('data/slots', `${roomId}.json`);
  const built = PRODUCT_ROOMS.has(roomId) && existsSync(slotsPath);
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
    // Only designer-scored, non-rejected cards of this room's slot qualify (card `room`, folder as fallback); best Nordic score first.
    const candidates = cards
      .filter(({ card, path }) => card.slot === slot.id && cardRoom(card, path) === roomId && card.status !== 'rejected')
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
        label_he: p ? p.name_he : `גרסה ${i + 1} · ממתינה למוצר`,
        is_default: i === 0,
      };
    });
    const temp = tempCoords.slots[slot.id];
    const fromFile = hotspotFromFile(slot, frame);
    const hotspot = fromFile ? fromFile : temp ? { u: temp.hotspot[0], v: temp.hotspot[1], provisional: true, visible: temp.visible !== false } : null;
    const zoomFromFile = Array.isArray(slot.zoom_frame) && slot.zoom_frame.length === 4 ? (slot.zoom_frame as [number, number, number, number]) : null;
    const hold = onHold.get(`${roomId}/${slot.id}`) ?? null;
    slots.push({
      id: slot.id,
      name_he: slotNamesHe[`${roomId}/${slot.id}`] ?? slot.name_he,
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
      on_hold: hold,
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
    // the room engine exists only for BUILT_ROOMS; a room built here for its products only (the test page) is not "built"
    built: BUILT_ROOMS.has(roomId),
  });
}

if (EXTRA_PRODUCTS) {
  const found: string[] = [];
  const collect = (x: unknown): void => {
    if (Array.isArray(x)) x.forEach(collect);
    else if (x && typeof x === 'object')
      for (const [k, v] of Object.entries(x)) {
        if (k === 'points' && Array.isArray(v))
          for (const p of v) if (typeof (p as { product?: unknown })?.product === 'string') found.push((p as { product: string }).product);
        collect(v);
      }
  };
  // several manifests, comma separated (S10: the story, and the houses' cushion sets in tools/house/)
  for (const m of EXTRA_PRODUCTS.split(',').filter(Boolean)) collect(readJson(sitePath(m)));
  const wanted = [...new Set(found)];
  const built = new Set([...fullProducts.map((p) => p.id), ...hidden.map((h) => h.id)]);
  const slotsOf = (room: string) => {
    const f = repoPath('data/slots', `${room}.json`);
    return existsSync(f) ? SlotsFileSchema.parse(readJson(f)).slots : [];
  };
  const living = slotsOf('living-room');
  for (const id of wanted) {
    if (built.has(id)) continue;
    const c = cards.find((x) => x.card.id === id);
    const slot = c ? (living.find((s) => s.id === c.card.slot) ?? slotsOf(cardRoom(c.card, c.path) ?? '').find((s) => s.id === c.card.slot)) : undefined;
    if (!c || !slot) {
      const draft = draftCards.some((d) => d.path.endsWith(`/${id}.json`));
      const reason = c
        ? `no slot ${c.card.slot} in the living room or the card's room`
        : draft
          ? 'draft card (DS API: colors and visual_weight unfilled)'
          : 'no valid product card';
      hidden.push({ id, slot: c?.card.slot ?? '', reason });
      continue;
    }
    const p = buildProduct(c.card, c.path, 'living-room', slot, []);
    if ('reason' in p) hidden.push(p);
    else fullProducts.push(p);
    built.add(id);
  }
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

// S7: neutral public ids end to end. Everything built above speaks card ids; from here on the public id (the card's
// slug) is the product's id and the prefix of its variants' ids, in both catalogs, the rooms' options and the seed.
// The full catalog keeps the card id in `card_id` (the supplier side); `hidden` stays in card ids (never public).
slugIndex(fullProducts.map((p) => p.id));
for (const p of fullProducts) {
  const card = p.id;
  p.card_id = card;
  p.id = publicId(card);
  p.variants = p.variants.map((v) => ({ ...v, id: publicVariantId(card, v.id) }));
  if (p.variants_full) p.variants_full = p.variants_full.map((v) => ({ ...v, id: publicVariantId(card, v.id) }));
}
for (const r of rooms) for (const s of r.slots) for (const o of s.options) if (o.product_id) o.product_id = publicId(o.product_id);
for (const x of studioLosing) x.variant_id = x.variant_id.replace(/^[^:]+/, (c) => publicId(c));

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
  // with options, the room's variant only: the others are derived from `options` (optionVariantId)
  variants: p.options ? p.variants.slice(0, 1) : p.variants,
  pack: p.pack,
  safety: p.safety,
  options: p.options,
  availability: p.availability,
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
  invalid_options: invalidOptions,
  draft_cards: draftCards,
  studio_prices_losing: studioLosing,
  economics: {
    settings,
    defaults_used,
    sources: {
      settings: settingsInput ? 'data/economics/settings.json' : null,
      products: Object.keys(productEcon).length ? 'data/economics/products.json' : null,
      freight: Object.keys(freights).length
        ? Object.keys(freights)
            .map((s) => `data/economics/freight-${s}.json`)
            .join(', ')
        : null,
    },
  },
};

mkdirSync(GENERATED, { recursive: true });
const outName = OUT_NAME ? `catalog.${OUT_NAME}` : 'catalog';
writeFileSync(join(GENERATED, `${outName}.public.json`), JSON.stringify(publicCatalog, null, 1));
writeFileSync(join(GENERATED, `${outName}.full.json`), JSON.stringify(fullCatalog, null, 1));

const living = rooms.find((r) => r.id === 'living-room');
const placeholders = living ? living.slots.reduce((n, s) => n + s.options.filter((o) => o.placeholder).length, 0) : 0;
console.log(
  [
    `catalog ${version} (${base.mode}${OUT_NAME ? `, ${outName}` : ''}; rooms ${[...PRODUCT_ROOMS].join(', ')})`,
    `  products shown: ${publicProducts.length} (provisional prices: ${fullProducts.filter((p) => p.price_provisional).length})`,
    `  hidden: ${hidden.length}${hidden.length ? ' · ' + hidden.map((h) => `${h.id}: ${h.reason}`).join('; ') : ''}`,
    `  living-room slots: ${living?.slots.length ?? 0}, placeholder options: ${placeholders}`,
    `  shipping line source: ${['manual', 'cj', 'zendrop', 'aliexpress', 'card', 'cache', 'leads'].map((k) => `${k} ${fullProducts.filter((p) => p.shipping_source === k).length}`).join(', ')} (no default figure)`,
    `  price source: ${['owner', 'studio', 'initial-card', 'initial-leads'].map((k) => `${k} ${fullProducts.filter((p) => p.price_source === k).length}`).join(', ')}`,
    `  no-loss floor (SITE1): ${flooredVariants} option prices and ${flooredUnits} single-piece prices raised to their own no-loss price; studio prices that lose on the site's reading: ${studioLosing.length}${studioLosing.length ? ' · ' + studioLosing.map((x) => `${x.variant_id} ₪${x.price_agorot / 100} < ₪${x.no_loss_agorot / 100}`).join('; ') : ''}`,
    `  not sold (PRE1): ${['nl2-above-market', 'nl2-express-only', 'slot-on-hold'].map((k) => `${k} ${fullProducts.filter((p) => p.availability.reason === k).length}`).join(', ')}; slots on hold: ${[...onHold.keys()].join(', ') || 'none'}`,
    `  economics defaults used: ${defaults_used.length ? defaults_used.join(', ') : 'none'}`,
    `  supplier images (FR-I): ${fullProducts.filter((p) => p.supplier_image.url).length} with a url · usage rights ${['confirmed', 'unclear', 'none']
      .map((r) => `${r} ${fullProducts.filter((p) => p.supplier_image.usage_rights === r).length}`)
      .join(', ')}`,
    `  fixed-product slots waiting for a card (F3): ${fixedWaiting.length ? fixedWaiting.join(', ') : 'none'}`,
    `  supplier options (2026-10-11): ${fullProducts.filter((p) => p.options).length} products with options, ${fullProducts.reduce((n, p) => n + (p.options?.v.length ?? 0), 0)} SKUs${
      invalidOptions.length ? ` · options dropped (invalid): ${invalidOptions.map((c) => `${c.path} (${c.issues})`).join('; ')}` : ''
    }`,
    `  card room vs folder: ${roomVsFolder.length ? `${roomVsFolder.length} disagree (card room used) · ${roomVsFolder.join('; ')}` : 'all agree'}`,
    `  invalid product cards skipped: ${invalidCards.length}${invalidCards.length ? ' · ' + invalidCards.map((c) => `${c.path} (${c.issues})`).join('; ') : ''}`,
    `  draft cards (DS API, colors and visual_weight unfilled; for the sourcing-agent, not shown): ${draftCards.length}${draftCards.length ? ' · ' + draftCards.map((c) => c.path).join('; ') : ''}`,
  ].join('\n'),
);

// S11, QA S6–S7 ת12: no public label is in the supplier's English. Once the designer's labels exist, a label (an option,
// an axis, a line) with Latin letters fails the build; a unit after a number (3000K) is the one exception
const latin = latinLabels(publicCatalog, fullCatalog);
console.log(
  `  lines (ת8): base names ${Object.keys(lineData.base).length}, Hebrew labels ${lineData.labels ? Object.keys(lineData.labels).length : 0} cards; not offered (sale-exclusions): ${excludedVariants} variants; parts of a set (not sold alone): ${setParts} variants; Latin in public labels: ${latin.length}`,
);
if (latin.length && existsSync(LABELS_FILE)) {
  console.error(
    `build-catalog: ${latin.length} public labels carry Latin letters (ת12):\n${latin.map((x) => `  ${x.product} · ${x.where}: ${x.text}`).join('\n')}`,
  );
  process.exit(1);
}

// S14, QA ת33: no public name, description or product note in Latin (the studio's notes never reach the page); a unit
// after a number and a standard's mark (CE) are the exceptions
const latinText = latinPublicText(publicCatalog.products);
// S14, QA ת27: every variant sold from a card with supplier options carries one of the card's option SKUs (the very
// option sold), never the card's product-level SKU
const cardById = new Map(cards.map((c) => [c.card.id, c.card]));
const skuIssues = supplierSkuIssues(fullCatalog.products, (p) => {
  const card = cardById.get(p.card_id ?? p.id);
  return card && { ...card, product_level_sku: cjProductOf(REPO, card)?.productSku ?? null };
});
const resolvedSkus = fullCatalog.products.filter((p) => {
  const card = cardById.get(p.card_id ?? p.id);
  return card && !card.options && singleSku(card, cjProductOf(REPO, card)).resolved;
});
console.log(
  `  public text (ת33): Latin in ${latinText.length} names, descriptions or notes · supplier SKUs (ת27): ${skuIssues.length} issues; ` +
    `a single variant's SKU in place of the card's product-level code: ${resolvedSkus.map((p) => `${p.card_id} → ${p.variants_full?.[0]?.supplier_sku}`).join(', ') || 'none'}`,
);
if (latinText.length) {
  console.error(
    `build-catalog: ${latinText.length} public texts carry Latin letters (ת33):\n${latinText.map((x) => `  ${x.product} · ${x.where}: ${x.text}`).join('\n')}`,
  );
  process.exit(1);
}
if (skuIssues.length) {
  console.error(
    `build-catalog: ${skuIssues.length} sold variants would ask the supplier for the wrong SKU (ת27):\n${skuIssues.map((x) => `  ${x.variant} (${x.card}): ${x.supplier_sku ?? 'none'}, ${x.why}`).join('\n')}`,
  );
  process.exit(1);
}

// S12 (S11 question 2): every set of distinct SKUs, sold or not (a hidden draft card too): its parts' SKUs at each size,
// or what sourcing has to name. A set without them is refused by the server (set_unavailable), never sent as N × one SKU.
const setsReport = Object.entries(lineData.sets).map(([cardId, set]) => {
  // a draft or invalid card is not in `cards`: the report reads it from its file (it is listed, not sold)
  const c =
    cards.find((x) => x.card.id === cardId)?.card ??
    (walk(repoPath('data/products'))
      .map((f) => {
        try {
          return readJson(f) as { id?: string; options?: unknown };
        } catch {
          return null;
        }
      })
      .find((x) => x?.id === cardId) as ProductCard | undefined);
  const o = c?.options as CardOptions | undefined;
  if (!c || !o) return { card: cardId, axis: set.axis, sold_here: false, sets: [], need: 'the card or its options are missing' };
  const axis = o.axes.find((a) => a.id === set.axis);
  const others = o.skus.filter((s) => {
    const own = set.parts?.[0] ?? (o.skus.find((x) => x.id === o.default_sku)?.values as Record<string, string> | undefined)?.[set.axis];
    return (s.values as Record<string, string>)[set.axis] === own;
  });
  const size = (productEcon[cardId]?.sell_qty as number | undefined) ?? fullProducts.find((p) => p.source_path.endsWith(`/${cardId}.json`))?.sell_qty ?? 3;
  const sets = others.map((s) => {
    const r = setComposition(set, axis, o.skus as { id: string; values: Record<string, string> }[], s as { id: string; values: Record<string, string> }, size);
    return { sku: s.id, values: s.values, parts: r.skus, incomplete: r.incomplete };
  });
  const need = sets.find((x) => x.incomplete)?.incomplete ?? null;
  return { card: cardId, axis: set.axis, size, sold_here: fullProducts.some((p) => p.source_path.endsWith(`/${cardId}.json`)), sets, need };
});
writeFileSync(join(GENERATED, 'sets-composition.json'), JSON.stringify({ built_at: new Date().toISOString(), sets: setsReport }, null, 1));
console.log(
  `  sets of distinct SKUs (S12): ${setsReport.map((r) => `${r.card}: ${r.need ? `NOT SOLD, sourcing to name the parts (${r.need})` : `${r.sets.length} sizes, ${r.size} SKUs each`}`).join('; ')}${
    setsNeedSkus.length ? ` · refused in this catalog: ${setsNeedSkus.length} set variants` : ''
  }`,
);
