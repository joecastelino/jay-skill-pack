---
name: tekion-quotes-menu-price-diagnosis
description: Diagnose a Tekion Service Menu pricing problem (e.g. "a rotation is charging $449.45") by building a throwaway Quote for the exact VIN+mileage. Isolate a single line's price via uncheck-and-watch-the-total, then EXPLODE the menu into individual opcodes using the "Add Menu Services as separate operations" setting to find which opcode carries the bad price and its labor-rate method (Fixed vs Service Catalog Pro Dynamic Pricing). Use when Joe flags a wrong/inflated price on a maintenance menu line for a specific RO/vehicle.
triggers:
  - tekion menu pricing
  - service menu wrong price
  - rotation charging too much
  - quotes tab menu price
  - why is menu price X
  - add menu services as separate operations
  - explode menu opcodes
  - service catalog pro dynamic pricing
---

## ⭐ ROOT-CAUSE HEADLINE (Joe's own framing, confirmed 2026-06-25)
For the rotation case the bug in one sentence: **the factory included-service "Rotate
wheels following manufacturers recommended sequence." PULLS TOYOTA'S 1.69 hr labor time
via SCP Dynamic Pricing on opcode TEK07120301 → inflated $ (e.g. $449.45).** The factory
feed's labor TIME (1.69 hr) is the source — not a stored menu price. So no menu-price
field edit fixes it; you must REPLACE that factory line with a pre-built fixed-rate opcode
(see VERIFIED CLEAN SWAP). Joe confirmed Jay's revert was correct AND clarified the real
fix is the swap, not leaving the factory line in place. When Joe says a rotation/service is
"pulling from Toyota at X hr," he means SCP-dynamic factory labor time → diagnose at the
opcode pricing-method level, then swap to the fixed-rate replacement opcode.

⭐ JOE'S RECURRING SHORTHAND (reconfirmed 2026-06-25): "the rotate wheels following IS
pulling from Toyota, which is 1.69" = the factory included-service "Rotate wheels following
manufacturers recommended sequence." is pulling Toyota's 1.69 hr labor time via SCP Dynamic
Pricing on TEK07120301. When you hear "pulling from <OEM>" + a labor HOUR figure (1.69), that
IS the root cause statement — the price is OEM factory labor TIME × rate through SCP, not a
stored menu/opcode price. Do NOT re-diagnose from scratch; confirm the opcode's labor method =
Dynamic/SCP and move to the fixed-rate replacement-opcode swap ("Perform Tire Rotation"). Joe
also signals a correct prior action with "you did perfect" / "you reverted perfect" — that's
acceptance, not a request to keep working; acknowledge and confirm the end-state, don't re-open.

## Tekion Quotes-tab Service Menu price diagnosis

When Joe flags "RO #X — store charging $Y for service Z (e.g. rotation)" on a
maintenance menu, the live menu price for that exact vehicle+interval is read most
reliably by building a **Quote** (no commitment, no RO edit). This is the right tool —
the `/ro/service-menu` viewer often won't resolve a VIN, and the RO itself shows the
BILLED amount, not the menu's quoted price.

## Step 0 — get the VIN + interval off the RO (API, no browser)
`repair-orders:search` with `documentNumber IN ["<RO#>"]` → `documentId`, then
`/repair-orders/{rid}/ro-vehicle` → VIN, year/make/model, mileage. (See
tekion-openapi-repair-orders skill.) The OPCODE tags (e.g. `TXM20`) tell you which
interval menu was used. Mileage tells you which interval to quote (15,666 mi → 15K).

## Step 1 — open Quotes (persistent :9223 browser, already logged in)
- Confirm dealer: `localStorage.currentActiveDealerId` (876=SCT).
- Open 9-dot launcher: `/click {"selector":"[class*=nine-dots]"}`.
- The launcher only shows "Recently Used" by default — **search** instead:
  `/type {"selector":"input[placeholder=\"Search\"]","text":"Quotes"}` then
  `/click {"text":"Quotes"}` → lands `/ro/quotes`.

## Step 2 — Create Quote with the VIN + mileage
- `/click {"text":"Create Quote"}`.
- VIN: `/type {"selector":"input[placeholder=\"Search VIN #\"]","text":"<VIN>"}` —
  this AUTO-DECODES Make/Year/Model/Trim (wait ~4s).
- Odometer: the text input immediately AFTER the Model field (enumerate inputs;
  it's the one whose parent-text follows the model name). `/type` needs a selector
  and bare `/type` with only text fails — instead **focus it via eval then send
  digits one key at a time** via `/press`:
  ```
  /eval {"js":"document.querySelectorAll('input')[N].focus();'ok'"}
  for each digit d in "15000": /press {"key":"d"}
  ```
  Verify `document.querySelectorAll('input')[N].value` shows "15,000".
- `/click {"text":"Continue"}` → lands `/ro/quotes/<id>/service/new`.

## Step 3 — open the Service Menu tab → interval → tiers
- `/click {"text":"Service Menu"}` (a tab next to Recall / Deferred / Service Catalog).
- The interval tiles list as split text "15K mi" + "Maintenance Package". Click
  the interval: `/click {"text":"15K mi"}` (NOT the full "15K mi Maintenance
  Package" string — that match times out).
- Three tiers expand: **Basic / Basic + / Signature**. Click each tier name to see
  its TOTAL price + included Services list + Package OpCode.
  - Read prices from the DOM: `/eval {"js":"var m=document.body.innerText.match(/\\$[0-9,]+\\.[0-9]{2}/g);JSON.stringify(m)"}`.

## Step 4 — ISOLATE a single service line's price (the key trick)
The UI shows NO per-line price label. To get one line's contribution:
1. With a tier selected, note the package total.
2. **Uncheck the target service line** by clicking its exact text, e.g.
   `/click {"text":"Rotate wheels following manufacturers recommended sequence."}`.
3. Re-read the total. **The drop = that line's menu price.**
   Verified RO 564419 (2024 4Runner JTEKU5JR6R6239372, 15K Basic, opcode
   TEK15000BNM): total $642.52 with rotation → $193.07 without →
   **$642.52 − $193.07 = $449.45 = the rotation line's price.** That's the bug.
4. Re-check the line to confirm it jumps back ($193.07 → $642.52).

## Step 4.5 — ⭐ EXPLODE the menu into separate opcodes (Joe's method — FASTEST root cause)
THIS is the most reliable way to find WHICH opcode carries the bad price and HOW it's
priced. It beats the Step-5 menu-setups archaeology below (which dead-ends on "system
service" lines). Joe taught this 2026-06-24 and it nailed RO 564419 in minutes.

There is a Service Menu Setups SETTING: **"Add Menu Services as separate operations."**
Flip it ON → add the menu to a quote → every bundled service breaks out into its OWN
operation line with its OWN opcode + labor-rate METHOD → flip it back OFF. This is a
deliberate config change: NARRATE each step, and ALWAYS revert it when done.

1. **Flip ON.** Go `/ro/service-menu-setups/settings`. The toggle's data-test-id is
   `@tekion-repairOrders-serviceMenuSetups-settings-addmenuServiceAsseparateOperation`.
   Read `getAttribute('aria-checked')` FIRST (record original state — was `false`).
   `/click` the toggle → confirm `aria-checked='true'` → click **Save**
   (`[data-test-id=@tekion-repair-orders-serviceMenuSetups-settingsSaveComponent-Save]`)
   → confirm a "Success" toast.
2. **Build a fresh quote** (Steps 1-3) and **Add To Quote** on the target tier
   (`/click {"text":"Add To Quote"}`). It still shows as ONE line in the Services(1)
   list, but the header now lists the exploded opcodes (e.g.
   "TEK15000BNM, TEK07120301, SMFUELCLEANER, ...").
3. **Open the service line** (`/click {"text":"<menu description>"}`, e.g.
   "15000 miles basic normal service menu") → lands `/ro/quotes/<id>/service/<sid>`.
   Read `document.body.innerText` — you get **Op1, Op2, … each with Opcode +
   description + Labor Rate METHOD**. The mispriced line's Labor Rate is the tell:
   - `Fixed` = flat rate on the opcode (fine).
   - `$ 228 / hr | Service Menu Pricing` = menu labor rate (fine).
   - **`Dynamic Pricing | Service Catalog Pro Guide`** = ⚠️ price computed by SCP's
     dynamic pricing guide, NOT stored on the opcode. THIS is what inflated the
     RO-564419 rotation: Op2 = **TEK07120301 (Rotate Wheels)** on Dynamic Pricing →
     SCP generated $449.45. Every other op in that package was Fixed/Service-Menu.
4. **Flip the toggle back OFF** (same selectors; click toggle → `aria-checked='false'`
   → Save → "Success"). VERIFY it's off before moving on. Leaving it ON changes how
   menus add to every RO store-wide.
5. **Confirm at the opcode level.** Open `/ro/opcode/edit/<OPCODE>` (e.g.
   `/ro/opcode/edit/TEK07120301`). If the Default-tab **Labor hours are BLANK and
   Labor Rate = "Select"/blank** for CP/W/I, the opcode stores NO fixed price → the
   amount is 100% from Service Catalog Pro dynamic pricing (confirms the diagnosis).

   **THE FIX (Joe's call — change nothing without explicit go):** either (a) set a
   FIXED labor rate/hours on that opcode so it stops pulling the dynamic SCP price
   (cleanest, matches the package's other Fixed ops), or (b) correct the Service
   Catalog Pro dynamic-pricing guide entry for that opcode if dynamic pricing is
   wanted. Recommend (a).

## Step 5 — (FALLBACK) trace the bad price into Service Menu Setups (EDIT-side)
Use this only if Step 4.5 is unavailable. Once Step 4 proves WHICH line is mispriced,
open the menu in Service Menu Setups to find WHY (read-only — do NOT edit/Publish
without Joe's explicit go). NOTE: this path often dead-ends because a factory line is
a "system service" not shown on the edit screen (see step 5.5) — prefer Step 4.5.

1. Go to `/ro/service-menu-setups`. Rows render with an **odometer-animated**
   interval cell (not directly clickable). Open via the **⋮ kebab → Edit**.
   - **ALL kebabs share data-test-id `0-action-kebabMenu`** — selecting `[data-test-id=0-action-kebabMenu]` hits the FIRST row (default sort = Last Modified, often NOT your interval). VERIFY before Edit: map each kebab to its row text:
     `/eval {"js":"Array.from(document.querySelectorAll('[data-test-id$=action-kebabMenu]')).map(k=>{var r=k.closest('[class*=rt-tr],[role=row],tr');return (r?r.innerText.slice(0,18):'?')})"}`
   - Tag the right one and click it: `...[INDEX].setAttribute('data-jay','t');` then `/click {"selector":"[data-jay=t]"}`, then `/click {"text":"Edit"}`.
   - **ALWAYS confirm the title**: `document.body.innerText.match(/Edit Menu[^\n]*/)` must read your interval (I opened the 80K by mistake first — the kebab pointed at the wrong row).

2. The edit view has a **Menu Included Services** table = multiple VEHICLE ROWS
   (each a Make/Models/Years/Trims override). One vehicle can match several rows.
   **OVERRIDE PRIORITY: the BOTTOM-MOST applicable row wins** — so the row that
   actually drives the quote is usually the LAST 4Runner row (e.g. the "84 trims
   selected" specific row), NOT the first "All Models" row. Don't assume row 1.

3. Expand a row via its `.rt-expandable` cell (tag by index + click). DECOY WARNING:
   the first/All-Models row may hold **dummy placeholder prices** (I saw flat
   $1,000 / $2,000 / $3,000 in Total-Menu-Price fields that did NOT match the quote)
   — those rows are NOT the active one. Match the row whose pricing reconciles to
   the Step-4 quote.

4. In the expanded row read **Menu Price → Price Type** and **Labor Hours → Hours
   Type** (read input VALUES, not just innerText):
   - **Sum of Services** = package total is the SUM of each service's own labor
     price → a single bad line (the rotation) is summed straight in. (This was the
     RO-564419 case: Row 4 = Custom → Sum of Services on all tiers.)
   - **Total Menu Price** = a flat $ per tier typed on the row (the override case).
   - **Total Labor + Parts** = separate labor $ + parts $.

5. **KEY GOTCHA — a "system" service is NOT editable here.** The edit row's
   "Modify System Services / Add Services" lists only the MODIFIED/ADDED services.
   A factory line like "Rotate wheels" is a **SYSTEM service** inherited from the
   base menu, so it does NOT appear in this list and its labor price is NOT on this
   screen. With Sum-of-Services, that means the bad $449.45 lives one level down in
   the **service catalog / the opcode that the system rotation service maps to** —
   check the **Intervals & Opcodes** tab (menu service → opcode mapping) and that
   opcode's labor price, OR ask Joe where the rotation's catalog price lives. This
   is the wall: STOP and ask rather than guess which opcode/price is wrong.

## Reporting
## Step 5 — EXPLODE the menu into individual opcodes (the deep diagnostic)
The uncheck-delta (Step 4) tells you the dollar amount of a line but NOT which opcode
carries it. To get the actual opcode + its pricing method:
1. **Service Menu Setups → Settings tab** (`/ro/service-menu-setups/settings`).
   Toggle **"Add Menu Services as separate operations" ON**
   (data-test-id `@tekion-repairOrders-serviceMenuSetups-settings-addmenuServiceAsseparateOperation`,
   read `aria-checked` for current state) → click **Save**
   (`@tekion-repair-orders-serviceMenuSetups-settingsSaveComponent-Save`), wait for
   "Success" toast. RECORD that it was OFF so you revert.
2. Rebuild the quote (Steps 1–3), add the package ("Add To Quote"), then CLICK the
   added service line to open its detail view. It now lists **Op1, Op2, … each as a
   separate operation** with its own **opcode, description, Labor Hrs, and Labor
   Rate method**. Read the DOM (`document.body.innerText`) — the panel truncates
   visually but the full op list is in the text. The mispriced line's Labor Rate
   method is the tell: e.g. rotation showed **"Dynamic Pricing | Service Catalog Pro
   Guide CP"** while siblings were "Fixed" or "$228/hr Service Menu Pricing".
3. **FLIP THE TOGGLE BACK OFF + Save** (verify aria-checked=false, "Success" toast)
   BEFORE doing anything else. Leaving it ON changes how every menu writes ROs.
   Verified RO 564419: 15K Basic exploded to TEK15000BNM (container) + **TEK07120301
   (Rotate Wheels, Dynamic Pricing — the $449.45 culprit)** + SMFUELCLEANER +
   SMETHANOL + DIAG + BGBAT.

## Step 6 — the opcode CANNOT be fixed in Opcode Management
Opening the opcode in Opcode Management (`/ro/opcode/edit/<OPCODE>`) shows its Default
tab has **blank Labor Hrs and blank Labor Rate** — because the price comes from Service
Catalog Pro dynamic pricing, not a stored value. So you do NOT fix it there. The fix
lives in **Service Menu Setups → Included Services** (left sub-nav tile, lands
`/ro/service-menu-setups/included-service` — singular).

### ⛔ MENU PACKAGE opcodes: Overrides tab = Cost-Center-ONLY (verified TEK90000VNM, 2026-07-03)
The dead end is even harder for the PACKAGE opcode itself (`TEK\d+[BPV][NS]M`, e.g.
TEK90000VNM): its Opcode Management **Overrides tab exposes ONLY a "Cost Center" module**
— no Labor, no Parts sub-sections at all. You cannot build a vehicle-scoped labor
time/price override there. Hit live trying to set 2.4hr/$469.88 for a 2014 Camry on the
90K package; screenshot proof `/tmp/tek90k_overrides.png`. Joe's directive: vehicle-scoped
labor/price adjustments for menu packages go through **Service Menu Setups** (vehicle rows
/ Included Services), never Opcode Management. Also note: NO menu-side fix retroactively
reprices an already-built RO line — the line must be deleted + re-added on the RO to
re-pull the new price (mind tech assignment if status=Working).

## ⭐ VERIFIED CASE — factory REPAIR op riding in a menu base (brake booster, SCT 120K, 2026-07-03)
Symptom: 2017 Highlander (VIN 5TDKZRFH2HS511864, 118,378 mi) quoted 120K Basic at a wild
**$4,162.38**. Diagnosis followed this skill exactly and it worked end-to-end:
1. Clean throwaway quote → Service Menu → "120K mi" → confirmed `Package OpCode : TEK120000BNM`
   and the line "Replace brake booster vacuum pump." present in Basic.
2. **Delta isolation (Step 4 trick):** unchecked just that line in the quote UI →
   Basic $4,162.38 → **$1,842.35** (line worth **$2,320.03**). Re-checked to restore.
3. Explode toggle round-trip (Step 4.5) → fresh quote → line = **TEK02110102**, Labor Rate
   "Dynamic Pricing | Service Catalog Pro Guide CP", parts 2930031011 PUMP ASSY VACUUM
   $1,002.62 + gasket + 3 bolts ≈ $1,037.71 parts. Toggle flipped back OFF + Save verified.
Root-cause pattern: a full **repair** operation (SCP-dynamic labor + $1K parts) embedded in
a menu's System services feed — same class as the 4Runner rotation case, but bigger. Fix =
suppress in the driving vehicle row's Modify System Services (uncheck all tiers), after
row-membership confirmation. Verify target after fix: Basic re-quotes at the measured
minus-line price ($1,842.35).

## Step 7 — Included Services search reveals the DUPLICATE-ENTRY trap
On the Included Services page, type the service name into the page search box
(placeholder "Search..."). **The Ant search input is finicky** — /type often won't
stick; FOCUS it via eval then send characters one at a time via /press (incl. "Space"
key for spaces), then verify `.value`. Searching "Rotate Wheels" returned **TWO
entries for the SAME opcode TEK07120301**:
- "Rotate Wheels" (short name)
- "Rotate wheels following manufacturers recommended sequence." (long factory desc)

The MENU/quote binds to the LONG-description variant. ⚠️ CORRECTION (verified
2026-06-24): the two records do NOT carry different prices — BOTH map to opcode
TEK07120301 and BOTH price at $449.45 via SCP dynamic pricing. So swapping the variant
is COSMETIC (changes the label only), NOT a price fix. See the \"PRICE PUNCHLINE\" section
below. The real price fix is opcode-level (Fixed rate vs SCP guide), not a variant swap.
The swap is still useful if Joe wants the SHORT label to display, but do not expect it
to change the dollar amount.

### Modify System Services — where the swap happens
In the menu Edit view, expand the applicable vehicle row (override priority = BOTTOM-
MOST applicable row wins; for the 4Runner that was Row 4 = "84 trims selected", NOT
the "All trims" rows which had dummy flat $1,000/$2,000/$3,000 values). Menu
Configuration = "System + Overrides". The expanded row has **"Modify System Services"**
(modify factory services already in the base menu) and **"Add Services"** (services
added on top), each with tier columns Basic/Basic+/Signature + "Apply to all Tiers".
GOTCHA: a SYSTEM service (like the factory rotation) may NOT appear as an editable row
in either list — it's inherited from the base menu. To swap it you Add the correct
included-service variant (the picker shows BOTH TEK07120301 entries — pick the right
one) and, if the quote then shows a duplicate, EXCLUDE the system one.

## ⭐⭐ ROOT CAUSE OF MY FAILED ATTEMPT — WRONG ROW (Joe corrected me 2026-06-24)
The Phase-2 verify failed for ONE reason: **I edited the WRONG vehicle row.** I picked
**Row 4 (\"84 trims selected\")** because the explicit trim count looked like the
\"specific\" row. **WRONG — Row 4 (the 84-trim row) is the EV / Mirai menu, NOT the
4Runner.** Joe made the rotation change on **Row 2** and the diagnostic worked.

THE CORRECT ROW-IDENTIFICATION METHOD (do this BEFORE editing any row):
1. Tekion menu rows are **order-of-operations, bottom-to-top** — the bottom-most row
   wins — **BUT only among rows whose trim list ACTUALLY CONTAINS the vehicle's trim.**
   Don't just take the bottom-most or the explicit-trim-count row blind.
2. Open each candidate row's **Trim Details** (click the \"All trims selected\" /
   \"N trims selected\" cell in the Trim column) and **find the specific trim** (e.g.
   4Runner Limited). Confirm THAT row is the corresponding menu before touching it.
3. \"All trims selected\" rows DO include the 4Runner; the \"84 trims selected\" row was a
   carve-out for EV/Mirai. The explicit count is NOT \"more specific = the winner\" — it
   can be a totally different vehicle set. ALWAYS verify trim membership, never infer
   from the count.
4. DOM note: the Trim column renders as a long comma-joined chip list (\"All, 2WD
   Pickups, 4Runner, ... Mirai, ...\"), and the \"All trims selected\" summary is a
   CSS-truncated label — text matchers on \"trims selected\" find nothing. Click the
   trim cell by its row position / coordinates to open Trim Details.

So the earlier \"unchecking tier columns is a no-op\" finding is REINTERPRETED: it may
well have been a no-op on Row 4 simply because Row 4 never drives the 4Runner quote in
the first place. The removal mechanism on the CORRECT row (Row 2) is what Joe used
successfully — re-derive it on Row 2 when he hands it back.

## ⛔ FAILED FIX ATTEMPT — what does NOT remove a base-System service (verified 2026-06-24)
RO 564419 / 15K rotation. Attempted fix: in the menu Edit view, Row 4 (84-trim),
ADDED the long rotation variant into **Modify System Services**, then UNCHECKED it
across all tiers via the **\"Apply to all Tiers\"** checkbox (Basic/Value/Severe all
cleared — visually confirmed), then **Save → Publish** (\"Service menu published
successfully\"). Phase-2 verify (toggle \"Add Menu Services as separate operations\" ON
→ fresh 4Runner@15K quote) showed the rotation **STILL present** and price **STILL
$642.52 / $449.45 unchanged.** TEK07120301 did NOT drop out.

LESSON: **Unchecking the tier columns on a Modify-System-Services row does NOT remove
a factory base-System service from the menu.** Those tier checkboxes only toggle the
service for the override row's own tier mapping; the rotation flows in from the BASE
System menu (factory data feed) regardless. Adding-then-unchecking the same opcode in
Modify System Services is a no-op for pricing. Do NOT use this lever to remove a
system service. The correct removal mechanism is still UNKNOWN as of this session —
likely an explicit \"exclude\"/delete action on the System service itself, or removing
the long included-service entry at the menu-config / base-system level. **STOP and ask
Joe for the exact lever rather than guessing** (per never-guess rule). The Step-7
\"swap the variant in Modify System Services\" claim below is UNPROVEN for system
services — treat it as a hypothesis that this session's verify contradicted.

NOTE the failed Phase-1 edit leaves a harmless artifact: the long-rotation row sits in
Modify System Services with all tiers unchecked (no pricing effect). Offer Joe to
re-publish without it to restore the menu byte-for-byte, or leave it parked.

## ✅ WHAT ACTUALLY REMOVES THE ROTATION = the REMOVAL works, but only on the RIGHT ROW (verified 2026-06-24)
After Joe reverted and re-did the fix on **Row 2** (the correct 4Runner row, NOT my
Row 4), a fresh 4Runner@15K quote showed **Basic $642.52 → $193.07, rotation GONE,
Services 5 → 4.** The $449.45 dropped exactly. So the *removal* of the factory system
rotation DOES work — my Row-4 attempt failed ONLY because Row 4 is the EV/Mirai menu
and never drives the 4Runner quote. **The lever exists and works; the bug was my row
selection.** Confirm the active row via Trim Details (the trim list must contain the
vehicle) BEFORE editing — this is the single most important step.

## ⭐⭐⭐ THE ACTUAL VARIANT-SWAP MECHANISM (Joe taught it 2026-06-24 — THIS is the answer)
Joe's exact instruction, verbatim: *\"add the old opcode, rotate wheels following… and
have that all UNCHECKED; and force rotate wheels all CHECKED to swap one for the other.\"*

KEY MENTAL MODEL — how \"Modify System Services\" actually works:
- Modify System Services rows are **dropdowns that POINT AT base-system services to
  OVERRIDE their tier checkboxes.** A base-system service (e.g. the factory rotation,
  the long \"…following manufacturers…\" variant) inherits its default = CHECKED/on-all-
  tiers UNLESS you add a Modify-System row that points at it and unchecks it.
- So to SWAP long→short you list BOTH as Modify-System rows:
  1. **Long variant (\"Rotate wheels following manufacturers recommended sequence.\")**
     → add it as a Modify-System row → **UNCHECK ALL tiers** → this SUPPRESSES the
     factory long line (the $449.45 one).
  2. **Short variant (\"Rotate Wheels\")** → add it → **CHECK ALL tiers** → this turns
     the correctly-priced one ON.
- Net = long off, short on = one swapped for the other. **You do NOT delete the system
  line — you list it and uncheck it.** This corrects my earlier \"uncheck = no-op\" claim:
  unchecking IS the suppression lever; it was a no-op before ONLY because I did it on the
  wrong ROW (Row 4 = EV/Mirai, never drives the 4Runner).

### VERIFIED RESULTS (Row 2, the correct 4Runner row):
- Long UNCHECKED + Save+Publish → rotation $449.45 line **GONE**, Basic $642.52 → $193.07,
  Services 5 → 4. ✅ The suppression WORKS.
- Short CHECKED in Modify System Services alone → did NOT inject (Basic stayed $193.07,
  no rotation). RESOLVED: checking a non-base service in Modify System Services is a no-op
  for injection. The short variant MUST be added via the lower **\"Add Services\"** section
  (proven below — QO# 000490 then showed \"Rotate Wheels\" with Basic back to $642.52).
  Modify System Services can only MODIFY/suppress base-feed services; Add Services injects
  new ones. This is now fully verified, not a hypothesis.

### ⚙️ HOW TO ACTUALLY CLICK THESE CONTROLS (hard-won mechanics — reuse exactly)
- **Open a Modify-System / Add-Services \"Select\" dropdown:** it's a react-select. The
  placeholder div has pointer-events intercepted, so /click on it TIMES OUT. Instead
  dispatch a synthetic mouse sequence on the element at the dropdown's coordinates:
  ```
  /eval {\"js\":\"var el=document.elementFromPoint(360,Y);['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:360,clientY:Y})));'ok'\"}
  ```
  (Y = the dropdown row's y-coordinate; find empty \"Select\" placeholders via
  `[class*=tekion-select][class*=placeholder]` whose text===\"Select\", filter by y<700
  for the Modify section vs the Add section lower down.) The menu loads ~1100+ options.
- **Pick an option:** the option list renders even when menuOpen reads false. Find by
  text (`[class*=option]` filtered by description regex), tag it, then dispatch the SAME
  mousedown/mouseup/click sequence on the option element. Verify the dropdown row now
  shows the chosen service text.
- **⚠️ CHECKBOXES — the critical gotcha:** the Ant/React tier checkboxes IGNORE
  programmatic `.click()` AND synthetic MouseEvents (stays checked). The ONLY thing that
  toggles them is the **server's real Playwright /click** on the checkbox's clickable
  WRAPPER. Procedure: locate the target checkbox by row-y + column-x (cols observed at
  x≈417 ApplyAllTiers / 518 Basic / 818 Value / 1118 Severe), tag the `input.ant-checkbox-input`
  with data-jay, climb to its `closest('[class*=checkbox],label')` wrapper, tag THAT, then
  `/click {\"selector\":\"[data-jay=wrap]\"}`. Unchecking **\"Apply to all Tiers\" (x≈417)
  cascade-clears all four** in that row (verified). Re-read `.checked` to confirm.
- A NEWLY ADDED Modify-System row comes in **ALL CHECKED by default** — so after adding
  the long variant you MUST uncheck it (Apply-to-all-Tiers cascade).
- Save = `button[data-test-id$=footer-Save]`, Publish = `button[data-test-id$=footer-Publish]`.
  Both fire a \"Success\" toast that FADES fast — capture it via eval immediately after
  click (`document.body.innerText.match(/Success/i)`), don't rely on a later screenshot.
  PUBLISH (not just Save) is required for a quote to reflect the change.

### ✅✅ FULLY SOLVED 2026-06-24 — the THREE distinct sections + the price truth
The variant swap is now fully verified end-to-end. Joe added the short variant himself
in the correct section and had Jay inspect it. The mechanism:

THREE DISTINCT SECTIONS on the expanded vehicle row — DO NOT CONFUSE THEM:
1. **Modify System Services** = override/SUPPRESS services already in the base feed.
   Can ONLY toggle base-feed services. Add the long variant here + UNCHECK all tiers →
   suppresses the factory $449.45 line. (Checking a NON-base service here does NOTHING —
   that was the failed inject attempt.)
2. **Add Services** = INJECT a brand-new service into the menu (this is where Fuel System
   Cleaner, Ethanol Additive, 4-Wheel Alignment live). To bring the short \"Rotate Wheels\"
   INTO the menu you add it HERE with all tiers CHECKED. ✅ This is the inject lever.
3. **Add Inspections** = a SEPARATE section lower down for inspections (Multi-Point etc.).
   Its row inputs have ids like `ADDED_INSPECTIONS_NAME_N`. **DO NOT add services here** —
   Jay mistakenly typed \"Rotate\" into Add Inspections (got \"RotateRotate / No Match Found\");
   Joe caught it: \"Stop. You are in the wrong section.\" Cancel out (button Cancel → confirm
   dialog has Cancel/**Yes**, click Yes) to discard the dirty unsaved edit.

VERIFIED FINAL CONFIG (Row 2, the 4Runner row) that Joe published:
- Modify System Services: \"Rotate Wheels\" (short) checked all + \"Rotate wheels following…\"
  (long) UNCHECKED all.
- Add Services: \"Rotate Wheels\" (short) added, all tiers CHECKED. ← the inject.
- Re-quote: rotation line shows as \"Rotate Wheels\" (short) ✅ — the swap label took.

### ⚠️⚠️ THE PRICE PUNCHLINE — a variant swap does NOT change the price
After the full swap, the 4Runner 15K Basic re-quoted at **$642.52 again**, and isolating
the \"Rotate Wheels\" line (uncheck-delta) = **$449.45 — IDENTICAL to the long variant.**
WHY: BOTH included-service variants map to the SAME opcode `TEK07120301`, and the $449.45
comes from **Service Catalog Pro Dynamic Pricing on that opcode**, NOT from the included-
service record. Swapping long→short changes only the DISPLAY LABEL, not the dollar amount.
So the duplicate-entry/swap theory (old Step 7) is a RED HERRING for the price — it fixes
the label, never the price.

**THE REAL PRICE FIX is at the opcode/pricing level (per Step 4.5 / Step 6):** either set
a FIXED labor rate+hours on TEK07120301 (so it stops pulling SCP dynamic pricing — cleanest,
matches the package's other Fixed ops), OR correct the Service Catalog Pro dynamic-pricing
guide entry for that opcode. The menu-side variant swap is cosmetic for $. Report this
clearly to Joe and get his call on which lever before changing pricing.

LESSON FOR JAY: when Joe flags an inflated menu price, do NOT assume the fix is a menu-side
variant swap. The swap is the label; the PRICE lives on the opcode (Fixed vs SCP-dynamic).
Diagnose the pricing method FIRST (Step 4.5 explode), and if it's SCP-dynamic, the fix is
opcode-level, full stop.

## ⭐ VERIFIED CLEAN SWAP — the REAL price fix via a pre-built fixed-rate opcode (2026-06-25)
The definitive end-to-end fix (Joe's 4Runner 15K case, executed by Jay): when the menu
rotation pulls Toyota's factory 1.69 hr via SCP Dynamic Pricing on TEK07120301 ($449.45),
the fix is to SWAP the factory included-service for a SEPARATE opcode Joe pre-built with
correct FIXED labor overrides — here **"Perform Tire Rotation"** (a distinct opcode, NOT
the same TEK07120301). Steps that WORKED, in order:
1. Open the 15K menu Edit, expand **Row 2** (the 4Runner row — confirm via Trim Details:
   the trim list incl. 4Runner Limited; do this BEFORE editing, per Joe's standing method
   of grabbing the vehicle's trim and verifying row membership).
2. **Modify System Services** already contained "Rotate wheels following manufacturers
   recommended sequence." with ALL 4 tiers CHECKED (= the $449.45). Click its
   **Apply-to-all-Tiers** checkbox → cascade-clears all 4 → suppresses the factory line.
   (No need to ADD it — it was already a row; just uncheck.)
3. **Add Services** → open the empty "Select" react-select → pick the correct opcode.
   ⚠️ DUPLICATE-OPCODE TRAP: the picker showed BOTH "Perform Tire Rotation" AND
   "Perform Tire Rotation (2)". Joe had created "(2)" IN ERROR — the PLAIN one is correct.
   ALWAYS ask Joe which variant when a "(N)" duplicate appears; do NOT guess.
   A newly added Add-Services row comes in ALL 4 tiers CHECKED by default — that's the
   desired state (all 3 tiers active), no further checkbox action needed.
4. Save (`button[data-test-id$=footer-Save]` → "Success") then Publish (find button by
   text "Publish", tag, click → "Success"). Publish is REQUIRED for the quote to reflect.
5. Verify on the list page: 15K row Published Status = "Published", Last Modified = today.
6. Re-quote (4Runner VIN @ 15000 mi) → Service Menu tab → 15K mi → Basic tier → confirm
   the line now reads "Perform Tire Rotation"; uncheck-delta gave $261.47 − $193.07 =
   **$68.40** (the override price) vs the old $449.45. Done.
RESULT: Basic total $642.52 → $261.47, rotation $449.45 → $68.40. THIS is the working
recipe — a fixed-rate replacement opcode injected via Add Services, NOT a same-opcode
variant swap (which is cosmetic). The :9223 GET /screenshot returns JSON {screenshot:b64};
decode to PNG for vision. The react-select empty "Select" must be opened by dispatching
mousedown/mouseup/click on its `[class*=control]` center (synthetic), then click the option
by exact text match; checkboxes need the server's real /click on the
`label.ant-checkbox-wrapper` (Apply-to-all cascades all tiers).

## ↩️ THE REVERT PROCEDURE (verified 2026-06-25 — mirror of the swap)
After diagnostics, Joe will say "undo both." Revert is the exact mirror. On the correct
vehicle row (Row 2), expanded:
1. **Re-CHECK the long variant** in Modify System Services → click its "Apply to all Tiers"
   checkbox (cascade-checks all 4 tiers) → restores the factory line.
2. **UNCHECK the short "Rotate Wheels"** in Modify System Services → click its "Apply to all
   Tiers" (cascade-clears). ⭐ GOTCHA: unchecking a Modify-System row to fully empty makes
   Tekion DROP THE ROW ENTIRELY on next render (it's no longer listed) — that's correct, the
   row only existed to carry overrides. Don't be alarmed it "disappeared."
3. **DELETE the "Rotate Wheels" row from Add Services** — see the delete mechanism below.
4. **Save → Publish** → re-quote the 4Runner@15K → confirm back to **$642.52** with the line
   "Rotate wheels following manufacturers recommended sequence." and Services count 5.

## 🗑️ HOW TO DELETE an Add-Services row (verified 2026-06-25)
Add-Services rows have NO inline trash icon. The remove control is an **overflow kebab (⋮)**
at the FAR RIGHT of the row, past the Severe checkbox (observed at x≈1417, class
`icon-overflow` — title attribute literally "icon-overflow"). Procedure:
- Find the row's `[class*=singleValue]` whose text === the service name; scrollIntoView center.
- Find the `[class*=root_icon][class*=icon-overflow]` element at the row's y with x>1300; tag it.
- `/click` it (real Playwright click) → an overflow menu opens with **Edit** and **Delete**.
- `/click {"text":"Delete"}` → row removed immediately (NO confirm dialog). Verify the service
  no longer appears in `[class*=singleValue]` list.
NOTE: Modify-System-Services rows are removed differently — you don't delete them, you just
uncheck to empty and Tekion drops them (see Revert step 2).

## ⭐ ROW-IDENTIFICATION = JOE'S MANDATORY METHOD (taught 2026-06-25) — do this BEFORE any edit
Joe's standing instruction: when modifying a menu for a specific vehicle, **grab the
vehicle's exact trim, then confirm trim membership in each candidate row** to prove WHICH
row actually drives that vehicle's quote — never infer from the truncated Model/Trim cell.

### ☠️ THE DOM-DEDUP TRAP (cost real confusion 2026-06-25 — DO NOT REPEAT)
Querying `[class*=rt-tr]` and de-duplicating rows by truncated innerText (a `Set()`)
**COLLAPSES distinct rows that share the same truncated prefix.** On the SCT 15K menu the
rows were: Row1 Toyota/4Runner "All trims selected", Row2 Toyota/4Runner "All trims
selected", Row3 GR Supra/Supra, Row4 Toyota/4Runner **"84 trims selected"** (the EV/Mirai
carve-out). Rows 1, 2 and 4 all truncate to the IDENTICAL string "Toyota All, 2WD Pickups,
4Runner…" → the Set() reported only **2 rows** and HID Row2 and Row4 entirely. Editing the
wrong row on a Published menu is the disaster case. **NEVER trust the dedup'd DOM row list.**
Get the TRUE row structure from a **screenshot + vision** (it reads the rendered Trim column:
"All trims selected" / "84 trims selected") — vision saw all 4 rows when the DOM query saw 2.

### 📸 SCREENSHOT ON :9223 — endpoint is a GET returning base64 JSON (verified 2026-06-25)
The persistent browser server's `/screenshot` is **GET, not POST** (POST returns "Cannot POST
/screenshot"). Routes: GET /health /screenshot /snapshot /url ; POST /click /console /cookies
/eval /navigate /press /type. To capture+analyze:
```
curl -s "http://localhost:9223/screenshot" -o /tmp/s.json   # returns {"screenshot":"<base64>"}
```
then in Python: `b64=json.load(open(...))['screenshot']; strip optional 'data:...,' prefix;
base64.b64decode → write .png` → feed to vision_analyze. The raw curl output FILE is JSON text,
not a PNG — decode it first or read_file/file will report "JSON text data".

### 🔎 THE TRIM DETAILS MODAL IS AN ATTRIBUTE-FILTER PICKER, NOT A FLAT TRIM LIST (corrected 2026-06-25)
Clicking a row's Trim cell (the "All trims selected" / "N trims selected" text in the Trim
column — open it with a synthetic mousedown/mouseup/click at the cell's x,y, e.g. ~1065,Yrow)
opens an **ant-modal** titled "Trim Details" that is a FILTER UI, not a searchable list of
"4Runner Limited" style names. It contains: Filters(N), Select All, attribute groups
(**Engine Liter / Engine Cylinder / Aspiration / No. of Doors / Body Type / Transmission /
Fuel Type / Drive Type / Sub Model / Body Class**) each with checkboxes + Show More, a
**"Type here"** text search, and radios **"All trims (including future trims)" vs "Specific
trims"**. So you CANNOT just type a trim name and read a yes/no match. The earlier skill claim
"search the trim list for the specific trim" is INACCURATE for this picker. Read the modal
body via `document.querySelector('.ant-modal-body').innerText` (the generic
`[class*=modal]` selector grabs an EMPTY wrapper — target `.ant-modal-body`, len ~2000).
**HOW to actually confirm membership is still an open question for Joe** — when a row is
"All trims selected" and its Model column includes the model (4Runner), that row covers the
vehicle; the attribute picker is for NARROWING to specific trims, not for membership lookup.
If unsure which of two "All trims selected" 4Runner rows is active, STOP and ask Joe rather
than guess (override priority says bottom-most APPLICABLE wins, but confirm which row he built
the overrides on). Per never-guess rule, do not pick a row on a Published menu by inference.

### Practical row-confirm sequence (what worked 2026-06-25)
1. Get the vehicle's exact trim off the RO (repair-orders API → ro-vehicle).
2. Open the menu Edit; take a `/screenshot` (GET) → vision to enumerate the TRUE rows + each
   row's Trim-cell label (don't dedup the DOM).
3. Identify candidate rows whose Model includes the vehicle; the "N trims selected" row is
   usually a carve-out (EV/Mirai) — treat as a DECOY unless vision/Joe confirms it applies.
4. Confirm with Joe which row carries the overrides he built BEFORE editing.

## ⭐⭐⭐ THE REAL PRICE FIX = SWAP TO A PRE-BUILT CORRECT-OVERRIDE OPCODE (verified 2026-06-25)\nThe cleanest price fix Joe actually uses is NOT the cosmetic "Rotate Wheels" label swap and\nNOT editing TEK07120301 — it is swapping the bad factory line for a SEPARATE service that\nJoe pre-built WITH correct labor overrides. On SCT 15K (4Runner, Row 2) the target was\n**"Perform Tire Rotation"** (Joe built its overrides before handing the task to Jay). Because\nthat opcode carries a real Fixed/override price, injecting it actually CHANGES the dollar\namount (unlike the "Rotate Wheels" cosmetic swap). When Joe says "remove X opcode and add Y\nopcode," he means this real swap.\n\nThe two moves on the correct vehicle row (Row 2), expanded:\n1. **SUPPRESS the bad factory line** in **Modify System Services**.\n   ⭐ KEY: the long factory variant "Rotate wheels following manufacturers recommended\n   sequence." may **ALREADY be present in Modify System Services with all 4 tiers CHECKED**\n   (that checked row IS what produces the $449.45). If so you DON'T re-add it — just UNCHECK\n   it: click its **Apply-to-all-Tiers** checkbox (x≈417 at the row's y) → cascade-clears all\n   4 (verify `.checked===false` on all four at x≈417/518/818/1118). Record the baseline\n   (all-checked) state first for revert. (If it's NOT already listed, add it via the empty\n   Modify-System "Select" then uncheck — the older path below.)\n2. **INJECT the correct opcode** via **Add Services** (NOT Modify System Services, NOT Add\n   Inspections). Open the Add-Services empty "Select" dropdown, pick the pre-built service,\n   CHECK all tiers. This is the lever that brings the correctly-priced service in.\n\n### ☠️ DUPLICATE OPTION IN THE ADD-SERVICES PICKER — STOP AND ASK (verified 2026-06-25)\nThe service picker can list **TWO identical-looking options** for the same description, e.g.\n**"Perform Tire Rotation"** AND **"Perform Tire Rotation (2)"**. The option text shows ONLY\nthe description — NO opcode — so you cannot tell from the DOM which one carries Joe's correct\noverrides. This is the same duplicate-record trap as the original "Rotate Wheels" /\nTEK07120301 situation. **Per the never-guess rule: STOP and ask Joe which entry (the plain\none vs "(2)") is the opcode he built**, rather than injecting the wrong record and having the\nprice come back wrong again. Filter the picker options with\n`Array.from(document.querySelectorAll('[class*=option]')).filter(o=>/<desc>/i.test(o.textContent))`\nto list every match before asking.\n\n⭐ RESOLVED on SCT 15K (2026-06-25): the picker showed \"Perform Tire Rotation\" AND\n\"Perform Tire Rotation (2)\". Jay first injected \"(2)\" (Joe had it pre-checked all tiers),\nbut Joe stopped him: **\"(2)\" was an opcode Joe created IN ERROR; the correct pre-built\noverride opcode is the PLAIN \"Perform Tire Rotation\".** Lesson: a \"(N)\" suffix on a\nduplicate often = a mistaken/scratch record — never assume it's the newer/better one.\nAlways confirm the exact entry with Joe; he knows which is the real one. After selecting,\nVERIFY the chosen row's singleValue text matches EXACTLY (the plain one shows \"Perform\nTire Rotation\" with NO \"(2)\").\n\n⚠️ REMOVING A WRONGLY-ADDED Add-Services row (verified 2026-06-25): clicking the row's\noverflow icon (`[class*=root_icon]` at far right, x≈1320) then **\"Edit\"** can make the\njust-added (unsaved) row **DISAPPEAR entirely** from the singleValue list — i.e. it\nreverted the add. That's a fine way to undo an unsaved wrong selection (re-verify the\nrow is gone: filter singleValues for the description). For a SAVED row, the documented\nDelete path (kebab → Delete) still applies. After removal the page reflows — re-find the\nempty Add-Services \"Select\" dropdown by section boundaries before re-adding the correct one.\n\n### Add-Services empty dropdown — finding & clicking it (verified 2026-06-25)\nThe Add-Services section sits BETWEEN the "Add Services" header and the "Add Inspections"\nheader. After unchecking the rotation row the page REFLOWS and coordinates SHIFT — re-measure,\ndon't reuse stale x,y. Sequence that worked:\n- Get section boundaries: find the leaf elements whose textContent===\"Add Services\" and\n  ===\"Add Inspections\"; read their `getBoundingClientRect().y`.\n- Find empty "Select" placeholders (`[class*=placeholder]` text===\"Select\") whose y is\n  BETWEEN those two headers = the Add-Services add-row(s).\n- `scrollIntoView({block:\"center\"})` the control, then **screenshot+vision** to get the live\n  x,y of the empty Select (vision reads it reliably; raw coordinate math drifts after reflow).\n- Open it with the synthetic mousedown/mouseup/click on the react-select `[class*=control]`\n  at that x,y. `elementFromPoint` returns **null** if the y is off by even a little after\n  reflow — if null, re-screenshot and re-find. A successful open shows ~1100-1200 `[class*=option]` nodes.\n- The Trim-modal Cancel button is DUPLICATED (modal-wrap + content both match text=\"Cancel\")\n  → a bare `/click {text:Cancel}` TIMES OUT (wrap intercepts pointer events). Tag the Cancel\n  button INSIDE `.ant-modal-content` with data-jay and click the tagged selector instead.\n\n## 🔐 MID-TASK SESSION TIMEOUT RECOVERY (verified 2026-06-25 — :9223 browser)
The :9223 persistent browser CAN time out mid-task ("You have been logged out due to
inactivity" → bounces to /login). login.py may FAIL here because Playwright bumped to a new
version and the headless-shell binary is missing (`chromium_headless_shell-1223 ... Executable
doesn't exist`). DO NOT block on login.py — drive the login UI directly through :9223 (it's
already headful and sitting on the login page):
1. `input#email` (type=text) → type username (jcastelino@scvolkswagen.com) → `/click {"text":"Next"}`.
2. `input#password` appears → **baseline-count OTP emails FIRST**:
   `HOME=/home/itadmin himalaya envelope list -a personal -f "[Gmail]/All Mail" --page-size 20 | grep -ci "Tekion-Login OTP"`
   (use himalaya account `personal`, NOT google_api.py — that script only exists in a backup now).
3. Type password (<TEKION_PASSWORD>) → `/click {"text":"Login"}` (this AUTO-sends a fresh OTP).
4. `input#otp` + "Verify and Proceed" appear → poll inbox until count increases, then read code:
   `ID=$(himalaya envelope list ... | grep -i "Tekion-Login OTP" | head -1 | grep -oE '^\| *[0-9]+' | grep -oE '[0-9]+')`
   then `himalaya message read -a personal -f "[Gmail]/All Mail" "$ID" | grep -oE 'OTP number is : [0-9]{6}'`.
5. `/type input#otp` the 6 digits → `/press Tab` → `/click {"text":"Verify and Proceed"}`.
6. Success = `localStorage.t_token` present; URL redirects back to wherever you were.
7. ⚠️ **DEALER RESETS TO BC (1251) after re-login** — you MUST switch back to SCT (876):
   click the top-right dealer badge ("BC Blackstone Chevrolet", element at y<100), then in the
   dropdown click the leaf whose text === "Stevens Creek Toyota". Verify
   `localStorage.currentActiveDealerId === "876"` BEFORE resuming menu edits — editing the wrong
   store's menu is the disaster case. Re-navigate to the menu edit URL after switching.

## Live Published-menu change discipline (Joe's requirement)
Before ANY change to a Published menu, RECORD the exact pre-change state for a clean
revert: menu id, the row being edited (+ its trim selector), the current variant/
opcode, and the baseline quote numbers (tier totals + isolated line delta). Joe
requires Publish (not just Save) for the change to reflect in a quote. After testing,
get Joe's explicit call on keep-vs-revert — do NOT leave a Published menu changed
without his go. The revert is the mirror operation (swap back, Save + Publish, confirm
the baseline number returns).

## ⭐ PARTS-BEHIND-A-SERVICE-LINE diagnosis (Corolla Hybrid 90K / BG 303 + 31832, in progress 2026-06-25)
A DIFFERENT class of menu bug: not a wrong PRICE, but the WRONG PARTS attached behind a
service line. Joe's case: SCT 90K menu serves a 2024 Corolla HYBRID (eCVT) that takes
manufacturer **E-Trans fluid (E-TAF, part 0888681986)**, but the menu's CVT service line
**"Drain and Fill Continuously Variable Transmission (CVT) Fluid, Add Conditioner"** has
**BG 303 + part 31832** (BG CVT chemistry) attached — wrong for this vehicle. (The closed RO
565535 actually billed the correct E-TAF $155.93, so the RO was fine; the MENU SETUP is what's
mis-configured going forward.)

KEY LESSONS (all hard-won this session):
- **Parts attached behind a service line are INVISIBLE to a text/DOM scan of the service list.**
  A `document.querySelectorAll` leaf-text scan finds the SERVICE rows ("Drain and Fill CVT
  Fluid…") but NOT the parts riding behind them (BG 303 / 31832). To surface the parts you must
  **"Add To Quote"** on the tier (`/click {"text":"Add To Quote"}`) so the package loads onto the
  quote and its parts populate the parts table — OR open the **"Choose Parts"** control. Per Joe:
  "to get parts, you'll need to 'add to quote' to see the parts that are associated."
- **☠️ TIER-LABEL MISMATCH (the trap I hit live):** the QUOTE UI tier buttons are
  **Basic / Basic+ / Signature**, but Joe's menu-builder screenshots name them
  **Basic / Value / Premium**. They do NOT map 1:1 by name, and the totals/counts diverge:
  e.g. clicking "Signature" gave **9 services @ $714.88**, which did NOT match the Premium
  screenshot (**TEK90000PSM, 13 services, $2,310.62**). NEVER assume Signature = Premium by name.
  The reliable anchor is the **package opcode**: TEK90000**B**NM=Basic, TEK90000**V**NM=Value,
  TEK90000**P**SM=Premium/Severe. Read the opcode (or build the quote and match the total/service-
  count to Joe's screenshot) to confirm which on-screen button is the tier you want — and if it
  still doesn't reconcile, STOP and ask Joe which button maps to the target menu (never-guess).
- **☠️ STALE MODAL TRAP:** a leftover "Choose Parts" modal from earlier exploration silently keeps
  showing the WRONG (earlier) tier — its DOM scan returns that old tier's parts, not the one you
  think you selected. Close it first: `/click {"selector":".ant-modal-close"}` (or the Cancel
  inside `.ant-modal-content`), then verify `!document.querySelector('.ant-modal-body')` before
  re-querying. Confirm you're back on `/ro/quotes/<id>/service/new` clean.
- **VIRTUALIZED Choose-Parts list:** the modal scrolls; a DOM scan may only see the top 2-3
  services (oil/air/cabin filters) and MISS the CVT line further down. Physically scroll the
  modal or screenshot+vision rather than trusting a single DOM query for "is the part there."
- **☠️☠️ STALE-PACKAGE-OPCODE TRAP (the #1 time-waster this session — verified 2026-06-25):**
  clicking a mileage interval chip (e.g. "90K") HIGHLIGHTS the chip but does NOT always reload
  the package panel — the panel can keep rendering a PREVIOUS interval's package (I had 90K
  highlighted while the panel still showed **`Package OpCode : TEK5000VNM`** = the 5K menu,
  6 services @ $416.88, NO CVT line). This is why prices/service-counts won't reconcile to Joe's
  screenshots and the expected line is "missing." **ALWAYS read the `Package OpCode` BEFORE trusting
  the panel** — it must contain your interval number (TEK**90000**xxx for 90K). If it shows a
  different interval (TEK5000…), RE-CLICK the interval chip and re-verify the opcode flips. The
  highlighted chip is NOT proof the package loaded.
  ⭐⭐ /mouse RE-CLICKS CAN FAIL FOREVER (verified BT 2026-07-22): on the PILL-style rail
  (leaf pills "5K"…"200K" at y≈239, BT dealer 1249), SIX consecutive server /mouse clicks on
  the 70K pill's coordinates never flipped the package (stayed TEK5000BNM). THE FIX: dispatch
  synthetic MouseEvents on the pill's clickable ANCESTOR — climb parentElement while the
  parent's innerText is still short (<12 chars, i.e. still just the pill), then
  `['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,
  cancelable:true,view:window,clientX:cx,clientY:cy})))`. Worked FIRST TRY (ancestor class was
  `root_content_blackNormalContent…`). Same MouseEvent dispatch needed for the TIER button
  ("Preferred" etc.). Also: this rail is a horizontal CAROUSEL — pills for later intervals sit
  at x>viewport (70K at x=1748); click the `.icon-right-arrow*` button (~x1256,y251) in a loop
  until the target pill's x < ~1200 BEFORE clicking it. Verify by `Package OpCode : TEK<iv>...`
  regex, never by pill highlight. Read it via:
  `/eval {"js":"JSON.stringify([...new Set(Array.from(document.querySelectorAll('span,div,td,label')).filter(e=>e.children.length===0).map(e=>e.textContent.trim()))].filter(t=>/Package OpCode|TEK\\d/i.test(t)))"}`
- **RELIABLE TIER-CONFIRM ONE-SHOT:** after clicking interval THEN tier, verify all four anchors at
  once — opcode, total price, service count, and CVT-line presence — in a single eval so you KNOW
  you're on the right menu before "Add To Quote":
  `/eval` filtering leaf text for `/Package OpCode|TEK\d/`, `/^\$[\d,]+\.\d{2}$/` (≠$0.00),
  `/^Services \(\d+\)$/`, and `/CVT|Continuously Variable|Drain and Fill/`. Verified the 90K Value
  reconciles: **TEK90000VNM, $1,978.62, Services (13), CVT line present** = matches Joe's screenshot.
- **SURFACING THE ATTACHED PARTS (the working path, verified 2026-06-25):** after the menu is on the
  quote (`Services(1)` shows the TEKxxxxx line), the parts are NOT yet visible — **click the added
  service line's text** (`/click {"text":"TEK90000VNM"}`) to EXPAND it; the parts then appear in the
  DOM with qty/on-hand/unit/total. Pull a clean structured read by climbing from each part's leaf
  node to its row ancestor:
  `/eval {"js":"(function(){var nodes=Array.from(document.querySelectorAll('*')).filter(e=>e.children.length===0&&/^(303 - FLUID CONDITIONER|31832 - FULL SYNTHETIC CVT FLUID QTS)/.test((e.textContent||'').trim()));return JSON.stringify([...new Set(nodes.map(n=>{var r=n;for(var i=0;i<6&&r.parentElement;i++){r=r.parentElement;if(/\\$/.test(r.textContent)&&r.textContent.length<200)break}return r.textContent.replace(/\\s+/g,' ').trim().slice(0,180)}))])})()"}`
  VERIFIED RESULT (90K Value CVT line): **31832 FULL SYNTHETIC CVT FLUID QTS = 9 each × $42.75 =
  $384.75** + **303 FLUID CONDITIONER (BG 303) = 1 each × $30.64 = $30.64** = **$415.39 of wrong
  parts** behind that line every sale. Root cause confirmed: menu built with aftermarket synthetic
  CVT fluid + BG 303 instead of Toyota E-Trans (E-TAF 0888681986) this eCVT requires. Same on Premium
  (TEK90000PSM). Fix not yet executed — Joe walking Jay through it live (swap-vs-remove + edit in
  Service Menu Setups for it to stick going forward); get explicit go before Save/Publish.
- **The fix (once parts are confirmed):** the wrong parts (BG 303 + 31832) are attached behind the
  CVT service line in **Service Menu Setups** under that service's parts (or via "Choose Parts" in
  the quote) — detach them. Joe's logic: this Hybrid takes manufacturer E-Trans fluid, not BG CVT,
  so no BG CVT service → no BG 303 / 31832. Confirm the exact service-line→parts binding with Joe
  and get explicit go before any Save/Publish (live Published menu). NOTE Corolla Hybrid genuinely
  HAS an eCVT, so the question is fluid SPEC (E-TAF vs BG), not "remove CVT service entirely" —
  clarify scope with Joe.

### ⭐ READING THE INCLUDED-SERVICE OPCODE (BGCVTF — verified 2026-06-25)
The CVT line's opcode is NOT exposed in the collapsed menu quote (only the wrapper
TEK90000VNM shows). To get it, EXPLODE the menu into separate operations (Step 4.5
"Add Menu Services as separate operations" toggle) — that breaks each service into its
own opcode line. Joe identified it as BGCVTF. VERIFY directly by navigating
/ro/opcode/edit/BGCVTF (use execute_code -> curl /eval with json.dumps to avoid the
quote-escaping that breaks a raw -d body): the page reads "Opcode Details: BGCVTF -
DRAIN AND REFILL CVT FLUID" with Default-tab parts 303 - FLUID CONDITIONER +
31832 - FULL SYNTHETIC CVT FLUID QTS, and tabs Default | Overrides + "Add override".
Pull the CORRECT replacement part straight from the closed RO (tekion-openapi-repair-orders):
RO 565535 billed part 0888681986 name "08886-81986 - E-TAF,TE", qty 1, unit
$155.93 — that's the Toyota E-Trans fluid this eCVT requires.

### ⭐⭐⭐ THE OVERRIDE GOES IN SERVICE MENU SETUPS -> INCLUDED SERVICES, *NOT* OPCODE MANAGEMENT (Joe corrected Jay 2026-06-25)
I was about to build the override on /ro/opcode/edit/BGCVTF (Opcode Management). WRONG.
Joe: the override for a menu-included service is made in Service Menu Setups -> Included
Services, NOT Opcode Management — the SAME rule as the 15K rotation fix ("the opcode CANNOT
be fixed in Opcode Management"). When fixing the parts/pricing of a service that runs inside a
maintenance menu, the lever is always the menu builder's Included Services entry for that opcode,
not the standalone opcode edit page.

### ⭐⭐⭐ OVERRIDE PRECEDENCE — DO NOT REMOVE THE DEFAULT PARTS (Joe confirmed 2026-06-25)
Architectural fact Joe stated explicitly: "once you build the parts in the override, Tekion
will look at override first within the opcode." So to fix the wrong-fluid bug you do NOT delete
31832 or 303 from the Default tab. You ADD an override row scoped to the affected vehicle
(Toyota / Corolla Hybrid / 2024 only / all trims) with the correct part E-TAF 0888681986,
qty 1, $155.93. The override SUPERSEDES the default parts for that matched vehicle (it replaces
by precedence — it does NOT stack), while every other vehicle still gets the default 31832+303.
This resolves the earlier worry "will E-TAF just join the BG parts?" — no, the override wins.
SCOPE NOTE: "Corolla Hybrid" is a SEPARATE Tekion model from gas "Corolla"; Joe scoped this
override to 2024 Corolla Hybrid ONLY because that's the only model being reported.

### 🧭 OPENING THE TARGET INTERVAL ROW ON THE SETUPS LIST (kebab mechanics, verified 2026-06-25)
On `/ro/service-menu-setups`, the interval cell is an odometer animation (not clickable) so
you open a menu via its ⋮ kebab → Edit. Hard-won mechanics:
- The :9223 **`/click` endpoint does NOT accept x/y coordinates** — it returns
  `{"error":"One of selector, text, or ref is required"}`. You must click by selector/text/ref.
- The kebab icons did NOT match `icon-(more|kebab|dots|vertical|ellipsis)`; on SCT they render as
  `div.root_icon_size__md__… icon-over` at a fixed **x≈1209**, one per row, rows ~41px tall
  (header ≈y266, row1≈304, then +41 each). Map row→y first.
- CONFIRM the row before clicking: `document.elementFromPoint(360, Yrow)` text must read your
  interval (e.g. "90,000 mi"). Then TAG that kebab and click by selector:
  find the `root_icon_size__md` div closest to (1209, Yrow), `el.id="JAY_90K_KEBAB"`, then
  `/click {"selector":"#JAY_90K_KEBAB"}` → actions dropdown (Edit/Duplicate/Deactivate) → Edit.
- This proximity-tag-then-click pattern is the reliable way to hit a SPECIFIC row's kebab when
  all kebabs share the same class and the `0-action-kebabMenu` test-id always resolves to row 1.

### 🧭 REACHING THE OVERRIDE EDIT SCREEN — Included Services search + "Edit service" (verified 2026-06-25)
Joe's exact nav: for a SIMPLE parts override you do NOT need to open the mileage menu at all —
go straight to **Included Services** and search the opcode. Path that worked:
1. From a Service Menu Setups page, click the left sub-nav **"Included Services"** → lands
   `/ro/service-menu-setups/included-service` (SINGULAR "included-service"). Unfiltered it lists
   ~1,194 services.
2. **☠️ WRONG-SEARCH-BOX TRAP (cost a detour):** the page has TWO search inputs. The
   `placeholder="Search here..."` (`ant-input`) is the **GLOBAL RO search** — typing the opcode
   there + Enter NAVIGATES AWAY to the Repair Orders page ("Showing 0 out of 0"). The CORRECT one
   is the **page-level expandable search** `placeholder="Search..."`, class `root_expandableSearch`,
   data-test-id `@tekion-repair-orders-serviceMenuSetups-includedServiceTable-expandableSearch-searchBar`.
3. That expandable input is **collapsed/`offsetParent==null` until expanded**, so `/type` on it
   TIMES OUT ("element is not visible"). But once it IS visible, the reliable way to fill this
   React-controlled input is the native-setter via /eval (NOT /type):
   ```
   /eval {"js":"(function(){var i=document.querySelector('[data-test-id=\"@tekion-repair-orders-serviceMenuSetups-includedServiceTable-expandableSearch-searchBar\"]');i.focus();var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(i,'BGCVTF');i.dispatchEvent(new Event('input',{bubbles:true}));i.dispatchEvent(new Event('change',{bubbles:true}));return i.value})()"}
   ```
   then `/press {"key":"Enter"}` → filters to "1 Result(s)" with the opcode row.
4. On the filtered row, the kebab (⋮) at the far right (`root_icon_size__md … icon-ove…`, x≈1212)
   → proximity-tag-then-`/click` by selector (all kebabs share the class; tag the one nearest the
   row's y) → dropdown shows **"Edit service"** → `/click {"text":"Edit service"}`.
5. Lands `/ro/service-menu-setups/included-service/edit-service/<serviceId>/default` with tabs
   **Default | Overrides**, controls **"Pull From Opcode" / "Allow Override" / "Add override" /
   Parts**, and the Default-tab parts visible (303 + 31832 confirmed). THIS is the per-opcode
   override sub-panel. Click **Overrides** tab → **Add override** to build the vehicle-scoped row.
   (BGCVTF serviceId observed: 693c443aa21e1d4aa51afc42 — IDs are per-store, don't hardcode.)
NOTE: the Service Menu Setups LIST search you'd done on YOUR screen does NOT propagate to the :9223
browser session — always re-filter in the agent's own browser before acting on a row.

### Correct end-to-end fix plan for a wrong-parts menu line (the BGCVTF recipe)
1. Build a throwaway quote for the exact VIN+mileage; explode to confirm the opcode (BGCVTF).
2. Pull the CORRECT part + qty from the closed RO via OpenAPI (E-TAF 0888681986, qty 1).
3. Go to Service Menu Setups -> the target interval menu (90K) -> Included Services, find the
   BGCVTF "Drain and Refill CVT Fluid" entry.
4. Record baseline (current default parts + any existing override rows) for a clean revert.
5. Add an override row scoped Toyota / Corolla Hybrid / 2024 / all trims with part E-TAF
   0888681986, qty 1, $155.93. LEAVE the default 31832+303 untouched (override precedence handles it).
6. Save -> Publish (Publish required for the quote to reflect).
7. Re-quote the 2024 Corolla Hybrid -> confirm the CVT line now pulls E-TAF (and 31832/303 gone
   for this vehicle). Get Joe's explicit go before Save/Publish on the live Published menu.
NOTE the same wrong-parts setup exists on the Premium (TEK90000PSM) tier — apply the override there too.

## 🛑🛑🛑 STEP ZERO FOR ANY \"WRONG SERVICE/PRICE ON A MENU\" TICKET: PULL A CLEAN QUOTE FIRST (Joe stopped Jay TWICE, 2026-06-25)
Before ANY menu-row dissection, trim-membership walk, or \"menu is mapped wrong\"\nconclusion, **build ONE fresh throwaway quote for the exact VIN at the exact mileage and\nread what the menu ACTUALLY produces.** This confirms the symptom even REPRODUCES. Skipping\nthis is the #1 mistake — Joe caught Jay red-handed on RO 565983: Jay spent a dozen tool\ncalls dissecting 18 menu rows and concluded \"menu mapped wrong,\" then Joe asked **\"wait..\ndid you pull the quote first? nothing is wrong here.\"** A clean quote took 5 minutes and\nproved the menu was FINE.\n\nWHY THE CLEAN QUOTE IS DECISIVE (RO 565983 outcome): with the VIN decoded to its CORRECT\n**AT** trim (\"Base: Car 2.5L L4 4DR … FWD: **AT**: Car\"), the 60K menu pulled **\"Perform\nAutomatic Transmission Fluid Exchange Service\"** (correct) and the inspection \"Inspect\nautomatic transmission fluid\" — and **ZERO manual-transmission service lines** on both\nBasic ($168.88-ish service set, 9 services) and Basic+ (incl. 4-wheel alignment, brake\nfluid exchange, etc.). The original ticket symptom (\"Manual Transmission Exchange on Basic\n& Plus\") was an ARTIFACT of the RO having been built under the wrong/default MT trim BEFORE\nthe vehicle's master record was corrected to AT — NOT a menu defect. Verdict: **not\nreproducible → menu is okay → close the ticket.**\n\nTHE CORRECT ORDER OF OPERATIONS (do not skip ahead):\n1. **Clean quote FIRST.** Fresh VIN + mileage, let Tekion auto-decode the trim (don't force\n   it — see what it actually defaults to), read Basic + Basic+ service lists. Does the\n   reported bad line ACTUALLY appear? If NO → not reproducible, menu is fine, STOP and report.\n2. **Only if it DOES reproduce**, check the decoded TRIM + \"Default trim selected\" warning\n   (wrong-trim mapping, below).\n3. **Only then** walk menu rows / trim membership / row scoping.\n\nWHY THIS BURNS TIME WHEN SKIPPED: finding the same vehicle in multiple menu rows, or a\nservice on \"All trims\" rows, **looks like** a bug but is NORMAL Tekion design — overlapping\nrows resolve via override priority, and \"All trims\" + correct trim decode still produces the\nright services. Multi-row membership is NOT proof of a problem by itself; only the QUOTE\noutput is. Joe's framing: the quote is ground truth; the menu internals are theory. Lead\nwith ground truth.\n\nLESSON FOR JAY (Joe's recurring correction): Jay's diagnostics are strong but he dives into\ninternals before confirming the symptom. For EVERY \"wrong X on a menu\" ticket, the first\naction is a clean reproduction quote — never the menu editor.\n\n## ⭐ WRONG-SERVICE-LINE = WRONG-TRIM-MAPPING root cause (the MT-vs-AT trap, 2026-06-25)
A THIRD class of menu bug (distinct from wrong-PRICE and wrong-PARTS): a service line
appears on a menu that **shouldn't be there for this vehicle** (Joe's case: RO 565983,
2010 Camry — a **Manual Transmission Exchange** line showing on the 60K Basic & Plus
menus). The instinct is "the menu is wrong," but the FIRST thing to check is whether
**Tekion auto-decoded the VIN to the WRONG TRIM** — specifically a manual-transmission
trim on a car that's actually an automatic.

Joe's own diagnostic framing (verbatim): "see if the vehicle trim is an automatic, and
maybe the vehicle is just mapped to the wrong menu, or if the menu is wrong." So the
decision tree, IN ORDER, is:
1. **Wrong TRIM mapping?** (vehicle decoded to a manual trim → manual-trans service is
   correctly included *for a manual*, but the car is an automatic). ← check this FIRST.
2. **Wrong MENU mapping?** (vehicle is landing on a menu/row it shouldn't).
3. **Menu itself wrong?** (the menu wrongly includes the line for everyone). ← last.

### How to detect the wrong-trim mapping (verified RO 565983)
- Build the throwaway quote with the VIN (Steps 1–2). When the VIN decodes, **READ THE
  TRIM STRING and look for the transmission token.** Tekion's default trim for an
  ambiguous VIN looks like:
  **"Base: Car 2.5L L4 4DR Naturally Aspirated Gas Fi: FWD: `MT`: Car"** — the **`MT`**
  = Manual Transmission (vs `AT` = automatic, `CVT`). An `MT` here on a car that should
  be an automatic IS the bug.
- There is an orange warning right under the trim field: **"Default trim selected.
  Please select the correct trim for accurate services and pricing."** This is Tekion
  TELLING you the trim is a guess — its presence is a strong signal the trim/transmission
  may be wrong. Read the trim via screenshot+vision (the trim string is a CSS-truncated
  singleValue; vision reads it reliably).
- WHY it happens: many VINs decode ambiguously between MT and AT (e.g. 2010 Camry Base
  2.5L 4-cyl — NHTSA's DecodeVin also can't tell; it returns no Transmission field).
  Tekion grabs the DEFAULT/first trim, which is often the MANUAL variant, so a
  manual-only service (Manual Transmission Exchange / fluid) flows onto the menu.
- CROSS-CHECK the real transmission: NHTSA `DecodeVin/<VIN>?format=json` gives
  make/model/year/engine but often NOT transmission for these — so confirm the actual
  car with Joe ("is this one an automatic?") rather than asserting. Per never-guess:
  if the VIN is genuinely MT/AT-ambiguous, ASK before declaring the menu wrong.

### The fix (once Joe confirms it's actually an automatic)
- Primary: **select the correct Automatic (AT) trim** for the vehicle in the quote/RO —
  the manual-trans service then drops off because the AT trim's menu doesn't include it.
  Verify by re-pulling the 60K Basic/Plus and confirming the Manual Transmission Exchange
  line is gone.
- If it RECURS across a model/generation (Tekion keeps defaulting these VINs to MT), the
  durable fix may be at the VIN→trim default or at the menu's trim-scoping (scope the
  Manual Transmission Exchange row to MT trims only, so a mis-defaulted vehicle still
  wouldn't get it). Confirm scope/lever with Joe before any Published-menu change.

### Lesson
When a WRONG SERVICE (not a wrong price) shows on a menu, do NOT jump to editing the
menu. First read the decoded TRIM + the "Default trim selected" warning. A manual-trans
service on an automatic car is almost always a **wrong-trim mapping**, not a broken menu.

### ✅ RESOLUTION — RO 565983 was NOT a bug at all; menu is FINE (FINAL, verified 2026-06-25)
⚠️ SUPERSEDES the earlier \"counter-case\" reasoning below. After all the row-walking, Joe\nstopped Jay and made him **pull a clean quote** (see STEP ZERO at the top). With the VIN\ndecoded to its correct **AT** trim, the 60K Basic & Plus menus pulled the **Automatic**\nTransmission Fluid Exchange (correct) and **NO manual-transmission line**. So RO 565983 was\n**not reproducible — the menu is okay.** The ticket's \"Manual Transmission Exchange\" symptom\ncame from the RO being built under the wrong/default MT trim BEFORE the master Vehicle\nDetails record was corrected to AT. THE MENU WAS NEVER WRONG. All the multi-row membership\nfindings below were a red herring — overlapping rows + \"All trims\" are normal Tekion design,\nand a correctly-decoded AT trim simply doesn't match the manual-trans path. Keep the\nrow-walk MECHANICS below (they're reusable), but DISREGARD the \"menu mapped wrong\"\nCONCLUSION for this RO. The lesson: clean quote first; multi-row membership ≠ a bug.\n\n### ⚠️⚠️ (HISTORICAL / SUPERSEDED) earlier mid-session belief that RO 565983 was a menu-mapping bug
The decision tree above held #1 (wrong-trim) as the most likely. Mid-session Jay believed
RO 565983 (2010 Camry) was #3 — the menu IS wrong — and Joe said "I think that
means the menu is mapped wrong." ⚠️ This was REVERSED by the clean quote (see RESOLUTION
above): the menu is fine. Sequence Jay used to (incorrectly) build the menu-wrong theory:
- The throwaway-quote trim defaulted to MT (with the orange "Default trim selected"
  warning), which LOOKED like wrong-trim. BUT Joe's screenshot of the **Vehicle Details
  master record** already showed TRIM = "…FWD; **AT**; Car" (Automatic). So the master
  was correct AND the live RO still got the manual-trans line → the trim wasn't the bug.
- When the master record is already AT but the menu still served the manual line, the
  cause is the **menu row that carries the manual service is not trim-restricted to MT**.
- ROOT CAUSE CONFIRMED: in the 60K menu editor, the manual-trans service is literally
  **"Perform Manual Transmission Fluid Service"** (NOT "Manual Transmission Exchange" —
  that's the ticket's shorthand). It appeared on **6 vehicle-group rows, every one scoped
  "All trims selected"** (5 broad "Toyota / All Models" rows incl. Camry + the GR Supra
  row), with year scope including 2010. "All trims" = both MT and AT trims, so the service
  bleeds onto AUTOMATIC vehicles. That's the bug — a service that should be MT-only is on
  All-trims rows.
- FIX (get Joe's go before any Published-menu change): on the applicable "All Models /
  All trims" row(s), scope the **Manual Transmission Fluid Service** to MT trims only (its
  Trim Details → Transmission = MT), or exclude it from the AT path. Almost certainly
  recurs on OTHER interval menus (30K/90K/etc.) with the same All-trims row pattern.

REVISED DECISION TREE: still check wrong-trim FIRST, but the deciding evidence is the
**master Vehicle Details record's trim** (not the throwaway quote's defaulted trim). If
the MASTER is already the correct transmission yet the line still shows → skip straight
to menu-mapping (#3): find the row carrying the offending service and read its trim scope.

### 🔧 HOW TO WALK ROW TRIM-MEMBERSHIP IN THE MENU EDITOR (the reusable mechanics, verified 2026-06-25)
This is the "which row did this vehicle fall into / which row carries the bad service"
procedure on `/ro/service-menu-setups/edit/<menuId>` via the :9223 browser.
- **`/click` takes NO x/y coordinates** — `{x,y}` returns HTTP 400
  `{"error":"One of selector, text, or ref is required"}`. Click by selector/text/ref only.
  To hit a specific element by position: tag it via /eval with `data-jay`, then
  `/click {"selector":"[data-jay=...]"}`. (Raw mouse coords need a synthetic
  mousedown/mouseup/click dispatch via /eval — see the react-select notes elsewhere.)
- **Open the target interval:** on the Setups list, tag the `.icon-overflow` div inside
  the row whose innerText starts with "60,000 mi", /click it → dropdown
  Edit/Duplicate/Deactivate → /click {"text":"Edit"} → lands /edit/<menuId>.
- **Enumerate the vehicle-group rows:** they have ~one drag handle + one expand caret
  (`[class*=root_icon_size__md]` at x≈104) each. Reading each row's innerText gives the
  Make + truncated Model list ("Toyota All, 2WD Pickups, 4Runner… Camry…").
- **☠️ THE TRUNCATED-CHIP TRAP (cost the most time):** the Model chip showing "…Camry…"
  does NOT mean the row's selected TRIMS include any Camry. The bottom row here showed
  "Camry" in its Model chip but its **Trim Details modal contained only 1998 RAV4 trims**
  (84 selected) — typing "Camry" into that modal's search returned 0 results. ALWAYS
  verify actual trim membership, never infer from the Model chip.
- **Open a row's Trim Details:** find that row's trim input (`.ant-input` whose value
  matches `/trims selected|All trims/`), tag + /click it → "Trim Details" ant-modal opens
  (Filters by Engine/Cylinder/Transmission/Drive/etc. + a trim search + radios "All trims
  (incl future)" / "Specific trims"). Read `.ant-modal-body` innerText. To test membership,
  type the model into the modal's search input and read the result lines. **Always CLOSE
  with the modal's Cancel (never Save on a live menu)** — there are TWO "Cancel" elements,
  so tag the VISIBLE one inside the modal (offsetParent!=null, rect.x>=0) and click that;
  a bare /click {"text":"Cancel"} times out on the hidden duplicate.
- **FASTER than per-row trim-walking when hunting a specific BAD SERVICE:** EXPAND every
  row (the carets ignore synthetic .click but a dispatched mousedown/mouseup/click MouseEvent
  sequence at the caret's coords DID expand them — verify by grepping the page for known
  service names afterward), then grep `document.body.innerText` for the exact service label.
  For each occurrence, walk UP the DOM to the ancestor that also contains a "trims selected"
  input = the owning vehicle-group row; read that input's value (All trims vs N trims) and
  the row header text (Make/Model/Year). This directly answers "which rows carry the bad
  service and are they All-trims (bug) or MT-only (correct)." This is how RO 565983 was
  nailed: 6 occurrences of "Perform Manual Transmission Fluid Service", all on All-trims rows.
- **Service-label gotcha:** the offending line's real label may differ from the ticket's
  words. Grep broadly (`/manual/i`, `/transmission/i`) to discover the exact strings —
  this menu had FOUR trans services: "Perform WS Automatic Transmission Fluid Exchange
  Service", "Perform Automatic Transmission Fluid Exchange Service", "Drain and Fill CVT
  Fluid…", and "Perform Manual Transmission Fluid Service" (the MT one).
- After the rows settle, most reload to "All trims selected" — a row showing "N trims
  selected" is usually a specific carve-out (here the RAV4 row); don't assume the
  numbered-trim row is "the" Camry row.

### ⭐⭐⭐ "ALL TRIMS" ROWS *ARE* SEARCHABLE FOR THE VEHICLE — and MULTI-ROW MEMBERSHIP PROVES THE MENU IS WRONG (verified 2026-06-25, Joe's method)
CORRECTION to an earlier wrong claim ("All trims rows show no enumerated list / 0
results / you can't search the vehicle in Trim"). **THAT IS FALSE.** Verified on RO
565983 (2010 Camry, 60K menu): rows on the **"All trims (including future trims)"** radio
STILL have a searchable, scrollable (virtualized) trim list (e.g. "502 search results",
"104", "15"). You absolutely CAN — and per Joe MUST — open EACH row's Trim Details and
SEARCH THE EXACT VEHICLE to confirm membership.

JOE'S MANDATORY METHOD (verbatim intent): "click on every one of the trims window… it
pulls up a new window, Trim Details… you'll have to scroll and look. I bet that vehicle
will show up in MULTIPLE rows, indicating the menu is wrong." The proof of a menu-mapping
bug is that the SAME vehicle is a member of MORE THAN ONE vehicle-group row.

PROCEDURE (the reusable multi-row membership walk):
1. Enumerate trim inputs in document order — ids `trim_0`, `trim_1`, … (one per row). pos=index+1.
2. For each row: open its trim input (scrollIntoView center, then dispatch
   mousedown/mouseup/click MouseEvent at the input's x,y — a plain /click TIMES OUT on
   off-screen/unstable inputs; the synthetic dispatch + `.focus()` opens the modal).
3. In the modal find the search input (non-radio input width>120), tag data-jay, and
   **/type the narrowed query "<YEAR> <MODEL>"** (e.g. "2010 Camry") so the virtualized
   list filters WITHOUT deep scrolling. Wait ~1.5s.
4. Read membership: grep `.ant-modal-content` innerText for the "<YEAR> <MODEL>" line +
   capture the "N search results" count. has-match = vehicle IS a member of that row.
5. **CLOSE with the modal's Cancel** — tag the VISIBLE Cancel inside `.ant-modal-content`
   (offsetParent!=null); there are TWO Cancel elements so a bare /click {text:Cancel}
   times out on the hidden one. NEVER Save on a live Published menu.
6. Tally matching positions. **>1 matching row = menu mapped wrong** (Joe's signal). RO
   565983 result: 2010 Camry was a member of **Rows 1, 2, 7, 13** of the 60K menu → menu
   mapped wrong, exactly as Joe predicted.

☠️ VIRTUALIZATION RESULT-COUNT DRIFT: the "N search results"/row-count is UNSTABLE across
re-opens of the SAME row (Row 1 showed "2" one open, "14" the next; Row 2 showed "104"
pre-filter then "7" after the search applied). The COUNT is unreliable; the MEMBERSHIP
(does "<year> <model>" appear at all) is the reliable signal. If a row shows a big count
and has-match=false, the search hadn't applied yet — RE-CHECK that row before concluding
non-membership.

⏱️ BATCH ≤9 ROWS PER execute_code CALL: walking ~18 rows (open+search+cancel ~5-6s each)
EXCEEDS the 300s execute_code timeout. Do batches of ≤9; the `trim_N` ids persist across
calls so resume by index.

🔎 TRUNCATED-CHIP LIE (reconfirmed, opposite direction): the Model chip can SHOW a model
the row does NOT actually contain at trim level — the bottom 60K row chip read "…Camry…"
but its Specific-trims selection was 84 1998-RAV4 trims; "Camry" search → 0 results. The
chip both over- AND under-reports; ONLY the in-modal vehicle search is authoritative.

NEXT STEP after proving multi-row membership: for each matching row, drill the
transmission variants (AT vs MT) of the matched model and tie which matching row carries
the offending service (e.g. "Perform Manual Transmission Fluid Service") — that names the
exact row+trim+service to fix. Get Joe's go before any Published-menu change.

## ⭐ FOURTH SYMPTOM CLASS — "ALL 3 TIERS QUOTE THE SAME $ AMOUNT" (verified 2026-06-26, RO 565663)
Distinct from wrong-PRICE / wrong-PARTS / wrong-SERVICE-LINE: the advisor reports
"all 3 service options were the same $ amount." This means Basic / Basic+ / Signature
all price identically because the upper tiers add NO incremental services over Basic
for that vehicle (so all three resolve to the same service content → same total).

### Step-Zero clean quote still applies — reproduce FIRST
RO 565663: 2016 Scion tC, VIN JTKJF5C79GJ024481, ticket said "12K". Built a throwaway
quote @ 12,000 mi → Service Menu tab. ⚠️ **THERE IS NO LITERAL "12K" TILE** — the rail
shows 5K/10K/15K/20K/25K. A 12,000-mi vehicle maps to the **10K** package (TEK10000BNM).
When the advisor's interval has no exact tile, quote the nearest LOWER package (the one
the odometer falls into) first; if it doesn't reproduce, also try the next tile up and
ask Joe which interval he means.

### THE TECHNIQUE: read each tier's price + content (Tekion shows only the SELECTED tier)
Tekion's package panel displays ONLY the currently-selected tier's total + service list
— it does NOT show all three side by side. So you must CLICK each tier tab and capture
its total. Verified procedure (after the 10K package is loaded — confirm
`Package OpCode : TEK10000BNM` is showing):
```
for tier in ["Basic","Basic +","Signature"]:   # note the SPACE in "Basic +"
    /click {"text": tier}; sleep 2.5
    /eval {"js":"JSON.stringify((document.body.innerText.match(/\\$[\\d,]+\\.\\d{2}/g)||[]))"}
```
RESULT (565663): Basic / Basic+ / Signature ALL = **$217.10**, and ALL showed the
**same 2 services** (Perform Tire Rotation + Change Engine Oil/Filter) + 10 inspections.
That identical service content across tiers IS the confirmation — not just the equal
price. A correctly-tiered menu has Basic+ and Signature each LAYERING ON more services
(filters, fluid services, etc.) at a higher total.

### ☠️ VERIFY IT'S REAL, NOT A REFRESH ARTIFACT
Clicking a tier tab by text-match can leave a STALE price if the panel didn't actually
switch. CONFIRM the switch by reading the **service COUNT + service NAMES** for the
selected tier (screenshot+vision is the reliable cross-check), not just the dollar
figure. 565663 confirmed Signature genuinely showed only 2 services (same as Basic) —
so the equal price was real, not stale.

### Root cause + where the fix lives (get Joe's go before any change)
The upper tiers carry no extra included services for this vehicle's scope. Likely
either (a) the Basic+/Signature tier columns in this menu's setup have no additional
services assigned to the Scion tC's vehicle row, or (b) the upper tiers were never
built out for older non-Toyota (Scion) models. CONFIRM by opening the 10K menu in
Service Menu Setups and reading the applicable vehicle row's tier columns (Basic /
Basic+ / Signature) in Modify System Services / Add Services — which services are
checked per tier. Do NOT assert the cause from the quote alone; inspect the row config
(read-only) first, then bring Joe the fix plan. NEVER edit/Publish without his go.

NOTE the Scion tC again decoded to a **default MT trim** with the orange "Default trim
selected" warning (same MT/AT ambiguity as the 2010 Camry) — note it, but for an
"all tiers same price" ticket the trim is usually NOT the cause (the equal-price bug is
a tier-content problem, not a trim problem). Don't let the trim warning derail the
tier-content diagnosis.

### ⭐⭐ VERIFIED CASE + THE ATTRIBUTE-BUCKET ROOT CAUSE (2023 Sienna hybrid, SCT, 2026-07-15)
Kevin's ticket: "Sienna menus broken, same price on all three tiers." Full diagnosis worked
end-to-end and revealed the general root-cause pattern for this symptom class:

**CONTROL-VEHICLE ISOLATION (the key move):** don't stop at reproducing on the reported
vehicle — quote CONTROL vehicles on the SAME intervals to isolate WHICH row bucket is broken:
- 2023 Sienna (hybrid) 30K: $562.74 / $562.74 / $562.74 — BROKEN (identical, same 4 services/tier)
- 2022 Camry 30K: $949.50 / $2,032.02 / $2,364.02 (9/14/17 svcs) — fine
- 2022 Prius (ALSO hybrid) 30K: $944.27 / $1,978.62 / $2,310.62 — fine
- 2018 Sienna (gas V6) 45K: $261.47 / $595.35 / $1,081.28 — fine
Conclusion: NOT "all Siennas", NOT "all hybrids" — it's ONE vehicle-row bucket. SCT menus
have NO model-specific rows; rows are segmented by **DRIVE_TYPE × TRANSMISSION × FUEL_TYPE
attribute buckets** (read from each row's TRIM parameter `standardTrimFilterDetails`). The
2021+ Sienna hybrid decodes into a hybrid bucket (its e-CVT decodes differently than Prius's
CVT → different row) whose Basic+/Signature tier services were never populated. With
priceConfig = **SUM_OF_SERVICES and no tier add-on services checked, all tiers collapse to
the identical total** — that's the config signature of this bug. The working hybrid bucket
(Prius's row) is the fix template.

### ⭐⭐ BULK MENU-ROW DUMP — read EVERY menu's rows+pricing via API in one pass (2026-07-15)
Beats per-row Trim-modal walking by an order of magnitude when you need row scoping across
many interval menus. All in the :9223 logged-in browser:
1. **Menu detail endpoint (GET, works with captured headers):**
   `/api/service-module/u/opcode/service-menu/<menuId>` → `data.menus[]` = the vehicle rows,
   each with `parameters` (MAKE/MODEL/YEAR/TRIM — TRIM carries `standardTrimFilterDetails`
   with the DRIVE_TYPE/TRANSMISSION/FUEL_TYPE bucket) and
   `priceConfig.priceTierMappings[]` ({packageType BASIC/VALUE/PREMIUM, drivingCondition
   NORMAL/SEVERE, menuPriceType SUM_OF_SERVICES|TOTAL_MENU_PRICE, value}).
   ⚠️ The `/service-menu/search` POST endpoint 500s ("unexpected.error") — don't use it.
2. **Capture auth headers:** install an XHR hook that records `setRequestHeader` args on any
   /api/ request, then SPA-navigate (history.pushState + PopStateEvent) to
   /ro/service-menu-setups to make the app fire a request → `window.__hdrs` now replays in
   in-page `fetch(url,{headers:window.__hdrs})`.
3. **Get the menu-id list via REACT FIBER** (list API is broken, DOM rows have no hrefs):
   find a row cell ('30,000 mi'), walk to the element with a `__reactFiber$` key, climb
   `.return` checking `memoizedProps.data/.dataSource/.record` for an array of objects with
   `.id` + `.intervals` — that's the full menu list (25 on SCT incl. ids).
4. Loop menus → fetch detail → per row extract models/years/trim-bucket + priceTierMappings;
   flag rows where all TOTAL values identical or where SUM_OF_SERVICES rows exist for the
   target vehicle. Dumps 79 menus in ~20s.
⚠️ These fetches return ~120KB per menu — process IN-PAGE (store to window.__menuDump,
return only summaries) or the eval response truncates.

### ☠️ QUOTE-BUILD GOTCHAS learned this session
- **NEVER fabricate a VIN** — a made-up VIN fails decode ("VIN Cannot be decoded!").
  Use the **Manual** radio instead: for each of Make*/Year*/Model*, find the label div,
  climb to its container, tag the react-select `<input>` with data-jay, /type the value,
  /press Enter. Verify via `[class*=singleValue]` texts = ["Toyota","2023","Sienna"].
- **Interval tiles are CARDS** matching regex `^\d+(\.\d+)?K mi\s*Maintenance Package$`
  (b.width<300, b.height<160) — click via synthetic mousedown/mouseup/click MouseEvent on
  the card div. Bare `/click {"text":"30K mi"}` and clicking "45K" leaf text are unreliable;
  the card regex works every time. The rail shows only ~4 cards around the odometer
  (25K/30K/35K/40K for a 25,000-mi quote) — for other intervals build a new quote at a
  different odometer (a 47,000-mi quote shows 45K/50K/55K/60K).
- **Tier verify = Package OpCode suffix**, not the highlighted button:
  Basic→TEK<iv>BNM, "Basic +"→TEK<iv>VNM, Signature→TEK<iv>PSM. Loop click-tier →
  re-read `Package OpCode : (TEK\S+)` until the suffix matches (up to 3-4 retries, ~3s
  apart — tier clicks frequently no-op the first time).
- **The 300s execute_code timeout WILL kill long tier sweeps** — batch ≤1 interval
  (3 tiers) per call. State persists in the page between calls.
- **Evidence to capture per tier:** the `Services (N)` count + the service NAMES between
  "Services (" and "Package OpCode" — identical service lists across tiers is the proof
  the tiers collapsed (equal price alone could be coincidence).
- Interval cards leave a package modal open — click its Cancel before selecting another
  card, or subsequent card lookups return nothing.

## Reporting
Report: the interval + tier + opcode, the line that's mispriced, the exact delta, the
opcode's pricing METHOD (Fixed vs Dynamic/SCP vs $/hr), whether there are DUPLICATE
included-service entries for that opcode, and whether the tier even makes sense (e.g.
15K Basic includes rotation but NO oil change). Do NOT change anything unless Joe
explicitly says to. The fix lives in Service Menu Setups Included Services (swap the
included-service variant), NOT the opcode default and NOT Opcode Management.
opcode/catalog labor price (Intervals & Opcodes tab), NOT a flat tier override.

## Pitfalls
- `/ro/service-menu` viewer may not resolve a VIN; Quotes does — use Quotes.
- Tier total strings can split across DOM nodes; regex the innerText for `$X.XX`.
- The package list shows totals only; per-line price is ONLY obtainable by the
  uncheck-delta method above.
- Always confirm the active dealer before quoting — wrong store = wrong menu.
- EDIT-SIDE: all row kebabs share `0-action-kebabMenu`; selecting the test-id hits
  ROW 1, not your interval. Map kebab→row text first, tag the right index, and
  confirm the "Edit Menu - <interval> mi" title before reading anything.
- EDIT-SIDE: the first "All Models" row can carry DUMMY prices ($1,000/$2,000/$3,000)
  — reconcile the row's prices to the Step-4 quote to find the REAL active row
  (bottom-most applicable / specific-trim row usually wins).
- EDIT-SIDE: a SYSTEM (factory) service line won't appear in the row's Modify/Add
  Services list and isn't priced on the edit screen — its price is in the opcode/
  service catalog (Intervals & Opcodes tab). Don't conclude the price is "missing";
  it's one level down. Stop and ask if you can't reach it without guessing.
