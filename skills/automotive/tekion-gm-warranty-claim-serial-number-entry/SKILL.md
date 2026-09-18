---
name: tekion-gm-warranty-claim-serial-number-entry
description: 'Answer "where do I enter the serial number (engine/transmission/valve body) for a GM warranty claim in Tekion?" — NEW/installed serial field exists (claim form → Part Details). OLD/REMOVED serial has NO field in Tekion GM ZREG catalog (51 GWM fields, only Serial Part Number) so claims reject in GM Global. Verified live BC/1251 2026-09-16/18. Open item - need a rejected RO# to confirm which GM element is flagged before writing clerk cheat sheet or enhancement request.'
triggers:
  - serial number on a warranty claim
  - old serial number engine transmission valve body claim
  - GM claim rejects serial number
  - where do I type the serial number in Tekion
  - claim rejected in GM global fix in Tekion
  - process claim serial number field
---

# Tekion GM Warranty Claim — Serial Number entry

**Answer: the field EXISTS.** It is NOT on the RO and NOT on the part line — it lives inside
the **GM warranty claim form**, on the **Part Details** section, one free-text cell per part row.

## Exact click path (verified live BC/1251, 2026-09-16)
1. Open the RO (`/ro/repair-orders/ro-list` → click the RO row → URL becomes
   `/ro/repair-orders/<roId>/jobs/<jobId>`).
2. Select the **warranty job** in the left Jobs list (must be the job carrying the W pay type).
3. Click the **job-level kebab** (⋮ `[class*=KebabMenuTrigger]`, visible + `x>1000`, `y>150`) —
   it sits in the job panel header. Menu items: *Job Clocked Time · Job External Note ·
   **Process Claim** · Tech Flag Hrs*.
4. Click **Process Claim** → the GM claim form opens with 7 sections:
   `Claim Information | CCC | Labor Details | Part Details | Net Info | Additional Details | Summary`.
5. **Part Details** table columns: `Part Number | Unit Price | Quantity | **Serial Number** |
   Causal Part | GM Part`.
   - The Serial Number cell is an **enabled, editable input** (`disabled:false`, `readOnly:false`)
     whose placeholder is **"Type and Press Enter to Add Serial No."** — Enter adds ANOTHER
     serial to the same part line (multi-value supported).
   - Same section also has a per-row **Causal Part** checkbox, a **GM Part** checkbox, and a
     standalone **"Causal Part Number"** field ("If no causal part number available, please
     enter description") + `+ Add Part`.
6. Footer buttons: `Save as Draft | Cancel | Relogin and submit | Submit`.

## Why stores think "there is no field"
- There is **NO serial field at RO level** — verified: 0 inputs matching `/serial/i` on the RO
  job screen, and the job's "Billed Parts" table has no serial column/input. Nothing on the
  repair side ever prompts for it.
- The claim form auto-populates everything else, so it reads like a review-only screen; clerks
  click through Claim Information → Submit.
- The form is only reachable via **job kebab → Process Claim**, so if they never open it the
  serial is simply never transmitted (GM then rejects in Global).
- Verified live example: RO 101799 (2023 Cadillac Escalade, engine claim) — the claim's Part
  Details had 25 part rows, every Serial Number cell empty, one of them
  `12745425 - ENGINE  $5,456.20`.

## API/data-model confirmation (public OpenAPI)
`~/.hermes/profiles/jay/home/../../dealerdetail/specs/apis/repair-order__*.json`
(`~/dealerdetail/specs/apis/`):
- `PartDetailDto` (in `ro-update-warranty-claim`) and `PartDto` (in `get-repair-order-warranty-claim`)
  both carry `serialNumber` ("Serial number of the part"), alongside `causal`, `defectNumber`,
  `invoiceNumber`, `installationTime`.
- So the serial IS part of the claim payload Tekion sends to GM — it's a data-entry gap, not a
  missing integration.
- `LaborDetailDto` has only time/amount fields + `oemOpcode` — there is NO serial at the labor level.

## Post-submission / rejection handling (KB-cited)
`KB0021612` (GM Warranty Claim Form Status Integration): the job screen's **Claim Information**
table shows per-form `Claim Number | OpCode | Submission Date | Status | Comments | Claim Total |
Approved Amount`; statuses are **Submitted / Accepted and Paid / Rejected**, and hovering the
info icon on a *Rejected* status shows the reason(s). KB explicitly documents
"**Re-application of Rejected Forms** … rectify them, and resubmit another warranty claim form."
`KB0023747` / `KB0021610` describe the submission workflow (Process Claim → fill sections →
Submit → GM portal credential modal).

## Pitfalls
- **`Cancel` cleanly closes the claim form with nothing saved.** Use it to exit after inspecting;
  never touch `Save as Draft` / `Submit` for read-only recon.
- Opening Process Claim on an **Invoiced/Closed** RO works fine (verified) — you don't need an
  open RO to inspect the form.
- The claim form's section links are hash anchors (`…/jobs/<jobId>#partDetails`) — clicking a
  section name just scrolls; there are no separate tab panels.
- **Do the KB scraping FIRST or on a different port.** `kb_search_scrape.py` navigates the
  `:9223` *bound* page to `tekion.service-now.com` — it can REPLACE the Tekion tab entirely
  (`/pages` showed `count:1`, Tekion page gone), so any open Tekion modal/state is destroyed and
  later `/eval` calls 500 on `localStorage.t_user`. Check `/pages` + `/url` before trusting evals.
- Verify with DOM, not OCR: `[...document.querySelectorAll('input')].filter(i=>/Add Serial No/.test(i.placeholder||'')).length`
  — non-zero = the claim form is open and its part rows are visible.

## SECOND serial field — the labor line (found 2026-09-16, same session, Joe follow-up)
Joe's correction: *"that is for NEW serial number … there should be another field kind of like
where you would put a reprogramming code for the OLD removed serial number"*. So I enumerated the
whole claim model, not just the rendered form.

Verified from the front-end chunk `roWarrantyClaimForm.<hash>.chunk.js` (fetch the URL straight out
of `performance.getEntriesByType('resource')` and regex it in-page — `window.__H` XHR hook only
captures response bodies, and **the hook is wiped by any hard navigation**, so install it AFTER
the page loads and then drive the SPA):

- **Part row** field ids: `partNumber, partQuantity, partCausalIndicator, serialNumbers (ARRAY),
  partConditionCode, partAppealActionCode, partCoreAmount, partInvoiceNumber, partDiscount,
  partExtendedAmount, partNumber, nonGmPartIndicator…`
  - `serialNumbers` is the part-line serial — multi-value tag input, and the ONLY validation rule on
    it is `"For causal part, number of serial numbers should match number of quantity"`.
    **Consequence: a qty-1 causal part accepts exactly ONE serial** (so you cannot smuggle
    old+new onto the same causal part line).
- **Labor line** field ids (`otherLaborDetails` rows, table key `otherLaborTableOptions`):
  `otherLaborOperationCode (Opcode), otherHours (Labor Hours)`, and — additional GM labor-line
  detail fields that exist in the model but are gated by server config:
  **`serialNumber`**, **`spsWarrantyClaimCode`** (SPS = GM Service Programming System — this is the
  "reprogramming code" family Joe referenced), `keyCode`, `batteryTesterCode`, `flushCode`,
  `gridReference`, `documentId`, `shipDirectOrderNumber`, `diagnosticCode`, `calibrationValue`,
  `mileageMeasurement`, `brakes`.
  - Field requirement/visibility comes from the **server-side config**, not the client:
    the chunk builds `validationConfig` by merging `bootstrap.labourFields` + `gmFields` +
    `dependencyCodes` (per-labor-opcode dependency map) — helper `en(field, cfg)` reads
    `cfg[field].required`. The config endpoint is
    `GET /api/service-module/u/oem/gm/claimForm/transactionType/<ZREG|ZSET|ZFAT|ZACD|ZPTA…>/config`
    → `{data:{gmFields, causeCodes, bootstrap}}`; there's also `POST …/oem/gm/gmFields`.
  - **LIVE RESULT on RO 101799 job 3 (BC, ZREG):** adding a row via *Labor Details → Other Labor
    Details → "+ Add Opcode"* renders ONLY two columns — `otherLaborOperationCode` + `otherHours`
    (+ REMOVE action). The serial/SPS columns did NOT render, and the row's Opcode combobox opened
    with **zero options**. So on this claim the labor-line serial is not reachable through the UI.
- **GM's own field catalog Tekion can send for ZREG = 51 GWM fields** (`data.gmFields`, each with
  `gwmFieldName` + `required: R/O/NA`). The ONLY serial-bearing entry is
  **`serialNumber` → GWM "Serial Part Number"** (required = **O**). Serial-ish neighbours you may
  be tempted to use instead: `Reference Number`, `Causal Part Number`, `Non-GM Part Indicator`,
  `Original Installation Date/Distance`, `GM Pre-Repair Authorization Code`,
  `Service Management Authorization Code`. There is **no "Old/Removed Serial" GWM field** in the
  ZREG catalog.
- Not serial fields, for completeness: **Additional Details** tab = `authorizationType` +
  `authorizationNumber` + `generalComments` (+ attachments); **Net Info** = criteria/amount +
  `Additional Information` column (net items NIC/NIE/NS1/NS2/NPT/NIT/NIS/NIP/NIA/NIF/NIM/NIR;
  freight-postage codes include "Core"); CCC = complaint category/code, cause code, correction text.
- The same chunk serves Ford/Volvo/Subaru/etc. claim forms — don't mistake a Ford block
  (e.g. Ford-only `exchangeSerialInvoice` / "Tech Journal, Battery Code or Serial #") for a GM
  field. Always confirm the block is under `gmclaimFormV2`/`gmFields`.

**Bottom line to give Joe/store (2026-09-16):** Tekion exposes exactly ONE VIN-claimable serial per
part line and one *latent* labor-line serial that isn't rendered for GM/ZREG; GM's ZREG field
catalog has exactly one serial field. If GM's rejection demands a serial Tekion cannot map, the
claim cannot be completed in Tekion today → finish in GM Global, or file a Tekion enhancement to
map the labor-line `serialNumber`/`spsWarrantyClaimCode`. Confirm GM's exact field label/rejection
text (or a rejected RO# — Claim Information info icon) before promising a workaround.

## Open question to confirm before writing clerk instructions
Which serial GM actually wants (installed/new vs removed/old unit), and the exact GM-side field
label GM flags. Get one *Rejected* RO# + the info-icon reason, then decide: (a) part-line serial
(only if GM's "Serial Part Number" is the removed unit's serial), (b) comments-body workaround
(`Additional Details → General comments` / Net Info `Additional Information` — GM receives these as
text, they do NOT satisfy a required serial field), or (c) not possible in Tekion → GM Global
completion + Tekion enhancement request.

## Clean-up discipline for this recon
Adding an "Other Labor" row to inspect its columns is an UNSAVED draft change: delete the row
(REMOVE action in `action-cell-0-REMOVE-Button`) and then click **Cancel** on the claim form.
Verified clean exit = URL returns to `/ro/repair-orders/<roId>/jobs/<jobId>` with tabs
`Jobs (n) | Recommendations (n) | MPI …`, part rows untouched, `otherLaborOperationCode-cell` count 0.