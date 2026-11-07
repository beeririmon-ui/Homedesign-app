/**
 * The story's test checkout and its confirmation (loaded by story.ts on /story/checkout/ and /story/order/ only). The
 * form is in the page (tools/make-story.ts); this fills the summary from the test cart, checks the fields with the
 * site's own rules, says every error at the field and in a summary that takes the focus, and on a valid form keeps a
 * test order in this browser, empties the cart and opens its confirmation. Nothing is charged, nothing is sent.
 */
import { browserStore, priceHe, type StoryCart } from './story-cart';
import { errorsOf, placeOrder, readOrders, totals, type CheckoutForm, type ShippingMethod } from './checkout-model';

type Ctx = { cart: StoryCart; methods: ShippingMethod[]; announce: (t: string) => void; mark: (n: string, d?: unknown) => void; counted: () => void };
const LABELS: Record<string, string> = {
  full_name: 'שם מלא',
  email: 'אימייל',
  phone: 'טלפון',
  city: 'עיר',
  street: 'רחוב',
  house: 'מספר בית',
  zip: 'מיקוד',
  terms: 'אישור התקנון',
};
const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T | null;
const items = (n: number) => (n === 1 ? 'פריט אחד' : `${n} פריטים`);

function lineEl(name: string, option: string | null, detail: string): HTMLLIElement {
  const li = document.createElement('li');
  li.className = 'mag-credit st-co-line';
  const body = document.createElement('span');
  body.className = 'mag-credit-body';
  const n = document.createElement('span');
  n.className = 'mag-credit-name';
  n.textContent = option && !name.includes(option) ? `${name} · ${option}` : name;
  const d = document.createElement('span');
  d.className = 'mag-credit-detail';
  d.textContent = detail;
  body.append(n, d);
  li.append(body);
  return li;
}

export function initCheckout({ cart, methods, announce, mark, counted }: Ctx): void {
  const form = $<HTMLFormElement>('co-form');
  if (!form) return;
  const summary = () => {
    const c = cart.current();
    const method = (form.querySelector<HTMLInputElement>('input[name="shipping"]:checked')?.value ?? 'economy') as ShippingMethod['id'];
    const t = totals(methods, method, c);
    $('co-lines')!.replaceChildren(...(c?.lines ?? []).map((l) => lineEl(l.name_he, l.option_he, `${l.qty} × ${priceHe(l.unit_price_agorot)} · ${priceHe(l.line_total_agorot)}`)));
    $('co-subtotal')!.textContent = priceHe(t.subtotal);
    $('co-shipping')!.textContent = t.shipping ? priceHe(t.shipping) : 'חינם';
    $('co-total')!.textContent = priceHe(t.total);
    $('co-free')!.textContent = t.toFree ? `עוד ${priceHe(t.toFree)} למשלוח חסכוני חינם.` : '';
    for (const m of methods) {
      const out = document.querySelector<HTMLElement>(`[data-ship-price="${m.id}"]`);
      if (out) out.textContent = c?.subtotal_agorot && m.free_over_agorot !== null && c.subtotal_agorot >= m.free_over_agorot ? 'חינם' : priceHe(m.price_agorot);
    }
    const empty = !c?.lines.length;
    $('co-empty')!.hidden = !empty;
    form.hidden = empty;
    const held = cart.held();
    $('co-held')!.hidden = !held.length;
    $('co-held')!.textContent = held.length ? `לא בהזמנה (המלאי אינו זמין כעת): ${held.map((h) => h.name_he).join(', ')}.` : '';
  };
  summary();
  form.addEventListener('change', (e) => {
    if ((e.target as HTMLInputElement).name === 'shipping') summary();
  });
  const val = (k: string) => (form.elements.namedItem(k) as HTMLInputElement | null)?.value ?? '';
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const f: CheckoutForm = {
      full_name: val('full_name'),
      email: val('email'),
      phone: val('phone'),
      city: val('city'),
      street: val('street'),
      house: val('house'),
      apartment: val('apartment'),
      zip: val('zip'),
      notes: val('notes'),
      terms: (form.elements.namedItem('terms') as HTMLInputElement).checked,
      shipping: (form.querySelector<HTMLInputElement>('input[name="shipping"]:checked')?.value ?? 'economy') as ShippingMethod['id'],
    };
    const errs = errorsOf(f);
    for (const k of Object.keys(LABELS)) {
      const input = $<HTMLInputElement>(`f-${k}`);
      const msg = $(`err-${k}`);
      const m = errs[k as keyof typeof errs];
      input?.setAttribute('aria-invalid', m ? 'true' : 'false');
      if (msg) {
        msg.hidden = !m;
        msg.textContent = m ?? '';
      }
    }
    const box = $('co-errors')!;
    const keys = Object.keys(errs) as (keyof typeof errs)[];
    if (keys.length) {
      // the summary names every field and links to it, and takes the focus (the site's checkout does the same)
      box.hidden = false;
      const h = document.createElement('p');
      h.textContent = keys.length === 1 ? 'יש לתקן שדה אחד:' : `יש לתקן ${keys.length} שדות:`;
      const ul = document.createElement('ul');
      for (const k of keys) {
        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = `#f-${k}`;
        a.className = 'mag-link';
        a.textContent = `${LABELS[k]}: ${errs[k]}`;
        li.append(a);
        ul.append(li);
      }
      box.replaceChildren(h, ul);
      box.focus();
      mark('checkout:errors', keys);
      return;
    }
    box.hidden = true;
    const c = cart.current();
    if (!c?.lines.length) return;
    const order = placeOrder(browserStore(), f, methods, c);
    cart.clear();
    counted();
    mark('checkout:placed', order.id);
    announce(`הזמנת הבדיקה ${order.id} התקבלה.`);
    location.assign(`/story/order/?id=${encodeURIComponent(order.id)}`);
  });
}

export function initOrder(): void {
  const id = new URLSearchParams(location.search).get('id') ?? '';
  const order = readOrders(browserStore()).find((o) => o.id === id) ?? null;
  $('or-missing')!.hidden = !!order;
  $('or-found')!.hidden = !order;
  if (!order) return;
  $('or-number')!.textContent = order.id;
  $('or-greeting')!.textContent = order.first_name ? `תודה, ${order.first_name}.` : 'תודה.';
  $('or-lines')!.replaceChildren(...order.lines.map((l) => lineEl(l.name_he, l.option_he, `${l.qty} · ${priceHe(l.line_total_agorot)}`)));
  $('or-sum')!.textContent = `${items(order.lines.reduce((n, l) => n + l.qty, 0))} · ${priceHe(order.subtotal_agorot)}, ${order.shipping_he} ${order.shipping_agorot ? priceHe(order.shipping_agorot) : 'חינם'} · סה״כ ${priceHe(order.total_agorot)}`;
  $('or-city')!.textContent = order.city ? `למשלוח ל${order.city}.` : '';
  $<HTMLElement>('or-title')?.focus({ preventScroll: true });
}
