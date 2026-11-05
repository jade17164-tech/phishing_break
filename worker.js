// 수업 번역기 DeepL 중계 서버 (Cloudflare Worker)
// DeepL 키는 이 코드에 넣지 말고, Worker 설정의 비밀 변수 DEEPL_KEY 에 넣으세요.
const ALLOWED = ['https://jade17164-tech.github.io'];

export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin') || '';
    const cors = {
      'Access-Control-Allow-Origin': ALLOWED.includes(origin) ? origin : ALLOWED[0],
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Vary': 'Origin',
    };
    const reply = (body, status = 200) =>
      new Response(typeof body === 'string' ? body : JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

    if (req.method === 'OPTIONS') return new Response(null, { headers: cors });
    if (!ALLOWED.includes(origin)) return reply({ error: 'forbidden' }, 403);
    const key = env.DEEPL_KEY;
    if (!key) return reply({ error: 'no_key' }, 500);
    const base = key.trim().endsWith(':fx') ? 'https://api-free.deepl.com' : 'https://api.deepl.com';
    const auth = { Authorization: 'DeepL-Auth-Key ' + key.trim() };
    const path = new URL(req.url).pathname;

    if (path === '/usage') {
      const r = await fetch(base + '/v2/usage', { headers: auth });
      return reply(await r.text(), r.status);
    }
    if (path !== '/translate' || req.method !== 'POST') return reply({ error: 'not_found' }, 404);

    let body;
    try { body = await req.json(); } catch { return reply({ error: 'bad_json' }, 400); }
    const text = Array.isArray(body.text) ? body.text.filter(t => typeof t === 'string').slice(0, 20) : [];
    const context = typeof body.context === 'string' ? body.context.slice(0, 2000) : undefined;
    if (!text.length || text.join('').length > 5000) return reply({ error: 'bad_text' }, 400);

    const send = extra => fetch(base + '/v2/translate', {
      method: 'POST',
      headers: { ...auth, 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, source_lang: 'EN', target_lang: 'KO', context, ...extra }),
    });
    // 최신 고품질 모델을 먼저 쓰고, 계정에서 안 되면 기본 모델로 다시 보냄
    let r = await send({ model_type: 'prefer_quality_optimized' });
    if (r.status === 400) r = await send({});
    return reply(await r.text(), r.status);
  },
};
