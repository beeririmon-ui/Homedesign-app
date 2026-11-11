/** qa-agent, 2026-11-11: the floor lamp bought and paid through the API (mock page), for the order line's supplier SKU. */
const BASE = process.env.QA_BASE ?? 'http://127.0.0.1:8799';
const h = { 'content-type': 'application/json', 'cf-connecting-ip': '203.0.113.77' };
const cart = (await (await fetch(`${BASE}/api/cart`, { method: 'POST', headers: h })).json()).id;
const put = await fetch(`${BASE}/api/cart/${cart}/items`, { method: 'PUT', headers: h, body: JSON.stringify({ variant_id: 'floor-lamp-pleated-walnut-stem-p2hz3:default', pack: 'set', qty: 1 }) });
const c = await (await fetch(`${BASE}/api/checkout`, { method: 'POST', headers: h, body: JSON.stringify({ cart_id: cart, customer: { full_name: 'בודקת איכות', email: 'qa@example.invalid', phone: '050-0000000' }, address: { city: 'חיפה', street: 'הנמל', house: '1' }, shipping_method: 'economy', consents: { terms: true, marketing: false } }) })).json();
const session = new URL(c.redirect_url).pathname.split('/').pop();
const pay = await fetch(`${BASE}/mock-pay/${session}/complete`, { method: 'POST', redirect: 'manual', body: new URLSearchParams({ outcome: 'success' }) });
console.log(JSON.stringify({ put: put.status, order_id: c.order_id, pay: pay.status }));
