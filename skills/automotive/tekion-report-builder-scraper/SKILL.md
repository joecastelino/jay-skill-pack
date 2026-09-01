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

## Pitfalls
- `~` in terminal = `/home/itadmin/.hermes/profiles/jay/home/`; scripts live at
  REAL `/home/itadmin/tekion-reports/`.
- Session expires ~2h10m — always run login.py (reuse-if-alive) first.
- The detail page search box in the report LIST view is global search — typing
  a report name there opens RO global search, not the report. Navigate by
  direct URL instead.
- Slack PDF attachment downloads failed for the user; PNG inline worked.
  Deliver PDFs by email through Stacey.
