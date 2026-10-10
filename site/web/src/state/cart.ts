import { signal, computed } from '@preact/signals';
import type { Cart, Pack } from '@hd/shared';
import { api, ApiError } from '../api';
import { announce } from './ui';

const KEY = 'hd.cart';
export const cart = signal<Cart | null>(null);
export const cartBusy = signal(false);
export const cartError = signal<string | null>(null);
export const cartCount = computed(() => cart.value?.count ?? 0);

function savedId(): string | null {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}
function saveId(id: string | null): void {
  try {
    if (id) localStorage.setItem(KEY, id);
    else localStorage.removeItem(KEY);
  } catch {
    /* storage unavailable: the cart lives for this page view only */
  }
}

export async function loadCart(): Promise<void> {
  const id = savedId();
  if (!id) return;
  try {
    cart.value = await api.getCart(id);
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 409)) saveId(null);
    else cartError.value = e instanceof ApiError ? (e.messageHe ?? null) : null;
  }
}

async function ensureCart(): Promise<string> {
  if (cart.value) return cart.value.id;
  const c = await api.createCart();
  saveId(c.id);
  cart.value = c;
  return c.id;
}

export async function setQty(variantId: string, pack: Pack, qty: number, label?: string): Promise<boolean> {
  cartBusy.value = true;
  cartError.value = null;
  try {
    const id = await ensureCart();
    cart.value = await api.setItem(id, variantId, pack, qty);
    if (label) announce(qty > 0 ? label : `הוסר מהסל`);
    return true;
  } catch (e) {
    if (e instanceof ApiError && (e.status === 404 || e.status === 409) && e.code.startsWith('cart')) {
      saveId(null);
      cart.value = null;
      return setQty(variantId, pack, qty, label);
    }
    cartError.value = e instanceof ApiError ? (e.messageHe ?? 'לא הצלחנו לעדכן את הסל.') : 'לא הצלחנו לעדכן את הסל.';
    announce(cartError.value);
    return false;
  } finally {
    cartBusy.value = false;
  }
}

/** Adds to the cart: `pack` is the set (default) or one piece (P1); each is its own line. */
export async function addToCart(variantId: string, name: string, qty = 1, pack: Pack = 'set', packLabel?: string): Promise<boolean> {
  const current = cart.value?.lines.find((l) => l.variant_id === variantId && l.pack === pack)?.qty ?? 0;
  return setQty(variantId, pack, Math.min(20, current + qty), `נוסף לסל: ${name}${packLabel ? `, ${packLabel}` : ''}`);
}

export function forgetCart(): void {
  saveId(null);
  cart.value = null;
}

export function saveOrderToken(orderId: string, token: string): void {
  try {
    localStorage.setItem(`hd.order.${orderId}`, token);
  } catch {
    sessionTokens.set(orderId, token);
  }
}
const sessionTokens = new Map<string, string>();
export function orderToken(orderId: string): string | null {
  try {
    return localStorage.getItem(`hd.order.${orderId}`) ?? sessionTokens.get(orderId) ?? null;
  } catch {
    return sessionTokens.get(orderId) ?? null;
  }
}
