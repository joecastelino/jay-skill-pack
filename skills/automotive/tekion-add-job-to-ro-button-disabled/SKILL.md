---
name: tekion-add-job-to-ro-button-disabled
description: >
  Diagnose "I can't add opcode X to RO #NNNNNN" / the "Add To RO" button is greyed
  out with no error message in Tekion. Root cause is almost always the RO Approval
  Flow "Paytype Rules" setting, NOT the opcode, the RO, or a permission.
triggers:
  - can't add opcode to RO
  - Add To RO button disabled
  - Add To RO greyed out
  - PORTMAJOR can't be added
trigger: Add To RO disabled, cannot add job to repair order, add job greyed out, opcode won't add to RO, Tekion approval flow paytype, Approval Workspace still work, /core/approval-workspace
---

# "Add To RO" button disabled — Tekion

## Symptom
On an existing RO, Add Job → search an opcode → select it → the **Add To RO**
button stays `disabled`. **No toast, no red validation, no tooltip.** Filling
Cause/Complaint does not help. Happens for EVERY opcode, on EVERY RO at that
store — which is the tell that it is a STORE SETTING, not an RO/opcode problem.

## Root cause (verified TL/1092, 2026-08-26)
Service Settings → General Setup → **Enable RO Approval flow = ON**, with
**Paytype Rules → "Additional Jobs can be added for the following Paytypes" = EMPTY**.

The minified gate (chunk `80511.*.js`) is effectively:

```js
allowedPayTypes = new Set(approvalSetting.jobsAllowedToAdd || [])
disabled = approvalFlowEnabled && !allowedPayTypes.has(job.payType)
```

Empty list → the Set is empty → **every** pay type is blocked → button
permanently disabled. Turning the approval flow ON without populating the
paytype list bricks job-adding store-wide. There is deliberately no error
message because the UI treats it as "not permitted", not "invalid".

## Fast diagnosis (no clicking around)
In an authenticated :9223 page, arm an XHR hook, load
`/service/settings/ro-settings` to capture live axios headers (a bare `fetch`
will 500 "Token doesn't exist or is invalid"), then replay per dealer:

```js
GET /api/service-module/u/settings/service-settings
// headers: copy captured ones, swap dealerId + tek-siteId ('-1_<dealerId>')
// read data.approvalSetting:
//   roApprovalFlowEnabled, jobsAllowedToAdd, allowJobChangeByPayType,
//   metaData[0].modifiedTime   <-- tells you WHEN someone flipped it
```

**Verdict rule:** `roApprovalFlowEnabled === true && !jobsAllowedToAdd?.length`
→ that store cannot add jobs to any RO. Period.

## Proof-of-cause test (non-destructive, in-memory only)
Patch the Set prototype membership for the live page, re-select the opcode, and
observe the button enable. Revert immediately with `delete` — nothing is saved
to Tekion. Confirms the gate without touching store config.

## The fix (business decision — ASK Joe first)
Service Settings → General Setup → scroll to **Enable RO Approval flow**:
- **Option A** — populate *Additional Jobs can be added for the following Paytypes*
  with the pay types that should be addable (e.g. Customer Pay, Internal, Warranty),
  keeping approval governance. This is what BT/1249 does.
- **Option B** — toggle *Enable RO Approval flow* OFF entirely (what ST, BC, SV,
  VC, AR run with).

Then **Submit** (button bottom-right). Requires a success toast — re-navigate
away and back to verify, a hash-only nav does NOT remount the SPA.

## Verify the fix landed (API, not vision)
Re-read `approvalSetting` and confirm `metaData[0].modifiedTime` ADVANCED to the
moment of the change. TL 2026-08-26: flipped-on 8/25 15:10 PT → fixed 8/26 10:59 PT.
Joe's fix set BOTH `roApprovalFlowEnabled:false` AND populated
`jobsAllowedToAdd:[CUSTOMER_PAY,WARRANTY,INTERNAL]` — either alone unblocks it.

## "Does Approval Workspace still break if I turn the flow off?" — NO
Expect this as the immediate follow-up question. Answer, verified live:

- **Approval Workspace is a CORE app, not gated by the service setting.** Route is
  **`/core/approval-workspace`** — it loads clean with flow OFF (Settings tab,
  My Approvals, filters, Bulk Actions all render; shows `My Approvals (0)`).
- What turning the flow off actually does: **RO job-add / paytype-change requests
  stop being generated.** The advisor just does the action directly. In-flight items
  and other request types remain viewable/actionable.
- So: module alive, RO-approval pipeline dormant. Those are different things — say
  both, don't answer with just "yes it works."

### The empty-approvers trap (flag this proactively)
`approvalSetting.metaData[].hierarchies[].levels[].approvers` can be `[]` while a
`requestType` (e.g. `OTHER_LABOR_HOURS`) is still configured. TL has exactly this.
Harmless while the flow is OFF, but **re-enabling with an empty approver list is a
SECOND way to wedge the store** — requests generate with nobody able to approve them.
Check it before any future re-enable.

## Finding a Tekion module route — use the app grid, don't guess
Cost 4 wasted navigations guessing `/ro/approval-workspace`,
`/service/approval-workspace`, `/ro/approvals`, `/ro/approval` — all returned the
empty SPA shell (`innerText.length == 117`, just the sidebar codes) which looks
identical to "module broken." The real route was `/core/...`.

Reliable discovery: open the nine-dot app grid (`/mouse` ~x22,y32) then regex the
visible text for the module name:

```js
[...document.querySelectorAll('a,div,li,span')]
  .filter(e => e.offsetParent !== null)
  .filter(e => /approv/i.test((e.innerText||'').trim()))
```

Then `scrollIntoView` the exact-match leaf and `/mouse` its center — the tiles are
`href`-less React handlers, so read the resulting `location.pathname`.

Bonus recon: the left sidebar's 2-letter codes DO carry real hrefs. Map them with
`innerText` → `getAttribute('href')` to dump the whole module list at once
(`EH`→`/core/employeeHours`, `RO`→`/ro/repair-orders`, `PO`→`/parts/purchase-order/list`,
`R`→`/core/reports`, `US`→`/core/user-setup`, …).

## Pitfalls
- **An empty SPA shell (`innerText.length ≈ 117`) means WRONG ROUTE, not a broken
  page.** A real loaded page is 300+ chars minimum, usually thousands.
- **The RO List page-level search (`input[searchfield="ALL"]`) would not filter to a
  specific RO#** — tried native value-setter + `input` + synthetic Enter, and
  `/type` + `/press Enter`; list stayed unfiltered at 218,568 results. Don't sink
  time into it; navigate to the RO by URL/id or drive the search a different way.
- `:9223 /screenshot` is a **GET**, not POST (POST 404s).
- Do NOT chase the opcode: `MPVI` returning "no button" just means the opcode
  didn't match search; `ALIGN`/`PORTMAJOR` returning `disabled:true` is the real gate.
- ALWAYS run the 7-store fleet comparison before calling it a Tekion defect. If
  6 stores are fine, it is store config, not a platform bug.
- `metaData[0].modifiedTime` is gold: correlate it against when the store started
  complaining.
- Strip Pendo overlays before any `/mouse` click on Tekion settings pages.
