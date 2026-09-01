---
name: amg-wip-monthly-column-fill
description: Fill a month column of Joe's AMG WIP workbook (the monthly fixed-ops tracker, rows=metrics cols=months, one tab per store) with Tekion data — hours sold by pay type, vehicle attendance, ToyotaCare hours, workshop hours, WIP $, ELRs. Includes the quota-free dealer-detail DB method for operation-level hours. Use when Joe says he needs to "finish" or "work on" the AMG WIP sheet for a month.
triggers:
  - fill in the wip sheet for this month
  - finish the amg wip workbook
  - update the wip column for a store
  - hours sold by pay type for wip
  - vehicle attendance numbers for wip
  - elr numbers for the wip sheet
  - workshop hours on the wip tab
  - wip dollar column needs updating
---

# AMG WIP Monthly Column Fill (Tekion → workbook)

## What this is
Joe's **AMG WIP.xlsx** = the monthly fixed-ops metric tracker (DISTINCT from the payroll-vs-RTH workbook in amg-wip-payroll-vs-rth-analysis). 8 tabs: Stevens Creek Toyota, Stevens Creek Volkswagen, Toyota of Fresno (=BT service), Blackstone Body Shop (=BT body), Volkswagen of Clovis, Fresno GM (=BC), Toyota of Lancaster, Alfa Romeo of San Jose. Rows = metrics, one column per month (header row 1 = datetime dated the **26th**, but Joe confirmed the window is the **CALENDAR month**, 1st→EOM).

- Live copy on Joe's Drive: file id `1esCOBSklptjeR3We9dKG6rcaDEfii6aJ` (an **.xlsx in Drive, NOT a native Sheet** — Sheets API can't write it; download via Drive `files/{id}?alt=media` with Bearer token, or convert to native Sheet for API writes). Local mirror: `/home/itadmin/amg-wip/AMG-WIP-live.xlsx`.
- Jay's Google access: symlink `~/.hermes/profiles/jay/google_token.json → /home/itadmin/.hermes/google_token.json` (Walter's base token, Joe's account, Sheets read/write + drive.readonly). Verify with google-workspace `setup.py --check`.

## SCT tab row map (col A labels; other tabs similar)
r4-10 Hours Sold: CUSTOMER / TXM / TOYOTA CARE / PREPAIRD MAINTENANCE / WARRANTY / PDI / INTERNAL · r13-14 VEHICLE ATTENDANCE: TOYOTA / OTHERS · r18-21 WORKSHOP: TOTAL AVAIL HOURS / TOTAL PROD HOURS / UNAPPLIED · r25-30 LABOR RATES (manual, carry forward) · r32 WIP $ · r35-45 ELR by make×paytype · r49-55 ACCESSORY ELRs · r60-67 TXM COUNT/SALE/COST/GROSS + parts block.

**TELL for an unfilled month:** the new column is an exact COPY of the prior month (every cell identical). Diff col N vs N-1 before assuming it's done.

## 🚨🚨 STEP ZERO — COVERAGE AUDIT. DO THIS BEFORE YOU PULL A SINGLE NUMBER.
**Burned 2026-09-01. I reported "91/93 cells filled" — the real denominator was ~194.
I filled 2 of 6 blocks per tab and MISSED 103 CELLS. Joe's reply: "dude. JAY, WTF. you
missed like half the sheet."** The bug was not the data. The bug was that my verification
loop only scanned **rows 3–15**, so it validated against my own assumption instead of the
sheet. A self-consistent check over the wrong range is worse than no check — it produces
a confident, wrong completion report.

**Every tab has SIX blocks. Rows 4–14 are only the first two.**

| # | Block | SCT rows | Source |
|---|---|---|---|
| 1 | Hours Sold | 4–10 | advisor-perf API (METHOD 0) |
| 2 | Vehicle Attendance | 13–14 | advisor-perf API, `roCount`, no status filter |
| 3 | **Workshop Analysis** | 17–21 | **Tech Performance API — see METHOD 0c** ✅ all 8 tabs solved |
| 4 | **Labor Rates + WIP $** | 24–32 | manual settings / carry forward; **WIP $ source still unknown — ASK** |
| 5 | **ELR (YTD)** incl TXM/OTHER/ACCESSORY | 34–55 | advisor-perf API, **YTD window** — see METHOD 0d. **~16 rows, not 6** |
| 6 | **TXM COUNT/SALE/COST/GROSS + parts** | 57–67 | Report Builder — see the TXM report table (3 candidates at SCT) |

**Blocks 4 and 6 are the only ones still needing Joe.** Block 4: do the Labor Rates carry
forward from the prior month, and where does WIP $ come from (an accounting screen)?
Block 6: does he change the date on the TXM report or run it as-is post-month-end?
Ask all of these in ONE message — they're 60-second answers that unblock ~40 cells.

Run this FIRST, and again as the final gate before reporting done:
```python
# for each sheet: every row where the PRIOR month has a value but target month is blank
for r in range(2, ws.max_row+1):
    prior, target = ws.cell(r,c_prior).value, ws.cell(r,c_target).value
    if isinstance(prior,(int,float)) and target in (None,""):
        print(s, r, ws.cell(r,1).value, prior)
```
**Report completion as `filled / (filled+missing)` from THIS audit — never from the count
of cells you happened to write.** Blocks 3–6 are ~60% of the workbook.

### 🔁 WHY THIS RECURRED — and the standing order that prevents it
Joe's exact words on delivery: *"dude. JAY, WTF. you missed like half the sheet.
ELR???? that is a YTD number for all the toyota stores."* Two separate failures in one
delivery, and BOTH were detectable before sending:

1. **Wrong denominator.** I verified 91 cells against the 93 I intended to write, not
   against the ~194 the sheet actually has. **A verification whose row range is derived
   from your own plan can only ever confirm your plan.** Derive the range from the
   PRIOR MONTH'S FILLED CELLS — that is the only ground truth for "what belongs here."
2. **Partial block = silent wrong answer.** I filled 6 of ~16 ELR rows. A partially-filled
   block looks *more* finished than an empty one and is far less likely to get caught.
   **Never ship a partially-filled block** — either complete it or leave it entirely blank
   and name it in the delivery message.

**Standing order: run the coverage audit TWICE — once before pulling data (to scope the
work) and once immediately before delivering (as the gate). Paste the resulting
missing-cell count into the message to Joe.** If that number is not zero, lead with it
rather than burying it. He is far more tolerant of "62 cells still blank, here's why" than
of a confident "done" that isn't.

**Corollary — when Joe names a specific row in anger, treat it as a category, not an
instance.** "ELR???? that is a YTD number" wasn't only about ELR being YTD (it already was);
the real signal was *the ELR block is incomplete*. Re-audit the whole block he points at.

## ⭐ METHOD 0 — THE ADVISOR-PERFORMANCE API (2026-08-31, USE THIS FIRST)
**This supersedes all the UI/calendar-clicking below for every Hours Sold / Attendance /
ELR row. Joe's complaint that drove this: the UI path burned ~5 hours and didn't finish
one tab, while he did the whole workbook by hand in 3. Do NOT drive the report screen.**

The report screen is just a client for one endpoint. Replay it and you get Joe's exact
numbers, scriptable across 8 tabs × ~40 rows.

- **Endpoint:** `POST /api/service-module/u/reporting/advisor-performance/summary`
- **Body:** `{"reportName":"REPAIR_ORDER_REPORT","reportGroup":"REPAIR_ORDER",
  "filters":[{"field":"migrated","values":[false],"operator":"IN"}, ...],"projections":[]}`
- **Response:** `data.reportData[]`, one row per advisor. **`primaryAdvisorId === "-1"` is the
  TOTAL rollup row** — that's the number the sheet wants.
- **Field names:** `billingTimeInSeconds` (÷3600 = Bill Hrs), `roCount`, `elrValue`
  (already dollars), `totalLaborSaleAmount` / `totalGrossAmount` / `totalSaleAmount` /
  `totalCostAmount` (**CENTS**, ÷100), `hoursPerRo`, `gpPercent`, `laborGpPercent`.
- **Filter fields available** (from the definition's `filterPreferences`):
  `primaryAdvisorId, payTypeStatus, payTypeFirstClosedTime, makeId, opcodes, payType,
  subPayType, roStatus, roJobCount, roCreatedTime, roClosedTime, roFirstClosedTime,
  checkinMedium, departmentId, serviceTypeIds, serviceMode, roNo, billingTimeInSeconds,
  laborPartsSubletSaleAmount, invoiceCreatedTime, roFirstInvoicedTime`.
  Note the field is **`opcodes`** (plural) — `opcode` / `indexDetail.opcode` return 0 rows.

### ⭐⭐ Pull Joe's SAVED FILTER GROUPS as DATA (kills the biggest failure mode)
`GET /api/sales/settings/u/v1.0.0/groupFilter/ADVISOR_PERFORMANCE_REPORT_SUMMARY/filter/preference/list`
→ `data[]` each `{groupName, filters:[{field,operator,values}]}`.

**This permanently solves the "a saved group's NAME is not proof of its filter logic"
trap documented below** — you now read the literal definition instead of loading the group
in the UI and squinting at it. Confirmed live: the group named `PDI` is really
`opcodes NIN [PDI] + payType IN [INTERNAL]` (= the INTERNAL row), exactly as Joe said.

Recipe: take the saved group's filters, **drop rows with empty `values`** (e.g.
`primaryAdvisorId IN []` — sending it empty is harmless but pointless), and **override
`payTypeFirstClosedTime` with your target window**. `wip_engine.group_filters()` does this.

### Setup / arming (headers come from a real captured request)
A bare `fetch()` can't auth — the app's axios interceptor signs requests. So:
1. `:9225` browser must be logged in (`/eval {"js":"localStorage.currentActiveDealerId"}`).
2. Arm the XHR hook + navigate to `/core/reports/service/advisor-performance`; the page
   fires a real `advisor-performance/summary` on load, and the hook captures its headers.
   `python3 ~/tekion-reports/wip_engine.py --arm` does this and polls until captured.
3. All later calls reuse those headers via in-page `fetch`.
4. **Cross-store = swap two headers only:** `dealerId` and `tek-siteId: '-1_<dealerId>'`.
   Verified working for all 7 dealers without re-login or a UI dealer switch — this is the
   big win vs. the dealer-pill dance.

**Engine:** `/home/itadmin/tekion-reports/wip_engine.py` — `arm()`, `month_ms(y,m)`,
`ytd_ms(y,m)` (Pacific), `saved_groups(dealer)`, `group_filters(groups,name,a,b)`,
`summary(dealer,filters,site=None)`, `total_row()`, `hrs()`, `money()`, `elr()`, `rocount()`.

**Two engine fixes landed 2026-08-31 — reload before using:**
1. `summary(..., site=...)` optional override for `tek-siteId` (proved BT ignores it,
   but the param stays for other multi-site probes).
2. `group_filters()` now re-windows **any** date field a saved group uses
   (`payTypeFirstClosedTime | roClosedTime | roCreatedTime`), not just the first.
   Before this fix VC's groups all returned a silent 0.00.
Always `importlib.reload(W); W.arm()` at the top of every `execute_code` cell — the
sandbox is fresh each call.

### VALIDATE AGAINST A KNOWN-GOOD PRIOR MONTH BEFORE FILLING ANYTHING
Reproduce last month's column first; report the match table to Joe. SCT June 2026 —
6 of 8 rows exact:

| Sheet row | Source | June target | API | ✓ |
|---|---|---|---|---|
| CUSTOMER | CP, opcodes NIN [TAC*,TSC*], **NO make filter** | 2,666.82 | 2,666.82 | ✅ |
| TOYOTA CARE | group `TAC/TOYOTACARE REVISED 3/1/25` | 283.70 | 283.70 | ✅ |
| PREPAID MAINT | group `TSC/Prepaid Hours REVISED 3/1/25` | 895.35 | 895.35 | ✅ |
| WARRANTY | `payType IN [WARRANTY]` **+ opcodes NIN [TXM 30-set]** | 1,000.80 | 1,000.80 | ✅ |
| INTERNAL | group `PDI` (= opcodes NIN [PDI] + INTERNAL) | 1,209.78 | 1,209.78 | ✅ |
| ATTENDANCE TOYOTA | group `WIP Attendance - Toyota` → **roCount** | 5,243 | 5,243 | ✅ |
| PDI | `opcodes IN [PDI]` | 416.90 | 418.40 | ⚠️ off 1.5 |
| TXM | ??? | 744.96 | 541.96 | ❌ unresolved |

**TWO CORRECTIONS to earlier skill notes, discovered by this reproduction:**
1. **CUSTOMER excludes the make filter.** The saved group `Customer Pay Hours 10/1/2025`
   carries `makeId IN [toyota,scion]`, which yields 2,613.92 — but the sheet says 2,666.82,
   which is the same filters *without* makeId. Don't blindly trust the saved group here.
2. **WARRANTY subtracts the TXM opcodes.** `Warranty Hours 11/1` alone gives 1,519.90;
   sheet is 1,000.80 = WARRANTY minus the 30 TXM opcodes (WARRANTY∩TXM = 519.10). This
   reconciles the old "is Warranty TXM-contaminated?" thread — the exclusion is real.

### ⚠️ TXM ROW — REPORT BUILDER API CRACKED 2026-09-01, BUT THE SOURCE IS STALE
Joe confirmed the source is Report Builder **`SCP-Toyota Care 2.0`** (operation-grain,
`RO_OPERATION_OPCODE STARTS_WITH "TEK"`), NOT Advisor Performance.

**⭐ HOW TO RUN ANY REPORT BUILDER REPORT HEADLESSLY (2026-09-01, big unlock):**

🚨 **THE 500 `RB3` TRAP — the execute body MUST be WRAPPED. Read this before debugging.**
Burned ~10 tool calls on 2026-09-01. Symptom: *every* report 500s with
`{"errorCode":"RB3","key":"request.execution.failed"}` — **including reports that worked
in a previous session**, which makes it look like Tekion broke or the reports are corrupt.
They aren't. The cause is POSTing the **bare report object** as the body:

```js
// ❌ 500 RB3 every time — this is the report object, not the request
fetch("/api/reportbuilder/u/execute/withOptions?preview=false",{body:JSON.stringify(rep)})
// ✅ must be wrapped in the two-key envelope
{"reportConfig": rep, "reportExecutionOptions": {...}}
```
Both `GET /api/reportbuilder/u/report/list` and `POST /report/search` hand you a bare
report object, so it is very natural to POST it directly and conclude the report is broken.
**If you see RB3, check the envelope before anything else.**

**When in doubt, capture the UI's real payload instead of reconstructing it** (this is what
finally resolved it):
1. Navigate to `/report-manager`, then **arm the XHR hook AFTER the nav** — navigation wipes
   an earlier hook, and you'll get an empty `__XH` and wrongly conclude the page fires no XHR.
2. Click the report row → it fires the real `execute/withOptions`.
3. Read `JSON.parse(capturedCall.b)` → stash as `window.__TPL` and mutate *that*.

```
1) GET /api/reportbuilder/u/report/list        → data[] (all reports; has id/name/dataSource)
   or POST /api/reportbuilder/u/report/search  → data.esResponse.hits[]
   (POST /report/list → 405; GET /report/search → 405; /reports, /report/all → 404)
2) POST /api/reportbuilder/u/execute/withOptions?preview=false
   {"reportConfig": <report object>,
    "reportExecutionOptions":{"sort":[],"filters":[],"searchText":"","groupBy":[],
      "includeFields":[],"searchableFields":[],"excludeFields":[],
      "pageInfo":{"start":0,"rows":500}}}
   → data.count           = record count (OPERATION grain, not RO)
   → data.projections     = the totals block, e.g.
     REPAIRORDER_OPERATION_ASSIGNED_BILL_HOURS__SUM  (already HOURS, not seconds)
     REPAIRORDER_JOB_OPERATION_BILLING_TIME__SUM     (already HOURS)
     RO_CP_LABOR_TOTAL_AMOUNT__SUM / RO_WP_LABOR_TOTAL__SUM (CENTS)
     groupMetrics__RO_NUMBER__VALUE_COUNT / __RO_CLOSEDTIME__MAX
```
**Filters live in `reportConfig.filterConfigs`, NOT `reportConfig.filters`.** Mutating a
non-existent `filters` key is a silent no-op — the report runs fine and returns its default
window, so you get a plausible wrong number with no error. Sanity-check every windowed run
against `projections["groupMetrics__RO_CLOSEDTIME__MAX"]` — if that date isn't inside your
target month, your override didn't take.
- **Cross-store:** same 2-header swap (`dealerId`, `tek-siteId`). Each store has its OWN
  copy, and **the names differ — search `"SCP"`, not the exact title:**

| Store | Report | id | created | category filter | bill-hrs? |
|---|---|---|---|---|---|
| SCT 876 | `SCP-Toyota Care 2.0` | `6a45095462e5ff667243d553` | 2026-07-01 | Vehicle + Maintenance | ✅ |
| BT 1249 | `SCP-Toyota Care 2.0` | `66227a89735ee81a7ca35bad` | 2024-04 | Vehicle + Maintenance | ✅ |
| TL 1092 | `SCP OP Code-ToyotaCare (TXM)` | `6585c492ee94990ac065f290` | 2023-12 | **Vehicle only** | ❌ **returns 0** |

### ⭐ A BETTER TXM SOURCE EXISTS AT SCT — report **`TXM`** `65bbe1cc93de29200c569725`
Found 2026-09-01 by listing ALL reports rather than searching `"SCP"`. **Its `kpiMetrics`
are an exact match for the sheet's TXM block** — which `SCP-Toyota Care 2.0` is not:
```
RO_CP_LABOR_COST_AMOUNT · RO_CP_LABOR_TOTAL_AMOUNT
RO_WP_LABOR_COST_AMOUNT · RO_WP_LABOR_TOTAL
REPAIRORDER_JOB_OPERATION_BILLING_TIME        (already HOURS)
groupMetrics: RO_NUMBER (count), RO_CLOSEDTIME, RO_CREATEDTIME
filterConfigs: RO_CLOSEDTIME DATE_RELATIVE/LAST_MONTH
             + RO_OPERATION_OPCODE STARTS_WITH "txm"     ← note: txm-prefix, NOT "TEK"
```
Created 2024-02, description *"TXM for the Month"*. Compare against `SCP-Toyota Care 2.0`
(created **2026-07-01**, `STARTS_WITH "TEK"` + category Vehicle/Maintenance) which
structurally **cannot** reproduce any month before July 2026. SCT also has a third,
`TXM Report` `64f22a4f36d1a00007ac9d20` (2023-09, hardcoded 21-opcode `Txm*` list, CP/IP/WP
cost+total metrics).

**Enumerate before assuming** — `searchText:"SCP"` finds only one of these three:
```js
GET /api/reportbuilder/u/report/list   // → data[], filter client-side on name/dataSource
// SCT 876 : "TXM Report" 64f22a4f36d1a00007ac9d20 | "TXM" 65bbe1cc93de29200c569725
//           | "SCP-Toyota Care 2.0" 6a45095462e5ff667243d553
// TL 1092 : "SCP OP Code-ToyotaCare (TXM)" | "txm @ PRICE 11" 64a813f2128394000784360c
//           | "TOYOTA CARE MECH LABOR (TAC)" 67a1536b7b113e771d98224e  (REPAIR_ORDER_JOB!)
// BT 1249 : "SCP-Toyota Care 2.0" 66227a89735ee81a7ca35bad | "SCP-Toyota Care" 659488f80a75803d99131b76
```

### ⚠️ UNRESOLVED: the `TXM` report ignores every date override (ASK JOE FIRST)
Once the RB3 envelope bug was fixed the report executes, but **the June window is silently
ignored** — returns count 4,302 with `RO_CLOSEDTIME__MAX` in **May**, vs the sheet's 1,442.
Tried and all identical-wrong (4,302 / May):
`filterConfigs` RO_CLOSEDTIME as `DATE_STANDARD`+BTW (ms num **and** ms string),
`ADVANCED`+BTW, `ADVANCED`+`subType:FILTER_RULE`+BTW, and clearing
`period`/`relativeDateType`. Pushing the window into `reportExecutionOptions.filters`
instead **does** change the result (count 2,902, max close 08-26) but still isn't the month.

**Before burning more calls: ask Joe whether he changes the date at all.** The report ships
as relative `LAST_MONTH`, so if he simply runs it as-is just after month-end, **no override
is needed** — run it unmodified and read the totals. That one question is far cheaper than
reverse-engineering the filter grammar. (Consistent with the METHOD 0 lesson: the
`SCP-Toyota Care 2.0` override *did* work via `ADVANCED`/BTW, so the grammar differs
per report — likely `RO_CLOSEDTIME` is not this report's `primaryDateFieldKey`.)

  (Corrects an earlier note claiming TL has no such report — it does, just named differently.
  Find it with `searchText:"SCP"`, then match on `id`.)
- **TL's report carries no billable-hours field** — `..._ASSIGNED_BILL_HOURS__SUM` is `0` for
  every window, only `count` is real. TL TXM **cannot** be produced from it; ask Joe to read
  the number off his screen.
- **BT's report does NOT equal Joe's sheet** (it runs ~11% high, consistently):
  Apr 300.1 vs 271.0 · May 337.7 vs 301.0 · Jun 396.6 vs 354.0. So "the report is the source"
  is true for *record counts* but the hours still need Joe's confirmation per store.
- **Override the date window** (report ships as relative `LAST_MONTH`): drop the
  `RO_CLOSEDTIME` entry from `reportConfig.filterConfigs` and push
  `{fieldKey:"RO_CLOSEDTIME",dataSource:"REPAIR_ORDER",values:[startMs,endMs],
    type:"ADVANCED",subType:"FILTER_RULE",operator:"BTW",booleanOperator:"AND"}`.
  **Only `type:"ADVANCED"` + `operator:"BTW"` works.** `DATE_RANGE`/`BTW` and
  `DATE`/`BETWEEN` both 400 `unexpected.error`; epoch **seconds** silently return 0;
  `"YYYY-MM-DD"` strings return a DIFFERENT (smaller) number than ms — use **ms** or full
  ISO w/ offset. Mutating `relativeDate` 0/1/2 does nothing.
  Equivalence proven: override-Aug == native LAST_MONTH-Aug (796 / 362.1 both ways).

**🚨 THE TRAP — the Report Builder ES index lags ~4 DAYS. Verify before trusting it.**
On 2026-09-01 the report returned **0 records for Aug 26–31** while the advisor API showed
the store closed **1,606 ROs** in that window; `hits[].ingestionTime` maxed at 08-28 01:47.
So its month total is **understated and drifts depending on when you open it**.
**Always** run this check before writing a Report-Builder-sourced cell:
```python
# 1. tail-window check: does the report see the last ~5 days of the month?
# 2. compare hits[].ingestionTime max vs now
```
If it's stale → **leave the cell blank and tell Joe**, don't write a number you know is low.

**Why June can never validate this report:** it was **created 2026-07-01**
(`createdTime == modifiedTime == 1782909268489`). Running it over June yields 448 / 208.80
vs Joe's 744.96 — not a filter bug, the data simply predates the report.

**TXM candidate definitions vs Joe's own history** (still unresolved — ASK, DON'T GUESS):
| definition | Apr | May | Jun (target 744.96) |
|---|---|---|---|
| `TXM REVISED 9/1` 30-opcode group | 762.00 | **769.55 ✅exact** | 541.96 ❌ |
| TEK opcodes w/ `category==VEHICLE` (52) | 0.00 | 0.00 | 271.20 |
| TXM30 + TEK-VEHICLE | 762.00 | 769.55 | 813.16 |

The saved group matches May **to the cent** then breaks in June → the opcode mix changed
mid-year. `TXMPLUS` is a huge bundle (3,495 hrs alone) — never add it.
`TXMPLUS00TFL` / `TXMROTATE` return 0. **Fastest close-out: ask Joe to open the SCP report
on a month he already has and read the number.**

The elimination log below is kept only so nobody re-walks it:

#### (historical) why no Advisor-Performance filter could ever match
June target 744.96 hrs / 1,442 count / $215,399 sale. Ruled out exhaustively:
30-opcode `TXM REVISED 9/1` set (541.96), the 63-opcode `TXM ` superset, full `TXM*`
opcode list incl. TXMPLUS/TXMROTATE/MT000B (4,042 — TXMPLUS alone is 3,495, way over),
every date basis (`payTypeFirstClosedTime` / `roClosedTime` / `roCreatedTime` /
`invoiceCreatedTime`=0 rows), status filtered vs not, ±make filter, and the 26th→25th
window (722.26 — close but not it). **Count 1,442 smells like a SERVICE/operation count,
not an RO count → likely the Report Builder report `SCP-Toyota Care 2.0`, not Advisor
Performance.** Ask Joe which report feeds the TXM row before filling it. Same for PDI's
1.5-hr gap.

### 🔑🔑 ROOT CAUSE OF EVERY "MY NUMBER IS HIGH" GAP — RO GRAIN vs OPERATION GRAIN
**Discovered 2026-09-01. This explains SV Care/Care Plus, SCT TXM, and probably TL PDI /
SV Service Xpress too. Check this FIRST on any bucket that reads high.**

`advisor-performance/summary` with an `opcodes IN [...]` filter returns **every hour on every
RO that CONTAINS one of those opcodes** — including the unrelated lines on the same ticket.
Joe's sheet counts **only the matching operation lines**. So the API is structurally high
whenever a bucket's opcodes ride along on bigger tickets.

Proof (SV June Care/Care Plus, target 35.20):

| method | result |
|---|---|
| `advisor-performance/summary`, `opcodes IN` (RO grain) | 76.04 ❌ |
| Report Builder `REPAIR_ORDER_OPERATION` (operation grain) | **43.5** ✅ much closer |

**How to get operation grain — clone a `REPAIR_ORDER_OPERATION` report as a template.**
Every store has one; find it by listing reports and filtering on `dataSource`:
```js
// searchText:"" + rows:60 lists ALL of a store's reports with their dataSource
{"searchText":"","searchFields":["name"],"pageInfo":{"start":0,"rows":60},
 "sort":[{"field":"modifiedTime","order":"DESC"}],"includeDeleted":false}
// SV 826 → "SCVW A-La-Cart - Script"  670541e839c34f5e2be9f404
// AR 6195 → "ARSJ A-La-Cart - Script" 67f5225e5547ec4c9460f04d
//          + "Gross by OpCode - Template" 6739830db7e1e51a7e744131
```
Field names at this grain are **different** from the RO-grain report:
- `ROPERATION_OPCODE` (note: ONE `P` — not `RO_OPERATION_OPCODE`)
- `JOB_PAYTYPE` (values `CUSTOMER_PAY` / `WARRANTY` / `INTERNAL`)
- `RO_CLOSEDTIME` still the date key, still `type:"ADVANCED"` + `operator:"BTW"` + ms.

**🚨 Mutate the template MINIMALLY — do not rebuild it.** Swapping in your own
`fields`/`kpiMetrics`/`groups` to request an hours aggregate returns **500 `unexpected.error`**
every time. What works: keep the template's own `fields` block untouched, only replace the
values inside the existing `RO_CLOSEDTIME` and `ROPERATION_OPCODE` filter entries (and drop
`JOB_PAYTYPE` if you want all pay types), then **sum hours client-side from the returned rows**:
```js
pageInfo:{start:0,rows:500}   // then:
let s=0; hits.forEach(x=>{ s += (x.billingTimeInSeconds||0) });
```
**`billingTimeInSeconds` at operation grain is already HOURS, despite the name**
(1.4 == 1.4 hr, and `laborTimeInSeconds` matches it). Do NOT divide by 3600 here — that is
the opposite of the RO-grain `billingTimeInSeconds` convention in the advisor API.

Splitting SV Care/Care Plus by pay type this way revealed it is **~100% warranty**
(WARRANTY 43 ops / 43.3 hrs · CUSTOMER_PAY 1 op / 0.2 hrs) — a genuinely useful finding for
Joe, and the kind of thing RO grain hides completely.

Whole-fleet June cross-check took ~25 tool calls with the engine. Two structural
discoveries that block everything until you know them:

### 🔑 DISCOVERY 1 — BT is TWO tabs inside ONE dealer, split BY ADVISOR
"Toyota of Fresno" (BT service) and "Blackstone Body Shop" are both dealer **1249**.
There is **NO site/department dimension in this API** — `tek-siteId` is IGNORED for
dealer 1249 (`-1_1249`, `1_1249`, `2_1249`, `1249` all return the identical 3,609.72),
and `departmentId` / `serviceType` / `roType` / `serviceMode` filters all return 0 rows.
The DB has no site key either (`payload.ro` has no `siteId`/`departmentId`; all null).

**The split is the ADVISOR SET.** Body shop advisors are the extreme hours-per-RO
outliers (27–75 hrs/RO vs ~1.5 for service):

```python
BT_BODY = ["73c7e798-5d39-4603-b516-16eae5f36216",   # 410.40 hrs / 15 ROs
           "bfa0b344-a494-4117-a225-269b91e12f36",   # 391.30 hrs / 17 ROs
           "93017239-1132-4ecd-b881-1f023d4b8af7"]   # internal 59.00 / 2 ROs
NB = {"field":"primaryAdvisorId","operator":"NIN","values":BT_BODY}   # → service tab
IB = {"field":"primaryAdvisorId","operator":"IN", "values":BT_BODY}   # → body shop tab
```
Verified June: service CUSTOMER 2,805.62 ✅ / INTERNAL 1,747.10 ✅; body CUSTOMER
804.10 ✅ / INTERNAL 59.00 ✅ / Attend Others 14 ✅. Without this split BT looks
~800 hrs over and you will waste an hour hunting a phantom filter.
**To find the advisor set at any multi-department store:** pull the per-advisor rows
(non-`-1`) and sort by hours-per-RO — body/heavy-line advisors stand out by 10-50×.

### 🔑 DISCOVERY 2 — saved filter groups carry DEAD date windows AND a different date field
A saved group embeds whatever date field its author used — VC's groups use
**`roClosedTime`**, not `payTypeFirstClosedTime` — with the **hardcoded window from the
day it was saved**. The original `group_filters()` only re-windowed
`payTypeFirstClosedTime`, so every VC group silently returned **0.00** (no error, just
zeros — the worst kind of failure). Fixed in the engine: it now re-windows ANY of
`payTypeFirstClosedTime | roClosedTime | roCreatedTime`. After the fix VC Care/Care Plus
40.46 ✅ and Carefree 132.20 ✅ landed exactly.
**Rule: a 0.00 from a saved group means a stale date field, not "no data."**

### Saved-group inventory (re-verified, all 7 dealers)
`SCT 876` = 11 groups · `VC 1891` = 6 (CARE/CAREPLUS, CAREFREE, Service Xpress, WARRANTY
SOLD HOURS, wARRANTY hOURS, Open Repair Orders) · `AR 6195` = 1 (`Quickservice ` — note
the trailing space; = `opcodes IN [LOF,LOF2L,LOF4C,LOFV6]`, reproduces 78.90 ✅).
**SV 826 / BT 1249 / BC 1251 / TL 1092 = ZERO groups** → derive from opcodes.

### Per-store bucket recipes VERIFIED against June
Common: `CL = payTypeStatus IN [CLOSED]`, `D = payTypeFirstClosedTime BTW [monthstart,monthend]`.
Attendance rows use **no** status filter.

| Tab | Row | Filter | June ✓ |
|---|---|---|---|
| **Fresno GM (BC 1251)** | CUSTOMER / WARRANTY / INTERNAL | `CL+D+payType IN [X]` | 2050.30 / 1262.40 / 755.30 all ✅ |
| BC | Attend GM / Others | `D + makeId IN/NIN ["chevrolet","cadillac"]` | 1926 ✅ / 264 ✅ — **2 makes ONLY; adding gmc+buick gives 1997/193 ✗** |
| **Alfa Romeo (6195)** | CUST/WARR/INT | `CL+D+payType` | 263.53 / 104.10 / 202.08 all ✅ |
| AR | Quick Service | saved group `Quickservice ` | 78.90 ✅ |
| AR | Attend AR / Others | `makeId IN/NIN ["alfaromeo","alfa romeo"]` (**both spellings**, data is dirty) | 92 ✅ / 41 ✅ |
| **BT service (1249+NB)** | CUST / INT | `CL+D+payType+NB` | 2805.62 ✅ / 1747.10 ✅ |
| BT | TOYOTA CARE | `CL+D+opcodes IN TAC-set+NB` | 668.80 ✅ |
| BT | PREPAID / PDI | `opcodes IN TSC-set` / `opcodes IN [PDI]` | 0.00 ✅ / 274.10 ✅ |
| **Body Shop (1249+IB)** | CUST / INT / Attend Oth | as above with `IB` | 804.10 ✅ / 59.00 ✅ / 14 ✅ |
| **TL 1092** | WARR / INT / Attend Oth | `CL+D+payType` | 1243.31 ✅ / 506.42 ✅ / 245 ✅ |
| TL | TOYOTACARE | **`opcodes IN TAC-set + TSC-set` COMBINED** (602.60 vs 602.10; TAC alone = 196.80 ✗) | ~✅ |
| **SV 826** | WARR / INT / Attend Oth | `CL+D+payType` | 617.38 ✅ / 222.26 ✅ / 55 ✅ |
| **VC 1891** | CUST / INT | `CL+D+payType` | 635.75 ✅ / 107.28 ✅ |
| VC | CARE/CAREPLUS, CAREFREE | saved groups (post date-fix) | 40.46 ✅ / 132.20 ✅ |

Opcode sets per store come from `POST /api/service-module/u/opcode/search`
`{"searchText":"TAC","page":{"from":0,"size":100}}` → `data.hits[]` with
`opcode/description/status`. **Opcode sets differ per store** — TL has `PDI` +
`PDICILAJET` and TSC1-5 active; BT has only `PDI` and TSC1-4 INACTIVE. Never reuse
SCT's list blind.

### ❌ Still unreproduced after full June sweep — ASK JOE, DO NOT GUESS
| Item | Engine | Sheet | Gap |
|---|---|---|---|
| TL PDI | 274.00 (100% WARRANTY pay) | 236.76 | −37.24 |
| VC Attendance VW | 677 (628 excl internal) | 587 | −90 |
| SV Service Xpress | 453.61 | 368.63 | −85 |
| SV Care/Care Plus | 63.21 (using VC's opcode list) | 35.20 | −28 → **43.5 at operation grain, see ROOT CAUSE section; residual 8.3** |

**Joe's SV Care/Care Plus opcode list (he gave it 2026-09-01)** = VC's 10 **plus `10K` and `20K`**:
`01030020 01030040 01030060 01030080 01040010 01040030 01040050 01040070 01390040 01390080 10K 20K`

#### ⭐ VALIDATE ACROSS ~6 MONTHS, NOT ONE — the error SIGN is the diagnosis
Single-month validation cannot distinguish "wrong filter" from "wrong basis." Run the
candidate against every month Joe already has and look at the **sign pattern**:

| Month | Sheet | Op-grain calc | Diff |
|---|---|---|---|
| Jan | 35.50 | 58.0 | **+22.5** |
| Feb | 28.68 | 42.9 | **+14.2** |
| Mar | 46.20 | 50.0 | +3.8 |
| Apr | 48.30 | 39.9 | **−8.4** |
| May | 42.82 | 34.2 | **−8.6** |
| Jun | 35.20 | 43.5 | +8.3 |

**Error swinging BOTH directions ⇒ STOP — no filter can fix it.** A wrong/missing filter is
monotonically biased (always high or always low). A sign flip means the *basis* differs.
Two corroborating tells here: Joe's values carry **cents** (28.68, 42.82) while
`billingTimeInSeconds` sums land on **tenths** (43.5, 34.2, 58.0); and every line is
`laborName:"Warranty Care/Care Plus"` / `laborDescription:"50% Labor Rate"` — so his figure
is almost certainly derived from **labor dollars ÷ rate**, not summed line hours.
Don't keep adding filters — ask which screen he reads it off.

`10K`/`20K` contribute **0.0** at SV in June, so adding them changed nothing; and
`JOB_CLOSEDTIME` as the date key returns **0 rows** (only `RO_CLOSEDTIME` works).

**SV Service Xpress — still unresolved, and `serviceTypeIds` is a DEAD END as a FILTER.**
It works as a `group_by` (SV has 9 buckets) but returns **0.00** as a filter value at SV.
Grouping June and scoring each bucket against Joe's Apr/May/Jun (523.64 / 340.57 / 368.63)
matched **nothing** — closest bucket was 360.79 vs 368.63 but 0.00 in Apr/May. All
service-type list endpoints 404 (see dead-ends). Ask Joe for the source screen.

**AR SERVICE CONTRACT row — RESOLVED, there is no source. Joe makes it up.**
His words: *"I just make that number up... I just need you to keep it within a certain
believable number."* All 28 AR Report Builder reports enumerated — no service-contract report
exists, and it is not a pay type. **Do not burn time hunting it again.** Fill it with an
in-band estimate off his own trailing history (2026 range 14.53–20.68, mean ~18.3, flat and
NOT correlated with volume), nudged in the direction customer hours moved. Label it EST when
reporting to him.
| BT Warranty svc/body | 1200.60 / 533.50 | 1206.70 / 527.40 | 6.1 on wrong side of the split |

**Sub-2-hour drift is EXPECTED and not a bug** when validating an old month: SV Customer
680.21 vs 678.31, TL Customer 2473.49 vs 2471.79, SV Attend 745 vs 746, TL Attend 3821
vs 3822. Cause = ROs reopened/re-closed in the ~2 months since Joe pulled the column.
Say this explicitly instead of hunting it — same-day pulls won't have it.

### More dead ends closed 2026-08-31 (do not re-probe)
- **No service-type / department / site endpoint exists** for this app. All 404 or 500:
  `/api/service-module/u/{makes,departments,service-type/list,serviceTypes,site/list}`,
  `/api/servicesettings/u/{ro/sites,servicetype/all,site/<id>}`,
  `/api/dealer-management/u/sites`, `/api/tenant/u/dealer/<id>/sites`,
  `/api/user-management/u/{dealers,user/context,logged-in-user}`,
  `/api/preference/u/{dealer/list,user/dealers}`.
  Get make lists from the **dealer-detail DB** instead:
  `payload->'vehicle'->>'make'` grouped by store (`wip_makes2.cjs` pattern).
- **`serviceTypeIds` is per-dealer.** VC's Service Xpress id `6421d1490d173d3a9412d197`
  returns **0.00** at SV, BC and AR. Don't port an id across stores.
- **Only 3 payTypes exist fleet-wide:** `CUSTOMER_PAY`, `WARRANTY`, `INTERNAL`. `PDI`,
  `SERVICE_CONTRACT`, `EXTENDED_WARRANTY`, `TOYOTA_CARE`, `PREPAID`, `MAINTENANCE_PLAN`
  all return 0 at every store. Every other sheet row is an **opcode** bucket, not a
  pay type. (So AR's SERVICE CONTRACT 18.85 row is opcode-derived — ask Joe which.)
- `advisorName` / `primaryAdvisorName` come back **null** in `reportData[]` — resolve
  UUIDs via `/openapi/v4.0.0/users/{id}` if you need names.

## Dead ends (don't re-walk these)
- **`Advisor Performance Report(3)`** in `/core/reports` is a DIFFERENT, newer report
  (visibility-dashboard, `documentId 68f20e5a175cec6153a05014`) hitting
  `POST /api/rosearchservice/u/visibility-dashboard/generate-summary-report`. It works and
  gives a nice grouped grid, BUT: a hand-built body 500s `unexpected.error` — you must
  clone `report-definition/<id>` → `customEsRequests` and only mutate `filters`/`groups`.
  Worse, **opcode filtering is unavailable there** (`indexDetail.opcode` as a filter or
  group returns 0 rows / totals only), so it can't do the TAC/TSC/TXM buckets. Values come
  back in cents + `billingTimeInSeconds`. Use the older `advisor-performance/summary`
  instead — it's the one whose saved groups match Joe's sheet.
- **Only SCT and VC have saved filter groups.** SV, BT, BC, TL return `[]`; AR has one
  (`Quickservice `). Their tabs use different row labels (CARE/CARE PLUS, CAREFREE,
  SERVICE XPRESS, QUICK SERVICE, MOPAR EXPRESS, GM makes) → derive per-store opcode sets
  and reproduce that store's prior month before filling.
- **Google OAuth is dead** (`invalid_grant` on BOTH `/home/itadmin/.hermes/google_token.json`
  and Stacey's copy) → can't pull the live Drive workbook. Work from the uploaded file /
  local mirror and hand Joe numbers in Slack.

### Non-SCT tab row maps (from AMG-WIP-live.xlsx, June col)
- **SCVW / VW Clovis:** r4 CUSTOMER, r5 WARRANTY, r6 CARE/CARE PLUS, r7 CAREFREE,
  r8 INTERNAL, r9 SERVICE XPRESS · r12 VOLKSWAGEN, r13 OTHERS · r17-21 workshop ·
  r29 WIP · r32-37 ELR.
- **Toyota of Fresno (BT service):** same shape as SCT but TXM block at r58-65 and
  labeled TXM LABOR SALE/COST/GROSS.
- **Blackstone Body Shop:** compressed — r4 CUSTOMER, r5 WARRANTY, r6 INTERNAL ·
  r9 TOYOTA, r10 OTHERS · r14-17 workshop · r28 WIP · r31-37 ELR.
- **Fresno GM (BC):** r4 CUSTOMER, r5 WARRANTY, r6 INTERNAL · r10 GENERAL MOTORS,
  r11 OTHERS · r15-18 workshop · r22-26 rates (incl EXTENDED SERVICE CONTRACT LABOR,
  QUICK SERVICE) · r29 WIP · r32-34 ELR.
- **Toyota of Lancaster:** SCT-like; TXM block r57-64.
- **Alfa Romeo SJ:** r4 CUSTOMER, r5 WARRANTY/ROAD READY, r6 INTERNAL, r7 QUICK SERVICE,
  r8 SERVICE CONTRACT, r9 MOPAR EXPRESS(N/A) · r13 ALFA ROMEO, r14 OTHERS.

## 🚨 WRITING INTO THE WORKBOOK — READ THIS BEFORE ANY `openpyxl` SAVE
Learned the hard way 2026-09-01 (caught before delivery, but only just).

**1. Joe keeps a SOURCE-REFERENCE NOTE COLUMN immediately right of the last date column.**
On SCT it's col 50 holding `C7`,`w3`,`c1`,`c2`,`w4`,`I5`,`I6` and `elr/ytd` ×5 — his
shorthand for which report/tab each row came from. Same on Toyota of Fresno (col 49:
`C3`,`w4`,…), TL (col 49), SV (col 50: `c/w`,`w`).
**Writing the new month to `max(date_cols)+1` SILENTLY DESTROYS IT.**
→ **Always `ws.insert_cols(target)`** so the notes shift right, never overwrite.
→ Audit first: for each sheet, print cols `lastdate+1 .. lastdate+3` rows 1–45 and look
  for short text values. A cell reading `w3` where you expected a number = you're in the
  note column.

**2. The unfilled-month TELL is real and it bit here.** In `AMG-WIP-live.xlsx` the July
column was an exact copy-paste of June on EVERY tab (SCT CUST 2666.82 / TXM 744.96 /
WARR 1000.8 identical). Real July was materially different (CUST 2275.73, WARR 1420.70).
**Diff col N vs N-1 before assuming a month is done** — and if it's a copy, fill it too,
then TELL Joe you overwrote a placeholder so he can reconcile against his own records.

**3. Don't clear cells you didn't write.** First instinct on a stale copied value was
`cell.value=None` — that's how the note column got hit. Rebuild from the pristine file
with inserts instead of patching in place.

**4. Preserve formatting:** load with `data_only=False` (keeps formulas), copy
`number_format` from the June cell of the same row, and write the header as
`datetime(y,m,26)` (Joe's columns are dated the 26th though the window is calendar-month).

**5. Verify after save:** reload `data_only=True` and assert every written cell equals the
JSON it came from, and that blocked buckets are `None` (not 0, not stale). Report the
mismatch count — target 0.

## FAST PATH — the whole workbook in ~4 minutes
`/home/itadmin/tekion-reports/wip_aug.py` (misnamed; takes any month):
```bash
python3 ~/tekion-reports/wip_aug.py 2026-08 9225 > ~/amg-wip/aug2026.json
```
Emits all 8 tabs keyed `"r4 CUSTOMER": 2466.6`, with unresolved buckets as a
`"BLOCKED — ..."` string so the writer skips them instead of writing junk. Run two months
(prior + target) and diff. Whole 8-tab pull ≈ 3 min wall clock.

### Session bootstrap when `:9223` is busy (this is the normal case at night)
`:9223` is owned by the nightly Caliber `cron-tekion.sh` (starts ~1:16AM, runs 12+hrs, and
**drifts the dealer context**). `:9225` is usually logged out. Do NOT fight over `:9223`:
1. `python3 ~/tekion-auth/login.py --force` (Gmail OTP path; verify himalaya first with
   `HOME=/home/itadmin himalaya envelope list -a personal -f "[Gmail]/All Mail" -s 3`).
2. Inject the fresh storage state into `:9225` (cookies + localStorage), then `/navigate`
   to `https://app.tekioncloud.com/home` and confirm `currentActiveDealerId`.
3. `W.PORT = 9225` before `W.arm()`.

**Engine bug fixed 2026-09-01:** `wip_engine.ev()` / `nav()` had `port=PORT` as a
**default argument**, so `PORT` was captured at import time and `W.PORT=9225` was ignored
(every call still hit 9223). Now `port=None` → resolved at call time. If you see calls
going to the wrong browser, this is why.

## MANDATORY PROTOCOL (Joe context)
Joe's benchmark: **he fills all 8 tabs by hand in ~3 hours.** A prior attempt burned
5 hours and did not finish one tab (UI/date-picker clicking). If you are past ~30 min
without a validated column, you are on the wrong path — switch to METHOD 0 below.

1. **Never fill a cell you can't prove.** For EACH store, first reproduce a known-good
   prior column (June) via API and diff to the cent. Show Joe the diff table. Only
   then produce the new month. This is what buys trust — he cross-checks.
2. **Never invent or SILENTLY estimate a number** — but do NOT leave a cell blank as a
   final answer either. Present the best-available figure WITH its basis and error band and
   let Joe authorize it. He does (2026-09-01, SV Care/Care Plus: *"you can write the 43.5 in
   there"* after seeing the ±8-hr both-directions table; and on AR SERVICE CONTRACT:
   *"I just make that number up... keep it within a certain believable number"*).
   The unacceptable thing is a confident number with no stated provenance — not an
   explicitly-labeled EST. Blank cells are a last resort for rows where even the grain is
   unknown, and they must be called out to Joe by row.
3. **One email/output per store**, fleet rollup only as an extra.
4. Flag anomalies as anomalies, not as data errors (e.g. Aug warranty +24% while
   everything else fell).

## METHOD 0b — THE ENGINE + VERIFIED BUCKETS (built 2026-08-31)
**Do NOT click the report UI / date calendar.** Joe's Advisor Performance screen is
backed by a plain internal API you can replay for any store, any window, in one call.
Engine: **`/home/itadmin/tekion-reports/wip_engine.py`** (drives the `:9225` browser).
Reproduced SCT June EXACTLY on 6 of 8 rows + all 6 ELRs to the cent on first pass;
whole-column pull takes ~5 tool calls instead of ~5 hours.

```python
import sys; sys.path.insert(0,"/home/itadmin/tekion-reports")
import wip_engine as W
W.arm()                      # builds auth headers from localStorage
G = W.saved_groups(876)      # Joe's saved filter groups, WITH their real definitions
a,b   = W.month_ms(2026,8)   # target month, Pacific
ya,yb = W.ytd_ms(2026,8)     # ELR window (ELR is the ONLY YTD row)
t = W.total_row(W.summary(876, filters))
W.hrs(t)      # billingTimeInSeconds/3600
W.rocount(t); W.elr(t); W.money(t,'totalLaborSaleAmount')
```

- **Endpoint:** `POST /api/service-module/u/reporting/advisor-performance/summary`
  body `{"reportName":"REPAIR_ORDER_REPORT","reportGroup":"REPAIR_ORDER",
  "filters":[{"field":"migrated","values":[false],"operator":"IN"}, ...],"projections":[]}`
  → `data.reportData[]`. **TOTAL row = the one with `primaryAdvisorId == "-1"`.**
  Hours in SECONDS, all $ in CENTS, `elrValue` already a float.
- **Read Joe's saved groups instead of guessing what a name means:**
  `GET /api/sales/settings/u/v1.0.0/groupFilter/ADVISOR_PERFORMANCE_REPORT_SUMMARY/filter/preference/list`
  → exact `field/operator/values` per group. This retires the whole
  "load group in the popover and squint at the rows" ritual.
- **AUTH HEADERS: build from `localStorage`, do NOT XHR-capture them.** Capturing a
  live request works but **dies the moment you navigate** (cost a debugging detour).
  `W.MKH` assembles them from `t_token` / `currentActiveRoleId` /
  `currentActiveDealerId` / `currentActiveSiteId` / `t_user.id`. Cross-store = just
  swap `dealerId` + `tek-siteId: -1_<id>` in the header dict; no dealer switching.
- **Opcode census:** `POST /api/service-module/u/opcode/search`
  `{"searchText":"TEK","pageInfo":{"start":0,"rows":2000},"filters":[]}` →
  `data.hits[]` with `opcode` + `category`. (SCT: 1,371 TEK opcodes, 316 SERVICE_MENU.)

### `/eval` JS pitfalls that cost time here
- A **regex literal** inside the JS payload (`/advisor-performance\/summary/`) made the
  `:9225` `/eval` endpoint return **HTTP 500**. Use `x.u.indexOf("...")>-1` instead.
- Wrap the whole IIFE in `try{}catch(e){return "EX:"+String(e)}` and return
  `await r.text()` into a `window.__VAR`, then parse in a second call — a throw inside
  the async IIFE also surfaces as an opaque 500.
- Report Builder search returns `j.data.esResponse.hits`, **not** `j.data.hits`.

### Bucket definitions VERIFIED against Joe's June SCT column (use these, not the group names)
The saved group names do NOT equal Joe's sheet math. Validated deltas:
| Row | Filter that reproduces the sheet | June check |
|---|---|---|
| CUSTOMER r4 | payType CP + opcodes NIN (TAC*+TSC*) — **NO makeId filter** | 2,666.82 ✅ (with the group's makeId → 2,613.92 ✗) |
| TOYOTA CARE r6 | opcodes IN TAC15–TAC80 + payType NIN WARRANTY | 283.70 ✅ |
| PREPAID r7 | opcodes IN TSC1–TSC10 + payType IN CUSTOMER_PAY | 895.35 ✅ |
| WARRANTY r8 | payType IN WARRANTY + **opcodes NIN the 30 TXM\* opcodes** | 1,000.80 ✅ (group alone → 1,519.90 ✗) |
| PDI r9 | opcodes IN [PDI] + payType IN INTERNAL | 418.40 (sheet 416.90, ~1.5 off) |
| INTERNAL r10 | opcodes NIN [PDI] + payType IN INTERNAL | 1,209.78 ✅ |
| ATTEND r13/r14 | makeId IN / NIN [toyota,scion], no status filter | 5,243 / 138 ✅ |
Date field = **`payTypeFirstClosedTime`** (Joe's clock). `roClosedTime`/`roCreatedTime`
give different numbers; `invoiceCreatedTime` returns 0. Window = CALENDAR month
(1st–EOM) — the 26th-to-25th window does NOT reproduce Joe's figures.

**ONLY SCT + VC have saved filter groups.** SV/BT/BC/TL return `[]` — derive their
buckets from opcodes and June-validate before filling anything.

## Data methods (validated 2026-08-03, SCT July) — LEGACY UI PATH, fallback only

### 1. Vehicle Attendance (RO count) — live OpenAPI, search-only, quota-cheap
`POST /repair-orders:search` filters: `closedTime BTW [monthStartPT_ms, monthEndPT_ms]` + `status IN CLOSED,INVOICED`, pageSize 200, paginate via `meta.nextPageToken`. NO fan-out → survives even when DEALER_QUOTA is tight (search itself kept working while /jobs fan-out 429'd). Script: `/home/itadmin/tekion-reports/wip_sct_july_attendance.py`. SCT July = 5,199.

**Make split (Joe's canonical filter — VERIFIED EXACT 2026-08-03):** saved filter group **"WIP Attendance - Toyota"** now exists on SCT Advisor Performance (built+saved by Jay via :9223): Pay Type Closed Date / Between / 1st–EOM + Make / In / Toyota, Scion (multi-select "In", NOT is-like). Applying it for July reproduced Joe's number EXACTLY: Total RO Count **5,060** (also Bill Hrs 6,386.37 all-paytype Toyota/Scion). TOYOTA row = that count; OTHERS = Make Not In Toyota/Scion. Save-group mechanics: funnel popover → "Save Filter Group" (top-right) → name input (placeholder "Type Here") + Save span; new group appears in the top singleValue dropdown options. Joe's clock = PAY TYPE CLOSED DATE; RO closedTime differs ~0.3% (DB-derived est was 5,073) — for the sheet use the report/filter-group number. In the DB: `payload->'vehicle'->>'make'` matched case-insensitively against `/toyota|scion/` (casing dirty: "toyota"+"Toyota"). Script: `/home/itadmin/dealer-detail/apps/web/wip_makes.cjs`. PITFALL: live OpenAPI `repair-orders:search` does NOT inline vehicle (link stub only) — make-split live needs per-RO fan-out; use the DB or the saved filter group. For non-Toyota stores confirm the make list per store brand with Joe before first use.

### 2. Hours by pay type / opcode buckets — dealer-detail DB (ZERO Tekion quota) ⭐
**Key discovery:** the dealer-detail Supabase DB (`/home/itadmin/dealer-detail/apps/web`, `RawRepairOrder.payload`) embeds the FULL RO snapshot: `payload.jobs[] = {job:{payType,subPayType,type}, operations:[{operation:{opcode, labor:{billDuration, laborAllowanceDuration, saleAmount, costAmount}}, parts:[...]}]}` plus `payload.vehicle.make`. So operation-level **billed hours = labor.billDuration / 3600** for a whole month with NO API fan-out. Query with a `.cjs` node script via Prisma `$queryRawUnsafe` (no psql installed): join `Store` on abbreviation (SCT/SCVW/BST/BC/TOL/VWC/ARSJ), window on `closeDate` (UTC: month start/end + 07:00 for PT). Working scripts: `apps/web/wip_sct_july_sanity.cjs`, `wip_probe.cjs`.

**Coverage caveat:** DB lags live — SCT July had 4,644 of 5,199 (89%). Report hour numbers as "slightly low" or backfill first (`npm run sync:store -- SCT <days>`, quota-gated).

**Backfill PITFALL (burned 2026-08-03):** `npm run sync:store` needs `.env` loaded — bare invocation prints "Missing required environment variables: DATABASE_URL..." yet still EXITS 0 and ingests NOTHING. Always wrap like the nightly cron: `cd apps/web && set -a && . ./.env && set +a && npm run sync:store -- SCT 35`. Verify ingestion afterward by re-counting the month's ROs (fetchedAt max should be fresh), never trust exit code alone.

### 3. Hours Sold bucket mapping (Joe confirmed 2026-08-03, CORRECTED same day)
The 7 hours rows come from Joe's SAVED FILTER GROUPS on SCT Advisor Performance (load group → set dates → Apply → read Bill Hrs TOTAL).

**⚠️ ONLY ELR IS YTD — EVERYTHING ELSE IS THE TARGET MONTH ONLY (Joe corrected 2026-08-03, same-day reversal of an earlier "needs to be YTD" instruction that turned out to be ELR-specific).** Rule:
- **ELR** (every ELR cell/row, e.g. r35-45 LABOR RATES/ELR block, r49-55 ACCESSORY ELRs) → date range 01/01/<year> → EOM of target month (YTD-to-date average).
- **Everything else** (Hours Sold r4-10, VEHICLE ATTENDANCE r13-14, WIP $, RO counts, parts $, TXM count/sale/cost/gross, workshop hours) → single calendar MONTH window (1st–EOM of the target month only), NOT YTD.
Verified July-only CP (07/01–07/31/2026): **Bill Hrs 2,211.33, ROs 3,177** — this is the correct number for the Hours Sold row. The YTD run (18,486.81/23,619/$174.65) is ONLY valid for the ELR figure ($174.65); do not use the YTD hours/RO-count for the monthly Hours Sold or Attendance rows.

Joe confirmed which groups:
- **CUSTOMER** = `Customer Pay Hours 10/1/2025` — was corrupted (stored Pay Type = **Internal**, stale save); FIXED + re-saved with Joe's approval 2026-08-03 (now Pay Type In Customer Pay). Definition: Pay Type Status In Closed + Opcode **Not In** TAC80–TAC15,TSC1–TSC10 + Pay Type In Customer Pay + Make In Toyota,Scion. (The Internal-corrupted run gave July 1,455.75 ≈ INTERNAL row's magnitude.)
- **WARRANTY** = `Warranty Hours 11/1` ✓ (Joe: correct)
- **TOYOTA CARE** = `TAC/TOYOTACARE REVISED 3/1/25` ✓
- **PREPAID MAINT** = `TSC/Prepaid Hours REVISED 3/1/25` ✓
- **PDI row's saved group is actually the INTERNAL bucket (RESOLVED + CONFIRMED 2026-08-03):** the saved group literally named "PDI" is configured as Opcode **"Not In" PDI** + Pay Type **"In" Internal** — i.e. it EXCLUDES PDI opcodes and scopes to Internal pay type. Jay flagged this as implausible for a PDI-only read (July gave Bill Hrs 1,126.78 / RO Count 4,720) rather than guessing; Joe confirmed: "yes, that's how I got the internal number" — **use this group's output for the INTERNAL row, not the PDI row.** A true standalone PDI-only filter (Opcode "In" PDI) has NOT been built/verified — if the sheet ever needs a distinct PDI number, that's still open; ask Joe rather than assume. **Lesson: a saved group's NAME is not proof of its filter logic — always re-open the funnel popover and read the actual field/operator/value rows before trusting output, especially if the resulting count looks implausible.**
- **WARRANTY TXM-exclusion (re-confirmed 2026-08-03):** Joe initially flagged the Warranty Hours 11/1 Bill Hrs (1,420.7) as possibly TXM-contaminated and had Jay test flipping Opcode from "Not In" TXM-list to "In" the same list to quantify the leak — mid-test Joe corrected himself: "I made a mistake, TXM filter is correct." The group's Opcode "Not In" [TXM list] is CORRECT as-is; no fix needed. Always revert a diagnostic "In"-flip test back to "Not In" immediately once told the filter is fine, before moving on (don't leave the report in the test state).
- **⚠️ TXM ROW = Report Builder "SCP-Toyota Care 2.0" (Joe CONFIRMED 2026-08-31: "SCP-Toyota Care 2.0, YOU GOT IT!").**
  This SUPERSEDES the earlier note that pointed this report at the TOYOTA CARE row —
  that was wrong twice over (first "TXM = SCP", then "corrected" to TOYOTA CARE, now
  back to TXM and confirmed by Joe). **TOYOTA CARE comes from the TAC opcodes via the
  Advisor Performance API** (see METHOD 0 table); **SCP-Toyota Care 2.0 feeds the TXM
  row + the TXM COUNT/SALE/COST/GROSS + TXM PARTS block (r60-67).**
  Report id `6a45095462e5ff667243d553`, `/report-manager/report/<id>/reportType/custom/detail`.
  **Its real filter is `RO_OPERATION_OPCODE STARTS_WITH "TEK"`** + `RO_OPERATION_CATEGORY
  EQUALS [Vehicle, Maintenance]`, grouped by `RO_NUMBER` — i.e. FACTORY MENU opcodes,
  **NOT** the `TXM*` opcodes. That is why no TXM*-opcode filter can ever reproduce it
  (I burned many calls trying every date basis, TXMPLUS, and make filter before
  reading the config). Read the config, don't guess:
  `POST /api/reportbuilder/u/report/search` `{"searchText":"SCP","searchFields":["name"],
  "sort":[{"field":"modifiedTime","order":"DESC"}],"pageInfo":{"start":0,"rows":50},
  "includeDeleted":false}` → `data.esResponse.hits[0]` has `filterConfigs`, `kpiMetrics`, `fields`.
  KPI read = **"Operation Assigned Bill Hours (Total)"**; record count = "N Record(s)".
  **TIMING TRAP:** the report is `DATE_RELATIVE / LAST_MONTH`, so it renders the PRIOR
  month and only flips after midnight on the 1st. Pulling the WIP column on the last
  day of the month gets you the WRONG month — wait for the flip, or estimate from the
  dealer-detail DB (`payload.jobs[].operations[]` where opcode `^TEK`, using
  `laborAllowanceDuration/3600`) which reproduced 1,013 of 1,038 records = 97.6%
  (gap = sync lag, not logic). Say which one you used.
- **Advisor Performance sums whole ROs; this report sums OPERATIONS.** Never expect the
  advisor-performance API to reproduce an operation-grain Report Builder number. Report has a relative date filter "RO Closed Date = Last Month" that AUTO-SHIFTS each month — no manual date entry needed, just open it on/after the 1st of the following month. Gotcha: the page's "Latest successful sync"/"Last Updated" timestamp can show a STALE date (e.g. showed "Jul 3" when opened Aug 3) — this is cosmetic; the underlying data table still reflects the FULL target month (verified max row date = last day of month, 1,038 records). Read the KPI summary strip or the Total row for **Operation Assigned Bill Hours (Total)**. Verified July SCT: Bill Hrs = **493**. For **TOYOTA CARE's ELR (YTD)**, use the separate saved Advisor Performance group **`TAC/TOYOTACARE REVISED 3/1/25`** with dates set 01/01→EOM-of-target-month (verified July SCT: ELR $118.34, matches Prepaid Maint's ELR coincidentally — both are OEM-mandated-maintenance opcodes, not a bug). So TOYOTA CARE row = TWO sources: Report Builder (Bill Hrs) + saved filter group (ELR YTD).
- ~~TXM row's own source is now UNRESOLVED again~~ **STALE — IGNORE. RESOLVED 2026-08-31:
  Joe confirmed verbatim "SCP-Toyota Care 2.0, YOU GOT IT!"** TXM row + the TXM
  COUNT/SALE/COST/GROSS + TXM PARTS block all come from Report Builder
  `SCP-Toyota Care 2.0` (id `6a45095462e5ff667243d553`). Still open: whether BT/TL have
  their own per-store copy of that report or share SCT's — ask Joe.
- Attendance = `WIP Attendance - Toyota` group (see above).
SAVED-GROUP PITFALLS: loaded groups carry STALE dates (reset every time) and possibly WRONG edited-then-saved values — read every row (esp. Pay Type) after loading, before Apply. Date calendar: month-grid cells have no onClick — advance RIGHT panel arrow first, then LEFT (left arrow caps adjacent to right panel); details in tekion-standard-reports-performance skill. For YTD: left-panel prev-month arrow (~606,441) back to Jan, click "1" in left panel, click "31" (or EOM) in right panel — range inputs update only after BOTH ends clicked.

**SWITCHING THE SAVED-GROUP DROPDOWN ITSELF (fix, 2026-08-03):** switching the LOADED GROUP (the react-select showing e.g. "Customer Pay Hours 10/1/2025" at the top of the popover) to a different saved group (e.g. "Warranty Hours 11/1") via a raw `/mouse` COORDINATE click on the option row is UNRELIABLE — coordinates drift/mis-hit between renders, and a wrong click can add a stray filter row (e.g. "Bill Hrs Equals") instead of switching groups, leaving the popover in a corrupted "*Edited" state. FIX:\n1. If popover shows "*Edited" or looks corrupted, navigate away (e.g. `/navigate` to `.../home`) and back to the report URL for a clean remount — a same-URL/hash-only reload does NOT reset it.\n2. Open funnel icon via `/mouse` on `.root_filterTrigger_icon` bounding-rect center.\n3. Click the group select control via `/mouse` on `.ant-popover [class*="-control"]` bounding-rect center to open the option listbox.\n4. Query live option elements: `document.querySelectorAll('[id*="option"]')` filtered to `offsetParent` truthy; find target by exact `innerText.trim()` match.\n5. Do NOT click by coordinate. Instead dispatch events directly on that found element in one `/eval` call: `target.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}))`, then `mouseup`, then `target.click()`.\n6. Verify by reading `document.querySelector('.ant-popover').innerText` afterward — confirm group name + a few dependent filter values changed as expected (e.g. Pay Type flipped, Opcode list flipped) BEFORE touching dates or clicking Apply.\nThis mirrors the existing Apply-button dispatch fix below — /mouse coordinate clicks are unreliable on this popover's dynamically-positioned elements in general; prefer find-element-then-dispatch-events for every interactive control inside `.ant-popover`.

**"*Edited" IS NORMAL, NOT NECESSARILY CORRUPTION (clarified 2026-08-03):** after a successful Apply, reopening the funnel to change the date range again (e.g. switch from month-only to YTD for the ELR read) will show "*Edited" on the group name — this JUST MEANS the current dates differ from the saved default, it is expected/harmless mid-workflow. Only treat the popover as actually corrupted (needing a navigate-away-and-back reset) if you see an UNEXPECTED extra filter ROW that wasn't part of the group's definition (e.g. a stray "Bill Hrs Equals" row) — that's the real signal of a mis-click, not the "*Edited" badge alone.

**APPLY-VERIFICATION FIX (2026-08-03) — supersedes the "popover count drops to 0" check below:** polling `document.querySelectorAll('.ant-popover').length === 0` after clicking Apply is UNRELIABLE — in practice the popover element can persist in the DOM (count stays 1) for 10+ seconds even though Apply fully succeeded and the grid already refreshed with the new filtered data. Waiting on this check can cost several minutes of false "still open" polling. INSTEAD, after dispatching the Apply click: (1) wait ~2-3s, (2) read `document.body.innerText` and look for the new result-count/date-range in the filter summary bar, or better, take a `/screenshot` + `vision_analyze` and directly confirm the results table shows the expected filter name and a plausible new result count. Don't gate on popover DOM removal.
**APPLY-CLICK PITFALL (burned 2026-08-03):** clicking Apply via the :9223 `/mouse` endpoint at its coords SILENTLY FAILS on this popover — popover stays open (`*Edited` remains), grid never refreshes, and you'll poll stale totals forever. FIX: dispatch native MouseEvents on the LEAF element via /eval: `[...document.querySelectorAll('.ant-popover *')].filter(e=>e.offsetParent&&e.children.length===0&&e.innerText.trim()==='Apply')` → dispatch mousedown/mouseup/click with bubbles:true. Verify success = popover count drops to 0 AND Total row changes within ~10s. Also: :9223 `/screenshot` is **GET** returning JSON `{"screenshot": "<base64>"}` (POST /screenshot = 404).

### 3b. Bucket mapping via DB (cross-check only — never guess)
RO data exposes only THREE payTypes: CUSTOMER_PAY / WARRANTY / INTERNAL. The sheet splits 7 ways. Observed: TAC15–TAC80 opcodes under CP = TOYOTA CARE row (matches sct-toyotacare-billed-hours-report skill, "not Warranty" rule); TSC* opcodes under CP ≈ prepaid maintenance candidate; TXM* opcodes appear under WARRANTY. **PDI/TXM/PPM bucket definitions must come from Joe's saved Advisor Performance filters — ASK, don't infer.** (Asked 2026-08-03, answer pending — record it here when given.)

### 4. Workshop hours (avail/prod/unapplied) — ⭐ SOLVED VIA API, see METHOD 0c below
(Legacy: the Tech Performance report UI. Don't click it — replay the API.)

### 5. Labor Rates rows
Manual/rare — carry forward prior month unless Joe says changed.

## ⭐ METHOD 0c — WORKSHOP ANALYSIS BLOCK (rows 17–21) — SOLVED 2026-09-01
Joe: *"I get the available hours/productive hours from the technician performance reports."*
One API call per store. **Exact to the cent on 6 of 7 dealers on the first attempt.**

```python
POST /api/service-module/u/reporting/technician
{"reportName":"FLAG_TIME_REPORT","reportGroup":"FLAG_REPORT","metrics":[],
 "pageInfo":{"start":0,"rows":300},
 "filters":[{"field":"payDay","operator":"BTW","values":[monthStartMs, monthEndMs]}]}
→ data.lineItems[]   # techId "-1" is the TOTAL row
```
Same 2-header cross-store swap (`dealerId`, `tek-siteId: -1_<id>`) as the advisor API.

| Sheet row | Field | Note |
|---|---|---|
| TOTAL AVAIL HOURS | `attendanceTimeInSeconds` / 3600 | |
| TOTAL PROD HOURS | `assignedBillingTimeInSeconds` / 3600 | **NOT** `flagTimeInSeconds` / `clockTimeInSeconds` |
| UNAPPLIED | AVAIL − PROD | derive it; don't use `unAppliedTimeInSeconds` (it's signed/different) |

**Note the date field is `payDay`** — not `payTypeFirstClosedTime`. This is the flag-date
window. Hours here ARE in seconds (unlike operation-grain Report Builder).

June 2026 validation: SCT 7747.94/7008.48 ✅ · SV 2112.45/1518.06 ✅ · TL 3783.05/4204.85 ✅ ·
VC 2358.91/1243.83 ✅ · AR 713.27/599.61 ✅ · BC 3356.87 ✅/4079.80 (−1.0) · BT ✗ (see below).

**Self-check built into the sheet:** AVAIL − PROD == UNAPPLIED exactly (7747.94 − 7008.48
= 739.46). If your two numbers don't reproduce the prior month's UNAPPLIED, you picked the
wrong fields — verify before pulling all 8 tabs.

### ✅ BT service-vs-body split — SOLVED 2026-09-01 via `departmentId`
Joe: *"in the filters, there is a filter for department. I put collision center."*
Tech Performance returns **both BT tabs combined** by default (4,592 avail / 7,138 prod).
The `BT_BODY` advisor-ID trick from DISCOVERY 1 does **not** work here — this endpoint is
keyed by **techId**, not advisorId. The real dimension is `departmentId`:

```python
D3N = {"field":"departmentId","operator":"NIN","values":["1249_department_3"]}  # → BODY SHOP tab
D3I = {"field":"departmentId","operator":"IN", "values":["1249_department_3"]}  # → SERVICE tab
```
June 2026: body prod **1,355.40** = sheet **1,355.40** ✅ exact · service prod 5,782.92 vs
sheet 5,783.72 ✅ (0.80 reopened-RO drift).

🚨 **THE NAMING TRAP — the operator is inverted from what the group name implies.** Joe's
saved group is called **"Toyota Body Shop"** but its filter is `departmentId **NIN**
["1249_department_3"]`. So `1249_department_3` **IS main service**, and *excluding* it is
what leaves collision. If you read the group name and write `IN`, you silently get the
service tab's number on the body tab. Same lesson as the ADVISOR_PERFORMANCE `PDI` group:
**read the literal operator, never infer from the name.**

🔑 **How the ID was found (reuse this for any multi-department store):**
```
GET /api/sales/settings/u/v1.0.0/groupFilter/TECH_PERFORMANCE/filter/preference/list
→ data[] = {groupName, filters:[{field,operator,values}]}
```
BT returns `Toyota Body Shop` (the NIN rule above) + `Toyota Service Main` (no dept filter).
**Do not guess department IDs and do not hunt for a departments endpoint** — read Joe's own
saved group and lift the value verbatim. This is the TECH_PERFORMANCE sibling of the
ADVISOR_PERFORMANCE_REPORT_SUMMARY group-filter endpoint documented in METHOD 0.

**Only BT has a department split.** Full sweep of the TECH_PERFORMANCE groups:
SCT `Xpress RTH` / `Main shop RTH` (techId lists) · SV `Xpress RTH` / `RTH` / `Tech RTH` ·
BC `Main RTH` · TL `Team C Dispatch` · **VC and AR have none.** Every non-BT store is
single-department, which is why they all validated clean without a filter.

⚠️ **The department filter splits PRODUCTIVE hours but NOT attendance** — both branches
return avail 4,451.53. That's why the sheet's Body Shop avail is a round **1,300** (manual
capacity, not from Tekion). Carry Joe's manual figure forward; don't overwrite it.

Dead ends confirmed here (do not re-probe):
- Guessing dept values: `departmentId IN ["SERVICE"]` → 0 rows (field is valid, value wasn't).
  `department`/`departmentIds`/`laborType`/`techDepartment` → 400.
- `serviceMode IN [SERVICE]` → returns techs but prod 0.
- `groupBy` must be a LIST (`[{field,size}]`) — a bare string 400s. Grouping by
  `departmentId`/`serviceMode` does NOT bucket; returns the same single total.
- No departments endpoint exists: `/api/service-module/u/departments` + 13 other candidates
  all 404/500. **The saved-group endpoint is the only way in.**
- Tech-name resolution: `/api/users/u/<id>` → 404, and `/api/{u/employees,users,employee}/search`
  all 404. `lineItems[]` carries **only `techId`** — no name field.
- **Subset-sum is a trap.** Before finding the department filter I got an exact arithmetic
  split (body = 140.65 avail / 1,354.60 prod: one attendance tech + 10 of 17 zero-attendance
  techs). 10-of-17 has too many combinations for an exact hit to mean anything. It happened
  to be right, but it was unfalsifiable — refusing to write it and asking Joe instead took
  one message and produced the real, reusable answer.

## ⭐ METHOD 0d — THE FULL ELR BLOCK (rows 34–55) — SOLVED 2026-09-01
**ELR is the ONLY YTD block** (`W.ytd_ms(y,m)` = Jan 1 → EOM target). Joe flagged this
directly: *"ELR???? that is a YTD number for all the toyota stores."*

🔑 **The asymmetry that breaks a naive pass: rows 35–41 are STORE-WIDE (no make filter),
rows 43–45 filter to NON-Toyota.** "TOYOTA CUSTOMER" does *not* mean `makeId IN [toyota]`
— adding that filter gives 174.93 instead of 174.77. The `OTHER *` rows are the only
make-filtered ones. Read `elrValue` off the `-1` total row.

| Row | Filter (+ `CL` + YTD window) | June | Got |
|---|---|---|---|
| r35 TOYOTA CUSTOMER | `payType CP` + `opcodes NIN [TAC*+TSC*]` | 174.77 | **174.77** ✅ |
| r36 TOYOTA WARRANTY | `payType WARRANTY` | 304.78 | 300.04 ⚠️ |
| r37 TOYOTA INTERNAL | `payType INTERNAL` + `opcodes NIN [PDI]` | 147.92 | **147.92** ✅ |
| r38 TOYOTA TXM | `opcodes IN [TXM 30-set]` | 291.76 | **291.76** ✅ |
| r39 TOYOTA CARE | `opcodes IN [TAC*]` | 117.47 | 117.49 ✅ |
| r40 TOYOTA PREPAID | `opcodes IN [TSC*]` | 118.75 | 118.72 ✅ |
| r41 TOYOTA PDI | `opcodes IN [PDI]` | 286.16 | **286.16** ✅ |
| r43 OTHER CUSTOMER | `payType CP` + `makeId NIN [toyota,scion]` | 163.15 | **163.15** ✅ |
| r45 OTHER INTERNAL | `payType INTERNAL` + `makeId NIN [toyota,scion]` | 196.87 | **196.87** ✅ |

Note r35/r37 reuse the **same exclusions as their Hours Sold counterparts** (CP excludes
TAC/TSC; INTERNAL excludes PDI) — mirror the block-1 recipe, just swap the window to YTD
and read `elrValue` instead of hours. r36 warranty runs ~1.5% low (reopened ROs, expected
drift on an old month). r44 OTHER WARRANTY is 0.00 in the sheet — don't chase it.

### TXM COUNT/SALE/COST block (rows 57–67) — grain confirmed, opcode set incomplete
The advisor API with the TXM 30-opcode group returns `roCount` **1,007 vs the sheet's
1,442** for June, and EVERY dollar field is low by that same ~70% ratio
(labor sale 156,611 vs 215,399; parts sale 38,760 vs 48,333). **Same root cause as the
TXM hours gap** — the saved opcode set is missing members. Confirms the block is
operation-grain and must come from Report Builder `SCP-Toyota Care 2.0`, not this API.
Money fields come back as **strings** in some rows — coerce with `float()` before dividing
by 100 (a raw `row[k]/100` throws `TypeError: unsupported operand type(s) for /: 'str'`).

## Sanity-check protocol (Joe asked for this explicitly)
**Reproduce the PRIOR month's column first (see METHOD 0's validation table) and show Joe
the match table before filling the new month.** He fills the sheet by hand from numbers
posted in Slack, so deliver in row order, per store, and flag any row you could NOT
reproduce rather than shipping a guessed value. Joe accepts "I don't know yet" but not
confident wrong answers.

### ⏱ TIME BUDGET (Joe raised this directly, 2026-08-31)
He did the entire 8-tab workbook by hand in ~3 hours; a prior Jay attempt spent ~5 hours
and finished zero tabs. Rules now:
- Go to METHOD 0 (API) immediately. Do NOT open the report UI, and never touch the
  ant-calendar date picker.
- Budget ~10 min per store tab once the engine is armed.
- If you're 30+ minutes in with no validated numbers, STOP and tell Joe what's blocking.
- Don't build new tooling mid-task while he waits — grind the known path, script it after.

## YTD variant — ELR ONLY (verified 2026-08-03, corrected same day)
Joe's rule: **only the ELR figure is YTD**; every other cell (hours, RO counts, attendance, $ totals) uses the single target MONTH. Use this YTD date-range method only when computing an ELR row/cell. Same saved groups, just set Pay Type Closed Date = 01/01/YYYY → end of current month for the ELR read, then re-Apply with 1st–EOM of the target month for the actual Hours Sold number from the same group. Date entry: open funnel → click the START date input in the popover → use `.ant-calendar-prev-month-btn` nav arrow (~606,441) repeatedly until left panel header = "Jan YYYY" → click day 1 in `.ant-calendar-range-left` → click day 31 (end day) in `.ant-calendar-range-right` (right panel will already show the end month). Inputs update to 01/01/2026 / 07/31/2026 and the calendar closes.

**CRITICAL APPLY PITFALL:** the popover's Apply button does NOT respond to /mouse coordinate clicks (popover stays open, grid keeps stale totals — polled 60s with no change). Must dispatch a native MouseEvent on the leaf Apply element via /eval:
```js
const els=[...document.querySelectorAll('.ant-popover *')].filter(e=>e.offsetParent&&e.children.length===0&&e.innerText.trim()==='Apply');
const el=els[els.length-1];const b=el.getBoundingClientRect();
['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:b.x+b.width/2,clientY:b.y+b.height/2})));
```
Verify success = popover count drops to 0 AND grid Total changes within ~10s. Poll `document.body.innerText` slice after 'Sublet Parts Cost' until the old RO count disappears.

Total-row read order after 'Sublet Parts Cost\nTotal\n': ROcount, [6 $ columns], **BillHrs**, ELR, ... (e.g. YTD CP: `23619 ... 18486.81, 174.65`).

/screenshot endpoint = **GET** returning JSON `{screenshot: <base64>}` — not POST.

**Verified YTD CP (SCT, 01/01–07/31/2026): Bill Hrs 18,486.81, ROs 23,619, ELR $174.65** (July-only was 2,211.33 / 3,177 / $172.63).

## Pitfalls
- OpenAPI RO search results have NO `id` field — use `documentId`; jobs live at `data.jobs`, operations at `data.roOperations` (fan-out path only).
- `get_token(cfg)` requires the cfg arg (`sys.path.insert(0,"/home/itadmin/tekion-api")`).
- 2-4 AM PT = VI pull window; DEALER_QUOTA 429s on fan-out likely. Search-only endpoints still worked.
- Labor $ in CENTS (/100); billDuration in SECONDS (/3600).
- Header dates (26th) are cosmetic — window is calendar month (Joe, 2026-08-03).

## SCT July 2026 — full Hours Sold table LOCKED (2026-08-03, ready for Excel)
| Bucket | Bill Hrs (July) | RO Count (July) | ELR (YTD) |
|---|---|---|---|
| CUSTOMER | 2,211.33 | 3,177 | $174.65 |
| WARRANTY | 1,420.7 | 1,571 | $303.69 |
| TOYOTA CARE | 493 | — | $118.34 |
| PREPAID MAINT | 966.79 | 796 | $118.34 |
| INTERNAL | 1,126.78 | 4,720 | $148.60 |
| ATTENDANCE (Toyota row) | 5,060 (RO count, from WIP Attendance - Toyota group) | | |
PDI and TXM rows still unresolved as of this pass — see notes above; do not guess, ask Joe.

## Reusable date-range + Apply code pattern (verified working end-to-end, 2026-08-03)
For a MONTH-only window (e.g. 07/01-07/31/2026), after loading the group, the popover's calendar typically opens with left panel = prior month, right panel = target month already (since Tekion defaults near "today"). Steps that reliably worked:
1. Click the Start-date input to open the calendar (`/mouse` on its bounding-rect center is fine for this one field — it's the calendar CELLS and Apply button that need the dispatch trick, not this input).
2. Read `.ant-calendar-my-select` (2 elements = left/right panel headers) to see which months are showing.
3. If the RIGHT panel isn't the target month yet, click `.ant-calendar-next-month-btn` (or `.ant-calendar-prev-month-btn` to go back) repeatedly until it is — poll the my-select text after each click.
4. Click day "1" in `.ant-calendar-range-right .ant-calendar-cell` (filter `innerText.trim()==='1'` and NOT class `last-month`/`next-month`) to set the START date directly in the target month (do this INSTEAD of navigating the left panel back if left panel would land on the wrong month for a same-month range).
5. Click day "31" (or EOM) similarly in the right panel for END date.
6. Confirm both inputs read the expected values before Apply: `[...document.querySelectorAll('.ant-popover input')].filter(e=>e.offsetParent&&(e.placeholder==='Start date'||e.placeholder==='End date')).map(e=>({ph:e.placeholder,val:e.value}))`.
7. Apply via the leaf-element MouseEvent dispatch trick (see APPLY-CLICK PITFALL above) — never `/mouse` coordinates on Apply.
8. Read the Total row via `document.body.innerText`, slice from `\nTotal\n` — column order is: RO Count, Labor Cost, Labor Sale, Labor Gross, Parts Cost, Parts Sale, Parts Gross, **Bill Hrs**, **ELR ($)**, Coupon Labor, Labor GP%, Sublet Parts Gross, Coupon Parts, ELR%, ELR/RO, Hrs/RO, GP%, Total Gross, Total Sales, Total Cost, Parts GP%, Sublet Labor Sale/Cost/Gross, Sublet Parts Sale/Cost.
For a YTD window (01/01→EOM target month): same mechanics but the LEFT panel needs multiple `.ant-calendar-prev-month-btn` clicks to reach January, then click day "1" in the LEFT panel and day "31"/EOM in the RIGHT panel (which should already show the target month).
