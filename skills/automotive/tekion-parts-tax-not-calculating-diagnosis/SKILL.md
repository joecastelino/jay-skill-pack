---
name: tekion-parts-tax-not-calculating-diagnosis
description: Diagnose "sales tax isn't calculating / tax is $0" on Tekion Parts Sales Orders (counter sales), especially for CUSTOM sale order types like ONLINE RETAIL. Finds whether the store was migrated to the NEW Parts Tax Code Setup and whether a sale type is missing from the saved tax-code grid. Use when a Parts Manager reports missing tax on SOs.
---

# Tekion Parts Sales Order — tax not calculating

## When to use

A Parts Manager (e.g. Glade @ SCT) says "tax on sales orders isn't working / tax is $0".
Classic signature: SOME sale types tax fine, one specific type (usually a CUSTOM sale order
type like `ONLINE RETAIL`) shows $0 tax, and it started on a specific date.

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

## Step 4 — The fix

**Parts → Settings → Tax Setup for Parts** (`/parts/tax-code-setup`) → **Edit** → on each
missing sale-type row, **explicitly re-select the tax code in every component cell** (Parts,
Core Sale, Core Returns, Fees, Labour) *even though they already appear filled* → **Save**.

Verify: re-`GET /api/parts-settings/u/tax-setup` and confirm the sale type now appears in
`saleTypeTaxSetup` with a real `taxCodeId`. Then create a test SO of that type and confirm
`taxCodeGrid.length == 5`.

⚠️ This is a live financial-control change — **get Joe's explicit go before saving.**

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
6. **`page.from` pagination on order search works**, but `searchText:"<orderNo>"` is the
   fast way to jump to a specific order and get its numeric `id`.
7. Dollar fields in `saleAmount` / `tax.saleTaxAmount` are **CENTS**. `taxSummary.subTotal`
   is **DOLLARS**. Both appear on the same object — do not mix them.

## Verified reference values (SCT / dealer 876, 2026-08-20)

- Migration timestamp: `1787195464151` = 8/19/2026 8:11 PM PT
- Tax code `10% Tax` id = `6a867038a5537a692d78fdef`, effective 8/19/2026 8:10 PM PT
- Setup record id = `876_part_settings_tax_setup`, siteId `-1_876`
- Custom sale order types at SCT: `ONLINE RETAIL_RETAIL` (parent RETAIL, dept
  "06 - Online Parts Sales"), `ONLINE WHOLESALE_WHOLESALE` (parent WHOLESALE)
- Exposure at detection: 6 orders / $250.10 / ~$25 tax
