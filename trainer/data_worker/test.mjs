// Worker behaviour against a mock R2 binding: allowed file, CORS origin handling, HEAD, preflight, refused methods,
// paths outside trainer/v<n>/*.flac (including traversal attempts), missing objects.
import assert from 'node:assert/strict';
import worker from './src/index.js';
const files = { 'trainer/v1/di0.flac': new Uint8Array([102, 76, 97, 67, 1, 2, 3]) };
const object = (bytes) => ({ size: bytes.length, httpEtag: '"e1"', body: new Blob([bytes]).stream(), writeHttpMetadata: (h) => h.set('Content-Type', 'audio/flac') });
const env = { DATA: { get: async (k) => (files[k] ? object(files[k]) : null), head: async (k) => (files[k] ? { ...object(files[k]), body: null } : null) } };
const call = (path, init = {}) => worker.fetch(new Request('https://lttc-data.example.workers.dev' + path, init), env);
const site = { headers: { Origin: 'https://sfranjou.com' } };

let r = await call('/trainer/v1/di0.flac', site);
assert.equal(r.status, 200); assert.equal(r.headers.get('content-type'), 'audio/flac');
assert.equal(r.headers.get('access-control-allow-origin'), 'https://sfranjou.com'); assert.equal(r.headers.get('content-length'), '7');
assert.match(r.headers.get('cache-control'), /immutable/); assert.deepEqual(new Uint8Array(await r.arrayBuffer()), files['trainer/v1/di0.flac']);
r = await call('/trainer/v1/di0.flac', { headers: { Origin: 'https://evil.example' } });
assert.equal(r.status, 200); assert.equal(r.headers.get('access-control-allow-origin'), null);   // browsers block the read
r = await call('/trainer/v1/di0.flac', { method: 'HEAD', ...site }); assert.equal(r.status, 200); assert.equal((await r.arrayBuffer()).byteLength, 0);
r = await call('/trainer/v1/di0.flac', { method: 'OPTIONS', ...site }); assert.equal(r.status, 204); assert.equal(r.headers.get('access-control-allow-methods'), 'GET, HEAD');
for (const method of ['PUT', 'POST', 'DELETE']) { r = await call('/trainer/v1/di0.flac', { method, ...site }); assert.equal(r.status, 405); }
for (const p of ['/', '/trainer/v1/', '/trainer/v1/di0.wav', '/other/di0.flac', '/trainer/v1/../secret.flac', '/trainer/v1/%2e%2e/x.flac', '/trainer/v1/DI0.flac'])
  { r = await call(p, site); assert.equal(r.status, 404, p); }
r = await call('/trainer/v1/di9.flac', site); assert.equal(r.status, 404);
console.log('data worker: 200/CORS/HEAD/preflight/405/404 cases pass');
