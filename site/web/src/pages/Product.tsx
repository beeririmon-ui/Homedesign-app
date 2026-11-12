import { shopPath } from '@hd/shared/product-url';
import { useEffect, useRef, useState } from 'preact/hooks';
import type { Pack, PublicProduct } from '@hd/shared';
import { packLabelHe } from '@hd/shared/packs';
import { catalog, product, slotOf } from '../catalog';
import { Price, galleryImages, optionImage } from '../components/Media';
import { ProductGallery } from '../components/ProductGallery';
import { addToCart, cartBusy, justAdded } from '../state/cart';
import { navigate } from '../router';
import { pendingOpen } from '../state/room';
import { PackPicker } from '../components/PackPicker';
import { SafetyRow } from '../components/SafetyRow';
import { OptionPicker } from '../components/OptionPicker';
import { Waitlist } from '../components/Waitlist';
import { defaultVariantId, variantPackPrice, variantView } from '../variants';
import { knownValues, visibleNotes } from './productNotes';

const WALK = ['hall', 'living-room', 'dining-room', 'work', 'corridor', 'boy', 'girl', 'bath', 'master'];

export function Product({ p }: { p: PublicProduct }) {
  const [qty, setQty] = useState(1);
  // P1: the set is the default; a single piece is the other choice (only for products sold as a set)
  const [pack, setPack] = useState<Pack>('set');
  // supplier options (2026-10-11): the room's option first; the customer may choose any other
  const [variantId, setVariantId] = useState(() => defaultVariantId(p));
  useEffect(() => {
    setVariantId(defaultVariantId(p));
  }, [p.id]);
  const v = variantView(p, variantId) ?? variantView(p)!;
  const price = variantPackPrice(v, pack);
  const estimated = pack === 'unit' && v.unit_price_estimated;
  const where = slotOf(p)!;
  const images = galleryImages(p, v.variant_id);
  // S17 (QA ה5): a field whose value is unknown is not shown; a note about the picture only beside a picture
  const materials = knownValues(p.materials_he);
  const notes = visibleNotes(p.notes_he, images.length > 0);
  const dims = [p.dimensions_cm.width, p.dimensions_cm.depth, p.dimensions_cm.height].filter((x): x is number => typeof x === 'number');
  // §9.1, the phone: the paper band with "הוספה לסל" appears once the page's own button has left the screen
  const buy = useRef<HTMLDivElement>(null);
  const [barOn, setBarOn] = useState(false);
  useEffect(() => {
    const el = buy.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;
    const io = new IntersectionObserver(([e]) => setBarOn(!!e && !e.isIntersecting && e.boundingClientRect.top < 0));
    io.observe(el);
    return () => io.disconnect();
  }, [p.id]);
  // the room's number in the walk through the house (art direction §6.3: 01 the entrance, 02 the living room, …)
  const roomN = String(WALK.indexOf(where.room.id) + 1 || catalog.rooms.findIndex((r) => r.id === where.room.id) + 1).padStart(2, '0');
  const added = justAdded.value === `${v.variant_id}:${pack}`;
  const add = () =>
    void addToCart(
      v.variant_id,
      p.name_he,
      qty,
      pack,
      [v.option_he, p.pack ? packLabelHe(pack, p.pack.set_qty) : null].filter(Boolean).join(', ') || undefined,
    );
  const showInRoom = () => {
    pendingOpen.value = { slot: where.slot.id, option: where.option.position };
    navigate(`/rooms/${where.room.id}/`);
  };
  return (
    <div class="wrap page">
      <nav class="crumbs" aria-label="פירורי לחם">
        <ol>
          <li>
            <a href="/">בית</a>
          </li>
          <li>
            <a href={`/rooms/${where.room.id}/`}>{where.room.name_he}</a>
          </li>
          <li aria-current="page">{where.slot.name_he}</li>
        </ol>
      </nav>
      <article class="product" aria-labelledby="product-title">
        {/* S15: a product with no picture that may ship (no render, and a supplier photo the public build withholds for
            its rights) shows a neutral tile, never an empty column */}
        <div class="product-media">
          {images.length ? <ProductGallery images={images} id={`p-${p.id}`} /> : <div class="product-noimg" aria-hidden="true" />}
        </div>
        <div class="product-info">
          <div class="page-head" style={{ marginBottom: 0 }}>
            {/* §9.1: the running head, "02 · הסלון · אגרטל"; the temporary names are said once, in the footer (§6.6) */}
            <p class="run-head">
              <span class="num">{roomN}</span> · {where.room.name_he} · {where.slot.name_he}
            </p>
            <h1 id="product-title" tabIndex={-1}>
              {p.name_he}
            </h1>
          </div>
          <div class="price-row" aria-live="polite">
            <Price class="price-big" agorot={price} provisional={v.price_provisional && !estimated} />
            {estimated ? <span class="small">מחיר משוער</span> : null}
            {p.pack ? <span class="small">{packLabelHe(pack, p.pack.set_qty)}</span> : null}
            {p.compare_at_agorot && pack === 'set' && v.in_room ? (
              <span class="price-old">
                <span class="sr-only">מחיר קודם: </span>
                <Price agorot={p.compare_at_agorot} />
              </span>
            ) : null}
            <span class="small muted">כולל מע״מ</span>
          </div>
          <p class="lede">{p.description_he}</p>
          <OptionPicker p={p} value={v.variant_id} onChange={setVariantId} id={`opt-${p.id}`} />
          <PackPicker
            p={p}
            value={pack}
            onChange={setPack}
            id={`pack-${p.id}`}
            prices={{ set: v.price_agorot, unit: v.unit_price_agorot, unitEstimated: v.unit_price_estimated }}
          />
          {/* §9.1: the other variations of this place in the room, as small credits with their studio picture */}
          <section class="slot-more" aria-labelledby={`more-${p.id}`}>
            <h2 id={`more-${p.id}`}>עוד בעמדה הזו</h2>
            <ol>
              {where.slot.options.map((o) => {
                const op = product(o.product_id);
                const img = optionImage(where.slot.id, o.position);
                return (
                  <li key={o.position}>
                    {img ? <img class="thumb" src={img} alt="" width={64} height={80} loading="lazy" /> : <span class="thumb" aria-hidden="true" />}
                    {op ? (
                      <span>
                        {op.id === p.id ? (
                          <span class="title" aria-current="true">
                            {op.name_he}
                          </span>
                        ) : (
                          <a href={shopPath(op.id)}>{op.name_he}</a>
                        )}
                        <span class="detail">
                          {[knownValues(op.materials_he)[0], op.id === p.id ? 'הדף הזה' : null].filter(Boolean).join(' · ')} ·{' '}
                          <Price agorot={op.price_agorot} />
                        </span>
                      </span>
                    ) : (
                      <span class="detail">גרסה {o.position}: ממתינה למוצר</span>
                    )}
                  </li>
                );
              })}
            </ol>
          </section>
          <dl class="specs-list">
            {materials.length ? (
              <>
                <dt>חומרים</dt>
                <dd>{materials.join(', ')}</dd>
              </>
            ) : null}
            {dims.length ? (
              <>
                <dt>מידות</dt>
                <dd>
                  {dims.join(' × ')} ס"מ (לפי הספק{v.in_room ? '' : ', של האפשרות שבחדר'})
                </dd>
              </>
            ) : null}
            {v.shipping_days ? (
              <>
                <dt>זמן אספקה</dt>
                <dd>
                  {v.shipping_days[0]}–{v.shipping_days[1]} ימים במשלוח החסכוני (הערכה של הספק)
                </dd>
              </>
            ) : null}
            <SafetyRow safety={p.safety} />
          </dl>
          {notes.length ? (
            <ul class="notes-list">
              {notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          ) : null}
          {p.availability.status !== 'available' ? (
            // PRE1 (NL2, AU2, R6Q2): no cart button; the reason in the customer's words and the waiting list
            <div class="buy-row">
              <Waitlist product_id={p.id} id={`wl-${p.id}`} />
              <button type="button" class="btn btn-ghost" onClick={showInRoom}>
                הצגה בחדר
              </button>
            </div>
          ) : (
            <div class="buy-row" ref={buy}>
              <div class="qty" role="group" aria-label="כמות">
                <button type="button" onClick={() => setQty(Math.min(20, qty + 1))} aria-label="הגדלת הכמות">
                  +
                </button>
                <output aria-live="polite" aria-label={`כמות: ${qty}`}>
                  {qty}
                </output>
                <button type="button" onClick={() => setQty(Math.max(1, qty - 1))} aria-label="הקטנת הכמות" disabled={qty === 1}>
                  −
                </button>
              </div>
              <button type="button" class="btn btn-primary" disabled={cartBusy.value || !v.available} onClick={add}>
                {!v.available ? 'אזל אצל הספק' : added ? 'נוסף לסל' : 'הוספה לסל'}
              </button>
              <button type="button" class="btn btn-ghost" onClick={showInRoom}>
                הצגה בחדר
              </button>
            </div>
          )}
          <p class="small muted">
            ביטול עסקה והחזרות לפי חוק הגנת הצרכן. <a href="/returns/">פרטים</a>
          </p>
        </div>
      </article>
      {p.availability.status === 'available' && v.available ? (
        <div class="buy-bar" hidden={!barOn}>
          <Price class="price-big" agorot={price} />
          <button type="button" class="btn btn-primary" disabled={cartBusy.value} onClick={add} tabIndex={barOn ? 0 : -1}>
            {added ? 'נוסף לסל' : 'הוספה לסל'}
          </button>
        </div>
      ) : null}
    </div>
  );
}
