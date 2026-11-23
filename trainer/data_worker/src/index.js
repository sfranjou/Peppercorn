// LTTC trainer data Worker (2026-11-22). Serves the provided DI recordings from the R2 bucket `lttc-data` (binding DATA).
// Only GET/HEAD of trainer/v<n>/<name>.flac; CORS for the site and the local trainer; files are versioned, so they are
// cached forever. The Workers Free plan caps requests at 100,000/day (then error 1027), which keeps R2 reads inside
// R2's free tier: no bill is possible from traffic.
const ORIGINS = new Set(['https://sfranjou.com', 'https://www.sfranjou.com', 'http://127.0.0.1:8770', 'http://localhost:8000']);
const KEY = /^trainer\/v[0-9]+\/[a-z0-9_]+\.flac$/;

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin');
    const headers = new Headers({ Vary: 'Origin' });
    if (ORIGINS.has(origin)) headers.set('Access-Control-Allow-Origin', origin);
    if (request.method === 'OPTIONS') {
      headers.set('Access-Control-Allow-Methods', 'GET, HEAD'); headers.set('Access-Control-Max-Age', '86400');
      return new Response(null, { status: 204, headers });
    }
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      headers.set('Allow', 'GET, HEAD'); return new Response('Method not allowed', { status: 405, headers });
    }
    const key = new URL(request.url).pathname.slice(1);
    if (!KEY.test(key)) return new Response('Not found', { status: 404, headers });
    const object = request.method === 'HEAD' ? await env.DATA.head(key) : await env.DATA.get(key);
    if (!object) return new Response('Not found', { status: 404, headers });
    object.writeHttpMetadata(headers);
    headers.set('ETag', object.httpEtag); headers.set('Content-Length', String(object.size));
    headers.set('Cache-Control', 'public, max-age=31536000, immutable');
    return new Response(request.method === 'HEAD' ? null : object.body, { headers });
  },
};
