---
name: tekion-parts-so-gl-account-routing
description: Diagnose "this parts Sales Order / counter sale is hitting the WRONG GL account" (e.g. a Wholesale SO posting to a retail parts sales account). Covers the GLAM Fixed Operations > Part & Accessories > Parts-Counter mapping table, its 6 keying dimensions, the customer.taxable master-flag gotcha, and the internal API endpoints to pull a full SO for evidence. Use for any "why did SO X go to retail instead of wholesale" question.
triggers:
  - sales order hitting retail sales
  - so going to wrong gl account
  - counter sale posting to retail
  - wholesale so posted retail
  - parts sales order gl mapping
  - why did this sales order go to
  - parts-counter mapping
  - compare two sales orders gl
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

### What actually differs (OPEN — unresolved, do not guess)

The `taxable` value **snapshotted onto each order**, plus tax regime:

| | SO 331990 → retail | SO 323623 → wholesale |
|---|---|---|
| `customer.taxable` (order snapshot) | `true` | `false` |
| `taxRegime` | **`null`** | `SALES_TAX` |
| `taxConfiguration` | NO TAX on all 5 components, `taxExempt:false` | — |
| `taxSummary.totalTaxAmount` | `0.00` on $4,661.81 | — |

Same master exemption status, different snapshot. Unverified leads, in strength order:
1. **`/api/cms/u/tax-code-setup/<id>` differs materially** — De Laveaga's response is
   9,356 bytes vs Crash Champions' 3,026. Parse and diff these first.
2. **`taxRegime: null` on 331990** — a null regime may fall through to the Taxable branch.
3. **Timing** — De Laveaga master last modified Oct 30 2025; SO created Aug 24 2026. If
   the order captured a stale/default `taxable`, that's a Tekion snapshot bug.

Per Joe's NEVER-GUESS rule: present the leads and ask which to chase. Do not pick one and
assert it.

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
2. **The mapping row itself** — `Taxable / Wholesale → 4740 …COUNTER RTL…` sends taxable
   wholesale revenue into the retail counter account. Arguably wrong by design.
   **This one survives regardless of the snapshot question** — it's a standalone finding.

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

## ⚠️ TRAPS (both nearly produced a wrong answer)

1. **DUPLICATE orderNo across eras.** Searching `323623` returned **TWO** hits:
   - id **519922** — created 2026, SCT wholesale, counterperson STEVEN MARTINEZ ← the real one
   - id **257325** — created **2019-10-17**, `saleType: RETAIL`, `saleSubTypeId: null`,
     `departmentName: null`, counterperson **"System"** = a legacy/migrated record.

   Grabbing the wrong one would have "proved" the same SO number goes both retail and
   wholesale. **Always disambiguate by `createdTime` + internal `id`; treat
   `partCounterPersonName:"System"` + null department as a pre-migration ghost.**

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
8. Report the matched row, the mechanism, and any candidate defects that SURVIVED
   verification.
9. **Change nothing** if he said diagnosis only — he says "I DON'T WANT YOU TO FIX
   ANYTHING" and means it. End with "nothing touched."

## Related skills
- `tekion-internal-cost-center-gl-routing` — internal REPAIR ORDER cost centers, Services-Internal table, GLAM nav + Chart of Accounts reads
- `tekion-parts-sales-orders` — SO workflow, pricing hierarchy, no-reopen rule
- `tekion-parts-tax-not-calculating-diagnosis` — when tax is $0 and shouldn't be (taxCodeGrid dropped by migration)
- `tekion-journal-entry-error-diagnosis` — when the JE actually errors
- `persistent-browser-server` — `:9225` lane, XHR hook, `/mouse`
