import { readFile } from 'node:fs/promises';
import test from 'node:test';
import assert from 'node:assert/strict';

const { default: worker, eligibleRelease, hasPublishedArticle, requestBuild } = await import('./pls-article-scheduler.mjs');
const epoch = value => Date.parse(value);
const noon = epoch('2026-10-11T12:00:00+04:00');
const recovery = epoch('2026-10-11T12:20:00+04:00');
const title = 'Tax Planning vs Tax Evasion in the UAE: Where Is the Line?';
const liveHtml = `<h1>${title}</h1><script type="application/ld+json">${JSON.stringify({ '@graph': [{ '@type': 'BlogPosting', headline: title }] })}</script>`;
const env = { PAGES_BASE_URL: 'https://approved-pls-test.pages.dev', PAGES_DEPLOY_HOOK: 'https://api.cloudflare.com/client/v4/pages/webhooks/deploy_hooks/FAKE-NOT-A-CREDENTIAL' };

test('release guard admits both approved Dubai noon dates and a single recovery slot', () => {
  assert.equal(eligibleRelease(noon, noon)?.title, title);
  assert.equal(eligibleRelease(recovery, recovery)?.title, title);
  assert.match(eligibleRelease(epoch('2026-10-18T12:00:00+04:00'), epoch('2026-10-18T12:00:00+04:00'))?.title, /^AI and Tax Services/);
  assert.match(eligibleRelease(epoch('2026-10-18T12:00:25.833+04:00'), epoch('2026-10-18T12:00:26.652+04:00'))?.title, /^AI and Tax Services/);
  assert.equal(eligibleRelease(noon, noon - 1), null);
  assert.equal(eligibleRelease(recovery, recovery - 1), null);
  assert.equal(eligibleRelease(noon, noon + 40 * 60000 + 1), null);
  for (const value of ['2027-10-11T08:00:00Z', '2026-10-10T08:00:00Z', '2026-11-11T08:00:00Z', '2026-10-11T07:00:00Z', '2026-10-11T08:15:00Z']) {
    assert.equal(eligibleRelease(epoch(value), epoch(value)), null);
  }
  assert.equal(eligibleRelease(NaN, noon), null);
});

test('publication evidence needs matching h1 and actual BlogPosting metadata', () => {
  assert.equal(hasPublishedArticle(liveHtml, title), true);
  assert.equal(hasPublishedArticle(`<h1>${title}</h1>BlogPosting`, title), false);
  assert.equal(hasPublishedArticle(liveHtml.replace('BlogPosting', 'WebPage'), title), false);
  assert.equal(hasPublishedArticle(liveHtml.replace('<h1>', '<h2>').replace('</h1>', '</h2>'), title), false);
  assert.equal(hasPublishedArticle('<h1>Fallback page</h1>' + liveHtml, title), false);
});

async function withRuntime(at, fakeFetch, action) {
  const originalFetch = globalThis.fetch;
  const originalNow = Date.now;
  const originalLog = console.log;
  const logs = [];
  Date.now = () => at;
  globalThis.fetch = fakeFetch;
  console.log = (...args) => logs.push(args.join(' '));
  try { await action(logs); }
  finally { globalThis.fetch = originalFetch; Date.now = originalNow; console.log = originalLog; }
}

test('scheduled-only handler makes zero calls outside dates, and has no HTTP endpoint', async () => {
  assert.deepEqual(Object.keys(worker), ['scheduled']);
  await withRuntime(noon - 1, async () => { throw new Error('Unexpected fetch'); }, async () => {
    await worker.scheduled({ scheduledTime: noon }, env);
  });
});

test('verified article skips the hook, while a missing article triggers one bounded POST', async () => {
  const calls = [];
  await withRuntime(noon, async (url, options) => {
    calls.push({ url, options });
    return new Response(liveHtml, { status: 200, headers: { 'Content-Type': 'text/html' } });
  }, async logs => {
    await worker.scheduled({ scheduledTime: noon }, env);
    assert.equal(calls.length, 1);
    assert.match(logs.join(' '), /rebuild skipped/);
  });
  calls.length = 0;
  await withRuntime(noon, async (url, options) => {
    calls.push({ url, options });
    return options.method === 'POST' ? new Response('{}', { status: 200 }) : new Response('Missing', { status: 404 });
  }, async logs => {
    await worker.scheduled({ scheduledTime: noon }, env);
    assert.equal(calls.length, 2);
    assert.equal(calls[1].options.method, 'POST');
    assert.ok(calls.every(call => call.options.signal instanceof AbortSignal && call.options.redirect === 'manual'));
    assert.ok(!logs.join(' ').includes('https://'));
    assert.ok(!logs.join(' ').includes(env.PAGES_DEPLOY_HOOK));
  });
});

test('unsafe origins and incorrect configuration fail before any network call', async () => {
  await withRuntime(noon, async () => { throw new Error('Unexpected fetch'); }, async () => {
    for (const base of ['https://preview.project.pages.dev', 'https://pls-uae.com', 'http://project.pages.dev', 'https://project.pages.dev/path', 'https://project.pages.dev?query=yes']) {
      await assert.rejects(worker.scheduled({ scheduledTime: noon }, { ...env, PAGES_BASE_URL: base }), /approved stable production Pages origin/);
    }
    await assert.rejects(worker.scheduled({ scheduledTime: noon }, { ...env, PAGES_DEPLOY_HOOK: 'https://unapproved.example/hook' }), /deploy hook Secret/);
  });
});

test('large verification responses are capped and hook failures reveal no URL', async () => {
  let posts = 0;
  await withRuntime(noon, async (_url, options) => {
    if (options.method === 'POST') { posts++; return new Response('Failure', { status: 500 }); }
    return new Response('x'.repeat(65537) + liveHtml, { headers: { 'Content-Type': 'text/html' } });
  }, async () => {
    await assert.rejects(worker.scheduled({ scheduledTime: noon }, env), error => {
      assert.match(error.message, /rebuild request failed/);
      assert.ok(!error.message.includes('https://'));
      assert.ok(!error.message.includes(env.PAGES_DEPLOY_HOOK));
      return true;
    });
    assert.equal(posts, 3);
  });
});


test('transient HTTP failure retries once and accepts the successful build request', async () => {
  let posts = 0;
  await withRuntime(noon, async () => new Response('{}', {status: ++posts === 1 ? 503 : 200}), async logs => {
    await requestBuild(env.PAGES_DEPLOY_HOOK, async () => false);
    assert.equal(posts, 2);
    assert.ok(logs.some(x => x.includes('rebuild_attempt_failed') && x.includes('503')));
    assert.ok(logs.some(x => x.includes('rebuild_accepted') && x.includes('200')));
  });
});

test('permanent HTTP rejection does not repeat the same request', async () => {
  let posts = 0;
  await withRuntime(noon, async () => {posts++; return new Response('', {status:403});}, async () => {
    await assert.rejects(requestBuild(env.PAGES_DEPLOY_HOOK, async () => false), /rebuild request failed/);
    assert.equal(posts, 1);
  });
});

test('a lost response followed by verified publication suppresses duplicate builds', async () => {
  let posts = 0;
  await withRuntime(noon, async () => {posts++; throw new TypeError('Private URL must never enter logs');}, async logs => {
    await requestBuild(env.PAGES_DEPLOY_HOOK, async () => true);
    assert.equal(posts, 1);
    assert.match(logs.join(' '), /further rebuilds skipped/);
    assert.ok(!logs.join(' ').includes('Private URL'));
  });
});

test('network failures are capped at three attempts and log no error messages or hook URL', async () => {
  let posts = 0;
  await withRuntime(noon, async () => {posts++; throw new TypeError(env.PAGES_DEPLOY_HOOK);}, async logs => {
    await assert.rejects(requestBuild(env.PAGES_DEPLOY_HOOK, async () => false), /rebuild request failed/);
    assert.equal(posts, 3);
    assert.ok(!logs.join(' ').includes(env.PAGES_DEPLOY_HOOK));
  });
});


test('Worker-compatible fetches reject redirects without forwarding the private hook', async () => {
  const destinations = [];
  await withRuntime(noon, async (url, options) => {
    assert.equal(options.redirect, 'manual');
    destinations.push(url);
    return new Response('', { status: 302, headers: { Location: 'https://unexpected.invalid/' } });
  }, async () => {
    await assert.rejects(worker.scheduled({ scheduledTime: noon }, env), /Pages rebuild request failed/);
  });
  assert.equal(destinations.length, 2);
  assert.equal(destinations[1], env.PAGES_DEPLOY_HOOK);
  assert.ok(!destinations.some(url => url.includes('unexpected.invalid')));
});
