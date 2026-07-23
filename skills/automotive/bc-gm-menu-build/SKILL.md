---
name: bc-gm-menu-build
description: >
  The Blackstone Chevrolet & Cadillac (BC, Tekion dealer 1251) GM service-menu
  build project. Contains Joe's spec direction (clone the Blackstone Toyota
  architecture), the verified GMLOF oil-tier price audit, the parts-override
  plan for vehicle-correct GM parts, and open decisions. Load for ANY "GM menu",
  "BC menu build", "GMLOF", or Blackstone Chevrolet service menu work.
triggers:
  - gm menu
  - bc menu build
  - gmlof
  - blackstone chevrolet menu
---

# BC GM Menu Build — Joe's GM Menu Project

Multi-session project (started 2026-07-12). Sibling of the BT build — load
`bt-tony-menu-rebuild` for the full proven build mechanics (universal add-on
row, suppress/swap, included-service Fixed-price fix, quote-explode verify).

Slack home = BC menu thread `slack:C0BGTDMP9U2:1783876336.294119`.
BC store manager counterpart = Ruben Estrada (Restrada@blackstonegm.com).
Audit JSON: `/home/itadmin/bc-menu-build-gmlof-audit.json` (move into a
`/home/itadmin/bc-menu-build/` project dir when the build starts).

## Joe's spec direction (2026-07-12 Slack, his words paraphrased)
1. **Architecture = clone Blackstone Toyota** (Jay recommended BT over SCT/TOL
   spot-fix approach; Joe asked "like SCT or Lancaster or BT?" — BT is the
   evolved playbook). Universal add-on row, sum-of-services pricing, dedicated
   fixed-price menu opcodes, factory-line suppress/swap where needed.
2. **GMLOF family = the premium oil-change tiers on the menu** (GMLOF, GMLOF6,
   GMLOF8 "and a few more" — actual family is 7 opcodes, see audit).
3. **He wants vehicle-correct parts like TEK05052501 pulls** — but with menu
   price integrity. Plan: vehicle-scoped PARTS OVERRIDE rows on each GMLOF
   opcode (Overrides tab), forced fixed part prices that sum to target.
   Trade-off stated to Joe: overrides = static table we maintain per new model
   year, vs TEK's dynamic factory pull with floating price. He accepted.
4. **Washer fluid + fuel additive = SEPARATE menu lines** (currently the
   additive parts ride INSIDE every GMLOF tier — see audit note).
5. Joe will supply the **BG à-la-carte services list** for the add-on stack.

## GMLOF tier audit (live BC data, verified 2026-07-12)
All-in = CP FLAT labor + Σ(customerPayUnitPrice × qty). All 0.8 hr labor.

| Opcode | Status | Labor | Parts | All-in | Notes |
|---|---|---|---|---|---|
| GMLOF | IN_ACTIVE | not set | 24.20 | dead | 5qt shell, unpriced "bill oil filter" |
| GMLOF6 | ACTIVE | 60.49 | 88.45 | **148.94** | ⚠️ drifted — $1.01 short of 149.95? |
| GMLOF8 | ACTIVE | 48.48 | 114.47 | **162.95** | clean target |
| GMLOFD | ACTIVE | 45.37 | 204.58 | **249.95** | diesel, clean |
| GMLOFHD | ACTIVE | 45.37 | 244.58 | **289.95** | heavy diesel, clean |
| GMLOFL87 | ACTIVE | 48.69 | 157.35 | **206.04** | ⚠️ L87 V8 0W-40, no clean target |
| GMLOFMOBILE1 | ACTIVE | 79.24 | 250.71 | **329.95** | 8qt Mobil 1, clean |

Key part facts:
- **Every ACTIVE tier carries additive parts baked in**: 19435370 fuel
  treatment $27.85 (GMLOFD uses 19435373 $39.96; HD uses 19540631 $79.96;
  MOBILE1's 19435370 priced $34.49) + BG9822 "CLASS ACT" $9.99. Stripping
  these to their own menu line drops each tier ~$38 (varies) and requires
  re-solving labor to new targets.
- Most tiers use **generic placeholder parts** (partNumber:null "Oil Filter"/
  "Engine Oil" with a unitPrice) — that's where the vehicle-correct override
  rows come in. GMLOFL87 is the exception (real GM numbers: 12735811 filter,
  19432866 0W-40).
- Descriptions say tiers already include "Rotate tires... Set Tire Pressures,
  top off all fluids" — check for double-charging if rotation is also a
  separate menu line.
- 12580255 ($7.64, on GMLOF8/L87) — identify what this part is before
  restructuring.

## ARCHITECTURE LOCKED (2026-07-12 PM — supersedes the GMLOF-override plan above)
Joe's idea, Jay endorsed: **keep factory TEK05052501 on the menu and build
vehicle-scoped override rows on THAT opcode's Overrides tab** — one oil line,
overrides pick the tier by vehicle scope, parts stay DYNAMIC (correct filter +
correct oil qty per VIN). No suppress/swap like BT. Fixed labor per override
row back-solved so labor + dynamic parts ≈ tier target ("up to X quarts" =
CEILING pricing — less oil bills less, never more; Joe accepted).

**⭐ TIER MAP — JOE'S FINAL RULING 2026-07-13 (SUPERSEDES the LOF-family
targets; do NOT use the old $174.95/$199.95 numbers):**
| Tier | Scope | Target | Status |
|---|---|---|---|
| 4 & 6 cyl | Cylinder filter 4+6 | **$119.95** | ✅ LIVE, published + verified (ceiling $114.02 Malibu = correct under-target) |
| V8 gas | 5.3L + other gas V8 (excl 6.2L, excl Corvette/Camaro) | **$129.95** | ✅ LIVE 2026-07-14, penny-verified $129.95 exact |
| 6.2L plain (L86) | 2018-and-older 6.2L trucks/SUVs (year-split, Joe approved) | **$179.95** | ✅ LIVE 2026-07-14, penny-verified $179.95 exact |
| 6.2L L87 | 2019+ 6.2L trucks | **$204.95** | ✅ LIVE (labor $155.88, verified $204.95 exact) |
| Diesel 3.0L | Duramax LM2/LZ0 | **$214.95** | ✅ LIVE 2026-07-20, penny-verified $214.95 exact (QO#0930 Tahoe LM2) |
| HD diesel 6.6L | L5P 2500HD/3500HD | **$249.95** | sibling exists (labor $160.88 Define Here, NO parts rows yet) — needs parts+scope+back-solve |
| Mobil 1 | **ALL Corvettes + ALL Camaros** (every trim/engine) | **$279.95** | sibling created, needs parts+scope |
Notes: Tekion trim filter has no engine CODE — L86 vs L87 split is by MODEL
YEAR (2019+ = L87), Joe confirmed. Corvette/Camaro carve-out row must sit
BELOW overlapping engine rows (bottom-most applicable row wins). All tiers
0.5 Customer Hrs. Chevrolet first; Cadillac/Buick/GMC rows after Joe approves.
Old LOF-family audits remain at `/home/itadmin/bc-menu-build/{gmlof,lof}-audit.json`.

**Add-on stack** = Joe's BG sheet (`bc-menu-build/bg-services.xlsx`, parsed to
`bg-op-list.json`) — **21 services** (FISVC $259.95, DIESELFI, BGMOA, BGFSC 44k,
DFSC/DFC diesel cleaners, TRANS/TRSV10/TRSV-FILTER8/TRSV-FILTER trans tiers,
BATT, PSSERV, COOLANT/COOLANTD, CABIN, BGEPR/BGEPRD, BFX, FRONTDIFSVC,
REARDIFSVC, TCASESVC). Additive + washer = separate menu lines.
Chevrolet first; Cadillac + Buick later via make-scoped rows.

## 175K PILOT RECON (done 2026-07-12 — the dead interval, like BT's 160K)
- **Menu id = `65530c2cd0e3ef410082bb3d`**, ACTIVE/PUBLISHED, pure SYSTEM menu:
  1 empty template row (SYSTEM_WITH_OVERRIDE, no vehicle scoping, no services,
  all tiers SUM_OF_SERVICES). applicableMakes = chevrolet/buick/cadillac/gmc.
  Baseline for revert: `bc-menu-build/175k-baseline-20260712.json`.
- **BC rail uses 7.5K spacing — 175000 renders as "172.50K mi"**, NOT "175K".
  Package opcode = **TEK172500PSM**. Content today: Engine Oil & Filter +
  Tire Rotate + 19 inspections; PSM/SEVERE card showed $233.73 → oil op billed
  **0.40 hr / $30.00** once added to quote (QO#0905, 2021 Silverado 1500 @174,000).
- **TEK05052501 EXISTS at BC** — `/ro/opcode/edit/TEK05052501` loads (list
  search missed it; direct-URL rule again). Standard Overrides structure.

## Labor rates at BC (found 2026-07-12 — Joe built a new menu rate)
**URL: `/ro/labor-pricing`** (works at any store; added to sitemap). BC has 5:
CP $269/hr (1-RETAIL), INTERNAL $229/hr, WARRANTY $240.37/hr, LABOR GRID
$0–$3,963.47/90hr, **"Service Menu Pricing" $200/hr (4-TRADE) ← Joe's new rate**.
OPEN: hours-driven ($200/hr × hrs, price floats) vs Fixed-labor overrides with
$200/hr as fallback floor (exact tier targets) — asked Joe, awaiting his call.

## BC quote-build mechanics (differ from BT — hard-won 2026-07-12)
- **Native value-setter throws "Illegal invocation" at BC** (cached descriptor
  trick fails). Use `input.focus(); document.execCommand('insertText', false,
  text)` instead — works on make/year/model react-selects AND #vehicleOdometer.
  Option pick: exact-text leaf + mousedown/mouseup/click dispatch.
- Create Quote form input ids: `make`, `year`, `model`, `vehicleOdometer`.
  Model needs exact option text ("Silverado 1500", "Silverado 2500HD").
- **Rail-arrow trap**: the only `.icon-*arrow*` near the rail was the PAGE BACK
  button — clicking it bounced to the quotes list and lost the draft quote.
  The 7.5K-spaced rail had no hidden 175K entry; 172.50K IS the 175K menu.
- Pendo overlays fire at BC too — remove `[id*=pendo],[class*=pendo]` after
  every hard nav.
- Bare in-page fetch of `/api/service-module/u/opcode/search` 500s at BC
  ("Token doesn't exist") — direct fetch works for SOME endpoints (serviceMenu
  GET by id worked!) but not opcode search. serviceMenu config fetch:
  `fetch('/api/service-module/u/opcode/service-menu/'+id)` returned 200 direct.

## PILOT TEST RESULTS (2026-07-12 PM — the decisive session)
**Joe's rulings**: Plan B locked (fixed-labor overrides; $200/hr rate = fallback
floor only). Rate verified in edit form = $200/Hour (Joe thought $180 — it's
200, he accepted) with **part price code 4-TRADE** (intentional: menu parts
bill at TRADE when the line bills through that rate).

**Test override row built on TEK05052501** (row id `6a53ece349b96432985076f3`,
entityId `65530c29d0e3ef410082b163`): Chevrolet / Silverado 1500 / ALL_YEARS /
trim filter ENGINE_LITRE=6.2L (106 trims, "All trims incl future" radio),
Identifier=All Identifiers, Job=All Jobs, Customer Hrs 0.5, CP=Fixed Price
$100. Re-quoted QO#0905 → row FIRED (scoping works).

**⚠️ CRITICAL FINDING — labor PRICE overrides do NOT price menu lines AT
EITHER SURFACE (Path B test, definitively closed 2026-07-12 PM):**
- Opcode-level override row (CP Fixed $100): HOURS flowed (0.40→0.50 hr) but
  the flat price did NOT — quote billed 0.5 × $269 CP = $134.50.
- **Included-Service Overrides→Labor row TESTED TOO AND ALSO IGNORED**: built
  the same 6.2L-scoped row on the Included Service (Overrides tab → Labor →
  Define Here → row → CP Fixed Price $125.88), verified saved in the POST
  `.../included-service/<id>/overrides` payload (`laborRateType:"FLAT",
  flatPrice:125.88`), SAVED + menu PUBLISHED + re-quoted → quote calc STILL
  returned `pricingDetail.laborRateType:"CUSTOM", pricePerHour:269`,
  laborPrice $134.50. **The menu pricing engine ignores vehicle-scoped labor
  PRICE overrides entirely; only labor HOURS overrides flow through.** The
  earlier hypothesis "fix surface = Included Services" is WRONG for labor
  price — do not rebuild there.
- Menu-context labor price comes ONLY from the included service's own Labor
  config (Default tab Define-Here pay-type table: Labor Price Guide / Hourly
  Price / Fixed Price per CP/I/W row) — which is NOT vehicle-scoped, or from
  the menu vehicle row's Custom package price.

**✅ Path B parts half WORKS — parts price override rides through the dynamic
feed:** Included-Service Overrides→Parts Define-Here row (6.2L scope), add
part 19432337 with price $5.11 → quote resolves the part DYNAMICALLY and
prices it `priceType:"OVERRIDE", overriddenPrice:5.11` (8 × $5.11 = $40.88
trade). Dynamic parts + forced trade prices coexist.
- ⚠️ **SUPERSESSION BYPASS**: filter override on 12816256 did NOT take
  ($10.35 CALCULATED, not $8.19) — the feed requested ORIGINAL part 12731742
  and superseded it (`partResolveType:"REPLACED"`,
  `originalRequestedPartNumber:"12731742"`); the override match runs against
  the requested/original number. Key filter overrides to the ORIGINAL part
  number (12731742) as well — untested, verify with one quote.

**🏆 BREAKTHROUGH (2026-07-12 PM, later session) — Default-tab fixed labor
DOES fire in menu context, WITH parts staying dynamic:**
- Flipped the Included Service's **Default tab → Labor → Define Here → CP
  Fixed Price $100**, saved, re-quoted → quote returned `laborRateType:
  "FLAT", laborPrice: 100` (was CUSTOM $269/hr $134.50) while parts STILL
  pulled dynamically (oil 19432337 `OVERRIDE 8 × $5.11`, filter CALCULATED).
  Joe's rejected trade-off (fixed price vs dynamic parts) is FALSE — both
  coexist when fixed labor lives on the **Default tab**, not Overrides.
- Overrides-tab labor price = dead at BOTH surfaces even with Default =
  Define Here (tested: Override FLAT $125.88 never fired; the $100 that fired
  was the Default-tab value). **Only Default-tab labor prices menu lines.**
- ⚠️ SIDE EFFECT: flipping ONE Default-tab radio to Define Here flips ALL
  FOUR sections (y≈412/492/913/1177) to Define Here — re-scan every radio
  after any flip AND after save. Revert = flip all back to Pull From Opcode
  + Save (verified clean revert; quote returned to $185.73 baseline).

**→ LOCKED ARCHITECTURE (reported to Joe, per-line price = gospel):**
Six sibling **included services all pointing at the SAME factory opcode
TEK05052501** — one per tier (gas ≤6qt / gas 8qt / L87 6.2L / diesel / HD
diesel / Mobil 1). Each: Default Labor = Define Here → Fixed Price =
tier target − trade parts, Customer Hrs 0.5; **Parts = Pull From Opcode**
(dynamic GM feed preserved, VIN-correct parts + supersession); trade prices
forced via Overrides→Parts price rows (proven OVERRIDE ride-through). Menu
vehicle rows scoped by engine swap the right service in (BT swap mechanics,
zero hardcoded parts). L87 math: $174.95 − $49.07 parts = FLAT $125.88.
Rejected paths (for the record): $200/hr float (L87 $149.07, misses target),
custom package price rows (whole-interval only), BT-style static-parts swap
(Joe vetoed — kills dynamic pull).
- ⚠️ SUPERSESSION FIX (untested): key the filter trade override to the
  ORIGINAL requested part (12731742) in addition to 12816256 — override
  matching runs against the original number, so supersession bypasses
  overrides keyed only to the replacement.
- Still need from Joe: the five missing tier prices (only L87 $174.95
  confirmed against this architecture; LOF-family targets above are the
  likely values).

**Test artifacts still live at BC (clean up or build on per Joe's call):**
opcode test row $100 on TEK05052501; Included-Service Overrides Labor row
(FLAT 125.88) + Parts row (19432337@5.11 + 12816256@8.19), both 6.2L-scoped;
175K menu (65530c2cd0e3ef410082bb2c edit URL — note: PUBLISHED this session
to flush override changes; menu content itself unchanged). Included Service
id for the oil line = `65530c2cd0e3ef410082bb07`, entityId `...b163`.

**✅ Parts plumbing verified GOLD (the big unknown)**: menu oil line resolves
REAL GM parts dynamically per VIN — requested filter 12731742 auto-superseded
(`partResolveType:"REPLACED"`) to 12816256 @ $10.35; oil 19432337 × **8 qts**
@ $7.36 = $58.88. Parts total $69.23 for the 6.2L truck. Parts priced via
matrix at CP (filter: list 11.70 / trade 8.19 / billed 10.35) — re-check which
book applies once labor bills through the menu rate, then back-solve tier
labor = target − parts.

## 6.2L PILOT BUILT & LIVE (2026-07-12 PM, Joe's "build it")
**What exists now (first tier of the locked architecture, published):**
- Sibling service **"Engine Oil & Filter Remove and Replace - 6.2L V8"**,
  id `6a5441c449b9643298508fc6`, opcode TEK05052501, CP **Fixed Price $125.88**,
  Customer Hrs 0.50, Parts = Pull From Opcode, zero overrides (API-verified).
- 172.50K menu (`edit/65530c2cd0e3ef410082bb2c`): vehicle row Chevrolet /
  Silverado 1500 / All years / ENGINE_LITRE 6.2L (106 trims); factory oil line
  all tiers UNCHECKED (suppressed), sibling service all tiers CHECKED. Saved +
  PUBLISHED. Swap **confirmed firing** on QO#0905.
- Old factory service `65530c2cd0e3ef410082bb07` scrubbed back to factory-clean
  (all Default radios Pull From Opcode, overrides/fetch returns `data:[]`).

**⚠️ LEAK RULE (proven)**: overrides/test values on the SHARED factory service/
opcode fire into EVERY sibling service pulling from it (the $100 test override
contaminated the new 6.2L line). Per-tier labor/parts config must live on each
sibling; the shared factory service must stay pristine.

**⚠️ QUOTE SWAP PREREQ**: the menu row only matches if the quote vehicle has a
DECODED STYLE matching the engine scope — QO#0905's VIN decoded as 5.3L and the
swap silently didn't fire. Fix: quote page → chevron next to vehicle name →
Vehicle Update modal (**react-selects**, type directly) → pick the 6.2L style.

**✅ TIER 1 (6.2L) COMPLETE — trade-parts override built + verified 2026-07-13,
then REPRICED to Joe's new $204.95 target same day (labor $125.88 → $155.88).**
Sibling service Overrides→Parts Define-Here row (Chevrolet / Silverado 1500 /
ALL_YEARS / ENGINE_LITRE 6.2L, 106 trims): Modify System Parts rows =
19370233 qty 8 @ $5.11, **12731742 (ORIGINAL) qty 1 @ $8.19**, 12816256
(replacement) qty 1 @ $8.19 (both filter numbers keyed as belt-and-suspenders).
Saved (row id `6a550d3d58c7d50e40a16dd8`, entityType SERVICE) + menu PUBLISHED.
Quote ground truth (QO#0905 172.50K): laborRateType FLAT $125.88; filter
12816256 ×1 @ $8.19 **OVERRIDE** (partResolveType REPLACED, orig 12731742 —
supersession-bypass fix CONFIRMED: keying the override to the ORIGINAL number
makes it match through supersession); oil 19370233 ×8 @ $5.11 OVERRIDE.
**Line total = 125.88 + 40.88 + 8.19 = $174.95 EXACT.** Architecture proven
end-to-end; remaining tiers are clones of this recipe.

**VERIFIED 2026-07-13 (post-cleanup quote read, QO#0905 172.50K 6.2L line):**
- Sibling Default-tab **Fixed labor $125.88 FIRES on the live quote** ✅ — the
  locked architecture's labor half is proven end-to-end in production.
- Parts currently CALCULATED retail: filter 12816256 ×1 @$10.35 + oil
  19370233 ×8 @$15.24 → line ~$258 vs $174.95 target. Delta = the missing
  sibling-service trade-parts override (only remaining build step for tier 1).
- Old factory service cleanup CONFIRMED server-side: Default PUT 200 with
  `pullLaborFromOpcode:true`, overrides/fetch empty — factory-pristine.
- Dealer drift to 1249 struck AGAIN (3rd+ time this project) — re-verify
  `currentActiveDealerId === "1251"` before EVERY read/mutation, no exceptions.

### Repricing a tier's fixed labor (proven 2026-07-13, $125.88→$155.88)
1. Soft pushState to the sibling's `/edit-service/<id>/default` (dealer must
   already be 1251 — soft nav preserves dealer; hard nav resets to 1249 ~50%).
2. The Default-tab Labor Fixed Price input = `#labor-price`
   (ant-input-number, x≈643 y≈720). Native value-setter + input/change events
   works directly — no /mouse focus needed.
3. Bottom Save → verify the PUT `/opcode/service/<id>` response contains the
   new `flatPrice` (XHR hook). Toast may NOT render — trust the 200 + payload.
4. Re-publish the menu (soft nav to `/ro/service-menu-setups/edit/<menuId>`,
   Publish btn ≈1211,689) — quote won't reprice until published.
5. Verify on quote via the serviceMenu XHR capture (line total = labor + Σparts).
⚠️ RANDOM NAV-AWAY HAZARD: mid-edit the SPA once spontaneously landed on a
different menu edit page (unsaved labor change lost silently) and another time
bounced to the /sp/en help portal killing all evals (HTTP 500 from /eval =
page context died — check `location.pathname` first, hard /navigate back,
possibly twice). Re-verify field value before saving after ANY recovery.
- **React Query caches edit-service routes**: pushState nav does NOT refire the
  service GET or overrides/fetch. Reliable pattern = hard `location.assign` to
  the edit URL → arm XHR hook → click the Overrides tab → capture the POST
  `.../opcode/service/<id>/overrides/fetch` response (the ground truth).
- Override row delete: hover row → `[aria-label="icon-trash"]` appears at
  x≈1505 → synthetic dispatch works fine here → bottom Save. Save fires POST
  `.../overrides` — `{"data":[],"status":"success"}` = confirmed empty.
- Page renders HIDDEN duplicate Save/Cancel + rows at negative-x — always
  filter candidates to `rect.x > 0`.
- **Dealer drift struck TWICE this session** (landed on 1249/BT mid-work).
  Verify `localStorage.currentActiveDealerId === "1251"` after EVERY hard nav
  and before every mutation. Dealer switch: pill (1130,32) → picker leaf
  "Blackstone Chevrolet Cadillac" — must re-open + click in ONE script pass
  (dropdown closes between execute_code calls).
- **Quote rail carousel**: correct arrows = `icon-right-arrow-thin` /
  `icon-left-arrow-thin` at **y>400** (~1216,569). The `icon-left-arrow` at
  (80,87) is the PAGE BACK button — clicking it dumps you to the quotes list.
  ~5 right-thin clicks from 7.5K reaches 172.50K.
- Clicking an interval tile fires GET
  `/api/service-module/u/ro-read/v2/serviceMenu?intervalOnly=false` (~30KB) —
  parse `data.serviceMenuCatalog[0].menuPackages[0].serviceMenuItems[]`:
  `itemName`, `operationCode`, `laborHours`, `laborPrice`,
  `pricingDetail.flatPrice`, `parts[].{partNumber,quantity,unitPrice,priceType}`
  (priceType OVERRIDE vs CALCULATED = did the trade override take).

## SIBLING-SERVICE CREATE RECIPE (Add Service form — hard-won 2026-07-13)
All 6 remaining tier siblings created this way (dealer 1251):
- 4&6 Cyl `6a557b5549b964329854255e` (placeholder $70.88)
- V8 Gas `6a557b9be3559457bb280db8` ($80.88)
- 6.2L L86 2018-older `6a557bd64aa6485eea036e6e` ($130.88)
- 3.0L Duramax `6a557bf14aa6485eea036e9e` ($140.88)
- 6.6L HD Diesel `6a557c0d0da08c418d8c10fe` ($160.88)
- Mobil 1 Corvette/Camaro `6a557c29aa85e61624e3c481` ($180.88)
⚠️ Placeholder CP prices — MUST re-solve labor per tier after capturing live
trade parts, then reprice via the proven `#labor-price` edit flow.

Flow: `/ro/service-menu-setups/included-service` → "Add Service" btn → form at
`/add-service/default`. **Do the ENTIRE fill in ONE async /eval JS block with
sleeps** — the SPA randomly bounces to other pages (menu edit at dealer 1249!)
between separate execute_code calls; single-pass survived 5/5 times.
1. **OPCODE FIRST — picking the opcode AUTO-RESETS name + hrs** (autofill
   wipes anything typed earlier). React-select at x≈319,y≈234: focus inner
   input → execCommand('insertText','TEK05052501') → poll up to 15s for the
   option → pick via mousedown/mouseup/click dispatch (works here, unlike the
   part-name dropdowns).
2. THEN name (`#name`: focus, setSelectionRange, insertText) and Customer Hrs
   (`#CUSTOMER_HOURS_FIELD`: native value-setter + input/change works).
3. Labor "Define Here" radio = the x≈1154 radio nearest y≈492; `radio.click()`
   works. **On the ADD form this does NOT flip the other 3 sections** (Data
   Source/Parts/Fees stay Pull From Opcode — unlike the edit-page Default-tab
   flip-all side effect). Verify all 4 pairs anyway.
4. CP rate ant-select (x 300-500, topmost) → Fixed Price option (MouseEvent
   dispatch). Price input appears: `input#labor-price[placeholder="Enter
   price"]`. **Native value-setter here = RED-BORDER validation error on
   Save** — must focus + execCommand('insertText') + dispatch blur.
5. Save = **REAL bridge /mouse click at the button's coords** (element
   .click() silently no-ops — no POST fires). Success = POST
   `/api/service-module/u/opcode/service` **201** + redirect to
   `edit-service/<newId>/default`. Capture via XHR hook armed before click.
I/W pay rows can stay "Select" (unconfigured) — only CP needed to save.

### Rep-vehicle quotes for tier verification (worked 2026-07-13)
Live BC inventory VINs = `/home/itadmin/the-goods/data/bc.json` (421 units,
keys vin/year/model/trim) — bucket by model to find a rep VIN per tier (e.g.
Malibu 1.5L 4-cyl `1G1ZD5STXNF147570`, Colorado V6, 2500HD L5P, Corvette,
Camaro). Quote create: `/ro/quotes` → Create Quote btn (1168,96) → `#vin`
focus + insertText + Enter keydown → VIN auto-decodes make/year/model →
`#vehicleOdometer` insertText '174000' → Continue btn → lands on
`/ro/quotes/<id>/service/new`. Then Service Menu tab (997,305), rail
right-arrow-thin (1223,576) ×5 to 172.50K, click interval tile, capture the
`ro-read/v2/serviceMenu` XHR (~30KB) for the line's parts ground truth.

## ⚠️ OPCODE-LEVEL CONTAMINATION BLOCKER (found 2026-07-13, awaiting Joe)
TWO PARTS override rows live on factory TEK05052501 ITSELF (entityId
`65530c29d0e3ef410082b163`): ids `6a51326c13e83167cc9104ec` (ALL Chevrolet)
+ `6a513cf973812f2514f90601` (ALL GMC), created 7/10 (PRE-project — possibly
Joe's own). They force oil 19432337 → **qty 8** @ $5.11, 88862469 → qty 2,
filter 12816256 @ $8.19 on EVERY vehicle. Quote-verified: 2022 Malibu 1.5L
4-cyl bills 8 QUARTS. Per-part matching insight: opcode rows only corrupt
vehicles whose FEED requests those exact part numbers — L87 trucks request
19370233 so the L87 tier verified clean despite these rows. But all
0W-20 gas vehicles (4/6-cyl, V8 5.3L) request 19432337 → qty corrupted →
**cannot back-solve those tiers to the penny until rows are deleted** (asked
Joe 7/13; do NOT delete without his OK — never-guess rule).
Read rows: opcode edit → Overrides tab click → Parts sub-nav (x≈123,y≈282)
→ capture GET `.../override/PARTS` via XHR hook (direct fetch 500s).

## MAKE RULING (Joe, Slack 2026-07-14 PM): CHEVROLET-ONLY for now
"1 for now, lets make sure chevrolet works, then I'll send you everyone else."
Build all remaining tier rows Chevrolet-only; GMC/Cadillac/Buick backfill is a
LATER pass once Joe sends the rest. GMC/Cadillac/Buick → factory pricing is
EXPECTED interim behavior (don't re-flag the Yukon fall-through as a bug).

## L86 TIER ✅ COMPLETE 2026-07-14 PM (4th tier live — see references/build-state-2026-07-20.md (LATEST; 07-15 and 07-14 files are stale))
- Parts override row `6a570d4fe8f4995ab2ec893e` on sibling `6a557bd64aa6485eea036e6e`:
  Chevrolet / ALL_MODELS / years 2018→2007 / ENGINE_LITRE 6.2L (136 trims);
  19432337 qty8 @5.11 + 12731742 @8.19 + 12816256 @8.19 (server-verified).
- Labor: Add-Service placeholder $130.88 was ALREADY the back-solve
  (179.95−49.07) — check placeholder before repricing; they were seeded as
  back-solves.
- Menu row 4 (172.50K): Chevrolet/All/2007–2018/6.2L; MSS factory line
  unchecked, L86 sibling added all tiers. Saved + PUBLISHED.
- Penny-verified $179.95 EXACT on QO `6a570985914c9d039a04ba0d` — 2018
  Silverado LTZ 6.2L via **SYNTHETIC VIN 3GCUKSEJ6JG481376** (no ≤2018 6.2L
  in bc.json: took a real 2018 Silverado VIN, swapped engine char to J +
  series to S, recomputed check digit — Tekion decoded it fine; reusable
  trick when inventory lacks a rep vehicle).
- Row overlap: 2018 6.2L matched BOTH V8-gas row (3) and L86 row (4) —
  bottom-most-wins correctly gave L86. L87 row unaffected (2019+ scope).

### New mechanics this pass (2026-07-14 PM #2)
- **MSS/Add-Services service search inputs (#SYSTEM_SERVICES_NAME_0 /
  #ADDED_SERVICES_NAME_0): value-setter AND /type both fail (eval 500s /
  clears). WORKS: real /mouse click on cell → JS .focus() → per-char
  `/press` key taps → options render → pick via mousedown/up/click dispatch.**
  Search is fuzzy-scored: 'oil' buries the target; type a DISTINCTIVE
  substring ('older' → 2 hits, ' & filter' → exact factory line).
- Row-4 caret: plain pivotIcon .click() no-ops; full mousedown/mouseup/click
  MouseEvent dispatch expands it.
- **In-page fetch() of service-module APIs 500s "Token doesn't exist"** (axios
  interceptor auth — same as TL lesson). Menu GET/overrides-fetch must be
  captured via XHR hook + driving the UI (hook BEFORE clicking Overrides→Parts
  sub-nav; the fetch fires on Parts click, len ~30 = empty data[] from the
  Overrides tab click itself).
- Year multi-select: ArrowDown opens, then scrollIntoView each year option +
  real /mouse click, Escape to close. 12 years (2007–2018) took ~20s.
- MSS row state after reload: SYSTEM_SERVICES row cbs [false×4] + ADDED row
  cbs [true×4] = suppression persisted; verify via checkbox y-alignment scan.

## ALL 6 SIBLING SERVICES CREATED (2026-07-13 PM — batch Add Service recipe)
Created via Included Services → **Add Service** button (top-right ~1202,160).
All: opcode TEK05052501, Customer Hrs 0.5, Labor=Define Here, CP=Fixed Price
(placeholder — re-solve labor after capturing each tier's live trade parts),
Parts=Pull From Opcode (untouched):
| Tier | Service name suffix | id | placeholder labor |
|---|---|---|---|
| 4&6 cyl | "- 4 & 6 Cylinder" | `6a557b5549b964329854255e` | 70.88 |
| V8 gas | "- V8 Gas" | `6a557b9be3559457bb280db8` | 80.88 |
| L86 | "- 6.2L V8 (2018 & Older)" | `6a557bd64aa6485eea036e6e` | 130.88 |
| Diesel | "- 3.0L Duramax Diesel" | `6a557bf14aa6485eea036e9e` | 140.88 |
| HD diesel | "- 6.6L HD Diesel" | `6a557c0d0da08c418d8c10fe` | 160.88 |
| Mobil 1 | "- Mobil 1 (Corvette & Camaro)" | `6a557c29aa85e61624e3c481` | 180.88 |
(L87 `6a5441c449b9643298508fc6` already live at $204.95 verified.)

### Add Service form recipe (hard-won 2026-07-13 — batch-proven ×6)
Single-pass async JS block via /eval works (see FILL_JS in session); key traps:
1. **Field ORDER: opcode FIRST, then name/hrs** — picking the opcode option
   AUTO-POPULATES Service Name and WIPES name+hrs typed before it.
2. Opcode react-select: focus inner input of the 2nd `-control` (x≈319,y≈234),
   `document.execCommand('insertText')`, poll up to 15s for the option,
   pick via mousedown/mouseup/click dispatch (works here, unlike part options).
3. Name `#name`: focus + setSelectionRange + insertText. Hrs
   `#CUSTOMER_HOURS_FIELD`: native value-setter + input/change events OK.
4. Labor **Define Here radio: `radio.click()` works** (x≈1154,y≈492); flipping
   Labor does NOT flip Parts/Fees on the ADD form (unlike the edit-page
   all-four-flip trap). Verify all radios after anyway.
5. CP rate = FIRST `.ant-select` in x 300-500 band → MouseEvent dispatch →
   dropdown li "Fixed Price".
6. **Price input (`#labor-price` placeholder "Enter price"): native
   value-setter LEAVES A RED BORDER and Save silently no-ops** (form thinks
   it's empty). Fix: focus + `document.execCommand('insertText')` + blur.
7. **Save button MUST be a REAL bridge /mouse click** at its coords —
   synthetic `.click()` dispatch does NOT fire the POST. Success = URL flips
   to `/edit-service/<newId>/default` + POST `/opcode/service` 201 (XHR hook).
8. Between creations: soft pushState back to the included-service list;
   Discard modal if prompted; re-verify dealer 1251 EVERY pass.

### Opcode-level contamination purge (2026-07-13, Joe approved deletion)
The two 7/10 test rows on TEK05052501 Overrides→Parts (row ids
`6a51326c13e83167cc9104ec` ALL-Chevrolet + `6a513cf973812f2514f90601` ALL-GMC,
forcing 19432337 qty 8 @5.11 + 12816256 @8.19 on EVERY vehicle — quote-proven
to bill 8qts on a 1.5L Malibu) are DELETED: hover row → `[aria-label=
"icon-trash"]` at x≈1513 (synthetic dispatch fine) → repeat → real-mouse Save
→ POST override/PARTS returned `{"data":[]}`. Factory opcode now pristine —
sibling parts overrides are the ONLY pricing surface. When telling Joe about
opcode-row deletions, clarify it's override ROWS, not the opcode itself.

### Shared-browser hazards (this session's drift root causes)
- **Jay's own cron jobs share the :9223 browser**: SCT alignment 7PM, SCT
  back-counter bin check 8:00PM + count sheet 8:15PM all yank the session to
  dealer 876 / other pages MID-BUILD. Around 7-9PM expect hijacks — re-pin
  1251 + re-verify path before EVERY mutation, and prefer single-pass JS
  blocks that finish in one eval.
- SPA also spontaneously lands on a BT (1249) menu edit page
  `/ro/service-menu-setups/edit/69c6e9ed7fb9de2c3f3e0996` ("Edit Menu - 5000
  mi") — recover: soft pushState away, Discard modal, re-pin.
- Quote page can go BLANK (body empty, path "blank") after publish+nav —
  hard /navigate again, wait 15-20s.
- Malibu 4-cyl test quote (for the 4&6-cyl tier): QO id
  `6a557463b64104323679c49c` (2022 Malibu 1.5L, VIN 1G1ZD5STXNF147570,
  odo 174,000 → use 172.50K interval). Rep VINs for other tiers pullable from
  `/home/itadmin/the-goods/data/bc.json` (live BC inventory).

## TIER A (4&6-cyl $119.95) BUILT 2026-07-13 PM — labor back-solve + penny-verify PENDING
State as of session end (resume here):
- Sibling `6a557b5549b964329854255e` Overrides→Parts row LIVE: Chevrolet /
  All Models / All Years / Trim filter **Engine Cylinder {4,6}** (~7,944
  trims). Modify System Parts rows SAVED server-side: 19432357 qty 6 @ $4.69
  (Colorado V6 oil), 55594651 qty 1 @ $10.21 (Colorado filter), 19432337
  @ $5.11 (Malibu oil), 25206377 qty 1 @ $6.87 (Malibu filter).
- 172.50K menu row 2 LIVE + PUBLISHED: Chevrolet/All/All, Cylinder {4,6},
  factory oil line suppressed, 4&6-cyl sibling checked all tiers.
- Malibu quote-verify (QO `6a557463b64104323679c49c`) confirmed swap fires,
  labor FLAT, parts all priceType OVERRIDE (1×6.87 + 5×5.11 = $32.42).
- **Tier A labor REPRICED + VERIFIED 2026-07-14 AM**: `#labor-price` already
  held **81.6** (ceiling back-solve: 119.95 − 38.35 = $81.60), menu
  re-PUBLISHED (PUT publish=true 200). Malibu (QO 0908) serviceMenu capture:
  labor FLAT 81.60 + 1×6.87 + 5×5.11 = **$114.02** (under target = correct
  ceiling behavior).  ✅ **COLORADO QTY-NULL — RESOLVED 2026-07-14**: Joe quoted a DIFFERENT
  Colorado VIN and the oil change worked (qty populated, tier billed). The
  qty-null is an ISOLATED GM-feed data gap on specific build styles, not a
  build defect. On live ROs such vehicles surface as Request Pending and
  parts fills qty at the counter. Tier A fully validated. (Original finding
  kept below for reference:)
  ⚠️ **COLORADO QTY-NULL ISSUE (was open, now resolved above)**:
  fresh 2019 Colorado V6 quote (QO 0910, VIN 1GCGSCEN7K1294993) — swap fires,
  part PRICES override (19432357 @4.69, 55594651 @10.21 both OVERRIDE) but
  `quantity:null` in the feed → quote line bills labor-only $81.60 and parts
  sit qty 0 "Request Pending" (P&A request state). GM feed didn't return oil
  capacity for this style. Cannot penny-verify $119.95 on this VIN until
  resolved — try a different V6 VIN or ask Joe how advisors handle
  Request-Pending menu parts.
- **CEILING-VEHICLE METHOD (per-tier)**: oil qty floats per engine within a
  scope (Malibu 5qt vs Colorado 6qt). Pick the highest-parts-cost vehicle in
  scope from bc.json, quote it to capture its feed parts + trade prices, add
  EVERY distinct part number seen across rep vehicles to Modify System Parts
  (each with its trade price), and back-solve labor to the CEILING vehicle.
- Tier B (V8 gas): partial scope row was WIPED by dealer drift (Make+Model
  set, never saved). Rebuild from scratch; Overrides tab showed "No rows
  found" on re-check. Tiers C–F untouched.

## TIER B (V8 gas $129.95) REBUILT 2026-07-14 — parts override SAVED+VERIFIED
- Scope row id `6a566c24cdc3c0708c8c4854` on sibling `6a557b9be3559457bb280db8`:
  Chevrolet / ALL models (285, via "All" option in the model multiselect) /
  ALL_YEARS / trim filter **ENGINE_CYLINDER ["8"] + FUEL_TYPE ["Gas"]**
  (server-verified payload). Fuel Type facet (Joe confirmed) solves the 6.6L
  gas-L8T vs diesel-L5P litre collision in ONE row — no model enumeration.
- Modify System Parts (server-verified via overrides/fetch): 19432337 qty 8
  @ 5.11, 12731742 (ORIGINAL) qty 1 @ 8.19, 12816256 (superseded) qty 1 @ 8.19.
- Labor already $80.88 = 129.95 − 49.07 (8-qt ceiling parts) — NO reprice
  needed (placeholder happened to equal the back-solve).
- Corvette/Camaro ARE caught by this row (gas V8) — by design: the Mobil 1
  menu row sits BELOW, bottom-most-wins steals them. Verify at quote time.
- Rep VIN verified feed: 2019 Silverado 1500 RST `1GCUYEED7KZ122937`
  (5.3L, feed = 19432337×8 + 12731742→12816256 REPLACED). Quote id
  `6a5667d3548c3a1defd78dc9` (odo 174,000 → 172.50K interval).
- ✅ TIER B COMPLETE 2026-07-14 PM: menu row 3 built (Chevrolet / All models /
  All years / trim filter ENGINE_CYLINDER 8 + FUEL_TYPE Gas, 11,397 trims),
  factory oil line suppressed via MSS add + uncheck 'Apply to all Tiers'
  master box, V8 Gas sibling added via Add Services (all tiers checked).
  Saved (PUT setup?publish=false 200) + PUBLISHED (PUT publish=true 200).
  PENNY-VERIFIED on Silverado quote serviceMenu capture: labor FLAT 80.88 +
  19432337×8@5.11 OVERRIDE + 12816256×1@8.19 OVERRIDE = $129.95 EXACT.
  NOTE: menu row order in API = 6.2L(1), 4&6cyl(2), V8gas(3) — V8-gas row is
  bottom-most today and still verified correct on a 5.3L; the 6.2L row wins
  for 6.2L trucks because its scope row is MORE SPECIFIC (Silverado 1500 +
  ENGINE_LITRE 6.2L). Watch ordering when adding Mobil 1 (must beat V8-gas
  row for Corvette/Camaro — verify at quote time, reorder via drag handle at
  x≈139 if bottom-most-wins doesn't already resolve it).

## YEAR SPLIT EXECUTED 2026-07-14 PM (L87 row now 2019–2026) + ⚠️ MAKE-COVERAGE BLOCKER
- Joe's ruling: 6.2L **2018-and-older = $179.95 (L86 tier)**, **2019+ = $204.95
  (L87 tier)**. Implemented by adding YEAR scope **2019–2026** to the EXISTING
  L87 menu row on the 172.50K menu (not by row ordering), saved + PUBLISHED.
  This makes ≤2018 6.2L trucks fall through to FACTORY pricing until the L86
  row exists — intentional interim state.
- **Negative verify method (new pattern)**: proved the year scope works by
  quoting an OUT-of-scope vehicle — 2016 GMC Yukon Denali 6.2L, odo 174,000,
  quote id `6a56a57dd284f235bbf46e01` — and confirming the oil line came back
  FACTORY (labor 107.60, parts 19432337×8@7.36 + 12816256@10.35, all
  CALCULATED, no FLAT labor). A tier build isn't fully verified until both an
  in-scope penny-verify AND an out-of-scope negative verify pass.
- ⚠️ **THE YUKON EXPOSED THE MAKE GAP**: menu-row Make cell is SINGLE-SELECT
  (Buick/Cadillac/Chevrolet/GMC) and every tier row is Chevrolet-only — so
  GMC/Cadillac/Buick vehicles NEVER match any tier and bill factory dynamic
  pricing. Asked Joe 2026-07-14: (1) keep Chevrolet-only, or (2) duplicate
  each tier row per make (4 rows/tier) + backfill the 3 live tiers.
  **DO NOT build the L86 row or any further tier rows until Joe answers** —
  the Make scoping of every remaining row depends on it. Check Slack for his
  answer before resuming.
- L86 verify candidates from bc.json (≤2018 6.2L): Silverado high trims,
  Tahoe/Suburban; Escalade=Cadillac, Sierra Denali=GMC (only usable if
  option 2). The 2016 Yukon quote above is reusable as an L86 penny-verify
  vehicle IF GMC ends up in scope.
- Session hazards re-confirmed: hijack to dealer 1092 parts page, bounce to
  `/sp/en` help-portal login (all evals die — hard /navigate back, maybe
  twice), bounce to `/core/roles`. Re-arm XHR hooks after every recovery;
  re-verify `{path, dealer}` before every mutation.

### New mechanics found 2026-07-14 (Tier B rebuild session)
- **overrides/fetch response shape = `data[0].overrideResponse`** (row JSON is
  nested one level down — NOT data[0] directly). parameters[] + override.
  modifiedSourceParts[] with overriddenQuantity per part.
- **MSP row-builder interaction pattern that works**: react-select cells need
  a REAL /mouse click on the cell to MOUNT the input (JS focus on a td input
  fails with 'no input' half the time); THEN keyboard ArrowDown (opens menu,
  options render) → dispatch mousedown/mouseup/click on the option node.
  Identifier/Job dropdowns each have exactly one option (All Identifiers /
  All Jobs).
- **Rows reflow BOTH axes after every single interaction** (±325px x AND
  ~40px y shifts; qty x jumped 709→1033 mid-session). Re-scan by part-number
  text anchor (find the row containing '128162 56', then number-inputs within
  ±18px y) — never reuse coords, never trust a prior scan.
- **Qty values get WIPED by reflow** — after setting qty+price on a row,
  re-audit ALL rows' input values before Save (one qty silently reverted to
  '' and another row inherited a phantom '8').
- **Caret-expand mid-edit fires the "Do you want to save your changes?"
  modal → click Save** — this SAVES the scope row server-side (POST 200 w/
  row JSON) and is a legitimate way to persist the scope before parts work.
  Save bounces you back to the Default tab; re-enter Overrides → Parts.
- **Cross-store toasts (SCT/TOL "Fulfillment Request") fired ONTO the BC edit
  page mid-build** (Jay's own crons + live store traffic share :9223).
  NEVER click them — remove from DOM: querySelectorAll ant-notification/
  toast/notification containers with rect.x>800 → .remove(). Verify body
  text no longer contains other store names before proceeding.
- **Stray half-filled MSP row (Identifier set, no Job/Part) blocks Save with
  red borders** — delete it via its row kebab (icon-overflow at x≈1075 in
  the row band) → Delete menu item (renders mid-screen ≈x1152). Screenshot+
  vision BEFORE clicking Delete (toast-hazard rule) and re-verify the 3 real
  part rows survived after.
- **Save success renders NO toast** here — trust the POST /overrides 200 +
  response contains modifiedSourceParts. Then ground-truth verify: hard
  reload → arm hook → Overrides tab → Parts sub-nav click (filter x>0! the
  hidden negative-x dup 'Parts' nav exists) → capture overrides/fetch.
- Quote create flow re-verified: /ro/quotes → Create Quote (1168,96) → #vin
  focus+insertText+Enter → decode wait 6s → #vehicleOdometer insertText →
  Continue (1211,689). New quote does NOT appear in the quotes list until it
  has services — go direct to `/ro/quotes/<id>/service/new`.
- 'Something went wrong' quote dead-end after soft nav: hard /navigate to
  /ro/quotes recovers (documented before, re-confirmed).

### TIER B GROUND TRUTH CAPTURED 2026-07-14 AM (resume from here)
- Rep quote: **2019 Silverado 1500 RST 5.3L, VIN 1GCUYEED7KZ122937, QO id
  `6a5667d3548c3a1defd78dc9`**, odo 174,000 → 172.50K interval. Feed parts
  (qty populated fine): oil **19432337 × 8 qts** (CP $7.36 CALCULATED) +
  filter **12816256** REPLACED from orig **12731742** (CP $10.35).
- Trade back-solve: 8 × $5.11 + $8.19 = **$49.07 parts → labor = 129.95 −
  49.07 = $80.88 — the sibling's placeholder is ALREADY $80.88, no reprice
  needed.** Remaining Tier B work = parts override row (19432337 @5.11 +
  BOTH filter numbers 12731742/12816256 @8.19) + menu swap row + publish +
  re-verify on QO 0911-era Silverado quote above.
- ⚠️ **6.6L LITRE AMBIGUITY (unresolved scoping hazard)**: BC's 2500HD gas
  V8 (L8T) and Duramax diesel (L5P) are BOTH "6.6L" in the trim
  ENGINE_LITRE filter — litre alone cannot split V8-gas from HD-diesel.
  Check whether the trim modal Filters offer a FUEL TYPE facet before
  saving the V8-gas scope; if none, scope the diesel tiers' rows and place
  them BELOW so bottom-most-wins ordering resolves it. Do not guess.
- Fresh quotes with NO services attached do NOT render in the /ro/quotes
  list — navigate straight to `/ro/quotes/<id>/service/new` by saved id.
- Colorado qty-null: resolved (see Tier A note) — isolated GM style gap;
  Joe's re-quote on a different VIN billed correctly.

### New pitfalls found 2026-07-13 PM (this window)
- **Part-search dropdown backend GOES STALE in long edit sessions**: every
  part search returns []/"No Match Found" — even for numbers already saved
  in the same table; no XHR even fires. FIX = hard reload the edit-service
  page (saved rows persist server-side), re-expand, add fresh. Don't fight it.
- **Screenshot endpoint changed: GET (not POST) `:9223/screenshot`** →
  JSON with base64 `screenshot` key; decode to /tmp/*.png for vision_analyze.
  POST /screenshot now 404s.
- **`/type` endpoint CLEARS the field before typing** — always send the
  complete final string; incremental appends wipe prior input.
- Modify System Parts table reflowed **~325px LEFT** after row adds — a
  part number landed in the Identifier cell of the wrong column. Re-locate
  every cell by placeholder/text query immediately before each interaction.
- Mid-edit **Confirm Navigation modal → click Save** preserves the row scope
  (validated again).
- Caret-hunting mis-click on the left-nav CM icon navigated away and WIPED
  the unsaved menu row — **save the menu edit page BEFORE expanding rows**.
- Evening cron hijacks confirmed again (drift to 876 parts page ~9PM);
  pgrep showed no competing process — the drift can occur with nothing in
  ps. Re-pin: pill (1130,32) → leaf (1095,262), verify localStorage.

## OPEN DECISIONS (waiting on Joe)
- [ ] Delete the 2 opcode-level ALL-make parts rows on TEK05052501? (blocker above)
- [ ] Washer fluid line spec (BG9822 $9.99 rides inside GMLOF codes today)
- [ ] Tier scoping map: which models/engines = 6qt vs 8qt vs L87 vs Mobil 1
- [ ] Additive part #: GMLOF carries 19435370, BG sheet BGFSC uses 19435372;
  19435372 = $90.53 inside FISVC vs $27.85 pour-in — deliberate?
- [ ] LOFHD = LOFMOBILE1 = $279.95 tie acceptable?

## Mechanics notes (this store)
### Included-Service Overrides mechanics (learned in the Path B test 2026-07-12)
- **Overrides tab structure**: left sub-nav Labor / Parts / Fees / Identifier &
  Jobs; EACH sub-section has its own Pull From Opcode ⟷ Define Here radio and
  its own vehicle row builder. Flipping Define Here spawns the builder fresh.
- Save = bottom-most 'Save' button; success POST goes to
  `/api/.../included-service/<id>/overrides` (200) — capture it to verify the
  persisted row JSON (parameters[] + override.laborPriceDetails /
  override.parts) instead of trusting the toast.
- **Quote does NOT reprice on menu edits until the menu is PUBLISHED** — after
  any included-service override save, open the menu (`/ro/service-menu-setups`
  → kebab → Edit → Publish) before re-quoting, else you're reading stale.
- Quick one-line isolation on the quote: toggle the service checkbox off/on in
  the menu panel — each toggle fires `opcode/service-menu/recalculate` (capture
  it; ~30KB, parseable whole) whose TEK05052501 node holds laborPrice /
  pricingDetail / parts[] with priceType — the definitive per-line truth.
- **SPA "wrong turn — Retry" error page**: pushState nav into edit-service can
  land on a dead error screen; recover with a hard `location.href` reload of
  the edit URL (hooks die, re-arm).
- Default-tab inspection is safe if NEVER saved: flip Define Here to read the
  pay-table (CP rate ant-select options = Labor Price Guide / Hourly Price /
  Fixed Price; price input id `labor-price`), then hard-reload to discard.
- Parts add-row on an Included-Service Overrides→Parts row: same CRITICAL
  ORDER as opcode surface — Identifier + Job FIRST, then part number (type
  FULL number, pick real option, ignore Create). Rows reflow after adds;
  re-scan coords. Failed save = generic red toast, no field borders.

### Overrides row-builder traps at BC (hard-won 2026-07-12 PM)
- **Sibling Overrides→Parts build recipe (worked clean 2026-07-13):** flip
  Parts radio Define Here (/mouse on the radio) → build scope row (react-select
  Make via /mouse + option click; Model/Year = ant-dropdown checkbox lists,
  label-walk-up pairing; Trim modal via /mouse on cell center, filter 6.2L,
  Apply, keep All-trims, Save) → expand row caret by selector → parts go in
  **Modify System Parts** (NOT Add Custom Parts) → per add-row: Identifier +
  Job FIRST, then part number. **Part option pick: /mouse on the option is
  UNRELIABLE for react-select part options (cell stays empty/red) — use
  KEYBOARD: focus inner input, /type the number, wait 3s, ArrowDown past the
  Create option to the real one, Enter.** Qty/price = native value-setter on
  the ant-input-number after /mouse-focus; if activeElement misses, select the
  input directly by position and focus()+set. Table shifts ~±325px x on
  row-add reflow — re-scan coords every row. Save success = toast "Opcode
  updated successfully" + POST .../service/<id>/overrides response contains
  the row JSON.
- **Quote page "Something went wrong" after publish:** soft pushState nav to a
  quote URL can dead-end (stale React Query). Fix = hard /navigate to
  /ro/quotes list → click the quote number cell → Service Menu tab. Dealer
  survives hard nav ~50% — ALWAYS re-check currentActiveDealerId.
- **Failed Save silently COLLAPSES the row and wipes ALL inner fields**
  (Identifier/Job/Hrs/rate/price) with only a generic "Please correct form
  errors" toast — no red borders findable, no field-level message. Required
  set before Save: Identifier=All Identifiers, Job=All Jobs, **Customer Hrs**
  (required!), rate type, price. Re-expand and redo everything if it errors.
- **Caret expand needs a REAL bridge `/mouse` click** at the caret coords —
  synthetic MouseEvent dispatch on `elementFromPoint` no-ops for row expand.
- Left-nav section items (Labor/Parts/Fees/Cost Center) sit close to row
  carets — a mis-aimed click switches section and drops unsaved work (row
  scope survives if the nav-away "save your changes?" modal → Save).
- **Native value-setter WORKS on ant-input-number inputs** (price, Customer
  Hrs) — the "Illegal invocation" failure is react-select-specific only.
  `document.execCommand('insertText')` also works but the bridge /eval can
  500 intermittently — retry loop (3×, 2s) around eval calls.
- CP Labor Rate select = ant-select (not react-select): open via MouseEvent
  dispatch on `.ant-select` in the pay-table row band, options render in
  `.ant-select-dropdown li` (Labor Price Guide / Hourly Price / Fixed Price).
  Fixed Price reveals an `input.ant-input-number-input[placeholder="Enter
  price"]`.
- The sticky Save-bar (`.save-container`) overlays pay-table coords — click
  buttons via element dispatch, not raw coords.
- Trim engine filter: open trim modal → Filters → check 6.2L → Apply →
  verify banner "Filters (1)" + result count (106) → keep "All trims
  (including future trims)" radio → modal Save. Saved payload shows
  `standardTrimFilterDetails: {ENGINE_LITRE:["6.2L"]}`.
- **FUEL TYPE is a trim-modal filter facet too (Joe confirmed 2026-07-14)** —
  resolves the 6.6L gas-L8T vs 6.6L diesel-L5P litre collision: scope V8-gas
  as Engine Cylinder 8 + Fuel Type Gas; diesel tiers as litre + Fuel Diesel.

### Tier-5 recovery lessons (2026-07-20 — parts silently dropped AFTER verified save)
- **Row scope surviving ≠ parts surviving.** A misnavigation/SPA hiccup between save
  and publish left the Overrides→Parts row persisted (Make/Model/Year intact) but
  `customParts: []` — the 3 parts were GONE even though an earlier remount-verify
  had passed. TELL on the quote: menu line prices at labor-only (e.g. $148.20 flat).
  Always re-verify parts specifically before penny-verify.
- **override/LABOR vs override/PARTS are SEPARATE endpoints** — an empty capture on
  the LABOR fetch is NOT proof the parts row is empty. Match the section (left-nav
  Labor/Parts) to the endpoint you're reading, else false "empty" diagnosis.
- **Publish ground truth = XHR capture of `PUT
  /api/service-module/u/opcode/service-menu/setup?publish=true` → 200.** No confirm
  modal appears at BC. Arm the hook BEFORE clicking Publish (1211,689).
- **A quote line added BEFORE publish stays STALE forever** — it never repriced
  after republish. Don't fight the delete: the expanded service line's trash icon
  is at ~(1225,407) (kebab at 1201,209 opens nothing), but the cheapest path on a
  throwaway quote is to just add a FRESH copy of the package from the Service Menu
  panel and read that line.
- Trim modal: **Apply only applies filters; the modal's own Save (~1005,711) is
  what commits** — Apply-then-close loses the selection.

### Tier-5 COMPLETION lessons (2026-07-20 PM — $214.95 verified; T5 recipe finalized)
- **ROOT FIX for repeated T5 failures = move to the :9225 dedicated browser**
  (/home/itadmin/persistent-browser-2, same endpoints /eval /mouse /type /press
  /screenshot). Cron jobs only drive :9223 — dealer stopped drifting instantly.
  All future BC build work: use :9225, leave :9223 to the crons. NOTE: :9225
  /screenshot = GET, same base64 `screenshot` key; execute_code scripts that
  wrap eval calls MUST pass explicit `timeout=` to terminal() — a bare curl -m
  inside execute_code once hung the whole 300s script despite the browser
  being healthy.
- **DOUBLE-FILTER TRAP (cost one publish cycle)**: putting BOTH the original
  (12727115) and superseded (12735608) filter numbers in **Add Custom Parts**
  bills BOTH → line came in at $222.62 (+$7.67 over). The both-numbers
  belt-and-suspenders rule applies to *price* overrides in Modify System
  Parts (L87/L86/V8 pattern), NOT to Add Custom Parts where each row is an
  actual billed line. Diesel siblings use Add Custom Parts (oil 19370138 ×7
  @8.44 + ONE filter 12727115 @7.67); keep the superseded number ONLY in
  Modify System Parts for suppression/price matching.
- **Delete an Add Custom Parts row**: row overflow btn (icon-overflow,
  x≈1352, 16px wide — real /mouse misses it; use full
  pointerdown/mousedown/pointerup/mouseup/click dispatch on the
  `button.ant-dropdown-trigger` at that y) → Delete menu item → bottom Save
  while row expanded → verify the POST /overrides req payload customParts
  list.
- **Add Custom Parts field order is same as MSP**: Identifier → Job → part#
  → price. Row placeholders: 'Add identifiers from here' / 'Add jobs from
  here'; walk up from placeholder text to the [class*=control] ancestor and
  dispatch mousedown to open. Price input id `customerPayUnitPrice_undefined`,
  qty `partQuantity_undefined_quantity` — match to the row by y-band (±12px).
- **Included-service list row → Edit service**: the ⋮ is also a
  `button.ant-dropdown-trigger` (icon-overflow x≈1212) needing the full
  5-event dispatch; then click the 'Edit service' menuitem.
- **Included Services page search: type into the input with
  placeholder 'Search...' (x≈1232, expandableSearch), NEVER 'Search here...'
  (x≈253 = GLOBAL search → bounces to RO pages).** Native value-setter +
  input event works; results filter live (8 hits for the oil-line family).
- **Parts list page (parts/inventory/part) search quirks at BC**: the 'Type
  Here' box autocomple LI 'Create \"<num>\"' with no real option = BC does NOT
  stock that number (e.g. 12708183 unstocked). Table body does NOT reliably
  refilter from synthetic Enter — use the autocomplete dropdown or partial-
  number typing; trade prices are readable straight from the list row text
  (Part|Desc|Brand|...|Cost|List|Trade order).
- **T6 rep vehicle**: BC stocked 2024 Silverado 2500HD LTZ VIN
  2GC1YPEY0R1118216 (stock C6326) = vPIC-confirmed 6.6L Diesel **L5P**; the
  2025 2500HD LT 2GC1KNE74S1228298 is the 6.6L **GAS L8T** (good negative-
  verify vehicle for the fuel-type split). vPIC one-liner:
  `curl 'https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/<VIN>?format=json'`
  → DisplacementL + FuelTypePrimary + EngineModel.

### T6 RESUME POINT (session end 2026-07-21 AM — pick up exactly here)
- **T5 = DONE, penny-verified $214.95 exact** (QO#0930 Tahoe LM2, after
  deleting the duplicate superseded-filter row from Add Custom Parts).
  5 of 7 tiers live. Remaining: T6 ($249.95) + T7 Mobil 1 ($279.95) + final
  7-tier reconciliation table to Slack thread C0BGTDMP9U2.
- **T6 sibling audit confirmed** (`6a557c0d0da08c418d8c10fe`): Default Labor =
  Define Here, CP Fixed placeholder $160.88; **Parts = Pull From Opcode, ZERO
  override rows** — full build needed (parts + scope + labor back-solve).
- Next concrete steps: (1) create throwaway quote on the L5P rep VIN
  2GC1YPEY0R1118216 (2024 2500HD LTZ, stock C6326), odo 174,000 → 172.50K;
  (2) capture the L5P feed parts + trade prices via the serviceMenu/Choose
  Parts XHR — **BC does NOT stock filter 12708183** (only Create placeholder
  in parts search); identify the actual stocked L5P filter (12735608/12816256
  supersession family surfaced in partial search — confirm off the quote feed,
  don't guess); (3) sibling Overrides→Parts: Add Custom Parts rows (oil +
  ONE filter, diesel pattern like T5) + suppression in Modify System Parts;
  (4) back-solve labor = 249.95 − trade parts, reprice via #labor-price;
  (5) menu row scoped 6.6L + Fuel Type Diesel; (6) publish + penny-verify on
  the L5P VIN + **negative-verify on the 6.6L GAS L8T VIN 2GC1KNE74S1228298**
  (must fall to V8-gas row $129.95, not T6).
- T7 after: Mobil 1 sibling `6a557c29aa85e61624e3c481`, menu row must be
  BOTTOM row (steal Corvette/Camaro from V8-gas row) — verify at quote time.
- All work on :9225 (dedicated browser, dealer 1251) — do NOT return to :9223.

### Ground-truth verification via override API (beats trusting toasts)
- Opcode detail: GET `/api/service-module/u/opcode/<OPCODE>/v2` (no override
  data in it — `pricingRules`/`laborRateConfigs` empty).
- Override rows: GET/POST `/api/service-module/u/opcode/<entityId>/override/LABOR`
  — fires when the Overrides tab loads / row saves. Capture via XHR hook +
  SPA pushState away-and-back (hooks survive pushState, die on hard nav).
  Saved row JSON = parameters[] (MAKE/MODEL/YEAR/TRIM) + override.laborHours +
  override.laborPriceDetails (laborRateType FLAT, flatPrice).
- Quote pricing ground truth: POST `.../service/calculate` response →
  `serviceMenuItems[]` has laborHours, originalLaborPrice, pricingDetail
  (pricePerHour), parts[] w/ partNumber, quantity, unitPrice,
  partResolveType, originalRequestedPartNumber. **XHR capture caps at 200K
  chars — the calculate response overflows; slice-extract with regex, don't
  json.loads the whole capture.**
- Parts price books: POST `/api/parts/proxy/u/lookup/inventory` response has
  listPrice + tradePrice per part.
- Quote menu panel: toggling a service checkbox updates the tier card price
  LIVE ($30 → $233.73) — quick way to isolate one line's contribution
  without adding to quote.

- Dealer switch to BC: picker leaf innerText = **"Blackstone Chevrolet
  Cadillac"** (no ampersand), verify `currentActiveDealerId === "1251"`.
- The in-page opcode search (15-header set, per tekion-opcode-api skill) works
  fine at BC as a DIRECT fetch — no XHR hook needed. searchText "GMLOF",
  searchFields OPCODE+DESCRIPTION → 7 hits.
- Part prices are IN the search hits (`parts[].customerPayUnitPrice`) — no
  per-opcode detail fetch needed for price audits (patched into
  tekion-opcode-api skill).
- BC menu opcodes = same TEK convention as Toyota stores (212 SERVICE_MENU
  ACTIVE, verified 2026-07-02) — the menu shells exist.
