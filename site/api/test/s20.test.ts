/**
 * S20 (QA S18): the Worker accepts only what is real.
 * - ת57: with no provider that sends it, `/api/waitlist` refuses (409 `waitlist_closed`) and stores nothing, and
 *   `/api/checkout` never records a consent to marketing email. With a provider that declares the capability, both work.
 * - ת62: the declaration is per capability: a provider that sends only the order confirmation opens neither.
 * - ת61: the contact details in the deploy check, and the Worker's one "כתבו לנו" line, only with an email to write to.
 *
 * The test providers are declared here only (vi.mock below), the way an adapter will declare its own (@hd/shared/email).
 */
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { contactIssues, contactOf, isPlaceholderEmail } from '@hd/shared/contact';
import { app } from '../src/app';
import type { Env, SupplierJob } from '../src/env';
import { contactConfigIssues } from '../src/lib/config';
import { errorMessageHe } from '../src/lib/log';
import { buildSeedSql } from '../scripts/seed';
import { parseJsonc } from '../scripts/jsonc';
import { createD1, migrate } from './d1-shim';
import { catalog } from './fixture';

vi.mock('@hd/shared/email', async (orig) => {
  const m = await orig<typeof import('@hd/shared/email')>();
  const TEST: import('@hd/shared/email').EmailProviders = {
    'qa-all': [...m.EMAIL_CAPABILITIES],
    'qa-confirm-only': ['order_confirmation'],
  };
  return {
    ...m,
    EMAIL_PROVIDERS: TEST,
    emailProviderIssue: (v: unknown) => m.emailProviderIssue(v, TEST),
    emailCapabilities: (v: unknown) => m.emailCapabilities(v, TEST),
    canEmail: (v: unknown, c: import('@hd/shared/email').EmailCapability) => m.canEmail(v, c, TEST),
    emailSends: (v: unknown) => m.emailSends(v, TEST),
  };
});

const API = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const TSX = resolve(API, '../node_modules/tsx/dist/cli.mjs');
const wrangler = readFileSync(join(API, 'wrangler.jsonc'), 'utf8');

let env: Env;
beforeEach(() => {
  const DB = createD1();
  migrate(DB, buildSeedSql(catalog));
  env = {
    DB,
    SUPPLIER_QUEUE: { send: vi.fn(async (_m: SupplierJob) => undefined), sendBatch: vi.fn() } as unknown as Queue<SupplierJob>,
    ENVIRONMENT: 'test',
    PAYMENT_PROVIDER: 'mock',
    SUPPLIER_PROVIDER: 'mock',
    INVOICE_PROVIDER: 'mock',
    ACCESS_TEAM_DOMAIN: '',
    ACCESS_AUD: '',
    PAYMENT_WEBHOOK_SECRET: 'test-webhook-secret-0123456789',
    EMAIL_PROVIDER: 'UNDECIDED',
  };
});
const req = (path: string, init?: RequestInit) => app.request(`http://localhost${path}`, init, env);
const json = (body: unknown, method = 'POST'): RequestInit => ({ method, headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
const waitlistRows = async () => (await env.DB.prepare('SELECT COUNT(*) AS n FROM waitlist').first<{ n: number }>())?.n;

async function checkout(marketing: unknown) {
  const cart = (await (await req('/api/cart', { method: 'POST' })).json()) as { id: string };
  await req(`/api/cart/${cart.id}/items`, json({ variant_id: 'vase-a:default', qty: 1 }, 'PUT'));
  const res = await req(
    '/api/checkout',
    json({
      cart_id: cart.id,
      customer: { full_name: 'ישראלה ישראלי', email: 'buyer@example.com', phone: '050-1234567' },
      address: { city: 'תל אביב', street: 'הרצל', house: '10' },
      shipping_method: 'express',
      consents: { terms: true, marketing },
    }),
  );
  const body = (await res.json()) as { order_id?: string };
  const row = body.order_id
    ? await env.DB.prepare('SELECT c.marketing_consent, c.marketing_consent_at FROM orders o JOIN customers c ON c.id = o.customer_id WHERE o.id = ?')
        .bind(body.order_id)
        .first<{ marketing_consent: number; marketing_consent_at: string | null }>()
    : null;
  return { status: res.status, row };
}

describe('S20 ת57: the waiting list without a provider', () => {
  const asks = [
    { email: 'buyer@example.com', product_id: 'vase-a' },
    { email: 'buyer@example.com', room: 'living-room', slot: 'vase' },
    // even a malformed one: refused before it is read
    { email: 'not-an-email' },
  ];
  for (const EMAIL_PROVIDER of ['UNDECIDED', undefined, 'mock', 'qa-all ', 'QA-ALL', 'qa-confirm-only'])
    it(`EMAIL_PROVIDER=${String(EMAIL_PROVIDER)}: 409 waitlist_closed, nothing stored`, async () => {
      env.EMAIL_PROVIDER = EMAIL_PROVIDER;
      for (const a of asks) {
        const r = await req('/api/waitlist', json(a));
        expect(r.status).toBe(409);
        expect(((await r.json()) as { error: string }).error).toBe('waitlist_closed');
      }
      expect(await waitlistRows()).toBe(0);
    });
  it('in production and in preview the same', async () => {
    for (const ENVIRONMENT of ['production', 'preview'] as const) {
      env.ENVIRONMENT = ENVIRONMENT;
      expect((await req('/api/waitlist', json(asks[0]))).status).toBe(409);
    }
    expect(await waitlistRows()).toBe(0);
  });
  it('with a provider that sends the back-in-stock message: the list of PRE1, one email for a product or a slot', async () => {
    env.EMAIL_PROVIDER = 'qa-all';
    expect((await req('/api/waitlist', json(asks[0]))).status).toBe(201);
    expect((await req('/api/waitlist', json(asks[1]))).status).toBe(201);
    expect((await req('/api/waitlist', json({ email: 'buyer@example.com', product_id: 'nope' }))).status).toBe(404);
    expect((await req('/api/waitlist', json({ email: 'not-an-email', product_id: 'vase-a' }))).status).toBe(422);
    expect((await req('/api/waitlist', json({ email: 'buyer@example.com' }))).status).toBe(422);
    const rows = await env.DB.prepare('SELECT email, product_id, room_id, slot_id FROM waitlist ORDER BY created_at').all();
    expect(rows.results).toEqual([
      { email: 'buyer@example.com', product_id: 'vase-a', room_id: null, slot_id: null },
      { email: 'buyer@example.com', product_id: null, room_id: 'living-room', slot_id: 'vase' },
    ]);
  });
});

describe('S20 ת57: the checkout never records a consent nobody can act on', () => {
  for (const EMAIL_PROVIDER of ['UNDECIDED', undefined, 'mock', 'qa-confirm-only'])
    it(`EMAIL_PROVIDER=${String(EMAIL_PROVIDER)}: "marketing": true is stored as no, and the order goes on`, async () => {
      env.EMAIL_PROVIDER = EMAIL_PROVIDER;
      const { status, row } = await checkout(true);
      expect(status).toBe(201);
      expect(row).toEqual({ marketing_consent: 0, marketing_consent_at: null });
    });
  it('with a provider that sends marketing email: the consent is recorded, with its time; "no" stays no', async () => {
    env.EMAIL_PROVIDER = 'qa-all';
    const yes = await checkout(true);
    expect(yes.row?.marketing_consent).toBe(1);
    expect(yes.row?.marketing_consent_at).toMatch(/^\d{4}-\d\d-\d\dT/);
    expect((await checkout(false)).row).toEqual({ marketing_consent: 0, marketing_consent_at: null });
  });
  it('a malformed consent is still refused by the schema, as before', async () => {
    expect((await checkout('yes')).status).toBe(422);
  });
});

describe('S20 ת61: the contact details', () => {
  it('UNDECIDED (today, every environment) is no contact; a well-formed email (and phone) is one', () => {
    const cfg = parseJsonc(wrangler) as { vars: Record<string, unknown>; env: Record<string, { vars: Record<string, unknown> }> };
    for (const vars of [cfg.vars, ...Object.values(cfg.env).map((e) => e.vars)]) {
      expect(vars.CONTACT_EMAIL).toBe('UNDECIDED');
      expect(vars.CONTACT_PHONE).toBe('UNDECIDED');
      expect(contactConfigIssues(vars)).toEqual([]);
      expect(contactOf(vars)).toBeNull();
    }
    expect(contactOf({ CONTACT_EMAIL: 'shop@hd-test.co.il', CONTACT_PHONE: 'UNDECIDED' })).toEqual({ email: 'shop@hd-test.co.il', phone: null, phone_href: null });
    expect(contactOf({ CONTACT_EMAIL: ' shop@hd-test.co.il ', CONTACT_PHONE: '03-1234567' })).toEqual({
      email: 'shop@hd-test.co.il',
      phone: '03-1234567',
      phone_href: '+97231234567',
    });
    expect(contactOf({ CONTACT_EMAIL: 'a@b.co', CONTACT_PHONE: '+972 50-123-4567' })?.phone_href).toBe('+972501234567');
    expect(contactOf({ CONTACT_EMAIL: 'a@b.co', CONTACT_PHONE: '1-800-123-456' })?.phone_href).toBe('1800123456');
    expect(contactOf({ CONTACT_EMAIL: 'a@b.co', CONTACT_PHONE: '*1234' })?.phone_href).toBe('*1234');
  });
  it('a malformed value, a phone without an email, or a missing variable fails the deploy check', () => {
    expect(contactIssues({ CONTACT_EMAIL: 'shop at hd', CONTACT_PHONE: 'UNDECIDED' })).toEqual([expect.stringContaining('is not an email address')]);
    expect(contactIssues({ CONTACT_EMAIL: 'shop@hd.co.il', CONTACT_PHONE: '12345' })).toEqual([expect.stringContaining('is not an Israeli phone number')]);
    expect(contactIssues({ CONTACT_EMAIL: 'UNDECIDED', CONTACT_PHONE: '03-1234567' })).toEqual([expect.stringContaining('CONTACT_PHONE without CONTACT_EMAIL')]);
    expect(contactIssues({})).toEqual([expect.stringContaining('CONTACT_EMAIL is not set')]);
    expect(contactOf({ CONTACT_EMAIL: 'shop at hd' })).toBeNull();
    expect(isPlaceholderEmail('hello@example.com')).toBe(true);
    expect(isPlaceholderEmail('a@shop.test')).toBe(true);
    expect(isPlaceholderEmail('shop@hd-test.co.il')).toBe(false);
  });
  it('check-config names a malformed contact in production, and passes the repo as it is', () => {
    const f = join(mkdtempSync(join(tmpdir(), 'hd-s20-cfg-')), 'wrangler.jsonc');
    writeFileSync(f, wrangler.replace(/("production"[\s\S]*?)"CONTACT_EMAIL": "UNDECIDED"/, '$1"CONTACT_EMAIL": "shop-at-hd"'));
    const bad = spawnSync(process.execPath, [TSX, 'scripts/check-config.ts', f], { cwd: API, encoding: 'utf8', timeout: 60_000 });
    expect(bad.status).toBe(1);
    expect(bad.stderr).toMatch(/production: CONTACT_EMAIL="shop-at-hd" is not an email address/);
    const ok = spawnSync(process.execPath, [TSX, 'scripts/check-config.ts'], { cwd: API, encoding: 'utf8', timeout: 60_000 });
    expect(ok.status, ok.stderr).toBe(0);
    expect(ok.stdout).toMatch(/production production \(.*contact UNDECIDED\)/);
  });
  it('the Worker\'s error line: "כתבו לנו" only with an email to write to; the code either way', async () => {
    expect(errorMessageHe('E-ABCD2345')).toBe('משהו השתבש אצלנו. נסו שוב בעוד רגע. קוד השגיאה: E-ABCD2345.');
    expect(errorMessageHe('E-ABCD2345', { CONTACT_EMAIL: 'UNDECIDED' })).not.toMatch(/כתבו/);
    expect(errorMessageHe('E-ABCD2345', { CONTACT_EMAIL: 'shop@hd-test.co.il' })).toBe(
      'משהו השתבש אצלנו. נסו שוב בעוד רגע. אם זה חוזר, כתבו לנו ל-shop@hd-test.co.il וציינו את הקוד E-ABCD2345.',
    );
    // through a request: an unhandled error (a D1 that throws) answers with the line of this environment
    env.DB = {
      prepare: () => {
        throw new Error('boom');
      },
    } as unknown as D1Database;
    const plain = (await (await req('/api/health')).json()) as { error_id: string; message_he: string };
    expect(plain.message_he).toBe(`משהו השתבש אצלנו. נסו שוב בעוד רגע. קוד השגיאה: ${plain.error_id}.`);
    env.CONTACT_EMAIL = 'shop@hd-test.co.il';
    const withContact = (await (await req('/api/health')).json()) as { error_id: string; message_he: string };
    expect(withContact.message_he).toContain(`כתבו לנו ל-shop@hd-test.co.il וציינו את הקוד ${withContact.error_id}`);
  });
});
