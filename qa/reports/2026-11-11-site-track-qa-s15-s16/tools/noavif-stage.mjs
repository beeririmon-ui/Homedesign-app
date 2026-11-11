/**
 * qa-agent, S16 (2026-11-11): ת43 and ה1 in Chromium, my own way.
 *
 * ת43, a phone without AVIF: not a script that patches the probe and answers AVIF requests with WebP (the e2e's way), but
 * the browser's own switch: CDP `Emulation.setDisabledImageTypes(['avif'])` (DevTools' "disable AVIF"), set before the
 * first request. Chromium then does not advertise AVIF, skips <source type="image/avif">, and fails to decode AVIF, as a
 * browser without it would. Pixel 7, warm-modern house, no pointer/touch/focus: every byte received (CDP
 * encodedDataLength) until the engine is ready, which poster was taken, whether any AVIF was asked for, and when the engine
 * started. The control: the same with AVIF (the engine waits for intent).
 *
 * ה1, the stage while the poster loads: the poster held (route not answered for 4 s); the stage's mean luminance at
 * 300 ms and the inline placeholder's size; then a slow network (1.6 Mbps, 150 ms) to time the first non-dark stage.
 *   QA_BASE=… QA_COPY=<copy>/site QA_OUT=<folder> node noavif-stage.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const COPY = process.env.QA_COPY;
const require = createRequire(join(COPY, 'package.json'));
const { chromium, devices } = require('playwright-core');
const sharp = require('sharp');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const HOUSE = '/rooms/living-room/?style=warm-modern';
const { defaultBrowserType: _b, ...pixel } = devices['Pixel 7'];
const MB = 1024 * 1024;

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = {};

async function firstLoad(disableAvif) {
  const ctx = await browser.newContext({ ...pixel, locale: 'he-IL' });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  if (disableAvif) await cdp.send('Emulation.setDisabledImageTypes', { imageTypes: ['avif'] });
  const urls = new Map();
  const got = [];
  let accept = null;
  cdp.on('Network.requestWillBeSent', (e) => {
    urls.set(e.requestId, e.request.url);
    if (e.type === 'Image' && !accept) accept = e.request.headers.Accept ?? e.request.headers.accept ?? null;
  });
  cdp.on('Network.loadingFinished', (e) => got.push([urls.get(e.requestId) ?? '?', e.encodedDataLength, Date.now()]));
  const t0 = Date.now();
  await page.goto(`${BASE}${HOUSE}`, { waitUntil: 'load' });
  const probe = await page.evaluate(
    () =>
      new Promise((r) => {
        const i = new Image();
        i.onload = () => r('decodes AVIF');
        i.onerror = () => r('no AVIF');
        i.src =
          'data:image/avif;base64,AAAAHGZ0eXBhdmlmAAAAAG1pZjFhdmlmbWlhZgAAANZtZXRhAAAAAAAAACFoZGxyAAAAAAAAAABwaWN0AAAAAAAAAAAAAAAAAAAAAA5waXRtAAAAAAABAAAAImlsb2MAAAAAREAAAQABAAAAAAD6AAEAAAAAAAAAGgAAACNpaW5mAAAAAAABAAAAFWluZmUCAAAAAAEAAGF2MDEAAAAAVmlwcnAAAAA4aXBjbwAAAAxhdjFDgSACAAAAABRpc3BlAAAAAAAAAAIAAAACAAAAEHBpeGkAAAAAAwgICAAAABZpcG1hAAAAAAAAAAEAAQOBAgMAAAAibWRhdBIACgc4ADYQENBpMg0bABpppoQAAK/1OBXM';
      }),
  );
  let ready = null;
  let readyAt = null;
  try {
    await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: disableAvif ? 45_000 : 8_000, polling: 20 });
    ready = Date.now() - t0;
    readyAt = Date.now();
  } catch {
    ready = null;
  }
  const poster = await page.evaluate(() => {
    const img = document.querySelector('section.stage img.poster');
    return img ? img.currentSrc.replace(location.origin, '') : null;
  });
  await page.waitForTimeout(300);
  const total = got.reduce((s, [, b]) => s + b, 0);
  const atReady = readyAt ? got.filter(([, , t]) => t <= readyAt).reduce((s, [, b]) => s + b, 0) : null;
  const out = {
    avif_disabled: disableAvif,
    probe,
    image_accept_header: accept,
    poster,
    engine_ready_ms: ready,
    bytes_at_ready_MB: atReady === null ? null : Number((atReady / MB).toFixed(2)),
    bytes_at_ready_plus_300ms_or_8s_MB: Number((total / MB).toFixed(2)),
    files_at_ready: readyAt ? got.filter(([, , t]) => t <= readyAt).length : null,
    avif_requested: got.filter(([u]) => /\.avif(\?|$)/.test(u)).length,
    largest: got
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6)
      .map(([u, b]) => `${(b / 1024).toFixed(0)} KB ${u.replace(BASE, '')}`),
  };
  await ctx.close();
  return out;
}
res.no_avif = await firstLoad(true);
console.log('ת43 no AVIF:', JSON.stringify(res.no_avif));
res.with_avif = await firstLoad(false);
console.log('ת43 with AVIF (control):', JSON.stringify(res.with_avif));

// ה1: the stage while the poster is held, then on a slow network
async function stage(vp, name) {
  const ctx = await browser.newContext(vp.m ? { ...pixel, locale: 'he-IL' } : { viewport: { width: 1280, height: 800 }, locale: 'he-IL' });
  const page = await ctx.newPage();
  let held = 0;
  await page.route(/\/media\/house\/.+\/poster\/.+\.(avif|webp)/, async (route) => {
    held++;
    await new Promise((r) => setTimeout(r, 4000));
    await route.continue().catch(() => undefined);
  });
  await page.goto(`${BASE}${HOUSE}`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(300);
  const stageEl = page.locator('section.stage').first();
  const shot = await stageEl.screenshot({ path: join(OUT, 'overlays', `h1-stage-held-${name}.png`) }).catch(() => page.screenshot({ path: join(OUT, 'overlays', `h1-stage-held-${name}.png`) }));
  const { channels } = await sharp(shot).stats();
  const mean = (channels[0].mean + channels[1].mean + channels[2].mean) / 3;
  const inline = await page.evaluate(() => {
    const html = document.documentElement.outerHTML;
    const m = /url\((?:&quot;|["'])?(data:image\/[a-z]+;base64,[A-Za-z0-9+/=]+)/.exec(html) ?? /(data:image\/(?:webp|avif|jpeg|png);base64,[A-Za-z0-9+/=]{100,})/.exec(html);
    return m ? { chars: m[1].length, type: m[1].slice(5, m[1].indexOf(';')) } : null;
  });
  await ctx.close();
  return { held, stage_mean_at_300ms: Number(mean.toFixed(1)), inline_placeholder: inline };
}
if (process.env.QA_ONLY_43) { await browser.close(); writeFileSync(join(OUT, 'data/noavif-43.json'), JSON.stringify(res, null, 1)); process.exit(0); }
res.h1_held_1280 = await stage({}, '1280');
res.h1_held_400 = await stage({ m: true }, '400');
console.log('ה1 held:', JSON.stringify(res.h1_held_1280), JSON.stringify(res.h1_held_400));

// slow network: how long the stage stays dark (mean < 40) and when the poster arrives
{
  const ctx = await browser.newContext({ ...pixel, locale: 'he-IL' });
  const page = await ctx.newPage();
  const cdp = await ctx.newCDPSession(page);
  await cdp.send('Network.enable');
  await cdp.send('Network.emulateNetworkConditions', { offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8 });
  const t0 = Date.now();
  await page.goto(`${BASE}${HOUSE}`, { waitUntil: 'commit' });
  const samples = [];
  for (let i = 0; i < 30; i++) {
    const shot = await page.screenshot().catch(() => null);
    if (shot) {
      const { channels } = await sharp(shot).stats();
      samples.push([Date.now() - t0, Number(((channels[0].mean + channels[1].mean + channels[2].mean) / 3).toFixed(1))]);
    }
    const posterDone = await page.evaluate(() => { const i = document.querySelector('section.stage img.poster'); return !!i && i.complete && i.naturalWidth > 0 && !!i.currentSrc; }).catch(() => false);
    if (posterDone && samples.length > 3) {
      samples.push(['poster complete', Date.now() - t0]);
      break;
    }
    await page.waitForTimeout(250);
  }
  res.h1_slow = samples;
  console.log('ה1 slow 1.6 Mbps (ms, mean of the whole screen):', JSON.stringify(samples));
  await ctx.close();
}
await browser.close();
writeFileSync(join(OUT, 'data/noavif-stage.json'), JSON.stringify(res, null, 1));
