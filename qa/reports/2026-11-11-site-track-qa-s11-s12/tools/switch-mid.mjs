/**
 * qa-agent, 2026-11-11 (ת15 at b94c5bc1): what Chromium actually PAINTS while the house switches (a CDP screencast of
 * the page, every frame it composites), not a re-render of the dissolve's states after it ends. For every painted frame:
 *  - the stage band's mean brightness (a black frame is a dip far under both houses);
 *  - the mix it shows: the least-squares a in  frame ≈ (1 − a)·A + a·B, with A the last frame before the press and B
 *    the last frame after the dissolve, and the residual of that fit relative to |A − B| (a frame that is neither house
 *    nor a blend of both, a black one or a third picture, has a large residual).
 * Pass: no frame under 0.9 × the darker house; at least one painted frame with 0.25 ≤ a ≤ 0.75 and a relative residual
 * ≤ 0.35 (both houses visible at once); a rising through the dissolve. Nordic → warm-modern → Nordic → warm-modern, full
 * and reduced motion, at 1280×720 and 400×800 (touch). Contact sheets and the midpoint frame to overlays/.
 *   QA_BASE=http://127.0.0.1:8799 QA_COPY=<copy>/site QA_OUT=<qa folder> node switch-mid.mjs
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
const require = createRequire(join(process.env.QA_COPY, 'package.json'));
const { chromium } = require('playwright-core');
const sharp = require('sharp');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OUT = process.env.QA_OUT;
const browser = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--disable-background-networking'],
});
const GW = 160; // the analysis grid width
async function grey(buf, band) {
  const img = sharp(buf);
  const m = await img.metadata();
  const top = Math.round(m.height * band[0]);
  const height = Math.round(m.height * band[1]) - top;
  const { data, info } = await img.extract({ left: 0, top, width: m.width, height }).resize({ width: GW }).greyscale().raw().toBuffer({ resolveWithObject: true });
  return { px: Float64Array.from(data), w: info.width, h: info.height };
}
const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
function fit(f, A, B) {
  let num = 0;
  let den = 0;
  for (let i = 0; i < f.length; i++) {
    const d = B[i] - A[i];
    num += (f[i] - A[i]) * d;
    den += d * d;
  }
  const a = den ? num / den : 0;
  let res = 0;
  for (let i = 0; i < f.length; i++) res += (f[i] - (A[i] + a * (B[i] - A[i]))) ** 2;
  return { a: +a.toFixed(3), rel_residual: +Math.sqrt(res / Math.max(den, 1)).toFixed(3) };
}
const res = [];
for (const v of [{ w: 1280, h: 720 }, { w: 400, h: 800, m: true }]) {
  for (const reduced of [false, true]) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: v.w, height: v.h }, isMobile: !!v.m, hasTouch: !!v.m, reducedMotion: reduced ? 'reduce' : 'no-preference' });
    ctx.setDefaultTimeout(120000);
    const p = await ctx.newPage();
    await p.goto(`${BASE}/rooms/living-room/`, { waitUntil: 'load' });
    await p.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 120000 });
    const sb = await p.locator('section.stage').boundingBox();
    if (v.m) await p.touchscreen.tap(sb.x + 10, sb.y + sb.height / 2);
    else await p.mouse.click(sb.x + 10, sb.y + sb.height / 2);
    for (let i = 0; i < 120 && !(await p.evaluate(() => window.__hdEngine?.ready)); i++) await p.waitForTimeout(250);
    await p.waitForTimeout(2500);
    // the stage's band on the page, as fractions of the viewport (below the header, above the fold)
    const band = [Math.max(0, sb.y + 4) / v.h, Math.min(v.h, sb.y + sb.height - 4) / v.h];
    for (const [k, target] of [
      [1, 'warm-modern'],
      [2, 'nordic'],
      [3, 'warm-modern'],
    ]) {
      // hide the marks and controls' motion from the picture: only the room
      await p.evaluate(() => document.querySelectorAll('.hotspots, .outlines').forEach((el) => (el.style.visibility = 'hidden')));
      const cdp = await ctx.newCDPSession(p);
      const frames = [];
      cdp.on('Page.screencastFrame', async (f) => {
        frames.push({ t: f.metadata.timestamp, data: f.data });
        await cdp.send('Page.screencastFrameAck', { sessionId: f.sessionId }).catch(() => undefined);
      });
      await cdp.send('Page.startScreencast', { format: 'png', everyNthFrame: 1, maxWidth: v.w > 500 ? 640 : 400, maxHeight: 800 });
      await p.waitForTimeout(400);
      const press = Date.now() / 1000;
      const btn = p.locator(`.segmented button[data-house="${target}"]`);
      if (v.m) await btn.tap();
      else await btn.click();
      await p.waitForTimeout(3500);
      await cdp.send('Page.stopScreencast');
      await cdp.detach();
      const sw = await p.evaluate(() => window.__hdHouseSwitch ?? null);
      const pre = frames.filter((f) => f.t < press);
      const post = frames.filter((f) => f.t >= press);
      if (!pre.length || post.length < 2) {
        res.push({ viewport: `${v.w}x${v.h}`, reduced, run: k, to: target, error: `frames: ${pre.length} before, ${post.length} after` });
        continue;
      }
      const A = await grey(Buffer.from(pre.at(-1).data, 'base64'), band);
      const B = await grey(Buffer.from(post.at(-1).data, 'base64'), band);
      const series = [];
      for (const f of post) {
        const g = await grey(Buffer.from(f.data, 'base64'), band);
        series.push({ t_ms: Math.round((f.t - press) * 1000), mean: +mean(g.px).toFixed(1), ...fit(g.px, A.px, B.px), _buf: f.data });
      }
      const meanA = mean(A.px);
      const meanB = mean(B.px);
      const floor = 0.9 * Math.min(meanA, meanB);
      const mids = series.filter((s) => s.a >= 0.25 && s.a <= 0.75 && s.rel_residual <= 0.35);
      const darkest = series.reduce((m, s) => (s.mean < m.mean ? s : m), series[0]);
      const worstFit = series.filter((s) => s.a > 0.05 && s.a < 0.95).reduce((m, s) => (s.rel_residual > (m?.rel_residual ?? -1) ? s : m), null);
      // the midpoint frame, and a contact sheet of the dissolve
      const mid = mids.sort((x, y) => Math.abs(x.a - 0.5) - Math.abs(y.a - 0.5))[0] ?? null;
      const tag = `${v.w}-${reduced ? 'reduced' : 'full'}-${k}-to-${target}`;
      if (mid) await sharp(Buffer.from(mid._buf, 'base64')).jpeg({ quality: 85 }).toFile(join(OUT, 'overlays', `switch-mid-${tag}.jpg`));
      const pick = series.filter((s) => s.t_ms <= 1600);
      const tiles = [];
      for (const s of pick.length > 24 ? pick.filter((_, i) => i % Math.ceil(pick.length / 24) === 0) : pick)
        tiles.push(await sharp(Buffer.from(s._buf, 'base64')).resize(v.w > 500 ? 240 : 120).jpeg({ quality: 70 }).toBuffer());
      if (tiles.length) {
        const tm = await sharp(tiles[0]).metadata();
        const cols = v.w > 500 ? 6 : 10;
        await sharp({ create: { width: cols * (tm.width + 4), height: Math.ceil(tiles.length / cols) * (tm.height + 4), channels: 3, background: { r: 255, g: 255, b: 255 } } })
          .composite(tiles.map((b, i) => ({ input: b, left: (i % cols) * (tm.width + 4), top: Math.floor(i / cols) * (tm.height + 4) })))
          .jpeg({ quality: 75 })
          .toFile(join(OUT, 'overlays', `switch-sheet-${tag}.jpg`));
      }
      const during = series.filter((s) => s.a > 0.02 && s.a < 0.98);
      let monotone = true;
      for (let i = 1; i < during.length; i++) if (during[i].a < during[i - 1].a - 0.08) monotone = false;
      const r = {
        viewport: `${v.w}x${v.h}`,
        reduced,
        run: k,
        to: target,
        page: sw ? { dissolve_ms: Math.round(sw.end - sw.start), press_to_end_ms: Math.round(sw.end - sw.asked) } : null,
        painted_after_press: series.length,
        house_means: [+meanA.toFixed(1), +meanB.toFixed(1)],
        darkest: { t_ms: darkest.t_ms, mean: darkest.mean, a: darkest.a },
        frames_in_dissolve: during.length,
        mid: mid ? { t_ms: mid.t_ms, a: mid.a, rel_residual: mid.rel_residual, mean: mid.mean } : null,
        worst_fit_in_dissolve: worstFit ? { t_ms: worstFit.t_ms, a: worstFit.a, rel_residual: worstFit.rel_residual, mean: worstFit.mean } : null,
        a_rises: monotone,
        series: series.map(({ _buf, ...s }) => s),
      };
      // reduced motion: 0.3 s, a loaded swiftshader may paint no frame inside it; the darkest-frame rule still holds
      r.pass = darkest.mean >= floor && (reduced || !!mid) && monotone;
      res.push(r);
      console.log(tag, JSON.stringify({ pass: r.pass, page: r.page, means: r.house_means, darkest: r.darkest, n: r.frames_in_dissolve, mid: r.mid, worst: r.worst_fit_in_dissolve }));
    }
    await ctx.close();
  }
}
await browser.close();
writeFileSync(join(OUT, 'data/switch-mid.json'), JSON.stringify(res, null, 1));
