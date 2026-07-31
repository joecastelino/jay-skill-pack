---
name: tekion-ro-void-job-remove-parts
description: Remove parts from a Tekion RO and VOID the ticket, OR flip the job to INTERNAL pay and close at $0 (Joe's preferred cleanup). Void order - void JOB first, then RO-level void appears. Covers Return Part flow, deleting stuck Request Pending returns via the fulfillment row kebab Remove, the Void Job remove-parts gate, pay-type CP-to-I switch with Confirm PayType Change modal, and the Internal cost-center requirement. Verified live on SCT test RO 574398 (2026-07-31).
---

# Tekion: Remove Parts + Void an RO (job first, then RO)

**The order (Joe, 2026-07-31): "You have to void JOB then the void line will come."**
Void the job(s) → only then does the RO-level void option appear. And the Void Job
modal itself is GATED: *"Void cannot be reversed. To void you have to remove parts."*
— the blue **Void** button stays DISABLED until the job's parts are off.

So full sequence: **remove/return parts → Void Job (per job) → RO void line appears → void RO.**

## Verified click-paths (SCT test RO 574398, :9223 browser)

### 1. Remove a part from the RO side — "Return Part"
- Each billed-part row has a **kebab (⋮) at far right (x≈1866)** with exactly two
  options: **Causal** and **Return Part**.
- **Return Part modal**: Referential Return checkbox (checked), Return Status
  "Request Pending", Return Reference = RO#, Parts (prefilled), Quantity
  auto-fills **−1** (per fulfilled qty), Unit/Total price auto-fill, **Return
  Reason*** dropdown (SCT options: Incorrect Part Ordered by Customer w/
  Restocking Fee / Incorrect Parts Ordered by Parts Advisor / Customer doesn't
  need / Defective / Defective-Warranty / Totaled by insurance 10%/20% /
  backorder return / **Other**). Picking **Other** exposes a required text
  field — **Joe says just type "void"** when voiding. → **Submit**.
- Result: a new row appears in Billed Parts with qty −1, status **"Request Pending"**.

### 2. Void Job
- Job-card kebab = the **icon-overflow at (≈1186,201)**, in the header row with
  "Created By … on <date>" (NOT the RO header kebab at (1315,76), and NOT the
  trash icons — the trash at y≈377 deletes the CAUSE row, y≈551 deletes the op).
- Menu: Insurance/Warranty Split, Job Clocked Time, Job External Note, Job
  Split, Sublet Job, Tech Flag Hrs, **Void Job**.
- **Void Job modal**: banner "Void cannot be reversed. To void you have to
  remove parts.", concern line, **Reason for Void** (plain ant-input — "void"
  is fine), Labor section ("No Technicians are clocked in"), Parts table
  (read-only, no per-row remove controls IN the modal), **Cancel / Void**.
- **Void stays disabled while any part line is still on the job** (net-$0 with
  +1/+1/−1 lines was NOT enough — lines must actually be removed/fully
  returned). Reason text alone does not enable it.

### 3. RO-level void
- NOT YET SEEN. The RO header kebab menu (Add/Edit Coupon, Add/Edit Fee, Audit
  Logs, Cashier, Hold, Invoice Pdf Preview, Media, Profit/Loss View, RO Bulk
  Action, RO Clocked Time, Vehicle Update, View Posting Preview, View RO PDF)
  contains **no Void** while jobs are live. Per Joe it appears after the job(s)
  are voided. Document the exact location when first seen.

## ✅ SOLVED — removing a stuck "Request Pending" part return (2026-07-31)
The Fulfill → Order/Fill → Submit path NEVER processes a pending RETURN request
(toasts success but ledger unchanged — that flow is for ordering/filling, not
returns). The working path is to **DELETE the pending return row from the
fulfillment grid**:

1. Open the RO's fulfillment detail
   (`/parts/ro-sales/details/parts-fulfillment/<roNum>/<docId>/<fulfillId>`).
2. If banner "**<user> is currently using this page**" shows, click **Unlock**
   → Warning modal "previous users unsaved actions would be lost… proceed?" →
   **Yes**. (Stale locks from your own earlier visits count too.)
3. Hover the part grid rows. Row kebabs (⋮ at x≈1215) differ by row type:
   - Fulfilled sale row: `Add Comment / Move Part / Update Negative Sale / Return Part`
   - **Pending-return row: `Add Comment / Update / Remove`** ← this one
4. Kebab on the pending-return row → **Remove** → modal "Remove Part —
   Deleting this part here will also remove this from RO. Are you sure?" →
   **Ok Delete** → toast "**The return part was deleted. Please save/refresh
   to see latest updates.**"
5. Exit via **Cancel → Ok** (release lock). Back on the RO, the pending −1
   row AND its paired request are gone.

Note: this *deletes the return request*; the previously-Fulfilled −1 return
line stays as a real ledger line. Netting +1/−1 fulfilled lines = $0 job.

## Alternative to voiding: flip the whole job to INTERNAL and close (Joe often prefers this)
Joe 2026-07-31: "switch the whole ticket to internal and close it, it should
balance to zero." Cheaper than void when the goal is just a $0 test/cleanup RO.

1. **Gate:** clicking the pay-type radio while ANY return rows exist toasts
   "**Caution — Remove Returned parts to proceed with Pay Type change**".
   First delete pending returns (above). Fulfilled net-zero return PAIRS also
   had to be cleared in our case (the paired +1/−1 rows vanished with the
   request delete, leaving 1 clean +1 line; the switch then worked).
2. **Pay Type radios CP / W / I** live on the JOB FORM (ant-radio-button-wrapper
   NOT inside `[class*=footer]` — there's a duplicate group in the RO footer;
   use the job-form one, ≈(684,385) when job scrolled to top).
3. `/mouse` click **I** → **Confirm PayType Change** modal (shows Existing
   $310/hr CP vs Updated $250/hr Internal pricing) → **Ok** → radio flips to I.
4. Click job **Save** → toast "Job Updated". RO header goes **Ready for Invoice**.
5. **Internal jobs REQUIRE a Cost Center** — job card flags "Need Attention:
   Cost Centers Should not be Empty". Cost Center select is on the job form
   below the op (a 'Select' placeholder, SCT options incl. Service Dept
   Policy-7113, Parts Dept Policy-7115, Company Vehicle Service-7503, PDI-2211,
   We Owe/Due Bill-3042…). **ASK JOE which cost center** — it's a GL decision.
6. Then **Invoice** (header button; disabled until cost center set) → close.
   Internal RO bills the store, customer balance $0.

Other gotchas found:
- "RO Bulk Action" drawer (RO header kebab) has left-nav items Internal Split /
  Internal cost center / Void job / Re open etc., but they were ALL
  `disabledHeading` (cursor not-allowed) on an un-invoiced RO — not the path.
- Job Save button = bottom-right of job form; success toast is "Job Updated".

## Fulfillment-page mechanics (hard-won)
- Fulfillment list search: the expandable box (`placeholder "Ctrl + Shift + L"`)
  needs **Clear filters first** (Status defaults In-Progress/Pending/Submitted)
  AND per-char typing via native value-setter + keydown/keyup + Enter — a single
  setter+Enter does nothing. If bucket counters (New Part Requests etc.) get
  clicked, filters wedge — hard re-navigate to
  `/parts/ro-sales/parts-fulfillment` to reset.
- Open the RO's fulfillment: click the RO# cell → lands on
  `/parts/ro-sales/details/parts-fulfillment/<roNum>/<docId>/<fulfillId>`.
- Opening it **soft-locks it** ("This Fulfillment has been locked for other
  users") — ALWAYS exit via **Cancel → Ok** to release, never navigate away.
- OpenAPI parts truth: `GET /repair-orders/{rid}/jobs/{jid}/operations/{oid}/parts`
  → `data.parts[]` (jobs list = `data.jobs`, operations = `data.roOperations` —
  inconsistent envelope keys). quantities[] has SALE/DELIVERED/SOR/RESERVED/HOLD.
  $ in CENTS.

## :9223 driving pitfalls (this session)
- `/screenshot` is **GET** (POST → "Cannot POST"); response JSON `{screenshot:
  base64}` — decode before vision_analyze.
- Heredoc JSON with embedded `\n` in strings breaks the server's body-parser —
  write JS to a file and use a tiny python wrapper that json-wraps it
  (`/tmp/ev.py` pattern).
- Kebabs/menu items need full mousedown/mouseup/click MouseEvent dispatch;
  ant-dropdown items are leaf elements matched by exact innerText.
- Return Reason ant-select won't open via element dispatch — `/mouse` click its
  coords, then options are `.ant-select-dropdown:not(.ant-select-dropdown-hidden)
  .ant-select-item`.
- Toast area accumulates cross-store "Fulfilment Request" noise — match toast
  TEXT, don't assume the newest toast is yours.

## Cross-refs
- `tekion-ro-close-blocked-triage` Step 3c (locked part rows, return badges)
- `tekion-parts-sales-orders` (counter returns, CM credit memos)
