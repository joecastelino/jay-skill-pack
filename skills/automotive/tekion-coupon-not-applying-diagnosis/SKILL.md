---
name: tekion-coupon-not-applying-diagnosis
description: Diagnose "failed to apply coupon" / "the coupon won't attach to job N" on a Tekion repair order. The #1 root cause is NOT the coupon — it is the OPCODE's "Discount Eligible" checkbox being unchecked. Covers the full evidence-first triage, the API field mapping that proves it without clicking anything, and how to audit a whole store for un-couponable opcodes.
triggers:
  - failed to apply coupon
  - coupon won't apply
  - can't add coupon to job
  - coupon not working tekion
  - discount eligible
  - coupon error repair order
---

# Tekion — "Failed to apply coupon" diagnosis

Verified live 2026-08-25 on **TL RO 398530 job 7 (`CABIN`)**, coupon `LB10`.
Joe reported it; root cause found in ~15 min with zero guessing.

**Bottom line up front:** Tekion gates coupon eligibility at the **OPCODE** level,
not the coupon level (KB0026638). If a valid, active, correctly-scoped coupon
refuses to attach, check the opcode's **Discount Eligible** checkbox FIRST — it is
unchecked far more often than anything is wrong with the coupon.

Companion skills: `tekion-coupon-management` (create/edit coupons),
`tekion-openapi-repair-orders` (RO lookup), `tekion-opcode-api` (opcode search API),
`persistent-browser-server` (:9223).

---

## Step 1 — Identify the RO and the job's opcode (API, no browser, ~5s)

Joe gives a bare RO number. **RO numbers are NOT unique across the 7 stores** — sweep
all dealers before assuming a store. RO 398530 existed at BOTH ST/876 (a CLOSED 2023
RO) and TL/1092 (the live IN_PROGRESS one). Disambiguate on `status` + `creationTime`.

```python
import sys, json, urllib.request
sys.path.insert(0,"/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg=load_config(); tok=get_token(cfg); BASE=cfg["base_url"]+"/openapi/v4.0.0"
def H(d): return {"Authorization":f"Bearer {tok}","app_id":cfg["app_id"],
                  "dealer_id":d,"Content-Type":"application/json"}
# sweep
for k,d in cfg["dealers"].items():
    out=post("/repair-orders:search", d,
      {"filters":[{"field":"documentNumber","operator":"IN","values":["398530"]}],"pageSize":5})
    ...
# then jobs -> operations gives the opcode for "job 7"
jobs = get(f"/repair-orders/{rid}/jobs")["data"]["jobs"]          # jobNumber is a STRING "7"
ops  = get(f"/repair-orders/{rid}/jobs/{jid}/operations")["data"]["roOperations"]
# -> {"opcode":"CABIN","opcodeDescription":"REPLACE CABIN AIR FILTER",
#     "labor":{"saleAmount":1295}}   # CENTS
```
`jobNumber` matches the numbered job list in the RO UI exactly, so "job 7" maps
directly. Also free here: `payType` (must be a pay type the coupon covers) and
`status`. Grab the customer/vehicle too (`/ro-vehicle`, `/ro-customers/{id}`) so the
report to Joe is concrete.

## Step 2 — Read the OPCODE's discount flag (API, still no clicking)

`POST /api/service-module/u/opcode/search` in the authenticated :9223 page returns
everything needed. **The field mapping is the unlock:**

| Opcode Management UI (Default → Labor Rate Configuration) | API field on `priceDetails[]` |
|---|---|
| **Discount Eligible** checkbox | **`eligibleForPromotions`** |
| Allow Override checkbox | `canOverride` |
| Labor Rate type (Flat / Labor Price Guide / Hourly) | `laborRateType` (`FLAT`/`DYNAMIC`/`CUSTOM`) |
| Hourly Price $ | `pricePerHour` (DOLLARS, internal API) |

There is one `priceDetails[]` entry per `payType` (CUSTOMER_PAY / WARRANTY / INTERNAL).
**Check the row matching the JOB's pay type.**

```js
// in :9223 /eval, awaited, stash to window.__y then read it back
const H={"Accept":"application/json, text/plain, */*","applicationId":"ARC_NA","clientId":"web",
"dealerId":localStorage.getItem('currentActiveDealerId'),"locale":"en_US",
"original-tenantid":"americanmotorscorporation","original-userid":localStorage.getItem('__user_id'),
"productIds":"ARC","program":"DEFAULT","roleId":localStorage.getItem('currentActiveRoleId'),
"subApplicationId":"US","tek-siteId":localStorage.getItem('currentActiveSiteId'),
"tekion-api-token":localStorage.getItem('t_token'),"tenantname":"americanmotorscorporation",
"userId":localStorage.getItem('__user_id'),"Content-Type":"application/json"};
const body={pageInfo:{start:0,rows:20},searchText:"CABIN",
  sort:[{order:"DESC",field:"createdTime"}],filters:[],nextPageToken:null,
  searchFields:["OPCODE"]};
const j=await (await fetch('https://app.tekioncloud.com/api/service-module/u/opcode/search',
  {method:'POST',credentials:'include',headers:H,body:JSON.stringify(body)})).json();
const h=(j.data.hits||[]).find(x=>x.opcode==='CABIN');   // search is PREFIX/fuzzy — exact-match!
const cp=h.priceDetails.find(p=>p.payType==='CUSTOMER_PAY');
cp.eligibleForPromotions   // false  <-- THE ROOT CAUSE
```

**Prove it by contrast, don't just assert it.** Loop a handful of the store's opcodes
and show Joe a table — a coupon that demonstrably works (TL `ROTATE` ← FREE ROTATION
coupon) will read `true`, the broken one reads `false`. TL 2026-08-25:
`ROTATE` ✅ true, `TEK09040104` ✅ true, **`CABIN` ❌ false**, `4ALIGN` ❌ false,
`WIPER` ❌ false. That contrast is what makes the diagnosis undeniable.

Optional visual confirmation: `/ro/opcode/edit/<CODE>` → scroll "Labor Rate
Configuration" into view → `/screenshot` + `vision_analyze` ("is Discount Eligible
checked on each pay-type row?"). The checkbox `ctx` text is empty in the DOM so
plain innerText scraping won't tell you which box is which — vision is faster.

## Step 3 — Clear the coupon itself (so you can rule it out)

Open the coupon and confirm it isn't the problem. `/core/coupons` lists all;
edit URL = `/core/coupons/edit/<base64(couponCode)>` (`LB10` → `TEIxMA==`).
Read with:

```js
(()=>{const i=[];document.querySelectorAll('input').forEach(e=>{if(e.offsetParent)i.push([e.id||e.placeholder,e.value])});
const s=[...document.querySelectorAll('.ant-switch')].map(x=>[x.parentElement.innerText.slice(0,55),x.className.includes('ant-switch-checked')]);
return JSON.stringify({i,s,txt:document.body.innerText.slice(document.body.innerText.indexOf('Edit Coupon'))});})()
```
Checklist (KB0026638): **Active?** · **date range covers today?** (blank Expiry = never
expires) · **Applied On** covers the right side (Labor / Parts / Labor & Parts) ·
**Pay Types** includes the job's pay type · **Include Services → Opcodes** either empty
(applies anywhere) or contains this opcode · usage limit not hit.
`LB10` passed all of these AND explicitly listed `CABIN` in Include Services → so the
coupon was innocent and the opcode was guilty.

## Step 4 — The fix

`/ro/opcode/edit/<CODE>` → **Default** tab → Labor Rate Configuration → check
**Discount Eligible** on the row for the job's pay type → **Update**.
One checkbox. It is a live production pricing-config change and it is GLOBAL to that
opcode — **get Joe's explicit go before flipping it**, then verify by re-reading
`eligibleForPromotions` via the API (not by re-reading your own unsaved DOM).

## Step 5 — Offer the store-wide audit

`eligibleForPromotions:false` is rarely a one-off. Offer to loop every ACTIVE opcode
at the store through the search endpoint (300ms pacing, ~50/page via
`pageInfo.rows` + `nextPageToken` cursor) and hand Joe the full list of opcodes that
can never take a coupon. At TL, `WIPER` (vs the `10OFFWIPER` coupon) and `4ALIGN`
were already broken the same way — flagging that proactively is the value-add.

---

## Pitfalls hit this session

- **Don't start in the browser.** The RO sweep + jobs/operations + opcode search all
  answer the question over API in seconds. The browser was only needed for the coupon
  read and the visual checkbox confirmation.
- **Opcode search is prefix/fuzzy** — always `hits.find(x=>x.opcode===CODE)`, never
  `hits[0]`. And it is case-sensitive.
- **`/eval` results truncate ~20K chars** — stash to `window.__x` inside the async IIFE
  and pull it back in a second `/eval` (slice if still large).
- **A Pendo "Tekion Learning Center" modal silently swallowed the dealer-pill click.**
  The pill `/mouse` returned success, but
  `[class*="root_dealerInfoItem_container"]` returned `n:0` twice — looks exactly like
  "wrong selector". It was an overlay. Fix:
  `document.querySelectorAll('[id*="pendo"],[class*="pendo"]').forEach(e=>e.remove())`
  then re-click the pill → 25 rows appear. Screenshot + vision_analyze is the fastest
  way to spot this (it showed the modal immediately). Note the modal's "Close" button
  is itself a `_pendo-button` — removing the nodes is quicker than clicking it.
- **Coupon department types matter**: the TL list mixes `Service` and `Parts` coupons.
  A Parts-department coupon will not attach to a service job.
- Public OpenAPI `/repair-orders/{rid}/ro-coupons` returns `{"data":{}}` with
  `meta.count:1` — useless for reading which coupons are on an RO. Don't chase it.
- `/repair-orders/{rid}/ro-customers` 404s; the customer link is
  `/ro-customers/{customerId}` (id comes from `primaryCustomer.id` on the search result).
