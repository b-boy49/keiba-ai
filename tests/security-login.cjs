// Integration test with an in-process model of Upstash's atomic EVAL operation.
// A real Redis/Upstash test is still needed to exercise the Lua interpreter.
const assert = require('node:assert/strict');
const http = require('node:http');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { test } = require('node:test');

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const buckets = new Map();
let outage = false;
const store = http.createServer(async (req, res) => {
  try {
    let raw = ''; for await (const chunk of req) raw += chunk;
    if (outage) { res.writeHead(503).end(); return; }
    const command = JSON.parse(raw);
    assert.equal(req.url, '/'); assert.equal(command[0], 'EVAL'); assert.equal(command.length, 7);
    const [, , keys, key, window, max, valid] = command;
    assert.equal(keys, 1); assert(['0', '1'].includes(valid));
    const now = Date.now(); let bucket = buckets.get(key);
    if (bucket && bucket.expires <= now) { buckets.delete(key); bucket = undefined; }
    let result;
    if (bucket && bucket.count >= Number(max)) result = [0, Math.ceil((bucket.expires - now) / 1000)];
    else {
      if (valid === '0') {
        if (!bucket) bucket = { count: 0, expires: now + Number(window) * 1000 };
        bucket.count++; buckets.set(key, bucket);
      }
      result = [1, 0];
    }
    res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ result }));
  } catch { res.writeHead(400).end(); }
});

async function startApp(configured) {
  const env = { ...process.env, KEIBA_ACCESS_PASSWORD: 'isolated-test-password', KEIBA_SESSION_SECRET: 'isolated-test-secret-at-least-32-characters', UPSTASH_REDIS_REST_URL: configured ? 'http://127.0.0.1:19896' : '', UPSTASH_REDIS_REST_TOKEN: configured ? 'isolated-test-token' : '', KEIBA_LOGIN_RATE_LIMIT_WINDOW_SECONDS: '3', KEIBA_LOGIN_RATE_LIMIT_MAX_ATTEMPTS: '12' };
  const child = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'dev', '-p', '19897'], { env, stdio: 'ignore' });
  for (let i = 0; i < 100; i++) {
    if (child.exitCode !== null) throw new Error('Next.js exited before startup');
    try { await fetch('http://127.0.0.1:19897/access'); return child; } catch { await sleep(200); }
  }
  child.kill(); throw new Error('Next.js did not start');
}
async function stopApp(child) { const exit = once(child, 'exit'); child.kill(); await exit; }
const request = (path, options = {}) => fetch('http://127.0.0.1:19897' + path, { ...options, redirect: 'manual' });
const login = password => request('/api/auth/login', { method: 'POST', headers: { 'content-type': 'application/json', 'x-vercel-forwarded-for': '192.0.2.1' }, body: JSON.stringify({ password }) });

test('shared-IP login, atomic failure limit and fail-closed behaviour', { timeout: 120000 }, async () => {
  store.listen(19896, '127.0.0.1'); await once(store, 'listening');
  let app;
  try {
    app = await startApp(false);
    let response = await login('isolated-test-password');
    assert.equal(response.status, 503); assert.equal((await response.json()).error, 'RATE_LIMIT_UNAVAILABLE');
    await stopApp(app); app = undefined;
    app = await startApp(true);

    // Valid concurrent requests must not consume the 12 failure slots.
    const successes = await Promise.all(Array.from({ length: 50 }, () => login('isolated-test-password')));
    assert.equal(successes.filter(r => r.status === 200).length, 50);
    const cookies = successes.map(r => r.headers.get('set-cookie').split(';')[0]);
    assert.equal(new Set(cookies).size, 50);
    for (const cookie of cookies.slice(0, 2)) {
      response = await request('/api/ai/status', { headers: { cookie } });
      assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'private, no-store');
    }
    assert.equal((await request('/api/ai/status')).status, 401);

    // Successful logins cannot clear a concurrent or earlier failed attempt.
    const mixed = await Promise.all([
      ...Array.from({ length: 6 }, () => login('wrong')),
      ...Array.from({ length: 50 }, () => login('isolated-test-password')),
    ]);
    assert.equal(mixed.filter(r => r.status === 401).length, 6);
    assert.equal(mixed.filter(r => r.status === 200).length, 50);
    for (let i = 0; i < 6; i++) assert.equal((await login('wrong')).status, 401);
    response = await login('isolated-test-password'); assert.equal(response.status, 429);
    assert(Number(response.headers.get('retry-after')) > 0);
    await sleep(3200);
    assert.equal((await login('isolated-test-password')).status, 200);

    const failures = await Promise.all(Array.from({ length: 50 }, () => login('wrong')));
    assert.equal(failures.filter(r => r.status === 401).length, 12);
    assert.equal(failures.filter(r => r.status === 429).length, 38);
    outage = true; assert.equal((await login('isolated-test-password')).status, 503);
    console.log('50 concurrent successful logins: 50 passed; 50 concurrent incorrect logins: 12 rejected, 38 limited');
  } finally {
    if (app) await stopApp(app);
    await new Promise(resolve => store.close(resolve));
  }
});
