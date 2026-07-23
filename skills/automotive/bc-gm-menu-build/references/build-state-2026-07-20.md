# BC 172.50K Oil-Tier Build State — 2026-07-20 PM (supersedes AM version)

## Scoreboard: 5 of 7 verified

| # | Tier | Target | Status |
|---|------|--------|--------|
| 1 | 6.2L L87 (2019–2026) | $204.95 | ✅ live |
| 2 | 4 & 6 cyl | $119.95 | ✅ live (Malibu $114.02 ceiling = correct) |
| 3 | V8 gas | $129.95 | ✅ live |
| 4 | L86 6.2L (2007–2018) | $179.95 | ✅ live |
| 5 | 3.0L Duramax | $214.95 | ✅ **PENNY-VERIFIED $214.95 EXACT 2026-07-20 PM** (QO#0930 fresh line) |
| 6 | 6.6L HD diesel (L5P) | $249.95 | 🟡 sibling exists (id `6a557c0d0da08c418d8c10fe`, labor Define Here $160.88 placeholder, Parts=Pull From Opcode, NO override rows) — parts capture + build pending |
| 7 | Mobil 1 (all Corvettes + all Camaros) | $279.95 | ⬜ sibling `6a557c29aa85e61624e3c481` exists; must be BOTTOM row |

## Tier 5 FINAL as-built (verified 2026-07-20 PM)
- Service `6a557bf14aa6485eea036e9e` TEK05052501 "- 3.0L Duramax Diesel".
- **Add Custom Parts** (NOT Modify System Parts for the billed lines):
  oil **19370138 qty 7 @ $8.44** + filter **12727115 qty 1 @ $7.67** — ONE
  filter only. The superseded 12735608 was initially added too and BOTH
  billed → $222.62 (+$7.67). Deleted 12735608 from Add Custom Parts (row ⋮
  icon-overflow x≈1352 → Delete → Save while expanded); it remains in
  Modify System Parts for suppression. **Rule: both-filter-numbers
  belt-and-suspenders = Modify System Parts price overrides ONLY; Add
  Custom Parts rows each BILL.**
- Labor flat **$147.20 effective** (147.20 + 59.08 + 7.67 = 214.95 — quote
  showed OIL $59.08 total, FILTER $7.67; Choose Parts modal confirms).
- Scope: Chevrolet / All models / All years / trim filters **3.0L + Diesel**
  (198 trims). Trim modal shows only "Diesel" checked until Show More
  expands Engine Liter (3.0L hides in the collapsed facet).
- Menu row published; fresh line on QO#0930 (`6a5e505c2e9f16469c9c3009`,
  2023 Tahoe LM2) = **$214.95 EXACT**.

## Root fix that unblocked everything: :9225 dedicated browser
All build work moved OFF the cron-shared :9223 to **:9225**
(/home/itadmin/persistent-browser-2). Same endpoints (/eval /mouse /type
/press /screenshot GET). Dealer drift = gone. Keep this split permanently:
Jay live edits on :9225 during BC build, crons own :9223.

## Resume point — Tier 6 (6.6L HD L5P, $249.95)
1. Rep vehicles (vPIC-confirmed): **DIESEL L5P = 2024 Silverado 2500HD LTZ
   VIN 2GC1YPEY0R1118216 (stock C6326)**; GAS L8T = 2025 2500HD LT
   2GC1KNE74S1228298 (use as negative-verify for the fuel-type split).
2. Prior recon: oil **88862469 (gallon) qty 3 @ $30.62 trade** from quote
   `6a5e3981a065544761947885`. **HD filter part # still NOT captured** —
   BC does NOT stock 12708183 (parts search offers only Create). Capture
   the filter from a fresh L5P quote's Choose Parts / serviceMenu XHR
   (feed shows requested + superseded numbers + trade).
   Was mid-Create-Quote when session ended: Create Quote form open,
   VIN input = "Search VIN #" placeholder (~419,486).
3. Build = T5 recipe clone: Overrides→Parts Define Here, scope Chevrolet /
   All / All / trim filters 6.6L + Diesel, Add Custom Parts (oil + ONE
   filter at trade), back-solve labor = 249.95 − parts, menu row 6 with MSS
   factory suppress, Save-per-row, Publish (PUT 200), penny-verify fresh
   line, negative-verify the L8T gas truck still hits V8-gas $129.95.
4. Tier 7 Mobil 1: BOTTOM row, verify steals Corvette/Camaro from V8-gas.
5. Final 7-tier reconciliation table → slack:C0BGTDMP9U2:1783876336.294119.
6. Chevrolet-only until Joe sends other makes.

## Pitfalls confirmed/added 2026-07-20 PM
- Add Custom Parts row delete: overflow ⋮ needs full 5-event dispatch
  (pointerdown→click) on `button.ant-dropdown-trigger`; /mouse at coords
  misses the 16px target.
- Included Services list: page search = 'Search...' input x≈1232
  (expandableSearch); 'Search here...' x≈253 = GLOBAL trap. Row Edit
  service also via 5-event dispatch on its icon-overflow trigger.
- Parts inventory page table does NOT refilter on synthetic Enter; read
  trade prices from row text or use autocomplete; 'Create "<num>"' with no
  real option = part not stocked at BC.
- execute_code wrapping bridge curls MUST pass explicit timeout= to
  terminal(); one bare call hung the full 300s with a healthy browser.
- override/LABOR vs override/PARTS separate endpoints; publish proof = PUT
  setup?publish=true 200 capture; pre-publish quote lines never reprice —
  always add a fresh package line after publish.
