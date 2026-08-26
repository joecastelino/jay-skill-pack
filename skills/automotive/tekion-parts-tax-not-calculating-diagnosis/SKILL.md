---
name: tekion-parts-tax-not-calculating-diagnosis
description: Diagnose "sales tax isn't calculating / tax is $0" on Tekion Parts Sales Orders (counter sales), especially for CUSTOM sale order types like ONLINE RETAIL. Finds whether the store was migrated to the NEW Parts Tax Code Setup and whether a sale type is missing from the saved tax-code grid. Use when a Parts Manager reports missing tax on SOs.
triggers:
  - tax isn't calculating on sales orders
  - tax is showing $0 on parts sale
  - online retail sale type not taxing
  - parts sales order missing tax
  - sale type dropped from tax code grid
  - tax setup for parts migration issue
  - fee is charging tax when it shouldn't
  - custom sale type shows no tax
  - saleTypeTaxSetup missing sale type
---

# Tekion Parts Sales Order — tax not calculating

## When to use

A Parts Manager (e.g. Glade @ SCT) says "tax on sales orders isn't working / tax is $0".
Classic signature: SOME sale types tax fine, one specific type (usually a CUSTOM sale order
type like `ONLINE RETAIL`) shows $0 tax, and it started on a specific date.

**Inverse symptom?** If the complaint is "a FEE is charging tax and shouldn't", use
**`tekion-fee-charging-tax-diagnosis`**. Same migration, opposite direction: the fee's
`pricingSetup.active[].taxConfigs` is empty so it falls through to the `FEES` component
tax code in this very `saleTypeTaxSetup`. Legacy `EXCLUDE_TAX_CALCULATIONS` no longer
suppresses tax under the new engine.

## Root cause #1 (the one that actually happened, SCT 2026-08-20)

Tekion migrates stores onto a **new Parts Tax Code Setup** (feature flag
`USE_NEW_TAX_CODES_SETUP` / `PARTS_TAX_CODE_ENABLED`). The migration writes a record
`<dealerId>_part_settings_tax_setup` containing `saleTypeTaxSetup[]` — but it only carries
over the **native** sale types (RETAIL / WHOLESALE / INTERNAL + VENDOR).

**CUSTOM sale order types (ONLINE RETAIL, ONLINE WHOLESALE, any dealer-created type) are
silently dropped.** Orders created under them get `taxConfiguration.taxCodeGrid = []`,
so order-level tax aggregation never runs → `totalTaxAmount: 0` even though the customer
is taxable, the parts are taxable, and the LINE resolves a tax %.

### 🚨 The UI LIES — do not trust the screen

`/parts/tax-code-setup` ("Tax Setup for Parts") **renders "10% Tax" in the ONLINE RETAIL /
ONLINE WHOLESALE rows even when nothing is saved for them.** That's the dropdown's default
render, not persisted data. Vision-analyzing the screenshot will confidently tell you the
rows are populated. **Always verify against the API**, never the screen.

## Step 1 — Confirm the symptom & find the cutover moment

Use the :9223 authenticated browser (see PITFALLS for getting `window.__H`).

Pull recent orders and print the discriminators side by side:

```js
// order search
POST /api/partTrade/u/sale/order/search
{"sort":[{"field":"createdTime","order":"DESC"}],
 "filters":[{"field":"siteId","key":"siteId","operator":"IN","values":["-1_876"]},
            {"field":"saleSubTypeId","key":"saleSubTypeId","operator":"IN","values":["ONLINE RETAIL_RETAIL"]}],
 "searchText":"","groupBy":[],
 "includeFields":["id","orderNo","createdTime","status","tax","saleAmount"],
 "page":{"from":0,"size":100}}
// -> data.count, data.hits[]

// order detail
GET /api/partTrade/u/sale/order/{id}   // v4/{id} variant exists but 500s from a bare fetch
```

Read these four fields per order:

| Field | Meaning |
|---|---|
| `taxConfiguration.taxCodeGrid.length` | **THE discriminator.** 5 = new engine wired. 0 = broken (or pre-migration). |
| `tax.saleTax` / `tax.saleTaxAmount.amount` | **LEGACY** engine tax (cents). Populated on PRE-migration orders. |
| `tax.preciseTaxCodesTaxAmount` | **NEW** engine tax. Populated on POST-migration orders. |
| `taxSummary.totalTaxAmount` vs `taxSummary.preciseTotalTaxAmount` | mismatch (0 vs a real number) = grid missing but line resolved |

**Reading the two engines is the key insight.** A pre-migration order shows
`saleTax:"10", saleTaxAmount:{amount:509}` and `grid:0` — that is **WORKING** (legacy),
not broken. A post-migration order shows `saleTax:null, preciseTaxCodesTaxAmount:0, grid:0`
— that is **BROKEN**. Do not report "it's been broken for 14,000 orders" — sort by time and
find the flip.

Walk order IDs sequentially (`for id in 527600..527680`) to get a clean chronological table
across ALL sale types — that exposes the exact minute the store flipped engines.

## Step 2 — Prove it against the saved setup (the money shot)

```js
GET /api/parts-settings/u/tax-setup
```

Returns `data.saleTypeTaxSetup[]` (one entry per sale type, each with `taxCodeMappings[]`
for components PARTS / CORE_SALE / CORE_RETURN / FEES / LABOUR) plus
`data.miscellaneousTaxSetup[]` (VENDOR). Also `data.createdTime` = **the migration
timestamp** — cross-check it against the order flip from Step 1. They will match.

If the complained-about sale type is **absent from `saleTypeTaxSetup`**, that's the root cause.

## Step 3 — Quantify exposure

Count non-VOIDED orders of that sub-type created since `data.createdTime`, sum
`saleAmount.amount / 100`. Report orders, dollars, and est. missed tax. Joe wants the number.

## Step 4 — The fix (CONFIRMED WORKING, SCT 8/20/2026 9:41 AM PT)

Navigate by **DIRECT URL `/parts/tax-code-setup`** ("Tax Setup for Parts").

⚠️ **There is no "Parts → Settings" menu item** — Joe pushed back on that exact wording.
The app-grid Settings tab has a tile called **"Parts Settings"** which goes to
`/parts/parts-settings` — a *different* page. Other near-miss tiles that waste your time:
"Tax Codes Setup" → `/core/taxCodes/list` (the master tax-CODE list, not the mapping grid),
and "Code Setup" → `/parts/priority-codes` (special-order priority codes). Just give the
direct URL.

On the page: **Edit** → on each missing sale-type row, **uncheck / re-check (re-select) the
tax code in every component cell** (Parts, Core Sale, Core Returns, Fees, Labour) *even
though they already appear filled* → **Save**. The uncheck-and-recheck is what forces the
row to actually persist — a plain Save with the phantom-rendered values does nothing.

**Verify by API, not by the screen:**
```js
GET /api/parts-settings/u/tax-setup
// every sale type should now appear with n=5 taxCodeMappings:
//   RETAIL 5 · WHOLESALE 5 · INTERNAL 5 · ONLINE RETAIL_RETAIL 5 · ONLINE WHOLESALE_WHOLESALE 5
```
Then pull the newest order of that sub-type and confirm `taxCodeGrid.length == 5` and
`taxSummary.totalTaxAmount > 0`. SCT proof: same $1.55 order shape went $0 tax at 8:36 AM →
**$0.16 at 9:42 AM** (order 331391, grid 5, `10% Tax`).

### Orders created during the broken window DO NOT self-heal

They keep `grid: 0` forever. List them and hand them back for re-keying:
DRAFT ones must be deleted and re-entered (or a line removed/re-added to force a tax
recalc) **before invoicing**, or they invoice untaxed. Already-DELIVERED/CLOSED ones need a
manual tax correction. At SCT this was 4 orders (~$248 of the $250.10 exposure sat in 3
DRAFTs).

### ⚠️ DO NOT APPLY THIS YOURSELF — Joe's standing rule

This is a live financial-control change. **Jay stays read-only (GET / POST-search only) on
tax + settings screens.** Deliver the diagnosis and the exact click instructions; Joe or a
store user performs the save.

Joe said it flat out on 2026-08-20 after the fleet was fixed: **"I don't want you to fix
it."** At SCT he had a store user do the uncheck/recheck; at BT/BC/TOL his people applied
the same fix from Jay's writeup. Jay's job was verification only. Never assume that
"I gave you the fix and you didn't object" = approval to save.

**Say the nav path in the user's own menu terms.** Joe pushed back with *"I don't see
'parts' and then 'settings'"* on a path that didn't exist in his UI. Walk the real screen
(or give the direct URL) before quoting a breadcrumb — see the tile traps above.

## "The row is GREYED OUT and I can't change it" (BT, 8/20/2026)

**Not a bug and not a permission problem.** A sale-type row on `/parts/tax-code-setup` is
rendered disabled when that custom sale sub-type is **Inactive**.

Source of truth — one call, all stores:
```js
GET /api/parts-settings/u/settings   // per dealerId header
// -> data.saleSubTypes[] = [{saleSubTypeId, saleType, saleSubType, active}]
```
`active:false` ⇒ that row is greyed on the tax screen. Exact 1:1 match, verified at BT:
disabled inputs sat at row y=499 (`Online Wholesale`) and y=542 (`Wholesale Credit Card`),
and those are precisely the two with `active:false`.

**It does not need fixing.** An inactive sale type can't be selected on a new SO, so it
cannot generate untaxed orders. Only unlock it (Parts Settings → Custom Sale Order Types →
flip Status to Active) if the store actually intends to *use* that type again — then
re-do the tax-setup uncheck/recheck for the newly-active row.

Confirm the row-to-status mapping visually: the greyed cells have a grey background and
**no dropdown caret**; enabled cells are white with a caret. Count them in the DOM with
`[...document.querySelectorAll('input')].filter(e=>e.offsetParent!==null&&e.disabled)` —
they come in groups of 5 (one per component), so `10 disabled` = exactly 2 locked rows.

### Not every store has custom sale types

Before hunting a missing row, check whether the store even has one. `saleSubTypes` was
`[]` at VC and all-inactive at AR and SV — those stores only run native
RETAIL/WHOLESALE/INTERNAL and are **not exposed to this bug at all**. Don't apply the fix
there and don't report them as broken.

## Fleet-wide sweep (do this once, don't check stores one at a time)

`window.__H` can be retargeted to ANY dealer by swapping two headers — no dealer switching,
no re-login:
```js
const H = Object.assign({}, window.__H, {dealerId:'1249', 'tek-siteId':'-1_1249'});
```
Loop all 7 (AR 6195, BC 1251, BT 1249, ST 876, SV 826, TL 1092, VC 1891) against
`/api/parts-settings/u/tax-setup` + `/api/parts-settings/u/settings` and print
`saleTypes:n` and `saleSubTypes[].active`. Whole fleet audited in one call.

### Fleet state at 8/20/2026 ~10 AM (post-fix reference)

| Store | Setup modified | Sale types in grid | Custom sub-types | Verdict |
|---|---|---|---|---|
| ST 876 | 8/20 9:41 AM | 5 | ONLINE RETAIL ✓, ONLINE WHOLESALE ✓ | fixed |
| BC 1251 | 8/20 9:48 AM | 5 | both active | fixed |
| BT 1249 | 8/20 9:49 AM | 8 | 3 active, 2 **inactive** (greyed) | fixed, greying is correct |
| TL 1092 | 8/20 9:50 AM | 5 | both active | fixed |
| AR 6195 | 8/19 8:10 PM | 3 | Body/Mechanical Shop, both inactive | N/A — no active custom types |
| VC 1891 | 8/19 8:10 PM | 3 | none (`[]`) | N/A |
| SV 826 | 5/19/2026 | 5 | Body/Mechanical Shop, both inactive | N/A — migrated long before, unaffected |

Note SV migrated 10/28/2025 — **the 8/19/2026 8:10–8:12 PM cutover hit 6 of 7 stores in a
90-second window**, which is what made this look like a fleet-wide outage.

## Ruled-out causes (check fast, then move on)

- Customer tax exempt → `customer.taxable`, `taxConfiguration.taxExempt`
- Part not taxable → `partSaleDetails[].taxable`
- Wholesale showing $0 tax is **normal** — resale-certificate customers resolve to `NO TAX`
  at line level with a full `grid:5`. Grid present + NO TAX = correct, not a bug.

## PITFALLS

1. **`window.__H` dies on every hard navigation.** `/navigate` does a full page load and
   wipes the XHR hook. Re-install the hook, then trigger traffic with an **in-app SPA nav**:
   ```js
   history.pushState({},'','/parts/inventory/part');
   window.dispatchEvent(new PopStateEvent('popstate'));
   ```
   A hard `/navigate` right after installing the hook gives `H:false, n:0`.
2. **A bare in-page `fetch()` to `/api/...` works ONLY with `window.__H` headers.** Without
   the app's axios interceptor headers you get 500/"Token doesn't exist".
3. **Don't guess `/api/tax-codes/u/*` paths** — nearly all 404, and
   `GET /api/tax-codes/u/taxCodes/setup` returns a misleading `{"data":null,"status":"success"}`
   (200 but useless). The Parts tax config lives under **`/api/parts-settings/u/tax-setup`**.
   The Service one is a different screen entirely
   (`/service/settings/ro-settings/tax-code-settings`).
4. **Find endpoints by capturing, not guessing.** Install the XHR hook, SPA-navigate to the
   settings page, then dump `window.__X.map(x=>x.m+' '+x.u)`. That's how
   `/api/parts-settings/u/tax-setup` was found after ~15 wasted 404 probes.
5. **Grepping the JS bundles works** for route/permission constants
   (`[...document.querySelectorAll('script[src]')].map(s=>s.src)` then fetch + indexOf).
   It surfaced `TAX_CODE_SETTINGS uiRoute:"/tax-code-settings"` and the feature flags
   `USE_NEW_TAX_CODES_SETUP`, `PARTS_TAX_CODE_ENABLED`,
   `PARTS_TAX_CODE_CUSTOMER_TAX_EXEMPT_ENABLED`. It does NOT contain API paths for these.
6. **`page.from` pagination on order search is UNRELIABLE — verify it every time.**
   With a `siteId` IN filter it is **silently IGNORED**: `from=0/20/40/100` all returned the
   identical first 20 orderNos (VC, 2026-08-24), so a "scanned 600 orders" loop really
   scanned the same 20 thirty times and reported a false `found 0`. Before trusting any
   multi-page scan, print the first orderNo of pages 0/20/40 and confirm they differ.
   If `from` is ignored, paginate by **`createdTime` time-window bisection** with an
   id-dedupe set. `searchText:"<orderNo>"` remains the fast way to jump to one order and
   get its numeric `id`.
7. Dollar fields in `saleAmount` / `tax.saleTaxAmount` are **CENTS**. `taxSummary.subTotal`
   is **DOLLARS**. Both appear on the same object — do not mix them.

## Verified reference values (SCT / dealer 876, 2026-08-20)

- Migration timestamp: `1787195464151` = 8/19/2026 8:11 PM PT
- Tax code `10% Tax` id = `6a867038a5537a692d78fdef`, effective 8/19/2026 8:10 PM PT
- Setup record id = `876_part_settings_tax_setup`, siteId `-1_876`
- Custom sale order types at SCT: `ONLINE RETAIL_RETAIL` (parent RETAIL, dept
  "06 - Online Parts Sales"), `ONLINE WHOLESALE_WHOLESALE` (parent WHOLESALE)
- Exposure at detection: 6 orders / $250.10 / ~$25 tax

---

## "Tax Setup for Parts" is a HIDDEN page — direct URL only

Verified at VC (1891) on 2026-08-24: `/parts/tax-code-setup` has **NO navigation entry anywhere**.
- Nine-dot grid → Settings → Parts Settings group lists ONLY: Source Code, Price Codes, Price Breaks,
  Parts Settings, Customized Price, Code Setup (=/parts/priority-codes), Manufacturers,
  Return Reasons, Void Reasons, Default Parts Pricing, Adjustment Reasons, Core Management Setup,
  Parts Login Settings. **No "Tax Setup".**
- `/parts/parts-settings` (General Settings / Print settings / PDF Configuration / Label Configuration)
  has no tax tab either — only an unrelated "Enable tax on Sublet" toggle.
- `/parts/inventory`, `/parts/price-codes`, `/parts/default-part-pricing` — no tax link.

**Reach it by typing the URL: `https://app.tekioncloud.com/parts/tax-code-setup`**
(page title renders as "Tax Setup for Parts"; Edit button top-right ~x1233,y219).
Grid = rows Vendor/Retail/Wholesale/Internal (+custom sale types) × columns
Parts | Core Sale | Core Returns | **Fees** | Labour.

## INVERSE CASE: a FEE is being taxed when it shouldn't be (VC BATTFEE, 2026-08-24)

Same new-Parts-Tax-Code-Setup engine, opposite symptom. A **fee** gets taxed because the parts
tax grid maps component `FEES` → a tax code, and the fee's own pricing setup carries no tax
config to override it.

Diagnose via API (in-page fetch with `window.__H`, override `dealerId`/`tek-siteId`):
```
POST /api/service-module/u/fee/v3/search                 -> fee id by feeCode
POST /api/service-module/u/fee/v3/details?locale=en_US   body {fees:[{feeCode,id}]}
     -> data[0].pricingSetup.active[0].taxConfigs   <-- the ONLY thing the new engine reads
GET  /api/parts-settings/u/tax-setup                     -> saleTypeTaxSetup[].taxCodeMappings (component FEES)
```
`data[0].configs[].overrideFlags` containing `EXCLUDE_TAX_CALCULATIONS` is **LEGACY** and is
ignored once an order shows `extra.isNewTaxCodeSetupEnabled=["true"]`.

VC (1891): tax-setup created 2026-08-19 8:10 PM PT maps FEES → "8.975% Tax" for RETAIL,
INTERNAL and WHOLESALE. `BATTFEE` active `taxConfigs = []` — the only fee at the store with 0
(SMOGTEST=1; WTAX/LOFDIS/RESTOCK/MISC/FEE=3). Alfa Romeo's `CABATT`/`BATTCORE` each carry 3
`{taxRegimeType:SALES_TAX, taxable:false, payType:CUSTOMER_PAY|WARRANTY|INTERNAL}` rows —
that's the correct shape.

**UI TRAP — there is no "not taxable" control on the Edit Fee page.** The page shows a section
`Taxes applicable on fee` → label `Sales Tax` → an **ant-select MULTISELECT whose options are
PAY TYPES only**: `CP - Default customer pay`, `CVSC - Vehicle Service Contract`,
`I - Default internal pay`, `W - Default warranty pay`. No taxable/non-taxable choice exists.
Worse, WTAX (which HAS 3 `taxable:false` rows in its record) renders the same empty "Select" —
so the screen **cannot distinguish 0 rows from 3 false rows**. Never tell Joe to "set it to not
taxable"; there is no such field. Read `pricingSetup.active[0].taxConfigs` by API instead.

### ⚠️ I gave Joe a wrong fix here — read this before proposing one (2026-08-24)

I told Joe to "add 3 non-taxable rows on the fee's pricing setup." He replied *"I don't see the
not taxable section, I only see the apply taxes on."* He was right; I had read the API record
shape and assumed a matching UI existed. **Do not translate an API field into a UI instruction
without opening the screen.**

What the screens actually show:
- `/core/fees/edit/<FEECODE>` → only the pay-type multiselect described above.
- `/parts/tax-code-setup` ("Tax Setup for Parts") → grid of **sale types × components**
  (Parts / Core Sale / Core Returns / **Fees** / Labour), rows Vendor/Retail/Wholesale/Internal
  plus any custom sale types. **This is where the fee tax comes from.** Click `Edit` (top-right
  of the grid, ~x1233,y219) to see every cell as a tax-code dropdown.

Two candidate fixes, and **I could not confirm which is correct — don't guess between them**:
1. Clear/blank the **Fees** cell in Parts Tax Setup. Simple, but it is **store-wide** — it
   untaxes EVERY fee at that store, not just the one in question.
2. Get the 3 `taxable:false` rows onto the individual fee (the WTAX/LOFDIS shape). Surgical and
   correct, but **no UI path was found that writes them** — they may be migration- or
   legacy-screen-written.

Correct move when you hit this: present both options with that trade-off stated, and recommend a
Tekion ticket phrased as *"under the new Parts Tax Code Setup, how do we mark an individual fee
non-taxable when the Fees component is mapped to a tax code?"*, citing a working/non-working
pair at the same store (VC 1891: WTAX exempt vs BATTFEE taxed). This is a NEVER-GUESS moment per
Joe's standing rule — say where the wall is instead of inventing a plausible click-path.

**Evidence scans that came back empty — don't repeat them.** BATTFEE was NOT found on any VC
parts sale order (600+ scanned, incl. `searchText:'battery'` and `'000915105'`) nor on 200 ROs
from `/tmp/vcros.json`. `partSaleDetails[].charges[]` and `assetCharges` were `[]` on every
order; `taxSummary.subTotalFees` was `0` everywhere. Recent VC orders also show
`taxSummary:{}` / `taxCodeGrid:[]` entirely on some CLOSED orders. So the fee's presence could
NOT be confirmed from order payloads — the config comparison (BATTFEE vs sibling fees vs Alfa
Romeo's CABATT/BATTCORE) was the only evidence that held up. Also: `searchText` + `siteId` filter
combos intermittently 400 with `"Requested URI does not represent any resource"`.

**Nav notes:** fee list `/core/fees` (VC = 26 fees), edit page `/core/fees/edit/<FEECODE>`,
parts tax grid `/parts/tax-code-setup` (Edit button ~x1233,y219).
If `/navigate` appears to land on `tekion.service-now.com`, the :9223 server is bound to the
wrong TAB — `curl /pages` then `POST /pages/select {"index":N}`. Do NOT loop retrying navigates
(see `persistent-browser-server` skill). After re-selecting a page, **re-verify
`currentActiveDealerId`** — the bound tab may be a different store (this session it was BT/1249
while the work was VC/1891).
Dealer switcher shows only 6 rows; `scrollIntoView` the target row BEFORE reading coords —
coords shift after scrolling (VC moved from y472 to y396) and a stale-coord click silently
opens the wrong thing or nothing.

**Safety:** opening the Parts Tax Setup grid in Edit mode is read-safe, but there is no
`Cancel` text node to click reliably — navigate away instead, and tell Joe explicitly that you
backed out without saving.
