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
| **Pay Types Setup** (Service 3.0 — split payers from pay types) | App Grid → Settings → Service Settings → Pay Types Setup, or direct `/ro/paytypes`. "Add New" (top-right) → Base Pay Type (Customer/Internal/Warranty) + 3-letter Notation + Name + Default Payer + Associated Payers (multi-select). Base C/I/W pay types can't be deactivated, only custom ones. Requires "View Pay Types Setup" permission (Roles → Permissions → Service → RO). Step 1 of the Service 3.0 manager setup chain: Pay Types → Tax Codes → Vehicle Groups → Labor Pricing → Opcode pay-type config → Customer Mgmt defaults → Fees → GLAM cash holding account. Verified 2026-08-14. |
| Service Menu Setups | sidebar **SM** → Service Menu |
| **Service Settings** (pre-invoice rules, flags, holds, approval settings) | ✅ `/service/settings/ro-settings` (verified TL 2026-07-15; hash anchors work e.g. `#PRE_INVOICE`). ⚠ `/ro/service-settings` & `/ro/settings/service-settings` render BLANK. Reachable via App Grid → search "Service Settings". Left-nav sections incl. Pre-Job Completion / **Pre-Invoice** / Recommendation Addition Rules. **Block invoice until recs reviewed** = Pre-Invoice rule "Pending Recommendations Error" (RO-level): check Applicable + radio **Error** (Warning only warns). Condition statuses = DRAFTED, SUBMITTED, RETURNED_TO_TECH, REVIEWED, SENT_TO_CUSTOMER, CUSTOMER_APPROVED (which rec statuses block). Table = react-table `.rt-tr`/`.rt-td` divs; radio click via /mouse on live rect; **Submit** btn bottom-right. |
| Dispatch Settings | ✅ **`/ro/dispatch-settings`** (direct nav verified TL 2026-08-24). Tabs: General Settings / Skills / Technician Skills / RO Priority / RO Hold. General Setup contains **"Auto Assign Technician to Added Job"**, "Choose between Multiple Technician on RO", "Only Assign if Technician has matching Skills", "Auto assign Technician same as Last Service from Return RO", "Auto Assign Technician who submitted Recommendation", "…for previously Deferred services", "Allow Dispatch across teams", Reserve Technician, Max RO Idle Time. ⚠ `/dse/dispatch-settings` bounces to /home; `/service/settings/dispatch-settings` and `/ro/settings/dispatch` render blank shells. |
| **Profile Settings / Notification Settings** (per-user notification toggles) | ✅ **`/userProfile`** (verified 2026-08-24). Tabs: My Profile / General Preferences / **Notification Settings**. Or: avatar at bottom-left of left rail (~30,660) → ant-popover → **"View Profile Setting"** (~165,619). Notification Settings tab leaf ≈(530,155). ⚠ `/core/profile-settings` and `/core/user-profile/notification` **silently land on a Fee edit page** (`/core/fees/edit/...`) — assert `location.href`. Full event list dumpable from `GET /api/notificationServiceV2/u/user/preference/<dealerId>` — see skill `tekion-notification-settings-audit`. |
| **Labor Time Guide** (OEM warranty labor times, per-vehicle lookup) | App Grid → \"Labor Time Guide\" tile (shows under Recently Used Apps once used) or direct nav `/ro/labor-time-guide`. Search by VIN (most reliable) or Make/Year/Model cascading selects. **NO download/export button exists in the UI** — it's a live per-vehicle OEM feed, not a static file/report. Full API (`POST /api/service-module/u/vps/labor-time/all`, paginated, auth-trap same as other internal APIs — must drive via UI/XHR-hook, raw fetch 500s) + bulk-export approach in skill `tekion-labor-time-guide`. |

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

### Coupons (Core)
| Workflow | URL / Nav |
|----------|-----------|
| **Coupon Management** (service/parts discount coupons) | ✅ **`/core/coupons`** (list) · create `/core/coupons/create` · edit `/core/coupons/edit/<base64(couponCode)>`. ⚠ `/core/coupon-management` renders BLANK. Reach via App Grid → search "coupon". Full form mechanics = skill `tekion-coupon-management`. Coupon eligibility gated at OPCODE level ("Coupon Eligible" toggle, KB0026638). SCT GL convention: Labor→4402 / Parts→4702 SLS-ASM DISCOUNT. |

### Vehicle Inventory
| Workflow | URL / Nav |
|----------|-----------|
| Vehicle Inventory (VI) | sidebar **VI** (prefer OpenAPI for data — see `tekion-vi-api-migration`) |
| **Vehicle Inventory Setup** (Stock Type, General, Pricing, Account Setup, **Stock# Rules**, Option Sheet, Others, Mobile VI) | ✅ **`/vi/visettings`** (verified SCT 2026-08-17). ⚠ Page ALWAYS defaults to the "Stock Type" tab on load/reload — must click the "Stock# Rules" tab text every time you arrive. Stock# Rules = ordered condition rows (Stock Type \| Stock Sub Type \| Make combo) → sample stock# pattern (e.g. `C210001`, `S5000`); last row is usually a broad non-factory-brand catch-all with 70+ Makes. Edit via row's pencil icon (`.editBtn` / `icon-edit`) → modal w/ Make multi-select (find by `document.querySelectorAll('.ant-select-selection--multiple')[2]`, NOT position — index 0/1 are Stock Type/Sub Type). Modal can render taller than viewport — scroll `.ant-modal-wrap.ant-modal-centered` to `scrollHeight` before locating the Make search input, else you click/type into the wrong field. **TWO SAVES required**: modal's own Save (inside `.ant-modal-content`) THEN the page-level Save button (bottom-right, outside modal) — skipping either loses the change. Verify via full remount (nav to `/home` then back + re-click Stock# Rules tab), not same-render DOM. Full walkthrough (Mercedes-Benz missing from SCT's catch-all Make list, trade-ins got wrong stock#) = skill `tekion-vi-stock-number-rules-fix`. |

### Reporting
| Workflow | URL / Nav |
|----------|-----------|
| Report Builder | sidebar **RB** |
| Reports | sidebar **R** |

### Accounting (VERIFIED SCT 2026-08-21)
| Workflow | URL / Nav |
|----------|-----------|
| Chart of Accounts | ✅ `/accounting/chartOfAccounts/list` (sidebar **CA**). 1,331 accounts at SCT. |
| **Journal Entries** | ✅ **`/accounting/journalEntry/list`** (camelCase; `/accounting/journalentry/list` also works). Status tabs at y≈146: All / Draft / **Error** (x≈281) / Pending Approval. Virtualized table — parse `body.innerText`, no `.ant-table-row`. Open a row by `/mouse`-clicking the ID leaf cell at x≈344. |
| JE detail (auto-posting) | `/accounting/journalEntry/transactionId/<txnId>/dealerId/<dealerId>/transactionType/AUTO_POSTING/edit` |
| **GL Account Transaction Mapping** | ✅ **`/accounting/glaccountmapping/list`** (ALL LOWERCASE). Left-nav accordion: Variable Operations (New/Used Vehicles, F&I, Receivables, Payables) · Fixed Operations (Services, Part & Accessories, Purchase Orders, Warranty Credit, **Others**) · Payment Receipts (Variable Ops, Fixed Ops, Tekion Pay) · Payroll. Cash-holding accounts live under **Others → Fixed Operations (Other)**. |
| Financial Statements | App Grid → Financial Statements (sidebar **FS**) |
| **Setup Fields (Cost Center Setup)** | ✅ **`/accounting/setupFields`** (camelCase, VERIFIED SCT 2026-08-24). Tabs: GL Accounts Setup / Journal Setup / **Cost Center Setup** (leaf at ≈582,158). Cost Center Setup has 4 categories in a 2×2 grid: **Parts Sale Order - Internal** (caret ≈112,260) · **Repair Order - Internal** (caret ≈**720,260**) · **Repair Order - CP Insurance/Warranty Split** (≈112,342) · **Repair Order - Warranty** (≈720,342). `+` icons at x≈610 / x≈1218 on each row. This is where RO-Internal cost centers (the "PDI", "Safecat 5450", "RENTALS 8160" names) are created/renamed. |
| Distribution Accounts | ✅ `/accounting/distributionAccounts/list` |
| Accounting Global Settings | App Grid → Settings tab → Accounting Settings group |

⚠ **Accounting dead-end URLs (all tested, all waste turns):**
`/accounting/journal-entry`, `/accounting/journal-entries`, `/accounting/glam` → **silently redirect to chartOfAccounts/list** (looks successful — ALWAYS assert `location.href` after navigate).
`/accounting/journal/list`, `/accounting/glAccountMapping` (camelCase) → blank page.
`/accounting/accountSetup`, `/accounting/accountingSettings`, `/accounting/settings/glAccountMapping` → bounce to `/ro/quotes`.
`/gl/journal-entry` → bounces to `/home`.
`/accounting/setup-fields`, `/accounting/setupFields/costCenter`, `/accounting/costCenter/list`, `/accounting/cost-center/list`, `/accounting/costCenterSetup/list`, `/accounting/settings/costCenter`, `/accounting/gl-account-mapping` → **all silently land on chartOfAccounts/list**. Only `/accounting/setupFields` and `/accounting/glaccountmapping/list` work.

**App Grid coords (verified 2026-08-24, 1280-wide viewport):** nine-dot launcher = **(30,31)**. Tabs Apps / Analytics / **Settings** / Store render at y≈145 — the "Settings" leaf is a `DIV` whose `textContent.trim()==='Settings'` with `children.length<=1` (a strict `children.length===0` filter finds NOTHING — that exact filter cost several turns). Under Settings → *Recently Used Settings*, **GL Account Mapping** tile ≈**(472,278)**. When leaf-text selectors come back `[]`, fall back to `/screenshot` + `vision_analyze` for coords — that's what unblocked it.

Diagnosing JEs stuck in Error → skill **`tekion-journal-entry-error-diagnosis`**.

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
- **`:9223` API shapes (easy to get wrong):** `/eval` takes `{"js": "..."}` NOT `{"expression":...}`.
  `/type` REQUIRES a `selector` — `{"text":"..."}` alone returns **HTTP 400**. Screenshot is
  **GET** `/screenshot` → `{"screenshot":"<base64>"}`; **POST /screenshot is 404**. There is no `/status`
  endpoint (use `/health`).
- **Expandable page-level search fields start at width 0** — click the `.icon-search` magnifier next to
  them first, then `/type` into the now-visible input. A width-0 input silently swallows typing.
- **A "successful" navigate can be a redirect.** Several Tekion URLs 200 into a *different* screen
  (e.g. bad accounting URLs land on chartOfAccounts). Always read back `location.href` after
  `/navigate` before trusting the page.
- **Left-nav accordions / virtualized lists:** coordinates shift as sections expand. Always
  `scrollIntoView({block:'center'})` the target element, RE-READ `getBoundingClientRect()`, then
  `/mouse` click. A stale coord clicks the previously-selected item and you'll misread the panel as
  belonging to your target.
- **Editable vs read-only rows:** in editable (Draft/Error) records, dropdown cells are react-selects
  (`[class*="tekion-select-b62m3t-container"]`, innerText `"Select"` when empty) and values live in
  `input.value`; in posted/read-only records the same table renders as plain text. If a value-extraction
  JS returns empty arrays, you're probably on a read-only record — read `innerText` instead.

## Global Security Settings (session auto-logout, MFA, IP) — verified via KB 2026-07-23
- Nav: App Grid → Settings → Core Settings → **Global Security Settings** tile → Default Policy → Configure Policy tab → left pane **Session Management**
- Session Management (Auto Logout) is SPLIT: Web vs Mobile+iPad sections.
  - Mobile+iPad: Session Timeout Duration 1/5/10/15/30 days (default 30); Inactive timeout 4h–72h (default 48h). Floor = 4h.
  - Web: same duration options; Inactive timeout 5min–72h (default 24h).
- Must click **Save and Activate** (bottom-right) for policy to take effect.
- PER-DEALERSHIP policy — no copy mechanism between stores; configure each of the 7 individually.
- Requires "Edit Security Settings" permission (Roles → Permissions → General → General).
- KB0022240 (session mgmt how-to), KB0022401 (dealer security FAQ). Distilled: /home/itadmin/tekion-kb/distilled/mobile-auto-logout-session-management.md
