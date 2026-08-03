---
name: amg-wip-monthly-column-fill
description: Fill a month column of Joe's AMG WIP workbook (the monthly fixed-ops tracker, rows=metrics cols=months, one tab per store) with Tekion data — hours sold by pay type, vehicle attendance, ToyotaCare hours, workshop hours, WIP $, ELRs. Includes the quota-free dealer-detail DB method for operation-level hours. Use when Joe says he needs to "finish" or "work on" the AMG WIP sheet for a month.
---

# AMG WIP Monthly Column Fill (Tekion → workbook)

## What this is
Joe's **AMG WIP.xlsx** = the monthly fixed-ops metric tracker (DISTINCT from the payroll-vs-RTH workbook in amg-wip-payroll-vs-rth-analysis). 8 tabs: Stevens Creek Toyota, Stevens Creek Volkswagen, Toyota of Fresno (=BT service), Blackstone Body Shop (=BT body), Volkswagen of Clovis, Fresno GM (=BC), Toyota of Lancaster, Alfa Romeo of San Jose. Rows = metrics, one column per month (header row 1 = datetime dated the **26th**, but Joe confirmed the window is the **CALENDAR month**, 1st→EOM).

- Live copy on Joe's Drive: file id `1esCOBSklptjeR3We9dKG6rcaDEfii6aJ` (an **.xlsx in Drive, NOT a native Sheet** — Sheets API can't write it; download via Drive `files/{id}?alt=media` with Bearer token, or convert to native Sheet for API writes). Local mirror: `/home/itadmin/amg-wip/AMG-WIP-live.xlsx`.
- Jay's Google access: symlink `~/.hermes/profiles/jay/google_token.json → /home/itadmin/.hermes/google_token.json` (Walter's base token, Joe's account, Sheets read/write + drive.readonly). Verify with google-workspace `setup.py --check`.

## SCT tab row map (col A labels; other tabs similar)
r4-10 Hours Sold: CUSTOMER / TXM / TOYOTA CARE / PREPAIRD MAINTENANCE / WARRANTY / PDI / INTERNAL · r13-14 VEHICLE ATTENDANCE: TOYOTA / OTHERS · r18-21 WORKSHOP: TOTAL AVAIL HOURS / TOTAL PROD HOURS / UNAPPLIED · r25-30 LABOR RATES (manual, carry forward) · r32 WIP $ · r35-45 ELR by make×paytype · r49-55 ACCESSORY ELRs · r60-67 TXM COUNT/SALE/COST/GROSS + parts block.

**TELL for an unfilled month:** the new column is an exact COPY of the prior month (every cell identical). Diff col N vs N-1 before assuming it's done.

## Data methods (validated 2026-08-03, SCT July)

### 1. Vehicle Attendance (RO count) — live OpenAPI, search-only, quota-cheap
`POST /repair-orders:search` filters: `closedTime BTW [monthStartPT_ms, monthEndPT_ms]` + `status IN CLOSED,INVOICED`, pageSize 200, paginate via `meta.nextPageToken`. NO fan-out → survives even when DEALER_QUOTA is tight (search itself kept working while /jobs fan-out 429'd). Script: `/home/itadmin/tekion-reports/wip_sct_july_attendance.py`. SCT July = 5,199.

**Make split (Joe's canonical filter — screenshot confirmed 2026-08-03):** Joe's Advisor Performance filter group = **Pay Type Closed Date / Between / 1st–EOM** + **Make / In / Toyota, Scion** (multi-select "In", NOT is-like; Name + Pay Type Status rows left unset). TOYOTA row = that count; OTHERS row = Make **Not In** Toyota/Scion. His clock = PAY TYPE CLOSED DATE (per-invoice), mine = RO closedTime — expect ~0.3% definitional drift (SCT July: his 5,060 vs my DB-derived ~5,073); Joe's report number is ground truth for the sheet, mine is the cross-check. In the DB: `payload->'vehicle'->>'make'` matched case-insensitively against `/toyota|scion/` (make casing is dirty: both "toyota" and "Toyota" appear). Script: `/home/itadmin/dealer-detail/apps/web/wip_makes.cjs`. PITFALL: the live OpenAPI `repair-orders:search` results do NOT inline vehicle — `vehicle` is a link stub, so make-split live requires per-RO fan-out; use the DB. For non-Toyota stores swap the make list per store brand (VW stores: Volkswagen; BC: Chevrolet/Cadillac? — CONFIRM with Joe per store before first use).

### 2. Hours by pay type / opcode buckets — dealer-detail DB (ZERO Tekion quota) ⭐
**Key discovery:** the dealer-detail Supabase DB (`/home/itadmin/dealer-detail/apps/web`, `RawRepairOrder.payload`) embeds the FULL RO snapshot: `payload.jobs[] = {job:{payType,subPayType,type}, operations:[{operation:{opcode, labor:{billDuration, laborAllowanceDuration, saleAmount, costAmount}}, parts:[...]}]}` plus `payload.vehicle.make`. So operation-level **billed hours = labor.billDuration / 3600** for a whole month with NO API fan-out. Query with a `.cjs` node script via Prisma `$queryRawUnsafe` (no psql installed): join `Store` on abbreviation (SCT/SCVW/BST/BC/TOL/VWC/ARSJ), window on `closeDate` (UTC: month start/end + 07:00 for PT). Working scripts: `apps/web/wip_sct_july_sanity.cjs`, `wip_probe.cjs`.

**Coverage caveat:** DB lags live — SCT July had 4,644 of 5,199 (89%). Report hour numbers as "slightly low" or backfill first (`npm run sync:store -- SCT <days>`, quota-gated).

**Backfill PITFALL (burned 2026-08-03):** `npm run sync:store` needs `.env` loaded — bare invocation prints "Missing required environment variables: DATABASE_URL..." yet still EXITS 0 and ingests NOTHING. Always wrap like the nightly cron: `cd apps/web && set -a && . ./.env && set +a && npm run sync:store -- SCT 35`. Verify ingestion afterward by re-counting the month's ROs (fetchedAt max should be fresh), never trust exit code alone.

### 3. Bucket mapping (OPEN QUESTION — never guess)
RO data exposes only THREE payTypes: CUSTOMER_PAY / WARRANTY / INTERNAL. The sheet splits 7 ways. Observed: TAC15–TAC80 opcodes under CP = TOYOTA CARE row (matches sct-toyotacare-billed-hours-report skill, "not Warranty" rule); TSC* opcodes under CP ≈ prepaid maintenance candidate; TXM* opcodes appear under WARRANTY. **PDI/TXM/PPM bucket definitions must come from Joe's saved Advisor Performance filters — ASK, don't infer.** (Asked 2026-08-03, answer pending — record it here when given.)

### 4. Workshop hours (avail/prod/unapplied)
Tekion Tech Performance report (see tekion-standard-reports-performance skill), flag-date window = calendar month.

### 5. Labor Rates rows
Manual/rare — carry forward prior month unless Joe says changed.

## Sanity-check protocol (Joe asked for this explicitly)
Before filling a whole column: present 3-5 computed cells vs the prior month's values, state coverage caveats, and have Joe verify 1-2 (CP Bill Hrs total + RO Count from his Advisor Performance report for the same window) before running the rest. Joe fills the sheet by hand from numbers posted in Slack — deliver in row order.

## Pitfalls
- OpenAPI RO search results have NO `id` field — use `documentId`; jobs live at `data.jobs`, operations at `data.roOperations` (fan-out path only).
- `get_token(cfg)` requires the cfg arg (`sys.path.insert(0,"/home/itadmin/tekion-api")`).
- 2-4 AM PT = VI pull window; DEALER_QUOTA 429s on fan-out likely. Search-only endpoints still worked.
- Labor $ in CENTS (/100); billDuration in SECONDS (/3600).
- Header dates (26th) are cosmetic — window is calendar month (Joe, 2026-08-03).
