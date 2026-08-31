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

### ✅ TXM ROW — RESOLVED 2026-08-31 (see METHOD 0b for the full recipe)
Joe confirmed the source is Report Builder **`SCP-Toyota Care 2.0`** (operation-grain,
`RO_OPERATION_OPCODE STARTS_WITH "TEK"`), NOT Advisor Performance. The elimination log
below is kept only so nobody re-walks it:

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

### METHOD 0c — ALL 8 TABS, JUNE-VALIDATED (2026-08-31). START HERE.

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
| SV Care/Care Plus | 63.21 (using VC's opcode list) | 35.20 | −28 |
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

## MANDATORY PROTOCOL (Joe context)
Joe's benchmark: **he fills all 8 tabs by hand in ~3 hours.** A prior attempt burned
5 hours and did not finish one tab (UI/date-picker clicking). If you are past ~30 min
without a validated column, you are on the wrong path — switch to METHOD 0 below.

1. **Never fill a cell you can't prove.** For EACH store, first reproduce a known-good
   prior column (June) via API and diff to the cent. Show Joe the diff table. Only
   then produce the new month. This is what buys trust — he cross-checks.
2. **Never invent or silently estimate a number.** If a row won't reproduce, say so and
   ask (TXM, this session). Joe accepts "I don't know yet"; he does not accept a
   confident wrong number.
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

### 4. Workshop hours (avail/prod/unapplied)
Tekion Tech Performance report (see tekion-standard-reports-performance skill), flag-date window = calendar month.

### 5. Labor Rates rows
Manual/rare — carry forward prior month unless Joe says changed.

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
