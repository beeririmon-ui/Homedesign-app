import { useEffect } from 'preact/hooks';
import { catalog, livingRoom, scene } from '../catalog';
import { Picture } from '../components/Media';
import { go, preload } from '../components/Transition';

export function Home() {
  // the only transition reachable from the hall frame today: into the living room
  useEffect(() => {
    const id = setTimeout(() => preload('T-E0'), 1200);
    return () => clearTimeout(id);
  }, []);
  const built = catalog.rooms.filter((r) => r.built);
  const soon = catalog.rooms.filter((r) => !r.built);
  return (
    <>
      <section class="hero" aria-labelledby="home-title">
        <Picture src={scene.hall.src} widths={scene.hall.widths} sizes="100vw" alt="" loading="eager" fetchpriority="high" />
        <div class="veil" aria-hidden="true" />
        <div class="content">
          <p class="eyebrow">חלל הכניסה · {scene.hall.temporary ? 'תמונה זמנית' : 'נורדי'}</p>
          <h1 id="home-title" tabIndex={-1}>
            בית אחד. כל פריט בו אפשר לקנות.
          </h1>
          <p>היכנסו לסלון, געו בכל פריט ובחרו את הגרסה שמתאימה לכם. החדר מתעדכן מולכם.</p>
          <a
            class="btn btn-primary"
            href={`/rooms/${livingRoom.id}/`}
            onClick={(e) => {
              e.preventDefault();
              go('T-E0', `/rooms/${livingRoom.id}/`);
            }}
          >
            היכנסו לסלון
          </a>
        </div>
      </section>
      <section class="wrap page" aria-labelledby="rooms-title">
        <div class="page-head">
          <h2 id="rooms-title">החדרים בבית</h2>
          <p class="muted">מתחילים בסלון הנורדי. שאר החדרים נבנים לפי הסדר, אחרי שהסלון מושלם.</p>
        </div>
        <ul class="slot-list">
          {built.map((r) => (
            <li key={r.id} class="card slot-item" style={{ gridTemplateColumns: '1fr' }}>
              <div class="meta">
                <a href={`/rooms/${r.id}/`}>
                  <strong>{r.name_he}</strong>
                </a>
                <span class="small muted">{r.slots.length} פריטים לבחירה, 3 וריאציות בכל אחד</span>
              </div>
            </li>
          ))}
          {soon.map((r) => (
            <li key={r.id} class="card slot-item" style={{ gridTemplateColumns: '1fr' }}>
              <div class="meta">
                <strong>{r.name_he}</strong>
                <span class="small muted">בקרוב</span>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </>
  );
}
