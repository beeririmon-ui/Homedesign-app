/**
 * S23, QA S22 ת85: two checks on the site's prices, warnings only (a price is never changed here: the prices are the
 * manager's and pricing's, data/economics/products.json). tools/build-catalog.ts runs both on every build.
 *  - `skuAnchorIssue`: a studio price was set for one SKU (the card's default then); every other option's price is
 *    derived from it, so when the default moves the whole ladder moves. The SKU is the entry's `retail_sku`, else the
 *    anchor list (tools/price-anchors.json) while the price is the one the anchor recorded.
 *  - `ladderInversions`: on a size axis, the other choices the same, a smaller size priced above a larger one.
 */
export type PriceAnchor = { sku: string; retail_ils: number; retail_src: string | null; from?: string };

/** the area a size value names ("200x300", "200×300 ס"מ", "קוטר 180 ס"מ", "180"), or null */
export function sizeArea(id: string, label?: string | null): number | null {
  for (const t of [label ?? '', id]) {
    const r = /(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)/i.exec(t);
    if (r) return Number(r[1]) * Number(r[2]);
  }
  const d = /קוטר\s*(\d+(?:\.\d+)?)/.exec(label ?? '')?.[1] ?? /^(?:round-?)?(\d{2,3})$/.exec(id)?.[1];
  return d ? Math.PI * (Number(d) / 2) ** 2 : null;
}

/** the warning for a studio price whose SKU is not the default, or not known; null when it is the default */
export function skuAnchorIssue(
  e: { retail_ils: number; retail_src?: string | null; retail_sku?: string | null },
  defaultSku: string,
  anchor: PriceAnchor | undefined,
): { set_for: string | null; what: string } | null {
  const src = e.retail_src ?? null;
  const setFor = e.retail_sku ?? (anchor && anchor.retail_ils === e.retail_ils && anchor.retail_src === src ? anchor.sku : null);
  if (setFor === defaultSku) return null;
  if (setFor)
    return {
      set_for: setFor,
      what: `₪${e.retail_ils} (${src ?? 'no source'}) was set for SKU ${setFor}; the default SKU is now ${defaultSku}, and every option's price moved with it`,
    };
  return {
    set_for: null,
    what: anchor
      ? `₪${e.retail_ils} (${src ?? 'no source'}) was set again since its anchor (₪${anchor.retail_ils}, ${anchor.retail_src ?? 'no source'}, SKU ${anchor.sku}) and does not say for which SKU (retail_sku)`
      : `₪${e.retail_ils} (${src ?? 'no source'}) does not say for which SKU it was set (no retail_sku, no anchor)`,
  };
}

type Axis = { id: string; values: { id: string; label_he?: string | null }[] };
type Row = { values: Record<string, string>; retail_agorot: number };
export type LadderInversion = { axis: string; smaller: string; smaller_ils: number; larger: string; larger_ils: number; pairs: number };
/** per size axis (two values or more that name a size): the worst inversion and how many pairs are inverted */
export function ladderInversions(axes: Axis[], rows: Row[]): LadderInversion[] {
  const out: LadderInversion[] = [];
  for (const a of axes) {
    const area = new Map(a.values.map((v) => [v.id, sizeArea(v.id, v.label_he)] as const));
    if ([...area.values()].filter((x) => x !== null).length < 2) continue;
    const others = (r: Row) =>
      axes
        .filter((b) => b.id !== a.id)
        .map((b) => r.values[b.id])
        .join('|');
    let pairs = 0;
    let worst: LadderInversion | null = null;
    for (const x of rows)
      for (const y of rows) {
        const ax = area.get(x.values[a.id] ?? '') ?? null;
        const ay = area.get(y.values[a.id] ?? '') ?? null;
        if (ax === null || ay === null || !(ax < ay) || others(x) !== others(y) || !(x.retail_agorot > y.retail_agorot)) continue;
        pairs++;
        if (!worst || x.retail_agorot - y.retail_agorot > (worst.smaller_ils - worst.larger_ils) * 100)
          worst = {
            axis: a.id,
            smaller: x.values[a.id]!,
            smaller_ils: x.retail_agorot / 100,
            larger: y.values[a.id]!,
            larger_ils: y.retail_agorot / 100,
            pairs: 0,
          };
      }
    if (worst) out.push({ ...worst, pairs });
  }
  return out;
}
