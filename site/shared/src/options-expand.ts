/**
 * S13: the supplier options' browser half, zod-free (the room's JS budget). The variant id of an option and the
 * expansion of the compact public options (./options `PublicOptionsSchema`) into the shape the components use. The
 * schemas stay in ./options, which re-exports these; a page imports this module and never loads zod.
 */
import type { AxisId, PublicOptions } from './options';

/** Our variant id for a supplier option: the product and its value ids ("<product id>:beige+45x45"). */
export const optionVariantId = (productId: string, valueIds: string[]): string => `${productId}:${valueIds.join('+')}`;

export type OptionSku = {
  variant_id: string;
  values: Record<string, string>;
  price_agorot: number;
  price_provisional: boolean;
  unit_price_agorot: number | null;
  /** null: the product's shipping days */
  shipping_days: [number, number] | null;
  available: boolean;
  in_room: boolean;
};
export type ExpandedOptions = {
  axes: { id: AxisId; name_he: string; values: { id: string; label_he: string; hex: string | null }[] }[];
  skus: OptionSku[];
  default_variant: string;
};

export function expandOptions(productId: string, o: PublicOptions): ExpandedOptions {
  const axes = o.axes.map((a) => ({ id: a.id, name_he: a.name_he, values: a.values.map(([id, label_he, hex]) => ({ id, label_he, hex })) }));
  const off = new Set(o.off);
  const px = new Set(o.px);
  const skus = o.v.map((ix, i) => {
    const ids = ix.map((k, j) => axes[j]!.values[k]!.id);
    return {
      variant_id: optionVariantId(productId, ids),
      values: Object.fromEntries(axes.map((a, j) => [a.id, ids[j]!])),
      price_agorot: o.p[i]!,
      price_provisional: px.has(i) ? !o.pv : o.pv,
      unit_price_agorot: o.u?.[i] ?? null,
      shipping_days: o.d?.[i] ?? null,
      available: !off.has(i),
      in_room: i === o.room,
    };
  });
  return { axes, skus, default_variant: skus[o.room]!.variant_id };
}
