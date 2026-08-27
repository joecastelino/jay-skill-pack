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

## THE FIX
On `/core/reports` → Advisor Performance Report, set the **Status filter to include
BOTH `INVOICED` and `CLOSED`** (or clear it). Save it as the default view so the
store stops re-running the INVOICED-only version. Then the number stops "dropping."

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
