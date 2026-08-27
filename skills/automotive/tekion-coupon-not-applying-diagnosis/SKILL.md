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

**A job can hold MULTIPLE operations — check the flag on ALL of them.** Don't stop at
the first/most-descriptive opcode. On TL RO 397670 the job held `CONCERN` ($0 labor)
and `REC` ($1,706.60 labor); `REC` was the blocker. Iterate every entry in
`roOperations` and note which ones actually carry `labor.saleAmount > 0`.

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

### ⚠️ TWO DATA MODELS COEXIST — read both or you will report a false negative

Tekion is migrating opcodes off legacy `priceDetails[]` onto a new
`laborRateConfigs[]` shape. **Saving an opcode in the current UI migrates it** — after
the save, `priceDetails` comes back **`[]` (empty)** and the real flag lives in
`laborRateConfigs[]`. So an audit that only reads `priceDetails` reports
`eligibleForPromotions: null` on a freshly-FIXED opcode and it looks *still broken*.
This bit me 2026-08-25: Joe had already checked the box on `CABIN` and `AIRFILTER`
minutes earlier and my first pass still called them false.

New shape (`GET /api/service-module/u/opcode/<CODE>/v2` → `data.laborRateConfigs[]`):
```js
const row = d.laborRateConfigs.find(x =>
  (x.parameters||[]).some(p => p.parameter==='SUB_PAY_TYPE'
                            && (p.values||[]).includes('ALL_CUSTOMER_PAY')));
const de  = row.values.find(f => f.field==='DISCOUNT_ELIGIBLE').value.enabled;  // <- flag
// siblings in values[]: LABOR_RATE {id,type,value}, ALLOW_OVERRIDE {enabled},
//                       TAX_CONFIG {taxConfigs:[{taxRegimeType,taxable}]}
```
Rule: **if `priceDetails.length === 0`, fall through to `laborRateConfigs`.**
`search` only ever returns `priceDetails`, so migrated opcodes must be fanned out to
`/v2` individually. Cheap: filter the search results to the `priceDetails`-empty ones
first (at TL that was 3 of 981 ACTIVE), then fan out only those.

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

## Step 4 — The fix (and how to batch it reliably)

`/ro/opcode/edit/<CODE>` → **Default** tab → Labor Rate Configuration → check
**Discount Eligible** on the row for the job's pay type → **Update**.
One checkbox. It is a live production pricing-config change and it is GLOBAL to that
opcode — **get Joe's explicit go before flipping it**, then verify by re-reading the
flag via the API (not by re-reading your own unsaved DOM).

### Working batch loop (15 opcodes at TL, 2026-08-25, 100% success)

Per opcode: `/navigate` → poll `document.body.innerText.length > 1200` → strip Pendo →
`scrollIntoView` the "Labor Rate Configuration" text node → locate row → `/mouse` the
checkbox → assert DOM `[override,discount] === [true,true]` → `/mouse` Update →
**poll the API until the flag reads `true`** (10 × 1.3s).

```js
// row + checkbox coords. Page renders DUPLICATE nested matches — take rows[rows.length-1]
// (innermost/real). Checkbox is cbs[1]; cbs[0] is Allow Override.
const rows=[...document.querySelectorAll('tr,[class*="row"]')].filter(r=>
  r.innerText && /Customer P/.test(r.innerText) &&
  r.querySelectorAll('input[type=checkbox]').length===2 && r.offsetParent!==null);
const r=rows[rows.length-1], cbs=[...r.querySelectorAll('input[type=checkbox]')];
const rc=cbs[1].getBoundingClientRect();   // -> /mouse {x:cx, y:cy}
```
Checkbox lands at x≈1062, Update button at x≈1211 — but **recompute per page**, the y
shifts with the Parts section height. `/mouse` on the raw `<input>` center works; no
label-click or synthetic event needed.

### CRITICAL: never trust the toast, verify by API

Toasts are unreliable here in BOTH directions:
- **False negative:** `BATT` and `BELT` returned no toast in my scraper → I logged
  `NO_TOAST` and the API confirmed still-`false`. But when I redid `BATT` manually the
  screenshot showed the success toast plainly — my selector just missed it (the toast
  container class varies, and it auto-dismisses in ~3s).
- Toasts also **stack and persist** across navigations, so a stale
  "Opcode 'X' updated successfully" from the previous opcode can make the *current*
  one look saved.

So the loop's success condition must be the API read, not the toast. Poll
`/v2` → `laborRateConfigs` → CUSTOMER_PAY → `DISCOUNT_ELIGIBLE.enabled === true`.
Save latency is 1–3s. Also re-check `modifiedTime` — a fresh epoch (today) is
corroboration that the write actually landed.

### Pitfall: `window.__helper` does NOT survive `/navigate`

I stashed the flag-reader as `window.__flag` once, then navigated per opcode — the
function was gone and every `/eval` threw **HTTP 500** (which reads like a server
error, not a wiped global). Inline the whole header-building + fetch IIFE into each
verification call, or re-install it after every navigation.

### Pitfall: DOM may already be true before you click

`BATT`/`BELT` showed `discount:false` in one pass and `ALREADY_TRUE` in the retry
(the earlier save had in fact landed). Always branch on the current DOM state and
return `ALREADY_TRUE` rather than clicking — clicking a true box **unchecks** it.
Cross-check `ALREADY_TRUE` against the API before reporting it as fixed.

Only the **Customer Pay** row needs flipping for a CP coupon. Leave Internal and
Warranty `false` — that's correct (you don't coupon a warranty claim). Confirmed
end state at TL: CP `true`, INT `false`, WAR `false` on all 15.

**Already remediated at TL/1092 (2026-08-25) — do NOT re-flag in a future audit:**
`CABIN` + `AIRFILTER` (Joe did these himself), plus the 15 Jay flipped:
`4ALIGN` `BALANCE` `WIPER` `BATT` `RBRAKE` `BELT` `ATFX` `BFX` `FUELINJ` `HVAC`
`DETAIL` `MAJORP` `MAJORV` `INTERV` `4X4SERVC`.
Plus **`REC`** — Joe flipped it himself 2026-08-27 09:06 (RO 397670 / coupon `MILI`).
Joe **deliberately deferred** `TIRE3` `TIRE4` `FLAT` `SMOG` out of the 19-item
revenue bucket — he trimmed the list I proposed. Don't flip them unprompted; offer
tires/value-packages as an explicit next batch.

**Baseline first, always.** Before flipping anything, re-read the current flag — on
this job two of the targets had already been fixed by Joe minutes earlier and I
reported them as broken. Diff the audit against this remediated list.

## Step 5 — The store-wide audit (do it, don't just offer it)

`eligibleForPromotions:false` is never a one-off. Full-store sweep, ~7s:

```js
// in :9223 /eval — paginate the search cursor, stash to window.__aud
let tok=null, all={};
while(true){
  const b={pageInfo:{start:0,rows:50},searchText:"",sort:[{order:"DESC",field:"createdTime"}],
           filters:[],nextPageToken:tok,searchFields:["OPCODE","DESCRIPTION"]};
  const j=await (await fetch(URL,{method:'POST',credentials:'include',headers:H,
                                  body:JSON.stringify(b)})).json();
  const d=j.data||{}, hits=d.hits||[];
  hits.forEach(h=>{const cp=(h.priceDetails||[]).find(p=>p.payType==='CUSTOMER_PAY');
    all[h.opcode]={s:h.status,t:h.opcodeType,npd:(h.priceDetails||[]).length,
                   promo:cp?cp.eligibleForPromotions:null};});
  tok=d.nextPageToken; if(!tok||!hits.length) break;
  await new Promise(r=>setTimeout(r,110));
}
```
`nextPageToken` is the ONLY working cursor (`pageInfo.start` does not advance).
Dedupe by `h.opcode`, not `h.id` — same opcode can surface twice.
Then split: `npd>0 && promo===false` = broken on legacy model;
`npd===0` = migrated, fan out to `/v2` (see Step 2).

**TL/1092 baseline 2026-08-25:** 1,710 opcodes total, 981 ACTIVE, **93 ACTIVE with
Customer Pay Discount Eligible OFF**. Group them for Joe by business impact, not
alphabetically — he only cares about the ones a coupon would realistically hit:

| Bucket | n | Examples |
|---|---|---|
| Revenue services (real coupon targets) | 19 | 4ALIGN, BALANCE, WIPER, TIRE3, TIRE4, FLAT, BATT, RBRAKE, BELT, ATFX, BFX, FUELINJ, HVAC, DETAIL, SMOG, MAJORP/V, INTERV, 4X4SERVC |
| Value packages | 23 | every `*KV` (10KV…120KV) |
| Prepaid maintenance | 23 | all `TAC*`, all `TSC*`, UVAC, BUY3 |
| Diag / inspection | 8 | ENGDIAG, MECDIAG, TRANSDIAG, HVACDIAG, BRAKEINSP, CHECK, ALIGN, TPS |
| Admin / internal (leave alone) | 20 | MISC, ~~REC~~ (**WRONG — see below**), RECALL, SUBLET, RENT*, PDI, QC, UVI, MPVI, DUE, LYFT, BODY, LOTD, PARTSHOLD, SAFECAT |

Diag/inspect and admin codes being false is arguably CORRECT (you don't discount a
recall or a sublet). Say so — don't hand Joe a 93-line "everything is broken" list.

### ⚠️ `REC` IS NOT AN ADMIN OPCODE — I got this wrong and it cost a second ticket

**TL RO 397670, 2026-08-27** (2005 Camry Solara, Carole Lee, $2,394.65): Joe tried to
apply coupon `MILI` ($100 off) and it refused. Root cause = **`REC` had Discount
Eligible OFF on Customer Pay** — the exact opcode I had bucketed as "admin/internal,
leave alone" in the 8/25 sweep two days earlier. Joe fixed it himself before I
finished. Coupon `MILI` was innocent (ACTIVE, no expiry, 10% capped at $100,
Labor & Parts, CP, opcode scope empty). After the flip: coupon attached,
`effectiveDiscount = 10000` cents = **$100**.

`REC` = "recommended services" — it is where advisors park sold/recommended work. It
carries **real customer-pay labor dollars on a huge share of ROs** (on 397670 it held
all $1,706.60 of the job's labor while the sibling `CONCERN` op was $0). Anything a
coupon could realistically touch, `REC` touches.

**Rules that follow from this:**
1. **Never bucket an opcode by its name or assumed purpose.** Classify by *evidence* —
   sum actual closed-RO Customer-Pay labor $ per opcode over the last 90 days and flag
   any discount-ineligible opcode carrying material CP labor. A name like REC / MISC /
   DUE tells you nothing about whether money flows through it.
2. **Check EVERY operation on the job, not just the headline opcode.** A job can hold
   several ops; the one blocking the coupon is whichever carries the labor, which is
   often not the first or the most descriptively-named one. Iterate all of
   `roOperations` and read the flag on each.
3. Re-run the evidence-based sweep at the other stores — the same trap almost certainly
   exists at SCT/BC/BT. Bring Joe the trimmed list before flipping anything (he trims).
There is no bulk toggle in the UI; each is `/ro/opcode/edit/<CODE>` → Default →
Discount Eligible → Update.

---

## Pitfalls hit this session

- **Joe edits Tekion in parallel while you work the same ticket.** He flipped
  `CABIN` and `AIRFILTER` himself minutes before I read them, and I reported them as
  still broken. Re-read current state immediately before declaring anything broken or
  before clicking. `lastModifiedBy` + `modifiedTime` on `/v2` tell you who beat you to it.
- **He trims the batch list you propose.** I offered 19 revenue opcodes; he came back
  with 15 (dropped `TIRE3` `TIRE4` `FLAT` `SMOG`). Execute exactly the trimmed list and
  offer the remainder as an explicit follow-up batch — don't "helpfully" include them.
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
- **Verify a fix by API, and check the right model.** After Joe (or you) checks the box,
  re-read `/v2` and look at `laborRateConfigs`, not `priceDetails` — the save migrates
  the record and `priceDetails` goes empty. `modifiedTime` (epoch ms) + `lastModifiedBy`
  on `/v2` confirm who touched it and when, which is how I proved Joe's own edit had
  landed 20 min before I looked.
- Internal `/api/rosearchservice/u/repairorder/search` 500s with hand-built headers
  (axios interceptor auth). Use the public OpenAPI for RO lookup (Step 1); only opcode
  endpoints replay cleanly from in-page `fetch`.
- OpenAPI tokens expire mid-session → sudden 401 on a call that worked minutes ago.
  Re-`get_token()` rather than assuming a scope problem.
