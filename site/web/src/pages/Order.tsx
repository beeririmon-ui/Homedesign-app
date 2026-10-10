/**
 * Order status for the buyer. The return from the payment page never changes state: the status shown here comes
 * from the server, which marks an order paid only from the signed webhook. Polls briefly while payment is pending.
 */
import { useEffect, useState } from 'preact/hooks';
import type { OrderView } from '@hd/shared';
import { api, ApiError } from '../api';
import { orderToken } from '../state/cart';
import { Price } from '../components/Media';
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
  return (
    <div class="wrap page">
      <div class="page-head">
        <h1 tabIndex={-1}>{paid ? 'תודה, ההזמנה התקבלה' : `הזמנה ${id}`}</h1>
      </div>
      {error ? (
        <p class="notice error" role="alert">
          {error}
        </p>
      ) : !order ? (
        <p role="status">טוען את ההזמנה…</p>
      ) : (
        <div class="card summary" style={{ maxWidth: 560 }}>
          <p>
            מספר הזמנה: <strong class="num">{order.id}</strong>
          </p>
          <p role="status">
            סטטוס: <span class="status-pill">{order.status_he}</span>
          </p>
          <ul style={{ margin: 0, paddingInlineStart: 18 }}>
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
