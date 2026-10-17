// PLS article release scheduler. The deploy hook stays in the existing Worker Secret.
// Cron: 0,20 8 11,18 10 * (12:00 and one 12:20 Dubai recovery check).
const RELEASES = {
  11: {
    at: Date.parse('2026-10-11T08:00:00Z'),
    path: '/articles/tax-planning-vs-tax-evasion-in-the-uae-where-is-the-line/',
    title: 'Tax Planning vs Tax Evasion in the UAE: Where Is the Line?',
  },
  18: {
    at: Date.parse('2026-10-18T08:00:00Z'),
    path: '/articles/ai-and-tax-services-what-the-future-means-for-uae-businesses/',
    title: 'AI and Tax Services: What the Future Means for UAE Businesses',
  },
};
const TIMEOUT_MS = 8000;
const HOOK_TIMEOUT_MS = 30000;
const MAX_BUILD_ATTEMPTS = 3;
const MAX_HTML_BYTES = 65536;

export function eligibleRelease(scheduledTime, now = Date.now()) {
  if (!Number.isFinite(scheduledTime) || !Number.isFinite(now)) return null;
  const event = new Date(scheduledTime);
  const release = RELEASES[event.getUTCDate()];
  if (!release || event.getUTCFullYear() !== 2026 || event.getUTCMonth() !== 9 ||
      event.getUTCHours() !== 8 || ![0, 20].includes(event.getUTCMinutes())) return null;
  // A delayed event may run within a short recovery window, never before its slot.
  if (now < scheduledTime || now < release.at || now > release.at + 40 * 60 * 1000) return null;
  return release;
}

export function hasPublishedArticle(html, title) {
  const heading = html.match(/<h1\b[^>]*>([\s\S]*?)<\/h1>/i);
  if (!heading || heading[1].replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim() !== title) return false;
  for (const script of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
    if (!/\btype\s*=\s*["']application\/ld\+json["']/i.test(script[1])) continue;
    try {
      const data = JSON.parse(script[2]);
      const nodes = Array.isArray(data) ? data : Array.isArray(data['@graph']) ? data['@graph'] : [data];
      if (nodes.some(node => node && (Array.isArray(node['@type']) ? node['@type'] : [node['@type']]).includes('BlogPosting') && node.headline === title)) return true;
    } catch { /* A malformed or unrelated block is not publication evidence. */ }
  }
  return false;
}

function approvedOrigin(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || !/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.pages\.dev$/.test(url.hostname) ||
        url.port || url.username || url.password || !['', '/'].includes(url.pathname) || url.search || url.hash) throw new Error();
    return url.origin;
  } catch { throw new Error('Configure the approved stable production Pages origin.'); }
}

function approvedHook(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.hostname !== 'api.cloudflare.com' || url.port ||
        url.username || url.password || url.hash) throw new Error();
    return url.href;
  } catch { throw new Error('Configure the Pages deploy hook Secret.'); }
}

async function articleIsLive(url, title) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal, redirect: 'manual', headers: { 'Cache-Control': 'no-cache' }, cf: { cacheTtl: 0 } });
    if (response.status !== 200 || !response.headers.get('Content-Type')?.toLowerCase().includes('text/html') || !response.body) {
      await response.body?.cancel();
      return false;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let bytes = 0;
    let html = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > MAX_HTML_BYTES) {
        await reader.cancel();
        return false;
      }
      html += decoder.decode(value, { stream: true });
    }
    html += decoder.decode();
    return hasPublishedArticle(html, title);
  } catch {
    // Network errors may contain URLs. Keep those details out of logs.
    return false;
  } finally { clearTimeout(timer); }
}

export async function requestBuild(hook, verifyPublication) {
  for (let attempt = 1; attempt <= MAX_BUILD_ATTEMPTS; attempt++) {
    // An earlier timed-out request may still have started a successful build.
    if (attempt > 1 && await verifyPublication()) {
      console.log('Approved article verified after a failed response; further rebuilds skipped.');
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), HOOK_TIMEOUT_MS);
    let status = 0;
    let category = 'network';
    try {
      const response = await fetch(hook, {
        method: 'POST', signal: controller.signal, redirect: 'manual',
      });
      status = response.status;
      await response.body?.cancel();
      if (response.ok) {
        console.log(JSON.stringify({ event: 'rebuild_accepted', attempt, status }));
        return;
      }
      category = 'http';
    } catch (error) {
      category = error?.name === 'AbortError' || error?.name === 'TimeoutError' ? 'timeout' : 'network';
    } finally { clearTimeout(timer); }
    // Safe diagnostics deliberately omit URLs, response bodies and error messages.
    console.log(JSON.stringify({ event: 'rebuild_attempt_failed', attempt, status, category }));
    const retryable = status === 0 || [408, 425, 429].includes(status) || status >= 500;
    if (!retryable || attempt === MAX_BUILD_ATTEMPTS) {
      throw new Error('Pages rebuild request failed; inspect the safe attempt status and Pages deployment records.');
    }
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

export default {
  async scheduled(event, env) {
    const release = eligibleRelease(event.scheduledTime);
    if (!release) return;
    const origin = approvedOrigin(env.PAGES_BASE_URL);
    const hook = approvedHook(env.PAGES_DEPLOY_HOOK);
    if (await articleIsLive(origin + release.path, release.title)) {
      console.log('Approved article verified as published; rebuild skipped.');
      return;
    }
    await requestBuild(hook, () => articleIsLive(origin + release.path, release.title));
    console.log('Pages rebuild requested; publication still requires verification.');
  },
};
