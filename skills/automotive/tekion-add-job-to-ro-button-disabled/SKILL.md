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
trigger: Add To RO disabled, cannot add job to repair order, add job greyed out, opcode won't add to RO, Tekion approval flow paytype
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

## Pitfalls
- Do NOT chase the opcode: `MPVI` returning "no button" just means the opcode
  didn't match search; `ALIGN`/`PORTMAJOR` returning `disabled:true` is the real gate.
- Do NOT blame RO state, multi-payer, or role permissions — check the setting first.
- ALWAYS run the 7-store fleet comparison before calling it a Tekion defect. If
  6 stores are fine, it is store config, not a platform bug.
- `metaData[0].modifiedTime` is gold: correlate it against when the store started
  complaining.
- Strip Pendo overlays before any `/mouse` click on Tekion settings pages.
