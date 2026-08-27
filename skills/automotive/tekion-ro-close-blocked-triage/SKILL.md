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
  - cannot invoice this ticket
  - we cant invoice
  - I need to add a new payer
  - can't add a payer
  - cannot invoice this ticket
  - we cant invoice
  - invoice checkbox greyed out
  - causes must not be empty
  - storyline text must not be blank
  - can't add a payer
  - add new payer is disabled
  - job stuck partially invoiced
  - blank payer on the split
  - payer count doesn't match
  - partially invoiced
  - job stuck partially invoiced
  - i need to add a new payer
  - split shows zero percent
  - invoice closed at zero dollars
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

## Step 3e — "WE CAN'T INVOICE THIS TICKET" — the 60-second recipe (verified TL RO 398524, 2026-08-25)

The most common shape of this ticket, and the fastest one to solve. **Do these
four things in order and you have the whole answer in about a minute — do NOT
start clicking around the RO first.**

**Symptom shape:** `status: IN_PROGRESS`, `/ro-invoices` → `data: {}`, most jobs
`COMPLETED` but **one** job still `IN_PROGRESS`, and the store just says "it won't
invoice."

### 1. Sweep all 7 dealers for the RO# (never assume the store)
Joe/the store rarely names the store. TL RO **398524** ALSO existed at ST/876 as a
CLOSED 2023 RO. Disambiguate on recent `modifiedTime` + `IN_PROGRESS`.

### 2. `/jobs` immediately tells you WHICH job blocks
```python
for jb in jobs: print(jb["jobNumber"], jb["payType"], jb["status"])
```
On 398524: jobs 1,3,4,5,6,7,8 = INTERNAL/COMPLETED, **job 2 = CUSTOMER_PAY /
IN_PROGRESS** ← that one job is the entire blocker. This is free and takes 2s.

### 3. Read the job-list innerText for the per-job "Need Attention" strings
Navigate `/ro/repair-orders/<rid>/jobs/<jid>` and slice
`document.body.innerText`. The **job-list rail on the left renders every job's
blocker count**, and the CURRENTLY-SELECTED job additionally renders its blocker
TEXT inline right under its "Need Attention" line:
```
2.
PORT2, CABIN - PORTFOLIO- PERFORM 2ND ...
Recommendation
In Progress
CP
0.70 ... $101.67
1
Need Attention
Causes must not be empty          ← only shown for the SELECTED job
```
⚠ **To read a DIFFERENT job's blocker text you must navigate to that job's URL** —
the other rows only show the count. Loop `/jobs/<jid>` per job id if you need them all.

### 4. Click the header **Invoice** button → Payers Consolidated View = the proof
`document.getElementById('invoice').click()` (id is literally `invoice`;
`data-test-id="@tekion-repairOrders-roDetailsPage-roHeader-invoiceButton"`).
It does NOT navigate — it opens the Payers panel appended to the SAME page (the
URL never changes, so don't conclude the click failed). Then read checkbox state:
```js
[].slice.call(document.querySelectorAll('input[type=checkbox]')).map(function(e){
  var r=(e.closest('.ant-checkbox')||e).getBoundingClientRect(); var l=e.closest('label');
  return {y:Math.round(r.y), dis:e.disabled, chk:e.checked, txt:l?l.innerText:''};});
```
398524 result — **exactly the picture the store sees**:
| Payer | Status | Invoice checkbox |
|---|---|---|
| 213124 PORTFOLIO | Open | `disabled:true` |
| 1212810 AMERICA DOWD | Open | `disabled:true` |
| 94227 Toyota of Lancaster (internal) | Ready for Invoice | `disabled:false, checked:true` |

**Disabled Invoice checkbox on the payers whose job is IN_PROGRESS = the block.**
(Contrast with Step 3b, where ALL controls incl. Print PDF/Resync were disabled on
a payer whose job WAS complete → that's the desync bug. Here Print PDF is disabled
too, but the cause is simply an incomplete job, not desync. Distinguish by job status.)

### 5. The Warnings accordion in Payers View is COLLAPSED — click it
`Warnings` (leaf element, ~x160,y208) collapses its contents. Before clicking, the
innerText just reads `Warnings` and vision reports "warning triangle, content not
visible." After a `/mouse` click it expands to the actual strings.
**On 398524 those were `Cost Amount for the job is going to be zero` + `The cost
center description is empty` — WARNINGS, NOT BLOCKERS.** Proof: the internal payer
carrying them was already `Ready for Invoice` with an ENABLED checkbox. Do not
report warnings as the root cause. The blocker is whatever the IN_PROGRESS job's
Need Attention says.

### 6. Diff against a control RO to predict the NEXT failure
Same opcode filter trick as Step 3d. For 398524 (opcode `PORT2`, TL, last 5 days):
- 398528 CLOSED → **0** Need Attention flags anywhere
- 398620 READY_FOR_INVOICE → flagged **`Storyline text must not be blank`**

That's how you learn TL's Pre-Invoice rules enforce **BOTH Cause AND Storyline** —
so telling the store "just add the Cause" would have them back in 5 minutes when
PORT2 then trips on the missing story line. **Always warn about the second rule.**

### 7. What the fix actually is (advisor/tech, ~30s)
Job 2 → **Add Cause** → type cause · expand the flagged op → **Add Story Line** →
type what was performed · **Save** → **Mark as Complete** · header **Invoice** →
the Open payers' checkboxes enable → **Invoice Selected Payer(s)**.

**STOP HERE — do not type the cause/story yourself.** That text is the technician's
diagnosis on a live customer RO; inventing it violates the never-guess rule and
falsifies the repair record. Offer: "give me the wording and I'll enter it, save,
mark complete and invoice in under a minute." Everything up to that point is
read-only and Jay should do it all autonomously (per the automation mandate) —
the ONLY handoff is the human-authored text.

### Which op is at fault, when a job has several
Compare `causes`/`corrections` per operation from `/operations`. On 398524 job 2:
`CABIN` had `causes:"dirty"` + `corrections:"REPLACED CABIN AIR FILTER."` (it came
in from an APPROVED recommendation, which populates both), while `PORT2` had
`causes:null, corrections:null`. **The recommendation-sourced op is complete; the
menu/base op is the empty one.** Job-level `causes` being null while an op has one
is normal — don't read job-level alone.

## Step 3f — PARTIALLY_INVOICED job with a ZEROED payer split (verified TL RO 398856, 2026-08-27)

Fourth distinct shape, and the one that fools you because **every other check comes
back clean**. Do not burn time hunting for Need Attention strings here — there are none.

**Symptom shape:** RO `READY_FOR_INVOICE`; all Internal jobs `CLOSED`; exactly one
CP job at **`PARTIALLY_INVOICED`**; `ro-invoices` DOES return records (unlike Step 3d/3e
where it's `{}`) — but every one has **`invoiceAmount: 0`** and `status: CLOSED`.

### The tells, in order of speed

1. **RO `tags` give it away for free** in the search result — look for
   `{'field':'JOB','value':'STATUS_PARTIALLY_INVOICED'}` alongside
   `STATUS_CLOSED`. That single tag distinguishes this mode from 3d/3e before you
   fetch anything else.
2. **`/jobs`**: 6 INTERNAL/CLOSED + `jobNumber 1, CUSTOMER_PAY, PARTIALLY_INVOICED`.
3. **`/ro-invoices` closed at $0** for BOTH payTypes (CUSTOMER_PAY and INTERNAL).
   Invoices that exist, are CLOSED, and total $0 while the job carries real money =
   the money was never assigned to a payer.
4. **Job-detail `innerText` — no modal needed.** The `Pay Split By Payer` panel
   renders inline (see `tekion-ro-payer-split-sunbit` READ section):
   ```
   Pay Split By Payer
   Payer            Split Amount   Split Percentage
   166920 - Amir Baig   CP   $0.00   0 %
   -                    CP   Deductible   -   %
   ```
   **CP payer at `$0.00 / 0 %` + a blank second row = nobody is holding the charge.**
   Meanwhile the job row above it shows the real sale: `0.50 hrs  $21.01  $61.37`
   (cost | sale), and every job row ends in `0 Need Attention`.
5. Reconcile the sale from `/operations` + parts so you can quote the exact stuck
   dollar figure: labor `saleAmount: 2909` (**cents** → $29.09) + billed parts
   $32.28 = **$61.37**. Quoting the number is what makes the diagnosis land.

### Root cause & the fix
The job cannot finish invoicing because its charge has no payer. Fix = **Manage Splits
→ Add New Payer → assign the amount** (full write path in
`tekion-ro-payer-split-sunbit`). Note the inverse relationship between the two skills:
that skill's #1 write-side trap is *"the payer you ADDED stays at $0.00/0%"*; here the
*ORIGINAL* payer is the one sitting at $0.00/0%. Same grid, same root behaviour —
the grid back-solves and somebody must hold 100%.

⚠ **STOP before choosing the payer record.** On a prepaid-maintenance opcode
(`TSC2` = Toyota Service Care 2) the correct payer is plausibly a Toyota/TSC
third-party account rather than the customer — but "plausibly" is a guess on a live
customer RO. Per the never-guess rule: report the stuck amount, show the split table,
and ask **which payer**. Everything up to that point is read-only and Jay does it
autonomously; the payer identity is the only handoff.

### API response-shape gotchas that cost real calls here
- **`repair-orders:search` results have NO `id` key.** `it['id']` → `KeyError` and
  your control-RO loop dies. The RO id is only reachable via the sub-resource links:
  `it['jobs']['id']` (or parse `it['jobs']['link']` = `/repair-orders/<rid>/jobs`).
  `documentNumber`, `status`, `modifiedTime`, `tags` are top-level and safe.
- **Every collection uses a DIFFERENT data key.** A generic
  `data.results or data.jobs or data` parser silently returns `[]` and prints
  nothing (looks like "no operations exist"):
  | endpoint | key |
  |---|---|
  | `repair-orders:search` | `data.results` |
  | `/jobs` | `data` is a **bare list** |
  | `/operations` | `data.roOperations` |
  | `/ro-invoices` | `data.roInvoices` |
  When a fan-out returns empty, dump `json.dumps(resp)[:2000]` before concluding
  the data isn't there.
- **A 429 burst can hit all 7 dealers at once and then clear on its own.** The
  opening cross-store sweep returned `HTTP 429` for ar/bc/bt/st/sv/tl/vc; the same
  query succeeded minutes later after the preflight ran. Don't launch a retry
  storm (thundering-herd rule) — do the browser-side prep work, then retry once.

## Step 3f — "can't invoice" with ZERO Need Attention flags = payer split, not validation (TL RO 398856, 2026-08-27)

Step 3e assumes the blocker is a Need Attention validation string. **If the job list
shows `0` Need Attention on every job and it still won't invoice, stop looking at
validation** — the blocker is the payer split on the money-carrying job.

Symptom shape: `status: READY_FOR_INVOICE`, one job `PARTIALLY_INVOICED` carrying real
dollars, every other job Internal/$0.00/Closed, and **both `ro-invoices` closed at
`invoiceAmount: 0`**. That last one is the giveaway — a job worth $61.37 cannot have
produced two $0.00 invoices unless nobody is holding the charge.

Read the split off the job page innerText (no modal needed), between
`Pay Split By Payer` and `Collapse All Operations`:
```
166920 - Amir Baig   CP  $0.00   0 %
-                    CP  Deductible  -  %      ← blank payer name
```
A `-` where a payer name belongs = orphaned payer. Confirm by diffing the **header chip
count vs Payers View row count** ("3 Payers" chip vs 2 listed rows).

**Do NOT recommend reopening as the fix without reading Payers View first.** On 398856
the reopen unlocked the payers completely (`Closed`→`Ready for Invoice`, checkboxes
enabled) and the split grid stayed hard-locked because the JOB was still
`PARTIALLY_INVOICED`. The lock is job-level. It also flipped 6 clean jobs from
`Closed`/0 flags to `Completed`/**2 Need Attention each**, creating new work.

Full triage, the disabled-`Add New Payer` diagnostic, and the escalation ladder
(Resync Payer → Cashiering → Tekion ticket) live in
**`tekion-ro-payer-split-sunbit`** § "I CAN'T ADD A PAYER".

## Step 3f — "CAN'T INVOICE" where one job is PARTIALLY_INVOICED with an ORPHANED payer (verified TL RO 398856, 2026-08-27)

Fourth distinct failure mode. Distinguish it from 3e immediately: in 3e the blocking job
is `IN_PROGRESS` with **Need Attention** text. Here the job is **`PARTIALLY_INVOICED`
with ZERO Need Attention flags anywhere on the RO**, and pre-invoice validation passes
clean. Nothing tells you what's wrong.

**Symptom shape:** `status: READY_FOR_INVOICE`; six jobs `CLOSED`; one CP job
`PARTIALLY_INVOICED` holding real money; `/ro-invoices` shows BOTH payer invoices
`CLOSED` at **`invoiceAmount: 0`**. RO search `tags` include
`JOB: STATUS_PARTIALLY_INVOICED`.

### The 3-second detection: header chip count ≠ Payers View row count
Job header chip said **"3 Payers"**; Payers View listed **2**. That delta IS the
orphaned payer. Corroborate in the split panel — slice innerText between
`"Pay Split By Payer"` and `"Collapse All Operations"`:
```
166920 - Amir Baig   CP   $0.00    0 %
-                    CP   Deductible   -   %      ← blank payer name, holds 100%
```
A `-` where a payer name belongs, on a row holding 100% of the money, = orphan.

### Order of operations (learned the hard way — I did this backwards)
1. **Audit Logs FIRST.** It contains the root cause, proves/kills the Cashiering theory,
   and shows exactly which payers a reopen touched. Expand all `Show` links.
2. Payers View — read actual row status before recommending anything.
3. Only then consider Resync / Cashiering / ticket.

I instead theorised payer-reopen → resync → Cashiering across several turns; Joe cut it
off with **"IT WAS NEVER CASHIERED"** — a fact the audit log had already contained
(`NA → Paid → Closed`, no cashiering step).

### Root cause pattern: mid-stream opcode swap on a prepaid-maintenance job
```
Job Details - Job 1  07:34 AM  by <advisor>
  Fees HW   Fees   : Deleted Fees → None
  Operation Details  Opcode : TSC3 → TSC2
```
Opcode changed **after parts were filled** (07:32). Swapping a prepaid-maintenance
opcode in place rebuilds the payer/deductible structure beneath a job that already has
parts + a payer → deductible row orphaned. Not specific to TSC2/TSC3; any such pair.

### Why a reopen does NOT fix it
An RO reopen releases the **payers** (both went `Closed` → `Ready for Invoice`, all
checkboxes enabled) but the **job stays `PARTIALLY_INVOICED`** and Manage Splits stays
hard-locked. The orphaned payer has **zero audit entries in the RO's whole history** —
never NA, never Paid, never Closed — so there is no record to reverse.
⚠ The reopen is not free: jobs 2–7 flipped from `Closed`/0 flags to `Completed`/**2 Need
Attention each** (TL enforces Cause AND Storyline, §3e). Warn before recommending it.

### Everything is read-only once PARTIALLY_INVOICED
`concern`, `causeText_*` (also `readOnly`), `storyLine_*`, all labor fields,
`primaryPayerId`, job `Save`, `Mark as Complete` — all `disabled`. Job kebab offers only
`Job Clocked Time · Job External Note · Tech Flag Hrs`. **You cannot edit the opcode to
undo the swap.** Prove it by dumping input `disabled` flags, don't assert it.

### Resync Payer: 200 ≠ fixed
`POST /api/service-module/u/RO/<roId>/payer/resync` → `200 "Payer data resynced
successfully."` and **nothing changed**. Its own confirm modal states the scope —
"update attributes like the cost center, pay type and labor rate … based on their latest
Customer Management profile." Attribute refresh only; it cannot recreate a missing payer.

### Outcome: Tekion support ticket (no UI fix exists)
```
TL (dealer 1092) RO 398856, job 1 (TSC2, $61.37) — orphaned payer, job frozen in
Partially Invoiced. At 07:34 the advisor changed the job opcode TSC3 → TSC2 and deleted
the HW fee in the same edit (audit log), after parts were filled at 07:32. Split grid
shows a Deductible column at $21.01 / 100.00% with a BLANK payer (-). RO header reports
3 Payers; Payers Consolidated View lists 2. Invoiced 08:54, closed 09:04, NEVER
cashiered. RO since reopened — audit shows only I Status: Closed→NA and CP Status:
Closed→NA; the third payer has ZERO audit entries, so there is no record to reverse.
POST /payer/resync returns 200 with no effect. Job 1 remains Partially Invoiced with the
full job panel read-only and Manage Splits locked (Add New Payer + all split fields
disabled). Pre-invoice validation passes clean.
Request: remove/repair the orphaned deductible payer on job 1 so the job can be invoiced.
```

### Before answering "how do I stop this recurring?" — fleet-scan first
Free API sweep of the whole opcode family (250 TL ROs / 90 days across TSC1–TSC5)
returned **zero** other `PARTIALLY_INVOICED`. So it is NOT an opcode config defect and
there is nothing to "fix" in the opcodes. Prevention that is actually true: once parts
are filled, **void the job and re-add under the correct opcode** rather than editing the
opcode in place. No Tekion setting was found that gates opcode changes (approval rules
exist for labor hours and pay type only) — say so rather than inventing a toggle.

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

### :9223 traps hit on TL 398524 (2026-08-25) — screenshots, clicks, drift

- **`/screenshot` on :9223 is a GET that returns JSON, not a PNG.** `curl -X POST
  localhost:9223/screenshot` → `Cannot POST /screenshot`. Correct call is
  `curl -s localhost:9223/screenshot -o /tmp/x.png` — but the body is
  `{"screenshot":"<base64>"}`, so the file is **JSON text, and `vision_analyze`
  rejects it with "Only real image files are supported."** Decode first:
  ```python
  d=json.load(open("/tmp/x.png")); open("/tmp/real.png","wb").write(base64.b64decode(d["screenshot"]))
  ```
  Endpoint list on this server: /click /console /cookies /eval /health /mouse
  /navigate /pages /press /screenshot /snapshot /type /url.
  ⚠ The `browser_vision` / `browser_*` MCP tools open a SEPARATE unauthenticated
  context and return a BLANK page — never use them for :9223 work.
- **`/mouse` uses viewport coordinates; the viewport is only 1280×720.** A
  `getBoundingClientRect()` y of 892 or 1005 is BELOW the fold, and the click
  silently lands on nothing (returns `success:true`). Either `scrollIntoView`
  first, or **prefer `element.click()` via /eval** for buttons with a stable id —
  `document.getElementById('invoice').click()` worked when the /mouse at the same
  coords did nothing.
- **Guard every coord-finder against `undefined`.** `filter(...)[0]` returning
  undefined then `.scrollIntoView()`/`.parentElement` throws
  `TypeError: Cannot read properties of undefined` and the whole /eval fails.
  Return `{none:1}` and branch on it.
- **Collapsible/virtualized sections mean "element not found" ≠ "not there".**
  `Op2.` / `Mark as Complete` / `Type Cause here` all vanished from the DOM when
  their section collapsed or the panel scrolled. Re-navigate to the job URL to
  reset state rather than hunting.
- **Dealer/page drift is aggressive on :9223.** Between two adjacent tool calls the
  SPA landed on `/service/settings/ro-settings` and later `/ro/pdf-settings`
  without any navigation from me (stray click-through / another session). ALWAYS
  re-`/eval` `location.href` before trusting a DOM read, and re-navigate to the RO
  URL if it moved.
