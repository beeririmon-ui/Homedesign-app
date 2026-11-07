import { useEffect } from 'preact/hooks';
import { match, navigate, path, type Route } from './router';
import { productBySegment, room } from './catalog';
import { headFor } from './head';
import { productPath } from '@hd/shared/product-url';
import { Layout } from './components/Layout';
import { TransitionOverlay } from './components/Transition';
import { Home } from './pages/Home';
import { Room } from './pages/Room';
import { Product } from './pages/Product';
import { CartPage } from './pages/Cart';
import { Checkout } from './pages/Checkout';
import { OrderPage } from './pages/Order';
import { MockPay } from './pages/MockPay';
import { Legal } from './pages/Legal';
import { NotFound } from './pages/NotFound';

export function Page({ route }: { route: Route }) {
  switch (route.name) {
    case 'home':
      return <Home />;
    case 'room': {
      const r = room(route.room);
      return r?.built ? <Room room={r} slot={route.slot} option={route.option} /> : <NotFound />;
    }
    case 'product': {
      // S5: /p/<slug>/; an old address by card id still opens the page and moves to the neutral one
      const hit = productBySegment(route.id);
      if (hit?.old && typeof window !== 'undefined') queueMicrotask(() => navigate(productPath(hit.product.id) + location.search, { replace: true }));
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
