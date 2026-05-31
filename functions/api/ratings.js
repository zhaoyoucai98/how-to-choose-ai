/**
 * Cloudflare Pages Function - /api/ratings
 * GET: 获取评分列表 / POST: 提交新评分
 */
export async function onRequest({ request, env }) {
  const SUPABASE_URL = env.SUPABASE_URL || '';
  const SUPABASE_KEY = env.SUPABASE_KEY || '';

  const headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json',
  };

  // GET 请求 - 查询评分
  if (request.method === 'GET') {
    try {
      const res = await fetch(
        `${SUPABASE_URL}/rest/v1/ratings?order=created_at.desc`,
        { headers }
      );
      const data = res.ok ? await res.json() : [];
      return new Response(JSON.stringify({ data, count: data.length }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (e) {
      return new Response(JSON.stringify({ data: [], count: 0 }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // POST 请求 - 创建评分
  if (request.method === 'POST') {
    try {
      const body = await request.json();
      const postHeaders = { ...headers, Prefer: 'return=representation' };
      const res = await fetch(`${SUPABASE_URL}/rest/v1/ratings`, {
        method: 'POST',
        headers: postHeaders,
        body: JSON.stringify(body),
      });
      const data = res.ok ? await res.json() : [];
      return new Response(JSON.stringify({ msg: 'ok', data }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    } catch (e) {
      return new Response(JSON.stringify({ error: e.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  return new Response(JSON.stringify({ error: 'Method not allowed' }), {
    status: 405,
    headers: { 'Content-Type': 'application/json' },
  });
}
