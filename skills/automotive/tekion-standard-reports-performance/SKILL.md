---
name: tekion-standard-reports-performance
description: >
  Pull Tekion Standard Reports from the REPORTS module (/core/reports) via the
  :9223 authenticated browser — especially the fixed-ops performance suite
  (Advisor Performance, Tech Performance / proficiency = assigned-billed vs
  attendance hours). Covers the filter funnel (Flag Date range, Make filter),
  Group By, and Export. Use when Joe wants advisor/tech performance numbers, or
  ANY report that is NOT a custom Report Builder report.
triggers:
  - tech performance report
  - advisor performance report
  - proficiency report
  - assigned billed hours attendance
  - standard reports tekion
  - core reports
---

# Tekion Standard Reports — Fixed-Ops Performance

## KEY DISTINCTION (this cost a detour — don't repeat it)
Tekion has TWO separate reporting places. Know which one BEFORE you start:

| | REPORTS module | Report Builder |
|--|--|--|
| Sidebar | **R** (icon href `/core/reports`) | **RB** (`/report-manager`) |
| URL | **`/core/reports`** | `/report-manager/...` |
| Contains | Tekion's ~172 built-in Standard Reports + custom | Joe's custom reports (Menu Sales, Alignment scripts) |
| Advisor/Tech Performance? | **YES (Standard Reports → Service)** | NO — none named perf |
| Attendance/clocked hours | Yes (time-clock sourced) | No (RB can't source time-clock) |

**Joe's fixed-ops performance reports (Advisor Performance, Tech Performance) are
Standard Reports in the REPORTS module, NOT Report Builder.** If someone asks for
these, go straight to `/core/reports`. The custom-report search API and the
`tekion-report-builder-scraper` skill do NOT apply to them.

### URL gotchas
- ✅ `/core/reports` — the Reports module landing (Standard + Custom tabs, category rail).
- ❌ `/reports` — bounces to `/home`.
- ❌ `/report-manager` — that's Report Builder (different thing).
- Find the module URL from the sidebar if unsure: the "R" rail icon's `href` is
  `/core/reports`; "R" at the bottom (`/core/roles`) is Roles, don't confuse them.

## The two reports (verified live SCT/876, 2026-07-01)

### Advisor Performance (Service category)
`/core/reports/service/advisor-performance` — updates every 4-6h ("Last Updated Date"
shown top-left; has a **Refresh** button). This is the advisor side of Joe's workflow.
FULL column order (verified SCT 2026-07-01, 26 cols):
`Name · RO Count · Labor Cost · Labor Sale · Labor Gross · Parts Cost · Parts Sale ·
Parts Gross · Bill Hrs · ELR ($) · Coupon Labor · Labor GP (%) · Sublet Parts Gross ·
Coupon Parts · ELR (%) · ELR/RO · Hrs / RO · GP (%) · Total Gross · Total Sales ·
Total Cost · Parts GP (%) · Sublet Labor Sale · Sublet Labor Cost · Sublet Labor Gross ·
Sublet Parts Sale · Sublet Parts Cost`. **TOTAL row appears FIRST** (store rollup).
- **Top-bar filters** (visible, NOT in the funnel): `Name` (In / Select...),
  `Pay Type Status` (In / Select..., e.g. Closed), `Pay Type Closed Date` (Between /
  date range). The funnel adds Opcode / Pay Type / etc.
- **Joe's number for "ToyotaCare billed hours" = the `Bill Hrs` TOTAL** after applying
  his TAC filter group for the month.

### Tech Performance (Beta) — the PROFICIENCY report
`/core/reports/service/tech-performance`. Joe's "assigned billed hours vs attendance
hours". Defaults to **current week (Sunday start) by FLAG DATE**.

**API behind it (captured SV 2026-07-20):** `POST /api/service-module/u/reporting/technician`
body `{"reportName":"FLAG_TIME_REPORT","reportGroup":"FLAG_REPORT","metrics":[],
"pageInfo":{"start":0,"rows":50},"filters":[{"field":"payDay","operator":"BTW","values":[ms0,ms1]}]}`
→ `data.lineItems[]` per techId (techId "-1" = TOTAL row) with all timeInSeconds fields
incl `unAppliedTimeInSeconds` + $ in CENTS. PER-TECH ONLY — `groupBy` → 404, detail
reportNames return the same shape. For opcode-grain clock time use skill
`tekion-tech-clock-time-by-opcode` (TECH_CLOCK visibility-dashboard datasource).
GOTCHA: replaying this API needs fresh headers captured by CLICKING through
/core/reports → the report row; a direct page.goto of the report URL doesn't fire the query.
Columns in order:
`Technician Name · Attendance Hours · Actual Hours · Flagged Hours ·
Assigned Billed Hours · Proficiency % · Efficiency % · Unapplied Hours ·
Daily OT Hours · Double OT Hours · Employee No · (Attendance/Flag)% · Productivity %`
- **TOTAL row at the TOP** of the table (store rollup).
- Proficiency % is computed by Tekion (roughly Flagged vs Attendance). Joe cares
  about **Assigned Billed Hours vs Attendance Hours** specifically.

## Navigating & reading (all via :9223, authenticated)

1. Auth + be on the RIGHT dealer first (see `tekion-autonomous-login` /
   `tekion-sitemap`). Default after login = BC 1251 → switch to target store.
2. `POST /navigate {url:"https://app.tekioncloud.com/core/reports"}`, sleep 6.
3. Filter to a category to shrink the list: click the left-rail category text
   (e.g. `Service`) — match `el.textContent.trim()===\"Service\" && rect.x<300`.
4. Open a report: click its name row (`textContent===\"Tech Performance\" && rect.x>200`).
5. Read the grid from `document.body.innerText` — rows are newline-delimited
   (Technician name, then the numeric columns in order). The TOTAL row appears first.

## Filters — the funnel (this is where Make + date range live)

- The filter trigger = a funnel icon with class **`root_filterTrigger_icon`** at the
  TOP-LEFT of the report toolbar (~x101, y165 on SCT). It is NOT in innerText —
  find by selector, click via `/mouse` (see click note below).
- It opens an **ant-popover** (`.ant-popover` containing text "Apply") — the
  **filter group**. Rows are `field + operator + value`:
  - **Flag Date** — operator **Between** — set the date range HERE (the report has
    no top-bar date picker; the range is inside this popover).
  - **Name** — operator **In** — Select... (pick technicians/advisors).
  - **Add Filter** button adds a new row (defaults to Department / In).
- **Filterable FIELDS on Tech Performance**: Department, Pay Type Closed Date,
  **Make**, Service Type. (Pick the field from the row's field dropdown; option class
  `field__option`.)
- **Make operator on Tech Performance = "In"** (multi-select the makes via Select...),
  NOT free-text "is like". Joe's "make is like / is not like" phrasing comes from a
  DIFFERENT report/field (Advisor Performance or a Report Builder report) — confirm
  per report, don't assume the operator vocabulary.
- Bottom of popover: `Reset · Reset To Default Group · Apply`, plus
  `Default Filter / Save Filter Group` at top. Click **Apply** to run.

## SAVED FILTER GROUPS — load Joe's, don't rebuild (verified SCT Advisor Perf 2026-07-01)
Joe builds & SAVES named filter groups. At the TOP of the funnel popover is a
tekion-select showing the current group name (default text "Default Filter",
class contains `tekion-select-...-singleValue`, ~x214,y238). **Click it to open the
saved-group list** (options class `field__option`). Select the group by its exact
text → it loads all its rows. Then set/adjust the DATE and click Apply.
- Joe's SCT Advisor-Performance saved groups (2026-07-01): `Complete Service
  Department`, `prepaid`, `TXM`, `TXM REVISED 9/1`, `PDI`,
  **`TAC/TOYOTACARE REVISED 3/1/25`**, `TSC/Prepaid Hours REVISED 3/1/25`,
  `TXM REVISED 9/1 Warranty Hours`, `Customer Pay Hours 10/1/2025`,
  `Warranty Hours 11/1`.
- **TAC/TOYOTACARE REVISED 3/1/25** contains: Pay Type Status **In → Closed**;
  Pay Type Closed Date **Between → (blank, you set it)**; Opcode **In →
  TAC80,TAC75,TAC70,TAC65,TAC60,TAC55,TAC50,TAC45,TAC40,TAC35,TAC30,TAC25,TAC20,TAC15**;
  Pay Type **Not In → Warranty**. (The TAC## opcodes are the ToyotaCare mileage
  intervals.) Joe sets the DATE FIRST, then reads the **Bill Hrs** total.
- These group names are STORE-SPECIFIC — a group saved at SCT may not exist at
  BC/BT/etc. Re-open the group dropdown per store; if the group is missing, rebuild
  the filter rows manually from the definition above.

## ⚠️ THE DATE-RANGE CALENDAR TRAP (got badly stuck 2026-07-01 — READ THIS)
Setting the Flag Date / Pay Type Closed Date range is the FRAGILE part. Both a
top-bar "-" range and the in-funnel "Between" open the SAME dual-pane ant-style
calendar (Start-date panel left, End-date panel right, each its OWN month). Three
traps that wasted ~20 min:
1. **Typed dates get REJECTED.** Setting `input.value` via the native value-setter
   (or focus+type) reverts to the old value — React ignores it. Do NOT try to type
   the date. The picker only accepts CLICKING day cells.
2. **The nav arrows jump by YEAR and move panels INDEPENDENTLY.** The outer
   left-arrow moved the LEFT panel Jan2025→Jan2014; the outer right-arrow moved the
   RIGHT panel May2026→May2027. They are NOT "one month" buttons. There are inner
   (month) vs outer (year) chevrons — do not assume; verify the header after EACH
   click before clicking again.
3. **Vision coordinates are in SCALED SCREENSHOT space (~1226px wide), NOT the DOM
   viewport.** `/mouse` takes DOM-viewport pixels. So `vision_analyze` arrow coords
   (e.g. x585/x1102) land in the WRONG place when passed to `/mouse`. To click a
   calendar cell reliably, get its coords from the **DOM** (`getBoundingClientRect`
   on the day-cell element filtered by its text), never from the vision screenshot.

### RELIABLE date-set recipe (use this, skip the arrow-clicking flail)
Preferred: **the safest fast path is the OpenAPI cross-check** — for a Bill-Hrs /
billed-hours-by-opcode number over a month, sum labor hours for the closed target
opcodes (e.g. TAC15–TAC80) via `repair-orders:search` + jobs/operations
(`tekion-openapi-repair-orders`), which sidesteps the calendar entirely. Do this to
VERIFY Joe's manual figure rather than fighting the picker.
If you MUST drive the UI calendar: (a) open the picker, (b) read the two panel
headers from the DOM to know current months, (c) find the correct month/year via the
panel's header **year/month switcher** (click the year text to get a year grid, then
the month) rather than single-stepping arrows, (d) once the target month renders,
locate the day cell by DOM (`[title]`/cell text === "1"/"30") and `/mouse` its
DOM-rect center, (e) repeat for the end day, (f) Apply. Verify the applied range by
reading the input `.value` (e.g. "06/01/2026" / "06/30/2026") BEFORE trusting the
result number.

### DELIVERABLE DISCIPLINE
Don't report a number pulled from a HALF-SET date range. If the calendar won't
cooperate, tell Joe and pull the figure via API instead — a wrong billed-hours number
is worse than a short delay. When Joe gives you HIS manual number (e.g. "I got 283.7"
for TAC Bill Hrs June 2026), treat it as the target to reconcile against, and offer
the API cross-check.

## Toolbar controls
- **Group By** dropdown (chevron `service_reports_groupByMenu_chevron`, ~x1182).
- **Export/download** icon (`root_iconAsBtn_container`, ~x1233,y165) — for pulling
  the data out to a sheet.
- **Column config** / settings (`root_columnConfig_triggerIcon` / `icon-settings`,
  ~x1210,y221).

## :9223 API pitfalls (hit this session)
- **`/type` needs a `selector`** (or `ref`): `{selector:"input#email", text:"..."}`.
  A bare `{text:...}` errors "selector or ref, and text are required".
- **`/click` needs a selector/ref**, NOT raw coordinates. To click by pixel
  coordinates use **`/mouse`**: `{x:101, y:165}`. (Raw coords in `/click` →
  "One of selector, text, or ref is required".)
- **React ignores JS `.click()`** on buttons (Next/tabs/funnel). Either `/press`
  Enter on a focused input, or `/mouse` the element's bounding-box center.
- **`/screenshot` returns base64 JSON**, not a PNG file. Decode before vision:
  `d=json.loads(open(f,'rb').read()); png=base64.b64decode(d["screenshot"])`.
  `vision_analyze` rejects the raw JSON ("Only real image files are supported").
- Popovers/dropdowns render in **portals** — query `.ant-popover` /
  `.ant-select-dropdown` / `.rc-virtual-list`, not the inline DOM.

## Login note (2026-07-01)
The standalone `login.py` broke because Playwright bumped to chromium 1223 and the
headless-shell binary isn't installed (`chromium_headless_shell-1223` missing). Don't
fight it — just drive the login THROUGH the already-open `:9223` browser (it's the
persistent authenticated context you want anyway): email→Enter, password→Enter (Login
auto-sends OTP), poll himalaya `[Gmail]/All Mail` subject "Tekion-Login OTP" for the
count to increase, enter the 6-digit code→Enter. Success signal = `t_token` in
localStorage + URL `/home`.

## Cross-store
Same report URLs work at every store — just switch dealer first (dealer pill /
popover, verify `localStorage.currentActiveDealerId`). Match Joe's SCT date range
(Flag Date Between) exactly when pulling BC/BT/SV/TL/AR/VC.

## Related
- `tekion-sitemap` (nav), `tekion-autonomous-login` (auth),
  `tekion-report-builder-scraper` (the OTHER reporting place — custom reports only).
