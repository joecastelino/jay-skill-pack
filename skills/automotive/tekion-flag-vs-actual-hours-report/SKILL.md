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

3. **★ BEST SOURCE — the flag LEDGER in ONE call** (found 2026-08-28, BC):
   `POST /api/service-module/u/reporting/technician/breakdown` — same body shape as
   the Tech Performance call (`reportName: FLAG_TIME_REPORT`, `reportGroup:
   FLAG_REPORT`, `filters: [{field:"payDay",operator:"BTW",values:[lo,hi]},
   {field:"techId",operator:"IN",values:[uuid]}]`, `pageInfo:{start:0,rows:1000}`).
   Returns **one lineItem per flag entry** already joined to the RO:
   `roId, roNo, jobNumber, operationId, opcode, payType, make, payDay, flagTime,
   flagTimeInSeconds, flagHourType, flagHourAdjustmentReason, flaggedByUserId,
   assignedBillingTimeInSeconds, operationBillingTimeInSeconds,
   referenceHoursForFlagging, wagePerHour, laborSale/Cost/GrossAmount, jobConcern`.
   This **replaces the whole `/ro/v1/{id}` fan-out** for flag data — 1 call per tech
   instead of ~140 RO calls (~3 min), and it sums EXACTLY to the Tech Performance
   `flagTimeInSeconds`. Still use `/ro/v1/{id}` when you need per-tech
   `billingTimeInSeconds` on the op, `autoFlagTechnicians`, or who-else-is-on-the-job.

Old note (superseded): "flags ONLY live inside `/ro/v1/{id}`" — false. Sibling
guesses `/reporting/technician/detail` and `/drilldown` DO 404; `/breakdown` is real.

## Method

1. **Refresh session + headers** (captures die ~2h): run
   `/home/itadmin/tekion-auth/login.py --force`, then
   `/home/itadmin/tekion-reports/capture_svd_actualtime_sv.py` (any internal
   capture works — headers are session-wide). Strip `:`-pseudo headers, save to
   `/tmp/sv_headers_fresh.json`. Probe with one request; 401 = stale.
2. **Get the RO population — DON'T use OpenAPI if you can avoid it.**
   **★ PREFERRED (2026-08-28): group TECH_CLOCK by `roId`, not `roNo`.** The
   visibility-dashboard `generate-summary-report` TECH_CLOCK datasource (see skill
   tekion-clock-time-by-opcode for the request shape) accepts `groups[0].field =
   "roId"`, and **that value IS the RO documentId** — the exact key `/ro/v1/{id}`
   and `clockDetails/fetch` need. Zero OpenAPI calls, zero quota, no pagination.
   Group by `roNo` only when you want human-readable output; grab both if needed.
   Other useful group fields: `opcode`, `inTimeDate`, `techId`, `payType`.

   **BURNED AT BC 2026-08-28:** the documented OpenAPI path below returned
   `{"data":{"results":[]},"meta":{"totalCount":0}}` for BC RO numbers that
   demonstrably exist — `repair-orders:search` with `documentNumber IN [...]` found
   NOTHING at dealer 1251, and the response shape is `data.results` (a dict), not
   `data` (a list), so naive `for d in r["data"]` crashes with
   `'str' object has no attribute 'get'`. Don't build on it.

   *(Legacy path, only if you truly need closed-RO-list semantics)* Closed-RO list
   via OpenAPI `repair-orders:search` with closedTime GTE/LTE + status IN
   [CLOSED, INVOICED]. **PAGINATION TRAP**: `pageInfo.pageNumber` is **IGNORED** —
   every page returns the SAME first 20 rows (pageSize capped at 20 despite asking
   100), and `meta.nextPageToken` DRIFTS OUTSIDE the closedTime filter. FIX =
   **closedTime bisection**: recursively split [lo,hi] until
   `meta.totalCount <= len(results)`, concat, dedupe on documentId.
3. **Fan out** both internal calls per RO (0.25s pace, 429 backoff), aggregate
   per techId: `flag_s` = sum of all flagTimeInSeconds across ops, `actual_s` =
   sum of clockedTimeInSeconds. Keep rows where `actual - flag >= 180s` (0.05h
   noise floor).
4. **Resolve tech names in bulk**:
   `POST /api/rosearchservice/u/visibility-dashboard/lookup/resolve-by-id`
   body `{"lookupByIds":[{"lookUpAsset":"TECH_ID","ids":[...]}]}` (same headers).
5. Rank by gap; present per-tech summary table + per-RO detail with opcodes.

## Turnkey scripts
**Any-store header capture (built 2026-08-28, use this — the `_sv` ones are
hardcoded to dealer 826):**
`/home/itadmin/tekion-reports/capture_tech_report_headers.py <dealerId> "<Dealer Name RX>"`
→ `/tmp/tekion_tech_headers_<dealer>.json` (headers + `__post_body` + sample resp).
Headless Playwright w/ storage_state; skips the dealer-switch if
`localStorage.currentActiveDealerId` already matches; navigates /core/reports →
Service → Tech Performance (direct goto does NOT fire the data request). ~60s.
Sibling `capture_tech_drilldown.py <dealerId> "<Dealer RX>" "<Tech Name RX>"` clicks
a tech row and dumps every `/api/` POST — that's how `/breakdown` was found. Note
the BC report URL is `/core/reports/service/tech-performance-v2`.

**The two-tech audit (BC 2026-08-28):**
`/home/itadmin/tekion-reports/bc_flag_audit_two_techs.py` → writes
`data/bc-flag-audit-192-5576.json`; recon output `data/bc-flag-recon-192-5576.json`.
Edit the `TECHS` dict + window constants. Uses TECH_CLOCK-by-roId (no OpenAPI).

**Older SV store-wide version:**
`/home/itadmin/tekion-reports/sv_flag_below_actual_h1jul.py` →
`data/sv-flag-below-actual-h1jul.json`. Adapt: date window (Pacific tz!), store =
re-capture headers at that store (internal headers carry dealerId/tek-siteId —
switch dealer in the capture browser first, or swap `dealerId` and
`tek-siteId: -1_<id>` headers like deferred_services_90d.py).
286 ROs ≈ 5 min; run background with notify_on_complete.

**Note (2026-08-28):** `login.py` (no `--force`) reported ALIVE with 41163 min left
and the capture worked first try — don't reflexively `--force`, probe first.

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
When Joe narrows to ONE tech (\"can we focus on Loreto Tualla?\"), don't reuse the\nclosed-RO list — pull ALL ROs the tech clocked on in the window regardless of\nstatus (open/HOLD included), then join flags. Two extra insights this surfaces:\n- **closedTime-window LEAK**: the store-wide scan keys on ROs *closed* in the\n  window, so an RO worked in-window but closed AFTER it is invisible (Tualla\n  372028 + 371877 were misses the store scan never showed). For per-tech audits,\n  key on clock-punch date, not closedTime.\n- **Open/HOLD ROs with clock-but-no-flag** are catchable BEFORE close (flag on\n  the RO tech-time modal — cheap fix) vs closed ones needing Flag Hours Report\n  adjustments. Split the output by status.\nAlso report the REVERSE rows (flag > clock, e.g. a REC flag with no punch) —\nJoe wants both directions. Pattern read that landed well: a tech who flags\nusually flags to the hundredth; gaps = ROs where the tech-time modal was never\nopened at all (behavioral, not systemic).\n\n## "The flagged hours look suspect / don't match" ticket (BC 2026-08-28)
Joe's framing is usually **"tech flagged hours are suspect of not matching, compare
to Tech Performance (beta)"** with 1-2 **employee numbers**, not names.

**Step 0 — resolve employee number → tech UUID.** OpenAPI
`GET /openapi/v4.0.0/users` (pageSize 100) →
`employeeDetails.employeeDisplayNumber` + `userNameDetails.completeNames[DISPLAY_NAME]`
+ `userRoleDetails.primaryRole.persona`. **PAGINATION GOTCHA: the next-page param is
`nextFetchKey`, NOT `fetchKey`** — passing `fetchKey` (or `pageToken`/`fetch_key`)
is silently ignored and you re-fetch page 1 forever (I "pulled 800 users" that
deduped to 100 and missed both targets). 375 users at BC = 4 pages.
`/openapi/v4.0.0/employees` = 404, doesn't exist.
Note `employeeId` is inconsistent (`1251_192` vs a UUID) — key on
`employeeDisplayNumber`.

**Step 1 — reproduce the report number first.** Pull
`/reporting/technician` FLAG_TIME_REPORT for the window with a `techId` filter, then
sum the `/breakdown` ledger independently. At BC both tied EXACTLY (63.50 and 56.10).
Say that out loud: *the report is not miscounting*. This is the Joe STEP-ZERO rule —
prove the symptom reproduces before diagnosing.

**Step 2 — the real answer is almost always the payDay-vs-punch-date mismatch.**
`flagHourType: AUTO_ADDED` + `referenceHoursForFlagging: BILL_HOURS` +
`job.autoFlagTechnicians: true` means **Flagged Hours is BILLED hours by design and
never equals the clock.** Flags land on `payDay` = the date flagged (invoice/close),
NOT the day wrenched. So any Tech Performance date range mixes flags for work
clocked weeks earlier with punches that will flag later. Present it as:
- **clocked-but-never-flagged** (unpaid tech time) — the actionable leak
- **flagged-above-clock** (billed > wrench, normal on warranty/flat-rate)
- **flags with no in-window punch** (the windowing artifact itself)
A tech who turns ROs same-week (Barks: 62.33 clk / 63.50 flag, max ±1.87/RO) looks
clean; a tech sitting on long open ROs (Tafolla: 26 hrs punched with ZERO flag,
incl. one RO at 17.46) looks broken — same store, same settings, different WIP age.

**Step 3 — always surface the manual adjustments.** Filter
`flagHourType != "AUTO_ADDED"`. `MANUALLY_ADDED` with a **negative**
`flagTimeInSeconds` = someone clawed hours back by hand (BC: two −1.00 entries on
8/18). Negative AUTO_ADDED rows are billing reversals. Joe wants both directions
reported; negatives are the ones that start conversations.

## Pitfalls
- **`/ro/v1/{id}` response shape**: RO header fields (`roNo`, `status`,
  `closedTime`, `primaryAdvisorId`, `documentNumber`) are nested one level down in
  `data.ro`, NOT on `data` — `data` itself only holds
  `jobs/recommendations/jobParts/clockTimes/invoices/id/ro`. Reading
  `data.get("documentNumber")` silently yields `None` and your report prints `RO ?`
  for every row (cost me a full re-run).
- **`/reporting/technician` accepts ANY `reportName` string.** I probed 6 invented
  names (FLAG_TIME_DETAIL_REPORT, FLAG_HOURS_REPORT, TECH_FLAG_DETAIL...) and every
  one returned 200 with the SAME 2 rows. Unknown reportName is ignored, not
  rejected — "it worked!" proves nothing. Verify the row SHAPE changed.
  Same trap: `/api/service-module/u/settings` with unknown `requestOptions` returns
  `{}` rather than erroring; don't infer "setting absent" from it.
- A tech can appear in clockDetails but have NO techIdWithBillingTimes entry
  (clocked on a job they were never assigned/flagged on) — union the tech sets,
  missing flag entry = 0. Conversely a tech row can read `bill 0.00 / flag 0.00`
  on an op that IS billed (BC RO 100739 job4 CONCERN billed 4.00W) — that's the
  signature of "he clocked it, someone else's hours carried the job."
- Times in SECONDS; OpenAPI $ in CENTS.
- **Reconcile totals BOTH ways before reporting.** A tech's net (clocked − flagged)
  can look tiny while hiding two large offsetting errors — Tafolla netted only
  −7.45 hrs but that was 37.5 under + 30.1 over. Always print under/over/zero-flag
  buckets separately, never just the net.
- Don't run a wide "chase the missing 0.60 hr" scan before checking arithmetic: I
  fanned 225 extra ROs looking for stray flags and found 0 — the 55.50 vs 56.10 gap
  was just entries the narrower discovery window had excluded, which `/breakdown`
  returns for free. Use `/breakdown` FIRST and the gap never appears.
- 401 on replay = stale capture; login.py can report ALIVE while storage state
  is dead — use `--force` then re-capture.
- Don't trust the first "0 results" run: check `meta.totalCount` vs rows
  returned before believing the window is empty.
