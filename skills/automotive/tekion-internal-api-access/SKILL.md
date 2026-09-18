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

### Job-level routes probed on `/api/service-module/u/ro/<roId>/job/<jobId>` (TL, 2026-09-17)

| Route | Result | Meaning |
|---|---|---|
| `POST …/reopen` | 400 `RJ1137 "Can reopen only completed job"` | **EXISTS** — a real job reopen, gated on job being COMPLETED |
| `GET …/status` | 500 `unexpected.error` | route exists (not a GET-readable resource) |
| `GET …/split` | 500 `unexpected.error` | route exists |
| `POST …/void` | 404 empty | not this shape |
| `POST …/mark-complete` | 404 empty | not this shape |
| `GET …/paytype`, `GET …/payers` | 404 empty | not these shapes |
| `GET /ro/<roId>/payers` | 500 `unexpected.error` | route EXISTS (errors on a corrupt payer set) |

Rule of thumb: **404 + empty body = wrong path; `{"status":"failed","errorDetails":{…}}` = right path,
request rejected.** Use empty/`{}` bodies to probe existence WITHOUT mutating.

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
Validation errors you'll see and what they mean — **ORDER MATTERS, fix them in this sequence** (each one
only appears once the previous is satisfied):
- `splitType/splitBy NotBlank :: must not be blank` → you nested the body under `splitInfo`; flatten it.
- `RJ1976 "Primary payer should be present"` → add **`primaryPayerId` at the TOP LEVEL** of the body
  (same id as the primary split's `payerId`). Without it the write always fails, even with a
  perfectly valid `splits[]`.
- `RO1365 post.tax.request.amount.mismatch.with.job.post.tax.total` → when `postTax:true` + `splitBy:AMOUNT`,
  **sum of every split's `postTaxAmount` MUST equal the RO bucket's `postTaxTotal`** (from `ro.totals`).
- HTTP **200 = the split was actually written.** Read the job back to confirm.

### Healthy-split template (copy the shape from a working sibling job on the SAME RO)

Best move is to read a clean job of the same pay type on the same RO and clone its `splitInfo`. Verified
working CUSTOMER_PAY shape (TL 398856 job 1 fix, 2026-09-17) — one payer, 100%, no phantom:

```json
{"splitType":"TOTAL","splitBy":"PERCENTAGE","postTax":false,
 "primaryPayerId":"<customer payerId>",
 "splits":[{"payerId":"<customer payerId>","subPayType":"CUSTOMER_PAY",
   "components":[{"splitPercentage":100,"splitAmount":6500,"amountToSplit":6500,
     "componentId":"<jobId>","component":"JOB","parentComponentId":"<jobId>","homogenousSplit":true}],
   "costCenters":[{"type":null,"costCenter":"COLLECT_AT_CASHIERING","value":"100"}],
   "postTaxAmount":6500}]}
```

An INTERNAL-pay sibling job instead showed: `splitBy:"PERCENTAGE"`, `postTax:false`, 100% to the internal
payer (`4e8ee417-5fce-4f14-90be-6a2c54908c0b` at TL), and
`costCenters:[{"type":"ACCOUNTING","costCenter":"<24-hex cost-center id>","value":"100"}]`.
**Cost centers are referenced by 24-hex id, not by name** — a store saying "goes to cost center 2105" gives
you a human label you must resolve to an id before you can write it.
ALWAYS snapshot the ORIGINAL `splitInfo` (verbatim JSON, to a file) before writing — that's the revert path.

## Reaching the app when React Query hides the call

The app PERSISTS its query cache (`localStorage['persist:primary']`), so re-visiting a page fires
**no network calls** — you cannot sniff a call for an entity you already viewed. Workarounds that worked:
- open the modal on an **RO/job you have NOT opened this session** (fresh entity ⇒ real call)
- or skip capture entirely: build the headers above and call the endpoint directly.

## XHR-hook header capture — the `setRequestHeader` timing trap (hit 2026-09-17, BC)

Arming the hook and then reading `window.__H` gave **`{}` / `kh:0` three times in a row** because
the override was installed INSIDE `send()`. **axios calls `xhr.open()` → `xhr.setRequestHeader(...)`
→ `xhr.send()`**, so a `setRequestHeader` patch applied during `send()` is installed *after* every
real header was already set. Patch the **prototype at hook-install time**:

```js
var oset = XMLHttpRequest.prototype.setRequestHeader;
XMLHttpRequest.prototype.setRequestHeader = function(k,v){
  try{ (this.__hh = this.__hh || []).push([k,v]); }catch(e){}
  return oset.apply(this, arguments);
};
XMLHttpRequest.prototype.open = function(m,u){ this.__m=m; this.__u=u; this.__hh=[]; return oopen.apply(this,arguments); };
XMLHttpRequest.prototype.send = function(b){
  var self=this;
  this.addEventListener('load', function(){
    if(self.__u && self.__u.indexOf('/api/')>=0){
      var h={}; (self.__hh||[]).forEach(function(p){h[p[0]]=p[1]});
      if(Object.keys(h).length>4){ window.__H=h; window.__Hu=self.__u; }
    }
  });
  return osend.apply(this,arguments);
};
```
Verified BC/1251: **15 headers** captured incl. `tekion-api-token`, roleId, userId, tenantname,
dealerId, tek-siteId, original-userid, original-tenantid, clientId, locale, program, applicationId,
subApplicationId, productIds. Save them to `/tmp/<store>_hdr.json` and **replay from plain Python
urllib** — that worked for every endpoint below with NO in-page fetch and NO cookie juggling
(the recalls-only skill's "external urllib always fails" applies to *hand-built* headers; a full
captured set works). The token is user-scoped but **`dealerId` + `tek-siteId` are store-scoped —
swap those two (−1_<dealer>) to read another store's data with the same capture.**

**Triggering a fresh XHR once the hook is armed:** re-entering a page for an entity already in the
persisted React Query cache fires NOTHING. `history.pushState + PopStateEvent` **DOES work when the
target is an entity you have not opened this session** (verified: pushState to a never-opened RO id
fired the RO's calculation/recommendation XHRs). Target a fresh id, not the one on screen.

## Verified endpoints at BC (dealer 1251, 2026-09-17) — RO dispatch/stuck-RO triage

| Endpoint | Result |
|---|---|
| `GET /api/service-module/u/ro/<roId>` | 200 — `{data:{jobs[],recommendations[],sublets[],ro{}}}`; `ro` carries **`status`, `assignedTechDetails[{techId,status,techStatus}]`, `promiseTime`, `closedTime`, `roNo`, `tagNo`, `source`, `appointmentId`, `allAdvisorIds`, `vehicleInfo`, `customerInfo`, `totals`** |
| `GET /api/scheduling/u/appointment/<apptId>` | 200 — **`appointmentStatus`, `appointmentSource` (BDC_SCHEDULING…), `preRoStatus`, `roNo`, `roId`, `assignedTechIds[]`, `campaignDetails`, `appointmentTakerUserId`, `createdTime`, `updatedByUserId`, `serviceAdvisorId`** ("TEK00" = unassigned placeholder) |
| `GET /api/service-module/u/ro/<roId>/audit` `/history` `/status-history` `/technician` `/jobs/<jid>` | **404 empty** — no RO status/assignment history is exposed. **There is no API timestamp for "when was a technician assigned"** — if a ticket hinges on it, say so rather than guessing. |

### Dispatch Settings live at `/ro/dispatch-settings` (NOT `/service/settings/dispatch-settings` → blank page)
Toggle states are readable from the `ant-switch` classes: `ant-switch ant-switch-checked` = ON,
plain `ant-switch` = OFF. BC as found: **Auto Assign Technician to Added Job = ON**, Choose between
Multiple Technician on RO = OFF, Only Assign if Technician has matching Skills = ON,
Auto assign same-as-last-service = OFF, who-submitted-Recommendation = ON, previously-Deferred = ON.

## Pitfalls

- The persistent-browser server exposes only /health /pages /screenshot /snapshot /url /click /console
  /cookies /eval /mouse /navigate /pages/close /pages/select /press /type — **NO CDP, NO request
  interception**. Chromium is launched without `--remote-debugging-port`.
- SPA `history.pushState` + `PopStateEvent` did NOT reliably remount components; the URL can drift
  (once landed on `…/jobs/new`). Prefer `/navigate` to an explicit deep link.
- App micro-frontend chunks are NOT in `document.querySelectorAll('script[src]')`; the root-shell
  bundles are on the public CDN `d36263b6wju30t.cloudfront.net/frontend/assets/DMS/us-west-1/production1/root/prod/tekion-root-shell_<ver>/static/js/`
  and can be fetched+grep'd from the terminal with **no auth** — that's how the header recipe was found.