/**
 * Order status for the buyer. The return from the payment page never changes state: the status shown here comes
 * from the server, which marks an order paid only from the signed webhook. Polls briefly while payment is pending.
 */
import { useEffect, useState } from 'preact/hooks';
import type { OrderView } from '@hd/shared';
import { ORDER_STEPS_HE, orderStep } from '@hd/shared/constants';
import { lineName, splitLineName } from '@hd/shared/lines';
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

/** a line drawn in a house: the slot's option it is drawn with, and every line of the order drawn by that option */
type Pick = Placed & { lines: Line[] };
/** a line of the order that is in no picture: no house renders it, or its place shows another option the order holds */
type Unshown = { line: Line; img: string | null; instead: string | null; style: string | null };

/**
 * S8, §9.5 "החדר שלך"; S12, QA ת21 (fidelity first): each line is drawn in the house it was bought in (a line bought off
 * the room engine: the first house that renders it), and only where that house has a layer of the very variant bought.
 * A variant without a layer is never drawn in another colour: the card's picture of it, and a line that it has none.
 * A shadow multiplies, a light screens, as the engine draws them.
 *
 * S14, QA ת28: every line of the order is accounted for. A picture draws one option per slot (the first the order
 * holds); a line whose place already shows another option is listed under the pictures with its own picture and the
 * reason, never dropped.
 *
 * S15, master-designer's copy (docs/proposals/your-room-copy-2026-11-11.md §1): the caption describes the picture only;
 * what was ordered and is not in it is in the list under it, which opens with its own line ("בהזמנה, ולא בהדמיה:").
 * "עם מה שהזמנתם, בגוונים שבחרתם" is said only when the list is empty and no set is drawn whole.
 */
function YourRoom({ lines }: { lines: Line[] }) {
  const [houses, setHouses] = useState<Record<string, House | null>>({ [NORDIC]: nordic });
  const want = [...new Set([...lines.flatMap((l) => (l.house ? [l.house] : [])), ...(lines.some((l) => !l.house) ? HOUSES.map((x) => x.style) : [])])];
  useEffect(() => {
    for (const style of want) if (!(style in houses)) void loadHouse(style).then((h) => setHouses((was) => ({ ...was, [style]: h })));
  }, [want.join()]);
  if (want.some((style) => !(style in houses))) return null;
  const rooms = new Map<string, { house: House; picks: Pick[] }>();
  const unshown: Unshown[] = [];
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
      unshown.push({ line: l, img: cardImage(l.house ? houses[l.house] : null, l), instead: null, style: null });
      continue;
    }
    const r = rooms.get(at.house.style) ?? { house: at.house, picks: [] };
    rooms.set(at.house.style, r);
    const taken = r.picks.find((p) => p.slot === at.place.slot);
    // the same option (two pieces of one set): drawn by the same layer
    if (taken?.position === at.place.position) taken.lines.push(l);
    // another option of the same slot: one picture draws one option per slot; this one is listed, with what is drawn there
    else if (taken) unshown.push({ line: l, img: cardImage(at.house, l), instead: drawnName(at.house, taken, l), style: at.house.style });
    else r.picks.push({ ...at.place, lines: [l] });
  }
  if (!rooms.size && !unshown.length) return null;
  const pictured = rooms.size > 0;
  return (
    <div class="your-rooms">
      {[...rooms.values()].map(({ house, picks }) => (
        <RoomFigure key={house.style} house={house} picks={picks} listed={unshown.length > 0} />
      ))}
      {unshown.length ? (
        <div class="your-room-list">
          {/* the list's lead is its name; without any picture on the page it says so, and the rows give no reason */}
          <p id="your-room-missing-title" class="small your-room-lead">
            {pictured ? 'בהזמנה, ולא בהדמיה:' : 'לפריטים שהזמנתם אין הדמיה בחדר.'}
          </p>
          <ul class="your-room-missing" aria-labelledby="your-room-missing-title">
            {unshown.map(({ line, img, instead }, i) => (
              <li key={i} data-variant={line.variant_id} data-why={instead ? 'slot-taken' : 'no-layer'}>
                {img ? <img src={img} alt="" width={64} height={64} loading="lazy" decoding="async" /> : <span class="your-room-noimg" aria-hidden="true" />}
                <span>
                  {lineName(line.name_he, lineLabelHe(line))}
                  {instead || pictured ? <span class="small muted your-room-why">{whyHe(line, instead)}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

/** a line's base name and its labels (the option the order's name carries, and the pack), §1.1 rows 3, 8 and 9 */
function partsOf(l: Line): { base: string; label: string } {
  const { base, label } = splitLineName(l.name_he);
  return { base, label: [label, lineLabelHe(l)].filter(Boolean).join(', ') };
}

/** §1.1 rows 7 and 8: why a listed line is not in the picture, on its own line under the name */
function whyHe(l: Line, instead: string | null): string {
  if (instead) return `בהדמיה, באותו מקום: ${instead}.`;
  return partsOf(l).label ? 'אין הדמיה לאפשרות הזו.' : 'אין הדמיה לפריט הזה.';
}

/**
 * §1.1 rows 9–11: what the picture shows in the place of a listed line. A set: its name ("סט קאמל ופקאן",
 * else "סט אחר"); otherwise the base name of what is drawn, with its option only when the listed line has the same base
 * name (two shades of one cushion), so the two can be told apart.
 */
function drawnName(house: House, p: Pick, row: Line): string {
  if (house.drawn(p.slot, p.position).length > 1) return house.drawnLabel?.(p.slot, p.position) ?? 'סט אחר';
  const mine = partsOf(row).base;
  const names = p.lines.map((l) => {
    const { base, label } = partsOf(l);
    return base === mine && label ? `${base}, ${label}` : base;
  });
  return [...new Set(names)].join(', ');
}
/** the pieces an option's layer draws that the order does not hold (a set drawn whole) */
function extras(house: House, p: Pick): string[] {
  const bought = new Set(p.lines.map((l) => l.variant_id));
  return house.drawn(p.slot, p.position).filter((v) => !bought.has(v));
}

/**
 * S15 (§1.1 rows 1–5): the caption says what the picture shows, in the house's own words for the place ("הסלון בבית
 * הנורדי"). A set drawn whole says how much of it was ordered; "what you ordered" only when that is all the order holds.
 */
function captionOf(house: House, picks: Pick[], listed: boolean): string {
  const sets = picks.filter((p) => extras(house, p).length);
  if (!sets.length && !listed) return `הדמיה: ${house.place_he}, עם מה שהזמנתם, בגוונים שבחרתם.`;
  const parts = sets.map((p) => {
    const set = house.drawnLabel?.(p.slot, p.position) ?? 'הסט';
    const ordered = [...new Set(p.lines.map((l) => l.variant_id))];
    const all = house.drawn(p.slot, p.position).length;
    return ordered.length === 1
      ? `${set} מוצג כולו; הזמנתם ממנו פריט אחד: ${partsOf(p.lines[0]!).base}.`
      : `${set} מוצג כולו; הזמנתם ממנו ${ordered.length} פריטים מתוך ${all}.`;
  });
  return [`הדמיה: ${house.place_he}.`, ...parts].join(' ');
}

function RoomFigure({ house, picks, listed }: { house: House; picks: Pick[]; listed: boolean }) {
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
    <figure class="your-room" aria-labelledby={cap} data-house={house.style} data-drawn={picks.flatMap((p) => p.lines.map((l) => l.variant_id)).join(' ')}>
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
        {captionOf(house, picks, listed)}
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
