# BC 172.50K Oil-Tier Build State — 2026-07-15 (supersedes 2026-07-14)

## Scoreboard: 4 of 7 tiers LIVE (published + penny-verified)

| # | Tier | Target | Status |
|---|------|--------|--------|
| 1 | 6.2L L87 (2019–2026) | $204.95 | ✅ live, year-scoped 2019+ |
| 2 | 4 & 6 cyl | $119.95 | ✅ live (Malibu under-target = correct ceiling behavior) |
| 3 | V8 gas | $129.95 | ✅ live |
| 4 | L86 6.2L (2007–2018) | $179.95 | ✅ live 2026-07-15 |
| 5 | 3.0L Duramax | $214.95 | ⬜ NEXT — sibling service exists |
| 6 | 6.6L HD diesel | $249.95 | ⬜ sibling exists |
| 7 | Mobil 1 (all Corvettes + all Camaros) | $279.95 | ⬜ sibling exists; must be BOTTOM row |

## Joe's scoping rulings (LOCKED)
- **Chevrolet-only for ALL tiers for now.** Make cell is single-select; Joe: "1 for now, lets make sure chevrolet works, then I'll send you everyone else." GMC/Cadillac/Buick added later per Joe. Those makes billing factory pricing interim = expected.
- **6.2L year split**: 2019-and-newer = L87 $204.95; 2018-and-older = L86 $179.95.
- Row order: broad rows high, carve-outs (6.2L rows, Mobil 1) BELOW — bottom-most applicable row wins.

## Tier 4 (L86) as-built detail
- Scope row: Make=Chevrolet, All models, Years 2007–2018, trim filter Engine Litre=6.2L → "Filters (1)", 136 trims, "All trims (including future trims)" radio kept.
- Parts override keyed to BOTH 12731742 AND 12816256 (filter supersession); oil 19432337 @ $5.11 trade.
- Fixed labor back-solved: $130.88. Penny proof: 2018 Silverado 1500 LTZ 6.2L → 130.88 + 8×5.11 + 8.19 = **$179.95 exact**, all parts OVERRIDE (trade).
- No 2018-older 6.2L in live inventory → used a decoded valid-checksum 2018 Silverado LTZ 6.2L VIN for the throwaway verify quote.
- Overlap verified: 2018 6.2L matches V8-gas row AND L86 row → bottom-most (L86) wins correctly; L87 2019+ row untouched.

## Pitfalls hit this session (in addition to SKILL.md list)
1. **Heavy DOM walks 500 the :9223 eval on the trim modal** (thousands of nodes) — use light targeted queries (querySelector by facet label), not full-tree walks.
2. **MSP blank add-row can sit BELOW the 720px viewport fold** — silent no-op clicks; scrollIntoView the add-row before typing.
3. **Hard navigation wipes unsaved part rows** (never-saved MSP entries vanish) — save each part row before any nav; rebuild if a hard nav happened mid-entry.
4. Model dropdown: verify the checkbox-list actually took ("Select" still showing = didn't take); re-open and check items individually.
5. Session restart can land on TL (1092) — re-pin 1251 and verify localStorage.currentActiveDealerId before every mutation (cron hijack rule still applies 7–9 PM).

## Next actions (resume here)
1. Build tier 5 (3.0L Duramax $214.95): Chevrolet-only, trim filter Engine Litre=3.0L diesel; same Tier-A recipe (parts override w/ trade prices incl. superseded filter #s, back-solve flat labor from ceiling-quart vehicle, menu row suppress factory line + check Duramax sibling, save-per-row, publish, penny-verify on real/decoded quote).
2. Then tier 6 (6.6L HD $249.95), tier 7 (Mobil 1 Corvette+Camaro $279.95 — insert as BOTTOM row).
3. Ping BC menu thread slack:C0BGTDMP9U2:1783876336.294119 as each goes live; deliver full 7-tier reconciliation table at the end.
4. Await Joe's make list for GMC/Cadillac/Buick expansion — do NOT add other makes until he sends them.
