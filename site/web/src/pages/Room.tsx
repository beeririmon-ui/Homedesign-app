import { productPath } from '@hd/shared/product-url';
import { useEffect, useState } from 'preact/hooks';
import type { CatalogRoom } from '@hd/shared';
import { product } from '../catalog';
import { RoomExperience } from '../components/RoomExperience';
import { optionImage, Price } from '../components/Media';
import { pendingOpen, selection } from '../state/room';

export function Room({ room, slot, option }: { room: CatalogRoom; slot?: string; option?: number }) {
  useEffect(() => {
    if (slot) pendingOpen.value = { slot, option: option ?? selection.value[slot] ?? 1 };
  }, [slot, option]);
  // S3: entered from a story page (?from=/story/…/), the way back to it; read after the first paint (prerendered HTML)
  const [from, setFrom] = useState<string | null>(null);
  useEffect(() => {
    const f = new URLSearchParams(location.search).get('from');
    setFrom(f && /^\/story\/[a-z0-9/-]+\/$/.test(f) ? f : null);
  }, []);

  return (
    <>
      {/* S5: the way back to the story sits on the stage (it was below it in S3) */}
      <RoomExperience room={room} backTo={from} />
      <section class="wrap page" aria-labelledby="items-title">
        <div class="room-intro">
          <h2 id="items-title">מה יש בחדר</h2>
          <p class="muted">
            כל פריט בחדר הוא מוצר שאפשר לקנות. לכל פריט שלוש גרסאות: געו בנקודה על התמונה, או בחרו מהרשימה. המילוי (ענפים, נרות, עיתונים ועץ הזית) מראה איך
            משתמשים במוצר ולא נמכר.
          </p>
        </div>
        <ul class="slot-list">
          {room.slots.map((s) => {
            const pos = selection.value[s.id] ?? 1;
            const opt = s.options[pos - 1];
            const p = product(opt?.product_id);
            const img = optionImage(s.id, pos);
            return (
              <li key={s.id} class="card slot-item">
                {img ? <img class="thumb" src={img} alt="" loading="lazy" width={64} height={64} /> : <span class="thumb" aria-hidden="true" />}
                <div class="meta">
                  <strong>{s.name_he}</strong>
                  <span class="small">{p ? <a href={productPath(p.id)}>{p.name_he}</a> : <span class="muted">וריאציה {pos} · ממתינה למוצר</span>}</span>
                  <span class="row">
                    {p ? <Price agorot={p.price_agorot} provisional={p.price_provisional} /> : null}
                    {s.on_hold || (p && p.availability.status !== 'available') ? <span class="small muted">המלאי אינו זמין כעת</span> : null}
                    <a class="link-btn" href={`/rooms/${room.id}/?slot=${s.id}`}>
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
      </section>
    </>
  );
}
