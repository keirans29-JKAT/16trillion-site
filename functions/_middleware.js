// Password gate for the internal preview of www.16trillion.com (Cloudflare Pages Function; runs on Cloudflare before any file is served).
// Settings in Cloudflare → project → Settings → Variables and Secrets (type: Secret):
//   SITE_PASSWORD  the sign-in password
//   SITE_SECRET    a long random string that signs the sign-in cookie (changing it signs everyone out)
// Without both settings the site stays closed.

const COOKIE = 'site_session';
const DAYS = 30;
const OPEN = new Set(['/robots.txt', '/assets/16trillion-logo.png']);
const enc = new TextEncoder();

async function hmac(secret, msg) {
  const key = await crypto.subtle.importKey('raw', enc.encode(secret), {name: 'HMAC', hash: 'SHA-256'}, false, ['sign']);
  const sig = await crypto.subtle.sign('HMAC', key, enc.encode(msg));
  return btoa(String.fromCharCode(...new Uint8Array(sig))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
function sameText(a, b) {          // constant-time comparison
  const x = enc.encode(a), y = enc.encode(b); let d = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) d |= (x[i] || 0) ^ (y[i] || 0);
  return d === 0;
}
async function makeToken(secret) { const exp = Date.now() + DAYS * 864e5; return `${exp}.${await hmac(secret, 'site:' + exp)}`; }
async function validToken(secret, token) {
  if (!token) return false; const [exp, sig] = token.split('.');
  if (!exp || !sig || !(+exp > Date.now())) return false;
  return sameText(sig, await hmac(secret, 'site:' + exp));
}
function cookieOf(req, name) {
  const m = (req.headers.get('Cookie') || '').split(/;\s*/).find(c => c.startsWith(name + '='));
  return m ? decodeURIComponent(m.slice(name.length + 1)) : '';
}
const safeNext = n => (typeof n === 'string' && n.startsWith('/') && !n.startsWith('//') && !n.startsWith('/login')) ? n : '/';
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

function page(body, status = 200, headers = {}) {
  return new Response(`<!doctype html><html lang="en-IN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow"><title>16Trillion — Preview</title><link rel="icon" href="/assets/16trillion-logo.png" type="image/png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,600;1,6..96,600&family=Noto+Serif:wght@600&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
:root{--navy:#0c1e34;--gold:#c9a961;--cream:#faf4e4}
*{box-sizing:border-box} body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--navy);color:var(--cream);font-family:"IBM Plex Sans",system-ui,sans-serif;padding:16px}
.box{width:100%;max-width:360px;display:grid;gap:18px;text-align:center}
.mark{width:84px;height:84px;margin:0 auto} .mark [stroke]{stroke:#e9c46a} .mark text,.mark g[fill]:not([fill="none"]){fill:#e9c46a}
.w1{font-family:"Bodoni Moda","Noto Serif",Georgia,serif;font-weight:600;font-size:2rem;color:#fff}
.ru{font-family:"Noto Serif",Georgia,serif;font-weight:600;color:#e9c46a}
.w2{font-family:"Bodoni Moda","Noto Serif",Georgia,serif;font-style:italic;font-weight:600;color:#e9c46a;margin-top:-14px}
form{display:grid;gap:10px;margin-top:8px;text-align:left}
label{font-size:.85rem;color:#c9cfd8}
input{font:inherit;padding:10px 12px;border-radius:6px;border:1px solid rgb(201 169 97/.5);background:rgb(255 255 255/.06);color:var(--cream)}
input:focus{outline:2px solid var(--gold);outline-offset:1px}
button{font:inherit;font-weight:500;padding:10px;border:0;border-radius:6px;background:var(--gold);color:var(--navy);cursor:pointer}
.err{color:#f4a49c;font-size:.88rem} .note{font-size:.78rem;color:#8d98a8}
</style></head><body><main class="box">
<svg class="mark" viewBox="-100 -100 200 200" aria-hidden="true"><g fill="none" stroke="#c9a961"><circle r="95" stroke-width="3"/><line x1="-95" x2="95" stroke-width="2"/><line y1="-95" y2="95" stroke-width="2"/><path d="M0,-95A42,95 0 0 1 0,95M0,-95A42,95 0 0 0 0,95M-95,0A95,38 0 0 0 95,0M-95,0A95,38 0 0 1 95,0" stroke-width="1.8"/></g><text x="0" y="22" font-family="Bodoni Moda,Georgia,serif" font-size="66" font-weight="800" fill="#c9a961" text-anchor="middle">16</text><g fill="#c9a961"><path d="M36,-70l1.4,3.6 3.6,1.4-3.6,1.4-1.4,3.6-1.4-3.6-3.6-1.4 3.6-1.4Z"/><path d="M58,-54l2.4,6.2 6.2,2.4-6.2,2.4-2.4,6.2-2.4-6.2-6.2-2.4 6.2-2.4Z"/><path d="M74,-40l1.6,4.2 4.2,1.6-4.2,1.6-1.6,4.2-1.6-4.2-4.2-1.6 4.2-1.6Z"/><path d="M50,-64l.9,2.3 2.3,.9-2.3,.9-.9,2.3-.9-2.3-2.3-.9 2.3-.9Z"/><path d="M68,-22l1.1,2.9 2.9,1.1-2.9,1.1-1.1,2.9-1.1-2.9-2.9-1.1 2.9-1.1Z"/></g></svg>
<div class="w1">16T<span class="ru">₹</span>illion</div><div class="w2">Wealth Advisory</div>
${body}</main></body></html>`, {status, headers: {'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store', 'x-robots-tag': 'noindex, nofollow', ...headers}});
}
const loginForm = (next, err) => page(`<form method="post" action="/login">
<input type="hidden" name="next" value="${esc(next)}">
<label for="pw">Preview password</label><input id="pw" name="password" type="password" autocomplete="current-password" required autofocus>
${err ? '<p class="err" role="alert">That password is not right.</p>' : ''}
<button type="submit">Sign in</button></form><p class="note">Internal preview for 16 Trillion Wealth Advisory LLP.</p>`, err ? 401 : 200);

export async function onRequest(context) {
  const {request, env, next} = context;
  const url = new URL(request.url);
  if (OPEN.has(url.pathname)) return next();
  if (!env.SITE_PASSWORD || !env.SITE_SECRET) return page('<p class="err">This site is not configured yet.</p>', 503);

  if (url.pathname === '/logout') {
    return new Response(null, {status: 303, headers: {Location: '/login', 'Set-Cookie': `${COOKIE}=; Path=/; Max-Age=0; HttpOnly; Secure; SameSite=Lax`}});
  }
  if (url.pathname === '/login') {
    if (request.method === 'POST') {
      const form = await request.formData();
      const to = safeNext(form.get('next'));
      if (sameText(String(form.get('password') || ''), env.SITE_PASSWORD)) {
        return new Response(null, {status: 303, headers: {Location: to,
          'Set-Cookie': `${COOKIE}=${encodeURIComponent(await makeToken(env.SITE_SECRET))}; Path=/; Max-Age=${DAYS * 86400}; HttpOnly; Secure; SameSite=Lax`}});
      }
      await new Promise(r => setTimeout(r, 1200));     // slows down password guessing
      return loginForm(to, true);
    }
    return loginForm(safeNext(url.searchParams.get('next')), false);
  }
  if (await validToken(env.SITE_SECRET, cookieOf(request, COOKIE))) {
    const res = await next();
    // always revalidate the page itself, so a new version shows on the next normal reload
    if ((res.headers.get('content-type') || '').includes('text/html')) {
      const r = new Response(res.body, res); r.headers.set('Cache-Control', 'no-cache'); return r;
    }
    return res;
  }
  const accept = request.headers.get('Accept') || '';
  if (request.method === 'GET' && accept.includes('text/html')) {
    return new Response(null, {status: 302, headers: {Location: '/login?next=' + encodeURIComponent(url.pathname + url.search)}});
  }
  return new Response('Sign in required', {status: 401, headers: {'cache-control': 'no-store'}});
}
