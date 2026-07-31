---
name: tekion-ro-void-job-remove-parts
description: Remove parts from a Tekion RO and VOID the ticket. Per Joe - you must VOID THE JOB first, then the RO-level void line appears. Covers the part-row kebab Return Part flow, the Void Job modal and its remove-parts-first gate, and the parts-fulfillment side. Verified live on SCT test RO 574398 (2026-07-31). Contains one documented UNSOLVED step - do not guess past it.
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

## ⚠ UNSOLVED — processing the pending part return (DO NOT GUESS)
The "Request Pending" −1 row does NOT get processed by:
- Parts RO Sales → Fulfillment → open RO → **Fulfill** button → Order/Fill
  modal → Submit. That toasts "Successfully updated the Reserve/Hold/Fill
  details" but the OpenAPI parts ledger still shows the old lines; the pending
  request row just disappears from the RO view and the request seems to
  evaporate/stay unprocessed. (Tried twice, verified via
  `/repair-orders/{rid}/jobs/{jid}/operations/{oid}/parts` — lines unchanged.)
- The **"Requests"** toggle next to the job header on the fulfillment detail
  page — it's a READ-ONLY popover (Part/Qty/Price, no accept button).
The RO's existing −1 line (id 96) was created 7/17 by Joe, so a working
process-return path exists — **ask Joe to show it** (likely a parts-counter
Process Return flow). Update this section when learned.

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
