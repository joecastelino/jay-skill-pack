---
name: tekion-internal-api-access
description: Call Tekion's INTERNAL (browser) APIs directly from the page — /api/service-module/u/* and friends — without driving the UI. Solves the "Token doesn't exist or is invalid" / "Missing headers" walls that block bare fetch calls. Use whenever an internal Tekion endpoint is needed (reading RO/job JSON, payer splits, split writes) or the app's React Query cache hides the call you need to capture.
---

# Tekion Internal API Access (SOLVED 2026-09-17)

The Tekion DMS SPA talks to `/api/...` internal endpoints with an **axios interceptor** adding auth.
A bare `fetch()` from `/eval` does NOT get those headers — hence the classic failures:
`500 "Token doesn't exist or is invalid"` or `403 "Missing headers"`.

## The header recipe (reverse-engineered from tekion-base-vendor.js)

The bundle's DSE header builder:
```js
{"tekion-api-token": apiToken(),   // apiToken() === localStorage.t_token  (or sessionStorage if export mode)
 roleid, tenantname, dealerid,     // NOTE: all LOWERCASE, no hyphens
 clientId: "web",                  // CLIENT_ID = "web"
 "tek-siteId",                     // camelCase w/ hyphen — from tcookie
 correlationId: <random>}
```

Build it in-page:
```js
var TC = JSON.parse(decodeURIComponent(document.cookie.split('tcookie=')[1].split(';')[0]));
var H = {
  'tekion-api-token': localStorage.t_token,
  'roleid': TC.roleId||'',
  'tenantname': TC.tenantname||'americanmotorscorporation',
  'dealerid': TC.dealerId||'',        // current dealer, e.g. '1092'
  'clientId': 'web',
  'tek-siteId': TC['tek-siteId']||'', // e.g. '-1_1092'
  'correlationId': String(Date.now())
};
fetch('/api/…', {headers:H, credentials:'include'})
```

`tcookie` (cookie, URL-encoded JSON) carries: `roleId, userId, tenantname, dealerId, tek-siteId, original-userid, original-tenantid, clientId`.
`localStorage.t_token` = the 536-char JWT. `localStorage.t_user` = user profile.

**WRONG header names that waste time** — do NOT use: `Authorization: Bearer`, `dealer-id`, `role-id`,
`tek-site-id`, `x-access-token`, `token`. Auth header is **`tekion-api-token`** (raw token, no "Bearer").

## Verified working endpoints (TL dealer 1092, 2026-09-17)

| Endpoint | Result |
|---|---|
| `GET /api/service-module/u/ro/<roId>` | 200 — `{data:{jobs[],recommendations[],sublets[],ro{}}}` |
| `GET /api/service-module/u/ro/<roId>/job/<jobId>` | 200 — full job doc (payType, primaryPayerId, splitInfo, payerTaxCodes, operations, totals) |
| `PUT /api/service-module/u/multi-payer-split/assetType/RO/assetId/<roId>/job/<jobId>` | **write path for payer splits** — body = the splitInfo object |

`ro` sub-object holds `customerInfo` (id = the customer PAYER id), `totals` (per-bucket
preTaxTotal/postTaxTotal — the authoritative money), `status`, `invoice`.

404 responses come back with an EMPTY body; a matched route that fails returns the app's
**business-error JSON** (`{"status":"failed","errorDetails":{...}}`) — use that difference to tell
"wrong path" from "right path, bad request".

## Payer-split write shape

Body is the split object itself (NOT wrapped in `{splitInfo:…}`):
```json
{"splitType":"TOTAL","splitBy":"AMOUNT"|"PERCENTAGE","postTax":true,
 "splits":[{"payerId":"…","subPayType":"CUSTOMER_PAY","components":[
    {"splitPercentage":100,"splitAmount":6137,"amountToSplit":6137,
     "componentId":"…","component":"JOB","parentComponentId":"…","homogenousSplit":true}, …],
   "costCenters":[{"type":null,"costCenter":"COLLECT_AT_CASHIERING","value":"100"}],
   "postTaxAmount":6500}]}
```
Validation errors you'll see and what they mean:
- `splitType/splitBy NotBlank :: must not be blank` → you nested the body under `splitInfo`; flatten it.
- `RO1365 post.tax.request.amount.mismatch.with.job.post.tax.total` → when `postTax:true` + `splitBy:AMOUNT`,
  **sum of every split's `postTaxAmount` MUST equal the RO bucket's `postTaxTotal`** (from `ro.totals`).

## Reaching the app when React Query hides the call

The app PERSISTS its query cache (`localStorage['persist:primary']`), so re-visiting a page fires
**no network calls** — you cannot sniff a call for an entity you already viewed. Workarounds that worked:
- open the modal on an **RO/job you have NOT opened this session** (fresh entity ⇒ real call)
- or skip capture entirely: build the headers above and call the endpoint directly.

## Pitfalls

- The persistent-browser server exposes only /health /pages /screenshot /snapshot /url /click /console
  /cookies /eval /mouse /navigate /pages/close /pages/select /press /type — **NO CDP, NO request
  interception**. Chromium is launched without `--remote-debugging-port`.
- SPA `history.pushState` + `PopStateEvent` did NOT reliably remount components; the URL can drift
  (once landed on `…/jobs/new`). Prefer `/navigate` to an explicit deep link.
- App micro-frontend chunks are NOT in `document.querySelectorAll('script[src]')`; the root-shell
  bundles are on the public CDN `d36263b6wju30t.cloudfront.net/frontend/assets/DMS/us-west-1/production1/root/prod/tekion-root-shell_<ver>/static/js/`
  and can be fetched+grep'd from the terminal with **no auth** — that's how the header recipe was found.