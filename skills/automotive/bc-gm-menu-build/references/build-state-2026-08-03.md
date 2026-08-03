# BC GM Menu Build — State as of 2026-08-03 (supersedes build-state-2026-07-20.md)

## T6 HD Diesel $249.95 — ✅ DONE, PENNY-VERIFIED, PUBLISHED
- Sibling: `6a557c0d0da08c418d8c10fe` ("Engine Oil & Filter Remove and Replace - 6.6L HD Diesel")
- Scope: Chevrolet / All models / All years + trim filters 6.6L + Diesel (1,314 Duramax trims)
- Parts (rows keyed): oil 88862469 ×3 + filter keyed as ORIGINAL 12731742 (supersedes → 12816256 at quote time; live-feed parts total = $126.48 at TRADE)
- Labor: back-solved to **$123.47** flat CUSTOMER_PAY (NOT the earlier 149.90 placeholder — real feed parts were 126.48 not 133.00). Saved via #labor-price, survived remount.
- Menu row: published on 172.50K menu (row via makeId_5/trim_5), factory oil suppressed via MSS, T6 sibling attached.
- Penny-verify PASS: L5P VIN 2GC1YPEY0R1118216 (2024 Silverado 2500HD, quote 6a6f4bb6f4611b401618bbf9 QO#0946) → 123.47 + 126.48 = **$249.95 EXACT**.
- Negative-verify PASS: gas L8T VIN 2GC1KNE74S1228298 NOT captured by T6 — falls to V8-gas line.

## ⚠️ OPEN FINDING — Tier B (V8-gas) gap, pre-existing, NOT caused by T6
Gas 6.6L L8T bills **$175.45**, not the $129.95 target:
1. Feed requests oil **19432357 ×8** — Tier B override covers **19432337** only; per-part matching means the override never fires.
2. Filter bills 9.93 vs the 8.19 override (untraced).
Fix candidate = add a 19432357 override row to the V8-gas sibling + trace filter delta. AWAITING JOE'S CALL (never-guess rule) — do not touch Tier B pricing without his go.

## REMAINING WORK
1. **T7 Mobil 1 $279.95** — sibling `6a557c29aa85e61624e3c481` (untouched): capture Corvette/Camaro live feed, parts + labor back-solve (target − TRADE parts), menu row at BOTTOM of rows, publish, verify it DOES capture Corvette/Camaro and nothing else wrongly.
2. **Final 7-tier reconciliation table** to Joe in the BC thread (include the L8T $175.45 gap).

## NEW PITFALLS LEARNED THIS BURST (172.50K menu edit page + edit-service page, dealer 1251)
- **Menu-row make/MSS dropdowns: synthetic events do NOT commit picks.** "picked" can report while header stays `Select|Select...`. Use REAL mouse clicks via the :9223 /mouse endpoint on the exact option element. Wrong picks DO land silently (got Buick on the make select; got "AC Condenser Fan" on the MSS service select) — ALWAYS read back the committed row text after every pick and re-open/re-pick if wrong.
- **MSS suppression on the menu row requires the modal Apply** before the row save counts; then top-level Save/Publish.
- Save PUT can return **500 validation** — inspect the payload; retry after fixing row state (don't blind-retry).
- Carousel arrow clicks can bounce the browser to the Quotes LIST page mid-flow — re-open the quote and re-navigate the rail; verify "Package OpCode: TEK172500PSM" in DOM before trusting the panel.
- Right panel resets to low intervals after package reload — re-click 172.50K and confirm opcode before reading tier detail.
- Edit-service page still remounts spontaneously; re-verify labor/parts after any remount (123.47 verified persisted).

## Reference figures
- Trade prices: 85614334 filter trade $41.14 / list 58.77 / cost 30.18 (from /parts/inventory/part page — direct lookup/inventory API 500s).
- Live-feed T6 parts total at TRADE = $126.48 (quote is ground truth over hand-summed row prices).
- Tier targets: T6 diesel 249.95 · T7 Mobil1 279.95 · V8-gas baseline 129.95 (currently billing 175.45 — see gap above).
