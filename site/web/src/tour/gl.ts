/**
 * MOCK1: the tour's WebGL2 renderer. The same two passes as the room engine's compositor (engine/gl.ts), built for
 * effects that live on single layers:
 *
 *  1. compose: the base and every layer, bottom to top, into a target at the layers' own width; a layer carries its own
 *     state (opacity, blur, a wipe's clip, a lift, a gain). Only the rectangles whose layers changed are drawn again
 *     (scissor), and the target's mip levels are rebuilt for those rectangles only (an exact 2 × 2 box, level to level),
 *     so an effect costs its product's area, never the room's.
 *  2. display: one full-screen pass through the camera, with what an effect adds over the room: the scan plane (the depth
 *     of the room's box, from the plan's camera), a dimmed room around the products, their outline, a tint, the swap's
 *     light line, a wipe between two houses (by depth, or along the floor), and the door's wall.
 *
 * The rule the tour stands on: at rest every one of these is off, a layer at rest is copied texel for texel, and the
 * frame is exactly the composition of the layers. An effect's last frame IS that composition (the same target, the same
 * path), so nothing can jump when it ends.
 */
import type { Box, Cam, Viewport } from '../engine/types';
import type { Decoded } from '../engine/loader';
import { coverSize } from '../engine/camera';
import type { TourCamera } from './data';

export type LayerDraw = {
  key: string;
  rect: Box;
  shadow: boolean;
  opacity: number;
  /** blur, as a mip level of the layer's own texture (0: sharp) */
  lod: number;
  /** the part of the canvas (u) the layer is drawn in: a wipe */
  clip: [number, number];
  /** a lift, in canvas v (negative: up) */
  dy: number;
  gain: number;
  /** the product's code in the mask (its depth, see MASK_PER_M); 0: not a product */
  code: number;
};
export const layer = (key: string, rect: Box, shadow: boolean, code = 0): LayerDraw => ({
  key,
  rect,
  shadow,
  opacity: 1,
  lod: 0,
  clip: [0, 1],
  dy: 0,
  gain: 1,
  code,
});
/** [x0, y0, x1, y1] in the target's pixels, y down */
export type Px = [number, number, number, number];
/** the mask's second channel: a product's depth in metres × this (distinct per product, and a depth the shader reads) */
export const MASK_PER_M = 40;

export const FX = { none: 0, scan: 1, dim: 2, wave: 3, depth: 4 } as const;
export type Display = {
  cam: Cam;
  vp: Viewport;
  aspect: number;
  /** a plain dissolve from target A to target B */
  mix: number;
  fx: (typeof FX)[keyof typeof FX];
  /** the effect's position: the plane's depth (m), or the wave's place across the room (m) */
  t: number;
  amt: number;
  /** the whole room's exposure, in stops */
  ev: number;
  /** a warm tint over the products (the "how much they fill" flash) */
  tint: number;
  /** the outline of every product */
  outline: number;
  /** the outline of one product: its depth (m), strength */
  pulse: [number, number];
  /** the swap's light line: u, v0, v1, strength */
  line: [number, number, number, number];
  /** the vignette outside a box (the close-up; at most 0.10) */
  vig: number;
  vigBox: Box;
  /** the door's portal: centre x, y, half width, half height (CSS px), its radius and how much of the wall is there */
  door: [number, number, number, number];
  doorR: number;
  doorAmt: number;
};
export const restDisplay = (cam: Cam, vp: Viewport, aspect: number): Display => ({
  cam,
  vp,
  aspect,
  mix: 0,
  fx: FX.none,
  t: 0,
  amt: 0,
  ev: 0,
  tint: 0,
  outline: 0,
  pulse: [0, 0],
  line: [0, 0, 0, 0],
  vig: 0,
  vigBox: [0, 1, 0, 1],
  door: [0, 0, 0, 0],
  doorR: 0,
  doorAmt: 0,
});

const QUAD = new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]);
const LEVELS = 5;

const LAYER_VS = `#version 300 es
in vec2 aPos;
uniform vec4 uRect;
uniform float uDy;
out vec2 vTex;
out vec2 vFrame;
void main() {
  vec2 f = vec2(mix(uRect.x, uRect.y, aPos.x), mix(uRect.z, uRect.w, aPos.y) + uDy);
  gl_Position = vec4(f.x * 2.0 - 1.0, 1.0 - f.y * 2.0, 0.0, 1.0);
  vTex = aPos;
  vFrame = f;
}`;
const LAYER_FS = `#version 300 es
precision highp float;
in vec2 vTex;
in vec2 vFrame;
uniform sampler2D uTex;
uniform float uOpacity;
uniform float uLod;
uniform float uGain;
uniform float uCode;
uniform vec2 uClip;
uniform int uMode; // 0 product, 1 shadow (multiply), 2 mask
uniform ivec3 uOrg; // exact: 1, the rect's left, the rect's top row from the target's bottom
out vec4 o;
void main() {
  if (vFrame.x < uClip.x || vFrame.x > uClip.y) discard;
  // at rest a layer is copied texel for texel: the composition is the layers' own pixels
  vec4 t = uOrg.x == 1 ? texelFetch(uTex, ivec2(int(gl_FragCoord.x) - uOrg.y, uOrg.z - int(gl_FragCoord.y)), 0) : textureLod(uTex, vTex, uLod);
  if (uMode == 1) o = vec4(mix(vec3(1.0), t.rgb, uOpacity), 1.0);
  else if (uMode == 2) {
    if (t.a < 0.5) discard;
    o = vec4(1.0, uCode, 0.0, 1.0);
  } else o = vec4(min(t.rgb * uGain, vec3(t.a)), t.a) * uOpacity;
}`;

/** the mask's edge: where the coverage changes between a texel's neighbours, written beside the coverage and the code */
const EDGE_FS = `#version 300 es
precision highp float;
uniform sampler2D uTex;
out vec4 o;
void main() {
  ivec2 p = ivec2(gl_FragCoord.xy);
  ivec2 hi = textureSize(uTex, 0) - 1;
  vec4 m = texelFetch(uTex, p, 0);
  float e = 0.0;
  for (int i = 1; i <= 2; i++) {
    e += abs(texelFetch(uTex, min(p + ivec2(i, 0), hi), 0).r - texelFetch(uTex, max(p - ivec2(i, 0), ivec2(0)), 0).r);
    e += abs(texelFetch(uTex, min(p + ivec2(0, i), hi), 0).r - texelFetch(uTex, max(p - ivec2(0, i), ivec2(0)), 0).r);
  }
  o = vec4(m.r, m.g, min(1.0, e * 0.25), 1.0);
}`;
const DISPLAY_VS = `#version 300 es
in vec2 aPos;
out vec2 vScreen;
void main() { vScreen = vec2(aPos.x, 1.0 - aPos.y); gl_Position = vec4(aPos * 2.0 - 1.0, 0.0, 1.0); }`;
/** the display pass, built per need (`#define`s after the version line): a frame pays only for what it shows */
const DISPLAY_FS = (defines: string): string => `#version 300 es
${defines}precision highp float;
in vec2 vScreen;
uniform sampler2D uA;
uniform sampler2D uB;
uniform sampler2D uMask;
uniform vec2 uViewport;
uniform vec2 uFrame;
uniform vec3 uCam;
uniform float uMix;
uniform int uFx;
uniform float uT;
uniform float uAmt;
uniform float uEv;
uniform float uTint;
uniform float uOutline;
uniform vec2 uPulse;
uniform vec4 uLine;
uniform float uVig;
uniform vec4 uVigBox;
uniform vec4 uDoor;
uniform vec2 uDoorR;
uniform vec4 uCamFrame; // the camera frame in the canvas: u0 u1 v0 v1
uniform vec4 uProj; // u0 v0 kx ky
uniform vec4 uLoc; // camera x y height
uniform vec4 uAxes; // the camera's forward and right on the plan
uniform vec4 uRoomXY; // x0 x1 y0 y1
uniform float uRoomH;
out vec4 o;
const vec3 WARM = vec3(1.0, 0.86, 0.66);
vec2 edge(vec2 uv) { return clamp(1.0 - abs(1.0 - abs(uv)), vec2(0.0005), vec2(0.9995)); }
// the room's box seen from the plan's camera: depth along the axis (m), and the place on the plan (x, y)
vec3 box(vec2 uv) {
  vec2 c = (uv - uCamFrame.xz) / (uCamFrame.yw - uCamFrame.xz);
  float x = (c.x - uProj.x) / uProj.z;
  float s = (c.y - uProj.y) / uProj.w;
  vec2 D = uAxes.xy + x * uAxes.zw;
  float d = 60.0;
  if (s > 0.0001) d = min(d, uLoc.z / s);
  if (s < -0.0001) d = min(d, (uLoc.z - uRoomH) / s);
  if (D.x < -0.0001) d = min(d, (uRoomXY.x - uLoc.x) / D.x);
  if (D.x > 0.0001) d = min(d, (uRoomXY.y - uLoc.x) / D.x);
  if (D.y < -0.0001) d = min(d, (uRoomXY.z - uLoc.y) / D.y);
  if (D.y > 0.0001) d = min(d, (uRoomXY.w - uLoc.y) / D.y);
  return vec3(d, uLoc.xy + d * D);
}
// a mix that IS its end at its end (a driver may compute mix as a + (b - a) * k, one level off in a pixel or two)
vec3 blend(vec3 a, vec3 b, float k) { return k <= 0.0 ? a : k >= 1.0 ? b : mix(a, b, k); }
void main() {
  vec2 px = vScreen * uViewport;
  vec2 uv = edge(uCam.xy + (px - 0.5 * uViewport) / (uFrame * uCam.z));
  vec2 st = vec2(uv.x, 1.0 - uv.y);
  vec3 a = texture(uA, st).rgb;
  vec3 c = a;
#ifdef MIX
  if (uMix > 0.0) c = blend(a, texture(uB, st).rgb, uMix);
#endif
#ifdef BOX
  if (uFx == 1 || uFx == 3 || uFx == 4) {
    vec3 g = box(uv);
    if (uFx == 1) {
      // the scan plane: the room a little dimmer ahead of it, a thin warm band where it cuts the room, a short trail
      c *= mix(1.0, 0.812, smoothstep(0.0, 0.35, g.x - uT) * uAmt);
      float band = smoothstep(0.06, 0.0, abs(g.x - uT));
      float trail = smoothstep(0.7, 0.0, uT - g.x) * step(g.x, uT);
      // added light, held back on what is already bright (the wall by the window never burns out)
      c += WARM * (band * 0.34 + trail * 0.05) * uAmt * (1.0 - 0.55 * c);
    } else if (uFx == 3) {
      // the material wave: from the window wall across the floor boards, the next house behind it
      c = blend(a, texture(uB, st).rgb, 1.0 - smoothstep(uT - 0.14, uT + 0.14, g.y));
      c += WARM * smoothstep(0.24, 0.0, abs(g.y - uT)) * 0.26 * uAmt * (1.0 - 0.55 * c);
    } else {
      // the shell's swap: the plane comes from the back wall to the front, the next house behind it
      c = blend(a, texture(uB, st).rgb, smoothstep(uT - 0.1, uT + 0.1, g.x));
      c += WARM * smoothstep(0.08, 0.0, abs(g.x - uT)) * 0.34 * uAmt * (1.0 - 0.55 * c);
    }
  }
#endif
#ifdef MASK
  if (uFx == 1 || uFx == 2 || uOutline > 0.0 || uPulse.y > 0.0 || uTint > 0.0) {
    vec4 m = texture(uMask, st);
    // the product's depth (the mask is filtered: the code is weighted by the coverage)
    float dp = m.r > 0.02 ? m.g / m.r * 255.0 / ${MASK_PER_M}.0 : -9.0;
    if (uFx == 2) c *= mix(1.0, mix(0.35, 1.0, m.r), uAmt);
    c = mix(c, WARM, m.r * uTint);
    float s = uOutline;
    if (uPulse.y > 0.0) s = max(s, uPulse.y * (1.0 - smoothstep(0.008, 0.016, abs(dp - uPulse.x))));
    // the scan: a product's outline lights as the plane reaches it, and fades behind it
    if (uFx == 1 && dp > 0.0) s = max(s, uAmt * smoothstep(dp - 0.16, dp, uT) * (1.0 - smoothstep(dp + 0.2, dp + 0.75, uT)));
    // the outline is the mask's own edge, found once when the mask is made (its third channel)
    c = mix(c, WARM, clamp(m.b * 2.2, 0.0, 1.0) * s);
  }
#endif
  if (uLine.w > 0.0) {
    float dx = abs(uv.x - uLine.x) * uFrame.x * uCam.z;
    float span = smoothstep(uLine.y - 0.01, uLine.y + 0.01, uv.y) * (1.0 - smoothstep(uLine.z - 0.01, uLine.z + 0.01, uv.y));
    c += WARM * (smoothstep(1.6, 0.0, dx) * 0.85 + smoothstep(7.0, 0.0, dx) * 0.16) * span * uLine.w;
  }
  if (uVig > 0.0) {
    vec2 q = max(vec2(uVigBox.x - uv.x, uVigBox.z - uv.y), vec2(uv.x - uVigBox.y, uv.y - uVigBox.w));
    c *= 1.0 - uVig * smoothstep(0.0, 0.22, length(max(q, 0.0)));
  }
  if (uEv != 0.0) c *= exp2(uEv);
#ifdef DOOR
  if (uDoorR.y > 0.0) {
    // the door (temporary, in code): a plaster wall with a rounded portal, a walnut line round it, the jamb's shade
    vec2 p = abs(px - uDoor.xy) - uDoor.zw + uDoorR.x;
    float sd = length(max(p, 0.0)) + min(max(p.x, p.y), 0.0) - uDoorR.x;
    vec3 wall = vec3(0.925, 0.898, 0.855) * (0.945 + 0.055 * exp(-max(sd, 0.0) / 150.0));
    vec3 room = c * (1.0 - 0.3 * smoothstep(-16.0, 0.0, sd));
    vec3 w = mix(room, wall, smoothstep(-0.6, 0.6, sd));
    w = mix(w, vec3(0.42, 0.29, 0.2), smoothstep(2.0, 0.9, abs(sd - 0.4)));
    c = mix(c, w, uDoorR.y);
  }
#endif
  o = vec4(c, 1.0);
}`;

const DISPLAY_UNIFORMS = [
  'uA',
  'uB',
  'uMask',
  'uViewport',
  'uFrame',
  'uCam',
  'uMix',
  'uFx',
  'uT',
  'uAmt',
  'uEv',
  'uTint',
  'uOutline',
  'uPulse',
  'uLine',
  'uVig',
  'uVigBox',
  'uDoor',
  'uDoorR',
  'uCamFrame',
  'uProj',
  'uLoc',
  'uAxes',
  'uRoomXY',
  'uRoomH',
] as const;
type Target = { tex: WebGLTexture; fb: WebGLFramebuffer[]; w: number; h: number };
type Tex = { tex: WebGLTexture; w: number; h: number };

export class TourGL {
  private gl: WebGL2RenderingContext;
  private layerProg: WebGLProgram;
  private displayProgs = new Map<number, { prog: WebGLProgram; loc: Record<string, WebGLUniformLocation | null> }>();
  private vao: WebGLVertexArrayObject;
  private textures = new Map<string, Tex>();
  private targets: Target[] = [];
  private mask: { tex: WebGLTexture; fb: WebGLFramebuffer; w: number; h: number } | null = null;
  /** what the display reads: the mask with its edge */
  private edge: { tex: WebGLTexture; fb: WebGLFramebuffer } | null = null;
  private edgeProg: WebGLProgram;
  private codes: Uint8Array | null = null;
  private loc: Record<string, WebGLUniformLocation | null> = {};
  /** pixels shaded by the last compose (for the frame-rate evidence) */
  shaded = 0;

  static create(canvas: HTMLCanvasElement, width: number, cam: TourCamera): TourGL | null {
    const gl = canvas.getContext('webgl2', {
      alpha: false,
      antialias: false,
      premultipliedAlpha: true,
      preserveDrawingBuffer: false,
      powerPreference: 'high-performance',
    });
    if (!gl) return null;
    try {
      return new TourGL(gl, width, cam);
    } catch (e) {
      console.warn('the tour needs WebGL2', e);
      return null;
    }
  }

  private constructor(
    gl: WebGL2RenderingContext,
    readonly width: number,
    private camera: TourCamera,
  ) {
    this.gl = gl;
    if ((gl.getParameter(gl.MAX_TEXTURE_SIZE) as number) < width) throw new Error('texture size');
    this.height = Math.round(width / (16 / 9));
    this.layerProg = this.program(LAYER_VS, LAYER_FS);
    this.edgeProg = this.program(DISPLAY_VS, EDGE_FS);
    for (const n of ['uRect', 'uDy', 'uTex', 'uOpacity', 'uLod', 'uGain', 'uCode', 'uClip', 'uMode', 'uOrg'])
      this.loc[`l.${n}`] = gl.getUniformLocation(this.layerProg, n);
    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, QUAD, gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
    this.vao = vao;
    this.targets = [this.target(), this.target()];
    const mw = Math.round(this.width / 2);
    const mh = Math.round(this.height / 2);
    const tex = this.texture(gl.LINEAR);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, mw, mh);
    const fb = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    this.mask = { tex, fb, w: mw, h: mh };
    const etex = this.texture(gl.LINEAR);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA8, mw, mh);
    const efb = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, efb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, etex, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    this.edge = { tex: etex, fb: efb };
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }
  readonly height: number;

  private program(vs: string, fs: string): WebGLProgram {
    const gl = this.gl;
    const p = gl.createProgram()!;
    for (const [type, src] of [
      [gl.VERTEX_SHADER, vs],
      [gl.FRAGMENT_SHADER, fs],
    ] as const) {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s) ?? 'shader');
      gl.attachShader(p, s);
    }
    gl.bindAttribLocation(p, 0, 'aPos');
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(p) ?? 'link');
    return p;
  }

  /**
   * The display program for what a frame needs (DOOR 1, BOX 2, MASK 4, MIX 8). A frame at rest or in a camera move is a
   * camera and one texture; the plane, the masks, a second composition and the door's wall are compiled in only for
   * the frames that show them. Every variant computes the room's pixel the same way, so changing variant changes nothing.
   */
  private displayProgram(flags: number): { prog: WebGLProgram; loc: Record<string, WebGLUniformLocation | null> } {
    let p = this.displayProgs.get(flags);
    if (!p) {
      const gl = this.gl;
      const defines = ['DOOR', 'BOX', 'MASK', 'MIX'].filter((_, i) => flags & (1 << i)).map((d) => `#define ${d}\n`);
      const prog = this.program(DISPLAY_VS, DISPLAY_FS(defines.join('')));
      const loc: Record<string, WebGLUniformLocation | null> = {};
      for (const n of DISPLAY_UNIFORMS) loc[n] = gl.getUniformLocation(prog, n);
      this.displayProgs.set(flags, (p = { prog, loc }));
    }
    return p;
  }
  /** compiles the variants the tour uses, ahead of the first effect (a program linked in the middle of a move is a dropped frame) */
  warm(): void {
    for (const f of [0, 1, 2, 4, 6, 8]) this.displayProgram(f);
  }

  private texture(min: number): WebGLTexture {
    const gl = this.gl;
    const t = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, min);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }

  private target(): Target {
    const gl = this.gl;
    const tex = this.texture(gl.LINEAR_MIPMAP_LINEAR);
    gl.texStorage2D(gl.TEXTURE_2D, LEVELS, gl.RGBA8, this.width, this.height);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAX_LEVEL, LEVELS - 1);
    const fb: WebGLFramebuffer[] = [];
    for (let l = 0; l < LEVELS; l++) {
      const f = gl.createFramebuffer()!;
      gl.bindFramebuffer(gl.FRAMEBUFFER, f);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, l);
      fb.push(f);
    }
    return { tex, fb, w: this.width, h: this.height };
  }

  /** `mips`: a product layer or a shadow (its blur is a mip level of its own); the bases have none */
  upload(key: string, img: Decoded, mips: boolean): void {
    const gl = this.gl;
    const old = this.textures.get(key);
    const tex = old?.tex ?? this.texture(mips ? gl.LINEAR_MIPMAP_LINEAR : gl.LINEAR);
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, !('close' in img));
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    if (mips) gl.generateMipmap(gl.TEXTURE_2D);
    this.textures.set(key, { tex, w: img.width, h: img.height });
  }
  has(key: string): boolean {
    return this.textures.has(key);
  }

  private drawLayers(layers: LayerDraw[], w: number, h: number, mode: 'compose' | 'mask'): void {
    const gl = this.gl;
    gl.useProgram(this.layerProg);
    gl.bindVertexArray(this.vao);
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform1i(this.loc['l.uTex']!, 0);
    for (const [i, l] of layers.entries()) {
      const t = this.textures.get(l.key);
      if (!t || l.opacity <= 0) continue;
      if (mode === 'mask') {
        if (!l.code || l.shadow) continue;
        gl.disable(gl.BLEND);
      } else if (i === 0 && !l.shadow && l.opacity === 1) gl.disable(gl.BLEND);
      else {
        gl.enable(gl.BLEND);
        if (l.shadow) gl.blendFuncSeparate(gl.DST_COLOR, gl.ZERO, gl.ZERO, gl.ONE);
        else gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      }
      const x0 = Math.round(l.rect[0] * w);
      const y0 = Math.round(l.rect[2] * h);
      // texel for texel when the layer is at rest and its file is the rectangle's size
      const exact = mode === 'compose' && l.lod === 0 && l.dy === 0 && t.w === Math.round(l.rect[1] * w) - x0 && t.h === Math.round(l.rect[3] * h) - y0;
      gl.bindTexture(gl.TEXTURE_2D, t.tex);
      gl.uniform4f(this.loc['l.uRect']!, l.rect[0], l.rect[1], l.rect[2], l.rect[3]);
      gl.uniform1f(this.loc['l.uDy']!, l.dy);
      gl.uniform1f(this.loc['l.uOpacity']!, l.opacity);
      gl.uniform1f(this.loc['l.uLod']!, l.lod);
      gl.uniform1f(this.loc['l.uGain']!, l.gain);
      gl.uniform1f(this.loc['l.uCode']!, l.code / 255);
      gl.uniform2f(this.loc['l.uClip']!, l.clip[0], l.clip[1]);
      gl.uniform1i(this.loc['l.uMode']!, mode === 'mask' ? 2 : l.shadow ? 1 : 0);
      gl.uniform3i(this.loc['l.uOrg']!, exact ? 1 : 0, x0, h - 1 - y0);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    gl.disable(gl.BLEND);
  }

  /**
   * Composes `layers` (the base first) into target `n`: the whole of it, or only `rects` (what changed since the last
   * call). The mip levels follow, for the same rectangles.
   */
  compose(n: 0 | 1, layers: LayerDraw[], rects: Px[] | null): void {
    const gl = this.gl;
    const t = this.targets[n]!;
    const list: Px[] = rects ?? [[0, 0, t.w, t.h]];
    gl.bindFramebuffer(gl.FRAMEBUFFER, t.fb[0]!);
    gl.viewport(0, 0, t.w, t.h);
    this.shaded = 0;
    if (rects) gl.enable(gl.SCISSOR_TEST);
    for (const r of list) {
      if (rects) gl.scissor(r[0], t.h - r[3], r[2] - r[0], r[3] - r[1]);
      // only the layers that reach the rectangle are drawn (the base always does): a draw call each, not the whole room's
      const touch = rects
        ? layers.filter(
            (l) =>
              l.rect[0] * t.w < r[2] && l.rect[1] * t.w > r[0] && (l.rect[2] + Math.min(0, l.dy)) * t.h < r[3] && (l.rect[3] + Math.max(0, l.dy)) * t.h > r[1],
          )
        : layers;
      this.drawLayers(touch, t.w, t.h, 'compose');
      this.shaded += (r[2] - r[0]) * (r[3] - r[1]);
    }
    gl.disable(gl.SCISSOR_TEST);
    // the mip levels, level to level: every texel is the mean of its own four (the same for a rectangle and for the whole)
    for (let l = 1; l < LEVELS; l++) {
      gl.bindFramebuffer(gl.READ_FRAMEBUFFER, t.fb[l - 1]!);
      gl.bindFramebuffer(gl.DRAW_FRAMEBUFFER, t.fb[l]!);
      const lw = t.w >> l;
      const lh = t.h >> l;
      for (const r of list) {
        const x0 = Math.max(0, r[0] >> l);
        const x1 = Math.min(lw, Math.ceil(r[2] / (1 << l)));
        const y0 = Math.max(0, (t.h - r[3]) >> l);
        const y1 = Math.min(lh, Math.ceil((t.h - r[1]) / (1 << l)));
        if (x1 > x0 && y1 > y0) gl.blitFramebuffer(x0 * 2, y0 * 2, x1 * 2, y1 * 2, x0, y0, x1, y1, gl.COLOR_BUFFER_BIT, gl.LINEAR);
      }
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  /** The products of a composition, as the display's mask: coverage, and each product's code. Read back for the taps. */
  composeMask(layers: LayerDraw[], read = true): void {
    const gl = this.gl;
    const m = this.mask!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, m.fb);
    gl.viewport(0, 0, m.w, m.h);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    this.drawLayers(layers, m.w, m.h, 'mask');
    // the taps read the codes on the CPU: only for a mask that stays (a read-back in the middle of an effect stalls it)
    if (read) {
      const buf = new Uint8Array(m.w * m.h * 4);
      gl.readPixels(0, 0, m.w, m.h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
      const codes = (this.codes ??= new Uint8Array(m.w * m.h));
      for (let i = 0; i < codes.length; i++) codes[i] = buf[i * 4 + 1]!;
    }
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.edge!.fb);
    gl.useProgram(this.edgeProg);
    gl.bindVertexArray(this.vao);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, m.tex);
    gl.uniform1i(gl.getUniformLocation(this.edgeProg, 'uTex'), 0);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  /** the code of the product at a point of the canvas (0: none) */
  codeAt(u: number, v: number): number {
    const m = this.mask!;
    if (!this.codes || u < 0 || u >= 1 || v < 0 || v >= 1) return 0;
    return this.codes[(m.h - 1 - Math.floor(v * m.h)) * m.w + Math.floor(u * m.w)]!;
  }

  display(s: Display, a: 0 | 1 = 0): void {
    const gl = this.gl;
    const { fw, fh } = coverSize(s.vp, s.aspect);
    const c = this.camera;
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
    const flags =
      (s.doorAmt > 0 ? 1 : 0) |
      (s.fx === FX.scan || s.fx === FX.wave || s.fx === FX.depth ? 2 : 0) |
      (s.fx === FX.scan || s.fx === FX.dim || s.outline > 0 || s.pulse[1] > 0 || s.tint > 0 ? 4 : 0) |
      (s.mix > 0 ? 8 : 0);
    const { prog, loc: u } = this.displayProgram(flags);
    gl.useProgram(prog);
    gl.bindVertexArray(this.vao);
    for (const [i, tex, name] of [
      [0, this.targets[a]!.tex, 'uA'],
      [1, this.targets[a ? 0 : 1]!.tex, 'uB'],
      [2, this.edge!.tex, 'uMask'],
    ] as const) {
      gl.activeTexture(gl.TEXTURE0 + i);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniform1i(u[name]!, i);
    }
    gl.uniform2f(u['uViewport']!, s.vp.w, s.vp.h);
    gl.uniform2f(u['uFrame']!, fw, fh);
    gl.uniform3f(u['uCam']!, s.cam.cu, s.cam.cv, s.cam.z);
    gl.uniform1f(u['uMix']!, s.mix);
    gl.uniform1i(u['uFx']!, s.fx);
    gl.uniform1f(u['uT']!, s.t);
    gl.uniform1f(u['uAmt']!, s.amt);
    gl.uniform1f(u['uEv']!, s.ev);
    gl.uniform1f(u['uTint']!, s.tint);
    gl.uniform1f(u['uOutline']!, s.outline);
    gl.uniform2f(u['uPulse']!, s.pulse[0], s.pulse[1]);
    gl.uniform4f(u['uLine']!, s.line[0], s.line[1], s.line[2], s.line[3]);
    gl.uniform1f(u['uVig']!, s.vig);
    gl.uniform4f(u['uVigBox']!, s.vigBox[0], s.vigBox[1], s.vigBox[2], s.vigBox[3]);
    gl.uniform4f(u['uDoor']!, s.door[0], s.door[1], s.door[2], s.door[3]);
    gl.uniform2f(u['uDoorR']!, s.doorR, s.doorAmt);
    gl.uniform4f(u['uCamFrame']!, c.frame[0], c.frame[1], c.frame[2], c.frame[3]);
    gl.uniform4f(u['uProj']!, c.u0, c.v0, c.kx, c.ky);
    const yaw = (c.yaw_deg_left * Math.PI) / 180;
    gl.uniform4f(u['uLoc']!, c.loc[0], c.loc[1], c.loc[2], 0);
    // docs/house-plan.json conventions: f = (-sin yaw, -cos yaw), r = (cos yaw, -sin yaw)
    gl.uniform4f(u['uAxes']!, -Math.sin(yaw), -Math.cos(yaw), Math.cos(yaw), -Math.sin(yaw));
    gl.uniform4f(u['uRoomXY']!, c.room.x[0], c.room.x[1], c.room.y[0], c.room.y[1]);
    gl.uniform1f(u['uRoomH']!, c.room.h);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.activeTexture(gl.TEXTURE0);
  }

  /** the pixels on the canvas right after a display (the tests' seams), RGBA, bottom row first */
  readScreen(): { w: number; h: number; data: Uint8Array } {
    const gl = this.gl;
    const w = gl.drawingBufferWidth;
    const h = gl.drawingBufferHeight;
    const data = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, data);
    return { w, h, data };
  }

  /** a rectangle of a target's own pixels (the tests: the composition itself), RGBA, top row first */
  readTarget(n: 0 | 1, r: Px): Uint8Array {
    const gl = this.gl;
    const t = this.targets[n]!;
    const w = r[2] - r[0];
    const h = r[3] - r[1];
    const data = new Uint8Array(w * h * 4);
    gl.bindFramebuffer(gl.FRAMEBUFFER, t.fb[0]!);
    gl.readPixels(r[0], t.h - r[3], w, h, gl.RGBA, gl.UNSIGNED_BYTE, data);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    const row = w * 4;
    const out = new Uint8Array(data.length);
    for (let y = 0; y < h; y++) out.set(data.subarray((h - 1 - y) * row, (h - y) * row), y * row);
    return out;
  }

  resize(cssW: number, cssH: number, dpr: number): void {
    const c = this.gl.canvas as HTMLCanvasElement;
    c.width = Math.max(1, Math.round(cssW * dpr));
    c.height = Math.max(1, Math.round(cssH * dpr));
  }

  destroy(): void {
    const gl = this.gl;
    for (const t of this.textures.values()) gl.deleteTexture(t.tex);
    this.textures.clear();
    for (const t of this.targets) {
      for (const f of t.fb) gl.deleteFramebuffer(f);
      gl.deleteTexture(t.tex);
    }
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}
