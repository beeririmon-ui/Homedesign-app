export default {
  async fetch(req: Request, env: { DB: D1Database }) {
    const r = await env.DB.prepare('select 1 as x').first();
    return new Response(JSON.stringify(r));
  },
};
