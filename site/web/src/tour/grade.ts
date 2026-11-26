/**
 * MOCK8 (2026-11-26, briefs/site-mock8-integrate-2026-11-26.md; FB16): the house grade of a frame, as render-agent's
 * light pass applies it (assets/renders/tools/fb16/fb16.py apply_grade; the parameters in the manifest's
 * `fb16.frames.<id>.grade`): on the composite, in CIELAB (D65, OpenCV's sRGB conversion), a monotone cubic L curve
 * through five knots, and a and b scaled with the exposure plus a shift to warm in the mid-tones:
 *
 *   L' = pchip(L);  a' = a (L' + 16) / (L + 16) + da w(L');  b' = b (L' + 16) / (L + 16) + db w(L')
 *   w = smoothstep(15, 30, L') (1 − smoothstep(92, 99, L'))
 *
 * The engine draws it in the compose pass (web/src/tour/gl.ts: the layers into a raw target, then this, then the
 * frame's glows over it), so the composition the display, the dissolves and the walks read IS the graded frame. The
 * shader below and `gradeRgb` are the same arithmetic (the unit test holds them to the fb16 tool's own numbers). No
 * import: the unit tests read it on its own.
 */
export type TourGrade = {
  /** the L curve's knots, in and out, and its slopes at them (the fb16 tool's pchip, written by the room's tool) */
  kin: number[];
  kout: number[];
  m: number[];
  /** the shift to warm (a, b) at full weight */
  da: number;
  db: number;
};

const lin = (c: number) => (c > 0.04045 ? ((c + 0.055) / 1.055) ** 2.4 : c / 12.92);
const srgb = (c: number) => (c > 0.0031308 ? 1.055 * c ** (1 / 2.4) - 0.055 : 12.92 * c);
const f3 = (t: number) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
const smooth = (e0: number, e1: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - e0) / (e1 - e0)));
  return t * t * (3 - 2 * t);
};
/** the L curve: the cubic Hermite of the interval L is in (the last one past the knots) */
export function curve(g: TourGrade, L0: number): number {
  const L = Math.min(100, Math.max(0, L0));
  let i = 0;
  for (let k = 1; k < g.kin.length - 1; k++) if (L >= g.kin[k]!) i = k;
  const h = g.kin[i + 1]! - g.kin[i]!;
  const t = (L - g.kin[i]!) / h;
  const t2 = t * t;
  const t3 = t2 * t;
  return (2 * t3 - 3 * t2 + 1) * g.kout[i]! + (t3 - 2 * t2 + t) * h * g.m[i]! + (-2 * t3 + 3 * t2) * g.kout[i + 1]! + (t3 - t2) * h * g.m[i + 1]!;
}
/** one 8-bit sRGB colour through the grade, rounded to 8 bits */
export function gradeRgb(rgb: readonly number[], g: TourGrade): [number, number, number] {
  const [r, gg, b] = rgb.map((x) => lin(x / 255)) as [number, number, number];
  const X = (0.412453 * r + 0.35758 * gg + 0.180423 * b) / 0.950456;
  const Y = 0.212671 * r + 0.71516 * gg + 0.072169 * b;
  const Z = (0.019334 * r + 0.119193 * gg + 0.950227 * b) / 1.088754;
  const fx = f3(X);
  const fy = f3(Y);
  const fz = f3(Z);
  const L = Y > 0.008856 ? 116 * fy - 16 : 903.3 * Y;
  let A = 500 * (fx - fy);
  let B = 200 * (fy - fz);
  const L2 = curve(g, L);
  const sc = (L2 + 16) / (L + 16);
  const w = smooth(15, 30, L2) * (1 - smooth(92, 99, L2));
  A = A * sc + g.da * w;
  B = B * sc + g.db * w;
  let Yr: number;
  let fy2: number;
  if (L2 <= 7.9996248) {
    Yr = L2 / 903.3;
    fy2 = 7.787 * Yr + 16 / 116;
  } else {
    fy2 = (L2 + 16) / 116;
    Yr = fy2 ** 3;
  }
  const inv = (f: number) => (f <= 0.206893 ? (f - 16 / 116) / 7.787 : f ** 3);
  const Xr = inv(A / 500 + fy2) * 0.950456;
  const Zr = inv(fy2 - B / 200) * 1.088754;
  const out = [3.240479 * Xr - 1.53715 * Yr - 0.498535 * Zr, -0.969256 * Xr + 1.875991 * Yr + 0.041556 * Zr, 0.055648 * Xr - 0.204043 * Yr + 1.057311 * Zr];
  return out.map((c) => Math.min(255, Math.max(0, Math.round(srgb(Math.min(1, Math.max(0, c))) * 255)))) as [number, number, number];
}

/** the same, as the compose pass draws it: the raw composite in, the graded frame out (texel for texel) */
export const GRADE_FS = `#version 300 es
precision highp float;
uniform sampler2D uRaw;
uniform float uKin[5];
uniform float uKout[5];
uniform float uM[5];
uniform vec2 uDab;
out vec4 o;
vec3 lin(vec3 c) { return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c)); }
vec3 srgb(vec3 c) { return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c)); }
float f3(float t) { return t > 0.008856 ? pow(t, 1.0 / 3.0) : 7.787 * t + 16.0 / 116.0; }
float inv3(float f) { return f <= 0.206893 ? (f - 16.0 / 116.0) / 7.787 : f * f * f; }
float curve(float L0) {
  float L = clamp(L0, 0.0, 100.0);
  int i = 0;
  for (int k = 1; k < 4; k++) if (L >= uKin[k]) i = k;
  float h = uKin[i + 1] - uKin[i];
  float t = (L - uKin[i]) / h;
  float t2 = t * t;
  float t3 = t2 * t;
  return (2.0 * t3 - 3.0 * t2 + 1.0) * uKout[i] + (t3 - 2.0 * t2 + t) * h * uM[i] + (-2.0 * t3 + 3.0 * t2) * uKout[i + 1] + (t3 - t2) * h * uM[i + 1];
}
void main() {
  vec3 l = lin(texelFetch(uRaw, ivec2(gl_FragCoord.xy), 0).rgb);
  float X = dot(vec3(0.412453, 0.357580, 0.180423), l) / 0.950456;
  float Y = dot(vec3(0.212671, 0.715160, 0.072169), l);
  float Z = dot(vec3(0.019334, 0.119193, 0.950227), l) / 1.088754;
  float fy = f3(Y);
  float L = Y > 0.008856 ? 116.0 * fy - 16.0 : 903.3 * Y;
  float A = 500.0 * (f3(X) - fy);
  float B = 200.0 * (fy - f3(Z));
  float L2 = curve(L);
  float sc = (L2 + 16.0) / (L + 16.0);
  float w = smoothstep(15.0, 30.0, L2) * (1.0 - smoothstep(92.0, 99.0, L2));
  A = A * sc + uDab.x * w;
  B = B * sc + uDab.y * w;
  float Yr = L2 <= 7.9996248 ? L2 / 903.3 : pow((L2 + 16.0) / 116.0, 3.0);
  float fy2 = L2 <= 7.9996248 ? 7.787 * Yr + 16.0 / 116.0 : (L2 + 16.0) / 116.0;
  float Xr = inv3(A / 500.0 + fy2) * 0.950456;
  float Zr = inv3(fy2 - B / 200.0) * 1.088754;
  vec3 rgb = vec3(3.240479 * Xr - 1.53715 * Yr - 0.498535 * Zr, -0.969256 * Xr + 1.875991 * Yr + 0.041556 * Zr, 0.055648 * Xr - 0.204043 * Yr + 1.057311 * Zr);
  o = vec4(srgb(clamp(rgb, 0.0, 1.0)), 1.0);
}`;
