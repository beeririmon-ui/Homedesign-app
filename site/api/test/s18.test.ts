/**
 * S18: the customer's email in the deploy check. EMAIL_PROVIDER is in every environment of wrangler.jsonc, UNDECIDED
 * (none is built); a mock, a typo or nothing fails the deploy check, as a job's provider does (ת17). The job providers'
 * own check is unchanged: the customer's email is not a job, and no job reads it.
 */
import { describe, expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { PROVIDERS, configIssues, emailConfigIssues } from '../src/lib/config';
import { parseJsonc } from '../scripts/jsonc';

const API = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const TSX = resolve(API, '../node_modules/tsx/dist/cli.mjs');
const wrangler = readFileSync(join(API, 'wrangler.jsonc'), 'utf8');
type Cfg = { vars: Record<string, unknown>; env: Record<string, { vars: Record<string, unknown> }> };

describe('S18: EMAIL_PROVIDER in the deploy check', () => {
  it('every environment carries UNDECIDED, and passes', () => {
    const cfg = parseJsonc(wrangler) as Cfg;
    for (const vars of [cfg.vars, ...Object.values(cfg.env).map((e) => e.vars)]) {
      expect(vars.EMAIL_PROVIDER).toBe('UNDECIDED');
      expect(emailConfigIssues(vars)).toEqual([]);
    }
  });
  it('a mock (in any environment), a typo or nothing is refused', () => {
    for (const ENVIRONMENT of ['development', 'preview', 'production'])
      expect(emailConfigIssues({ ENVIRONMENT, EMAIL_PROVIDER: 'mock' }), ENVIRONMENT).toEqual([expect.stringContaining('EMAIL_PROVIDER=mock is refused')]);
    expect(emailConfigIssues({ EMAIL_PROVIDER: 'Resend' })).toEqual([expect.stringContaining('EMAIL_PROVIDER="Resend" is not a provider')]);
    expect(emailConfigIssues({})).toEqual([expect.stringContaining('EMAIL_PROVIDER is not set')]);
  });
  it('it is not a job provider: the job providers and their check are as they were', () => {
    expect(Object.keys(PROVIDERS)).toEqual(['PAYMENT_PROVIDER', 'INVOICE_PROVIDER', 'SUPPLIER_PROVIDER', 'NOTIFY_PROVIDER']);
    expect(
      configIssues({ ENVIRONMENT: 'production', PAYMENT_PROVIDER: 'grow', INVOICE_PROVIDER: 'grow', SUPPLIER_PROVIDER: 'cj', NOTIFY_PROVIDER: 'UNDECIDED' }),
    ).toEqual([]);
  });
  it('check-config fails a wrangler.jsonc whose production has a mock email, and names it', () => {
    const f = join(mkdtempSync(join(tmpdir(), 'hd-s18-cfg-')), 'wrangler.jsonc');
    writeFileSync(f, wrangler.replace(/("production"[\s\S]*?)"EMAIL_PROVIDER": "UNDECIDED"/, '$1"EMAIL_PROVIDER": "mock"'));
    const bad = spawnSync(process.execPath, [TSX, 'scripts/check-config.ts', f], { cwd: API, encoding: 'utf8', timeout: 60_000 });
    expect(bad.status).toBe(1);
    expect(bad.stderr).toMatch(/production: EMAIL_PROVIDER=mock is refused/);
    const ok = spawnSync(process.execPath, [TSX, 'scripts/check-config.ts'], { cwd: API, encoding: 'utf8', timeout: 60_000 });
    expect(ok.status, ok.stderr).toBe(0);
    expect(ok.stdout).toMatch(/production production \(.*customer email UNDECIDED[,)]/);
  });
});
