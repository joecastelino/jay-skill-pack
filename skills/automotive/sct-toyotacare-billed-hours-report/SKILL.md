---
name: sct-toyotacare-billed-hours-report
description: Pull the ToyotaCare (TAC) billed-hours number from Tekion's Advisor Performance report (Reports module) for SCT or any store, using Joe's saved TAC/ToyotaCare filter — and roll it out to the other 6 AMG stores. Use when Joe asks for ToyotaCare / TAC billed hours, or is building his monthly SCT fixed-ops sheet ("first number, Toyota Care").
triggers:
  - toyotacare billed hours
  - tac billed hours report
  - pull the toyota care number
  - first number for my monthly sheet
  - tac bill hrs for sct
  - advisor performance report toyotacare filter
  - roll out tac hours to all stores
  - toyota care hours by store
---

# SCT ToyotaCare (TAC) Billed-Hours Report

## 🚨 UI PATH DEAD (2026-09-02) — API IS NOW THE ONLY SOURCE
Tekion replaced the report with **"Advisor Performance Report(3)"**
(visibility-dashboard engine). The new report has **NO Opcode filter** (17 filter
fields, none opcode) and **Joe's saved groups are GONE** — the saved-group
dropdown shows only "Default Filter"; "TAC/TOYOTACARE REVISED 3/1/25" no longer
exists. The entire "Joe's saved filter" browser method below is HISTORICAL.
Pull TAC billed hours via the OpenAPI path (`tl_tac_api.py` works for any Toyota
store via dealer key). Details of the new report:
`tekion-standard-reports-performance`.

Joe's monthly fixed-ops sheet build starts with the **ToyotaCare billed-hours** number, pulled from Tekion's **Advisor Performance** standard report using a saved filter he built. This skill pulls it reliably and replicates it across all 7 stores.

## Where the report lives
- Module: **Reports** (sidebar "R"), NOT Report Builder (RB).
- URL: `/core/reports/service/advisor-performance` (Service category).
- Advisor Performance columns: RO Count · Labor Sale · Labor Gross · Parts Sale · Parts Gross · **Bill Hrs** · ELR($) · Hrs/RO · Total Gross · Total Sales · GP%. Has a TOTAL row at top. Updates every 4–6h.

## Joe's saved filter (the key)
Filter funnel icon (top-left of toolbar, `.root_filterTrigger_icon` ~x101,y165) opens an ant-popover. At the top is a **"Default Filter" group-selector** dropdown (tekion-select ~x214,y238). Select the saved group **"TAC/TOYOTACARE REVISED 3/1/25"**. It contains:
- **Pay Type Status** = In → Closed
- **Pay Type Closed Date** = Between → **BLANK** (set the date FIRST, per period)
- **Opcode** = In → **TAC80, TAC75, TAC70, TAC65, TAC60, TAC55, TAC50, TAC45, TAC40, TAC35, TAC30, TAC25, TAC20, TAC15**
- **Pay Type** = Not In → Warranty

Set the Pay Type Closed Date range (e.g. June 2026 = 6/1/26–6/30/26), Apply, then read the **Bill Hrs** TOTAL. That's the ToyotaCare billed-hours number. (Joe's June 2026 SCT figure = 283.7.)

## PITFALL: the date-range calendar fights automation
The dual-pane calendar in the Reports module is flaky under :9223:
- Typed dates get **rejected by React** (native value-setter reverts to prior value).
- Outer header arrows jump by **YEAR**, not month; the two calendars move independently.
- **Vision-derived arrow/day coordinates are in SCREENSHOT-SCALED space (~1226px wide), NOT DOM-viewport space** — clicking them lands on the wrong target. Find day-cell coords by DOM cell text/title in viewport space instead.

Don't grind the calendar UI for long (Joe's rule: don't spend hours scripting around a tool limit when a proven path exists).

## RELIABLE ALTERNATIVE (recommended for cross-store rollout): OpenAPI
Dodge the calendar entirely and compute the number from RO data:
1. `POST /repair-orders:search` (OpenAPI, `tekion_client.get_token`, dealer id per store) with a **closedTime window** for the period + status IN CLOSED,INVOICED.
2. Filter jobs/operations to the **TAC15..TAC80** opcode set (exclude Warranty pay type).
3. Sum labor **billed hours** across matching operations. (Any $ field is in **CENTS — /100** — though billed hours are hours, not cents.)
4. Cross-check against Joe's browser number (his 283.7 for SCT June) to validate before rolling out.

## Cross-store rollout

### TL (Toyota of Lancaster, 1092) — DONE, API-sourced (2026-09-01)
Script `/home/itadmin/tekion-reports/tl_tac_api.py <start> <end> tl` +
renderer `render_tl_tac.py`. Dodges the Advisor-Performance calendar entirely.
- **TL's TAC family = `TAC` plus `TAC5,10,15,...,80`** (16 ACTIVE opcodes,
  `INDIVIDUAL_SERVICE`). Note TL has **TAC5 and TAC10**, which SCT's saved
  filter (TAC15–TAC80) does NOT include — do not reuse SCT's opcode list at TL.
  Enumerate per store via `POST /api/service-module/u/opcode/search
  {"searchText":"TAC","pageInfo":{"start":0,"rows":100}}`.
- TL Aug 2026 reference: **116 ops / 54.35 billed hrs / $7,105.25 labor sale /
  $5,866.94 gross / ELR $130.73**, 14 advisors, 4,046 closed ROs scanned.
- ⚠️ TL's Report Builder copy (*"SCP OP Code-ToyotaCare (TXM)"*,
  `6585c492ee94990ac065f290`) is **NOT a TAC report** — it filters
  `RO_OPERATION_OPCODE STARTS_WITH "TEK"` and its index runs 5–9 days stale
  (understated Aug by ~15%). Never quote it as ToyotaCare. Full rebuild
  method: skill `tekion-rebuild-broken-report-builder-report`.
- **ELR is the number Joe follows up asking for** — always report
  `labor sale / billed hours` alongside hours, and offer the YTD trend. TAC ELR
  runs low by design (TAC10 ≈ $150/hr vs TAC35 ≈ $91/hr drags the blend).
- Runtime: a month ≈ 4 min, YTD ≈ 25–30 min → **background + notify_on_complete**,
  never foreground (180s limit).

After SCT is confirmed, pull the same TAC billed-hours for the other 6 stores (BC, BT, SV, TL, AR, VC) for the SAME period. Note: **TAC opcodes are Toyota-specific** — only Toyota stores (BT, TL, and SCT) will have them; non-Toyota stores (BC, SV, AR, VC) won't return ToyotaCare data. Confirm with Joe which stores he wants before assuming.

### TL (Toyota of Lancaster, 1092) — verified 2026-09-01
TL has **16 active TAC opcodes**: `TAC` (bare) + `TAC5, TAC10, TAC15, TAC20,
TAC25, TAC30, TAC35, TAC40, TAC45, TAC50, TAC55, TAC60, TAC65, TAC70, TAC75`.
Enumerate per store, don't copy SCT's list:
`POST /api/service-module/u/opcode/search {"searchText":"TAC","pageInfo":{"start":0,"rows":100},"filters":[],"sort":[]}`
→ `data.hits[]` with `opcode`/`status`/`description`. Note the split in naming:
TAC5–TAC30 are "TOYOTA AUTO CARE", TAC35+ are "TOYOTA CARE PLUS" — if Joe asks
for one and not the other, that's the cut line. **The bare `TAC` opcode is real
and active (14 ops at TL in Aug) — a `TAC\d+` regex silently drops it.**

### ⚠️ TL's Report Builder report is NOT a TAC report — don't use it as the source
TL has `SCP OP Code-ToyotaCare (TXM)` (id `6585c492ee94990ac065f290`,
dataSource REPAIR_ORDER). Despite the name it filters
`RO_OPERATION_OPCODE STARTS_WITH "TEK"` — the TEK **menu** family, not TAC — plus
`RO_OPERATION_CATEGORY EQUALS "Vehicle"`, which now matches **zero** rows (live
ops come back as category `MAINTENANCE`). It is also served off a stale ES index
(as of 2026-09-01: max ingestion 8/24, latest closed RO 8/22 — 9 days missing).
Two different reports wearing one name; **confirm TAC-vs-TEK with Joe before
quoting a number.** Full triage in skill `tekion-report-builder-scraper`.

### Live API replacement (preferred over both the calendar UI and Report Builder)
`/home/itadmin/tekion-reports/tl_tac_api.py START END [dealer_key]` — closedTime
bisection + OPCODE-tag prefilter + operations fan-out; reports ops / bill hours /
labor sale / gross per TAC opcode with advisor id and pay type per line. Zero
index lag. Runs longer than the 180s foreground cap for a full month → launch
with `background=true, notify_on_complete=true`. Works for any Toyota store via
the dealer key (`st`, `bt`, `tl`).

## Verification one-liner
Report back per store: `STORE | period | TAC Bill Hrs = N.N | source (browser Advisor Perf / OpenAPI)`.
