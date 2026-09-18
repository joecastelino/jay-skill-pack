---
name: tekion-verify-ro-actually-closed
description: Triage a forwarded ticket where a manager/advisor says an RO "shows closed but was never closed" (often a printed invoice hand-annotated with a note like "PREPAID PARTS"). Verifies server-side whether the closure is real, who closed it, and whether it was actually paid — before accepting or rejecting the complaint. Inverse of tekion-ro-close-blocked-triage.
triggers:
  - shows closed but never closed
  - shows closed but not closed
  - ticket shows closed
  - RO shows closed
  - was never closed
  - prepaid parts
  - closed but never closed
  - verify this RO is closed
  - who closed this RO
  - forwarded invoice screenshot
  - is this ticket really closed
---

# "Shows closed but never closed" — verify a closure's legitimacy

Distinct from `tekion-ro-close-blocked-triage` (which is about ROs that CANNOT close).
This is the inverse: the RO **is** closed, and someone is claiming it shouldn't be /
was never really finished.

⚠ **Incoming form is usually a phone screenshot of two printed RO invoices, hand-annotated.**
That means: (a) OCR is unreliable, and (b) **you do not know which store**. Do not reason
off the image — pull ground truth first. Verified 2026-09-18 (BC RO 100781 + 100590).

## Step 1 — Cross-store sweep for the RO# (never assume the store)

Every store has an RO 100781/100590. Hit the OpenAPI search per dealer and pick the row
with the recent `modifiedTime` + plausible status.

```python
sys.path.insert(0, "/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg = load_config(); tok = get_token(cfg)
BASE = cfg["base_url"] + "/openapi/v4.0.0"
# dealer_id header = cfg["dealers"][abbrev]  (ar/bc/bt/st/sv/tl/vc)
# POST /repair-orders:search {"filters":[{"field":"documentNumber","operator":"IN",
#   "values":[ro]}],"pageSize":5}   -> data.results; RO id only via it["jobs"]["link"]
```
The `tags` array in the search hit is free signal — it carries
`{'field':'JOB','value':'STATUS_CLOSED'}` / `STATUS_PARTIALLY_INVOICED`, `BASE_PAY_TYPE_*`,
opcodes, fees.

## Step 2 — The internal RO JSON is the whole answer (one call)

Browser :9223, headers per skill `tekion-internal-api-access`
(`tekion-api-token` = `localStorage.t_token`, **not** Bearer).

```
GET /api/service-module/u/ro/<roId>       -> {data:{jobs[],recommendations[],sublets[],ro{}}}
```
`ro` gives you everything needed to judge the closure:

| field | why it matters |
|---|---|
| `status`, `closedTime`, `modifiedTime` | is it actually closed, and when |
| `closedBy` | **who** closed it (resolve the name, Step 3) |
| `invoice` | per-payer `{amount, dueAmount, status, closedTime, closedBy}` + `invoicedByUserId`, `lastUpdatedByUserId` |
| `totals.customerPay/warrantyPay/internalPay` | dollars in **CENTS**; `postTaxTotal`, `partSaleAmount`, `laborSaleAmount`, `subletLaborSaleAmount`, `tax` |
| `customerInfo`, `vehicleInfo` | true customer/vehicle — use these, never the OCR |
| `allAdvisorIds`, `assignedTechDetails[].status` | advisor vs tech vs closer |
| `fees`, `transportType`, `source`, `type` | Lyft/sublet/walk-in context |

`GET /api/service-module/u/ro/<roId>/job/<jobId>` → `{payType, status, invoiceStatus,
operations[], operationGroups[], splitInfo, partStatus, concern}`.

**Matrix that makes the call:** `closedBy` vs `invoicedByUserId` vs `allAdvisorIds`.
- closer **is** the advisor/tech → normal close.
- closer is a **warranty clerk / service manager / admin**, weeks after check-in →
  the signature of a ticket **closed out administratively** rather than by whoever did
  the work. That is the finding the store is actually reaching for — say it explicitly.

## Step 3 — Resolve the closer's name (public OpenAPI, free)

```python
GET /openapi/v4.0.0/users/<uuid>   # works for UUIDs and numeric ids
# name = data.userNameDetails.completeNames[i].value  (a LIST of {nameType,value})
# role = data.userRoleDetails.primaryRole.persona     (e.g. WARRANTY_CLERK, SERVICE_MANAGER)
```

## Step 4 — Does the printed invoice match the server? (diff it)

Compare the screenshot's totals/lines against `ro.totals` + `ro.invoice`. In the verified
case both matched **to the cent** and every payer had `dueAmount: 0` → the RO was closed
AND settled, which flatly contradicts "never closed". Reporting that diff is the
deliverable when the complaint doesn't reproduce.

## Step 5 — "PREPAID PARTS" annotations: do NOT invent the meaning

`partsSaleAmount: 0` on a pure-labor RO (BC 100590 = $129.95 alignment) can still be
hand-marked "PREPAID PARTS" — so the annotation is **not** about parts on that RO. Two
readings, and they need different work:

1. **Parts-side** — a prepaid/special-order part tied to the RO is still open in the parts
   system (never receipted/delivered/closed out) while the RO shows closed.
2. **Work-side** — closed out administratively without the work/part being finished.

Per the never-guess rule: report the verified RO/invoice state, state both readings, and
ask **which screen they're looking at when they say it "shows closed"** (RO list vs a
parts prepaid/SOR list vs the WIP). Do NOT pick a root cause for a phrase you can't map.

## Endpoint inventory — what exists vs 404 (probed 2026-09-18, BC 1251)

**Works**
- `GET /api/service-module/u/ro/<roId>`
- `GET /api/service-module/u/ro/<roId>/job/<jobId>`
- OpenAPI `GET /repair-orders/{rid}/jobs` (data key **varies**: bare list OR `data.jobs` dict — always `d = r["data"]; rows = d["jobs"] if isinstance(d,dict) else d`)
- OpenAPI `GET /repair-orders/{rid}/jobs/{jid}/operations` → `data.roOperations`
- OpenAPI `GET /repair-orders/{rid}/ro-invoices` → `data.roInvoices` (amounts in cents)

**404 (don't waste calls)**
- OpenAPI `GET /repair-orders/{rid}/operations` — **RO-level path does NOT exist**; operations are only reachable per-job.
- `/api/service-module/u/ro/<rid>/parts`, `/job/<jid>/parts`, `/job/<jid>/part`, `/deposits`, `/payments`
- `/api/service-module/u/ro/<rid>/job/<jid>/operations/parts` → 500 `unexpected.error`
- Parts deposit/SOR/prepaid search paths all 404: `/api/wms/parts/u/{deposit,prepaid,specialOrderRequest,sor,partsOrder}/search`, `/api/partTrade/u/{deposit,special-order-request}/search`.
  ⇒ **There is no exposed prepaid-parts / deposit read API.** Reading a prepaid-part workflow means driving the PUA UI, not probing paths.

## Pitfalls

- **`vision_analyze` on the forwarded screenshot misread the VIN and the odometer**
  (real: 1GYS4HK98PR549808 / 26,100 mi; OCR: "1GYS4HKJ8..." / "75,909 Mi"). Pull
  customer + vehicle from `ro.vehicleInfo` / `ro.customerInfo` and never quote OCR digits.
- **:9223 dealer pill:** the container rows ALL report the same `y` (hidden template dupes).
  Enumerate **leaf** elements (`e.children.length===0`) and filter to the rendered band
  (`x>900, y in 40..700`) to get the real row coords before `/mouse`-ing. Verify
  `localStorage.currentActiveDealerId` flipped afterward — the pill click is the only
  reliable switch.
- **`/eval` 500s or SyntaxErrors are usually your own JS.** One unbalanced brace in an
  `async` IIFE returned `SyntaxError: Unexpected token ')'`. Write the payload with
  `json.dumps({"js": ...})` from Python so it's escaped correctly, and prefer plain ES5
  constructs inside.
- Store the fetched `ro`/job JSON to **`/home/itadmin/tekion-reports/`** if you need it
  later — `~/` under Jay's profile is wiped on the daily reset.
