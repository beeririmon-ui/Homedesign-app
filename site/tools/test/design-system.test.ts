/**
 * The magazine design system in code (S5, 2026-11-07): docs/site-art-direction-2026-11-02.md §4–§7, read as rules on
 * the stylesheets. One token source (styles/system.css); every duration and curve from the motion table (G5.11);
 * none of the forbidden list (§7.3, G5.10): no backdrop blur, no shrink or growth on press or hover, no spinner or
 * shimmer, no bounce; letter-spacing 0 in Hebrew (G5.19); no justified text; radius 0, 2 or the dot's 50% (§6.1).
 *
 * The magazine pages (the story, the detail pages, the story's shop) are held to all of it. The shop and the room
 * engine are held to the forbidden list and the motion table; their layouts move to the magazine grid in §9's sprint.
 */
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { sitePath } from '../lib/paths';

type Decl = { file: string; selector: string; prop: string; value: string; media: string };
const MAGAZINE = ['web/src/styles/system.css', 'web/src/test-page/magazine.css', 'web/src/story/story.css', 'web/src/styles/shop.css'];
const SHOP = ['web/src/styles/tokens.css', 'web/src/styles/base.css', 'web/src/styles/room.css', 'web/src/styles/wheel.css', 'web/src/styles/pages.css'];

/** a small CSS reader: rules (with their @media) and declarations; enough for these stylesheets */
function decls(file: string): Decl[] {
  const css = readFileSync(sitePath(file), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  const out: Decl[] = [];
  const stack: string[] = [];
  let buf = '';
  for (const ch of css) {
    if (ch === '{') {
      stack.push(buf.trim());
      buf = '';
    } else if (ch === '}') {
      flush();
      stack.pop();
      buf = '';
    } else if (ch === ';') flush();
    else buf += ch;
  }
  function flush(): void {
    const at = buf.indexOf(':');
    const sel = stack[stack.length - 1] ?? '';
    if (at > 0 && !sel.startsWith('@')) {
      out.push({
        file,
        selector: sel,
        prop: buf.slice(0, at).trim(),
        value: buf.slice(at + 1).trim(),
        media: stack.filter((s) => s.startsWith('@')).join(' '),
      });
    }
    buf = '';
  }
  return out;
}
const all = (files: string[]) => files.flatMap(decls);
const where = (d: Decl) => `${d.file} ${d.selector} { ${d.prop}: ${d.value} }`;
const REDUCED = /prefers-reduced-motion/;

describe('the design system: one source of tokens', () => {
  it('every curve is defined once, in styles/system.css, and no curve leaves [0, 1] (no bounce, §7.3)', () => {
    const curves = all([...MAGAZINE, ...SHOP]).filter((d) => /cubic-bezier\(/.test(d.value));
    expect(curves.filter((d) => d.file !== 'web/src/styles/system.css').map(where)).toEqual([]);
    for (const d of curves) {
      const [x1, y1, x2, y2] = /cubic-bezier\(([^)]*)\)/.exec(d.value)![1]!.split(',').map(Number);
      expect(
        [x1, y1, x2, y2].every((n) => n! >= 0 && n! <= 1),
        where(d),
      ).toBe(true);
    }
  });

  it('every duration of a transition or an animation is a token (G5.11); reduced motion may only shorten', () => {
    const timed = all([...MAGAZINE, ...SHOP]).filter((d) => /^(transition|animation)(-duration|-delay)?$/.test(d.prop));
    const literal = timed.filter((d) => {
      // a fallback inside var() is the token's own value; a literal outside var() is not allowed
      const bare = d.value.replace(/var\([^()]*(\([^()]*\)[^()]*)*\)/g, '');
      return (
        /(^|[\s,(])\d*\.?\d+m?s\b/.test(bare) &&
        !(
          REDUCED.test(d.media) &&
          /^0?\.01m?s$|^0s$/.test(
            bare
              .trim()
              .split(/\s+/)
              .find((x) => /m?s$/.test(x)) ?? '',
          )
        )
      );
    });
    expect(literal.map(where)).toEqual([]);
  });

  it('the shop names are aliases of the system, not values of their own (colour, radius, curves)', () => {
    const tokens = decls('web/src/styles/tokens.css').filter((d) => d.selector === ':root');
    for (const name of ['--bg', '--line', '--line-strong', '--danger', '--glass', '--radius', '--radius-pill', '--ease', '--ease-out', '--f-body'])
      expect(tokens.find((d) => d.prop === name)?.value, name).toMatch(/^var\(--/);
  });
});

describe('the forbidden list (§7.3, G5.10)', () => {
  it('no backdrop blur, spinner, shimmer or rotation anywhere', () => {
    const bad = all([...MAGAZINE, ...SHOP]).filter(
      (d) => /backdrop-filter/.test(d.prop) || (/^animation(-name)?$/.test(d.prop) && /spin|shimmer|pulse|rotate|bounce/i.test(d.value)),
    );
    expect(bad.map(where)).toEqual([]);
  });

  it('nothing shrinks or grows on press, hover or focus', () => {
    const bad = all([...MAGAZINE, ...SHOP]).filter(
      (d) => /:(hover|active|focus|focus-visible)|\[data-(hover|active)/.test(d.selector) && /scale\(/.test(d.value),
    );
    expect(bad.map(where)).toEqual([]);
  });

  it('letter-spacing is 0 (Hebrew), text is never justified', () => {
    const bad = all([...MAGAZINE, ...SHOP]).filter(
      (d) => (d.prop === 'letter-spacing' && d.value !== '0') || (d.prop === 'text-align' && d.value === 'justify'),
    );
    expect(bad.map(where)).toEqual([]);
  });
});

describe('the magazine pages', () => {
  it('radius is 0, 2 px or a radius token; 50% only for a dot', () => {
    const bad = all(MAGAZINE).filter(
      (d) =>
        d.prop === 'border-radius' &&
        !/^((0|2px|var\(--r-(surface|control)\))\s*){1,4}$/.test(d.value) &&
        !(d.value === '50%' && /dot|mark|swatch/.test(d.selector)),
    );
    expect(bad.map(where)).toEqual([]);
  });

  it('type sizes are the scale (§4.2): a font shorthand or size names a --t- token', () => {
    const bad = all(MAGAZINE).filter((d) => (d.prop === 'font' || d.prop === 'font-size') && /\d+px/.test(d.value.replace(/var\([^)]*\)/g, '')));
    expect(bad.map(where)).toEqual([]);
  });
});
