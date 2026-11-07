import type { ComponentChildren } from 'preact';
import { useEffect, useRef } from 'preact/hooks';
import { cartCount } from '../state/cart';
import { announcement } from '../state/ui';
import type { Route } from '../router';

export function Layout({ route, children }: { route: Route; children: ComponentChildren }) {
  const first = useRef(true);
  const key = JSON.stringify(route);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    // route change: move focus to the new page heading (screen readers announce it)
    const h = document.querySelector<HTMLElement>('#main h1');
    (h ?? document.getElementById('main'))?.focus({ preventScroll: true });
  }, [key]);

  const count = cartCount.value;
  return (
    <>
      <a class="skip-link" href="#main">
        דילוג לתוכן
      </a>
      <header class="site-header">
        <div class="wrap">
          {/* §6.2: the wordmark's place, words only ("הבית" until a name is chosen, ART5) */}
          <a class="brand" href="/" aria-label="דף הבית">
            הבית
          </a>
          <nav class="nav" aria-label="ראשי">
            <a href="/rooms/living-room/" aria-current={route.name === 'room' ? 'page' : undefined}>
              סלון
            </a>
            <a href="/cart/" aria-current={route.name === 'cart' ? 'page' : undefined} aria-label={`סל הקניות, ${count} פריטים`}>
              <span aria-hidden="true">
                סל (<span class="cart-count num">{count}</span>)
              </span>
            </a>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
      <footer class="site-footer">
        <div class="wrap">
          <nav aria-label="מידע">
            <a href="/accessibility/">הצהרת נגישות</a>
            <a href="/terms/">תקנון</a>
            <a href="/returns/">ביטולים והחזרות</a>
            <a href="/privacy/">פרטיות</a>
          </nav>
          <p>אתר בהקמה: התמונות, השמות והמחירים זמניים. שם המותג טרם נבחר.</p>
        </div>
      </footer>
      <div class="live-region" aria-live="polite" aria-atomic="true">
        {announcement.value ? (
          <div class="toast" key={announcement.value.id}>
            {announcement.value.text}
          </div>
        ) : null}
      </div>
    </>
  );
}
