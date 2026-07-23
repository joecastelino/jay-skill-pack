---
name: bt-tony-menu-rebuild
description: >
  The Blackstone Toyota (BT, dealer 1249) service-menu rebuild project for Tony
  Garcia (Service Manager). Tony wants menus restructured into Factory Recs /
  Factory Recs Plus with 25 ordered add-on services. Contains the FULL locked
  spec, Joe's approved decisions, the opcode audit results, and the build plan.
  Load for ANY "BT menu", "Tony menu", "Factory Recs", or Blackstone Toyota
  service menu work. STATUS 2026-07-21: full 5K–200K range (5K-step) built,
  PUBLISHED, Tony-validated; Phase 7 generic Transmission Fluid placeholders
  DONE; Phase 8 Tony's BG MENU REVAMP 2026 part-match batch DONE + quote-verified
  (baseline tony-partmatch-baseline-20260721.json). Remaining: x2.5K half-step
  menus + EV rows only.
triggers:
  - blackstone toyota menu
  - tony menu
  - factory recs
  - BT menu rebuild
  - 160k menu
---

## POST-ROLLOUT STATE NOTE (2026-07-20): generic Transmission Fluid placeholder

The transmission service now bills a generic placeholder part **"Transmission Fluid"**
(created via the opcode Part Name dropdown's `Create "..."` option — opcode-local, NO
inventory record; Joe-sanctioned) instead of a specific fluid, so estimates never show
the wrong fluid (WS on a CVT). Two surfaces were swapped, prices mirrored exactly:
- **SMTRANSMISSION opcode** (`/ro/opcode/edit/SMTRANSMISSION`): removed BG3143 FULL SYN
  ATF → `Transmission Fluid` @ $136.24 (BG6600 $41.75 untouched).
- **Menu included-service** `Perform Automatic Transmission Fluid Exchange Service`
  (`/ro/service-menu-setups/included-service/edit-service/697ba2a4c4a9a7372669a4d1/default`
  — the record menus actually bill): removed BG3123 UNIVERSAL SYN ATF 3GAL →
  `Transmission Fluid` @ $185.31 (BG106 $47.85, BG310 $32.06 untouched).
Service total stays $499.95 exact ($234.73 labor + $265.22 parts); Preferred menu total
unchanged ($4,721.65). Baseline for rollback:
`/home/itadmin/bt-menu-build/smtransmission-opcode-before-20260720.json`.
Pitfall hit: typing in the parts area can focus the **Fees** select ("No Match Found",
no Create option) — the Create option only appears in the real Part Name select
(`partName_undefined`). Full recipe in `tekion-opcode-default-pricing`.
EXTENDED 2026-07-21 (Joe's yes) to ALL remaining trans-fluid paths — see Phase 7 COMPLETE below.

#

# BT Menu Rebuild — Tony Garcia's Factory Recs / Factory Recs Plus

Multi-session project (started 2026-07-02). Source docs + scripts in
`/home/itadmin/bt-menu-build/` (persistent): `tony-menu-request.pdf/.txt` (Tony's
email spec, 6/16/2026), `spiff-sheet.pdf/.txt` (BG product incentives context),
`audit_opcodes.js` (batch audit template).

Slack home = BT menu thread `slack:C0B8EPN76GJ:1783013683.414359`.
Tony Garcia = Service Manager BT, agarcia@blackstonetoyota.com, 559-709-2758.

## Tony's spec (from his email — the contract)
Two customer-facing options per interval menu:
1. **Factory Recs** — base package = current factory/system services UNCHANGED.
2. **Factory Recs Plus** — Factory Recs content **required & LOCKED** (cannot be
   unselected — Joe confirmed Tekion has a **checkbox** for this in the builder),
   plus 25 add-on services individually selectable, **in Tony's exact order**:

| # | Price | Service | Opcode |
|---|-------|---------|--------|
| 1 | $189.95 | EPR Service | OILEPRMOA |
| 2 | $20.00 | Add MOA Oil Additive | BGMOAG |
| 3 | $41.92 | Add Fuel Additive | 44K ❌missing |
| 4 | $10.00 | Washer Fluid Service | BGWASHER |
| 5 | $50.00 | Wiper Blade Service | WIPER |
| 6 | $14.95 | Key FOB Battery | FOBBATTERY ❌missing |
| 7 | $89.95 | Tire Balance (incl rotation) | ROTATEBAL ❌missing |
| 8 | $99.95 | Vehicle Alignment | 4ALIGN |
| 9 | $59.95 | Battery Service | BGBATT |
| 10 | $89.95 | Cabin Filter Service | CABIN |
| 11 | $219.95 | Brake Fluid Service | EXCHANGEB |
| 12 | $219.95 | Power Steering Service | EXCHANGEPS |
| 13 | $149.95 | Throttle Body Service | THROTTLE |
| 14 | $129.95 | MAF Sensor Service | MAF |
| 15 | $299.95 | Fuel Induction Cleaning Kit | FUELINJ |
| 16 | $299.95 | Engine Coolant Service | EXHANGEC (yes, that spelling) |
| 17 | $249.95 | Hybrid Coolant Service | COOLHV ⚠️ |
| 18 | $299.95 | Inverter Coolant Service | HVCOOLANT ❌missing ⚠️ |
| 19 | $499.95 | Automatic Transmission Service | ATF |
| 20 | $249.95 | Front Differential Service | FDIFF |
| 21 | $249.95 | Rear Differential Service | RDIFF |
| 22 | $249.95 | Transfer Case Service | TRANSFER |
| 23 | $89.95 | Hybrid Filter Svc Level 1 | HVFILTERLV1 |
| 24 | $600.00 | Hybrid Filter Svc Level 2 | HVFILTERLV2 |
| 25 | $89.95 | A/C Refresher Service | ACFRESH |

## Joe's locked decisions (2026-07-02, all confirmed in thread)
1. **Locked base** = YES there is a checkbox in Tekion for un-deselectable services — find it in the builder.
2. **Pricing = OPCODE level** (not menu-level). Audit existing prices, report deltas — don't silently change opcode prices.
3. ~~**3 tiers**: tier1=Factory Recs, tier2=Factory Recs Plus, tier3=KEEP but HIDDEN/unused.~~
   **SUPERSEDED 2026-07-09: TWO tiers — Basic + Premium, VALUE REMOVED** (Joe:
   "remove value. Just do basic and premium"). Done globally via Tiers & Details.
4. **Pilot on the 160K menu, EDIT IT DIRECTLY** ("it's dead" — near-zero traffic). Joe moved pilot from 10K→160K deliberately for zero blast radius.
5. **Factory Recs content** = current factory/system services unchanged; only restructuring tiers + adding the 25 add-ons.
6. **Hybrid items (COOLHV, HVCOOLANT, HVFILTERLV1/2) scoped to HYBRID vehicle rows only** — yes, do the extra row work.
7. Driving condition = Jay's call → both tiers apply to Normal + Severe.
8. **DRAFT only — Save, never Publish, until Joe reviews the 160K build.**

## Opcode audit results (BT dealer 1249, verified 2026-07-02)
- **21 of 25 exist**, all ACTIVE INDIVIDUAL_SERVICE, all FLAT customer-pay labor
  with parts attached. Full price table archived in session; spot-verified:
  4ALIGN flat $99.95/0 parts, HVFILTERLV2 flat $600.00, ATF $496.04 labor.
- **"4 MISSING" WAS WRONG — near-duplicate cousins exist (found 2026-07-02 PM).**
  The first audit exact-matched `h.opcode === "44K"` and missed case variants +
  cousins. Corrected picture:
  - `44k` (LOWERCASE) EXISTS — it IS BG 44K fuel cleaner, flat **$2.00** (parts-cost
    placeholder?) vs Tony's $41.92. Reuse+reprice, don't create "44K".
  - `FOBBATT` exists — "REPLACE KEY FOB BATTERY", $5.99/0.1hr vs Tony's FOBBATTERY
    $14.95. Reuse+reprice recommended (avoid "(2)"-style duplicate clutter).
  - `BALANCE` exists — "FOUR WHEEL BALANCE" $89.95/0.8hr = Tony's exact price but
    balance-ONLY; Tony's ROTATEBAL includes rotation. Genuinely create ROTATEBAL
    (or Tony okays BALANCE). Also `ROTATE` exists ($39.95/0.3).
  - `HVCOOLANT` was NEVER missing — `HVCOOLANTEXCH` carries **displayValue
    "HVCOOLANT"** (a create attempt for a new HVCOOLANT opcode FAILS with a
    silent Error toast: the pre-Create validation searches opcode OR
    displayValue and finds the dupe). It IS Tony's #18 inverter opcode.
  Jay proposed reuse+reprice 44k/FOBBATT + create only ROTATEBAL — awaiting Joe.
- **AUDIT RULE (burned once): never declare an opcode missing from exact-match
  alone.** Re-search case-insensitively AND by description keywords (e.g.
  "FOB", "BALANCE", "FUEL ADD") with searchFields OPCODE+DESCRIPTION before
  concluding missing. Tekion opcodes are case-sensitive strings.
- **MASS-REPRICE FLAG:** most of the 21 existing opcodes are priced BELOW Tony's
  sheet (OILEPRMOA $143.44→$189.95, CABIN $44.10→$89.95, EXCHANGEPS $153→$219.95,
  etc.). Opcode-level pricing per Joe means ~18 live à-la-carte reprices — needs
  Joe's explicit go with full old→new delta table first. ATF $496.04≈$499.95 and
  4ALIGN/HVFILTERLV2 already match.
- Note: internal /api/service-module priceDetails.flatPrice is in DOLLARS (labor
  only — parts extra), unlike public OpenAPI cents.
- **BT new-opcode conventions** (from siblings BGMOAG/WIPER/4ALIGN): Individual
  Service, category MAINTENANCE, serviceType "Maintenance Service", default pay
  CUSTOMER_PAY, FLAT CP price, autoDispatch on, consumer scheduling off.
  4ALIGN+CABIN share skillId 62e18f962ab79c00065f490a.
- **Create Opcode form** = `/ro/opcode` → "Create Opcode" btn → `/ro/opcode/add`.
  Key field ids: `opcode_undefined` (x255) / `opcodeDisplayValue_undefined` (x405) /
  `description_undefined` (x555) all y≈285; `CATEGORY_FIELD`, `SERVICE_TYPE_FIELD`,
  `SKILL_FIELD_ID` (required*), pay-type radios (value CUSTOMER_PAY/WARRANTY/INTERNAL),
  `LABOR_HOURS_FIELD`+`MANUFACTURER_HOURS_FIELD`, pricing rows w/ `labor-price`
  inputs, parts react-select `partName_undefined`. Save/mechanics per
  tekion-opcode-default-pricing (:9223 /mouse method).
- **⚠️ COOLHV crossed-wires flag (raised to Joe, unresolved):** Tony's #17 COOLHV
  = "Engine hybrid system coolant" but BT's COOLHV opcode description says
  "DRAIN & REFILL INVERTER COOLANT" — which is Tony's #18 (HVCOOLANT, missing).
  Confirm with Tony before creating HVCOOLANT / re-describing COOLHV.

## Build method (per tekion-service-menu-setups skill)
- :9223 session; switch dealer via pill → BT leaf (localStorage
  currentActiveDealerId must read **1249**). Dealer pill at x≈980,y≈0; BT row via
  `[class*=root_dealerInfoItem_container]` + innerText match.
- Menu list: `/ro/service-menu-setups` → 160,000 mi row → ⋮ (row.right−18px) →
  Edit → `/ro/service-menu-setups/edit/<menuId>`.
- **STEP ZERO: capture the full pre-change 160K state** (screenshots + the menu
  config JSON by menuId) for a clean revert path — Joe requires this.
- Tier names/tags on **Tiers & Details** tab (Menu Name + Tag free text).
- Add-on order matters (Tony's exact sequence) — verify service ordering control
  (drag handles) in Modify/Add Services.
- After build: pull a throwaway 160K quote on a BT VIN to verify rendering
  (incl. a hybrid VIN to check hybrid-row scoping), screenshot both tiers for Joe.

## 160K DRAFT BUILD — DONE 2026-07-03 (saved, NOT published)
**CRITICAL DISCOVERY: menus do NOT use raw à-la-carte opcodes.** The builder's
"Add Services" dropdown lists **Included Services** and searches by service NAME
(not opcode). BT has a pre-built **SM-prefix opcode family** specifically for
menus (store convention — use these, not 4ALIGN/CABIN/etc.):
- Map service→opcode via API: list custom included services (42 at BT), then pull
  each service's detail to read its opcode. E.g. "Perform 4 wheel Alignment" =
  SMALIGNMENT, not 4ALIGN.
- Tony# → SM service used: 1 SMMOAEPR, 2 SMBGMOAG, 3 SMFUELCLEANER, 4 SMWASHER,
  5 SMINSERT, 7 SMBALANCE, 8 SMALIGNMENT, 9 SMBATTERYKIT, 10 SMCABIN, 11 SMBFF,
  12 SMPOWERSTEERING, 13 SMTCLEANING, 14 SMMASS, 15 SMIND, 16 SMCOOLANTEXCHANGE,
  19 SMTRANSMISSION(WS), 20 SMFRONTDIFF, 21 SMREARDIFF, 22 SMTRANSFER,
  23 SMHVFILTER, 25 SMFRIG (Frigi-Fresh).
- Built state: 160K menu was completely EMPTY (pure SYSTEM menu — truly dead).
  Added vehicle row Toyota/All Models(88)/All Years/All Trims; Menu Config =
  System + Overrides (factory content untouched); 21 add-ons on **tier-2
  (Value/Normal) only**, Tony's order; menuStatus=DRAFT confirmed via API
  read-back. Screenshot: /home/itadmin/bt-menu-build/160k-draft-addservices.png
- SKIPPED (no included-service exists yet, add later): #6 FOBBATTERY, #7 ROTATEBAL
  (need new included services pointing at FOBBATT/ROTATEBAL opcodes),
  #17/#18 coolant pair (pending Tony), #24 HVFILTERLV2 (only one SMHVFILTER
  exists, used for Lv1 — Lv2 needs its own).
- **GOTCHA: tier names live in Tiers & Details which is GLOBAL across ALL
  interval menus** — renaming to "Factory Recs"/"Factory Recs Plus" for the 160K
  pilot renames every menu at the store. Hold rename until full rollout go.
- **NO per-service "required/locked" checkbox found** on the builder screen —
  may be tier behavior (Basic auto-included in Value) or in Settings. Open
  question to Joe (he said a checkbox exists — asked where he saw it).
- ROTATEBAL opcode CREATED at BT 2026-07-02 (Joe: "rotatebal, create"): ACTIVE,
  "BALANCES ALL TIRES AND INCLUDES TIRE ROTATION", CP $89.95 Fixed, 0.8hr flag,
  no parts, sibling convention (Individual/Maintenance/Maintenance Service).
  But it still needs an INCLUDED SERVICE created before it can go on the menu.
- Prices on the menu come from the SM opcodes → next audit target is the SM
  family vs Tony's sheet (separate delta table), not the à-la-carte codes.

## COOLANT PAIR RESOLVED & BUILT 2026-07-03 (Tony's 7/3 email, Joe's go in Slack)
Tony clarified: existing coolant opcodes "are gone, BG has one does all"; he wants
BOTH lines — #17 = ENGINE hybrid-system coolant $249.95, #18 = INVERTER coolant
$299.95. "One is engine the other is inverter."
- **COOLHV re-purposed** (was "DRAIN & REFILL INVERTER COOLANT" $188.81 labor):
  desc → "ENGINE HYBRID SYSTEM COOLANT SERVICE", CP FLAT labor → **$190.77** +
  parts 00272SLLC2 $34.95 + BG546 $24.23 = **$249.95 all-in**. Verified via API.
  Pre-change snapshot: `/home/itadmin/bt-menu-build/coolhv-before-20260703.json`.
- **HVCOOLANTEXCH re-purposed as Tony's #18** (creating a new HVCOOLANT opcode is
  IMPOSSIBLE — its displayValue is already "HVCOOLANT", Create errors on dupe):
  desc → "INVERTER COOLANT REPLACEMENT SERVICE", CP FLAT labor → **$185.35** +
  parts 00272SLLC2 x2 $69.90 + BG546 $24.23 + BG540 $20.47 = **$299.95 all-in**.
  Kept its original 3-part BG "one does all" part set. Verified via API.
  Pre-change snapshot: `/home/itadmin/bt-menu-build/hvcoolantexch-before-20260703.json`.
- Pricing model used: Tony's sheet prices = ALL-IN (labor+parts), matching how
  4ALIGN/HVFILTERLV2 matched his sheet. Parts kept at real unit prices; labor
  flat set to (target − parts).
- STILL NEEDED for the menu: SM included services for both (scoped to HYBRID
  rows) — neither has an included service yet.


- [x] Spec read, decisions locked, opcode audit done
- [x] Audit CORRECTED: only ROTATEBAL+HVCOOLANT truly new; 44k/FOBBATT/BALANCE cousins found
- [x] Stacey draft to Joe re: COOLHV/HVCOOLANT crossed wires (draft verified in Drafts, SENT=0)
- [x] Coolant pair RESOLVED (Tony 7/3 email) + BUILT: COOLHV=engine $249.95 all-in, HVCOOLANTEXCH=inverter $299.95 all-in (see section above)
- [ ] Joe: reuse+reprice 44k/FOBBATT + create ROTATEBAL only, or create all 3 verbatim?
- [ ] Joe: go/no-go on mass reprice of ~18 existing opcodes to Tony's sheet
- [ ] Tony (via Joe email): COOLHV vs HVCOOLANT description mapping
- [x] 160K baseline captured (was EMPTY — pure system menu, no custom rows)
- [x] 160K draft built & SAVED (21 SM add-ons tier-2 only, Tony's order); ROTATEBAL opcode created
- [ ] Find the "locked/required" checkbox (NOT on builder screen — asked Joe where he saw it)
- [ ] Tier rename decision (Tiers & Details is GLOBAL — hold until rollout go)
- [ ] Hybrid scoping (hybrid items currently on the all-Toyota row; needs hybrid-only rows)
- [x] Included services CREATED 2026-07-03 (Joe's go): "Key FOB Battery"/FOBBATT,
  "Tire Balance and Rotation"/ROTATEBAL, "Hybrid Filter Service Level 2"/HVFILTERLV2 —
  all Custom+Active, Pull From Opcode (labor/parts/pricing inherit). CREATE METHOD:
  /ro/service-menu-setups/included-service → Add Service btn → opcode react-select at
  x≈334,y≈239 (search by OPCODE; option list shows "CODE - DESC") → #name field →
  Save (bottom-right ~1211,687) → toast "Service created successfully". Opcode select
  displays the DISPLAY VALUE after pick (FOBBATT shows "FOBBATTERY"); flag hrs
  auto-pull confirms linkage. NOTE 44k needs NO reprice — $2 labor + BG208RSC $39.92
  part = $41.92 all-in = Tony's price already.
- [x] Coolant pair included services CREATED 2026-07-03: "Hybrid Coolant Service"/COOLHV,
  "Inverter Coolant Service"/HVCOOLANTEXCH — Pull From Opcode, Active. (Hybrid-row
  scoping still pending — currently on the all-Toyota row like everything else.)
- [x] Tony's 7/3 punch-list items 1-4 DONE 2026-07-03: all 5 missing services ADDED to
  the 160K draft (rows 21-25: Key FOB Battery, Tire Balance and Rotation, Hybrid
  Coolant Service, Inverter Coolant Service, Hybrid Filter Service Level 2), tier
  boxes normalized to Value-only (0010) matching the other 21 — NOTE new Add Services
  rows DEFAULT TO ALL 4 TIERS CHECKED (1111), must uncheck 3. Saved + verified by
  hard reload read-back (26 committed rows, all 0010). Also renamed included service
  "Perform WS Automatic Transmission Fluid Exchange Service" → dropped "WS" (Tony item
  4) via Edit Service #name field, saved.
- [ ] ORDER GAP: the 5 new services sit at rows 21-25 (appended), NOT in Tony's slot
  order (#6,#7,#17,#18,#24). Joe 7/3: "Bottom of list is fine until I publish all" —
  reorder to Tony's sequence as part of the PRE-PUBLISH pass, not before.
- [ ] Tony item 5 "need to be able to unselect all (can only unselect half)" — NOT
  addressed; ties to the locked/required-services design question. DO NOT GUESS — ask
  Joe/Tony what surface he means (quote screen tier behavior vs menu config).
- [ ] FOBBATT à-la-carte price still $5.99+part vs Tony's $14.95 — Joe hasn't ruled
- ADD-SERVICES ROW MECHANICS (menu builder): committed row containers have ids
  `ADDED_SERVICES_NAME_<n>`; the blank add-row is the one whose text = "Select".
  NEVER locate the select via generic placeholder scan — the FIRST placeholder hit
  is the vehicle-row Make select (`makeId_0`) and typing there wipes the Make cell
  (recover: native value-setter '' + input event + blur; committed value returns).
  Correct pattern: getElementById blank row → scrollIntoView → /mouse click center →
  tag its inner input `data-jay` → /type search text → click option by text match.
  Search is by SERVICE NAME (not opcode).
- [x] SM-opcode price audit DONE 2026-07-08 (Tony reported "pricing is off"; full delta
  at `/home/itadmin/bt-menu-build/price-audit-20260707.json`). Findings:
  - **À-la-carte codes: 24 of 25 ON target** (all-in labor+parts matches Tony's sheet).
    Codes ~$1.96 "short" (EXCHANGEB, EXHANGEC, FDIFF, RDIFF, TRANSFER, ATF) carry an
    HW/ATSDIS FEE code that fills the gap at RO time — by design, NOT drift. Only true
    outlier: WIPER = $19.99 labor + 2 unpriced blade parts vs Tony's $50 (blades price
    at RO by what's installed).
  - **160K menu: 15 of 26 lines price WRONG** because the SM opcode family was never
    repriced to Tony's sheet. Worst deltas: SMMOAEPR $46 (vs $189.95), SMALIGNMENT $50
    (vs $99.95), SMIND NO PRICE AT ALL (vs $299.95), SMHVFILTER $250 (vs Lv1 $89.95 —
    over Lv2 territory), SMFRIG CUSTOM $228/hr (vs $89.95), SMCOOLANTEXCHANGE ~$196 +
    DYNAMIC labor (vs $299.95), SMTRANSMISSION $389 (vs $499.95), SMBFF $134 (vs
    $219.95), SMTCLEANING $62.30 (vs $149.95), SMMASS $66 (vs $129.95), SMBATTERYKIT
    $25.47 (vs $59.95), SMCABIN $74 (vs $89.95), SMPOWERSTEERING $197.06 (vs $219.95),
    SMFRONTDIFF $160/SMREARDIFF $149/SMTRANSFER $129 (vs $249.95 each).
  - Correct on menu: the 5 services Jay built/repriced directly (Key FOB $14.95,
    Tire Bal+Rot $89.95, Hybrid Coolant $249.95, Inverter Coolant $299.95, HV Filter
    Lv2 $600) + MOA/Fuel Additive/Washer close.
- [x] **SMBALANCE DUPLICATE RESOLVED 2026-07-09: Joe said "Smbalance should come off" — deleted Balance All 4 Wheels row from 160K draft via row trash icon (icon-trash, must scrollIntoView inline:center — row actions live in a horizontally-scrollable root_fieldLayout_columnContainer, trash sits at x~1425 off a 1280 viewport until scrolled), Save at (133,689), verified gone after reload. ROTATEBAL stays. No confirm modal on row delete. SM REPRICE DONE 2026-07-08 (Joe picked OPTION 1** — reprice SM opcodes
  fleet-wide, accepting live 10K–150K menu impact). All 20 SM opcodes now price to
  Tony's all-in sheet (target = labor + existing parts), verified by API read-back:
  16 straight FLAT labor changes (SMALIGNMENT 99.95, SMMOAEPR 153.02, SMFUELCLEANER
  5.46, SMWASHER 1.71, SMINSERT 10.10, SMBATTERYKIT 39.48, SMCABIN 44.11, SMBFF
  185.23, SMPOWERSTEERING 125.83, SMTCLEANING 137.65, SMMASS 113.02, SMTRANSMISSION
  321.96, SMFRONTDIFF 175.09, SMREARDIFF 138.16, SMTRANSFER 219.10, SMHVFILTER 39.95)
  + 4 specials: SMBGMOAG restructured labor 3.18/part BG115 16.82 (=20.00 like
  à-la-carte BGMOAG); SMFRIG CUSTOM $228/hr→Fixed 64.82 (+BG7073 25.13 = 89.95);
  SMCOOLANTEXCHANGE DYNAMIC→Fixed 103.79 (+parts 196.16 = 299.95); SMIND (was
  unpriced) Fixed 186.76 + 1.0hr flags + part BG6591M added @113.19 (= 299.95).
  METHOD: :9223 batch script /tmp/sm_reprice.sh pattern — full-reload nav to
  /ro/opcode/edit/<OP>, poll for Update btn, tag the CP-row "Enter price" input
  (y-match to CP badge), /type + Tab, scrollIntoView Update → /mouse (1211,688).
  Rate-type change (DYNAMIC/CUSTOM/none→Fixed): click CP row .ant-select (x493) →
  option "Fixed Price" (.ant-select-dropdown-menu-item, legacy class) → new input
  appears same row. Part add: #partName_undefined react-select — bare number "6591"
  found only tarpaulins; FULL code "BG6591M" matched. Part price = the "0.00" input
  y-matched to the part row.
- [ ] SMBALANCE ($50, balance-only) intentionally NOT repriced — duplicate of the new
  Tire Balance+Rotation $89.95 row on the 160K; resolve which stays during the
  pre-publish reorder pass.
- [ ] WIPER blades still unpriced parts (à-la-carte $19.99 labor vs Tony's $50) —
  blades price at RO by what's installed; menu uses SMINSERT ($50 all-in, correct).
- [ ] Verification quote + Joe review → Publish decision → rollout plan for remaining intervals

## PHASE 2 — LIVE 10K SAMPLE BUILD (started 2026-07-09, IN FLIGHT)
Joe authorized: "build and publish the 10k only, let's sample that" — layered
add-on rows over the LIVE 10K, zero deletions, publish 10K only, then replicate
to 20K–150K after sign-off.

**10K menu id = `6570cab6eba6c973636a27f1`** (Active/Published). 160K draft id =
`653b4ccc6264f83465cf2826`. Baseline (Joe's revert rule):
`/home/itadmin/bt-menu-build/10k-baseline-20260709.json` (326KB).

### Critical recon findings (change the plan vs the 160K)
1. **The live 10K is NOT empty like the 160K was — it has 23 vehicle rows**
   (`data.menus` list). Bottom-most applicable row wins (standard Tekion
   precedence). The row driving most Toyota quotes = the bottom all-Toyota row.
2. **An EV row ALREADY EXISTS** (fuel-type filtered `['Hybrid (FHEV)','Battery
   EV (EV/BEV)']`, order 22) with EV-appropriate content — verified live via
   bZ4X viewer pull ($178.88/$218.88/$388.88, no oil/fuel services). DO NOT
   build a new EV row; leave untouched pending Tony's EV service list.
3. **PRICING-MODEL FORK — RESOLVED: Joe picked "sum of services"** on the new
   add-on rows (existing rows keep their fixed Total Menu Price config; the
   Preferred card total becomes computed for vehicles hitting the new rows).
4. Existing bottom row already carries 9 add-ons across tiers (fuel cleaner,
   ethanol, EPR, washer, battery kit, Frigi, alignment, MOA, wipers) — carry
   their tier flags over so today's package contents don't shift.
5. **Fuel Type filter CONFIRMED in the BT builder** (Trim Details modal →
   Filters): Gas / Hybrid (FHEV) / Hybrid (PHEV) / Diesel / Battery EV (EV/BEV).
   Hybrid-row scoping is buildable.

### Baseline JSON = fastest read of menu structure (no UI clicking needed)
`data.menus` sorted by `order`; each row's vehicle scoping nested in
`parameters` (list) — the `parameter=="TRIM"` entry carries
`value.standardTrimFilterDetails.FUEL_TYPE` (list incl. None). Read fuel-type
scoping of every row straight from the baseline file before touching the UI.

### API/browser mechanics learned this phase
- Bare in-page `fetch("/api/service-module/u/serviceMenu/<id>")` → **500**
  (missing axios interceptor headers). Capture config via XHR prototype hook
  (`XMLHttpRequest.prototype.open/send` override) while the APP loads the page.
- **Hook dies on `location.reload()`** — navigate via SPA only
  (`history.pushState` + `dispatchEvent(new PopStateEvent("popstate"))`).
- Metadata endpoint: `/api/service-module/u/opcode/service-menu/metadata`
  (milesUsed, durationsUsed, intervalMetadata).
- 10K row anchor in menu list: `.rt-tr` with `innerText.indexOf("10,000 mi")===0`
  — a substring match falsely hits "110,000 mi".
- **Shared-session drift is ACTIVE**: mid-modal the session got navigated to a
  Parts RO page at SCT by another user, killing the modal and 500ing /eval.
  Verify `currentActiveDealerId==="1249"` + path before EVERY batch; keep steps
  short.
- Do NOT pipe the :9223 screenshot endpoint through a shell one-liner (the
  terminal tool blocks that pattern) — fetch screenshots via execute_code
  with urllib and write the decoded PNG to /tmp.

### Remaining phase-2 steps
✅ ALL DONE 2026-07-09 — 10K BUILT + **PUBLISHED**, verified. See Phase-2 results below.

## PHASE 2 RESULTS — 10K PUBLISHED 2026-07-09 (verified by throwaway quotes)
**Joe's rulings that day:** (a) pricing = **"sum of services"** on the new rows
(rejected the hybrid fixed-Basic recommendation); (b) **remove VALUE tier, keep
Basic + Premium** — a GLOBAL Tiers & Details change hitting every BT interval menu.

**What was built (menu now 25 rows):**
- Row 24 (universal): Toyota / All models / All years / Trim-modal fuel filter =
  Gas + Hybrid FHEV + PHEV + Diesel (EV excluded). **21 add-ons**, Tony's order.
- Row 25 (hybrid): fuel = Hybrid (FHEV)+(PHEV) only. 4 HV services (#17,18,23,24).
- Add-on tier flag pattern on both rows: **PREMIUM/SEVERE enabled=true only**
  (PREMIUM/NORMAL false, BASIC all false) — renders on the Preferred card.
- Existing 23 rows + EV row (order 22) untouched. Baselines:
  `10k-baseline-20260709.json` (pre) + `10k-after-build-20260709.json` (post) in
  `/home/itadmin/bt-menu-build/`.

**Quote verification (all passed):** 2025 4Runner gas → Preferred $3,652.42,
23 svcs (2 factory + all 21 add-ons, no HV); 2025 Camry (hybrid-only lineup) →
Preferred $1,582.24, 7 svcs (3 factory + 4 HV, universal fuel-filter correctly
kept the 21 gas add-ons OFF... note: Camry got HV row only because its trims are
hybrid); bZ4X EV → $178.88/$388.88 unchanged. Basic card everywhere = factory
content only. Two cards per quote (Value gone).

### Phase-2 mechanics (hard-won, reuse for 20K–150K rollout)
1. **Tiers & Details removal can SILENTLY fail to persist** — first save showed
   "Basic, Premium" in the control but a reload showed 3 tiers again. ALWAYS
   verify by SPA re-nav + read-back of the tiers cell text after save.
2. **Add Services option picking must be EXACT text match** — prefix/substring
   matching picked a wrong near-name service once (deleted the row via its ⋮ and
   redid it). Match `innerText.trim() === name` on the dropdown options.
3. **Viewer (/ro/service-menu) selects are tekion-select, NOT ant-select** —
   dropdown container class `tekion-select-*-menu`; placeholder texts "Select
   Make/Year/Model". Pattern: click placeholder text center via /mouse → options
   are leaf `div`s inside `[class*="-menu"]` → click by exact text. Model list is
   long: type filter via native value-setter into the visible input first.
4. **To change vehicle in the viewer, hard-reload `/ro/service-menu`** (the
   collapse icon next to the vehicle name does NOT reopen the picker). Safe once
   everything is saved. Then interval rail: click element with exact text "10K".
5. **Publish = button bottom-right (~1211,689), NO confirm modal.** Verify via
   XHR hook: `PUT /api/service-module/u/opcode/service-menu/setup?publish=true`
   → 200, followed by menu GET refetch. Arm the hook BEFORE clicking.
6. **Persisted vehicle scoping lives ONLY in `parameters`** — top-level `make/
   models/years/trims/trimFilterDetails` stay null even on scoped rows. Read
   `parameters[]`: MAKE `{makes:["toyota"]}`, MODEL/YEAR `allValues:true`, TRIM
   entry carries the trimKey list from the fuel filter. Don't be alarmed by
   null top-level fields in read-backs.
7. Bare in-page `fetch()` of the menu GET still 500s post-publish — read-back
   requires the XHR-hook-during-app-load pattern, or parse the saved after-build
   JSON capture.
8. **$3,652 gas Preferred flagged to Joe** — honest sum of all 21 services; his
   call whether to trim per interval or custom-price. Not a bug.

## PHASE 2b — "ALL SERVICES FOR EVERY VEHICLE" MERGE (2026-07-09, published)
Tony changed the spec: ONE universal add-on row, ALL 25 services available to
EVERY vehicle (gas/hybrid/EV/diesel) — advisors deselect what doesn't apply.
Done: hybrid row's 4 services merged into the universal row (25 total,
Premium-only flags), fuel-type restriction REMOVED from the Trim modal (EVs now
included — verified via "bZ4X" search in trim modal, 13 results), hybrid-only
row DELETED (authorized by new spec), saved + **published**, verified on a bZ4X
quote (Preferred = 26 svcs $4,738.34; old fixed EV packages $178.88/$388.88 are
gone BY DESIGN). After-state: `10k-after-merge-20260709.json`.
- GOTCHA: "Filters (9)" label in the Trim modal counts filter GROUPS, not active
  filters — verify inclusion by trim search, not the count.
- 20K–150K rollout must now use THIS single-row structure, not the old two-row.

## PHASE 3 — FACTORY REPRICING (Tony: oil $109.95, rotation $39.95) 2026-07-10
Joe's fix (verbatim): "exclude the tek05052501, find an opcode smlof, add that
and use fixed pricing... force the parts in at a fixed price. Make the sum of
the fixed price 109.95, and use a fixed labor rate."

**Rotation ($39.95) — ❌ INCLUDED-SERVICES REPRICE DOES NOT WORK (proven by
quote explode 2026-07-10):** All THREE TEK07120301 included-service variants were
set to CP Fixed $39.95 (apostrophe `...2712`, no-apostrophe `...2726`, "Rotate
Wheels" `...2807` — the latter two needed the Labor group's **"Define Here"
radio** clicked first to enable the Labor Price Guide select). Saves succeeded,
BUT the exploded quote still bills TEK07120301 at **0.30 hr × $228/hr "Service
Menu Pricing" = $68.40** — the menu-level labor rate WINS over the
included-service Default pricing. Same disease as SCT's rotation; cure = opcode
SWAP (suppress system rotation line + add a fixed-price custom opcode), same
pattern as SMLOF. BT candidate: **SMROTATE** ("Perform Tire Rotation", custom,
CP Fixed — but currently **$19.00**, display "Perform Toyota Care Tire
Rotation", 0.30hr; may be deliberate Toyota Care pricing — get Joe's call before
bumping to $39.95 or creating a fresh opcode). Related: SMFMROTATE, ROTATEBAL.

**Oil ($109.95) — SMLOF swap:** TEK05052501 (factory line, Dynamic|BST GRID
$240 labor) can't be repriced; it gets EXCLUDED per-row and replaced by opcode
**SMLOF** (`Change oil, filter and drain plug gasket.`, id 65709d4a802074332d5cc92e,
INDIVIDUAL_SERVICE/ACTIVE, Service Menu category, EXPRESS skill). SMLOF set to:
CP **Fixed labor $59.95** + forced parts at fixed prices (OIL FILTER 1@$6.00 +
Oil 6@$7.00=$42.00 + Drain Plug Gasket 1@$2.00) = **$109.95 exact**. Fixed price
means qty doesn't move the total — flagged to Joe that 6qt is nominal.
**Menu-side swap — UNIVERSAL ROW ONLY (row-by-row abandoned):** per-row swap via
`oil_swap_rows.py` proved unreliable AND unnecessary:
- **Custom-configuration rows have NO Modify System Services section** → script
  returns `NO_MSS_SECTION`; suppression impossible there. Only "System +
  Overrides" rows have MSS.
- Bottom-most applicable row wins for every vehicle → applying the swap to the
  ONE universal bottom row (System + Overrides, the 25-service Phase-2b row) is
  sufficient. That's what's live/published.
- Procedure on the universal row: expand caret → MSS → add factory oil line,
  uncheck ALL tiers (suppress) → Add Services → SMLOF's service, all tiers →
  save row → Publish. **TWO oil variants needed suppression** (found via
  duplicate line on a Tundra quote): the factory TEK05052501 line AND the
  CAPITALIZED "Change Engine Oil, Filter and Drain Plug Gasket." — SMLOF's own
  line is the lowercase "Change engine oil, filter..." (capitalization is the
  only distinguisher; MSS "oil" search lists 15 variants).
- SMLOF is NOT findable in Add Services by opcode — search by service NAME text.

### VERIFIED STATE 2026-07-10 (10K published)
Quotes: Tundra 2WD Basic **$178.35** (QO#2234/2236), RAV4 Basic **$248.34**
(QO#2235, delta = $69.99 cabin filter + hybrid inspection). Pre-fix $413.09.
**Quote EXPLODE confirms oil line = exactly $109.95** (Op SMLOF: Fixed labor
$59.95 + parts $50.00) but **rotation = $68.40** (see rotation section — open).

### Line-level verification method (MANDATORY — package totals hide failures)
Package totals looked plausible while rotation was silently wrong. To verify
line pricing: `quote_check.py` builds the quote → click **"Add To Quote"** →
wait ~8s → click the RO line containing the package opcode (leaf with
/TEK10000BNM/) → the op detail panel lists Op1..N with per-op opcode, labor
rate type (Fixed vs "$ 228 / hr Service Menu Pricing"), and forced parts with
unit/total prices. Read `document.body.innerText` from 'Op1.' onward.
`quote_check.py` usage: `python3 quote_check.py 2024 "Tundra 2WD"` — model
select needs EXACT trim text ('Tundra 2WD', not 'Tundra').

### Phase-3 browser gotchas (hard-won)
1. **Opcode List search needs per-char keydown/keyup + native value-setter +
   Enter keydown/keypress/keyup** — a single set+input+Enter silently does
   nothing (0 XHR hits, list unchanged). Type char-by-char with key events.
2. **React-select options need `mousedown` dispatch** (react-select commits on
   mousedown, not click) — dispatch mousedown/mouseup/click sequence on the
   option element. A raw /mouse click at option coords can also miss.
3. **scrollIntoView BEFORE /mouse** — the Add Services blank 'Select' sits below
   the fold (y>1100); clicking off-screen coords focuses nothing (activeElement
   stays BODY). scrollIntoView({block:'center'}), re-read coords, then click.
4. Find a row's tier checkboxes by walking UP from the exact-text leaf node
   until a parent holds 2–8 `input[type=checkbox]` — row containers have no
   stable class.
5. Menu row carets need real MouseEvent dispatch (plain .click() no-ops).
6. ~~Rotation fix at Included Services level applies at EVERY interval~~ —
   DISPROVEN (see rotation section): menu "Service Menu Pricing" $/hr overrides
   included-service Default pricing. The SMLOF-style opcode swap is PER-MENU
   (repeat per interval during rollout) for BOTH oil and rotation.
7. **oil_swap_rows.py SPA-nav (pushState) leaves previously-expanded rows
   mounted → false "(already done)" reads.** Patched to hard `location.assign`
   + 16s wait + sanity-check exactly ONE row expanded. Trust nothing from the
   pre-patch background run; universal-row approach superseded it anyway.

## PHASE 3b — TONY'S PUNCH LIST v2 (2026-07-10, via Joe's iMessage screenshots)
Tony's items + verified diagnosis (exploded RAV4 Prime 10K quote QO#2241, 29 ops):
| Item | Opcode | Current (quote) | Target | Root cause |
|---|---|---|---|---|
| Factory rec rotation | TEK07120301 | $68.40 (0.30×$228/hr menu) | $39.95 | menu pricing wins — needs opcode swap |
| Factory cabin filter | TEK04020101 | Dynamic BST grid + $21.99 part | $89.95 | dynamic pricing — needs opcode swap |
| EPR service | SMMOAEPR | $180.87 | **$189.95** | fixed labor +$9.08 |
| Auto transmission | SMTRANSMISSION | $607.22 ($228/hr menu labor + $265.22 parts) | $499.95 | menu pricing overriding (see below) |
| HV Batt Pack Cooling Svc | SMHVFILTER | $50 part line | swap → "Hybrid Filter Service Level 1" | ~~HVFILTERLV1 missing~~ WRONG — see below |
Plus "apply to all VINs" (= keep universal-row design).

**Key findings this pass:**
- **SCREENSHOT AMBIGUITY RULE:** Joe's two screenshots of the same Tony text read
  139.95 vs 189.95 on first vision pass. Resolve by PIL-cropping the message band
  + 2x LANCZOS upscale + re-vision with a targeted digit question → both clearly
  $189.95. Never act on a single ambiguous vision read of a price.
- **Menu "Service Menu Pricing" ($228/hr) overrides even REPRICED custom SM
  opcodes**, not just factory TEK lines: quote shows SMTRANSMISSION, SMMASS,
  SMIND billing at $228/hr menu labor despite the 2026-07-08 Fixed-price reprice.
  Other SM ops on the same quote show "Fixed" and honor it. So the 07-08 SM
  reprice did NOT fully land on quotes for those three — check labor rate TYPE
  per-op in the explode, never trust the opcode edit page alone.
- **Included Services at BT ("hybrid" search):** COOLHV, HVFILTERLV2,
  SMHVFUELCLEANER, SMTRANSMISSIONHYBRID, TEK05070104 only. No Level 1 — must
  create opcode + included service (need Tony's Level-1 content/price first;
  DO NOT guess).
- SMROTATE opcode read: CP Fixed **$19.00** (input "19"), 0.30hr, display name
  "Perform Toyota Care Tire Rotation", labor rate field 100.00 = the base rate,
  discount 0.30. Likely deliberate Toyota Care pricing — don't bump; create a
  fresh fixed opcode for the $39.95 menu rotation instead. **STATUS as of
  2026-07-10 session end: Joe was asked TWICE (bump SMROTATE vs new clean
  opcode) and did NOT answer — question still OPEN. Do not touch SMROTATE
  without his explicit call; recommended path = new clean fixed opcode.**

### Phase-3b EXECUTED 2026-07-10 (EPR + HV→LV1 done, published, verified)
- **EPR ✅**: `/ro/opcode/edit/SMMOAEPR` fixed labor 153.02 → **162.10**
  (+ $27.85 fixed parts = $189.95 exact). Update btn (1211,688) → Success toast.
- **HVFILTERLV1 EXISTS — the "does not exist" finding was WRONG.** Joe: "Its
  item 23 on his list... and the opcode does exist." Direct URL
  `/ro/opcode/edit/HVFILTERLV1` loads it ("REMOVE AND REPLACE HYBRID BATTERY
  FILTER", CP Fixed $44 labor + $45.95 part = $89.95 all-in) even though BOTH
  the opcode-list search AND the Included Services opcode dropdown missed it.
  **RULE: an opcode absent from list/search/dropdown may still exist — always
  try the direct edit URL before declaring missing** (extends the earlier
  case-sensitivity audit rule; searches only see registered included services
  / preloaded subsets).
- Created included service "Hybrid Filter Service Level 1" (Pull From Opcode).
  **NEW GOTCHA on Add Service page:** if the page is scrolled, clicking the
  "Add an opcode" placeholder can focus the FEES react-select instead (you'll
  see ~32 preloaded fee options, typing filters fees) — scroll to top, click
  the opcode select by its own rect, confirm the option list shows
  "CODE - DESC" opcode format before typing.
- **HV→LV1 menu swap ✅** on universal row of 10K menu `6570cab6eba6c973636a27f1`:
  unchecked "Perform HV Battery Pack Cooling System Service" (was Premium-only),
  added "Hybrid Filter Service Level 1" Premium-only via the PROVEN
  `oil_swap_rows.py` helpers (`open_select_under('Add Services')` →
  `type_in_active` → `click_option_exact`) — ad-hoc typing into
  `ADDED_SERVICES_NAME_<n>` inputs failed again; always use the helpers.
- **UNIVERSAL ROW = SECOND-TO-LAST caret.** The LAST caret on the menu edit
  page is a blank template row (expands to "No rows found") — expanding it
  wastes a cycle and looks like a broken page.
- **"Apply to all Tiers" checkbox CASCADE:** unchecking the Apply-all box
  clears ALL tier checkboxes on that service row — re-check the intended tiers
  after. Row cb pattern here: [Apply-all, Basic, Premium].
- **Publish first-click silent no-op:** after Save the page re-renders and the
  first Publish click can do nothing (no toast). Re-locate the button, click
  again, require the Success toast.
- Verified on throwaway QO#2242 (2023 RAV4 Prime, odo 9500, Premium): HV line
  gone, LV1 present, LV2 untouched, total $4,918.28 → **$4,927.36** (+$9.08 =
  exact EPR labor bump, double-confirming EPR is live on quotes).
- **Menu $228/hr override scope confirmed wider:** it tramples opcode Fixed
  (SMTRANSMISSION Fixed $321.96 → quote bills $607.22) AND included-service
  Fixed (rotation $39.95 setting never took). MAF + fuel induction also bill
  at $228/hr but Tony did NOT list them — don't fix without Joe's word.

**Quote-build gotchas added:**
- Toyota model options at BT: "RAV4" and "RAV4 Prime" only — NO "RAV4 Hybrid"
  option (unlike trim names inside menu rows). Use RAV4 Prime for a hybrid VIN test.
- Odometer input can silently not take on first /type — click the input via its
  own rect, retype, then READ BACK `#vehicleOdometer.value` before Continue. If
  Continue fires with empty odo you stay stuck on Vehicle Information.
- `history.pushState` to `/ro/quotes` FAILS from a different SPA module (e.g.
  /parts/*) — the RO app isn't mounted. Hard `POST /navigate` when crossing modules.
- Reading Preferred card: click leaf with exact text 'Preferred', wait 5s, read
  body text from 'Preferred' — package total + full service list + Package OpCode.
- Explode read of ops >~Op14 needs a second innerText slice (start at 'Op15.') —
  single slice truncates.
- Opcode-list expandable search selector: input with attribute `searchfield="ALL"`
  (class root_expandableSearchField). The plain `.ant-input` "Search here..." is
  the global trap. XHR hook on `opcode/search` captures hits; but after /navigate
  the hook must be re-armed (nav wipes it).

### Rollout TODOs (next session)
- [x] 10K oil swap DONE via universal row, PUBLISHED, quote-explode verified
  ($109.95 exact).
- [x] **EPR** DONE 2026-07-10: SMMOAEPR fixed labor 162.10 (= $189.95 all-in),
  verified live on quote.
- [x] **HV FILTER Lv1** DONE 2026-07-10: HVFILTERLV1 opcode existed all along
  (direct URL); included service created; swapped onto universal row
  Premium-only; published + quote-verified.
- [x] **ROTATION ✅ 2026-07-12**: NO new opcode needed — existing à-la-carte
  `ROTATE` opcode was already CP Fixed **$39.95**/0.30hr (my 07-10 "SMROTATE or
  new opcode" question was moot). Created included service "Perform Tire
  Rotation Service" (Pull From Opcode → ROTATE), suppressed BOTH factory
  rotation variants on the universal row, added the new service all-tiers.
  Also set TEK07120301's opcode CP row LPG→Fixed $39.95 (belt & suspenders;
  the menu swap is what actually fixed the quote). Verified Op4 ROTATE Fixed.
- [x] **CABIN ✅ 2026-07-12**: NO new opcode — reused SMCABIN ($44.11 fixed
  labor + Cabin Filter $30.00 + BG7073 $15.84 = **$89.95 all-in**, was already
  right from the 07-08 SM reprice). Suppressed factory TEK04020101 variants
  ("Replace cabin air filter." + "Replace Cabin Air/Pollen Filter") on the
  universal row, added existing included service "Replace Cabin Filter"
  all-tiers. Verified Op2 SMCABIN Fixed, parts $45.84.
- [x] **TRANSMISSION ✅ 2026-07-12**: root cause was the INCLUDED SERVICE
  "Perform Automatic Transmission Fluid Exchange Service" (id
  697ba2a4c4a9a7372669a4d1) having its OWN Labor **Define Here** with CP =
  Labor Price Guide $228/hr — that's what overrode the opcode's Fixed price.
  Fix = on the Edit Service page, CP row select → Fixed Price → $234.73
  (+ $265.22 parts BG106/BG310/BG3123 = **$499.95 exact**). NO menu-row swap
  needed. Pre-change snapshot:
  `/home/itadmin/bt-menu-build/smtransmission-included-svc-before-20260712.json`.
  Verified quote explode Op18 SMTRANSMISSION Fixed 234.73 + $265.22 parts.

### 2026-07-12 session learnings (rotation/cabin/trans close-out)
- **THE $228/hr OVERRIDE MYSTERY SOLVED**: "menu Service Menu Pricing tramples
  opcode Fixed" is really *the included service's Labor group set to
  Define Here + Labor Price Guide*. Check the INCLUDED SERVICE's Default tab
  labor config FIRST before assuming an unfixable menu-level override —
  SMTRANSMISSION needed only that one select flipped; no suppress/swap.
- **Factory line suppression must cover the APOSTROPHE variant**: the live 10K
  quote's rotation line is "Rotate wheels following manufacturer's recommended
  sequence." (with '), while MSS also lists a no-apostrophe cousin. First pass
  suppressed only the no-apostrophe one → quote unchanged ($308.25, 4 svcs).
  Suppress BOTH (+ "Rotate Wheels"). Same lesson class as the two oil variants.
- **Pendo tour overlay strikes again**: dealer-pill clicks and quote Continue
  silently no-op'd; `document.elementFromPoint` showed pendo-backdrop. Remove
  `[id*=pendo],[class*=pendo]` after EVERY hard navigation at BT.
- Verified final 10K Basic (Tundra 2WD gas) = **$239.85** = SMLOF 109.95 +
  ROTATE 39.95 + SMCABIN 89.95. Explode: all ops Fixed, zero $228/hr lines in
  Basic. Preferred SEVERE = $4,721.65 (was 4,738.34; −16.69 = trans 607.22→
  499.95 partially offset by +89.95 cabin & +39.95 rotation now in package,
  minus suppressed factory lines).
- Swap script (suppress+add on universal row, reusable for 20K–150K rollout):
  `/home/itadmin/bt-menu-build/rotation_cabin_swap.py`.
- MAF ($66→$129.95 target) + fuel induction still bill $228/hr — Tony did NOT
  list them; their included services likely also Define-Here LPG. Ask Joe
  before touching (same one-select fix as transmission if he wants it).
## MENU CHANGE AUDIT VIA API — no UI needed (cracked 2026-07-12 PM, "what did my tweak do?")
When Joe (or anyone) manually edits a menu and asks for repercussions, diff it
entirely over HTTP — do NOT fight the shared :9223 session for a quote first
(session was mid-edit at another store; navigating away wipes their form).

1. **Fresh headers via PASSIVE capture** (old /tmp/tekion_rec_headers.json was
   401-stale): arm a hook on :9223 that records the app's OWN XHR request
   headers — override `XMLHttpRequest.prototype.open/setRequestHeader/send`,
   stash `{u,h}` into `window.__jayHdrs` for any /api/ request with >3 headers.
   The idle app fires XHRs on its own (a part-lookup fired within ~2 min);
   just poll `window.__jayHdrs`. Zero DOM/nav disturbance. Save to /tmp.
2. **Menu config GET works from plain urllib** with those headers + swapped
   `dealerId`/`tek-siteId: -1_<dealer>`:
   `GET /api/service-module/u/opcode/service-menu/<menuId>` → full config
   (menus rows, servicesMetaData, menuStatus). NOTE: `/u/serviceMenu/<id>` is
   404 — the working path has `opcode/service-menu`. This CORRECTS the earlier
   "read-back requires XHR-hook-during-app-load" note: only in-page bare
   fetch() fails; external urllib with captured headers is fine.
3. **Row services** live at `row.servicesMetaData.services[]` (a dict with key
   `services`, not a list): each `{referenceId, type: MODIFIED_SYSTEM|ADDED,
   included, tierMappings:[{packageType, drivingCondition, enabled}]}`.
   A "suppressed/unchecked" service = ALL tierMappings enabled:false (row stays
   in the list — diff enabled flags, not presence).
4. **Resolve referenceId → name/opcode**:
   `GET /api/service-module/u/opcode/included-service/<referenceId>` →
   `data.name` + `data.opcode`. Works for both factory (TEK*) included-service
   variants and custom services. (Endpoint intermittently 404s on a first probe
   — retry the same path before falling back.)
5. **Diff vs the archived snapshot** (`10k-live-*.json` etc. in
   /home/itadmin/bt-menu-build/) on (referenceId, included, type, tierMappings).
   Anything not explained by my own logged work = the user's manual tweak.
6. **modifiedTime on menu data is EPOCH SECONDS, not ms** (unlike most Tekion
   timestamps) — 1783905798 = 2026-07-12 18:23 PT. Dividing by 1000 gives 1970.
7. Check whether a re-enabled factory line got repriced: its included-service
   detail shows `laborRateType` (DYNAMIC = grid pricing back in play).

**2026-07-12 PM tweak recorded (Joe, live/published 6:23 PM):** universal row —
factory oil TEK05052501 + BOTH factory cabin TEK04020101 variants RE-ENABLED
Basic+Premium; SMLOF and SMCABIN UNCHECKED (fixed $109.95/$89.95 packages off);
ROTATE $39.95 untouched. Factory oil still DYNAMIC → Basic reverts toward ~$400;
both cabin variants enabled = possible duplicate cabin line on some VINs.
Awaiting Joe's intent before re-fixing. Snapshot:
`10k-current-20260712pm.json` + `row24-state-20260712pm.json`.

### 2026-07-12 PM — Joe's manual tweak + REVERT (Tony's call)
- Joe manually re-enabled factory oil (TEK05052501) + both factory cabin variants
  (TEK04020101) on the universal row and unchecked SMLOF/SMCABIN (published 6:23 PM).
  Diagnosed via API diff; factory oil confirmed still DYNAMIC (would revert Basic
  toward ~$400). Tony chose to keep the swap design → REVERTED + republished same
  night. Script: `/home/itadmin/bt-menu-build/revert_20260712.py` (reuses
  rotation_cabin_swap helpers; uncheck factory variants + re-check SMLOF/SMCABIN).
  Snapshots: `10k-current-20260712pm.json` (Joe's tweak) /
  `10k-after-revert-20260712.json` (verified post-publish).
- **API read-back method (no browser needed once headers captured):**
  GET `/api/service-module/u/opcode/service-menu/<menuId>` with captured axios
  headers (swap dealerId + tek-siteId=-1_<dealer>) = full menu config incl. per-row
  `servicesMetaData.services[]` with referenceId + tierMappings. NOTE the bare
  `/u/serviceMenu/<id>` path 404s — it's `/u/opcode/service-menu/<id>`.
  Resolve referenceId→name/opcode via `/u/opcode/included-service/<refId>`.
  Header capture: arm XHR open/setRequestHeader/send hook in :9223, wait for the
  app's next natural XHR (may take minutes if user idle), save headers to /tmp.
  data.modifiedTime is epoch SECONDS (not ms) on this endpoint.
- **Session-drift resilience:** the shared session can be yanked to another
  store/page mid-run by a human user. Saves that already PUT 200 persist; re-nav to
  the menu URL and Publish separately. Always confirm publish via the XHR hook
  seeing `publish=true` → 200 (toast text is unreliable).
- [ ] "Apply to all VINs" (Tony) = already satisfied by universal-row design.
- [x] Tony validated the 10K 2026-07-13 ("the 10 is perfect") → rollout began.

## ROLLOUT COMPLETE (2026-07-14 AM)
ALL 25 5K-step interval menus (5K–130K) carry the universal row, published:
10K/20K/30K hand-built + re-sequenced 7/13; 5K + the other 22 batch-built via
`batch_rollout.sh` → `rollout_one.py <menuId> <interval>` (one menu ≈6.5 min,
22 menus ≈2.5 hrs unattended, zero failures). Every menu verified in-log: base
interval stamped to menu's own interval, 27 added + 8 suppress entries,
save+publish PUT 200. Quote spot-checks (fresh quotes): 15K Corolla $239.85
TEK15000BNM; 60K Camry $707.83 TEK60000BNM; 120K Camry $621.28 TEK120000BNM;
130K verified separately at Joe's request (2018 Camry @129,500 → $239.85 Basic,
TEK130000BNM) — all correct swaps + Tony's order. x7.5K menus (22.5K…112.5K)
NOT built (excluded from Joe's "5k-130k"; confirm before touching). Menu IDs =
`menu-id-map.json`. Batch pattern: /usr/bin/bash + no declare -A + dealer
guard before each menu + hard-abort on missing MENU_DONE.
**Status:** Tony validated the 5K–130K set ("tony loves these", 2026-07-17).

## 135K–200K ROLLOUT COMPLETE (2026-07-17, Joe's go)
All 14 remaining 5K-step menus built + PUBLISHED via
`batch_rollout_135_200.sh` → rollout_one.py (zero failures, ~6.5 min/menu):
135K/140K/145K/150K/155K/165K/170K/175K/180K/185K/190K/195K/200K + **160K LAST**
(the old DRAFT pilot menu — rollout_one added the fresh universal row BELOW the
stale 26-row Value-tier pilot row; since Value tier is deleted those old rows
render nothing, and bottom-most row wins anyway. Publishing flipped 160K
DRAFT→PUBLISHED — the "160K re-tier" TODO is OBE/dead).
All base intervals read back correct on FIRST read (these old 653b* menus have
menu-level base = their own interval, unlike the 65a* menus that default 5000/10000).
Quote-verified on QO#2290 (2018 Camry @148,500): 150K/160K/200K all
Basic $239.85 (3 svcs: SMLOF oil + ROTATE + SMCABIN), Preferred SEVERE
$4,721.65 (27 svcs, Tony's order), correct TEK<interval>BNM/PSM opcodes.
**Every BT interval menu 5K–200K (5K-step) now carries the universal row.**
Remaining exclusions: x2.5K menus (7.5/22.5/37.5/52.5/…/187.5, incl 142.5/157.5/172.5)
untouched per Joe's scope.

### Quote-rail verification gotchas (2026-07-17)
- The Service Menu interval rail on the quote page renders ALL 40 intervals as
  plain leaf texts '5K'…'200K' (no ' mi' suffix) at y≈235 — filter candidates by
  BOTH exact text AND 200<y<280, else you match unrelated page text.
- A '150K mi' match at y≈785 = the SECTION list (below the fold), clicking it can
  bounce you to /ro/quotes list. Re-open the quote via its direct URL
  /ro/quotes/<id>/service/new if that happens.
- First interval click often no-ops (opcode stays null) — retry loop keyed on
  `Package OpCode : TEK<interval>` regex, same stuck-panel disease as before.

## PHASE 6 — 135K–200K ROLLOUT (launched 2026-07-17, Joe's ask)
Batch script: `/home/itadmin/bt-menu-build/batch_rollout_135_200.sh` (14 menus:
135/140/145/150/155/165/170/175/180/185/190/195/200K + **160K LAST**). Same
rollout_one.py pipeline. Key facts:
- **160K special case**: it was still DRAFT from the old pilot with the 26
  Value-tier add-on rows. Running rollout_one on it adds a FRESH universal row
  BELOW the stale pilot row (bottom-most wins) and PUBLISHES — this supersedes
  the old "re-tier the 160K draft" TODO. Verify post-run that the stale pilot
  row isn't causing surprises; consider deleting it in a cleanup pass.
- **135K+ menus already have menu-level base = their own interval** (per
  menu-id-map: 135000→base 135000, 200000→base 200000, etc.) — unlike the
  5K–130K range where base often defaulted to 5000/10000. rollout_one's
  set_base_interval is a no-op there ("base interval currently: 135000 mi"),
  but keep the verify step — never skip it.
- **x2.5K menus in this range (142.5/157.5/172.5/187.5K) SKIPPED** — same rule
  as the x7.5K skips; Joe hasn't asked for any half-step menus.
- Re-auth path when :9223 sits at /login: `login.py` (fresh OTP) → cookie +
  22-key localStorage injection (chunk >30KB keys) → land BC 1251 → UI dealer
  pill switch to BT. Worked first try per persistent-browser-server skill.
- REMINDER (Joe corrected me 2026-07-17): 5K–130K was ALREADY COMPLETE +
  Tony-validated ("tony loves these") — check the menu-id-map statuses before
  proposing rollout work; don't re-offer finished ranges.

**MULTI-SESSION COLLISION root cause (solved 2026-07-14/15):** the phase-5
"human at BC keeps yanking the session" was actually a SECOND Jay Hermes
session (different Slack thread) driving the same :9223 tab — Joe: "You have
2 sessions going." Symptoms identical to human contention: dealer flips
1249→1251 mid-script, MAKE_FAIL/"no make", half-filled forms appearing.
Before blaming a human or debugging the script, check for another active Jay
thread and ask Joe which has priority. Restarting the browser server clears
duplicate tabs (browser-data/ profile keeps auth). Keep the dealer+URL guard
before every mutating step and hard-abort on drift regardless.

## SERVICE ORDER (locked 2026-07-13 — Tony's requirement)
Add-on render order on the quote = the order services were ADDED to the row. Tony wants: factory natives (Tekion auto-renders these first) → oil change + tire rotation swaps → his #1–25 exact order. The canonical add sequence lives in `/home/itadmin/bt-menu-build/resequence_row.py` TARGET list — **use TARGET (not build_row.py's old ADD list) for all future menu builds (40K–150K)**. resequence_row.py also FIXES an existing menu: deletes all added rows (per-row `icon-trash` inside `.rt-tr`, no confirm modal) and re-adds in order. Run with `--no-expand` if row already expanded. GOTCHA: the last-added row's innerText carries a screen-reader artifact ("option <name>, selected.") — blur activeElement + normalize before comparing order; script's order_ok check fails on it (save manually after verifying normalized order). Verify persistence via full location.reload() (React Query caches; pushState jiggle does NOT refetch, in-page fetch w/ captured headers = 401). Verified on QO#2265 (VIN JTNC4MBE0S3251213): 10K/20K Preferred $4,721.65 (27 svcs), 30K $4,800.64 (28, air filter first), all in Tony's order; Basic $239.85 (10K/20K) / $318.84 (30K).

## CRITICAL PITFALL — Base Services interval (burned 2026-07-13)
When building the universal row on a NON-10K menu, the row's "Base Services" interval (`baseSystemInterval`) defaults to **10000** (menu-level default / inherited from replicating the 10K template) — NOT the menu's own interval. Result: the row pulls the **10K factory package** onto the 20K/30K menu (Tony's 30K Corolla quote showed the 10K $239.85 Basic + short inspection list; missing engine air filter, ATF/ball-joint/brake-line inspections etc.). Joe fixed both manually in the UI (20K row → 20000, 30K row → 30000) on 2026-07-13. Native rows are stamped with their menu's interval (30K natives = 30000) — the universal row must match. **For every 40K–150K rollout menu: set the row's Base Services to that menu's interval as part of the build, and verify via API diff (`baseSystemInterval` on the new row == menu interval) before publish.** Diagnostic tell: quote price exactly equals the 10K package ($239.85) = wrong base interval.

Also: the "Add Menu Services as separate operations" settings toggle (/ro/service-menu-setups/settings) was flipped OFF + saved 2026-07-13 after diagnostics (per standing rule: flip OFF immediately once opcodes identified). Settings toggles need real MouseEvent dispatch on the switch element — /mouse coord clicks silently no-op; verify "Settings saved successfully" toast.

## PHASE 4 — 20K/30K ROLLOUT (2026-07-13, PUBLISHED — awaiting Tony validation)
Joe's instruction: build 20K + 30K next, Tony validates before the rest.
- **20K menu id = `659c5c8aa5a90d178d29a983`** (was 20 rows) → universal row
  added as row 21. Built + PUBLISHED, API-verified: 8 factory variants
  suppressed (all tierMappings disabled), 27 add-ons (24 Premium/Severe-only +
  3 all-tiers: Replace Cabin Filter, Change engine oil…gasket. [SMLOF], Perform
  Tire Rotation Service [ROTATE]).
- **30K menu id = `659ebdce171a420e5fb2e9fa`** (was 33 rows) → universal row
  added as row 34. Same content, built + PUBLISHED, API-verified.
- Baselines + after-states: `{20k,30k}-baseline-20260713.json`,
  `{20k,30k}-after-build-20260713.json` in /home/itadmin/bt-menu-build/.
- **REUSABLE TOOLING built this phase:**
  - `rollout_lib.py` — all proven helpers (nav_menu, open_select_under w/
    focus-polling retry, type_in_active, click_option_exact, row_checkboxes,
    uncheck_all/check_all/set_premium_only, save_menu, publish_menu w/
    XHR-hook verification).
  - `build_row.py <menu_id> [--publish]` — full universal-row content build
    (suppress 8 factory oil/rotation/cabin variants + add 27 services in 10K
    order with correct tier flags). Runs ~6 min. Requires the universal row to
    already exist as the BOTTOM row (create via UI first) and session at BT.
  - `quote_check2.py <year> <model> <odo> <interval>` — parameterized quote
    verifier (interval rail may need icon-left-arrow clicks; rail can open
    showing 120K+).
- **ROW-CREATE RECIPE (UI, per menu):** blank row = `input#makeId_<N>` (N=count
  of committed rows). Click make input → option "Toyota" → model cell (x≈385,
  same row y) → option "All" → year cell (x≈635) → option "All" (multi-select;
  "All" cascades to every year; dismiss by toggling the select's own trigger
  at its container x≈635→center ≈723) → trim input `#trim_<N>` → Trim Details
  modal → radio ALL already default, 0 filters → modal Save (the LOWEST Save
  button, not the page save at 133,689) → trim shows "All trims selected" →
  page Save. Verify via API: MODEL=[ALL_MODELS], YEAR=[ALL_YEARS],
  cfgType=SYSTEM_WITH_OVERRIDE, priceConfig=SUM_OF_SERVICES (default).
- **NEW SUPPRESS VARIANTS at 20K/30K** (not on the 10K list): "Includes:-
  Replace engine oil and oil filter." and "Includes:- Replace engine oil & oil
  filters." — the SUPPRESS list in build_row.py covers all 8 known oil/rotation/
  cabin variants; NOT_IN_SYSTEM is a safe skip for intervals lacking a variant.
- **PITFALLS this phase:** (1) open_select_under original single-shot click
  failed under script pacing — focus arrives async; fixed with retry+poll (the
  reason the first two build runs no-op'd; Save 200 on a no-op build is
  harmless). (2) A "RO P&A request" toast hijacked a trim-modal click midway —
  modal survived, but always re-verify state after any click near bottom-right.
  (3) Shared session got yanked to BC mid-verification (human working at BC on
  an included-service EDIT page) — do NOT navigate away; builds were already
  published, quotes deferred.
### 🔴 CRITICAL BUG FOUND BY TONY (2026-07-13): baseSystemInterval mismatch
Tony's 30K quote screenshot (2025 Corolla Hatchback) showed Basic = **$239.85
with the 10K factory package** — short inspection list, NO 30K-specific factory
content (engine air filter, ATF inspection, ball joints, brake lines, drive
shaft boots, steering linkage, exhaust, fuel lines, etc.).

**Root cause:** each menu ROW carries `baseSystemInterval` — this stamp tells
Tekion WHICH factory maintenance package to render at quote time, independent
of which interval menu the row lives in. The UI row-create recipe inherits the
menu-level default (10000 at BT for ALL interval menus, even the 30K menu whose
`intervals=['30000']`). Native 30K rows are stamped 30000; my new universal row
got 10000 → bottom-most row wins → vehicles got 10K factory content on the 30K
menu. **Row structure/pricing was right; only the interval stamp was wrong.**

**Rules for the 40K–150K rollout:**
1. After creating the universal row, ALWAYS diff the new row's
   `baseSystemInterval` against the native rows in the after-build JSON
   (`sorted(cfg['menus'], key=order)`; Counter the existing rows' stamps).
   The new row MUST match the interval-appropriate native stamp before publish.
2. 20K was coincidentally OK-ish: native 20K rows use 5000/10000 (Toyota's 20K
   IS a 10K-type service), so a 10000 stamp matches neighbors there. 30K/60K/
   90K/120K etc. have their own richer factory packages — mismatch is guaranteed
   if the stamp isn't corrected.
3. Where to fix: the row editor's interval field if exposed; otherwise the row
   must be rebuilt/API-corrected with the right stamp. (Verify surface in UI —
   don't guess.)
4. **Price tell:** if a higher interval's Basic quote equals the 10K's $239.85
   exactly AND shows the short 10K inspection list, suspect this bug first.
5. When the real 30K+ factory package loads, watch new factory REPLACEMENT
   items (e.g. Replace Engine Air Filter at 30K) for dynamic/SCP pricing
   inflation — same disease as the $449 rotation. Flag price to Joe before
   touching.

Diagnosis artifacts: compare `30k-after-build-20260713.json` row 34
(`baseSystemInterval: 10000`) vs native rows (30000). Tony's evidence
screenshots: factory chart = ADAS Portal "30,000 Miles or 36 Months
Recommended Service" list.

- [ ] **FIX 30K row 34 baseSystemInterval 10000→30000**, re-publish, verify
  quote shows full 30K factory package + check new factory line pricing.
- [ ] Re-check 20K the same way against the factory 20K chart (likely fine —
  native rows are 5000/10000 — but verify).
- [ ] Verification quotes on 20K + 30K (Corolla Hatchback @29,500 + Tundra gas)
  — pending session free.
- [ ] Tony validates 20K + 30K → then replicate to 40K–150K (same recipe:
  create row via UI, **verify baseSystemInterval**, run build_row.py, publish).
### 🔴 SERVICE ORDER BUG (found by Tony 2026-07-13, VIN JTNC4MBE0S3251213) — FIX IN FLIGHT
Add-on services render on the quote card **in the order they were ADDED to the
row** (array position in `servicesMetaData.services`; the `order` field is None
— array order IS the render order). build_row.py's ADD list was NOT Tony's
sequence → fuel additive (#3) at slot ~11, hybrid coolant/inverter (#17/18)
after Frigi, HV Lv1/Lv2 at the end, oil+rotation swaps rendering LAST. Same
wrong order stored on 10K/20K/30K.

**Joe-approved target order** (stated as default, he confirmed by "fix it"):
native factory lines render first automatically → then the factory swaps
**oil (SMLOF), rotation (ROTATE)** → then **Tony #1–25 in his exact order**
with cabin at #10. This also makes Basic render air filter → oil → rotation →
cabin. Fix = re-sequence the universal row's added services on each menu
(delete+re-add in correct order via build_row.py with reordered ADD list, or
drag handles if they exist — VERIFY, never assumed). Re-verify with the same
VIN at each interval, republish. **40K–150K rollout must use the corrected ADD
order from the start.**

### VIN-based throwaway quote (faster + exact-vehicle, verified 2026-07-13)
Create Quote form has `input#vin` (placeholder "Search VIN #"): tag data-jay →
/type VIN → dispatch Enter keydown/keypress/keyup on the input → ~4s → form
auto-decodes Make/Year/Model/Trim (read body text for the decoded model). Then
odometer + Continue as usual. Beats Make/Year/Model picking when Tony reports a
specific VIN. Interval rail leaf: exact text '30K' (children<=2) or '30K mi';
verify via `Package OpCode : TEK30000BNM` before reading the card. Read Basic
card from body text at 'Basic'; click leaf 'Preferred' (children===0) for the
Preferred card.

### Refetch a menu config after someone else's UI edit (no stale headers needed)
Arm XHR hook in :9223, then pushState to `/ro/service-menu-setups` → popstate →
pushState to `/edit/<menuId>` → popstate (pushState direct to the edit URL when
already there does NOT refetch — must bounce via the list). Body arrives in
`window.__xh` (~600KB); pull in 15000-char `.substr()` slices and reassemble.
NOTE: rollout_lib's `ev()` returns `{'result': ...}` — its `jres()` returns None
on non-JSON results; use a plain `(r or {}).get('result')` helper for strings.
Dealer switch when pill /mouse click no-ops: remove pendo overlays, then
dispatch mousedown/mouseup/click MouseEvents directly on
`.root_selectedDealer_dealer*` and on the `root_dealerInfoItem_container` leaf.

- [x] **RE-SEQUENCE 10K/20K/30K DONE 2026-07-13** — resequence_row.py ran on all
  three, republished, verified on fresh QO#2265 (VIN JTNC4MBE0S3251213): Basic
  $239.85 (10K/20K) / $318.84 (30K, air filter first), Preferred $4,721.65 /
  $4,800.64 all in Tony's order. Joe: "Looks perfect" → gave GO for **5K–130K**.

## PHASE 5 — 5K–130K FULL ROLLOUT (started 2026-07-13, IN FLIGHT)
Joe's go: build 5K, 15K, 25K, 35K–130K (23 menus, 5K-step). **OPEN QUESTION:
x7.5K menus (22.5K/37.5K/52.5K/67.5K/82.5K/97.5K/112.5K) exist too — asked Joe,
skipping unless he says include.** 5K build got interrupted by session
contention (see below) — 5K menu has row-create PARTIALLY done (check makeId_15
row state: Make=Toyota was set, model/year/trim NOT; row was never saved so a
reload discards it).

### Menu ID map (ALL intervals, saved `/home/itadmin/bt-menu-build/menu-id-map.json`)
Fetched via `GET /api/service-module/u/opcode/service-menu` (bare path — the
`/setup?pageNumber=` list variant 500s) with captured headers. Returns intervals,
menuStatus, and menu-level baseSystemInterval per menu. Key targets:
5K=69c6e9ed7fb9de2c3f3e0996, 15K=659866ddbee97f18d19db9bf,
25K=659eafdca5a90d178d2c1765, 35K=65a00ee39546860202233336,
40K=65a029fb65a9d765dfb6cd86, 45K=65a155d465a9d765dfb80604,
50K=65a19f51c7ebdd6b7c5d1440, 55K=65a56294c7ebdd6b7c5f0043,
60K=65a565a8c7ebdd6b7c5f0947, 65K=65a573b3c7ebdd6b7c5f3430,
70K=65a577eff4a9a4675af516bd, 75K=65a57b1b65a9d765dfbafc2e,
80K=65a57daef4a9a4675af527c1, 85K=65a5804465a9d765dfbb0be1,
90K=65a58319954686020227c9a4, 95K=65a58816c7ebdd6b7c5f6f0b,
100K=65a5897a65a9d765dfbb26c0, 105K=65a58f20954686020227ec8b,
110K=65a5912b65a9d765dfbb3def, 115K=65a592a1c7ebdd6b7c5f8c91,
120K=65a59342f4a9a4675af56491, 125K=65a598fb65a9d765dfbb553b,
130K=65a599ed9546860202280ade.

### Base System Interval control — FOUND (answers the phase-4 open question)
Inside the EXPANDED universal row there is a labeled ant-select
**`div#BASE_SYSTEM_INTERVAL_SELECT`** ("Base System Interval *", renders e.g.
"20000 mi"). Fix = click the select (scrollIntoView + /mouse center) → pick
option text `"<interval> mi"` from `.ant-select-dropdown-menu-item` (real
MouseEvent dispatch) → read back the select's innerText. NO API write needed —
set it in the UI as part of every build, verify after reload.

### One-shot per-menu builder: `rollout_one.py <menu_id> <interval>`
Full pipeline: nav → create vehicle row (Toyota/All/All/All-trims) → save →
reload → expand universal row (second-to-last caret) → set Base System Interval
→ suppress 8 factory variants → add 27 services in Tony's TARGET order → save →
**reload + re-verify (order, interval, tier flags) → publish**. Dies loudly on
any mismatch (never publishes bad state). Run in background with tee log,
ONE menu at a time.

### Phase-5 pitfalls (hit 2026-07-13)
1. **Row-cell markup differs on older menus**: on the 5K menu the Model/Year
   cells are `.ant-dropdown-trigger` elements showing **"Select..."** (with
   ellipsis, x≈372/622), NOT the 'Select' leaf text used on 20K/30K. cell_click
   must match 'Select', 'Select...', AND 'All'. Make/trim are still
   `input#makeId_<n>` / `input#trim_<n>`.\n2. **`/ro/quotes/new` direct-nav 500s** ("Something went wrong") — create
   quotes via `/ro/quotes` → "Create Quote" button. On the QUOTE page the
   interval rail is the FULL horizontal list (leafs '5K'…'200K' at y≈239,
   scrollIntoView inline:'center'); inside the Add-Service Service-Menu PANEL
   it's the 4-visible carousel (icon-right-arrow to advance). Verify
   `Package OpCode : TEK<interval>...` after every rail click — clicks can
   no-op (retry loop).
3. **SESSION CONTENTION IS THE #1 ROLLOUT RISK**: a human at BC kept yanking
   the session mid-build (dealer flips 1249→1251 between script steps; builds
   die on guard). Found a HALF-FILLED Add-Included-Service form at BC
   (TEK05052501, $70.88) — taking the session wipes it. Protocol: run
   `session_watch.py` (background; exits when back-at-BT or idle ≥6 min),
   ASK Joe before wiping visible unsaved human work, guard dealer+URL before
   EVERY mutating step (rollout_one.py does).
4. Background runners: launch via `terminal(background=true)` with
   `/usr/bin/bash -c 'python3 -u … | tee log'` — bare `nohup` is rejected.

- [ ] Resume 5K–130K: for each menu run rollout_one.py, then batch-verify
  with throwaway quotes (spot-check a few intervals incl. Basic totals for
  factory-item dynamic-pricing surprises; 30K-style richer packages at
  60K/90K/120K deserve a look).
- [ ] Joe's answer on x7.5K menus (22.5K–112.5K) — include or skip?
- [ ] 15K/25K/45K/60K/90K/100K/110K/130K menu-level default base = 5000 (per
  menu-id-map) — the interval-set step is MANDATORY on every single build.

## PHASE 5 — 5K–130K ROLLOUT PREP (2026-07-13, in flight)
Joe's go: build 5K, 15K, 25K, 35K–130K (5K-step only; x7.5K menus SKIPPED per
Joe's "5k-130k" — 22.5K/37.5K/etc. untouched unless he says otherwise).
- **MENU ID MAP (all BT intervals) = `/home/itadmin/bt-menu-build/menu-id-map.json`**,
  fetched via `GET /api/service-module/u/opcode/service-menu` with captured
  headers (plain urllib works; the `/setup?pageNumber=...` list path 500s).
  Returns id, intervals[], menuStatus, and MENU-LEVEL baseSystemInterval.
- **⚠️ MENU-LEVEL baseSystemInterval ≠ menu's own interval on most menus**
  (40K menu base=10000, 15K base=5000, 130K base=5000...). This menu-level
  default is what a NEW row inherits — so on nearly every rollout menu the new
  universal row WILL be born with the wrong stamp. Always fix the ROW's Base
  Services to match native rows before publish (the 10K/20K/30K lesson,
  systematized).
- **Scripts:** `create_row.py <menu_id>` (UI row creation: make/model/year/trim
  modal — element-dispatch clicks; untested as of 07-13 due to session yank),
  then `resequence_row.py`-style content build with TARGET order, then
  interval fix, save, API-verify, publish.
- **Quote verification corrections:** direct `/ro/quotes/new` URL = "Something
  went wrong" error page — go `/ro/quotes` (full reload if error state) → click
  "Create Quote" button → `/ro/quotes/create`. VIN decode: tag `#vin` data-jay,
  /type VIN, dispatch Enter keydown/keypress/keyup, ~5s, decoded model appears
  in body text (input .value stays as typed, make/year/model inputs stay
  empty-valued — read body text not field values). Interval rail on the quote's
  Service Menu panel renders TWO ways: '5K mi' pill carousel (use
  icon-right-arrow to page) OR plain '5K'/'30K' tab row — match either text;
  ALWAYS verify `Package OpCode : TEK<interval>...` flipped before reading the
  card (stuck-panel disease).
- **Session contention is real even after Joe says "session is all you"** —
  another human flipped the session BT→BC mid-build (aborted create_row safely
  at the MAKE step; nothing saved). Watcher: `session_watch.py` via
  terminal(background=true) — polls dealer+path every 30s, exits when back at
  1249 or idle ≥6 min. Guard dealer/URL before EVERY mutating step; a build
  script must die loudly on drift (guard_or_die), never continue.
- [x] **160K draft re-tier — OBE 2026-07-17**: rollout_one added a fresh
  universal row below the stale Value-tier pilot rows and published (deleted
  Value tier renders nothing; bottom-most row wins). Optional cleanup: delete
  the stale 26-row pilot row someday.
- [ ] Tony's EV service list → then touch EV rows.

## PHASE 7 — GENERIC "TRANSMISSION FLUID" PLACEHOLDER (✅ COMPLETE 2026-07-21)
Weekend incident: menu auto-populated BG Transmission Service with **WS fluid on a
CVT vehicle**; customer questioned the estimate. Joe wants transmission opcodes to
bill a **generic part called "Transmission Fluid"** (same fixed price) instead of a
specific fluid; Parts substitutes the real fluid (WS/CVT/etc.) on the RO, giving
the tech a verification step.

**KEY MECHANIC (Joe confirmed):** the opcode parts dropdown's `Create "..."` option
creates a generic placeholder part with a settable price **without adding anything
to parts inventory/master**. No new inventory part needed. (This corrects the
long-standing "always ignore the Create option" habit — Create IS the tool here.)

**ALL 5 FLUID LINES GENERICIZED (2026-07-20 + 07-21, prices mirrored exactly):**
| Surface | Was | Now |
|---|---|---|
| SMTRANSMISSION opcode | BG3143 FULL SYN ATF $136.24 | Transmission Fluid $136.24 |
| Included svc 697ba2a4c4a9a7372669a4d1 (what menus bill) | BG3123 UNIV SYN ATF 3GAL $185.31 | Transmission Fluid $185.31 |
| SMTRANSMISSIONHYBRID | **00289-ATFWS WORLD STANDARD ATF qty7@$15.66** ← the literal WS source from the weekend estimate | Transmission Fluid qty7@$15.66 ($109.62; labor $211.01/1.8hr untouched) |
| ATFXWS (Transmission Fluid Exchange) | BG3123 UNPRICED → billed dynamically at parts-master LIST $134.57 | Transmission Fluid **FIXED $134.57** |
| HVTRANS (Hybrid Trans Fluid Svc) | BG3123 $136.24 | Transmission Fluid $136.24 |

**ATF opcode** ($496.04 flat) = LABOR-ONLY, zero parts on Default + Overrides —
nothing to swap, left alone. Untouched everywhere: BG106, BG310, BG6600 additives.

**Verification per line:** success toast → true remount (/home + back) → live quote
explode on the CVT Corolla (QO#2297); totals exact ($499.95 SMTRANSMISSION,
$4,721.65 Preferred 70K; ATFXWS parts $189.27/labor $298.26; HVTRANS $198.81/$203.92).
Revert baselines in /home/itadmin/bt-menu-build/: smtransmission-opcode-before-20260720.json,
smtransmissionhybrid- and atfxws-hvtrans-opcode-before-20260720.json.

**PITFALLS learned:**
- Opcode/quote search does NOT surface custom opcodes by CODE (even SMTRANSMISSION
  only offers `Create "..."`) — search by DESCRIPTION instead. SMTRANSMISSIONHYBRID's
  description has a typo: "Vehciles".
- Typing near the parts area can focus the **Fees** select ("No Match Found", no
  Create option) — the Create option only appears in the real Part Name select
  (`partName_undefined`).
- **PRICE-FREEZE CAVEAT (flagged to Joe):** placeholder parts have no master record,
  so their prices are FROZEN. ATFXWS previously floated with BG3123's list price —
  now fixed at $134.57; if BG3123 list changes, these lines need a manual touch.

**70K menu validated 2026-07-20** on Joe's VIN 5YFEPRAE0LP109245 (2020 Corolla
CVT, odo 69,500): Basic $239.85 TEK70000BNM (3 swaps + 5 inspections), Preferred
$4,721.65 SEVERE TEK70000PSM (27 svcs, Tony's order). This VIN = ideal
re-verification vehicle for any future trans-fluid change (CVT = the failure case).
Housekeeping note: throwaway verification quotes at BT (incl.
/ro/quotes/6a5e447e2e9f16469c9bf6f6 and QO#2297) may want cleanup.

## PHASE 8 — TONY'S "BG MENU REVAMP 2026" SHEET (received 2026-07-21, AWAITING JOE'S GO)
Tony sent a Google-Sheet PDF adding a **PART NUMBERS column** to his 25-service
spec + 2 embedded asks. Docs: `/home/itadmin/bt-menu-build/docs/BG-MENU-REVAMP-2026.pdf`
(+ revamp-1.png render). Full API audit dump:
`/home/itadmin/bt-menu-build/opcode-parts-audit-20260721.json` (all 25 à-la-carte +
23 SM* menu opcodes, status/cpFlat/rateType/parts w/ prices).

**PDF EXTRACTION PITFALL:** vision_analyze misread the sheet badly (hallucinated
"BG245" on ~15 rows). Ground truth = PyMuPDF word extraction:
`fitz.open(pdf)[0].get_text('words')` grouped by rounded y — the PART NUMBERS
column starts at x≈208 (between Op Code x≈161 and Description x≈300). Always use
positional text extraction, never vision, for spreadsheet PDFs.

**AUDIT METHOD (fast, no browser):** plain urllib POST to
`/api/service-module/u/opcode/search` with captured headers from
`/tmp/tekion_put_headers.json` (swap dealerId→1249, tek-siteId→-1_1249),
searchFields:["OPCODE"], exact-match filter, 0.3s pacing — 48 opcodes in ~20s.
External urllib works fine for opcode/search (not just in-page).

**Tony's 2 asks:** (1) transmission generic part = ALREADY DONE (Phase 7);
(2) EPR must state it includes an oil change + populate oil & filter —
à-la-carte OILEPRMOA already has generic OIL + OIL FILTER (unpriced) but
**SMMOAEPR (menu) has neither** (only BG6579).

**DRIFT FOUND: SMMOAEPR = $199.03 not $189.95** (+$9.08): labor $162.10 intact
from the 07-10 fix but the part is now BG6579 @ $36.93 (was $27.85 in parts) —
a parts-master price move re-broke the all-in target. LESSON: fixed-labor+real-part
all-in targets silently drift when parts reprice; consider generic fixed-price
placeholder parts (Phase-7 style) for price-critical lines.

**Part mismatches vs Tony's column** (all prices otherwise land exactly):
| Svc | Tony wants | Tekion has | Surface |
|---|---|---|---|
| BGBATT (à-la-carte) | BG985 | BG8801 (SM version has BG985 ✓) | à-la-carte |
| EXCHANGEPS (à-la-carte) | BG332 | BG6700 (SM has BG332 x2 ✓) | à-la-carte |
| COOLHV #17 | BG546+BG540+2gal 00272-SLLC2 | 1gal+BG546 only | MENU (pull-from-opcode) |
| HVCOOLANTEXCH #18 | NO BG, 1gal only | 2gal+BG546+BG540 | MENU |
| SMFRONTDIFF #20 | bg746 | BG75032 x2 | menu |
| SMREARDIFF #21 | bg328 | BG75032 x3 | menu |
| SMTRANSFER #22 | bg746 | BG79232 | menu |
| SMFRIG #25 | 00289-ACRKT | BG7073 Frigi-Fresh (à-la-carte ACFRESH has ACRKT ✓) | menu |

Note: COOLHV/HVCOOLANTEXCH part sets are exactly **SWAPPED** vs Tony's sheet
(the 7/3 build assigned them backwards relative to his revamp spec). Minor:
Tony's "892T" = BG982T; his 00272-SLLL2/SSLC2 = 00272-SLLC2 typos.
Joe ruled 2026-07-21: "Match Tony's column" — diffs/transfer swapped verbatim.

## ✅ EXECUTED 2026-07-21 (all rows above fixed, quote-verified)
Final state: SMFRONTDIFF=BG746 x2 (labor 188.33), SMREARDIFF=BG328 x1 + BG746 x3
(labor 133.34), SMTRANSFER=BG746 x2 (labor 188.33), SMFRIG=00289-ACRKT @43.00
(labor 46.95, holds $89.95), SMMOAEPR=BG109 29.69 + BG115 16.82 + generic Oil x6
@7.00 + generic OIL FILTER @6.00 (labor 143.44 → $189.95 exact), COOLHV=BG546+BG540
+2gal SLLC2, HVCOOLANTEXCH=1gal SLLC2 only. BGBATT/EXCHANGEPS needed NO touch —
**the audit JSON was STALE on those two** (live already had BG985/BG332). Baseline
revert file: bt-menu-build/tony-partmatch-baseline-20260721.json.

## Execution lessons (2026-07-21 batch, :9225 browser)
- **Y-coordinate row targeting is UNRELIABLE** on the opcode-edit parts table:
  matching inputs by "same y as the part select" hits the ADJACENT row after
  scrolls/re-renders (qty/price landed on wrong parts twice). Robust pattern =
  walk up from the `div#partName_undefined` select to the row CONTAINER, then pick
  that container's inputs by index (`partQuantity_undefined_quantity` = qty,
  `cpUnitPrice_undefined` = price). Verify with a re-read + screenshot/vision if
  reads conflict; **hard-remount (nav to /ro/opcode and back) before trusting a
  post-save read** — same-page reads can show your own unsaved DOM.
- `/type` endpoint needs `{selector, text}`; tag targets with `data-jay` attr,
  clear tags between ops (`removeAttribute`) or stale tags hijack later types.
- `click_trash` returning NO_ROW ≠ row gone — re-check after remount (BG540
  lingered once and needed a second trash + re-save).
- **SMMOAEPR included-service** (id 659ffecf65a9d765dfb63fd3) had Labor on
  Pull-From-Opcode but PARTS on Define-Here with stale prices — menu price won't
  follow opcode edits there. Fix: flip Labor to Define-Here CP Fixed 143.44 AND
  update the Define-Here part prices (29.69/16.82). Save fires 4x "Service saved
  successfully" toasts (normal).
- Opcode lookup APIs failed this session (v2/code/<CODE> 404, opcode/search via
  urllib "NOT FOUND" for real codes) — UI read via nav_opcode + part_rows() was
  the reliable ground truth; use the API dump only as a starting hint (it goes
  stale: BGBATT/EXCHANGEPS).
- **Quote-verify recipe** (proven): create throwaway quote → VIN 5YFEPRAE0LP109245
  odo 69500 → Service Menu tab → 70K → Preferred tier (TEK70000PSM = 27 services,
  ALL SM* opcodes incl. diffs/coolants/frigi) → Add To Quote → click the RO line
  to explode parts → regex-count old part numbers (must be 0) + new ones.
  Re-click interval until "Package OpCode :" shows the right TEK code.
  Note: BG7073 legitimately remains in SMCABIN (cabin+Frigi spray combo) — not a miss.

## Post-launch corrections (2026-07-22, both VERIFIED live)
- **SMIND / "Perform Fuel Injection and Air Induction System Cleaning Service"**
  (included-service edit id **6977a74d7247de1efa785cac**): rebuilt as Define-Here —
  Labor = CP **Fixed $186.76**, Part = **BG6591M PLATINUM FUEL INDUCTION KIT** ×1 @
  **$113.19** → line total **$299.95**. Verified via 70K-Preferred throwaway quote:
  parts request shows BG6591M @ 113.19.
- **SMMOAEPR** (id 659ffecf65a9d765dfb63fd3) service NAME reworded per Joe:
  "Install Motor Oil Additive and Engine Performance Restoration Kit" →
  **"EPR Service - Includes Engine Oil Change, BG EPR Treatment and MOA Additive
  Internal Engine Cleaning"**. Renaming = just re-type the `#name` input on the
  Edit Service page + Save; labor/parts untouched (Fixed 143.44, BG109+BG115+oil/
  filter). New wording renders directly in the quote's menu service list — the menu
  pulls the included-service NAME live, no menu-row edit or Publish needed.
- ⭐ BT quote rail = leaf PILLS ("70K" at y≈239) on a horizontal carousel:
  /mouse clicks on the pill coords can NO-OP forever (6 straight failures, panel
  stuck TEK5000BNM). Fix = dispatch synthetic MouseEvents on the pill's clickable
  ANCESTOR (climb parent while innerText <12 chars; class root_content_black…).
  Arrow the carousel (.icon-right-arrow* ~x1256,y251) until pill x<1200 first.
  Tier button ("Preferred") needs the same MouseEvent dispatch. Always verify by
  "Package OpCode : TEK<iv>…" regex.
- Save-toast + hard-remount (/home then back) verification both used per the
  SAVE-VERIFY trap; name + prices persisted.
