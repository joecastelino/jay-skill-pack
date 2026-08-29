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

## FASTEST PATH — the flag LEDGER endpoint (discovered BC 2026-08-28)

Before fanning out over ROs, try this. It replaces steps 2-4 for flag data and is
~100x cheaper (2 calls instead of 300):

**`POST /api/service-module/u/reporting/technician/breakdown`** — same body as the
Tech Performance aggregate (`reportName: FLAG_TIME_REPORT`, `reportGroup:
FLAG_REPORT`, filter `payDay BTW [lo,hi]`, optional `techId IN [...]`,
`pageInfo.rows` up to 1000). Returns **one row per individual flag entry** with:
`roId, roNo, jobNumber, operationId, opcode, payType, make, payDay, flagTime,
flagTimeInSeconds, flagHourType (AUTO_ADDED/MANUALLY_ADDED),
flagHourAdjustmentReason, flaggedByUserId, referenceHoursForFlagging,
assignedBillingTimeInSeconds, operationBillingTimeInSeconds, wagePerHour,
laborSaleAmount/CostAmount/GrossAmount, jobConcern`.
Sum of `flagTimeInSeconds` ties EXACTLY to the aggregate report's
`flagTimeInSeconds` — use that as the self-check.
`/detail` and `/drilldown` are 404; only `/breakdown` exists.

The aggregate (`/reporting/technician`) is literally the endpoint the Tech
Performance (beta) screen calls, so matching it is tautological — the real
cross-check is `/breakdown` (ledger) + `/ro/v1/{id}` (RO documents) agreeing
with it, which are different data paths.

**referenceHoursForFlagging** tells you the store's flag policy. `BILL_HOURS`
(BC) = auto-flag copies BILLED hours, so Flagged always == Assigned Billed and
NEVER tracks the clock — do not report that identity as a bug. `ACTUAL_HOURS`
(SV) = flags follow punches.

**payDay ≠ work day.** A flag lands on the date it was flagged (usually
invoice/close), so a Tech-Performance date range mixes flags for work clocked
weeks earlier with punches from the window. ALWAYS quantify both leaks
separately: (a) ROs punched in-window with zero/low flag, (b) ROs flagged
in-window with no in-window punch. Reporting only the net hides offsetting
errors (BC Tafolla: net −7.45 hid 26.2 unpaid + 30.1 over-flagged).

## FAILURE MODE 2 — the flag INDEX silently drops entries (BT 1249, tech 512, 2026-08-28)

When a tech says "RO X, Y, Z are MISSING from my flag hours", it is often NOT a
data-entry problem and NOT the payDay-timing effect. Tekion has two stores of
flag data and they can disagree:

| | source | used by |
|---|---|---|
| INDEX | `POST /api/service-module/u/reporting/technician/breakdown` (ES) | Tech Performance (beta), Flag Time Report — **what pays the tech** |
| TRUTH | `GET /api/service-module/u/ro/v1/{roId}` → `.jobs[].operations[].techIdWithBillingTimes[].flagTimesWithPayDay[]` | the RO document itself |

Flag entries that exist on the RO document but never made it into the ES index
are invisible to the report — the tech worked, the flag posted on the RO, and
the report never pays it.

**Reconcile them.** Match on the 4-tuple `(roId, operationId, payDay, flagTimeInSeconds)`;
use a `collections.Counter` and decrement, because a single operation legitimately
carries multiple flag entries (including 0-second reversals). Anything left over
on the TRUTH side is a dropped entry.

Scripts: `bt512_flag_index_gap.py` (clock-driven RO discovery) and
`bt512_flag_index_gap_wide.py` (adds OpenAPI `repair-orders:search` on
`modifiedTime GTE` so ROs the tech never PUNCHED on are still checked).

**PITFALL — clock-driven RO discovery misses flag-only ROs.** The first pass only
inspected ROs the tech had TECH_CLOCK punches on, which hid RO 151197 (1.80 h
flagged, zero punches by that tech). Always union the punched-RO set with an
OpenAPI `repair-orders:search` sweep of the window.

**PITFALL — `/breakdown` 500s on a `roNo` filter.** Only `payDay` + `techId`
filters are accepted. To check one RO, pull the tech's whole window and filter
client-side.

Diagnostic tell that it is an index drop and not timing: the missing entries are
interleaved in time with entries that DID index (so it is not a cutoff), they are
all `AUTO_ADDED`, and re-reading the RO document shows the flag present with a
valid `payDay` inside the report window. Nothing in the UI can fix this — the
flag is already correct on the RO. It needs a Flag Hours Report adjustment to
pay the tech, plus a Tekion ticket for the indexing defect.

**Corroborate across stores before calling it a Tekion defect** (the standing
fleet-comparison rule — a single store's oddity has repeatedly turned out to be
local config). Confirmed at **two of seven** stores, **3 of the first 4 techs
checked** (2026-08-28, window Aug 16–27):

| store | emp | tech | dropped entries | hours | $ @ wage |
|---|---|---|---|---|---|
| BT 1249 | 512 | Luis Vasquez Melchor | 4 | 3.80 | — |
| BC 1251 | 5576 | Victor Tafolla | 4 | 2.40 | $124.80 @ $52 |
| BC 1251 | 410 | Craig Holman | 2 | 3.40 | $176.80 @ $52 |
| BC 1251 | 192 | Michael Barks | 0 | 0.00 | clean |

**Signature to quote in the Tekion ticket — it has held for every hour-bearing
drop across both stores:** pay type **WARRANTY**, `flagHourType AUTO_ADDED`,
flagged in the **back half of the pay period** (08/26–08/27), present and valid
on the RO document, absent from the ES index. Zero-hour entries drop too
(Tafolla RO 101268, customer pay) — same index failure, no pay impact, so count
entries dropped separately from hours dropped.

**Drops are NOT confined to closed ROs** — Holman's 2.40 hr drop was on RO 101329
`IN_PROGRESS`, his 1.00 hr drop on RO 100980 `INVOICED`. One tech's drop list can
therefore need BOTH fix paths; always print the RO status per dropped entry and
split the remediation list (tech-time modal vs Flag Hours Report adjustment)
rather than assuming a single path per tech.

### ⭐ TWO RENDERERS — the clean one is usually what he actually wants
Joe's follow-up to the corrected version was **"write it so it doesn't look like
it's *corrected*"** (2026-08-28). A report headed "CORRECTED" with a
Tekion-vs-Correction-vs-Corrected table is an *internal diagnostic* — it advertises
that the DMS was wrong and it can't go to a tech, a manager, or a pay file.

| script | output stem | use for |
|---|---|---|
| `render_tech_perf_corrected.py` | `tech_perf_corrected_bt_<emp>_<date>` | proving the gap, Tekion ticket evidence |
| **`render_tech_perf.py`** | `tech_perf_bt_<emp>_<date>` | **the deliverable** — routine report, one set of numbers |

Both read the SAME package JSON. The clean one merges `indexed` + `missing` into a
single ledger and never mentions the distinction: native 13-column Tech Performance
layout (TOTAL row on top), KPI cards = Flagged / Attendance / Proficiency /
Efficiency, a Labor Summary, then the flag detail. Page 2 = flagged-vs-clocked by RO
plus per-RO job detail with concerns. Zero words like *corrected / missing /
recovered / defect*. Grep the HTML for those before sending.

**Default to building the clean one** and keep the diagnostic version as backup
evidence — don't wait to be asked twice.

Two things the clean renderer must handle that the diagnostic one didn't:
- **Labor cost is `$0` on entries read from the RO document** (no `laborCostDetail`).
  Tekion derives it as `flag_hrs × wage`, so derive it the same way — otherwise labor
  gross is overstated by the full tech-pay amount. Sanity check: **Labor Cost should
  equal Tech Pay** ($490.09 vs $490.10, rounding).
- **Concern text arrives mojibaked** (UTF-8 bytes read as latin-1): `â\x80\x93` for an
  en-dash, `â\x80\x99` for a curly apostrophe. Round-trip with
  `s.encode("latin-1").decode("utf-8")` inside a try/except.

## DELIVERABLE — the CORRECTED Tech Performance report (BT 512, 2026-08-28)

Once you've proven an index drop, Joe's next message is **"can you generate a
corrected version for me?"** — same shape as the advisor closed-performance
reports. Build it, don't just describe the gap.

```bash
cd /home/itadmin/tekion-reports
python3 render_tech_perf_corrected.py \
    data/bt-<emp>-corrected-<YYYY-MM-DD>.json "<Tech Name>" <emp> <YYYY-MM-DD>
```
Outputs `out/tech_perf_corrected_bt_<emp>_<date>.{png,pdf,csv}`.

Input JSON keys: `native` (the lineItem from `/reporting/technician`), `indexed`
(that day's `/breakdown` rows), `missing` (recovered entries), `clock` (`{roNo: hrs}`
from TECH_CLOCK), `store_name`, `wage_per_hour` (CENTS), `tech`, `date`.

Layout: 4 KPI cards (Flagged-Tekion / Flagged-Corrected / Proficiency / **Tech Pay
Impact in dollars** — that last one is what makes it actionable), a Tekion-vs-
Correction-vs-Corrected metric table, the recovered-entries table with a **Fix Path**
column, then page 2 = the full flag ledger with an `In Report? yes/NO — dropped`
column plus clocked-vs-flagged by RO.

**Fix Path rule:** RO status `INVOICED`/`CLOSED` → *Flag Hours Report adjustment*;
anything else (`READY_FOR_INVOICE`, `IN_PROGRESS`) → *tech time modal on the RO*.

### Two data traps that produced wrong numbers on the first render
1. **Don't reuse a `payDay` you carried in from a hand-built dict.** RO 151197's
   timestamp printed as 09:27 instead of the true 13:27. Re-read `payDay` from the
   RO document's `flagTimesWithPayDay[]`, matching on `flagTimeInSeconds`.
2. **PRORATE labor sale to the flagged share.** `sum(labor.preSplits[].amountToSplit)`
   is the WHOLE operation's sale. RO 149531 flagged 0.10 hr of a 0.70 hr operation —
   charging the full $169.83 overstated the recovery by $145. Use
   `sale * flag_sec / op_billing_sec`. Correct total was $919.86, not $1,065.43.

Report both `flagTimeInSeconds` and `operationBillingTimeInSeconds` in the ledger so
a partial flag is visible rather than looking like a discrepancy.

### Native metric definitions (confirmed against `/reporting/technician`)
- Efficiency % = flag / clocked · Proficiency % = flag / attendance
- Unapplied = attendance − flag (**goes negative when corrected flag > attendance** —
  that is real and worth calling out, not a render bug)
- **`departmentId NIN [<dealer>_department_5]` is the screen's DEFAULT filter.** With it
  applied BT 512 showed 4.30 flag hrs; without it, 7.80. If your native total doesn't
  match what the user sees, this filter is why — capture `__post_body` and match it.

## PITFALL — never let a report fall back to another store's logo

`logo_0.png` and `logo_st.png` in `~/tekion-reports/` are **both Stevens Creek Toyota**,
despite the neutral-looking `logo_0` name. Many older renderers hardcode `logo_0.png`
as a generic default. On 2026-08-28 a Blackstone Chevrolet Tech Performance report
went to Joe with the Stevens Creek Toyota logo in the header — he caught it immediately.

Rules:
- SCT is the ONLY store with a verified logo asset on disk. There is no BC/BT/TL/SV/VC/AR
  logo file, and the AMG signature asset `amg-dealer-logos.jpg` only holds generic
  MANUFACTURER marks (Chevy bowtie, Toyota oval), not dealership logos.
- Dealer websites are Cloudflare-403'd to both curl and the browser tool — you cannot
  scrape a logo at run time.
- So: render a **text wordmark in the store's brand colors** for every non-SCT store.
  `render_tech_perf.py` has a `_brand(store)` helper returning
  `(line1, line2, color1, accent)` and builds `MARK` (img when SCT, wordmark otherwise).
  The accent color also drives the header rule and `h2` bars via a `--accent` CSS var.
- CSS is injected with `.replace("__ACCENT__", ACCENT)`, **not** `%`-formatting —
  the stylesheet contains `width:100%` which breaks `%` substitution.
- Always `vision_analyze` the rendered PNG and explicitly ask "what dealership branding
  is in the header?" before emailing. The numbers being right does not make the report right.

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

## ★ TURNKEY — the generic package builder (built BC 2026-08-28, use this first)

Stop writing a bespoke `<store><emp>_flag_gap.py` per request. One script assembles
the complete package JSON both renderers consume, for ANY store / tech / date range:

```bash
cd /home/itadmin/tekion-reports
python3 build_tech_perf_package.py --dealer 1251 --tech-emp 5576 \
        --from 2026-08-16 --to 2026-08-27 --store-name "Blackstone Chevrolet"
# -> data/tech-<dealer>-<emp>-<from>_<to>.json
```

It does all four sources in order: resolve employee# → tech UUID, `/reporting/technician`
(native), `/breakdown` (index ledger), TECH_CLOCK by roNo, then the RO-document sweep
(punched ROs ∪ OpenAPI `modifiedTime` window) and prints the `NOT IN INDEX` table.
Requires `/tmp/tekion_tech_headers_<dealer>.json` from `capture_tech_report_headers.py`.

Then render — the renderer takes an **optional 5th arg = END date** for a range:

```bash
python3 render_tech_perf.py data/tech-1251-5576-2026-08-16_2026-08-27.json \
        "Victor Tafolla" 5576 2026-08-16 2026-08-27
# -> out/tech_perf_<dealer>-<emp>-<from>_<to>.{png,pdf,csv}
```

Range mode adds a **Daily Summary** table (entries / ROs / flag hrs / labor sale / tech
pay per flag date), switches the header chip to "Flag Dates", and stamps `%m/%d %H:%M`
on every ledger row instead of bare time. Single-date behaviour is unchanged when the
5th arg is omitted. The output stem is derived from the package filename, so two techs
never overwrite each other.

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

**Three more `/users` shape traps, all hit at BC 2026-08-28** (each one silently
returns the wrong answer instead of erroring — budget a debug pass here):
- **It is CURSOR-paginated, and `pageNumber` is accepted-and-ignored.** Sending
  `pageInfo.pageNumber` 1,2,3… returns the identical first 100 users every time, so
  the loop "succeeds" and both target techs are simply absent. The ONLY way forward
  is `meta.nextFetchKey` → next request's `nextFetchKey`. Stop when it's absent.
  Self-check: assert the deduped user count grows each page.
- **`data` is a bare LIST at some dealers**, a `{"results":[...]}` dict at others.
  Handle both: `rows = d if isinstance(d, list) else d.get("results", [])`.
- **`completeNames` is a LIST of `{nameType, value}` at BC**, a dict elsewhere.
  `completeNames["DISPLAY_NAME"]` throws `TypeError: list indices must be integers`.
  Normalize before reading.

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

## ⭐ WHEN THE INDEX IS CLEAN — triage the leftover gap, don't force a defect

Two techs at the same store, same window, same settings will NOT both have the
index defect. At BC 2026-08-28: Tafolla was short 2.40 hrs / 4 dropped entries;
**Barks tied EXACTLY — 85 entries for 85, 63.50 hrs for 63.50.** Say the clean
result plainly and just as loudly as the defect. Joe's next question is then
"so what discrepancy DOES he have?", because the Tech Performance screen still
showed Barks 3.92 hrs unapplied (attendance 67.42 / clocked 62.33 / flagged 63.50).

Walk the clocked-RO list and bucket every unflagged RO into one of four causes.
Only ONE of them is a Tekion bug:

| bucket | tell | verdict |
|---|---|---|
| **payDay just outside the window** | flag exists on the RO doc, `payDay` = day after `--to` | timing, not lost — lands next pay period |
| **RO still open** | status `IN_PROGRESS`/`READY_FOR_INVOICE` | not billed yet; flags post at billing |
| **closed with ZERO labor billed** | every op `billSec: 0`, `flags: []`, `laborSale: None` | **store-process** issue — nothing to flag against |
| **flag on doc, absent from index** | doc has a valid in-window `payDay`, `/breakdown` doesn't | **the Tekion defect** |

Barks: RO 101947 CLOSED 2.86 clocked → flagged 2.70 on 08/28 (one day late);
RO 101249 IN_PROGRESS 1.34; RO 101304 CLOSED 0.49 with `TPS`/INTERNAL and
`CONCERN`/WARRANTY both at `billSec 0` — the only genuine gap, and it belongs in a
conversation with the store, not the Tekion ticket.

Everything else was normal flat-rate outperformance (clocked 3.63 / flagged 5.50,
12.95 / 14.50, 2.41 / 3.50 → 101.9% efficiency). **Beating flat rate is not a
discrepancy** — label it so nobody chases it.

Fetch the per-RO evidence with `clock_by("roId", …)` for the RO universe, then
`GET /api/service-module/u/ro/v1/{roId}` per candidate. Note
`POST /api/rosearchservice/u/ro/search` is a **404 — that endpoint does not exist**;
RO lookup goes through the clock report + `/openapi/v4.0.0/repair-orders:search`.

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
