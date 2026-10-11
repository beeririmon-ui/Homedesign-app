/**
 * Supplier options on the product page (studio rules ג, 2026-10-11, "כל האפשרויות של הספק בדף המוצר"): one group per
 * axis, the customer chooses, and the price, the picture and the cart follow the chosen SKU. The room keeps showing
 * its own option (`in_room`); a line says which one it is when the choice differs.
 *
 * Accessible by construction: each axis is a fieldset whose legend names the axis and the current value; the values are
 * native radios (one tab stop, arrow keys, RTL handled by the browser) drawn as colour swatches (hex) or chips, and an
 * axis with many values is a native select. A value that does not exist with the choices above it is disabled (a
 * cascade: the first axis is free, so every SKU stays reachable); an out-of-stock option is disabled too.
 */
import type { PublicProduct } from '@hd/shared';
import { availableValues, pickSku, selectionOf } from '@hd/shared/options';
import { optionLabelHe, optionsOf } from '../variants';

const CHIPS_MAX = 8;
const SWATCHES_MAX = 16;

type Props = {
  p: PublicProduct;
  /** the chosen variant id */
  value: string;
  onChange: (variantId: string) => void;
  /** unique per page: names and ids */
  id: string;
};

export function OptionPicker({ p, value, onChange, id }: Props) {
  const o = optionsOf(p);
  if (!o) return null;
  const room = o.skus.find((s) => s.in_room) ?? o.skus[0]!;
  const sku = o.skus.find((s) => s.variant_id === value) ?? room;
  const sel = selectionOf(o.axes, sku);
  return (
    <div class="opt-picker" data-options={o.skus.length}>
      {o.axes.map((a, i) => {
        const ok = availableValues(o.axes, o.skus, sel, i);
        const choose = (v: string) => {
          const r = pickSku(o.axes, o.skus, sel, i, v);
          if (r.sku) onChange(r.sku.variant_id);
        };
        const current = a.values.find((v) => v.id === sel[a.id]);
        const swatches = a.id === 'color' && a.values.length <= SWATCHES_MAX && a.values.every((v) => v.hex);
        const fid = `${id}-${a.id}`;
        if (!swatches && a.values.length > CHIPS_MAX)
          return (
            <div class="opt-axis" key={a.id}>
              <label class="opt-legend" for={fid}>
                {a.name_he}
              </label>
              <select id={fid} class="opt-select" value={sel[a.id]} onChange={(e) => choose((e.currentTarget as HTMLSelectElement).value)}>
                {a.values.map((v) => (
                  <option key={v.id} value={v.id} disabled={!ok.has(v.id)}>
                    {v.label_he}
                    {ok.has(v.id) ? '' : ' (לא זמין בבחירה הזו)'}
                  </option>
                ))}
              </select>
            </div>
          );
        return (
          <fieldset class="opt-axis" key={a.id}>
            <legend class="opt-legend">
              {a.name_he}: <span class="opt-current">{current?.label_he}</span>
            </legend>
            <div class={`opt-values${swatches ? ' is-swatches' : ''}`}>
              {a.values.map((v) => {
                const off = !ok.has(v.id);
                return (
                  <label key={v.id} class={`opt-value${off ? ' is-off' : ''}`} title={swatches ? v.label_he : undefined}>
                    <input type="radio" name={fid} value={v.id} checked={sel[a.id] === v.id} disabled={off} onChange={() => choose(v.id)} />
                    {v.hex ? <span class="opt-swatch" style={{ background: v.hex }} aria-hidden="true" /> : null}
                    <span class={swatches ? 'sr-only' : 'opt-text'}>{v.label_he}</span>
                    {off ? <span class="sr-only"> (לא זמין בבחירה הזו)</span> : null}
                  </label>
                );
              })}
            </div>
          </fieldset>
        );
      })}
      {sku !== room ? (
        <p class="small muted opt-room-note">
          בחדר מוצגת האפשרות {optionLabelHe(p, room.values)}.{' '}
          <button type="button" class="link-btn" onClick={() => onChange(room.variant_id)}>
            חזרה לאפשרות שבחדר
          </button>
        </p>
      ) : null}
    </div>
  );
}
