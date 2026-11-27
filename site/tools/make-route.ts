/**
 * MOCK9 (2026-11-27, briefs/site-mock9-route-ui-2026-11-27.md; FB21): the guided route's legs, behind HD_PUBLIC=0.
 * Reads tools/tour/route.json: the stations in the owner's order, and a line per leg — the folder of a real leg's frames
 * (motion-agent's, with a manifest that marks the ease frames) or null (the leg walks in code until its clip exists).
 * Each real leg is encoded as tools/make-arrival.ts encodes the arrival, so the page plays it the same way (a video over
 * the canvas, its rate driven by the scroll or held by "הלאה"):
 *
 *   web/public/media/tour/route/<leg>.1920.60.mp4   the wide screen's, H.264 High, two-pass, ≤ 6 MB
 *   web/public/media/tour/route/<leg>.1080.30.mp4   the phone's, from the folder's own 30 fps frames, ≤ 2.5 MB
 *   web/public/media/tour/route/<leg>.<w>.poster.webp  each file's first frame, the video's poster (MOCK10, FB26: a
 *                                                    web view draws a play icon on a video without one)
 *   .generated/route.json                            the stations and the legs as the page reads them (tour/route.ts)
 *
 * The files are encoded once per change of a leg's frames, the config or this file (a stamp beside them). ffmpeg is a
 * tool of this machine, not of the site: a machine without it keeps the files it has.
 */
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const fail = (msg: string): never => {
  throw new Error(`make-route: ${msg}`);
};
type Cfg = { order: string[]; legs: Record<string, string | null> };
type Variant = { w: number; h: number; fps: number; frames: number };
type Manifest = {
  id: string;
  qa?: string;
  chain: { ease_in_frames: Record<string, [number, number]>; ease_out_frames: Record<string, [number, number]> };
  variants: Record<string, Variant>;
};
const cfg = read<Cfg>(sitePath('tools/tour/route.json'));
const ROOMS = ['living-room', 'dining', 'bath', 'master', 'boy', 'girl', 'work'];
if (cfg.order.length !== new Set(cfg.order).size || cfg.order.some((g) => !ROOMS.includes(g))) fail(`order ${cfg.order.join(', ')}: each room once`);
const pairs = cfg.order.slice(1).map((to, i) => `${cfg.order[i]}>${to}`);
for (const k of Object.keys(cfg.legs)) if (!pairs.includes(k)) fail(`leg "${k}" is not a step of the route`);

const REL = 'tour/route';
const OUT = join(MEDIA_OUT, REL);
const LIMIT = { desktop: 6 * 1024 * 1024, phone: 2.5 * 1024 * 1024 } as const;
const want = {
  desktop: { key: '1920', w: 1920, h: 1080, fps: 60, kbps: 5000, max: 7500, level: '4.2' },
  phone: { key: '1080', w: 1080, h: 608, fps: 30, kbps: 1900, max: 2800, level: '4.0' },
} as const;
const ffmpeg = (args: string[]) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...args], { stdio: ['ignore', 'ignore', 'inherit'] });
const hasFfmpeg = (() => {
  try {
    execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
})();

type LegVideo = {
  src: string;
  poster: string;
  w: number;
  h: number;
  fps: number;
  frames: number;
  bytes: number;
  ease_in: [number, number];
  ease_out: [number, number];
};
const legs = pairs.map((pair, i) => {
  const [from, to] = pair.split('>') as [string, string];
  const id = `leg${i + 1}`;
  const dir = cfg.legs[pair] ?? null;
  if (!dir) return { id, from, to, real: null, qa: null };
  const abs = repoPath(dir);
  const fm = read<Manifest>(join(abs, 'manifest.json'));
  const files = { desktop: join(OUT, `${id}.1920.60.mp4`), phone: join(OUT, `${id}.1080.30.mp4`) };
  const real = {} as Record<'desktop' | 'phone', LegVideo>;
  const src: string[] = [join(abs, 'manifest.json')];
  for (const k of ['desktop', 'phone'] as const) {
    const w = want[k];
    const v = fm.variants[w.key] ?? fail(`${dir} has no variant ${w.key}`);
    if (v.w !== w.w || v.h !== w.h || v.fps !== w.fps) fail(`${dir} ${w.key} is ${v.w}×${v.h}@${v.fps}, not ${w.w}×${w.h}@${w.fps}`);
    const ein = fm.chain.ease_in_frames[w.key] ?? fail(`${dir}: no ease-in frames for ${w.key}`);
    const eout = fm.chain.ease_out_frames[w.key] ?? fail(`${dir}: no ease-out frames for ${w.key}`);
    if (!(ein[0] === 1 && ein[1] < eout[0] && eout[1] === v.frames)) fail(`${dir} ${w.key}: the ease frames ${ein} / ${eout} do not frame ${v.frames}`);
    src.push(join(abs, w.key, `${String(v.frames).padStart(4, '0')}.webp`));
    real[k] = {
      src: `${REL}/${id}.${w.key}.${w.fps}.mp4`,
      poster: `${REL}/${id}.${w.key}.poster.webp`,
      w: v.w,
      h: v.h,
      fps: v.fps,
      frames: v.frames,
      bytes: 0,
      ease_in: ein,
      ease_out: eout,
    };
  }
  const stamp = createHash('sha256')
    .update(JSON.stringify({ tool: readFileSync(new URL(import.meta.url), 'utf8'), dir, src: src.map((f) => [f, statSync(f).size, statSync(f).mtimeMs]) }))
    .digest('hex')
    .slice(0, 16);
  const STAMP = join(OUT, `${id}.stamp.json`);
  const have = () => existsSync(files.desktop) && existsSync(files.phone);
  const fresh = existsSync(STAMP) && read<{ stamp: string }>(STAMP).stamp === stamp && have();
  if (!fresh) {
    if (!hasFfmpeg) {
      if (!have()) fail(`ffmpeg is not on this machine and ${id}'s files are missing`);
      console.warn(`make-route: ffmpeg is missing; ${id}'s files already here are kept as they are`);
    } else {
      mkdirSync(OUT, { recursive: true });
      const tmp = join(tmpdir(), `hd-route-${process.pid}-${id}`);
      mkdirSync(tmp, { recursive: true });
      for (const k of ['desktop', 'phone'] as const) {
        const w = want[k];
        const input = ['-framerate', String(w.fps), '-start_number', '1', '-i', join(abs, w.key, '%04d.webp'), '-frames:v', String(real[k].frames)];
        // two-pass H.264 High, yuv420p, faststart, no audio; a keyframe every half second (the rate changes often)
        const common = [...input, '-an', '-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high'];
        const rate = [
          '-level:v',
          w.level,
          '-pix_fmt',
          'yuv420p',
          '-b:v',
          `${w.kbps}k`,
          '-maxrate',
          `${w.max}k`,
          '-bufsize',
          `${Math.round(w.max * 1.4)}k`,
          '-g',
          String(w.fps / 2),
        ];
        const log = join(tmp, `pass-${w.fps}`);
        ffmpeg([...common, ...rate, '-pass', '1', '-passlogfile', log, '-f', 'mp4', '/dev/null']);
        ffmpeg([...common, ...rate, '-pass', '2', '-passlogfile', log, '-movflags', '+faststart', files[k]]);
      }
      rmSync(tmp, { recursive: true, force: true });
      writeFileSync(STAMP, JSON.stringify({ stamp }));
    }
  }
  // the poster: the folder's own first frame, as it is (a WebP of the file's size)
  for (const k of ['desktop', 'phone'] as const) {
    mkdirSync(OUT, { recursive: true });
    copyFileSync(join(abs, want[k].key, '0001.webp'), join(MEDIA_OUT, real[k].poster));
  }
  for (const k of ['desktop', 'phone'] as const) {
    const size = statSync(files[k]).size;
    if (size > LIMIT[k]) fail(`${id}'s ${k} file is ${(size / 1048576).toFixed(2)} MB, over ${LIMIT[k] / 1048576} MB`);
    real[k].bytes = size;
  }
  return { id, from, to, real, qa: fm.qa ?? null };
});

mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'route.json'), JSON.stringify({ order: cfg.order, legs }));
const mb = (n: number) => `${(n / 1048576).toFixed(2)} MB`;
console.log(
  `route: ${cfg.order.length} stations; ` +
    legs.map((l) => (l.real ? `${l.id} ${l.from}→${l.to} ${mb(l.real.desktop.bytes)} / ${mb(l.real.phone.bytes)}` : `${l.id} in code`)).join('; ') +
    ' → .generated/route.json',
);
