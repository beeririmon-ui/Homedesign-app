/**
 * Payment webhooks and the mock hosted payment page.
 * The order is marked paid only here, after the signature, the amount and the idempotency key check out.
 * The browser's return to /order/<id>/ never changes order state.
 */
import { Hono } from 'hono';
import { formatIls, randomToken, sha256Hex } from '@hd/shared';
import type { AppEnv, Env } from '../env';
import { HttpError, nowIso } from '../lib/http';
import { paymentProvider } from '../lib/payments';
import { MOCK_SIGNATURE_HEADER, signMockEvent } from '../lib/payments/mock';
import type { PaymentEvent } from '../lib/payments/types';

export const webhooks = new Hono<AppEnv>();

export async function handlePaymentEvent(env: Env, providerId: string, event: PaymentEvent, bodySha: string): Promise<{ outcome: string; duplicate: boolean }> {
  const now = nowIso();
  const inserted = await env.DB.prepare(
    `INSERT INTO payment_events (id, provider, provider_event_id, type, amount_agorot, signature_ok, body_sha256, received_at)
     VALUES (?, ?, ?, ?, ?, 1, ?, ?) ON CONFLICT(provider, provider_event_id) DO NOTHING`,
  )
    .bind(crypto.randomUUID(), providerId, event.id, event.type, event.amount_agorot, bodySha, now)
    .run();
  if (!inserted.meta.changes) return { outcome: 'duplicate', duplicate: true };

  const order = await env.DB.prepare('SELECT id, status, total_agorot FROM orders WHERE payment_session_id = ? AND payment_provider = ?')
    .bind(event.session_id, providerId)
    .first<{ id: string; status: string; total_agorot: number }>();

  let outcome: string;
  if (!order) outcome = 'unknown_session';
  else if (event.type === 'payment.failed') {
    if (order.status === 'pending_payment') {
      await env.DB.prepare("UPDATE orders SET status = 'payment_failed', updated_at = ? WHERE id = ?").bind(now, order.id).run();
    }
    outcome = 'marked_failed';
  } else if (event.amount_agorot !== order.total_agorot) outcome = 'amount_mismatch';
  else if (order.status !== 'pending_payment' && order.status !== 'payment_failed') outcome = 'already_processed';
  else {
    await env.DB.batch([
      env.DB.prepare("UPDATE orders SET status = 'paid', paid_at = ?, updated_at = ? WHERE id = ?").bind(now, now, order.id),
      env.DB.prepare(
        "INSERT INTO supplier_orders (id, order_id, supplier, status, created_at, updated_at) VALUES (?, ?, ?, 'queued', ?, ?) ON CONFLICT(order_id, supplier) DO NOTHING",
      ).bind(crypto.randomUUID(), order.id, env.SUPPLIER_PROVIDER, now, now),
      env.DB.prepare('INSERT INTO audit_log (at, actor, action, subject, detail) VALUES (?, ?, ?, ?, ?)').bind(now, `webhook:${providerId}`, 'order.paid', order.id, JSON.stringify({ event: event.id })),
    ]);
    await env.SUPPLIER_QUEUE.send({ kind: 'submit-order', order_id: order.id });
    // Next (not in this phase): enqueue the tax invoice job with the chosen invoicing service.
    outcome = 'paid';
  }
  await env.DB.prepare('UPDATE payment_events SET order_id = ?, processed_at = ?, outcome = ? WHERE provider = ? AND provider_event_id = ?')
    .bind(order?.id ?? null, now, outcome, providerId, event.id)
    .run();
  return { outcome, duplicate: false };
}

webhooks.post('/payment/:provider', async (c) => {
  const providerId = c.req.param('provider');
  const raw = await c.req.text();
  if (raw.length > 32_768) throw new HttpError(413, 'payload_too_large');
  const provider = paymentProvider(c.env, new URL(c.req.url).origin, providerId);
  const verified = await provider.verifyWebhook(c.req.raw.headers, raw, Math.floor(Date.now() / 1000));
  if (!verified.ok) {
    console.warn('payment webhook rejected', providerId, verified.reason);
    throw new HttpError(401, 'invalid_signature');
  }
  const result = await handlePaymentEvent(c.env, provider.id, verified.event, await sha256Hex(raw));
  return c.json({ received: true, ...result });
});

// ---------- mock hosted payment page (development / preview only) ----------
export const mockPay = new Hono<AppEnv>();

mockPay.use('*', async (c, next) => {
  if (c.env.PAYMENT_PROVIDER !== 'mock' || c.env.ENVIRONMENT === 'production') throw new HttpError(404, 'not_found');
  await next();
});

const esc = (s: string) => s.replace(/[&<>"']/g, (ch) => `&#${ch.charCodeAt(0)};`);

mockPay.get('/:session', async (c) => {
  const session = c.req.param('session');
  const order = await c.env.DB.prepare("SELECT id, total_agorot, status FROM orders WHERE payment_session_id = ? AND payment_provider = 'mock'")
    .bind(session)
    .first<{ id: string; total_agorot: number; status: string }>();
  if (!order) throw new HttpError(404, 'session_not_found');
  const nonce = randomToken(12);
  c.header('Content-Security-Policy', `default-src 'none'; style-src 'nonce-${nonce}'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'`);
  return c.html(`<!doctype html><html lang="he" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>תשלום מדומה · ${esc(order.id)}</title>
<style nonce="${nonce}">body{font:17px/1.6 system-ui,sans-serif;background:#F4F1EC;color:#3A3A3A;margin:0;padding:24px;display:grid;place-items:center;min-height:100vh;box-sizing:border-box}main{max-width:420px;width:100%;background:#FBFAF7;border:1px solid #D9D6D0;border-radius:12px;padding:24px}h1{font-size:22px;margin:0 0 8px}.warn{background:#3A3A3A;color:#F4F1EC;padding:8px 12px;border-radius:8px;font-size:14px}button{font:inherit;font-weight:600;padding:14px 18px;border-radius:999px;border:1px solid #3A3A3A;width:100%;margin-top:12px;cursor:pointer}.pay{background:#3A3A3A;color:#F4F1EC}.fail{background:transparent;color:#3A3A3A}</style></head>
<body><main><p class="warn">סביבת פיתוח: זה דף תשלום מדומה. אין כאן סליקה ואין להזין פרטי אשראי.</p>
<h1>תשלום להזמנה ${esc(order.id)}</h1><p>לתשלום: <strong>${esc(formatIls(order.total_agorot))}</strong></p>
<form method="post" action="/mock-pay/${esc(session)}/complete"><button class="pay" name="outcome" value="success">אישור תשלום (מדומה)</button><button class="fail" name="outcome" value="fail">דחיית תשלום (מדומה)</button></form>
</main></body></html>`);
});

/** Plays the provider: signs the event with the webhook secret and calls our own webhook endpoint. */
mockPay.post('/:session/complete', async (c) => {
  const session = c.req.param('session');
  const form = await c.req.parseBody();
  const outcome = form.outcome === 'fail' ? 'payment.failed' : 'payment.succeeded';
  const order = await c.env.DB.prepare("SELECT id, total_agorot FROM orders WHERE payment_session_id = ? AND payment_provider = 'mock'")
    .bind(session)
    .first<{ id: string; total_agorot: number }>();
  if (!order) throw new HttpError(404, 'session_not_found');
  const secret = c.env.PAYMENT_WEBHOOK_SECRET;
  if (!secret) throw new HttpError(503, 'payment_not_configured');
  const event: PaymentEvent = { id: `mev_${randomToken(12)}`, type: outcome, session_id: session, amount_agorot: order.total_agorot };
  const { body, signature } = await signMockEvent(secret, event, Math.floor(Date.now() / 1000));
  const origin = new URL(c.req.url).origin;
  const { app } = await import('../app');
  let ctx: ExecutionContext | undefined;
  try {
    ctx = c.executionCtx;
  } catch {
    ctx = undefined; // unit tests run without an execution context
  }
  const res = await app.fetch(
    new Request(`${origin}/api/webhooks/payment/mock`, { method: 'POST', headers: { 'content-type': 'application/json', [MOCK_SIGNATURE_HEADER]: signature }, body }),
    c.env,
    ctx,
  );
  if (!res.ok) throw new HttpError(502, 'mock_webhook_failed');
  return c.redirect(outcome === 'payment.succeeded' ? `/order/${order.id}/` : `/checkout/?failed=1`, 303);
});
