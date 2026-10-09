/**
 * Room engine evidence on dist-artifact (Chromium + SwiftShader, 1280×800):
 *   variants   for every slot: the composed room at option 1 and option 2/3, and a pixel diff that must be zero
 *              outside the product's bounding box (tools/temp boxes + a 3 px resampling margin).
 *   hotspots   the product rings at rest and the glow state (hover/focus).
 *   transition 6 frames along T-E0 (hall → living room), the last one after the landing, plus a check that the
 *              landed frame equals the room at rest (no jump at the hand-off).
 *
 *   npm run screens:room            (after npm run preview:artifact)
 *   npm run screens:room -- --before   writes the same evidence with a "before-" prefix (for a comparison run)
 */
import { spawn } from 'node:child_process';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { chromium, type Page } from '@playwright/test';
import sharp from 'sharp';
import { sitePath } from './lib/paths';

type Box = [number, number, number, number];
const PORT = 5198;
const ORIGIN = `http://127.0.0.1:${PORT}`;
const OUT = sitePath('screens');
const PREFIX = process.argv.includes('--before') ? 'before-' : '';
const ONLY = process.argv.find((a) => a.startsWith('--only='))?.slice(7);
mkdirSync(OUT, { recursive: true });

const temp = JSON.parse(readFileSync(sitePath('tools/temp/living-room.nordic.json'), 'utf8')) as {
  slots: Record<string, { boxes: Box[]; ellipses?: [number, number, number, number][]; visible?: boolean }>;
};
const shapeBoxes = (id: string): Box[] => {
  const t = temp.slots[id];
  if (!t) return [];
  return [...t.boxes, ...(t.ellipses ?? []).map((e): Box => [e[0] - e[2], e[0] + e[2], e[1] - e[3], e[1] + e[3]])];
};

const server = spawn('python3', ['-m', 'http.server', String(PORT), '--bind', '127.0.0.1', '-d', sitePath('dist-artifact')], { stdio: 'ignore' });
process.on('exit', () => server.kill());
await new Promise((r) => setTimeout(r, 700));
const html = readFileSync(sitePath('dist-artifact/index.html'), 'utf8');
const wrapped = `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head><body>${html}</body></html>`;

const browser = await chromium.launch({
  executablePath: process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium',
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'],
});
const W = 1280;
const H = 800;
const problems: string[] = [];
const report: string[] = [];

async function newPage(): Promise<Page> {
  const ctx = await browser.newContext({ viewport: { width: W, height: H }, deviceScaleFactor: 1, locale: 'he-IL' });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => problems.push(`pageerror: ${e.message}`));
  await page.route(`${ORIGIN}/`, (route) => route.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: wrapped }));
  return page;
}

// a string, not a closure: tsx (esbuild keepNames) would inject a __name helper the page does not have
const frames = (page: Page, n = 3) =>
  page.evaluate(`new Promise((r) => { let i = 0; const f = () => (++i >= ${n} ? r() : requestAnimationFrame(f)); requestAnimationFrame(f); })`);

async function stageShot(page: Page): Promise<{ png: Buffer; raw: Buffer; w: number; h: number; x: number; y: number }> {
  const r = (await page.locator('.stage').boundingBox())!;
  const png = await page.screenshot({ clip: { x: r.x, y: r.y, width: r.width, height: r.height } });
  const { data, info } = await sharp(png).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  return { png, raw: data, w: info.width, h: info.height, x: r.x, y: r.y };
}

async function openRoom(page: Page): Promise<void> {
  await page.goto(`${ORIGIN}/`, { waitUntil: 'load' });
  await page.evaluate(() => matchMedia('(prefers-reduced-motion: reduce)').matches);
  await page.getByRole('link', { name: 'היכנסו לסלון' }).click();
  await page.locator('button.hotspot:visible').first().waitFor({ timeout: 20_000 });
  await page.waitForTimeout(800);
}

// ---------------- 1. variants ----------------
async function variants(): Promise<void> {
  const page = await newPage();
  await page.emulateMedia({ reducedMotion: 'reduce' }); // no transition overlay, no cross-fade: compare settled frames
  await openRoom(page);
  await page.mouse.move(640, 400);
  await page.mouse.down();
  await page.mouse.up();
  await page.waitForFunction(() => window.__hdEngine?.ready === true, undefined, { timeout: 20_000 });
  await page.addStyleTag({ content: '.hotspots,.stage-ui,.stage-temp-note,.stage-vignette{display:none!important}' });
  // all variant layers decoded and on the GPU before measuring
  const slots = (await page.evaluate(() => Object.keys(window.__hdEngine!.getSelection()))) as string[];
  await page.waitForTimeout(2500);
  const sheet: { input: Buffer; left: number; top: number }[] = [];
  const TW = 400;
  const TH = 250;
  let row = 0;
  for (const slot of slots) {
    if (ONLY && slot !== ONLY) continue;
    const boxes = shapeBoxes(slot);
    if (!boxes.length) continue;
    await page.evaluate((s) => window.__hdEngine!.setSelection(s, 1, 0), slot);
    await frames(page);
    const a = await stageShot(page);
    const cam = (await page.evaluate(() => {
      const e = window.__hdEngine!;
      return { cam: e.cam, vp: e.vp, aspect: e.aspect };
    })) as { cam: { cu: number; cv: number; z: number }; vp: { w: number; h: number }; aspect: number };
    const fw = Math.max(cam.vp.w, cam.vp.h * cam.aspect);
    const fh = fw / cam.aspect;
    const toPx = (u: number, v: number) => [cam.vp.w / 2 + (u - cam.cam.cu) * fw * cam.cam.z, cam.vp.h / 2 + (v - cam.cam.cv) * fh * cam.cam.z] as const;
    const pxBoxes = boxes.map((b) => {
      const [x0, y0] = toPx(b[0], b[2]);
      const [x1, y1] = toPx(b[1], b[3]);
      return [x0 - 3, x1 + 3, y0 - 3, y1 + 3];
    });
    const union = [Math.min(...pxBoxes.map((b) => b[0]!)), Math.max(...pxBoxes.map((b) => b[1]!)), Math.min(...pxBoxes.map((b) => b[2]!)), Math.max(...pxBoxes.map((b) => b[3]!))];
    const inBox = (x: number, y: number) => pxBoxes.some((b) => x >= b[0]! && x <= b[1]! && y >= b[2]! && y <= b[3]!);
    for (const n of [2, 3]) {
      await page.evaluate(([s, k]) => window.__hdEngine!.setSelection(s as string, k as number, 0), [slot, n]);
      await frames(page);
      const b = await stageShot(page);
      let outside = 0;
      let outsideMax = 0;
      let inside = 0;
      const diff = Buffer.alloc(a.w * a.h * 3);
      for (let y = 0; y < a.h; y++)
        for (let x = 0; x < a.w; x++) {
          const i = (y * a.w + x) * 3;
          const d = Math.max(Math.abs(a.raw[i]! - b.raw[i]!), Math.abs(a.raw[i + 1]! - b.raw[i + 1]!), Math.abs(a.raw[i + 2]! - b.raw[i + 2]!));
          const inside_ = inBox(x, y);
          if (d > 3) {
            if (inside_) inside++;
            else {
              outside++;
              outsideMax = Math.max(outsideMax, d);
            }
          }
          const v = Math.min(255, d * 6);
          diff[i] = inside_ ? v : 255 * Number(d > 3);
          diff[i + 1] = inside_ ? v : 0;
          diff[i + 2] = inside_ ? v : 0;
        }
      const ok = outside === 0;
      report.push(`${ok ? 'PASS' : 'FAIL'}  ${slot} 1→${n}: changed pixels inside bbox ${inside}, outside bbox ${outside} (max Δ ${outsideMax})`);
      if (!ok) problems.push(`variant ${slot} 1→${n}: ${outside} pixels changed outside the product bbox`);
      if (n === 2) {
        // crop around the product for the evidence sheet: before | after | diff (red = outside the bbox)
        const pad = 60;
        const cx0 = Math.max(0, Math.floor(union[0]! - pad));
        const cy0 = Math.max(0, Math.floor(union[2]! - pad));
        const cw = Math.min(a.w - cx0, Math.ceil(union[1]! - union[0]! + 2 * pad));
        const ch = Math.min(a.h - cy0, Math.ceil(union[3]! - union[2]! + 2 * pad));
        const crop = async (buf: Buffer, raw = false) =>
          (raw ? sharp(buf, { raw: { width: a.w, height: a.h, channels: 3 } }) : sharp(buf))
            .extract({ left: cx0, top: cy0, width: cw, height: ch })
            .resize(TW, TH, { fit: 'contain', background: '#141312' })
            .png()
            .toBuffer();
        sheet.push({ input: await crop(a.png), left: 0, top: row * TH });
        sheet.push({ input: await crop(b.png), left: TW, top: row * TH });
        sheet.push({ input: await crop(diff, true), left: 2 * TW, top: row * TH });
        row++;
      }
    }
    if (slot === 'vase' || slot === 'cushions') {
      writeFileSync(`${OUT}/${PREFIX}variant-${slot}-1.png`, a.png);
      await page.evaluate(([s]) => window.__hdEngine!.setSelection(s as string, 2, 0), [slot]);
      await frames(page);
      writeFileSync(`${OUT}/${PREFIX}variant-${slot}-2.png`, (await stageShot(page)).png);
    }
    await page.evaluate((s) => window.__hdEngine!.setSelection(s, 1, 0), slot);
  }
  if (row)
    await sharp({ create: { width: 3 * TW, height: row * TH, channels: 3, background: '#000' } })
      .composite(sheet)
      .png()
      .toFile(`${OUT}/${PREFIX}variants-sheet.png`);
  // poster (shell) vs engine composition at the default selection: the temporary layers must not add anything
  await page.evaluate(() => {
    const e = window.__hdEngine!;
    const sel = e.getSelection();
    return Promise.all(Object.keys(sel).map((s) => e.setSelection(s, 1, 0)));
  });
  await frames(page);
  const comp = await stageShot(page);
  await page.evaluate(() => {
    (document.querySelector('.room-canvas') as HTMLElement).style.visibility = 'hidden';
  });
  await frames(page);
  const poster = await stageShot(page);
  let changed = 0;
  let maxD = 0;
  for (let i = 0; i < comp.raw.length; i += 3) {
    const d = Math.max(Math.abs(comp.raw[i]! - poster.raw[i]!), Math.abs(comp.raw[i + 1]! - poster.raw[i + 1]!), Math.abs(comp.raw[i + 2]! - poster.raw[i + 2]!));
    if (d > 12) changed++;
    maxD = Math.max(maxD, d);
  }
  report.push(`poster vs composed default: ${changed} pixels differ by more than 12 levels (max Δ ${maxD})`);
  writeFileSync(`${OUT}/${PREFIX}room-composed-default.png`, comp.png);
  await page.context().close();
}

// ---------------- 2. hotspots ----------------
async function hotspots(): Promise<void> {
  const page = await newPage();
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await openRoom(page);
  await page.screenshot({ path: `${OUT}/${PREFIX}hotspots-rest.png` });
  const vase = page.locator('button.hotspot[data-slot="vase"]');
  await vase.hover();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/${PREFIX}hotspots-glow-hover.png` });
  await page.mouse.move(5, 5);
  await page.keyboard.press('Tab');
  await page.locator('button.hotspot[data-slot="framed-art"]').focus();
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/${PREFIX}hotspots-glow-focus.png` });
  await page.context().close();
}

// ---------------- 3. transition ----------------
async function transition(): Promise<void> {
  const page = await newPage();
  await page.goto(`${ORIGIN}/`, { waitUntil: 'load' });
  await page.getByRole('heading', { level: 1 }).first().waitFor();
  await page.waitForTimeout(3000); // T-E0 preloaded
  // a timeline of screenshots: start, three during the walk, the hand-off, the landing
  const t0 = Date.now();
  await page.getByRole('link', { name: 'היכנסו לסלון' }).click();
  const shots: { t: number; png: Buffer }[] = [];
  while (Date.now() - t0 < 6500) {
    shots.push({ t: Date.now() - t0, png: await page.screenshot() });
    const done = await page.evaluate(() => !document.querySelector('.seq-overlay') && window.__hdEngine?.ready === true);
    if (done && shots.length > 2) break;
  }
  await page.waitForTimeout(600);
  shots.push({ t: Date.now() - t0, png: await page.screenshot() });
  const pick = [0, 0.2, 0.4, 0.6, 0.8, 1].map((k) => shots[Math.round(k * (shots.length - 1))]!);
  for (const [i, s] of pick.entries()) writeFileSync(`${OUT}/${PREFIX}transition-${i + 1}.png`, s.png);
  report.push(`transition: ${shots.length} screenshots over ${shots[shots.length - 1]!.t} ms (SwiftShader; frame pacing is not representative)`);
  // landing check: the last screenshot of the sequence vs the room at rest a moment later
  const rest = await page.screenshot();
  const a = await sharp(pick[5]!.png).removeAlpha().raw().toBuffer();
  const b = await sharp(rest).removeAlpha().raw().toBuffer();
  let diff = 0;
  for (let i = 0; i < a.length; i += 3) if (Math.abs(a[i]! - b[i]!) > 12) diff++;
  report.push(`transition landing: ${diff} pixels differ between the landed frame and the room at rest`);
  const tw = 427;
  const th = 267;
  await sharp({ create: { width: tw * 3, height: th * 2, channels: 3, background: '#000' } })
    .composite(await Promise.all(pick.map(async (s, i) => ({ input: await sharp(s.png).resize(tw, th).png().toBuffer(), left: (i % 3) * tw, top: Math.floor(i / 3) * th }))))
    .png()
    .toFile(`${OUT}/${PREFIX}transition-sheet.png`);
  await page.context().close();
}

try {
  const which = process.argv.find((a) => a.startsWith('--part='))?.slice(7);
  if (!which || which === 'variants') await variants();
  if (!which || which === 'hotspots') await hotspots();
  if (!which || which === 'transition') await transition();
} catch (e) {
  problems.push(`failed: ${e instanceof Error ? e.stack : String(e)}`);
} finally {
  await browser.close();
  server.kill();
}
for (const r of report) console.log(r);
console.log(`screenshots: ${OUT}/${PREFIX}*.png`);
if (problems.length) {
  for (const p of problems) console.error(`FAIL  ${p}`);
  process.exit(1);
}
