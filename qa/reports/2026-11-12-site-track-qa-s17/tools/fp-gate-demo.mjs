/**
 * qa-agent, S17 (2026-11-12), ת50: what the public gate says about OUR OWN next layers. Four of the warm-modern phase-2
 * layers (tracked at a988b099: a sconce and the bowl, each product and shadow) are encoded as the build encodes a house
 * layer (WebP, 1920 wide, transparent) and placed where the house's layers live (media/house/…/M0/slots/<slot>/1.*.1920.webp)
 * in a copy of the clean public dist; then `check:rights --dist=` (HD_PUBLIC=1). None of them is a supplier picture.
 *   QA_PUB=<public copy>/site QA_DATA=<out dir> QA_TMP=<scratch> node fp-gate-demo.mjs
 */
import { spawnSync } from 'node:child_process';
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
const PUB = process.env.QA_PUB;
const DATA = process.env.QA_DATA;
const TMP = process.env.QA_TMP;
const sharp = createRequire(join(PUB, 'package.json'))('sharp');
const L = '/home/user/homedesign-app/assets/renders/living-room/warm-modern/phase2-2026-11-10/layers';
const D = join(TMP, 'd-fp');
rmSync(D, { recursive: true, force: true });
cpSync(join(PUB, 'web/dist'), D, { recursive: true });
const put = [
  ['accent-sconces/accent-sconces-cj-travertine-block-updown-8x16-r5.png', 'accent-sconces/1.product.1920.webp'],
  ['accent-sconces/accent-sconces-cj-travertine-block-updown-8x16-r5-shadow.png', 'accent-sconces/1.shadow.1920.webp'],
  ['bowl/bowl-cj-matte-black-bowl-20.png', 'bowl/1.product.1920.webp'],
  ['bowl/bowl-cj-matte-black-bowl-20-shadow.png', 'bowl/1.shadow.1920.webp'],
];
for (const [src, dst] of put) {
  const out = join(D, 'media/house/living-room/warm-modern/M0/slots', dst);
  mkdirSync(join(out, '..'), { recursive: true });
  writeFileSync(out, await sharp(join(L, src)).resize(1920).webp({ quality: 82, alphaQuality: 90 }).toBuffer());
}
const json = join(DATA, 'rights-fp-layers.json');
const r = spawnSync('npx', ['--no-install', 'tsx', 'tools/check-image-rights.ts', `--dist=${D}`, `--json=${json}`], { cwd: PUB, env: { ...process.env, HD_PUBLIC: '1' }, encoding: 'utf8' });
const j = JSON.parse(readFileSync(json, 'utf8'));
console.log(`QA ת50 demo: 4 of our own phase-2 layers in a public dist → check:rights exit ${r.status}; found ${JSON.stringify(j.by_content.found)}`);
for (const f of j.findings) console.log(`  ${f.where}: ${f.what}`);
rmSync(D, { recursive: true, force: true });
