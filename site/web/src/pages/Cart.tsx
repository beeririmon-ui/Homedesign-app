import { useEffect } from 'preact/hooks';
import { catalog } from '../catalog';
import { Price } from '../components/Media';
import { cart, cartBusy, cartError, loadCart, setQty } from '../state/cart';

export function CartPage() {
  useEffect(() => {
    void loadCart();
  }, []);
  const c = cart.value;
  const lines = c?.lines ?? [];
  const provisional = lines.some((l) => l.price_provisional);
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
              <li key={l.variant_id} class="card cart-line">
                <div>
                  <a class="title" href={`/p/${l.product_id}/`}>
                    {l.name_he}
                  </a>
                  <p class="small muted">
                    <Price agorot={l.unit_price_agorot} provisional={l.price_provisional} /> ליחידה
                  </p>
                </div>
                <Price agorot={l.line_total_agorot} class="num" />
                <div class="controls">
                  <div class="qty" role="group" aria-label={`כמות של ${l.name_he}`}>
                    <button type="button" disabled={cartBusy.value || l.qty >= 20} onClick={() => void setQty(l.variant_id, l.qty + 1, `כמות עודכנה: ${l.qty + 1}`)} aria-label="הגדלת הכמות">
                      +
                    </button>
                    <output aria-label={`כמות: ${l.qty}`}>{l.qty}</output>
                    <button type="button" disabled={cartBusy.value || l.qty <= 1} onClick={() => void setQty(l.variant_id, l.qty - 1, `כמות עודכנה: ${l.qty - 1}`)} aria-label="הקטנת הכמות">
                      −
                    </button>
                  </div>
                  <button type="button" class="link-btn" disabled={cartBusy.value} onClick={() => void setQty(l.variant_id, 0, 'הוסר מהסל')}>
                    הסרה<span class="sr-only"> של {l.name_he}</span>
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
              <dd class="small">נבחר בשלב הבא ({catalog.shipping.find((s) => s.is_default)?.label_he} כברירת מחדל)</dd>
            </dl>
            <p class="small muted">המחירים כוללים מע"מ.{provisional ? ' המחירים זמניים ועוד לא אושרו.' : ''}</p>
            <a class="btn btn-primary" href="/checkout/">
              להמשך לתשלום
            </a>
          </aside>
        </div>
      )}
    </div>
  );
}
