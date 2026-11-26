/**
 * MOCK4 (2026-11-18): the arrival for the tour, behind HD_PUBLIC=0. MOCK7 (2026-11-26) stopped the walk in the hall and
 * walked on into the living room in code (web/src/tour/gl.ts PUSH).
 *
 * MOCK8 (2026-11-26, briefs/site-mock8-integrate-2026-11-26.md): FB19's arrival, one first-person walk from the door,
 * played by gentle scroll impulses (web/src/tour/walk.ts). The walk is the one tools/tour/arrival.json names (`walk`):
 *
 *   ka2   the part that is final: K-A2 (motion-agent, approved), the door D0 to the hall HT2 fb16, retimed to 60 fps with
 *         both ends locked onto those stills (tools/transitions/walk_ka2.py, cached in .generated/arrival-walk/); from
 *         its last frame (HT2 itself, `end.kind` "still") the tour walks on into the living room in code, as MOCK7 did
 *   fb19  motion-agent's whole walk (its folder's frames), D0 to M0-W fix1: its last frame is the living room's own
 *         frame (`end.kind` "room"), and the room takes over there
 *
 * Swapping in the final sequence is that one line of arrival.json. Writes:
 *
 *   web/public/media/tour/arrival/arrival.1920.60.mp4   the wide screen's walk, H.264 High, two-pass, ≤ 8 MB
 *   web/public/media/tour/arrival/arrival.1080.30.mp4   the phone's, ≤ 3 MB
 *   web/public/media/tour/arrival/d0.<w>.webp           the door, the walk's first frame (the page's first paint)
 *   web/public/media/tour/arrival/end.1920.webp         ka2: the walk's last frame, the still the push starts from
 *   web/public/media/tour/arrival/hall.1920.webp        the hall with the new living room through the opening (HDx2
 *                                                       fb19): the stop of the short fade under reduced motion
 *   .generated/arrival.json                             the walk as the page reads it
 *
 * The labels on the doors at the rest on HC (MOCK4, ARR-M1) went with that rest: FB19 has no stop and no look to the
 * left at the junction. The page still draws labels when a walk has them (none here).
 *
 * The web files are encoded once per change of the sources, the config or this file (a stamp beside them). ffmpeg
 * and python3.12 are tools of this machine, not of the site: a machine without them keeps the files it has.
 */
import sharp from 'sharp';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { GENERATED, MEDIA_OUT, repoPath, sitePath } from './lib/paths';

type Source =
  | { kind: 'clip'; clip: string; tool: string; first: string; last: string }
  | { kind: 'frames'; dir: string; variant: string };
type End = { kind: 'still'; still: string; camera: string } | { kind: 'room' };
type Cfg = { walk: string; walks: Record<string, { source: Source; end: End }>; impulse: number; snap: number; hall: string };
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const fail = (msg: string): never => {
  throw new Error(`make-arrival: ${msg}`);
};
const CFG_FILE = sitePath('tools/tour/arrival.json');
const cfg = read<Cfg>(CFG_FILE);
const W = cfg.walks[cfg.walk] ?? fail(`no walk "${cfg.walk}" in tools/tour/arrival.json`);
if (!(cfg.impulse > 0.15 && cfg.impulse < 0.7)) fail(`impulse ${cfg.impulse}: one impulse must play a stretch, and 2–3 reach the room`);

const REL = 'tour/arrival';
const OUT = join(MEDIA_OUT, REL);
/** the brief's limits: the desktop ≤ 8 MB at 60 fps, the phone ≤ 3 MB, every file under the Artifact's 15 MB */
const LIMIT = { desktop: 8 * 1024 * 1024, phone: 3 * 1024 * 1024 } as const;
const FPS = 60;
const WALK_DIR = join(GENERATED, 'arrival-walk');

// ---------- the source: the master of a clip (made here), or a folder's frames ----------
const srcFiles = W.source.kind === 'clip' ? [W.source.clip, W.source.first, W.source.last].map((f) => repoPath(f)) : [];
let frames = 0;
let input: string[];
/** the phone's walk: the folder's own 30 fps frames where it has them (its last frame is the still too), else every
 *  other frame of the 60 fps walk */
let phoneInput: string[] | null = null;
let phoneFramesOwn = 0;
if (W.source.kind === 'frames') {
  const dir = repoPath(W.source.dir);
  type FM = { path: string; variants: Record<string, { w: number; h: number; fps: number; frames: number }> };
  const fm = read<FM>(join(dir, 'manifest.json'));
  const v = fm.variants[W.source.variant] ?? fail(`${W.source.dir} has no variant ${W.source.variant}`);
  if (v.w !== 1920 || v.h !== 1080 || v.fps !== FPS) fail(`${W.source.dir} ${W.source.variant} is ${v.w}×${v.h}@${v.fps}, not 1920×1080@60`);
  frames = v.frames;
  srcFiles.push(join(dir, 'manifest.json'), join(dir, W.source.variant, `${String(frames).padStart(4, '0')}.webp`));
  input = ['-framerate', String(FPS), '-start_number', '1', '-i', join(dir, W.source.variant, '%04d.webp')];
  const p = fm.variants['1080'];
  if (p && p.w === 1080 && p.h === 608 && p.fps === 30) {
    phoneFramesOwn = p.frames;
    srcFiles.push(join(dir, '1080', `${String(p.frames).padStart(4, '0')}.webp`));
    phoneInput = ['-framerate', '30', '-start_number', '1', '-i', join(dir, '1080', '%04d.webp'), '-frames:v', String(p.frames)];
  }
} else {
  const master = join(WALK_DIR, `${cfg.walk}.master.mp4`);
  const rec = join(WALK_DIR, `${cfg.walk}.json`);
  const tool = sitePath(W.source.tool);
  const mstamp = createHash('sha256')
    .update(JSON.stringify({ tool: readFileSync(tool, 'utf8'), src: srcFiles.map((f) => [f, statSync(f).size]) }))
    .digest('hex')
    .slice(0, 16);
  const mstampFile = join(WALK_DIR, `${cfg.walk}.stamp`);
  if (!(existsSync(master) && existsSync(rec) && existsSync(mstampFile) && readFileSync(mstampFile, 'utf8') === mstamp)) {
    mkdirSync(WALK_DIR, { recursive: true });
    console.log(`make-arrival: the walk ${cfg.walk} is made from its clip (${W.source.tool}, about a minute)`);
    execFileSync('python3.12', ['-I', tool, ...srcFiles, master, rec], { stdio: ['ignore', 'inherit', 'inherit'] });
    writeFileSync(mstampFile, mstamp);
  }
  frames = read<{ out_frames: number }>(rec).out_frames;
  input = ['-i', master];
  srcFiles.push(master);
}
const phoneFrames = phoneFramesOwn || Math.floor((frames - 1) / 2) + 1;

const stamp = createHash('sha256')
  .update(
    JSON.stringify({
      tool: readFileSync(new URL(import.meta.url), 'utf8'),
      cfg,
      src: [...srcFiles, repoPath(cfg.hall), ...(W.end.kind === 'still' ? [repoPath(W.end.still)] : [])].map((f) => [f, statSync(f).size, statSync(f).mtimeMs]),
    }),
  )
  .digest('hex')
  .slice(0, 16);
const STAMP = join(OUT, 'stamp.json');
const files = {
  desktop: join(OUT, 'arrival.1920.60.mp4'),
  phone: join(OUT, 'arrival.1080.30.mp4'),
  d0: [1080, 1920].map((w) => join(OUT, `d0.${w}.webp`)),
  hall: join(OUT, 'hall.1920.webp'),
  end: join(OUT, 'end.1920.webp'),
};
const have = () =>
  existsSync(files.desktop) && existsSync(files.phone) && files.d0.every(existsSync) && existsSync(files.hall) && (W.end.kind !== 'still' || existsSync(files.end));
const ffmpeg = (args: string[]) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...args], { stdio: ['ignore', 'ignore', 'inherit'] });
const hasFfmpeg = (() => {
  try {
    execFileSync('ffmpeg', ['-version'], { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
})();

const fresh = existsSync(STAMP) && read<{ stamp: string }>(STAMP).stamp === stamp && have();
if (!fresh) {
  if (!hasFfmpeg) {
    if (!have()) fail('ffmpeg is not on this machine and the encoded files are missing');
    console.warn('make-arrival: ffmpeg is missing; the encoded files already here are kept as they are');
  } else {
    rmSync(OUT, { recursive: true, force: true });
    mkdirSync(OUT, { recursive: true });
    const tmp = join(tmpdir(), `hd-arrival-${process.pid}`);
    mkdirSync(tmp, { recursive: true });
    // two-pass H.264 High, yuv420p, faststart, no audio; a keyframe every half second (the walk's rate changes often)
    const encode = (vf: string[], fps: number, kbps: number, max: number, level: string, out: string, from = input) => {
      const common = [...from, ...vf, '-an', '-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high'];
      const rate = ['-level:v', level, '-pix_fmt', 'yuv420p', '-b:v', `${kbps}k`, '-maxrate', `${max}k`, '-bufsize', `${Math.round(max * 1.4)}k`, '-g', String(fps / 2)];
      const log = join(tmp, `pass-${fps}`);
      ffmpeg([...common, ...rate, '-pass', '1', '-passlogfile', log, '-f', 'mp4', '/dev/null']);
      ffmpeg([...common, ...rate, '-pass', '2', '-passlogfile', log, '-movflags', '+faststart', out]);
    };
    encode(['-frames:v', String(frames)], 60, 5000, 7500, '4.2', files.desktop);
    // the phone's: every other frame (the first and, the count being odd, the last are the stills), 1080 × 608
    if (phoneInput) encode([], 30, 1900, 2800, '4.0', files.phone, phoneInput);
    else encode(['-vf', 'fps=30:round=near,scale=1080:608:flags=lanczos'], 30, 1900, 2800, '4.0', files.phone);
    const first = join(tmp, 'f1.png');
    ffmpeg([...input, '-frames:v', '1', first]);
    for (const [i, w] of [1080, 1920].entries()) await sharp(first).resize({ width: w }).webp({ quality: 80, effort: 6 }).toFile(files.d0[i]!);
    await sharp(repoPath(cfg.hall)).removeAlpha().resize({ width: 1920 }).webp({ quality: 85, effort: 6 }).toFile(files.hall);
    if (W.end.kind === 'still') await sharp(repoPath(W.end.still)).removeAlpha().resize({ width: 1920 }).webp({ quality: 92, effort: 6 }).toFile(files.end);
    rmSync(tmp, { recursive: true, force: true });
    writeFileSync(STAMP, JSON.stringify({ stamp }));
  }
}
for (const k of ['desktop', 'phone'] as const) {
  const size = statSync(files[k]).size;
  if (size > LIMIT[k]) fail(`the ${k} walk is ${(size / 1048576).toFixed(2)} MB, over ${LIMIT[k] / 1048576} MB`);
}

// ---------- the still's camera (ka2): the push into the living room is aimed through it ----------
type Cam = { loc: [number, number, number]; yaw_deg_left: number; u0: number; v0: number };
const plan = read<{ style_shells_1_3_1: Record<string, Record<string, { cameras?: Record<string, Cam> }>> }>(repoPath('docs/house-plan.json'));
const endCam = (() => {
  if (W.end.kind !== 'still') return null;
  const c = plan.style_shells_1_3_1['warm-modern']?.entrance?.cameras?.[W.end.camera] ?? fail(`no camera ${W.end.camera} in the warm-modern entrance`);
  const r5 = (x: number) => +x.toFixed(5);
  return [r5(c.loc[0]), r5(c.loc[1]), r5(c.loc[2]), r5(c.yaw_deg_left), r5(c.u0), r5(c.v0)] as [number, number, number, number, number, number];
})();

const data = {
  id: `T-D0 arrival FB19 (${cfg.walk})`,
  walk: cfg.walk,
  qa: 'K-A2 approved by the coordinator (2026-11-26); the walk is a preview behind HD_PUBLIC=0',
  /** the walk's end: "still" (its last frame is a still the tour walks on from, in code) or "room" (the room's own frame) */
  end: W.end.kind,
  frames,
  land_s: +((frames - 1) / FPS).toFixed(4),
  land_60: frames,
  /** the share of the walk one scroll impulse plays, and the rest (in impulses) a last impulse walks through */
  impulse: cfg.impulse,
  snap: cfg.snap,
  videos: {
    desktop: { src: `${REL}/arrival.1920.60.mp4`, w: 1920, h: 1080, fps: 60, frames, bytes: statSync(files.desktop).size },
    phone: { src: `${REL}/arrival.1080.30.mp4`, w: 1080, h: 608, fps: 30, frames: phoneFrames, bytes: statSync(files.phone).size },
  },
  door: { src: `${REL}/d0`, widths: [1080, 1920] },
  /** reduced motion's stop (HDx2 fb19, the hall with the new living room through the opening); MOCK4 named it `hc` */
  hc: { src: `${REL}/hall`, width: 1920 },
  still: W.end.kind === 'still' ? { src: `${REL}/end`, width: 1920 } : null,
  /** the walk's last frame and its camera [x, y, z, yaw, u0, v0] (ka2: HT): the push into the living room starts there */
  land: { frame: frames, cam: endCam ?? [0, 0, 0, 0, 0.5, 0.5] },
  // MOCK4's labels at the rest on HC: FB19 has no rest, no labels
  hc_60: 0,
  rest_60: [0, 0] as [number, number],
  proj: { kx: 0.6667, ky: 1.1852 },
  labels: [],
  cams: { from: 0, f: [] },
};
mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'arrival.json'), JSON.stringify(data));
const mb = (n: number) => `${(n / 1048576).toFixed(2)} MB`;
console.log(
  `arrival (${cfg.walk}, ends on ${W.end.kind === 'still' ? `a still at ${W.end.camera}, the push walks on` : 'the room'}): ` +
    `desktop ${mb(data.videos.desktop.bytes)} (${frames} frames @60), phone ${mb(data.videos.phone.bytes)} (${phoneFrames} @30), ` +
    `the door ${files.d0.map((f) => `${(statSync(f).size / 1024).toFixed(0)} KB`).join(' / ')}, the hall ${(statSync(files.hall).size / 1024).toFixed(0)} KB` +
    `${fresh ? ' (cached)' : ''} → .generated/arrival.json`,
);
