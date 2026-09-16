---
name: tekion-gm-warranty-claim-serial-number-entry
description: Answer/execute "where do I enter the serial number (engine/transmission/valve body) for a GM warranty claim in Tekion?" — the field DOES exist, buried in the claim form. Verified live at BC (dealer 1251) 2026-09-16.
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

## Open question to confirm before writing clerk instructions
Which serial GM actually wants (installed/new vs removed/old unit). Tekion's field is a free-text
per-part cell, so it can carry either or both (multi-value). Confirm against a real *Rejected*
claim's stated reason (Claim Information → info icon) before telling clerks what to type.