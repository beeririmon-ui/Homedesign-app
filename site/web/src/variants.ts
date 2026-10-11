/**
 * One variant of a product, as the product page, the wheel and the in-browser mock API see it. A product with supplier
 * options (studio rules ג, 2026-10-11) has one variant per SKU with its own price; the room shows `default_variant`.
 * Without options the product is its one variant ('<id>:default'). Same pricing as the Worker (api/src/lib/store.ts).
 */
import type { Pack, PublicProduct } from '@hd/shared';
import { expandOptions, type ExpandedOptions } from '@hd/shared/options';

const expanded = new WeakMap<object, ExpandedOptions>();
/** The product's supplier options in the components' shape (the catalog ships them compact); null without options. */
export function optionsOf(p: PublicProduct): ExpandedOptions | null {
  if (!p.options) return null;
  let o = expanded.get(p.options);
  if (!o) expanded.set(p.options, (o = expandOptions(p.id, p.options)));
  return o;
}

export type VariantView = {
  variant_id: string;
  price_agorot: number;
  price_provisional: boolean;
  /** one piece of a set (P1), null when the product is not a set sold singly */
  unit_price_agorot: number | null;
  unit_price_estimated: boolean;
  /** "בז', 45×45 ס"מ": what the cart line says was chosen; null without options */
  option_he: string | null;
  shipping_days: [number, number] | null;
  available: boolean;
  in_room: boolean;
};

/** The variant the room shows (and the default everywhere a product is bought without choosing). */
export const defaultVariantId = (p: PublicProduct): string => optionsOf(p)?.default_variant ?? p.variants[0]!.id;

/** The option values of a SKU in the axes' order, in Hebrew ("בז', 45×45 ס"מ"). */
export function optionLabelHe(p: PublicProduct, values: Record<string, string>): string {
  return (optionsOf(p)?.axes ?? []).map((a) => a.values.find((v) => v.id === values[a.id])?.label_he ?? values[a.id]).join(', ');
}

export function variantView(p: PublicProduct, variantId: string = defaultVariantId(p)): VariantView | null {
  const o = optionsOf(p);
  if (!o) {
    if (variantId !== p.variants[0]!.id) return null;
    return {
      variant_id: variantId,
      price_agorot: p.price_agorot,
      price_provisional: p.price_provisional,
      unit_price_agorot: p.pack?.unit_price_agorot ?? null,
      unit_price_estimated: !!p.pack?.unit_price_estimated,
      option_he: null,
      shipping_days: p.shipping_days,
      available: true,
      in_room: true,
    };
  }
  const s = o.skus.find((x) => x.variant_id === variantId);
  if (!s) return null;
  return {
    variant_id: s.variant_id,
    price_agorot: s.price_agorot,
    price_provisional: s.price_provisional,
    unit_price_agorot: s.unit_price_agorot,
    unit_price_estimated: s.in_room ? !!p.pack?.unit_price_estimated : s.unit_price_agorot !== null,
    option_he: optionLabelHe(p, s.values),
    shipping_days: s.shipping_days ?? p.shipping_days,
    available: s.available,
    in_room: s.in_room,
  };
}

/** Price of the chosen pack of a variant: the set (the sale unit) or one piece (P1). */
export function variantPackPrice(v: VariantView, pack: Pack): number {
  return pack === 'unit' && v.unit_price_agorot !== null ? v.unit_price_agorot : v.price_agorot;
}
