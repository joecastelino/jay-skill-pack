---
name: tekion-cashier-other-payment-error
description: Diagnose a Tekion Cashiering failure — either the generic "error something went wrong" on an "Other" payment to a GL account, OR a greyed-out `Collect Payment` button / insurance-split payment error. Read-only diagnostic playbook — covers the Control type-ahead trap, open-job blockers, CVSC/contract payers, GL controlField config, and the Split-Type-change-un-invoices-the-RO trap. Use when a store says "I can't cashier this RO", "payment error on the insurance split", or "Other close to <GL> errors out".
---

# Tekion Cashiering — "Other" payment throws "something went wrong"

Status of knowledge: the trap in step 2 is **confirmed**. The blockers in step 4 are
**strong candidates, not yet proven** on a live fix. Say so when reporting.

## When to use
- "I'm trying to cashier RO N. If I do an *Other* close and select <GL account>, I get
  *error something went wrong*."
- Any Cashiering error with **no field-level red text** — that pattern means the
  rejection is server-side, not front-end validation.

## Rule 0 — this is a READ-ONLY job unless told otherwise
Joe's phrasing "just run the diagnostics" = change nothing.
**Never click Collect Payment / Post — it posts money.** If you need the true server
error body, arm an XHR capture and have *Joe* click it.

## Step 1 — Pull the RO's real state via API before touching the UI
`GET /api/service-module/u/ro/<roObjectId>` (NOT `/repair-orders/<id>` → 404).
Record for every payer: `payerId`, `name`, `payType`, `subPayType`, `status`, amount.
Record for every job: index, `payType`, `status`.

Reconcile the dollar figure the store is trying to collect against the sum of the
`READY_FOR_INVOICE` payers — it usually equals two payers combined (±1¢ rounding).
That tells you which payers are actually in play.

## Step 2 — THE TRAP: the Control field is a TYPE-AHEAD
This has produced two wrong root-cause calls. Read it twice.

On the **Other Details** payment form, clicking the **Control** field renders
**zero option nodes**. `document.querySelectorAll('[id*=-option-]')` returns `[]`
and a screenshot shows an empty popover / "No Match Found".

**That is normal.** It is a lookup that only queries once you type.

Type a few characters of the payer name (e.g. `EAN`) → it fires
`/api/lookup/search` → returns e.g. `1356258 - EAN`.

Do **not** conclude "the Control dropdown is broken / the GL has no valid controls"
from an empty popover. Type first, always.

Corollary trap: the **Control Type** dropdown offers only `Customer` and `Custom`
and does *not* change with the selected GL account. That looks like a
control-type mismatch bug versus a `controlField: REPAIR_ORDER` account. It is a
red herring — stores successfully close Other payments to these accounts every day.

## Step 2b — VARIANT: `Collect Payment` is GREYED OUT (no error toast at all)
Confirmed live on **BC 99491, 2026-08-29**. Different failure mode from the
"something went wrong" toast — treat it separately.

**Isolate the amount first, in one pass.** Type several different amounts into the
payment Amount field and read the button's `disabled` attribute after each:
exact balance, balance ±1¢, and a round number well under balance. If it stays
disabled at *every* amount, **the amount is irrelevant** — stop theorizing about
over/under-payment and go look at payer status.

The real cause in that case: **nothing has been invoiced.** Invoice header reads
`Open` and every payer is `Ready for Invoice`, not `Invoiced`. Tekion will not let
you collect against a payer that has not been invoiced, so the button is dead
regardless of what you type. Fix = **Invoice Selected Payer(s)** in Payers
Consolidated View first, then cashier.

Do NOT lead with an overpayment theory. A few-cent delta between collected and
owed is real and worth flagging, but it is almost never why the button is disabled.

### 2b-bis — "RO N can't be charged to <GL acct> in Cashiering"
Same family. Confirmed again on **BC 100569, 2026-08-29** (2021 Durango, FRESNO
COUNTY SHERIFF, $127.14, acct **220 ACCOUNTS RECEIVABLE - CUSTOMERS**).

Fast triage, in this order — all read-only, ~4 API calls:
1. RO status. `READY_FOR_INVOICE` + `GET /api/service-module/u/ro/<id>/ro-invoices`
   returning `{}` = **not invoiced yet**. That alone explains the failure. This
   resolved itself the moment the payer got invoiced ("it started to work").
2. Target GL's control config (Step 5 search). `220` = ASSET,
   `controlField: CUSTOMER`, `controlNumberMandatory: true` — a mandatory control
   that cannot resolve until there's an invoiced A/R customer to point at.
3. Cashier panel per payer. An internal/house payer
   (e.g. `americanmotorscorporation-1251`) commonly shows
   **"No payment modes are setup"** with Transactions (0) — that is the *internal*
   side and is expected; make sure the store is on the **customer** payer, which
   shows Card/Cash/Check/OEM/Other/Gift Card.
4. Need Attention warnings. `Cost Amount for the job is going to be zero` and
   `The cost center description is empty` are **warnings, not blockers** (restated
   because they keep looking like the culprit). Payers Consolidated View with
   Invoice / Print PDF / Resync all enabled = no desync, no orphan payer.

**Expect these to self-resolve.** Several "can't charge to X" reports have cleared
on their own between the report and the diagnosis, because the store invoiced the
payer in the meantime. Do the read-only sweep anyway and report the state you
found; don't claim a fix you didn't make.

Worth flagging even after it clears: a blank internal cost-center Description at
RO creation (it hard-blocks other internal ROs), and $0.00-cost internal jobs
(MPVI/TPS flagging zero = nothing posts to the internal side; normal for
inspections, a labor-rate/opcode gap if the store expects cost).

## Step 2c — Changing a job's Split Type UN-INVOICES the RO
Editing **Job N → Manage Splits → Split Type** (e.g. `INSURANCE` → `PAY_SPLIT`)
silently backs out the invoice. The audit log (RO Details) shows it plainly:
```
I  Status : Invoiced → NA
CP Status : Paid    → NA
```
Two downstream consequences:
1. All payers drop to `Ready for Invoice` → Cashiering is dead until re-invoiced
   (see Step 2b).
2. **Tax can move between payers.** In the BC 99491 case the same two parts were
   `8.35% Tax` on the insurance payer and `NO TAX *` on the customer's deductible
   lines — so the customer's balance dropped and his already-collected card
   payment became an overpayment. Read the **Payers Consolidated View** per-payer
   line detail to see which side carries the tax; don't assume.
   Caveat: the arithmetic may not tie exactly (there $71.47 × 8.35% = $5.97 but the
   actual delta was $5.93). Say "approximately, and I can't fully account for it"
   rather than presenting a clean derived number you can't prove.

**The Manage Splits grid goes hard-locked read-only once money is collected.**
On a job with an applied payment, every meaningful control has `disabled` set:
`splitType`, the `Deductible Split` toggle, every `payableAmount-payer_N_M`,
`Add New Payer`, and the modal `Save`. Only the cost-center rows (Split %,
Description) stay editable — a red herring. **You cannot revert the split from the
UI while a payment is applied.** The payment has to be voided/refunded first, which
is real money and needs Joe's explicit go.

Also watch for this warning above the payer table, which blocks invoicing even when
all jobs *display* Completed:
```
Payer can ONLY be Invoiced after All Jobs in RO are Completed
For the following Payers: <payer>
```
Benign by contrast: `Cost Amount for the job is going to be zero` and
`The cost center description is empty` are warnings, not blockers.

## Step 3 — Confirm the symptom is RO-specific, not GL-specific
Ask (or check): does the same Other → same GL close work on *other* ROs?
If yes — and it usually is — **the GL account is exonerated.** Stop investigating
GL config and go hunt what is different about *this* RO. This single question kills
most wrong theories in one line.

## Step 4 — Candidate blockers, in order of cheapness
1. **An open job.** Any job not in a terminal state (e.g. `TECH_ASSIGNED`) while the
   RO sits at `READY_FOR_INVOICE`. Tekion refuses to cashier and reports the generic
   error *without naming the job*. Cheapest thing to rule out, and a hard blocker
   regardless of anything else. Check every job's status, not just the RO status.
2. **A contract payer.** `subPayType: CVSC` (vehicle service contract) carries money
   as `contractAmount` + `contractTax` rather than a plain amount, and routes through
   the service-contract billing path. Structurally different from the plain
   `CUSTOMER_PAY` payers where Other-closes work fine.
3. **Multi-payer RO** with mixed states (WARRANTY CLOSED + INTERNAL INVOICED +
   CUSTOMER_PAY + CVSC all on one RO) — more surface for a partial-state rejection.

## Step 5 — GL account config (only if step 3 says the GL *is* implicated)
`POST /api/accounting/u/glAccount/search`, body
`{"searchText":"<acct# or name>","page":{"from":0,"size":50}}`, replayed in-page with
captured axios headers (`window.__H`).

Response `data.hits[]` carries `accountNumber`, `accountName`, `accountTypeId`,
`controlField`, `controlNumberMandatory`, `active`, `departmentId`, `modifiedTime`.

Reference (BC / dealer 1251): `256 PORTFOLIO`, ASSET, SERVICE dept,
`controlField: REPAIR_ORDER`, `controlNumberMandatory: true`, behind schedule
**#49 PORTFOLIO-CLAIMS** (`controlType: REPAIR_ORDER`, `DETAIL_FORWARD`).
Fleet: 256 is BC-only. BT has `2104 PORTFOLIO WARRANTY` / `2108 PORTFOLIO EXPRESS
CLAIMS`; ST uses `2105`; TL uses REFERENCE.

**No GL change history exists via API** — `glAccount/audit/search` and `/history`
both 404. `modifiedTime` gives you *when*, never *what* or *who* in readable form.
Do not present a timing correlation as a cause.

## Step 6 — Getting the actual server error (needs Joe)
Every accounting endpoint returns the same useless
`{"status":"failed","errorDetails":{"key":"unexpected.error"}}`.
To get real detail, install the interceptor **before** the click:

```js
// hook BOTH — the Control lookup and cashier posts are XHR, a fetch-only hook misses them
window.__X=[];
(function(){var o=XMLHttpRequest.prototype.open,s=XMLHttpRequest.prototype.send;
 XMLHttpRequest.prototype.open=function(m,u){this.__m=m;this.__u=u;return o.apply(this,arguments)};
 XMLHttpRequest.prototype.send=function(b){var x=this;
   x.addEventListener('load',function(){window.__X.push({m:x.__m,u:x.__u,b:b,s:x.status,r:(x.responseText||'').slice(0,4000)})});
   return s.apply(this,arguments)})();
```
Then ask Joe to reproduce, and read `window.__X`. Drive SPA navigation with
`history.pushState` + `PopStateEvent` — a hard reload wipes the hook.

## Pitfalls
- Empty Control popover ≠ broken. **Type first.** (see Step 2)
- Don't build a theory off `vision_analyze` of a dropdown — it cannot distinguish
  "no options" from "not queried yet". Pull state from the API.
- `window.__X` empty right after a UI click usually means the hook was installed
  after the app captured its transport reference, or the click fired no request.
- Bridge viewport is ~720px tall; form fields below y≈720 need scrolling before a
  coordinate click will land.
- `:9223` session drifts dealers between turns — verify
  `localStorage.currentActiveDealerId` before trusting any account/RO read.

## Reporting
Lead with what is *different about this RO*, not with GL theory. Give the cheap
check first (open job). Mark unproven items as unproven — Joe accepts
"I don't know yet" but not confident wrong answers, and he will hand you a
one-line counter-example that destroys a shaky theory.
