/**
 * Lighthouse gates on mobile (default Lighthouse mobile emulation and throttling): accessibility = 100,
 * performance ≥ 90. Runs against a running local build (`npm run preview`, or HD_BASE_URL).
 *   npm run lighthouse
 * Reports go to site/.lighthouse/ (gitignored).
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import lighthouse from 'lighthouse';
import * as chromeLauncher from 'chrome-launcher';
import { sitePath } from './lib/paths';

const BASE = process.env.HD_BASE_URL ?? 'http://127.0.0.1:8788';
const chromePath = process.env.PW_CHROMIUM ?? '/opt/pw-browsers/chromium';
const catalog = JSON.parse(readFileSync(sitePath('.generated/catalog.public.json'), 'utf8')) as { products: { id: string }[] };
const pages = ['/', '/rooms/living-room/', `/p/${catalog.products[0]!.id}/`, '/checkout/'];
const OUT = sitePath('.lighthouse');
mkdirSync(OUT, { recursive: true });

const chrome = await chromeLauncher.launch({
  chromePath,
  chromeFlags: ['--headless=new', '--no-sandbox', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
let failed = false;
try {
  for (const p of pages) {
    const res = await lighthouse(`${BASE}${p}`, {
      port: chrome.port,
      output: 'html',
      onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'],
      logLevel: 'error',
    });
    if (!res) throw new Error(`no result for ${p}`);
    const c = res.lhr.categories;
    const score = (k: string) => Math.round((c[k]?.score ?? 0) * 100);
    const a11y = score('accessibility');
    const perf = score('performance');
    const ok = a11y === 100 && perf >= 90;
    failed ||= !ok;
    const m = res.lhr.audits;
    console.log(
      `${ok ? 'ok  ' : 'FAIL'}  ${p.padEnd(48)} perf ${perf}  a11y ${a11y}  bp ${score('best-practices')}  seo ${score('seo')}  ` +
        `LCP ${m['largest-contentful-paint']?.displayValue ?? '?'}  TBT ${m['total-blocking-time']?.displayValue ?? '?'}  CLS ${m['cumulative-layout-shift']?.displayValue ?? '?'}`,
    );
    writeFileSync(`${OUT}/${p.replace(/\W+/g, '_') || 'home'}.html`, res.report as string);
  }
} finally {
  chrome.kill();
}
if (failed) process.exit(1);
