import type { ComponentChildren } from 'preact';
import { useEffect, useRef } from 'preact/hooks';
import { cartCount } from '../state/cart';
import { announcement, cycleTheme, theme } from '../state/ui';
import { IconBag, IconHouse, IconTheme } from './Icons';
import type { Route } from '../router';

const THEME_LABEL = { system: 'ערכת צבע: לפי המכשיר', light: 'ערכת צבע: בהירה', dark: 'ערכת צבע: כהה' } as const;

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
          <a class="brand" href="/" aria-label="דף הבית">
            <IconHouse />
            <span>הבית</span>
          </a>
          <nav class="nav" aria-label="ראשי">
            <a href="/rooms/living-room/" aria-current={route.name === 'room' ? 'page' : undefined}>
              סלון
            </a>
            <a href="/cart/" aria-current={route.name === 'cart' ? 'page' : undefined} aria-label={`סל הקניות, ${count} פריטים`}>
              <IconBag />
              <span class="hide-sm" aria-hidden="true">
                סל
              </span>
              <span class="cart-count num" aria-hidden="true">
                {count}
              </span>
            </a>
            <button type="button" class="icon-btn" onClick={cycleTheme} aria-label={THEME_LABEL[theme.value]} title={THEME_LABEL[theme.value]}>
              <IconTheme />
            </button>
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
