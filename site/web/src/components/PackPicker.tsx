/**
 * Set or single piece (P1): an accessible radio group (native radios: arrow keys, one tab stop, labels read by screen
 * readers) shown only when the product is a set that is also sold by the piece. The set is the default.
 */
import type { Pack, PublicProduct } from '@hd/shared';
import { formatIls } from '@hd/shared/money';

type Props = {
  p: PublicProduct;
  value: Pack;
  onChange: (pack: Pack) => void;
  /** unique per page: the group's name and ids */
  id: string;
  /** dark glass surface (the variant wheel) instead of the page */
  onStage?: boolean;
};

export function PackPicker({ p, value, onChange, id, onStage }: Props) {
  const pack = p.pack;
  if (!pack) return null;
  const perPiece = Math.ceil(p.price_agorot / pack.set_qty / 100) * 100;
  const options: { v: Pack; title: string; price: number; hint: string }[] = [
    { v: 'set', title: `סט של ${pack.set_qty}`, price: p.price_agorot, hint: `${formatIls(perPiece)} לפריט, כמו בתמונה` },
    { v: 'unit', title: 'יחידה אחת', price: pack.unit_price_agorot, hint: pack.unit_price_estimated ? 'מחיר משוער' : 'פריט בודד' },
  ];
  return (
    <div class={`pack-picker${onStage ? ' on-stage' : ''}`} role="radiogroup" aria-labelledby={`${id}-label`}>
      <span id={`${id}-label`} class="pack-label">
        איך לקנות
      </span>
      <div class="pack-options">
        {options.map((o) => (
          <label key={o.v} class="pack-option">
            <input type="radio" name={id} value={o.v} checked={value === o.v} onChange={() => onChange(o.v)} />
            <span class="pack-text">
              <span class="pack-title">
                {o.title} · <span class="num">{formatIls(o.price)}</span>
              </span>
              <span class="pack-hint">{o.hint}</span>
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}

/** Price of the chosen pack. */
export function packPrice(p: PublicProduct, pack: Pack): number {
  return pack === 'unit' && p.pack ? p.pack.unit_price_agorot : p.price_agorot;
}
