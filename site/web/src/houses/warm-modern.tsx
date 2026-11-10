/**
 * S10: the warm-modern house (DIR2), a lazy chunk of the room page behind the flag: phase 1 as approved (AP3-WM): the v3c
 * base and the cushions slot, three sets on the wheel (B first, the default: CAM1). Its data is tools/make-house.ts's.
 * A set is sold as a set: one press puts every piece of it in the cart, at its set (P1); a piece can be bought on its own,
 * and a piece sold as a pack also as a single unit when the supplier offers it (SET1). A piece out of stock (PRE1, MED1)
 * says so and is never sold; a piece without a price is listed without a button.
 */
import { useState } from 'preact/hooks';
import type { CatalogRoom, Pack, PublicProduct } from '@hd/shared';
import { formatIls } from '@hd/shared/money';
import { packLabelHe } from '@hd/shared/packs';
import data from '@generated/house.living-room.warm-modern.json';
import type { House } from '../house';
import type { Scene } from '../engine/types';
import { mediaUrl } from '../media';
import { Price } from '../components/Media';
import { PackPicker } from '../components/PackPicker';
import { addToCart, cartBusy } from '../state/cart';
import { variantPackPrice, variantView, type VariantView } from '../variants';

type Piece = { product_id: string | null; variant_id: string | null; name_he: string; option_he: string | null };
type HouseSet = { position: number; id: string; label_he: string; thumb: string; items: Piece[] };
type Data = { style: string; name_he: string; status_he: string; alt_he: string; scene: Scene; room: CatalogRoom; sets: HouseSet[]; products: PublicProduct[] };

const h = data as unknown as Data;
const byId = new Map(h.products.map((p) => [p.id, p]));

type Row = { piece: Piece; p?: PublicProduct; v: VariantView | null; pack: Pack; sellable: boolean };

function SetPanel({ set }: { set: HouseSet }) {
  const [packs, setPacks] = useState<Record<number, Pack>>({});
  const rows: Row[] = set.items.map((piece, i) => {
    const p = piece.product_id ? byId.get(piece.product_id) : undefined;
    const v = p && piece.variant_id ? variantView(p, piece.variant_id) : null;
    return { piece, p, v, pack: packs[i] ?? 'set', sellable: !!p && !!v && v.available && p.availability.status === 'available' };
  });
  const forSale = rows.filter((r) => r.sellable);
  const total = forSale.reduce((s, r) => s + variantPackPrice(r.v!, r.pack), 0);
  const add = async (rs: Row[]) => {
    for (const r of rs)
      await addToCart(
        r.v!.variant_id,
        r.p!.name_he,
        1,
        r.pack,
        [r.piece.option_he, r.p!.pack ? packLabelHe(r.pack, r.p!.pack.set_qty) : null].filter(Boolean).join(', ') || undefined,
      );
  };
  return (
    <div class="set-panel">
      <ul class="set-items" aria-label={`בסט: ${set.items.length} פריטים`}>
        {rows.map((r, i) => (
          <li key={i} class="set-item" data-variant={r.piece.variant_id ?? ''}>
            <span class="set-text">
              <span class="set-name">{r.piece.name_he}</span>
              {r.piece.option_he ? <span class="specs">{r.piece.option_he}</span> : null}
            </span>
            <span class="set-buy">
              {r.v ? <Price agorot={variantPackPrice(r.v, r.pack)} provisional={r.v.price_provisional} /> : <span class="specs">עוד בלי מחיר</span>}
              {r.sellable ? (
                <button type="button" class="btn btn-ghost set-add" disabled={cartBusy.value} onClick={() => void add([r])}>
                  לסל<span class="sr-only"> רק את {r.piece.name_he}</span>
                </button>
              ) : r.v ? (
                <span class="specs set-oos">המלאי אינו זמין כעת</span>
              ) : null}
            </span>
            {r.p?.pack && r.v && r.sellable ? (
              <PackPicker
                p={r.p}
                value={r.pack}
                onChange={(k) => setPacks({ ...packs, [i]: k })}
                id={`set-${set.id}-${i}`}
                onStage
                prices={{ set: r.v.price_agorot, unit: r.v.unit_price_agorot, unitEstimated: r.v.unit_price_estimated }}
              />
            ) : null}
          </li>
        ))}
      </ul>
      {forSale.length ? (
        <button type="button" class="btn btn-ghost set-all" id="add-set" disabled={cartBusy.value} onClick={() => void add(forSale)}>
          {forSale.length === rows.length ? 'הסט כולו לסל' : `${forSale.length} הפריטים שבמלאי לסל`} · <span class="num">{formatIls(total)}</span>
        </button>
      ) : null}
    </div>
  );
}

export const house: House = {
  style: h.style,
  name_he: h.name_he,
  status_he: h.status_he,
  alt_he: h.alt_he,
  intro_he: 'בבית הזה מתחלפות בינתיים הכריות והשמיכה, בשלושה סטים. שאר הפריטים הם חלק מהתמונה, ויקבלו גלגל משלהם בשלב הבא.',
  scene: h.scene,
  room: h.room,
  product: (id) => (id ? byId.get(id) : undefined),
  thumb: (position) => {
    const s = h.sets[position - 1];
    return s ? mediaUrl(s.thumb.replace(/\.webp$/, '')) : null;
  },
  info: (position) => {
    const s = h.sets[position - 1];
    return s ? <SetPanel key={s.id} set={s} /> : null;
  },
};
