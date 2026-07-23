---
name: tekion-deferred-services-report
description: Pull declined/deferred service data (recommendations customers didn't buy) for any Tekion store via the internal Deferred Services report API — service name, counts, dollar estimates, customer/vehicle/advisor detail. Zero OpenAPI quota; works when OVERALL_QUOTA is exhausted. Use for marketing campaign lists (Autumn) or lost-sales analysis.
triggers:
  - declined services
  - deferred services
  - declined deferred report
  - lost sales recommendations
---

# Tekion Deferred/Declined Services Report

Proven end-to-end at BC (dealer 1251) 2026-07-08: 2,915 deferred line items over 90 days,
harvested in ~15 pages via the :9223 authenticated browser. Zero OpenAPI quota.

## Key facts

- Tekion's UI report = REPORTS module → `/core/reports/service/deferredServices`.
- Backend = `POST /api/service-module/u/reporting/recommendation/search` (internal API,
  fire in-page via fetch with captured `window.__H` headers + credentials:'include').
- Status vocabulary: recommendations are **DEFERRED** (declined) or **APPROVED** (sold).
  DECLINED / RECOMMENDED / OPEN / COMPLETED all return 0 — "declined" == DEFERRED.
- The UI's default filter adds `comebackCompleted NIN [true]` (excludes ones the customer
  later came back and bought). Include or drop per the ask; counts differ (~204 vs 2,915
  difference at BC was mostly the roClosedTime default window, not comeback).

## Request body (paginates properly, unlike activity-log)

```json
{"reportName":"RO_RECOMMENDATIONS","reportGroup":"RECOMMENDATION",
 "sort":[{"field":"universalId","order":"ASC"}],
 "filters":[
   {"operator":"BTW","values":[t0_ms,t1_ms],"type":"roClosedTime","key":"roClosedTime","field":"roClosedTime"},
   {"field":"status","values":["DEFERRED"],"operator":"IN"}],
 "pageInfo":{"start":0,"rows":200}}
```
Response: `data.reportData.count` + `data.reportData.hits[]`. Paginate by
`start += hits.length` until start >= count — pageInfo pagination WORKS here (200/page,
15 pages for 2,915, ~300ms delay between pages was fine).

## Hit record fields (the useful ones)

- `concern` = the service name/description (free-text advisor concern — normalize!)
- `opcodes` = array (often ["MISC"] or ["REC"], not a real opcode — concern is the name)
- `jobAmounts.estimateAmount` = declined-job estimate in **CENTS** (/100). `totalAmount` also cents.
- `roNo`, `roId`, `roClosedTime`, `payType`
- `primaryAdvisorId` (UUID — resolve via OpenAPI /users/{id} when quota returns)
- `customer` = {name, firstName, lastName, email, phone} — full contact info for campaign lists
- `vehicle` = {vin, year, makeLabel, model, trim, mileageIn}
- `severity`, `mpvi`, `comebackCompleted`, `lastDeferredBy/Time`,
  `approvedOrDeferredDetails` = {comment, communicationMode, communicatedDate}

## Recipe

1. :9223 alive + correct dealer: check `localStorage.currentActiveDealerId`; switch via the
   dealer pill UI (mouse click x≈1130,y32 → click store row center; localStorage set does NOT work).
2. Capture headers: arm a setRequestHeader hook filtered to `recommendation/search`, then
   SPA-navigate (history.pushState + PopStateEvent) away and back to
   `/core/reports/service/deferredServices` to force the app to fire the XHR → `window.__H`.
3. Harvest in-page: async loop with the body above, accumulate `window.__DEF[h.id]={...trimmed fields}`.
4. Ferry out: `window.__S=JSON.stringify(window.__DEF)`, pull in 15,000-char slices via /eval
   (eval truncates ~20k), reassemble in Python. Use hermes_tools json_parse for curl output.
5. Aggregate: normalize `concern` (strip RECOMMENDATION:/REC: prefixes, collapse whitespace,
   uppercase) — free text means near-dupes remain ("WHEEL ALIGNMENT" vs "4 WHEEL ALIGNMENT");
   note that to the requester. Group → count, avg $ (estimateAmount/100), total $.
6. Output CSV to /home/itadmin/tekion-reports/data/ (persistent — NOT ~ which is ephemeral).

## Pitfalls

- estimateAmount is CENTS (standard Tekion) — /100 or you'll report $1M declines.
- Some records have blank concern → "(NO DESCRIPTION)" bucket; exclude from top-N, mention count.
- OpenAPI has NO recommendations endpoint — this internal API is the only programmatic path.
- Fresh page loads wipe window hooks — use pushState SPA nav, not location.href.
- Reference run files: /home/itadmin/tekion-reports/data/bc-deferred-90d-raw-2026-07-08.json,
  BC-declined-services-top20-90d-2026-07-08.csv.
