# Tekion DMS — Navigation Site Map

**Purpose:** Direct URL/navigation reference so Jay can jump straight to any Tekion
workflow without hunting through menus. All paths verified live in the
persistent-browser (`:9223`) session. Base = `https://app.tekioncloud.com`.

> **HOW TO USE:** Most SPA screens are reachable by `POST /navigate {url}` directly —
> no clicking through the App Grid. Always be on the RIGHT DEALER first (see Dealer
> Switching). After navigate, `time.sleep(4-6)` for React to render.
> Mirror copy (non-skill access): `~/tekion-reports/TEKION-SITEMAP.md`.

---

## 0. Session / Auth (do this FIRST every session)

| Step | How |
|------|-----|
| Check persistent browser up | `curl -s http://localhost:9223/health` → `{"status":"ok"}`. If `exit 7`, restart server (see `persistent-browser-server` skill). |
| Check auth | navigate `/home`; if URL bounces to `/login` OR body contains "Username" → NOT authed. |
| Login | username `jcastelino@scvolkswagen.com` → Enter → password `<TEKION_PASSWORD>` → Enter → 6-digit OTP. **React form: use `/press` Enter, not JS click.** |
| OTP | Gmail IMAP `jcastelino@americanmotorscorp.com` / `<GMAIL_APP_PASSWORD>`, `[Gmail]/All Mail`, subject "Tekion-Login OTP". Baseline count BEFORE password submit, poll for count increase. |
| Token check | `localStorage.getItem('t_token')` → HAS_TOKEN means authed. |

**Default dealer after login = BC Blackstone Chevrolet (1251). ALWAYS switch to the target store before navigating.**

---

## 1. Dealer Switching (CRITICAL — do before any store-specific nav)

```js
// 1. open switcher
document.querySelector('.root_dealerSelect_container__eXjxN2P5EN')?.click();
// wait ~2s for portal, then 2. click the store
const inner = document.querySelector('.ant-popover-inner-content');
for (const el of inner.querySelectorAll('li,div,span,[role="option"],[class*="item"]')){
  const t=(el.textContent||'').trim();
  if(t.startsWith('ST') && t.includes('Stevens Creek Toyota')){ el.click(); break; }
}
// verify: localStorage.getItem('currentActiveDealerId') === '876'
```
Items render as `STStevens Creek Toyota` (code+name, no space). Match by prefix + name.

### Dealer ID map
| Code | Store | dealerId |
|------|-------|----------|
| BC | Blackstone Chevrolet (DEFAULT) | 1251 |
| BT | Blackstone Toyota | 1249 |
| ST | Stevens Creek Toyota | **876** |
| SV | Stevens Creek VW | **826** (verified 2026-07-15; OpenAPI `americanmotorscorporation_826_0`) |
| TL | Toyota of Lancaster | 1092 |
| AR | Alfa Romeo SJ | _(tbd)_ |
| VC | VW Clovis | _(tbd)_ |

---

## 2. App / Module URL Map

Sidebar 2-letter codes (left rail): RO, EH, A, C, EO, FS, PO, SP, SM, DS, CM, OM, VI, CA, RB, US, SO, R.

### Service / Repair Orders
| Workflow | URL / Nav |
|----------|-----------|
| Repair Orders (RO module) | sidebar **RO** |
| **RO detail page** | `/ro/repair-orders/<documentId>/jobs/<jobId>` (verified SV 2026-07-15). ⚠ `/ro/service/<docId>/details` renders BLANK — don't use. Easiest path when you only have the RO#: navigate `/ro`, type the RO# into the global "Search here..." box (`input.ant-input`, placeholder `Search here...`) + Enter → result card "RO #<num> \| Tag #..." → `/mouse`-click the card (deepest element matching `RO #<num>`; note innerText match may need the full-page search since the text spans nested nodes — collect candidates with `.includes('RO #<num>')` sorted by innerText length). documentId/jobId come free from OpenAPI `repair-orders:search` + `/jobs`. |
| Opcode Management (V2) | `/ro/opcode` (list) ; edit `/ro/opcode/edit/<OPCODE>` |
| Labor Pricing (store labor RATES: CP/Warranty/Internal/Grid/menu rates) | `/ro/labor-pricing` — table: Name, Rate, Price code, Status + "Add Labor Pricing" btn. (NOT `/ro/labor-price-guide`, `/ro/rate-setup`, `/ro/settings` — those render blank.) Verified BC 2026-07-12. |
| Service Menu Setups | sidebar **SM** → Service Menu |
| **Service Settings** (pre-invoice rules, flags, holds, approval settings) | ✅ `/service/settings/ro-settings` (verified TL 2026-07-15; hash anchors work e.g. `#PRE_INVOICE`). ⚠ `/ro/service-settings` & `/ro/settings/service-settings` render BLANK. Reachable via App Grid → search "Service Settings". Left-nav sections incl. Pre-Job Completion / **Pre-Invoice** / Recommendation Addition Rules. **Block invoice until recs reviewed** = Pre-Invoice rule "Pending Recommendations Error" (RO-level): check Applicable + radio **Error** (Warning only warns). Condition statuses = DRAFTED, SUBMITTED, RETURNED_TO_TECH, REVIEWED, SENT_TO_CUSTOMER, CUSTOMER_APPROVED (which rec statuses block). Table = react-table `.rt-tr`/`.rt-td` divs; radio click via /mouse on live rect; **Submit** btn bottom-right. |
| Dispatch Settings | App Grid → Dispatch Settings |

### Service Scheduling (VERIFIED 2026-06-24 from KB webinar)
| Workflow | URL / Nav |
|----------|-----------|
| **Scheduling Settings** | App Grid → Scheduling Settings. Tabs (work TOP-DOWN): General · Service Advisors · Shops · Transportation · Capacities · Consumer Scheduling · Summary. **GOLDEN RULE: lowest ceiling that gets hit = the cap.** |
| **Scheduling Settings direct URL** | `/dse-v2/scheduling-settings` (tabs: `/transportation`, `/summary`, ...). App Grid search "Scheduling" → tile under Digital Service Experience 2.0 Settings. Guessed URLs bounce to /home. |
| **Lyft ride radius** | Transportation tab → Lyft row → Restrictions table → "Ride distance / Less than / N mi" → Save → Summary → Run Scheduler. (Verified SCT 2026-07-14, 10→15 mi.) |
| Apply changes immediately | **Summary tab → "Run Scheduler"** button (else changes wait for the overnight scheduler ~midnight–2 AM). |
| Shops ordering | **Most-restrictive shop at TOP** (system reads top-down, first match wins); default shop = catch-all. |
| Parts-on-appointment | General → **"Notify parts department of appointments"** toggle (ON = all parts-opcodes; or set a day-range window). |
| Global holidays | Dealer Configuration → **Dealer Details** (grayed-out holidays only editable there). |
| Concierge / mobile write-up | **ONLY via the mobile write-up app** (Tekion ARC). Captures digital signature when customer not present (night-drop/PUDO/tow). Assign Porter → CP link texted → customer signs → RO# created. Non-appt: set transportation type = Concierge. |

### CRM Process Automation (VERIFIED 2026-06-24 from KB webinar)
| Workflow | URL / Nav |
|----------|-----------|
| **Process Automation** | App Grid → Process Automation tile. Top filter defaults to **Active**. Type filter = Rules vs Processes. Left-nav = trigger filters (Newly checked in, Lead updated, Lead stage updated, Lead custom stage updated). |
| Edit a process | Click name → pencil (rename) or 3-dots → Edit. **Advanced View required when branches exist.** **YES=left/green, NO=right/red.** |
| 3-dots menu | Edit · Process Execution Log · Audit Log. |
| Save options | **Publish** (active) · **Save as Draft** (⚠ makes it INACTIVE — never on a live process) · Save as Template. |
| Reading the list | Active count = leads currently in; Run count = lifetime total. **Active(green) ≠ running** (zero counts = no leads flowing → check triggers). |

### Parts (VERIFIED 2026-06-23)
| Workflow | URL / Nav |
|----------|-----------|
| **Parts & Inventory** (parts list) | **`/parts/inventory/part`** |
| **Part Detail** | **`/parts/inventory/part/view/M_TMNA_<PARTNUM>/details`** (Toyota OEM prefix = `M_TMNA_`; strip dashes from part #, e.g. `044650R010`) |
| Part → Stocking Details | on the part view page, click left-nav text **"Stocking Details"** (sub-tabs: Basic, Stocking, Bin, Pricing, Linked, Additional all render on one scroll page) |
| Purchase Order (stock orders) | sidebar **PO**, or list URL **`/parts/purchase-order/list`** (~10s load, shows \"Loading...\" first). Status tabs w/ counts: All/Draft/Submitted/Invoiced/Partially Received/Received/Unpaid (each is a leaf `div/span`, click to filter). Table is virtualized (no `.ant-table-row`) — parse `body.innerText`: line === PO# then next 14 lines = columns: PO Number·Control Number·Invoice Number·Vendor·PO Amount·**PO Type** (`OEM Stock Order`=auto daily / `OEM Special Order`=VIN-special / `Vendor Stock Order`=non-OEM)·OEM·No. of Parts·Issued By·Date Created·**PO Status** (Draft=never submitted)·VIN·Est Delivery·Age·Invoice Status. The in-page \"Search here...\" box is unreliable (can jump to RO search) — filter by status tab instead. |
| Source Code (list) | **`/parts/source-codes/list`** — but direct URL renders blank; reach via App Grid (nine-dots) → search "Source Code" → click tile. Then click a code row → opens `/parts/source-codes/edit/<id>`. |
| **BRP/BSL & Phase-in (Stocking Parameters)** | Source code detail page → click **"Stocking Parameters"** tab → **"Edit stocking parameters"** button (bottom-right). Fields: No. of months to monitor, Best reorder point (Days), Best stocking level (Days), Phase-in/out/inactivation. NOTE: source-level BRP/BSL APPLIES to all parts in the source; a part's Stocking Details shows "-" for BRP/BSL when it inherits from the source (NOT a misconfig). Max 3 saves per 30 min. |
| Special Order Request (SOR) | Parts menu → Special Order Request. SOR tied to **customer number** (not VIN/phone). 3 create paths: Customer# ("C" id), Sales Order, Repair Order. Special-order PO **cannot exist without an SOR**. |
| **Parts Sales Order** (counter sales) | **`/parts/sales-order`** (nine-dots → Sales Order). **= the Caliber RO-dollars source** (no OpenAPI; browser scrape only). Create → customer → Sale Type (Retail/Wholesale/Internal) → add parts → Create → Modify→Invoice → Cashiering. Prepaid parts stay in inventory until Bulk Actions→Mark as Received. Core return = CM credit-memo. |
| **Parts RO Sales** (parts on ROs) | nine-dots → Parts RO Sales. Two tabs: **P&A** (Price & Availability = quote, NOT sold) and **Fulfillment** ("bill it and pull it" = approved → pull). Counterperson col blank = New Request. SOR oval: Red=not ordered, Orange=some ordered, Green=all ordered+received. |
| **Parts Receiving** | URL **`/parts/receiving/orders`** (⚠ NOT `/parts/parts-receiving` — that renders a blank shell forever; `/parts/receiving` redirects correctly). Tabs Orders\|Floats; right-side views Exception Reports / Receipt Transactions / **Shipments** (`/parts/receiving/shipments` = per-PO Order Qty vs Received Qty table); quick filters w/ live counts: All / Manual Receipt / **Orders Not Received** / Backordered / Cancelled / Cross shipped. ⚠ The lone download icon (x≈2296, off-viewport) exports the FLOATS csv (`partTrade/u/float/search/download`), NOT the orders table — harvest orders via XHR hook on `partTrade/u/purchase/search` (paginated 50/page, page 1 cache-served; see skill `tekion-parts-shipped-not-received-report`). Bulk fill vs one-by-one. **Create Manual Receipt** (enter Control Number) → ⚠ auto-creates a STOCK order. Float section: assign Source Code/Bin → Submit; row (…) = Receive to an Order / Remove from Float. Line dispositions: Backordered/Canceled/Cross-Shipped. **Labels can't print here — use Warehouse Management.** |
| **Default/Price config** | Settings → **Part Settings**: Default Pricing Setup, Price Codes, Price Breaks & Formulas (matrix; base = Cost/List/Trade/Comp/Warranty), Customize Price Setup. Pricing hierarchy (low→high): Source Code → default sale-type → Customer-Defined → Parts Kit/Flat → **Manual Override (king of kings)**. |
| Core return | **Core Management** app (NOT a credit PO). |
| **Parts Settings (General toggles)** | ✅ **`/parts/parts-settings`** (VERIFIED 2026-06-29). ⚠️ TRAP: `/parts/settings/parts-settings` renders BLANK (only top nav, ~107 chars) — wrong route, do NOT use. Tabs: **General Settings** · Print settings · PDF Configuration · Label Configuration. General Settings contains (top→bottom): Supersession Replacement Settings (incl. **Transfer Bins** radio = the ghost-bin root cause: \"Transfer the bin from old part\" vs \"Manually select the bin\"), Gross Profit Validation, Custom Sale Order Types, SOR Receiving, Parts RO Sales Settings (Fulfilment Logic), Quote auto-void, SOR Creation, Core Settings, OEM/Vendor PO Closing, **Negative On-Hand** (Stock Order Calc Logic: consider -ve qty vs treat as 0; **BSL Rounding Logic** = Round Up/Down/Nearest), Feature Settings, Material Return, Picklist, OEM PO submission. Bottom = Cancel / Save. |
| Other Parts Settings tiles (real routes, from KB deep-links) | Source Code `/parts/source-codes/list` · Price Codes `/parts/price-codes/list` · Price Breaks `/parts/price-breaks` · Priority Codes `/parts/priority-codes` · Manufacturers `/parts/manufacturer` · Return Reasons `/parts/return-reasons` · Void Reasons `/parts/void-reasons` · Default Part Pricing `/parts/default-part-pricing` · Adjustment Reasons `/parts/adjustment-reason` · Core Mgmt bins setup `/parts/core-management-setup/bins-setup` (Default Bin / Other Bins config only). |
| **\"Sell by Bin\" feature** | ⚠️ NOT in the visible store-level UI. Read the ENTIRE General Settings tab (`/parts/parts-settings`) 2026-06-29 — NO Sell-by-Bin toggle, also absent from Warehouse Mgmt + bins-setup. KB0010624 says \"Sell by bin feature must be activated. Found in Parts Settings,\" but it's almost certainly a **support-gated backend flag** (same pattern as Min/Max override needing support@tekion.com). Do NOT claim where it is — open a Tekion ticket to enable + confirm location. Needed to make a non-primary bin (e.g. 5005) sell/stock; NOT needed to merely clear a ghost-bin negative (that's a Bin Spot Check). |

#### Parts search (on `/parts/inventory/part`)
1. The table search box = `input.ant-input` with `placeholder="Type Here"` (the 2nd text input; tag it: `input.placeholder==='Type Here' → setAttribute('data-jaysearch','1')`).
2. `/click` the field → `/type` the part number → `/press` Enter.
3. Result appears as **row 1** in the table with a **blue part-number link** (rendered `04465-0R010` with dash). Click that link text (`el.textContent.trim()===formatted# && el.children.length===0`, also click `.closest('a')`).
4. Lands on the part view URL above.

#### Part Stocking Details — fields available (verbatim labels)
`Source Code` · `Stocking Status` (Non-Stock/Active/Inactive) · `Manual Order` (Yes/No) ·
`Total On Hand Quantity` · `Hold Quantity` · `On Order Quantity` · `Open Documents` ·
`Specify stocking parameters in` (Days/Quantity) · `Best Reorder Point (Days)` (BRP) ·
`Best Stocking Level (Days)` (BSL) · `Minimum Quantity` · `Maximum Quantity` ·
`Last Purchase Date` · `Last Sale Date`. Additional Details has `Material Return Indicator`,
`OEM min/max order qty`, `Classification Code`.

#### Parts internal data APIs (browser-replay, NOT OpenAPI — verified 2026-06-24)
All take the app's axios headers (`window.__H` = capture once via setRequestHeader hook on a real
XHR: tekion-api-token, roleId, userId, tenantname, dealerId, tek-siteId, original-userid/tenantid,
clientId, locale, program, applicationId, subApplicationId, productIds). Replay in-page with `fetch`.
| Data | Endpoint (POST) | Body | Returns |
|------|------|------|---------|
| **Per-part sales velocity** | `/api/wms/parts/u/inventory/utility/salehistory/groupByMonth` | `{partId:"M_TMNA_<PN>"}` (inventoryId ignored) | `{data:[{year,month(name),saleQty}]}` full monthly history |
| **Live on-order qty (BATCH)** | `/api/partTrade/u/purchase/parts/liveOnOrderQty` | bare ARRAY `["M_TMNA_<PN>",...]` (NOT `{partIds}`) | `{data:[{partId,quantity}]}` |
| # sale txns/mo | `/api/wms/parts/u/inventory/utility/noOfSales/groupByMonth` | `{partId}` | monthly txn counts |
| All source-code settings | `/api/parts/proxy/u/settings/source-code` (GET) | — | ALL 22 codes w/ stockingParam+demandCalc+phaseIn |
| Source-code part list (export) | `.icon-download1` click → `/api/media-v3/u/v2/presignedurls` → in-browser fetch xlsx | — | inlineStr xlsx |
Harvest at scale: in-page concurrent worker (conc=10) looping partIds, batches of ~200 per `/eval`.
12.6k parts velocity ≈ 4 min, on-order ≈ 30s. See `tekion-source-code-parts-scrub` for full method.

### Vehicle Inventory
| Workflow | URL / Nav |
|----------|-----------|
| Vehicle Inventory (VI) | sidebar **VI** (prefer OpenAPI for data — see `tekion-vi-api-migration`) |

### Reporting
| Workflow | URL / Nav |
|----------|-----------|
| Report Builder | sidebar **RB** |
| Reports | sidebar **R** |

### Accounting
| Workflow | URL / Nav |
|----------|-----------|
| Chart of Accounts | App Grid → Chart of Accounts |
| Financial Statements | App Grid → Financial Statements |

### Admin
| Workflow | URL / Nav |
|----------|-----------|
| Roles / Permissions | ✅ **`/core/roles`** (direct nav, verified 2026-07-10). Select role → `?role=<mongoId>` or `?role=<dealerId>_RoleName` (e.g. `1251_ServiceAdvisor`). NO duplicate-role action — clone via **Create Custom Role** modal + Role Template select. Full mechanics in skill `tekion-roles-permissions`. |
| User Setup | sidebar **US** |
| Employee Onboarding | App Grid → Employee Onboarding |

---

## 3. OpenAPI vs Browser — pick the right tool

- **Data reads (ROs, parts on-hand, vehicles, opcodes/labor $)** → OpenAPI, no browser.
  See `tekion-openapi-repair-orders`. Parts on-hand: `POST /parts-inventory:search {searchText}`
  (returns ONLY partNumber/description/brand/onHandQty — NOT stocking settings).
- **Stocking settings, min/max, source codes, phase status, ANY config edit** → browser only.
  The OpenAPI does NOT expose these. Use this site map.
- **Caliber RO dollars** → browser scraper (Sales Orders), see `tekion-pipeline-operations`.

---

## 4. React/SPA gotchas (apply everywhere)

- React inputs ignore JS `.click()`/`dispatchEvent`. Use `/press` Enter and `/type`.
- Ant Design dropdowns/popovers render in **portals** invisible to snapshot/vision/JS-query
  (dealer switcher, React-Select). Use the JS `.ant-popover-inner-content` pattern or vision+coords.
- The `browser_*` tool is a SEPARATE browser from `:9223` and is NOT logged in. Do ALL
  Tekion work through `:9223` HTTP API in `execute_code`. Use `vision_analyze` on a saved
  `/screenshot` PNG (write to `/tmp/...`, the sandbox can't see `/home/itadmin`).
- Sessions expire ~30 min idle / ~20h hard. Re-login when `t_token` missing.
