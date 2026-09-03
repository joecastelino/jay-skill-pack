---
name: tekion-parts-so-gl-account-routing
description: Diagnose "this parts Sales Order / counter sale is hitting the WRONG GL account" (e.g. a Wholesale SO posting to a retail parts sales account). Covers the GLAM Fixed Operations > Part & Accessories > Parts-Counter mapping table, its 6 keying dimensions, the customer.taxable snapshot-vs-master trap, the 2026-08-19 store-wide NO-TAX code rollout that flipped every wholesale order to taxable, date-window bisection (search pagination is silently ignored), and the internal API endpoints to pull a full SO for evidence. Use for any "why did SO X go to retail instead of wholesale" or "where did the taxable status change" question.
triggers:
  - sales order hitting retail sales
  - so going to wrong gl account
  - counter sale posting to retail
  - wholesale so posted retail
  - parts sales order gl mapping
  - why did this sales order go to
  - parts-counter mapping
  - compare two sales orders gl
  - where did the taxable status change
  - customer taxable flipped
  - wholesale customers showing taxable
---

# Tekion — Which GL Account a Parts Sales Order Posts To

Joe's question shape: *"CAN YOU LOOK AT SALES ORDER 331990-1? I THINK ITS HITTING RETAIL SALES."*
Often followed by: *"I can give you two examples — 331990-1 went to retail, 323623-2 went to wholesale, why?"*

**Two examples is a gift — it turns this into a diff, not a theory.** Pull both,
enumerate every mapping dimension, and find the ONE that differs. Do not theorize
from the mapping table alone.

> This is the **counter-sale / Sales Order** sibling of `tekion-internal-cost-center-gl-routing`
> (which covers internal REPAIR ORDER cost centers). Different GLAM table, different dimensions.

## The mapping table: GLAM → Fixed Operations → Part & Accessories → **Parts-Counter**

Nav (`:9225`, verified SCT 876 2026-09-01):
```
/accounting/glaccountmapping/list
  left-nav "Fixed Operations"        (click by exact innerText)
  left-nav "Part & Accessories (6)"  (INCLUDE the count suffix in the match)
  main-panel accordion "Parts-Counter"  → expands read-only rows
```
Sub-tables under Part & Accessories at SCT: `Parts-Customer Pay`, `Parts-Toyota Care`,
`Parts-Internal`, `Parts-Warranty`, `Online Parts Payments`, **`Parts-Counter`**.
A Sales Order (counter sale) resolves through **Parts-Counter**. Parts on an RO go
through Parts-Customer Pay / Parts-Warranty / Parts-Internal instead.

**6 keying dimensions:** `Service Type · Source Code · Customer Tax Status · Sale Type (Fixed Ops) · Sales Subtype · Department → GL Account`

SCT 876 Parts-Counter rows (verified 2026-09-01):
```
All | All            | Taxable     | Retail    | ONLINE RETAIL    | 06 - Online Parts Sales | 4748 SLS- TOY PARTS ONLINE RETAIL
All | All            | Non-taxable | Wholesale | ONLINE WHOLESALE | 06 - Online Parts Sales | 4731 SLS- TOY PARTS WHLSALE-ONLINE
All | 333 - TIRES    | All         | Retail    | All | All        | 4725 SLS PRT RO CUST PAY TIRES-TOY
All | 990 - GOG      | All         | Retail    | All | All        | 4774 SLS GAS, OIL, GREASE
All | All            | Non-taxable | Retail    | All | All        | 4750 SLS PRT WHOLESALE MECH-TOY
All | All            | Taxable     | Retail    | All | All        | 4740 SLS PRT COUNTER RTL-TOY
All | 333 - TIRES    | All         | Wholesale | All | All        | 4725 SLS PRT RO CUST PAY TIRES-TOY
All | 990 - GOG      | All         | Wholesale | All | All        | 4774 SLS GAS, OIL, GREASE
All | All            | Non-taxable | Wholesale | All | All        | 4750 SLS PRT WHOLESALE MECH-TOY   <-- wholesale
All | All            | Taxable     | Wholesale | All | All        | 4740 SLS PRT COUNTER RTL-TOY      <-- RETAIL!
All | 333 - TIRES    | All         | Internal  | All | All        | 4734 SLS-TOY PARTS INTERNAL TIRES
All | 50 - SIGHTLINE | All         | Internal  | All | All        | 4785 SLS - PARTS ACCESSORY INTERNAL
All | 990 - GOG      | All         | Internal  | All | All        | 4774 SLS GAS, OIL, GREASE
All | All            | All         | Internal  | All | 05 - P&A   | 4730 SLS PRT RO INTERNAL RTL-TOY
```

## ⭐ WHICH ROW MATCHES: **Customer Tax Status is the tie-breaker**

`All / All / **Taxable** / Wholesale / All / All → 4740 SLS PRT COUNTER **RTL**-TOY`

**A Wholesale sale evaluated as Taxable maps to the RETAIL counter account.** That row
exists and duplicates the Retail/Taxable destination. Sale Type = Wholesale is NOT
sufficient to land in 4750. That part is solid.

### 🛑 RETRACTED 2026-09-01 — `customer.taxable` is NOT the customer master flag

**I reported "De Laveaga's master record is flagged Taxable" and had to retract it to
Joe in the same session. Do not repeat this.**

`data.salesOrder.customer.taxable` on the SO payload is a **per-order snapshot stamped
at order creation** — it is NOT the customer master record. Reading it and calling it
"the master" is a confident wrong answer.

**The actual master lives at:**
```
GET /api/cms/u/customers/<customerId>
  → data.taxInformation.partsTaxInfo[0].taxExempted     <-- the one that governs parts
  → data.taxInformation.serviceTaxInfo[0].taxExempted
  → data.taxInformation.salesTaxInfo[0].taxExempted
     (+ .reasonForTaxExemption, .taxExemptNumber, .taxPercentage, .overrideTaxPercentage)
GET /api/cms/u/tax-code-setup/<customerId>              <-- exempt tax-code grid
```
UI: **Customer Management → open customer → left-nav "Tax Exemptions" → Parts sub-tab.**

**What the masters actually said (both SCT customers, verified):**

| | De Laveaga 1243835 | Crash Champions n555 116053 |
|---|---|---|
| `partsTaxInfo.taxExempted` | **true** (resale, 101201554-10000) | **true** (resale, 209912384) |
| `serviceTaxInfo.taxExempted` | true | false (9.375%) |
| `salesTaxInfo.taxExempted` | false | false (9.375%) |

**BOTH are Parts tax-exempt — identical on the dimension that matters.** So the customer
master does NOT explain why one went retail and one went wholesale. The list-view columns
agree: both show `Parts Tax Exempted - Yes`.

### What actually differs (advanced 2026-09-02 — snapshot contradicts the lines)

The `taxable` value **snapshotted onto each order**, plus tax regime:

| | SO 331990 → retail | SO 323623 → wholesale |
|---|---|---|
| `customer.taxable` (order snapshot) | `true` | `false` |
| `taxRegime` | **`null`** | `SALES_TAX` |
| `taxConfiguration` | NO TAX on all 5 components, `taxExempt:false` | — |
| `taxSummary.totalTaxAmount` | `0.00` on $4,661.81 | — |

#### ⭐ THE KEY FINDING — header flag and LINE tax codes contradict each other

Joe's follow-up was *"K, so where did the taxable status change?"* The answer is
**it never changed — and the order disagrees with itself.**

Drill into `partSaleDetails[].taxCodeDetails[0]`:

| SO | header `customer.taxable` | line-level tax code | tax charged |
|---|---|---|---|
| 331990 De Laveaga | `true` | **all lines `NO TAX` @ `taxPercentage:"0"`**, `manualTaxCode:false` | $0 |
| 323623 Crash Champions | `false` | `taxable:true` but **no tax code resolved at all** | $0 |

So on 331990 the resale exemption **did** apply at the line level (NO TAX, 0%) while the
header simultaneously says taxable. **One order, two contradictory tax facts.**

This is the mechanism to present: `customer.taxable` is a generic per-order snapshot and
is **not** the parts-exemption resolution — the real exemption lives in the line tax code.
If GLAM keys Customer Tax Status off that stale header flag rather than the line codes, a
Wholesale order from a valid resale-cert customer matches
`Taxable / Wholesale → 4740 …COUNTER RTL…`. Zero tax charged, still booked retail.

**Still NOT proven:** which flag GLAM actually reads (header vs line code). Everything is
*consistent* with the header, but do not assert it. To close it, pull the posted GL/journal
lines for both SOs and see which account each actually hit (read-only). Say so plainly —
Joe accepts "I haven't nailed that yet"; he does not accept a confident wrong answer.

---

## 🚨 ROOT CAUSE FOUND 2026-09-02 — a store-wide tax-code rollout on 08/19, not a customer edit

Joe's follow-up was *"K, so where did the taxable status change?"* **Answer: it changed on
2026-08-20, store-wide, for every wholesale customer at once — and no customer record was
touched.** This supersedes the per-customer theorizing above. Check this FIRST.

**The evidence — bisect the SO history by `createdTime` and watch the snapshot flip:**

| Date | Wholesale SOs that day | `customer.taxable` |
|---|---|---|
| 08/19 and earlier | 70 | **`false`** (0 of 20 sampled true) |
| 08/20 onward | 157 | **`true`** (16 of 20 sampled true) |

Sharp to the hour, across **unrelated** customers with different masters and different certs:
```
Crash Champions  SO 331342 @ 08/19 16:42 = false  →  SO 331482 @ 08/20 13:35 = TRUE
De Laveaga       SO 331239 @ 08/19 11:26 = false  →  SO 331531 @ 08/20 15:23 = TRUE
```
De Laveaga's master was last modified **2025-10-30** — ten months before. Nobody edited it.

**The trigger — a new tax code went effective the night of 8/19:**
```
taxCode "NO TAX"  id 6a867038a5537a692d78fdf0
effectiveDate = 2026-08-19 20:10   ← ~17h before the first flipped order
taxRate = 0, taxCategory = SALES_TAX, codeType = SUB
```

**The structural tell — `taxConfiguration` exists only on post-change orders:**

| | SO 331990 (08/24, post) | SO 323623 (07/06, pre) |
|---|---|---|
| `taxConfiguration` | populated, `taxExempt:false`, all 5 components → `NO TAX` | **`null`** |
| `taxDetails` | `[]` | `[{taxRegimeType:SALES_TAX, taxPercentage:"10", taxable:false}]` |
| line `taxCodeDetails[0]` | `NO TAX` @ 0% | none resolved |

**Mechanism:** the rollout changed *how exemption is represented*. It stopped stamping the
header exempt (`taxable=false`) and instead stamps **`taxable=true` then zeroes tax via a
`NO TAX` code at the line**. Customer impact is nil — **$0 tax either way, exemption still
honored**. But GLAM keys on Customer Tax Status, so every wholesale order since 08/20 now
matches `Taxable / Wholesale → 4740 …COUNTER RTL…`. That's **~150+ SOs/day** mis-posting to
retail, not one order.

**Lesson: when two unrelated customers exhibit the same anomaly, STOP diagnosing the
customers.** Bisect for a boundary date and look for a settings/tax-code change on that
date. A per-customer explanation cannot account for a synchronized flip.

⚠️ Still open at hand-off: both SOs report `postedToAccounting=false` and every line
`transactionPosted=false`, **including the CLOSED July one**. Either SOs post via a path the
record doesn't reflect, or there's a backlog. I could NOT confirm dollars actually sitting in
4740 (see the blocked GL paths below). Do not claim the ledger without that.

## 🚨 JOE'S CORRECTION 2026-09-03 — "we have wholesale customers that are taxable"

**This kills any GLAM edit as the fix.** The `Taxable/Wholesale → 4740` row is DELIBERATE
design: genuinely taxable wholesale customers (no resale cert) → 4740, exempt wholesale
→ 4750. Pre-8/19 the header flag genuinely distinguished the two populations. The 8/19
rollout destroyed that signal — since 8/20 EVERY wholesale order stamps `taxable=true`
(exemption lives only in line-level NO TAX codes), so GLAM can no longer tell a real
taxable wholesale customer from an exempt one.

**Consequences:**
- Do NOT propose collapsing to `All → 4750` or repointing the Taxable/Wholesale row —
  either direction misposts one of the two populations. There is NO GLAM change that
  fixes this if GLAM reads the header flag.
- The fix is a **Tekion defect ticket**: "8/19 tax-code release changed header taxable
  derivation for exempt customers; GL routing by Customer Tax Status broken since 8/20."
- The header flag is COMPUTED by Tekion's tax engine at SO creation from the customer
  master — it is an output, not a stored setting. There is nothing dealer-side to flip
  (Joe asked "can I just flip it myself?" — no; the inputs are all correct already).

**Ticket evidence pair (same customer, master untouched since 2025-10-30):**
- De Laveaga Service (cust 1243835): SO **331239** @ 08/19 11:26 AM `taxable=false` vs
  SO **331531** @ 08/20 3:23 PM `taxable=true`. Both Wholesale, both $0 tax.
- Backup, second customer: Crash Champions n555 (116053): SO **331342** (08/19 4:42 PM,
  false) vs SO **331482** (08/20 1:35 PM, true).
- Cite tax code "NO TAX" id `6a867038a5537a692d78fdf0`, effectiveDate 2026-08-19 8:10 PM —
  it's Tekion's own release artifact; hardest detail for support to deflect.

**JE reading (for Joe's "where do I see tax in journal entries"):** collected tax NEVER
touches 4xxx sales accounts — it credits a sales-tax-payable LIABILITY line. Exempt
wholesale orders have NO tax line at all, pre- or post-8/20; the only JE difference is
which sales account gets the credit (4750 vs 4740). You cannot find this defect by
looking for tax — look at the sales-credit account number.

**Note (unverified claim I made to Joe):** GLAM evaluates at POSTING time, not
order-creation — so a routing fix would also catch the unposted backlog. Verify before
repeating.

**Open follow-ups Joe may return to:**
1. Confirm dollars actually in 4740 (pull 4740/4750 transaction detail 8/20→now, look for
   known-exempt wholesale SO numbers). If exempt SOs sit in 4750 anyway → GLAM reads the
   customer MASTER, not the header → no defect, stand down.
2. Verify genuinely-taxable customers STILL get charged tax post-8/20 (a second bug here
   would be a real tax-collection failure — the expensive kind).
3. Fleet check: same 8/19 tax-code rollout likely hit the other 6 stores.
4. `postedToAccounting=false` on a CLOSED July SO — ask Tekion whether cosmetic or real.

---

#### Dating the change — SO snapshots beat `modifiedTime`

Build a merged timeline from customer-master `modifiedTime` vs SO `createdTime`/`modifiedTime`:

```
2025-10-30 10:25  De Laveaga master modified
2026-07-06 13:28  CC SO 323623 created
2026-07-20 14:09  CC master modified          <-- lands INSIDE 323623's open life
2026-08-24 11:36  SO 331990 created
2026-08-27 08:38  SO 331990 modified
2026-08-31 13:34  CC SO 323623 modified (closed)
```

**De Laveaga's master was last touched ten months BEFORE SO 331990 existed** — that alone
refutes "someone changed the customer." Use this negative result; it's the cleanest way to
exonerate the counter people. Both orders were `saleType=WHOLESALE` /
`saleSubTypeId=WHOLESALE`, so **nobody picked the wrong sale type** either.

Also surfaced: Crash Champions is **Parts-exempt but Service-NOT-exempt** (asymmetric).
Flag it as worth a look; don't call it a defect without asking.

Remaining unverified lead: **`/api/cms/u/tax-code-setup/<id>` differs materially** —
De Laveaga 9,356 bytes vs Crash Champions 3,026. Parse and diff if the JE check is
inconclusive.

Per Joe's NEVER-GUESS rule: present the leads and ask which to chase. Do not pick one and
assert it.

### 🚫 The customer Activity Log is NOT an audit trail — don't waste turns there

Customer → left-nav **Compliance → Activity Log** looks like the place to find "who changed
the tax flag." **It is GDPR-only.** Its Type filter is
`Request Raised By Customer, Data Exported, Data Deleted, Data Corrected, Data Selling & Sharing Stopped`
and it read **"Activity log is empty for this customer"** for both customers.

There is **no exposed per-field change history** for customer tax settings. `modifiedTime`
on the master is all you get. Tell Joe that directly rather than hunting for a log that
doesn't exist.

So the counter-intuitive summary: *"the order charged no tax but is treated as taxable
for GL routing, because routing reads the customer record."*

### Worked diff (the two orders Joe supplied)

| | SO 331990 (id 528289) | SO 323623 (id 519922) |
|---|---|---|
| Customer | 1243835 – De Laveaga Service | 116053 – Crash Champions (north 555) |
| saleType / saleSubTypeId | WHOLESALE / WHOLESALE | WHOLESALE / WHOLESALE |
| departmentName | 05 – PARTS & ACCESSORIES | 05 – PARTS & ACCESSORIES |
| price code | `698df942ab268c104c3d14ca` (37 \| list-37%) | `630e11f47d560d0007a8c2d3` |
| **customer.taxable** (order snapshot, NOT master) | **true** | **false** |
| **master `partsTaxInfo.taxExempted`** | **true** | **true** ← identical, explains nothing |
| → GL | **4740 RETAIL** | **4750 WHOLESALE** |

**Source code was ruled out conclusively, not by assumption:** source
`630e11860c76920008ed4417` appears on BOTH orders (2/2 lines on 323623, 14/54 on
331990) and produced different accounts. Neither order touched 333-TIRES or 990-GOG.
Sales Subtype was null on both (so the ONLINE RETAIL/ONLINE WHOLESALE rows never
applied). **Always find a shared value on a dimension to eliminate it — that's stronger
evidence than "these look the same."**

### Two separate defects — present BOTH, let Joe choose
1. **Customer master record** — check `partsTaxInfo[0].taxExempted` on both customers
   before claiming inconsistent setup. In the 331990/323623 case this candidate DIED:
   both were Parts-exempt. Only raise it if the masters actually differ.
2. **The mapping row itself** — `Taxable / Wholesale → 4740 …COUNTER RTL…`.
   ⚠️ SUPERSEDED 2026-09-03: Joe confirmed this row is DELIBERATE — SCT has genuinely
   taxable wholesale customers (no resale cert) that belong in 4740. Do NOT call the row
   a defect or propose editing it. See "JOE'S CORRECTION" section above.

Don't pick for him. He may want the customer fixed (one account) or the row fixed
(all taxable wholesale customers).

## 🔬 Pulling the customer master (do this BEFORE blaming customer setup)

The customer endpoints are **fetch()-based, not XHR** — the XHR hook alone MISSES them.
Install a `window.fetch` wrapper too:
```js
(function(){ if(window.__fcap) return 'already'; window.__fcap=[];
 var F=window.fetch;
 window.fetch=function(u,o){ try{window.__fcap.push({u:(u&&u.url)||u, o:o});}catch(e){}
   return F.apply(this,arguments); };
 return 'fhooked';})()
```
Navigate to `/core/customer/viewCustomer/<customerId>`, let it settle, then replay
in-page with a captured request's headers:
```js
(async function(){
  var c = window.__cap.filter(x=>x.u.indexOf('/api/cms/u/customers/')>-1)[0];
  window.__X = window.__X || {};
  for (var k in {dl:'2c95b9d9-...', cc:'50bad0fe-...'}) {}   // loop your ids
  var r = await fetch('/api/cms/u/customers/'+ID+'?reciprocalTrading=false&locale=en_US',
                      {headers:c.h, credentials:'include'});
  window.__X[key] = await r.text(); return r.status;
})()
```
Then read `window.__X[key]` back in ≤15,000-char slices and write to disk — **`window.__X`
and both hooks are destroyed by the next `/navigate`.** Save to a real dir under
`/home/itadmin/` (e.g. `/home/itadmin/so331990/`), never `~`.

Recursive scan pattern that caught my error — walk the whole customer JSON for
`tax|exempt` keys rather than reading the one field you expect:
```python
def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if re.search(r'tax|exempt', k, re.I) and not isinstance(v, (dict, list)):
                print(f"{p}.{k} = {v!r}")
            walk(v, f"{p}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, f"{p}[{i}]")
```

Other customer-module endpoints seen: `/api/cms/u/customers/<id>/vInfo`,
`/api/cms/u/customers/<id>/v1/notes`, `POST /api/cms/u/v2/customers/advancedsearch`,
`GET /api/cms/u/v2/customers/cnf/dealers`.

## Evidence collection — internal API (zero OpenAPI quota)

There is **no OpenAPI sales-order endpoint**. Browser/internal only. Work on `:9225`
(Jay's `:9223` is Joe's lane + the nightly `cron-tekion.sh` owns it).

### 1. Arm the XHR hook, load the SO list, capture real axios headers
```js
(function(){ if(window.__cap) return 'already'; window.__cap=[];
 var O=XMLHttpRequest.prototype.open,S=XMLHttpRequest.prototype.send,SR=XMLHttpRequest.prototype.setRequestHeader;
 XMLHttpRequest.prototype.open=function(m,u){this.__m=m;this.__u=u;this.__h={};return O.apply(this,arguments);};
 XMLHttpRequest.prototype.setRequestHeader=function(k,v){try{this.__h[k]=v;}catch(e){};return SR.apply(this,arguments);};
 XMLHttpRequest.prototype.send=function(b){var x=this;x.addEventListener('load',function(){
   try{window.__cap.push({u:x.__u,m:x.__m,h:x.__h,b:b,r:x.responseText.slice(0,400000)});}catch(e){}});
   return S.apply(this,arguments);};
 return 'hooked';})()
```
Then `/navigate` to `https://app.tekioncloud.com/parts/sales-order`.
⚠️ **Arm the hook AFTER the navigate settles, or re-arm** — a hook armed pre-navigate is
wiped by the full page load (`window.__cap` came back `[]` the first time).

### 2. Find the SO in the UI (facet search)
The SO list facet search input is `#downshift-0-input` (placeholder `Ctrl + Shift + L`,
`data-test-id=@tekion-parts-salesOrder-list-facetSearch-input`). **Plain `/type` works
here** — no native-value-setter dance needed.
```
/type {"selector":"#downshift-0-input","text":"331990"}
sleep 3
# dropdown offers: Customer | Part Number | Part Description | Sales Order | VIN | Customer Purchase No
# /mouse the "Sales Order" option (read its live rect; was ~601,424 at 1280 wide)
```
Then `/mouse` the SO number cell in the results row → lands on
`/parts/sales-order/details/<INTERNAL_ID>/so-details`. **Note the URL carries the
internal numeric id (528289), not the orderNo (331990)** — you need that id for the
API calls.

### 3. Replay the search API to bypass the list's default status filter
```js
(async function(){
  var c = window.__cap.filter(x=>x.u.indexOf('sale/order/search')>-1).pop();
  var b = JSON.parse(c.b);
  b.filters = b.filters.filter(f=>f.field!=='status');          // <-- CRITICAL
  b.searchTextFields=[{searchText:"323623",searchFields:["SO_ORDER_NO","SO_SANITIZED_ORDER_NO"]}];
  b.pageInfo={start:0,rows:10};
  var r = await fetch(c.u,{method:'POST',headers:c.h,body:JSON.stringify(b),credentials:'include'});
  var j = await r.json(); window.__r2 = JSON.stringify(j).slice(0,300000);
  return JSON.stringify({status:r.status, n:j.data.hits.length});
})()
```
Response shape: `data.{count,hits[],nextPageToken,…}`.

### 4. Pull the full SO
```js
// GET, replaying captured headers
'/api/partTrade/u/sale/order/v4/<id>'                    // salesOrder + salesOrderReturnList + salesOrderSummary
'/api/partTrade/u/sale/order/<id>/all/invoices'          // per-invoice (331990-1/-2/-3) w/ invoicedPartDetails
'/api/partTrade/u/sale/order/<id>/invoice/detail'
'/api/partTrade/u/sale/order/quick-filter/count?convertQtyToSaleUnit=true'
'/api/parts-picklist/u/picklist/refType/SALES_ORDER/refId/<id>'
```
Fields that matter for GL routing, all on `data.salesOrder`:
```
saleType, saleSubTypeId, departmentId/departmentName, siteId, paymentType,
status, paymentStatus, postedToAccounting, closedTime, currentInvoiceSeq,
customer.{taxable, priceCodeId, displayId, name},
taxConfiguration.{taxExempt, taxCodeGrid[]}, taxSummary.{totalTaxAmount,…},
partSaleDetails[].{sourceCodeId, partNumber, partType, partLineStatus, sellingPrice}
```
Read big `__cap[i].r` / `window.__X` values back in **≤15,000-char slices** (`/eval`
truncates around 20k) and reassemble.

## ⚡ FAST PATH — header harvest without the UI dance (verified 2026-09-02, `:9223`)

When Joe is waiting, skip the facet-search clicking entirely. Total ~10 calls:

1. **Switch dealer via the UI pill** (setting `localStorage` alone does NOT work).
   Click the store name pill at `~1145,32`, wait 4s, then enumerate rows:
   `document.querySelectorAll('[class*="dealerInfoItem"],[class*="dealerItem"]')`
   filtered `offsetParent!==null`. `/mouse` the leaf row (e.g. `Stevens Creek Toyota@1074,344`),
   wait ~9s, verify `localStorage.currentActiveDealerId === '876'`.

2. **Navigate to `/parts/sales-order`, THEN arm the XHR hook, THEN click Refresh.**
   Arming before the navigate = `__cap` empty (page load wipes it). The Refresh button is
   at `~606,96` — find it with an exact-innerText scan constrained to `rect.width < 160`
   (a naive leaf-node `children.length===0` scan **misses it**; it's a `BUTTON` wrapping a
   `DIV`). One click fires 8 XHRs including the search + full axios headers.

3. **Build a generic in-page replayer once**, then reuse for every endpoint:
```js
(function(){var h=(window.__cap||[]).map(c=>c.h).filter(x=>x&&x['tekion-api-token'])[0];
window.__H=h;
window.__go=function(url,body,method){window.__r=null;
  var o={method:method||(body?'POST':'GET'),headers:JSON.parse(JSON.stringify(h)),credentials:'include'};
  if(body)o.body=JSON.stringify(body);
  fetch(url,o).then(r=>r.text()).then(t=>{window.__r=t;}).catch(e=>{window.__r='ERR '+e;});
  return 'go';};
return h?'H-OK':'H-MISSING';})()
```
   Then `window.__go(url[,body])`, `sleep 6`, read `window.__r`. **A bare in-page
   `fetch()` without these headers returns `500 "Token doesn't exist or is invalid"`** —
   cookies alone are not enough; the axios interceptor's `tekion-api-token` is required.

**Correct endpoints (2026-09-02):**
```
POST /api/partTrade/u/sale/order/search      ← NOT /sales-order/search (that one 404s silently → LEN 0)
GET  /api/partTrade/u/sale/order/<internalId>
GET  /api/cms/u/customers/<customerId>
```
Minimal search body — **drop the `status` filter to see CLOSED orders**:
```json
{"sort":[{"field":"modifiedTime","order":"DESC"}],
 "filters":[{"field":"siteId","key":"siteId","operator":"IN","values":["-1_876"]}],
 "searchText":"331990","groupBy":[],
 "includeFields":["id","orderNo","createdTime","modifiedTime","saleType","saleSubTypeId",
                  "saleAmount","customer","status","partCounterPersonName","departmentName"],
 "searchableFields":[],"page":{"from":0,"size":5}}
```
Response: `data.{count,hits[]}`.

### 🔴 PAGINATION IS SILENTLY IGNORED on `/sale/order/search` — use date-window bisection

**The `from`/`start` offset does nothing.** I looped `from = 0,20,40,60,80,100` and got
"120 rows" that were **six identical copies of the same 20 records**. `count` reports the
true total (e.g. 32) but you only ever receive ~20 hits, always the same ones. This will
manufacture a completely false history if you concatenate the pages.

**Workaround — window on `createdTime` and walk the windows:**
```python
def T(s): return int(datetime.datetime.strptime(s,"%Y-%m-%d %H:%M").timestamp()*1000)

body={"sort":[{"field":"createdTime","order":"ASC"}],
 "filters":[
   {"field":"siteId","key":"siteId","operator":"IN","values":["-1_876"]},
   {"field":"customer.id","key":"customer.id","operator":"IN","values":[CUSTOMER_ID]},
   {"field":"createdTime","key":"createdTime","operator":"BTW","values":[T(a),T(b)]}],
 "searchText":"","groupBy":[],
 "includeFields":["orderNo","createdTime","customer"],
 "searchableFields":[],"page":{"from":0,"size":20}}
```
Keep each window under ~20 results (check `count`; if `count > 20` split the window).
Sort `ASC` so the earliest rows in the window are the ones you actually receive.

**Useful filter fields (all verified working):** `siteId`, `customer.id`, `saleType`
(`WHOLESALE`/`RETAIL`), `status`, `createdTime` with `BTW` + epoch-ms pair.

### ⭐ Scope test — is it ONE customer or the WHOLE STORE?

Before blaming a customer, re-run the same window **filtered on `saleType` only, no
customer filter**, on the day before and the day of the suspected change:
```json
"filters":[{"field":"siteId",...},
           {"field":"saleType","key":"saleType","operator":"IN","values":["WHOLESALE"]},
           {"field":"createdTime","key":"createdTime","operator":"BTW","values":[...]}]
```
Then eyeball `customer.taxable` across ~20 different body shops. If the flag is uniform
across unrelated customers, it's a **store-level settings change**, and every per-customer
hypothesis is dead. This one query converted a two-order puzzle into a 150-orders/day
finding.

One-shot tax extractor for a pulled SO (`window.__r` = the SO payload):
```js
(function(){var d=JSON.parse(window.__r).data;var codes={};
(d.partSaleDetails||[]).forEach(function(p){var c=(p.taxCodeDetails&&p.taxCodeDetails[0])||{};
 var k=(p.taxable?'taxable=T':'taxable=F')+' | code='+(c.taxCode||'none')+' | pct='+(c.taxPercentage||'-');
 codes[k]=(codes[k]||0)+1;});
return JSON.stringify({cust:d.customer&&d.customer.name,soTaxable:d.customer&&d.customer.taxable,
 sale:d.saleType,status:d.status,lines:(d.partSaleDetails||[]).length,
 taxTotal:d.tax&&d.tax.taxAmount,breakdown:codes});})()
```
Grouping the lines into a **counted breakdown** (rather than dumping every line) is what
made the header-vs-line contradiction obvious at a glance.

11. **`POST /screenshot` does not exist on the `:9223` bridge** (`Cannot POST /screenshot`,
    and `GET /` is `Cannot GET /` — no route listing). You cannot hand Joe a visual of the
    GLAM table from that port; reconstruct tables as text via `/eval` innerText scans.
    Available verified routes: `/health`, `/eval` (body key **`js`**), `/navigate`, `/mouse`, `/type`.

12. **`execute_code` has a hard 300s ceiling** — a chained multi-`/eval` browser script got
    killed at 300s having made **zero** recorded tool calls. Wrap every curl in
    `timeout N`, budget 35–50s per `/eval`, and keep each `execute_code` block to a handful
    of calls. Long browser work must be chunked across blocks, not looped in one.

13. **Don't assume you know which customers the two SOs belong to.** I carried forward an
    assumption from a prior session that both orders were the same customer and navigated
    to the wrong customer record first. 331990 = **De Laveaga**, 323623 = **Crash Champions**
    — two different accounts. Pull `customer.id` off each SO payload *before* opening any
    customer page.

14. **Reaching posted JEs / GL detail — all four paths I tried FAILED.** Budget for this or
    tell Joe up front you may not close the ledger loop:
    - `/navigate` to `/accounting/journal-entries` **silently redirects** to
      `/accounting/chartOfAccounts/list`. The URL is wrong or gated; the page you land on
      is not the one you asked for. Always re-read `location.href` after navigating.
    - `POST /api/cms/u/accounting/gl-account/search` → `validation.invalid.request`
    - `POST /api/accounting/u/gl-account/search` → `unexpected.error`
      (both with valid captured headers — the body shape is wrong and I never recovered it)
    - Guessed SO-invoice endpoints all returned `PENDING`/nothing:
      `/sale/order/<id>/invoices`, `/sale/order/invoice/<id>`,
      `/invoice/salesOrder/<id>`, `/sale/order/<id>/accounting`
    - Accounting left-nav only exposes two links: `FS::/accounting/financialStatements/list`
      and `CA::/accounting/chartOfAccounts/list` — there is no journal-entry link to click.
    **Next time: capture the real endpoint from the app** (arm the XHR hook, then reach
    Journal Entries by clicking through the App Grid rather than a guessed URL).

15. **`/type` fails on Tekion's Chart-of-Accounts search input — three ways.** Wasted ~5
    calls here:
    - `/type` with `{x,y}` → `{"error":"selector or ref, and text are required"}`
      (the endpoint needs `selector` or `ref`, NOT coordinates)
    - `/type` with a tagged `[data-jay=...]` selector → `page.fill: Timeout 30000ms exceeded`
      even though the locator resolved
    - native-value-setter + `input`/`change`/`Enter` events → input visually accepts the
      text but **fires zero XHRs** (`__cap` stayed `[]`)

    Getting a React grid to actually re-query is unreliable. **Prefer replaying the search
    API via `window.__go` over driving the UI search box.**

16. **The XHR hook does not survive `/navigate` — and neither does `window.__go`.** After
    every navigation: re-arm the hook, trigger one real app action (e.g. the Refresh
    button) to repopulate `__cap`, then rebuild `__go`. Rebuilding `__go` on a page where
    `__cap` is empty returns `NOHDR` and every later call fails with
    `500 "Token doesn't exist or is invalid"`. I hit this once and had to bounce back to
    `/parts/sales-order` purely to re-harvest headers.

## ⚠️ TRAPS (both nearly produced a wrong answer)

1. **DUPLICATE orderNo across eras + FUZZY search.** Searching `323623` returned **FOUR**
   hits, only two of which had that order number:
   - id **519922** — orderNo 323623, created 2026, SCT wholesale, STEVEN MARTINEZ ← the real one
   - id **257325** — orderNo 323623, created **2019-10-17**, `saleType: RETAIL`,
     `saleSubTypeId: null`, `departmentName: null`, counterperson **"System"** = legacy ghost
   - id 207592 — orderNo **398217**, Laura Ramirez ← *not even the number you searched*
   - id 248756 — orderNo **355755**, Laura Ramirez ← *ditto*

   **`searchText` is fuzzy — `hits[0]` is NOT necessarily your order.** Always filter the
   hits array on exact `orderNo` yourself, THEN disambiguate survivors by `createdTime` +
   internal `id`. Treat `partCounterPersonName:"System"` + null department as a
   pre-migration ghost. Grabbing the wrong record would have "proved" the same SO number
   goes both retail and wholesale.

2. **The SO list's DEFAULT status filter hides CLOSED orders.** Default filter is
   `status IN [DRAFT, DELIVERED, PARTIALLY_DELIVERED, INVOICED]` — **CLOSED is absent.**
   A legitimately closed SO shows **"0 Result(s) / No rows found"** in the UI, which
   looks like "that order doesn't exist at this store." 323623 (CLOSED/PAID) did exactly
   this. Strip the `status` filter in the API replay, or clear it in the UI.

3. **Mixed cents/dollars in the SAME response.** `data.salesOrderSummary.subTotal =
   466181.0` (cents) while `data.salesOrder.taxSummary.subTotal = 4661.81` (dollars) and
   `invoices[].totalInvoiceAmount.amount = 460013` (cents). Do not blanket-apply the
   "Tekion is always cents" rule inside this payload — check each field against the
   on-screen number.

4. **`postedToAccounting: false` on closed, fully-paid SOs.** Don't read that as "never
   posted." Scope your claim to *which mapping row the transaction matches*, and offer
   to pull the actual JEs if he wants posted-ledger proof. (Joe accepts "I haven't
   confirmed the JE yet"; he does not accept a confident wrong answer.)

5. **Dealer drift on `:9225`.** A `/mouse` mis-click during nav flashed a "Blackstone
   Chevrolet Cadillac" toast mid-session. Re-assert `localStorage.currentActiveDealerId`
   AND the header store name before trusting any read.

6. `/eval` body param is **`js`**, not `expression` (→ `{"error":"js is required"}`).

7. **🔴 ORDER SNAPSHOT ≠ MASTER RECORD.** The single worst trap here — it cost a
   retraction to Joe. `salesOrder.customer.taxable` is frozen onto the order at creation.
   When Joe asks *"where is the master record that says X is taxable?"* you must be able
   to point at `/api/cms/u/customers/<id> → taxInformation.partsTaxInfo[0].taxExempted`
   and the **Tax Exemptions → Parts** sub-tab. If you never pulled that endpoint, you do
   not know the master. **Pull the master before asserting anything about customer setup.**

8. **Customer endpoints are `fetch()`, not XHR** — the XHR hook returns nothing for them.
   Install the `window.fetch` wrapper too (see the customer-master section above).

9. **The three Tax Exemptions sub-tabs look near-identical.** Parts / Sales / Service all
   render the same grid layout. I nearly reported the **Service** tab's values as the
   Parts answer. Screenshot and `vision_analyze` asking *"which sub-tab is highlighted
   blue?"* before reading any value off it — and prefer the API payload over the screen.
   Also: the list-view columns (`Sales Tax`/`Service Tax`/`Parts Tax` Yes/No) are
   ambiguously labeled and are NOT a reliable read of exemption status.

10. **UI vs API mismatch on the exempt number.** Screenshot rendered De Laveaga's tax
    exempt number as `101201554-11000`; the API returned `101201554-10000`. Could be OCR,
    could be real. **Never quote a number to Joe off vision — quote it from the payload.**

## Diagnosis checklist (order matters)

1. Confirm the store + dealer id on the browser port.
2. Pull BOTH orders via `sale/order/v4/<id>` (strip status filter to find them).
3. Verify you have the right record — check `createdTime`, reject "System" ghosts.
4. Tabulate all 6 Parts-Counter dimensions for both.
5. Read the live Parts-Counter mapping rows from GLAM.
6. Find the single differing dimension; **eliminate the others by shared value**, not by
   eyeballing.
7. **If the differing dimension is Customer Tax Status → PULL BOTH CUSTOMER MASTERS**
   (`/api/cms/u/customers/<id>`, `partsTaxInfo[0].taxExempted`) before saying a word about
   customer setup. The order snapshot is not the master. If the masters match, say so and
   name the snapshot mechanism as OPEN rather than inventing one.
7b. **⭐ IF THE MASTERS MATCH — RUN THE SCOPE TEST BEFORE ANYTHING ELSE.** Query all
   wholesale SOs store-wide across a date range and check whether `customer.taxable` is
   uniform across unrelated customers. If it is, this is a **store-level change, not a
   customer problem** — bisect `createdTime` windows to find the exact flip date, then
   look for a tax code whose `effectiveDate` sits just before it
   (`taxConfiguration.taxDetails[].taxRateDetails[].effectiveDate` on a post-change SO).
   Two unrelated customers with the same anomaly is the signal. Do not spend turns
   diffing customer records once you see it.
8. Report the matched row, the mechanism, and any candidate defects that SURVIVED
   verification.
9. **Change nothing** if he said diagnosis only — he says "I DON'T WANT YOU TO FIX
   ANYTHING" and means it. End with "nothing touched."
10. **Offer the fleet check.** A store-level tax-code rollout probably hit the other six
    stores the same night. Joe escalates to the whole fleet anyway — offer it up front.

## Related skills
- `tekion-internal-cost-center-gl-routing` — internal REPAIR ORDER cost centers, Services-Internal table, GLAM nav + Chart of Accounts reads
- `tekion-parts-sales-orders` — SO workflow, pricing hierarchy, no-reopen rule
- `tekion-parts-tax-not-calculating-diagnosis` — when tax is $0 and shouldn't be (taxCodeGrid dropped by migration)
- `tekion-journal-entry-error-diagnosis` — when the JE actually errors
- `persistent-browser-server` — `:9225` lane, XHR hook, `/mouse`
