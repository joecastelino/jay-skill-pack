---
name: tekion-included-service-parts-override
description: >
  Build a vehicle-scoped PARTS override row on a Tekion menu-included opcode via
  Service Menu Setups → Included Services → Edit Service → Overrides → Parts,
  driven by the persistent-browser :9223 HTTP endpoints (/eval, /click, /type,
  /press). Covers the exact DOM (react-select Make, ant-dropdown checkbox
  Model/Year multi-selects, Trim Details modal), the verified click-paths, and
  the costly pitfalls (wrong /eval key, navigate-away row wipe, coordinate
  drift, disabled trim input). Use when swapping/adding parts on an opcode that
  lives INSIDE a service menu (e.g. BGCVTF CVT fluid → E-TAF for Corollas).
triggers:
  - included service parts override
  - service menu opcode parts override
  - edit service overrides parts
  - BGCVTF override
  - menu included opcode part swap
trigger: >
  included services, edit service, service menu parts override, menu-included
  opcode, BGCVTF, override parts row builder, service-menu-setups included-service,
  E-TAF override, CVT fluid override, /ro/service-menu-setups/included-service
---

# Tekion Included-Service PARTS Override (Service Menu Setups)

Swap or add a part on an opcode that is used **inside a service menu**, scoped to
specific vehicles. This is a DIFFERENT surface from Opcode Management
(`/ro/opcode/edit/`). For a menu-included opcode you do the override here, NOT in
Opcode Management, and you do NOT touch the mileage menu itself.

## ⭐ END-TO-END CHECKLIST (the whole skill set in one place)

The full BGCVTF case (SCT 90K Corolla Hybrid: wrong BG 303+31832 CVT fluid →
correct Toyota E-TAF) executed start-to-finish 2026-06-25, Joe-approved. Order:

1. **Identify the opcode + correct part FIRST (no browser).** Explode the menu in
   a quote to find the opcode (`tekion-quotes-menu-price-diagnosis`), then pull the
   CORRECT part/qty/price off the closed RO via OpenAPI
   (`tekion-openapi-repair-orders`). e.g. RO 565535 → 0888681986 "E-TAF,TE", qty 1,
   $155.93. NEVER invent the part — read it from the RO.
2. **Nav** to Service Menu Setups → Included Services → search opcode → kebab →
   Edit service → **Overrides** tab → **Parts** sub-nav → **Define Here**.
3. **Build the scope row:** Make → Model (multi-select) → Year → Trim (modal,
   CVT/transmission filter as needed). Match by LABEL not coordinate.
4. **Expand the row** (caret/chevron by selector) → the parts table appears with
   the inherited Default parts.
5. **Edit parts per Joe's direction:** either ADD the correct part on top (override
   precedence wins) OR DELETE the inherited defaults and add only the correct part
   (the BGCVTF case: delete 303+31832, add E-TAF). Confirm WHICH with the user.
6. **Set qty + price** on the new part (verify exact values from the RO).
7. **Save once** → URL flips `/overrides` → `/default` = success. Re-open
   Overrides → Parts to confirm the row persisted.
8. **🎯 RE-QUOTE TO VERIFY (the proof-of-fix loop — do this, it's the payoff).**
   Build a fresh quote for the exact VIN+mileage, select the affected tier, read
   the package TOTAL and the part behind the line. RECONCILE THE DOLLARS: the
   package total must drop by exactly (old parts $ − new part $). The BGCVTF case:
   $1,978.62 → $1,719.16 = **−$259.46** = ($415.39 old BG parts − $155.93 E-TAF). ✅
   And the CVT line now shows "0888681986 - Toyota EV TransAxle 1 ea $155.93", with
   303/31832 gone for this vehicle. A clean dollar reconciliation is the strongest
   proof to Joe that the override is live. See "RE-QUOTE VERIFICATION" section below.
9. **Apply to sibling tiers if needed.** The override is opcode-scoped, so it should
   carry to every tier using that opcode (e.g. Premium TEK90000PSM as well as Value
   TEK90000VNM) — re-quote the other tier to confirm, build a parallel override only
   if it doesn't carry.

**Companion skills:**
- `tekion-opcode-overrides` / `tekion-vehicle-override-row-builder` — the OTHER
  surface (Opcode Management grid). Different DOM/engine; don't conflate.
- `tekion-service-menu-setups` — nav to Service Menu Setups, Included Services tab.
- `tekion-quotes-menu-price-diagnosis` — explode a menu into opcodes to find which
  opcode/line carries the wrong part.
- `persistent-browser-server` / `tekion-computer-use` — the :9223 server.

## 🔍 PHASE 0 — RO INVESTIGATION (diagnose the wrong part — verified RO 565709, 2026-06-25)

Joe flags these as: **"RO <#> <interval> <PART CATEGORY> IS INCORRECT. CORRECT
PART# IS <PN>."** e.g. "565709 120K CABIN FILTER IS INCORRECT. CORRECT PART# IS
87139-YZZ81." Your job: find the OPCODE the wrong part hangs on, confirm the right
part, and propose the override. Do it via OpenAPI first (no browser, fast).

1. **Pull the RO** (`tekion-openapi-repair-orders`): `repair-orders:search` with
   `documentNumber IN ["565709"]` → `documentId` + OPCODE `tags` (e.g. the menu
   opcode `TEK120000VNM` shows in tags). Then `/repair-orders/{rid}/ro-vehicle` →
   VIN/year/make/model (the scope target).
2. **Walk jobs → operations → parts** on the menu op to see EVERY part behind the
   menu line. For each op, GET `.../jobs/{jid}/operations` then
   `.../operations/{oid}/parts`. Read `partNumber` + `partName`.
   ⚠️ **partName, NOT description** — `description` is usually null on RO part lines.
3. **☠️ DON'T CONFUSE FILTER TYPES.** A Toyota maintenance menu carries MULTIPLE
   filters behind one line. Verified on RO 565709's TEK120000VNM:
   - `17801YZZ01` = "17801-YZZ01 - ELEMENT SUB-ASSY, AI" = **ENGINE AIR filter**
   - `8713906030` = "**87139**-YZZ81 - ELEMENT, AIR REFINER" = **CABIN AIR filter**
   - `90915YZZF1` = "90915-YZZF1 - FILTER, OIL" = **OIL filter**
   The `87139` prefix = Toyota CABIN filter; `17801` = engine air; `90915` = oil.
   Match Joe's flagged CATEGORY ("cabin filter") to the right part — don't grab the
   engine air filter by mistake.
4. **☠️ KEY INSIGHT — a hand-corrected RO means the MENU DEFAULT is the bug.** If the
   closed RO already bills the CORRECT part (e.g. 565709 already had 87139-YZZ81),
   that means an advisor/parts person manually fixed it on this RO. The defect is in
   the **menu SETUP default** — the menu pulls the WRONG cabin filter by default, and
   it gets corrected by hand each time. So you CANNOT see the wrong part on the
   corrected RO — you must **build a fresh quote for that VIN+interval** and explode
   the menu (or read Service Menu Setups) to see what the DEFAULT cabin filter is.
   That default-wrong part is what your override replaces.
5. **Find the line's OPCODE — ⚠️ VIA THE QUOTES PORTAL ONLY (Joe: "no exceptions").**
   The cabin/air/oil filters all hang on the MENU op (e.g. TEK120000VNM) in the
   collapsed RO, but the actual INCLUDED-SERVICE opcode that carries the cabin filter
   (the thing you override) is one level down. Joe's HARD RULE (2026-06-25, insisted
   twice, praised when followed): **you discover the opcode through the QUOTES PORTAL,
   not the menu editor and not the Included Services list.** Verified working method:
   - (a) Settings → flip "**Add Menu Services as separate operations**" toggle ON +
     **Save** (`/ro/service-menu-setups/settings`, switch `data-test-id
     @tekion-repairOrders-serviceMenuSetups-settings-addmenuServiceAsseparateOperation`;
     standing auth to flip it — ALWAYS flip it back OFF after). The settings page has
     its own **Save** button — clicking the toggle is not enough, you must Save.
   - (b) `/ro/quotes` → **Create Quote** → type VIN into `input[placeholder='Search VIN #']`
     (auto-decodes) → set odometer **digit-by-digit** (focus the input, `/press` each
     digit; value-set doesn't stick) → **Continue**.
   - (c) Service page → **right-panel "Service Menu" tab** → click the
     "**<N>K mi Maintenance Package**" tile (center, e.g. x≈684) to open the tier
     picker → click the **tier** (Basic / **Basic + = VALUE = VNM** / Signature) →
     **Add To Quote**.
   - (d) ⚠️ **THE PER-OP OPCODES RENDER IN THE QUOTE'S RIGHT-SIDE OPERATION DETAIL
     PANEL** — click the added menu service line (line "B") to open
     `/ro/quotes/<id>/service/<svcId>`; the operations break out there as
     `Op<N>.TEK........-<Service Name>` each with its part line below. They do NOT
     appear in the **collapsed LEFT line** (which truncates the opcode string to
     "TEK050...") and NOT in the menu editor / Included Services list. The menu adds
     as ONE bundled left line — that's NORMAL; the breakdown is on the RIGHT.
   - (e) Read every opcode + its service + part with one /eval:
     ```js
     // full (untruncated) opcodes anywhere on the page:
     (()=>JSON.stringify([...new Set((document.body.innerText.match(/TEK[0-9A-Z]{5,12}/g)||[]))]))()
     // opcode↔service↔part mapping ("Op7.TEK04020101-Replace Cabin Air Filter" + "8713906030 - ELEMENT, AIR REFINER"):
     (()=>JSON.stringify([...new Set(Array.from(document.querySelectorAll('div,span,td')).map(e=>e.textContent.trim()).filter(t=>/^Op\d+\.TEK|REFINER|FILTER|ELEMENT|\d{10} - /i.test(t)&&t.length<60))])) ()
     ```
   - **VERIFIED** (RO 565709, SCT 876, 120K Value menu TEK120000VNM): Op3 TEK07120301
     Tire Rotation; Op4 TEK05052501 Oil/Filter (90915-YZZF1); Op5 TEK05052403 Spark
     Plugs (90080-91180); Op6 TEK05050306 Engine Air Filter (17801-YZZ01); **Op7
     TEK04020101 Replace Cabin Air Filter (part 87139-06030 = WRONG, correct 87139-YZZ81)**;
     Op13 SMBGMOAG Premium Oil Conditioner. So the cabin-filter override goes on opcode
     **TEK04020101**.
   - **Flip the explode toggle back OFF** when done (per standing-auth rule).
   For the CVT case the opcode was BGCVTF; for the cabin filter it's TEK04020101.
   **Confirm the opcode before building the override — never guess it.**
6. **Propose to Joe:** vehicle scope (year/make/model from ro-vehicle), the WRONG
   default part, the CORRECT part (Joe's PN, e.g. 87139-YZZ81), the opcode, and
   whether to ADD-on-top vs DELETE-and-replace. Get explicit go before editing the
   live menu.

NOTE: the quote VIN decode can show alarming mileage (e.g. 443,712 mi on a 2004
Camry) — that's the real odometer on a high-mileage car, not a decode bug. Use the
interval Joe named (120K) for the quote odometer, not the RO's actual mileage.

## Joe's mechanic (CONFIRMED) — override REPLACES by precedence, doesn't stack

### ⚠️ Two behaviors verified at BC 2026-07-12 (apply fleet-wide, menu context):
1. **Parts PRICE overrides ride through the dynamic feed** — a Define-Here
   parts row that lists a feed-resolved part number with a forced price makes
   the quote resolve the part dynamically but bill `priceType:"OVERRIDE"` at
   your price. Dynamic parts + forced (e.g. trade) prices coexist.
   **SUPERSESSION BYPASS**: if the feed requests an OLD part number and
   supersedes it (`partResolveType:"REPLACED"`,
   `originalRequestedPartNumber` set), an override keyed to the NEW number
   does NOT match — key the override to the ORIGINAL/requested number.
2. **Labor PRICE overrides (vehicle-scoped rows, CP Fixed/FLAT) are IGNORED by
   the menu pricing engine at BOTH surfaces** — opcode Overrides AND
   Included-Service Overrides→Labor. Saved payload shows
   `laborRateType:"FLAT", flatPrice` but the quote still bills the included
   service's own rate (e.g. CUSTOM $269/hr). Labor HOURS overrides DO flow.
   For exact menu-line labor pricing use the included service's Default-tab
   Fixed Price (not vehicle-scoped) or a Custom package price on the menu
   vehicle row (`tekion-menu-custom-price-row`).
   Also: menu edits/overrides don't hit quotes until the MENU is re-Published.

Tekion evaluates the **override FIRST** within the opcode. When you build a parts
override scoped to a vehicle, for a vehicle matching that scope the override parts
**supersede** the Default-tab parts. **You do NOT remove the Default parts** — they
stay for every other vehicle. (Joe: "you do not remove the default parts — just
build the override.")

⚠️ EXCEPTION the user may direct: on the override row's OWN parts table you may be
told to **delete the inherited default parts and add only the correct fluid** (e.g.
delete 303 + 31832, add E-TAF). That's a per-row parts-table edit AFTER the scope
row is built — confirm with the user which they want before acting. The Default
TAB parts (for non-matching vehicles) are never touched either way.

## Engine: persistent browser :9223 HTTP endpoints (NOT the browser tool)

This surface is driven via the long-running Playwright server on port 9223. The
endpoints and their EXACT payload keys (getting these wrong wastes calls):

| Endpoint | Method | Payload | Notes |
|----------|--------|---------|-------|
| `/navigate` | POST | `{"url": "..."}` | SPA goto |
| `/eval` | POST | `{"js": "..."}` | ⚠️ KEY IS `js` — NOT `expression`/`script`/`code`/`fn`. Returns `{"result": <val>}`. Awaits Promises. |
| `/click` | POST | `{"selector": "..."}` or `{"text": "..."}` or `{"ref": "@eN"}` | ⚠️ NO x/y coords. Tag the element with a `data-*` attr via /eval, then click by `[data-jay='...']`. |
| `/type` | POST | `{"selector": "...", "text": "..."}` | Types into the matched input. |
| `/press` | POST | `{"key": "Escape"}` | Playwright keyboard. |
| `/mouse` | POST | `{"x": 1239, "y": 319}` (opt `clicks`,`button`,`move`) | ✅ REAL pointer click (move→down→up). REQUIRED to open the Trim Details modal and any React/Ant cell that ignores selector `/click`. Added to server.js 2026-06-25. |
| `/screenshot` | GET | — | Returns `{"screenshot": "data:image/png;base64,..."}`. Save + vision_analyze. |

Pattern that works every time: **/eval to TAG the exact visible element** (set
`data-jay='foo'`), then **/click `{"selector":"[data-jay='foo']"}`**. This sidesteps
duplicate-match and ghost-element traps.

## NAV PATH (verified SCT 876)

1. Nine-dots → Settings → Service Menu Setups → left-nav **Included Services**
   (`/ro/service-menu-setups/included-service`). See `tekion-service-menu-setups`.
2. Use the **page-level expandable search** (data-test-id
   `...includedServiceTable-expandableSearch-searchBar`, placeholder "Search...",
   class `root_expandableSearch`) — NOT the global "Search here..." box (that
   bounces you to Repair Orders). Type the opcode (e.g. `BGCVTF`) + Enter.
3. Row kebab (⋮) → **Edit service** → lands on
   `/ro/service-menu-setups/included-service/edit-service/<id>/default`
   (e.g. BGCVTF id `693c443aa21e1d4aa51afc42` at SCT).
4. Click the **Overrides** tab (`/click {"text":"Overrides"}` works).
5. Overrides lands on the **Labor** left sub-section by default. Click **Parts**
   in the left sub-nav (Labor / Parts / Fees). The visible sidebar item is a
   `div.root_heading_h4__...` at x≈104 — tag it and click by selector (text-match
   alone resolves 3 elements incl. an off-viewport ghost → timeout).
6. In Parts, set the toggle to **Define Here** (vs "Pull From Opcode"). Each sub-
   section (Labor/Parts/Fees) has its OWN toggle — make sure you flip Parts', not
   Labor's. The row builder (Make/Model/Year/Trim) appears.

## The row builder DOM (positive-x = real, negative-x = ghost)

Edit Service renders TWO copies of the row builder: a HIDDEN one at NEGATIVE x
coords and the REAL visible one at positive x. ALWAYS filter controls to
`offsetParent!==null && rect.x>=0 && rect.x<1400` before tagging/clicking.

Row-1 column layout (verified):
- **Make** ≈ x345, y303 — **react-select** (`[class*="-control"]`). Options:
  Scion / Toyota only.
- **Model** ≈ x545 — **ant-dropdown-trigger** CHECKBOX multi-select with a search
  box ("cor" filters to Corolla family). NOT react-select.
- **Year** ≈ x795 — **ant-dropdown-trigger** CHECKBOX multi-select (All / 2027 /
  2026 / 2024 / ...). NOT react-select.
- **Trim** ≈ x1046 — a **disabled `<input id="trim_N">`** inside a clickable
  ancestor `<div role="button" class="full-width">`. You must click the role=button
  ancestor (the input itself is `disabled` → /click times out on it). Opens the
  **Trim Details** modal.

## Step-by-step (verified BGCVTF / 2024 Corolla family / CVT)

### Make
- Tag the visible control at x≈345,y≈303 → /click → options `[id*="-option-"]`
  appear → tag the one whose innerText==='Toyota' → /click. Verify via a
  `[class*="-singleValue"]` reading "Toyota".

### Model (checkbox multi-select)
- Tag the `.ant-dropdown-trigger` at x≈545,y≈303 → /click → a search box (input at
  ≈x556,y345) + checkbox list appears.
- /type "cor" into the search box (tag it first) → filters to: Corolla, Corolla
  Cross, Corolla Hatchback, Corolla iM, **Corona**, GR Corolla.
- ⚠️ **Pair each checkbox to its label by WALKING UP from the checkbox** — the
  `.ant-checkbox-wrapper` innerText is EMPTY; the label text is a sibling/ancestor.
  Match by `el.closest()` walk, NOT by raw y-coordinate (the row pitch shifts ~34px
  between the static-scan snapshot and the live filtered list → coordinate tagging
  checks the WRONG model).
- Check the 5 Corolla family models; **leave Corona unchecked**. Verify final
  state by reading each checkbox's `.checked` paired with its label.

### Year (checkbox multi-select)
- Close Model first (see dismissal rule below). Tag the Year trigger at x≈795 →
  /click → checkbox list (All / 2027 / 2026 / 2025 / 2024 / ...).
- Tag the checkbox whose label==='2024' (walk-up pairing) → /click. Verify only
  2024 checked.

### Trim (modal) — ✅ SOLVED via the `/mouse` coordinate-click endpoint
- Close Year first. The Trim cell is a **disabled `<input id="trim_N">`** inside a
  `<div role="button" class="full-width">`. Selector/text/ref `/click` on either
  the input OR the role=button ancestor **does NOT open the Trim Details modal**
  (verified 2026-06-25: `/click` returned success but no `.ant-modal-content`
  appeared; clicking the inner `searchIcon` div did nothing; even directly
  invoking the React `onClick` off fiber props returned "called onClick" but
  rendered no modal — only an empty `.ant-popover` w=0 at the anchor). The cell
  needs a **genuine OS-level pointer sequence**.
- **THE FIX (proven, 2026-06-25): use the `/mouse` coordinate-click endpoint**
  (Playwright `page.mouse.move(x,y)` then `page.mouse.click(x,y)` — a real
  pointerdown→up→click). This was ADDED to the :9223 server.js in this session;
  see `persistent-browser-server` skill for the endpoint + restart procedure.
  ```python
  # get the cell center, then real-pointer click it
  coords = ev('''(()=>{const inps=[...document.querySelectorAll('input[placeholder="Select Vehicle Trim"]')].filter(e=>e.offsetParent);inps.sort((a,b)=>a.getBoundingClientRect().y-b.getBoundingClientRect().y);const inp=inps[0];let root=inp;for(let k=0;k<6&&root;k++){if(root.getAttribute&&root.getAttribute('role')==='button')break;root=root.parentElement;}const r=(root||inp).getBoundingClientRect();return JSON.stringify({cx:Math.round(r.x+r.width/2),cy:Math.round(r.y+r.height/2)});})()''')
  post("mouse", {"x": cx, "y": cy})   # opens Trim Details modal (.ant-modal-content w≈888)
  ```
- The Trim Details modal layout (verified): LEFT = **Filters (N)** panel with an
  **Apply** button at its top-right (≈x367,y94), filter sections Engine Liter /
  Cylinder / Aspiration / Doors / Body Type / **Transmission (CVT, MT)**. RIGHT =
  **Choose** radios **"All trims (including future trims)"** (default selected) vs
  "Specific trims", a search box, "N search results", and the trim list. Bottom-
  right = Cancel / **Save** (≈x1006,y712).
- Steps (all via `/mouse` to coordinates read from /eval): (1) click the **CVT**
  checkbox in Transmission (find it inside `.ant-modal-content`, match label
  text 'CVT', click its center). (2) Verify CVT `.checked===true`. (3) click
  **Apply** → result count drops (26→23 = CVT-only, MT excluded) and Filters
  shows "(1)". (4) keep "All trims (including future trims)" radio. (5) click
  modal **Save** → modal closes (`.ant-modal-content` offsetParent null).
- Verify the Trim cell now reads **"All trims selected"** (screenshot+vision).
- Dismiss any stray dropdown by clicking a safe in-panel coordinate via /mouse
  (e.g. x600,y250) — still NEVER click left-rail icons.

### Parts on the row — EXPAND, DELETE, ADD (verified end-to-end 2026-06-25)

The parts table does NOT show by default — you must **expand the vehicle row**:
- The row's far-LEFT has a **caret/chevron** (`aria-label="icon-caret-down root_table_pivotIcon"`, ≈x284,y319, w=14) AND a separate **drag handle**
  (`icon-drag-and-drop`, ≈x312,y319). ⚠️ Do NOT click the drag handle — it does
  nothing useful and earlier sessions confused it for the chevron.
- ✅ **Click the chevron by SELECTOR, not raw /mouse coords.** Tag it via
  `[aria-label*="icon-caret"]` (the leftmost one on the row) and `/click
  {"selector":"[data-jay='chev']"}`. Raw `/mouse` at (284,319) was flaky — it
  toggled open-then-closed or missed (caret class varies; sometimes
  `root_icon_size__md`, sometimes only resolvable by aria-label). Selector-click
  expanded reliably. Verify via the caret element gaining an `isExpanded` class
  / parts (303/31832) becoming visible.

Once expanded, the row's **"Add Custom Parts"** table appears BELOW the vehicle
row + 3 checkboxes (Enable Part Price Cap / Consider for Parts preparation /
Eligible for Customer Pay). It inherits the Default parts (e.g. 303 + 31832).
Per user direction either ADD the override part on top, or DELETE the inherited
parts and add only the correct one.

**DELETE a default part (per-part kebab → Delete):**
- Each part row has a **kebab (⋯)** overflow button at its far right
  (`[class*="icon-overflow"]`, ≈x920,y<part-row-y>). Tag + `/click` it → a small
  menu opens with a **Delete** option.
- ⚠️ The kebab does NOT directly delete — it opens a menu. Find the **Delete**
  menu item (search visible `li`/menu-item innerText==='Delete'), get its center,
  and click it. Verify the part disappears from the table (`parts now: [...]`).
- ⚠️ **Rows reflow after each delete** — after deleting 303, 31832 moves UP into
  303's old y-position, and the table can shift LEFT (~70px). ALWAYS re-scan the
  kebab/Delete coordinates fresh before the NEXT delete; never reuse the prior
  delete's coords. (Reusing stale coords or a stale `data-jay` tag = a `/click`
  that matches nothing → 10s timeout, or worse hits a popup, see pitfall 10.)

**ADD the override part:**
- The empty add-part row has a **Part Name dropdown** (≈x325,y532), a **Quantity**
  ant-input-number (default "1"), and a **Price** ant-input-number (placeholder
  "0.00"). There is NO separate "Add" button — the blank row IS the add row.
- Click the Part Name dropdown → tag its now-active search `input` (offsetParent
  set, on that y-band) → `/type` the part NUMBER (e.g. `0888681986`). Options
  render: the real part (`"08886-81986 - E-TAF,TE"`) **plus a `Create "..."`
  option** — IGNORE Create, click the real part (match innerText startsWith the
  dashed number or includes the part name).
- Set **Quantity** (usually defaults to 1 — verify) and **Price**: tag the
  row's Price `input.ant-input-number-input` (the one with placeholder "0.00",
  rightmost on the row), `/mouse`-click it, then `/type` the price (e.g.
  `155.93`). Verify `el.value` reads exactly `155.93` and qty reads `1`.
- Correct part comes from the closed RO (don't invent): e.g. E-TAF
  `0888681986`, qty **1**, price **$155.93** (from RO 565535).
- The table always keeps ONE trailing empty placeholder row (qty 1 / $0.00) for
  the next add — that is NOT a real part, ignore it in your final verification.

### Save
- Record the pre-change baseline for a clean revert FIRST. Narrate before acting.
- Hit Save ONCE after all fields are set (Joe: configure everything, save once).
- The page-level **Save** button is bottom-right (≈x1211,y687, blue, next to
  Cancel). Tag it by `button` innerText==='Save' with `rect.y>600` (there can be
  other "Save" buttons higher up, e.g. inside the Trim modal) and click by
  selector or `/mouse` at its center.
- ✅ **Save-success signal (verified 2026-06-25):** on a successful page Save the
  URL flips from `.../edit-service/<id>/overrides` BACK to `.../edit-service/<id>/default`
  and the view returns to the Default tab. Confirm persistence by re-clicking the
  **Overrides** tab → **Parts** sub-nav → the override row should still be present
  (read a `[class*="-singleValue"]` = your part, e.g. "08886-81986 - E-TAF,TE").
  Expand the row once (caret by selector) to verify the parts table = only the
  override part (old defaults gone, qty/price correct).
- ⚠️ Expanding/collapsing toggles: each caret `/click` flips state. If the row was
  already expanded from the build, one click COLLAPSES it. Read the caret's
  `isExpanded`/aria state (or screenshot) to know which way it'll toggle before
  trusting an empty parts read.
- STOP for the user's review BEFORE re-quoting. Re-quote the exact VIN+mileage
  only after explicit go.

## 🎯 RE-QUOTE VERIFICATION (the proof-of-fix loop — verified 2026-06-25)

After Joe says go, build a throwaway quote to PROVE the override is live and
reconcile the dollars. This is the single most convincing thing to report.

1. **Open Quotes.** Deep-linking `/quotes` or `/ro/quotes/create` BOUNCES to
   `/home`. The working path: `/navigate {"url":"https://app.tekioncloud.com/ro/quotes"}`
   (the LIST page loads directly), then `/click {"text":"Create Quote"}` → lands
   `/ro/quotes/create`. Confirm dealer first: `localStorage.currentActiveDealerId`
   (876 = SCT) — wrong store = wrong menu.
2. **Enter VIN:** `/type {"selector":"input[placeholder='Search VIN #']","text":"<VIN>"}`
   → auto-decodes Make/Year/Model/Trim (wait ~5s; verify it shows e.g. "Corolla
   Hybrid XLE ... CVT"). There may be an orange "Trim details have changed" notice
   — harmless.
3. **Odometer:** find the input near y≈590, x<500 (it has no placeholder). `/type`
   alone often won't stick — FOCUS via eval (`document.querySelector("[data-jay='odo']").focus()`)
   then send each digit via `/press {"key":"9"}` etc. Verify it reads "90,000".
   `/click {"text":"Continue"}` → lands `/ro/quotes/<id>/service/new`.
4. **Service Menu tab → interval → tier.** `/click {"text":"Service Menu"}`, then
   click the interval (`/click {"text":"90K mi"}` — NOT the full "90K mi Maintenance
   Package" string). Tiers render as **Basic / Basic + / Signature**. ⚠️ TIER-NAME
   MAP: Basic+ = **Value** (TEK90000**V**NM), Signature = **Premium** (TEK90000**P**SM),
   Basic = TEK90000**B**NM. Click the tier, then ⚠️ **VERIFY the package opcode**
   before trusting the panel (stale-package trap — the panel can lag the highlighted
   chip):
   ```
   /eval {"js":"JSON.stringify([...new Set(Array.from(document.querySelectorAll('span,div,td,label')).filter(e=>e.children.length===0).map(e=>e.textContent.trim()))].filter(t=>/Package OpCode|TEK\\d/i.test(t)).slice(0,4))"}
   ```
   It must read `Package OpCode : TEK90000VNM` (your interval number). If it shows a
   different interval, RE-CLICK the tier/interval until it flips.
5. **Read the new TOTAL + reconcile.** Grab the package total
   (`/^\$[\d,]+\.\d{2}$/`, ≠$0.00). It should be (original total − Δparts). The
   BGCVTF case: was $1,978.62, now **$1,719.16**, Δ = −$259.46 = $415.39 (old
   31832+303) − $155.93 (E-TAF). A clean reconciliation = override confirmed.
6. **Confirm the part behind the line.** `/click {"text":"Add To Quote"}` →
   `/click {"text":"TEK90000VNM"}` to EXPAND the menu line → read the parts:
   ```
   /eval {"js":"(function(){var n=Array.from(document.querySelectorAll('*')).filter(e=>e.children.length===0&&/(E-TAF|81986|FLUID CONDITIONER|FULL SYNTHETIC CVT|303 -|31832)/i.test((e.textContent||'').trim()));return JSON.stringify([...new Set(n.map(function(x){var r=x;for(var i=0;i<6&&r.parentElement;i++){r=r.parentElement;if(/\\$/.test(r.textContent)&&r.textContent.length<220)break;}return r.textContent.replace(/\\s+/g,' ').trim().slice(0,200);}))]);})()"}
   ```
   VERIFIED result: `"0888681986 - Toyota EV TransAxle 1 each $155.93"` and the old
   303/31832 ABSENT = override is live for this vehicle. Screenshot for Joe's records.
7. **Report:** interval + tier + opcode, old-vs-new part, old-vs-new total, the
   exact Δ, and that the dollars reconcile. Offer to verify/duplicate on the sibling
   tier (Premium TEK90000PSM).

## PITFALLS (each cost real work)

1. **`/eval` key is `js`.** Using `expression`/`script` returns HTTP 400
   `{"error":"js is required"}`. Verified the only accepted key is `js`.

2. **🛑 NAVIGATE-AWAY ROW WIPE (worst).** Dismissing a dropdown by tagging a
   "neutral" element via SHORT text/heading match can match a LEFT-NAV MODULE ICON
   (e.g. a `root_heading` whose innerText is just "R" at x≈26,y≈149 = the Reports
   module). Clicking it NAVIGATES OFF the Edit Service page and **wipes the entire
   unsaved override row** (nothing was saved → total loss, but live config safe).
   NEVER click left-rail icons or top-of-page single-letter headings to dismiss a
   dropdown. To dismiss: try `/press {"key":"Escape"}` ×2; if the dropdown stays
   open (`.ant-dropdown:not(.ant-dropdown-hidden)` still present), use the
   **SAFEST dismissal = toggle the dropdown's OWN trigger closed** (click the same
   `[data-jay='...']` trigger you opened it with — ant multi-selects toggle shut).
   Verified clean: dropdown closes, `location.pathname` unchanged, row intact.
   This is the preferred method — it can NEVER navigate away. Only if that fails,
   click a SAFE in-panel neutral target positively identified by screenshot (the
   "Define Here" label or a section header INSIDE the parts panel, x>0, panel
   y-band) — and verify it's not a nav element first. NEVER use short-text/heading
   matches for neutral clicks (that's what caused the wipe).

3. **Coordinate drift on checkbox lists.** A static DOM scan can report checkbox
   y-positions that differ from the live filtered list (34px pitch shift). Tagging
   by y checked the wrong model (got "Corolla Hatchback" when targeting "Corolla").
   ALWAYS match checkboxes by their paired LABEL TEXT, never by y.

4. **Checkbox wrapper innerText is empty.** Walk up from the `input[type=checkbox]`
   (`for k<5: p=p.parentElement; if innerText: txt=...; break`) to get the label.

5. **Trim input is `disabled`.** /click on `#trim_N` times out ("element is not
   enabled"). Click its `role="button"` ancestor div instead — but note even that
   selector-click WON'T open the Trim Details modal; you MUST use the `/mouse`
   coordinate endpoint (real pointer sequence) at the cell center. See the Trim
   step above. This was the single biggest wall in the BGCVTF session and is now
   solved by `/mouse`.

6. **text-match resolves to ghosts.** `/click {"text":"Parts"}` matched 3 elements,
   first off-viewport → "element is outside of the viewport" timeout. Tag the
   VISIBLE one (offsetParent!=null, x in 0..1400) and click by `[data-jay]`.

7. **Escape doesn't always close ant-dropdown multi-selects.** After picking
   years, Escape sometimes leaves the dropdown OPEN, and a follow-up click meant
   for the next field re-opens the same dropdown. Verify closed via
   `document.querySelector('.ant-dropdown:not(.ant-dropdown-hidden)')` returning
   null before moving on.

8. **Screenshot + vision_analyze is the ground truth.** The DOM scans miss
   layout (negative-x ghosts, virtualized lists). Screenshot after each major step
   and read it with vision before trusting an /eval result.

9. **🛑 TEKION NOTIFICATION-POPUP WIPE (2nd-worst, hit TWICE this session).**
   Tekion fires transient **toast/notification popups in the BOTTOM-RIGHT** (e.g.
   "RO 570876 P&A request", "RO 570903") while you work. If a `/mouse` click —
   especially a kebab or Delete click whose stale/reflowed coords drift toward the
   bottom-right — lands ON one of these toasts, it **navigates you to a totally
   different screen** (e.g. a P&A Request / RO-sales details page) and **wipes the
   entire unsaved override row** (same total-loss as the left-nav wipe). Worse,
   the destination page may be **"locked for other users"** — you must exit it
   cleanly so you don't leave it locked for the real user.
   MITIGATIONS: (a) Prefer mid-screen Delete-menu coordinates (≈x775) over the
   far-right kebab when clicking the menu item — the Delete option renders LEFT of
   the kebab, safely away from the bottom-right toast zone. (b) After opening any
   kebab, **screenshot+vision FIRST** to confirm the Delete menu is open AND to
   check for a bottom-right toast, then click Delete at the verified mid-screen
   coord. (c) NEVER blind-click reflowed coordinates — re-scan every time. (d) If
   you DO get navigated away: capture `location.href`, hard-`/navigate` back to the
   Edit Service URL (if the page warns it's locked, exit cleanly), and rebuild the
   row from scratch (nothing was saved). Recovery is faster if you've kept the
   exact field recipe (Make/Model/Year/Trim + part/qty/price) handy.

10. **Stale `data-jay` tags + reflow = silent 10s timeout.** After a row reflows
   (post-delete) or the page re-renders, a previously-set `data-jay` attribute may
   no longer be on the element you want (or on nothing). A `/click
   {"selector":"[data-jay='x']"}` that matches nothing **blocks ~10s then fails**.
   Re-tag fresh against the CURRENT DOM before each click in a reflow-prone area
   (parts table after deletes).

## Reusable /eval snippets

Tag + click (the core pattern):
```js
// tag the visible Make control near x345,y303
(() => { let f=null;
  document.querySelectorAll('[class*="-control"]').forEach(el=>{
    const r=el.getBoundingClientRect();
    if(el.offsetParent===null||r.x<0||r.x>1400||r.width===0) return;
    if(Math.abs(r.x-345)<30 && Math.abs(r.y-303)<30){ el.setAttribute('data-jay','makectl'); f=true;}
  }); return JSON.stringify(f); })()
```

Checkbox↔label pairing (model/year):
```js
(() => { const out=[];
  document.querySelectorAll('input[type="checkbox"].ant-checkbox-input').forEach(el=>{
    const r=el.getBoundingClientRect();
    if(el.offsetParent===null||r.x<500||r.y<360||r.y>720) return;
    let p=el, txt='';
    for(let k=0;k<5 && p;k++){ const t=(p.innerText||'').trim(); if(t){txt=t;break;} p=p.parentElement;}
    out.push({txt:txt.slice(0,25), checked:el.checked});
  }); return JSON.stringify(out); })()
```

Find the Trim role=button trigger:
```js
(() => { const inp=document.querySelector('#trim_1'); let p=inp;
  for(let k=0;k<6 && p;k++){
    if(p.getAttribute && p.getAttribute('role')==='button'){ p.setAttribute('data-jay','trimtrig'); return 'ok';}
    p=p.parentElement;
  } return 'notfound'; })()
```

Verify a dropdown is closed:
```js
(() => { const d=document.querySelector('.ant-dropdown:not(.ant-dropdown-hidden)'); return d?'OPEN':'closed'; })()
```
