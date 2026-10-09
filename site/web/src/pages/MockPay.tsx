/**
 * Artifact preview only: an in-browser stand-in for the PSP's hosted payment page. On the site the Worker serves
 * /mock-pay/* (dev and preview only) and completes the payment through the signed webhook.
 */
import { useEffect, useState } from 'preact/hooks';
import { api } from '../api';
import { navigate } from '../router';
import { Price } from '../components/Media';

export function MockPay({ session }: { session: string }) {
  const [info, setInfo] = useState<{ order_id: string; total_agorot: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    if (!api.mockPay) {
      setMissing(true);
      return;
    }
    api.mockPay.info(session).then(setInfo, () => setMissing(true));
  }, [session]);

  async function done(outcome: 'success' | 'fail') {
    if (!api.mockPay) return;
    setBusy(true);
    navigate(await api.mockPay.complete(session, outcome));
  }

  return (
    <div class="wrap page">
      <div class="card summary" style={{ maxWidth: 460, marginInline: 'auto' }}>
        <p class="notice warn">תצוגה מקדימה: זה דף תשלום מדומה. אין כאן סליקה ואין להזין פרטי אשראי.</p>
        <h1 tabIndex={-1}>{info ? `תשלום להזמנה ${info.order_id}` : 'תשלום מדומה'}</h1>
        {missing ? (
          <p role="alert">דף התשלום לא נמצא.</p>
        ) : info ? (
          <>
            <p>
              לתשלום: <Price class="price-big" agorot={info.total_agorot} />
            </p>
            <button type="button" class="btn btn-primary" disabled={busy} onClick={() => void done('success')}>
              אישור תשלום (מדומה)
            </button>
            <button type="button" class="btn btn-ghost" disabled={busy} onClick={() => void done('fail')}>
              דחיית תשלום (מדומה)
            </button>
          </>
        ) : (
          <p role="status">טוען…</p>
        )}
      </div>
    </div>
  );
}
