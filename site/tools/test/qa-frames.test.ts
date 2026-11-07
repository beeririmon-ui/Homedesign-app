/**
 * QA's register and the older records (tools/lib/qa-frames.ts): the highest version wins, a row is chosen by the
 * option the frame shows, and a record the site cannot read fails loudly (QA on S2, 2026-11-07), never as no rows.
 */
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { afterAll, describe, expect, it } from 'vitest';
import { repoPath } from '../lib/paths';
import { qaReader, registerReader, rowOf } from '../lib/qa-frames';

const DIR = 'site/.generated/test-qa-frames';
const put = (name: string, d: unknown) => writeFileSync(repoPath(DIR, name), JSON.stringify(d));
const row = (card_id: string, verdict: string, dot: string, option: unknown = null) => ({ card_id, option, verdict, note: '', dot });
mkdirSync(repoPath(DIR), { recursive: true });
afterAll(() => rmSync(repoPath(DIR), { recursive: true, force: true }));

describe('the QA register', () => {
  it('reads the highest version, its frames and its close-ups, and picks the row of the option the frame shows', () => {
    put('ged-register-a.json', { version: 1, frames: { f: { state: 'almost', rows: [row('bowl', 'yes', 'yes')] } } });
    put('ged-register-b.json', {
      version: 2,
      frames: {
        f: { state: 'final_test', rows: [row('cushion', 'yes', 'yes', { color: 'tea' }), row('cushion', 'partly', 'closeup_only', { color: 'white' })] },
      },
      closeups: { 'cu-1': { state: 'final_test', rows: [row('cushion', 'yes', 'yes', { color: 'white' })] } },
      superseded_by: { old: 'f' },
    });
    const r = registerReader(DIR);
    expect(r.version).toBe(2);
    const f = r.read('f')!;
    expect(f.state).toBe('final_test');
    expect(rowOf(f, 'cushion', { color: 'white', size: '50x50' })!.dot).toBe('closeup_only');
    expect(rowOf(f, 'cushion', { color: 'tea', size: '50x50' })!.faithful).toBe('yes');
    expect(r.read('cu-1')!.rows[0]!.faithful).toBe('yes');
    // an option without its own row is "not checked", never the first row of another option (QA on S4)
    expect(rowOf(f, 'cushion', { color: 'green', size: '50x50' })).toBeNull();
    expect(r.supersededBy('old')).toBe('f');
    expect(r.read('nope')).toBeNull();
  });

  it('fails loudly on a register it cannot read: an unknown state, a frame without rows, a row without its dot', () => {
    for (const bad of [
      { version: 3, frames: { f: { state: 'ready', rows: [row('bowl', 'yes', 'yes')] } } },
      { version: 3, frames: { f: { state: 'final_test', rows: [] } } },
      { version: 3, frames: { f: { state: 'final_test', rows: [{ card_id: 'bowl', verdict: 'yes' }] } } },
    ]) {
      put('ged-register-c.json', bad);
      expect(() => registerReader(DIR)).toThrow(/cannot be read/);
    }
    rmSync(repoPath(DIR, 'ged-register-c.json'));
  });

  it('reads units_in_frame (register v4, G-ED.6), and fails loudly on a count it cannot use', () => {
    put('ged-register-d.json', { version: 4, frames: { f: { state: 'final_test', rows: [{ ...row('cushion', 'yes', 'yes'), units_in_frame: 2 }] } } });
    expect(rowOf(registerReader(DIR).read('f')!, 'cushion', null)!.units).toBe(2);
    for (const units_in_frame of [0, 1.5, '2', 99]) {
      put('ged-register-d.json', { version: 4, frames: { f: { state: 'final_test', rows: [{ ...row('cushion', 'yes', 'yes'), units_in_frame }] } } });
      expect(() => registerReader(DIR)).toThrow(/cannot be read/);
    }
    rmSync(repoPath(DIR, 'ged-register-d.json'));
  });

  it('fails loudly on the older records the site cannot read: part1 without "against", frames without rows', () => {
    put('old-part1.json', { part1: { frames: { f: { state: 'almost', rows_changed: [] } } } });
    expect(() => qaReader([`${DIR}/old-part1.json`])('f')).toThrow(/against/);
    put('old-flat.json', { frames: { f: { state: 'almost', counts: { rows: 7 } } } });
    expect(() => qaReader([`${DIR}/old-flat.json`])('f')).toThrow(/no rows/);
  });
});
