/**
 * Checkout: contact, address, shipping, consent → POST /api/checkout → redirect to the PSP's hosted payment page
 * (a mock here). No card fields ever touch this site (no PCI scope). Errors: summary at the top + inline per field.
 */
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CheckoutRequest } from '@hd/shared';
import { catalog } from '../catalog';
import { Price } from '../components/Media';
import { api, ApiError } from '../api';
import { cart, forgetCart, loadCart, saveOrderToken } from '../state/cart';
import { navigate } from '../router';
import { validateCheckout, type FieldErrors } from '../validate';

type Method = 'economy' | 'express';

/** Mirrors shared/src/pricing.ts customerShippingAgorot (the server recomputes it from D1). */
export function shippingFor(method: Method, subtotal: number): number {
  const s = catalog.shipping.find((x) => x.id === method);
  if (!s) return 0;
  return s.free_over_agorot !== null && subtotal >= s.free_over_agorot ? 0 : s.price_agorot;
}

const FIELDS: { k: keyof FieldErrors; label: string }[] = [
  { k: 'full_name', label: 'שם מלא' },
  { k: 'email', label: 'אימייל' },
  { k: 'phone', label: 'טלפון' },
  { k: 'city', label: 'עיר' },
  { k: 'street', label: 'רחוב' },
  { k: 'house', label: 'מספר בית' },
  { k: 'zip', label: 'מיקוד' },
  { k: 'terms', label: 'אישור התקנון' },
];

export function Checkout({ failed }: { failed: boolean }) {
  const [f, setF] = useState({ full_name: '', email: '', phone: '', city: '', street: '', house: '', apartment: '', zip: '', notes: '' });
  const [method, setMethod] = useState<Method>('economy');
  const [terms, setTerms] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const summary = useRef<HTMLDivElement>(null);

  useEffect(() => {
    void loadCart();
  }, []);

  const c = cart.value;
  const lines = c?.lines ?? [];
  const subtotal = c?.subtotal_agorot ?? 0;
  const shipping = shippingFor(method, subtotal);
  const economy = catalog.shipping.find((s) => s.id === 'economy');
  const toFree = economy?.free_over_agorot != null ? economy.free_over_agorot - subtotal : null;

  const set = (k: keyof typeof f) => (e: Event) => setF({ ...f, [k]: (e.currentTarget as HTMLInputElement).value });

  async function submit(e: Event) {
    e.preventDefault();
    if (!c) return;
    const req: CheckoutRequest = {
      cart_id: c.id,
      customer: { full_name: f.full_name.trim(), email: f.email.trim(), phone: f.phone.trim() },
      address: { city: f.city.trim(), street: f.street.trim(), house: f.house.trim(), apartment: f.apartment.trim(), zip: f.zip.trim(), notes: f.notes.trim() },
      shipping_method: method,
      consents: { terms: terms as true, marketing },
    };
    const errs = validateCheckout(req);
    setErrors(errs);
    setSubmitError(null);
    if (Object.keys(errs).length) {
      requestAnimationFrame(() => summary.current?.focus());
      return;
    }
    setBusy(true);
    try {
      const res = await api.checkout(req);
      saveOrderToken(res.order_id, res.order_token);
      forgetCart();
      if (api.kind === 'mock') navigate(res.redirect_url);
      else location.assign(res.redirect_url); // the PSP's hosted page (another origin in production)
    } catch (err) {
      setSubmitError(err instanceof ApiError ? (err.messageHe ?? 'לא הצלחנו ליצור את ההזמנה. נסו שוב.') : 'לא הצלחנו ליצור את ההזמנה. נסו שוב.');
      requestAnimationFrame(() => summary.current?.focus());
    } finally {
      setBusy(false);
    }
  }

  const field = (k: keyof typeof f & keyof FieldErrors, label: string, props: Record<string, unknown> = {}, hint?: string) => (
    <div class="field">
      <label htmlFor={`f-${k}`}>{label}</label>
      {hint ? (
        <span class="hint" id={`h-${k}`}>
          {hint}
        </span>
      ) : null}
      <input
        id={`f-${k}`}
        name={k}
        value={f[k]}
        onInput={set(k)}
        aria-invalid={errors[k] ? 'true' : undefined}
        aria-describedby={[hint ? `h-${k}` : '', errors[k] ? `e-${k}` : ''].filter(Boolean).join(' ') || undefined}
        {...props}
      />
      {errors[k] ? (
        <span class="err" id={`e-${k}`}>
          {errors[k]}
        </span>
      ) : null}
    </div>
  );

  const errList = FIELDS.filter((x) => errors[x.k]);
  return (
    <div class="wrap page">
      <div class="page-head">
        <h1 tabIndex={-1}>פרטים לתשלום</h1>
        <p class="muted">התשלום מתבצע בדף המאובטח של חברת הסליקה. פרטי האשראי לא עוברים דרך האתר הזה.</p>
      </div>
      {failed ? (
        <p class="notice error" role="alert">
          התשלום לא הושלם ולא חויבתם. אפשר לנסות שוב.
        </p>
      ) : null}
      {!lines.length ? (
        <div class="notice">
          <p>הסל ריק, אין מה לשלם.</p>
          <p>
            <a href="/rooms/living-room/">חזרה לסלון</a>
          </p>
        </div>
      ) : (
        <div class="cart-grid">
          <form class="form" onSubmit={submit} noValidate aria-describedby="req-note">
            <div ref={summary} tabIndex={-1}>
              {errList.length ? (
                <div class="error-summary" role="alert">
                  <h2>יש לתקן {errList.length === 1 ? 'שדה אחד' : `${errList.length} שדות`}</h2>
                  <ul>
                    {errList.map((x) => (
                      <li key={x.k}>
                        <a href={`#f-${x.k}`}>
                          {x.label}: {errors[x.k]}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : submitError ? (
                <p class="notice error" role="alert">
                  {submitError}
                </p>
              ) : null}
            </div>
            <p id="req-note" class="small muted">
              כל השדות חובה, חוץ מדירה, מיקוד והערות.
            </p>
            <fieldset>
              <legend>פרטי קשר</legend>
              {field('full_name', 'שם מלא', { autocomplete: 'name', required: true })}
              <div class="fields-2">
                {field(
                  'email',
                  'אימייל',
                  { type: 'email', autocomplete: 'email', inputMode: 'email', dir: 'ltr', required: true },
                  'לשם נשלחים אישור ההזמנה והחשבונית.',
                )}
                {field('phone', 'טלפון', { type: 'tel', autocomplete: 'tel', inputMode: 'tel', dir: 'ltr', required: true }, 'לשליח, למשל 050-1234567.')}
              </div>
            </fieldset>
            <fieldset>
              <legend>כתובת למשלוח</legend>
              <div class="fields-2">
                {field('city', 'עיר', { autocomplete: 'address-level2', required: true })}
                {field('street', 'רחוב', { autocomplete: 'address-line1', required: true })}
              </div>
              <div class="fields-2">
                {field('house', 'מספר בית', { inputMode: 'numeric', required: true })}
                <div class="field">
                  <label htmlFor="f-apartment">דירה (רשות)</label>
                  <input id="f-apartment" name="apartment" value={f.apartment} onInput={set('apartment')} autocomplete="address-line2" />
                </div>
              </div>
              {field('zip', 'מיקוד (רשות)', { inputMode: 'numeric', autocomplete: 'postal-code', dir: 'ltr' }, '7 ספרות.')}
              <div class="field">
                <label htmlFor="f-notes">הערות לשליח (רשות)</label>
                <textarea id="f-notes" name="notes" rows={2} maxLength={200} value={f.notes} onInput={set('notes')} />
              </div>
            </fieldset>
            <fieldset>
              <legend>משלוח</legend>
              {catalog.shipping.map((s) => {
                const price = shippingFor(s.id, subtotal);
                return (
                  <label key={s.id} class="choice">
                    <input type="radio" name="shipping" value={s.id} checked={method === s.id} onChange={() => setMethod(s.id)} />
                    <span>
                      <strong>{s.label_he}</strong>
                      <br />
                      <span class="small muted">{s.days_he}</span>
                    </span>
                    <span class="num">{price === 0 ? 'חינם' : <Price agorot={price} />}</span>
                  </label>
                );
              })}
              {toFree !== null && toFree > 0 ? (
                <p class="small muted">
                  עוד <Price agorot={toFree} /> בסל, והמשלוח החסכוני חינם.
                </p>
              ) : null}
            </fieldset>
            <div class="field">
              <label class="check">
                <input
                  type="checkbox"
                  checked={terms}
                  onChange={(e) => setTerms(e.currentTarget.checked)}
                  aria-invalid={errors.terms ? 'true' : undefined}
                  aria-describedby={errors.terms ? 'e-terms' : undefined}
                  id="f-terms"
                />
                <span>
                  קראתי ואני מסכים/ה ל<a href="/terms/">תקנון</a> ול<a href="/returns/">מדיניות הביטולים וההחזרות</a>.
                </span>
              </label>
              {errors.terms ? (
                <span class="err" id="e-terms">
                  {errors.terms}
                </span>
              ) : null}
            </div>
            <label class="check">
              <input type="checkbox" checked={marketing} onChange={(e) => setMarketing(e.currentTarget.checked)} />
              <span>אשמח לקבל עדכונים על מוצרים חדשים במייל (רשות, אפשר להסיר בכל עת).</span>
            </label>
            <button type="submit" class="btn btn-primary" disabled={busy} aria-busy={busy}>
              {busy ? 'יוצרים את ההזמנה…' : 'מעבר לתשלום מאובטח'}
            </button>
          </form>
          <aside class="card summary" aria-labelledby="sum-title">
            <h2 id="sum-title">ההזמנה</h2>
            <ul class="small" style={{ margin: 0, paddingInlineStart: 18 }}>
              {lines.map((l) => (
                <li key={l.variant_id}>
                  {l.name_he} × {l.qty}
                </li>
              ))}
            </ul>
            <dl>
              <dt>סכום ביניים</dt>
              <dd>
                <Price agorot={subtotal} />
              </dd>
              <dt>משלוח</dt>
              <dd>{shipping === 0 ? 'חינם' : <Price agorot={shipping} />}</dd>
              <dt class="total">לתשלום</dt>
              <dd class="total">
                <Price agorot={subtotal + shipping} />
              </dd>
            </dl>
            <p class="small muted">כולל מע"מ. חשבונית מס נשלחת במייל אחרי התשלום.</p>
          </aside>
        </div>
      )}
    </div>
  );
}
