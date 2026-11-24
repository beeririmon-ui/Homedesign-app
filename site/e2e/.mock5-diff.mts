import { chromium } from '@playwright/test';
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, locale: 'he-IL' });
const page = await ctx.newPage();
const rest = () => page.waitForFunction(() => window.__hdTourState?.phase === 'room' && window.__hdTourState.busy === false && window.__hdTour?.busy === false, undefined, { timeout: 120000 });
const grab = () => page.evaluate(() => { const e = window.__hdTour!; return Array.from(e.read([0, 0, e.gl.width, e.gl.height])); });
const [from, to] = [process.argv[2]!, process.argv[3]!];
await page.goto(`http://127.0.0.1:8788/tour/?skip=1&room=${to}`);
await page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60000 });
await rest();
const A = await grab();
const W = await page.evaluate(() => window.__hdTour!.gl.width);
await page.goto(`http://127.0.0.1:8788/tour/?skip=1&room=${from}`);
await page.waitForFunction(() => window.__hdTour?.ready === true, undefined, { timeout: 60000 });
await rest();
await page.locator(`.tour-frames button[data-frame="${to}"]`).click();
await page.waitForFunction((x) => window.__hdTourState?.room === x, to);
await rest();
const B = await grab();
let n = 0, x0 = 1e9, y0 = 1e9, x1 = -1, y1 = -1, mx = 0;
for (let i = 0; i < A.length; i += 4) {
  const d = Math.max(Math.abs(A[i]! - B[i]!), Math.abs(A[i + 1]! - B[i + 1]!), Math.abs(A[i + 2]! - B[i + 2]!));
  if (d) { n++; const p = i / 4, x = p % W, y = Math.floor(p / W); x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); mx = Math.max(mx, d); }
}
console.log({ W, n, box: [x0, y0, x1, y1], mx });
await b.close();
