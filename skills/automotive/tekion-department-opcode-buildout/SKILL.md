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
