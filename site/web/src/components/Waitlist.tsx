/**
 * "המלאי אינו זמין כעת" (PRE1, decisions NL2 / AU2 / R6Q2; site art direction §6.8): no disabled button. The customer
 * reads why there is no cart button, and can leave one email to be told when the product is back. The line under the
 * field says what the address is for (nothing else is collected).
 *
 * S18: the form promises an email ("נשלח הודעה אחת כשהמוצר חוזר"), so it is offered only where an email provider really
 * sends it (site/copy, the group `waitlist`). While none does (EMAIL_PROVIDER=UNDECIDED, today) the customer reads the
 * line "המלאי אינו זמין כעת" alone, and no address is asked for.
 */
import { useState } from 'preact/hooks';
import { EMAIL } from '@hd/shared/constants';
import { api, ApiError } from '../api';
import { copyHe } from '../copy';

const OFFER = copyHe('waitlist.offer');
const WHY = copyHe('waitlist.why');
const SUBMIT = copyHe('waitlist.submit');
const DONE = copyHe('waitlist.done');

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
      {!OFFER ? null : state === 'done' ? (
        <p class="small" role="status">
          {DONE}
        </p>
      ) : !open ? (
        <button type="button" class="btn btn-ghost" onClick={() => setOpen(true)}>
          {OFFER}
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
            {WHY}
          </p>
          {error ? (
            <p class="small field-error" role="alert">
              ⚠ {error}
            </p>
          ) : null}
          <button type="submit" class="btn btn-primary" disabled={state === 'busy'} aria-busy={state === 'busy' ? 'true' : undefined}>
            {state === 'busy' ? 'רגע…' : SUBMIT}
          </button>
        </form>
      )}
    </div>
  );
}
