/**
 * qa-agent, 2026-11-10 (S8/S10): every line of dist/_redirects asked of the server (no redirect following): the status
 * and Location must be the line's, and the target must answer 200. Also a few old addresses that are not in the file:
 * an S7 slug with a size (S8 decided not to keep them), a card id with a trailing slash missing.
 *   QA_BASE=http://127.0.0.1:8799 node redirects-live.mjs <dist>/_redirects out.json
 */
import { readFileSync, writeFileSync } from 'node:fs';
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const lines = readFileSync(process.argv[2], 'utf8').split('\n').filter((l) => l.trim());
const out = [];
for (const l of lines) {
  const [from, to, code] = l.trim().split(/\s+/);
  const r = await fetch(BASE + from, { redirect: 'manual' });
  const loc = r.headers.get('location');
  const t = loc ? await fetch(new URL(loc, BASE), { redirect: 'manual' }) : null;
  out.push({ from, to, code: Number(code), status: r.status, location: loc, ok: r.status === Number(code) && loc === to, target_status: t?.status ?? null });
}
const extra = [];
for (const u of ['/p/planter-seagrass-belly-38x34-jyyuu/', '/p/basket-seagrass-belly-38x34-ltsd4/', '/p/vase-cj-textured-white-stoneware', '/story/living-room/warm-modern/tool']) {
  const r = await fetch(BASE + u, { redirect: 'manual' });
  extra.push({ url: u, status: r.status, location: r.headers.get('location') });
}
const res = { lines: out.length, ok: out.filter((x) => x.ok).length, target_200: out.filter((x) => x.target_status === 200).length, bad: out.filter((x) => !x.ok || x.target_status !== 200), extra, all: out };
writeFileSync(process.argv[3], JSON.stringify(res, null, 1));
console.log(JSON.stringify({ lines: res.lines, ok: res.ok, target_200: res.target_200, bad: res.bad, extra }, null, 1));
