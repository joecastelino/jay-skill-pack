---
name: tekion-tech-clock-time-by-opcode
description: >
  Get ACTUAL technician clocked time (punch time) per OPCODE / per RO / per tech
  from Tekion via the internal rosearchservice visibility-dashboard TECH_CLOCK
  datasource, and join it against billed hours to find over-clock / unapplied-time
  gaps by opcode. Use when Joe asks "which opcode has the most unapplied time",
  "actual vs billed hours by opcode", tech clock time analysis, or proficiency
  drill-downs below the per-technician grain. Verified SV (826) 2026-07-20.
triggers:
  - unapplied time by opcode
  - actual clocked hours opcode
  - tech clock report
  - over-clock gap
  - TECH_CLOCK datasource
---

# Tekion — Actual Clock Time by Opcode (TECH_CLOCK datasource)

## The definitional trap (state this to Joe FIRST)
Tekion "Unapplied Hours" (Tech Performance report) = attendance time a tech is
clocked in but NOT clocked onto any RO job. By strict definition it has **no
opcode**. When Joe asks "which opcode has the most unapplied time", the
answerable question is: **which opcode eats the most ACTUAL wrench time vs.
billed/flagged time** (over-clock gap). Confirm the framing, then use this method.

## What does NOT work (all verified dead ends 2026-07-20)
- ❌ Public OpenAPI `/repair-orders/{rid}/clock-entries` → 404 (pilot app version;
  in specs but blocked at all stores until app update approved).
- ❌ Tech Performance (`/core/reports/service/tech-performance`) — per-TECH only.
  Its API = `POST /api/service-module/u/reporting/technician` body
  `{"reportName":"FLAG_TIME_REPORT","reportGroup":"FLAG_REPORT","metrics":[],
  "pageInfo":{"start":0,"rows":50},"filters":[{"field":"payDay","operator":"BTW",
  "values":[ms0,ms1]}]}` → `data.lineItems[]` per techId with
  `unAppliedTimeInSeconds`, `clockTimeInSeconds`, `flagTimeInSeconds`,
  `attendanceTimeInSeconds`, `assignedBillingTimeInSeconds`, $ in cents.
  `groupBy` param → 404. `FLAG_TIME_DETAIL_REPORT` / `CLOCK_TIME_REPORT` return
  the SAME shape (no detail rows). `reporting/search` with FLAG reportNames →
  count 0 always.
- ❌ Internal `/api/service-module/u/ro/{id}` operations `totals.actualTimeInSeconds`
  → null/0 on every op checked (119 ops, 20 ROs). Not populated at op level here.
- ❌ In-page fetch or bare replay with old cached headers → 401 session expired.

## What WORKS — visibility-dashboard TECH_CLOCK
SV has a custom report **"Ro Actual Time Report"** (`SVD_RO_ACTUAL_TIME_REPORT`,
docId `691de96e06475874eb137a1b`) built on datasource **TECH_CLOCK** = one row
per clock punch, fields include: `roNo, roId, opcode, techId, inTime, outTime,
roundedOffTimeInSeconds, jobNumber, payType, departmentId, makeId, concern,
adjustmentReason, documentType`.

**Endpoint:** `POST https://app.tekioncloud.com/api/rosearchservice/u/visibility-dashboard/generate-summary-report`
Body = ARRAY of one request object (capture a live one and mutate — see below):
```json
[{"dataSource":"TECH_CLOCK",
  "filters":[{"key":"inTime","field":"inTime","values":[ms0,ms1],"operator":"BTW"}],
  "defaultFilters":[{"key":"documentType","field":"documentType","values":["CLOCK_ACTUAL"],"operator":"IN"}],
  "groups":[{"key":"opcode","field":"opcode","metrics":[
     {"field":"roId","function":"CARDINALITY",...},
     {"field":"roundedOffTimeInSeconds","function":"SUM",...}],
    "groupType":"FIELD","rows":2000,"start":0,...}],
  "includeFieldKeys":[...], "pageSize":50, ...}]
```
Response: `data.headerRowList` + `data.rowList[]`, each row
`reportCellList[] = [{key,displayValue},...]` — first cell = group value
(row 0 = "TOTAL"), metric cells keyed by metric UUID. Hours metric comes back
already in HOURS (float), not seconds.

### Key mechanics
- **Swap the group field freely**: `techId`, `opcode`, `roNo` all work.
  `groups:[]` (no grouping, hoping for raw rows) → 500. **subGroups WORK**
  (e.g. roNo → opcode) for two-level breakdowns.
- **documentType: filter to `CLOCK_ACTUAL` ONLY.** The datasource also holds
  `CLOCK_DERIVED` with identical hours — including both DOUBLE-COUNTS (verified:
  624.36 + 624.36 = 1248.72).
- Sibling endpoints: `GET .../visibility-dashboard/report-definition/{docId}`
  (read a custom report's full definition = the query recipe),
  `POST .../lookup/resolve-by-id` `{"lookupByIds":[{"lookUpAsset":"TECH_ID","ids":[...]}]}`
  (techId→name), `POST .../lookup/fetch/all` `{"assetType":"TECH_ID",...}`.
  `generate-detail-report`/`generate-report` → 404; `generate-breakdown-report`
  exists (400 with summary body — different shape, uncracked).
- Report list per store: `GET /api/rosearchservice/u/visibility-dashboard/report-definition/minimal/all?locale=en_US`.
  **The custom report may be store-specific** (SVD_* = SV's). If a store lacks an
  RO Actual Time Report, you can still POST the TECH_CLOCK query directly — the
  datasource is Tekion-native, not report-dependent (unverified at other stores;
  check report-definition/minimal/all first).

## Header capture (the reliable recipe)
Old cached internal headers go stale (401). Capture fresh ones via headless
Playwright + storage_state (NOT the :9223 server — its hooks kept getting lost
to SPA state drift and other-turn navigation):
1. `cd /home/itadmin/tekion-auth && python3 login.py` (refresh storage state).
2. Run a capture script modeled on
   `/home/itadmin/tekion-reports/capture_svd_actualtime_sv.py`:
   headless chromium, `storage_state=/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json`,
   `page.on("request")` filter for the target API path, goto /home, kill pendo,
   switch dealer via pill (verify `currentActiveDealerId`), then **click through
   `/core/reports` → Custom Reports tab → report row**. 
   ⚠️ Direct `page.goto(.../tech-performance)` does NOT fire the report query —
   the SPA needs the click-through from the reports list (FAIL_NO_CAPTURE).
3. Save `dict(req.headers)`; strip `:pseudo`, `content-length`, `accept-encoding`
   before replaying via urllib. Replay works store-wide by keeping the captured
   dealerId (re-capture per store, or try swapping dealerId/tek-siteId headers —
   works for service-module reporting per the deferred-services skill).

## Full unapplied/over-clock-by-opcode workflow (script exists)
`/home/itadmin/tekion-reports/sv_unapplied_by_opcode.py` (adapt store/window):
1. TECH_CLOCK summary grouped by `opcode` → actual clocked hrs + unique ROs per opcode.
2. TECH_CLOCK summary grouped by `roNo` → punched-RO population.
3. OpenAPI `repair-orders:search` `documentNumber IN [50-batch]` → documentIds.
4. Internal `/api/service-module/u/ro/{id}` fan-out → sum
   `operations[].billingTimeInSeconds` per opcode (billed hours; /3600).
5. Join: `gap = clocked − billed` per opcode, rank desc. Also emit hrs/RO.
Run as BACKGROUND process (fan-out of hundreds of ROs exceeds the 300s
execute_code limit). Output JSON → `~/tekion-reports/data/`.

## Companion facts
- Tech Performance API money fields are CENTS; TECH_CLOCK hours metric is HOURS.
- Tech Performance UI default = current week from Sunday by FLAG DATE; its API
  date filter field is `payDay`.
- SV custom reports also include Advisor Performance Report(3) and Service Sale
  Report 3.0 on the same visibility-dashboard framework — same replay method
  applies to any of them.
