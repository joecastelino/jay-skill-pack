---
name: tekion-report-builder-scraper
description: >
  Scrape any Tekion Report Builder CUSTOM report (e.g. "SCT Menu Sales Opened")
  headlessly — find the report id, open it under the right dealer, expand
  grouped rows, parse to JSON, render a manager-ready scorecard (PNG+PDF), and
  email it via Stacey. Use whenever Joe/managers want recurring Tekion report
  data without downloading PDFs from Tekion's emailed reports.
triggers:
  - scrape tekion report
  - report builder
  - sct menu sales
  - custom report
  - menu sales report
  - tekion report scrape
  - scorecard
---

# Tekion Report Builder Scraper

> **NOTE (2026-06-15):** For the daily "SCT Menu Sales Opened" report
> specifically, this Report-Builder DOM path (`sct_menu_sales.py`) is now
> **DEPRECATED**. The live pipeline is `sct_menu_sales_api.py` (LIVE OpenAPI,
> no RB lag) — see skill **sct-menu-sales-api-scorecard**. Use THIS skill only
> for OTHER custom Report Builder reports, or an explicit cross-check.

Production pipeline (proven 2026-06-12, "SCT Menu Sales Opened", 8/8 records):

1. `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 /home/itadmin/tekion-auth/login.py` — refresh session if stale
2. `/home/itadmin/tekion-reports/sct_menu_sales.py` — scrape → JSON in `~/tekion-reports/data/` (real path `/home/itadmin/tekion-reports/`)
3. `/home/itadmin/tekion-reports/render_scorecard.py` — JSON → PNG + PDF scorecard
4. Email PDF via Stacey: `~/bin/ask-agent stacey "...email PDF at <path> to <addr>..."` (Slack PDF uploads can fail for the user — email is the reliable channel)

## CRITICAL FINDINGS — do not rediscover these

### ~~Report data is DOM-only~~ — **WRONG, CORRECTED 2026-09-01. A DATA API EXISTS.**

The old claim ("no data API, parse innerText") was FALSE — blind endpoint
probing missed it because the path needs a **query string** and the **entire
reportConfig object as the body**. DOM scraping is now a FALLBACK only.

```
POST /api/reportbuilder/u/execute/withOptions?preview=false
{"reportConfig": <the FULL hit object from report/search, unmodified>,
 "reportExecutionOptions":{"sort":[],"filters":[],"searchText":"",
   "groupBy":[],"includeFields":[],"excludeFields":[],
   "pageInfo":{"start":0,"rows":500}}}
```
Returns `data.count`, `data.hits[]` (full row objects), `data.projections`
(the KPI totals), `data.groups[]`. Paginate with `pageInfo.start` += 500.

**How to find the endpoint if it ever moves:** hook `window.fetch` BEFORE
navigating (`nav()` then hook then `pushState`), because the report call is
FETCH not XHR — an XHR-only hook captures nothing and produces the false
"no API exists" conclusion. Capture `.u` + `.b` of every call.

#### Date-window override — only ONE filter shape works
Replace the report's own date filter (drop by `fieldKey`, then push):
```js
{fieldKey:"RO_CLOSEDTIME", dataSource:<cfg.dataSource>, field:null,
 values:[startMs,endMs], type:"ADVANCED", subType:"FILTER_RULE",
 operator:"BTW", booleanOperator:"AND", period:null, filterConfigs:null,
 relativeDate:0, groupExpandFilter:false, relativeDateType:null}
```
- `type:"DATE_RANGE"` + `operator:"BTW"` → **400 unexpected.error**
- `type:"DATE"` + `operator:"BETWEEN"` → **400**
- editing `relativeDate` on a `DATE_RELATIVE/LAST_MONTH` filter → **silently
  ignored**, returns the same numbers for 0/1/2
- epoch **seconds** → 0 rows; `"YYYY-MM-DD"` → wrong count. Use **epoch ms**
  (ISO-8601 with offset also works).

VERIFY equivalence before trusting an override: run the report BOTH natively
(untouched config) and with your explicit window for the same period — they
must match exactly. Mine did (Aug 796/362.1 both ways).

#### ⚠️ Report Builder is a STALE ES INDEX — always check before reporting
Its index lags **4–7 days, and the lag differs per dealer**. Symptom: the tail
of the month returns **zero** rows while the store was demonstrably open.
- Check freshness: `max(hit.ingestionTime)` across the rows.
- Cross-check the same window against a live source (advisor-performance
  `summary`). Real case: report returned 0 records for Aug 26–31 at 3 stores
  while live data showed **1,248 / 1,508 / 1,293** ROs closed in that window.
- Tell the user the number matches their screen but understates the month.

---

## "MY REPORT ISN'T WORKING" — run this triage IN THIS ORDER (2026-09-01)
Users say "broken" for four very different things. Diagnose by API in ~5 calls;
do NOT open the UI, and do NOT rebuild anything until you know which one it is.

**1. Is the config structurally incomplete?**
`dataSource is None` on the hit = a half-finished report (TL had 8 of 82 like
this: "ROs in Service", "GSM sold match", "FILTERS SOLD THROUCH ROS"…). Those
have null `fields`/`filterConfigs`/`groups` too and can never render. Nothing to
fix server-side — it was never built.

**2. Is the index stale?** (most common — this was the TL TAC answer)
Run the report NATIVELY (untouched config) and histogram the rows:
```python
ing = Counter(ts(x['ingestionTime']) for x in hits if x.get('ingestionTime'))
cl  = Counter(ts(x['roClosedTime'])  for x in hits if x.get('roClosedTime'))
print('max ingestion', max(ing), '| closed range', min(cl), '->', max(cl))
print('tail:', sorted(cl.items())[-8:])
```
TL "SCP OP Code-ToyotaCare (TXM)": 563 rows, max ingestion **8/24**, latest
closed RO **8/22** — the last 9 days of August were simply absent. The report
"works"; the index is 9 days behind. **Report the gap in days, not just "stale."**

**3. Does one filter now match NOTHING?** Bisect by dropping filters one at a
time and comparing counts — a filter whose stored VALUE drifted out of the data
silently zeroes the report:
```python
for keep_cat in (True, False):   # drop the suspect filter
    ...  # same config minus RO_OPERATION_CATEGORY
```
TL case: `RO_OPERATION_CATEGORY EQUALS "Vehicle"` → **0 rows**; drop it → 99 rows.
The operations now come back as category **`MAINTENANCE`**, so the saved value no
longer exists. A report can sit at 0 for months this way and look "broken."

**4. Does the report actually filter what its NAME says?**
Always read `filterConfigs` out loud to the user before rebuilding. TL's report
is named *ToyotaCare (TXM)* but filters `RO_OPERATION_OPCODE STARTS_WITH "TEK"` —
i.e. the TEK menu family, **not** the TAC opcodes. Get the real opcode family from
`POST /api/service-module/u/opcode/search {"searchText":"TAC","pageInfo":{"start":0,"rows":100}}`
(TL: 16 active — `TAC` + `TAC5,10,15…80`). Confirm with the user WHICH set they
mean before shipping numbers — two different reports were wearing one name.

### Reading operation-level $ and hours off a REPAIR_ORDER report
`projections` (the KPI totals) can be **0.0 even when the rows have money** —
at TL, `REPAIRORDER_OPERATION_LABOR_PRICE__SUM` / `PARTS_PRICE__SUM` /
`LABOR_COST__SUM` all returned `0.0` while
`REPAIRORDER_JOB_OPERATION_BILLING_TIME__SUM` was correct (245.7). **Never trust
a 0.0 projection — sum off `hits[]` client-side.**
Each `REPAIR_ORDER` hit carries nested lists (this is the whole RO, not one op):
`repairOrderJobs`, `repairOrderJobOperations`, `repairOrderJobOperationParts`,
`repairOrderOperationTechnicians`, `repairOrderTechClockIns`,
`repairOrderTechFlagHours`, `recommendations`, `repairOrderNotes`,
`customerDetails`.
On `repairOrderJobOperations[]`: `opcode`, `jobOpCodeDescription`, `billHours`
(HOURS), `billingRate`, **`laborAmount` = CENTS** (14011 → $140.11),
`operationFlagHours`, `operationJobHours`, `storyLineText`, `roMileage`.
`labourTimeInSeconds` is **misnamed — it is HOURS** (1.6), matching `billHours`.
The per-op `opcodeLaborPrice/opcodeLaborGross/costAmount` fields are usually
`null` — that's why the projections come back 0; cost/gross must come from the
OpenAPI (`labor.costAmount`) instead.
**Filtering a whole-RO hit set: you must re-filter the nested ops yourself.**
A report filtered to opcode `TAC*` still returns ROs with all 9 of their
operations attached; summing blindly counts unrelated work (the RO-level vs
operation-level inflation trap above).

#### Operation-level vs RO-level — the #1 cause of "my number is too high"
`dataSource:"REPAIR_ORDER"` aggregates **whole ROs**; a report on
`REPAIR_ORDER_OPERATION` returns **individual operation lines**. Summing RO
hours for an opcode filter inflates the answer (it counts every hour on any RO
that merely *touches* the opcode). Real case: 76.04 (RO-level) vs 43.5
(op-level) vs 35.20 (user's true figure).
- Hours field on operation rows = **`billingTimeInSeconds`** (misnamed — it is
  already HOURS, e.g. `1.4`; `laborTimeInSeconds` matches it). `projections`
  will NOT contain hours unless the report defines that metric — sum the field
  off `hits[]` client-side instead.
- Find an op-level template to clone: search reports and filter
  `dataSource==="REPAIR_ORDER_OPERATION"`. Its opcode field is
  **`ROPERATION_OPCODE`** (note: no `_` after RO) and pay type is `JOB_PAYTYPE`.
- Building a config from scratch → 500. **Clone an existing report and mutate
  only `filterConfigs`.** Same for adding metric fields — a hand-built
  `fields`/`kpiMetrics` array 500s.
- Useful row fields for diagnosis: `laborName`, `laborDescription`
  (e.g. `"Warranty Care/Care Plus"` / `"50% Labor Rate"`), `opcodeDescription`.

### Finding the report id + full config (this part DOES have an API)
Capture internal headers once from a Playwright session (`page.on("request")`
on any `/api/reportbuilder/` call), then replay with urllib. Required headers
include `tekion-api-token`, `dealerid`, `tek-siteid: -1_<dealerid>`,
`original-tenantid`, `userid`, `roleid`, `clientid: web`, `applicationid: ARC_NA`.
```
POST /api/reportbuilder/u/report/search   (dealerid header = store, e.g. 876 SCT)
{"sort":[{"field":"modifiedTime","order":"DESC"}],"filters":[],"searchText":"<name>",
 "searchFields":["name"],"pageInfo":{"start":0,"rows":50},"includeDeleted":false}
```
→ hits contain id, dataSource, full `filterConfigs`, `groups`, `fields`,
`schedulingConfigs`. This is how you verify WHAT a report filters on.

#### 30-second header bootstrap (do this FIRST — 2026-09-01)
`/home/itadmin/tekion-reports/api-headers-live.json` exists but its
`tekion-api-token` is almost always **STALE** → `401 AUTH401
"Login user session is expired."` Don't re-capture via Playwright; graft a live
token off the `:9223` browser and retarget the dealer:
```python
r=subprocess.run(["curl","-s","-m","15","http://127.0.0.1:9223/eval",
  "-H","Content-Type: application/json",
  "-d",json.dumps({"js":"localStorage.getItem('t_token')"})],capture_output=True,text=True)
tok=json.loads(r.stdout)["result"]
h=dict(json.load(open('/home/itadmin/tekion-reports/api-headers-live.json')))
h['tekion-api-token']=tok
h['dealerId']='1092'; h['tek-siteId']='-1_1092'   # target store, NOT whatever :9223 is on
h['Content-Type']='application/json'
```
The `:9223` **/eval endpoint takes `{"js": ...}` — `{"expression": ...}` returns
`{"error":"js is required"}`.** The browser's own active dealer is irrelevant;
these are plain header-scoped REST calls, so no dealer switch / no UI popover
needed just to read or execute a report. (Confirmed working from BC-1251
browser against TL-1092.)

#### Response is nested: `data.esResponse`, not `data`
`report/search` → `out["data"]["esResponse"]["hits"|"count"]`.
`execute/withOptions` → `out["data"]["hits"|"count"|"projections"|"groups"]`.
Different envelopes on the two calls — `data['hits']` on search returns nothing
and looks like "0 reports at this dealer."

#### DON'T search by name — list everything and grep locally
`searchText` + `searchFields:["name"]` is token-ish and unreliable: at TL,
`"TOL"`→16 hits, `"SCP"`→5, but **`"TAC"`, `"Toyota"`, `"Care"` all → count 0**
even though `SCP OP Code-ToyotaCare (TXM)` exists. Pull the whole list with
`searchText:""` (paginate `pageInfo.start` += 50) and filter in Python. Use
`includeDeleted:true` to see soft-deleted copies (TL: 82 active vs 90 total) —
a manager's "broken report" is sometimes a deleted twin of a live one.
To find which report uses an opcode, grep the configs you already pulled:
`[x for x in hits if 'TAC' in json.dumps(x.get('filterConfigs') or []).upper()]`.

### Dealer context is everything
- Custom reports are dealer-scoped. Browser lands on BC (1251) by default; the
  report list/detail only shows the active dealer's reports. Direct preview URL
  under the wrong dealer silently bounces to the list.
- Switch dealer FIRST (proven popover method from inject_and_go.py: click
  `[class*='dealerSelect']`, then JS-click the leaf element containing the
  dealer name), THEN `page.goto` the detail URL:
  `https://app.tekioncloud.com/report-manager/report/<id>/reportType/custom/detail`
- Save per-dealer storage_state (e.g. `/tmp/sct-state.json`) to skip re-switching.

### The grid is NOT ag-grid — Tekion custom table
- Rows: `[class*=tRow_bodyRowContainer]`; group rows show label `Name (N)`.
- Expanders: `[class*=expander_expansionCellSize]` (one per group row).
  ag-grid selectors (`.ag-row`, `.ag-group-contracted`) match NOTHING.
- **Expansion strategy that works** (two failed first): loop — re-read group
  state fresh each round, find first group whose visible child-row count < its
  `(N)`, real `page.mouse.click()` its expander, verify count grew, repeat.
  Blind multi-click sweeps TOGGLE earlier groups shut as the table re-renders.
- Wait for `"Total row count"` in innerText before touching anything (poll up
  to 80s; Tekion is slow). `"N Record(s)"` on page = ground truth; scraper must
  assert parsed rows == N (`complete: true`).

### Parsing innerText
Flat line dump after expansion: group lines `Name (N)`, then per row 11 lines:
date(MM/DD/YY), RO#, opcode, year, make, model, mileage, then 4 money cells
($Labor Gross, $Parts Gross, $Labor Price, $Parts Price). Layout is
field-count-sensitive — verify with regex guards (date, digits, `^\$[\d,]+\.\d{2}$`).

## Scorecard rendering
`render_scorecard.py`: HTML (dark theme, KPI boxes) → Playwright screenshot
(PNG) + `pg.pdf(width=...px, height=scrollHeight, print_background=True)`.
- KPI labels must mirror Tekion's emailed report: "Opcode Labor Gross (SUM)" /
  "Opcode Parts Gross (SUM)" — managers compare against Kevin's Tekion email.
- Include ALL report columns (labor/parts gross AND price + total); first
  version clipped the rightmost column — use `table-layout:fixed` + wide body
  (1150px+) and size the PDF page to the body width.
- Vision-verify the PNG before sending (`vision_analyze`: check KPIs present,
  rightmost column not cut off).

## Official OpenAPI is NOT an alternative here
AMG's prod key (`/home/itadmin/tekion-api/config.json`, client in
`tekion_client.py`) — CORRECTION 6/12/26: the key DOES cover repair-orders and
parts via colon-action paths (POST /repair-orders:search, nested /jobs/
/operations/parts; POST /parts-inventory:search). Old 403/404s were wrong
paths. See skill `tekion-openapi-repair-orders`. UI scraping is now only
needed for things the API truly lacks (e.g. Report Builder custom reports
themselves, GL until correct path found). RO-level
reporting must go through Report Builder scraping or the session scraper.
The partner docs portal (apc.tekioncloud.com) needs its own login we don't have.

## Cross-store: reports are per-dealer COPIES with different definitions
The same conceptual report exists separately at each store, with a different
id, different name, and **different filters**. Never assume one store's copy
applies fleet-wide — search each dealer and diff `filterConfigs`.
Real case: `SCP-Toyota Care 2.0` = SCT `6a45095462e5ff667243d553` (created
2026-07-01, category `["Vehicle","Maintenance"]`) vs BT `66227a89735ee81a7ca35bad`
(created 2024) vs TL, which names it `SCP OP Code-ToyotaCare (TXM)`
(created 2023, `["Vehicle"]` only, and has **no billable-hours field at all**).

A report **cannot reproduce months before its own `createdTime`** — SCT's copy
was created 7/1/2026, so querying June through it returns a plausible-looking
but wrong number (208.80 vs the true 744.96). ALWAYS check `createdTime`
before back-testing, and note `createdTime == modifiedTime` proves the
definition was never edited (rules out "someone changed the filter").

## Adapting to a new report/store
Copy `sct_menu_sales.py`; change REPORT_ID (find via report/search POST),
DEALER_NAME, and the per-row field layout in `parse_report_text` (count the
report's columns; money-cell count = number of $ fields). Everything else
(login, switch, expand, verify) is generic.

## Replacing a stale RB report with a LIVE OpenAPI equivalent (the real deliverable)
Per Joe's automation mandate: once RB is proven unreliable, **stop diagnosing the
screen and ship an API-sourced replacement** — don't hand back a config fix.
Reference implementation: **`/home/itadmin/tekion-reports/tl_tac_api.py`**
(`tl_tac_api.py START END [dealer_key]`, opcode-family report: ops / bill hours /
labor sale / gross per opcode + advisor id + pay type per line).
Recipe, reusable for any opcode-family report:
1. `closedTime BTW [lo,hi]` + `status IN [CLOSED,INVOICED]` via
   **recursive bisection** — `pageNumber` is ignored and `nextPageToken` drifts
   out of the window (see tekion-openapi-repair-orders). Dedupe on `documentId`.
2. Prefilter on the **free OPCODE tags** in the search result; only fan out
   jobs→operations on candidates (TL Aug: 99 candidates out of the full month).
3. Sum `labor.saleAmount`/`costAmount` (**CENTS**) and bill hours per opcode.
4. Windows are on **closedTime**, matching the report's `RO_CLOSEDTIME` filter,
   so the two are directly comparable — always quote the stale-vs-live delta.
**Runtime:** a full month exceeds the 180s foreground terminal cap (and the 300s
`execute_code` cap). Launch with `terminal(background=true,
notify_on_complete=true)` writing to a log — do NOT retry it in the foreground.

## Pitfalls
- `~` in terminal = `/home/itadmin/.hermes/profiles/jay/home/`; scripts live at
  REAL `/home/itadmin/tekion-reports/`.
- Session expires ~2h10m — always run login.py (reuse-if-alive) first.
- The detail page search box in the report LIST view is global search — typing
  a report name there opens RO global search, not the report. Navigate by
  direct URL instead.
- Slack PDF attachment downloads failed for the user; PNG inline worked.
  Deliver PDFs by email through Stacey.
