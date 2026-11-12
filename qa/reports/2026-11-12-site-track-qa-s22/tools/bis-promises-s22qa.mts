/**
 * QA S22, ת67 on the third build: frontend-dev's scratch site (e2e/scratch-site.ts: a test provider `e2e-bis` that sends
 * back_in_stock only), built and kept, then the gate (tools/check-promises.ts) inside it, as the build would run it with
 * that provider: the waiting-list lines are allowed, anything else is a finding. No server is needed after the build.
 *   cd <copy>/site && node node_modules/tsx/dist/cli.mjs <this> --site=<copy>/site --port=8843 --out=<json>
 */
import { spawnSync } from 'node:child_process';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
const arg = (n: string) => process.argv.find((a) => a.startsWith(`--${n}=`))?.slice(n.length + 3);
const SITE = arg('site')!;
const { startScratchSite } = (await import(pathToFileURL(join(SITE, 'e2e/scratch-site.ts')).href)) as any;
const site = await startScratchSite({ port: Number(arg('port') ?? 8843), keep: true });
try {
  const dir = join(site.dir, 'site');
  const r = spawnSync(process.execPath, [join(dir, 'node_modules/tsx/dist/cli.mjs'), 'tools/check-promises.ts', `--json=${arg('out')}`], { cwd: dir, encoding: 'utf8', env: { ...process.env, HD_PUBLIC: '0', HD_WRANGLER: '' } });
  console.log(`check-promises in the back_in_stock scratch build: exit ${r.status}`);
  console.log(`${r.stdout}${r.stderr}`.split('\n').filter((l) => /check-promises|promise|allowed|stops/.test(l)).join('\n').slice(0, 2000));
} finally {
  await site.stop();
  spawnSync('rm', ['-rf', site.dir]);
}
