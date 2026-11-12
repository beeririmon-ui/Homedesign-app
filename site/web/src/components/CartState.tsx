/**
 * S21, QA ת63: the cart and the checkout before they know the cart. Since S19 (ת55) both are a full page load, so the
 * saved cart is fetched on every entry (QA: 361 ms locally, over a second on a slow network). Meanwhile the page says
 * nothing it does not know: no "הסל ריק." and no "הסל ריק, אין מה לשלם.", only a quiet placeholder where the lines will be,
 * marked `aria-busy` (it appears after a beat, so a fast load shows nothing at all). A first load that failed says so
 * (the page's error line) and offers to try again; it never calls the cart empty.
 */
import { loadCart } from '../state/cart';

export function CartLoading() {
  return (
    <div class="cart-loading" aria-busy="true">
      <span class="sr-only">טוענים את הסל.</span>
      <span class="cart-loading-line" aria-hidden="true" />
      <span class="cart-loading-line" aria-hidden="true" />
      <span class="cart-loading-line short" aria-hidden="true" />
    </div>
  );
}

export function CartUnavailable() {
  return (
    <div class="cart-unavailable">
      <button type="button" class="btn btn-ghost" onClick={() => void loadCart()}>
        לנסות שוב
      </button>
    </div>
  );
}
