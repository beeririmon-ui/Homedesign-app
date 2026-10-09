import './styles/fonts.css';
import './styles/tokens.css';
import './styles/base.css';
import './styles/room.css';
import './styles/wheel.css';
import './styles/pages.css';
import { hydrate, render } from 'preact';
import { App } from './App';
import { initRouter, onLinkClick } from './router';
import { loadTheme } from './state/ui';
import { loadCart } from './state/cart';

// The artifact has no <html> tag of its own: set language and direction here (the site's index.html has them too).
document.documentElement.lang = 'he';
document.documentElement.dir = 'rtl';
loadTheme();
initRouter();
document.addEventListener('click', onLinkClick);

const root = document.getElementById('app')!;
// Prerendered pages hydrate; the artifact build (no prerender) renders from scratch.
// The order page is a shared shell (the id lives in the URL, the token in this browser), so it renders fresh.
if (root.firstElementChild && !__ARTIFACT__ && !location.pathname.startsWith('/order/')) hydrate(<App />, root);
else render(<App />, root);

void loadCart();
