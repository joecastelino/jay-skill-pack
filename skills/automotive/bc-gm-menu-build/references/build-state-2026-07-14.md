# BC menu build state — updated 2026-07-14 ~10:15 PM

## Joe's make ruling (Slack 2026-07-14 PM)
**Chevrolet-only for now** — "1 for now, lets make sure chevrolet works, then
I'll send you everyone else." Build ALL remaining tiers Chevrolet-only; the
other makes (GMC/Cadillac/Buick) come as a backfill pass later when Joe sends
the rest. Yukon/GMC falling to factory pricing is EXPECTED interim behavior.

## Tier scoreboard (7 tiers, dealer 1251, menu edit 65530c2cd0e3ef410082bb2c)
| # | Tier | Target | Status |
|---|---|---|---|
| 1 | 6.2L L87 | $204.95 | ✅ LIVE, published, penny-verified; row YEAR-SCOPED 2019–2026 |
| 2 | 4 & 6 cyl | $119.95 | ✅ LIVE, verified (Malibu $114.02 = ceiling behavior) |
| 3 | V8 gas | $129.95 | ✅ LIVE, penny-verified $129.95 (Silverado 5.3L) |
| 4 | L86 6.2L ≤2018 | $179.95 | ✅ LIVE 2026-07-14 PM, published, penny-verified $179.95 EXACT |
| 5 | 3.0L Duramax | $214.95 | NEXT (sibling 6a557bf14aa6485eea036e9e, placeholder 140.88) |
| 6 | 6.6L HD diesel | $249.95 | NOT started (sibling 6a557c0d0da08c418d8c10fe, placeholder 160.88) |
| 7 | Mobil 1 Corvette/Camaro | $279.95 | NOT started (sibling 6a557c29aa85e61624e3c481); row must sit BOTTOM |

## L86 build record (2026-07-14 PM session)
- Sibling `6a557bd64aa6485eea036e6e` Overrides→Parts row id
  `6a570d4fe8f4995ab2ec893e`: Chevrolet / ALL_MODELS / years 2018→2007 /
  ENGINE_LITRE 6.2L (136 trims). modifiedSourceParts server-verified:
  19432337 qty 8 @5.11, 12731742 qty 1 @8.19 (ORIGINAL), 12816256 qty 1
  @8.19 (superseded).
- Labor: placeholder $130.88 = 179.95 − 49.07 back-solve. NO reprice needed
  (Add-Service placeholders were chosen as back-solves — check before repricing).
- Menu row 4 on 172.50K: Chevrolet / All models / 2007–2018 / 6.2L filter;
  MSS factory oil line all tiers UNCHECKED; Add Services L86 sibling all
  tiers CHECKED. Saved (PUT publish=false 200) + PUBLISHED (publish=true 200).
- Penny-verify: 2018 Silverado 1500 LTZ 6.2L, **synthetic VIN
  3GCUKSEJ6JG481376** (no ≤2018 6.2L Chevy in bc.json inventory — VIN built
  by swapping engine code J + series S into a real 2018 VIN + recomputing
  check digit; Tekion decoded it fine), QO `6a570985914c9d039a04ba0d`,
  odo 174,000. serviceMenu capture: FLAT 130.88 + 8×5.11 + 8.19 OVERRIDE
  = **$179.95 EXACT**.
- Row-overlap note: 2018 6.2L matches BOTH row 3 (V8 gas) and row 4 (L86) —
  bottom-most wins gave L86 correctly. 2019+ 6.2L only matches rows 1/3 —
  L87 (more specific scope row) still wins, unchanged.

## Menu row order now (bottom-most wins)
1. 6.2L L87 (Silverado 1500, 6.2L, 2019–2026)
2. 4&6 cyl (Chevrolet/All/All, Cyl {4,6})
3. V8 gas (Chevrolet/All/All, Cyl 8 + Gas)
4. L86 (Chevrolet/All/2007–2018, 6.2L)
Mobil 1 must go BELOW row 3 (steal Corvette/Camaro from V8-gas); Duramax/HD
diesel rows are non-overlapping with gas rows (fuel/litre) but keep them below
anyway.

## Remaining work
1. Tier 5 Duramax $214.95: quote a 3.0L LM2/LZ0 (bc.json or synthetic VIN),
   capture feed parts (oil qty ~7, ACDelco diesel filter, DEXOS D), trade
   prices, parts override on sibling ...6e9e, back-solve labor, menu row
   (Chevrolet/All/All years? litre 3.0L — check trim facet), suppress+add,
   publish, penny-verify.
2. Tier 6 HD diesel $249.95: 6.6L + FUEL_TYPE Diesel (solves L8T collision).
3. Tier 7 Mobil 1 $279.95: ALL Corvettes + ALL Camaros, every engine; row at
   BOTTOM; verify it steals from V8-gas row on a Corvette quote.
4. Final 7-tier reconciliation table to Joe; per-tier Slack pings as they go live.
5. LATER (Joe to send): backfill make rows (GMC/Cadillac/Buick) on all 7 tiers.

## Key artifacts
- L86 verify quote: QO `6a570985914c9d039a04ba0d` (2018 Silverado LTZ 6.2L,
  synthetic VIN 3GCUKSEJ6JG481376, odo 174,000)
- Tier B verify quote: QO `6a5667d3548c3a1defd78dc9` (2019 Silverado RST 5.3L)
- Yukon negative-verify: QO `6a56a57dd284f235bbf46e01` (2016 GMC, factory ✓)
- Menu/SM dumps: /tmp/bc_menu_full.json, /tmp/bc_l86_sm.json
- Live BC inventory for rep VINs: /home/itadmin/the-goods/data/bc.json
