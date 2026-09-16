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
  - tech closed report higher than tech flagged report
  - flagged hours should be more than closed
  - why is the closed report higher than the flagged report
  - tech performance report two different numbers same period
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

## Variant: ONE RO "looks short" + the tech's period total doesn't match (BC RO 102964, 2026-09-16)
A tech (via manager) says "this RO pays 1.40 but I show 0.20, and my tech total
shows 80-something when you showed me 111." Run this BEFORE concluding a defect.

**1. The Tech Flag Hours modal lists each flag ENTRY as its own row and the
hours boxes on each row are the DELTA, not the running total.** The tech reads
the BOTTOM (most recent) row and calls it his pay. RO 102964:

| Flag date | Actual hrs | Assigned Labor hrs | Assigned Bill hrs | Assigned Labor $ |
|---|---|---|---|---|
| 09/11 | 1.20 | 1.20 | 1.20 | $274.80 |
| 09/14 | 0.20 | 0.20 | 0.20 | $61.72 |
| | | | **1.40** | **$336.52** |

The RO job line reads `1.40 / 0.00 / 1.40 hrs` (bill / actual / flagged) and the
modal totals read Bill 1.40 / Flagged 1.40 / Labor Cost $72.80. Nothing is
short — 0.20 is literally the last entry row.

**2. That PDI "1.20 + small top-up" pattern is NORMAL, not a defect.** The PDI
op's billed hours get raised at RO close, so Tekion posts the DIFFERENCE as a
second AUTO_ADDED flag instead of replacing the first. Hit 5 PDI ROs in one week
at BC (102956 +0.30, 102959 +0.30, 102767 +0.20, 102964 +0.20, 102395 +0.00).

**3. THE RO DOCUMENT DOES NOT CARRY ASSIGNED BILLED HOURS.** The per-technician
billing field on op rows read **0.00 on all 103 op rows** of that RO. Real
assigned-billed hours live ONLY in the flag ledger / Tech Flag Hours modal. So a
manager pulling a screen that shows 0.00 or 0.20 is reading that field or the
last entry row — never the total.

**4. The "two different numbers" resolution (assigned billed vs clocked vs
period).** Do NOT guess — sum every metric over candidate windows and see which
one lands on the disputed figure. BC emp 5576 (Victor, $52/hr):

| Period | Assigned Billed = Flagged | Clocked | Attendance |
|---|---|---|---|
| Aug 1–15 | 98.40 | 67.31 | 76.41 |
| **Aug 16–31** | **113.70** | **79.18** | 101.79 |
| Sep 1–15 | **86.10** | 55.37 | 74.47 |

Only 113.70 is near the "111" he was shown = the completed prior pay period.
The "80-something" is either the CURRENT period (86.10) or the CLOCKED column of
the SAME Aug 16–31 window (79.18). Then ASK Joe which screen + date range the
disputed number came from — the answer changes what the manager should say.

**5. STORE CONFIG that makes or breaks this: the tech-level flag reference.**
At BC it is set to `BILL_HOURS`, so assigned-billed EQUALS flagged on EVERY
entry (verified across 103 Sept + 81 Aug 16–31 + 56 Aug 1–15 entries). At a store
where it isn't, the two diverge and "he's paid on assigned billed" matters.
Check it before claiming the numbers agree.

**6. Reconciliation sweep.** Walk every RO touching the tech's clock/flag data
and compare the RO documents against the reporting index; same-day flag indexing
lag shows up as a small delta (2.00 hrs / 2 ROs at BC) — say so explicitly and
don't dress it up as a defect.

**7. The one thing worth escalating:** count MANUALLY keyed flag entries in the
period (BC Sept 1–15: 14.10 of 86.10 hrs, incl. a −2.00 reversal, keyed by 5
different people — Yer Vang, Serena Quezada, Houa Moua, Juan Ramirez, Humberto
Dominguez). Manual flag in/out is what makes a tech's day-to-day total jump, and
it's the only line a manager should actually validate.

**Deliverable:** rendered per-RO flag ledger (page 2 = RO#, flag date, flag type,
who flagged it) via `render_tech_perf.py` →
`/home/itadmin/tekion-reports/out/tech_perf_<dealer>-<emp>-<start>_<end>.{png,pdf}`.
Non-SCT stores use the text WORDMARK (no dealer logo — see REPORT LOGO TRAP).

## Variant: "the tech's CLOSED report is HIGHER than his FLAGGED report" (BC emp 5576, 2026-09-16)
Joe's instinct is right that flagged should be >= closed — but ONLY inside one RO set.
The Tech Performance screen has a **date-basis choice**, and the two exports Joe compared
were the SAME report over the SAME Sep 1–15 window, just scoped differently:

| Export | Flagged | Assigned Bill | Clock | Attendance |
|---|---|---|---|---|
| scoped by **RO CLOSE date** | **112.20** | 112.20 | 48.66 | 74.47 |
| scoped by **FLAG date** (screen default; = Flag Hours Report) | **86.10** | 86.10 | 55.36 | 74.47 |

**Why close-date scope > flag-date scope:** close-date scope pulls EVERY flag sitting on
the ROs that closed in the window — including flags entered back in a PRIOR pay period —
and simultaneously drops flags on ROs that were flagged in-window but have NOT closed yet.
The difference reconciles to the penny:

```
 86.10 (flag-date basis = the real pay-period number)
+30.80  August-flagged hours swept in on 4 ROs that CLOSED Sep 1–15
       101268 +11.00 (flagged Aug 27)   99905 +10.30 (Aug 3–14)
       100101  +7.50 (Aug 3–13)         101435  +2.00 (Aug 26)
 -4.70  September flags on 4 ROs still OPEN (Invoiced / In Progress / PDI / Ready-for-Invoice)
       102705 -1.50  102962 -1.20  102759 -1.00  102994 -1.00
= 112.20 ✓
```

**At BC this can never be a config discrepancy:** `referenceHoursForFlagging = BILL_HOURS`,
so within any fixed RO set Flagged EXACTLY equals Assigned Billed (86.10/86.10 and
112.20/112.20 above). The ONLY variable is which ROs are in scope. Say that explicitly —
it's what kills the "the report is broken / underpaying my tech" theory.

**The 30.80 was already PAID** — 17.80 h in Aug 1–15 (ROs 99905, 100101) and 13.00 h in
Aug 16–31 (ROs 101268, 101435). It rode in only because those ROs finally closed in Sept.

**Do:** run payroll off the FLAG-DATE view. **Do NOT** add the two figures or treat the gap
as missing hours. The one real risk to flag: if anyone ever pays off the close-date view,
the 30.80 gets paid a SECOND time.

**Deliverable Joe asks for:** the RO-level list behind the sweep — one row per flag ENTRY
(RO#, job, opcode, flag date, prior pay period, RO close date, hours) as CSV+email. BC file:
`/home/itadmin/tekion-reports/out/bc5576-swept-august-flags-2026-09-15.csv`.

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
