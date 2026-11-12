/**
 * S22 (QA ת70, ה23): a second site for the e2e suite, built in a scratch copy with what the repo's build never has: an
 * email provider that sends the back-in-stock message, and (optionally) the shop's contact details. The repo itself is
 * never touched: its EMAIL_PROVIDERS stay empty and its contact UNDECIDED (CONTACT1, EMAIL1).
 *
 * - **The copy:** site/ without its build output, its node_modules (linked, entry by entry, with @hd/* pointing at the
 *   copy's own workspaces) and its media (hard links). `shared/src/email.ts` gets one test provider, `e2e-bis`, that
 *   declares `back_in_stock` only; `api/wrangler.jsonc` names it at the top level (the flag build's environment, and
 *   wrangler dev's), with the contact details when asked. Sample contact values are fine there: behind the flag a
 *   sample is a warning, never the public build (@hd/shared/contact-samples).
 * - **The build:** build-copy, the web build (client, SSR, prerender), the seed and the migrations of a D1 of its own.
 * - **The server:** wrangler dev on its own port, inspector port and state folder, next to the suite's preview.
 * Runs after `npm run build` (prepare:data's output, .generated and web/story, is copied as it is).
 */
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const SKIP =
  /(^|\/)(node_modules|\.git)(\/|$)|^(web\/dist|web\/\.ssr|web\/public\/media|api\/dist|\.wrangler-state|\.wrangler|test-results|playwright-report|dist-artifact|\.cache|\.lighthouse|screens|prototype)(\/|$)/;

export type ScratchSite = { url: string; dir: string; log: () => string; stop: () => Promise<void> };
export type ScratchOptions = { port: number; contact?: { email: string; phone?: string }; keep?: boolean };

function sh(cmd: string, args: string[], cwd: string, env: Record<string, string> = {}): string {
  const r = spawnSync(cmd, args, { cwd, encoding: 'utf8', env: { ...process.env, HD_PUBLIC: '0', HD_WRANGLER: '', ...env }, timeout: 600_000 });
  const out = `$ ${[cmd, ...args].join(' ')} (in ${relative(SITE, cwd) || '.'})\n${r.stdout ?? ''}${r.stderr ?? ''}`;
  if (r.status !== 0) throw new Error(`scratch site: ${cmd} ${args.join(' ')} failed (${r.status ?? r.signal})\n${out.slice(-3000)}`);
  return out;
}
function patch(file: string, from: string, to: string): void {
  const s = readFileSync(file, 'utf8');
  if (!s.includes(from)) throw new Error(`scratch site: the anchor is missing in ${file}: ${from}`);
  writeFileSync(file, s.replace(from, to));
}
/** the copy's node_modules: every entry linked to the repo's, the workspaces to the copy's own folders */
function linkModules(from: string, to: string, workspaces: Record<string, string>): void {
  mkdirSync(to, { recursive: true });
  for (const e of readdirSync(from)) {
    if (e === '@hd' && Object.keys(workspaces).length) {
      mkdirSync(join(to, '@hd'));
      for (const [name, dir] of Object.entries(workspaces)) symlinkSync(dir, join(to, '@hd', name));
      continue;
    }
    symlinkSync(join(from, e), join(to, e));
  }
}

export async function startScratchSite(o: ScratchOptions): Promise<ScratchSite> {
  const dir = mkdtempSync(join(tmpdir(), 'hd-s22-site-'));
  const site = join(dir, 'site');
  let log = '';
  cpSync(SITE, site, { recursive: true, filter: (src) => !SKIP.test(relative(SITE, src).split('\\').join('/')) });
  const ws = Object.fromEntries(['shared', 'api', 'web', 'tools'].map((w) => [w, join(site, w)]));
  linkModules(join(SITE, 'node_modules'), join(site, 'node_modules'), ws);
  for (const w of ['api', 'web', 'shared', 'tools'])
    if (existsSync(join(SITE, w, 'node_modules'))) linkModules(join(SITE, w, 'node_modules'), join(site, w, 'node_modules'), {});
  mkdirSync(join(site, 'web/public'), { recursive: true });
  log += sh('cp', ['-al', join(SITE, 'web/public/media'), join(site, 'web/public/media')], SITE);
  if (existsSync(join(SITE, 'api/.dev.vars'))) cpSync(join(SITE, 'api/.dev.vars'), join(site, 'api/.dev.vars'));
  // the test provider and its environment (the copy only)
  patch(
    join(site, 'shared/src/email.ts'),
    'export const EMAIL_PROVIDERS: EmailProviders = {};',
    "export const EMAIL_PROVIDERS: EmailProviders = { 'e2e-bis': ['back_in_stock'] }; // S22 e2e scratch copy only",
  );
  const wr = join(site, 'api/wrangler.jsonc');
  patch(wr, '"EMAIL_PROVIDER": "UNDECIDED",', '"EMAIL_PROVIDER": "e2e-bis",');
  if (o.contact) {
    patch(wr, '"CONTACT_EMAIL": "UNDECIDED",', `"CONTACT_EMAIL": "${o.contact.email}",`);
    if (o.contact.phone) patch(wr, '"CONTACT_PHONE": "UNDECIDED",', `"CONTACT_PHONE": "${o.contact.phone}",`);
  }
  const node = process.execPath;
  const tsx = join(site, 'node_modules/tsx/dist/cli.mjs');
  const vite = join(site, 'node_modules/vite/bin/vite.js');
  const wrangler = join(site, 'node_modules/wrangler/bin/wrangler.js');
  log += sh(node, [tsx, 'tools/build-copy.ts'], site);
  log += sh(node, [vite, 'build'], join(site, 'web'));
  log += sh(node, [vite, 'build', '--ssr', 'src/entry-server.tsx', '--outDir', '.ssr'], join(site, 'web'));
  log += sh(node, [tsx, 'scripts/prerender.ts'], join(site, 'web'));
  log += sh(node, [tsx, 'scripts/seed.ts'], join(site, 'api'));
  const state = ['--local', '--persist-to', '../.wrangler-state'];
  log += sh(node, [wrangler, 'd1', 'migrations', 'apply', 'DB', ...state], join(site, 'api'), { CI: '1' });
  log += sh(node, [wrangler, 'd1', 'execute', 'DB', ...state, '--file', '../.generated/seed.sql'], join(site, 'api'), { CI: '1' });
  const server: ChildProcess = spawn(
    node,
    [wrangler, 'dev', '--port', String(o.port), '--inspector-port', String(o.port + 1000), ...state, '--var', 'ENVIRONMENT:preview-local'],
    { cwd: join(site, 'api'), env: { ...process.env, HD_PUBLIC: '0', CI: '1' }, detached: true, stdio: ['ignore', 'pipe', 'pipe'] },
  );
  server.stdout?.on('data', (d: Buffer) => (log += d.toString()));
  server.stderr?.on('data', (d: Buffer) => (log += d.toString()));
  const url = `http://127.0.0.1:${o.port}`;
  const stop = async () => {
    try {
      process.kill(-server.pid!, 'SIGTERM');
    } catch {
      /* already gone */
    }
    await new Promise((r) => setTimeout(r, 500));
    if (!o.keep) rmSync(dir, { recursive: true, force: true });
  };
  for (let i = 0; i < 240; i++) {
    try {
      if ((await fetch(`${url}/api/health`)).ok) return { url, dir, log: () => log, stop };
    } catch {
      /* not up yet */
    }
    if (server.exitCode !== null) break;
    await new Promise((r) => setTimeout(r, 500));
  }
  await stop();
  throw new Error(`scratch site: wrangler dev did not answer on ${url}\n${log.slice(-3000)}`);
}
