/**
 * WebGL2 compositor. Two passes:
 *  1. compose: every layer is a textured quad at its rect, drawn bottom-to-top into a framebuffer at frame
 *     resolution with premultiplied blending (normal, multiply, screen). Runs only when something changes.
 *  2. display: one full-screen pass that maps screen → frame through the camera, mixes the previous and next
 *     compositions (variant/style cross-fades) and shifts UVs by the depth map (parallax during zoom).
 * At rest nothing is drawn; the GPU is idle.
 */
import type { Compositor, DisplayState, DrawLayer } from './compositor';
import type { Decoded } from './loader';
import { coverSize } from './camera';

const QUAD = new Float32Array([0, 0, 1, 0, 0, 1, 1, 1]);

const LAYER_VS = `#version 300 es
in vec2 aPos;
uniform vec4 uRect; // u0 u1 v0 v1
out vec2 vTex;
void main() {
  vec2 f = vec2(mix(uRect.x, uRect.y, aPos.x), mix(uRect.z, uRect.w, aPos.y));
  gl_Position = vec4(f.x * 2.0 - 1.0, 1.0 - f.y * 2.0, 0.0, 1.0);
  vTex = aPos;
}`;
const LAYER_FS = `#version 300 es
precision mediump float;
in vec2 vTex;
uniform sampler2D uTex;
uniform float uOpacity;
out vec4 o;
void main() { o = texture(uTex, vTex) * uOpacity; }`;

const DISPLAY_VS = `#version 300 es
in vec2 aPos;
out vec2 vScreen;
void main() { vScreen = vec2(aPos.x, 1.0 - aPos.y); gl_Position = vec4(aPos * 2.0 - 1.0, 0.0, 1.0); }`;
const DISPLAY_FS = `#version 300 es
precision highp float;
in vec2 vScreen;
uniform sampler2D uPrev;
uniform sampler2D uNext;
uniform sampler2D uDepth;
uniform float uMix;
uniform vec2 uViewport;
uniform vec2 uFrame;
uniform vec3 uCam;
uniform vec4 uPar; // dolly, focus, driftX, driftY
out vec4 o;
void main() {
  vec2 px = vScreen * uViewport;
  vec2 uv = uCam.xy + (px - 0.5 * uViewport) / (uFrame * uCam.z);
  float d = texture(uDepth, clamp(uv, 0.0, 1.0)).r;
  float k = uPar.x * (d - uPar.y);
  uv = uCam.xy + (uv - uCam.xy) / (1.0 + k);
  uv += (d - 0.5) * uPar.zw;
  uv = clamp(uv, vec2(0.0005), vec2(0.9995));
  vec2 t = vec2(uv.x, 1.0 - uv.y);
  vec4 a = texture(uPrev, t);
  vec4 b = texture(uNext, t);
  o = vec4(mix(a.rgb, b.rgb, uMix), 1.0);
}`;

type Target = { fb: WebGLFramebuffer; tex: WebGLTexture; w: number; h: number };

export class GLCompositor implements Compositor {
  readonly kind = 'webgl2' as const;
  private gl: WebGL2RenderingContext;
  private layerProg: WebGLProgram;
  private displayProg: WebGLProgram;
  private vao: WebGLVertexArrayObject;
  private textures = new Map<string, WebGLTexture>();
  private depthTex: WebGLTexture;
  private prev: Target | null = null;
  private next: Target | null = null;
  private maxTex: number;
  private loc: Record<string, WebGLUniformLocation | null> = {};

  static create(canvas: HTMLCanvasElement): GLCompositor | null {
    const gl = canvas.getContext('webgl2', {
      alpha: false,
      antialias: false,
      premultipliedAlpha: true,
      preserveDrawingBuffer: false,
      powerPreference: 'high-performance',
    });
    if (!gl) return null;
    try {
      return new GLCompositor(gl);
    } catch (e) {
      console.warn('WebGL2 init failed, falling back to canvas 2D', e);
      return null;
    }
  }

  private constructor(gl: WebGL2RenderingContext) {
    this.gl = gl;
    this.maxTex = gl.getParameter(gl.MAX_TEXTURE_SIZE) as number;
    this.layerProg = this.program(LAYER_VS, LAYER_FS);
    this.displayProg = this.program(DISPLAY_VS, DISPLAY_FS);
    for (const n of ['uRect', 'uTex', 'uOpacity']) this.loc[`l.${n}`] = gl.getUniformLocation(this.layerProg, n);
    for (const n of ['uPrev', 'uNext', 'uDepth', 'uMix', 'uViewport', 'uFrame', 'uCam', 'uPar'])
      this.loc[`d.${n}`] = gl.getUniformLocation(this.displayProg, n);
    const vao = gl.createVertexArray()!;
    gl.bindVertexArray(vao);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, QUAD, gl.STATIC_DRAW);
    for (const p of [this.layerProg, this.displayProg]) {
      const a = gl.getAttribLocation(p, 'aPos');
      gl.enableVertexAttribArray(a);
      gl.vertexAttribPointer(a, 2, gl.FLOAT, false, 0, 0);
    }
    this.vao = vao;
    // neutral depth until the real map arrives
    this.depthTex = this.texture();
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([128, 128, 128, 255]));
  }

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

  private texture(): WebGLTexture {
    const gl = this.gl;
    const t = gl.createTexture()!;
    gl.bindTexture(gl.TEXTURE_2D, t);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    return t;
  }

  upload(key: string, img: Decoded): void {
    const gl = this.gl;
    const t = this.textures.get(key) ?? this.texture();
    gl.bindTexture(gl.TEXTURE_2D, t);
    // ImageBitmaps arrive premultiplied; for <img> fallbacks ask GL to premultiply on upload.
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, !('close' in img));
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
    this.textures.set(key, t);
  }

  has(key: string): boolean {
    return this.textures.has(key);
  }

  setDepth(img: Decoded): void {
    const gl = this.gl;
    gl.bindTexture(gl.TEXTURE_2D, this.depthTex);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
  }

  private target(w: number, h: number): Target {
    const gl = this.gl;
    const tex = this.texture();
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texStorage2D(gl.TEXTURE_2D, Math.floor(Math.log2(Math.max(w, h))) + 1, gl.RGBA8, w, h);
    const fb = gl.createFramebuffer()!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    return { fb, tex, w, h };
  }

  private ensureTargets(w: number): void {
    const width = Math.min(w, this.maxTex);
    const height = Math.round(width / (16 / 9));
    if (this.next && this.next.w === width) return;
    for (const t of [this.prev, this.next]) if (t) this.drop(t);
    this.prev = this.target(width, height);
    this.next = this.target(width, height);
  }

  private drop(t: Target): void {
    this.gl.deleteFramebuffer(t.fb);
    this.gl.deleteTexture(t.tex);
  }

  compose(layers: DrawLayer[], width: number): void {
    const gl = this.gl;
    this.ensureTargets(width);
    const t = this.next!;
    gl.bindFramebuffer(gl.FRAMEBUFFER, t.fb);
    gl.viewport(0, 0, t.w, t.h);
    gl.clearColor(0.08, 0.075, 0.07, 1);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(this.layerProg);
    gl.bindVertexArray(this.vao);
    gl.enable(gl.BLEND);
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform1i(this.loc['l.uTex']!, 0);
    for (const l of layers) {
      const tex = this.textures.get(l.key);
      if (!tex) continue;
      if (l.blend === 'multiply') gl.blendFuncSeparate(gl.DST_COLOR, gl.ONE_MINUS_SRC_ALPHA, gl.ZERO, gl.ONE);
      else if (l.blend === 'screen') gl.blendFuncSeparate(gl.ONE, gl.ONE_MINUS_SRC_COLOR, gl.ZERO, gl.ONE);
      else gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniform4f(this.loc['l.uRect']!, l.rect[0], l.rect[1], l.rect[2], l.rect[3]);
      gl.uniform1f(this.loc['l.uOpacity']!, l.opacity);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    gl.disable(gl.BLEND);
    gl.bindTexture(gl.TEXTURE_2D, t.tex);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
  }

  swap(): void {
    [this.prev, this.next] = [this.next, this.prev];
  }

  display(s: DisplayState): void {
    const gl = this.gl;
    if (!this.next || !this.prev) return;
    const { fw, fh } = coverSize(s.vp, s.aspect);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
    gl.useProgram(this.displayProg);
    gl.bindVertexArray(this.vao);
    const units: [WebGLTexture, string][] = [
      [this.prev.tex, 'd.uPrev'],
      [this.next.tex, 'd.uNext'],
      [this.depthTex, 'd.uDepth'],
    ];
    units.forEach(([tex, name], i) => {
      gl.activeTexture(gl.TEXTURE0 + i);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.uniform1i(this.loc[name]!, i);
    });
    gl.uniform1f(this.loc['d.uMix']!, s.mix);
    gl.uniform2f(this.loc['d.uViewport']!, s.vp.w, s.vp.h);
    gl.uniform2f(this.loc['d.uFrame']!, fw, fh);
    gl.uniform3f(this.loc['d.uCam']!, s.cam.cu, s.cam.cv, s.cam.z);
    gl.uniform4f(this.loc['d.uPar']!, s.parallax, s.focus, s.drift[0], s.drift[1]);
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    gl.activeTexture(gl.TEXTURE0);
  }

  resize(cssW: number, cssH: number, dpr: number): void {
    const c = this.gl.canvas as HTMLCanvasElement;
    c.width = Math.max(1, Math.round(cssW * dpr));
    c.height = Math.max(1, Math.round(cssH * dpr));
  }

  destroy(): void {
    const gl = this.gl;
    for (const t of this.textures.values()) gl.deleteTexture(t);
    this.textures.clear();
    for (const t of [this.prev, this.next]) if (t) this.drop(t);
    gl.getExtension('WEBGL_lose_context')?.loseContext();
  }
}
