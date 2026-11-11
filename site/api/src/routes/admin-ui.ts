/**
 * S13 (launch checklist 6.3): the admin screen, Hebrew and RTL, at /admin/ behind the same gate as the Admin API
 * (Cloudflare Access, re-verified by lib/access.ts `requireAdmin`). It is rendered by the Worker: no admin code is in
 * the public build (web/dist), and the page runs no script at all (plain links and forms, CSP `script-src` absent).
 *
 * - **The design system:** the page links the site's own stylesheet (tokens, type, buttons, fields, the status pill),
 *   found in the built index page, and adds a few rules of its own for the tables (`ADMIN_CSS`, a nonce).
 * - **The list:** status filter (or "needs a person") and search by the public order number.
 * - **An order:** items with house and variant; the payment, invoice and supplier tracks from the audit log; refunds and
 *   the cancellation; the actions (cancel, refund, invoice checked by a person, the mock supplier outside production).
 * - **Forms post here** (same origin only: `Origin` or `Sec-Fetch-Site` must say so), act through the same functions as
 *   the API, and redirect back with a result code (never free text in the address).
 */
import { Hono, type Context } from 'hono';
import { formatIls, ORDER_ID, randomToken } from '@hd/shared';
import type { AppEnv } from '../env';
import { adminWriteCheck, requireAdmin } from '../lib/access';
import {
  ADMIN_STATUS_HE,
  AUDIT_HE,
  CANCEL_STAGE_HE,
  CANCEL_STATE_HE,
  CREDIT_STATE_HE,
  FILTERS,
  INVOICE_STATE_HE,
  REFUND_STATE_HE,
  SHIPMENT_STATUS_HE,
  checkInvoice,
  listOrders,
  orderDetail,
  type AuditRow,
  type Filter,
  type OrderDetail,
} from '../lib/admin-orders';
import { cancelOrder } from '../lib/cancel';
import { requestRefund } from '../lib/refunds';
import { applySupplierUpdate } from '../lib/shipments';
import { MOCK_SUPPLIER_EVENTS, mockSupplierOpen, mockUpdate } from './admin';
import { log } from '../lib/log';

export const adminUi = new Hono<AppEnv>();
adminUi.use('*', requireAdmin);

const esc = (v: unknown): string => String(v ?? '').replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`);
const ils = (agorot: number | null | undefined) => esc(formatIls(agorot ?? 0));
const when = (iso: string | null | undefined) =>
  iso ? esc(new Date(iso).toLocaleString('he-IL', { timeZone: 'Asia/Jerusalem', dateStyle: 'short', timeStyle: 'short' })) : '—';

/** the site's stylesheet (hashed name), read once from the built index page */
let siteCss: string | null | undefined;
async function siteStylesheet(c: Context<AppEnv>): Promise<string | null> {
  if (siteCss !== undefined) return siteCss;
  if (!c.env.ASSETS) return (siteCss = null);
  try {
    const html = await (await c.env.ASSETS.fetch(new Request(new URL('/', c.req.url)))).text();
    siteCss = /<link[^>]+rel="stylesheet"[^>]+href="(\/assets\/[^"]+\.css)"/.exec(html)?.[1] ?? /href="(\/assets\/main-[^"]+\.css)"/.exec(html)?.[1] ?? null;
  } catch {
    siteCss = null;
  }
  return siteCss;
}

/** the screen's own rules, on the site's tokens (styles/system.css, tokens.css) */
const ADMIN_CSS = `
body{background:var(--paper,#F4F1EC);color:var(--ink,#3A3A3A);font-family:var(--f-text,system-ui,sans-serif);margin:0}
.admin-bar{display:flex;gap:16px;align-items:baseline;justify-content:space-between;border-bottom:1px solid var(--rule,#D9D6D0);padding:14px var(--gutter,24px)}
.admin-bar strong{font-size:18px}.admin-bar .who{font-size:14px;color:var(--ink-2,#5f5b55)}
.admin{max-width:1240px;margin:0 auto;padding:24px var(--gutter,24px) 64px}
.admin h1{font-size:30px;margin:0 0 4px;font-family:var(--f-display,inherit);font-weight:500}
.admin h2{font-size:20px;margin:32px 0 10px;font-weight:600}
.admin h3{font-size:16px;margin:0 0 8px;font-weight:600}
.admin table{width:100%;border-collapse:collapse;font-size:15px;background:var(--surface,#FBFAF7)}
.admin th,.admin td{text-align:start;padding:9px 10px;border-bottom:1px solid var(--rule,#D9D6D0);vertical-align:top}
.admin th{font-weight:600;font-size:13px;color:var(--ink-2,#5f5b55);background:var(--paper,#F4F1EC)}
.admin td.num,.admin .num{font-variant-numeric:tabular-nums;direction:ltr;unicode-bidi:isolate}
.admin a{color:inherit}
.filters{display:flex;flex-wrap:wrap;gap:12px;align-items:end;margin:16px 0 20px}
.filters label{display:grid;gap:4px;font-size:14px}
.filters select,.filters input,.act input,.act textarea,.act select{font:inherit;font-size:16px;padding:9px 10px;border:1px solid var(--rule-control,#8a857d);border-radius:2px;background:#fff;min-height:44px;box-sizing:border-box}
.tracks{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}
.track{background:var(--surface,#FBFAF7);border:1px solid var(--rule,#D9D6D0);padding:14px}
.track ol{list-style:none;margin:8px 0 0;padding:0;font-size:14px}
.track li{padding:6px 0;border-top:1px solid var(--rule,#D9D6D0)}
.track .now{font-size:17px;font-weight:600}
.acts{display:grid;grid-template-columns:repeat(2,1fr);gap:16px}
.act{background:var(--surface,#FBFAF7);border:1px solid var(--rule,#D9D6D0);padding:14px;display:grid;gap:10px;align-content:start}
.act label{display:grid;gap:4px;font-size:14px}
.act .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.act p{margin:0;font-size:14px}
.flag{display:inline-block;font-size:13px;padding:2px 8px;border:1px solid var(--ink,#3A3A3A);border-radius:2px}
.flag.warn{background:var(--ink,#3A3A3A);color:var(--paper,#F4F1EC)}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 16px;font-size:15px;margin:0}
.kv dt{color:var(--ink-2,#5f5b55)}.kv dd{margin:0}
.flash{padding:10px 14px;border:1px solid var(--ink,#3A3A3A);background:var(--surface,#FBFAF7);margin:12px 0}
.flash.error{border-color:var(--error,#9b2c2c)}
.muted{color:var(--ink-2,#5f5b55)}.small{font-size:14px}
.btn{font:inherit;font-weight:600;min-height:44px;padding:10px 18px;border-radius:2px;border:1px solid var(--ink,#3A3A3A);background:var(--ink,#3A3A3A);color:var(--paper,#F4F1EC);cursor:pointer}
.btn-ghost{background:transparent;color:var(--ink,#3A3A3A)}
@media (max-width:900px){.tracks,.acts{grid-template-columns:1fr}}
`;

async function page(c: Context<AppEnv>, title: string, body: string, status: 200 | 404 = 200): Promise<Response> {
  const nonce = randomToken(12);
  const css = await siteStylesheet(c);
  c.header(
    'Content-Security-Policy',
    `default-src 'none'; style-src 'self' 'nonce-${nonce}'; font-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`,
  );
  c.header('Cache-Control', 'no-store');
  c.header('X-Robots-Tag', 'noindex');
  return c.html(
    `<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>${esc(title)} · ניהול</title>${css ? `<link rel="stylesheet" href="${esc(css)}">` : ''}<style nonce="${nonce}">${ADMIN_CSS}</style></head>
<body><header class="admin-bar"><strong><a href="/admin/">ניהול הזמנות</a></strong><span class="who">מחובר: ${esc(c.get('actor'))}</span></header>
<main class="admin" id="main">${body}</main></body></html>`,
    status,
  );
}

const FILTER_HE: Record<Filter, string> = { attention: 'דורש טיפול', ...ADMIN_STATUS_HE } as Record<Filter, string>;

/** the list: /admin/ (the address the links use; app.ts) and /admin */
export const adminList = async (c: Context<AppEnv>) => {
  const filter = FILTERS.includes(c.req.query('status') as Filter) ? (c.req.query('status') as Filter) : undefined;
  const raw = (c.req.query('q') ?? '').trim();
  const search = /^\d{1,10}$/.test(raw) ? raw : undefined;
  const rows = await listOrders(c.env.DB, { filter, search, limit: 100 });
  const options = [
    `<option value="">הכל</option>`,
    ...FILTERS.map((f) => `<option value="${f}"${f === filter ? ' selected' : ''}>${esc(FILTER_HE[f])}</option>`),
  ].join('');
  const table = rows.length
    ? `<table><caption class="sr-only">הזמנות</caption><thead><tr><th scope="col">מספר</th><th scope="col">נוצרה</th><th scope="col">לקוח</th><th scope="col">פריטים</th><th scope="col">סכום</th><th scope="col">מצב</th><th scope="col">ספק</th><th scope="col">חשבונית</th><th scope="col">הוחזר</th></tr></thead><tbody>${rows
        .map(
          (
            r,
          ) => `<tr><td class="num"><a href="/admin/orders/${esc(r.id)}">${esc(r.id)}</a></td><td>${when(r.created_at)}</td><td>${esc(r.full_name)}</td><td class="num">${esc(r.items)}</td><td class="num">${ils(r.total_agorot)}</td>
<td><span class="status-pill">${esc(ADMIN_STATUS_HE[r.status] ?? r.status)}</span>${r.attention ? ' <span class="flag warn">דורש טיפול</span>' : ''}${r.cancel_state === 'requested' ? ' <span class="flag">ביטול ממתין</span>' : ''}</td>
<td class="small">${esc(
            (r.shipments ?? '')
              .split(',')
              .filter(Boolean)
              .map((s) => SHIPMENT_STATUS_HE[s] ?? s)
              .join(' · ') || '—',
          )}</td><td class="small">${esc(INVOICE_STATE_HE[r.invoice_state ?? 'none'])}</td><td class="num">${r.refunded_agorot ? ils(r.refunded_agorot) : '—'}</td></tr>`,
        )
        .join('')}</tbody></table>`
    : `<p role="status">אין הזמנות${filter || search ? ' שמתאימות לחיפוש' : ''}.</p>`;
  return page(
    c,
    'הזמנות',
    `<h1>הזמנות</h1><p class="muted small">${rows.length} מוצגות, החדשות קודם.</p>
<form class="filters" method="get" action="/admin/" role="search"><label>מצב<select name="status">${options}</select></label>
<label>מספר הזמנה<input name="q" inputmode="numeric" pattern="[0-9]{1,10}" value="${esc(search ?? '')}" autocomplete="off" dir="ltr"></label>
<button class="btn" type="submit">סינון</button>${filter || search ? ' <a class="btn btn-ghost" href="/admin/">ניקוי</a>' : ''}</form>${table}`,
  );
};
adminUi.get('/', adminList);

/** the result of an action, by code: never free text from the address */
const DONE_HE: Record<string, string> = {
  canceled: 'ההזמנה בוטלה. אם שולמה, התשלום הוחזר במלואו.',
  cancel_requested: 'בקשת הביטול נשלחה לספק. ההזמנה תבוטל ותזוכה כשהספק יאשר.',
  cancel_refused: 'הספק סירב לבטל: ההזמנה ממשיכה.',
  refunded: 'ההחזר בוצע. חשבונית זיכוי בדרך.',
  refund_duplicate: 'ההחזר הזה כבר בוצע קודם (אותו מפתח): לא הוחזר שוב.',
  invoice_found: 'נרשם: החשבונית נמצאה אצל הספק.',
  invoice_none: 'נרשם: אין חשבונית אצל הספק. ג׳וב החשבונית ירוץ שוב.',
  mock_applied: 'התשובה של הספק המדומה נרשמה.',
  mock_unchanged: 'התשובה של הספק המדומה לא שינתה דבר.',
};
const ERROR_HE: Record<string, string> = {
  bad_origin: 'הבקשה לא הגיעה מהעמוד הזה. רעננו ונסו שוב.',
  invalid_form: 'חלק מהפרטים חסרים או לא תקינים.',
  exceeds_paid: 'ההחזר גבוה ממה שנשאר להחזיר.',
  nothing_left: 'כל הסכום כבר הוחזר.',
  key_reused: 'הטופס הזה כבר שימש להחזר אחר. רעננו ונסו שוב.',
  refused: 'הסולק סירב להחזר. לא הועבר כסף.',
  provider_failed: 'הסולק לא ענה. ההחזר שמור; שליחה חוזרת מאותו טופס לא תחזיר פעמיים.',
  provider_unavailable: 'אי אפשר להחזיר דרך הסולק כרגע: החזירו ביד אצל הסולק.',
  unresolved: 'ההחזר מחכה לבדיקה של אדם אצל הסולק.',
  in_progress: 'ההחזר כבר בדרך לסולק.',
  not_paid: 'ההזמנה לא שולמה.',
  already_shipped: 'ההזמנה כבר נשלחה: אי אפשר לבטל. אפשר להחזיר כסף אחרי שהפריט חוזר.',
  already_refunded: 'ההזמנה כבר זוכתה במלואה.',
  supplier_submit_in_progress: 'ההזמנה נשלחת לספק ממש עכשיו. נסו שוב בעוד דקה.',
  supplier_not_configured: 'אין חיבור לספק: בטלו אצל הספק ביד.',
  supplier_cancel_not_built: 'אין לספק הזה קריאת ביטול עדיין: בטלו אצלו ביד.',
  supplier_failed: 'הספק לא ענה לבקשת הביטול. נסו שוב.',
  not_cancelable: 'אי אפשר לבטל את ההזמנה במצב הזה.',
  invoice_not_unresolved: 'החשבונית לא מחכה לבדיקה.',
  no_invoice_claim: 'אין להזמנה הזו חשבונית בבדיקה.',
  no_mock_shipment: 'אין להזמנה הזו משלוח אצל הספק המדומה.',
};

const MOCK_HE: Record<(typeof MOCK_SUPPLIER_EVENTS)[number], string> = {
  accepted: 'הספק התחיל להכין',
  shipped: 'יצאה למשלוח (עם מספר מעקב)',
  delivered: 'נמסרה',
  cancel_confirmed: 'הספק אישר את הביטול',
  cancel_refused: 'הספק סירב לבטל',
};

function track(title: string, now: string, rows: AuditRow[]): string {
  return `<section class="track" aria-label="${esc(title)}"><h3>${esc(title)}</h3><p class="now">${esc(now)}</p><ol>${
    rows.length
      ? rows
          .map(
            (a) =>
              `<li><span class="num">${when(a.at)}</span> · ${esc(AUDIT_HE[a.action] ?? a.action)} <span class="muted small">(${esc(a.actor)})</span></li>`,
          )
          .join('')
      : '<li class="muted">אין עדיין.</li>'
  }</ol></section>`;
}

function orderPage(c: Context<AppEnv>, d: OrderDetail): string {
  const o = d.order as Record<string, unknown> & { address: Record<string, string> };
  const id = String(o.id);
  const status = String(o.status);
  const done = c.req.query('done');
  const err = c.req.query('error');
  const flash = done && DONE_HE[done] ? `<p class="flash" role="status">${esc(DONE_HE[done])}</p>` : '';
  const flashErr = err ? `<p class="flash error" role="alert">${esc(ERROR_HE[err] ?? 'הפעולה לא הצליחה.')}</p>` : '';
  const ships = d.supplier_shipments;
  const paymentNow =
    d.money.refunded_agorot >= d.money.paid_agorot && d.money.paid_agorot > 0
      ? `הוחזר במלואו (${formatIls(d.money.refunded_agorot)})`
      : d.money.refunded_agorot
        ? `שולם ${formatIls(d.money.paid_agorot)}, הוחזרו ${formatIls(d.money.refunded_agorot)}`
        : o.paid_at
          ? `שולם ${formatIls(d.money.paid_agorot)}`
          : (ADMIN_STATUS_HE[status] ?? status);
  const invoiceNow = d.invoice
    ? `${INVOICE_STATE_HE[d.invoice.state] ?? d.invoice.state}${d.invoice.provider_invoice_id ? ` · ${d.invoice.provider_invoice_id}` : ''}`
    : INVOICE_STATE_HE.none!;
  const supplierNow =
    d.cancellation?.state === 'requested'
      ? CANCEL_STATE_HE.requested!
      : ships.length
        ? ships.map((s) => SHIPMENT_STATUS_HE[s.status] ?? s.status).join(' · ')
        : 'לא נשלחה לספק';

  const items = `<table><caption class="sr-only">פריטים</caption><thead><tr><th scope="col">#</th><th scope="col">פריט</th><th scope="col">וריאנט</th><th scope="col">בית</th><th scope="col">כמות</th><th scope="col">מחיר</th><th scope="col">מי שולח</th></tr></thead><tbody>${d.items
    .map(
      (i) =>
        `<tr><td class="num">${i.line}</td><td>${esc(i.name_he)}</td><td class="num small">${esc(i.variant_id)}</td><td>${esc(i.house ?? '— (מחוץ לחדר)')}</td><td class="num">${i.qty}${i.pack === 'set' && i.unit_sell_qty > 1 ? ` × סט ${i.unit_sell_qty}` : ''}</td><td class="num">${ils(i.qty * i.unit_price_agorot)}</td><td class="small">${esc(i.fulfillment_source === 'il_3pl' ? 'מחסן בישראל' : 'ספק')}</td></tr>`,
    )
    .join('')}</tbody></table>`;

  // the cancellation, by stage: what the button does is written next to it
  const sent = ships.some((s) => ['submitted', 'accepted', 'cancel_requested'].includes(s.status));
  const gone = ['shipped', 'delivered', 'refunded'].includes(status) || ships.some((s) => s.status === 'shipped' || s.status === 'delivered');
  // a request waiting on the supplier is not sent again from here: the supplier's answer settles it
  const waiting = d.cancellation?.state === 'requested';
  const cancelText = waiting
    ? 'הבקשה אצל הספק. כשיענה: אישור מבטל ומחזיר את כל התשלום; סירוב משאיר את ההזמנה בדרך.'
    : status === 'canceled'
      ? d.money.paid_agorot > d.money.counted_agorot
        ? 'ההזמנה בוטלה אבל ההחזר לא הושלם: ביטול חוזר משלים אותו (אותו מפתח, לא פעמיים).'
        : 'ההזמנה בוטלה.'
      : gone
        ? 'ההזמנה כבר יצאה: אי אפשר לבטל. החזר כסף (מלא או חלקי) אחרי שהפריט חוזר.'
        : sent
          ? 'אחרי שליחה לספק: נשלחת לספק בקשת ביטול. ההזמנה תבוטל ותזוכה רק כשהספק יאשר.'
          : o.paid_at
            ? 'לפני שליחה לספק: ההזמנה מבוטלת מיד, והתשלום מוחזר במלואו דרך הסולק.'
            : 'לפני תשלום: ההזמנה מבוטלת. לא שולם עליה דבר.';
  const canCancel = !gone && !waiting && !(status === 'canceled' && d.money.paid_agorot <= d.money.counted_agorot);
  const cancel = `<form class="act" method="post" action="/admin/orders/${esc(id)}/cancel"><h3>ביטול</h3>
${d.cancellation ? `<p><span class="flag${d.cancellation.state === 'requested' ? ' warn' : ''}">${esc(CANCEL_STATE_HE[d.cancellation.state] ?? d.cancellation.state)}</span> · ${esc(CANCEL_STAGE_HE[d.cancellation.stage] ?? d.cancellation.stage)} · ${when(d.cancellation.requested_at)} · ${esc(d.cancellation.requested_by)}</p>` : ''}
<p>${esc(cancelText)}</p>${
    canCancel
      ? `<label>סיבה (נרשמת ביומן)<input name="reason" required minlength="2" maxlength="300" autocomplete="off"></label><div class="row"><button class="btn" type="submit">${status === 'canceled' ? 'השלמת הביטול' : sent ? 'שליחת בקשת ביטול לספק' : 'ביטול ההזמנה'}</button></div>`
      : ''
  }</form>`;

  const left = d.money.refundable_agorot;
  const refund = `<form class="act" method="post" action="/admin/orders/${esc(id)}/refund"><h3>החזר כספי</h3>
<dl class="kv"><dt>שולם</dt><dd class="num">${ils(d.money.paid_agorot)}</dd><dt>הוחזר</dt><dd class="num">${ils(d.money.refunded_agorot)}</dd><dt>נשאר להחזיר</dt><dd class="num">${ils(left)}</dd></dl>${
    left > 0
      ? `<input type="hidden" name="key" value="rf_${esc(randomToken(16))}">
<label>סכום בשקלים (ריק: כל היתרה)<input name="amount" inputmode="decimal" pattern="[0-9]{1,7}([.][0-9]{1,2})?" dir="ltr" autocomplete="off"></label>
<label>סיבה (נרשמת ביומן)<input name="reason" required minlength="2" maxlength="300" autocomplete="off"></label>
<p class="muted">לעולם לא יותר ממה ששולם. שליחה חוזרת של אותו טופס לא מחזירה פעמיים. חשבונית זיכוי מופקת אחרי ההחזר.</p>
<div class="row"><button class="btn" type="submit">ביצוע החזר</button></div>`
      : `<p class="muted">${d.money.paid_agorot ? 'אין מה להחזיר.' : 'ההזמנה לא שולמה.'}</p>`
  }</form>`;

  const inv =
    d.invoice?.state === 'unresolved'
      ? `<form class="act" method="post" action="/admin/orders/${esc(id)}/invoice-check"><h3>חשבונית: לבדיקה של אדם</h3>
<p>הג׳וב לא יודע אם הספק ${esc(d.invoice.provider)} הפיק חשבונית. בדקו אצל הספק וסמנו מה מצאתם. אף פעם לא מופקת חשבונית שנייה.</p>
<p class="small muted">${esc(d.invoice.last_error ?? '')}</p>
<fieldset class="row"><legend class="sr-only">מה מצאתם</legend><label class="row"><input type="radio" name="outcome" value="found" required> יש חשבונית</label><label class="row"><input type="radio" name="outcome" value="none"> אין חשבונית: להפיק מחדש</label></fieldset>
<label>מספר החשבונית אצל הספק (אם יש)<input name="invoice_number" pattern="[A-Za-z0-9/_-]{1,40}" dir="ltr" autocomplete="off"></label>
<label>הערה (נרשמת ביומן)<input name="note" required minlength="2" maxlength="300" autocomplete="off"></label>
<div class="row"><button class="btn" type="submit">נבדק על ידי אדם</button></div></form>`
      : d.invoice?.checked_by
        ? `<div class="act"><h3>חשבונית</h3><p>נבדקה ידנית: ${esc(d.invoice.checked_by)} · ${when(d.invoice.checked_at)}</p></div>`
        : '';

  const mock = mockSupplierOpen(c.env)
    ? `<form class="act" method="post" action="/admin/orders/${esc(id)}/mock-supplier"><h3>ספק מדומה <span class="flag">פיתוח ותצוגה מקדימה בלבד</span></h3>
<p class="muted">משחק את התשובות של הספק, כמו שספק אמיתי ישלח אותן. ב-production אין את הלוח הזה.</p>
<div class="row">${MOCK_SUPPLIER_EVENTS.map((e) => `<button class="btn btn-ghost" name="event" value="${e}" type="submit">${esc(MOCK_HE[e])}</button>`).join('')}</div></form>`
    : '';

  const refunds = d.refunds.length
    ? `<h2>החזרים</h2><table><thead><tr><th scope="col">מתי</th><th scope="col">סכום</th><th scope="col">סוג</th><th scope="col">מצב</th><th scope="col">חשבונית זיכוי</th><th scope="col">מי</th><th scope="col">סיבה</th></tr></thead><tbody>${d.refunds
        .map(
          (r) =>
            `<tr><td>${when(r.claimed_at)}</td><td class="num">${ils(r.amount_agorot)}</td><td>${r.kind === 'full' ? 'מלא' : 'חלקי'}</td><td>${esc(REFUND_STATE_HE[r.state] ?? r.state)}</td><td class="small">${esc(CREDIT_STATE_HE[r.credit_state] ?? r.credit_state)}${r.credit_note_id ? ` · ${esc(r.credit_note_id)}` : ''}</td><td class="small">${esc(r.requested_by)}</td><td class="small">${esc(r.reason)}</td></tr>`,
        )
        .join('')}</tbody></table>`
    : '';

  const shipTable = ships.length
    ? `<h2>משלוחים</h2><table><thead><tr><th scope="col">ספק</th><th scope="col">מצב</th><th scope="col">מספר אצל הספק</th><th scope="col">מעקב</th><th scope="col">ניסיונות</th><th scope="col">שגיאה אחרונה</th></tr></thead><tbody>${ships
        .map(
          (s) =>
            `<tr><td>${esc(s.supplier)}</td><td>${esc(SHIPMENT_STATUS_HE[s.status] ?? s.status)}</td><td class="num small">${esc(s.supplier_order_id ?? '—')}</td><td class="num small">${esc(s.tracking_number ?? '—')}</td><td class="num">${s.attempts}</td><td class="small">${esc(s.last_error ?? '')}</td></tr>`,
        )
        .join('')}</tbody></table>`
    : '';

  const a = o.address;
  return `<p class="small"><a href="/admin/">← כל ההזמנות</a></p>
<h1>הזמנה <span class="num">${esc(id)}</span> <span class="status-pill">${esc(ADMIN_STATUS_HE[status] ?? status)}</span></h1>
<p class="muted small">נוצרה ${when(o.created_at as string)}${o.paid_at ? ` · שולמה ${when(o.paid_at as string)}` : ''} · ${esc(o.shipping_method === 'express' ? 'משלוח מהיר' : 'משלוח חסכוני')} · סה״כ <span class="num">${ils(o.total_agorot as number)}</span></p>
${flash}${flashErr}
<h2>מצב ההזמנה</h2><div class="tracks">${track('תשלום', paymentNow, d.tracks.payment)}${track('חשבונית', invoiceNow, d.tracks.invoice)}${track('ספק ומשלוח', supplierNow, d.tracks.supplier)}</div>
<h2>פעולות</h2><div class="acts">${cancel}${refund}${inv}${mock}</div>
<h2>פריטים</h2>${items}${refunds}${shipTable}
<h2>לקוח ומשלוח</h2><dl class="kv"><dt>שם</dt><dd>${esc(o.full_name)}</dd><dt>אימייל</dt><dd class="num">${esc(o.email)}</dd><dt>טלפון</dt><dd class="num">${esc(o.phone)}</dd>
<dt>כתובת</dt><dd>${esc([a.street, a.house].filter(Boolean).join(' '))}${a.apartment ? `, דירה ${esc(a.apartment)}` : ''}, ${esc(a.city)}${a.zip ? ` ${esc(a.zip)}` : ''}</dd>${a.notes ? `<dt>הערות</dt><dd>${esc(a.notes)}</dd>` : ''}</dl>
<h2>יומן</h2><table><thead><tr><th scope="col">מתי</th><th scope="col">מי</th><th scope="col">מה</th><th scope="col">פרטים</th></tr></thead><tbody>${d.audit
    .map(
      (r) =>
        `<tr><td class="num">${when(r.at)}</td><td class="small">${esc(r.actor)}</td><td>${esc(AUDIT_HE[r.action] ?? r.action)}</td><td class="small num">${esc((r.detail ?? '').slice(0, 160))}</td></tr>`,
    )
    .join('')}</tbody></table>`;
}

adminUi.get('/orders/:id', async (c) => {
  const id = c.req.param('id');
  const d = ORDER_ID.test(id) ? await orderDetail(c.env.DB, id) : null;
  if (!d) return page(c, 'לא נמצאה', `<h1>ההזמנה לא נמצאה</h1><p><a href="/admin/">חזרה לרשימה</a></p>`, 404);
  return page(c, `הזמנה ${id}`, orderPage(c, d));
});

// ---------- actions (forms) ----------
/** same origin only: a form on another site cannot act with the owner's Access cookie (S16: the Admin API's rule, lib/access.ts) */
function sameOrigin(c: Context<AppEnv>): boolean {
  return adminWriteCheck({ url: c.req.url, header: (n) => c.req.header(n) }, c.get('adminKind')).ok;
}
const back = (c: Context<AppEnv>, id: string, q: string) => c.redirect(`/admin/orders/${id}?${q}`, 303);

adminUi.post('/orders/:id/:action', async (c) => {
  const id = c.req.param('id');
  const action = c.req.param('action');
  if (!ORDER_ID.test(id)) return c.text('not found', 404);
  if (!sameOrigin(c)) return back(c, id, 'error=bad_origin');
  const f = await c.req.parseBody();
  const str = (k: string) => (typeof f[k] === 'string' ? (f[k] as string).trim() : '');
  const actor = c.get('actor');
  try {
    if (action === 'cancel') {
      const reason = str('reason');
      if (reason.length < 2 || reason.length > 300) return back(c, id, 'error=invalid_form');
      const r = await cancelOrder(c.env, id, actor, reason);
      if ('error' in r) return back(c, id, `error=${r.code}`);
      if (r.refund && !r.refund.ok) return back(c, id, `error=${r.refund.code}`);
      return back(c, id, `done=${r.outcome === 'canceled' ? 'canceled' : r.outcome === 'requested' ? 'cancel_requested' : 'cancel_refused'}`);
    }
    if (action === 'refund') {
      const reason = str('reason');
      const key = str('key');
      const amountRaw = str('amount');
      if (reason.length < 2 || reason.length > 300 || (amountRaw && !/^\d{1,7}(\.\d{1,2})?$/.test(amountRaw))) return back(c, id, 'error=invalid_form');
      const amount = amountRaw ? Math.round(Number(amountRaw) * 100) : 'rest';
      if (amount !== 'rest' && amount <= 0) return back(c, id, 'error=invalid_form');
      const r = await requestRefund(c.env, { orderId: id, amount, reason, key, actor });
      if (!r.ok) return back(c, id, `error=${r.code}`);
      return back(c, id, r.duplicate ? 'done=refund_duplicate' : 'done=refunded');
    }
    if (action === 'invoice-check') {
      const note = str('note');
      const outcome = str('outcome');
      const number = str('invoice_number');
      if (note.length < 2 || note.length > 300) return back(c, id, 'error=invalid_form');
      if (outcome === 'found' && !/^[A-Za-z0-9/_-]{1,40}$/.test(number)) return back(c, id, 'error=invalid_form');
      if (outcome !== 'found' && outcome !== 'none') return back(c, id, 'error=invalid_form');
      const r = await checkInvoice(c.env, id, actor, outcome === 'found' ? { outcome, invoice_number: number, note } : { outcome, note });
      if (!r.ok) return back(c, id, `error=${r.code}`);
      return back(c, id, `done=invoice_${outcome}`);
    }
    if (action === 'mock-supplier' && mockSupplierOpen(c.env)) {
      const event = str('event') as (typeof MOCK_SUPPLIER_EVENTS)[number];
      if (!MOCK_SUPPLIER_EVENTS.includes(event)) return back(c, id, 'error=invalid_form');
      const r = await applySupplierUpdate(c.env, { orderId: id, supplier: 'mock', update: mockUpdate(event, id), actor: `mock-supplier (${actor})` });
      if (r === 'unknown_shipment') return back(c, id, 'error=no_mock_shipment');
      return back(c, id, r === 'applied' ? 'done=mock_applied' : 'done=mock_unchanged');
    }
  } catch (err) {
    const error_id = log.error('admin.action_failed', { order_id: id, action }, err);
    return page(
      c,
      'שגיאה',
      `<h1>הפעולה נכשלה</h1><p>קוד שגיאה: <span class="num">${esc(error_id)}</span>. כלום לא הוחזר פעמיים; אפשר לנסות שוב.</p><p><a href="/admin/orders/${esc(id)}">חזרה להזמנה</a></p>`,
    );
  }
  return c.text('not found', 404);
});
