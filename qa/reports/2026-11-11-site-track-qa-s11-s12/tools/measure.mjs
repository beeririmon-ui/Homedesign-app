/** qa-agent, 2026-11-11: the measure of encoding-qa.mjs, for the poster candidates (the same code). */
// ---------- the measure (my own, as in S8–S10) ----------
const lin = (c) => {
  c /= 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};
const LUT = Float64Array.from({ length: 256 }, (_, i) => lin(i));
function lab(r, g, b) {
  const R = LUT[r], G = LUT[g], B = LUT[b];
  let x = (0.4124564 * R + 0.3575761 * G + 0.1804375 * B) / 0.95047, y = 0.2126729 * R + 0.7151522 * G + 0.072175 * B, z = (0.0193339 * R + 0.119192 * G + 0.9503041 * B) / 1.08883;
  const f = (t) => (t > 216 / 24389 ? Math.cbrt(t) : ((24389 / 27) * t + 16) / 116);
  x = f(x); y = f(y); z = f(z);
  return [116 * y - 16, 500 * (x - y), 200 * (y - z)];
}
function de2000([L1, a1, b1], [L2, a2, b2]) {
  const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2), Cb = (C1 + C2) / 2, G = 0.5 * (1 - Math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)));
  const a1p = (1 + G) * a1, a2p = (1 + G) * a2, C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
  const h = (a, b) => { if (a === 0 && b === 0) return 0; const t = (Math.atan2(b, a) * 180) / Math.PI; return t < 0 ? t + 360 : t; };
  const h1p = h(a1p, b1), h2p = h(a2p, b2), dLp = L2 - L1, dCp = C2p - C1p;
  let dhp = 0;
  if (C1p * C2p) { dhp = h2p - h1p; if (dhp > 180) dhp -= 360; else if (dhp < -180) dhp += 360; }
  const dHp = 2 * Math.sqrt(C1p * C2p) * Math.sin((dhp * Math.PI) / 360), Lbp = (L1 + L2) / 2, Cbp = (C1p + C2p) / 2;
  let hbp = h1p + h2p;
  if (C1p * C2p) { if (Math.abs(h1p - h2p) > 180) hbp += h1p + h2p < 360 ? 360 : -360; hbp /= 2; }
  const T = 1 - 0.17 * Math.cos(((hbp - 30) * Math.PI) / 180) + 0.24 * Math.cos((2 * hbp * Math.PI) / 180) + 0.32 * Math.cos(((3 * hbp + 6) * Math.PI) / 180) - 0.2 * Math.cos(((4 * hbp - 63) * Math.PI) / 180);
  const dth = 30 * Math.exp(-(((hbp - 275) / 25) ** 2)), RC = 2 * Math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7));
  const SL = 1 + (0.015 * (Lbp - 50) ** 2) / Math.sqrt(20 + (Lbp - 50) ** 2), SC = 1 + 0.045 * Cbp, SH = 1 + 0.015 * Cbp * T, RT = -Math.sin((2 * dth * Math.PI) / 180) * RC;
  return Math.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH));
}
/** ref and x: {data (RGB), w, h}; box: optional {x0,x1,y0,y1} */
export function compare(ref, x, box) {
  const b = box ?? { x0: 0, x1: ref.w, y0: 0, y1: ref.h };
  const hist = new Uint32Array(256);
  const des = [];
  let n = 0;
  for (let y = b.y0; y < b.y1; y++)
    for (let xx = b.x0; xx < b.x1; xx++) {
      const i = (y * ref.w + xx) * 3;
      const d = Math.max(Math.abs(ref.data[i] - x.data[i]), Math.abs(ref.data[i + 1] - x.data[i + 1]), Math.abs(ref.data[i + 2] - x.data[i + 2]));
      hist[d]++;
      n++;
      // ΔE on every 3rd pixel (deterministic sampling); 0 for identical pixels
      if (n % 3 === 0) des.push(d ? de2000(lab(ref.data[i], ref.data[i + 1], ref.data[i + 2]), lab(x.data[i], x.data[i + 1], x.data[i + 2])) : 0);
    }
  const pct = (q) => { let c = 0; for (let d = 0; d < 256; d++) { c += hist[d]; if (c >= q * n) return d; } return 255; };
  let max = 0;
  for (let d = 255; d >= 0; d--) if (hist[d]) { max = d; break; }
  let over = 0;
  for (let d = 9; d < 256; d++) over += hist[d];
  des.sort((a, c) => a - c);
  const m = { px: n, p99: pct(0.99), p999: pct(0.999), max, over8_pct: +((100 * over) / n).toFixed(3), de_p99: +des[Math.floor(des.length * 0.99)].toFixed(2) };
  m.pass = m.p99 <= 6 && m.p999 <= 10 && m.over8_pct <= 0.2 && m.de_p99 <= 3.5;
  return m;
}
export const fmt = (m) => `${m.p99}/${m.p999}/${m.max} · ${m.over8_pct}% · ΔE ${m.de_p99}${m.pass ? '' : '  FAIL'}`;

