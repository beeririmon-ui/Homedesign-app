/**
 * S22, QA ת69 and ה25: contact details that are samples, never the shop's. The public build (tools/build-copy.ts with
 * HD_PUBLIC=1) and the deploy check (api/scripts/check-config.ts, `production`) stop on any of them; behind the flag,
 * and in the other environments, they are a warning. The real value comes only from the owner (CONTACT1), and it is
 * never written in the repo: a value the repo's tests, fixtures or docs use is a sample by definition.
 *
 * A sample is:
 * - **reserved for examples** (RFC 2606, 6761): example.com/.net/.org and `example.*` in any TLD (example.co.il), and the
 *   TLDs .example, .test, .invalid, .localhost, .local;
 * - **our own test values** (`SAMPLE_EMAILS`, `SAMPLE_EMAIL_DOMAINS`, `SAMPLE_PHONES`): every address and phone the
 *   site's tests, fixtures and docs use, and the ones QA's tools set as the shop's contact. tools/test/s22.test.ts scans
 *   the site, the briefs and docs/ops, and fails on a value this module does not call a sample;
 * - **a common placeholder**: an address at domain.*, yourdomain.*, test.* and the like, or a placeholder name before the
 *   @ (test, email, name, user, john.doe…); a phone whose number after the prefix is one digit repeated (050-0000000),
 *   a run up or down (03-1234567, 052-7654321, 1-800-123-456, *1234), or starts with 555 (052-555-1234).
 *
 * This module is imported by the build and the deploy check only, never by the Worker or the web: its list does not ship.
 */

/** our own sample addresses, from the tests, fixtures, docs and QA's tools (lower case) */
export const SAMPLE_EMAILS: readonly string[] = ['shop@hd-test.co.il', 'shop@hd-qa.co.il', 'info@hd-qa.co.il', 'shop@hd.co.il', 'a@b.co'];
/** our own test domains: any address there is a sample */
export const SAMPLE_EMAIL_DOMAINS: readonly string[] = ['hd-test.co.il', 'hd-qa.co.il'];
/**
 * our own sample phones that no pattern below catches, as national digits (+972 read as 0): the shop phone of QA S20's
 * contact gate, and the customers' phones of the site's and QA's tests.
 */
export const SAMPLE_PHONES: readonly string[] = [
  '048123456',
  '0547716203',
  '0547716204',
  '0547716207',
  '0547716209',
  '0547716219',
  '0529137264',
  '0546173829',
  '0501818182',
];

/** the name of the domain (its label before the public suffix) that only a template or a test would use */
const DUMMY_DOMAIN_NAMES = new Set([
  'domain',
  'yourdomain',
  'your-domain',
  'mydomain',
  'my-domain',
  'yoursite',
  'your-site',
  'yourwebsite',
  'yourcompany',
  'your-company',
  'yourshop',
  'yourstore',
  'yourbrand',
  'test',
  'testing',
  'sample',
  'dummy',
  'fake',
  'placeholder',
  'example',
]);
/** the name before the @ that only a template or a test would use */
const DUMMY_LOCALS = new Set([
  'test',
  'testing',
  'tester',
  'example',
  'sample',
  'dummy',
  'fake',
  'email',
  'youremail',
  'your.email',
  'your-email',
  'yourname',
  'your.name',
  'name',
  'firstname.lastname',
  'first.last',
  'john.doe',
  'jane.doe',
  'johndoe',
  'janedoe',
  'foo',
  'bar',
  'foo.bar',
  'user',
  'username',
  'someone',
  'somebody',
  'nobody',
  'noreply',
  'no-reply',
  'donotreply',
]);
const RESERVED_TLD = /\.(?:example|test|invalid|localhost|local)$/;
const EXAMPLE_ANY_TLD = /(?:^|\.)example\.[a-z]{2,}(?:\.[a-z]{2,})?$/;
/** second-level labels of a two-part public suffix (co.il, org.il, com.au…) */
const SLD = new Set(['co', 'org', 'net', 'ac', 'gov', 'muni', 'k12', 'idf', 'com', 'edu']);

/** Why an email address is a sample, or null. */
export function sampleEmailReason(email: string): string | null {
  const e = email.trim().toLowerCase();
  const at = e.lastIndexOf('@');
  if (at < 1) return null;
  const local = e.slice(0, at);
  const domain = e.slice(at + 1);
  if (SAMPLE_EMAILS.includes(e)) return 'an address the repo’s tests or docs use';
  if (SAMPLE_EMAIL_DOMAINS.some((d) => domain === d || domain.endsWith(`.${d}`))) return 'a test domain of ours';
  if (RESERVED_TLD.test(domain) || EXAMPLE_ANY_TLD.test(domain)) return 'reserved for examples (RFC 2606)';
  const labels = domain.split('.');
  const suffix = labels.length >= 3 && SLD.has(labels[labels.length - 2]!) ? 2 : 1;
  const name = labels[labels.length - suffix - 1];
  if (name && DUMMY_DOMAIN_NAMES.has(name)) return `a template’s domain (${name}.…)`;
  if (DUMMY_LOCALS.has(local)) return `a template’s name before the @ (${local}@)`;
  return null;
}

/** a phone as national digits: +972 read as 0, spaces and dashes out; a star number keeps its star */
export function nationalDigits(phone: string): string {
  const s = phone.trim();
  if (/^\*\d+$/.test(s)) return s;
  let d = s.replace(/[^\d+]/g, '');
  if (d.startsWith('+972')) d = `0${d.slice(4)}`;
  else if (d.startsWith('972') && d.length >= 11) d = `0${d.slice(3)}`;
  return d.replace(/\+/g, '');
}

const run = (digits: string, step: 1 | -1): boolean => [...digits].every((c, i) => i === 0 || Number(c) === (Number(digits[i - 1]) + step + 10) % 10);

/** Why a phone is a sample, or null. */
export function samplePhoneReason(phone: string): string | null {
  const d = nationalDigits(phone);
  if (SAMPLE_PHONES.includes(d)) return 'a phone the repo’s tests use';
  // the number after its prefix: a star number's four digits, 1-800's six, a landline's or a mobile's last seven
  const sub = d.startsWith('*') ? d.slice(1) : /^1[5-9]00/.test(d) ? d.slice(4) : d.length >= 9 ? d.slice(-7) : '';
  if (sub.length < 4) return null;
  if (/^(\d)\1+$/.test(sub)) return 'one digit repeated';
  if (run(sub, 1) || run(sub, -1)) return 'a run of digits (1234567)';
  if (sub.startsWith('555')) return 'a 555 number';
  return null;
}

/**
 * What is a sample in an environment's contact variables: one line per sample value, or none. Only set values are
 * read (UNDECIDED and a malformed value are @hd/shared/contact's).
 */
export function contactSampleIssues(vars: Record<string, unknown>): string[] {
  const out: string[] = [];
  const email = vars.CONTACT_EMAIL;
  const phone = vars.CONTACT_PHONE;
  if (typeof email === 'string' && email.includes('@')) {
    const why = sampleEmailReason(email);
    if (why) out.push(`CONTACT_EMAIL=${email.trim()} is a sample address (${why}), not the shop's: the real one comes from the owner (CONTACT1)`);
  }
  if (typeof phone === 'string' && /\d/.test(phone)) {
    const why = samplePhoneReason(phone);
    if (why) out.push(`CONTACT_PHONE=${phone.trim()} is a sample number (${why}), not the shop's: the real one comes from the owner (CONTACT1)`);
  }
  return out;
}
