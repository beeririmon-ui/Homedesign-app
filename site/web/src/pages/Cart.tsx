import { useEffect } from 'preact/hooks';
import { catalog } from '../catalog';
import { Price } from '../components/Media';
import { shippingFor } from './Checkout';
import { cart, cartBusy, cartError, loadCart, setQty } from '../state/cart';
import { lineLabelHe } from './lineLabel';

export function CartPage() {
  useEffect(() => {
    void loadCart();
  }, []);
  const c = cart.value;
  const lines = c?.lines ?? [];
  const provisional = lines.some((l) => l.price_provisional);
  const eco = catalog.shipping.find((s) => s.id === 'economy');
  return (
    <div class="wrap page">
      <div class="page-head">
        <h1 tabIndex={-1}>סל הקניות</h1>
      </div>
      {cartError.value ? (
        <p class="notice error" role="alert">
          {cartError.value}
        </p>
      ) : null}
      {!lines.length ? (
        <div class="notice">
          <p>הסל ריק.</p>
          <p>
            <a href="/rooms/living-room/">חזרה לסלון</a>
          </p>
        </div>
      ) : (
        <div class="cart-grid">
          <ul class="cart-lines" aria-label="פריטים בסל">
            {lines.map((l) => (
              <li key={`${l.variant_id}:${l.pack}`} class="card cart-line">
                <div>
                  <a class="title" href={`/p/${l.product_id}/`}>
                    {l.name_he}
                  </a>
                  {lineLabelHe(l) ? <p class="small pack-line">{lineLabelHe(l)}</p> : null}
                  <p class="small muted">
                    <Price agorot={l.unit_price_agorot} provisional={l.price_provisional} /> {l.pack === 'set' && l.pack_qty > 1 ? 'לסט' : 'ליחידה'}
                  </p>
                </div>
                <Price agorot={l.line_total_agorot} class="num" />
                <div class="controls">
                  <div class="qty" role="group" aria-label={`כמות של ${l.name_he}${lineLabelHe(l) ? `, ${lineLabelHe(l)}` : ''}`}>
                    <button
                      type="button"
                      disabled={cartBusy.value || l.qty >= 20}
                      onClick={() => void setQty(l.variant_id, l.pack, l.qty + 1, `כמות עודכנה: ${l.qty + 1}`)}
                      aria-label="הגדלת הכמות"
                    >
                      +
                    </button>
                    <output aria-label={`כמות: ${l.qty}`}>{l.qty}</output>
                    <button
                      type="button"
                      disabled={cartBusy.value || l.qty <= 1}
                      onClick={() => void setQty(l.variant_id, l.pack, l.qty - 1, `כמות עודכנה: ${l.qty - 1}`)}
                      aria-label="הקטנת הכמות"
                    >
                      −
                    </button>
                  </div>
                  <button type="button" class="link-btn" disabled={cartBusy.value} onClick={() => void setQty(l.variant_id, l.pack, 0, 'הוסר מהסל')}>
                    הסרה
                    <span class="sr-only">
                      {' '}
                      של {l.name_he}
                      {lineLabelHe(l) ? `, ${lineLabelHe(l)}` : ''}
                    </span>
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <aside class="card summary" aria-labelledby="summary-title">
            <h2 id="summary-title">סיכום</h2>
            <dl>
              <dt>סכום ביניים</dt>
              <dd>
                <Price agorot={c!.subtotal_agorot} />
              </dd>
              <dt>משלוח</dt>
              <dd class="small">
                {eco ? shippingFor('economy', c!.subtotal_agorot) === 0 ? 'חינם (משלוח חסכוני)' : <Price agorot={eco.price_agorot} /> : 'נבחר בשלב הבא'}
              </dd>
            </dl>
            {eco?.free_over_agorot && c!.subtotal_agorot < eco.free_over_agorot ? (
              <p class="small">
                עוד <Price agorot={eco.free_over_agorot - c!.subtotal_agorot} /> והמשלוח החסכוני חינם.
              </p>
            ) : null}
            <p class="small muted">המחירים כוללים מע"מ. אפשר לבחור משלוח מהיר בשלב הבא.{provisional ? ' המחירים ודמי המשלוח זמניים ועוד לא אושרו.' : ''}</p>
            <a class="btn btn-primary" href="/checkout/">
              להמשך לתשלום
            </a>
          </aside>
        </div>
      )}
    </div>
  );
}
