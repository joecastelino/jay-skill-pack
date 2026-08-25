---
name: tekion-approval-notes-on-ro-pdf
description: How to get RO approval information / approval notes (additional warranty hours approvals, warranty job approvals, recommendation approvals) to print on a Tekion RO / invoice PDF. Covers the prerequisite Service Settings + support ticket, the PDF Configurator toggle, and where the live UI differs from the KB article. Use when Joe or a store asks "how do I get the approval notes on the RO PDF" or "approvals aren't printing on the warranty invoice".
---

# Tekion — Approval notes on the RO PDF

Source of truth: KB0010837 (*HOW TO: RO Approval Process*) + KB0021613
(*Service Settings - PDF Settings - PDF Configurator*), plus LIVE verification on
SCT (876) and VC (1891) 2026-08-25.

## The 3 layers — all must be true

### 1. Approvers / approval rules must exist
KB0010837 says email **support@tekion.com** with the **login ID(s)** of the approvers.
**That KB is stale** — on the current build there is a self-serve
**Approval Setup** app at **`https://app.tekioncloud.com/core/approval-setup`**
(App Grid → Settings → Approval Setup). It lists Business Processes:
`Deal recap` (Sales) and **`Service`** (Service), each with a rule count.
Build the Service approval rules there; only fall back to a support ticket if the
Service business process is missing.

TL (1092) baseline 2026-08-25: Service business process = **2 rules**, last modified
that day (Joe built them). Deal recap = 0 rules.

### 2. Turn the approval workflow on
Service Settings → **General Setup** → toggle **"Enable RO Approval flow"**.
URL `/service/settings/ro-settings`.
(The KB calls this section "Approval Settings"; on the current build it's the
`Enable RO Approval flow` toggle in General Setup.)

**AMG baseline 2026-08-25: SCT (876) has `Enable RO Approval flow` = OFF.** If it's off,
no approvals are ever recorded, so nothing can print — flipping the PDF toggle alone
does nothing.

### 3. Turn the print field on in the PDF Configurator
`App Grid → Settings → Services Settings → PDF Settings` — direct URL
**`https://app.tekioncloud.com/ro/pdf-settings`**
(NOT `/service/settings/pdf-settings`, which silently redirects to `ro-settings`).

Click the PDF you want (e.g. **Invoice - Warranty Pay**) → **Body** tab.

Two distinct rows live in Body:

| Body row | What it prints | Configurable? |
|---|---|---|
| **Approval List** | the RO approval records (requested/approved additional hours + warranty jobs, with the notes/comments entered during the approval) | plain on/off toggle, no sub-config |
| **Recommendation Approval Details** | the recommendation-approval verbiage line | has **Configure Section** → *Approval verbiage* text (default "Approved by Service Advisor on behalf of customer") |

Toggle **Approval List** ON → **Generate Preview** → **Save And Publish**.

**Which PDFs even have the Approval List row** (verified SCT 876 + VC 1891):
- ✅ **Invoice - Warranty Pay**
- ✅ **Invoice - Service Advisor**
- ❌ Invoice - Customer Pay, Invoice - Internal Pay, Closed RO Invoice — row does NOT exist.

This matches the KB: *"The approval information will display on the warranty invoice PDFs."*

**AMG baseline 2026-08-25** (`Enable RO Approval flow` / Approval List on Warranty Pay /
Approval List on Service Advisor):
- **SCT 876** — flow OFF / WP OFF / SA OFF
- **VC 1891** — flow OFF / WP OFF / SA OFF
- **TL 1092** — flow **OFF** / WP **ON** ✅ / SA OFF  ← PDF side already done, workflow toggle is the blocker

Recommendation Approval Details = ON everywhere.

## Triage order when someone says "approvals aren't on my RO PDF"
1. Read `Enable RO Approval flow` in Service Settings → General Setup. **OFF = stop here**,
   nothing is being recorded so the section prints empty no matter what.
2. Read `Approval List` on the PDF the store actually prints. Warranty jobs → *Invoice -
   Warranty Pay*. Confirm the RO's job pay types first via
   `GET /repair-orders/{rid}/jobs` → `payType` (free, no browser) — if the jobs are
   CUSTOMER_PAY there is no Approval List row on that PDF at all.
3. Only then check that an approval was actually requested/approved on the RO
   (RO kebab → RO Bulk Action → Approval) — no approval record = empty section.

## KB vs live — the discrepancy (don't chase it)
KB0010837 says: *"PDF Settings → click 'Configure Section' within the Jobs section of the
body and toggle 'Show Approval Notes' to on."*
**That toggle does not exist on the current build.** The live Jobs → Configure Section
modal contains only: Show Job Author · Show Job External Notes · Show Job Cause · Show Fee ·
Show Return RO Details · Show Tax Code · Show OEM opcode on Job Line · Display
Paytype/Payer Information (Pay Type / Payer) · Job Line/Operation (Apply To All, Show
JobLine(s), Show ServiceMenu JobLine(s), Show Other Payer Contribution) · Job Line
Configuration (Job Total Price / Total Labor / Total Parts / Total Bill Hrs) · Operation
Configuration (Show Operations, Tech Employee Cert #, Total Labor, Total Parts, Bill Hrs,
Parts Details, Parts Prices, Part Note, SOR Parts Table).
The functionality moved up to the Body-level **Approval List** row. Use that.

## Permissions
`Roles → Permissions → Service → PDF Settings`: **PDF Configurator View access** +
**PDF Configurator Edit access**.

## How approvals get created (so the notes have content)
RO → RO-level 3-dot kebab → **RO Bulk Action → Approval** → dropdown **Additional Hours**
→ expand job → enter **note/comment**, clock tag, hours requested → Save → Save the job.
The job auto-holds until approved/rejected (tech is NOT clocked out). The approver repeats
the same path and the status flips Requested → Approved/Rejected. **The note/comment entered
here is what prints as the approval note.**
Recommendation approvals: tech adds warranty recommendation → Submit → advisor/tech
"Request for Approval" → approver goes RO kebab → RO Bulk Action → expand → note → Approve/Reject.

## :9223 automation notes (hard-won)
- `/eval` payload key is **`js`**, not `expression`.
- `/screenshot` returns **JSON `{"screenshot": "<base64>"}`** — decode it; a raw `curl -o file.png`
  is a JSON file and `vision_analyze` rejects it ("Only real image files are supported").
- The `browser_*` tools open a SEPARATE unauthenticated context — never mix them with :9223.
- PDF rows: `[class*=inputTableRow_row]`; state = `.ant-switch` with class
  `ant-switch-checked`. Read all rows at once:
  ```js
  [...document.querySelectorAll('[class*=inputTableRow_row]')].filter(e=>e.offsetParent)
    .map(r=>{const sw=r.querySelector('.ant-switch');
      return r.innerText.replace(/\n/g,'/')+' :: '+(sw?sw.className.includes('ant-switch-checked'):null);})
  ```
- The `Configure Section` button will NOT respond to `/mouse` at its reported coords (the
  page is a long virtualized scroller and coords go stale). Use
  `row.querySelector('button').click()` instead — that works reliably.
- Opening a PDF: don't hand-build the configurator URL — click the row in the list
  (`.rt-tbody .rt-tr` whose innerText starts with the PDF name). The URL carries an
  `auditEntityId` that is **per-dealer**; a copied URL from another store loads that
  store's config.
- Dealer switch: pill at ~(1130,32), then `/mouse` the target
  `[class*="root_dealerInfoItem_container"]` row (AR 178 / AM 220 / BC 262 / BT 304 /
  ST 346 / SV 388 / TL 430 / VC 472 at 1095 x). Verify `localStorage.currentActiveDealerId`.
- KB SSO bootstrap: `/navigate` to `https://app.tekioncloud.com/core/knowledge-base/search`.

## Cross-references
`tekion-service-settings`, `tekion-kb-search-scrape`, `tekion-sitemap`.
