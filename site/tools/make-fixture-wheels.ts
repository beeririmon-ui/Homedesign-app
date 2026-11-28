/**
 * MOCK12 (2026-11-28, briefs/site-mock12-wheels-studio-2026-11-28.md): the fixture frame of two wheels. render-agent is
 * rendering the first real frames with several wheels (plan wm-wheels 7.2), and no product is faked into the build, so
 * the fixture is a small render folder made here of numbered swatches, said to be a demo ("הדגמה טכנית"), never a
 * product and never a price. It is built by tools/make-tour-room.ts like any frame:
 *  - wheel A: three options from the manifest's `default: false` layers (the MOCK4–11 way);
 *  - wheel B: three options from a wheel manifest next to it (`wheel_manifest`, the M0-W `<key>.wheel` format that
 *    render-agent writes): the one line a room's new wheels take;
 *  - a picture half hidden by a box in front of it: the room cuts its card, so outside the room it is named (FB29).
 * The page opens it only with `?skip=1&fixture=wheels2` in a build that is not the Artifact (tour/fixture-wheels2.ts),
 * and the Artifact never ships its files (tools/finalize-artifact.ts copies the frames of tools/tour/frames.json).
 *
 *   .generated/fixtures/wheels2/                         the folder and its config (never the render folders)
 *   .generated/tour.fixture-wheels2.warm-modern.json     web/public/media/tour/fixture-wheels2/warm-modern/
 */
import sharp from 'sharp';
import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { GENERATED, sitePath } from './lib/paths';

// the tour's own canvas (2720 × 1530): the engine composes every frame at the width it chose for the first (1920 or 2720)
const W = 2720;
const H = 1530;
/** the shapes are laid out on 1280 × 720 and scaled to the canvas */
const K = W / 1280;
const DIR = join(GENERATED, 'fixtures/wheels2');
const FOLDER = join(DIR, 'folder');
mkdirSync(join(FOLDER, 'layers'), { recursive: true });

type RGB = [number, number, number];
type Shape = { kind: 'rect' | 'disc'; x: number; y: number; w: number; h: number; rgb: RGB };
const at = (kind: Shape['kind'], x: number, y: number, w: number, h: number, rgb: RGB): Shape => ({
  kind,
  x: Math.round(x * K),
  y: Math.round(y * K),
  w: Math.round(w * K),
  h: Math.round(h * K),
  rgb,
});
const inside = (s: Shape, x: number, y: number): boolean => {
  if (s.kind === 'rect') return x >= s.x && x < s.x + s.w && y >= s.y && y < s.y + s.h;
  const rx = s.w / 2;
  const ry = s.h / 2;
  return ((x + 0.5 - s.x - rx) / rx) ** 2 + ((y + 0.5 - s.y - ry) / ry) ** 2 <= 1;
};
/** a layer: the shape, opaque, nothing round it (straight alpha, no matte) */
async function layer(file: string, s: Shape): Promise<void> {
  const buf = Buffer.alloc(W * H * 4);
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++)
      if (inside(s, x, y)) {
        const i = (y * W + x) * 4;
        buf.set(s.rgb, i);
        buf[i + 3] = 255;
      }
  await sharp(buf, { raw: { width: W, height: H, channels: 4 } })
    .png()
    .toFile(join(FOLDER, file));
}
/** a shadow (multiply): white, and a soft band under a shape that stands on something */
function shadowOf(s: Shape | null): Uint8Array {
  const sh = new Uint8Array(W * H).fill(255);
  if (!s) return sh;
  const y0 = s.y + s.h;
  for (let y = y0 - 6; y < Math.min(H, y0 + 18); y++)
    for (let x = s.x - 10; x < s.x + s.w + 10; x++) if (x >= 0 && x < W && y >= 0) sh[y * W + x] = 190 + Math.min(60, Math.abs(y - y0) * 3);
  return sh;
}
const savePng = (file: string, data: Uint8Array, ch: 1 | 3) =>
  sharp(Buffer.from(data), { raw: { width: W, height: H, channels: ch } })
    .png()
    .toFile(join(FOLDER, file));

// the plate: a wall and a floor of the house's tones
const plate = new Uint8Array(W * H * 3);
for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) plate.set(y < H * 0.62 ? [214, 203, 189] : [168, 140, 112], (y * W + x) * 3);
await savePng('plate.png', plate, 3);

const A = (rgb: RGB): Shape => at('rect', 250, 360, 220, 150, rgb);
const B = (rgb: RGB): Shape => at('disc', 920, 300, 170, 210, rgb);
const C: Shape = at('rect', 520, 120, 240, 180, [120, 132, 118]);
const D: Shape = at('rect', 600, 230, 260, 260, [92, 74, 60]);
const aTones: RGB[] = [
  [196, 127, 90],
  [127, 143, 106],
  [216, 200, 174],
];
const bTones: RGB[] = [
  [61, 58, 54],
  [232, 226, 214],
  [139, 111, 85],
];
for (const [i, t] of aTones.entries()) await layer(`layers/a-${i + 1}.png`, A(t));
for (const [i, t] of bTones.entries()) await layer(`layers/b-${i + 1}.png`, B(t));
await layer('layers/c.png', C);
await layer('layers/d.png', D);
await savePng('shadow-none.png', shadowOf(null), 1);
await savePng('shadow-a.png', shadowOf(A(aTones[0]!)), 1);
await savePng('shadow-b.png', shadowOf(B(bTones[0]!)), 1);
await savePng('shadow-d.png', shadowOf(D), 1);

// the folder's composite: the plate, then each default layer in z order — its shadow (multiply), then the layer — as
// the render tools compose it (numpy's rint: half to even)
const rint = (x: number) => {
  const f = Math.floor(x);
  const d = x - f;
  return d > 0.5 ? f + 1 : d < 0.5 ? f : f % 2 === 0 ? f : f + 1;
};
const truth = new Uint8Array(plate);
const stack: [Shape, Uint8Array][] = [
  [C, shadowOf(null)],
  [A(aTones[0]!), shadowOf(A(aTones[0]!))],
  [D, shadowOf(D)],
  [B(bTones[0]!), shadowOf(B(bTones[0]!))],
];
for (const [s, sh] of stack)
  for (let y = 0; y < H; y++)
    for (let x = 0; x < W; x++) {
      const i = y * W + x;
      for (let k = 0; k < 3; k++) truth[i * 3 + k] = inside(s, x, y) ? s.rgb[k]! : rint((truth[i * 3 + k]! * sh[i]!) / 255);
    }
await savePng('truth.png', truth, 3);

const L = (slot: string, product: string, z: number, file: string, shadow: string, def = true) => ({
  slot,
  product,
  z,
  layer: `layers/${file}`,
  shadow,
  ...(def ? {} : { default: false }),
});
writeFileSync(
  join(FOLDER, 'manifest.json'),
  JSON.stringify(
    {
      id: 'fixture-wheels2-2026-11-28',
      note: 'MOCK12: a demo of two wheels in one frame (numbered swatches, never a product). Made by site/tools/make-fixture-wheels.ts.',
      canvas: [W, H],
      frame_box: [0, 0, W, H],
      compose: 'plate.png; per layer in z order: shadow (multiply), then the layer (straight alpha)',
      layers: [
        L('fx-picture', 'fx-picture', 10, 'c.png', 'shadow-none.png'),
        L('fx-square', 'fx-square-1', 20, 'a-1.png', 'shadow-a.png'),
        L('fx-square', 'fx-square-2', 20, 'a-2.png', 'shadow-a.png', false),
        L('fx-square', 'fx-square-3', 20, 'a-3.png', 'shadow-a.png', false),
        L('fx-box', 'fx-box', 30, 'd.png', 'shadow-d.png'),
        L('fx-disc', 'fx-disc-1', 40, 'b-1.png', 'shadow-b.png'),
      ],
      light: [],
    },
    null,
    1,
  ),
);
// wheel B in the M0-W wheel format, in a manifest of its own next to the room's (as render-agent writes them)
const set = (k: number) => ({
  layer: `layers/b-${k}.png`,
  shadow: 'shadow-b.png',
  products: [{ card_id: `fx-disc-${k}` }],
  ...(k === 1 ? { default: true } : {}),
});
writeFileSync(
  join(FOLDER, 'manifest-wheel-fixture.json'),
  JSON.stringify(
    {
      id: 'fixture-wheels2-wheel-b',
      'fx-disc': {
        wheel: {
          slot: 'fx-disc',
          default: 'fx-disc-1',
          order: ['fx-disc-1', 'fx-disc-2', 'fx-disc-3'],
          sets: { 'fx-disc-1': set(1), 'fx-disc-2': set(2), 'fx-disc-3': set(3) },
        },
      },
    },
    null,
    1,
  ),
);
const names: Record<string, string> = {};
for (const k of [1, 2, 3]) {
  names[`fx-square-${k}`] = `דוגמה א${k} (לא מוצר)`;
  names[`fx-disc-${k}`] = `דוגמה ב${k} (לא מוצר)`;
}
names['fx-picture'] = 'דוגמה: תמונה מוסתרת (לא מוצר)';
names['fx-box'] = 'דוגמה: קופסה (לא מוצר)';
const cfg = join(DIR, 'fixture-wheels2.warm-modern.json');
writeFileSync(
  cfg,
  JSON.stringify(
    {
      note: 'MOCK12: the fixture frame of two wheels (tools/make-fixture-wheels.ts). A demo, behind HD_PUBLIC=0 and never in the Artifact.',
      room: 'fixture-wheels2',
      group: 'work',
      frame_he: 'הדגמה טכנית: שני גלגלים',
      style: 'warm-modern',
      name_he: 'הדגמה',
      layers: FOLDER,
      manifest: 'manifest.json',
      wheel_manifest: 'manifest-wheel-fixture.json',
      truth: 'truth.png',
      plan: 'docs/house-plan.json',
      camera: 'W0',
      room_plan: 'work',
      slots_file: 'data/slots/work.json',
      sample: null,
      prints: [],
      zoom: false,
      styles: false,
      option_names_he: names,
      slots: {
        'fx-picture': { card: null, kind: 'wall', name_he: 'הדגמה: תמונה', depth_m: 3.6 },
        'fx-square': { card: null, kind: 'surface', name_he: 'הדגמה: גלגל א', depth_m: 3.0 },
        'fx-box': { card: null, kind: 'floor', name_he: 'הדגמה: קופסה', depth_m: 2.8 },
        'fx-disc': { card: null, kind: 'surface', name_he: 'הדגמה: גלגל ב', depth_m: 2.6 },
      },
    },
    null,
    1,
  ),
);
// `--no-build`: the folder and its config only (the tool's own test builds it elsewhere: tools/test/mock12-wheels.test.ts)
if (!process.argv.includes('--no-build'))
  execFileSync(sitePath('node_modules/.bin/tsx'), [sitePath('tools/make-tour-room.ts'), cfg], { cwd: sitePath(), stdio: 'inherit' });
