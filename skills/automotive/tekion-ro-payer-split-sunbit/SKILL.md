---
name: tekion-ro-payer-split-sunbit
description: Add a second payer (Sunbit / third-party financier, insurance, another customer) to a Tekion repair-order JOB and split the dollars to them. Covers the "I added the payer but it stays at $0.00 / 0%" trap, the exact Manage Splits click path, and the Tekion global-hotkey trap that hijacks the browser mid-flow. Use for any "split job X to <payer>" or "can't get the Sunbit split to work" ticket.
triggers:
  - split the tires to Sunbit
  - add a payer to an RO job
  - pay type split by payers
  - multi payer split
  - can't get the split to work
---

# Tekion: split an RO job to a second payer (Sunbit et al.)

Verified live 2026-08-25 on SCT (dealer 876) RO 581089 job E (4TIRE, $1,299.50 tax-incl)
→ 100% moved to payer **1356097 SUNBIT**. PUT returned 200 and persisted across a
full page remount.

## ⚠️ THE #1 REASON IT "DOESN'T WORK"

Adding the payer is NOT the split. After **Add Payer**, the new payer lands at
**$0.00 / 0.00%** and the original payer still holds **100%**. Typing the full amount
into the NEW payer's box does **nothing** — I typed `1,299.50` into SUNBIT's field and
the grid showed *both* columns at $1,299.50 while SUNBIT's % stayed **0.00**. There is
no validation error, no red, no toast. It just silently doesn't take.

**You must reduce the ORIGINAL payer's amount.** The grid back-solves the remainder to
the new payer. Zeroing Alfredo → SUNBIT instantly flipped to `1,299.50 / 100.00%`.

If a manager says "I added Sunbit and it won't split," this is almost certainly it.

## READING an existing split (added 2026-08-26)

This skill is the WRITE side. If the question is "was this already split / did the
customer get charged the deductible," read first — don't touch anything:

- **The OpenAPI cannot see a payer split.** `/jobs` reports `payType:
  CUSTOMER_PAY` with **`subPayType: null`** even when a CVSC/third-party split is
  live; `/ro-fees` shows nothing; the job list shows each job at its FULL amount.
- **Free tells that a split exists**: RO search `tags` contain `PAY_TYPE: CVSC`
  and `PAY_TYPE: SPLIT_CUSTOMER_PAY_SPLIT`; and `/ro-invoices` carries a
  `payType: CUSTOMER_PAY` + **`subPayType: CVSC`** line separate from the plain
  `subPayType: CUSTOMER_PAY` line.
- **Ground truth = the job detail page**, no modal needed. Slice
  `document.body.innerText` between `"Pay Split By Payer"` and
  `"Collapse All Operations"` to get the payer rows, amounts, percentages — plus
  a **Contract Information** panel (Contract No. / Company / Deductible / Expiry)
  when the payer is a service contract.
- **A CP payer sitting at `$0.00 / 0 %` is not cosmetic — it BLOCKS invoicing.**
  (TL RO 398856, 2026-08-27: job 1 `TSC2` carrying $61.37 showed
  `166920 - Amir Baig  CP  $0.00  0 %` plus a blank `CP Deductible` row → job stuck
  `PARTIALLY_INVOICED`, both `ro-invoices` closed at `invoiceAmount: 0`, and **zero**
  Need Attention flags anywhere on the RO.) This is the mirror image of the write-side
  trap above: there the payer you ADDED stays at 0%, here the ORIGINAL payer is at 0%
  and nobody holds the charge. Same grid, same back-solve behaviour — somebody must
  total 100%. Full triage of that symptom = `tekion-ro-close-blocked-triage` Step 3f.
- The CP payer row is labelled **`Deductible`** on VSC jobs. That field is native
  and contract-bound — see `tekion-vsc-deductible-vs-fee-code` before anyone
  builds a fee code for a deductible or hardware overage.
- Loop EVERY covered job. One deductible per claim is normal: the deductible
  lands on one job and sibling covered jobs correctly show `$0.00 / 0 %`.

## ⚠️ "I CAN'T ADD A PAYER" — Add New Payer is DISABLED (verified TL RO 398856, 2026-08-27)

Different ticket from "the split won't take." If the store says they *can't add* the
payer at all, check whether the button is genuinely disabled before hunting permissions:

```js
[].slice.call(document.querySelectorAll('*')).filter(function(e){
  return e.offsetParent&&e.children.length===0&&/Add New Payer/.test(e.textContent)})
 .map(function(e){var b=e.closest('button');return {dis:b.disabled,pe:getComputedStyle(b).pointerEvents}});
// → {dis:true, pe:"none"}
```

Tekion locks the ENTIRE Manage Splits modal read-only, not just the button. Tell: dump
every input in the modal and they're ALL `disabled:true` (`splitType`, the
AMOUNT/PERCENTAGE radios, `postTaxPayableAmount-payer_N_M`, `percentageSplit-payer_N_M`,
`primaryPayerId`). If only *some* fields are disabled you have a different problem.
(Cost-center `description` inputs unlock independently — ignore them as a signal.)

### ⚠️ THE LOCK IS JOB-LEVEL, NOT PAYER-LEVEL — I got this wrong once, don't repeat it

My first read on 398856 was "the payer records are Closed, so reopen the payer invoices
and the grid unlocks." **That was WRONG and I had to retract it to Joe.** What actually
happened when Joe reopened:

| | before reopen | after reopen |
|---|---|---|
| Payers View rows | both `Closed`, all checkboxes `disabled` | both **`Ready for Invoice`**, checkboxes **enabled + checked** |
| Jobs 2–7 (Internal $0) | `Closed`, 0 Need Attention | `Completed`, **2 Need Attention each** |
| Job 1 TSC2 | `PARTIALLY_INVOICED` | **`PARTIALLY_INVOICED` (unchanged)** |
| Add New Payer | `disabled:true, pe:none` | **`disabled:true, pe:none` (unchanged)** |

So payers fully unlocked and the split grid **stayed hard-locked**. The gate is the JOB
sitting in `PARTIALLY_INVOICED` — not payer status. Verify after a full remount
(`/home` → back to the job URL), not off a stale DOM.

**Corollary: don't send the user hunting for a "payer-level unlock."** Read Payers View
FIRST and report actual row status before recommending anything — I told Joe to go
unlock the payer level when it was already unlocked.

### The orphaned-payer tell: header chip count ≠ Payers View row count

Job header chip read **"3 Payers"** while Payers View listed only **2**
(`94227 Toyota of Lancaster`, `166920 Amir Baig`). That third payer is the phantom —
the split grid showed a **Deductible column at $21.01 / 100.00% with the payer name
blank (`-`)**: somebody built the deductible split, never picked the payer, then both
`ro-invoices` closed at `invoiceAmount: 0`. Money assigned 100% to a payer that doesn't
resolve → job can't leave PARTIALLY_INVOICED → grid locked → nobody can assign one.

**Always diff the chip count against the Payers View row count.** A mismatch is the
cheapest possible detection of an orphaned payer record.

Read payer column LABELS from the grid header, not amounts alone — a `-` where a payer
name belongs is the smoking gun.

### What to try, in order (UNRESOLVED as of 2026-08-27 — do not fabricate a fix)

There is **no "reopen job" anywhere in the RO kebab**. Full TL kebab enumeration:
`Add/Edit Coupon · Add/Edit Fee · Audit Logs · Cashier · Hold · Invoice Pdf Preview ·
Media (N) · Payers View · Profit/Loss View · RO Bulk Action · RO Clocked Time ·
Update Estimate Amounts · Vehicle Update · View Posting Preview · View RO PDF`.
Same shape as the hidden Reopen gate in `tekion-reopen-closed-ro`.

1. **`Resync Payer`** on the affected payer row (enabled once payers reopen).
   Non-destructive, and it is literally the tool for payer records desynced from the RO.
   Cheapest shot at clearing the phantom. TRY THIS FIRST.
2. **Cashiering** (kebab → Cashier) — if the deductible was cashiered against the
   phantom payer, reversing that receipt is what releases the job. **Financial screen —
   get Joe's explicit go before clicking.**
3. If neither moves job 1 off PARTIALLY_INVOICED → **Tekion support ticket**. An
   orphaned invoiced payer is not fixable from the UI. Say that plainly rather than
   keeping the store clicking.

⚠ **Reopening is not free.** It flipped jobs 2–7 from `Closed`/0 flags to
`Completed`/**2 Need Attention each** (TL enforces both Cause AND Storyline — see
`tekion-ro-close-blocked-triage` Step 3e §6). Those must be cleared before the RO can
close again. Warn about this cost BEFORE recommending a reopen.

Warnings in Payers View on this RO (`Cost Amount for the job is going to be zero`,
`The cost center description is empty`) are **warnings, not blockers** — the payers were
`Ready for Invoice` with enabled checkboxes while showing them. Don't report them as the
root cause.

## Step 0 — locate the RO and the right JOB (zero quota, no browser)

Use `tekion-ro-job-paytype-triage` Step 1 to sweep all 7 dealers for the RO number
(RO numbers are NOT unique across stores), then list jobs to find the one holding the
tires. Job payload gives `jobNumber` ("1".."7") which maps to the UI's letters
A..G in order — but **read the concern text**, don't trust the ordering:

```
JOB 5  CUSTOMER_PAY  IN_PROGRESS  | MOUNT AND BALANCE FOUR TIRES Hankook KINERGY GT...
```
That was UI job **E**. Job detail URL:
`/ro/repair-orders/<documentId>/jobs/<jobId>`

## Step 1 — Manage Splits

On the job detail page, right panel under **Pay Type\***:
`Primary Payer | Default | Manage Splits | Pay Split By Payer`

Click **Manage Splits** → full-page modal **"Pay Type Split By Payers"**:
- Split Type: `Total`
- Split By Pay Type: `Amount` | `Percentage`
- toggles: `Deductible Split`, `Post Tax Split`
- grid: one column per payer × rows per component (job/op)
- bottom: `Payer - Cost Center Details` (Split Amount = PRE-tax) + `Total: $X (Tax Incl.)`

## Step 2 — Add New Payer

`Add New Payer` (top-right of modal, ≈1180,179) → **Add Payer** ant-modal:
- **Pay Type\*** select (≈636,310) → options are
  `W - Default warranty pay` / `CP - Default customer pay` /
  `CVSC - Vehicle Service Contract` / `I - Default internal pay`
- **Payer\*** select (≈629,389) — searchable customer list
- footer `Cancel` | **Add Payer** (primary, ≈895,480)

Sunbit is a normal customer record: **`1356097 SUNBIT`** (noemail@default.com) at SCT.
Search `sunbit`. If it's missing at another store, the customer record has to be
created first — that's the blocker, not the split UI.

After **Add Payer** the modal closes, a "Please wait while we calculate price" info
toast fires, and ~10s later a second payer column appears at $0.00 / 0%.

## Step 3 — move the money (the actual split)

Fields are `input#postTaxPayableAmount-payer_<N>_<row>` and
`input#percentageSplit-payer_<N>_<row>`. **The % field is `disabled`** — it's derived.
Payer 0 = original, payer 1 = the one you just added.

For a full move to the new payer, set payer 0's amount to `0`:

```python
ev("document.getElementById('postTaxPayableAmount-payer_0_0').setAttribute('data-jay','a0');'ok'")
api("/type","POST",{"selector":"[data-jay='a0']","text":"0"})
```
→ `payer_0 = 0 / 0.00%`, `payer_1 = 1,299.50 / 100.00%`

For a partial split, put the ORIGINAL payer's share in payer 0's box; the balance
lands on the new payer.

## Step 4 — Save + verify

Modal footer has THREE buttons matching text `Save` in the DOM (the job panel's own
Save bleeds through). The modal Save is the **rightmost primary** button ≈**(1210,688)**.
`1191,680` is the tertiary Cancel — clicking it does nothing useful.

Confirm the write with an XHR hook, not by looking at the screen:

```js
window.__all=[];const O=XMLHttpRequest.prototype.open,S=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this.__m=m;this.__u=u;return O.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(b){this.addEventListener('load',()=>{
  if(this.__m!=='GET')window.__all.push({m:this.__m,u:this.__u.slice(0,140),s:this.status})});
  return S.apply(this,arguments)};
```
Success = **`PUT /api/service-module/u/multi-payer-split/assetType/RO/assetId/<roId>/job/<jobId>` → 200`**.
The modal can stay open after a successful save — do NOT read "modal still open" as failure.

**True verification = full remount**, per the SAVE-VERIFY TRAP: navigate to `/home`,
then back to the job URL. Persisted state shows in the right panel:
```
Pay Split By Payer
1124109 - ALFREDO GUTIERR...  CP  $0.00
1356097 - SUNBIT              CP  $1,182.00
```
and the RO header payer chip increments (`3 Payers` → `4 Payers`).

Note the panel shows the **pre-tax** figure ($1,182.00) while the modal grid shows
**tax-incl** ($1,299.50). Both correct — different columns, not a discrepancy.
Also watch the RO total: it moved $1,510.68 → $1,550.68 on this save. Flag any total
change to Joe rather than explaining it away.

## PITFALLS (all cost real time on 2026-08-25)

- **Single-character `/press` calls trigger Tekion GLOBAL HOTKEYS.** Sending
  `s`,`u`,`n`,`b`,`i`,`t` one key at a time to "type" into the payer search worked ONCE
  and thereafter repeatedly navigated the whole SPA to
  `/service/settings/ro-settings#TAGS` mid-flow — losing the modal and all state, with
  no error. It only works while a text input genuinely holds focus; the instant focus
  drops, every letter becomes a shortcut.
  **FIX: always use `/type` with a selector.** The payer combobox's live input is
  **`#payerSearch`** (NOT `#PAYER` — that's the hidden react-select dummy input and
  `/type` on it 500s):
  ```python
  api("/mouse","POST",{"x":629,"y":389})          # open the combobox first
  api("/type","POST",{"selector":"#payerSearch","text":"sunbit"})
  ```
  Symptom you've been bitten: `find("SUNBIT")` returns `[]` and `location.href` reads
  `/service/settings/...`. Re-navigate and restart the flow.
- **`#PAYER` exists before the combobox is opened; `#payerSearch` only exists after.**
  Click the select's placeholder/container first, then type.
- **Notification toasts land on top of the modal and swallow `/mouse` clicks.**
  SCT fires live RO recommendation toasts constantly. Strip them before every click:
  `document.querySelectorAll('[id*="pendo"],[class*="ant-notification"],[class*="notification"],[class*="toast"]').forEach(e=>e.remove())`
- **`/eval` can return the previous page's DOM** — poll until
  `document.body.innerText.length > 1800` AND the URL contains `/jobs/` before acting.
- **A kebab/menu item at `x > 1280` is OFF-VIEWPORT and `/mouse` silently misses.**
  The RO kebab `.icon-overflow` reported `x:1252` in one layout and `x:1366` in another
  (Payers panel open shifts it). `/mouse` returns `success:true` and nothing happens.
  **FIX: prefer `element.click()` via `/eval`** for menu items —
  `document.querySelector('.icon-overflow').click()` worked at both x positions. Same
  for the menu leaves: filter to `textContent.trim()==='Payers View'` and `.click()`
  rather than computing coordinates.
- **Menu-item text matching needs `===`, not regex.** `/Payers View/.test(...)` matched
  a stale node after the panel had already opened and returned `{"none":1}` on the
  retry, which reads as "the click failed" when it actually succeeded. Re-check
  `location.href` and the panel's innerText before concluding anything failed.
- **Panels can render with ZERO checkboxes mid-load.** Reading
  `input[type=checkbox]` right after opening Payers View returned `[]`; the same query
  seconds later returned all 5 rows with correct `disabled` flags. Never conclude
  "controls are missing" from one read — re-poll.
- **The Payers View `Warnings` accordion is COLLAPSED by default** and its contents are
  absent from innerText until clicked. Click it before reporting "no warnings."
- Job-level `Pay Type*` radios collapse from `CP W I` to just `CP` once a split exists.
  That's expected, not a permissions problem.
- There is **no OpenAPI write path** for payer splits — browser only.
- **OpenAPI 429s hard on repeated `repair-orders:search`.** A 4× retry loop with 20s
  sleeps still returned 429 every time and burned 80s. When the API is drained, the
  BROWSER is ground truth for RO/job/payer status anyway — switch immediately instead of
  retrying (and per the thundering-herd rule, don't stack retry loops).
- **`opcode_preflight.py` can report `NOT SAFE TO BUILD: dealer` after waiting out the
  pipeline** — it pauses cron but does NOT switch dealers. Switch via the dealer pill
  yourself (scrollIntoView the leaf row, `/mouse` its center, verify
  `localStorage.currentActiveDealerId`), then proceed.

## Ask Joe before doing it when

- The job is **Completed/Closed** or the RO is **Invoiced** (re-splitting a closed
  invoice is a financial change).
- He hasn't stated the split amount — default to **100% of that job** to the third
  party (that's what Sunbit financing means), state the default inline, and offer
  the partial.

## Cross-refs
- `tekion-ro-job-paytype-triage` — locating the RO/job, cross-store RO# collision
- `persistent-browser-server` — :9223 lanes, dealer switch, `/mouse` vs `/click`
- `tekion-ro-close-blocked-triage` — when the real issue is "can't close"
