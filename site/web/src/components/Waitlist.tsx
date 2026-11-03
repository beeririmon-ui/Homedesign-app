/**
 * "המלאי אינו זמין כעת" (PRE1, decisions NL2 / AU2 / R6Q2; site art direction §6.8): no disabled button. The customer
 * reads why there is no cart button, and can leave one email to be told when the product is back. The line under the
 * field says what the address is for (nothing else is collected).
 */
import { useState } from 'preact/hooks';
import { EMAIL } from '@hd/shared/constants';
import { api, ApiError } from '../api';

type Props = { product_id?: string; room?: string; slot?: string; id: string; onStage?: boolean };

export function Waitlist({ product_id, room, slot, id, onStage }: Props) {
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState('');
  const [state, setState] = useState<'idle' | 'busy' | 'done'>('idle');
  const [error, setError] = useState<string | null>(null);

  async function submit(e: Event) {
    e.preventDefault();
    if (!EMAIL.test(email.trim())) {
      setError('כתובת האימייל לא תקינה.');
      return;
    }
    setError(null);
    setState('busy');
    try {
      await api.waitlist({ email: email.trim(), product_id, room, slot });
      setState('done');
    } catch (err) {
      setState('idle');
      setError(err instanceof ApiError ? (err.messageHe ?? 'לא הצלחנו לשמור את הבקשה. נסו שוב.') : 'לא הצלחנו לשמור את הבקשה. נסו שוב.');
    }
  }

  return (
    <div class={`waitlist${onStage ? ' on-stage' : ''}`}>
      <p class="waitlist-status">המלאי אינו זמין כעת</p>
      {state === 'done' ? (
        <p class="small" role="status">
          נרשמתם. נשלח הודעה אחת כשהמוצר חוזר.
        </p>
      ) : !open ? (
        <button type="button" class="btn btn-ghost" onClick={() => setOpen(true)}>
          עדכנו אותי כשחוזר
        </button>
      ) : (
        <form class="waitlist-form" onSubmit={(e) => void submit(e)} noValidate>
          <label htmlFor={`${id}-email`}>אימייל</label>
          <input
            id={`${id}-email`}
            type="email"
            inputMode="email"
            autocomplete="email"
            value={email}
            onInput={(e) => setEmail((e.currentTarget as HTMLInputElement).value)}
            aria-describedby={`${id}-why`}
            aria-invalid={error ? 'true' : undefined}
            required
          />
          <p id={`${id}-why`} class="small muted">
            נשלח הודעה אחת כשהמוצר חוזר למלאי. הכתובת לא תשמש לשום דבר אחר.
          </p>
          {error ? (
            <p class="small field-error" role="alert">
              ⚠ {error}
            </p>
          ) : null}
          <button type="submit" class="btn btn-primary" disabled={state === 'busy'} aria-busy={state === 'busy' ? 'true' : undefined}>
            {state === 'busy' ? 'רגע…' : 'עדכנו אותי'}
          </button>
        </form>
      )}
    </div>
  );
}
