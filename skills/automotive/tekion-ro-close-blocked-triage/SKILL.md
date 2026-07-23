---
name: tekion-ro-close-blocked-triage
description: Triage a "we reopened the RO/invoice but still cannot close it" ticket at any AMG store. Verify server-side whether the reopen actually persisted (it often did NOT), inspect the live RO in the browser, and identify the real block (accounting period lock, cashiering-only reopen, user lock) before advising.
triggers:
  - cannot close RO
  - RO won't close
  - reopened invoice
  - reopen RO
  - close RO blocked
  - lyft stuck in pending
  - transportation pending RO
---

# Tekion "Cannot Close RO" Triage

When a store says "I reopened the invoice and the RO as requested, we still cannot
close the RO" — do NOT take the "reopened" claim at face value. Verified case
(SCVW RO 371361, 2026-07-15): store insisted it was reopened, but the RO record's
`modifiedTime` was still the ORIGINAL close timestamp from a month prior → the
reopen never persisted server-side at all.

## Step 1 — OpenAPI ground truth (fast, no browser, ~30s)

```python
import sys, json, urllib.request, time
sys.path.insert(0, "/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg = load_config(); tok = get_token(cfg)
BASE = cfg["base_url"] + "/openapi/v4.0.0"
h = {"Authorization": f"Bearer {tok}", "app_id": cfg["app_id"],
     "dealer_id": cfg["dealers"]["sv"],  # ar/bc/bt/st/sv/tl/vc
     "Content-Type": "application/json"}
# search by documentNumber IN [<ro#>] → documentId, status, tags, assignee, modifiedTime
# GET /repair-orders/{rid}/jobs, .../operations, /ro-invoices, /ro-vehicle
```

Read off the search result + ro-invoices:
- **`status`** — still CLOSED? Then the "reopen" did not happen server-side.
- **`modifiedTime`** — THE KEY TELL. If it equals the original close time (weeks
  old), NOTHING has touched the RO since; the reopen attempt errored/was dismissed
  client-side. A real reopen stamps modifiedTime = today.
- **`roInvoices[].status` / `closedTime` / `invoiceAmount`** (cents — /100!) —
  invoice-level state, payType, who closed it (`closedByUser.id` →
  `/users/{id}` resolves the name).
- Jobs/operations: any op not CLOSED, parts with `fulfillmentStatus: HOLD`,
  pending recommendations = legitimate close blockers.

## Step 2 — Live browser verification (:9223)

1. Switch dealer via the UI pill (localStorage set does NOT work). Verify
   `currentActiveDealerId`.
2. Open the RO: navigate `/ro`, type RO# in the global "Search here..." box,
   Enter, `/mouse`-click the "RO #<num>" result card. Lands on
   `/ro/repair-orders/<docId>/jobs/<jobId>`.
   (⚠ `/ro/service/<docId>/details` renders blank.)
3. Kill Pendo overlays after nav: `document.querySelectorAll('[id*=pendo],[class*=pendo]').forEach(e=>e.remove())`.
4. Screenshot → `vision_analyze` for status badge, red banners, holds,
   pending recommendations, payer state.

## Step 3 — Root-cause candidates when "reopen didn't stick"

1. **Accounting period lock** — RO closed in a prior month that's now locked in
   accounting; Tekion refuses to reopen/re-post the invoice into the locked
   period. Most common for month-old ROs.
2. **Cashiering-level-only reopen** — reopening a receipt/invoice in Cashiering
   does NOT reopen the RO document; RO stays CLOSED and "Close RO" then errors
   (nothing open to close).
3. **RO soft-locked by another user** — open in someone else's browser session
   ("locked for other users").

4. **Lyft/transportation stuck in Pending** (verified SCT RO 573681, 2026-07-15) —
   the Tekion↔Lyft integration blocks RO close while the ride request is in
   Pending. Root cause in that case: the ride was requested but the **Lyft fee
   was never added to the RO** ("YOU DID NOT ADD FEE FOR LYFT" — Adam Esquivel);
   fix = settle/complete the Lyft request AND add the fee, then close.
   UI anatomy: the transport chip is `div#transportType` (`.transport-status`,
   classes `ro_transportDropdown_*`) in the RO header next to "RO Notes"; the
   Lyft job itself appears as an Add-on job line (opcode LYFT). To check current
   state: RO status pill = `[class*="ROInfoTab_status"]`, and DOM-scan for any
   leaf element matching /pending/i — zero hits + pill "Closed" = resolved.
   **Check the internal-notes trail FIRST** (RO Notes drawer) — it often contains
   the whole story (who flagged it, why, who fixed it, timestamps). In this case
   the store had already fixed it 20 min before the ticket; a "still pending"
   report can just be someone's stale screen — tell them to refresh.

## Step 3b — The OTHER failure mode: RO stuck IN_PROGRESS with an un-invoiced payer (SCVW RO 371316, 2026-07-15)

If Step 1 shows `status: IN_PROGRESS` (not CLOSED), the block is almost always **one
payer never invoiced** while the others are Paid. Diagnose:

1. **API tell**: `ro-invoices` returns invoices only for SOME pay types (e.g. CP +
   WARRANTY both PAID) while `jobs` shows jobs on another payType (e.g. INTERNAL)
   stuck at `COMPLETED` — those completed-but-never-invoiced jobs are the blocker.
   Classic source: **add-on jobs added AFTER the original invoices** (deductibles,
   keyfob batteries) whose pay type was later flipped (check Audit Logs for
   "Pay Type: CUSTOMER_PAY → INTERNAL").
2. **Payers Consolidated View** (RO page → top-right kebab `.icon-overflow` ~(1260,96)
   → "Payers View"): one row per payer with status Invoiced/Open + `Invoice`,
   `Print PDF`, `Resync Payer` checkboxes and bottom-right **"Invoice Selected
   Payer(s)"**. Expand a payer row via its **caret icon `icon-caret-right`** (left
   edge, ~x113) to see the per-job/per-part line items + tax totals for that payer.
   Hover the charge icon (`ro_chargeCustomer_chargeCustomerIcon`) to read the
   account's Credit Balance tooltip (rules out credit-limit blocks).
3. **THE SMOKING GUN — all Payers View controls disabled**: if the Invoice checkbox
   on the Open payer AND Print PDF AND Resync Payer are ALL `ant-checkbox-disabled`
   (verify: scan `input[type=checkbox]` `.disabled` in the row's y-band) with no
   tooltip, no toast, no hold, recs dispositioned → the payer records are DESYNCED
   from the RO, typically after repeated payer reopen/re-pay cycles. Not fixable
   from the UI → advise: everyone out of the RO (soft-locks), retry; then Resync
   Payer if it enables; else Tekion support ticket.
4. **Audit Logs** (same kebab → "Audit Logs", then click every "Show" link via JS
   `.click()` to expand "2 items updated" entries): reveals the reopen LOOP pattern —
   e.g. Mo reopening W+CP payers (Paid→NA) then re-paying minutes later, never
   touching the Internal payer. That's why the store's reopen "did nothing".
   Also surfaces pay-type flips and price edits with who/when.
5. **Recommendations are NOT a blocker if dispositioned** — "Deferred" counts as
   responded (Summary shows Responded: 2); only un-dispositioned recs trip the
   Pre-Invoice "Pending Recommendations Error" rule.
6. **RO Clocked Time** (kebab item) — confirm no open tech clockings (Actual hrs
   present, nothing running).

Flag to the store in the advice: any pay-type flip found in the audit log (e.g. a
CPO deductible moved from CP → Internal) — confirm intent before they invoice it
to the house account.

## Step 4 — Advise (don't guess — per Joe's never-guess rule)

Ask the store for:
- The **exact error text** when they hit Close (screenshot; the red toast
  bottom-right disappears fast).
- **The underlying intent** — why reopen a closed RO? If it's a $ correction on
  a prior-month invoice (esp. internal/inter-company payer), the right path is
  likely an adjustment/credit, NOT reopen-edit-reclose.

Report: current server-side state, the modifiedTime proof, the candidate causes,
and the two questions. Don't state a root cause without the error text.

## Pitfalls
- Tekion $ = CENTS everywhere in OpenAPI (30000 = $300.00).
- `(j.get("concern") or "")` can be a dict on some jobs — don't slice blindly.
- :9223 `/eval` param is `js` (not `expression`); `/navigate` body `{"url":...}`
  POST. Deepest-element click: collect candidates whose innerText `.includes()`
  the RO#, sort by innerText length ascending, `/mouse` the first.
- **:9223 DEALER DRIFT mid-investigation** (hit twice this task): between turns the
  browser can silently flip to another store (876/ST) — a direct RO-URL navigate then
  lands on `/jobs/new` with "Something went wrong". ALWAYS re-verify
  `currentActiveDealerId` before every navigate; if wrong, re-switch via the pill.
- The per-payer row kebab in Payers View only offers "Payers Details" (reference
  number) — the invoice actions are the row checkboxes, not the kebab.
- Internal charge accounts (e.g. "1244211 Alfa Romeo of San Jose" at SCVW) show
  as CP payer — inter-company detail work, worth noting in the advice.
- **:9223 lane contention** — if another Jay session is actively driving :9223,
  the dealer context can flip UNDER you mid-task (saw dealer 876→826 between
  turns). Tell: `currentActiveDealerId` changed without you touching it. Don't
  fight it — move to the :9225 subagent-lane browser. Cold-start if refused:
  `cd /home/itadmin/persistent-browser-2 && rm -f browser-data/Singleton* && HOME=/home/itadmin xvfb-run -a node server.js` (background). Its persisted
  browser-data usually restores auth on `/navigate` to /home ("Welcome back",
  default dealer 1251) — no token injection needed; then UI-switch dealer.
- The RO list page's page-level "Search..." box may return nothing for a valid
  RO#; the GLOBAL "Search here..." box (top, ~x431,y33) reliably surfaces the
  "RO #<num> | Tag #<n>" card — type via native value-setter, dropdown appears
  ~3s later, `/mouse` the card. If landing throws "No such ro exist"/"Something
  went wrong", just re-`/navigate` to the captured `/ro/repair-orders/<docId>/jobs`
  URL — transient SPA error.
