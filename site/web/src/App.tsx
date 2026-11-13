import { useEffect } from 'preact/hooks';
import { match, path, type Route } from './router';
import { productBySegment, room } from './catalog';
import { headFor } from './head';
import { Layout } from './components/Layout';
import { TransitionOverlay } from './components/Transition';
import { Home } from './pages/Home';
import { Room } from './pages/Room';
import { NotFound } from './pages/NotFound';
import { lazyPage } from './pages/lazy';

// S13: the pages off the room's first paint are chunks of their own (pages/lazy.tsx); the room and home are in the entry
const Product = lazyPage('product', () => import('./pages/Product').then((m) => m.Product));
const CartPage = lazyPage('cart', () => import('./pages/Cart').then((m) => m.CartPage));
const Checkout = lazyPage('checkout', () => import('./pages/Checkout').then((m) => m.Checkout));
const OrderPage = lazyPage('order', () => import('./pages/Order').then((m) => m.OrderPage));
const MockPay = lazyPage('mock-pay', () => import('./pages/MockPay').then((m) => m.MockPay));
const Legal = lazyPage('legal', () => import('./pages/Legal').then((m) => m.Legal));
// MOCK1: the wow-tour mock-up, a chunk of its own, behind HD_PUBLIC=0 (__TOUR__ folds the import away in a public build)
const Tour = typeof __TOUR__ !== 'undefined' && __TOUR__ ? lazyPage('tour', () => import('./tour/TourPage').then((m) => m.TourPage)) : null;

export function Page({ route }: { route: Route }) {
  switch (route.name) {
    case 'home':
      return <Home />;
    case 'room': {
      const r = room(route.room);
      return r?.built ? <Room room={r} slot={route.slot} option={route.option} style={route.style} /> : <NotFound />;
    }
    case 'product': {
      // S7: /p/<public id>/ (an old address by card id moves there by dist/_redirects, 301)
      const hit = productBySegment(route.id);
      return hit ? <Product p={hit.product} /> : <NotFound />;
    }
    case 'cart':
      return <CartPage />;
    case 'checkout':
      return <Checkout failed={route.failed} />;
    case 'order':
      return <OrderPage id={route.id} />;
    case 'mock-pay':
      return <MockPay session={route.session} />;
    case 'legal':
      return <Legal page={route.page} />;
    case 'tour':
      return Tour ? <Tour /> : <NotFound />;
    default:
      return <NotFound />;
  }
}

/** Server and client render the same tree; `url` is given on the server (prerender). */
export function App({ url }: { url?: string }) {
  const route = match(url ?? path.value);
  useEffect(() => {
    document.title = headFor(route).title;
  }, [path.value]);
  return (
    <>
      <Layout route={route}>
        <Page route={route} />
      </Layout>
      <TransitionOverlay />
    </>
  );
}
