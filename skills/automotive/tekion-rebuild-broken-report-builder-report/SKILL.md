---
name: tekion-rebuild-broken-report-builder-report
description: >
  Diagnose a Tekion Report Builder custom report that a manager says is "not
  working" (wrong/low numbers, blank, zero rows), then REBUILD it as a live
  OpenAPI-sourced report. Covers pulling the report's real definition, running
  it natively via the RB execute API, proving index staleness vs a definition
  bug, and shipping an API replacement + PNG/PDF scorecard by email.
triggers:
  - report builder not working
  - my report is broken
  - recreate it from the api
  - report shows wrong numbers
  - report is missing days
  - rebuild tekion report
  - report builder stale
---

# Rebuild a Broken Tekion Report Builder Report from the API

Proven end-to-end 2026-09-01 on **Toyota of Lancaster (TL, dealer 1092)**,
report *"SCP OP Code-ToyotaCare (TXM)"* → shipped `tl_tac_api.py` +
`render_tl_tac.py` + emailed scorecard, all in one session.

Joe's ask is almost always literally **"can you recreate it from the API?"** —
see AUTOMATION MANDATE. Don't hand back a config fix. Diagnose, then ship the
API replacement.

---

## 0. Get the store first, then STOP GUESSING which report

Joe will name the store ("toyota lancaster") and often only a nickname for the
report ("TAC"). **Enumerate all reports for that dealer and show him the list**
rather than probing. One `report/search` call gets all of them.

---

## 1. Authenticate the internal API (the 401 trap)

`/home/itadmin/tekion-reports/api-headers-live.json` holds a captured header
bundle — but its `tekion-api-token` **goes stale** and you get:

```
HTTP 401 {"errorCode":"AUTH401","key":"session.expired"}
```

**Fix in one call** — pull the live token out of the `:9223` browser and swap it
in. Note the eval endpoint parameter is **`js`**, NOT `expression`
(`{"error":"js is required"}` if you get this wrong):

```python
import json, subprocess, urllib.request
r = subprocess.run(["curl","-s","-m","15","http://127.0.0.1:9223/eval",
     "-H","Content-Type: application/json",
     "-d", json.dumps({"js":"JSON.stringify({t:localStorage.getItem('t_token')})"})],
     capture_output=True, text=True)
tok = json.loads(json.loads(r.stdout)["result"])["t"]

h = dict(json.load(open("/home/itadmin/tekion-reports/api-headers-live.json")))
h["tekion-api-token"] = tok
h["dealerId"]   = "1092"          # target store
h["tek-siteId"] = "-1_1092"       # MUST match dealerId
h["Content-Type"] = "application/json"
json.dump(h, open("/tmp/tl-headers.json","w"))
```

The browser can be parked on a **different dealer** (it defaults to BC/1251) —
that is FINE for this API. Only the `dealerId` / `tek-siteId` **headers** scope
the report list. No dealer switch needed.

---

## 2. List the reports — searchText is UNRELIABLE, enumerate instead

```python
body = {"sort":[{"field":"modifiedTime","order":"DESC"}],"filters":[],
        "searchText":"", "searchFields":["name"],
        "pageInfo":{"start":0,"rows":100}, "includeDeleted":False}
POST /api/reportbuilder/u/report/search
→ data.esResponse.{count, hits[]}
```

⚠️ **`searchText` gives FALSE NEGATIVES.** Searching `"TAC"`, `"Toyota"`,
`"Care"`, `"Auto Care"` ALL returned **count 0** at TL — while the report
literally named *"SCP OP Code-ToyotaCare (TXM)"* was sitting in the full list.
(Yet `"TOL"`→16 and `"SCP"`→5 worked.) **Always pull the full list with
`searchText:""` and filter client-side in Python.** Set `includeDeleted:True`
to catch a report someone deleted (that's a valid "it's not working" cause) —
note the deleted-inclusive list can be a *different* length (82 vs 90 at TL).

Each hit already contains the **complete definition**: `dataSource`,
`filterConfigs`, `fields`, `groups`, `kpiMetrics`, `createdTime`,
`modifiedTime`, `reportSourceType`.

### Red flag readable straight off the list
`dataSource: null` = a structurally **incomplete** config. Four TL reports were
in this state. That alone explains "not working" — no execution possible.

---

## 3. Read the definition BEFORE running anything

Dump `filterConfigs` / `fields` / `kpiMetrics`. Two failure modes show up here
that no amount of UI clicking reveals:

**(a) The report's NAME LIES about what it filters.** TL's *"ToyotaCare (TXM)"*
report actually filtered:
- `RO_CLOSEDTIME` `DATE_RELATIVE / LAST_MONTH`
- `RO_OPERATION_OPCODE` **`STARTS_WITH "TEK"`**  ← menu opcodes, not TAC at all
- `RO_OPERATION_CATEGORY` `EQUALS "Vehicle"`

Joe asked for "TAC = Toyota Auto Care." The report was pulling the TEK menu
family. **Always reconcile the manager's mental model against the actual
`filterConfigs` and say so explicitly** — "they're two different reports wearing
one name."

**(b) A filter value that silently went stale → ZERO rows.**
`RO_OPERATION_CATEGORY = "Vehicle"` now returns **0 rows** at TL because the
operations come back with `category: "MAINTENANCE"`. A single stale enum value
zeroes a whole report with no error. **Test each filter by dropping it and
re-running** — the one whose removal takes you 0 → N is the culprit.

**(c) `RO_OPERATION_CATEGORY` is BROKEN IN BOTH DIRECTIONS — never trust it.**
Verified on TL *"SCP OP CODE-Menu Performance"* (`657c60166bb7cc7fbb9daf2b`,
filters `RO_OPERATION_OPCODE STARTS_WITH "TEK"` + `CATEGORY = "Service_menu"`),
August 2026:

| run | rows | category mix on the TEK ops |
|---|---|---|
| category filter **ON** | 74 | `SERVICE_MENU 77, VEHICLE 22, BRAKES 2` |
| category filter **OFF** | 704 | `VEHICLE 88, POWER_TRAIN 5, SERVICE_MENU 3, ELECTRICAL 2, BRAKES 2, SUSPENSION 1` |
| **truth (API, menu opcode list)** | **49** | — |

So the filter simultaneously **lets non-menu ops through** (BRAKES/VEHICLE) and
**drops real menus**. Neither 74 nor 704 is a menu count.
➡ **Opcode MEMBERSHIP is the only reliable discriminator. Drop every
`RO_OPERATION_CATEGORY` filter in a rebuild** and match against the store's real
opcode set instead.

Also **never use a `STARTS_WITH "TEK"` prefix as a menu filter** — `TEK` also
matches individual services (`TEK09*` ToyotaCare, `TEK07*`, `TEK03*`, `TEK05*`).
The real menu set is `opcodeType == SERVICE_MENU && status == ACTIVE`, frozen at
`data/<store>-menu-opcodes.json` (TL = 212 opcodes, 53 intervals × BNM/BSM/PSM/VNM).

**(d) A KPI that returns `0.0` no matter how many rows come back.**
The SCP report's `LABOR_GROSS:SUM` and `PARTS_GROSS:SUM` returned **`0.0` on
both** the 74-row and 704-row runs. The rows exist; the money never populates.
This is usually the *actual* reason a manager says "it's not working" — the
report renders, it just has no dollars. **Always read `projections` on a native
run and check for all-zero KPIs before blaming the date window.**

---

## 4. Run the report natively via the execute API (ground truth)

```python
POST /api/reportbuilder/u/execute/withOptions?preview=false
{"reportConfig": <the FULL hit object, UNMODIFIED>,
 "reportExecutionOptions":{"sort":[],"filters":[],"searchText":"","groupBy":[],
   "includeFields":[],"excludeFields":[],
   "pageInfo":{"start":0,"rows":500}}}
→ data.{count, hits[], projections, groups}
```
Paginate `pageInfo.start += 500`. Mutate ONLY `filterConfigs` on a deepcopy for
probes — **building a config from scratch 500s**.

`projections` carries the KPI totals keyed `<FIELDKEY>__<FUNC>`, e.g.
`REPAIRORDER_JOB_OPERATION_BILLING_TIME__SUM`.

### Row shape (dataSource REPAIR_ORDER)
Each hit is a whole RO with nested lists — the ops are in
**`repairOrderJobOperations[]`** (also `repairOrderJobs`, `...OperationParts`,
`...OperationTechnicians`, `...TechClockIns`, `...TechFlagHours`).
Per-op fields: `opcode`, `jobOpCodeDescription`, `billHours`,
**`laborAmount` (CENTS)**, `billingRate`, `operationFlagHours`.

---

## 5. PROVE staleness — this is usually the actual answer

```python
max(ts(h["ingestionTime"]) for h in hits)      # index freshness
min/max(ts(h["roClosedTime"]) for h in hits)   # data coverage
Counter(ts(h["roClosedTime"]))                 # per-day tail
```

TL result: **max ingestion 8/24, newest closed RO 8/22** — the last 9 days of
August were simply absent. Live API for the same window: **116 ops / 54.35 hrs
/ $7,105** vs RB's **99 / 46.25 / $5,981** = RB understating by **~15%**.

Report this as a **stale-vs-live delta table**. It is far more persuasive than
"the index lags," and it is the justification for the rebuild.

---

## 6. Build the API replacement

Two working templates in `/home/itadmin/tekion-reports/`, pick by shape:

| script | window field | matches on | emits |
|---|---|---|---|
| `tl_tac_api.py` | `closedTime` | fixed opcode family (TAC, TAC5…TAC80) | labor only, `lines[]` |
| `scp_menu_perf_api.py` | `creationTime` (`--closed` flips it) | `data/<store>-menu-opcodes.json` | labor **+ parts** gross, `rows[]` |

**MATCH THE DATE FIELD TO THE RB DEFINITION.** `RO_CREATEDTIME` → `creationTime`;
`RO_CLOSEDTIME` → `closedTime` (+ `status IN [CLOSED, INVOICED]`). Getting this
backwards produces a defensible-looking number that won't tie to Joe's report.

Structure:

1. **date BTW bisection** — recursive split until
   `meta.totalCount <= len(results)`, dedupe on `documentId`, drop `VOIDED`.
   `pageNumber` is ignored and `nextPageToken` drifts outside the window.
2. **Prefilter on the FREE `tags` OPCODE values** from the search result —
   TL August: 4,046 closed ROs → **116 candidates**. A 35x reduction; without
   this you WILL hit 429.
3. **Fan out** `jobs` → `jobs/{jid}/operations` with `ThreadPoolExecutor(5-6)`,
   429 backoff `25*(attempt+1)`.
4. **Parts gross needs a THIRD level**: `jobs/{jid}/operations/{oid}/parts` →
   sum `saleAmount`/`costAmount`. Vehicle columns (year/make/model/odometer,
   for `RO_YEAR`/`RO_MODEL`/`RO_ODOMETERIN`) come from
   `/repair-orders/{id}/ro-vehicle` — fetch it **lazily, once per RO, only after
   the first matching op**, or you triple the call count for nothing.
5. Hours: `labor.billableHours`, else `labor.billDuration/3600` (**seconds**).
   Money: `saleAmount`/`costAmount` in **CENTS**.
6. Dump raw lines to `data/<store>-<report>-<start>_<end>.json` so re-renders
   and by-advisor cuts never re-scan.

---

## 6b. When the ask is just a COUNT — do NOT run the full rebuild

"How many TSC ROs did we generate in August?" does **not** need the operations
fan-out. The `tags[] {field:"OPCODE"}` values on the plain
`/repair-orders:search` result are enough, and the whole month runs in ~3.5 min
with **zero** per-RO calls.

```
tl_opcode_ro_count.py <start> <end> <store> <creationTime|closedTime> OP1,OP2,...
```
Prints total ROs in window, unique ROs containing any of the opcodes, per-opcode
counts, and a status breakdown. TL Aug 2026 TSC: 4,118 ROs → **647** with
TSC1–TSC5 (145/144/137/114/107), 626 CLOSED.

**Discover the opcode family first** — never assume the codes. Internal
`POST /api/service-module/u/opcode/search` with
`{"searchText":"TSC","pageInfo":{"start":0,"rows":200},"filters":[],"sort":[]}`
→ `data.hits[]` with `opcode / opcodeType / status / description`. TL has
exactly 5 TSC (`INDIVIDUAL_SERVICE`, all ACTIVE). Opcode schemes differ per
store — derive, don't reuse another store's list.

---

⏱ **A full month is ~200s of search alone — it EXCEEDS the 180s foreground
terminal limit.** Run it `background=true, notify_on_complete=true`. A YTD scan
is ~25–30 min.

⚠️ **BACKGROUND JOBS DIE SILENTLY.** The first TL YTD run sat with an **empty
log for 25 minutes**, then `ps -o etime=,stat=` showed state **`Zs`** — a
zombie, dead, no output file. `notify_on_complete` never fired. Two hard rules:
- Always launch with **`python3.11 -u`** (unbuffered) or the log stays empty and
  you cannot tell "still working" from "dead."
- Before reporting "still running," verify with
  `ps -p <pid> -o etime=,stat=` **and** check the output JSON exists. `Z`/`Zs`
  = relaunch it. Don't promise the user a number off a job you haven't proven
  is alive.

### Advisor names
`assignee.advisor.id` is free on the search result. Resolve via OpenAPI
`GET /openapi/v4.0.0/users/{id}` → `userNameDetails.completeNames[DISPLAY_NAME]`.
Cache to `data/<store>-advisor-cache.json`. 14 TL advisors resolved in ~4s.

---

## 7. Render + email

- Renderer templates: `render_tl_tac.py` (labor/ELR shape) and
  **`render_tl_scp.py`** (labor+parts gross shape: KPI cards, By-Opcode,
  By-Advisor with bars, **page 2 = full RO line detail** — created date, RO#,
  advisor, opcode, vehicle, odometer, hrs, labor/parts/total gross).
  Joe's "by advisor" means summary table **AND** RO-level detail on its own page.
- **Put the defect list IN the report**, not just the email — a red-accented
  `.note.warn` block enumerating why the RB version is wrong. Joe reads the PNG.
- **Branding: TL has NO logo asset** — text wordmark "TOYOTA OF / LANCASTER" in
  `#1a1a1a` / `#EB0A1E`. NEVER use `logo_0.png`/`logo_st.png` (both SCT).
- `vision_analyze` the PNG asking "what dealership branding is in the header?
  are columns cut off?" before sending. (It misreads digits — check layout only,
  never transcribe numbers from it.)
- Send with `from jay_mail import send_report` (SMTP, verifies delivery).
  Include the **stale-vs-live delta** in the email body — that's the headline.

---

## Pitfalls recap
- `:9223` `/eval` param is **`js`** not `expression`.
- Stale `tekion-api-token` → 401 `session.expired`; refresh from `t_token`.
- `report/search` `searchText` false-negatives — enumerate with `""`.
- `dataSource: null` on a hit = broken config, not a data problem.
- The report name may describe a different opcode family than it filters.
- A stale filter ENUM (`category: "Vehicle"`) silently returns 0 rows.
- **`RO_OPERATION_CATEGORY` is wrong in both directions — always drop it.**
- **`STARTS_WITH "TEK"` ≠ menus** — use the SERVICE_MENU opcode list.
- **All-zero KPI `projections` with non-zero row count** = the real complaint.
- Match the rebuild's date field to the RB filter (`RO_CREATEDTIME` vs `RO_CLOSEDTIME`).
- Deepcopy + mutate `filterConfigs` only; hand-built configs 500.
- Full-month scans must run in the background, with `-u`, and verify not zombie.
- Pure counts: use the free `tags` OPCODE prefilter, skip the op fan-out entirely.
