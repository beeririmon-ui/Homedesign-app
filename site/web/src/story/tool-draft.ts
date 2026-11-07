/**
 * S3: the house's own tool, a draft (/story/<room>/<style>/tool/; DIR2). The page shows the house's layers at the
 * tool's camera, stacked as the skeleton orders them (the shadow multiplies), and the soft switch between two houses:
 * the same camera and the same slots, another architecture, every layer in the same frame, about a second (skeleton
 * spec, "החלפת סגנון"; DIR2: a soft transition in the tool, a cut in the story). The address names the house shown.
 */
type Ctx = { announce: (t: string) => void; mark: (n: string, d?: unknown) => void };

export function initToolDraft({ announce, mark }: Ctx): void {
  const stage = document.getElementById('td-stage');
  if (!stage) return;
  const houses = [...stage.querySelectorAll<HTMLElement>('.st-td-house')];
  // the switch sits on the paper under the stage (design notes §8)
  const buttons = [...document.querySelectorAll<HTMLButtonElement>('.st-td-btn')];
  const show = (id: string, say: boolean) => {
    const to = houses.find((h) => h.dataset.house === id);
    if (!to) return;
    mark('tool:switch:start', id);
    for (const h of houses) {
      const on = h === to;
      h.classList.toggle('is-on', on);
      h.setAttribute('aria-hidden', String(!on));
      // the incoming house's layers load now (lazy until shown)
      if (on) for (const img of h.querySelectorAll('img')) img.loading = 'eager';
    }
    for (const b of buttons) b.setAttribute('aria-pressed', String(b.dataset.house === id));
    to.addEventListener('transitionend', () => mark('tool:switch:end', id), { once: true });
    const q = new URLSearchParams(location.search);
    if (id === houses[0]!.dataset.house) q.delete('house');
    else q.set('house', id);
    history.replaceState(history.state, '', `${location.pathname}${q.size ? `?${q.toString()}` : ''}`);
    if (say) announce(`${buttons.find((b) => b.dataset.house === id)?.textContent ?? ''}: ${to.getAttribute('aria-label') ?? ''}`);
  };
  for (const b of buttons) b.addEventListener('click', () => show(b.dataset.house!, true));
  const asked = new URLSearchParams(location.search).get('house');
  if (asked && asked !== houses[0]!.dataset.house) show(asked, false);
  mark('tool:ready');
}
