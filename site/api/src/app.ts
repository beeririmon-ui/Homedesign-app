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
  const ok = /^\/order\/[1-9]\d{9}\/?$/.test(new URL(c.req.url).pathname);
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
/**
 * S10 question 7 (S11): a room's address naming another house of the engine (?style=<id>) is served that house's own
 * prerendered page (web/dist/house/<room>/<style>/, scripts/prerender.ts): it waits for the house and carries no Nordic
 * poster, so a direct entry downloads nothing for nothing. Every other room address is the static page, as it was.
 */
app.get('/rooms/:room/', async (c) => {
  if (!c.env.ASSETS) throw new HttpError(404, 'not_found');
  const room = c.req.param('room');
  const style = new URL(c.req.url).searchParams.get('style');
  let res: Response | null = null;
  if (style && /^[a-z][a-z-]{0,39}$/.test(style) && /^[a-z0-9-]{1,40}$/.test(room)) {
    const own = await c.env.ASSETS.fetch(new Request(new URL(`/house/${room}/${style}/`, c.req.url)));
    if (own.ok) res = own;
  }
  res ??= await c.env.ASSETS.fetch(c.req.raw);
  const out = new Response(res.body, res);
  // the page's own CSP (the static assets get theirs from _headers; a response through the Worker sets it here)
  if ((out.headers.get('content-type') ?? '').includes('text/html')) out.headers.set('Content-Security-Policy', SITE_CSP);
  return out;
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
