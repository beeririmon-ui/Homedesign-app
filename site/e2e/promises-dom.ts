/**
 * S18, widened in S20 (QA ת60): what a page says as a person meets it after hydration, and every promise in it
 * (tools/lib/promises.ts). Read: the rendered text, the text of hidden nodes too, every attribute of every element
 * (value, aria-roledescription, data-… included), and what a stylesheet draws (::before, ::after content).
 */
import type { Page } from '@playwright/test';
import { promiseFindings } from '../tools/lib/promises';

export async function pageTexts(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const out = [document.body.innerText, document.body.textContent ?? '', document.title];
    for (const el of Array.from(document.querySelectorAll('*'))) {
      for (const a of Array.from(el.attributes)) if (a.value.trim() && a.name !== 'class' && a.name !== 'style' && a.name !== 'd') out.push(a.value);
      for (const pseudo of ['::before', '::after']) {
        const c = getComputedStyle(el, pseudo).content;
        if (c && c !== 'none' && c !== 'normal' && c !== '""') out.push(c.replace(/^"|"$/g, ''));
      }
    }
    return out;
  });
}

export async function promisesOn(page: Page): Promise<string[]> {
  return (await pageTexts(page)).flatMap((t) => promiseFindings(t).map((f) => `${f.rule}: "${f.sentence}"`));
}
