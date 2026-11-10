/**
 * Order status for the buyer. The return from the payment page never changes state: the status shown here comes
 * from the server, which marks an order paid only from the signed webhook. Polls briefly while payment is pending.
 */
import { useEffect, useState } from 'preact/hooks';
import type { OrderView } from '@hd/shared';
import { ORDER_STEPS_HE, orderStep } from '@hd/shared/constants';
import { api, ApiError } from '../api';
import { orderToken } from '../state/cart';
import { Picture, Price } from '../components/Media';
import { livingRoom, scene } from '../catalog';
import { mediaUrl } from '../media';
import type { SceneLayerSet } from '../engine/types';

/**
 * S8, §9.5 "החדר שלך": the room's composite with the variations the customer ordered, made from the room's own layers
 * (the same rects the engine draws), so it shows only products that exist. A shadow multiplies, a light screens. No
 * ordered product on the room's wheel: nothing is drawn.
 */
function YourRoom({ lines }: { lines: OrderView['lines'] }) {
  const picks = livingRoom.slots.flatMap((s) => {
    const o = s.options.find((x) => !!x.product_id && lines.some((l) => l.product_id === x.product_id));
    const layer = scene.slots[s.id];
    return o && layer?.product ? [{ id: s.id, pos: o.position, layer }] : [];
  });
  if (!picks.length) return null;
  const base = scene.base[0]!;
  const at = (set: SceneLayerSet, pos: number, cls: string) => {
    const [x0, x1, y0, y1] = set.rect;
    const src = set.src[pos - 1] ?? set.src[0];
    return src ? (
      <img
        class={`your-room-layer ${cls}`}
        src={mediaUrl(src, scene.widths.lo, 'webp')}
        alt=""
        loading="lazy"
        decoding="async"
        style={{ left: `${x0 * 100}%`, top: `${y0 * 100}%`, width: `${(x1 - x0) * 100}%`, height: `${(y1 - y0) * 100}%` }}
      />
    ) : null;
  };
  return (
    <figure class="your-room" aria-labelledby="your-room-cap">
      <div class="your-room-frame">
        <Picture src={base.src} widths={base.widths} sizes="(min-width: 1024px) 58vw, 100vw" alt="" loading="lazy" />
        {[...picks]
          .sort((a, b) => a.layer.z - b.layer.z)
          .map((p) => (
            <span key={p.id}>
              {p.layer.shadow ? at(p.layer.shadow, p.pos, 'is-multiply') : null}
              {at(p.layer.product!, p.pos, '')}
              {p.layer.light ? at(p.layer.light, p.pos, 'is-screen') : null}
            </span>
          ))}
      </div>
      <figcaption id="your-room-cap" class="small muted">
        הדמיה: {livingRoom.name_he}, כפי שהרכבת אותו.
      </figcaption>
    </figure>
  );
}
import { lineLabelHe } from './lineLabel';

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
  const step = order ? orderStep(order.status) : null;
  return (
    <div class="wrap page">
      <div class="page-head">
        <h1 tabIndex={-1}>{paid ? 'תודה. ההזמנה התקבלה.' : `הזמנה ${id}`}</h1>
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
          {paid ? <YourRoom lines={order.lines} /> : null}
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
          <ul class="order-lines">
            {order.lines.map((l, i) => (
              <li key={i}>
                {l.name_he}
                {lineLabelHe(l) ? ` (${lineLabelHe(l)})` : ''} × {l.qty} · <Price agorot={l.line_total_agorot} />
              </li>
            ))}
          </ul>
          <dl>
            <dt class="total">סה"כ שולם</dt>
            <dd class="total">
              <Price agorot={order.total_agorot} />
            </dd>
          </dl>
          {paid ? <p class="small muted">אישור וחשבונית מס יישלחו לאימייל. נעדכן כשההזמנה יוצאת למשלוח.</p> : null}
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
