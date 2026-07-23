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
trigger: report builder, custom report, menu sales report, Tekion report scrape, scorecard, SCT Menu Sales
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

### Report data is DOM-only. No data API exists.
- Playwright `page.on("response")` captures **zero** report-data calls on the
  detail page (service worker swallows traffic; `service_workers="block"` +
  `ctx.route("**/*")` made it WORSE — page rendered blank with 0 calls).
- In-page `fetch()` of reportbuilder endpoints → 500/405. Blind endpoint
  probing (`/execute`, `/data`, `/preview`, `/generate`) → all 404/405.
- THE answer: let the SPA render, then parse `document.body.innerText`.

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
