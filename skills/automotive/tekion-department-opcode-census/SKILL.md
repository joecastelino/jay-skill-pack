---
name: tekion-department-opcode-census
description: Answer "what opcodes would I need to build for department X" / "run a report of ROs closed in the <UCD/PDI/Body Shop/Express> department over the last N days". Produces the opcode list a department actually uses, classified EXCLUSIVE vs SHARED, cross-referenced against the Service Type each opcode is tagged to — which is what determines whether a GL-mapping-by-Service-Type change will actually capture the work.
triggers:
  - opcode list for department
  - what opcodes do I need to build
  - ROs closed in used car department
  - UCD opcodes
  - department opcode report
  - which opcodes does PDI use
  - build opcode set for a department
---

# Tekion — Department Opcode Census (what opcodes does dept X actually use?)

Joe's ask shape: *"I need to change the default internal account for the UCD
department… can you get me an opcode list that I would need to build for UCD? Run a
report over the last 90 days for ROs closed in used car department?"*

This is **not** just "list the opcodes." The useful deliverable is a three-way
classification that tells him whether his planned GL change will actually work:

1. Which opcodes the department uses, ranked by volume
2. **EXCLUSIVE vs SHARED** — is this opcode used ONLY by that dept, or also store-wide?
3. Which opcodes are already tagged to the department's **Service Type** (the thing
   the GL mapping actually routes on)

The punchline is almost always: *"you already have a Service Type and 6 tagged
opcodes; the gap is N shared opcodes you CANNOT retag without collateral damage."*

**Read first:** `tekion-internal-cost-center-gl-routing` (why Service Type is the
routing dimension), `tekion-openapi-repair-orders` (search/pagination mechanics),
`tekion-opcode-api` (the internal opcode search + serviceTypes endpoints).

---

## Step 1 — Enumerate ROs and census the departments (OpenAPI, no browser)

`assignee.department.id` is **free** on every `repair-orders:search` result — no
fan-out. Same for `tags[].field=="OPCODE"`. Do NOT fan out to jobs/operations in
this pass; a 90-day store pull is ~6,400 ROs and fanning out would 429 you.

```python
# window on creationTime BTW [lo,hi] as epoch-ms STRINGS, pageSize 50,
# chain plain meta.nextPageToken (creationTime pagination works;
# closedTime pagination is the broken one that needs bisection)
depts = collections.Counter(
    ((r.get("assignee") or {}).get("department") or {}).get("id") for r in ros)
# resolve: GET /departments/{id} -> data.name
```

Script: `/home/itadmin/tekion-reports/bc_ucd_dept_probe.py` (parameterize the dealer
key + window). Saves the whole RO index to
`data/<store>-<dept>-90d-index.json` so every later pass is offline and free.

**BC (1251) census, 90 days to 2026-08-26 — 6,393 ROs:**

| Dept id | Name | ROs |
|---|---|---|
| `1251_department_d` | Service | 5,303 |
| `640635e2ae4407005a2d8e6d` | PDI | 621 |
| **`640635f59130d8571b87b87d`** | **UCD** | **426** (391 CLOSED) |
| `628efbdc005c8e000745e588` | Express Service | 43 |

⚠️ Filter to `status == "CLOSED"` for a "closed ROs" report — UCD's 426 included
22 TECH_ASSIGNED / 12 IN_PROGRESS / 1 HOLD.

## Step 2 — Opcode frequency, dept vs rest-of-store (the classification pass)

Still offline, still zero API calls. **This comparison is the whole value of the
report** — count each opcode inside the department AND everywhere else:

```python
def tags(r): return {t["value"] for t in (r.get("tags") or []) if t.get("field")=="OPCODE"}
in_dept  = [r for r in ros if dept_of(r)==TARGET and r["status"]=="CLOSED"]
out_dept = [r for r in ros if dept_of(r)!=TARGET]
u = Counter(); o = Counter()
for r in in_dept:  [u.update([t]) for t in tags(r)]
for r in out_dept: [o.update([t]) for t in tags(r)]
# EXCLUSIVE if o[opcode]==0
```

Use `set(tags)` per RO so an opcode used twice on one RO counts once — you're
measuring RO penetration, not line count.

## Step 3 — Cross-reference each opcode's Service Type (browser, :9223)

This is the step that turns a list into an answer. Internal endpoints, 15-header
bundle (see `tekion-opcode-api`):

```
GET  /api/service-module/u/opcode/serviceTypes        -> id -> name map
POST /api/service-module/u/opcode/search              -> per-opcode hit
     body {pageInfo:{start:0,rows:50}, searchText:"<OPCODE>",
           sort:[{order:"DESC",field:"createdTime"}], filters:[],
           nextPageToken:null, searchFields:["OPCODE"]}
```
Search is prefix/fuzzy — always `hits.find(x => x.opcode === code)` for exact match.
Per hit grab: `serviceTypeIds[]`, `status`, `opcodeType`, `category`,
`priceDetails[]` (find `payType==='INTERNAL'` → `laborRateType` + `flatPrice` /
`pricePerHour`), `parts[]`.

**Internal-pay pricing is the bonus finding Joe cares about.** `laborRateType` values
seen: `FLAT` (with `flatPrice`), `CUSTOM` (with `pricePerHour`), `DYNAMIC` (SCP guide),
or **`None` = no internal price configured at all** — flag those, they're usually why
a department's cost picture looks wrong.

Working script: `/tmp/ocaudit.js` pattern — loop codes with 250ms pacing, stash in
`window.__oc`, then pull in ≤14,000-char slices (the `/eval` response truncates
around 20K).

## Step 4 — Report shape

Table of: opcode · dept count · elsewhere count · EXCLUSIVE/SHARED · Service Type ·
internal price. Then the three conclusions:

1. **Already covered** — opcodes tagged to the dept's Service Type. One GL mapping
   row (`Internal Pay | <Service Type> | <acct>`) captures all of them.
2. **The leak** — dept work running on opcodes tagged to OTHER service types.
   Quantify it (instances over the window).
3. **Why you can't just retag** — for each leaking opcode, the elsewhere-count IS
   the collateral damage. Retagging `ALIGN` (61 in UCD, 42 elsewhere) reroutes 42
   non-UCD alignments too. Offer: **clone** (UC-prefixed duplicates tagged to the
   dept's Service Type, requires writer behavior change) **vs leave** (accept
   shared opcodes hit the standard internal account).

Ignore the junk buckets: `REC` (recommendation placeholder) and `MISC` run
store-wide in the hundreds/thousands and mean nothing for this analysis.

### Verified BC UCD result (90d to 2026-08-26, 391 closed ROs, 27 distinct opcodes)

BC already has Service Type **"Used Car Department"** = `62e806c31e9d980006b3e8ef`.
Tagged to it (6): `UCDETAIL` 328 · `UCSAFETY` 294 · `UCSMOG` 193 · `UCEV` 35 ·
`UCFRONTLINE` 32 · `CERTSAFETY` 22.

Leaking through other service types (21), the notable ones:
`ALIGN` 61/42 elsewhere · `4ALIGN` 31/27 · `TIRE4` 19/14 · `TIRE2` 15/6 ·
`TIRE1` 6/21 · `FBRAKE` 11/33 · `RBRAKE` 8/15 · `AGMBATTERY` 10/20 · `BELT` 9/12 ·
`BALANCE` 7/6 · `CABIN` 1/220 · `LOF6` 1/924 (all XPRESS SERVICE / Main Service /
Maintenance Service / Cadillac Express Shop).
Only 4 opcodes were truly EXCLUSIVE to UCD: `UCFRONTLINE`, `CADTIRE2`, `CADTIRE3`,
`TEK05053107`.

No internal price set at all on: `UCDETAIL`, `CERTSAFETY`, `REC`, `BELT`, `BALANCE`,
`MISC`, `CADTIRE1-4`, `RECALL`, `TEK05040101`, `TEK05053107`.

## Step 5 (optional) — dollar weighting via fan-out

Only if Joe wants dollars per opcode. Fan out ONLY the department's closed ROs
(391, not 6,393) → `/repair-orders/{rid}/jobs` → `/jobs/{jid}/operations`, read
`labor.saleAmount`/`costAmount` (**CENTS — /100**) and `jb["payType"]`. Run as a
**background** process with a JSON checkpoint every 20 ROs (`nohup ... &`,
`notify_on_complete=true`) — ~800 nested calls exceeds the 300s foreground limit.
Script: `/home/itadmin/tekion-reports/bc_ucd_ops_scan.py` (resumes from
`data/bc-ucd-ops-ckpt.json`).

## Pitfalls

- **Don't fan out the whole store.** Tags-first prefiltering is the difference
  between 130 API calls and 25,000.
- **A department id list from one time-window sample is incomplete** — enumerate the
  full window before concluding a store has only N departments.
- The `assignee.department` census is per-RO, not per-job. A Service-dept RO with one
  UCD line won't show up. Acceptable for this report; say so if the numbers get
  challenged.
- `/eval` needs `{"js": ...}` (NOT `expression`) and `awaitPromise:true` for the async
  IIFE. Big results must be sliced out in ≤14K chunks.
- Don't answer "here's your opcode list" and stop. Joe's real question is *will my GL
  change capture this work* — the SHARED column is the answer to that.
