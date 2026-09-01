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

Template: `/home/itadmin/tekion-reports/tl_tac_api.py`
(`tl_tac_api.py <start> <end> <dealer_key>`). Structure:

1. **`closedTime` BTW bisection** — recursive split until
   `meta.totalCount <= len(results)`, dedupe on `documentId`.
   `pageNumber` is ignored and `nextPageToken` drifts outside the window.
2. **Prefilter on the FREE `tags` OPCODE values** from the search result —
   TL August: 4,046 closed ROs → **116 candidates**. A 35x reduction; without
   this you WILL hit 429.
3. **Fan out** `jobs` → `jobs/{jid}/operations` with `ThreadPoolExecutor(6)`,
   429 backoff `25*(attempt+1)`.
4. Hours: `labor.billableHours`, else `labor.billDuration/3600` (**seconds**).
   Money: `saleAmount`/`costAmount` in **CENTS**.
5. Dump raw lines to `data/<store>-<report>-<start>_<end>.json` so re-renders
   and by-advisor cuts never re-scan.

⏱ **A full month is ~200s of search alone — it EXCEEDS the 180s foreground
terminal limit.** Run it `background=true, notify_on_complete=true`. A YTD scan
is ~25–30 min.

### Advisor names
`assignee.advisor.id` is free on the search result. Resolve via OpenAPI
`GET /openapi/v4.0.0/users/{id}` → `userNameDetails.completeNames[DISPLAY_NAME]`.
Cache to `data/<store>-advisor-cache.json`. 14 TL advisors resolved in ~4s.

---

## 7. Render + email

- Renderer template: `/home/itadmin/tekion-reports/render_tl_tac.py`
  (KPI cards incl. **ELR**, By-Opcode table, By-Advisor table with bar, optional
  YTD comparison block).
- **Branding: TL has NO logo asset** — text wordmark "TOYOTA OF / LANCASTER" in
  `#1a1a1a` / `#EB0A1E`. NEVER use `logo_0.png`/`logo_st.png` (both SCT).
- `vision_analyze` the PNG asking "what dealership branding is in the header?
  are columns cut off?" before sending.
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
- Deepcopy + mutate `filterConfigs` only; hand-built configs 500.
- Full-month scans must run in the background.
