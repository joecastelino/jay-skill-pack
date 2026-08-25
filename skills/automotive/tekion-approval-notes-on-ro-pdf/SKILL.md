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
- **TL 1092** — flow **ON** ✅ / WP **ON** ✅ / SA **ON** ✅  (all three set by Jay 2026-08-25 at Joe's request; SA copy republished 3:12 PM)

Recommendation Approval Details = ON everywhere.

## CRITICAL: two different "approvals" — do not confuse them (verified TL 2026-08-25)

Tekion has **two unrelated approval systems**. Only ONE of them prints its comment.

| | **Approval Workspace** (`/core/approval-workspace`) | **RO Recommendation Approval** |
|---|---|---|
| What it is | Rules-engine sign-off: APPR0826-0000NN records, business process = Service, submitter, approvers by level | Advisor recording that the *customer* approved recommended work |
| Where the comment is typed | Approver's comment box when they Approve (e.g. "SEAN IS RAD!") | RO → Recommendations → approve on behalf of customer → **Note** field |
| PDF Body row | **Approval List** | **Recommendation Approval Details** |
| Does the comment print? | ❌ **NO** — only `Total Approval Request : N` prints | ✅ **YES** — prints as `Note<text>` |

**Verified on TL RO 398624** (Warranty Pay v2 PDF, all 3 layers ON, 2 completed
Approval Workspace records incl. one with comment "SEAN IS RAD!"):

```
ApprovalListTotalApprovalRequest:0
...
RecommendationApprovalDetails Sean Preston approved recommendations on behalf of Sean Preston.
ModeOfCommunication InPerson  PreviousEstimate $0.00  RevisedEstimate $236.63
DateandTime Tue Aug 25, 2026 at 03:01 PM
Note wARRANTY WORK APRROVAL          <-- the ONLY note that prints
```

So: the **Approval List** section is a *counter*, not a notes section, and it read
**0** even though Approval Workspace showed completed records — because
Approval-Workspace approvals are a different object than the RO-level
`RO Bulk Action → Approval → Additional Hours` requests that Approval List counts.

**If someone wants an approver's comment (like "SEAN IS RAD!") on the PDF: it is not
available in the standard PDF Configurator.** Options: (a) have the advisor type the
text into the Recommendation approval **Note** field instead — that DOES print;
(b) open a Tekion enhancement request to surface Approval Workspace comments.

## Recommendations And Inspection PDFs — the BEST place for approval notes

There are three R&I documents in PDF Settings (all Published at TL):
`Recommendations And Inspection - Warranty` / `- Customer` / `- Internal`.

**None of them has an `Approval List` row** (that row exists only on Invoice - Warranty
Pay and Invoice - Service Advisor). So Approval Workspace comments do not print here
either. BUT all three have **`Recommendation Approval Details` → Configure Section = ON**,
and — critically — **the R&I PDF prints EVERY approval event with its Note, while the
invoice prints only ONE (the last).**

Verified TL RO 398624, `Recommendations and Inspection - Warranty` ("Warranty Copy v4",
3 pages) — page 2 carried the full approval audit trail:

```
Recommendation Approval Details
  Sean Preston approved recommendations on behalf of Sean Preston.
  Mode Of Communication In Person | Previous $0.00 | Revised $236.63
  Date and Time Tue Aug 25, 2026 at 03:01 PM
  Note  wARRANTY WORK APRROVAL
  ---
  Mode Of Communication In Person | Previous $236.63 | Revised $709.89
  Date and Time Tue Aug 25, 2026 at 02:56 PM
  Note  SEAN APPROVED FOR TESTING PURPOSE
  ---
  Mode Of Communication In Person | Previous $473.26 | Revised $709.89
  Date and Time Tue Aug 25, 2026 at 01:06 PM
  Note  SEAN P
```

**Recommendation: if a store wants approval notes on paper, print the
`Recommendations and Inspection - Warranty` copy, not the invoice.** It gives the
full chronological trail with dollar deltas (previous → revised estimate),
mode of communication, timestamp, and the free-text Note for each approval.

Body rows on the R&I - Warranty PDF (TL, all ON unless noted): Inspection Details ·
RO External Notes (**OFF**) · Pending Recommendations (+Summary) · CA Recommendations
(+Summary) · Jobs (Configure Section) · Jobs Recommendations Summary · Deferred
Recommendations · Summary · Signature Placeholder · **Recommendation Approval Details
(Configure Section)** · Inspection Media · BAR/EPA.
The Customer and Internal variants expose the same recommendation/approval rows.

### Gotcha: R&I PDFs render INLINE, not via a signed S3 URL
Unlike the invoice copies, clicking `Recommendations and Inspection - Warranty` in
**View RO PDF** does NOT fire `/api/exports/pdf-v3` + `presignedurls` — the XHR hook
captures nothing (`window.__pu` stays `[]`). The document is rendered straight into
the DOM. Just read it:
```js
const t = document.body.innerText.replace(/\n+/g,' | ');
t.slice(t.indexOf('Warranty Copy v4'), t.indexOf('Warranty Copy v4')+3400)
```
No base64 slicing, no −27 font decode needed. Try this FIRST before the S3 route.

## Reading the actual generated PDF (the only real proof)

Do NOT judge by the on-screen preview. Pull the real file:

1. On the RO, install a `window.open` + XHR hook, then RO kebab →
   **Invoice Pdf Preview** (accounting copy) or **View RO PDF** → click the
   specific doc row (e.g. `Invoice - Warranty Pay - 1355955 - …`). The signed S3
   URL lands in your hook (`/api/exports/pdf-v3` then `/api/media-v3/u/v2/presignedurls`).
2. **curl of that S3 URL from the host FAILS** — Tekion masks the AWS key as
   `AKIART...Z5S6`. Have the BROWSER fetch it and base64 it into a global:
   ```js
   const r=await fetch(url); const by=new Uint8Array(await r.arrayBuffer());
   let s=''; for(let i=0;i<by.length;i++) s+=String.fromCharCode(by[i]);
   window.__wb=btoa(s);
   ```
3. Pull it out in ≤16000-char slices with `substr` (NOT `slice` — slice drops a
   char at some offsets and corrupts the base64 length):
   ```bash
   for off in $(seq 0 16000 $LEN); do curl -s -X POST localhost:9223/eval \
     -H 'Content-Type: application/json' -d "{\"js\":\"window.__wb.substr($off,16000)\"}" \
     | python3 -c "import sys,json;sys.stdout.write(json.load(sys.stdin)['result'])" >> wb.txt; done
   ```
4. **Tekion PDFs use a subset font with a −27 char offset**, so normal text
   extraction returns garbage and `pdftotext`/`pymupdf` are unavailable/broken here.
   Decompress the content streams, pull `(...)` string literals, then **add 27 to
   every char code**. Working extractor: `/tmp/pdftxt2.py` + the +27 shift, or:
   ```python
   ''.join(chr(ord(c)+27) if 1<=ord(c)<200 else ' ' for c in raw)
   ```
   Then strip `;` and spaces to get readable (if unspaced) text.

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

## Making the changes (hard-won 2026-08-25, TL)

### Service Settings toggle — it SILENTLY fails the first time
Flipping `Enable RO Approval flow` + Submit returned **no error, no toast**, and a
true remount showed it back **OFF**. A second identical attempt saved fine
(`POST /api/service-module/u/settings/service-settings` → 200). **Always verify with a
nav-away-and-back remount, and be prepared to repeat the flip.** Do not trust the
absence of an error. Also: polling for a "toast" catches the Tekion **notification
bell** feed (recommendation P&A alerts) — that is NOT a save confirmation. Confirm by
re-reading the switch after remount, not by toast text.

### PDF Configurator — use native .click(), not /mouse
`/mouse` at the switch's own `getBoundingClientRect()` center **silently no-ops**:
`document.elementFromPoint(x,y)` resolves to
`DIV.root_helperText_exportText…` — a transparent header overlay sits above the row.
Use `row.querySelector('.ant-switch').click()` instead. Same for `Configure Section`
(`row.querySelector('button').click()`).

### Publishing
`Save And Publish` opens a **confirm dialog** ("Publish / Do you want to publish the
PDF? / No Yes") — click the LAST visible `Yes` button. Success =
`POST /api/servicesettings/u/pdfconfigurator` → **200** with the dealerId echoed.
Verify in the PDF list: the row's *Updated By* / *Last Updated* changes to you + now,
Status stays `Published`.

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
