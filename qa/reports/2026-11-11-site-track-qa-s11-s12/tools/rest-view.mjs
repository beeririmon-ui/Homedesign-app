/** qa-agent, 2026-11-11: a room page at rest (no pointer, no touch, no focus) for 8 s: is the engine started, and what is painted. */
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { writeFileSync } from 'node:fs';
const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const res = [];
for (const [name, url] of [['nordic', '/rooms/living-room/'], ['warm-modern', '/rooms/living-room/?style=warm-modern']])
  for (const v of [{ w: 1280, h: 720 }, { w: 400, h: 860, m: true }]) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, isMobile: !!v.m, hasTouch: !!v.m });
    ctx.setDefaultTimeout(120000);
    const p = await ctx.newPage();
    await p.goto(`${BASE}${url}`, { waitUntil: 'load' });
    await p.waitForTimeout(8000);
    const st = await p.evaluate(() => ({
      engine: !!window.__hdEngine,
      ready: !!window.__hdEngine?.ready,
      poster: document.querySelector('img.poster')?.currentSrc?.split('/media/')[1] ?? null,
      canvas_opacity: document.querySelector('canvas.room-canvas') ? getComputedStyle(document.querySelector('canvas.room-canvas')).opacity : null,
    }));
    const file = `rest-${name}-${v.w}.jpg`;
    await p.screenshot({ path: join(OUT, 'overlays', file), type: 'jpeg', quality: 80 });
    res.push({ house: name, viewport: `${v.w}x${v.h}`, ...st, shot: file });
    console.log(name, v.w, JSON.stringify(st));
    await ctx.close();
  }
await browser.close();
writeFileSync(join(OUT, 'data/rest-view.json'), JSON.stringify(res, null, 1));
