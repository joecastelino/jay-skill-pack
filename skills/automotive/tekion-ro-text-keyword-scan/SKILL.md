---
name: tekion-ro-text-keyword-scan
description: Search Tekion repair orders for a keyword (e.g. "calibration", "windshield") across labor descriptions, job concern text, part names, fees, and notes, with a dollar figure on the matching line. Use for ROI/opportunity-sizing questions like "how much calibration/windshield/etc business did we do in the last N months". Covers the BT Collision Center / body shop department discovery and the critical "Per Estimate" lump-sum blind spot.
triggers:
  - scrub repair orders for keyword
  - how many ROs mention X
  - body shop repair orders
  - collision center data
  - windshield report
  - calibration report
---

# Tekion RO Text Keyword Scan (body shop / any department)

## When to use
Joe asks something like "pull the last N months of [body shop] ROs that mention
[word] with a dollar figure on the line" — usually for an ROI calc (e.g. "how much
calibration business would justify a new alignment machine", "how many windshield
jobs did we do"). This is a **keyword full-text scan across RO sub-resources**, not
a tag/opcode filter (the word won't be a clean tag).

## Step 0 — Which store(s) have the department in question?
Don't assume. All 7 AMG stores were checked 2026-08-18 for "Collision Center" /
body shop: **only BT (Blackstone Toyota, dealer 1249) has one** — department id
`1249_department_5`, name "Collision Center". The other 6 stores' only departments
are their main Service dept (+ BC also has UCD/PDI/Express Service). Confirm via:
```python
# GET /departments/{id} resolves an assignee.department.id to a human name
get(f"/departments/{did}", store_code)  # -> {"data":{"id":..,"name":"Collision Center"}}
```
Collect candidate department ids by sampling `assignee.department.id` off a handful
of `repair-orders:search` pages spread across the window (creationTime LTE at
several anchor points) — a single page won't surface all departments if they're rare.

## Step 1 — Pull the full RO index for the window
`creationTime BTW [lo_ms, hi_ms]` + pageSize 50 + follow `meta.nextPageToken` works
fine for a straight creationTime window (unlike `closedTime` windows, which need
bisection — see the PAGINATION TRAP section of `tekion-openapi-repair-orders`).
Expect roughly 1 API call per 50 ROs; a 92-day full-store pull (~11,600 ROs at a
mid-size store) takes ~230 pages / ~2.5 min. Dedupe by `documentId` when done (the
BTW token can occasionally re-serve a boundary row).

Filter down to your department: `(ro.get("assignee") or {}).get("department",{}).get("id") == target_dept_id`.
Save this candidate list to `/tmp/<store>_<dept>_all.json` (or under
`~/tekion-reports/data/` if it should survive past the ephemeral home).

## Step 2 — Fan out and regex-search every text field, per RO
For each candidate RO (typically 150-200, NOT the full store — this is why Step 1's
department filter matters, it's a 60-100x reduction before any fan-out):
1. `GET /repair-orders/{rid}/jobs` → for each job: `concern.text`
2. `GET /repair-orders/{rid}/jobs/{jid}/operations` → for each op: `opcodeDescription`,
   `labor.saleAmount`/`costAmount` (both CENTS — divide by 100)
3. `GET /repair-orders/{rid}/jobs/{jid}/operations/{oid}/parts` → for each part:
   `partName` + `description`, `saleAmount`/`costAmount` (cents; `saleAmount` on a
   part line is already the EXTENDED total, don't multiply by qty)
4. `GET /repair-orders/{rid}/jobs/{jid}/job-fees` and `GET /repair-orders/{rid}/ro-fees`
   → `name`/`description` field, amount
5. RO-level `externalNotes` field (already on the search result, free)

Regex case-insensitive on all of these; `re.compile(r"calibrat", re.I)` catches
calibration/calibrated/calibrating in one shot. Checkpoint to JSON by `documentId`
every ~10 ROs (reuse the align_scan checkpoint/resume pattern — `done` dict +
`results` list, `if rid in done: continue`) so a timeout/kill just resumes.
Run as a **background terminal process**, not execute_code — the fan-out (3-5
calls/RO × ~180 ROs = 500-900 calls) exceeds the 300s code-tool limit.

Include VOIDED/HOLD/every status in the candidate set unless told otherwise — a
job can get voided and rebilled, and the user may want the full picture including
open work (TECH_ASSIGNED, READY_FOR_INVOICE).

## ⚠️ CRITICAL CAVEAT — body shop $ mostly hides in lump-sum "Per Estimate" opcodes
Collision Center ROs are driven by **outside insurance estimates** (CCC ONE /
Mitchell work files — visible as "work file id: xxxx" in job concern text). The
Tekion opcodes used are lump-sum buckets:
- `BSRPE` = "Collision Center Repair Per Estimate"
- `BS5`/`BS6`/`BS7`/`BS8`/`BS10` = generic Body/Paint/Frame labor buckets
- Individual line items from the estimate (glass, calibration, ADAS recalibration,
  paint materials, etc.) are usually **NOT broken into separate Tekion operations**
  — they're baked into ONE lump labor $ on BSRPE/BS6/BS7. Only line items that also
  get a discrete **PART** added to the RO (trim moulding, stopper, dam, an actual
  glass part number) will surface in a keyword+dollar scan.

**Practical effect (verified 2026-08-18, BT 92-day window, 182 body shop ROs):**
- "calibration" kept scanning to nearly zero (2 hits) — both were customer concern
  text mentioning a park-sensor calibration need, never priced as its own line.
- "windshield" returned 21 ROs, but ~17 of them were the SAME $165.58 trim-kit part
  bundle (stopper/dam/moulding, part#s 56115-30100 / 56116-22050 / 56117-04050 /
  75533-04010 / 75534-04010) — NOT the actual glass or labor. Only 1 RO (143768)
  had an actual glass part line ($951.43). 4 ROs had "windshield" only in concern
  text with $0 capturable line.
- **Conclusion: a keyword scan on Tekion structured data systematically UNDERCOUNTS
  body-shop-category dollar volume.** State this caveat explicitly whenever
  reporting body shop keyword-scan results — don't let a low/misleading number
  stand unqualified (the user immediately pushed back "that can't be correct" on
  the first calibration result, and rightly so).
- For a TRUE dollar figure on a body-shop category (calibration jobs, glass jobs,
  ADAS jobs), the real source is the **CCC ONE / Mitchell insurance estimate
  exports**, not Tekion RO line items. Offer to pull those (portal access needed)
  or manually sample "Per Estimate" RO estimate PDFs, rather than presenting the
  Tekion-only keyword count as the final number.

## Output format
Always give the user actual RO numbers (documentNumber, not documentId) in a table:
RO#, date, status, $ found on the matching line(s), which sub-resource matched
(labor_desc / part / job_concern / fee / notes). If most hits are $0 (concern-text
only) or a repeated small trim-kit bundle, call that pattern out explicitly rather
than just handing over a grand total — that total can be misleadingly low relative
to the real business question (e.g. ROI for a machine purchase).

## Reusable script pattern
See `/home/itadmin/tekion-reports/bt_bodyshop_windshield_scan.py` (and the
calibration variant) for the full working implementation — just swap the `PATTERN`
regex and `INPUT` file to reuse for a new keyword or store.
