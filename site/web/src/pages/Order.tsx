/**
 * Order status for the buyer. The return from the payment page never changes state: the status shown here comes
 * from the server, which marks an order paid only from the signed webhook. Polls briefly while payment is pending.
 */
import { useEffect, useState } from 'preact/hooks';
import type { OrderView } from '@hd/shared';
import { ORDER_STEPS_HE, orderStep } from '@hd/shared/constants';
import { lineName } from '@hd/shared/lines';
import { api, ApiError } from '../api';
import { orderToken } from '../state/cart';
import { Picture, Price } from '../components/Media';
import { optionImage as optionPhoto, product as catalogProduct, supplierImage } from '../catalog';
import { mediaUrl } from '../media';
import { HOUSES, NORDIC, loadHouse, nordic, type House } from '../house';
import { optionsOf } from '../variants';
import type { SceneLayerSet } from '../engine/types';

type Line = OrderView['lines'][number];
type Placed = { slot: string; position: number; z: number; layer: NonNullable<House['scene']['slots'][string]> };

/** Where a house draws exactly this variant: the slot and the option whose layer renders it; null when none does. */
function placeOf(h: House, l: Line): Placed | null {
  if (!l.variant_id) return null;
  for (const s of h.room.slots) {
    const layer = h.scene.slots[s.id];
    if (!layer?.product) continue;
    for (const o of s.options) if (h.drawn(s.id, o.position).includes(l.variant_id)) return { slot: s.id, position: o.position, z: s.z, layer };
  }
  return null;
}

/** The card's picture of the variant bought (the supplier's photo of that option); null when there is none of it. */
function cardImage(h: House | null | undefined, l: Line): string | null {
  const p = h?.product(l.product_id) ?? catalogProduct(l.product_id);
  if (!p) return null;
  const o = optionsOf(p);
  const i = o ? o.skus.findIndex((s) => s.variant_id === l.variant_id) : -1;
  // another option than the room's: its own photo or none, never the room option's photo in another colour
  const img = o && i >= 0 && !o.skus[i]!.in_room ? optionPhoto(p.id, i) : o && i < 0 ? null : supplierImage(p.id);
  return img ? mediaUrl(img.src, undefined, 'webp') : null;
}

/**
 * S8, §9.5 "החדר שלך"; S12, QA ת21 (fidelity first): each line is drawn in the house it was bought in (a line bought off
 * the room engine: the first house that renders it), and only where that house has a layer of the very variant bought.
 * A variant without a layer is never drawn in another colour: the card's picture of it, and a line that it is not in the
 * room yet. A shadow multiplies, a light screens, as the engine draws them.
 */
function YourRoom({ lines }: { lines: Line[] }) {
  const [houses, setHouses] = useState<Record<string, House | null>>({ [NORDIC]: nordic });
  const want = [...new Set([...lines.flatMap((l) => (l.house ? [l.house] : [])), ...(lines.some((l) => !l.house) ? HOUSES.map((x) => x.style) : [])])];
  useEffect(() => {
    for (const style of want) if (!(style in houses)) void loadHouse(style).then((h) => setHouses((was) => ({ ...was, [style]: h })));
  }, [want.join()]);
  if (want.some((style) => !(style in houses))) return null;
  const rooms = new Map<string, { house: House; picks: Placed[] }>();
  const missing: { line: Line; img: string | null }[] = [];
  for (const l of lines) {
    const candidates = l.house ? [houses[l.house]] : HOUSES.map((x) => houses[x.style]);
    let at: { house: House; place: Placed } | null = null;
    for (const h of candidates) {
      const place = h ? placeOf(h, l) : null;
      if (h && place) {
        at = { house: h, place };
        break;
      }
    }
    if (!at) {
      missing.push({ line: l, img: cardImage(l.house ? houses[l.house] : null, l) });
      continue;
    }
    const r = rooms.get(at.house.style) ?? { house: at.house, picks: [] };
    if (!r.picks.some((p) => p.slot === at.place.slot)) r.picks.push(at.place);
    rooms.set(at.house.style, r);
  }
  if (!rooms.size && !missing.length) return null;
  return (
    <div class="your-rooms">
      {[...rooms.values()].map(({ house, picks }) => (
        <RoomFigure key={house.style} house={house} picks={picks} />
      ))}
      {missing.length ? (
        <ul class="your-room-missing" aria-label="פריטים שעוד לא בהדמיה">
          {missing.map(({ line, img }, i) => (
            <li key={i} data-variant={line.variant_id}>
              {img ? <img src={img} alt="" width={64} height={64} loading="lazy" decoding="async" /> : <span class="your-room-noimg" aria-hidden="true" />}
              <span>
                {lineName(line.name_he, lineLabelHe(line))}
                <span class="small muted"> · עוד לא מופיע בהדמיה של החדר.</span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function RoomFigure({ house, picks }: { house: House; picks: Placed[] }) {
  const sc = house.scene;
  const base = sc.base[0]!;
  const at = (set: SceneLayerSet, pos: number, cls: string) => {
    const [x0, x1, y0, y1] = set.rect;
    const src = set.src[pos - 1];
    return src ? (
      <img
        class={`your-room-layer ${cls}`}
        src={mediaUrl(src, sc.widths.lo, 'webp')}
        alt=""
        loading="lazy"
        decoding="async"
        style={{ left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%` }}
      />
    ) : null;
  };
  const cap = `your-room-cap-${house.style}`;
  return (
    <figure class="your-room" aria-labelledby={cap} data-house={house.style}>
      <div class="your-room-frame">
        <Picture src={base.src} widths={base.widths} sizes="(min-width: 1024px) 58vw, 100vw" alt="" loading="lazy" />
        {[...picks]
          .sort((a, b) => a.z - b.z)
          .map((p) => (
            <span key={p.slot} data-slot={p.slot} data-position={p.position}>
              {p.layer.shadow ? at(p.layer.shadow, p.position, 'is-multiply') : null}
              {at(p.layer.product!, p.position, '')}
              {p.layer.light ? at(p.layer.light, p.position, 'is-screen') : null}
            </span>
          ))}
      </div>
      <figcaption id={cap} class="small muted">
        הדמיה: {house.room.name_he} · {house.name_he}. מה שהזמנת, בגוון שהזמנת.
      </figcaption>
    </figure>
  );
}
import { lineLabelHe } from './lineLabel';

/**
 * S13 (3.3): the shipments that left, as the supplier reported them: "נשלחה" with its number, then "נמסרה". The link is
 * there only when the server passed it (a generic tracker that names no supplier); otherwise the number alone.
 */
function Tracking({ shipments }: { shipments: NonNullable<OrderView['shipments']> }) {
  return (
    <ul class="order-tracking" aria-label="משלוחים">
      {shipments.map((s, i) => (
        <li key={i}>
          <span class="status-pill">{s.status_he}</span>
          {s.tracking_number ? (
            <span>
              {' '}
              · מספר משלוח:{' '}
              <span class="num" dir="ltr">
                {s.tracking_number}
              </span>
            </span>
          ) : null}
          {s.tracking_url ? (
            <a class="order-track-link" href={s.tracking_url} target="_blank" rel="external noopener noreferrer">
              מעקב אחרי המשלוח<span class="sr-only"> (נפתח בחלון חדש)</span>
            </a>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

export function OrderPage({ id }: { id: string }) {
  const [order, setOrder] = useState<OrderView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = orderToken(id);
    if (!token) {
      setError('אין לנו גישה להזמנה הזו מהדפדפן הזה. את פרטי ההזמנה שלחנו לאימייל שלכם.');
      return;
    }
    let tries = 0;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const poll = async () => {
      try {
        const o = await api.getOrder(id, token);
        setOrder(o);
        if (o.status === 'pending_payment' && ++tries < 10) timer = setTimeout(() => void poll(), 1500);
      } catch (e) {
        setError(e instanceof ApiError && e.status === 404 ? 'ההזמנה לא נמצאה.' : 'לא הצלחנו לטעון את ההזמנה. נסו לרענן את הדף.');
      }
    };
    void poll();
    return () => clearTimeout(timer);
  }, [id]);

  const paid = order && order.status !== 'pending_payment' && order.status !== 'payment_failed';
  const closed = order?.status === 'canceled' || order?.status === 'refunded';
  const step = order ? orderStep(order.status) : null;
  return (
    <div class="wrap page">
      <div class="page-head">
        <h1 tabIndex={-1}>
          {order?.status === 'canceled' ? 'ההזמנה בוטלה.' : order?.status === 'refunded' ? 'ההזמנה זוכתה.' : paid ? 'תודה. ההזמנה התקבלה.' : `הזמנה ${id}`}
        </h1>
      </div>
      {error ? (
        <p class="notice error" role="alert">
          {error}
        </p>
      ) : !order ? (
        <p role="status">טוען את ההזמנה…</p>
      ) : (
        // §9.5: lines, not a card; the order number in figures only, without a prefix (ART6)
        <div class="order-sheet">
          <p>
            מספר הזמנה: <strong class="num">{order.id.replace(/^\D+/, '')}</strong>
          </p>
          {paid && !closed ? <YourRoom lines={order.lines} /> : null}
          {step !== null ? (
            <ol class="order-steps" aria-label={`מצב ההזמנה: ${order.status_he}`}>
              {ORDER_STEPS_HE.map((s, i) => (
                <li key={s} aria-current={i === step ? 'step' : undefined} class={i < step ? 'done' : ''}>
                  {s}
                </li>
              ))}
            </ol>
          ) : (
            <p role="status">
              סטטוס: <span class="status-pill">{order.status_he}</span>
            </p>
          )}
          {order.shipments?.length ? <Tracking shipments={order.shipments} /> : null}
          {order.refunded_agorot ? (
            <p class="order-refund">
              הוחזרו לאמצעי התשלום: <Price agorot={order.refunded_agorot} />. הזיכוי מופיע לפי מועדי חברת האשראי.
            </p>
          ) : null}
          <ul class="order-lines">
            {order.lines.map((l, i) => (
              <li key={i}>
                {lineName(l.name_he, lineLabelHe(l))} × {l.qty} · <Price agorot={l.line_total_agorot} />
              </li>
            ))}
          </ul>
          <dl>
            <dt class="total">סה"כ שולם</dt>
            <dd class="total">
              <Price agorot={order.total_agorot} />
            </dd>
          </dl>
          {paid && !closed ? (
            <p class="small muted">
              {step === 3
                ? 'ההזמנה נמסרה. אם משהו לא כפי שציפיתם, כתבו לנו.'
                : step === 2
                  ? 'ההזמנה בדרך אליכם. מספר המשלוח למעלה.'
                  : 'אישור וחשבונית מס יישלחו לאימייל. נעדכן כשההזמנה יוצאת למשלוח.'}
            </p>
          ) : null}
          {order.status === 'payment_failed' ? (
            <p>
              <a href="/cart/">חזרה לסל</a>
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}
