---
name: tekion-gross-not-posting-to-advisor
description: Diagnose "advisor gross dropped / gross not posting to advisor" complaints on the Tekion Advisor Performance Report. Usually the report's Status filter (INVOICED vs CLOSED), not a data loss or advisor-reassignment bug.
triggers:
  - gross not posting to advisor
  - advisor gross dropped
  - advisor performance report numbers went down
  - my gross disappeared
  - RO gross not showing on advisor
---

# "Gross Not Posting To Advisor" — Diagnosis

## Symptom
A manager (e.g. Kevin Stapp / SCT) screenshots the **Advisor Performance Report**
twice a few minutes apart. Between the two, the advisor's RO Count and Total Gross
DROP. They name 1-2 suspect ROs and say gross "isn't posting."

## ROOT CAUSE (confirmed 2026-08-27, SCT / Artist Battle)
The Advisor Performance Report has a **Status filter**, and the store runs it on
`Status = INVOICED`. **`INVOICED` and `CLOSED` are mutually exclusive buckets.**
When accounting closes an RO, it moves INVOICED → CLOSED and **silently falls out
of the report**. Nothing was lost, unassigned, or mis-posted — the view is just
filtered to a bucket that drains all day.

Case data:
- 6:10 PM report: 37 ROs, labor $8,442.40, parts $3,457.33, total $11,899.73
- 6:13 PM report: 36 ROs, labor $8,165.10, parts $3,252.89, total $11,417.99
- Delta: −1 RO, −$277.30 labor, −$204.44 parts, −$481.74 total
- **RO 581311 closed at 18:13:31** and its true gross = labor $277.30 / parts
  $204.44 / total $481.74 — an **exact penny match** to the delta.

Scale of the distortion at SCT for that one advisor, August MTD:
| View | ROs | Labor GP | Parts GP | Total GP |
|---|---|---|---|---|
| `INVOICED` only (what they see) | 31 | $7,459.45 | $2,889.71 | **$10,349.16** |
| `CLOSED` (hidden) | 195 | $53,391.66 | $19,165.45 | **$72,557.11** |
| TRUE MTD | 226 | $60,851.11 | $22,055.16 | **$82,906.27** |

**~88% of the advisor's real gross was invisible.**

## THIRD failure mode: 8/26 cohort near-totally absent (2026-08-27) ✅ RESOLVED — index lag, since FIXED
After fixing Status and Pay Type View, a "Pay Type Closed Date = yesterday" run
STILL undercounted. Joe confirmed off his own screen: 19 rows = **all 18 ROs that
closed 8/25, plus exactly one from 8/26 (581311)**. Truth was 28 ROs / $14,631.70.

Killer pair: **581233 closed 18:10, 581311 closed 18:13** — three minutes apart,
both CLOSED, both 2 invoices fully closed, same advisor, same pay types. One shows,
one doesn't. Every API date field (invoicedTime, modifiedTime, invoice created,
invoice closed) is identical in shape. Eight ROs / $2,282.01 dropped that day.

Legitimate exclusions found while checking (rule these out first):
- **581255** — status still `INVOICED`; its Internal invoice never closed. Correct.
- **580281** — warranty-only, excluded by Pay Type View = Customer Pay. Correct.

**Still not proven a defect.** Untested: the report only refreshes every 4–6 hrs and
Joe's run was 6:35 AM. Next step is Refresh + re-run, then reproduce at BT before
filing with Tekion. Suspicious shape: missing ROs cluster 08:24–10:59 while the
LATEST close of the day (18:13) is present — backwards for simple sync lag.

## ✅ CAUSE #3 RESOLVED 2026-08-28 — it is INDEX LAG, not a filter defect
Reproduced head-to-head at SCT. The native report is a **batch-generated ES index**
("Last Generated On" in the header — 3:31 AM the morning of the test) and recent
close-days **backfill in over ~3 days**. Aging curve (API truth vs native, same exact
RO sets, roNo IN probe with a full-year date window so the date filter can't be the
variable):

| Close day | age | API ROs | Native | % found | Missing $ |
|---|---|---|---|---|---|
| 8/20 | 8d | 18 | 18 | 100% | $0 |
| 8/24 | 4d | 257 | 257 | 100% | $88 |
| 8/25 | 3d | 270 | 270 | 100% | $0 |
| 8/26 | 2d | 134 | 102 | **76%** | $10,156 |
| 8/27 | 1d | 225 | **55** | **24%** | $36,905 |

**Yesterday's number on the native report is ~1/4 of reality.** ≥3 days old is exact.
The missing ROs are NOT clustered by pay type (INTERNAL dominates both the present and
the missing buckets in equal proportion), which kills the pay-type-filter theory.
~~**Practical rule: never read the native Advisor Performance Report for a day newer
than T-3.**~~ **← RETIRED 2026-08-31, see the re-test section below. Tekion fixed it.**

**Residual — CLEARED.** 577056 / 580281 / 581233 (closed 8/26) were absent at T-2 on
8/28; re-probed at T-5 on 8/31 they are all **present** (3 ROs / $1,598.82). They
backfilled on their own, so there is **no index-drop defect and no ticket to file**.

## ✅ RE-TEST 2026-08-31 — THE LAG IS GONE. Native is now same-day accurate.
Re-ran the exact aging comparison at SCT (876) after the weekend. Native
`lastUpdatedTime` = **8/30 23:31 PT** (previously the batch was a 3:31 AM job that left
recent days starved). Every close-day 8/20–8/30 now matches the API to ~100% on RO
count, **including T-1**:

| Close day | age | API RO | Native RO | % | $ delta |
|---|---|---|---|---|---|
| 8/24 | 7d | 258 | 259 | 100% | +$573 |
| 8/26 | 5d | 135 | 136 | 101% | +$121 |
| 8/27 | 4d | 225 | 225 | 100% | −$162 |
| 8/28 | 3d | 239 | 239 | 100% | −$253 |
| 8/29 | 2d | 26 | 26 | 100% | $0 |
| **8/30** | **1d** | **46** | **46** | **100%** | +$47 |

Compare to 8/28: T-1 was **24%** and T-2 was **76%**. Residual ROs 577056 / 580281 /
581233 all now return present (roNo IN probe, 3 ROs / $1,598.82) — they backfilled, so
**no index-drop ticket is warranted.** ±1 RO / small-$ deltas are definitional (a single
RO whose pay types straddle midnight counts on both days in the API report).

Cross-checked BT (1249): native is now **≥** the API report on 8/29–8/30, i.e. not
undercounting in the other store either.

**Revised practical rule (supersedes "never read newer than T-3"):** the native report
is usable again for recent days, BUT it is still a batch index — always read the
**"Last Generated On"** timestamp in the header before trusting a same-day figure, and
re-verify the aging curve if numbers ever look light again. The API report
(`advisor_closed_gross.py`) remains the ground-truth reference for any dispute.
**Re-testing method:** hit `generate-summary-report` per close-day with only the
`payTypeFirstClosedTime` BTW filter swapped, read the `TOTAL` row's `Ro Count`
(`f802dcf4-…`) and `Total Gross` (`c46b0950-…`) out of `reportCellList`, and diff against
`out/advisor_closed_gross_<store>_*.json` grouped by `closed_days`.

### How to reproduce the comparison (the method that settled it)
Capture the report's own XHR and replay it — a bare fetch 500s ("Token doesn't exist").

**Shortcut (2026-08-31, faster than XHR-hooking):** you don't need to capture headers by
driving the UI. Build them from `localStorage` in-page — this is what the axios
interceptor does anyway, and it works for `generate-summary-report`:
```js
var u=JSON.parse(localStorage.getItem('t_user')||'{}');
window.__H={'Accept':'application/json, text/plain, */*','Content-Type':'application/json',
 'tekion-api-token':localStorage.getItem('t_token'),
 'roleId':localStorage.getItem('currentActiveRoleId'),
 'userId':u.id,'tenantname':u.tenantName,
 'dealerId':localStorage.getItem('currentActiveDealerId'),
 'tek-siteId':'-1_'+localStorage.getItem('currentActiveDealerId'),
 'original-userid':u.id,'original-tenantid':u.tenantName,'clientId':'web','locale':'en_US',
 'program':'DEFAULT','applicationId':'ARC_NA','subApplicationId':'US','productIds':'ARC'};
```
Then `fetch(...,{headers:window.__H})` in-page. **Cross-store without switching dealers:**
copy `__H` and override just `dealerId` + `tek-siteId` (`'-1_<id>'`) — verified against BT
1249 while the browser sat on SCT 876. Saved request body template lives at
`/tmp/native_body.json` (a 1-element list; only swap `[0].filters`).
Stale saved header files (`/tmp/tekion_rec_headers.json`) expire — a 401
`session.expired` means rebuild from localStorage, not that the endpoint changed.

1. Preflight `:9223` (`opcode_preflight.py --dealer <ID>`; `--restore` after).
2. Hook `XMLHttpRequest` open/send/setRequestHeader, stash any call to
   `/api/rosearchservice/u/visibility-dashboard/generate-summary-report` **with its
   headers**, then SPA-nav (`history.pushState` + `PopStateEvent`) to `/core/reports`
   and `/mouse`-click the report name to fire it.
3. Replay in-page with mutated filters: the date filter is
   `field:"payTypeFirstClosedTime"` `operator:"BTW"` `[startMs,endMs]` (Pacific).
   Add `{key:"roNo",field:"roNo",values:[...],operator:"IN"}` to scope to an exact set.
   Do NOT change `groups` (replacing the group tree → `unexpected.error`).
4. Advisor IDs come back raw — resolve via
   `POST /visibility-dashboard/lookup/resolve-by-id` `{lookupByIds:[{lookUpAsset:"PRIMARY_ADVISOR_ID",ids:[...]}]}`.
5. To find WHICH ROs are missing, recursive-bisect the RO list on the returned
   `Ro Count` (~5 min for 225 ROs). `:9223 /eval` takes `{"js": ...}`, **not**
   `{"expression": ...}` (400 otherwise), and results must be sliced ≤15,000 chars.

## THE FIX
On `/core/reports` → Advisor Performance Report, set the **Status filter to include
BOTH `INVOICED` and `CLOSED`** (or clear it). Save it as the default view so the
store stops re-running the INVOICED-only version. Then the number stops "dropping."

## CAUSE #2 — CVSC (and warranty) hidden by the Pay Type View dropdown
Toyota service-contract work bills to `payType=CUSTOMER_PAY` with
**`subPayType=CVSC`**, on a SEPARATE invoice from the plain Customer Pay one — and
the plain CP invoice is then **$0.00**. With Pay Type View = Customer Pay the report
reads that $0 invoice and shows **zero gross on a ticket that clearly has gross**.
Verified SCT 2026-08-27: RO 577046 (true GP $575.40) and RO 577056 (true GP
$1,478.50) both displayed $0. Scale for ONE advisor in one month: **60 of 226 ROs /
$11,478.92 sat in CVSC.** Fix = Pay Type View → **All**. Tekion books this
correctly; whether CVSC *should* count toward advisor gross/pay plan is a business
decision for the VP, not a Tekion bug — raise it, don't assume.
Warranty-only ROs disappear the same way under a CP-filtered view.

## CAUSE #3 — "Pay Type Closed Date = yesterday" silently drops ROs ✅ RESOLVED & FIXED
**Was index lag; Tekion fixed it 2026-08-31. Kept for history — do not re-diagnose this.**
SCT 2026-08-27, user-confirmed on his own screen (not OCR): filtering closed-date to
8/25–8/26 returned **19 ROs — all 18 that closed 8/25, but only 1 of the 10 that
closed 8/26.** RO 581233 (all pay types closed 8/26 18:10) was absent while RO 581311
(closed 8/26 18:13) was present — 3 minutes apart, both CLOSED, both 2 fully-closed
invoices, same advisor. No API field distinguishes them. $2,282 of gross missing that
day. NOT yet proven a platform defect: Advisor Performance refreshes only every 4-6h
and the report was pulled 6:35 AM, so **always have the user hit Refresh and re-run
before escalating**, then reproduce at a second store.

## THE DURABLE ANSWER — stop fighting the report, build it from the API
Joe's response to all three causes was **"can you build a report for me via the API?"**
That is the expected deliverable once a native report is shown unreliable. See skill
**`tekion-advisor-closed-gross-api-report`** — `~/tekion-reports/advisor_closed_gross.py`
keys on true per-invoice pay-type close time and counts ALL pay types, so causes #1-#3
cannot bite. It found 9 ROs / $2,763.75 on 8/26 where Tekion showed 1 / $481.74.

## Diagnostic procedure (do it in this order)
1. **Sweep the RO# across all 7 dealers first** — RO numbers are NOT unique.
   Beware typos in the complaint: "851311" was really **581311** (851311 matched
   3 unrelated 2019/2020 ROs at BC/BT/ST and would have sent you down a rabbit hole).
2. **Confirm the advisor is actually still assigned**: `assignee.advisor.id` on
   `repair-orders:search`. If it still resolves to the complaining advisor via
   `GET /users/{id}`, it is NOT a reassignment/placeholder problem — skip that path.
3. **Check `status`** on each suspect RO. `CLOSED` + an INVOICED-filtered report
   = you already have your answer.
4. **Match the delta to the penny.** Compute the suspect RO's true gross
   (labor `saleAmount−costAmount` + parts `saleAmount−costAmount`, all CENTS ÷100)
   and compare to the difference between the two screenshots. An exact match is
   proof; anything else means keep digging.
5. **Quantify the hidden bucket** (MTD INVOICED vs CLOSED gross) so the manager
   sees the real magnitude, not just the one RO.

## ⚠️ NEVER diagnose off a SCREENSHOT transcription (burned 2026-08-27)
`vision_analyze` reliably MISREADS Tekion report digits. Verified errors in one image:
`579513`→"S79613", `$5,173.99`→"$517.99", `$3,394.19`→"$394.19", `$231.03`→"$217.03",
`-$36.14`→"$36.14" (sign dropped). Three "refs" I read off the image turned out to
belong to OTHER advisors and to have closed a week earlier.
**Rule: use the screenshot ONLY to learn which filters/date range the manager used.
Pull every RO number and dollar figure from the API.** Cross-check by matching the
report's ROW COUNT to your API set, not by matching individual OCR'd refs.
Also: "N Result(s)" on Advisor Performance = TOTAL row + advisor row(s), NOT RO count.
The real RO count is the `Ro Count` column.

## ⚠️ Do NOT declare a "Tekion defect" without a cross-store repro
On 2026-08-27 I called the Pay Type Closed Date filter defective because RO 581233
(pay types closed 8/26 18:10) was absent while 581311 (closed 8/26 18:13) was present.
That conclusion was premature — it rested on an OCR'd ref list. Before filing any
platform-defect ticket: (1) rebuild the expected set from the API, (2) have the user
read the specific RO numbers off their own screen, (3) reproduce at a second store.
Fleet-comparison-before-blaming-the-vendor is a standing rule.

## ESCALATION PATH — where this ends up
Once two of the three filters are shown wrong, Joe's move is **"can you build a
report for me via the API?"** Don't keep diagnosing the screen — pivot to
`tekion-advisor-closed-gross-api-report`, which is immune to all three failure
modes. Anticipate this and offer it early.

## Ask the user to read RO numbers off their screen
The fastest disambiguation is not more API work — it's "read me these five RO
numbers, are they present?" Joe's answer ("I have 581311 too, nothing else, 19
tickets") instantly separated the complete 8/25 cohort from the broken 8/26 one,
which no amount of my own OCR could establish.

## Pitfalls
- **All Tekion $ are CENTS** — divide by 100 or you report $1.5M on one RO.
- `closedTime` filters have a broken pagination token; use `invoicedTime` BTW with
  plain `paginationToken` chaining (works fine) — see `tekion-openapi-repair-orders`.
- Do NOT accept the screenshot's transcription of the RO number as gospel; verify
  against the API (`documentNumber` IN [...]), and read the RO# off the RO detail
  screenshot itself if one was attached.
- The screenshot advisor name on the RO detail view may show the CUSTOMER-facing
  writer, not the `assignee.advisor` — trust the API field.
- A large MTD fan-out (226 ROs × jobs/ops/parts) takes ~3 min; run it once and
  cache. Don't loop it.

## Pulling the manager's email
Stacey (email-agent) owns Gmail. Via the bridge, **subprocess argument-list form**
(parens/quotes in the message break the top-level terminal tool):
`~/bin/ask-agent stacey "<self-contained read-only request>"` — tell her explicitly
DO NOT SEND, save attachments to `/home/itadmin/tekion-reports/inbox/`, and return
absolute paths. Inline Gmail images all arrive named `image.png`; she renames them
`image_1..N.png`.
