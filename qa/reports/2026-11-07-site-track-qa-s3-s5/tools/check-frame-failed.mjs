/**
 * qa-agent, 2026-11-07 (S3-S5): the S5 error state. The frame's image requests are aborted (every width and format);
 * then: the message (text, role, where it sits), dots (none, also after a resize and after the frame is scrolled
 * into view), the list (whole), what the stage shows (no broken image, no grey box), the sheet from the list, axe.
 * Cases: boho A at 400 and 1280; nordic B only (A loads) at 1280; a slow-then-failed frame (6 s, then abort).
 *   QA_BASE=http://127.0.0.1:8799 node check-frame-failed.mjs out.json
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const AXE = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-07-site-track-qa-s3-s5/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
const res = [];
const run = async (style, frame, w, delay = 0) => {
  const ctx = await browser.newContext({ locale: 'he-IL', bypassCSP: true, viewport: { width: w, height: w > 500 ? 900 : 860 } });
  const p = await ctx.newPage();
  const rx = new RegExp(`/media/story/living-room/${style}/${frame}/(m?\\d+)\\.(avif|webp)`);
  let aborted = 0;
  await p.route(rx, async (route) => {
    aborted++;
    if (delay) await new Promise((r) => setTimeout(r, delay));
    await route.abort('failed');
  });
  await p.goto(`${BASE}/story/living-room/${style}/`, { waitUntil: 'load' });
  await p.locator(`#frame-${frame}`).scrollIntoViewIfNeeded();
  await p.waitForTimeout(delay + 1500);
  const read = () =>
    p.evaluate((frame) => {
      const sec = document.getElementById(`frame-${frame}`);
      const stage = sec.querySelector('.mag-stage');
      const msg = stage.querySelector('.st-img-error');
      const sb = stage.getBoundingClientRect();
      const mb = msg?.getBoundingClientRect();
      const img = stage.querySelector('img');
      const marks = [...sec.querySelectorAll('button.st-mark, .st-mark, [data-mark], button.mag-mark')].filter((m) => !m.hidden && getComputedStyle(m).display !== 'none' && getComputedStyle(m).visibility !== 'hidden');
      const d = JSON.parse(document.getElementById('st-data').textContent);
      const f = d.frames.find((x) => x.id === frame);
      return {
        failed_attr: stage.dataset.failed ?? null,
        message: msg ? { text: msg.textContent, role: msg.getAttribute('role'), box: [mb.left, mb.top - sb.top, mb.width, mb.height].map(Math.round), stage: [sb.width, sb.height].map(Math.round), bg: getComputedStyle(msg).backgroundColor } : null,
        visible_marks: marks.length,
        img: img ? { natural: img.naturalWidth, visibility: getComputedStyle(img).visibility, opacity: getComputedStyle(img).opacity, display: getComputedStyle(img).display } : null,
        stage_bg: getComputedStyle(stage).backgroundImage.slice(0, 60),
        list_items: sec.querySelectorAll('.st-credit').length || document.querySelectorAll(`.st-credit`).length,
        frame_items: f.items.length,
      };
    }, frame);
  const r0 = await read();
  await p.setViewportSize({ width: w > 500 ? 1000 : 360, height: 800 });
  await p.waitForTimeout(500);
  const r1 = await read();
  await p.setViewportSize({ width: w, height: w > 500 ? 900 : 860 });
  await p.waitForTimeout(400);
  await p.screenshot({ path: `${OV}/frame-failed-${style}-${frame}-${w}${delay ? '-slow' : ''}.png` });
  // the sheet from the list still opens
  const first = p.locator(`#frame-${frame} .st-open, .st-credit .st-open`).first();
  let sheet = null;
  if (await first.count()) {
    await first.click();
    await p.waitForTimeout(500);
    sheet = await p.evaluate(() => {
      const s = document.getElementById('st-sheet');
      const im = document.getElementById('st-sheet-img');
      return { open: !!s && (s.open || !s.hidden), img_natural: im?.naturalWidth ?? null, img_hidden: im ? im.hidden || getComputedStyle(im).display === 'none' : null };
    });
    await p.keyboard.press('Escape');
  }
  await p.addScriptTag({ content: AXE });
  const axe = await p.evaluate(async () => (await window.axe.run(document, { runOnly: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] })).violations.map((v) => `${v.id}: ${v.nodes.length}`));
  res.push({ style, frame, width: w, delay_ms: delay, aborted_requests: aborted, at_load: r0, after_resize: r1, sheet_from_list: sheet, axe });
  await ctx.close();
};
await run('boho', 'A', 400);
await run('boho', 'A', 1280);
await run('nordic', 'B', 1280);
await run('mediterranean', 'A', 1280, 6000);
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log(JSON.stringify(res, null, 1));
