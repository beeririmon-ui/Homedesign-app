/**
 * The supplier options' picker rules (studio rules ג, 2026-10-11): a cascade over the axes, the first axis free, an
 * out-of-stock SKU never offered. Pure and dependency-free, so a page can load it without the schemas of ./options
 * (which re-exports it): the site's product page (web/src/components/OptionPicker.tsx) and the story's detail page
 * (web/src/story/detail-model.ts) choose the same way.
 */
export type PickerSku = { variant_id: string; values: Partial<Record<string, string>>; available: boolean };
export type PickerAxis = { id: string; values: { id: string }[] };

/** SKUs that match the chosen values on the first `upTo` axes. */
function matching<T extends PickerSku>(skus: T[], sel: Record<string, string>, axes: PickerAxis[], upTo: number): T[] {
  return skus.filter((s) => axes.slice(0, upTo).every((a) => s.values[a.id] === sel[a.id]));
}

/**
 * Which values of axis `index` can be chosen, given the choices on the axes before it (a cascade: the first axis is
 * free, each next one offers only what exists with the ones above, so a customer can always reach every SKU).
 * A value whose SKUs are all out of stock is not available either.
 */
export function availableValues(axes: PickerAxis[], skus: PickerSku[], sel: Record<string, string>, index: number): Set<string> {
  const pool = matching(skus, sel, axes, index);
  return new Set(pool.filter((s) => s.available).map((s) => s.values[axes[index]!.id]!));
}

/**
 * The selection after the customer chose `value` on axis `index`: the axes after it keep their value when it still
 * exists, else take the first available one. Returns the selection and the SKU it names (null if none exists).
 */
export function pickSku<T extends PickerSku>(
  axes: PickerAxis[],
  skus: T[],
  sel: Record<string, string>,
  index: number,
  value: string,
): { sel: Record<string, string>; sku: T | null } {
  const next = { ...sel, [axes[index]!.id]: value };
  for (let j = index + 1; j < axes.length; j++) {
    const ok = availableValues(axes, skus, next, j);
    const id = axes[j]!.id;
    if (!ok.has(next[id]!)) {
      const first = axes[j]!.values.find((v) => ok.has(v.id)) ?? axes[j]!.values.find((v) => matching(skus, next, axes, j).some((s) => s.values[id] === v.id));
      if (first) next[id] = first.id;
    }
  }
  const sku = skus.find((s) => axes.every((a) => s.values[a.id] === next[a.id])) ?? null;
  return { sel: next, sku };
}

/** The selection that names a SKU (the default selection is the room's SKU). */
export function selectionOf(axes: PickerAxis[], sku: PickerSku): Record<string, string> {
  return Object.fromEntries(axes.map((a) => [a.id, sku.values[a.id]!]));
}
