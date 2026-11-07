import { createRequire } from 'node:module';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const out = [];
for (const [style, f] of [['nordic', 'B']]) {
  const ctx = await b.newContext({ locale: 'he-IL' });
  const p = await ctx.newPage();
  await p.goto(`http://127.0.0.1:8799/story/living-room/${style}/`, { waitUntil: 'load' });
  await p.waitForTimeout(600);
  const exp = await p.evaluate((f) => { const d = JSON.parse(document.getElementById('st-data').textContent); return [...new Set(d.frames.find((x) => x.id === f).items.map((k) => d.items[k]).filter((x) => x.status === 'available' && x.variant_id).map((x) => x.variant_id))]; }, f);
  await p.locator(`#look-${f}`).scrollIntoViewIfNeeded();
  await p.locator(`#look-${f}`).click();
  await p.waitForTimeout(400);
  const got = await p.evaluate(() => JSON.parse(localStorage.getItem('hd.story.cart')).items.map((i) => [i.variant_id, i.qty, i.pack]));
  out.push({ style, frame: f, expected: exp, got, same: exp.length === got.length && exp.every((v) => got.some((g) => g[0] === v && g[1] === 1 && g[2] === 'set')) });
  await ctx.close();
}
await b.close();
console.log(JSON.stringify(out));
