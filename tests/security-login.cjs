// Integration test with an in-process model of Upstash's atomic EVAL operation.
// A real Redis/Upstash test is still needed to exercise the Lua interpreter.
const assert = require('node:assert/strict');
const http = require('node:http');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const { test } = require('node:test');
const { createHash, createHmac, randomBytes, randomUUID } = require('node:crypto');

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const buckets = new Map();
const sessions = new Map();
let outage = false;
let failCommand = '';
const store = http.createServer(async (req, res) => {
  try {
    let raw = ''; for await (const chunk of req) raw += chunk;
    if (outage) { res.writeHead(503).end(); return; }
    const command = JSON.parse(raw);
    if (command[0] === failCommand) { res.writeHead(503).end(); return; }
    assert.equal(req.url, '/');
    if (command[0] === 'SET') {
      assert.match(command[1], /^keiba-ai:session:v2:[a-f0-9]{64}$/);
      assert.equal(command[2], '1'); assert.equal(command[3], 'EX');
      assert(command[4] > 0 && command[4] <= 43200);
      sessions.set(command[1], { expiry: Date.now() + command[4] * 1000, ttl: command[4] });
      res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ result: 'OK' })); return;
    }
    if (command[0] === 'GET' || command[0] === 'DEL') {
      const found = sessions.get(command[1]);
      if (found && found.expiry <= Date.now()) sessions.delete(command[1]);
      const result = command[0] === 'GET' ? (sessions.has(command[1]) ? '1' : null) : (sessions.delete(command[1]) ? 1 : 0);
      res.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ result })); return;
    }
    assert.equal(command[0], 'EVAL'); assert.equal(command.length, 7);
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
    assert(successes[0].headers.get('set-cookie').includes('HttpOnly'));
    assert(successes[0].headers.get('set-cookie').includes('SameSite=strict'));
    assert([...sessions.values()].every(s => s.ttl <= 43200 && s.ttl >= 43195));
    for (const cookie of cookies.slice(0, 2)) {
      response = await request('/api/ai/status', { headers: { cookie } });
      assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'private, no-store');
    }
    assert.equal((await request('/api/ai/status')).status, 401);
    failCommand = 'SET';
    response = await login('isolated-test-password'); assert.equal(response.status, 503); assert.equal(response.headers.get('set-cookie'), null);
    failCommand = '';

    const cookie = cookies[0];
    const logout = () => request('/api/auth/logout', { method: 'POST', headers: { cookie } });
    outage = true;
    response = await logout(); assert.equal(response.status, 503); assert.equal(response.headers.get('set-cookie'), null);
    assert.equal((await request('/api/ai/status', { headers: { cookie } })).status, 503);
    assert.equal((await request('/', { headers: { cookie } })).status, 503);
    outage = false;
    response = await logout(); assert.equal(response.status, 200); assert.match(response.headers.get('set-cookie'), /Max-Age=0/i);
    assert.equal((await request('/api/ai/status', { headers: { cookie } })).status, 401);
    const repeats = await Promise.all(Array.from({ length: 20 }, () => request('/api/ai/status', { headers: { cookie } })));
    assert(repeats.every(r => r.status === 401));

    const expiringCookie = cookies[1];
    const id = expiringCookie.split('=')[1].split('.')[2];
    const sessionKey = 'keiba-ai:session:v2:' + createHash('sha256').update(id).digest('hex');
    assert(sessions.has(sessionKey)); sessions.get(sessionKey).expiry = Date.now() - 1;
    assert.equal((await request('/api/ai/status', { headers: { cookie: expiringCookie } })).status, 401);

    const concurrentCookie = cookies[2];
    const overlap = await Promise.all([
      request('/api/auth/logout', { method: 'POST', headers: { cookie: concurrentCookie } }),
      ...Array.from({ length: 10 }, () => request('/api/ai/status', { headers: { cookie: concurrentCookie } })),
    ]);
    assert.equal(overlap[0].status, 200);
    assert(overlap.slice(1).every(r => r.status === 200 || r.status === 401));
    assert.equal((await request('/api/ai/status', { headers: { cookie: concurrentCookie } })).status, 401);

    const testSecret = 'isolated-test-secret-at-least-32-characters';
    const sign = value => createHmac('sha256', testSecret).update(value).digest('base64url');
    const legacy = `${Math.floor(Date.now()/1000)+3600}.${randomUUID()}`;
    assert.equal((await request('/api/ai/status', { headers: { cookie: `keiba_ai_session=${legacy}.${sign(legacy)}` } })).status, 401);
    const expired = `v2.${Math.floor(Date.now()/1000)-1}.${randomBytes(32).toString('base64url')}`;
    assert.equal((await request('/api/ai/status', { headers: { cookie: `keiba_ai_session=${expired}.${sign(expired)}` } })).status, 401);

    // The safe mode avoids repeated incorrect logins when the operator prohibits them.
    if (process.env.KEIBA_TEST_NO_REPEATED_FAILURES !== '1') {
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
    console.log('50 concurrent incorrect logins: 12 rejected, 38 limited');
    } else {
      console.log('Repeated-failure and 429 checks skipped by operator request');
    }
    outage = true; assert.equal((await login('isolated-test-password')).status, 503);
    console.log('50 concurrent successful logins: 50 passed');
  } finally {
    if (app) await stopApp(app);
    await new Promise(resolve => store.close(resolve));
  }
});
