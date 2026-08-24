---
name: tekion-fee-charging-tax-diagnosis
description: Diagnose "fee X is charging tax and it shouldn't" in Tekion (e.g. "BATTFEE is charging tax") — the INVERSE of tekion-parts-tax-not-calculating-diagnosis. Root cause is almost always the new Parts Tax Code Setup migration leaving a fee's active pricingSetup.taxConfigs EMPTY so the FEES component tax code applies. Covers the all-fees taxConfigs sweep, why legacy EXCLUDE_TAX_CALCULATIONS is ignored, and the parts sale-order pagination trap that produces false "found 0" scans.
triggers:
  - fee is charging tax
  - battfee charging tax
  - fee shouldn't be taxed
  - fee taxable when it should be exempt
  - disposal fee / battery fee tax wrong
  - tax showing on a fee line
---

# Tekion "a fee is charging tax when it shouldn't" diagnosis

## When to use
Store/Joe says a specific fee code is being taxed (BATTFEE, CABATT, BATTCORE,
tire disposal, doc fees...). This is the **mirror image** of
`tekion-parts-tax-not-calculating-diagnosis` ($0 tax) — same migration, opposite
symptom, and the same "screen renders a default that isn't saved" trap.

Related: `tekion-fee-not-showing-diagnosis` (fee invisible / not applying).

## TL;DR root cause

After a store is flipped to the **new Parts Tax Code Setup**, taxability of a fee
is decided by the fee's **active pricing setup `taxConfigs[]`**. If that array is
**empty**, the fee falls through to the parts tax setup's **`FEES` component tax
code** and gets taxed at the full rate.

The **legacy** `configs[].overrideFlags: EXCLUDE_TAX_CALCULATIONS` that used to
suppress tax is **IGNORED by the new engine**. A fee can show
`EXCLUDE_TAX_CALCULATIONS = true` in `configs[]` and still be fully taxed.
Do not let that flag talk you out of the diagnosis.

## The 60-second diagnostic — sweep ALL fees, find the outlier

This is the fast path. Don't scan transactions first; compare the fee against its
siblings at the same store. A misconfigured fee stands out instantly because
every correctly-configured fee has 1–3 `taxConfigs` rows and the broken one has 0.

```js
(async()=>{
const H=Object.assign({},window.__H,{dealerId:'<DEALERID>','tek-siteId':'-1_<DEALERID>'});
const r=await fetch('/api/service-module/u/fee/v3/search',{method:'POST',headers:H,
  body:JSON.stringify({searchText:'',filters:[],sort:[],page:{from:0,size:200}})});
const hits=((await r.json()).data||{}).hits||[];
const out=[];
for(const h of hits){
 const d=((await (await fetch('/api/service-module/u/fee/v3/details?locale=en_US',
   {method:'POST',headers:H,body:JSON.stringify({fees:[{feeCode:h.feeCode,id:h.id}]})})
   ).json()).data||[])[0]||{};
 const act=((d.pricingSetup||{}).active||[])[0]||{};
 out.push({code:d.feeCode, dept:d.department, st:d.dealerFeeStatus,
   actTaxCfg:(act.taxConfigs||[]).length,                      // <-- THE NUMBER
   actFlags:(act.overrideFlags||[]).map(f=>f.flag),
   cfgTax:(d.configs||[]).map(c=>(c.taxConfigs||[]).length).join(','),   // legacy, ignore
   cfgFlags:[...new Set([].concat(...(d.configs||[]).map(c=>(c.overrideFlags||[]).map(f=>f.flag))))]});
}
return JSON.stringify(out);})()
```

**`actTaxCfg: 0` on exactly one fee = that's your culprit.**

Real output, VW Clovis (1891), 2026-08-24:

```
BATTFEE      PARTS  ACTIVE   actTaxCfg 0   actFlags [AUTO_ADD_TO_PART]      <-- BROKEN
SMOGTEST     SALES  ACTIVE   actTaxCfg 1
ELECTFILING  SALES  ACTIVE   actTaxCfg 1
WTAX/LOFDIS/RESTOCK/MISC/FEE  actTaxCfg 3
```

A correctly non-taxable fee looks like this (Alfa Romeo `CABATT` / `BATTCORE`):

```json
"taxConfigs":[
 {"taxRegimeType":"SALES_TAX","taxable":false,"payType":"CUSTOMER_PAY","subPayTypes":["ALL_CUSTOMER_PAY"]},
 {"taxRegimeType":"SALES_TAX","taxable":false,"payType":"WARRANTY","subPayTypes":["ALL_WARRANTY_PAY"]},
 {"taxRegimeType":"SALES_TAX","taxable":false,"payType":"INTERNAL","subPayTypes":["ALL_INTERNAL_PAY"]}]
```

Cross-store comparison is the single strongest evidence you can hand Joe — he
accepts "every other fee here has 3 rows, this one has 0" immediately.

## Confirm the other half: the parts tax setup maps FEES

```js
GET /api/parts-settings/u/tax-setup     // headers overridden to target dealer
→ data.saleTypeTaxSetup[] per RETAIL / INTERNAL / WHOLESALE
  each with taxCodeMappings[] components: PARTS, CORE_SALE, CORE_RETURN, FEES, LABOUR
```

If `component: "FEES"` has a real tax code (e.g. `8.975% Tax`) — and it will —
then an empty `taxConfigs` on the fee means **taxed**. Note
`data.createdTime` = the migration cutover timestamp; anything after it is on
the new engine.

Corroborate on an order: `taxConfiguration.taxCodeGrid` will contain
`FEES=<tax code>`, and `extra.isNewTaxCodeSetupEnabled: ["true"]`.

## The fix (UI)

### ⚠️ DO NOT APPLY IT YOURSELF — Joe's standing rule
Fee taxability is a **live financial-control change**. Jay stays **read-only
(GET / POST-search only) on tax + fee + settings screens.** Deliver the diagnosis
and the exact click path; Joe or a store user performs the save. Joe stated it
flat out on 2026-08-20 during the parts-tax fleet fix: **"I don't want you to fix
it."** Offering "want me to go make the change now?" is the wrong close — offer
to **verify after they save** instead. Never treat "I gave the fix and he didn't
object" as approval.

Fees (`/core/fees`) → the fee → **active Pricing Setup** → Tax section → add three rows:

| Regime | Pay type | Sub pay type | Taxable |
|---|---|---|---|
| SALES_TAX | Customer Pay | ALL_CUSTOMER_PAY | **No** |
| SALES_TAX | Warranty | ALL_WARRANTY_PAY | **No** |
| SALES_TAX | Internal | ALL_INTERNAL_PAY | **No** |

**VERIFY BY API, NOT BY EYE.** Re-run the sweep and require `actTaxCfg: 3`.
The tax-code dropdown on blank rows renders a *default* value that is not saved —
identical trap to the SCT 876 parts-tax migration. Someone can "fix" it, see a
tax code on screen, and the record still shows `taxConfigs: []`.

Same applies to `modifiedTime`: a fresh `modifiedTime` proves *someone saved
something*, NOT that the tax configs landed. On the VC case the fee had been
edited 71 seconds before the complaint and still had `taxConfigs: []`.

## ⚠️ DEAD ENDS — do not repeat these (they cost hours)

### 1. `/api/partTrade/u/sale/order/search` IGNORES `page.from`
Every page returns the **same** first 20 rows. Proof:

```
from=0   -> [71598,71597,71596,71595]
from=20  -> [71598,71597,71596,71595]
from=40  -> [71598,71597,71596,71595]
from=100 -> [71598,71597,71596,71595]
```

So a loop `for(f=0; f<600; f+=20)` scans **the same 20 orders 30 times** and
reports a confident `scanned 600, found 0`. Three separate scans (600, 500, 400
orders) were all invalidated by this. Same family of quirk as
`/api/parts/activity-log/u/search` ignoring `pageNumber`
(see `tekion-part-sales-ledger-report`).

**Always sanity-check pagination by printing the first orderNo of pages 0/20/40
before trusting any scan.** If `from` is ignored, paginate by
**time-window bisection** on `createdTime` with an id-dedupe set instead.

### 2. Fee lines are NOT in `partSaleDetails[].charges[]`
That array is `[]`, and `assetCharges` is `[]` too, even on orders that carry
fees. Use the tax summary instead:

```
taxSummary.subTotalFees                       // fee dollars on the order
taxSummary.soSummaryForTax.totalFees          // (cents, on some payloads)
taxSummary.formattedTaxByTaxCodeId{}          // taxCode -> {totalTaxAmount,totalAmount}
taxConfiguration.taxCodeGrid[]                // component -> taxCode
```

### 3. `taxSummary: {}` and `taxCodeGrid: []` on older orders
Not a bug and not "no fees" — orders created **before** the new-tax-setup
cutover simply have no new-engine block. Use the cutover timestamp from
`tax-setup.createdTime` to know which orders can even be evaluated.

### 4. Endpoint / envelope failures
- `/api/parts/activity-log/u/search` requires the body wrapped in
  `{tekRequest:{...}}` — unwrapped returns `{"tekRequest":"must not be null"}`.
  Even wrapped, a `searchText` of a part number returned 0 here.
- `/api/tax-codes/u/search`, `/u/all`, `/api/parts-settings/u/tax-codes`,
  `/api/tax-management/u/tax-codes/search` — **all 404**. Read tax codes off an
  order's `taxConfiguration.taxDetails[]` instead.
- `/api/rosearchservice/u/ro/search` returns an empty body.
- Part search by internal id (`M_VW_000915105ADDSP`) or raw part number returns
  `count 0` — don't try to trace the fee through the part master.

### 5. Don't hunt the symptom in transactions first
~1,100 parts sale orders + 300 ROs were scanned before the config sweep. The
config sweep took one call and answered it. **Config first, transactions only to
quantify exposure.**

## Field-path discovery: recursive key walk (use this instead of guessing)
When a payload is large but your probed keys come back empty (`len 15253, keys []`),
stop guessing paths:

```js
const found=[];
(function walk(n,p){if(n&&typeof n==='object'){for(const k in n){const np=p+'.'+k;
 if(/fee|charge|tax/i.test(k)) found.push(np+' = '+JSON.stringify(n[k]).slice(0,300));
 walk(n[k],np);}}})(o,'');
```
This is what finally located `taxConfiguration.taxCodeGrid`,
`taxSummary.formattedTaxByTaxCodeId` and `extra.isNewTaxCodeSetupEnabled`.

## Cross-dealer without switching the UI
Never switch the UI dealer for a read-only diagnosis — override headers on a copy:

```js
const H = Object.assign({}, window.__H, {dealerId:'1891','tek-siteId':'-1_1891'});
```
Dealer ids: AR 6195 · BC 1251 · BT 1249 · ST 876 · SV 826 · TL 1092 · VC 1891.
`window.__H` is **destroyed by every `/navigate`** — rebuild it (builder in
`tekion-fee-not-showing-diagnosis`) and assert `window.__H.dealerId` before
trusting a scan. A scan started before a nav silently no-ops at `p:0`.

## Worked example — VW Clovis BATTFEE, 2026-08-24
Complaint: *"Battfee is charging tax."*
- VC flipped to new Parts Tax Code Setup **2026-08-19 8:10:32 PM PDT**;
  `FEES → 8.975% Tax` on RETAIL, INTERNAL and WHOLESALE.
- `BATTFEE` (id `642dda042a5f844bcd014c58`, dept PARTS, $200 FLAT_PRICE,
  GL `1891_2225`, `AUTO_ADD_TO_PART`, scoped to 19 VW battery partIds +
  source `642c1d66e21b84000770ce28`) had **`pricingSetup.active[0].taxConfigs: []`**
  while carrying legacy `configs[].EXCLUDE_TAX_CALCULATIONS = true` (ignored).
- Every other VC fee had 1–3 taxConfigs. AR's `CABATT`/`BATTCORE` had the full 3.
- Impact: $200 × 8.975% = **$17.95 of wrong tax per battery** since 8/19.
- Fee had been modified by Joe (CONTROLLER) 71s before the complaint and *still*
  showed `taxConfigs: []` → the edit didn't take.
- Fix = add the 3 non-taxable SALES_TAX rows; verify `actTaxCfg: 3` by API.
