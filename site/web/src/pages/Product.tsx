import { useState } from 'preact/hooks';
import type { PublicProduct } from '@hd/shared';
import { product, slotOf } from '../catalog';
import { Price, productImage } from '../components/Media';
import { addToCart, cartBusy } from '../state/cart';
import { navigate } from '../router';
import { pendingOpen } from '../state/room';

export function Product({ p }: { p: PublicProduct }) {
  const [qty, setQty] = useState(1);
  const where = slotOf(p)!;
  const img = productImage(p.id);
  const dims = [p.dimensions_cm.width, p.dimensions_cm.depth, p.dimensions_cm.height].filter((x): x is number => typeof x === 'number');
  const showInRoom = () => {
    pendingOpen.value = { slot: where.slot.id, option: where.option.position };
    navigate(`/rooms/${where.room.id}/`);
  };
  return (
    <div class="wrap page">
      <nav class="crumbs" aria-label="פירורי לחם">
        <ol>
          <li>
            <a href="/">בית</a>
          </li>
          <li>
            <a href={`/rooms/${where.room.id}/`}>{where.room.name_he}</a>
          </li>
          <li aria-current="page">{where.slot.name_he}</li>
        </ol>
      </nav>
      <article class="product" aria-labelledby="product-title">
        <div class="product-media">{img ? <img src={img} alt={`${p.name_he} (תמונה זמנית מתוך החדר)`} width={600} height={600} /> : null}</div>
        <div class="product-info">
          <div class="page-head" style={{ marginBottom: 0 }}>
            <p class="eyebrow">{where.slot.name_he}</p>
            <h1 id="product-title" tabIndex={-1}>
              {p.name_he}
            </h1>
            {p.name_provisional ? (
              <p>
                <span class="badge badge-temp">שם ותיאור זמניים</span>
              </p>
            ) : null}
          </div>
          <div class="price-row">
            <Price class="price-big" agorot={p.price_agorot} provisional={p.price_provisional} />
            {p.compare_at_agorot ? (
              <span class="price-old">
                <span class="sr-only">מחיר קודם: </span>
                <Price agorot={p.compare_at_agorot} />
              </span>
            ) : null}
            <span class="small muted">כולל מע"מ</span>
          </div>
          <p>{p.description_he}</p>
          <div>
            <h2 class="small" style={{ fontFamily: 'var(--f-body)', fontWeight: 600, marginBottom: 8 }}>
              וריאציות בעמדה
            </h2>
            <div class="options-row">
              {where.slot.options.map((o) => {
                const op = product(o.product_id);
                return op ? (
                  <a key={o.position} class="option-chip" href={`/p/${op.id}/`} aria-current={op.id === p.id ? 'true' : undefined}>
                    <span class="swatch" style={{ background: op.color_hex }} aria-hidden="true" />
                    {o.position}. {op.materials_he[0] ?? op.name_he}
                  </a>
                ) : (
                  <span key={o.position} class="option-chip muted" aria-disabled="true">
                    {o.position}. ממתינה למוצר
                  </span>
                );
              })}
            </div>
          </div>
          <dl class="specs-list">
            {p.materials_he.length ? (
              <>
                <dt>חומרים</dt>
                <dd>{p.materials_he.join(', ')}</dd>
              </>
            ) : null}
            {dims.length ? (
              <>
                <dt>מידות</dt>
                <dd>{dims.join(' × ')} ס"מ (לפי הספק)</dd>
              </>
            ) : null}
            {p.shipping_days ? (
              <>
                <dt>זמן אספקה</dt>
                <dd>
                  {p.shipping_days[0]}–{p.shipping_days[1]} ימים במשלוח החסכוני (הערכה של הספק)
                </dd>
              </>
            ) : null}
            {p.set_of ? (
              <>
                <dt>סט</dt>
                <dd>{p.set_of} פריטים</dd>
              </>
            ) : null}
          </dl>
          {p.notes_he.length ? (
            <ul class="notes-list">
              {p.notes_he.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : null}
          <div class="buy-row">
            <div class="qty" role="group" aria-label="כמות">
              <button type="button" onClick={() => setQty(Math.min(20, qty + 1))} aria-label="הגדלת הכמות">
                +
              </button>
              <output aria-live="polite" aria-label={`כמות: ${qty}`}>
                {qty}
              </output>
              <button type="button" onClick={() => setQty(Math.max(1, qty - 1))} aria-label="הקטנת הכמות" disabled={qty === 1}>
                −
              </button>
            </div>
            <button type="button" class="btn btn-primary" disabled={cartBusy.value} onClick={() => void addToCart(p.variants[0]!.id, p.name_he, qty)}>
              הוספה לסל
            </button>
            <button type="button" class="btn btn-ghost" onClick={showInRoom}>
              הצגה בחדר
            </button>
          </div>
          <p class="small muted">
            ביטול עסקה והחזרות לפי חוק הגנת הצרכן. <a href="/returns/">פרטים</a>
          </p>
        </div>
      </article>
    </div>
  );
}
