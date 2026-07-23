---
name: tekion-opcode-api
description: >
  Read, audit, and VERIFY Tekion opcode override rows directly from the backend
  REST API using the session's own auth token. This is the AUTHORITATIVE source
  of truth — the override UI grid frequently renders wrong/empty even when rows
  exist in the backend. Use to get the true committed row count before a batch,
  detect incomplete (part-less) rows, and confirm persistence after saving.
triggers:
  - opcode override audit
  - verify opcode rows
  - opcode pricing api
trigger: >
  Tekion API, opcode API, verify overrides, audit overrides, override row count,
  committed rows, override read-back, RACF row count, confirm persistence,
  service-module opcode endpoint, override JSON schema
---

# Tekion Opcode Override — Backend API Read / Audit / Verify

**The single most important reliability tool for override batch work.** Instead of
trusting the flaky override UI grid (which silently drops parts and lies about row
counts), read the committed override rows DIRECTLY from Tekion's REST API with the
session's own auth token. This is the AUTHORITATIVE source of truth — the UI grid is
just a (buggy) render of this data.

**Companion skills:** `tekion-opcode-overrides` (the UI write workflow this verifies),
`tekion-autonomous-login` (auth).

---

## Endpoint

```
GET https://app.tekioncloud.com/api/service-module/u/opcode/<OPCODE>_<DEALERID>/override/<TYPE>
```
- `<OPCODE>` e.g. `RACF`; `<DEALERID>` from `localStorage.currentActiveDealerId`
  (Stevens Creek Toyota = `876`) → entityId is `RACF_876`.
- `<TYPE>` is `PARTS` or `LABOR` — **UPPERCASE, plural**. `PART` / `parts` return
  500 "Given Override Type doesn't exist".

Returns `{ data: [ {overrideResponse:{...}}, ... ], status:'success' }`.

---

## Required Headers (MUST send all — `credentials:'include'` alone gives 500)

The app uses custom headers, not cookies. A manual `fetch` omitting these returns
500 "Token doesn't exist or is invalid".

```js
const H = {
  "Accept":"application/json, text/plain, */*",
  "applicationId":"ARC_NA", "clientId":"web",
  "dealerId":localStorage.getItem('currentActiveDealerId'),    // "876"
  "locale":"en_US",
  "original-tenantid":"americanmotorscorporation",
  "original-userid":localStorage.getItem('__user_id'),
  "productIds":"ARC", "program":"DEFAULT",
  "roleId":localStorage.getItem('currentActiveRoleId'),
  "subApplicationId":"US",
  "tek-siteId":localStorage.getItem('currentActiveSiteId'),    // "-1_876"
  "tekion-api-token":localStorage.getItem('t_token'),          // the JWT
  "tenantname":"americanmotorscorporation",
  "userId":localStorage.getItem('__user_id')
};
const r = await fetch('https://app.tekioncloud.com/api/service-module/u/opcode/RACF_876/override/PARTS',{credentials:'include',headers:H});
const j = await r.json();
```

### Most robust: capture the EXACT headers the app uses
Token/role/site auto-correct if you hook the app's own requests:
1. On the opcode LIST page, hook XHR + fetch (store requests in `window.__reqLog`).
2. SPA-navigate to the edit page (the hook survives `history.pushState`+popstate but
   NOT a full reload).
3. Click Overrides → Labor (fires one override GET) → read `window.__reqLog[0].hdrs`.
4. (LABOR fires on tab open; PARTS you then fetch manually with those headers.)

---

## Override Row JSON Schema (per `data[].overrideResponse`)

```
{ id, entityId:"RACF_876", order:<int 1..N>, entityType:"OPCODE",
  parameters:[
    {parameter:"MAKE",  value:{makes:["toyota"]},           allValues:false},
    {parameter:"MODEL", value:{models:["RAV4"]},            allValues:false},
    {parameter:"YEAR",  value:{years:["2018","2017",...]},  allValues:false},  // STRINGS, desc
    {parameter:"TRIM",  value:{trims:[], trimSelectionType:"ALL"}, allValues:false} // ALL = All trims
  ],
  override:{ type:"PARTS",
    customParts:[{ id:null, partId:"M_TMNA_87139YZZ81", partNumber:"87139YZZ81",
                   partName:"87139-YZZ81 - ELEMENT, AIR REFINER", overriddenQuantity:1, uom:"ea",
                   customerPay:{overriddenPrice:30.88,...}, warrantyPay:{...}, internalPay:{...} }],
    sourceParts:[], customerPartPricingEnabled:true, eligibleForPartPreparation:true }}
```
- **partId**: `M_TMNA_` + partNumber with dashes stripped (`87139-YZZ81`→`M_TMNA_87139YZZ81`).
- **partName**: `"<dashed-number> - ELEMENT, AIR REFINER"` (cabin) / `"<num> - FILTER, AIR A/C"` (88568).
- **A row with EMPTY `customParts:[]` is INCOMPLETE** — vehicle saved but the part dropped.

---

## Audit Snippet — run BEFORE adding (prevents dupes, finds bad rows)

```js
const rows = j.data.map(rec => {
  const o = rec.overrideResponse, p = o.parameters, g = n => p.find(z=>z.parameter===n)?.value;
  const yrs = (g('YEAR')?.years||[]).map(Number);
  return {
    order: o.order,
    model: (g('MODEL')?.models||[]).join('|'),
    yspan: yrs.length ? Math.min(...yrs)+'-'+Math.max(...yrs) : '(none)',
    nParts: o.override.customParts.length,
    part: o.override.customParts.map(x=>x.partNumber).join(',')
  };
}).sort((a,b)=>a.order-b.order);
console.table(rows);

// Find INCOMPLETE rows (vehicle saved, part dropped):
const incomplete = j.data.filter(r => !r.overrideResponse.override.customParts.length);
```

**Use this:**
- **At session START** — get the true committed floor. Reconcile against any prior
  claimed total before adding rows (claimed counts are often wrong; reload+API is truth).
- **AFTER each save / every ~8 rows** — confirm the row count incremented AND the new
  row's part/price are present. In-session UI count is NOT proof.
- **To find rows needing repair** — `customParts:[]` rows need their part re-attached.

### Verified baseline (2026-06-04)
Stevens Creek Toyota RACF = **42 committed rows** (orders 1-42), ending RAV4 2006-2018.
(Earlier sessions falsely claimed 43/46; reload+API proved 42.) When testing other stores,
read THAT store's RACF (its own dealerId) to establish its own baseline — overrides are
per-dealer.

---

## Write Endpoint (CAPTURE before trusting — do not guess for production data)

The create/update call is a non-GET to the override path. Before any programmatic write:
1. Arm an XHR+fetch hook for **non-GET** to `/override` BEFORE saving.
2. Do ONE real-click save through the UI (or re-save an incomplete row).
3. Record method + URL + body. Replay that EXACT shape for remaining rows.

⚠️ A synthetic Update click only fires the **base-opcode PUT** (`/api/service-module/u/opcode/RACF_876`,
~2894 bytes, NO override rows) — it does NOT carry override rows. The real override-save
request shape still needs a clean real-click capture before programmatic writes are safe.
This is LIVE pricing across a production DMS — verify every write by re-reading the PARTS
endpoint and confirming the new row's part+price. Direct API writes (once the shape is
captured) are NOT discarded by SPA reload, unlike unsaved UI rows.

---

## Dealer ID Reference
- Stevens Creek Toyota = `876` (siteId `-1_876`). Read other stores' IDs from
  `localStorage.currentActiveDealerId` after switching dealers in the UI.

---

## Opcode LIST / SEARCH endpoint (full catalog dump — VERIFIED 2026-06-12)

To scrape ALL opcodes at a store (e.g. "all TEK opcodes in the maintenance category"),
use the internal search endpoint with the SAME custom headers as the override reads:

```
POST https://app.tekioncloud.com/api/service-module/u/opcode/search
GET  https://app.tekioncloud.com/api/service-module/u/opcode/serviceTypes   (id → name map)
```

**The body MUST be the UI's exact shape** — discovered by hooking XHR via
`context.add_init_script()` (response listeners see NOTHING — service worker swallows
them — but a request hook on `XMLHttpRequest.send` captures bodies; scroll the
`/ro/opcode` list to trigger cursor pages):

```json
{"pageInfo":{"start":0,"rows":50},
 "searchText":"TEK",
 "sort":[{"order":"DESC","field":"createdTime"}],
 "filters":[],
 "nextPageToken":null,
 "searchFields":["OPCODE","DESCRIPTION","CONSUMER_SCHEDULING_NAME"]}
```

**Pitfalls (each burned a round-trip):**
- `pageNumber`/`pageSize`/`page`/`offset`/`start`/`from`/`limit`/`size` are ALL
  IGNORED — every variant returns the same first 20 rows. Only `pageInfo.rows` (max 50)
  and the cursor work.
- Cursor = **`data.nextPageToken`** from the response (base64). `data.key` is always
  null — do NOT loop on it (you'll fetch page 1 forever).
- `searchTerm`/`query`/`opcode` as search params are ignored; **`searchText`** works
  (matches opcode prefix + description).
- Run the fetch from page context (`page.evaluate`) with a logged-in storage state;
  dealer comes from `localStorage.currentActiveDealerId` — assert it before scraping.
- **External urllib ALSO works (verified 2026-07-21):** plain Python urllib POST to
  the search endpoint with captured axios headers (e.g. `/tmp/tekion_put_headers.json`,
  swap `dealerId` + `tek-siteId: -1_<dealer>` for the target store) succeeds — no
  browser needed for batch existence/price/parts audits. 48 opcodes @ 0.3s pacing ≈ 20s.

**Record fields that matter:** `opcode`, `category`, `serviceTypeIds[]`, `status`
(ACTIVE/IN_ACTIVE), `description`, `opcodeType`, labor times, `parts`.

**Reusable full-catalog dump script (verified 2026-07-03, 4 stores):**
`/home/itadmin/tekion-reports/opcode_pull.py <code>` — switches dealer via the UI
pill through :9223, verifies `currentActiveDealerId`, paginates the search endpoint
in-page (direct fetch with the 15-header set WORKS from an authenticated page — no
XHR-hook fallback was needed), accumulates in `window.__cat` keyed by id (10 pages
per /eval call to stay under timeouts), writes `<code>-opcodes-full.json` +
`<code>-menu-opcodes.json` (opcodeType===SERVICE_MENU && ACTIVE) to
`~/tekion-reports/data/`. Dealer-picker leaf names (AMG group, exact innerText):
Blackstone Toyota, Stevens Creek Volkswagen, **Volkswagen of Clovis** (NOT
"Volkswagen Clovis"), Alfa Romeo of San Jose, Stevens Creek Toyota, Toyota of
Lancaster, Blackstone Chevrolet Cadillac. If the picker popover is already open
from a failed attempt, don't re-click the pill (it toggles closed) — the script
checks for visible rows first. Baselines 2026-07-03: BST 1374 total/213 menu-active,
SCVW 1363/112, VWC 1387/221, ARSJ 1132/212.

## Batch opcode EXISTENCE + PRICE audit (verified BT 2026-07-02)

To audit a list of opcodes (\"which of these 25 exist, and what's each priced at?\") —
e.g. before a menu build — loop the search endpoint in-page with `searchFields:["OPCODE"]`
and filter to EXACT match (`hits.find(x=>x.opcode===c)`; the search is prefix/fuzzy, so
\"CABIN\" also returns CABINX etc.). ~300ms pause per call; 25 opcodes ≈ 10s, no 429s.

**Pricing lives in `hit.priceDetails[]`** — one entry per payType:
```json
{"payType":"CUSTOMER_PAY","laborRateType":"FLAT","flatPrice":143.44,
 "pricePerHour":null,"taxable":true, ...}
```
- Flat-rate opcode: `laborRateType:"FLAT"` + `flatPrice` = the CP labor price in
  DOLLARS (NOT cents — the internal /api/service-module returns dollars, unlike the
  public OpenAPI which is cents).
- `flatPrice` is LABOR ONLY. Menu/quote total = flatPrice + attached parts prices.
  So an opcode showing labor $44.10 vs the manager's sheet $89.95 is usually NOT a
  mismatch — the delta is parts.
- **Part prices ARE in the search hit (verified BC 2026-07-12 — no separate lookup
  needed):** `hit.parts[]` items carry `unitPrice` / `customerPayUnitPrice` /
  `warrantyPayUnitPrice` / `internalPayUnitPrice` + `quantity`. All-in price =
  `cpFlat + Σ(customerPayUnitPrice × quantity)`. Generic placeholder parts
  ("Oil Filter", "Engine Oil") have `partNumber:null` but still carry unitPrice;
  a truly unpriced part has `unitPrice:null`. Don't re-read the edit page for a
  price audit — the search hits are sufficient.
- Labor hours: `laborTimeInSeconds/3600` (also `customerLaborTimeInSeconds`).
- Run via :9223 `/eval` with `awaitPromise:true`; stash results in `window.__x` and
  pull with a second eval `JSON.stringify(window.__x)` (avoids the 20K eval truncation
  on big payloads — or slice if >16K).

Working template: `/home/itadmin/bt-menu-build/audit_opcodes.js` (existence+status)
— pair with a second pass extracting `priceDetails`/`laborH`/`nParts` per hit.
Real example output: BT audit of Tony's 25 menu add-ons → 21 exist ACTIVE
INDIVIDUAL_SERVICE, 4 missing (44K, FOBBATTERY, ROTATEBAL, HVCOOLANT).

**⚠️ Existence audits — exact-match is NOT enough (burned 2026-07-02, BT):** opcodes
are case-sensitive strings (`44k` ≠ `44K`) and stores accumulate near-duplicate
cousins (`FOBBATT` vs `FOBBATTERY`, `BALANCE`/`ROTATE` vs `ROTATEBAL`,
`HVCOOLANTEXCH` vs `HVCOOLANT`). Before declaring an opcode MISSING: re-search with
`searchFields:["OPCODE","DESCRIPTION"]` using description keywords (e.g. "FOB",
"BALANCE", "FUEL ADD") and compare case-insensitively. Creating a verbatim new opcode
when a cousin exists produces the "(2)"-duplicate clutter Joe hates — report cousins
and let Joe pick reuse+reprice vs create.

**⚠️ \\\"Maintenance category\\\" semantics (Joe's usage):** the `category` enum
(MAINTENANCE/BRAKES/POWER_TRAIN/SERVICE_MENU/...) is NOT what Joe means. TEK menu
opcodes are `category: SERVICE_MENU`. Joe's \"maintenance category\" = **serviceTypeIds
contains the \"Maintenance Service\" service type** (`5fcef4d21e9d980008c6ce52` at SCT —
re-read per store from `/opcode/serviceTypes`). SCT baseline 2026-06-12: 2,066 total
opcodes, 1,371 TEK*, of which **316 are Maintenance Service** (1,015 Service Catalog,
40 Toyota Care). Frozen snapshots in `~/tekion-reports/data/sct-tek-*.json` — used to
make report membership immune to service-type moves in Tekion.
