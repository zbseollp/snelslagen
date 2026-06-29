# Analytics & tracking — autotheorieoefenen.com

## Google Analytics
- **GA4 Measurement ID: `G-T6XZPT7H5R`**  (gtag.js, in <head>)  -> CARRY OVER (consent-gated)
- Legacy Universal Analytics `UA-48819692-23` (analytics.js) -> DEAD (UA discontinued), do NOT carry over.

## Search Console verification
- No `google-site-verification` meta tag found in homepage <head>.
- Likely verified via the GA-linked Google account or a DNS TXT record.
- ACTION (Phase 5): confirm verification method before cutover so history is preserved;
  do NOT create a new property (domain unchanged).

## Other tracking
- Cookie banner present on source ("cookieinfo" script). New site: self-hosted consent banner,
  GA loads only after Accept.
- No Facebook Pixel / Clarity / Hotjar detected in homepage head.
