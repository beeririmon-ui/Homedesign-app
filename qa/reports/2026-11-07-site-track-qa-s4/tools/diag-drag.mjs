/**
 * qa-agent, 2026-11-07 (S4): why flow.spec "drag with inertia" fails under load. The test's own steps (open the vase's
 * wheel, measure .arc, press at 30 % of its width, eight moves of 5 %, release), instrumented: the pointer events the
 * page receives (target, time, buttons), what sits under the press point, the arc's box when measured and when pressed,
 * running animations at measure time, and the option checked afterwards. N runs; QA_LOAD=1 means the caller loaded the CPU.
 *
 *   QA_BASE=http://127.0.0.1:8799 node …/diag-drag.mjs out.json [runs]
 */
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium, devices } = require('playwright-core');
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8788';
const RUNS = Number(process.argv[3] ?? 6);
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const out = [];
for (let r = 0; r < RUNS; r++) {
  const ctx = await browser.newContext({ ...devices['Desktop Chrome'], locale: 'he-IL' });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/rooms/living-room/`);
  await page.locator('button.hotspot').first().waitFor({ state: 'attached', timeout: 30000 });
  await page.locator('.stage').dispatchEvent('pointerdown');
  await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 30000 });
  await page.evaluate(() => {
    window.__qaEv = [];
    const log = (e) => {
      const t = e.target;
      window.__qaEv.push({ type: e.type, t: Math.round(performance.now()), x: Math.round(e.clientX), id: e.pointerId, target: `${t.tagName?.toLowerCase()}.${[...(t.classList ?? [])].join('.')}`, buttons: e.buttons });
    };
    for (const ty of ['pointerdown', 'pointermove', 'pointerup', 'pointercancel', 'lostpointercapture', 'gotpointercapture', 'click']) document.addEventListener(ty, log, true);
  });
  const t0 = Date.now();
  await page.locator('button.hotspot[data-slot="vase"]').click();
  const arc = page.locator('.arc');
  await arc.waitFor({ state: 'visible' });
  const opened_ms = Date.now() - t0;
  const box = (await arc.boundingBox());
  const FAST = process.env.QA_FAST === '1';
  let atMeasure = null;
  let under = null;
  if (!FAST) {
  atMeasure = await page.evaluate(() => {
    const a = document.querySelector('.arc');
    const dlg = a.closest('[role="dialog"], dialog, .wheel') ?? a.parentElement;
    return {
      anims: document.getAnimations().map((x) => `${x.constructor.name}:${x.animationName ?? x.transitionProperty ?? ''}:${x.playState}:${Math.round(x.currentTime ?? 0)}`).slice(0, 8),
      dialog_transform: getComputedStyle(dlg).transform,
      dialog_opacity: getComputedStyle(dlg).opacity,
      checked: document.querySelector('[role="radio"][aria-checked="true"]')?.getAttribute('aria-label')?.slice(0, 12),
    };
  });
  }
  const y = box.y + box.height / 2;
  const px = box.x + box.width * 0.3;
  if (!FAST) under = await page.evaluate(([x, y]) => {
    const e = document.elementFromPoint(x, y);
    return { el: `${e?.tagName.toLowerCase()}.${[...(e?.classList ?? [])].join('.')}`, in_arc: !!e?.closest('.arc'), arc_now: (() => { const b = document.querySelector('.arc').getBoundingClientRect(); return [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)]; })() };
  }, [px, y]);
  await page.mouse.move(px, y);
  await page.mouse.down();
  for (let i = 1; i <= 8; i++) await page.mouse.move(box.x + box.width * (0.3 + i * 0.05), y);
  await page.mouse.up();
  let checked = null;
  for (let k = 0; k < 25; k++) {
    await page.waitForTimeout(200);
    checked = await page.evaluate(() => document.querySelector('[role="radio"][aria-checked="true"]')?.getAttribute('aria-label')?.slice(0, 12));
    if (checked && !checked.startsWith('1 מתוך')) break;
  }
  const ev = await page.evaluate(() => window.__qaEv);
  const firstDown = ev.find((e) => e.type === 'pointerdown');
  const moves = ev.filter((e) => e.type === 'pointermove' && firstDown && e.t >= firstDown.t);
  out.push({
    run: r + 1,
    load: process.env.QA_LOAD === '1',
    opened_ms,
    box: [Math.round(box.x), Math.round(box.y), Math.round(box.width), Math.round(box.height)],
    at_measure: atMeasure,
    under_press: under,
    events: ev.filter((e) => e.type !== 'pointermove').map((e) => `${e.type}@${e.t}:${e.target}`).slice(-12),
    moves_received: moves.length,
    move_span_ms: moves.length ? moves.at(-1).t - moves[0].t : null,
    up_after_last_move_ms: (() => { const up = ev.find((e) => e.type === 'pointerup' && firstDown && e.t >= firstDown.t); return up && moves.length ? up.t - moves.at(-1).t : null; })(),
    checked_after: checked,
    pass: !!checked && !checked.startsWith('1 מתוך'),
  });
  await ctx.close();
}
await browser.close();
writeFileSync(process.argv[2] ?? '/dev/stdout', JSON.stringify(out, null, 1));
for (const o of out) console.log(JSON.stringify({ run: o.run, pass: o.pass, opened_ms: o.opened_ms, box: o.box, under: o.under_press, measure: o.at_measure, moves: o.moves_received, span: o.move_span_ms, up_gap: o.up_after_last_move_ms, ev: o.events.slice(-6) }));
