---
name: tekion-flag-vs-actual-hours-report
description: >
  Build a "closed ROs where tech FLAGGED hours were below ACTUAL clocked time"
  report (unpaid flat-rate tech time) for any Tekion store, per-tech per-RO grain.
  Uses two internal endpoints discovered 2026-07-30 - /ro/v1/{id} carries per-tech
  flag entries (flagTimesWithPayDay) and clockDetails/fetch carries per-tech actual
  punches. Also documents the repair-orders:search pageNumber-IGNORED pagination
  trap and its closedTime-bisection fix. Verified SV (826) Jul 1-15 2026.
triggers:
  - flagged hours below actual
  - flag vs actual time report
  - unpaid tech time
  - techs not flagged for clocked time
  - flag hours audit
---

# Tekion — Flagged Hours Below Actual Clocked Time (per RO, per tech)

## When to use
Joe asks "pull closed ROs where tech flagged hours were below actual time" — i.e.
flat-rate techs who clocked wrench time on an RO but were never flagged (= never
paid) for it. Different from the opcode-grain over-clock report
(tekion-clock-time-by-opcode): this is per-RO per-TECH, joining two RO-level
internal endpoints. Zero OpenAPI quota except the closed-RO list.

## The two data sources (KEY DISCOVERY 2026-07-30)

Both need captured axios headers (see Session refresh below). Base
`https://app.tekioncloud.com`.

1. **FLAG hours per tech per op**: `GET /api/service-module/u/ro/v1/{roId}` —
   note the **/v1/** segment; the plain `/ro/{roId}` variant does NOT carry flags
   (only laborTimeInSeconds/billingTimeInSeconds). Path:
   `data.jobs[].operations[].techIdWithBillingTimes[]` each has `techId` +
   `flagTimesWithPayDay[]` with `flagTimeInSeconds`, `flagTime` (epoch ms),
   `flagHourType` (MANUALLY_ADDED/...), `flaggedByUserId`,
   `flagHourAdjustmentReason`. Also useful: `referenceHoursForFlagging`
   (ACTUAL_HOURS), `limitFlagHrToBillHr`, `equateFlagHrToBillHr`,
   `jobs[].autoFlagTechnicians`.
2. **ACTUAL clocked per tech**: `POST /api/service-module/u/ro/clockDetails/fetch?allUsers=true`
   body `{"roId": <docId>, "jobIds": [<all job ids>]}` → `data[]` one doc per
   tech-per-op with `userId`, `clockedTimeInSeconds`, `clockTimes[]` punch detail
   (inTime/outTime/roundedOffTimeInSeconds/adjustmentReason). Skip `deleted:true`.
   Found by arming an XHR hook on :9223 and opening the RO kebab → "RO Clocked
   Time" (also fires when opening "Manage Technician" on a job).

Flag-hunting endpoint guesses (`/flagDetails/fetch`, `/flagTime/...`) all 404 —
the flags ONLY live inside `/ro/v1/{id}`.

## Method

1. **Refresh session + headers** (captures die ~2h): run
   `/home/itadmin/tekion-auth/login.py --force`, then
   `/home/itadmin/tekion-reports/capture_svd_actualtime_sv.py` (any internal
   capture works — headers are session-wide). Strip `:`-pseudo headers, save to
   `/tmp/sv_headers_fresh.json`. Probe with one request; 401 = stale.
2. **Closed-RO list via OpenAPI** `repair-orders:search` with closedTime
   GTE/LTE + status IN [CLOSED, INVOICED]. **CRITICAL PAGINATION TRAP** (burned
   3 iterations): `pageInfo.pageNumber` is **IGNORED** — every page returns the
   SAME first 20 rows (pageSize also capped at 20 despite asking 100), and
   `meta.nextPageToken` DRIFTS OUTSIDE the closedTime filter (following it walks
   into other months; SV 15-day window "found" 5,000+ ROs). FIX = **closedTime
   bisection**: recursively split [lo,hi] until `meta.totalCount <= len(results)`,
   concat, dedupe on documentId. ~60 calls for 286 ROs, fast.
   `documentId` is the fan-out key (top-level `id` is null on this endpoint).
3. **Fan out** both internal calls per RO (0.25s pace, 429 backoff), aggregate
   per techId: `flag_s` = sum of all flagTimeInSeconds across ops, `actual_s` =
   sum of clockedTimeInSeconds. Keep rows where `actual - flag >= 180s` (0.05h
   noise floor).
4. **Resolve tech names in bulk**:
   `POST /api/rosearchservice/u/visibility-dashboard/lookup/resolve-by-id`
   body `{"lookupByIds":[{"lookUpAsset":"TECH_ID","ids":[...]}]}` (same headers).
5. Rank by gap; present per-tech summary table + per-RO detail with opcodes.

## Turnkey script
`/home/itadmin/tekion-reports/sv_flag_below_actual_h1jul.py` → writes
`data/sv-flag-below-actual-h1jul.json`. Adapt: date window (Pacific tz!), store =
swap OpenAPI `dealer_id` + re-capture headers at that store (internal headers
carry dealerId/tek-siteId — switch dealer in the capture browser first, or swap
`dealerId` and `tek-siteId: -1_<id>` headers like deferred_services_90d.py).
286 ROs ≈ 5 min; run background with notify_on_complete.

## Reading the result (SV Jul 1-15 2026 reference)
286 closed ROs → 22 tech-RO rows, 15.8 hrs unpaid gap. Montgomery Hirsch 5.44
(one RO, 371607 MECDIAG, 4.41 clocked / 0 flagged = a third of the whole gap);
several techs with actual>0 and flag=0.00 = never flagged at all. Frame for Joe:
concentrated in a few techs/ROs, not store-wide; diag time is the usual leak.
Fix path for open ROs = flag on the RO tech-time modal; for CLOSED ROs =
Reports → Flag Hours Report → Add Adjustment (KB0014998, no reopen needed).
On the open-RO tech-time modal: Flagged hrs + Flag date + Reason + Flag Type are
all required per tech row; manual entry switches that row off auto-flag for the
RO (expected). Caveats: (1) flag ≠ bill can BLOCK invoice close if the store's
pre-invoice rule treats it as error (warning = fine) — check Service Settings if
close goes red; (2) per-tech Labor Cost $0.00 in the modal = wage type missing
on the employee record → flagged hours post at ZERO cost to RO/GL even though
payroll pays off the report; employee-record fix, NEVER touch without Joe's
explicit OK. Verified good example: SV RO 372190 line G — flagged 4.15 to match
actual clocked, op labor cost went $0 → $230.70 once fixed.

## Single-tech deep-dive variant (Joe follow-up, verified Tualla SV 2026-07-31)
When Joe narrows to ONE tech (\"can we focus on Loreto Tualla?\"), don't reuse the\nclosed-RO list — pull ALL ROs the tech clocked on in the window regardless of\nstatus (open/HOLD included), then join flags. Two extra insights this surfaces:\n- **closedTime-window LEAK**: the store-wide scan keys on ROs *closed* in the\n  window, so an RO worked in-window but closed AFTER it is invisible (Tualla\n  372028 + 371877 were misses the store scan never showed). For per-tech audits,\n  key on clock-punch date, not closedTime.\n- **Open/HOLD ROs with clock-but-no-flag** are catchable BEFORE close (flag on\n  the RO tech-time modal — cheap fix) vs closed ones needing Flag Hours Report\n  adjustments. Split the output by status.\nAlso report the REVERSE rows (flag > clock, e.g. a REC flag with no punch) —\nJoe wants both directions. Pattern read that landed well: a tech who flags\nusually flags to the hundredth; gaps = ROs where the tech-time modal was never\nopened at all (behavioral, not systemic).\n\n## Pitfalls
- Flag data is **only** in `/ro/v1/{id}` — plain `/ro/{id}` and OpenAPI
  operations have `actualTimeInSeconds: null` and no flag fields at all.
- A tech can appear in clockDetails but have NO techIdWithBillingTimes entry
  (clocked on a job they were never assigned/flagged on) — union the tech sets,
  missing flag entry = 0.
- Times in SECONDS; OpenAPI $ in CENTS.
- 401 on replay = stale capture; login.py can report ALIVE while storage state
  is dead — use `--force` then re-capture.
- Don't trust the first "0 results" run: check `meta.totalCount` vs rows
  returned before believing the window is empty.
