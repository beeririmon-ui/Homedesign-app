/**
 * qa-agent, 2026-11-07 (interface track S2): the detail pages (/story/<room>/<style>/p/<product>/), checked in the
 * browser against their own data block, independently of the page's code:
 *  - every SKU (through window.__story.detail().choose): price, credit (material · size · price), the size and lead-time
 *    specs, the picture and its caption, the add button or the reason, and the address (?axis=value; none for the
 *    story's option);
 *  - a supplier photo is captioned "באפשרות X" only when the picture is X's own photo, and no picture is the own photo of
 *    two options with different colours (it would be captioned as both);
 *  - a product without a price or without stock: no add button (and never a disabled one), the reason in its place;
 *  - the real controls: on pages with options, a radio or select is changed by the keyboard / click and the page follows;
 *  - an address that names an option opens on it.
 * Local preview, local Chromium.
 *
 *   node qa/reports/2026-11-07-site-track-qa-s1-s2/tools/check-detail.mjs out.json
 */
import { createRequire } from 'node:module';
import { readdirSync, writeFileSync } from 'node:fs';

const require = createRequire('/home/user/homedesign-app/site/package.json');
const { chromium } = require('playwright-core');
const OUT = process.argv[2] ?? '/dev/stdout';
const BASE = 'http://127.0.0.1:8788';
const DIST = '/home/user/homedesign-app/site/web/dist/story/living-room';
const pages = [];
for (const style of readdirSync(DIST)) {
  let ps = [];
  try {
    ps = readdirSync(`${DIST}/${style}/p`);
  } catch {}
  for (const p of ps) pages.push(`/story/living-room/${style}/p/${p}/`);
}
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: 'he-IL' });
const results = [];
for (const path of pages) {
  const page = await ctx.newPage();
  await page.goto(BASE + path, { waitUntil: 'load' });
  await page.waitForFunction(() => !!window.__story?.detail?.(), undefined, { timeout: 15000 });
  const r = await page.evaluate(async () => {
    const d = JSON.parse(document.getElementById('st-data').textContent).detail;
    const api = window.__story.detail();
    const $ = (id) => document.getElementById(id);
    const txt = (el) => (el && !el.hidden ? el.textContent.trim() : null);
    const keyQuery = (k) => {
      if (!d.axes.length || k.key === d.story_key) return '';
      const q = new URLSearchParams();
      for (const a of d.axes) q.set(a.id, k.values[a.id] ?? '');
      return `?${q.toString()}`;
    };
    const problems = [];
    const rows = [];
    // pictures that are the own photo of options with different colours
    const byImage = new Map();
    for (const k of d.skus)
      if (k.image !== null && k.image_of_option) {
        const c = k.values.color ?? k.values.other ?? JSON.stringify(k.values);
        if (!byImage.has(k.image)) byImage.set(k.image, new Set());
        byImage.get(k.image).add(c);
      }
    const sharedAcrossColours = [...byImage.entries()].filter(([, s]) => s.size > 1).map(([i, s]) => ({ image: i, options: [...s] }));
    for (const k of d.skus) {
      api.choose(k.key);
      await new Promise((r) => requestAnimationFrame(() => r()));
      const add = $('st-pd-add');
      const why = $('st-pd-why');
      const img = $('st-pd-img');
      const cap = txt($('st-pd-photo-cap'));
      const size = document.querySelector('[data-spec="מידות"]');
      const days = document.querySelector('[data-spec="זמן אספקה"]');
      const expectCredit = [d.material_he, k.size_he, k.price_he ?? 'המחיר עוד לא נקבע'].filter(Boolean).join(' · ');
      const expectWhy = d.status === 'unpriced' ? 'המחיר עוד לא נקבע' : !k.sellable ? 'המלאי אינו זמין כעת' : '';
      const im = k.image !== null ? d.images[k.image] : null;
      const row = {
        key: k.key,
        price_ok: (txt($('st-pd-price')) ?? '') === (k.price_he ?? ''),
        credit_ok: txt($('st-pd-credit')) === expectCredit,
        size_ok: !size || size.textContent.trim() === (k.size_he ? `${k.size_he} (לפי הספק)` : ''),
        days_ok: !days || (k.days ? days.textContent.includes(`${k.days[0]}–${k.days[1]}`) : days.textContent.trim() === ''),
        url_ok: location.search === keyQuery(k),
        image_ok: im ? !img.hidden && img.getAttribute('src') === im.src : img.hidden || (k.key === d.story_key && !!d.crop),
        caption: cap,
        caption_claims_option: !!cap && cap.includes('באפשרות'),
        caption_claim_ok: !(cap && cap.includes('באפשרות')) || (k.image_of_option && !!im && cap.includes(k.label_he ?? '@@')),
        button_ok: expectWhy ? add.hidden && !why.hidden && why.textContent.includes(expectWhy) : !add.hidden && why.hidden,
        never_disabled: !add.disabled && add.getAttribute('aria-disabled') !== 'true',
      };
      rows.push(row);
      for (const [f, v] of Object.entries(row)) if (f.endsWith('_ok') && v === false) problems.push(`${k.key}: ${f}`);
      if (!row.never_disabled) problems.push(`${k.key}: a disabled add button`);
    }
    api.choose(d.story_key);
    return {
      product: d.product,
      status: d.status,
      axes: d.axes.map((a) => `${a.id}:${a.values.length}`),
      skus: d.skus.length,
      images: d.images.length,
      story_key: d.story_key,
      own_photos: d.skus.filter((k) => k.image_of_option).length,
      story_photo_kind: d.skus.find((k) => k.key === d.story_key)?.image_of_option ? 'own' : d.skus.find((k) => k.key === d.story_key)?.image !== null ? 'listing main' : d.crop ? 'frame crop' : 'none',
      shared_photo_across_colours: sharedAcrossColours,
      closeups: d.skus.filter((k) => k.closeup).length,
      problems,
      rows_checked: rows.length,
    };
  });
  // the real controls: change the first axis by its control, then the address round-trip
  r.controls = null;
  const axes = await page.evaluate(() => JSON.parse(document.getElementById('st-data').textContent).detail.axes.map((a) => a.id));
  if (axes.length) {
    const before = await page.evaluate(() => ({ price: document.getElementById('st-pd-price').textContent, credit: document.getElementById('st-pd-credit').textContent, url: location.search, img: document.getElementById('st-pd-img').getAttribute('src'), key: window.__story.detail().current().key }));
    const ax = axes[0];
    const sel = page.locator(`select[data-axis="${ax}"]`);
    let how;
    if (await sel.count()) {
      const opts = await sel.locator('option:not([disabled])').evaluateAll((os) => os.map((o) => o.value));
      const cur = await sel.inputValue();
      const to = opts.find((v) => v !== cur);
      if (to) await sel.selectOption(to);
      how = `select ${ax} → ${to}`;
    } else {
      const radios = page.locator(`input[data-axis="${ax}"]:not([disabled])`);
      const n = await radios.count();
      let done = false;
      for (let i = 0; i < n && !done; i++) {
        const rd = radios.nth(i);
        if (!(await rd.isChecked())) {
          await rd.check({ force: true });
          how = `radio ${ax} → ${await rd.getAttribute('value')}`;
          done = true;
        }
      }
    }
    await page.waitForTimeout(150);
    const after = await page.evaluate(() => ({ price: document.getElementById('st-pd-price').textContent, credit: document.getElementById('st-pd-credit').textContent, url: location.search, img: document.getElementById('st-pd-img').getAttribute('src'), key: window.__story.detail().current().key, note: document.getElementById('st-pd-story-note')?.hidden === false }));
    // reload the address it wrote: the same option
    const url = page.url();
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__story?.detail?.(), undefined, { timeout: 15000 });
    const reloaded = await page.evaluate(() => window.__story.detail().current().key);
    r.controls = { how, before, after, sku_changed: before.key !== after.key, url_changed: before.url !== after.url, story_note_shown: after.note, reload_same_option: reloaded === after.key };
    if (!r.controls.sku_changed || !r.controls.url_changed || !r.controls.reload_same_option) r.problems.push(`controls: ${JSON.stringify(r.controls)}`);
  }
  r.path = path;
  results.push(r);
  await page.close();
}
await browser.close();
const summary = {
  pages: results.length,
  skus_checked: results.reduce((n, r) => n + r.rows_checked, 0),
  by_status: results.reduce((m, r) => ((m[r.status] = (m[r.status] ?? 0) + 1), m), {}),
  pages_with_problems: results.filter((r) => r.problems.length).map((r) => ({ path: r.path, problems: r.problems.slice(0, 6) })),
  shared_photo_across_colours: results.filter((r) => r.shared_photo_across_colours.length).map((r) => ({ path: r.path, shared: r.shared_photo_across_colours })),
  controls_tested: results.filter((r) => r.controls).length,
};
writeFileSync(OUT, JSON.stringify({ summary, results }, null, 1));
console.log(JSON.stringify(summary, null, 1));
