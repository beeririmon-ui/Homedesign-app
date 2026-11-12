// qa-agent S21: is a hotspot hydrated (Preact keeps its listeners on the element as `l`)? One page, my server.
import { createRequire } from 'node:module';
import { join } from 'node:path';
const { chromium } = createRequire(join(process.env.QA_COPY, 'package.json'))('playwright-core');
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const p = await (await b.newContext()).newPage();
await p.goto(process.argv[2], { waitUntil: 'commit' });
const t0 = Date.now();
const seen = [];
for (let i = 0; i < 60; i++) {
  const s = await p.evaluate(() => { const h = document.querySelector('button.hotspot'); return h ? { has: true, l: !!h.l, keys: Object.keys(h).join(',') } : { has: false }; }).catch(() => ({ err: 1 }));
  seen.push({ ms: Date.now() - t0, ...s });
  if (s.l) break;
  await new Promise((r) => setTimeout(r, 50));
}
console.log(JSON.stringify([seen[0], seen.at(-2), seen.at(-1)]));
await b.close();
