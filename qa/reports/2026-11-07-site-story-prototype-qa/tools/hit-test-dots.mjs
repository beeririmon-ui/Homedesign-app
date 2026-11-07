/**
 * qa-agent, 2026-11-07: can every visible dot be touched where it is drawn? For each frame, the page is scrolled the
 * way a reader arrives (the frame's section at the top of the window), the dots are shown (pointer move / touch), and
 * document.elementFromPoint at each dot's centre must return the dot's own button (not the top band, the draft chip or
 * another dot). Also records where each dot lands in frame pixels, for the overlays.
 *
 *   node qa/reports/2026-11-07-site-story-prototype-qa/tools/hit-test-dots.mjs [out.json]
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const OUT = process.argv[2] ?? '/dev/stdout';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = {};
for (const vp of [
  { name: 'phone_390', w: 390, h: 844, mobile: true },
  { name: 'desk_1280', w: 1280, h: 800, mobile: false },
  { name: 'desk_1440', w: 1440, h: 900, mobile: false },
]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, locale: 'he-IL' });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8788/test/story/', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  res[vp.name] = {};
  for (const id of ['nordic-A', 'nordic-B', 'warm-modern-A']) {
    await page.evaluate((id) => document.getElementById(`frame-${id}`).scrollIntoView({ block: 'start' }), id);
    await page.waitForTimeout(600);
    await page.evaluate((id) => window.__story.showMarks(id), id);
    await page.waitForTimeout(400);
    res[vp.name][id] = await page.evaluate((id) => {
      const head = document.getElementById('mag-head').getBoundingClientRect();
      const stage = document.querySelector(`#frame-${id} .mag-stage`);
      const frame = document.querySelector(`#frame-${id} .mag-frame`).getBoundingClientRect();
      const data = JSON.parse(document.getElementById('st-data').textContent);
      const fr = data.frames.find((f) => f.id === id);
      return {
        head_bottom: Math.round(head.bottom),
        stage_top: Math.round(stage.getBoundingClientRect().top),
        marks: [...stage.querySelectorAll('.st-mark')]
          .filter((m) => !m.hidden && getComputedStyle(m).display !== 'none')
          .map((m) => {
            const r = m.getBoundingClientRect();
            const cx = r.x + r.width / 2;
            const cy = r.y + r.height / 2;
            const hit = document.elementFromPoint(cx, cy);
            const own = !!hit && (hit === m || m.contains(hit));
            // the dot's place in the whole frame (u, v): desktop from the frame box; phone from the crop
            let u = (cx - frame.x) / frame.width;
            const v = (cy - frame.y) / frame.height;
            if (window.matchMedia('(max-width: 719px)').matches) u = fr.crop[0] + u * (fr.crop[1] - fr.crop[0]);
            return {
              item: m.dataset.item,
              product: data.items[m.dataset.item].product,
              cx: Math.round(cx),
              cy: Math.round(cy),
              u: Math.round(u * 10000) / 10000,
              v: Math.round(v * 10000) / 10000,
              hit_own_button: own,
              hit: own ? null : hit ? `${hit.tagName.toLowerCase()}${hit.id ? '#' + hit.id : ''}.${[...hit.classList].join('.')}` : null,
              under_top_band: cy - 23 < head.bottom,
            };
          }),
      };
    }, id);
  }
  await ctx.close();
}
await browser.close();
writeFileSync(OUT, JSON.stringify(res, null, 1));
for (const [vp, frames] of Object.entries(res))
  for (const [id, f] of Object.entries(frames)) {
    const bad = f.marks.filter((m) => !m.hit_own_button || m.under_top_band);
    console.log(`${vp} ${id}: head bottom ${f.head_bottom}, stage top ${f.stage_top}, ${f.marks.length} dots, ${bad.length} not clean: ${bad.map((m) => `${m.item} (${m.product}) hit=${m.hit} under_band=${m.under_top_band} cy=${m.cy}`).join('; ') || '-'}`);
  }
