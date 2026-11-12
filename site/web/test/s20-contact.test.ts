/**
 * S20, QA ת61: the contact block (components/Contact.tsx) and the lines around it, rendered as the prerender does.
 * Without contact details (this repo's build, CONTACT1 open): no block, no "כתבו לנו". With them (a build whose
 * wrangler.jsonc names CONTACT_EMAIL and CONTACT_PHONE, mocked here): mailto and tel links under the lines.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { h } from 'preact';
import { renderToString } from 'preact-render-to-string';

const CONTACT = { email: 'shop@hd-test.co.il', phone: '03-1234567', phone_href: '+97231234567' };
const LINES: Record<string, string | null> = {
  'legal.draft': 'טיוטת עבודה. הנוסח לא נבדק משפטית ולא אומת. שם העסק והכתובת יושלמו לפני ההשקה.',
  'legal.returns_notice': 'להודעת ביטול: פנו אלינו באחת הדרכים שלמטה, וציינו את מספר ההזמנה.',
  'legal.accessibility_contact': 'נשמח לשמוע על כל קושי. פניות לרכז/ת הנגישות נענות תוך 5 ימי עסקים.',
  'privacy.processors': 'x',
  'privacy.marketing': 'y',
};

afterEach(() => {
  vi.doUnmock('../src/copy');
  vi.resetModules();
});

describe('S20 ת61: the contact block', () => {
  it('this build has no contact details: no block in the footer’s place, the cancellation or the accessibility page', async () => {
    const { ContactBlock } = await import('../src/components/Contact');
    const { Legal } = await import('../src/pages/Legal');
    expect(renderToString(h(ContactBlock, { title: 'יצירת קשר' }))).toBe('');
    for (const page of ['returns', 'accessibility'] as const) {
      const html = renderToString(h(Legal, { page }));
      expect(html).not.toMatch(/mailto:|tel:|כתבו לנו|פנו אלינו/);
      expect(html).toMatch(/יושלמו לפני ההשקה/);
    }
  });
  it('with contact details: the email as mailto, the phone as tel, in one block wherever it is placed', async () => {
    vi.doMock('../src/copy', () => ({ contact: CONTACT, copyHe: (k: string) => LINES[k] ?? null }));
    const { ContactBlock } = await import('../src/components/Contact');
    const { Legal } = await import('../src/pages/Legal');
    const block = renderToString(h(ContactBlock, { title: 'יצירת קשר' }));
    expect(block).toContain('<p class="contact-title">יצירת קשר</p>');
    expect(block).toContain('href="mailto:shop@hd-test.co.il" dir="ltr">shop@hd-test.co.il</a>');
    expect(block).toContain('href="tel:+97231234567" dir="ltr" class="num">03-1234567</a>');
    const returns = renderToString(h(Legal, { page: 'returns' }));
    expect(returns).toContain(LINES['legal.returns_notice']);
    expect(returns).toContain('mailto:shop@hd-test.co.il');
    expect(returns).not.toMatch(/פרטי הקשר יושלמו/);
    expect(renderToString(h(Legal, { page: 'accessibility' }))).toContain('tel:+97231234567');
  });
  it('an email without a phone: the email alone', async () => {
    vi.doMock('../src/copy', () => ({ contact: { ...CONTACT, phone: null, phone_href: null }, copyHe: () => null }));
    const { ContactBlock } = await import('../src/components/Contact');
    const html = renderToString(h(ContactBlock, {}));
    expect(html).toContain('mailto:');
    expect(html).not.toContain('tel:');
  });
});
