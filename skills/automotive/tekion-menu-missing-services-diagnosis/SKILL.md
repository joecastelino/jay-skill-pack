---
name: tekion-menu-missing-services-diagnosis
description: >
  Diagnose a Tekion service-menu ticket where a manager/advisor says the menu is
  "missing items", "missing services", "the service didn't show up", or the
  package looks short — i.e. WRONG CONTENT, not wrong price. Differential
  diagnosis across the 4 known root causes (row tier-coverage gap, wrong
  baseSystemInterval stamp, row-scope miss, inert Modify-System-Services entry),
  all readable over the API without a browser. Sibling of
  tekion-quotes-menu-price-diagnosis (that one = wrong DOLLARS; this one = missing
  LINES).
triggers:
  - menu is missing items
  - missing services on the menu
  - service didn't show up on the quote
  - package looks short
  - menu content wrong
---

# Tekion Menu — "Missing Items" Differential Diagnosis

## When to load this
Someone (store manager, advisor, Joe relaying them) says a menu package is
**missing services / items / lines**. This is a CONTENT failure, not a pricing
failure. If the complaint is about a wrong dollar amount, use
`tekion-quotes-menu-price-diagnosis` instead.

⚠️ **STEP ZERO still applies** (Joe stopped me twice on this at SCT): pull a clean
throwaway quote on the exact VIN + mileage FIRST to confirm the symptom even
reproduces, before dissecting menu rows. But for "missing items" specifically, ALSO
run the tier-coverage audit below — it's a 10-second API read and it has already
caught a real production bug that a single quote would have missed (a quote only
shows you ONE tier/condition card).

## The 3 known root causes, in order of how fast they are to rule out

### 1. TIER-COVERAGE GAP (found at BC 2026-08-18 — the sneakiest)
A factory line was suppressed across all 6 packageType/drivingCondition combos but
the replacement sibling was enabled on only some. Result: on the uncovered cards the
service renders **nothing at all** — no line, no price, no error.

**THE INVARIANT:** when you suppress a factory line and add a replacement, the
replacement's enabled tier set MUST exactly equal the suppression's tier set.
A swap replacement is NOT an optional add-on.
- **Add-on** (optional upsell over untouched factory content) → tier-selective is fine
  (BT's 25 add-ons are deliberately PREMIUM/SEVERE-only).
- **Swap replacement** (suppressed factory line) → must match suppression exactly
  (BT's oil/rotation/cabin swaps are correctly all-tiers).
Carrying "add-on = Premium-only" muscle memory onto a swap row is exactly how the BC
bug happened.

**Detect:** run `scripts/tier_coverage.py` (below). Any combo printing
`NOTHING ENABLED` is a missing-items bug for every vehicle matching that row.

### 2. WRONG baseSystemInterval STAMP (found at BT 2026-07-13 by Tony)
Each menu **row** carries `baseSystemInterval`, which decides WHICH factory
maintenance package renders at quote time — independent of which interval menu the
row lives in. A row created through the UI inherits the **menu-level default**
(often 5000/10000), NOT the menu's own interval. Bottom-most row wins → vehicle gets
the 5K/10K factory package on a 30K/172.5K menu → short inspection list, missing
engine air filter / ATF / ball joints / brake lines etc.

**Price tell:** a higher interval's Basic quote equals the 10K's price exactly
(e.g. $239.85 at BT) AND shows the short 10K inspection list.
**Detect:** `scripts/check_base_interval.py <menuId>` — every row's stamp should
match the menu's own interval (or the interval-appropriate native-row stamp).
**Fix surface:** inside the expanded row, ant-select `div#BASE_SYSTEM_INTERVAL_SELECT`
("Base System Interval *") → pick `"<interval> mi"`.

### 3. ROW-SCOPE MISS
The vehicle doesn't match any tier row (make/model/year/trim/fuel/cylinder filter),
so it falls through to factory content — or matches a row you didn't intend
(bottom-most applicable row wins). Common at BC where rows are Chevrolet-only:
GMC/Cadillac/Buick never match and bill factory dynamic pricing.
**Detect:** `check_base_interval.py` prints each row's scope; compare against the
complaint vehicle's decoded trim. Confirm the decoded STYLE actually matches the
engine scope — a VIN decoding as 5.3L will silently skip a 6.2L row.

### 4. ⭐ INERT "MODIFY SYSTEM SERVICES" ENTRY — MSS can only toggle what the factory feed already sends (verified SCT 2026-08-21, RO 566084 inverter coolant)
The #1 cause of "no menu item, **no labor or parts**". An MSS row can be present,
`included:true`, correct tiers enabled — and still render NOTHING, because
**Modify System Services only suppresses/modifies services the factory (SCP) base
package already delivers for that vehicle.** If the base feed doesn't carry that
service for that trim, the MSS entry is a silent no-op. MSS is NOT an injector —
**Add Services** is. (Same architecture lesson as the rotation swap case.)

**CASE:** RO 566084, 2018 Toyota Camry **SE/XLE Hybrid** (VIN 4T1B21HK6JU004820,
60,596 mi in), advisor Robin: "inverter coolant service is missing — no menu item,
labor or parts."
- SCT 100K menu `6942d17b43914842ddb9f968` (ACTIVE), **row order 3 = the hybrid row**
  (FUEL_TYPE `['Hybrid (PHEV)','Hybrid (FHEV)']`, Toyota / ALL_MODELS / ALL_YEARS,
  `baseSystemInterval 100000` ✔).
- That row DOES contain `TEK05050913 "Replace Engine & Inverter Coolant."`, type
  **MODIFIED_SYSTEM**, `included:true`, tiers BASIC/NORMAL + VALUE/NORMAL +
  PREMIUM/SEVERE = true.
- The row IS winning — live quote tier totals match its `priceTierMappings`
  TOTAL_MENU_PRICE exactly: Basic **$857.88** / Basic+ **$1,081.88** / Signature
  **$1,271.88** (TEK100000BNM / VNM / PSM). So this is NOT a scope miss.
- Yet the rendered service list shows plain **"Replace Engine Coolant."** and no
  inverter line on all three tiers; Choose Parts shows only `SUPER LONG LIFE COOL
  $57.60` under it. → the MSS entry had nothing in the base feed to attach to.

**SECOND HALF OF THE BUG — the opcode is empty anyway.** Even once injected it prices $0:
`GET /api/service-module/u/opcode/TEK05050913` → `description "Cooling System Drain &
Refill"`, `opcodeType INDIVIDUAL_SERVICE`, `laborTimeInSeconds 0`,
`customerLaborTimeInSeconds 0`, `manufacturerLaborTimeInSeconds 0`, `parts null`,
and every `priceDetails[]` entry `laborRateId:null / pricePerHour:null / flatPrice:null`.
That is literally "no labor or parts."

**THE 3-PART FIX (needs Joe's explicit go — live PUBLISHED menu):**
1. Put labor hours + coolant part(s) on opcode **TEK05050913** in Opcode Management
   (TEK factory opcode → Opcode Mgmt is the right surface for its Default pricing).
2. On the 100K menu hybrid row (order 3), add the service via **Add Services** with
   all intended tiers checked — NOT Modify System Services. The existing MSS entry is
   inert either way.
3. ⚠️ **PRICE IMPLICATION:** that row is `TOTAL_MENU_PRICE` (fixed 857.88 / 1081.88 /
   1271.88), NOT SUM_OF_SERVICES — so adding the service gives it away **for free**
   unless the tier prices are raised. Always surface this before adding a line to a
   fixed-price row.

### ✅ EXECUTED REMEDIATION PLAYBOOK (SCT 2026-08-21, all 3 parts saved & verified)
Joe approved and this ran end-to-end. Exact mechanics, browser :9225 (`/eval` body key
is **`js`**; screenshot is **`GET /screenshot?path=...` returning base64** — `POST
/screenshot` 404s on this server build).

**PART 1 — build the opcode** (`/ro/opcode/edit/TEK05050913`, Default tab):
- Labor is **NOT** a seconds field. It's two `input.ant-input-number-input` boxes
  labeled **Customer** and **Manufacturer**, in **HOURS** (`1.00`). They sit ABOVE
  Labor Rate Configuration and default to 1.00 — set both explicitly anyway.
- Labor Rate Configuration → **Add** row → Pay Type resolves to `CP - Default` →
  Labor Rate dropdown → **Fixed Price** → price input (`placeholder="Enter price"`).
  Match the row's existing convention (SCT 100K row 3 = flat dollars: SMERP $20.00,
  BGBAT $67.80, SM4ALIGN $75.00) — do not back-solve hours × rate.
- Parts: react-select **`#partName_undefined`**. Type the part number **without
  dashes** (`00272SLLC2`); the option list `[class*="-option"]` returns index 0 =
  `Create "…"` (**never click this**) and index 1 = the real `00272-SLLC2 - SUPER
  LONG LIFE COOL`. Then Qty + Parts Price on that row's
  `input.ant-input-number-input` pair.
- Commit with **Update** (buttons are `Save Draft` / `Cancel` / **`Update`**).
  Require toast `Opcode 'TEK05050913' has been updated successfully`.

**PART 2 — inject via Add Services on the menu row**
(`/ro/service-menu-setups/edit/<menuId>`, expand row caret at **x≈111**, row y from
`.rt-tr-group` bounding rects):
- ⚠️ **THE DISAMBIGUATION TRAP:** after you add it, the SAME service name exists in
  BOTH `Modify System Services` and `Add Services`. Never match by text alone —
  locate the three section headers as **leaf elements** with exact text
  (`Modify System Services` / `Add Services` / `Modify System Inspections`), read
  their `y`, and bucket each service row by which header it falls under.
- ⚠️ **HIDDEN DUPLICATE:** the page renders a second off-screen copy of the row
  builder at **negative y** (saw cells at `y:-203` and `y:374` for the same service).
  Always target the positive-y / visible one.
- The Add Services blank row's react-select is the 2nd `[class*="-control"]`
  containing "Select" under that row. Type the service name, click the single option.
  New rows arrive with **all 4 tier checkboxes already true** — verify, don't assume.

**PART 3 — raise the tier prices (mandatory on TOTAL_MENU_PRICE rows)**
- Find the price inputs by matching their CURRENT values (`857.88` / `1,081.88` /
  `1,271.88`), tag them, `/type` the new values, then Tab. They reformat with commas
  (`1,032.88`) — read back allowing for the comma.
- **Labor Hours** are a SEPARATE `Custom / Menu Labor Hours hrs` row (same
  `/^\d[\d,]*\.\d\d$/` input pattern, lower y — e.g. 2.50/4.10/4.80). ASK Joe whether
  to bump them; it's a pay decision, not a Tekion one. On this case he said "bump the
  hours as you needed to" → added the new op's 1.00 hr to all three:
  **2.50→3.50 / 4.10→5.10 / 4.80→5.80**.
- **Save** (buttons `Save` / `Cancel` / **`Publish`**) → toast
  `Service menu saved successfully`. **Do not Publish without explicit go.**
  Publish is a plain button with **no confirmation modal** → toast
  `Service menu published successfully`.

⚠️ **`/type` (page.fill) INVALIDATES `data-jay` TAGS ON SIBLING INPUTS.** Filling one
React number input re-renders the group and strips the attributes off the others →
the next `/type` dies after 30s with `page.fill: Timeout … waiting for locator`.
**FIX: re-tag ALL inputs after EVERY single `/type`, `scrollIntoView` the next target,
then fill it. One at a time, re-query between each.** This bit me on the 3 labor-hour
fields (first succeeded, next two timed out) and cost ~65s per failed call.

**VERIFY LIKE THIS OR YOU'RE LYING TO YOURSELF:** re-reading the same DOM after Save
just re-reads your own unsaved state. Navigate to `/home`, wait, navigate BACK to the
edit URL, re-expand the row, and re-read. Only then are the persisted values real.
(Confirmed: service present under Add Services w/ 4 tiers true, prices 1,032.88 /
1,256.88 / 1,446.88 survived the remount.)

**Also:** BT-style Pendo tour overlays swallow `/mouse` clicks — run
`document.querySelectorAll('[id*=pendo],[class*=pendo]').forEach(e=>e.remove())`
after every hard nav.

### ✅ FINAL RESULT — PUBLISHED & QUOTE-VERIFIED (SCT 2026-08-21)
Joe cleared Publish. Post-publish clean quote, VIN `4T1B21HK6JU004820` @ 100,000 mi
(QO# 000657), all three tiers walked with the opcode suffix confirmed flipping:

| Tier | Package OpCode | Price | Inverter line | Svc count |
|---|---|---|---|---|
| Basic | TEK100000**BNM** | **$1,032.88** | ✔ present | 8 |
| Basic + | TEK100000**VNM** | **$1,256.88** | ✔ present | 11 |
| Signature | TEK100000**PSM** | **$1,446.88** | ✔ present | 13 |

`Replace Engine & Inverter Coolant.` now renders on all three cards, priced $175.00
(2 × 00272-SLLC2 @ $57.60 = $115.20 parts + $59.80 flat labor), 1.00 flag hr added to
each tier's menu hours. Root cause #4 confirmed fixed by the Add-Services route.

**QUOTE-PORTAL NAV (exact, this build):** `/ro/quotes` → **Create Quote** btn
(top-right ≈1168,96) → `Search VIN #` input + **Enter** → odometer input → **Continue**
→ lands on `/ro/quotes/<id>/service/new`. In the RIGHT panel the **Service Menu** tab
(≈1009,304) must be clicked *before* the interval tile is live; the interval rail then
renders and the tile (`100K mi`) opens the package card. Tier tabs sit at **y≈325**:
Basic **622** / Basic + **718** / Signature **829** — real `/mouse` clicks only
(synthetic MouseEvents no-op and fake "all tiers identical"). Read price + opcode by
regex off `document.body.innerText`; **do not trust vision here** — at a 720px viewport
it reports "no tier tabs / no package panel" simply because they're below the fold.

**FLEET-WIDE CENSUS ONE-LINER** (every ACTIVE menu's hybrid rows + their MSS entries, ~5s):
```python
for m in active_menus:                       # /u/opcode/service-menu/list
    d = get(f'{B}/service-menu/{m["id"]}')['data']
    for row in d['menus']:
        fuel = TRIM_param.get('standardTrimFilterDetails',{}).get('FUEL_TYPE')
        mods = [svc(s['referenceId'])['name'] for s in row['servicesMetaData']['services']
                if s['type']=='MODIFIED_SYSTEM']
```
SCT result: inverter coolant appears in **exactly one** menu (100K row 3). Hybrid-only
rows exist at 30K/60K/90K (7 rows each, zero MSS entries), 100K, and 120K
("Replace brake booster vacuum pump." × 7 rows). Resolve a `referenceId` to
name+opcode with `GET …/u/opcode/service/<referenceId>`. `…/u/opcode/search` POST
**500s** — don't bother.

## Fast API read path (no browser)
All three checks read the menu config over plain urllib — no browser, no session
contention, no dealer drift.

```python
HDRS = dict(json.load(open('/tmp/tekion_rec_headers.json')))
HDRS['dealerId']   = '1251'        # target store
HDRS['tek-siteId'] = '-1_1251'
url = f'https://app.tekioncloud.com/api/service-module/u/opcode/service-menu/{MENU_ID}'
```
- Path is `/u/opcode/service-menu/<id>` — the bare `/u/serviceMenu/<id>` 404s.
- Rows: `data.menus[]` sorted by `order`; scope lives ONLY in `parameters[]`
  (top-level make/models/years stay null even on scoped rows — don't be alarmed).
- Services: `row.servicesMetaData.services[]`, each
  `{referenceId, type: MODIFIED_SYSTEM|ADDED, tierMappings:[{packageType,
  drivingCondition, enabled}]}`. A suppressed service STAYS in the list with all
  `enabled:false` — **diff enabled flags, not presence**.
- Name/opcode: `GET /u/opcode/included-service/<referenceId>`.
  ⚠️ If the cached header file is scoped to a DIFFERENT dealer, these lookups 404
  under a swapped dealerId. The tier-flag structure still reads fine — which is all
  the coverage audit needs. Don't let 404s on name resolution stop the diagnosis.
- `data.modifiedTime` on this endpoint is epoch **SECONDS**, not ms.

## One-shot audit script
`scripts/menu_audit.py <MENU_ID> <DEALER_ID>` runs all three checks in one pass and
prints a PROBLEMS summary at the end. Example:
```
python3 scripts/menu_audit.py 65530c2cd0e3ef410082bb2c 1251
```
Store-agnostic — works on any of the 7 AMG dealers. Dumps the raw config to
`/tmp/menu-<MENU_ID>.json` so you can diff before/after a fix.
Run it BEFORE proposing a fix and AGAIN after publishing.

## ⚠️ THE VERIFICATION BLIND SPOT (the real lesson from BC)
**Penny-verifying one card does NOT verify a menu.** At BC I penny-verified six
tiers over a month ($119.95 / $129.95 / $179.95 / $204.95 / $214.95 / $249.95) and
every single check landed on a tier/condition card that happened to have the
replacement enabled. The bug lived in the three combos I never opened. My
verification method and my bug had the *same blind spot*, so the bug was invisible
to my own QA.

**Rule: after ANY suppress/swap menu build, run the tier-coverage audit before
declaring done — and treat a price-verified quote as proof about ONE card only.**
A tier isn't verified until all six packageType/drivingCondition combos are read.

## Reporting to Joe
Don't conflate failure classes. Separate:
- missing LINES (this skill) vs wrong DOLLARS (price-diagnosis skill)
- pre-existing open gaps (e.g. BC's unbuilt T7 Mobil 1, the L8T part-number gap)
  from the newly found bug
State which root cause the evidence supports, and if a live PUBLISHED menu needs
changing, get Joe's explicit go first (never-guess rule) — including confirming the
INTENDED tier coverage rather than assuming all six.
