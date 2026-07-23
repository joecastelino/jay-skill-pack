---
name: sct-toyotacare-billed-hours-report
description: Pull the ToyotaCare (TAC) billed-hours number from Tekion's Advisor Performance report (Reports module) for SCT or any store, using Joe's saved TAC/ToyotaCare filter — and roll it out to the other 6 AMG stores. Use when Joe asks for ToyotaCare / TAC billed hours, or is building his monthly SCT fixed-ops sheet ("first number, Toyota Care").
---

# SCT ToyotaCare (TAC) Billed-Hours Report

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
After SCT is confirmed, pull the same TAC billed-hours for the other 6 stores (BC, BT, SV, TL, AR, VC) for the SAME period. Note: **TAC opcodes are Toyota-specific** — only Toyota stores (BT, TL, and SCT) will have them; non-Toyota stores (BC, SV, AR, VC) won't return ToyotaCare data. Confirm with Joe which stores he wants before assuming.

## Verification one-liner
Report back per store: `STORE | period | TAC Bill Hrs = N.N | source (browser Advisor Perf / OpenAPI)`.
