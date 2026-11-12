import { Hono } from 'hono';
import type { AppEnv } from './env';
import { HttpError, PRIVATE_PAGE_CSP, SITE_CSP, securityHeaders } from './lib/http';
import { publicApi } from './routes/public';
import { webhooks, mockPay } from './routes/payments';
import { admin } from './routes/admin';
import { adminList, adminUi } from './routes/admin-ui';
import { requireAdmin } from './lib/access';
import { health } from './routes/health';
import { configureLog, errorMessageHe, orderIdInPath, orderLog } from './lib/log';

export const app = new Hono<AppEnv>();

// S17 (QA ת46): the log's rule for this environment (production: an error of an unknown order by name and code only)
app.use('*', async (c, next) => {
  configureLog(c.env);
  await next();
});
app.use('*', securityHeaders);
app.route('/api', publicApi);
app.route('/api/webhooks', webhooks);
app.route('/api/admin', admin);
// S13 (6.3): the admin screen, behind the same gate (Access); rendered here, never part of the public build
app.route('/admin', adminUi);
app.get('/admin/', requireAdmin, adminList);
// S13 (6.2): the uptime clock's endpoint; no secrets and no internal details
app.route('/healthz', health);
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
      // S17 (AN1): never the analytics beacon on the order page
      'content-security-policy': PRIVATE_PAGE_CSP,
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

/**
 * S13 (6.2): an error the request cannot recover from is a structured row (lib/log.ts: an error id, no PII), and the
 * customer gets a short message with that id, so a message to the shop finds the row.
 */
app.onError(async (err, c) => {
  if (err instanceof HttpError) return c.json({ error: err.code, message_he: err.messageHe }, err.status);
  const url = new URL(c.req.url);
  // S17 (ת46): an order in the path is a known order: its customer's values leave the row
  const l = await orderLog(c.env.DB, orderIdInPath(url.pathname));
  const error_id = l.error('request.unhandled', { method: c.req.method, path: url.pathname.slice(0, 120) }, err);
  return c.json({ error: 'internal_error', error_id, message_he: errorMessageHe(error_id, c.env) }, 500);
});

app.notFound((c) => (c.env.ASSETS ? c.env.ASSETS.fetch(c.req.raw) : c.json({ error: 'not_found' }, 404)));
