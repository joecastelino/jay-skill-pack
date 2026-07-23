---
name: tekion-parts-autoorder-diagnosis
description: Diagnose why parts at a Tekion store stocked out / didn't auto-order (forcing local sourcing from Sunnyvale/Capitol/etc.). The CANONICAL parts-replenishment skill (supersedes tekion-parts-shortage-diagnosis). Works from RO numbers OR part numbers. Pulls live Stocking Details (Source Code, Stocking Status, Manual Order, BRP/BSL, Min/Max, On Hand/Order, Open Documents, Transactions ledger) per part, runs the day-supply demand calc, exposes the BSL Round-Down trap and the negative-on-hand backfill trap, and produces a per-part verdict + fix (Min Qty vs source-code BRP/BSL vs in-and-out receiving discipline). Use whenever Joe asks "why aren't these parts auto ordering / why do we have shortages / why did we have to get parts locally / why is my shelf at 0 when Min is set."
triggers:
  - parts not auto ordering
  - why aren't parts auto ordering
  - inventory shortage
  - parts inventory shortage
  - why didnt this part reorder
  - parts stock out
  - had to get parts locally
  - sourced parts locally
  - tekion replenishment
  - stocking details
  - negative on hand
  - bsl round down
  - min qty but shelf is zero
  - in and out sale
  - why didnt the stock order include this part
---

# Tekion Parts Auto-Order / Shortage Diagnosis

When Joe gives you RO numbers or part numbers and asks why a store ran out and had
to source locally, this is the workflow. The question is ALWAYS "why didn't Tekion
replenish this?" — answered by reading each part's **Stocking Details**.

## Step 1 — Identify the parts (if given RO numbers)

**FIRST clarify the inputs:** Joe often pastes numbers labeled with the store where the parts
were *bought* (e.g. "Sunnyvale Toyota", "Capitol Toyota"). Those are NOT necessarily the store
that OWNS the RO — the ROs are almost always at one of the 7 AMG stores (usually SCT); the named
stores are just where staff drove to grab the part. Don't assume the part-source store is in-fleet.
In this parts-shortage context, 6-digit numbers = **RO numbers (documentNumber)**, NOT part numbers.

ROs → parts via OpenAPI (no browser). See `tekion-openapi-repair-orders`:
- `POST /repair-orders:search {filters:[{field:"documentNumber",operator:"IN",values:[...]}]}`
  (NOTE: `totalCount` can exceed returned rows when ROs were just closed — they index
  with a lag. Re-pull missing ones later.) dealer_id = the OWNING store (st=876 for SCT).
- Walk `jobs → operations → parts` to get `partNumber` per RO. The part the CUSTOMER
  came in for is usually under the matching opcode (FBRAKE/ADBRAKE=brakes, etc.):
  `/repair-orders/{rid}/jobs` → `data.jobs[]`; `.../jobs/{jid}/operations` → `data.roOperations[]`;
  `.../operations/{oid}/parts` → `data.parts[]`. Each part: `partNumber`, `quantities[]` (type
  SALE), `status`/`fulfillmentStatus` (DELIVERED/HOLD). `partName`/`description` are often null on
  the RO line — get the real description from the inventory search or the browser.
- Quick on-hand: `POST /parts-inventory:search {searchText:"<partnum>"}` (param is `searchText`,
  NOT `textSearch`) → returns ONLY `partNumber, description, brand, onHandQty`. onHandQty:0 = stockout.
  **This API does NOT expose stocking settings — that's why you need the browser.**

### ⛔ THE HARD LIMIT — the API CANNOT tell you WHY it didn't auto-order
The public **Parts Inventory API has exactly ONE endpoint** ("Search Parts Inventory") and its
schema exposes ONLY `partNumber/description/brand/onHandQty`. It does NOT expose Source Code,
Min/Max/BRP/BSL, phase-in/out status, or whether the daily stock order ran. Verify the limit (don't
re-discover it): `~/dealerdetail/specs/apis/parts-inventory__search-parts-inventory.json` — no
min/max/source field exists anywhere; `api_catalog.json` "Parts Inventory" lists only that one
endpoint. **The API confirms WHAT (on-hand=0); the WHY lives only in the Tekion Parts UI (browser).**

## Step 1b — Get part numbers OFF the RO in the browser (when API isn't indexed) — verified SCT 2026-06-23
If the OpenAPI hasn't indexed an RO yet (recently closed → totalCount > rows), do NOT guess
part numbers by pattern (e.g. assuming a rear pad is `04466<frontnum>` — that's wrong and Joe
will (rightly) tell you to \"be more autonomous\" and just go look). Read them straight off the RO:
1. `navigate /ro`, wait ~7s. Find the global search input (`placeholder=\"Search here...\"`), tag it
   `data-jaysearch`, `/click`, `/type` the RO number, `/press` Enter, wait 5s.
2. The result row appears as `RO #<num> | Tag #<n>` with customer/vehicle. Tag the leaf whose text
   includes `RO #<num>`, `/click [data-jayro]` → lands on `/ro/repair-orders/<id>/jobs/<jobid>`.
3. Parts live INSIDE each job, NOT on the RO summary. A page-level part-number regex returns NOTHING
   until you expand. Each job has a **\"Billed Parts\"** section (collapsed). The job opcode line shows
   the work (e.g. \"ADBRAKE - REPLACE BRAKES ... (REAR)\", \"REC - REPLACE REAR ROTORS AND BRAKE PADS\").
4. Click the JOB line (tag a leaf containing the opcode text, `/click`), then `/click {text:\"Billed
   Parts\"}`, wait 3-4s. Read innerText, find \"Billed Parts\", and the rows follow the header
   `Part · Quantity · On Hand · ETA · Unit Price · Total price · Status`. Each part renders as
   `<PARTNUM> - <DESCRIPTION>` then qty/onhand/price/status on following lines.
5. A multi-job RO has multiple \"Billed Parts\" blocks — match the one under the relevant opcode job.
   Filter the part lines for the customer-relevant part (PAD KIT / DISC / ROTOR / SHIM KIT) and ignore
   shop supplies (BRAKE WASH 40966, STOP SQUEAL 860, DOT 3 FLUID 85032, oils 746/etc.).
PITFALL — OEM vs aftermarket: a job titled \"...USING ADVICS BRAKE PADS\" bills an **ADVICS aftermarket**
pad, which can have a non-`04465/04466` Toyota number, OR the shop \"resurfaces\" rotors (no rotor part
billed at all). So the part actually billed may not match the OEM number you'd guess. Always read the
billed line. Verified SCT examples: front pads `04465-0R010`, RAV4 rear pads `04466-42060`, FJ rear
pads `04466-60090`, rear rotor `42431-60201` (DISC, RR), shim kit `04946-30100`.

## Step 2 — Pull live Stocking Details (browser, :9223)
Load `tekion-sitemap` skill for nav. Login, switch to the store (ST=876), then per part:
```
navigate /parts/inventory/part/view/M_TMNA_<PARTNUM>/details   (strip dashes from #)
click left-nav text "Stocking Details"
read document.body.innerText → parse labels
```
Pull: `Source Code`, `Stocking Status`, `Manual Order`, `Total On Hand Quantity`,
`On Order Quantity`, `Open Documents`, `Best Reorder Point (Days)` (BRP),
`Best Stocking Level (Days)` (BSL), `Minimum Quantity`, `Maximum Quantity`,
`Last Sale Date`, `Material Return Indicator`. (Full field list in tekion-sitemap.)

## Step 2b — Drill into Open Documents (the highest-signal step)
Click the blue `Open Documents` number to open a drawer listing every open PO/SO/RO/SOR
for the part (Doc Type filter defaults to "Sales Order, Customer SOR, Repair Order,
Purchase Order"; columns: Reference Type · Reference No. · Status · In-Progress Qty ·
Name · Employee Name · Date & Time). DOM gotchas (cost real time — do it this way):
- The `:9223` screenshot endpoint is **GET `/screenshot`** returning `{"screenshot":"<base64>"}`
  — NOT a POST with a path. Decode base64 and write the PNG to `/tmp/` so `vision_analyze`
  can read it (the sandbox can't see `/home/itadmin`).
- The Open Documents count is a leaf `<span>`, color `rgb(66,133,244)`, `cursor:pointer`
  — NOT an `<a>`. Find the leaf whose text === the count, `setAttribute('data-jayclick','1')`,
  then `POST /click {selector:"[data-jayclick='1']"}`. URL won't change (it's a drawer).
- The drawer table is **virtualized** — rows are NOT `.ant-table-row`/`<tr>`. Locate the
  container holding "N Result(s)", climb to a sizable ancestor, then collect **ordered leaf
  text** (`children.length===0`) and chunk into rows of 7 (Type, RefNo, Status, Qty, Name,
  Employee, Date). This reliably reconstructs the full table when cell selectors return [].
- Then interpret: Draft PO = unfinalized reorder; Partially Received/Received = history;
  multiple ancient Drafts = junk to delete.

## Step 2d — Transactions tab = the SHORTAGE SMOKING GUN (verified SCT 2026-06-23)
The part view has tabs: **Part Details · Transactions · Monthly Data · Pricing History ·
Vendor Pricing**. The **Transactions** tab is the single most decisive evidence for "where
is my shortage coming from" — it's the full unit-level ledger (often hundreds of rows; SCT
brake pads = 264). Click the leaf with text "Transactions" (tag `data-jaytx`, `/click` it),
wait ~6s, read `document.body.innerText`, find the header row ending in "Bin", then each
subsequent date-led line is a transaction. Columns:
`Date & Time · Transaction Type · Reference No. · Invoice No. · Control No. · Customer ·
Supplier/Vendor · Unit Cost · Unit Selling Price · Before Qty · Transaction Qty · After Qty
· Amount · User · Bin`.
Transaction Types and what they mean:
- **`PO Received`** (+qty) — stock arrived (Reference No. = PO #, Control No. = stock order id).
- **`Hold`** (+1 then) / **`RO filled`** (-1) — part committed to then consumed by a service RO.
- **`Negative OH Sale (Filled)`** (-1, After Qty goes NEGATIVE) — **THE SHORTAGE PROOF**: the
  part was SOLD/billed with on-hand already at 0. Each Negative OH Sale row = one job the store
  had to fill without stock (sourced locally / sold short). The **Reference No. on these rows
  is the RO number** — this is how you tie the customer-facing shortage back to specific ROs.
  At SCT, RO 569933 (Christine Julian) and 569940 (Letty Carrazco), both Jun 20, were Negative
  OH Sales on `04465-0R010` — literally the shortage Joe was asking about, in the ledger.
Read the Before→After pattern: a part that repeatedly goes `0 → (+1 PO Received) → (−1 RO
filled) → 0` is chronically at zero — every restock instantly consumed, no buffer ever builds.
That pattern + Negative OH Sale rows = a velocity/buffer problem, and confirms whether the
reorder cadence (daily stock order submission) is keeping up. Note `Last Sale Date` and the
NUMBER of transactions as a quick velocity proxy before diving into the full ledger.
A part auto-orders ONLY if ALL true: **Stocking Status = Active** AND not **Manual
Order** AND not **Manufacturer/RIM-controlled** AND it has a working reorder trigger
(BRP/BSL in days OR a Min Qty) AND on-hand ≤ that trigger.

The 5 reasons a part WON'T auto-order, mapped to the field that proves it:
1. **Stocking Status = Non-Stock** → never met Phase-In demand (e.g. 3 sales/12mo). Excluded.
2. **Stocking Status = Inactive** → phased out, no recent demand. **Excluded from stock
   order; must be manually reactivated.** (Common for low-velocity axles, boot kits.)
3. **Manual Order = Yes** → VIN-required special order; excluded by design. Working as intended.
4. **Manufacturer Controlled (RIM/ARO)** → Toyota RIM owns it; EXCLUDED from local calc.
   (Check if the store relies on RIM — if so the gap is on the RIM side, not Tekion.)
5. **BRP/BSL blank AND no Min Qty** → Active but no reorder trigger → never reorders.

### THE #1 ROOT CAUSE FOR \"SOURCE CODE IS SET BUT PART STILL STOCKS OUT\": BSL ROUND-DOWN (verified from Tekion Feb-2024 webinar transcript, 2026-06-23)
When the source code BRP/BSL is correctly set AND the part inherits it AND the part is Active,
but the part STILL never gets ordered, the cause is almost always the **BSL rounding logic**.
This is the mechanism that reconciles \"my reorder points are already set\" with \"I keep running
out\" — and it's the answer Joe was hunting for. The exact math (from the webinar, verbatim):

```
Day Supply = (total sales in monitored months ÷ # months) × 30      # avg daily usage × 30
BRP qty    = Day Supply × (BRP days set on source)
BSL qty    = Day Supply × (BSL days set on source)
```
Then the calculated BSL **quantity** (a fraction) gets rounded per a fleet-wide setting:
**Part Settings → General Settings → \"BSL Rounding Logic for Stock Order Calculation\"**, three options:
- **Round Down** (TEKION DEFAULT — this is the trap): *\"if a BSL conversion from days to
  quantity is a fraction of 0.9 or less, the system rounds DOWN to the nearest whole number\"* →
  i.e. **rounds to 0** → the part **silently drops off the stock order**. The webinar's exact words:
  *\"if you should be getting a specific part but it hasn't sold enough to make it to quantity of
  1 or more, that's why it's not picking up the part.\"* A genuine fast-mover whose days-of-supply
  math lands under 1.0 will NEVER auto-order under the default. THIS is the usual shortage source.
- **Round Up**: any fraction → next whole number. Catches every barely-qualifying fast-mover but
  inflates the order (then you must move junk parts you don't want to carry into a separate
  non-stock source code so they stop appearing).
- **Round to Nearest**: ≥0.5 rounds up, <0.5 rounds down. The webinar's RECOMMENDED middle ground —
  *\"an improved stock order but won't be so big it takes too long to review.\"*

So the fix for a fast-mover stocking out under a correct source code is NOT to override part BRP/BSL
(don't — Joe explicitly wants parts to keep falling within the source code). It's:
1. **Change BSL Rounding Logic from \"Round Down\" → \"Round to Nearest\"** (Part Settings → General
   Settings) — fleet-wide, fixes ALL fractional fast-movers, does NOT touch source-code inheritance.
2. **Set part-level Minimum Quantity** on known fast-movers (brake pads, rotors) — the webinar
   explicitly calls this out: *\"handy if you sell rotors for a specific model and need to maintain a
   quantity of 2 at all times… the system will not bring in 1 when you need 2.\"* Min Qty is NOT a
   BRP/BSL override — it's a floor UNDER the source-code logic, guaranteeing round-to-0 can't zero
   out a known mover. Min Qty CANNOT be 0.

OTHER GATES from the same transcript (a part must clear ALL to be ordered):
- **Two-phase phase-in**: a Non-Stock part first must meet phase-in demand (e.g. \"3 sales in 12
  months\"), THEN once Active it still must meet the demand-calc qty (the rounding gate above).
  Recently-phased-in parts can be Active but still order 0 until velocity builds.
- **Unit Pack Quantity**: if calc says 3 but pack qty = 5, it orders 5 (rounds up to pack).
- **Manual Order = Yes** → excluded (must be added manually / via SOR).
- **Manufacturer Controlled (RIM/ARO)** → excluded from Tekion's calc (OEM owns replenishment).
- **\"No parts for order\" message** when running a stock order = *\"per the source code settings or
  overrides, no parts qualify\"* → check source-code params ARE set, then check the rounding logic.
- **Unusual sales are excluded** from demand; **part returns** DO count in phasing + demand;
  a replaced part's demand (Part A) rolls into the replacement (Part B) so B keeps ordering.

### CRITICAL: blank part-level BRP/BSL is NORMAL inheritance, NOT a misconfig
**Do NOT conclude "BRP/BSL blank on the part = broken/misconfigured."** This was a wrong
diagnosis at SCT 2026-06-23 that Joe (a parts-savvy VP) immediately rejected ("the BRP/BSL
are already set"). The truth, confirmed in the part's **Edit Part** form:
- When the part's "Specify stocking parameters in" radio = **Days**, blank part-level
  `Best Reorder Point (Days)`/`Best Stocking Level (Days)` fields mean the part **INHERITS
  the source code's BRP/BSL** (e.g. Source 101 = 17/21 days). Blank = inherit, NOT empty.
- So Source-Code-page-shows-BRP/BSL AND part-page-shows-"-" are BOTH true and BOTH correct.
  The config is working. The read-only Stocking Details panel renders inherited values as "-".
- To PROVE what's stored vs inherited, open **Edit Part** (button bottom of part view; click
  by text "Edit Part" — it opens an inline edit form, URL does NOT change). The edit form
  exposes the radio state (Quantity vs Days) and the actual input values. Empty input +
  Days-selected = inheriting from source.
**Therefore: if the source code has BRP/BSL set, stop blaming stocking params. The breakdown
is almost always operational (Draft PO not submitted) or velocity/timing — go to Step 2b/2c/2d.**

### The most common REAL cause (verified SCT 2026-06-23)
A genuine fast-mover that lives at on-hand 0 (every received unit is instantly consumed by
the next RO) stocks out NOT because params are blank but because the **system-generated daily
stock order was left in Draft and never submitted** (see Step 2c), OR the demand window
dilutes velocity so the reorder qty rounds too low. Only treat "blank BRP/BSL + no Min" as the
cause if the SOURCE CODE itself also has them blank — check the source before claiming it.

### Other signals
- **Negative On Hand (−1)** = receiving/billing error (sold before received). Distorts
  replenishment; flag it for correction separately. (Full mechanism in Step 2e.)
- **On Order ≥ 1** on a stocked-out part = it DID reorder; this is a timing gap, not a
  failure. Don't flag as broken.

## Step 2e — THE NEGATIVE-ON-HAND BACKFILL TRAP (verified SCT 2026-06-23, the answer Joe praised)
This is the deepest root cause and the one Joe specifically wanted nailed. It explains why a
part with a CORRECT source code AND a working Min Qty STILL ends up sitting at on-hand 0 after
a restock — i.e. why "Min=2 but I keep finding 0 on the shelf."

**The mechanism (read the Transactions ledger Before→After columns to PROVE it):**
1. Part sits at on-hand **0** (last unit consumed by an earlier RO; shelf empty for days).
2. A service RO needs the part while the shelf is empty. The counter person **bills it straight
   off the RO** (the part is on the customer's ticket) → Tekion records a **`Negative OH Sale
   (Filled)`** and drives on-hand **NEGATIVE** (0 → −1). A SECOND same-day job → −1 → **−2**.
   The `Reference No.` on each Negative OH Sale row = the RO number (SCT: 569933 Julian 1:44 PM,
   569940 Carrazco 4:00 PM, both Jun 20, drove `04465-0R010` to −2).
3. When the next **PO Received** lands (+2), those units **BACKFILL the −2 deficit back to 0
   instead of rebuilding to the Min/BSL level.** So after a full restock the shelf lands at **0,
   not Min 2.** Min never recovers after a negative event — this is why "Min works in normal
   cycles but the part still shows 0."

**Why this matters / how to explain it to Joe:** Min Qty DOES work in a normal cycle (sell 1 →
on-hand 1 → reorders back to 2). It breaks ONLY on a negative-OH event: the received units pay
down the negative debt first, so you never climb back to Min. The settings are not broken — the
**parts-handling process** is. A negative on-hand is the smoking gun that a part was sold without
being received first.

### ⚠️ A NEGATIVE DOESN'T REQUIRE A MANUAL IN-AND-OUT SALE (verified SCT spark plug, 2026-06-24)
When the parts manager (Glade) insists \"we are NOT doing in-and-out sales\" yet on-hand is still
negative, do NOT assume they're wrong or that someone is fudging. Tekion drives on-hand negative
**automatically, with no manual trick**, whenever **\"allow sale at zero/negative on-hand\" is enabled
(Tekion's DEFAULT)** AND any invoice — **a wholesale Sales Order OR a service RO** — is filled while
the shelf is at 0. The system simply books a `Negative OH Sale (Filled)` and keeps going negative.
So the answer to \"how is he fulfilling these without them hitting inventory?\" is: **he isn't doing
anything special — Tekion lets the counter sell/bill at zero on-hand, and every such sale digs the
hole deeper.** THE FIX that actually enforces what Glade thinks is already happening: **turn OFF
\"allow negative on-hand sale\" in Part Settings** → the counter is then FORCED to receive a part
(+qty) before it can be billed, which is a true in-and-out by construction.

**Two sub-causes to surface from the Transactions ledger (use the Transaction Type column):**
1. **WHOLESALE outrunning the reorder.** Classify the outflow by type: `SO filled` (wholesale Sales
   Orders to outside shops — e.g. SLT Auto Repair, TLS Auto, RETAIL SALES) vs `RO filled` (internal
   service). At SCT spark plug `9008091180` the split was ~18 SO filled : 6 RO filled — a 3:1
   **wholesale** problem, not a service problem. The reorder qty was too small to ever catch up:
   run-down `45→41→...→6→0→−6→−12→−16`, and the one PO Received (+10) only pulled it to −6 (backfilled
   the hole instead of rebuilding). If wholesale velocity is the driver, the fix is bigger reorder
   qty / higher Min and the negative-sale lockout — NOT blaming service technicians.
2. **STRANDED-BIN NEGATIVE.** A part can show a net negative that is actually a never-reconciled
   second bin. SCT plug: **+5 in primary bin 2420 but −16 in secondary bin 5005, netting −11.** All
   live activity was in 2420; the −16 in 5005 is an old bad bin-transfer/uncounted balance. **A
   perfect restock will NOT clear it — someone must physically reconcile bin 5005.** The Transactions
   ledger's **Bin** column (last column) exposes this — group transactions by Bin and check whether
   the negative lives entirely in one bin that has no recent activity. Flag for manual bin recount.

   ### PHANTOM/ORPHAN BIN — the stranded negative with ZERO transaction lineage (verified SCT 2026-06-26)
   A SHARPER sub-case of stranded-bin: the negative bin has **NOT ONE transaction in the entire
   ledger.** SCT plug `90080-91180` re-checked 2026-06-26: bin 5005 = **−16** on the part detail,
   but walking ALL 1,175 transactions (Nov 2022→Jun 2026, all 14 pages) found **0 rows posted to
   5005** — every sale/RO-fill/SO-fill/Hold/PO-Received posted to bin 2420 (or "-" in early years),
   and ALL 10 lifetime adjustments were 2420/"-" too (none touched 5005). A live bin balance with NO
   transaction history is NOT depletion and NOT a billing/in-and-out error — it's a **bin-record
   artifact**: a bin re-map, a legacy/migration **opening balance**, or a bin seeded outside the
   posting flow at go-live. DIAGNOSIS: if the negative bin shows zero ledger rows, STOP looking for a
   bad sale/transfer — there isn't one. FIX = a **physical count correction** of BOTH bins to the
   tech's physical count (e.g. 2420 system 5 → physical 10; 5005 system −16 → physical 3; net −11 →
   +13), NOT a config change and NOT waiting for a restock (the incoming PO just backfills the net
   negative toward 0 instead of building shelf — which is exactly why the user feels "replenishment
   is broken" when On Order/Min/Max/BRP/BSL are all healthy). **Ask before posting the adjustment**
   (Joe/Glade may post inventory adjustments themselves), and OFFER a fleet-wide scan: if one bin
   (e.g. 5005 "back counter") carries a ghost balance on this part, it likely does on many parts —
   a one-time bin cleanup beats part-by-part. Confirm the bin↔location mapping with the user (SCT:
   2420 = front counter / primary, 5005 = back counter) before reporting.

   ### PHYSICAL-INVENTORY CROSS-CHECK proves the phantom was never corrected (verified SCT 2026-06-27)
   When the user asks \"wouldn't a physical inventory have cleaned this up?\" (Joe asked this on the
   plug), the answer is **a count only corrects bins it actually walks — a location-less ghost bin is
   never on the count route, so it survives every physical.** PROVE it with the dealer's own count docs:
   - A physical inventory produces TWO PDFs from the count vendor (SCT uses **Dealers Inventory Service**):
     (1) a **PRELIMINARY** = dollar RECAP only (classification totals, certification, count date — NO
     part-level detail); (2) a **FINAL PARTS EXCEPTION** report = ONLY parts where physical count ≠ system,
     each row = `Part# - Desc | Bin(s) | Variance Qty | Unit Cost | Variance Amount`.
   - **THE TEST:** search the EXCEPTION report for the part number. If the part is **ABSENT** from the
     exception list, the count declared it \"matched\" — meaning the counters verified the ACTIVE bin (2420)
     and never touched the ghost bin (5005). A part that's −16 in a dead bin but absent from exceptions =
     **airtight proof the dead bin was out of count scope.** (SCT plug `90080-91180`: absent from the
     2025 exception report entirely; bin 5005 appears just ONCE in the whole report, as another part's
     listed bin — so 5005 physically exists but was not in this part's count scope.)
   - This is why the negative is **self-perpetuating fleet-wide**: every annual count keeps matching active
     bins and skipping the dead CDK bins (5005/5000/5001/5004/RC1/RC2) on thousands of parts. Only a
     deliberate **bin merge/consolidation** (or a count that explicitly includes the ghost bins) clears it.
   - PDF text extract: `pdftotext` is NOT installed — use `python3 -c \"import pypdf; r=pypdf.PdfReader('f.pdf');
     print('\\n'.join(p.extract_text() or '' for p in r.pages))\"`. Part numbers may extract with the dash
     stripped or split across spaces — search BOTH `9008091180` and `90080-91180`. CACHE the PDFs out of
     `~/.hermes/profiles/jay/cache/documents/` into a real project dir immediately (cache is wiped on reset).

   ### Auto-replenishment is NOT broken when On Order is already firing (verified SCT 2026-06-27)
   On the phantom-bin part, the live Stocking Details read showed **On Order = 30, Manual Order = No,
   Status Active, Min/Max 25/30, BRP/BSL 25/30** — i.e. the engine IS working and already placed an order.
   The screen even prints the rule: *\"Parts will be ordered when (OH + On Order) drops to 25. Ordered qty
   = 30 − (OH + On Order).\"* The trap: `OH(−11) + On Order(30) = 19 < 25`, so it KEEPS ordering — driven by
   the phantom −16, not a config fault. Once 5005 is reconciled, true OH = +5 → (5+30)=35 > 25 and the
   over-ordering stops. **Lesson: when the user says \"replenishment isn't working\" but On Order ≥ 1, the
   engine is fine — hunt the poisoned on-hand (phantom bin / negative), not the stocking params.**

### Reading the Transactions ledger at SCALE — it's PAGINATED, not infinite-scroll (verified 2026-06-26)
The part-view **Transactions** tab renders only **50 rows** and is **server-paginated** (bottom shows
page-number buttons 1,2,3… + Next + a "Results Per Page" 15/30/50 selector). PITFALLS that cost real
time — do it this way:
- **Scrolling the table does NOTHING** — it's not virtualized infinite-scroll; the scroll container
  maxes at ~2040px and never loads more rows. You MUST click pagination.
- **XHR/fetch hooks DON'T capture the main ledger fetch** — the data loads via React Query and is
  cached client-side; page changes often serve from cache (no network call). The sibling enrichment
  calls you DO see (`/api/partTrade/u/sale/order/search`, `.../purchase/search`, `.../sor/search`)
  are NOT the ledger. Don't waste cycles hunting the endpoint via hooks.
- **Filters available**: only **Date** (start/end range picker) and **Transaction Type** (multi-select
  dropdown: SO/RO filled+unfilled, PO Received, Adjustment Increment/Decrement, Material Return, Added
  to Inventory, Hold/Un-Hold, Negative OH Sale Filled/Unfilled, False Hold/Hold Variance Adjustment,
  Returns). **There is NO Bin filter** (the "Bin" at the far right is just the table column header,
  off-screen at x≈2588). To isolate a bin you must page the whole ledger and filter rows yourself.
- **Fast targeted approach**: filter **Transaction Type → Adjustment Increment + Adjustment Decrement
  + Added to Inventory + Material Return** first (usually <15 rows total) to instantly see every
  manual stock movement and which bin each hit — this answers "did an adjustment create the negative?"
  in one screen without paging 1,175 rows.
- **Full enumeration (when you must)**: click "Next" page-by-page, and **verify the top-row date
  CHANGED before parsing** (the Next click can 500 or race; re-read innerText up to ~3s until
  `rows[0].date != prev`). ~24 pages for 1,175 rows. Save incrementally — a mid-dump kill truncates
  the file to 0. ROW PARSE: find the header line `Part No.\nDate & Time…`, then each row = the
  part-number line (`^(900|909)\d{7}$`) + the **next 16 lines** as columns: PartNo, Date&Time,
  TxnType, RefNo, InvNo, CtrlNo, Customer, Vendor, UnitCost, UnitSell, BeforeQty, TxnQty, AfterQty,
  Amount, User, **Bin**. WATCH: the 16-line stride drifts on rows missing a cell — sanity-check the
  Bin column values are real bins ('2420','5005','-'), not dates, before trusting a bin tally.

**The CORRECT counter procedure for a locally-sourced part = a true "in-and-out" sale:**
- When you drive to another dealer (Sunnyvale/Capitol) and grab a part because you're stocked
  out, you must **RECEIVE it in (+qty) FIRST**, THEN sell it out (−qty) on the RO. Net effect on
  on-hand = 0, and it **never goes negative**. That's a clean in-and-out (a.k.a. "in & out sale").
- What actually happened at SCT (and the failure to flag): the two local pads were **billed
  straight off the RO with NO receiving entry** → on-hand went to −2 → next stock PO backfilled
  the deficit instead of restocking → shelf back to 0. **NOT done as in-and-out.**
- **How to verify it was/wasn't an in-and-out:** in the Transactions ledger, a real in-and-out
  shows a `PO Received`/receipt (+qty) on the SAME day as the sale tied to the same local pickup.
  If you see a `Negative OH Sale (Filled)` with NO matching same-day receipt → it was billed
  straight off the RO (not in-and-out). That absence is the airtight proof.

**Where the negative came FROM (how to trace the start of a negative streak):** walk the ledger
backwards from the −N row. Find the last `RO filled` that took on-hand to 0 (SCT: Jun 12 7:06 AM,
RO 568334) — that's when the shelf went empty. Every Negative OH Sale AFTER that, until the next
PO Received, is a job filled short. The PO Received that pulls it back to 0 (SCT: Jun 23 3:46 AM,
PO 27785 stk062226) closes the streak. Report it as a dated timeline — Joe wants the exact when.

### CHECK THE OPEN DOCUMENTS before blaming stocking params (verified SCT 2026-06-23)
The `Open Documents` count on Stocking Details is a **clickable blue span** — click it to
see EVERY open PO/SO/RO/SOR touching the part. This frequently reveals the real cause is
NOT a misconfig but an **operational gap**: a reorder PO sitting in **Draft** (never
submitted/received), or **stale zombie draft POs** from years ago polluting on-order math.
At SCT the front brake pads stocked out because PO 27774 (qty 2, the actual reorder) was
left in **Draft** — the system DID generate it, nobody finalized it — plus two 2023 draft
POs (7690/7692) were still hanging open. BRP/BSL on Source 101 was fine (17/21 days). So:
**always open the document list first; a Draft reorder PO means the param logic worked and
the breakdown is in the PO workflow, not the stocking setup.**

How to read the Open Documents drawer (DOM is fiddly — see Step 2b).

## Step 2c — CONFIRM a suspect PO in the Purchase Order list (verified SCT 2026-06-23)
The Open Documents drawer lists PO numbers but does **NOT drill into the PO** (clicking the
PO number does nothing useful). To confirm whether a Draft PO is the system-generated stock
order, go to the PO module:
- URL: **`/parts/purchase-order/list`** (give it ~10s; it shows \"Loading...\" then renders).
- Status tabs across the top with live counts: **All / Draft / Submitted / Invoiced /
  Partially Received / Received / Unpaid**. Click the **Draft** tab (it's a leaf `div/span`,
  text exactly \"Draft\", `children.length===0` — tag it `data-jaytab` and `/click` the selector;
  the global \"Search here...\" box is unreliable and can bounce you to the RO search instead).
- The table is **virtualized** (no `.ant-table-row`). Read `document.body.innerText`, split on
  newlines, find the line === the PO number, and the **next 14 lines are that row's columns in
  order**: `PO Number · Control Number · Invoice Number · Vendor · PO Amount · PO Type · OEM ·
  No. of Parts · Issued By · Date Created · PO Status · VIN · Est Delivery · Age · Invoice Status`.
- **PO Type is the diagnostic key**:
  - `OEM Stock Order` = the system-generated daily replenishment order (this is what auto-order
    produces — its existence PROVES the param logic worked).
  - `OEM Special Order` = VIN/customer-specific (Manual Order parts).
  - `Vendor Stock Order` = non-OEM vendor (tires, accessories).
- **PO Status = Draft with no Control/Invoice Number = never submitted** → the parts on it were
  never actually ordered from the OEM, so they never arrived. At SCT, PO 27774 = \"OEM Stock
  Order\", Draft, $8,287.19, 181 parts, issued by Glade Wilson Jun 22 — the brake pads were
  correctly calculated onto it, but it sat in Draft. Meanwhile sibling PO 27785 (same day, same
  person, also \"OEM Stock Order\") was Partially Received — proving the daily order normally flows.
  ROOT CAUSE = a process gap (stock order generated but not submitted), NOT a config bug.

## Step 3 — RUN THE DEMAND CALC (verified executable procedure, SCT 2026-06-23)
When Joe asks \"do the demand calculation for this part\" (he will — he's parts-savvy and wants
the actual numbers, not theory), here's the proven workflow that produces the BSL qty + rounding.

### 3a. Get the part's monthly sales history (Monthly Data tab)
`navigate /parts/inventory/part/view/M_TMNA_<PARTNUM>/monthlyData` (NOTE the `/monthlyData`
suffix — it's its own URL). Wait 5s, read `document.body.innerText`. Find \"Quantity Sold History\";
the grid is `Year | Jan | Feb | ... | Dec` then one row per year (most-recent year first), values
are integer units sold or `-` for no data. Parse into `{year: [jan..dec]}`.
GOTCHA: on the `/monthlyData` URL the left-rail Stocking-Detail LABELS don't parse cleanly
(Source Code etc. come back wrong/None). Pull the **grid** from `/monthlyData` but pull the
**stocking fields** (Source Code, Status, Min, On-Hand) from the `/details` URL. Two separate reads.

### 3b. Get the SOURCE CODE parameters (the calc needs BRP/BSL days + monitor window)
`navigate /parts/source-codes/list` (give it ~6s; sometimes blank → re-nav once). Tag the leaf
whose text === the source code number (e.g. \"101\"), `/click [data-jaysc]`, wait 4s → lands on
`/parts/source-codes/edit/<mongoid>`. `/click {text:\"Stocking Parameters\"}`, wait 4s, read
innerText. The \"Demand Calculation Criteria\" block gives: `No. of months to monitor`, `Best
reorder point (Days)` (BRP), `Best stocking level (Days)` (BSL). Also note Phase-in (`Total
Demand for phase-in` over `No. of Past Months to Monitor`).
**Verified SCT source params (Toyota TMNA):**
- **Source 101** \"GENERAL STOCK 15-999\" (fast-movers): 9-mo monitor, **BRP 17d / BSL 21d**,
  phase-in 3 sales/12mo, phase-out <0/9mo, inactivate after 18mo no phase-in.
- **Source 103** \"GENERAL STOCK 2-3\" (slow-movers): 9-mo monitor, **BRP 80d / BSL 85d**,
  same phase-in/out/inactivation.
- Source code IDs differ per store; re-read the edit URL. Other Toyota sources: 10 (batteries),
  100 (GENERAL STOCK 1000-99999), 102. There were 22 active source codes at SCT.

### 3c. The formula (apply in execute_code — do NOT eyeball it)
```python
import math
W = months_to_monitor                      # e.g. 9
# build chronological list newest-first, take the most-recent W months (skip None cells)
total = sum(units in most-recent W months)
day_supply = total / (W * 30)              # avg units/day  (NOT total/W*30 — it's total/(W*30))
brp_qty = day_supply * BRP_days            # reorder trigger point
bsl_qty = day_supply * BSL_days            # order-up-to level  ← THE number that gets rounded
rdown   = math.floor(bsl_qty)              # Tekion DEFAULT rounding
rnear   = round(bsl_qty)                   # \"Round to Nearest\" option
rup     = math.ceil(bsl_qty)               # \"Round Up\" option
# phase-in qualification: sales in last 12 months >= phase_in_demand (e.g. 3)?
```
WATCH THE FORMULA: day_supply = total ÷ (W×30). The webinar example (350 units / 3 months →
3.88/day) confirms it's total ÷ (months×30), i.e. avg units per ~30-day month ÷ 30. Easy to
mis-transcribe as `total/W*30` (operator precedence) which is 900× too big — always parenthesize.

### 3d. Interpret per part — the four buckets that emerged at SCT
- **Active fast-mover, BSL lands 1.0–1.99, rounds DOWN to 1**: the classic shortage. System
  stocks only 1, dies on any same-day double. Fix = Min Qty floor and/or shorten monitor window.
- **Active, BSL ≥1.5, Round-to-Nearest flips it 1→2**: the rounding SETTING alone is the fix
  (e.g. SCT transponder key BSL 1.56: down=1, nearest=2).
- **Inactive status**: EXCLUDED regardless of math — must reactivate first (CV axle qualified on
  phase-in, 5 sales/12mo, but Inactive blocked it). A status problem, not a rounding problem.
- **Doesn't qualify phase-in (<3 sales/12mo) AND BSL <0.5**: genuine slow-mover the system
  correctly won't stock (SCT CV boot: 2 sales/12mo, BSL 0.63). Recommend special-order, not stock.
Present as a table: Part | Src | Status | OnHand | Min | 9-mo sold | day supply | **BSL qty** |
Round-Down | Round-Nearest | verdict. This is exactly the deliverable Joe wants.

### 3e. The Min-vs-BSL conflict ("what's the point of Min=2 if it only orders 1 at zero?")
Joe will ask this — it's the sharp question. The answer: **Min Qty WINS when it's higher than the
BSL-calculated qty, but only governs the NORMAL cycle.** In a clean cycle the engine orders up to
`max(Min, BSL_qty_rounded)` — so Min 2 beats a BSL that rounds to 1, and "sell 1 → reorder to 2"
works (Joe confirmed this happens normally). Min is a FLOOR under the source logic, not an override
of BRP/BSL days. Where Min appears not to work is the **negative-OH backfill** (Step 2e): after a
negative event the restock pays the deficit first and lands at 0, never climbing to Min. So Min is
doing its job in normal cycles; the breakdown is the negative event, not Min being ignored. Fix =
(a) Round-to-Nearest so the reorder fires BEFORE the shelf hits 0 (avoids ever going negative), plus
(b) a higher Min on true fast-movers, plus (c) in-and-out receiving discipline so locals never drive
on-hand negative in the first place.

## Step 4 — Report: per-part verdict table
Columns: RO · Part · Stocking Status · Min · BRP/BSL · On-Hand/On-Order/OpenDocs ·
Verdict (fixable misconfig vs working-as-designed vs timing vs RIM). Then give the
fix levers, separating **safe part-level edits** (Min Qty — Jay can do) from
**store-wide source-code changes** (BRP/BSL — needs parts-manager sign-off).

## Fixes (procedures)
- **Set Min/Max** (part-level guardrail): part view → Stocking Details → Edit Part →
  Minimum/Maximum Quantity → Save. **Min/Max CANNOT be 0** (clear the field instead);
  the Min/Max feature may need enabling via support@tekion.com. Min Qty stocks that qty
  "irrespective of demand" — the reliable force-stock for a fast-mover.
- **BRP/BSL / Phase-In** (source-wide): Source Code tile → Stocking Parameters → Edit.
  Affects ALL parts in the source — confirm with Joe/parts manager first.
- **Reactivate an Inactive part**: must be moved Non-stock manually or via inventory bulk update.

## Pitfalls
- **NEVER tell Joe "the reorder points are blank/misconfigured" without first checking the
  SOURCE CODE and the part's Edit-form radio.** Blank part-level BRP/BSL + Days-selected =
  inheriting from source = working as designed. Joe knows his parts data cold and will reject
  a wrong root cause instantly — verify in the Edit form before stating a config conclusion.
- Sequence the diagnosis EVIDENCE-FIRST: Open Documents (Step 2b) → PO list / PO Type (2c) →
  Transactions ledger (2d) BEFORE theorizing about params. The ledger + Draft-PO usually give
  the real answer; the param check is mostly to RULE OUT, not the headline.
- Don't conclude "RIM-controlled" without checking the field — at SCT all 6 parts were on
  LOCAL source codes (101/103), NOT RIM. The issue was blank BRP/BSL + Inactive status.
- Recently-closed ROs may not be fully indexed (totalCount > rows). Note which parts you
  couldn't resolve and re-pull later rather than guessing.
- All browser work via :9223 (logged in), NOT the browser_* tool (unauthenticated).
- **:9223 `/eval` param is `js`, NOT `expression`** — wrong key returns HTTP 400 (cost a full restore attempt 2026-06-27). e.g. `post("/eval",{"js":"document.body.innerText.slice(0,400)"})`.
- **Dealer switch is NOT just setting `currentActiveDealerId` in localStorage** (that key resets on nav and the in-page API keeps using the old dealer). Switch via the UI: click the dealer pill (`.root_dealerSe...` top bar, ~x1100 y20) → popover → `/mouse` click the store leaf (`root_dealerInfoItem_itemName`, e.g. "Stevens Creek Toyota" ~x1074 y346). Default dealer after a fresh login is Blackstone Chevrolet (BC/1251) — you MUST switch to 876 for SCT parts or the part URL bounces to the parts LIST.
- **A bare in-page `fetch()` to `/api/...` is REJECTED** ("Token doesn't exist or is invalid") even when the page is authenticated — the app's axios interceptor adds auth headers a raw fetch lacks. Read the rendered DOM (Bin Details / Stocking Details text) instead, or capture via an XHR hook letting the app fire its own request.
- **Screenshotting the Bin Details exhibit**: a plain `scrollIntoView` on the "Bin Details" header often lands ABOVE the table. Instead `/mouse`-click the left-sidebar "Bin Details" anchor (`.ant-tabs-tab` ~x184) to scroll-jump it into view, then `GET /screenshot` (returns `{screenshot:<base64>}` → base64-decode to PNG) and ALWAYS vision-verify the −NN is legible before handing it to Joe. See also the dedicated `tekion-ghost-bin-negative-onhand` skill for the full ghost-bin live-pull + vendor-letter workflow.

## When does Tekion count a part as SOLD / relieve on-hand? (FAQ)
This drives the demand math, so know it cold:
- Adding a part to an OPEN RO/Sales Order → goes to **Hold Qty** (committed, not relieved).
  On-hand still shows physical count; it is NOT yet "sold" for stock-order purposes.
- **On-hand is decremented and the sale enters sales HISTORY only when the RO/SO is
  INVOICED/CLOSED/posted** — not when billed to the line. Sales history (relieved units)
  is what BRP/BSL × usage uses to compute demand. So an RO open for weeks doesn't count
  toward demand until it's closed.
- A Purchase Order ADDS to on-hand only when the PO is **Received** (Draft/Partially
  Received POs are on-order phantoms, not on-hand).

## Authoritative engine facts (Tekion KB0013471 — re-confirmed 2026-06-24)
Distilled from Tekion's own "System Generated Stock Order" KB (PDF at `~/tekion-kb/pdfs/`,
text at `~/tekion-kb/text/PARTS_APP__System_Generated_Stock_Order.txt`). These CONFIRM the
day-supply/BRP/BSL math above verbatim and add these gotchas:
- **Stocking Status lifecycle + timing**: Non-Stock → Active (phase-in) → Inactive (no demand).
  **Phase-IN happens in REAL TIME**; **Phase-OUT updates end-of-month** (if set to months) or
  **end-of-day** (if set to days). Inactive parts must be moved to Non-Stock **manually** or via
  inventory bulk update — they don't auto-recover.
- **Order formula (official):** `On Hand + On Order − BSL = Order qty` (negative = order that many
  up to BSL); reorder triggers at BRP. On-Hold & On-Order are subtracted from the suggestion.
- **Unit Pack Quantity rounds UP**: if calc says 3 but the part's Unit Pack Qty (or OEM mandatory
  min purchase) = 5, the system proposes **5**. A separate rounding gate from BSL day→qty rounding.
- **Min/Max feature may need enabling via support@tekion.com** (it's not on by default at every
  store). Min Qty forces stock "irrespective of demand"; Max caps it. Neither can be 0.
- **Manual Order = Yes** → excluded from stock order (must add manually or via SOR). Use for
  VIN-required parts.
- **Manufacturer Controlled (RIM/ARO)** → EXCLUDED from ARC stock calc; OEM owns replenishment.
  ARS (Auto-Replenishment Settings) are managed at the OEM level. OEM BRP/BSL view: Detailed
  Extended Value report + part details.
- **Returns** count in phase-in/out + demand. **Unusual sales** are EXCLUDED from demand (ARC lets
  you mark a sale unusual at part or customer level — so a freak bulk sale won't inflate BSL).
- **Part replacement (A→B)**: both parts share a Source Code; combined A+B demand is used, B's
  stocking params apply, only **B** is proposed to order.
- **EOQ cost-break escalators**: extra qty (by Qty) or extra days-supply (by Days) per cost band —
  for cheap fast bulk parts (clips, o-rings) to reduce order touches.
- **Best practice (Tekion's words)**: a stock order should take "a few minutes to review and
  approve"; if you're modifying results a lot, raise BSL (more inventory) or lower BSL (less). Don't
  micro-override at part level — control at the source code.
- **GOTCHA: Stocking Parameters can be saved at most 3 times per 30-minute window** (Source Code →
  Stocking Parameters). Batch your edits.
- **Source Code detail tabs (KB0013461)**: Source Code Details · List of Parts · Sales History ·
  Stocking Parameters. List of Parts has quick filters: Positive On Hand / Negative On Hand /
  On-Hand+On-Hold > 0. Sales History ledger columns include Before Qty / Transaction Qty / After Qty
  (same Before→After pattern as the part-level Transactions tab — usable for source-wide scrubs).
- **Track Lost Sales** (source-level): enabling it activates "Treat lost sales as demand for stock
  order calculation" — folds missed sales into demand so a chronically-stocked-out part's BSL
  reflects true demand, not just filled sales. Worth recommending for fast-movers that sell short.

## Reference KB docs (saved)
`~/sct-parts-autoorder/kb/` (and mirrored `~/tekion-kb/pdfs/`): source-code-overview.pdf (KB0013461 — Source Code tabs, demand calc,
phase-in/out, inactivation; OEM RIM/ARO parts excluded from local calc), system-generated-stock-order.pdf
(KB0013471 — THE replenishment engine: Stocking Status, phase-in, BRP/BSL day-supply math, weighted
avg, EOQ, Unit Pack rounding, Min/Max + Manual Order overrides), set-min-max-stock-qty.pdf (KB0013425 —
how to set Min/Max; Min keeps qty stocked "irrespective of demand"; Min/Max can't be 0; may need
enabling via support@tekion.com). These are the authoritative Tekion replenishment specs.

### Tekion ServiceNow KB access — STILL BLOCKED; Joe sends PDFs instead (re-verified live 2026-06-24)
KB URL `https://tekion.service-now.com/sp?id=kb_view2` (login `tekion.service-now.com`). Re-tested
live 2026-06-24 after Joe's OpenAPI scope upgrade — STILL CLOSED, unchanged. DMS creds
(`jcastelino@americanmotorscorp.com` + DMS pw) → "User name or password invalid". The OpenAPI scope
upgrade did NOT touch this portal. SSO does NOT carry over — even logged into the DMS in the same
:9223 browser, the KB throws its own login page. The "Use external login" button is a dead JS
handler (no href, no redirect, no federation). ServiceNow KB is a SEPARATE identity system from
DMS/APC; the "same creds" assumption FAILS. Don't fight it — Joe exports KB articles as PDFs into
chat (the proven path), OR ask IT/the Tekion rep to provision a real dedicated ServiceNow KB login.
NOTE: parts diagnosis (auto-order, negatives, BSL rounding, wholesale/bin) does NOT need the KB —
authoritative data is in the live DMS (Transactions ledger, source-code params, PO list) + cached
PDFs. Extract PDF text: `pdftotext` is NOT installed; use `python3 -c "import pypdf; r=pypdf.PdfReader('f.pdf');
print('\n'.join(p.extract_text() for p in r.pages))"`. Cache PDFs out of the ephemeral
`~/.hermes/profiles/jay/cache/documents/` into a project dir immediately (it's wiped on daily reset).
