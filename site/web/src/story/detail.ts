/**
 * Layer 2, "הפרט": the detail page's behaviour (loaded by story.ts only on a detail page). The page is whole without it:
 * the option the story shows, its price, its picture and its close-up slot are in the HTML (tools/make-story.ts). This
 * adds the choice of option (the picker's rules in detail-model.ts), the price, the credit, the picture, the close-up
 * and the reason that follow it, the address that names it, and "הוספה לסל" into the story's test cart.
 */
import type { StoryCart } from './story-cart';
import { priceHe } from './story-cart';
import { choose, creditOf, fromQuery, photoOf, selection, storyNote, storySku, toQuery, whyOf, type DetailData, type DSku } from './detail-model';
import { availableValues } from '@hd/shared/picker';

type Ctx = {
  d: DetailData;
  cart: StoryCart;
  announce: (t: string) => void;
  mark: (name: string, detail?: unknown) => void;
  counted: () => void;
};

export function initDetail({ d, cart, announce, mark, counted }: Ctx): { current: () => DSku; choose: (key: string) => void } {
  const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T | null;
  const price = $('st-pd-price')!;
  const credit = $('st-pd-credit')!;
  const img = $<HTMLImageElement>('st-pd-img')!;
  const none = $('st-pd-none')!;
  const photoCap = $('st-pd-photo-cap')!;
  const media = $('st-pd-media')!;
  const cu = $<HTMLImageElement>('st-pd-cu')!;
  const cuEmpty = $('st-pd-cu-empty')!;
  const cuCap = $('st-pd-cu-cap')!;
  const add = $<HTMLButtonElement>('st-pd-add')!;
  const why = $('st-pd-why')!;
  const inCart = $('st-pd-in-cart')!;
  const note = $('st-pd-story-note')!;
  const noteText = $('st-pd-story-text')!;
  const size = document.querySelector<HTMLElement>('[data-spec="מידות"]');
  const days = document.querySelector<HTMLElement>('[data-spec="זמן אספקה"]');
  const pool = d.skus.map((k) => ({ variant_id: k.key, values: k.values, available: k.available }));
  let sku = fromQuery(d, location.search);
  let timer: ReturnType<typeof setTimeout> | undefined;

  const items = (n: number) => (n === 1 ? 'פריט אחד' : `${n} פריטים`);
  function showInCart(): void {
    const c = cart.current();
    inCart.hidden = !c?.count;
    inCart.textContent = c?.count ? `בסל: ${items(c.count)} · ${priceHe(c.subtotal_agorot)}` : '';
  }
  function setImage(el: HTMLImageElement, im: { src: string; srcset: string; w: number; h: number } | null, alt: string): void {
    el.hidden = !im;
    if (!im) {
      el.removeAttribute('src');
      el.removeAttribute('srcset');
      el.alt = '';
      return;
    }
    if (el.getAttribute('src') !== im.src) {
      el.srcset = im.srcset;
      el.src = im.src;
      el.width = im.w;
      el.height = im.h;
    }
    el.alt = alt;
  }
  function render(announceIt: boolean): void {
    const sel = selection(d, sku);
    d.axes.forEach((a, i) => {
      const ok = availableValues(d.axes, pool, sel, i);
      for (const r of document.querySelectorAll<HTMLInputElement>(`input[data-axis="${a.id}"]`)) {
        r.checked = r.value === sel[a.id];
        r.disabled = !ok.has(r.value);
        r.closest('label')?.classList.toggle('is-off', r.disabled);
      }
      const s = document.querySelector<HTMLSelectElement>(`select[data-axis="${a.id}"]`);
      if (s) {
        s.value = sel[a.id] ?? '';
        for (const o of s.options) o.disabled = !ok.has(o.value);
      }
      const cur = document.querySelector<HTMLElement>(`.st-pd-axis[data-axis="${a.id}"] .st-pd-current`);
      if (cur) cur.textContent = a.values.find((v) => v.id === sel[a.id])?.label_he ?? '';
    });
    price.textContent = sku.price_he ?? '';
    price.hidden = !sku.price_he;
    credit.textContent = creditOf(d, sku);
    const shown = photoOf(d, sku);
    setImage(img, shown.image, shown.alt);
    none.hidden = !!shown.image;
    photoCap.textContent = shown.caption;
    media.classList.toggle('has-closeup', !!sku.closeup);
    setImage(cu, sku.closeup, sku.closeup?.alt_he ?? '');
    cuEmpty.hidden = !!sku.closeup;
    cuCap.textContent = sku.closeup ? `תקריב בבית ה${d.style_he}. ${d.marks_he[sku.closeup.state] ?? ''}.` : `תקריב בבית ה${d.style_he}`;
    const w = whyOf(d, sku);
    add.hidden = !!w;
    why.hidden = !w;
    why.textContent = w;
    clearTimeout(timer);
    add.textContent = 'הוספה לסל';
    const n = storyNote(d, sku);
    note.hidden = !n;
    noteText.textContent = n ?? '';
    if (size) size.textContent = sku.size_he ? `${sku.size_he} (לפי הספק)` : '';
    if (days) days.textContent = sku.days ? `⁦${sku.days[0]}–${sku.days[1]}⁩ ימים במשלוח החסכוני (הערכה של הספק)` : '';
    history.replaceState(history.state, '', `${location.pathname}${toQuery(d, sku)}${location.hash}`);
    showInCart();
    mark('detail:sku', sku.key);
    if (announceIt) announce(`${sku.label_he ?? d.name_he}. ${creditOf(d, sku)}${w ? `. ${w}` : ''}`);
  }
  const pick = (index: number, value: string) => {
    sku = choose(d, sku, index, value);
    render(true);
  };
  d.axes.forEach((a, i) => {
    for (const r of document.querySelectorAll<HTMLInputElement>(`input[data-axis="${a.id}"]`))
      r.addEventListener('change', () => r.checked && pick(i, r.value));
    document
      .querySelector<HTMLSelectElement>(`select[data-axis="${a.id}"]`)
      ?.addEventListener('change', (e) => pick(i, (e.currentTarget as HTMLSelectElement).value));
  });
  $('st-pd-back')?.addEventListener('click', () => {
    sku = storySku(d);
    render(true);
    document.querySelector<HTMLElement>('#st-pd-options input:checked, #st-pd-options select')?.focus();
  });
  add.addEventListener('click', async () => {
    if (!sku.sellable || !sku.variant_id) return;
    try {
      const c = await cart.add(sku.variant_id);
      mark('cart:add', sku.variant_id);
      counted();
      showInCart();
      // the confirmation is in the button itself, 2.5 s, and said aloud; no toast (art direction §7.2)
      add.textContent = 'נוסף לסל';
      clearTimeout(timer);
      timer = setTimeout(() => (add.textContent = 'הוספה לסל'), 2500);
      announce(
        `נוסף לסל: ${d.name_he}${sku.key !== d.story_key && sku.label_he ? `, ${sku.label_he}` : ''}. בסל ${items(c.count)}, ${priceHe(c.subtotal_agorot)}.`,
      );
    } catch {
      announce('לא הצלחנו להוסיף לסל.');
    }
  });
  render(false);
  mark('detail:ready', sku.key);
  return {
    current: () => sku,
    choose: (key) => {
      sku = d.skus.find((k) => k.key === key) ?? sku;
      render(false);
    },
  };
}
