---
name: tekion-ro-close-blocked-triage
description: Triage a "we reopened the RO/invoice but still cannot close it" ticket at any AMG store. Verify server-side whether the reopen actually persisted (it often did NOT), inspect the live RO in the browser, and identify the real block (accounting period lock, cashiering-only reopen, user lock) before advising.
triggers:
  - cannot close RO
  - RO won't close
  - reopened invoice
  - reopen RO
  - close RO blocked
  - need attention on RO
  - ready for invoice stuck
  - causes must not be blank
  - cost center description is empty
  - what is wrong with this RO
  - lyft stuck in pending
  - transportation pending RO
  - cannot remove part
  - part stuck on RO
  - part return stuck
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

## Step 3c — "I can't REMOVE a part" tickets (verified TL RO 383381, 2026-07-30)

When the complaint is a stuck PART LINE (not a close block), diagnose in this order:

0. **Store unknown? Search documentNumber IN across all 7 dealers.** RO numbers
   recur across stores — 383381 hit BOTH st (CLOSED 2023, stale) and tl
   (IN_PROGRESS, modified yesterday). Pick the hit with the recent modifiedTime.
1. **API fan-out first** (jobs→operations→parts). The tell for this failure mode:
   the SAME partNumber appears TWICE — `+1` on one job and `−1` on another job,
   often at DIFFERENT prices (383381: +$76.55 on FLOORMAT vs −$113.39 on a REC
   job = net −$36.84 credit mismatch). A negative-qty line with positive
   `unitSaleAmount` and negative `saleAmount` = a processed RETURN.
   `createdByUserId.id` → `/users/{id}` tells you who posted each line.
2. **Why there's no delete option**: a part with status DELIVERED/Fulfilled that
   is tied to a **received SOR/PO** and/or a **Prepaid customer deposit** is
   LOCKED — Tekion renders NO trash icon on the row at all (verify: hover the
   row, scan buttons/`[class*="icon-"]` in its y-band; you'll only see
   drag-handle, badges, info, notes). Removal must go through a **parts-counter
   return**, never an RO-side line delete.
3. **Row badges are chevron-expandable, in-DOM (not popovers)**:
   - `SOR` badge chevron (`ro_partName_sorBadgeContainer` + adjacent
     `icon-chevron-down`) → SOR No, SOR Status, Requested By, SOR Date, PO No.
   - `Return` badge chevron (`ro_partName_returnBadgeContainer`) → return
     details: Quantity, Return Reference (RO#), Return Reason — and watch for an
     **unfilled required "Select a value" dropdown** left mid-workflow.
   - `Original Part Request` button links the return line to its source request.
   Read them by grabbing the part text node and walking up ~12-14 parents for
   innerText — `.ant-popover` queries return empty for these.
4. **Advise pattern**: a return posted on the WRONG job at the WRONG price should
   be voided/redone so it reverses the ORIGINAL billed line (prices cancel), and
   any prepaid deposit settled at the counter. Confirm intent (part fully off the
   RO vs cleanup) + exact error text before touching anything.
5. **If the goal is to VOID the ticket**: sequence is remove/return parts →
   job kebab (⋮ by "Created By…", ~(1186,201)) → **Void Job** (button disabled
   until parts are off) → RO-level void appears only after jobs voided. Full
   click-paths + the unsolved pending-return-processing gap in skill
   `tekion-ro-void-job-remove-parts`.

## Step 3d — READY_FOR_INVOICE stuck on job-level "Need Attention" validation (verified SCT RO 580200, 2026-08-24)

Third distinct failure mode, and the one the API is BLIND to. Symptom: `status:
READY_FOR_INVOICE`, job `COMPLETED`, `CLOSED_TIME` stamped in `schedule[]`, but
`/ro-invoices` returns **`data: {}`** (no invoice record) — the RO just sits
unposted for days.

**The API can tell you it's stuck but NEVER why.** `repair-orders:search`,
`/jobs`, `/operations`, `/ro-fees`, `/ro-coupons` all return clean, valid-looking
data. The blocking reasons are **UI-only validation strings** rendered in a
"Need Attention" block on the job card. You MUST read the RO page DOM.

**Where the answer lives** (`document.body.innerText` of
`/ro/repair-orders/<docId>/jobs/<jobId>`): a literal `Need Attention` line
followed by one string per blocker, e.g.
```
2
Need Attention
Causes must not be blank
The cost center description is empty
```
The leading number = blocker count. Just slice innerText — no vision needed.

Two seen on 580200 (Internal/house-account RO, opcode SAFECAT, $140):
1. **"Causes must not be blank"** — Job has Concern + a Corrections story line
   but an empty **Cause** field (tell: an `Add Cause` button still showing, and
   `input[placeholder="Type Cause here"]` with `value:""`).
2. **"The cost center description is empty"** — lives inside the **Manage Splits**
   modal → *Payer – Cost Center Details* table. Row 1 had Cost Center
   `We Owe / Due Bill - 3042`, 100%, Control/Control 2 **disabled**, and a
   **live, empty, required Description** input. There was also a half-started
   **second row** (Cost Center = `Select`, no %, no description).

**Reading the cost-center table** (the innerText of the whole RO page does NOT
include it until the modal is open):
```js
// after /mouse-clicking "Manage Splits"
var hdr=[...document.querySelectorAll('*')].filter(function(e){
  return e.offsetParent && e.children.length===0 &&
         e.textContent.indexOf('Payer - Cost Center Details')>=0;})[0];
var n=hdr; for(var i=0;i<6;i++) n=n.parentElement;   // 6 parents up = the block
n.innerText;                                          // the table as text
[...n.querySelectorAll('input,.ant-select')].filter(e=>e.offsetParent!==null)
  .map(e=>({cls:e.className,v:e.value,dis:e.disabled}));  // which fields are required/empty
```
`ant-input-disabled` = nothing to fill (fine). A plain `ant-input` with `value:""`
= the required-and-empty field Tekion is complaining about.

### ⭐ The move that made the diagnosis credible: a CONTROL RO
Don't just describe the broken RO — find a same-opcode RO that invoiced cleanly
and diff it. Free via the opcode filter:
```python
post("/repair-orders:search", {"filters":[
  {"field":"opcode","operator":"IN","values":["SAFECAT"]},
  {"field":"creationTime","operator":"BTW","values":[str(lo),str(now)]}],
  "pageSize":50})
```
Pick an `INVOICED` sibling, open its Manage Splits, compare. On 580512 (same
opcode / $140 / Internal) the cost-center table had **one** row with
Control/Control 2/**Description all disabled** and **zero** Need Attention flags.
That contrast — live-empty Description + a stray blank second row vs. all-disabled
single row — is what proves the finding instead of guessing.

**Also check the cost center is the RIGHT bucket.** 580200 was a PDI unit but its
cost center read `We Owe / Due Bill - 3042`, not PDI. That's a separate issue from
the two validation errors and worth flagging — it would post the $140 to the wrong
account even after the blockers clear. Per the never-guess rule: do NOT assert a
"PDI - 4440" option exists in that dropdown unless you actually opened it.

⚠ **"PDI 4440" conflates two different things** (clarified 2026-08-24/25). At SCT the
*cost center* in the Manage Splits picklist is labeled **`PDI - 2211`** (2211 = the
ASSET hold account, control `VIN_LAST_6`). **4440 SLS PRE-DEL SRV-TOY** is a **SALE**
account and is the *GL mapping target* for `Service Type = PDI` under
Fixed Operations → Services → Services-Internal — it is NOT a cost-center option.
So "the RO is going to PDI, 4440" mixes the cost-center layer with the GL-mapping
layer. Separate them explicitly in the answer. Full account table + mapping rows in
skill **`tekion-internal-cost-center-gl-routing`**.

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
  **COUNTERPOINT (2026-08-24): the reverse also happens — try BOTH boxes.** On the
  SCT RO list, typing 580200 in the GLOBAL "Search here..." + Enter did nothing
  (page stayed on /ro-list), while the **page-level expandable "Search..."**
  (root_expandableSearchField_expandableInput, ~x1025,y163) opened the omni-search
  drawer and produced the "RO #580200 | Tag #3TMLB" card immediately. Recipe that
  worked: /mouse the expandable input, tag it (e.setAttribute('data-jay','1')) to
  dodge selector collisions with the global box, /type on input[data-jay='1'],
  /press Enter, then /mouse the leaf element matching /RO #<num>/. Neither box is
  reliably "the" one; if the first does nothing in ~6s, switch to the other rather
  than debugging.

### :9223 / notification-toast traps hit on this task (2026-08-24)

- **ant-notification toasts STEAL your click coordinates.** Tekion pops
  RO/parts notifications continuously. /mouse returns success and nothing opens
  because document.elementFromPoint(x,y) is an ant-notification-notice-message
  overlaying the button. Diagnose with document.elementFromPoint(x,y).outerHTML;
  clear with document.querySelectorAll('.ant-notification').forEach(e=>e.remove())
  **immediately before every /mouse**, not once per page. (Same class of bug as
  the Pendo overlay, different element.)
- **Worse: a toast click NAVIGATES YOU AWAY.** Clicking through a notification
  jumped the SPA to /accounting/journalEntry/list and later
  /accounting/glaccountmapping/list mid-diagnosis. If a follow-up /eval shows an
  unexpected location.href, that's what happened — re-navigate to the RO URL,
  don't assume the session broke or that another user is driving the browser.
- **Guard /mouse against empty/off-screen coords.** A coord-finder that returns
  '{}' then api("/mouse",{}) = **HTTP 404** (server requires numeric x/y), and a
  freshly-navigated page can return **negative y** (e.g. y:-210) before layout
  settles so the click lands nowhere. Always poll until the element exists AND
  y>50, scrollIntoView({block:'center'}) first, then click.
- **/eval with arrow functions + optional chaining can 500 the server.** Some
  payloads using ?. or => returned HTTP 500 from :9223 itself. Rewrite in plain
  ES5 (function(){}, explicit null checks) and it works. A 500 on /eval is usually
  YOUR JS, not a dead browser — verify with a trivial
  /eval {"js":"JSON.stringify(location.href)"} before declaring the instance broken.
- **vision_analyze MIS-READ the cost-center block twice**, reporting the
  "Payer - Cost Center Details" section as "collapsed / not visible" when the DOM
  clearly had it expanded with populated rows. For dense Tekion tables trust the
  **DOM text** (n.innerText plus each input's value/disabled flags); use vision
  only for color/badge cues (the orange "Need Attention" icons) it can add.
