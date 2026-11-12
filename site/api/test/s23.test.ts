/**
 * S23, QA ת76: a known order's values in a log row, beyond S21 (ת64): a run of capitals before a Camel word ("DANAGat",
 * "XMLDana"), a value without its spaces ("danagat", "TELAVIV", "נועהבןדוד"), an encoded value (%XX, \uXXXX), a change of
 * script with no separator ("Noaלוי", "ID:נועהX"), and an invisible character inside a name. QA's own probes are read
 * from an external file (test/external/qa-s21-log-residue.json), not written here: the rule was not tuned on this file.
 * Each probe goes in a field and in an error's message, as QA ran them. Ordinary words stay whole; the cost on names that
 * are English words (ה36) is printed, and compared with S21's in the S23 README.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { configureLog, decodeEscapes, knownValues, logRow, stripKnown } from '../src/lib/log';

type Customer = { full_name: string; email?: string; address?: Record<string, string> };
type Probe = [who: string, id: string, text: string, gone: string[]];
const here = dirname(fileURLToPath(import.meta.url));
const qa = JSON.parse(readFileSync(resolve(here, 'external/qa-s21-log-residue.json'), 'utf8')) as {
  customers: Record<string, Customer>;
  residue: Probe[];
  claimed: Probe[];
  ordinary: { customer: string; words: string[]; accepted_changes: string[] };
  wordy: { customer: string; words: string[] };
};
const leaks = (out: string, gone: string[]) => gone.filter((g) => out.toLowerCase().includes(g.toLowerCase()));
function run(probes: Probe[]) {
  configureLog({ ENVIRONMENT: 'test' });
  try {
    return probes.map(([who, id, text, gone]) => {
      const k = knownValues(qa.customers[who]!);
      const row = logRow('error', 'qa.probe', { detail: text, error_id: 'E-2345ABCD', order_id: '1234567890' }, new Error(text), k) as Record<string, string>;
      return { id, field: row.detail!, message: row.error_message!, leaks: [...leaks(row.detail!, gone), ...leaks(row.error_message!, gone)] };
    });
  } finally {
    configureLog({ ENVIRONMENT: 'production' });
  }
}

describe('S23 ת76: the residue QA found after S21 (external list)', () => {
  it('every residue probe leaves no value, in a field or in a message', () => {
    const out = run(qa.residue);
    expect(out.length).toBe(10);
    expect(out.filter((r) => r.leaks.length)).toEqual([]);
  });
  it('the forms S19–S21 already took still go (no regression)', () => {
    const out = run(qa.claimed);
    expect(out.length).toBe(35);
    expect(out.filter((r) => r.leaks.length)).toEqual([]);
  });
  it('the error id and the order number keep their shape', () => {
    const k = knownValues(qa.customers.latin!);
    const row = logRow('error', 'qa.ids', { error_id: 'E-DANA2345', order_id: '1234567890', note: 'see E-DANA2345' }, undefined, k) as Record<string, string>;
    expect([row.error_id, row.order_id]).toEqual(['E-DANA2345', '1234567890']);
  });
});

describe('S23 ת76: ordinary words stay whole, and the cost is said', () => {
  it("QA's 36 words and tokens are unchanged (but the one QA accepted)", () => {
    const k = knownValues(qa.customers[qa.ordinary.customer]!);
    const changed = qa.ordinary.words.filter((w) => stripKnown(w, k) !== w);
    expect(qa.ordinary.words.length).toBe(36);
    expect(changed).toEqual(qa.ordinary.accepted_changes);
  });
  it('a value written encoded is read decoded only when that finds a value; other escapes stay as written', () => {
    const k = knownValues(qa.customers.latin!);
    expect(stripKnown('path=/a%20b/c?x=%2F', k)).toBe('path=/a%20b/c?x=%2F');
    expect(stripKnown('{"q":"\\u0041BC"}', k)).toBe('{"q":"\\u0041BC"}');
    // here the plain reading already finds every word ("%" is no letter): the escapes stay as written
    expect(stripKnown('to=Dana%20Gat%2C%20Tel%20Aviv', k)).toBe('to=[customer]%20[customer]%2C%20[customer]%20[customer]');
    expect(stripKnown('to=%44ana', k)).toBe('to=[customer]');
    expect(decodeEscapes('%D7%A0%D7%95%D7%A2%D7%94 %E0%A4 \\u05d3')).toBe('נועה %E0%A4 ד');
  });
  it('the boundaries: a capital run, a change of script; and what stays', () => {
    const k = knownValues(qa.customers.mixed!);
    expect(stripKnown('ROTHSCHILDStreet', k)).toBe('[customer]Street');
    expect(stripKnown('לויNoa', k)).toBe('[customer][customer]');
    expect(stripKnown('Noaלויה', k)).toBe('[customer]לויה');
    expect(stripKnown('Noah', k)).toBe('Noah');
    expect(stripKnown('HTTPServer iPhone McDonald', k)).toBe('HTTPServer iPhone McDonald');
  });
  it('ה36, names that are English words (Max Page, Rose Valley, Mark): printed, as QA asked, not asserted', () => {
    const k = knownValues(qa.customers[qa.wordy.customer]!);
    const out = Object.fromEntries(qa.wordy.words.map((w) => [w, stripKnown(w, k)]));
    console.warn(`S23 ה36 (wordy): ${JSON.stringify(out)}`);
    // the words that never carried the name stay whole
    expect([out.Maximum, out.pages, out.bookmark]).toEqual(['Maximum', 'pages', 'bookmark']);
  });
});
