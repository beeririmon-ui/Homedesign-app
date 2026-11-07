/**
 * qa-agent, 2026-11-07 (interface track S4; a copy of the S1/S2 tool with boho and QA_BASE): can every visible dot on the story pages be touched where it is drawn?
 * For each /story/<room>/<style>/ page with frames, and each frame on it, the page is scrolled the way a reader arrives
 * (the frame's section at the top), the dots are shown (window.__story.showMarks), and document.elementFromPoint at each
 * dot's centre must return the dot's own button (not the top band, the draft chip or another dot). Also: the dot's place
 * in frame units (u, v), the pairwise centre distances, and whether a 46 x 46 target overlaps another.
 * Local preview, local Chromium (/opt/pw-browsers/chromium).
 *
 *   QA_VIEWPORTS='[{"name":"phone_390","w":390,"h":844,"mobile":true}]' node …/hit-test-story.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const OUT = process.argv[2] ?? '/dev/stdout';
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8788';
const PAGES = ['nordic', 'warm-modern', 'modern-country', 'boho'].map((s) => `/story/living-room/${s}/`);
const VPS = JSON.parse(process.env.QA_VIEWPORTS ?? 'null') ?? [
  { name: 'phone_390', w: 390, h: 844, mobile: true },
  { name: 'phone_360', w: 360, h: 780, mobile: true },
  { name: 'desk_1280', w: 1280, h: 800, mobile: false },
  { name: 'desk_1280x720', w: 1280, h: 720, mobile: false },
  { name: 'desk_1440', w: 1440, h: 900, mobile: false },
  { name: 'desk_1920', w: 1920, h: 1080, mobile: false },
];
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = {};
for (const vp of VPS) {
  res[vp.name] = {};
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, locale: 'he-IL' });
  for (const path of PAGES) {
    const page = await ctx.newPage();
    await page.goto(BASE + path, { waitUntil: 'load' });
    await page.waitForTimeout(1500);
    const frames = await page.evaluate(() => JSON.parse(document.getElementById('st-data').textContent).frames.map((f) => f.id));
    for (const id of frames) {
      await page.evaluate((id) => document.getElementById(`frame-${id}`).scrollIntoView({ block: 'start' }), id);
      await page.waitForTimeout(600);
      await page.evaluate((id) => window.__story.showMarks(id), id);
      await page.waitForTimeout(400);
      const r = await page.evaluate((id) => {
        const head = document.getElementById('mag-head').getBoundingClientRect();
        const stage = document.querySelector(`#frame-${id} .mag-stage`);
        const frame = document.querySelector(`#frame-${id} .mag-frame`).getBoundingClientRect();
        const data = JSON.parse(document.getElementById('st-data').textContent);
        const fr = data.frames.find((f) => f.id === id);
        const phone = window.matchMedia('(max-width: 719px)').matches;
        const draft = stage.querySelector('.st-draft');
        const marks = [...stage.querySelectorAll('.st-mark')]
          .filter((m) => !m.hidden && getComputedStyle(m).display !== 'none')
          .map((m) => {
            const b = m.getBoundingClientRect();
            const cx = b.x + b.width / 2;
            const cy = b.y + b.height / 2;
            const hit = document.elementFromPoint(cx, cy);
            const own = !!hit && (hit === m || m.contains(hit));
            let u = (cx - frame.x) / frame.width;
            const v = (cy - frame.y) / frame.height;
            if (phone) u = fr.crop[0] + u * (fr.crop[1] - fr.crop[0]);
            return {
              item: m.dataset.item,
              product: data.items[m.dataset.item].product,
              cx: Math.round(cx),
              cy: Math.round(cy),
              u: Math.round(u * 10000) / 10000,
              v: Math.round(v * 10000) / 10000,
              hit_own_button: own,
              hit: own ? null : hit ? `${hit.tagName.toLowerCase()}${hit.id ? '#' + hit.id : ''}.${[...hit.classList].join('.')}` : null,
              target_top_under_band: cy - 23 < head.bottom,
            };
          });
        const pairs = [];
        for (let i = 0; i < marks.length; i++)
          for (let j = i + 1; j < marks.length; j++) {
            const dx = Math.abs(marks[i].cx - marks[j].cx);
            const dy = Math.abs(marks[i].cy - marks[j].cy);
            pairs.push({ a: marks[i].item, b: marks[j].item, dist: Math.round(Math.hypot(dx, dy) * 10) / 10, squares_overlap: dx < 46 && dy < 46 });
          }
        pairs.sort((p, q) => p.dist - q.dist);
        return {
          head_bottom: Math.round(head.bottom),
          draft: draft ? { text: draft.textContent, visible: draft.getBoundingClientRect().width > 0 } : null,
          dots_listed: data.frames.find((f) => f.id === id).items.filter((x) => data.items[x].dot).length,
          marks,
          closest: pairs.slice(0, 2),
          overlaps: pairs.filter((p) => p.dist < 44 || p.squares_overlap),
        };
      }, id);
      res[vp.name][`${path}#${id}`] = r;
    }
    await page.close();
  }
  await ctx.close();
}
await browser.close();
writeFileSync(OUT, JSON.stringify(res, null, 1));
for (const [vp, fr] of Object.entries(res))
  for (const [k, f] of Object.entries(fr)) {
    const bad = f.marks.filter((m) => !m.hit_own_button);
    const band = f.marks.filter((m) => m.target_top_under_band).map((m) => m.item);
    console.log(`${vp} ${k}: ${f.marks.length}/${f.dots_listed} shown, not own ${bad.length}${bad.length ? ' ' + bad.map((m) => `${m.item}:${m.hit}`).join(',') : ''}, overlaps ${f.overlaps.length}, closest ${f.closest[0]?.dist ?? '-'}, band-top ${band.join(',') || '-'}, draft ${f.draft?.visible ? f.draft.text : 'NONE'}`);
  }
