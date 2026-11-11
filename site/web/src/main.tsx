import './styles/fonts.css';
import './styles/tokens.css';
import './styles/base.css';
import './styles/room.css';
import './styles/wheel.css';
import './styles/pages.css';
import './styles/shop.css';
import { hydrate, render } from 'preact';
import { App } from './App';
import { initRouter, match, onLinkClick, path } from './router';
import { loadCart } from './state/cart';
import { preloadRoute } from './pages/lazy';

// The artifact has no <html> tag of its own: set language and direction here (the site's index.html has them too).
document.documentElement.lang = 'he';
document.documentElement.dir = 'rtl';
initRouter();
document.addEventListener('click', onLinkClick);

// S13: a link's page chunk starts loading when the link is pointed at or focused, before the click (pages/lazy.tsx)
const intent = (e: Event) => {
  const href = (e.target as Element | null)?.closest?.('a')?.getAttribute('href');
  if (href && href.startsWith('/') && !href.startsWith('//')) void preloadRoute(match(href));
};
document.addEventListener('pointerover', intent, { passive: true });
document.addEventListener('focusin', intent);

const root = document.getElementById('app')!;
// Prerendered pages hydrate; the artifact build (no prerender) renders from scratch.
// The order page is a shared shell (the id lives in the URL, the token in this browser), so it renders fresh.
// S13: the page's own chunk is in before the first render, so hydration meets the prerendered markup.
void preloadRoute(match(path.value)).then(() => {
  if (root.firstElementChild && !__ARTIFACT__ && !location.pathname.startsWith('/order/')) hydrate(<App />, root);
  else render(<App />, root);
});

void loadCart();
