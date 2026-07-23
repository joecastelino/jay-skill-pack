---
name: tekion-service-menu-setups
description: >
  Navigate to, read, and inspect Tekion Service Menu Setups (the service-menu
  builder where interval menus, tiers, tags, opcodes, included services and
  inspections are configured). Covers the non-obvious nav path, the page/tab
  structure, where free-text "notes"/tags live, and the headless storage_state
  harness that reaches it reliably. Use when asked to find/check/edit a service
  menu, a menu's tag/name, or "the last service menu".
triggers:
  - service menu setup
  - service menu setups
  - tekion service menu
  - find a service menu
trigger: service menu, service menu setup, service menu setups, menu builder, menu tier, menu tag, interval menu, included services, /ro/service-menu-setups
---

# Tekion Service Menu Setups

The **Service Menu Setups** module (NOT the customer-facing Service Menu viewer)
is where interval-based service menus are built: tiers, tags, opcodes, included
services, and inspections. This is distinct from Opcode Management and from the
`/ro/service-menu` *viewer* (which only lets you pick a vehicle to preview a
menu).

## Two different "Service Menu" things — don't confuse them

| Thing | URL | What it is |
|-------|-----|-----------|
| Service Menu **viewer** | `/ro/service-menu` | "SELECT VEHICLE DETAILS TO VIEW SERVICE MENU" — pick Make/Year/Model/VIN to preview. Has NO setup/list. The "SM" sidebar icon + the "SM Service Menu" Apps tile both land here. |
| Service Menu **Setups** | `/ro/service-menu-setups` | The builder/list of all interval menus. THIS is where menus are created/edited and where tags/names/notes live. |

## How to reach Service Menu Setups (the non-obvious path)

The Setups screen is NOT linked from the sidebar or the Apps tab. It lives under
the **Settings** tab of the nine-dots app launcher:

1. Click the **nine-dots app launcher** (top-left, `[class*='nine-dots']`).
2. Click the **Settings** tab (launcher has 3 tabs: Apps / Analytics / Settings).
   The tab is small text near `y<300`; clicking the wrong "Settings" string is a
   common miss — use Playwright `get_by_text("Settings", exact=True).first.click()`
   or a real `page.mouse.click()` on its bounding box.
3. In Settings, click the **"Service Menu Setups"** tile (abbrev **SS**). Exact
   label is plural: **"Service Menu Setups"**. Use
   `get_by_text("Service Menu Setups", exact=True).first.click()`.
4. You land on `/ro/service-menu-setups`. **You can also just `window.location.href`
   straight to `/ro/service-menu-setups` after the dealer switch** — once you've
   confirmed the URL it's far more reliable than re-clicking the launcher every time.

VERIFIED working June 2026 on Blackstone Toyota (dealer 1249).

## The Setups LIST page

Columns: **Interval | Vehicle/Collections | Status | Published Status |
Last Modified By | Last Modified Time | Actions(⋮)**. Default sort is **Last
Modified Time descending** (arrow on that header), so the TOP row = "the last
service menu" (most recently edited). Rows look like:
`10,000 mi  Toyota, GR Supra, 2021, A... +22  Active  Published  Joe Castelino  Wed Jun 17 2026`

Filters at top: Interval Type / Status / Published Status + Reset. Top-right:
**Create Menu** button. Each interval (5,000 / 7,500 / 10,000 … 200,000 mi) is a
separate menu row.

## The menu DETAIL view — tabs

Opening a menu (or the setup) shows a left sub-nav with these tabs:
**Service Menu | Tiers & Details | Intervals & Opcodes | Included Services |
Inspections | Settings**.

- **Service Menu** tab: the intervals table (read-only-ish overview).
- **Tiers & Details** tab: THE free-text fields. Has Make selector
  ("Toyota, Scion") + Tiers selector ("Basic, Value, Premium") and three tier
  columns, each with: **Menu Name** (e.g. Basic/Value/Preferred), **Tag**
  (free text — e.g. "Factory Recommended", "Blackstone Suggested Services",
  "I Love My Toyota-For those who LOVE their Toyota's"), and **Driving Condition**
  (Normal/Severe checkboxes). Cancel / **Save** buttons bottom-right.
- **Intervals & Opcodes / Included Services / Inspections / Settings**: per-area
  config.

**Where a "note" lives — TWO places (verified June 2026):**

1. **Tag / Menu Name** (Tiers & Details tab) — free-text descriptive fields
   (e.g. "Factory Recommended", "Blackstone Suggested Services"). Visible by
   reading input VALUES on that tab.

2. **THE NOTEPAD = per-vehicle-row "Vehicle Row Notes" (the real "note" feature).**
   This is what a user means by "the notepad in the menu." It is NOT a tab and NOT
   on the list page. Reach it:
   - On the Setups LIST, open the **⋮ (3-dot) actions** at the FAR-RIGHT of a row
     → menu shows **Edit | Duplicate | Deactivate** → click **Edit**. Lands on
     `/ro/service-menu-setups/edit/<menuId>` ("Edit Menu - 10000 mi").
   - The edit view has a **Menu Included Services** table; EACH row has small
     action icons including a **notes icon** (`class*='icon-note'`).
   - Real-mouse-click that notes icon → a **"Vehicle Row Notes"** panel opens with
     a **GENERAL NOTES (n)** list. Each note = author + role + dealer + timestamp +
     body (e.g. "GAS" by Joe Castelino, Jan 20 2026). The free-text note the user
     typed lives HERE, scoped to ONE vehicle row.
   - CRITICAL: the notepad is **per row**, so a note is on ONE specific
     make/model/year row of ONE interval menu. Searching tabs / innerText will
     NOT find it — you must open the row's notes icon.

If a search across tabs finds nothing, before brute-forcing: the note is most
likely in a **Vehicle Row Notes** notepad (open the right row), OR it wasn't
**Saved**, OR it's on a **different interval menu**. Ask the user which interval
+ which vehicle row rather than opening all ~40 menus × N rows. To grind it
automatically: for the target menu, Edit → iterate every row's notes icon →
read the GENERAL NOTES body → match.

## Canonical KB + video workflow (Tekion official docs — KB0010550 / KB0010538 / KB0010834 + Loom)

Verified against Tekion's own Knowledge Base PDFs AND the official Loom walkthrough
"Create and Manage Service Menu Setups" (Emily Shaw, transcript June 2026, saved at
`~/tekion-kb/`). This is the authoritative create/edit/pricing flow.

**LIVE NAV (from the Loom, fastest path):** App Grid (top-left) → **Settings** tab →
scroll to **Services** section → **Service Menu Setups** tile. FASTER: use the
**search bar at the top of the Settings panel** and type "service menu setups" → click
the tile. (This search-bar shortcut beats hunting/scrolling — verified in the video.)

**Nav path (official):** `App Grid > Settings > Service Settings > Service Menu Setups`.
(Confirms the launcher→Settings tab path above; "Service Settings" is the section,
"Service Menu Setups" is the tile.) Permission required: Service Menu Setups Edit
(`Roles > Permissions > Service > Service Menu`).

**Two service-menu types:** Factory menus (3rd-party data source / OEM) vs Custom
menus (built from scratch or modified factory menus). SCP = Service Catalog Pro
enables custom menu creation.

**Create Menu flow:**
1. `Create Menu` (top-right). To edit: kebab (⋮) beside menu → `Edit`.
2. **Select Intervals** section: `Interval Type` (Time / Distance), `Distance (Miles)`,
   `Base System Interval` (usually = Distance; determines which services/inspections
   pull in). The 'i' tooltip: base-system mileage applies to all dealer-make trims
   with no specific vehicle override.
3. **Menu Included Services** — add vehicle groups (rows): Make, Model, Year, Trim.
   - Trim: `Select Vehicle Trim` → Trim Details modal → filter by Engine Liter/
     Cylinder/Aspiration/Doors/Body Type/Transmission/Fuel/Drive/Sub Model/Body
     Class → choose **All trims (incl. future)** or **Specific trims** → Save.
   - Row actions: Expand (configure services/inspections/pricing), Drag handle
     (reorder), **Notes icon** (the Vehicle Row Notes notepad — see above), Copy,
     Delete.
   - **OVERRIDE PRIORITY (critical):** the **most specific** override wins; if a
     vehicle matches multiple groups, the **BOTTOM-MOST applicable** row takes
     priority over those above. Order rows accordingly.
4. **Expand a row** → `Menu Configuration`: **System + Overrides** (system menu +
   your additions) or **Custom** (only your selections). + `Base System Interval`.
5. **Modify System Services / Add Services / Modify System Inspections /
   Add Inspections**: pick Service/Inspection Name, choose tiers + driving condition
   (Normal/Severe), or `Apply to all Tiers`. Kebab → Exclude/Delete to remove.
6. **Menu Price** (`Price Type` dropdown):
   - **Sum of Services** — total of each individual service's labor amount (per-tier
     dropdowns lock to Sum of Services).
   - **Custom** → choose: *Sum of Services* / *Total Menu Price* (set $ per tier+
     condition) / *Total Labor + Parts Price* (set labor $ and parts $ separately).
   - **Total Menu Price** — fixed $ per condition. Shown price = entered price if
     actual sum is lower; if sum is higher, shows menu price as long as effective
     discount can be reduced from total labor; if discount > total labor, labor→0 and
     menu price = total parts price.
   - **Total Labor + Parts Price** — menu price = labor $ + parts $ entered.
7. **Labor Hours** (`Hours Type`): **Sum of Services** (auto) or **Menu Labor Hours**
   (set hours per tier+condition, to the hundredth). NOTE: Menu Labor Hours do NOT
   affect price — they only drive reporting (effective labor rate, etc.).
8. `Save` (draft) or `Publish` (make available).

**To change labor price on an existing maintenance-package menu (KB0023271):**
Service Menu Setups → Service Menu → find the interval → **kebab (far right)** →
expand the overrides → edit Sum of Service / Total Menu Price / Total Labor+Parts.

**Tiers & Details tab (SCP, KB0010538):** Up to **3 tiers** (Basic, Value, Premium).
Makes dropdown ('All' checkbox) + Tiers dropdown. Per tier: **Menu Name** (defaults
to tier name), **Tag** (displays under menu name on the RO — e.g. "OEM Recommended",
"Best Value"), **Driving Condition**.

**Customer-facing Service Menu VIEWER (KB0010834, `/ro/service-menu`):**
`Apps > Services > Service Menu` → enter VIN or YMM+trim → pick mileage interval
(angle brackets `<` `>`) → `Select Package`. Tier defaults: **Basic→togglable,
Value→Normal, Premium→Severe**. Uncheck individual services to drop them (price
updates). `Choose Parts` at bottom shows parts per service (uncheck to remove).
`Compare Mileage Intervals` toggle (must pick Package Type). Eye icon hides pricing.
GOTCHA: a job added via service menu **cannot be split**.

## Reading field values reliably

`document.body.innerText` does NOT include input values. To capture Menu
Name/Tag values, read inputs explicitly:
```js
document.querySelectorAll('input,textarea,[contenteditable]').forEach(e=>{
  const v = e.value!==undefined ? e.value : e.textContent;
  // walk up ~4 parents to find the nearest label/[class*=label] for context
});
```
Search text AND input values when hunting for a note:
```js
let blob=document.body.innerText;
document.querySelectorAll('input,textarea').forEach(i=>{blob+='\n[INPUT]'+(i.value||'');});
```

## Auth + harness (use headless storage_state, NOT :9223)

Reach this screen with a HEADLESS Playwright browser built from
`storage_state` — the persistent :9223 server's cookie/localStorage injection
fails for Tekion's SPA route guard (bounces through /login which wipes
localStorage). See the `persistent-browser-server` and `tekion-autonomous-login`
skills. Sequence:

1. `login.py` (reuse-if-alive) — if the resulting headless page renders the LOGIN
   FORM (`/Username/.test(body.innerText)`) the saved session is stale
   server-side; run `login.py --force`. NOTE `--check`/`REUSED`/`ALIVE` only
   reflect the JWT exp, not server acceptance — a "live" file can be a dead
   session.
2. Headless context: `browser.new_context(storage_state=".tekion-storage-state.json")`,
   `page.goto(BASE+"/home", wait_until="domcontentloaded")`, sleep ~9s.
3. Verify auth: body contains "Welcome back" and NOT "Username".
4. **Switch dealer in the SAME run** (each subprocess starts at default BC/1251):
   click `[class*='dealerSelect']`, then click the dealer-name leaf in the
   `.ant-popover-inner-content` portal; confirm `localStorage currentActiveDealerId`.
   BT=1249, SCT=876, etc.
5. `window.location.href = BASE+'/ro/service-menu-setups'`, sleep ~7s, read.

Working probe scripts written this session (templates):
`/home/itadmin/tekion-auth/reach_smsetups.py` (launcher→Settings→tile, captures
URL), `dump_tier_fields.py` (dumps Tiers Menu Name/Tag values), `scan_all_tabs.py`
(hunts a string across every tab incl. input values).

## PROGRAMMATIC MENU BUILD via :9223 (verified BT 160K rebuild, July 2026)

Full working recipe for building a menu's vehicle row + Add Services list headlessly.
Reference implementation artifacts: `/home/itadmin/bt-menu-build/` (160K Tony rebuild).

### APIs (in-page fetch with the standard ARC_NA header set + tekion-api-token)
- **Menu list**: GET `/api/service-module/u/opcode/service-menu/list` — response too big
  for one /eval (200k truncation); refetch in-page and return a projected map. GOTCHA:
  `miles` is null on older menus — use `intervals:["160000"]` (string array) to find the
  interval. Store to `window.__menus`.
- **Menu detail/baseline**: GET `/api/service-module/u/opcode/service-menu/<menuId>` —
  save this BEFORE editing (revert path). `menus:[]` empty = pure SYSTEM menu, no custom rows.
  After Save, re-GET and stash to `window.__saved`; verify `menuStatus:"DRAFT"` and walk
  `menus[0].servicesMetaData.services[].tierMappings` (packageType BASIC/VALUE/PREMIUM ×
  drivingCondition NORMAL/SEVERE, enabled bool) to confirm exactly what got checked.
- **Included-service → opcode mapping**: GET `/api/service-module/u/opcode/service/<serviceId>`
  → `{name, opcode, serviceType, status}`. THIS is how you learn which opcode a menu service
  fires. KEY INSIGHT: menus do NOT reference à-la-carte opcodes — stores keep a parallel
  menu-opcode family (BT = `SM*` prefix: SMALIGNMENT, SMCABIN, SMBFF…). Map Tony-style
  opcode lists (4ALIGN, CABIN) to their SM cousins via this endpoint before building.
- **Opcode search**: POST `/api/service-module/u/opcode/search` — body key is `searchText`
  (NOT `searchTerm`/`query`, those return unfiltered results); full body
  `{pageInfo:{start,rows},searchText,searchFields:["OPCODE"],sort:[...],filters:[]}` works.
  Search-list hits do NOT carry pricing fields.

### Reading the Add Services dropdown's full option list — React fiber walk
The service-name dropdown filters by SERVICE NAME (not opcode; typing an opcode = "No Match
Found"), options are client-side. Get all of them without typing: from the
`#ADDED_SERVICES_NAME_0` node, find the `__reactFiber$*` key, walk `fiber.return` up ~25
levels until `memoizedProps.options` is an array → `window.__opts` (448 entries at BT;
`{value:<serviceId>, label, type:SYSTEM|CUSTOM}`). Filter `type!=='SYSTEM'` for the 42
custom services.

### Filling the row builder
- **Edit URL via pushState** bounces to "Geez looks like we made a wrong turn" — click
  the `Retry` button (`/click {text:"Retry"}`) and it lands correctly on
  `/ro/service-menu-setups/edit/<id>`. (Full goto would wipe hooks; pushState+Retry keeps them.)
- **Make** = react-select `#makeId_<n>` (id is on the INPUT here) → click, then `/click {text:"Toyota"}`.
- **Model/Year** = `ant-dropdown-trigger ro_vehicleOverrideT*` divs (NOT react-selects).
  Click trigger → portal dropdown has an "All" item with 88/48 checkboxes → click "All" →
  NO Apply button; dismiss by toggling the SAME trigger again.
- **Trim** = `#trim_0` input → opens Trim Details modal; "All trims (including future trims)"
  radio is default; click modal `Save`.
- **Expand row caret**: `/click` by selector does NOT expand it — dispatch real
  `MouseEvent('mousedown'/'mouseup'/'click')` at the caret's box center via
  `document.elementFromPoint`. Expanded body innerText gains "Menu Configuration".
- **Type into service-name input**: `#ADDED_SERVICES_NAME_<n>` is a DIV — the real input is
  `div.querySelector('input')` (same id, nested). Native value-setter throws
  `Illegal invocation` in this eval bridge and the :9223 /type endpoint DOUBLES text on
  react-select inputs. WORKING method: `inp.focus(); document.execCommand('selectAll');
  document.execCommand('delete'); document.execCommand('insertText', false, txt)`.
  Wait ~2s, then options render as visible `[class*="option"]` leaves; match innerText
  exactly (case-insens), tag `data-jay='pick'`, `/click` it. Picking appends a fresh blank
  row (`Select` placeholder) automatically — find the next blank by
  `innerText.trim().startsWith('Select')`.
- **Tier checkboxes per service row**: `div.closest('.rt-tr')` → its 4 checkboxes sorted by
  x = [Apply-to-all-Tiers, Basic/Normal, Value/Normal, Severe]. New rows default ALL CHECKED
  (1111). Clicking Apply-all clears everything; then click the one you want. Idempotent
  normalizer: read states, click only mismatched boxes (skip index 0), re-read to verify.
- **Save**: tag the bottom `Save` button by exact innerText (Save x≈88 / Cancel x≈1060 /
  Publish x≈1166) — NEVER Publish. Success toast "Service menu saved successfully";
  menuStatus flips PUBLISHED→DRAFT (draft coexists with published version).

### Pitfalls specific to this build
- `execute_code` caps at 50 tool calls — a 18-service add loop @ ~3 calls each blows it
  mid-batch. Chunk to ≤7 services per script and re-scan filled rows between chunks.
- STALE `data-jay` tags accumulate — clear all (`[data-jay]` removeAttribute) at chunk start.
- /eval responses truncate at 200,000 chars AND terminal output JSON breaks near 8k —
  summarize server-side in the page, never return raw big JSON.
- **Tiers & Details (Menu Name/Tag) is GLOBAL across all interval menus** — renaming tiers
  for one pilot interval renames every menu at the store. Flag before touching.
- There is NO per-service "required/locked" checkbox in the row builder (2026-07). If a
  locked-base-tier behavior is requested, it isn't here — don't guess; ask.

## MASS-SUPPRESS a factory service across ALL vehicle rows (verified SCT 120K booster, 2026-07-03)

Use case: a wrong factory line (e.g. `Replace brake booster vacuum pump.` TEK02110102,
worth $2,320.03/tier) must be removed from EVERY vehicle row of an interval menu.
Mechanism per row: add the service to **Modify System Services** then uncheck all its
tiers (suppress). Reference run: SCT 120K menu id `6942c218df61bd08cf55cf69`, 20 rows.

### ⚠️ CRITICAL PITFALL — batched edits are SILENTLY DROPPED on Save

Editing many rows (expand → add → uncheck → collapse, repeat) and clicking **one Save
at the end** persists ONLY the FIRST row's change. The success toast fires, Publish
succeeds, but a fresh quote is UNCHANGED — total silent data loss, no error anywhere.
**Correct procedure: SAVE ONCE PER ROW, while that row is still expanded**, then
collapse and move to the next. Each save toasts "Service menu saved successfully".
After all rows: hard-reload the edit page and re-verify a sample of rows (booster row
present + all 4 checkboxes false) BEFORE Publish. Then Publish (with user's go) and
verify with a fresh throwaway quote.

### Per-row recipe (:9223 /eval)

1. **Expand row i**: carets are `.icon-caret-down` (visible-filtered, index = row).
   Plain `.click()` on the wrapper NO-OPs — dispatch real
   `MouseEvent('mousedown'/'mouseup'/'click')` at the caret's rect center.
   Verify exactly ONE visible "Modify System Services" header exists after expand.
2. **Idempotency check**: if the target service name already appears as a visible
   leaf (`innerText.trim()===name`), skip (row already done on a previous pass).
3. **Open the MSS add-row dropdown**: first visible leaf with text `Select` BELOW the
   MSS header's y (sort candidates by y, take [0]).
4. **Type the service name**: the dropdown input id is `SYSTEM_SERVICES_NAME_0` but
   that id is on a DIV — grab `.querySelector('input')` inside it, tag it
   `data-jay`, then `/type {selector,text}`. (Native value-setter throws
   `Illegal invocation` in this eval bridge.)
5. **Pick the option by EXACT text** — beware near-duplicates: `Replace Brake Booster
   Vacuum Pump` vs `Replace brake booster vacuum pump.` (trailing period = the factory
   one). Match trim()=== exactly.
6. **Uncheck**: find the service-name leaf's y; all checkboxes within ±14px of that y
   are the row's boxes ([Apply-to-all-Tiers, tier1, tier2, tier3]). Clicking the
   checked master unchecks everything; verify all 4 read false.
7. **SAVE NOW** (bottom Save button by exact innerText), wait for toast, THEN collapse.

### Row-count gotchas
- Vision on a screenshot under-counts rows (only sees above the fold) — count
  visible `.icon-caret-down` elements instead (SCT 120K = 20).
- The LAST row may be an empty template row (no MSS section, "No rows found"
  everywhere) — `hdr=0` from the open-select probe identifies it; skip it.

### Verify via quote — interval rail is a horizontal CAROUSEL
On the quote's Service Menu tab only ~3 interval cards render at once. scrollTop
jiggling does NOTHING (it's not a vertical list). Click the right-arrow **button**
(`.icon-right-arrow-thin` → `.closest('button').click()`) repeatedly (~5x to reach
120K) until the target card's text appears in body.innerText, then MouseEvent-click
the card. Read `Package OpCode : TEKxxxxx` + `Services (N)` + prices to confirm.
Booster result: Basic $4,162.38→$1,842.35, Basic+ $4,637.68→$2,317.65,
Signature $4,969.68→$2,649.65 (Services 11→10).

## VEHICLE-SCOPED CUSTOM PRICE/HOURS row (verified SCT 90K, 2014 Camry, 2026-07-03)

Full recipe in skill **tekion-menu-custom-price-row**. Key experiential facts:
- **Tier ID trap**: header shows `Basic | Basic + | Value | Signature | Premium` but the 3 real
  input columns are `BASIC_NORMAL_0` (BNM), `VALUE_NORMAL_0` (**= displayed "Basic +" = VNM tier**),
  `PREMIUM_SEVERE_0` (Signature/Severe).
- **Gating**: per-tier selects are `disabled` until the master `PRICE_TYPE_0`/`HOURS_TYPE_0`
  react-select is set to **Custom**.
- **These react-selects open ONLY via keyboard**: `inp.focus()` + dispatch
  `keydown/keyup ArrowDown (keyCode 40)` on the hidden input. mousedown on `-control`,
  /mouse coord clicks, and singleValue clicks ALL silently fail here.
- Per-tier choice `Total Menu Price` / `Menu Labor Hours` spawns an
  `input.ant-input-number-input` in that cell — set via native value setter + input/change/blur.
- `VALUE_NORMAL_0` id is NOT unique (Menu Price row + Labor Hours row + hidden dups at negative
  y + ant-checkbox-inputs elsewhere) — always filter by `offsetParent!==null`, y-range, and
  exclude `className.includes('checkbox')`.
- Untouched tiers stay "Sum of Services" → only the customized tier/vehicle changes (quote-verified:
  Basic $374.08 unchanged, Basic+ = exactly the custom $469.88 / 2.40 hrs on TEK90000VNM).
- Quote VIN decode needs an **Enter keydown** in `input#vin` after typing — /type alone doesn't fire it.

## Menu-wide SETTINGS page (/ro/service-menu-setups/settings) — verified BT 2026-07-04

Direct URL `/ro/service-menu-setups/settings` (also the Settings tab in the left sub-nav).
Per-STORE settings, own Save button (bottom-right, ~x1166). Contains:
- **Interval Type(s)** / **Default Menu Type** (Distance)
- **Add Menu Services as separate operations** toggle (the explode-menu toggle)
- **Allow unchecking of inspections** / **Only show VIN specific Service menu intervals** toggles
- **Unchecking of Service → "Allow percentage of services to be un-selectable"**: three
  `input.ant-input-number-input` fields (Premium / Value / Basic, left→right at y≈507).
  This caps how much of a menu package an advisor can UNCHECK on a quote/RO — 50 = only
  half the services can be deselected ("can't select all"), 100 = all can be unchecked.
  Set via native value-setter + input/change events (values render as "100.0"). Joe set
  BT to 100/100/100 on 2026-07-04 (was 50/50/50).
- **Pricing** + **Labor Hours** radio groups (remove-at-original vs effective markup/markdown
  percentage when Expected Menu Price/Hours vs Sum of Services differ)
- **Service Menu Parts Pricing** (maintain parts price on add/remove) toggle
Save → toast "Settings saved successfully". Verify persistence with a hard reload.

## FULL MENU-CONFIG AUDIT via API — cross-dealer, zero UI clicks (verified BC 2026-07-07)

Fastest way to audit an entire store's menu setup (used for the Ruben/BC meeting prep).
Works from the :9223 session even while the browser sits on a DIFFERENT dealer — the
menu list/detail endpoints honor overridden dealer headers (unlike opcode/search which
needed a UI dealer switch):

```js
const H = Object.assign({}, window.__H, {dealerId:'1251','tek-siteId':'-1_1251'});
const list = await (await fetch('/api/service-module/u/opcode/service-menu/list',{headers:H})).json();
// list too big for one /eval return — stash to window.__menus, return projections only
const d = await (await fetch('/api/service-module/u/opcode/service-menu/'+id,{headers:H})).json();
```

Field paths that matter (menu detail `data`):
- `intervals` (string array; `miles` often null), `menuStatus` (PUBLISHED/**DRAFT** = unpublished
  pending edits — check `modifiedTime`, BC had a DRAFT sitting 2 YEARS on its #2-volume interval),
  `status` (ACTIVE), `modifiedTime` (epoch SECONDS).
- `menus[]` = vehicle rows. **Row scope is NOT in make/models/years fields (all null/empty) —
  it's in `menus[].parameters[]`**: `{parameter:MAKE|MODEL|YEAR|TRIM, value:{...}, allValues}`.
  TRIM value carries `standardTrimFilterDetails` (FUEL_TYPE/DRIVE_TYPE/BODY_TYPE/ENGINE_CYLINDER…)
  + `trimSelectionType`. This is the untruncated row scope the editor DOM can't show.
- Per-row pricing: `menus[].priceConfig.priceTierMappings[]` =
  `{packageType BASIC|VALUE|PREMIUM, drivingCondition NORMAL|SEVERE, menuPriceType
  TOTAL_MENU_PRICE|SUM_OF_SERVICES, value}` (value in DOLLARS here, not cents).
  Hours: `laborHourConfig.laborHourTierMappings[]` (`laborTimeInSeconds`).
- Per-service tier enablement: `menus[].servicesMetaData.services[].tierMappings[]`
  (`enabled` bool per packageType×condition) — count these to see what each tier includes.
- `menus:[]` empty / rows=0 = pure SYSTEM menu (SCP dynamic pricing, zero store control —
  the SCT-$449-rotation risk class). BC: 25 of 45 menus were zero-row legacy (untouched
  since 2023) and had ZERO sales — all sales came off the customized 7.5K ladder.

PITFALL: `/api/service-module/u/opcode/service-menu/settings` and `/tier/details`
return 500 "Token doesn't exist or is invalid" — wrong paths, NOT an auth problem
(list/detail work fine in the same eval). Tiers & Details / menu settings must be read
in the UI.

Audit checklist that produced real findings (cross-ref config vs the store's menu-sales
masters, e.g. `bc-menu-closed-mtd-MASTER-*.json`):
1. DRAFT menuStatus on high-volume intervals (unpublished edits, unknown live risk).
2. Stale `modifiedTime` on fixed TOTAL_MENU_PRICE rows (price freeze).
3. Duplicate/conflicting rows: same parameters-scope, different prices (bottom-most wins).
4. Zero-row system menus still visible in the viewer rail (deactivate or enable
   "Only show VIN specific Service menu intervals").
5. Tier price ladder vs sold tier mix (small Basic→Value gap + Basic-heavy mix =
   presentation problem, not config).

## Persistent-browser (:9223) /click schema — coords are REJECTED

The persistent browser server's `/click` endpoint accepts **ONLY** `{selector}`,
`{text}`, or `{ref}` — **raw `{x,y}` coordinates return HTTP 400** (`"One of
selector, text, or ref is required"`). Verified June 2026 reaching the 60K menu Edit.
To click a position-only target:
- `/eval` to locate the element (e.g. the row's `.icon-overflow` 3-dot), then
  `el.setAttribute('data-jay','<tag>')`, then `/click` with
  `{selector:"[data-jay='<tag>']"}`.
- Or dispatch a real `MouseEvent('click',{bubbles:true})` inside `/eval`.
- Dropdown menu items (Edit/Duplicate/Deactivate) click reliably with `{text:"Edit"}`.

Working row→Edit recipe (60K menu): find the `60,000 mi` `tr`, grab its
`.icon-overflow`, tag + `/click` selector → dropdown opens → `/click {text:"Edit"}`
→ lands `/ro/service-menu-setups/edit/<menuId>`.

## Reading vehicle-row scope is HARD — chips are truncated, selections not in DOM

In the menu Edit view, each vehicle group row shows a collapsed summary chip like
`Toyota, All Models, All Y... +18` and `All trims selected`. The **full Model list
and Trim filter are NOT in the DOM** — react-select multiValue labels return empty,
no `title` tooltips, innerText only yields stray GR Supra rows. So you **cannot**
scrape "which row a given vehicle (e.g. an AT Camry) falls into" from the editor DOM.
To determine row/trim membership reliably, either (A) open each candidate row's
**Trim Details** modal in the editor and check trim inclusion (read-only; careful on
Published menus — don't change anything), or (B, preferred for a Published menu —
zero edit risk) read the menu config JSON from the service-menu-setups API by menuId,
which returns every group's exact model/year/trim filter + included opcodes untruncated.

## Pitfalls

- **Don't guess sub-paths** like `/ro/service-menu/settings`, `/setup`, `/list` —
  they're SPA non-routes; the app just shows the previous page (looks like a
  redirect). The ONLY real setups URL is `/ro/service-menu-setups`.
- **Settings-tab click is flaky headlessly** — sometimes the launcher stays on
  the Apps tab even after a "successful" click (DOM shows Apps tiles, no "Service
  Menu Setups" text). Verify by testing for setup-tile text
  (`/Service Menu Setup|Labor Pricing|Opcode Management/`) before clicking the tile;
  retry the Settings click up to 3×, or skip the launcher entirely and use the
  direct `/ro/service-menu-setups` URL.
- **Vision can see what the DOM dump missed** — the launcher panel renders in a
  portal; `browser_vision`/`vision_analyze` on a screenshot is a good cross-check
  when an `/eval` query returns empty.
- A note/tag not found anywhere usually means **not Saved** or **wrong interval** —
  ask, don't brute-force.
- **The interval cell renders as an ODOMETER (per-digit animated spans)**, so the
  "10,000 mi" link is NOT a single clickable leaf and direct text-match clicks on
  it fail silently (innerText shows stray digits "0 1 2 … 9"). To open a menu, use
  the **⋮ 3-dot → Edit** path instead: get the row's bounding box, real-mouse-click
  ~18px from its RIGHT edge to open the actions dropdown, then click "Edit". The
  table is wide (~1180px); compute `row.right - 18`, don't guess a fixed x.
- **The Notepad needs a REAL mouse click** on the `icon-note` element (React
  ignores synthetic `.click()`); find its bounding box via `class*='icon-note'`
  and `page.mouse.click(cx, cy)`. The panel content lands in a drawer/modal — read
  `[class*='drawer'],[class*='modal'],[class*='note']` innerText, not just body.
- **storage_state "not bounced to /login" is a FALSE POSITIVE**: a stale session
  keeps the URL on `/home` but renders the LOGIN FORM. Always assert the body
  contains "Welcome back" / lacks "Username" — if it shows Username, run
  `login.py --force` (the saved JWT can be valid but server-rejected).

Working probe scripts from the notepad-hunt session (BT, June 2026):
`/home/itadmin/tekion-auth/open_3dot.py` (3-dot dropdown → actions),
`edit_and_find_notepad.py` (3-dot → Edit → edit URL), `scroll_edit.py` (finds
`icon-note` in the edit view), `open_notepad.py` (clicks notes icon, reads
"Vehicle Row Notes" panel).
