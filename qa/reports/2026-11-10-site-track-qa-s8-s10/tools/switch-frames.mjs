/**
 * qa-agent, 2026-11-10 (S10, the house switch): what is painted during the switch. A CDP screencast of the page (every
 * frame Chromium paints) while the stage switches houses, each frame kept as a JPEG and laid out on a contact sheet with
 * its time from the press; alongside, per animation frame, the engine's own dissolve value (`mix`, 0 → 1), the rAF gap,
 * and the mean brightness of the stage in the painted frame (a black or blank frame shows as a dip).
 * Runs: Nordic → warm-modern (the first time: the house's chunk and layers load), back, and again; full and reduced
 * motion; at 1280×720 and at 400×800 (touch).
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node switch-frames.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'] });
const res = [];
for (const v of [{ w: 1280, h: 720 }, { w: 400, h: 800, m: true }]) {
  for (const reduced of [false, true]) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, isMobile: !!v.m, hasTouch: !!v.m, reducedMotion: reduced ? 'reduce' : 'no-preference' });
    const p = await ctx.newPage();
    await p.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
    await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 20000 });
    const sb = await p.locator('section.stage').boundingBox();
    if (v.m) await p.touchscreen.tap(sb.x + 10, sb.y + sb.height / 2);
    else await p.mouse.click(sb.x + 10, sb.y + sb.height / 2);
    for (let i = 0; i < 80 && !(await p.evaluate(() => window.__hdEngine?.ready)); i++) await p.waitForTimeout(250);
    await p.waitForTimeout(2500);
    for (const [k, target] of [[1, 'warm-modern'], [2, 'nordic'], [3, 'warm-modern']]) {
      const cdp = await ctx.newCDPSession(p);
      const frames = [];
      cdp.on('Page.screencastFrame', async (f) => {
        frames.push({ t: f.metadata.timestamp, data: f.data });
        await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => undefined);
      });
      await p.evaluate(() => {
        window.__qaMix = [];
        const t0 = performance.now();
        let last = t0;
        const loop = (now) => {
          const e = window.__hdEngine;
          window.__qaMix.push({ t: Math.round(now - t0), gap: Math.round(now - last), mix: e ? +Number(e.mix).toFixed(3) : null });
          last = now;
          if (now - t0 < 3500) requestAnimationFrame(loop);
        };
        requestAnimationFrame(loop);
      });
      await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 60, everyNthFrame: 1, maxWidth: v.w > 500 ? 640 : 400, maxHeight: 400 });
      await p.waitForTimeout(250);
      const press = Date.now() / 1000;
      const btn = p.locator(`.segmented button[data-house="${target}"]`);
      if (v.m) await btn.tap();
      else await btn.click();
      await p.waitForTimeout(3300);
      await cdp.send('Page.stopScreencast');
      await cdp.detach();
      const mixes = await p.evaluate(() => window.__qaMix);
      const sw = await p.evaluate(() => window.__hdHouseSwitch ?? null);
      // the stage's band in the painted frame (below the header), its mean brightness per frame
      const stats = [];
      const tiles = [];
      for (const f of frames) {
        const buf = Buffer.from(f.data, 'base64');
        const img = sharp(buf);
        const m = await img.metadata();
        const top = Math.round(m.height * (60 / v.h)) + 2;
        const band = await img.clone().extract({ left: 0, top, width: m.width, height: Math.max(10, Math.round(m.height * 0.6) - top) }).stats();
        const mean = band.channels.slice(0, 3).reduce((s, c) => s + c.mean, 0) / 3;
        stats.push({ t_ms: Math.round((f.t - press) * 1000), stage_mean: +mean.toFixed(1) });
        tiles.push(await img.resize(v.w > 500 ? 320 : 160).jpeg({ quality: 70 }).toBuffer());
      }
      // the contact sheet: up to 24 frames
      const pick = tiles.length > 24 ? tiles.filter((_, i) => i % Math.ceil(tiles.length / 24) === 0) : tiles;
      const tw = v.w > 500 ? 320 : 160;
      const th = (await sharp(pick[0]).metadata()).height;
      const cols = v.w > 500 ? 4 : 8;
      const rows = Math.ceil(pick.length / cols);
      const name = `switch-frames-${v.w}-${reduced ? 'reduced' : 'full'}-${k}-to-${target}.jpg`;
      await sharp({ create: { width: cols * (tw + 4), height: rows * (th + 4), channels: 3, background: { r: 255, g: 255, b: 255 } } })
        .composite(pick.map((b, i) => ({ input: b, left: (i % cols) * (tw + 4), top: Math.floor(i / cols) * (th + 4) })))
        .jpeg({ quality: 75 })
        .toFile(join(OUT, 'overlays', name));
      const during = mixes.filter((x) => x.mix !== null && x.mix > 0 && x.mix < 1);
      const means = stats.map((s) => s.stage_mean);
      res.push({
        viewport: `${v.w}x${v.h}`,
        reduced,
        run: k,
        to: target,
        page: sw ? { dissolve_ms: Math.round(sw.end - sw.start), press_to_end_ms: Math.round(sw.end - sw.asked) } : null,
        mix: { frames_in_dissolve: during.length, first_t: during[0]?.t ?? null, last_t: during.at(-1)?.t ?? null, max_gap_ms_in_dissolve: Math.max(0, ...during.map((x) => x.gap)), max_gap_ms_overall: Math.max(...mixes.map((x) => x.gap)), values: during.map((x) => [x.t, x.mix]).slice(0, 80) },
        painted: { frames: frames.length, stage_mean_first: means[0], stage_mean_last: means.at(-1), stage_mean_min: Math.min(...means), stage_mean_max: Math.max(...means), series: stats },
        sheet: name,
      });
    }
    await ctx.close();
  }
}
await browser.close();
writeFileSync(join(OUT, 'data/switch-frames.json'), JSON.stringify(res, null, 1));
console.log(JSON.stringify(res.map((r) => ({ vp: r.viewport, reduced: r.reduced, run: r.run, to: r.to, page: r.page, mix: { n: r.mix.frames_in_dissolve, span: [r.mix.first_t, r.mix.last_t], maxgap: r.mix.max_gap_ms_in_dissolve }, painted: { n: r.painted.frames, first: r.painted.stage_mean_first, min: r.painted.stage_mean_min, max: r.painted.stage_mean_max, last: r.painted.stage_mean_last } })), null, 1));
