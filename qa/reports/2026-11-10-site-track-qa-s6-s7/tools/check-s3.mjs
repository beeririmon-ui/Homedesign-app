/**
 * qa-agent, 2026-11-10 (S6-S7; from the S3-S5 tool): S3 in the browser, on QA's snapshot.
 *  1. every "עצב בעצמך" link on the story pages carries from=<its own page>
 *  2. the tool with from=: a story path gets "חזרה לסיפור" (its href exactly that path, on the stage, ≥ 44 px), anything
 *     else gets no link (external, protocol-relative, backslash, javascript:, a non-story path, traversal, encoded)
 *  3. the warm-modern tool draft: the draft mark, the layer stack (one box for all layers), the switch: fade length at
 *     normal and reduced motion, mid-switch opacities, any movement of a layer during the switch, ?house=, the second
 *     house's layers fetched only when chosen
 *   QA_BASE=http://127.0.0.1:8799 node check-s3.mjs out.json
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const OV = '/home/user/homedesign-app/qa/reports/2026-11-10-site-track-qa-s6-s7/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const res = { base: BASE, run_at: new Date().toISOString() };

// 1. the story's links into the tool
{
  const ctx = await browser.newContext({ locale: 'he-IL' });
  const p = await ctx.newPage();
  res.tool_links = [];
  for (const style of ['nordic', 'warm-modern', 'modern-country', 'boho', 'mediterranean', 'japandi']) {
    const path = `/story/living-room/${style}/`;
    await p.goto(BASE + path, { waitUntil: 'load' });
    const links = await p.evaluate(() =>
      [...document.querySelectorAll('a[href*="/rooms/"], a[href*="/tool/"]')].map((a) => ({ id: a.id || null, text: a.textContent.trim().slice(0, 40), href: a.getAttribute('href') })),
    );
    res.tool_links.push({
      page: path,
      links,
      all_carry_from: links.filter((l) => l.href.includes('/rooms/')).every((l) => new URL(l.href, BASE).searchParams.get('from') === path),
    });
  }
  await ctx.close();
}

// 2. the tool's way back
{
  const cases = [
    ['/story/living-room/nordic/', true],
    ['/story/', true],
    ['/story/living-room/boho/', true],
    ['https://evil.example/', false],
    ['//evil.example/', false],
    ['/\\evil.example/', false],
    ['javascript:alert(1)', false],
    ['/rooms/living-room/', false],
    ['/story/../admin/', false],
    ['/story/living-room/nordic', false],
    ['/story//evil.example/', null],
    ['%2F%2Fevil.example%2F', false],
    ['/story/living-room/nordic/?x=1', false],
    ['/story/living-room/nordic/#top', false],
    ['/STORY/living-room/', false],
  ];
  res.from_cases = [];
  for (const w of [1280, 400]) {
    const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: w > 500 ? 900 : 860 } });
    const p = await ctx.newPage();
    for (const [from, expect] of cases) {
      if (w === 400 && from !== '/story/living-room/nordic/') continue;
      const url = `${BASE}/rooms/living-room/?from=${from.startsWith('%') ? from : encodeURIComponent(from)}`;
      await p.goto(url, { waitUntil: 'load' });
      await p.waitForTimeout(500);
      const r = await p.evaluate(() => {
        const a = document.getElementById('back-to-story');
        if (!a) return null;
        const b = a.getBoundingClientRect();
        const st = document.querySelector('.stage')?.getBoundingClientRect();
        return {
          href: a.getAttribute('href'),
          resolved: a.href,
          box: [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)],
          stage: st ? [Math.round(st.left), Math.round(st.top), Math.round(st.width), Math.round(st.height)] : null,
          on_stage: !!st && b.left >= st.left && b.right <= st.right && b.top >= st.top && b.bottom <= st.bottom,
          corner: st ? { from_top: Math.round(b.top - st.top), from_left: Math.round(b.left - st.left), from_right: Math.round(st.right - b.right) } : null,
          blur: getComputedStyle(a).backdropFilter,
          bg: getComputedStyle(a).backgroundColor,
          radius: getComputedStyle(a).borderRadius,
        };
      });
      const sameOrigin = r ? new URL(r.resolved).origin === new URL(BASE).origin : null;
      res.from_cases.push({ width: w, from, expect_link: expect, link: r, same_origin: sameOrigin, ok: expect === null ? !r || sameOrigin : expect ? !!r && r.href === from && sameOrigin : !r });
      if (w === 400 && r) await p.screenshot({ path: `${OV}/tool-back-to-story-400.png` });
      if (w === 1280 && from === '/story/living-room/nordic/') await p.screenshot({ path: `${OV}/tool-back-to-story-1280.png` });
    }
    await ctx.close();
  }
}

// 3. the warm-modern tool draft and the soft switch
const draft = async (w, reduced) => {
  const ctx = await browser.newContext({ locale: 'he-IL', viewport: { width: w, height: w > 500 ? 900 : 860 }, reducedMotion: reduced ? 'reduce' : 'no-preference' });
  const p = await ctx.newPage();
  const fetched = [];
  p.on('request', (q) => {
    if (/\.(webp|avif|png|jpe?g)(\?|$)/.test(q.url())) fetched.push({ t: Date.now(), url: q.url().replace(BASE, '') });
  });
  await p.goto(`${BASE}/story/living-room/warm-modern/tool/`, { waitUntil: 'load' });
  await p.waitForTimeout(1200);
  const t0 = Date.now();
  const before = await p.evaluate(() => {
    const imgs = [...document.querySelectorAll('img')].filter((i) => i.closest('.st-td-stage, .mag-stage, [data-house]'));
    const mark = [...document.querySelectorAll('*')].find((e) => /טיוטה/.test(e.textContent ?? '') && e.children.length === 0);
    return {
      title: document.title,
      robots: document.querySelector('meta[name="robots"]')?.content ?? null,
      mark: mark ? { text: mark.textContent.trim(), box: (() => { const b = mark.getBoundingClientRect(); return [Math.round(b.left), Math.round(b.top), Math.round(b.width), Math.round(b.height)]; })() } : null,
      switch: [...document.querySelectorAll('button, [role="radio"], input[type="radio"]')].filter((b) => /נורדי|מודרני/.test(b.closest('label')?.textContent ?? b.textContent ?? '')).map((b) => ({ tag: b.tagName.toLowerCase(), text: (b.closest('label')?.textContent ?? b.textContent).trim(), pressed: b.getAttribute('aria-pressed') ?? b.getAttribute('aria-checked') ?? (b.checked ?? null) })),
      layers: imgs.map((i) => {
        const b = i.getBoundingClientRect();
        const s = getComputedStyle(i);
        return { src: (i.currentSrc || i.src).split('/').slice(-2).join('/'), house: i.closest('[data-house]')?.dataset.house ?? null, box: [b.left, b.top, b.width, b.height].map((v) => Math.round(v * 10) / 10), blend: s.mixBlendMode, opacity: getComputedStyle(i.closest('[data-house]') ?? i).opacity };
      }),
      html_house: [...document.querySelectorAll('[data-house]')].map((e) => ({ house: e.dataset.house, opacity: getComputedStyle(e).opacity, transition: getComputedStyle(e).transition })),
    };
  });
  const fetchedBefore = fetched.map((f) => f.url);
  // the switch
  const btn = p.locator('button, [role="radio"], label').filter({ hasText: 'נורדי' }).first();
  await p.evaluate(() => {
    window.__sw = [];
    const houses = () => [...document.querySelectorAll('[data-house]')];
    const t0 = performance.now();
    const loop = () => {
      const t = performance.now() - t0;
      window.__sw.push({ t: Math.round(t), o: houses().map((h) => [h.dataset.house, Number(getComputedStyle(h).opacity)]), tr: houses().map((h) => getComputedStyle(h).transform), boxes: [...document.querySelectorAll('[data-house] img')].map((i) => { const b = i.getBoundingClientRect(); return [b.left, b.top, b.width, b.height].map((v) => Math.round(v * 10) / 10).join(','); }) });
      if (t < 2500) requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  });
  const tClick = Date.now();
  await btn.click();
  await p.waitForTimeout(2600);
  const sw = await p.evaluate(() => window.__sw);
  const url = p.url();
  const after = await p.evaluate(() => [...document.querySelectorAll('[data-house]')].map((e) => ({ house: e.dataset.house, opacity: getComputedStyle(e).opacity })));
  const fetchedAfter = fetched.filter((f) => f.t >= tClick - 50).map((f) => f.url);
  await p.screenshot({ path: `${OV}/tool-draft-after-switch-${w}${reduced ? '-reduced' : ''}.png` });
  await ctx.close();
  // the fade: from the first frame where any house's opacity is strictly between 0 and 1 to the last
  const moving = sw.filter((s) => s.o.some(([, o]) => o > 0.01 && o < 0.99));
  const fade_ms = moving.length ? moving.at(-1).t - moving[0].t : 0;
  const mid = moving.length ? moving[Math.floor(moving.length / 2)] : null;
  const allBoxes = new Set(sw.flatMap((s) => s.boxes));
  const transforms = new Set(sw.flatMap((s) => s.tr));
  return { width: w, reduced, before, fetched_before_switch: fetchedBefore, fetched_on_switch: fetchedAfter, url_after: url, after, frames_sampled: sw.length, fade_frames: moving.length, fade_ms_approx: fade_ms, mid_switch: mid ? { t: mid.t, o: mid.o } : null, distinct_layer_boxes_during_switch: [...allBoxes], distinct_transforms: [...transforms] };
};
res.draft = [await draft(1280, false), await draft(400, false), await draft(1280, true)];
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(res, null, 1));
console.log('done');
