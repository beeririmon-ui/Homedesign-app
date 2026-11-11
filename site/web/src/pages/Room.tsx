import { shopPath } from '@hd/shared/product-url';
import { useEffect, useRef, useState } from 'preact/hooks';
import type { CatalogRoom } from '@hd/shared';
import { RoomExperience } from '../components/RoomExperience';
import { optionImage, Price } from '../components/Media';
import { pendingOpen, selectHouse, selection } from '../state/room';
import { HOUSES, loadHouse, nordic, type House } from '../house';

export function Room({ room: nordicRoom, slot, option, style }: { room: CatalogRoom; slot?: string; option?: number; style?: string }) {
  // S10: the house the address names (DIR2), once its chunk is here; the first render is the prerendered Nordic one
  const [house, setHouse] = useState<House>(nordic);
  const want = style && HOUSES.some((h) => h.style === style) ? style : nordic.style;
  // S10 question 7 (S11): an address naming another house starts waiting for it, from the first (prerendered) render,
  // so its page never carries the Nordic poster (the Worker serves that house's own prerendered page)
  const [pending, setPending] = useState(want !== nordic.style);
  // entering at a house's address, the stage waits for the house; a switch on the stage dissolves instead
  const entry = useRef(true);
  useEffect(() => {
    let live = true;
    if (entry.current && want !== house.style) setPending(true);
    entry.current = false;
    void loadHouse(want).then((h) => {
      if (!live) return;
      setHouse(h ?? nordic);
      setPending(false);
    });
    return () => {
      live = false;
    };
  }, [want]);
  selectHouse(house.style, house.room);
  const room = house.style === nordic.style ? nordicRoom : house.room;
  const product = house.product;
  useEffect(() => {
    if (slot && house.style === want) pendingOpen.value = { slot, option: option ?? selection.value[slot] ?? 1 };
  }, [slot, option, house]);
  // S3: entered from a story page (?from=/story/…/), the way back to it; read after the first paint (prerendered HTML)
  const [from, setFrom] = useState<string | null>(null);
  useEffect(() => {
    const f = new URLSearchParams(location.search).get('from');
    // a story page, or the story's index (QA S6–S7 ת14: the contents' "עצב בעצמך" carries from=/story/); a path only
    setFrom(f && /^\/story\/(?:[a-z0-9-]+\/)*$/.test(f) ? f : null);
  }, []);

  return (
    <>
      {/* S5: the way back to the story sits on the stage (it was below it in S3) */}
      <RoomExperience house={house} room={room} backTo={from} pending={pending} />
      <section class="wrap page" aria-labelledby="items-title">
        <div class="room-intro">
          <h2 id="items-title">מה יש בחדר</h2>
          {/* S12, QA ת23: a page waiting for its house lists nothing yet: never the Nordic room's pictures (the browser's
              lazy loading fetches them well below the fold) */}
          {pending ? null : (
            <p class="muted">
              {house.intro_he ??
                'כל פריט בחדר הוא מוצר שאפשר לקנות. לכל פריט שלוש גרסאות: געו בנקודה על התמונה, או בחרו מהרשימה. המילוי (ענפים, נרות, עיתונים ועץ הזית) מראה איך משתמשים במוצר ולא נמכר.'}
            </p>
          )}
        </div>
        {pending ? null : (
          <ul class="slot-list">
            {room.slots.map((s) => {
              const pos = selection.value[s.id] ?? 1;
              const opt = s.options[pos - 1];
              const p = product(opt?.product_id);
              const img = house.thumb ? house.thumb(pos) : optionImage(s.id, pos);
              return (
                <li key={s.id} class="card slot-item">
                  {img ? <img class="thumb" src={img} alt="" loading="lazy" width={64} height={64} /> : <span class="thumb" aria-hidden="true" />}
                  <div class="meta">
                    <strong>{s.name_he}</strong>
                    <span class="small">
                      {p ? (
                        <a href={shopPath(p.id)}>{p.name_he}</a>
                      ) : (
                        <span class="muted">{opt && !opt.placeholder ? opt.label_he : `וריאציה ${pos} · ממתינה למוצר`}</span>
                      )}
                    </span>
                    <span class="row">
                      {p ? <Price agorot={p.price_agorot} provisional={p.price_provisional} /> : null}
                      {s.on_hold || (p && p.availability.status !== 'available') ? <span class="small muted">המלאי אינו זמין כעת</span> : null}
                      <a class="link-btn" href={`/rooms/${room.id}/?${house === nordic ? '' : `style=${house.style}&`}slot=${s.id}`}>
                        החלפה
                        <span class="sr-only">
                          {' '}
                          של {s.name_he} ({s.options.length} וריאציות)
                        </span>
                      </a>
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </>
  );
}
