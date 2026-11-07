/**
 * qa-agent, 2026-11-07: screenshots of the built page with the dots shown (G5.3 on a screenshot): the phone at 390 x 844
 * for Nordic A and B, and the desktop at 1280 x 800 for Nordic A (the pendant's dot under the top band) and Nordic B.
 * Local preview, local Chromium.
 *
 *   node qa/reports/2026-11-07-site-story-prototype-qa/tools/shots.mjs
 */
import { createRequire } from 'node:module';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const OUT = '/home/user/homedesign-app/qa/reports/2026-11-07-site-story-prototype-qa/overlays';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
for (const vp of [
  { name: 'phone-390', w: 390, h: 844, mobile: true, dpr: 2 },
  { name: 'desk-1280', w: 1280, h: 800, mobile: false, dpr: 1 },
]) {
  const ctx = await browser.newContext({ viewport: { width: vp.w, height: vp.h }, isMobile: vp.mobile, hasTouch: vp.mobile, deviceScaleFactor: vp.dpr, locale: 'he-IL' });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:8788/test/story/', { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  for (const id of ['nordic-A', 'nordic-B']) {
    await page.evaluate((id) => document.getElementById(`frame-${id}`).scrollIntoView({ block: 'start' }), id);
    await page.waitForTimeout(700);
    await page.evaluate((id) => window.__story.showMarks(id), id);
    await page.waitForTimeout(450);
    await page.screenshot({ path: `${OUT}/screen-${vp.name}-${id}-dots.png` });
  }
  await ctx.close();
}
await browser.close();
console.log('ok');
