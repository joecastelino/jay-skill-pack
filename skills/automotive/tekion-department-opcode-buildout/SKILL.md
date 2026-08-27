---
name: tekion-department-opcode-buildout
description: Derive the complete opcode list a Tekion department (UCD/Used Car, PDI, Express, Body Shop) actually uses over a period, split it into already-correctly-tagged vs shared-with-other-departments, and produce a build sheet of new department-scoped opcodes so ONE Service-Type GL mapping row captures all of that department's internal spend.
triggers:
  - what opcodes do I need to build for UCD
  - department opcode list
  - route a department to its own GL account
  - used car department opcodes
---

# Tekion — Department Opcode Buildout (route a department to its own internal GL account)

**Use when:** a store wants a department (UCD/used-car recon, PDI, Express, Body Shop)
to post internal labor/parts to its OWN GL account, and asks "what opcodes would I
need to build?"

**The key structural fact (BC verified 2026-08-26):** the Service-Internal GL mapping
table routes by **Pay Type × Service Type**, NOT by department and NOT by cost center.
Cost-center records carry no GL account (Edit AND Add dialogs = Cost Center Name /
Enable Control / Enable Control 2 only). Department records carry no GL account either
(Code / Label / Department Type / Set as Default). So the ONLY lever is:

> tag every opcode the department uses to a dedicated **Service Type**, then add ONE
> mapping row `Internal Pay | <that Service Type> | <new GL account>`.

Everything downstream of this skill exists to figure out *which* opcodes need that tag.

---

## Step 1 — Find the department id and its RO volume (OpenAPI, free)

`assignee.department.id` is free on every `repair-orders:search` result — no fan-out.

```python
import sys, json, time, urllib.request, datetime, collections
sys.path.insert(0,"/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg=load_config(); tok=get_token(cfg)
BASE=cfg["base_url"]+"/openapi/v4.0.0"; DEALER=cfg["dealers"]["bc"]
# paginate creationTime BTW [90d ago, now], pageSize 50, chain meta.nextPageToken
# then: collections.Counter(((r.get("assignee") or {}).get("department") or {}).get("id"))
# resolve names via GET /departments/{id}
```
Working script: `~/tekion-reports/bc_ucd_dept_probe.py` (writes
`data/<store>-ucd-90d-index.json` with the full RO index — reuse it, don't re-search).

⚠️ Use `creationTime BTW` pagination (plain `paginationToken` chaining works).
Do NOT use `closedTime` filters — those hit the pagination bug requiring bisection.

**BC (1251) department census, 90d:** Service 5,303 · PDI 621 · **UCD 426** · Express 43.

## Step 2 — Get the opcode list FREE from tags (no fan-out)

OPCODE tags are on the search result. Filter to the department + `status == CLOSED`:
```python
def tags(r): return set(t["value"] for t in (r.get("tags") or []) if t.get("field")=="OPCODE")
```
Count each opcode's usage **inside** the department vs **outside** it. The
outside count is the whole game — see Step 4.

## Step 3 — Read each opcode's service type + internal price (internal API, zero quota)

Via the authenticated `:9223` browser, POST `/api/service-module/u/opcode/search`
with `searchFields:["OPCODE"]`, exact-match the hit, and read:
- `serviceTypeIds[]` → map via `GET /api/service-module/u/opcode/serviceTypes`
- `priceDetails[]` → find `payType=="INTERNAL"`: `laborRateType` (FLAT/DYNAMIC/CUSTOM),
  `flatPrice`, `pricePerHour` — **DOLLARS here, not cents** (internal API differs from OpenAPI)
- `laborTimeInSeconds/3600`, `parts[]`

Template: `/tmp/ocaudit.js` pattern in skill `tekion-opcode-api` (15-header bundle).
Stash into `window.__oc`, pull back in ≤14,000-char slices (eval truncates ~20K).

**BC service types (dealer 1251):** Sublet, Service Contract, PDI, Main Service,
Maintenance Service, Service Interval Menu, XPRESS SERVICE, ACCESSORIES, MPVI,
**Used Car Department `62e806c31e9d980006b3e8ef`**, Service Catalog, Service Menu,
Cadillac Express Shop.

## Step 4 — The three-bucket split (this is the deliverable)

- **Bucket A — already tagged to the department's service type.** No action. At BC,
  6 opcodes (UCDETAIL/UCSAFETY/UCSMOG/UCEV/UCFRONTLINE/CERTSAFETY) = 73.6% of $.
- **Bucket B — SHARED opcodes.** Used by the department AND elsewhere (e.g. `ALIGN`
  61× in UCD, 42× in Service). **You CANNOT retag these** — retagging would reroute
  the other department's work too. The only fix is to **CLONE** them with a
  department prefix (`ALIGN`→`UCALIGN`) tagged to the department service type, and
  tell that department's writers to use the clones.
- **Bucket C — catch-all placeholder opcodes.** Look for a bare generic op with ONE
  description across hundreds of lines. At BC, `REC` ("RECOMMENDATION") was 257 lines /
  $42,849 / 17.8% of UCD spend with zero categorization. **Always call this out — it's
  usually a bigger finding than the GL question they asked about.** Replace with 6–8
  real categorized opcodes (RECON/DIAG/ELEC/ENGINE/SUSP/AC/GLASS/SUBLET).

## Step 5 — Dollar-weight it (fan-out, background job)

Tag counts alone mislead — 1 line of a $328 op ≠ 328 lines of a $103 op. Fan out
`/repair-orders/{rid}/jobs` → `/jobs/{jid}/operations` on the department's CLOSED ROs
only, capture `opcode`, job `payType`, `labor.saleAmount`/`costAmount` (**CENTS** here —
public OpenAPI — divide by 100).

391 ROs ≈ 12 min. Run as `nohup ... &` background with `notify_on_complete`, checkpoint
every 20 ROs to JSON so it resumes. Script: `~/tekion-reports/bc_ucd_ops_scan.py`.

Then report per-opcode: lines, unique ROs, labor $, cost $, service type, and the
**tagged vs untagged dollar split** — that number ("$177,356 would route, $63,752
would miss") is what makes the decision for them.

## Step 6 — Build sheet + the ONE mapping row

Output a plain-text build sheet: Section A (already tagged), Section B (clones with
clone-from / labor hours / internal price copied from the source opcode), Section C
(catch-all replacements), then coverage math. Template output:
`~/tekion-reports/data/BC-UCD-opcode-build-sheet.txt`.

Final config step (in-house, no Tekion ticket):
```
Accounting > G/L Account Transaction Mapping > Fixed Operations > Services
  > "Service - Internal" > edit pencil > add row:
     Internal Pay | <Department Service Type> | <new GL account>
Parts is a SEPARATE table:
  Part & Accessories > "PARTS - REPAIR ORDER" > add the parallel row
```

---

## Step 4b — ALWAYS search for existing department-prefixed opcodes first

Before proposing a clone list, sweep the opcode catalog for opcodes that already
carry the department prefix (`searchText:"UC"` / `"UCD"`, `searchFields:["OPCODE"]`,
paginate the cursor). Stores build these ad-hoc and then stop using them.

At BC, `UCRECALL` ("USED CAR DEPARTMENT-INSPECT FOR ANY OPEN RECALLS") already
existed tagged to Used Car Department — but was used **zero** times in 90 days.
Proposing to "build" it would have been wrong; the real finding is that writers
aren't using an opcode that already exists.

**⚠️ DEALER DRIFT ON :9223 — verify before every catalog search.** The persistent
browser's `currentActiveDealerId` changes between turns (cron jobs, other sessions).
A `UC*` sweep run while the browser sat on TL (1092) returned TL's UCD family
(UCDAIR/UCDDETAIL/UCDKEY/UCDOIL/UCDRECALL/UCDSMOG/UCDWIPERS) — a completely
different store's opcodes, with a different Used Car Department service-type id
(`61f45b8e…` at TL vs `62e806c3…` at BC). Either assert the dealer id first, or
**hard-code `dealerId` + `tek-siteId: -1_<dealer>` in the header bundle** rather
than reading them from localStorage:
```js
"dealerId":"1251", "tek-siteId":"-1_1251"   // don't trust localStorage
```
Cross-store peeking IS useful once you know you're doing it — TL's combined
`UCDAIR` (cabin + engine air filter, one opcode) is a better pattern than two
separate ops, and worth offering as an alternative.

## Step 6b — DERIVE the department's skill convention; never copy the source opcode's

When cloning a shared opcode (Bucket B), the instinct is to carry over the source's
**Skill** so auto-dispatch still routes to the right tech group (`ALIGN` → `alignment`).
**That is usually wrong.** Joe's ruling at BC, emphatically: *"EVERYTHING SHOULD GO TO
UCD SKILL."* Departments dispatch as a unit; the department's own techs pick up all its
work regardless of work type.

**There is often NO skill literally named after the department.** BC's 39-skill list has
`tech/generic`, `alignment`, `4 wheel alignment`, `used car inspection`, `new car
department`, `PDI`, `Xpress Lube` … and **no "UCD"**. Don't go looking for one and don't
create one — instead **derive the convention empirically from the ops already tagged to
the department's service type**:

```
for op in existing_department_opcodes:
    read skillId  →  map via the /opcode/skills response
```
BC UCD result: UCSAFETY / UCDETAIL / UCEV / UCFRONTLINE / UCRECALL = `tech/generic`
(id `625505ea77490b000771f95a`); UCSMOG = `smog` (lone exception). Majority wins →
`tech/generic` IS the de-facto UCD skill. Set it on every clone.

Do this BEFORE building opcode #1 — I set `alignment` on UCALIGN, shipped it, and had to
go back and Update it. Ask/derive the skill convention in the same breath as pay type and
cost center.

**Also worth reporting when you audit the existing set** (both surfaced at BC and both
were news to Joe):
- an op whose skill breaks the pattern (UCSMOG on `smog` — may be intentional if there's
  a dedicated smog tech; ask, don't "fix")
- an op whose **pay type isn't INTERNAL** (UCRECALL = WARRANTY — correct for recall work,
  but it means that op will never hit the department's internal GL, so it's outside the
  scope of the mapping row you're building)

## Build them ONE AT A TIME with API read-back between each

Joe's explicit instruction, and it paid off immediately — the skill error was caught on
#1 instead of being replicated across 26 opcodes. Loop per opcode:
create → `pushState` remount → capture `GET /api/service-module/u/opcode/<CODE>/v2` →
show the committed field table → get confirmation → next. Never trust the post-save DOM;
see `tekion-opcode-create` for the XHR-hook read-back recipe and the list-page bounce
required between consecutive detail loads.

**If the XHR hook is unavailable, verify with a hard `navigate` to
`/ro/opcode/edit/<CODE>` and read the rendered form** (a bare in-page `fetch` to
`/api/service-module/u/opcode/search` returns HTTP 500 — the axios interceptor supplies
auth that a raw fetch can't). Fresh-load readback selectors:

| Read | Selector |
|---|---|
| opcode / display / description | `input[placeholder="Type Here"]` |
| all dropdown values in order | `[class*=singleValue], [class*=selection-item]` |
| labor rate prices | `input[placeholder="Enter price"]` |
| labor times | `input[placeholder="0"]` |

Expected `singleValue` sequence for a correct UCD op (BC): `Individual Service · Location ·
In · Maintenance · Used Car Department · tech/generic · I - Default internal pay ·
CP - Defau… · CP - Defau… · Fixed Price · Internal P… · Internal P… · Fixed Price · each ·
Used Car INV 240`. Row pay-type cells render **truncated** — match on prefix, never exact text.

### The verified per-opcode standard (BC 1251 UCD — pin this before building #1)

Fields split into **fixed** (same on every clone) and **inherited** (copied from the
source opcode, differs per clone). Getting that split wrong is the #1 rework cause.

**FIXED — identical on every clone:**

| Field | Value |
|---|---|
| Opcode Type | Individual Service *(form default)* |
| Service Type | **Used Car Department** (`62e806c31e9d980006b3e8ef`) |
| Skill | **tech/generic** (`625505ea77490b000771f95a`) — *form default, verify only* |
| Default Pay Type | `I - Default internal pay` — **form defaults to CP, must be changed** |
| Internal Default Cost Center | **Used Car INV 240** (`6286a14ce21b8400071cad0f`) @ 100%, override ON — **add it even when the source opcode has blank cost centers** (the brake and tire sources both did) |

**INHERITED — read off the source opcode's live record, per clone:**

| Field | Notes |
|---|---|
| Category | **The work type, NOT "Maintenance".** Brakes→`Brakes`, TIRE4→`Tire`. Category drives GLAM account mapping; **Service Type** is what carries the UCD routing, so Category is free to stay truthful to the work. |
| Labor hours (billed/actual) | e.g. brakes 2.00/2.00, TIRE4 1.60/1.60 |
| Rate row(s) | Copy the source's shape exactly — see the Internal-only rule below |
| Standard Opcode Mapping | Copy the rows — **the opcode number varies by work type** |

#### Joe's two standing rulings (BC, 2026-08-26 — verbatim: *"1) I want it copied. 2) internal only."*)

1. **COPY the Standard Opcode Mapping rows onto the clone.** Even though a UCD internal
   opcode will never be submitted as a warranty claim, Joe wants the mapping carried over.
   At BC that's 3 rows: `gm|chevrolet`, `gm|cadillac`, `gm|gmc`.
   ⚠️ **The mapped opcode number is per-work-type — do NOT reuse the previous clone's.**
   FBRAKE/RBRAKE → `0300`; TIRE4 → `0400`. Read it off the source every single time.
2. **Internal-only rate rows.** If the source opcode has no Customer Pay row, the clone
   gets none either — ONE row, `Internal Pay / All / <rate type> / $`. This **supersedes**
   the older "Rate row 2 = CP" guidance; UCALIGN/UC4ALIGN got a CP row, UCFBRAKE/UCRBRAKE
   correctly did not. Match the source.
   Rate type also varies: brakes = `Hourly Price $150.00`, TIRE4 = `Fixed Price $120.00`.

### ⚠️ Sibling opcodes are NOT interchangeable — diff the source before every clone

The tempting shortcut after two identical builds is to reuse the last recipe. It breaks.
`TIRE4` vs `FBRAKE`, both plain BC internal ops, differed on **four** fields: mapping
opcode (0400 vs 0300), Category (Tire vs Brakes), rate type (Fixed vs Hourly), and source
Service Type (XPRESS SERVICE vs Maintenance). Always `navigate` to
`/ro/opcode/edit/<SOURCE>` and dump inputs + `singleValue`s + the rate grid + the cost
centers *before* opening `/ro/opcode/add`. The build sheet is an estimate; the live
record is truth.

Minor divergence to be aware of: source `4ALIGN`'s CP rate row uses the **parent**
`Customer Pay` node (ALL_CUSTOMER_PAY), while the clones use the **leaf**
`CP - Default customer pay`. Harmless and self-consistent across the new set, but pick one
convention deliberately and stay on it.

**When an inherited field is genuinely ambiguous, ask — don't guess.** Category was the
one field where the fixed/inherited split wasn't obvious from the first four builds; one
short question to Joe is far cheaper than 26 opcodes mapped to the wrong GLAM account.

### ⚠️ Verify `currentActiveDealerId` before EVERY write, not just at session start

`:9223` drifts between turns (cron jobs, other agents, other sessions). BC 1251 drifted to
TL 1092 repeatedly. Creating an opcode at the wrong store is a real, silent failure mode —
assert the id immediately before clicking `Create`, not just when you opened the form.

### ⚠️ Budget the wall-clock honestly

Opcode #1 and #2 each took far longer than expected and Joe asked *"why is it taking you so
long this time?"* — then, after a log audit, *"make the fixes so this inefficiency doesn't
reoccur."* Measured cause of the 40-min / 190-call UC4ALIGN build:

| Cause | Calls |
|---|---|
| Wrote a headless script mid-task, debugged 20 cycles, **abandoned it** | ~75 |
| Never loaded `tekion-opcode-create` (loaded 3 wrong skills instead) | — |
| Browser contention with the 15-min `cron-pipeline` | ~15 |
| Leftover GL/cost-center probing bleeding in from the prior question | ~16 |
| One `/eval` per field instead of one batched call per section | ~70 |

**The fix is now enforced, not just documented** — before opcode #1:
```bash
cd /home/itadmin/tekion-reports && \
  /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 opcode_preflight.py --dealer <ID>
```
and build through `jay_opcode.py` (`from jay_opcode import B`), batching one SECTION per
`execute_code` call. **Target: ~10 min / ~25 calls per opcode. Past 40 calls, stop and
re-read `tekion-opcode-create`'s MANDATORY PROTOCOL rather than pushing harder.**
Run `opcode_preflight.py --restore` the moment the last opcode commits.

#### If preflight HANGS — two known causes, both diagnosed by reading its log

Do not sit and re-run it. `opcode_preflight.py` legitimately blocks while waiting out an
in-flight cron run, so **launch it with `terminal(background=true)` and poll** — a
foreground/`execute_code` call will blow the 300s timeout and tell you nothing. Then read
the log:

1. **`WAIT pipeline running: <pid> /bin/sh -c pgrep -af cron-pipeline`** — this is
   `pgrep -f` **self-matching**: `subprocess.run()`'s own `/bin/sh -c` wrapper contains the
   pattern string, so the wait loop can never exit. **Fixed 2026-08-26** via the bracket
   trick — `PIPELINE_PAT = "[c]ron-pipeline"` used at both `pgrep` call sites while
   `PIPELINE` stays plain for display. If this regresses, that's the fix.
2. **The `:9223` session silently expired** and the browser is sitting on `/login` — the
   cron pipeline navigating to a parts page is enough to trigger the redirect. Preflight's
   dealer-id assert then spins. Confirm with a `/eval` read of `location.href`, then:
   ```bash
   HOME=/home/itadmin python3.11 /home/itadmin/tekion-auth/login.py --force   # background it
   ```
   and re-inject cookies + localStorage into `:9223` (expect ~5 cookies / ~21 keys /
   token len ~536), re-assert `currentActiveDealerId`, then re-run preflight.

⚠️ **`search_files` tool anomaly on this file:** pattern `pgrep|cron-pipeline` against
`opcode_preflight.py` returned `total_count: 0` despite both strings being present. Fall
back to `grep -n` via `terminal` when grepping this script.

## Pitfalls

- **Don't propose retagging a shared opcode.** It silently reroutes the other
  department's GL. Clone instead.
- **`RECALL` should never be cloned into an internal department set** — recall work is
  warranty-reimbursed.
- **Watch for $0.00 cost columns.** BC's `UCDETAIL` showed $34,020 sale / $0.00 cost on
  all 328 lines (100% gross) — either flat-rated with no tech cost or an outside vendor
  billed as labor. Flag it; it's a separate finding.
- **Watch for opcodes with NO internal price configured** (`priceDetails` has no
  INTERNAL entry) — those are being priced ad-hoc per RO. Set fixed rates when cloning.
- Internal `/api/service-module` prices are **dollars**; public OpenAPI RO amounts are
  **cents**. Mixing them produces 100× errors.
- Ask whether they want labor only or labor + parts — parts is a separate mapping table
  and a labor-side change does not move parts.
