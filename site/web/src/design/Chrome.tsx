/**
 * FB13: what each design direction adds to the tour beyond its stylesheet. All of it is decoration (aria-hidden): the
 * page's own headings, buttons and lists still say everything, so a screen reader hears the same tour in every
 * direction. Every number on it is the tour's own data (the rooms, the products the owner's line counts, the frame's
 * camera); nothing is invented. Rendered only when a direction is chosen (design.ts), after the first paint.
 */
import type { Design } from './design';

export type At = 'entry' | 'living' | 'kitchen' | 'work' | 'bed' | 'bath' | 'boy' | 'girl';
export type ChromeData = {
  d: Design;
  phase: 'door' | 'entering' | 'room';
  /** the stop the visitor is at: 0 the door, then the rooms in the panel's order */
  stop: number;
  stops: number;
  roomHe: string;
  houseHe: string;
  /** the frame's camera (house plan) and its height in metres */
  frame: string;
  camH: number | null;
  /** the marks on the picture now, the room's products for sale (the owner's line), and the house's */
  items: number;
  sale: number;
  total: number;
  /** the close-up: the product's place among the marks, and its name */
  open: { n: number; of: number; name: string } | null;
};

export const two = (n: number): string => String(n).padStart(2, '0');

/** on the picture: the cover (a), the instrument's frame (b), the screening's fade (c) */
export function WinChrome({ c, replay }: { c: ChromeData; replay: string }) {
  if (c.d === 'a')
    return (
      <div class="dz-win" aria-hidden="true">
        <div class="dz-cover">
          <span class="dz-mast">הבית</span>
          <span class="dz-issue">גיליון 01 · {c.houseHe}</span>
          <span class="dz-lines">
            סיור ב-{c.stops - 1} חדרים
            <br />
            {c.total} מוצרים לבית
          </span>
        </div>
      </div>
    );
  if (c.d === 'b')
    return (
      <div class="dz-win" aria-hidden="true">
        <i class="dz-br" data-k="1" />
        <i class="dz-br" data-k="2" />
        <i class="dz-br" data-k="3" />
        <i class="dz-br" data-k="4" />
        <span class="dz-scan" key={`scan-${replay}`} />
        <span class="dz-tick" dir="ltr">
          <span>{c.frame}</span>
          {c.camH ? <span>h {c.camH.toFixed(2)} m</span> : null}
          <span>16:9</span>
        </span>
      </div>
    );
  return (
    <div class="dz-win" aria-hidden="true">
      <span class="dz-fade" key={`fade-${replay}`} />
      <div class="dz-card">
        <span class="dz-chap">פרק {two(c.stop)}</span>
        <span class="dz-ttl">{c.phase === 'door' ? c.houseHe : c.roomHe}</span>
      </div>
    </div>
  );
}

/** in the bands round the picture: the folio (a), the instrument's readout (b), the chapter (c) */
export function BandChrome({ c }: { c: ChromeData }) {
  const where = c.phase === 'door' ? 'שער' : `עמ׳ ${two(c.stop)}`;
  if (c.d === 'a')
    return (
      <>
        <div class="dz-folio" aria-hidden="true">
          <span class="dz-f1">גיליון 01 — {c.houseHe}</span>
          <span class="dz-rule" />
          <span class="dz-f2">
            {c.open ? `פריט ${two(c.open.n)} מתוך ${two(c.open.of)}` : where} <span class="dz-of">/ {two(c.stops - 1)}</span>
          </span>
        </div>
        <span class="dz-num" aria-hidden="true">
          {two(c.stop)}
        </span>
      </>
    );
  if (c.d === 'b')
    return (
      <>
        <span class="dz-idx" aria-hidden="true" dir="ltr">
          {two(c.stop)}
          <span>/{two(c.stops - 1)}</span>
        </span>
        <span class="dz-read" aria-hidden="true">
          {c.open ? (
            <>
              <b>נבחר</b> <span dir="ltr">{two(c.open.n)}/{two(c.open.of)}</span> · {c.open.name}
            </>
          ) : c.phase === 'door' ? (
            <>
              <span dir="ltr">{two(c.stops - 1)}</span> חדרים · <span dir="ltr">{c.total}</span> מוצרים · <span dir="ltr">170</span> מ״ר
            </>
          ) : (
            <>
              <span dir="ltr">{c.items}</span> סימנים · <span dir="ltr">{c.sale}</span> למכירה
            </>
          )}
        </span>
      </>
    );
  return (
    <>
      <span class="dz-chap-b" aria-hidden="true">
        {c.open ? `${two(c.open.n)} / ${two(c.open.of)}` : `פרק ${two(c.stop)}`}
      </span>
      <span class="dz-meta" aria-hidden="true">
        {c.phase === 'door' ? (
          <>
            {c.stops - 1} חדרים · {c.total} מוצרים
          </>
        ) : (
          <>{c.houseHe}</>
        )}
      </span>
    </>
  );
}

/** b: the house's plan in the rooms panel, the room the visitor is in lit (the same plan as the folded control's icon) */
const PLAN: [At, number, number, number, number, string][] = [
  ['living', 2, 2, 8, 5, 'סלון'],
  ['kitchen', 10, 2, 8, 5, 'מטבח'],
  ['work', 2, 7, 5, 3, 'עבודה'],
  ['entry', 7, 7, 5, 3, 'כניסה'],
  ['boy', 2, 10, 6.5, 2.75, 'ילד'],
  ['bath', 11, 10, 7, 2.75, 'רחצה'],
  ['girl', 2, 12.75, 6.5, 2.75, 'ילדה'],
  ['bed', 2, 15.5, 9, 2.5, 'שינה'],
];
export function PlanBig({ at }: { at: At }) {
  return (
    <div class="dz-plan" aria-hidden="true">
      <svg viewBox="1 1 18 17.5" focusable="false">
        <path class="dz-grid" d="M1 4h18M1 7h18M1 10h18M1 13h18M1 16h18M4 1v17.5M7 1v17.5M10 1v17.5M13 1v17.5M16 1v17.5" />
        {PLAN.map(([k, x, y, w, h, he]) => (
          <g key={k} data-on={k === at ? '' : undefined}>
            <rect x={x} y={y} width={w} height={h} />
            <text x={x + w / 2} y={y + h / 2}>
              {he}
            </text>
          </g>
        ))}
      </svg>
      <span class="dz-plan-k">תוכנית הבית · סכמה</span>
    </div>
  );
}
