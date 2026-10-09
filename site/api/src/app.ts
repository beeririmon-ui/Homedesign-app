import { Hono } from 'hono';
import type { AppEnv } from './env';
import { HttpError, securityHeaders } from './lib/http';
import { publicApi } from './routes/public';
import { webhooks, mockPay } from './routes/payments';
import { admin } from './routes/admin';

export const app = new Hono<AppEnv>();

app.use('*', securityHeaders);
app.route('/api', publicApi);
app.route('/api/webhooks', webhooks);
app.route('/api/admin', admin);
app.route('/mock-pay', mockPay);
app.all('/api/*', () => {
  throw new HttpError(404, 'not_found');
});

app.onError((err, c) => {
  if (err instanceof HttpError) return c.json({ error: err.code, message_he: err.messageHe }, err.status);
  console.error('unhandled', err);
  return c.json({ error: 'internal_error', message_he: 'משהו השתבש. נסו שוב.' }, 500);
});

app.notFound((c) => (c.env.ASSETS ? c.env.ASSETS.fetch(c.req.raw) : c.json({ error: 'not_found' }, 404)));
