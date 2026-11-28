/**
 * MOCK12 (2026-11-28, FB29): the cards a product is shown by outside the room (tools/make-tour-room.ts): how much of it
 * the room cuts, and its rim without the room it was cut from. Pure functions on raw RGBA, so the tool's test reaches
 * them (tools/test/mock12-wheels.test.ts).
 */
/**
 * MOCK12 (FB29): how much of a product's rim the room cuts, as shares of its rim (alpha ≥ 0.5, 4-connected):
 *  - `occluded`: where the rim meets a layer drawn above it (within 2 px): a sofa's arm over the throw, a cushion on the
 *    bedding. The layers are cut from one hero render, so a rim that meets an upper layer is that layer's outline;
 *  - `frame`: where the rim runs straight along the frame's lines (the hero covers the frame: a product it ended stops
 *    there) or the canvas's edge. A cord that leaves the frame is a few pixels of it.
 * Over `CUT`, the card is not shown outside the room (FB29: "משהו מסתיר אותו, אז הוא חתוך"): the page names the product.
 */
export const CUT = { occluded: 0.03, frame: 0.015 } as const;
export function rimCut(
  p: Buffer,
  W: number,
  H: number,
  top: Int16Array,
  k: number,
  fbx: [number, number, number, number],
): { occluded: number; frame: number } {
  const on = (x: number, y: number) => x >= 0 && y >= 0 && x < W && y < H && p[(y * W + x) * 4 + 3]! >= 128;
  let x0 = W;
  let y0 = H;
  let x1 = -1;
  let y1 = -1;
  for (let i = 0; i < W * H; i++)
    if (p[i * 4 + 3]! >= 128) {
      const x = i % W;
      const y = (i / W) | 0;
      if (x < x0) x0 = x;
      if (x > x1) x1 = x;
      if (y < y0) y0 = y;
      if (y > y1) y1 = y;
    }
  if (x1 < 0) return { occluded: 0, frame: 0 };
  let rim = 0;
  let occ = 0;
  for (let y = y0; y <= y1; y++)
    for (let x = x0; x <= x1; x++) {
      if (!on(x, y) || (on(x - 1, y) && on(x + 1, y) && on(x, y - 1) && on(x, y + 1))) continue;
      rim++;
      let hit = false;
      for (let dy = -2; dy <= 2 && !hit; dy++)
        for (let dx = -2; dx <= 2; dx++) {
          const X = x + dx;
          const Y = y + dy;
          if (X < 0 || Y < 0 || X >= W || Y >= H || on(X, Y)) continue;
          if (top[Y * W + X]! > k) {
            hit = true;
            break;
          }
        }
      if (hit) occ++;
    }
  const X0 = Math.round(fbx[0]);
  const Y0 = Math.round(fbx[1]);
  const X1 = Math.round(fbx[2]) - 1;
  const Y1 = Math.round(fbx[3]) - 1;
  let cut = 0;
  for (let x = Math.max(x0, X0); x <= Math.min(x1, X1); x++)
    for (const [Y, d] of [
      [Y1, 1],
      [Y0, -1],
    ] as const)
      for (let r = Y - 2; r <= Y + 2; r++)
        if (on(x, r) && !on(x, r + d)) {
          cut++;
          break;
        }
  for (let y = Math.max(y0, Y0); y <= Math.min(y1, Y1); y++)
    for (const [X, d] of [
      [X1, 1],
      [X0, -1],
    ] as const)
      for (let r = X - 2; r <= X + 2; r++)
        if (on(r, y) && !on(r + d, y)) {
          cut++;
          break;
        }
  for (let x = x0; x <= x1; x++) cut += (on(x, 0) ? 1 : 0) + (on(x, H - 1) ? 1 : 0);
  for (let y = y0; y <= y1; y++) cut += (on(0, y) ? 1 : 0) + (on(W - 1, y) ? 1 : 0);
  return { occluded: rim ? +(occ / rim).toFixed(4) : 0, frame: rim ? +(cut / rim).toFixed(4) : 0 };
}

/**
 * MOCK12 (FB29: "עם פדר, חיתוך פדר מסביב"): a card's rim without the room it was cut from. The layer's matte fades over
 * about 4 px of the room's own pixels; here it becomes a one-pixel anti-aliased edge (alpha 0.35 → 0, 0.75 → 1, smooth
 * between), and every pixel of the edge takes its colour from the product's solid pixels nearest it (within 3 px), not
 * from the wall behind it. Nothing is eroded, so a cord or a branch keeps its core.
 */
export function hardenRim(px: Buffer, w: number, h: number): Buffer {
  const out = Buffer.from(px);
  for (let i = 0; i < w * h; i++) {
    const a = px[i * 4 + 3]! / 255;
    const t = Math.min(1, Math.max(0, (a - 0.35) / 0.4));
    const s = t * t * (3 - 2 * t);
    out[i * 4 + 3] = Math.round(s * 255);
    if (a >= 0.98 || s === 0) continue;
    const x = i % w;
    const y = (i / w) | 0;
    let r = 0;
    let g = 0;
    let b = 0;
    let n = 0;
    for (let rad = 1; rad <= 3 && !n; rad++)
      for (let dy = -rad; dy <= rad; dy++)
        for (let dx = -rad; dx <= rad; dx++) {
          const X = x + dx;
          const Y = y + dy;
          if (X < 0 || Y < 0 || X >= w || Y >= h) continue;
          const j = Y * w + X;
          if (px[j * 4 + 3]! < 250) continue;
          r += px[j * 4]!;
          g += px[j * 4 + 1]!;
          b += px[j * 4 + 2]!;
          n++;
        }
    if (n) {
      out[i * 4] = Math.round(r / n);
      out[i * 4 + 1] = Math.round(g / n);
      out[i * 4 + 2] = Math.round(b / n);
    }
  }
  return out;
}

export type Box4 = { x0: number; y0: number; x1: number; y1: number };
/**
 * MOCK12: the card of a product drawn twice, far apart (a pair of sconces either side of a bed or a mirror), shows one
 * of them, not two specks in a wide empty card: the heaviest run of columns (then of rows) with alpha, where runs more
 * than 15 % of the box (at least 24 px) apart are pieces of their own. A product of one piece keeps its box.
 */
export function mainPiece(p: Buffer, W: number, box: Box4): Box4 {
  const on = (x: number, y: number) => p[(y * W + x) * 4 + 3]! >= 128;
  const split = (lo: number, hi: number, mass: (i: number) => number): [number, number] => {
    const gap = Math.max(24, 0.15 * (hi - lo + 1));
    const segs: { a: number; b: number; m: number }[] = [];
    let empty = Infinity;
    for (let i = lo; i <= hi; i++) {
      const m = mass(i);
      if (!m) {
        empty++;
        continue;
      }
      const last = segs[segs.length - 1];
      if (last && empty < gap) {
        last.b = i;
        last.m += m;
      } else segs.push({ a: i, b: i, m });
      empty = 0;
    }
    if (segs.length < 2) return [lo, hi];
    const best = segs.reduce((x, y) => (y.m > x.m ? y : x));
    return [best.a, best.b];
  };
  let b = { ...box };
  const [xa, xb] = split(b.x0, b.x1, (x) => {
    let n = 0;
    for (let y = b.y0; y <= b.y1; y++) if (on(x, y)) n++;
    return n;
  });
  b = { ...b, x0: xa, x1: xb };
  const [ya, yb] = split(b.y0, b.y1, (y) => {
    let n = 0;
    for (let x = b.x0; x <= b.x1; x++) if (on(x, y)) n++;
    return n;
  });
  b = { ...b, y0: ya, y1: yb };
  // the box tight round what is left
  let x0 = b.x1;
  let x1 = b.x0;
  let y0 = b.y1;
  let y1 = b.y0;
  for (let y = b.y0; y <= b.y1; y++)
    for (let x = b.x0; x <= b.x1; x++)
      if (on(x, y)) {
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        if (y > y1) y1 = y;
      }
  return x1 < x0 ? box : { x0, y0, x1, y1 };
}
