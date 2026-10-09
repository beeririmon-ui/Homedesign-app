import { Hono } from 'hono';
import type { AppEnv } from './env';
import { HttpError, SITE_CSP, securityHeaders } from './lib/http';
import { publicApi } from './routes/public';
import { webhooks, mockPay } from './routes/payments';
import { admin } from './routes/admin';

export const app = new Hono<AppEnv>();

app.use('*', securityHeaders);
app.route('/api', publicApi);
app.route('/api/webhooks', webhooks);
app.route('/api/admin', admin);
app.route('/mock-pay', mockPay);
// Buyer order pages share one prerendered shell; the client reads the id from the URL.
app.get('/order/*', async (c) => {
  if (!c.env.ASSETS) throw new HttpError(404, 'not_found');
  const ok = /^\/order\/HD-[A-Z0-9]{8}\/?$/.test(new URL(c.req.url).pathname);
  const res = await c.env.ASSETS.fetch(new Request(new URL(ok ? '/order/' : '/404.html', c.req.url)));
  return new Response(res.body, {
    status: ok ? res.status : 404,
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-store',
      'x-robots-tag': 'noindex',
      'content-security-policy': SITE_CSP,
    },
  });
});
app.all('/api/*', () => {
  throw new HttpError(404, 'not_found');
});

app.onError((err, c) => {
  if (err instanceof HttpError) return c.json({ error: err.code, message_he: err.messageHe }, err.status);
  console.error('unhandled', err);
  return c.json({ error: 'internal_error', message_he: 'משהו השתבש. נסו שוב.' }, 500);
});

app.notFound((c) => (c.env.ASSETS ? c.env.ASSETS.fetch(c.req.raw) : c.json({ error: 'not_found' }, 404)));
