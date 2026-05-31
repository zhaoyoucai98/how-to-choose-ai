/**
 * Cloudflare Pages Function - /api/analyze
 * JS 版推荐算法，与 Python 版 api/index.py 逻辑完全一致
 * 直接调用 Supabase REST API 获取模型数据
 */
export async function onRequestPost({ request, env }) {
  const SUPABASE_URL = env.SUPABASE_URL || '';
  const SUPABASE_KEY = env.SUPABASE_KEY || '';

  const headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': `Bearer ${SUPABASE_KEY}`,
    'Content-Type': 'application/json',
  };

  // 从 Supabase 拉取所有模型
  let models = [];
  try {
    const res = await fetch(
      `${SUPABASE_URL}/rest/v1/models?order=score.desc`,
      { headers }
    );
    models = res.ok ? (await res.json()) : [];
  } catch (e) {
    return new Response(JSON.stringify({ data: [] }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // 解析请求体
  let body;
  try {
    body = await request.json();
  } catch (e) {
    return new Response(JSON.stringify({ error: 'Invalid JSON body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const weights = body.weights || {};
  const preferRegion = body.prefer_region || 'auto';

  function calcScore(m) {
    const w = weights;
    const match =
      ((m.strength_reasoning || 0) * (w.reasoning || 0) / 100 +
       (m.strength_coding || 0)    * (w.coding || 0)    / 100 +
       (m.strength_knowledge || 0) * (w.knowledge || 0) / 100 +
       (m.strength_math || 0)      * (w.math || 0)      / 100 +
       (m.strength_multilingual || 0) * (w.multilingual || 0) / 100 +
       (m.strength_multimodal || 0) * (w.multimodal || 0) / 100);

    const price = m.price_per_m || 10;
    const medianPrice = 5.5;
    const priceScore = Math.max(0, 100 - (price / medianPrice) * 50);

    let regionBoost = 0;
    if (preferRegion === '国产' && m.region === '国产') {
      regionBoost = 10;
    } else if (preferRegion === '海外' && m.region === '海外') {
      regionBoost = 3;
    }

    return Math.round((match * 0.7 + priceScore * 0.3 + regionBoost) * 100) / 100;
  }

  const scored = models.map(m => ({ model: m, score: calcScore(m) }));
  scored.sort((a, b) => b.score - a.score);

  const result = [];
  for (const { model: m, score } of scored.slice(0, 10)) {
    const tags = [];
    const sCoding = m.strength_coding || 0;
    const sReasoning = m.strength_reasoning || 0;
    if (sCoding >= 88 && (weights.coding || 0) >= 20) {
      tags.push('编程能力强');
    }
    if (sReasoning >= 90 && (weights.reasoning || 0) >= 20) {
      tags.push('推理能力突出');
    }
    if ((m.price_per_m || 99) <= 5) {
      tags.push('性价比高');
    }
    if (m.region === '国产' && (preferRegion === 'auto' || preferRegion === '国产')) {
      tags.push('国产模型/数据合规');
    }
    if (tags.length === 0) {
      tags.push('综合能力均衡');
    }

    result.push({
      id: m.id,
      name: m.name,
      vendor: m.vendor,
      region: m.region || '',
      score: m.score || 0,
      price_per_m: m.price_per_m || 0,
      match_score: score,
      reason: tags.join(' · '),
    });
  }

  return new Response(JSON.stringify({ data: result }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}
