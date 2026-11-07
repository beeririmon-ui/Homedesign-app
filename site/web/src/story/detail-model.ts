/**
 * Layer 2, "הפרט" (/story/<room>/<style>/p/<product>/): the pure part of the detail page. The data block
 * (tools/make-story.ts) lists the product's SKUs in this house; this module chooses between them with the site's own
 * picker rules (@hd/shared/options: a cascade, the first axis free, an out-of-stock option not offered), reads and writes
 * the choice in the address (?color=…&size=…, so a link can name an option), and says what the page shows for a SKU:
 * the close-up when QA let one in, else the supplier's photo of that option, else (for the option the story shows) the
 * product's part of the story frame, else nothing but the swatch. web/test/story-detail.test.ts holds it.
 */
import { pickSku, selectionOf, type PickerSku } from '@hd/shared/picker';

export type DImage = { src: string; srcset: string; w: number; h: number };
export type DCloseup = DImage & { alt_he: string; state: string; qa_key: string };
export type DAxis = { id: string; name_he: string; values: { id: string; label_he: string; hex: string | null }[] };
export type DSku = {
  key: string;
  values: Record<string, string>;
  label_he: string | null;
  variant_id: string | null;
  price_agorot: number | null;
  price_he: string | null;
  available: boolean;
  sellable: boolean;
  size_he: string | null;
  days: [number, number] | null;
  /** an index into DetailData.images */
  image: number | null;
  /** the photo is this option's own (else the listing's main photo, shown for the story's option) */
  image_of_option: boolean;
  closeup: DCloseup | null;
};
export type DetailData = {
  product: string;
  name_he: string;
  material_he: string | null;
  status: 'available' | 'unavailable' | 'unpriced';
  set_qty: number;
  style_he: string;
  axes: DAxis[];
  skus: DSku[];
  images: DImage[];
  story_key: string;
  crop: DImage | null;
  crop_title_he: string | null;
  marks_he: Record<string, string>;
};

/** the picker's rules see a SKU by its key (a product without a price has no variant id yet) */
const pool = (d: DetailData): (PickerSku & { sku: DSku })[] => d.skus.map((k) => ({ variant_id: k.key, values: k.values, available: k.available, sku: k }));
export const storySku = (d: DetailData): DSku => d.skus.find((k) => k.key === d.story_key) ?? d.skus[0]!;
export const selection = (d: DetailData, sku: DSku): Record<string, string> =>
  selectionOf(d.axes, { variant_id: sku.key, values: sku.values, available: sku.available });

/** the SKU after the customer chose `value` on axis `index` (the axes after it keep their value when they can) */
export function choose(d: DetailData, current: DSku, index: number, value: string): DSku {
  const r = pickSku(d.axes, pool(d), selection(d, current), index, value);
  // the picker does not offer an option out of stock; a choice that would land on one does not happen
  return r.sku?.available ? r.sku.sku : current;
}

/** ?color=…&size=… names a SKU; anything else (or nothing) is the option the story shows */
export function fromQuery(d: DetailData, search: string): DSku {
  if (!d.axes.length) return storySku(d);
  const q = new URLSearchParams(search);
  const want = Object.fromEntries(d.axes.map((a) => [a.id, q.get(a.id)]));
  return d.skus.find((k) => d.axes.every((a) => k.values[a.id] === want[a.id])) ?? storySku(d);
}
/** the address for a SKU: none for the story's own option */
export function toQuery(d: DetailData, sku: DSku): string {
  if (!d.axes.length || sku.key === d.story_key) return '';
  const q = new URLSearchParams();
  for (const a of d.axes) q.set(a.id, sku.values[a.id] ?? '');
  return `?${q.toString()}`;
}

export type Shown = { image: DImage | null; alt: string; caption: string; kind: 'supplier' | 'frame' | 'none' };
/** the main picture for a SKU (the close-up has its own figure) */
export function photoOf(d: DetailData, sku: DSku): Shown {
  const im = sku.image !== null ? (d.images[sku.image] ?? null) : null;
  if (im)
    return {
      image: im,
      alt: `צילום הספק: ${d.name_he}${sku.label_he && sku.key !== d.story_key ? `, ${sku.label_he}` : ''}`,
      caption: sku.label_he && d.axes.length && sku.image_of_option ? `צילום הספק, באפשרות ${sku.label_he}.` : 'צילום הספק.',
      kind: 'supplier',
    };
  if (sku.key === d.story_key && d.crop)
    return { image: d.crop, alt: `${d.name_he}, בפריים`, caption: `בפריים "${d.crop_title_he ?? ''}". צילום הספק עוד לא הורד לגרסת הבדיקה.`, kind: 'frame' };
  return { image: null, alt: '', caption: 'צילום הספק עוד לא הורד לגרסת הבדיקה.', kind: 'none' };
}
export const creditOf = (d: DetailData, sku: DSku): string => [d.material_he, sku.size_he, sku.price_he ?? 'המחיר עוד לא נקבע'].filter(Boolean).join(' · ');
/** why there is no add button: never a disabled one (art direction §6.8) */
export function whyOf(d: DetailData, sku: DSku): string {
  if (d.status === 'unpriced') return 'המחיר עוד לא נקבע, ולכן המוצר עוד לא במכירה.';
  if (!sku.sellable) return 'המלאי אינו זמין כעת.';
  return '';
}
/** the line under the options when the choice is not the story's */
export function storyNote(d: DetailData, sku: DSku): string | null {
  if (!d.axes.length || sku.key === d.story_key) return null;
  return `בסיפור מוצגת האפשרות ${storySku(d).label_he ?? ''}.`;
}
