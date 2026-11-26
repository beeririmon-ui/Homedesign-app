/**
 * MOCK4 (2026-11-18): the arrival v2 for the tour (briefs/site-mock4-house-tour-2026-11-18.md), behind HD_PUBLIC=0. It
 * reads the QA-passed clean masters of motion-agent (assets/video/transitions/warm-modern/arrival-v2/, never changed
 * here) and writes:
 *
 *   web/public/media/tour/arrival/arrival.1920.60.mp4   the desktop walk, from the door to the landing on M0 (frames
 *                                                       1–702 of the 60 fps master), H.264 High, two-pass, ≤ 8 MB
 *   web/public/media/tour/arrival/arrival.1080.30.mp4   the phone's (frames 1–352 of the 30 fps master), ≤ 3 MB
 *   web/public/media/tour/arrival/d0.<w>.webp           the door, the first frame (the page's first paint)
 *   web/public/media/tour/arrival/hc.1920.webp          the rest on HC (reduced motion: D0 → HC → M0, route ch. 11.1)
 *   .generated/arrival.json                             the timeline, the labels' 3D points (ARR-M1) and the camera of
 *                                                       every frame they are on screen, for the page to draw them
 *
 * The walk stops at the landing on M0 (frame 702 = the room's base, empty): from there the room engine takes over and
 * plays reveal B on the real layers, as in MOCK3. The masters' own reveal and hold (703–834) are not shipped.
 *
 * The web files are encoded once per change of the masters or of this file (a stamp beside them). ffmpeg is a tool of
 * this machine, not of the site: a machine without it keeps the files it has, and fails only when none are there.
 *
 * MOCK7 (2026-11-26, briefs/site-mock7-tour-transitions-2026-11-26.md): the walk ends in the hall, at the end of the
 * turn to HDx, and the tour walks on into the living room in code (web/src/tour/gl.ts PUSH). Clip 2 (HDx → M0) is not
 * shipped: it shows the old walnut table and the old camera. The turn's last 15 frames are cut too: from frame 493 of
 * the 60 fps master the old table comes into the opening (checked frame by frame), so the walk stops at frame 490
 * (the phone's 245, the mean of 488–490), and the push starts from that very frame (`land.cam`: its camera, where the
 * page aims the push: through the opening, at M0).
 */
import sharp from 'sharp';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { GENERATED, MEDIA_OUT, repoPath } from './lib/paths';

const SRC = 'assets/video/transitions/warm-modern/arrival-v2';
const MASTER = { desktop: 'arrival-v2.desktop.1920.60fps.clean.mp4', phone: 'arrival-v2.phone.1080.30fps.clean.mp4' } as const;
const REL = 'tour/arrival';
const OUT = join(MEDIA_OUT, REL);
/** the brief's limits: the desktop ≤ 8 MB at 60 fps, the phone ≤ 3 MB, every file under the Artifact's 15 MB */
const LIMIT = { desktop: 8 * 1024 * 1024, phone: 3 * 1024 * 1024 } as const;
/** the frame of the 60 fps master the room engine took over on in MOCK4–6 (segments.json "M0 landing"), checked */
const M0_LANDING_60 = 702;
/** MOCK7: the walk's last frame, before the old walnut table enters the opening (frame 493); the phone's is 490 / 2 */
const LAND_60 = 490;
/** the rest on HC, a frame in its middle (segments.json "rest HC": 357–404) */
const HC_60 = 381;
/** the labels' window: the camera of every frame from here to there is written for the page (they move with the turns) */
const CAMS = [330, 440] as const;

type Cam = { frame: number; t: number; seg: string; loc: [number, number, number]; yaw: number; u0: number; v0: number };
type Segments = {
  timeline: Record<string, number | [number, number]>;
  segments: { segment: string; frames_60: [number, number]; frames_30: [number, number]; t: [number, number] }[];
  hc_label_anchors: {
    anchors: Record<string, { u: [number, number]; label?: null; centre?: number; src: string }>;
    label_points_3d: Record<string, [[number, number, number], [number, number, number]]>;
  };
};
const read = <T>(p: string): T => JSON.parse(readFileSync(p, 'utf8')) as T;
const dir = repoPath(SRC);
const seg = read<Segments>(join(dir, 'segments.json'));
const cams = read<Cam[]>(join(dir, 'camera.json'));
const land = seg.segments.find((s) => s.segment === 'M0 landing') ?? null;
if (!land || land.frames_60[0] !== M0_LANDING_60) throw new Error(`make-arrival: the landing on M0 is not frame ${M0_LANDING_60} of the master any more`);
const turn = seg.segments.find((s) => s.segment === 'right turn');
if (!turn || LAND_60 < turn.frames_60[0] || LAND_60 > turn.frames_60[1]) throw new Error(`make-arrival: frame ${LAND_60} is not in the turn to HDx any more`);
const LAND_30 = LAND_60 / 2;
const rest = seg.segments.find((s) => s.segment === 'rest HC')!;

const tool = readFileSync(new URL(import.meta.url), 'utf8');
const stamp = createHash('sha256')
  .update(JSON.stringify({ tool, masters: Object.values(MASTER).map((f) => [f, statSync(join(dir, f)).size, statSync(join(dir, f)).mtimeMs]) }))
  .digest('hex')
  .slice(0, 16);
const STAMP = join(OUT, 'stamp.json');
const files = {
  desktop: join(OUT, 'arrival.1920.60.mp4'),
  phone: join(OUT, 'arrival.1080.30.mp4'),
  d0: [1080, 1920].map((w) => join(OUT, `d0.${w}.webp`)),
  hc: join(OUT, 'hc.1920.webp'),
};
const have = () => existsSync(files.desktop) && existsSync(files.phone) && files.d0.every(existsSync) && existsSync(files.hc);
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
    if (!have()) throw new Error('make-arrival: ffmpeg is not on this machine and the encoded files are missing');
    console.warn('make-arrival: ffmpeg is missing; the encoded files already here are kept as they are');
  } else {
    rmSync(OUT, { recursive: true, force: true });
    mkdirSync(OUT, { recursive: true });
    const tmp = join(tmpdir(), `hd-arrival-${process.pid}`);
    mkdirSync(tmp, { recursive: true });
    // two-pass H.264 High, yuv420p, faststart, no audio; a keyframe every second (the skip and reduced motion seek)
    const encode = (master: string, frames: number, fps: number, kbps: number, max: number, level: string, out: string) => {
      const common = ['-i', join(dir, master), '-frames:v', String(frames), '-an', '-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high'];
      const rate = ['-level:v', level, '-pix_fmt', 'yuv420p', '-b:v', `${kbps}k`, '-maxrate', `${max}k`, '-bufsize', `${max * 1.4}k`, '-g', String(fps)];
      const log = join(tmp, `pass-${fps}`);
      ffmpeg([...common, ...rate, '-pass', '1', '-passlogfile', log, '-f', 'mp4', '/dev/null']);
      ffmpeg([...common, ...rate, '-pass', '2', '-passlogfile', log, '-movflags', '+faststart', out]);
    };
    encode(MASTER.desktop, LAND_60, 60, 5000, 7500, '4.2', files.desktop);
    encode(MASTER.phone, LAND_30, 30, 1900, 2800, '4.0', files.phone);
    // the stills: the door (frame 1) and the rest on HC, from the desktop master
    const still = (n: number) => {
      const png = join(tmp, `f${n}.png`);
      ffmpeg(['-i', join(dir, MASTER.desktop), '-vf', `select=eq(n\\,${n - 1})`, '-vsync', '0', '-frames:v', '1', png]);
      return png;
    };
    const d0 = still(1);
    for (const [i, w] of [1080, 1920].entries()) await sharp(d0).resize({ width: w }).webp({ quality: 80, effort: 6 }).toFile(files.d0[i]!);
    await sharp(still(HC_60)).webp({ quality: 80, effort: 6 }).toFile(files.hc);
    rmSync(tmp, { recursive: true, force: true });
    writeFileSync(STAMP, JSON.stringify({ stamp }));
  }
}
for (const k of ['desktop', 'phone'] as const) {
  const size = statSync(files[k]).size;
  if (size > LIMIT[k]) throw new Error(`make-arrival: the ${k} walk is ${(size / 1048576).toFixed(2)} MB, over ${LIMIT[k] / 1048576} MB`);
}

// ---------- the labels at the rest on HC (ARR-M1): their 3D points, and the camera of the frames they are on ----------
/** route ch. 5.5 and 11.1: the names, in the order they land (0.12 s apart, from 0.3 s before the camera stops) */
const LABELS: [string, string][] = [
  ['O-corridor-bath', 'רחצה'],
  ['O-corridor-boy', 'חדר ילד'],
  ['O-corridor-girl', 'חדר ילדה'],
  ['O-corridor-master', 'חדר שינה'],
];
const pts = seg.hc_label_anchors.label_points_3d;
const anchors = seg.hc_label_anchors.anchors;
for (const [id] of LABELS) if (!pts[id] || !anchors[id]) throw new Error(`make-arrival: no anchor for ${id}`);
// the laundry is an open opening with no label (ARR-M1): it is not drawn
if (anchors.laundry?.label !== null) throw new Error('make-arrival: the laundry has a label now; read ARR-M1 again');
const window_ = cams.filter((c) => c.frame >= CAMS[0] && c.frame <= CAMS[1]);
const r5 = (x: number) => +x.toFixed(5);
const data = {
  id: 'T-D0 arrival v2',
  qa: 'qa/reports/2026-11-18-arrival-v2 (passed, temporary, for the owner)',
  land_s: +((LAND_60 - 1) / 60).toFixed(4),
  land_60: LAND_60,
  hc_60: HC_60,
  rest_60: rest.frames_60,
  videos: {
    desktop: { src: `${REL}/arrival.1920.60.mp4`, w: 1920, h: 1080, fps: 60, frames: LAND_60, bytes: statSync(files.desktop).size },
    phone: { src: `${REL}/arrival.1080.30.mp4`, w: 1080, h: 608, fps: 30, frames: LAND_30, bytes: statSync(files.phone).size },
  },
  door: { src: `${REL}/d0`, widths: [1080, 1920] },
  hc: { src: `${REL}/hc`, width: 1920 },
  /** docs/house-plan.json conventions.projection: u = u0 + kx x/d, v = v0 + ky (hc − Z)/d (24 mm, 16:9) */
  proj: { kx: 0.6667, ky: 1.1852 },
  labels: LABELS.map(([id, name_he]) => ({ id, name_he, pts: pts[id]!, u: anchors[id]!.u })),
  /** [x, y, z, yaw, u0, v0] of frames cams[0]..cams[1] (60 fps, 1-based) */
  cams: { from: CAMS[0], f: window_.map((c) => [r5(c.loc[0]), r5(c.loc[1]), r5(c.loc[2]), r5(c.yaw), r5(c.u0), r5(c.v0)]) },
  /** MOCK7: the walk's last frame and its camera [x, y, z, yaw, u0, v0]: the transition into the living room starts there */
  land: (() => {
    const c =
      cams.find((x) => x.frame === LAND_60) ??
      (() => {
        throw new Error(`make-arrival: no camera for frame ${LAND_60}`);
      })();
    return { frame: LAND_60, cam: [r5(c.loc[0]), r5(c.loc[1]), r5(c.loc[2]), r5(c.yaw), r5(c.u0), r5(c.v0)] };
  })(),
};
mkdirSync(GENERATED, { recursive: true });
writeFileSync(join(GENERATED, 'arrival.json'), JSON.stringify(data));
const mb = (n: number) => `${(n / 1048576).toFixed(2)} MB`;
console.log(
  `arrival: desktop ${mb(data.videos.desktop.bytes)} (${LAND_60} frames @60), phone ${mb(data.videos.phone.bytes)} (${LAND_30} @30), ` +
    `the door ${files.d0.map((f) => `${(statSync(f).size / 1024).toFixed(0)} KB`).join(' / ')}, HC ${(statSync(files.hc).size / 1024).toFixed(0)} KB; ` +
    `${data.labels.length} labels, ${data.cams.f.length} cameras${fresh ? ' (cached)' : ''} → .generated/arrival.json`,
);
