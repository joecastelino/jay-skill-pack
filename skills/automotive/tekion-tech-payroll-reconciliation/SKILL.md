---
name: tekion-tech-payroll-reconciliation
description: >
  Reconcile a store manager's semi-monthly tech payroll sheet (attendance +
  assigned/flagged billed hours per tech) against Tekion's Tech Performance
  data via API. Use when Joe says "the tech performance report doesn't match
  what <manager> turned in on payroll" or sends a payroll PDF/spreadsheet to
  audit. Verified BC (1251) Aug 16-31 2026 — caught a $1,700 payroll error.
triggers:
  - payroll doesn't match tech performance
  - audit payroll sheet against tekion
  - tech hours payroll reconciliation
  - ruben payroll billed hours
---

# Tekion Tech Payroll Reconciliation

## What this solves
Manager submits payroll with per-tech Attendance Hours + Billed (Flagged) Hours.
Joe asks why it doesn't match the Tech Performance report. Reconcile every row
against Tekion's own numbers and identify WHICH rows are wrong and WHY.

**COMPARISON BASIS (Joe ruled 2026-09-04): audit the sheet's "billed" column
against Tekion's ASSIGNED BILLED HOURS (`assignedBillingTimeInSeconds`), NOT
Flagged Hours.** Use Flagged/Attendance only as diagnostics to identify which
column the manager mis-grabbed.

**Real outcome (BC 2026-09-04, Aug 16-31, Ruben):** on the Assigned Billed
basis, 22/27 techs matched exactly. 5 wrong rows, two failure modes, both
column-grab errors reading the report screen:
- 3 rows (Fernandez 937, Escobar 783, Chavira 5619): sheet value = the tech's
  Tekion **Attendance Hours** cell.
- 2 rows (Garcia 1129, Arreola 5602): sheet value = the **Flagged Hours** cell
  (adjacent column; flagged ≠ assigned-billed for those techs).
Net ~$1,716 overpaid / ~$98 underpaid. Not a Tekion bug — no post-pull flag
movement or adjustments.

## Step 1 — Parse the payroll sheet
- `pdftotext` often missing; use `pypdf` (`PdfReader(...).pages[i].extract_text()`).
- Rows key on **employee number** embedded in the name ("Fernandez, 937",
  "nathaniel 5635"). Pay = Billed × Pay Rate for flat-rate; Quick Lube techs
  get max(billed pay, attendance guarantee).
- Save work in a REAL dir (`/home/itadmin/bc-payroll-check/`), not `~`.

## Step 2 — Get authenticated internal-API headers
Saved header captures live at `/tmp/tekion_tech_headers_<dealer>.json` but the
`tekion-api-token` EXPIRES (401 "Login user session is expired").
**Fix without recapturing:** splice fresh values from a live browser's
localStorage into the old header dict:

```python
# :9223 may be owned by the nightly Caliber cron — check pgrep tekion-scraper;
# if busy, use :9225 (second authenticated browser). eval param is "js" NOT "expression".
js = 'JSON.stringify({tok:localStorage.getItem("t_token"),uid:localStorage.getItem("__user_id"),role:localStorage.getItem("currentActiveRoleId"),site:localStorage.getItem("currentActiveSiteId")})'
# POST http://127.0.0.1:9225/eval  {"js": js}
hdr["tekion-api-token"] = tok; hdr["userid"] = hdr["original-userid"] = uid
hdr["roleid"] = role; hdr["tek-siteid"] = site   # verify dealerid matches target store
```
Replayed from plain urllib these headers work for all service-module reporting
endpoints. Verify `localStorage.currentActiveDealerId` == target dealer first.
NOTE: in-page `fetch()` of `/api/service-module/u/reporting/technician` returns
500 (axios interceptor adds auth a bare fetch can't) — use the urllib replay.

## Step 3 — Pull Tekion's numbers (two endpoints)
Dates: Pacific tz, epoch ms, `payDay BTW [start00:00, end23:59:59.999]`.

**A. Whole-store summary (all techs, one call):**
`POST /api/service-module/u/reporting/technician`
```json
{"reportName":"TECH_PERFORMANCE_REPORT","reportGroup":"TECH_PERFORMANCE",
 "metrics":[],"pageInfo":{"start":0,"rows":300},
 "filters":[{"field":"payDay","operator":"BTW","values":[LO,HI]}]}
```
→ `data.lineItems[]` per techId (techId "-1" = TOTAL). Key fields (seconds):
`attendanceTimeInSeconds`, `assignedBillingTimeInSeconds`, `flagTimeInSeconds`,
`clockTimeInSeconds`, `unAppliedTimeInSeconds`. Dollars in CENTS.

**B. Per-tech flag ledger (for drilling a mismatch):**
`POST /api/service-module/u/reporting/technician/breakdown` with
`reportName:"FLAG_TIME_REPORT", reportGroup:"FLAG_REPORT"` + techId IN filter.
Rows carry `roNo, opcode, flagTime (entry timestamp), payDay, flagTimeInSeconds,
flagHourType (AUTO_ADDED), flagHourAdjustmentReason`.

**C. Map techId→employee number:** public OpenAPI `/openapi/v4.0.0/users`
cursor-paginated (`meta.nextFetchKey`, NEVER pageNumber);
`employeeDetails.employeeDisplayNumber`; `completeNames` is a LIST of
{nameType,value} — take DISPLAY_NAME.

## Step 4 — Diagnostic sequence for each mismatched row (in order)
0. **Compare against `assignedBillingTimeInSeconds` (Assigned Billed)** — that
   is the payroll basis Joe uses. Then test the mismatch value against the
   OTHER columns:
1. **Sheet value == Tekion Attendance Hours?** → column transposition by the
   manager (THE most common cause; hit 3/5 at BC). Attendance sits adjacent to
   Flagged on the report screen.
1b. **Sheet value == Tekion Flagged Hours?** → manager grabbed the Flagged
   column instead of Assigned Billed (2/5 at BC: Garcia 1129, Arreola 5602).
   Flagged vs Assigned Billed differ whenever flags booked to a tech other
   than the assigned tech.
2. **Flags entered after the manager pulled** (`flagTime >= pull date` with
   in-period payDay) → late/backdated flagging, numbers moved after payroll.
3. **Negative entries / flagHourAdjustmentReason** → post-payroll corrections
   (warranty re-books, RO reopens).
4. **payDay vs flagTime basis** — sum both ways; if the sheet matches the
   flag-entry-date basis, the manager used a different date column.
5. If hours vanished entirely (in no bucket) → flags deleted/reassigned; look
   for offsetting POSITIVE deltas on other techs (reassignment recipient).

## Step 5 — Report to Joe
- Per-tech table: sheet att/billed vs Tekion att/flagged with deltas, flag rows >±2h.
- Quantify $ impact per wrong row (hours delta × pay rate; mind QL guarantee logic).
- State explicitly whether it's a sheet error vs Tekion data movement — Joe
  will ask which.

## Pitfalls
- **Manager's attendance column ≠ Tekion attendance** — it comes from the
  timeclock/payroll system. At BC several techs (Francher 5627, Nathaniel 5635,
  Salcido 1001) show ZERO Tekion attendance (don't punch Tekion's clock), so
  never audit the attendance side against Tekion; only the BILLED side.
- Employee numbers on the sheet can be stale/nicknamed — BC "espinoza 5586" is
  Tekion emp **5580** (Diego Espinoza-Montes). Match by hours if emp# misses.
- Tekion rows not on the sheet (small hours, negative rows like Segovia -3.2)
  explain part of any TOTAL-row gap — reconcile per-tech, not by totals.
- Sheet year typos happen ("aug 16-31 2025" meaning 2026) — infer from context.

## Related
- `tekion-standard-reports-performance` (the report + its API, column defs)
- `tekion-flag-vs-actual-hours-report`, `tekion-tech-clock-time-by-opcode`
- `build_tech_perf_package.py` in ~/tekion-reports (single-tech deep package)
