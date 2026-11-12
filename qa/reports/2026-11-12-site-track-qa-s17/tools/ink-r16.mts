/** qa-agent S17: the ink (mean of 255 − grey on the gate's 32×32 image) of R16's thumbnail and of the picture it matched,
 *  to check that the proposed ink guard (ת50) keeps R16. tsx ink-r16.mts <public copy site> */
import { join } from 'node:path';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { fingerprint } from '../build-s17/site/tools/lib/rights-content';
const SITE = process.argv[2]!;
const sharp = createRequire(join(SITE, 'package.json'))('sharp') as typeof import('sharp');
const ink = (g: Buffer) => g.reduce((s, v) => s + 255 - v, 0) / 1024;
const orig = readFileSync(join(SITE, '.cache/supplier-images/5e613c763c880d953d3f76da.bin'));
const thumb = await sharp(orig, { failOn: 'none' }).rotate().resize(96).webp({ quality: 60 }).toBuffer();
const photo = readFileSync(join(SITE, 'web/public/media/products/accent-sconces-indoor-stone-wall-lamp-eavr7/photo.800.webp'));
const [a, b] = [await fingerprint(thumb), await fingerprint(photo)];
console.log(`QA R16 ink: thumbnail ${ink(a!.grey).toFixed(1)}, the matched photo ${ink(b!.grey).toFixed(1)} (the guard needs ≥ 4 on both)`);
