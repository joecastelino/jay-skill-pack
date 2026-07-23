---
name: tekion-clock-time-by-opcode
description: >
  Build an "actual tech clocked time vs billed time BY OPCODE" report (over-clock /
  unapplied-time-at-opcode-grain) for any Tekion store. Uses the internal
  rosearchservice visibility-dashboard TECH_CLOCK datasource (the engine behind the
  custom "Ro Actual Time Report"), which carries opcode on every clock punch —
  something the standard Tech Performance report cannot do (its Unapplied Hours is
  per-technician only). Verified SV (826) 2026-07-20.
triggers:
  - unapplied time by opcode
  - clocked vs billed hours opcode
  - tech clock time report
  - over-clock opcode
  - ro actual time report
---

# Tekion — Actual Clock Time vs Billed Time by Opcode

## When to use
Joe asks "which opcode has the most unapplied time?" or wants to know where tech
wrench time is going vs what gets billed/flagged. Strict Tekion "Unapplied Hours"
(Tech Performance report) = attendance-clocked but on NO job → has no opcode by
definition. The opcode-grain equivalent = **over-clock gap: actual job-clock punches
per opcode minus billed hours per opcode**. That's what this builds.

## Key discovery (2026-07-20, SV)
- Standard Tech Performance report (`/core/reports/service/tech-performance`, internal
  `POST /api/service-module/u/reporting/technician` with reportName FLAG_TIME_REPORT)
  returns per-TECH lineItems only (`unAppliedTimeInSeconds`, `clockTimeInSeconds`,
  `flagTimeInSeconds`...). `groupBy` param → 404. No opcode grain. Amounts in CENTS,
  times in SECONDS. `/reporting/search` with FLAG report names returns count 0 — dead end.
- **The gold: `POST /api/rosearchservice/u/visibility-dashboard/generate-summary-report`**
  with `dataSource: TECH_CLOCK` — each clock punch document carries
  `roNo, opcode, techId, inTime, outTime, roundedOffTimeInSeconds, jobNumber, payType,
  documentType`. Group by ANY of those fields.
- Discovered via SV custom report "Ro Actual Time Report"
  (reportId SVD_RO_ACTUAL_TIME_REPORT). Custom-report definitions are listed at
  `GET /api/rosearchservice/u/visibility-dashboard/report-definition/minimal/all?locale=en_US`
  and full definition at `.../report-definition/{documentId}` — the definition JSON
  shows the datasource + fields (that's how TECH_CLOCK was found).
- OpenAPI has NO clock data: `/repair-orders/{id}/clock-entries` 404 (pilot-blocked),
  operations' `totals.actualTimeInSeconds` is null/0 everywhere.

## Method (proven end-to-end)

### 1. Capture headers by replaying the report in headless Playwright
Internal API needs the app's axios headers; capture with a request listener while
opening `/core/reports` → Custom Reports → "Ro Actual Time Report" (or Tech
Performance for the technician endpoint). Script:
`/home/itadmin/tekion-reports/capture_svd_actualtime_sv.py` (SV; storage_state from
login.py, dealer-switch via pill, filters on `generate-summary-report`).
Saves headers+body to `/tmp/svd_actualtime_capture.json`.
- Run `login.py` first (tekion-auth) if state stale — old headers give 401
  "Login user session is expired".
- MUST navigate /core/reports → click rows; direct goto of the report URL does NOT
  fire the data request (row_not_found path also fails silently).

### 2. Query the summary endpoint directly (replay + swap group field)
Take the captured body verbatim, change only `groups[0].key/field` and the
`filters[0].values` date range. Group fields verified: `techId`, `opcode`, `roNo`,
`documentType`. Metrics: CARDINALITY(roId) + SUM(roundedOffTimeInSeconds) (=hours,
already decimal hours in displayValue).
- `defaultFilters` documentType IN [CLOCK_ACTUAL] — keep it! Without it rows double
  (CLOCK_DERIVED mirrors CLOCK_ACTUAL, 2x hours).
- Response: `data.rowList[].reportCellList[]` — first row is TOTAL. displayValue for
  group cell + metric cells (metric keys are the UUID keys from the body).
- Do NOT strip groups to [] (500), don't invent dataSources (TECH_FLAG etc → 500).
- subGroups work (roNo → opcode nested) but rows explode; per-RO opcode detail is
  easier via the internal RO fan-out below.

### 3. Billed hours per opcode: internal RO detail fan-out
`GET /api/service-module/u/ro/{documentId}` (same headers) →
`data.jobs[].operations[]` has `opcode` + `billingTimeInSeconds` (and laborAmount
cents). Get documentIds by batching the punched roNos through OpenAPI
`repair-orders:search` `documentNumber IN [≤50]`. ~450 ROs ≈ 3 min at 0.25s pace.

### 4. Join and rank
gap = clocked − billed per opcode, sort desc. Full script (adapt store):
`/home/itadmin/tekion-reports/sv_unapplied_by_opcode.py` → writes
`data/sv-unapplied-by-opcode-julmtd.json`.

## By-TECHNICIAN cut (verified SV 2026-07-20, Joe's follow-up)
Two-source join gives the full per-tech picture:
1. **Per-tech unapplied/attendance/flag**: replay Tech Performance
   `POST /api/service-module/u/reporting/technician` (headers+body in
   `/tmp/tekion_tech_headers_sv.json`, pop `__post_body`), set
   `filters[0].values=[start,now]`, `pageInfo.rows=100`. lineItems carry
   `attendanceTimeInSeconds, flagTimeInSeconds, unAppliedTimeInSeconds,
   clockTimeInSeconds, assignedBillingTimeInSeconds, proficiencyPercentage`.
   techId "-1" = TOTAL row.
2. **Who clocks on a given opcode**: on generate-summary-report, **subGroups do
   NOT nest** — adding a subGroup returns the same flat parent rows (silent
   no-op). Instead APPEND an opcode filter and keep the techId group:
   `body[0]["filters"].append({"key":"opcode","field":"opcode","values":["REC"],"operator":"IN"})`
   — one query per opcode of interest (fast, ~0.5s each).
3. **Resolve tech UUIDs → names in ONE call** (don't fan out OpenAPI /users —
   raw urllib with `access_token` header 401s "Missing mandatory headers"; needs
   `Authorization: Bearer` via tekion_client.api_get, and even then may not have
   these users): the app's own lookup is better —
   `POST /api/rosearchservice/u/visibility-dashboard/lookup/resolve-by-id`
   body `{"lookupByIds":[{"lookUpAsset":"TECH_ID","ids":[<uuids>]}]}` with the
   SAME captured headers → `data.lookUpResponse[0].lookUpCellResponse[]`
   `{id, displayValue}`. Also `lookup/fetch/all` with
   `{"assetType":"TECH_ID","dynamicFieldOfPayload":{"PAGE_START":0,"SEARCH_TEXT":"","SITE_ID":"-1_<dealer>"}}`
   lists all techs.
Output example: `data/sv-unapplied-by-tech-julmtd.json`. Reading: unapplied% =
unapplied/attendance; a tech with attendance>0 and flag=0 = not flagging at all
(new hire/porter — ask, don't accuse); negative unapplied (flag > attendance) =
missing attendance punches.

## Per-RO cut / "biggest ROs" (verified SV 2026-07-22, Joe's H1-July ask)
- Group by `roNo` = clocked hrs per RO; join billed via the internal RO fan-out
  → **over-clock gap per RO** (clocked − billed). Top offenders pop instantly
  (SV H1 Jul: RO 371517 David Tran 27.1c/10.9b = +16.2).
- **Per-tech per-RO**: subGroups don't nest (silent no-op), but the filter trick
  generalizes — keep `groups[0]=roNo` and APPEND
  `{"key":"techId","field":"techId","values":[<uuid>],"operator":"IN"}` to filters;
  one query per tech (~0.3s each, 14 techs fine). That attributes each RO's clock
  hours to techs.
- Framing for Joe: strict "unapplied" (attendance, no job punch) has NO RO by
  definition — RO gaps explained only ~40 of SV's 513 unapplied hrs; the rest is
  techs in the building not punched on any job (punch discipline). Present both
  the per-tech unapplied table AND the per-RO over-clock table, and say which is
  which.
- Turnkey script (adapt window/store): `/home/itadmin/tekion-reports/sv_unapplied_h1jul.py`
  → data/sv-unapplied-h1jul.json (clock_tech, clock_ro, clock_op, tech_ro, names,
  ro_detail w/ billed_by_op+status). Runs ~6 min for ~335 ROs; launch background.

## Session-staleness traps (burned 2026-07-22)
- Captured headers die with the Tekion session (~2h token): replaying a 2-day-old
  capture = 401. Re-run login.py THEN re-run the capture script to mint fresh
  headers — the capture is cheap (~90s) and is the only reliable refresh.
- **login.py can report ALIVE/REUSED while `.tekion-storage-state.json` is
  actually dead** (browser lands on /login "Username" page, dealer=None →
  capture script exits FAIL_DEALER). The token probe passes but cookies are
  stale. FIX: `login.py --force`, then re-run the capture.
- Replaying `/api/service-module/u/reporting/technician` with OLD headers +
  fresh cookie spliced in still 401s — use the FRESH capture's headers
  WHOLESALE (strip `:`-prefixed pseudo-headers); the rosearchservice capture's
  headers work fine on the service-module reporting endpoint too (same session).
- Capture file shape: `/tmp/svd_actualtime_capture.json` = `{"cap":[{u,body,h},...],"resp":{}}`
  — a LIST; pick the entry whose `u` contains `generate-summary-report`.
- Vehicle year/make/model: OpenAPI repair-orders:search results came back with
  empty vehicle fields for these ROs — don't rely on it for the RO table; RO# +
  tech + status is enough for Joe (he opens ROs himself).

## Pitfalls
- **Leading-zero opcode mismatch**: clock data strips leading zeros off numeric
  opcodes (punches on `1040050`, billing on `01040050`). Normalize
  `opcode.lstrip('0') if opcode.isdigit()` before joining or you get phantom
  gap pairs (+8 on one, −10 on the other).
- Times in seconds everywhere except summary displayValue (already hours).
- Both-direction gaps are meaningful: clocked≫billed = unapplied leak (SV July: REC
  +44 hrs); billed≫clocked = flagging without punching (SV July: MISC −88 hrs) —
  often the same work clocked under one opcode and flagged under another.
- The "Ro Actual Time Report" custom report may not exist at every store; the
  ENDPOINT + TECH_CLOCK datasource should still work with the same replayed body
  shape (headers are per-session, dealerId/tek-siteId headers control store — swap
  `dealerId` and `tek-siteId: -1_<dealer>` like deferred_services_90d.py does).
- 429/500 on visibility-dashboard = retry with backoff; zero OpenAPI quota consumed
  by the summary queries (only the docId lookup touches OpenAPI).

## SV July MTD reference result (2026-07-20)
448 ROs punched, 624.4 clocked hrs vs 867.2 billed on that population.
Worst over-clock: REC +43.9 (125.4c/81.5b, 47 ROs), PDIGOLF +6.2, MPVI +2.1.
Reverse: MISC −88.0 (20.5c/108.5b), PDIDETAIL −23.1, ACCAlignment −18.7.
By tech: David Tran 29.2 REC hrs on 3 ROs + David Salinas 23.6 on 9 = 53 of the
125 REC clock hrs; Ricardo Ruiz Placencia 63.4 attendance / 0 flagged; Devin
Blank best applied ratio (91%). Store-wide 631 unapplied vs 621 flagged hrs MTD.
