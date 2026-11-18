# www.16trillion.com

Website of 16 Trillion Wealth Advisory LLP. A plain static site (no build step) served by Cloudflare Pages.

- `public/` — the site itself (`index.html`, `assets/`, `robots.txt`)
- `functions/_middleware.js` — password gate that runs on Cloudflare before any page is served

**Status: internal preview.** The site stays behind the password, with `noindex` and a `robots.txt` that blocks search engines, until the SEBI RIA registration is granted.

## Cloudflare Pages settings

- Framework preset: None
- Build command: (leave empty)
- Build output directory: `public`

## Password gate

Cloudflare → this Pages project → Settings → Variables and Secrets → add two **Secrets** (Production and Preview):

- `SITE_PASSWORD` — the preview password
- `SITE_SECRET` — a long random string that signs the 30-day sign-in cookie (changing it signs every device out)

Without both, the site shows "not configured" and stays closed. After changing a variable, redeploy (Deployments → latest → Retry deployment). Sign out on a device: open `/logout`.

## Before launch (after registration)

1. Fill every `[PLACEHOLDER]` in `public/index.html` (fees, SEBI/BASL numbers, officers, SEBI office, onboarding channel, disclaimer wording).
2. Connect the contact form to prosper@16trillion.com (currently shows "not connected").
3. Remove `<meta name="robots" content="noindex,nofollow">`, change `robots.txt` to allow crawling, and delete `functions/_middleware.js`.
4. Compliance review.
5. Add the custom domain www.16trillion.com in Cloudflare Pages and update DNS at GoDaddy.
