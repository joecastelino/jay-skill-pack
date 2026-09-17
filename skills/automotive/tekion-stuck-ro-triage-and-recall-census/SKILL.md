---
name: tekion-stuck-ro-triage-and-recall-census
description: Triage a Tekion RO that was "written up but never dispatched / we missed it", and census every RO at a store carrying one recall campaign. Covers the RO status pipeline (UI label ↔ API enum), where the "To Be Dispatched" list comes from, why an RO never appears on it, the recall-sibling scan, and the report shape Joe expects. Built on BC RO 103410 / recall N262551720, 2026-09-17.
triggers:
  - RO was written up and never moved to ready for dispatch
  - we missed this RO
  - second one with that same recall
  - why is this RO sitting / stuck
  - which ROs have recall <campaign>
  - cars we missed in the dispatch queue
  - tech assigned but no hours
  - recall RO not worked
---

# Stuck-RO triage + recall-campaign census (Tekion)

Two questions arrive together and are answered from the same data pull:
1. **"Look at RO <n> — it was written up and never moved to the ready-for-dispatch screen, so we missed it."**
2. **"It's the second one with that same recall"** — i.e. find every RO carrying that recall and show which ones are stuck.

## 1. Identify the store FIRST (RO numbers collide across the 7 AMG stores)
Sweep `POST /repair-orders:search` `{"filters":[{"field":"documentNumber","operator":"IN","values":["<ro>"]}],"pageSize":10}`
across all dealers in `cfg["dealers"]` and disambiguate on `status` + `creationTime` (a RO with a
2016/2022 creationTime is a legacy record). A single store can return **two rows for the same RO#**
(e.g. a legacy `<dealer>_103410_<VIN>` shell + the live one) — the live one has a 24-hex `documentId`.

## 2. The RO status pipeline — UI label ↔ API enum (settled 2026-09-17)
The RO List **Status filter dropdown** is the authoritative enum order:
`Ready for Dispatch → Partially Assigned → Tech Assigned → In Progress → Ready for Invoice → Hold → Invoiced → Closed → Void`.

- **UI "Ready for Dispatch" == API `status: "UNASSIGNED"`.** Verified on 5 ROs (103541/103439/102822/103502/103535 all render "Ready for Dispatch" while the API says UNASSIGNED).
- The **"To Be Dispatched" tab is literally `status = Ready for Dispatch` AND no technician** (every row shows Technician `-`). It is a *work queue*, not a mailbox: **26 items at BC on 9/17/26, oldest opened 9/9** — so ROs routinely sit there 1–8 days.
- **An RO that already has a technician on it can NEVER appear in that list**, no matter how stuck it is. That is the whole mechanism behind "we never saw it".
- `assignee.technicians[].status == "PENDING"` is **normal** (= assigned, jobs not all completed). `COMPLETED` = that tech finished. It is NOT a "waiting for acceptance" flag — don't read it as one.
- **Auto-assign can bypass dispatch:** `/ro/dispatch-settings` (NOT `/service/settings/dispatch-settings`, which renders blank) → "Auto Assign Technician to Added Job". When ON, a write-up can hand an RO a tech the moment jobs are added and it skips the Ready-for-Dispatch bucket entirely. BC as found: that toggle ON, matching-skills ON, recommendation ON, deferred ON.

## 3. Recall campaign census (which ROs carry campaign X)
Campaign codes are **NOT opcodes** at GM — `opcode IN ["N262551720"]` returns **0**. The campaign lives
only in the **job concern text**, and the opcode is the generic `RECALL`. Method (script:
`/home/itadmin/tekion-reports/bc_recall_sibling_scan.py <CAMPAIGN> <DAYS>`):

1. Enumerate: `repair-orders:search` filters `opcode IN ["RECALL"]` + `creationTime GTE <now-NDays>`, pageSize 50, chain `meta.nextPageToken`. The **OPCODE tag is free on the search result** — use it to prefilter (BC/240d = 1,454 ROs ≈ 30 pages).
2. Fan out `GET /repair-orders/{documentId}/jobs` on each and substring-match the campaign against `job.concern.text` (case-insensitive). ~1,450 calls ≈ 10 min — run it as a **background process with `notify_on_complete`**, never foreground.
3. Enrich with `/ro-vehicle` (VIN/year/make/model/mileage) and `/ro-customers/{id}`.
4. Bucket by `status`; everything not CLOSED/INVOICED/VOID is "open" and worth a look. Also check for **duplicate VINs / duplicate customers** (the same car or person booked twice on the same recall).

**BC N262551720 result (for calibration):** 59 ROs in 8 months — it's a mass campaign, not a rare
event. So "the second one" is never a count of the recall — it's a count of *misses*. Present the open
ones in a table and ask which one he means by "the first one" rather than guessing.

## 4. Quantify the miss
Pull `labor.saleAmount` + the parts lines off a **completed** same-recall RO to state what was lost:
BC N262551720 = **$48.07 labor + camera p/n 42861580 $58.23 (~$106 GM pay)**. Then note whether the
stuck RO has the part line at all (103410 had none → the camera was never even ordered/pulled).

## 5. The BC recall write-up template
`MPVI (internal) + TPS (internal) + RECALL (warranty)` as three separate jobs is the store's standard
write-up for a recall visit — seeing that triad means the ticket was written correctly and the failure
is downstream (dispatch/tech), not at write-up. All three jobs flag **"Need Attention"** (empty Causes).

## 6. Report shape Joe expects
- **Timestamped as-found state** ("as found at 3:55 PM: status Tech Assigned, 0.00 hrs, $0.00, no parts line, not in To Be Dispatched") — the RO moves under you mid-investigation, so the timestamp is load-bearing.
- Customer / VIN / mileage / advisor / appointment booking source + promise time.
- Table of every other open RO on that recall, with the ones that look stuck flagged.
- The mechanism, stated with its confidence level (see pitfalls).
- An **automation offer**: daily stale-RO watch = open RO at Ready for Dispatch / Tech Assigned with **0.00 billed hours and age > 1 day**, recall jobs flagged.

## Pitfalls
- **`modifiedTime` is bumped just by OPENING the RO** (browser view or page render). Do not infer "someone edited this at 15:50" from `modifiedTime` — it's also a view-stamp. The same applies to the RO-list "RO Flag Updated Time". If the assignment/docedit time actually matters, say it isn't obtainable.
- **The RO status changes while you investigate** (103410 went TECH_ASSIGNED → IN_PROGRESS at ~16:14 because a tech finally started it). Re-read right before you send, and lead with the as-found timestamp.
- **No RO status/assignment history is exposed**: `/api/service-module/u/ro/{id}/audit|history|status-history|technician` all 404 empty. There is no API answer to "when was the tech assigned" — flag it as unknown; Joe accepts "I don't know yet" but not a confident wrong answer.
- `GET /repair-orders/{id}/ro-customers/{cid}` returns junk for internal accounts (`"americanmotorscorporation - 1251"`) — that's an internal/wholesale ticket, not a customer car. Don't present it as a customer name, and don't count it as a missed *customer*.
- **Background `terminal(background=true)` stdout can read as 0 lines while the job is clearly running** — don't conclude it's hung; have the script write its result JSON to disk and read that file (plus `ps -o etime,pcpu -p <pid>` to prove liveness).
- A GM recall job coded **CUSTOMER_PAY** instead of WARRANTY means GM won't pay — flag it whenever you see it in the census (found on BC 103413).
- Storage-state file `/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json` can look fresh (~73KB) but hold only 5 localStorage keys; for authenticated reads prefer the captured-header replay in skill `tekion-internal-api-access`.

## Related
`tekion-internal-api-access` (header capture + endpoints), `tekion-technician-queue-dispatch`
(auto-dispatch pulls a tech from the queue on RO create/reopen), `tekion-openapi-repair-orders`
(search/pagination/field rules), `tekion-recall-parts-appointment-workflow` (the parts-side recall queue).
