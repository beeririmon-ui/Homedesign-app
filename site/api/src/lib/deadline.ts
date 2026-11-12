/**
 * S14, QA ת31: a call to an outside provider (the invoice provider, the supplier) never outlives its claim.
 *
 * A claim (an invoice row, a supplier shipment in `submitting`) stands for a lease (10 minutes) before another run may
 * treat it as left behind by a crash and take it over. A Queue job may run for up to 15 minutes, so a call that hangs
 * could outlive the lease: a second run takes the claim over, asks the provider (nothing yet), and calls again. Two
 * invoices, or two supplier orders. So every such call has a deadline far below the lease: past it the call is aborted
 * (its `signal` fires, for a provider that passes it to fetch) and the run treats it as a failure that may have issued
 * something: the claim stays, and once the lease is over the next run asks the provider before it calls again.
 */
import { OwnError } from './errors';

/** The deadline of one call to a provider: far below every lease that guards it (CALL_TIMEOUT_MS × 5 ≤ lease). */
export const PROVIDER_CALL_TIMEOUT_MS = 60_000;

/** The call did not answer in time: it may still have done its work at the provider, so it is never a refusal. */
export class CallTimedOut extends OwnError {
  constructor(what: string, ms: number) {
    super(`${what}: no answer within ${ms < 1000 ? `${ms} ms` : `${Math.round(ms / 1000)} s`} (aborted; it may still have been done at the provider)`);
    this.name = 'CallTimedOut';
  }
}

/**
 * Runs `call` with a deadline. The call gets an AbortSignal that fires at the deadline; whatever the call does after it
 * is ignored here (the promise this returns has already rejected with CallTimedOut).
 */
export async function withDeadline<T>(what: string, ms: number, call: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const ac = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const late = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      const err = new CallTimedOut(what, ms);
      ac.abort(err);
      reject(err);
    }, ms);
  });
  try {
    return await Promise.race([call(ac.signal), late]);
  } finally {
    clearTimeout(timer);
  }
}
