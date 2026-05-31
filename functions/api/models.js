/**
 * Cloudflare Pages Function - /api/models
 * 从 Supabase 获取模型列表
 */
export async function onRequest({ env }) {
  const SUPABASE_URL = env.SUPABASE_URL || '';
  const SUPABASE_KEY = env.SUPABASE_KEY || '';

  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/models?order=score.desc`,
      {
        headers: {
          'apikey': SUPABASE_KEY,
          'Authorization': `Bearer ${SUPABASE_KEY}`,
          'Content-Type': 'application/json',
        },
      }
    );
    const data = res.ok ? await res.json() : [];
    return new Response(JSON.stringify({ data, count: data.length }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ data: [], count: 0, error: e.message }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
