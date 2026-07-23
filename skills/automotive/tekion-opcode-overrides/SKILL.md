---
name: tekion-opcode-overrides
description: >
  Add vehicle/part override rows to a Tekion opcode (Overrides tab) using the
  verified browser-tool cascading react-select method. This is the batch
  workflow used for cabin-filter part overrides (RACF etc.) — Make/Model/Year/
  Trim/Part per row, driven by the __buildRow() helper toolkit. Covers the
  real-click trim rule, the Save Changes confirmation modal, and mandatory
  reload+API verification. The most complex Tekion workflow we run.
trigger: >
  Tekion override, opcode override, vehicle override, part override, cabin air
  filter, RACF, cabin filter, add override row, Overrides tab, override pricing,
  batch overrides, __buildRow, Toyota cabin filter overrides
triggers:
  - opcode override rows
  - cabin filter overrides
  - vehicle part override batch
  - overrides tab opcode
---

# Tekion Opcode Overrides — Vehicle/Part Override Rows (VERIFIED BATCH METHOD)

This is the **Overrides tab** of an opcode edit page — a completely different UI
from the Default tab (which is `tekion-opcode-default-pricing`). It adds
vehicle-specific override rows: **Make → Model → Year → Trim → Part → Price**.
Used for cabin-filter part overrides (opcode `RACF` etc.).

**Companion skills:**
- **Login / OTP / dealer switch** → `tekion-autonomous-login` or `tekion-browser-navigation`
- **Read / audit / verify committed rows** → `tekion-opcode-api` (USE THIS to verify every batch — the UI grid lies)
- **Default-tab labor + parts pricing** → `tekion-opcode-default-pricing`
- **Deep reference / historical detail** → `tekion-opcode-pricing-v2`

---

## ⚠️ LABOR OVERRIDES ON OPCODES DO NOT PRICE MENU LINES (verified BC 2026-07-12, TEK05052501)

If the opcode is consumed by a SERVICE MENU, an **opcode-level LABOR override row's Fixed/flat
price does NOT flow to the menu quote line.** Verified end-to-end at BC: override row (CP =
Fixed Price $100, 0.5 hr, vehicle-scoped) saved fine and FIRED at quote time — the HOURS
flowed (0.40→0.50 hr) — but the line billed 0.5 × $269 CP = $134.50, ignoring the flat $100.
Cause: the menu's INCLUDED SERVICE carries its own labor config
(`pricingDetail.laborRateType:"CUSTOM"`, its own pricePerHour) which supersedes the opcode
override's flatPrice. **Fix surface for menu-line labor pricing = Service Menu Setups →
Included Services → Edit Service → Labor (and its own Overrides tab for vehicle-scoped
rows).** Opcode-level labor overrides still matter for hours and for non-menu usage.
PARTS behave differently: menu lines resolve the opcode's parts dynamically per VIN
(auto-supersession included, `partResolveType:"REPLACED"`) — parts overrides on the opcode
DO matter to menus.

---

## 🅣 TEK FACTORY-OPCODE PART-REPLACE METHOD — ✅ FULLY VERIFIED END-TO-END (Joe 2026-06-25, TEK04020101 @ SCT 876)

> ✅ **STATUS: COMPLETE & SAVED SUCCESSFULLY. Jay reproduced the entire flow solo 2026-06-25 and Joe
> confirmed "Opcode updated successfully." Two directives that broke the deadlock: (1) "add after the
> 15th row, create the 16th row" (into Modify System Parts, not Add Custom Parts); (2) "do the all
> identifiers and all jobs BEFORE you put the part number in."**
>
> **🟩 THE ANSWER (what unblocked Jay) — add 06030 as the 16th row INSIDE the Modify System Parts table:**
> - "Replace Part Number" (menu: Exclude / Replace Part Number / Link Part / Delete) appears on a part
>   row's ⋮ kebab ONLY when that row lives in the **"Modify System Parts"** table. The 15 native system
>   rows have it; the **"Add Custom Parts"** table rows (UPPER table) get **ONLY "Delete"** (WRONG surface).
> - **The Modify System Parts table HAS a blank add-row at its BOTTOM, right after the 15th system row**
>   (e.g. after 87139-76020). It looks like the other rows: a Job select ("Add jobs from here"),
>   Identifier select ("Add identifiers from"), and a **Part Name combobox**. Typing a part number into
>   THAT blank Part Name field creates the **16th row INSIDE the system table** — and the 16th row's ⋮
>   DOES carry "Replace Part Number." This is the whole trick: 16th row in the SYSTEM table, not a row in
>   the Custom table.
> - **PART NAME SEARCH GOTCHA:** type the FULL dashed part number `87139-06030` (NOT just the suffix
>   `06030` — suffix-only returns junk like `060306A - TRANY FLUID` + a `Create "06030"` fallback). With
>   the full number the dropdown returns `Create "87139-06030"` (IGNORE) and the real catalog row
>   `87139-06030 - ELEMENT, AIR REFINER` (PICK this).
> - Then open the 16th row's ⋮ → **Replace Part Number** → modal `Replace Part Number of
>   M_TMNA_8713906030` → **Select Part** dropdown → type `87139-YZZ81` → pick
>   `87139-YZZ81 - ELEMENT, AIR REFINER` → **Save** (modal) → **Save** (bottom override box).
> - **NOTE the row still DISPLAYS "87139-06030" after the modal Save** — that's correct; the Replace rule
>   maps old→new underneath, it does NOT relabel the visible cell. Verify the swap in a re-quote, not by
>   the cell text.
>
> 🟩 RESOLVED + VERIFIED END-TO-END (Joe confirmed 2026-06-25, "Opcode updated successfully"):
> **You MUST set Identifier="All Identifiers" AND Job="All Jobs" on the blank 16th add-row BEFORE you
> type the part number into Part Name.** This is the #1 thing Jay keeps forgetting. The other 15 system
> rows show "All Identifiers / All Jobs"; the new row spawns with empty placeholders ("Add identifiers
> from" / "Add jobs from here"). If you type the part number first and leave them empty, the bottom Save
> FAILS with red toast **"Please correct form errors to proceed"** (the empty Job column gets a red
> border at ~x245/y475). Joe's exact words: "you need to do the all identifiers and all jobs before you
> put the [part] number in." CORRECT ORDER on the 16th add-row:
> 1. Identifier column (~x365) → click → pick **"All Identifiers"**
> 2. Job column (~x585) → click → pick **"All Jobs"**
> 3. THEN Part Name (~x805) → type FULL `87139-06030` → pick the real `87139-06030 - ELEMENT, AIR REFINER`
> 4. Row ⋮ → Replace Part Number → YZZ81 → Save modal → bottom Save → green success.
> (Identifier/Job are NOT quantity/price — you still NEVER touch quantity or price. Setting Identifier+Job
> is required; it just mirrors what the native rows already have.)
> RECOVERY if you typed the part first and it's stuck wrong: nothing is saved yet, so SPA-reload the opcode
> (`location.reload()`) to discard the whole stray row, then rebuild in the correct order. The flaky
> ⋮→Delete dance on a custom-table row is not worth fighting — reload is cleaner.
>
> **PAGE STRUCTURE (verified, reliable — use these section anchors):** inside an expanded Overrides
> vehicle row, top-to-bottom: "Parts List / Add Custom Parts" header → custom-parts add-row (Part Name
> combobox; ⋮ = Delete only — WRONG surface) → **"Remove System Parts" toggle** (OFF by default; you do
> NOT need to flip it) → **"Modify System Parts" header** → 15 system-part rows, each with ⋮ =
> Exclude/Replace Part Number/Link Part/Delete → **BLANK 16th add-row at the bottom (Job / Identifier /
> Part Name)** ← THIS is where you add the original part. The custom table and the system table are
> DIFFERENT; only the system table (incl. its blank add-row) yields a Replace-capable ⋮.
>
> **COLUMN x-anchors after scrolling the table into view (verified DOM read):** Position/Job select
> ~x245-365, Part Name input `id="partName_undefined"` ~x805, Quantity `id="partQuantity_undefined_quantity"`
> ~x1033, Price `id="customerPayUnitPrice_undefined"` ~x1291, ⋮ `icon-overflow` ~x1400. The active part-search
> input surfaces as `id="AUTO_COMPLETE_FIELD_ID"` (renders off-screen until the combobox is focused) — tag
> the `partName_undefined` input with a `data-jay` attr and `/type {selector,text}` into it.
>
> **REPRODUCIBLE TOOL FLOW (persistent browser :9223, verified):** reload opcode (discards any stray
> custom-row add) → Overrides tab → Parts left sub-nav → expand the Toyota vehicle row via its far-LEFT
> caret → scroll 87139-76020 (15th row) into center → find the LAST `partName_undefined` input ABOVE the
> input (that's the blank 16th add-row) → **set its Identifier select → "All Identifiers" and Job select
> → "All Jobs" FIRST** → then click+type FULL `87139-06030` → pick the real
> ELEMENT option → confirm 06030 row now sits directly BELOW 76020 (inside the system table) → open its
> `icon-overflow` ⋮ → confirm menu = Exclude/Replace Part Number/Link Part/Delete → Replace Part Number →
> Select Part = 87139-YZZ81 ELEMENT → modal Save → (set Job/Identifier if Save errors) → bottom Save.
>
> --- (the rest of this section's click-path is reliable and unchanged) ---
>
> The TEK part-replace happens on the **OVERRIDES tab → Parts**, on the **"Modify System Parts"
> table that lives INSIDE an expanded vehicle row**. NOT the Default tab. NOT the custom add-row.
>
> **EXACT CLICK-PATH (the one that worked):**
> 1. `/ro/opcode/edit/<TEKOPCODE>` → **Overrides** tab → **Parts** left sub-nav.
> 2. Overrides→Parts shows a **vehicle-row builder**: rows of Make/Model/Year/Trim (e.g. Row 1
>    Toyota, Row 2 Scion, Row 3 blank). Joe's instruction for the cabin case: **"add to the existing
>    Toyota row."** Each vehicle row's controls (left→right): caret(expand) `icon-caret-down` ≈x284,
>    drag `icon-drag-and-drop` ≈x312 (DO NOT click), Model/Year/Trim selects, then far-right
>    `icon-notes`≈x1473, `icon-trash`≈x1513, `icon-copy2`≈x1549. The "kebab at x318" vision sometimes
>    reports is actually the DRAG handle — ignore it.
> 3. **Expand the Toyota row** via the far-LEFT caret (`[class*="icon-caret-down"]` at x<300, y≈row).
>    This reveals, lower in the expanded row, the **"Modify System Parts" table** — a long list of
>    system part rows (88508-01010, 87139-47010-83, YZZ96, 33010, 07010, 07020, YZZ92, 50100, 02090,
>    YZZ93, 58010, 0E040, 0R030, 76020, AND the 06030 row), each with its OWN `icon-overflow` (⋮)
>    kebab at x≈1083 (these sit at y≈800-1412, BELOW the fold — scroll the kebab into view).
> 4. On the **system part row for the ORIGINAL part (87139-06030)**, click its ⋮ `icon-overflow`.
>    The menu shows: **Exclude / Replace Part Number / Link Part / Delete**.
> 5. Click **"Replace Part Number"** → modal titled **"Replace Part Number of M_TMNA_8713906030"**
>    with a **"Select Part"** dropdown → choose **87139-YZZ81 - ELEMENT, AIR REFINER** → **Save** (modal).
> 6. Then **Save at the bottom of the override box** (the main Overrides Save). Done.
>
> 🚫 **NEVER set QUANTITY or PRICE (Joe corrected me hard 2026-06-25).** The Replace-Part-Number action
> is the WHOLE swap and nothing else. It tells Tekion: "any time you see the original part number, use
> the replacement instead." Tekion KEEPS its own quantity logic — if the car calls for 2 of the part,
> it pulls 2 of the REPLACEMENT — and the price comes from the **price code**, NOT any override price.
> Touching quantity here would force a qty (e.g. force 1 when the car needs 2). Touching price would
> override the price-code price. So: **no qty, no price — only the part-number swap.**
>
> 🚫 **DO NOT use the "Add Custom Parts" / blank Part-Name add-row path.** That custom-parts builder
> carries a quantity AND an override price (the exact thing to avoid). The correct surface is the
> ⋮ "Replace Part Number" on the EXISTING SYSTEM part row inside the expanded vehicle row. If you
> accidentally added the original part via the custom add-row, DELETE that stray row before doing the
> real replace.
>
> **VERIFICATION (proven):** fresh quote on the affected VIN+interval (toggle "Add Menu Services as
> separate operations" OFF — it should already be off), Service Menu → package tile → tier → Add To
> Quote → click the menu line to open `/service/<id>` → read the right detail panel. Cabin line now
> reads `87139YZZ81 - ELEMENT, AIR REFINER | 1 each | <onhand> | $21.99` and `87139-06030` is GONE.
> Quick DOM probe: `document.body.innerText.includes('87139YZZ81')` true / `includes('8713906030')` false.
>
> **Quotes-portal flow reminders (RE-VERIFIED END-TO-END 2026-06-25, the verification quote that
> confirmed the YZZ81 swap):** Create Quote button is top-right on the `/ro/quotes` list page — find it
> by TEXT (`button:text-is("Create Quote")`), it lands ≈(1110,80); a div tagged at the very top
> (≈168,64) is the WRONG element and the click times out. Lands on `/ro/quotes/create`. The VIN field
> placeholder is **"Search VIN #"** (≈419,320) — type the VIN, it decodes INLINE (no dropdown to click;
> default trim is fine for this check; body text shows Make/Year/Model). Odometer input
> `id` contains "vehicleOdometer" (≈89,587), a formatted ant-input (typing "120000" shows "120,000");
> use `/type {selector,text}`. Continue ≈(1166,673). Quote created at `/ro/quotes/{id}/service/new`.
> Right panel tabs: Recall / Deferred / Service Catalog / **Service Menu** — click Service Menu →
> the matching **"<N>K mi Maintenance Package"** tile auto-appears for the odometer (≈684,651) → click
> the package TILE to open the tier panel → **tier tabs render in a ~y304 band: "Basic" / "Basic +"
> (NOTE the SPACE) / "Signature"** (Basic + = Value = …VNM). **Confirm the package opcode flipped** by
> reading `document.body.innerText.match(/TEK\d+[A-Z]{0,3}/)` — Basic = …BNM, Basic + = …**VNM**,
> Signature = …PSM/SNM. Click "Basic +" → opcode must read **TEK<interval>VNM** → **Add To Quote**
> ≈(1137,672). The package adds as ONE bundled service LINE in the left list (normal). **To read the
> per-op parts you MUST click INTO the line:** the clickable target is the innermost **SPAN** holding
> "TEKxxxxxVNM - …" (≈95,243) — clicking a wrapping DIV (rect 0,0) does nothing; tag the span
> (`span` whose text matches /TEKxxxxxVNM/) and click it → navigates to `/service/{opId}`. Then the part
> lines are in `document.body.innerText` — quick proof probe: `/87139-?YZZ81/i.test(txt)` true,
> `/87139-?06030/i.test(txt)` false; the cabin line reads `87139YZZ81 - ELEMENT, AIR REFINER | 1 each |
> <onhand> | $21.99`. Verified totals: WITH the YZZ81 override = **$1,929.12** vs the wrong-06030
> baseline **$1,937.12** (−$8.00 on the 120K Value Camry).
>
> **Joe says the replace is GLOBAL to the opcode scope ("all that take the 06030"),** so confirm the
> chosen vehicle row's Make/Model/Year actually covers the vehicles that pull the old part. For the
> cabin case the existing Toyota row covered it.
>
> --- (older discovery notes below kept for context; the procedure above supersedes them) ---
>
> The Overrides→Parts surface is a **vehicle-row builder** (Make/Model/Year/Trim rows)
> where **each vehicle row has a kebab (⋮) menu** carrying "Replace Part Number". The earlier
> "Modify System Parts table on the Default tab" hypothesis was WRONG — there is no such table on
> TEK04020101; the populated rows seen in screenshots were the part-dropdown OPTION list, not committed
> rows. Joe says the
> replace is GLOBAL to the opcode scope ("all that take the 06030"), so confirm the chosen vehicle row's
> Make/Model/Year actually covers the vehicles that pull the old part before committing.
>
> ⚠️ **DO NOT TOUCH THE DEFAULT TAB for a TEK part-replace.** Joe was emphatic ("don't touch default!!!").
> If you accidentally add the original part on Default's blank add-row (which only has a TRASH icon, no
> ⋮), delete it — but deleting it leaves an UNSAVED pending edit, which triggers a "Confirm Navigation —
> save your changes?" modal when you switch tabs. The clean recovery (verified, "Option B"): dismiss the
> modal, then HARD-RELOAD the opcode page via JS `window.onbeforeunload=null; location.href=
> '/ro/opcode/edit/TEK04020101?_r='+Date.now()` (the persistent-browser server has NO `/goto` endpoint —
> POST /goto returns 404). The reload discards all pending Default state cleanly. Then go straight to
> Overrides → Parts and do the work there.
>
> **Stale evidence from the discovery session (kept for context):**
> - Joe's "Modify System Parts" screenshot (populated rows 88508-01010, 87139-47010-83, YZZ96…
>   + a "Remove System Parts" toggle top-right + per-row ⋮) was labeled **Default tab**, not Overrides.
> - The **live Overrides → Parts** on TEK04020101 showed ONLY the vehicle-row builder
>   (Make/Model/Year/Trim rows + "Add Custom Parts") — **no "Modify System Parts" table, no toggle.**
> - The **live Default → Parts** on TEK04020101 showed ONLY a single **blank "Part Name" input row**
>   — **no populated system parts and no "Remove System Parts" toggle.** The Default tab is one
>   long scrollable form; "Parts" in the left rail is a scroll ANCHOR to a section, not a sub-tab.
> - HYPOTHESIS (unconfirmed): the "Remove System Parts" toggle + populated table only render when
>   the opcode actually HAS system parts; TEK04020101's parts table appears empty, so neither shows.
>   If empty, the question "where is 06030 sourced from?" is unanswered — adding YZZ81 to the blank
>   row only ADDS it, it does not stop 06030 pulling. STOP and ask Joe rather than guess the source.
> - LESSON: before executing the TEK part-replace, FIRST confirm (via screenshot+vision) that a
>   populated "Modify System Parts" table + "Remove System Parts" toggle actually exist on the live
>   opcode, and on WHICH tab. If they don't, the opcode's parts may be empty and the root cause lies
>   elsewhere (the menu package itself, or a parent/catalog opcode) — flag to Joe, do not improvise.
>
> **VERIFIED LIVE BEHAVIOR (2026-06-25, TEK04020101 @ SCT 876 — adding the part DID reveal more):**
> - The Default→Parts add-row Part Name field is a **tekion-select (react-select) combobox**, NOT a
>   plain text input (placeholder-based input search returns nothing). Leftmost control in the row
>   band (y≈419): width≈267, center x≈238. Quantity = ant-input-number at x≈442; Price = ant-input-
>   number placeholder "0.00" at x≈708. The `/type` endpoint needs `{selector,text}` (NOT `{text}`
>   alone — bare `{text}` returns HTTP 400). Tag the combobox input with a `data-jay` attr and type
>   into it by selector.
> - Typing `87139-06030` into the combobox returned TWO options: `Create "87139-06030"` (IGNORE —
>   the create-new fallback) and the real catalog row `87139-06030 - ELEMENT, AIR REFINER` (PICK this).
> - **Selecting the real part populated the row** — and the row's only right-side control is an
>   `icon-trash` button at x≈812. **NO ⋮ kebab appears on the Default-tab row, even after hover**
>   (dispatched mouseover/mouseenter up the ancestor chain → still only trash; vision confirmed no
>   ⋮, no horizontal scroll hiding one).
> - **The ⋮ overflow/"Replace Part Number" menus live on the OVERRIDES tab parts table**, not Default:
>   a kebab scan found `icon-overflow` elements inside the `ro_opcodeOverrides_tableContainer` at
>   x≈2568-2616 (rendered far off-screen to the right). So Joe's screenshot with the populated
>   "Modify System Parts" table + ⋮ + "Remove System Parts" toggle was the **Overrides** parts view,
>   despite its header reading "Default" in the thumbnail.
> - CONCLUSION (pending Joe's final confirm): the type→⋮ Replace-Part-Number flow belongs on the
>   **Overrides tab → Parts**, not Default. The Default-tab add-row is just an add/trash builder with
>   no replace action. If you accidentally added the original part on the Default tab, delete that
>   stray row before redoing the flow on Overrides.
> - **REUSABLE PROBE SNIPPET** (find where the ⋮ replace menus are):
>   `[...document.querySelectorAll('[class*="icon-overflow"],[class*="overflow"]')].filter(e=>e.offsetParent)`
>   — if matches sit inside `*opcodeOverrides*` container / x far right, they're on the Overrides table.
> - **`singleValue` DOM read ≠ committed rows TRAP:** querying `[class*="singleValue"]` for part text
>   returns the part-dropdown OPTION list (e.g. all 13 cabin-filter catalog parts 87139-47010-83, YZZ96,
>   33010, 07010…), NOT the actual committed table rows. Vision (screenshot) is the truth for how many
>   real rows exist; the DOM `singleValue` count will mislead you into thinking a tab is populated when
>   it's empty. Always cross-check row count with `browser_vision`, not just `singleValue` length.
> - **`/type` endpoint payload:** the persistent-browser-server `/type` needs `{selector, text}` — bare
>   `{text}` returns HTTP 400 "Bad Request". Tag the target combobox input with a `data-jay` attr via
>   /eval, then `/type {"selector":"[data-jay='pname']","text":"87139-06030"}`.
> - **NEVER-GUESS PAID OFF HERE:** Joe repeatedly corrected the surface mid-task and was emphatic about
>   not touching Default. When the live DOM diverged from the documented method (no ⋮ on Default row),
>   stopping to ask rather than forcing a click was the right call — the documented "Modify System Parts"
>   method was simply wrong for this opcode. Trust live evidence over stale skill steps; flag the
>   divergence to Joe.

⚠️ **READ THIS FIRST if the opcode starts with `TEK`** (a factory/Tekion-catalog opcode,
e.g. `TEK04020101 - Cabin Air Filter Remove and Replace`). A factory TEK opcode is fixed a
COMPLETELY different way than the CABIN/RACF custom opcodes the rest of this skill covers —
**there is NO Make/Model/Year/Trim vehicle-row builder for the part swap.** Do NOT use
`__buildRow`/`__buildRow2` or the cascading react-select method for a TEK part swap.

**The mechanic = a per-row part-SUBSTITUTION rule on the OVERRIDES tab vehicle-row builder
(NOT a standalone "Modify System Parts" table — that was a wrong earlier hypothesis):**
1. Opcode Management → `/ro/opcode/edit/<TEKOPCODE>` → **Overrides** tab → **Parts** (left sub-nav).
2. The Overrides→Parts surface is the **vehicle-row builder**: rows of Make/Model/Year/Trim, each with
   a kebab (⋮) menu. Pick (or create) the vehicle row whose Make/Model/Year actually covers the
   vehicles that pull the wrong part. **Expand that row** (far-left caret) to reveal its parts.
3. **ADD the ORIGINAL (wrong) part number** into that row's parts (the one Tekion currently pulls,
   e.g. `87139-06030`). Part Name is a tekion-select combobox: type the number, pick the real catalog
   option (`87139-06030 - ELEMENT, AIR REFINER`), NOT the `Create "..."` fallback.
4. On that part's row, click the **3-dots (⋮)** → **"Replace Part Number"** → enter the **NEW** part
   number (e.g. `87139-YZZ81`).
5. This writes a **part-substitution rule scoped to that override row**: whenever Tekion sees the OLD
   part on this opcode for the matched vehicles, it auto-uses the NEW part. Joe describes this as the
   "all that take the 06030" scope — verify the row's vehicle scope is broad enough to catch them all.
6. It lives on the **Overrides** tab, so the factory **Default** is not altered. **DO NOT touch Default.**
7. **Save** (configure everything, hit Save once — Joe's rule). STOP for explicit go before Save
   on live data; record the pre-change state for a clean revert.
8. **Verify** by re-quoting the affected VIN+interval (toggle "Add Menu Services as separate
   operations" ON only if you need to explode — and flip it OFF immediately after) and confirming
   the line now pulls the new part.

**Why TEK is different (mental model):** custom opcodes (CABIN/RACF/BGCVTF) carry per-vehicle
override ROWS; factory TEK opcodes carry a fixed system parts list, and you override by mapping
old-part → new-part. Pick the surface by opcode prefix: **`TEK…` = this Modify-System-Parts
replace method; everything else = the vehicle-row method below.**

**Explode-toggle standing rule (Joe 2026-06-25):** flip "Add Menu Services as separate
operations" OFF **automatically and immediately** the moment the opcode is identified — don't
ask. (`/ro/service-menu-setups/settings`, has its own Save button — must Save both ON and OFF.)

---

## ⚡ TL;DR — The Proven Loop (CABIN/RACF custom-opcode vehicle-row method)

**⭐ PRODUCTION METHOD (2026-06-10): unattended batch via persistent-browser-server + `__buildRow2`.**
20+ rows/hour, no OTP churn, no blank-outs. See "Unattended Batch (Persistent Browser)" section
below and `scripts/buildrow2.js` + `scripts/batch_template.py`. The browser-tool approaches below
remain valid for interactive/debug work.

**Browser tool is the ONLY engine for vehicle override batch work.** Headless Playwright cannot
render the vehicle override table (Copy buttons return 0, checkbox dropdowns never open).
The browser tool works but blanks every 2-3 turns.

**Two approaches, pick based on context:**

### Approach A: `__buildRow` helper (from scratch, for the FIRST row discovery)
NEW empty add-row at bottom of grid. Uses JS-only Make→Model→Year→Part→Price. ⚠️ Model
step frequently fails (react-select hidden-input trap) — prefer COPY approach for production.

### Approach B: COPY button (PREFERRED — PRODUCTION BATCH METHOD)
1. Find ANY saved row sharing the same Make (e.g., Toyota) in the Parts grid.
2. **`browser_click` or JS-click the Copy icon** on that row → duplicate row appears.
3. **Model change (browser_click on Model cell → checkboxes appear inline → uncheck old, check target model → Escape to close).**
   The Model cell is an `ant-dropdown-trigger` with **checkbox multi-select** (NOT react-select!).
4. **Year swap (browser_click Year cell → checkboxes appear inline → uncheck old, check target years → Escape to close).**
   The Year cell is also an `ant-dropdown-trigger` with **checkbox multi-select** (NOT react-select!).
5. Expand row → set **Part** via `__setVal` + `__commitOpt`.
6. Set **Price** via `__setVal`.
7. **Save:** JS-click `#btnSalesSetupSave` [1], handle "Save Changes?" modal (Apply each row → modal Save).
8. **Verify:** reload → Overrides → Parts to confirm persistence.

**Why Copy wins:** Pre-fills Make + all vehicle dropdowns, avoiding the react-select
hidden-input trap entirely. Only Model/Year/Part need changes. Year swap is fast
(24 checkbox clicks in one browser_console call).

### PROVEN RECIPE (browser tool only — API-verify before trusting)

This sequence has worked for single-model batches in the browser tool. **⚠️ Always API-audit first**
(see Rule 0) — do NOT rely on prior claims about row counts. The browser tool blanks every 2-3 turns,
so ~3-5 rows per session is realistic.

**Per-row sequence (~30s):**
1. **Copy** an existing row sharing the same Make: `div.icon-copy2` or JS-click `[data-test-id$="-rowCopy"]`
2. **Year swap** (if needed): `browser_click` year cell on the copy → `browser_console` toggle react-select checkboxes:
   ```js
   var divs = document.querySelectorAll('.css-11unzgr > div[id*="react-select-"]');
   var deselect = ['2010','2011',...]; var select = ['2003','2004',...];
   for (var i=0; i<divs.length; i++) {
     var text = divs[i].textContent.trim();
     var cb = divs[i].querySelector('input[type="checkbox"]');
     if (deselect.includes(text) && cb.checked) divs[i].click();
     if (select.includes(text) && !cb.checked) divs[i].click();
   }
   ```
   Close: `document.body.click()` or click page header.
3. **Part + Price + Save**: inject helpers (once/session) → `__setVal(pin, '87139-YZZ81')` → wait 3s → `__commitOpt(/^87139-YZZ81/)` → `__setVal(priceInp, '21.99')`
4. **Save**: `window.__fire(document.querySelectorAll('#btnSalesSetupSave')[1])`
5. **Modal**: handle if present — click Apply → modal Save (JS or browser_click refs)
6. **Verify**: SPA-reload `/ro/opcode/edit/CABIN` → click Overrides → click Parts (Reload Trap!) → confirm row visible
     var optDivs = document.querySelectorAll('.css-11unzgr > div[id*="react-select-"]');
     var deselect = ['2003','2004','2005','2006','2007','2008','2009'];
     var select = ['2010','2011',...];
     for (var i=0; i < optDivs.length; i++) {
       var text = optDivs[i].textContent.trim();
       var cb = optDivs[i].querySelector('input[type="checkbox"]');
       if (deselect.includes(text) && cb.checked) optDivs[i].click();
       if (select.includes(text) && !cb.checked) optDivs[i].click();
     }
   })()
   ```
   Then press Escape to close. This avoids 20+ manual checkbox clicks.
4. **Part change via helpers** — inject helpers ONCE, then: `__setVal(pin, '87139-YZZ82')` → wait 3s → `__commitOpt(/^87139-YZZ82 - /)` to commit the react-select option.
5. **Price**: set via helpers — `__setVal` or native setter + input/change/blur events.
6. **Save**: `__fire` on `#btnSalesSetupSave[1]` works fine (synthetic click is OK for Save button, unlike Trim radio which requires real click).
7. **"Save Changes?" modal**: Use `browser_console` to click "Apply" then "Save":
   ```js
   // Click Apply
   [...document.querySelector('.ant-modal-content').querySelectorAll('button')]
     .find(b=>b.textContent.trim()==='Apply'&&b.offsetParent)?.click();
   // Wait 500ms, then click Save
   [...document.querySelector('.ant-modal-content').querySelectorAll('button')]
     .find(b=>b.textContent.trim()==='Save'&&b.offsetParent)?.click();
   ```
8. **Verify**: SPA reload (`/ro/opcode/edit/CABIN`) → click Overrides → click Parts (Reload Trap!) — confirm both rows visible.

**Why Copy wins:** It pre-fills Make + all vehicle dropdowns, avoiding the react-select hidden-input trap (`__buildRow` can't populate Model/Year without clicking the cells open first). Batching via Copy is ~30s per row vs ~60s for `__buildRow`.

### Post-row for BOTH approaches:
7. **Reload (`window.location.href` to opcode edit URL) → re-click the Parts sub-tab → re-read the API.** After SPA reload, the Overrides grid defaults to the **Labor** sub-tab which shows EMPTY rows. You MUST explicitly click the **Parts** sub-tab to see your committed rows. Then API-verify to confirm backend persistence.
8. Re-inject helpers after every reload/blank-out. Verify via API every ~8 rows.

---

## ⭐ Unattended Batch (Persistent Browser) — PRODUCTION METHOD (verified 2026-06-10)

Working scripts live in `/home/itadmin/tekion-operator/` (`batch_cabin_bt.py`,
`buildrow2.js`, `cabin_dataset.py`). Copies in this skill's `scripts/` dir.
Solves the blank-out problem entirely: the persistent-browser-server (port 9223,
`tekion-computer-use` / `persistent-browser-server` skills) keeps one logged-in Chrome
alive, and a Python loop drives it via HTTP. 20+ rows added at BT in one run.

**Per-row loop (Python, via `/eval` + `/click`):**
1. `goto_parts_tab()` — SPA-navigate to `/ro/opcode/edit/{OPCODE}` if needed, click
   **Overrides** top tab (`.ant-tabs-tab:text-is('Overrides'):visible`), then **Parts**
   left panel (`div[class*='leftPanelItem']:text-is('Parts'):visible`), then VERIFY the
   active item is "Parts". This guards against the Labor sub-tab trap.
2. Re-inject `override-helpers.js` + `buildrow2.js` (wiped on every reload).
3. `__buildRow2({make, modelExact, years, part, price})` via `/eval` (~30-60s; the
   `/eval` endpoint awaits Promises). Check log for `ERR:`.
4. Real Playwright click: `/click {"selector": "#btnSalesSetupSave >> nth=1"}`.
5. Handle "Save Changes?" modal if present (Apply ×N → modal Save).
6. **API read-back** (`GET .../override/PARTS`): confirm a row with this model + picked
   years exists. Only then count it OK.
7. On failure: SPA-reload to discard partial state, re-do step 1, continue. Abort after
   3 consecutive failures.

**`__buildRow2` improvements over v1 (all were real failure modes):**
- **Menu selector**: year dropdown menu class is emotion-generated (e.g. `css-1luefhm-menu`),
  NOT always `.css-11unzgr`. Use `[class*="-menu"]` with visible+has-options filter.
- **Polling instead of fixed sleeps**: Tekion dropdowns load slowly and inconsistently;
  fixed `setTimeout` waits caused intermittent `avail=` empty / `ERR:no-modal`. Poll up to
  ~10-15s for each dropdown/modal to appear.
- **Virtualized year list scrolling**: scroll the overflow child of the menu page-by-page,
  picking matching years on each pass, until no new options appear or all wanted years picked.
- **Duplicate-model row targeting**: `__findModelRow(model)` returns the FIRST row with that
  model — wrong when a saved row for the same model already exists (trim modal then opens on
  the SAVED row and the new row is left trim-blank → save drops it). `findOurRow()` matches
  model AND picked-years AND blank-trim preference.
- **Trim verify + retry**: after the trim modal Save, re-read the row's trim input value;
  retry the modal once if still blank. Returns `ERR:trim-not-set` instead of saving a doomed row.
- **`ERR:no-years-available`**: Tekion's year list for some models (Avalon Hybrid ≤2016,
  Camry Hybrid ≤2016) is narrower than the PDF. Treat as data-gap SKIP (don't count toward
  consecutive-failure abort), reload to discard the partial row, flag to Joe.
- **`ERR:no-trim-modal` / "No Trims Available"**: some model+years (e.g. Tundra Hybrid
  2WD/4WD 2024 at BT) open a trim modal that says **"No Trims Available"** with a DISABLED
  Save — Tekion has no trim data, so the row can NEVER be completed. Hard data gap: Cancel
  the modal, SPA-reload to discard, skip permanently. Don't retry.
- **Scion model dropdown sticks open**: after committing a Scion model the dropdown stays
  open and contaminates the cell text ("FR-SAllFR-SiAiM..."), breaking exact-match row
  finders. `__buildRow2` force-closes (body click + Escape) and uses a tolerant matcher
  (`text === model || text.startsWith(model + 'All')`).
- **Scion (and possibly other makes): model dropdown stays OPEN after commit**, contaminating
  the cell text (`__modelText` returns "FR-SAllFR-SiAiMiQtCxAxBxD" instead of "FR-S") →
  `ERR:no-model-row` for every Scion row. Fix (in buildrow2.js): after model commit, force-close
  with `document.body.click()` + Escape keydown, AND use a tolerant matcher that accepts
  `text === model || text.startsWith(model + 'All')`.
- **Trim modal intermittently doesn't open on first fire** (seen on Tundra Hybrid 2WD/4WD with
  only 1 year option). buildrow2.js retries the trim-modal open once before giving up with
  `ERR:trim-not-set`.

**Dedupe on restart**: compare model + normalized part + year-overlap against the API
read-back, so re-running the batch after a crash skips committed rows.

**Stray placeholder rows from failed attempts**: rows that half-built and got saved without a
real part show up in the API as `customParts: [{partNumber: null, partName: "CABIN", price: 30}]`
— the opcode's default placeholder, NOT the intended filter. After any batch, audit for
`partNumber === null && partName === "CABIN"` and delete those rows via the grid trash icon
(`[class*="icon-tr"]`, synthetic fire works) + Save. Delete higher grid indexes FIRST so lower
indexes don't shift. API `order` field is 1-based position among override rows; grid groupIdx
= order + 13 (groups 0-13 are the pricing table).

**Post-batch verification checklist (run ALL of these):**
1. PARTS row count matches expected (added + pre-existing − deleted strays)
2. LABOR endpoint returns 0 rows (no wrong-tab leakage)
3. Zero rows with `partNumber: null` placeholders
4. Every row's customerPay/warrantyPay/internalPay overriddenPrice == target price
   (⚠️ top-level `unitPrice` is often null — read `customerPay.overriddenPrice` instead)

**Costly pitfall — silent wrong-tab "successes"**: a GR Corolla test row built on the Labor
sub-tab saved fine (to LABOR) while every PARTS read-back showed nothing. If save "fails"
but the button click clearly fires, CHECK THE OTHER SUB-TAB'S ENDPOINT before debugging
the save mechanism.

---

### Rule 0 — ALWAYS API-AUDIT FIRST (before every batch)
**Never trust claims about override row counts — not even from this skill.** The UI grid lies,
prior-session claims can be wrong, and rows may not have persisted. Before starting ANY override
batch, run the `tekion-opcode-api` audit to get the true committed floor. Confirmed 2026-06-09:
skill claimed "46 rows at BT" but API showed only 2. Hours wasted building on a false premise.

- **`python3 audit.py`** (or equivalent) → get `{model, years, part, price}` for every committed row.
- Reconcile your todo list against the API truth, not the UI or prior session claims.
- Re-audit after every ~8 saves to confirm rows actually committed.
- If the audit count doesn't increase after a save: the save didn't persist. Do NOT keep adding rows.

### Rule 1 — TRIM must be set with a REAL `browser_click`, never synthetic
The trim modal's "All trims (including future trims)" radio **cannot** be set with
synthetic `__fire`/`MouseEvent` dispatch — it silently no-ops, leaving the row with a
**blank trim**. A blank-trim row is INVALID: it jams the Save confirmation modal and
silently reverts on reload.
- **FIX:** after `__buildRow()` fills Make/Model/Year/Part/Price, set the trim radio with
  a real `browser_click` on its ref (snapshot first — refs shift every render), then
  real-click the trim modal's **Save**. Confirm cell[5] reads "All trims selected" before
  the main Save.
- A COMPLETE row (with trim) commits via a single main Overrides Save with **no
  confirmation modal**. The modal only appears when rows have un-applied model/year changes.

### Rule 2 — The UI grid LIES about row counts; the API is truth
The Overrides grid frequently renders EMPTY or wrong even when all rows exist in the
backend (a render bug, not data loss). A `__save()` returning "saved" and an incrementing
in-session count are **NOT proof of a backend commit**.
- **ALWAYS** read the committed state via the backend API (`tekion-opcode-api`) at the
  START of a session (to get the true floor) and AFTER saving (to confirm persistence).
- **🪤 RELOAD TRAP (corrected 2026-06-10):** After SPA reload, the opcode edit page lands on
  the **Default TOP tab**. You must click **Overrides** (top tab) → then the **Parts** item in
  the left panel (the Overrides view may default to **Labor**). Building rows on Labor saves
  them as LABOR overrides (see the Labor Sub-Tab Trap section). Always verify the active
  `leftPanelItem` is "Parts" before building, and don't panic about "missing" rows — click
  Parts first.
- Reload-verify (`window.location.href` SPA reload) + re-click Parts sub-tab + API read is the only truth.

### Rule 3 — Browser tool IS the execution engine (Playwright headless CANNOT see the vehicle override grid)

**This is a hard blocker, not a preference.** As of 2026-06-09, Playwright headless Chromium:

- **Cannot render the vehicle override grid at all.** Groups 14+ (the `rt-tr-group` elements
  that hold Make/Model/Year/Trim override rows) appear as placeholder text ("SelectSelect...")
  with no saved row content. Copy buttons return count=0. Existing override rows are invisible.
- Cannot open `ant-dropdown-trigger` checkbox multi-selects (Model cells). JS `.click()`,
  `__fire()`, and Playwright `page.click()` all fail.
- Cannot commit react-select options (Year cells) — dropdowns stay at 0 visible options.

**Headless CAN handle**: login, OTP, dealer switch, navigation to CABIN, Overrides tab click,
Parts sub-tab click. The Parts pricing grid (groups 0-13) renders. But the vehicle override grid
(groups 14+) is completely inaccessible in headless.

**All vehicle override work MUST use the browser tool** (real Chrome via Browserbase). No
exceptions. Do NOT attempt headless Playwright batches for override rows — they will fail
100% of the time (confirmed: 0/45 rows saved, 2026-06-09).

### Rule 4 — Browser ref system degrades after ~15-20 turns
After prolonged use, `browser_click` calls start failing with `"Unexpected token @ while parsing css selector"`. **Fix:** `browser_navigate` to the opcode edit URL for a fresh session. The refs reset. Re-inject helpers after the fresh load.

### Rule 5 — Snapshot truncation hides rows 3+
The browser tool snapshot has a 121-element default limit. Since the page header + tabpanel consume ~60 elements, and each vehicle override row adds ~30-60 elements (more when dropdowns are open), only the **first 1-2 vehicle override rows** are visible in the snapshot. Ref-labelled cells for rows 3+ are **never accessible**. Workaround: use row 1 or row 2 as the template — modify it, copy it, then revert. Or scroll the target row into view and snapshot immediately to capture its refs before truncation.

### Rule 6 — Browser tool blank-out limits batches to ~3-5 rows per session

The browser tool blanks to `about:blank` after 2-3 turns, requiring full re-login (OTP).
Combined with 5-10 turns per row (snapshot→click→snapshot→dropdown fight→snapshot cycle),
the browser tool is **practical for ~3-5 rows per session**. For 40+ row batches, expect
10-15 login cycles over several hours. Not suitable for unattended automation.

**After blank-out, navigating via simple URL often shows a minimal UI** (8 elements: clock,
bell, no dashboard) even with valid localStorage tokens. A fresh `browser_navigate` to the
login page + full OTP login is usually required.

**Mitigation strategies:**
- **3-5 rows per session**: login → Overrides → Parts → process 3-5 rows → save → reload-verify → move on.
- **Copy-template approach**: Use row 1 as a mutable template (change Model/Year, copy it, revert row 1).
  This avoids the snapshot truncation issue for rows 3+.

### Rule 7 — Model dropdown checkboxes are INLINE in the cell (NOT a portal)

Unlike react-select portals (which append to `<body>`), the Model checkbox multi-select renders
**as DOM children of the grid `<td>` element**. When the Model cell is clicked, the checkboxes
appear directly inside the `rt-td` — they are NOT in a separate `.ant-dropdown` or `.ant-popover`.

**Consequences:**
- `.ant-dropdown-hidden` tricks do nothing (the checkboxes aren't in an ant-dropdown).
- `document.body.click()` and Escape key both fail to close the inline list (confirmed 2026-06-09).
- The only reliable close: click the Model cell AGAIN to toggle it closed, OR click the Year cell
  (which often auto-closes the Model list), OR SPA-reload.
- JS `.click()` on `.ant-checkbox-wrapper` elements DOES work for toggling — but only AFTER the
  list is opened by a real `browser_click` on the cell.

**Workaround for closing:** After setting model checkboxes, immediately click the Year cell
(via `browser_click`). The Year react-select opening usually forces the model inline list to
collapse. If it doesn't, SPA-reload is the only recovery.

### Rule 8 — The "All" checkbox DANGER
Clicking the "All" checkbox at the top of the model/year dropdown checks EVERY model/year in the list. This instantly corrupts the row. **NEVER click "All" unless you genuinely want every model selected.** If accidentally clicked, you MUST SPA-reload to discard the corrupted row — do NOT save.

### Rule 9 — Confirm Navigation dialog redirects to "Create Opcode"
When the "Confirm Navigation" / "Save Changes?" modal appears, clicking "Save" on the modal sometimes navigates to the "Create Opcode" page instead of staying on the CABIN edit page. This is a Tekion SPA bug. **Recovery**: `window.location.href = '/ro/opcode/edit/CABIN'` to return. If the Overrides tab is disabled (indicating the navigation happened mid-save), do a fresh navigation and re-check the Parts sub-tab to verify what actually saved.

---

## Reaching the Override Row Safely

### Template Row Workaround (for snapshot truncation)

When the snapshot truncates rows 3+, use **row 1 or row 2 as a template**:
1. `browser_click` row 1's Model cell → checkboxes appear with refs
2. Set the DESIRED model (uncheck current, check target) via `browser_click`
3. Close dropdown → `browser_click` row 1's Year cell → set desired years
4. **Copy** row 1 (now showing the target model/years) → the copy appears BELOW
5. **Revert** row 1: re-open Model dropdown → re-check original model → close. Re-open Year → re-set original years.
6. The copy (row 3+) is now populated with the target model/years. Interact via `browser_console` to expand it, set Part/Price, and Save.

This works because row 1 and row 2 checkboxes are always visible in the snapshot. Only rows 3+ are truncated.

- ⚠️ **NEW overrides go in a FRESH empty bottom row, NEVER row 0.** A populated Parts
  sub-tab keeps a persistent empty row at the very bottom (below the last `trim_N`). That
  empty row IS the add mechanism — fill its Make/Model/Year/Trim and a new empty row spawns
  below. Editing row 0 by coordinate **OVERWRITES the first existing override** (verified:
  accidentally turned a 4Runner override into a Prius). 
- Count existing rows BEFORE editing: `document.querySelectorAll('input[id^="trim_"]').length`.
  If > 0, you must use the bottom empty row, never edit in place.
- **Recovery if you edit/break the wrong row:** do NOT save. `window.location.href='/ro/opcode/edit/RACF'`
  (SPA reload) discards ALL unsaved React state and restores the last-committed baseline.
  SAFE on live data.
- **Viewport-edge trap:** the empty add-row sits near the bottom of the viewport; its
  Model/Year dropdown can render off-screen so option queries return 0. `scrollIntoView({block:'center'})`
  on the row's Make input before driving it.

---

## Opcode Structure Variants (CRITICAL — CABIN ≠ RACF)

**Not all opcodes use the same vehicle override row structure.** The `__buildRow()` helper was
built for the **RACF** opcode which has per-row part selection. Other opcodes may differ:

### RACF (Stevens Creek Toyota) — HAS per-row part input
The expanded sub-row shows the `customPartsMenuActionId` input where you select a specific part
number. Each vehicle row can have a different part (e.g. 4Runner 2003-2009 = 87139-YZZ81,
4Runner 2010-2026 = 87139-YZZ82).

### ⚠️ RESOLVED 2026-06-10: "CABIN has no part input" was FALSE — it was the LABOR SUB-TAB TRAP
Earlier sessions concluded CABIN at BT had no per-row part input and that saves "didn't
persist." Both observations were artifacts of being on the **Labor sub-tab**, not Parts:

- **After ANY reload, the opcode edit page lands on the DEFAULT top tab.** You must click
  the **Overrides** top tab, THEN the **Parts** item in the left panel. If you build rows
  while the **Labor** sub-tab is active, everything LOOKS identical (same grid, same
  Make/Model/Year/Trim cells) but: (a) the expanded sub-row shows only labor hour/rate
  fields (hence "no part input"), and (b) **Save silently POSTs to
  `/api/service-module/u/opcode/{OPCODE}_{dealerId}/override/LABOR`** — the row persists
  as a LABOR override, invisible to the PARTS API read-back. That's why saves seemed to fail.
- **Diagnostic that cracked it:** hook XHR before clicking Save and check which endpoint fires:
  ```js
  var oo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(m, u) {
    if (m !== 'GET') (window.__netLog = window.__netLog || []).push({method: m, url: String(u)});
    return oo.apply(this, arguments);
  };
  ```
  `.../override/LABOR` = wrong sub-tab. `.../override/PARTS` = correct.
- **Verify active sub-tab before building:** the active left-panel item has an
  `active`/`selected` class on `[class*="leftPanelItem"]`. Check it returns "Parts".
- **Cleanup of stray LABOR rows:** click Labor sub-tab → trash icon (`[class*="icon-tr"]`)
  on the row → Save → verify `GET .../override/LABOR` returns 0 rows.

On the **Parts** sub-tab, CABIN behaves exactly like RACF: per-row part input
(`customPartsMenuActionId`) exists, `__buildRow`/`__buildRow2` works, and a real Playwright
click on `#btnSalesSetupSave >> nth=1` persists rows (verified: 20+ rows added at BT).

## The Cascading Fields — Exact Behavior

| Field | Widget | How to drive |
|-------|--------|--------------|
| **Make** | typeable react-select (`input[id^="@tekion-repair-orders-opcodeManagementV2-vehicle"]`) | native-setter value + `input` event opens menu → commit option via `[id^="react-select-"][id*="-option-"]` with mousedown→mouseup→click. **makeRx must be CONTAINS (`/Toyota/`) not anchored** — after commit the cell text becomes an a11y string. |
| **Model** | `ant-dropdown-trigger` with **checkbox multi-select** (NOT react-select!) | Click the gridcell → portal opens with `input[type="checkbox"]` elements for each Toyota model → uncheck old model(s), check target model → click outside to close. Can toggle via JS: `cb.click()` on the checkbox element. |
| **Year** | **react-select multi-select** (`.css-11unzgr > div[id*="react-select-"]`) with native `<input type="checkbox">` per year | Click the gridcell → react-select portal opens with all years. Toggle via `browser_console` JS: find `.css-11unzgr > div[id*="react-select-"]`, filter by text, `.click()`. Close with `document.body.click()`. All years visible, no scrolling. |
| **Trim** | `ant-modal` (engine-filter dialog) | **REAL `browser_click`** the "All trims" radio → real-click modal Save. (See Rule 1.) Engine-filter + "Specific trims" only when the PDF splits a year range by engine. |
| **Part** | expandable sub-row react-select (RACF ONLY) | expand row via `[data-test-id$="-expanderIcon"]` → part input id `@tekion-repairOrders-opcodeManagementV2-customPartsTableCols-customPartsMenuActionId` (use `[id="..."]` attribute selector — the `@` breaks `#id`). native-setter + input, wait ~3s, commit the **catalog match** (e.g. `/^87139-YZZ81 - ELEMENT/`), NEVER the `Create "..."` fallback. **⚠️ ONLY EXISTS on RACF; CABIN at BT has no per-row part input.** |
| **Price** | `#customerPayUnitPrice_undefined` | native-setter + input/change/blur. Price is store-specific: RACF @ Stevens Creek = **$30.88**, CABIN @ Blackstone = **$21.99**. |

## Copy Button — The Fast Path for Similar Rows

When you already have one saved row with the same Make (e.g., a 4Runner override), the **Copy** button creates a pre-filled duplicate much faster than `__buildRow`. This avoids the react-select hidden-input trap entirely.

- **Copy button: `<button>` with `alt="row-copy"` or `[data-test-id$="-rowCopy"]`** inside each `.rt-tr` row.
- After clicking Copy, a duplicate row appears at the bottom of the grid with ALL vehicle fields pre-filled.
- Then you only need to: (1) change Model via real-click, (2) change Year via real-click, (3) change Part, (4) confirm Price, (5) set Trim.
- **Delete a bad copy row** via the Cancel/remove button (same row, `[alt="row-delete"]` or equivalent) — do NOT save a broken row.
- **The Copy row inherits the source row's saved state** — if the source committed cleanly, the copy starts clean too (no stuck "un-applied changes").

## Two Separate Tables on the Parts Tab (CRITICAL)

The Overrides → Parts tab renders **two independent ReactTable grids** stacked vertically:

### Table 1: Parts Pricing Grid (`rt-tr-group` groups 0-13)
Default pricing rows: W/I/CP/Labor rows, the CABIN opcode part row, BG7073 override, discount rows.
These are NOT vehicle-specific.

### Table 2: Vehicle Override Grid (`rt-tr-group` groups 14+)
Make/Model/Year/Trim vehicle-specific override rows. Each row has **8 `.rt-td` cells**:
- **cell[0]**: Expander icon (icon-caret-down)
- **cell[1]**: Drag icon (icon-drag-and-drop)
- **cell[2]**: Make — react-select (`makeId_N`)
- **cell[3]**: Model — **checkbox multi-select** (`ant-dropdown-trigger`)
- **cell[4]**: Year — **checkbox multi-select** (`ant-dropdown-trigger`)
- **cell[5]**: Trim — select/button
- **cell[6]**: Notes icon
- **cell[7]**: Trash + Copy buttons

**In a clean session** (no existing vehicle overrides), there are ZERO vehicle override rows. The Copy approach only works when at least one override row already exists. When there's no row to copy, use the **bottom "Select" row** to create the first override from scratch.

## ⚠️ CRITICAL: Model & Year Are CHECKBOX Multi-Selects (NOT React-Select)

**Verified 2026-06-08 in real browser (browser tool).** The Model and Year dropdowns in the vehicle override grid are simple **HTML checkbox multi-selects** — NOT react-select components. This is fundamentally different from what the Make field uses.

### Model Dropdown DOM
- Trigger: `ant-dropdown-trigger` with chevron icon on the gridcell
- Content: **ant-design checkboxes** (`.ant-checkbox-wrapper` with `.ant-checkbox-checked` class, NOT native `<input type="checkbox">`!) — each paired with a text label
- When clicked open via **real `browser_click`**, the gridcell EXPANDS to show checkboxes INLINE within the cell itself (not in a body-level portal)
- Each checkbox + label pair represents one Toyota model (e.g., "4Runner", "Avalon", "Camry")
- Checked state: `.ant-checkbox-wrapper-checked` on the label, `.ant-checkbox-checked` on the inner span
- To toggle: `browser_click` on the checkbox ref from the snapshot. JS `.click()` on the `.ant-checkbox-wrapper` label also works (unlike native `.click()` on `<input>`)

### Year Dropdown DOM
- **NOT the same as Model!** Year is a **react-select multi-select** (`.css-11unzgr > div[id*="react-select-"]`), NOT an inline ant-design checkbox list
- Each option div contains a native `<input type="checkbox">` — check `input[type="checkbox"].checked` to determine state
- All 35+ years render in a virtualized list (no scrolling needed)
- **Can be toggled programmatically via browser_console** — unlike Model which requires real clicks on ant-checkbox-wrappers
- To swap years: find `.css-11unzgr > div[id*="react-select-"]` → filter by text → `.click()` to toggle desired years
- Close with `document.body.click()` or clicking elsewhere on the page

### Why This Matters
The `__commitOpt()` helper (which searches `[id^="react-select-"][id*="-option-"]`) will **NEVER find Model/Year options** because they aren't react-select elements. These are simple checkbox lists rendered inline. The only way to interact is via **real `browser_click`** on the checkbox refs that appear in the snapshot after clicking the Model/Year cell. **`browser_console` JS `.click()` on the gridcell itself does NOT trigger the checkbox dropdown** — the ant-dropdown-trigger requires a real browser mouse event (verified 2026-06-08). Even in the browser tool (not headless), JS-only clicks fail on these triggers.

**Correct toggle approach (browser_click on refs):**
1. `browser_click` the Model gridcell (e.g., ref e70 for "4Runner icon-chevron-down") → dropdown opens, checkboxes appear with their own refs (e72="4Runner", e79="Avalon", etc.)
2. `browser_click` the UNWANTED checked checkboxes to uncheck them
3. `browser_click` the target model's checkbox
4. Press Escape to close dropdown
5. Verify the cell text shows only the desired model

**For Year:** same pattern — `browser_click` year cell → checkboxes appear → toggle desired years → Escape.

---

## The Helper Toolkit — `__buildRow()` (inject once per session)

The full verified toolkit is in **`scripts/override-helpers.js`**. Inject it via
`browser_console` at session start and RE-INJECT after every reload/blank-out (helpers
are wiped by `about:blank` and SPA reload).

`__buildRow(opts)` fills Make→Model→Year→Part→Price in one async call. **It does NOT
reliably set the trim** (Rule 1) — you do that separately with a real click.

```
opts = {
  make: 'Toyota',
  makeRx: /Toyota/,            // CONTAINS, not anchored
  modelExact: 'RAV4',
  modelRx: /^RAV4$/,           // optional, defaults from modelExact
  years: ['2018','2017',...],  // strings; pick the intersection with avail=
  part: '87139-YZZ83',
  price: '30.88',
  dedupeModels: ['RAV4 EV','RAV4 Hybrid']  // optional: uncheck substring siblings
}
```

### Promise + poll pattern (browser_console has no top-level await):
```js
// call 1: start
(() => { window.__lastLog='RUNNING'; window.__buildRow({make:'Toyota',makeRx:/Toyota/,modelExact:'RAV4',years:['2026','2025','2024','2023','2022','2021','2020','2019'],part:'87139-YZZ83',price:'30.88'}).then(l=>{window.__lastLog=l;}).catch(e=>{window.__lastLog='ERR:'+String(e);}); return 'started'; })()
// terminal: sleep 30
// call 2: read the audit log
(() => { return {log: window.__lastLog}; })()
```
The `log` array shows each step incl. `avail=` (years Tekion offered) and `picked=`
(years actually selected) — your audit trail. Budget ~28-31s (the builder has ~22s of
internal waits + catalog query time).

### Per-model loop:
1. `__buildRow({...})` → `sleep 30` → read `__lastLog` (confirm `part=...`, `price=30.88`, no `ERR`).
2. **Real `browser_click` the "All trims" radio** → real-click trim-modal Save. Verify cell[5] = "All trims selected".
3. Real `browser_click` Overrides Save (`#btnSalesSetupSave[1]`).
4. If "Save Changes?" modal: real-click **Apply** on the new row (confirm "Applied"), then real-click modal **Save**.
5. Wait ~5s, confirm modal closed.
6. **Reload + API read-back** to confirm persistence. Re-inject helpers.

---

## The "Save Changes?" Confirmation Modal

When rows have un-applied model/year changes, the Overrides Save opens a **"Save Changes?"**
ant-modal listing each changed row with its own **Apply** / **Discard** toggle plus a
modal-level **Save**. The commit ONLY happens after:
1. Real-click **Apply** on EACH listed row (toggle flips "Apply"→"Applied"), THEN
2. Real-click the modal's **Save**.

If you skip the modal, NOTHING persists. **Incomplete rows (missing trim) JAM this modal** —
it stays open and Save does nothing. Recovery: SPA reload discards the stuck row.

Modal selectors: `.ant-modal-content` (filter `offsetParent`). Use the browser tool's
real `browser_click` on refs for Apply and modal-Save — synthetic `__fire` opened the
modal but its Save didn't always respond.

- **`#btnSalesSetupSave` is DUPLICATED:** `[0]` = "Update" (Default tab), `[1]` = "Save"
(Overrides tab). Always use `querySelectorAll('#btnSalesSetupSave')[1]` for Overrides.
- **Synthetic `__fire` WORKS on the Save button** (unlike Trim radio which requires real click).
  Use `window.__fire(document.querySelectorAll('#btnSalesSetupSave')[1])` for speed.

---

## Data-Quality Rules (Cabin Filters — Joe-confirmed)

- **Opcode name and price are STORE-SPECIFIC.** Do NOT assume the same opcode exists across stores.
  - **RACF** at Stevens Creek Toyota = **$30.88**
  - **CABIN** at Blackstone Toyota = **$21.99**
  - Other stores may have different opcode names and prices. Always confirm the opcode name and price from the user/report before starting.
- **Part-pick priority:** use the **Standard Replacement** column part if it has ANY value
  (even if identical to OE). Fall to **Premium Charcoal (CH)** only if Standard blank. Fall
  to **OE** only if BOTH Standard and Premium are blank (`----------`).
- **Finish every year/engine band of a model before moving to the next model.** Map all
  bands up front. Example verified Prius (regular) block = 3 rows:
  - 2001-2009 1NZFXE → 87139-YZZ81
  - 2010-2015 2ZRFXE → 87139-YZZ82
  - 2016-2027 2ZRFXE/M20AFXS → 87139-YZZ83 (both engines share std part → ONE "All trims" row)
- **Single-engine year range → "All trims".** Engine-filter + "Specific trims" ONLY when the
  PDF splits a year range by engine with different part numbers (then one row per variant).
- **Tekion's year list can be NARROWER than the PDF.** Read `avail=` and select the
  INTERSECTION; never block waiting for a year the catalog doesn't list. (e.g. Prius c PDF
  says 2012-2021 but Tekion tops out at 2019.)
- **OE-only overlap rows** (a `----------`/`----------` row duplicating years already covered
  by a real-replacement row, e.g. Prius 2006-2009 87139-47020) — **skip + flag to Joe**, don't
  create an overlapping duplicate.
- **partId format** (for API writes): `M_TMNA_` + partNumber with dashes stripped
  (`87139-YZZ81` → `M_TMNA_87139YZZ81`). partName: `"<dashed-number> - ELEMENT, AIR REFINER"`
  for cabin filters, or `"<num> - FILTER, AIR A/C"` for 88568-series.

### Model-name mappings (PDF → Tekion option, verified)
- "PRIUS PHV" → **"Prius Plug-In"** (2012-2015 only; NOT "Prius Plug-In Hybrid" = 2025+ new model)
- "PRIUS V" → "Prius v"; "PRIUS c" → "Prius c"; "PRIUS PRIME" → "Prius Prime" (caps at 2024)
- RAV4 base 1996-2026; "RAV4 EV" (2012-2014), "RAV4 Prime" (2021-2024), "RAV4 Hybrid",
  "RAV4 Plug-In Hybrid" are SEPARATE Tekion options.
- **Scion is a SEPARATE Make** (iM, xA, xB, xD, tC, FR-S, iA, iQ) — `make:'Scion', makeRx:/Scion/`.
- "SUPRA" 2020+ → **"GR Supra"** (Tekion's "Supra" model ends at 1998).
- "TUNDRA" 2022+ → **"Tundra 2WD" / "Tundra 4WD"** (plain "Tundra" ends at 2007); also
  "Tundra Hybrid 2WD/4WD" exist but only list 2024.
- "TACOMA" → add "Tacoma" + "Tacoma 2WD" + "Tacoma 4WD" (all three exist as separate options).
- "SOLARA" → "Camry Solara"; "86" 2017-20 → "86", 2022+ → "GR86".
- "BZ4X" → both "bZ4X" and "bZ" exist (bZ = 2026 rename).
- Full verified dataset generator: `scripts/cabin_dataset.py` (96 rows, 62 Tekion models,
  PDF→Tekion mapping + part-pick priority already applied — reuse for other stores,
  just change the price).

## PDF Data Extraction (PROVEN — pdfplumber table extraction)

For cabin-filter PDFs (05_CabinAirFilters2024_hi.pdf), use **pdfplumber** — it preserves the model→sub-row relationship perfectly where raw text parsers fail.

```python
import pdfplumber, re
entries = []
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        for table in page.extract_tables():
            if len(table) < 2: continue
            for row in table[1:]:  # Skip header
                model = row[0].replace('\n', ' ').strip()
                sub_text = row[1]  # "year engine OE type\n..."
                parts_text = row[2]  # "std_part type\n..."
                # Split sub_rows by \n, parse year/engine/OE from each
                # Match parts by index from parts_text lines
                # Part-pick: Standard → Premium → OE fallback
```

**pip install pdfplumber** (no GPU needed). This is the ONLY method that reliably extracts the cabin-filter table structure. Raw text (`get_text("text")`) loses column alignment; pdfplumber's `extract_tables()` preserves it.
- **Supra** — OE-only, TWO filters per car (WAA01+WAA02, +WAA03 for 2023).
- **Yaris iA, Scion FR-S / iA / iQ** — OE-only listings; confirm whether to add OE or skip.
- **Scion tC** — table lists parts BUT PDF footnote says it "cannot be retrofitted with a
  Cabin Air Filter." CONFLICT — confirm before adding.

---

## Bulk PRICE EDIT on Existing Override Rows (proven 2026-06-12, 84/84 @ BT CABIN)

Changing prices on rows that already exist is MUCH simpler than adding rows — no `__buildRow2` needed. Working script: `/home/itadmin/cabin-filters-bt/update_price_30.py`.

**Direct API writes are IMPOSSIBLE**: PUT/POST to `/api/service-module/u/opcode/{OP}_{dealer}/override/PARTS` (single row, array, `{overrides:[...]}`, by-id, `/update`) all return 500 `unexpected.error` or 404. The UI grid is the ONLY write path; the GET endpoint stays the read/verify source of truth.

Recipe (persistent browser :9223, already on Overrides → Parts):
1. **Backup first**: GET `/override/PARTS`, save full JSON (rollback insurance).
2. Override rows = `.rt-tr` with ≥6 `.rt-td` AND an expander (`[data-test-id$="-expanderIcon"]` or `.rt-expandable`). Grid shows N+1 such rows — the last is the blank template row; it reports `no-target()` with empty values, expected, skip it.
3. Per row, in ONE `/eval`: click expander → poll up to 10×700ms for `input[id="customerPayUnitPrice_undefined"]` → pick the input whose `.value` equals the OLD price (this naturally leaves other parts in the row alone, e.g. BG7073 Frigi-Fresh) → native-setter set + `input,change,blur` → click expander again to collapse. JS `dispatchEvent` clicks WORK for expanders and inputs (unlike Save buttons).
4. After ALL rows: ONE real Playwright click `#btnSalesSetupSave >> nth=1` (Joe's rule: configure everything, hit Update once). Price-only edits may produce NO confirmation modal — `modal: None` is normal; check but don't fail on absence.
5. Verify via API GET: every target part's `customerPay.overriddenPrice` == new price. ~6s/row.

**Propagation gotcha**: the single grid price input drives customerPay AND warrantyPay AND internalPay — all three end up at the new price. If they must differ, this method can't do it.

**Re-runnable**: if the OLD-price input isn't found but values contain the NEW price, count as `already` and continue — safe after partial runs.

**Session restore into :9223**: if the persistent browser lost the app session, navigate to app origin, inject localStorage items ONE per /eval call from `.tekion-storage-state.json` (bulk injection silently fails on the huge `t_token`/`t_user` values), then re-navigate. Dealer switch: real /click on `[class*='dealerSelect_container']` then JS-click the leaf node with exact text.

## Pitfalls Quick Reference

- **⚠️ ALWAYS API-AUDIT FIRST**: The skill's own claim of "46 rows at BT" was wrong — only 2 existed.
  Audit via `tekion-opcode-api` before every batch. Do not trust prior session state.
- **HEADLESS = 100% FAILURE**: Playwright headless cannot render the vehicle override grid at all.
  Groups 14+ show placeholder text. Copy buttons count=0. Do not attempt.
- **Browser tool = ~3-5 rows/session**: Blanks every 2-3 turns. Plan for 10+ login cycles for 40+ rows.
- **Year-swap shortcut**: When using Copy approach, clicking 20+ individual year checkboxes is slow. Instead: browser_click the Year cell to open the react-select dropdown, then use `browser_console` to programmatically `.click()` each `div[id*="react-select-"]` in `.css-11unzgr` that matches your deselect/select lists. Check `input[type="checkbox"].checked` to determine current state. All 35+ years visible — no scrolling needed.
- **Year dropdown is react-window VIRTUALIZED** — can't scroll, all options visible on open.

- `[class*="-option"]` returns 0 → use `[id^="react-select-"][id*="-option-"]`.
- After Make commit, a new empty row spawns → re-scope by row CONTENT every step.
- makeRx anchored (`/^Toyota$/`) fails to re-find row → use CONTAINS (`/Toyota/`).
- Trim input click does nothing → click the input's `.ant-input-affix-wrapper` parent; set the radio with a REAL browser_click.
- Part `@`-prefixed id breaks `querySelector('#...')` → use `[id="..."]` attribute form.
- Price reads empty in `innerText` → it's an input `.value`.
- Year menu won't scroll → it's virtualized; option text already lists the full range on open.
- Synthetic Save / `__save()` "saved" ≠ committed → real-click + API verify.
- **Don't loop forever**: if a row fails after genuine retries, SPA-reload to clean up, report which models are done, continue.
- **Model dropdown won't close**: Escape/body clicks fail in browser tool. Use JS: `document.querySelectorAll('.ant-dropdown:not(.ant-dropdown-hidden)').forEach(o => o.classList.add('ant-dropdown-hidden'))`.
- **"All" checkbox corrupts row**: Clicking "All" in model/year dropdown selects everything. SPA-reload to recover, never save.
- **Save modal redirects to Create Opcode**: Tekion SPA bug — sometimes navigates away after modal Save. Re-navigate to `/ro/opcode/edit/CABIN` and check Parts tab for what actually saved.
- **browser_console + execute_code is the batch strategy**: For 10+ rows, use execute_code to run all row manipulation via browser_console, then ONE real-click Save. Avoids per-row snapshot grind.
- **Persistent browser server snapshot truncates Save/Cancel buttons**: The ~460-element snapshot cap means
  the bottom-of-page Save/Cancel buttons are NEVER in the snapshot — even after `scrollIntoView`. Ref-based
  clicks won't work. Use the `/click` endpoint with `{"text":"Save"}` (Playwright `page.click('text="Save"')`) 
  to target the button, or use React fiber onClick. Both fire the handler but row persistence is a separate issue
  (see CABIN structural differences above).

## React-Select Hidden Input Trap ⚠️

**Model and Year dropdowns are react-select components that DON'T render their `<input>` element until clicked open.**

When `__buildRow` tries `mc.querySelector('input[id^="@tekion-repair-orders-opcodeManagementV2"]')` on a collapsed Model cell (`rw.children[3]`), it returns `null` because the react-select hasn't been opened yet. The Model field skips silently — log shows `make=Toyota` but no `model=` entry.

**Fix:** The Model cell must be clicked open FIRST (real `browser_click` on the gridcell, or `__fire` on the chevron indicator), then the react-select input appears, THEN type the model name and commit the option.

**Detection:** Run `document.querySelectorAll('[id*="react-select-"][id*="-input"]')` — returns empty array until a react-select dropdown is opened.

**Playwright headless CANNOT open react-select dropdowns (verified 2026-06-08).** Synthetic clicks (`element.click()`, `__fire`, `MouseEvent` dispatch) and even Playwright's `page.keyboard.press('Enter')` all fail to trigger the react-select portal/popper in headless Chromium. The dropdown menu (`[id^="react-select-"][id*="-option-"]`) stays at 0 visible options.

## Playwright Headless — CRITICAL LIMITATION (2026-06-08)

**Playwright headless Chromium CANNOT open Tekion's `ant-dropdown-trigger` checkbox multi-select dropdowns.** This was verified exhaustively:

- `element.click()` (native DOM click) → dropdown does NOT open
- `window.__fire()` (synthetic MouseEvents) → does NOT open
- `page.keyboard.press('Enter')` → does NOT trigger react-select commit
- `page.locator(...).click()` (Playwright native) → does NOT open

The vehicle override rows with Copy buttons also don't render in headless (`4Runner: False`, `icon-copy: False`, `*[class*="copy"]` count = 0).

**Headless CAN handle**: Login, OTP, dealer switch, navigation to CABIN, Overrides tab click, Parts sub-tab click. The pricing grid (groups 0-13) renders. But the vehicle override grid (groups 14+) does NOT load, and checkbox dropdowns never appear.

**RECOMMENDATION**: Use the **browser tool** (real Chrome) for ALL vehicle override operations. The browser tool can open checkbox dropdowns and render the vehicle override table. For batches, use multi-row `browser_console` async calls (5-8 rows per call) to work around the blank-out issue.

When running headless Playwright batches for opcode overrides (instead of browser tool):

### Login + Dealer Switch via browser_console (no refs needed)
When the browser tool's ref-based click fails (e.g., `@` in CSS selectors), use these JS patterns:
```js
// Fill username
(function(){
  var input = document.querySelector('input[placeholder="Type Here"]:not([disabled])');
  var s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
  s.call(input, 'email@domain.com');
  input.dispatchEvent(new Event('input', {bubbles:true}));
})()
### Login + Dealer Switch via browser_console (no refs needed)
When the browser tool's ref-based click fails (e.g., `@` in CSS selectors after page reload), use **browser_console with native JS** — this ALWAYS works because it bypasses the ref system entirely:

```js
// === LOGIN FLOW (all via browser_console) ===
// 1. Fill username with native value setter (React-controlled inputs need this)
var inp = document.querySelector('input');
var n = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
n.call(inp, 'jcastelino@scvolkswagen.com');
inp.dispatchEvent(new Event('input',{bubbles:true}));
inp.dispatchEvent(new Event('change',{bubbles:true}));

// 2. Click Next (find button by text content)
document.querySelectorAll('button')[1].click();  // [0]="Join Waitlist", [1]="Next"

// 3. Wait for password page → fill password
var pw = document.querySelector('input[type="password"]');
n.call(pw, '<TEKION_PASSWORD>');
pw.dispatchEvent(new Event('input',{bubbles:true}));

// 4. Click Login
document.querySelectorAll('button').forEach(b=>{if(b.textContent.includes('Login'))b.click()});

// 5. Wait for OTP page → fetch code via terminal: python3 ~/caliber-ops/scripts/fetch_otp.py
// 6. Fill OTP
var otpInp = document.querySelector('input');
n.call(otpInp, 'OTP_CODE');
otpInp.dispatchEvent(new Event('input',{bubbles:true}));

// 7. Click Verify
document.querySelectorAll('button').forEach(b=>{if(b.textContent.includes('Verify'))b.click()});

// === DEALER SWITCH ===
// 8. Click dealer area (class contains 'dealer', text contains 'Blackstone')
document.querySelectorAll('*').forEach(el=>{
  var c=el.className;if(typeof c=='string'&&c.includes('dealer')&&el.textContent.includes('Blackstone'))el.click()
});
// 9. Click Blackstone Toyota in popover
var pop=document.querySelector('.ant-popover-inner-content');
pop.querySelectorAll('*').forEach(el=>{if(el.textContent.trim()==='Blackstone Toyota')el.click()});

// === NAVIGATE TO OPCODE ===
// 10. SPA navigate
window.location.href='/ro/opcode/edit/CABIN';

// 11. Click Overrides tab → click Parts sub-tab (via JS, must wait for page load)
document.querySelectorAll('[role="tab"]').forEach(t=>{if(t.textContent.includes('Overrides'))t.click()});
// Then find Parts button (any element with textContent==='Parts' and no children)
document.querySelectorAll('*').forEach(el=>{if(el.textContent==='Parts'&&el.children.length===0)el.click()});
```

### Login Selectors (Playwright — for headless batch)
```python
# Username — use placeholder match with :not([disabled]) to avoid stale session phone fields
await page.locator('input[placeholder="Type Here"]').first.fill(EMAIL)
await page.click('button:has-text("Next")')

# Password — must use type="password" because username input is now disabled  
await page.locator('input[type="password"]').fill(PASSWORD)
await page.click('button:has-text("Login")')

# OTP — fetch via fetch_otp.py, then fill + Verify
await page.locator('input[placeholder="Type Here"]').first.fill(otp)
await page.click('button:has-text("Verify")')
await page.wait_for_timeout(8000)

# Dashboard check: "Welcome back" in body
# If still on SMS/Email page: retry OTP once (OTPs expire within ~30s)
```

### Verified Full Login Script (canonical — works every time in headless)
The full login function in `~/cabin-filters-bt/batch.py` (lines ~70-175) handles: goto → username fill → Next → password fill → Login → OTP fetch + fill + Verify → retry if needed → dealer switch to BT → navigate to opcode → Overrides tab → Parts sub-tab → inject helpers. **This pattern works reliably in headless Chromium** — use it as the template for any Playwright Tekion batch script.

### Key Playwright Pitfalls
- **`page.goto(..., wait_until="networkidle")` NEVER completes on Tekion SPA** — the page keeps making background API calls. Always use `wait_until="domcontentloaded"` + explicit `wait_for_timeout()`.
- **`page.locator('input:visible').first` matches DISABLED inputs** — after clicking Next, the username field gets `ant-input-disabled` but is still `:visible`. Use `:not([disabled])` filter.
- **`os.path.expanduser("~")` resolves to Hermes sandbox home** (`/home/itadmin/.hermes/profiles/jay/home`) not the real `/home/itadmin`. Hardcode paths or use `os.environ.get("REAL_HOME", "/home/itadmin")`.
- **JS evaluation is more reliable than Playwright locators for react-select** — `page.evaluate("document.querySelectorAll('[role=\"tab\"]')...click()")` works where `page.click('[role="tab"]:has-text("Overrides")')` times out.

### Session Reuse
```python
# Inject saved localStorage tokens, then navigate to home
with open(SESSION_FILE) as f:
    sess = json.load(f)
await page.goto(LOGIN_URL, wait_until="domcontentloaded")
for k in ["t_token", "t_user", "dse_t_user", "currentActiveIsWorkspace", "currentActiveWorkspace"]:
    if k in sess:
        await page.evaluate(f"localStorage.setItem('{k}', {json.dumps(sess[k])})")
await page.goto(LOGIN_URL + "/home", wait_until="domcontentloaded", timeout=15000)
await page.wait_for_timeout(3000)
# Check if logged in: "Welcome back" in body
```
Sessions valid ~20 minutes after last login. Expired tokens → fresh login with OTP needed.

### Tab Navigation via JS (more reliable than Playwright locators)
```python
# Click Overrides tab
await page.evaluate("""() => {
    const tabs = document.querySelectorAll('[role="tab"]');
    for (const t of tabs) {
        if (t.textContent.trim() === 'Overrides') { t.click(); break; }
    }
}""")
# Click Parts sub-tab
await page.evaluate("""() => {
    const btns = document.querySelectorAll('button');
    for (const b of btns) {
        if (b.textContent.trim() === 'Parts' && b.offsetParent) { b.click(); break; }
    }
}""")

### ⚠️ Dealer switch via Browserbase (JS-only, no refs needed)

The dealer switcher is an Ant Design popover. To switch dealers in one browser_console call:
```js
// 1. Click dealer area (class contains 'dealer' + text contains 'Blackstone')
// ⚠️ className can be an SVGAnimatedString on SVG elements — check typeof first
document.querySelectorAll('*').forEach(el => {
  var c = el.className;
  if (typeof c === 'string' && c.includes('dealer') && el.textContent.includes('Blackstone')) el.click();
});
// 2. Click target dealer in popover
var popover = document.querySelector('.ant-popover-inner-content');
popover.querySelectorAll('*').forEach(el => {
  if (el.textContent.trim() === 'Blackstone Toyota') el.click();
});
```
If `[role="menuitem"]` returns empty, the popover uses `<div>`/`<span>` inside `.ant-popover-inner-content` instead. Filter by exact `textContent` match AND `offsetParent` (visible).
