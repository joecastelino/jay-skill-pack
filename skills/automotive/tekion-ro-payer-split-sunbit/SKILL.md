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
- Job-level `Pay Type*` radios collapse from `CP W I` to just `CP` once a split exists.
  That's expected, not a permissions problem.
- There is **no OpenAPI write path** for payer splits — browser only.

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
