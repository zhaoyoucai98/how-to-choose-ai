/**
 * Cloudflare Pages Function - /api/health
 * 健康检查接口
 */
export async function onRequest({ env }) {
  return new Response(JSON.stringify({
    status: 'ok',
    version: '1.0.0',
    platform: 'Cloudflare Pages',
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}
