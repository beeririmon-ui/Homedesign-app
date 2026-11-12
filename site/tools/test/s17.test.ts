/**
 * S17, QA ת49: the deploy check never downloads anything, and a provider is never set around it.
 * - `build.command` runs tsx from the repo's own node_modules by its path (never `npx tsx`, which from a folder without
 *   it downloads tsx from the registry and runs it); from any other folder the path is missing and node stops.
 * - The runbook: a provider is never set with --var or a secret.
 * - No `npx` without `--no-install` in anything that runs: the e2e, the tools, the API's scripts, the CI.
 */
import { describe, expect, it } from 'vitest';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { repoPath, sitePath } from '../lib/paths';

const wrangler = readFileSync(sitePath('api/wrangler.jsonc'), 'utf8');
const command = /"build":\s*\{\s*"command":\s*"([^"]+)"/.exec(wrangler)?.[1] ?? '';

describe('ת49: the deploy check', () => {
  it('runs tsx from site/node_modules by its path, and passes from site/api', () => {
    expect(command).toBe('node ../node_modules/tsx/dist/cli.mjs scripts/check-config.ts');
    expect(existsSync(sitePath('api', '../node_modules/tsx/dist/cli.mjs'))).toBe(true);
    const r = spawnSync('sh', ['-c', command], { cwd: sitePath('api'), encoding: 'utf8', timeout: 60_000 });
    expect(r.status, r.stderr).toBe(0);
    expect(r.stdout).toMatch(/check-config: .*production production/);
  });
  it('from another folder it stops at once, without npm (no download, no registry)', () => {
    const dir = mkdtempSync(join(tmpdir(), 'hd-s17-deploy-'));
    const r = spawnSync('sh', ['-c', command], { cwd: dir, encoding: 'utf8', timeout: 30_000, env: { ...process.env, npm_config_offline: 'true' } });
    expect(r.status).not.toBe(0);
    expect(`${r.stdout}${r.stderr}`).toMatch(/Cannot find module/);
    expect(`${r.stdout}${r.stderr}`).not.toMatch(/npm|npx|registry/i);
  });
  it('the runbook: a provider is never set with --var or a secret', () => {
    const runbook = readFileSync(repoPath('docs/ops/deploy-runbook.md'), 'utf8');
    expect(runbook).toMatch(/ספק לעולם לא נקבע ב-`--var` או כסוד/);
    expect(runbook).toContain('wrangler deploy --var SUPPLIER_PROVIDER');
  });
  it('no `npx` without --no-install in anything that runs', () => {
    const files: string[] = [];
    const walk = (d: string) => {
      for (const n of readdirSync(d)) {
        const p = join(d, n);
        if (statSync(p).isDirectory()) walk(p);
        else if (/\.(ts|mjs|js|jsonc|json|yml|sh)$/.test(n)) files.push(p);
      }
    };
    for (const d of ['e2e', 'tools', 'api/scripts', 'api/src', 'web/scripts']) walk(sitePath(d));
    files.push(
      sitePath('api/wrangler.jsonc'),
      sitePath('package.json'),
      sitePath('api/package.json'),
      sitePath('web/package.json'),
      repoPath('.github/workflows/site-ci.yml'),
    );
    const bare: string[] = [];
    for (const f of files) {
      if (f.endsWith('tools/test/s17.test.ts')) continue;
      readFileSync(f, 'utf8')
        .split('\n')
        .forEach((line, i) => {
          // a call: 'npx' as a program (a string or a command line); a comment, or a test that it is absent, is no call
          if (/^\s*(?:\/\/|\*|\/\*)/.test(line) || /\.not\.toMatch\(/.test(line)) return;
          if (/(?:['"`]npx['"`]|(?:^|[\s;&|"'`(])npx\s+(?!--no-install))/.test(line) && !/['"`]npx['"`],\s*\[\s*['"`]--no-install/.test(line))
            bare.push(`${f.slice(sitePath('').length)}:${i + 1}: ${line.trim().slice(0, 100)}`);
        });
    }
    expect(bare).toEqual([]);
  });
});
