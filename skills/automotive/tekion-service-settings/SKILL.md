---
name: tekion-service-settings
description: >
  Reference map of Tekion's Service Settings application (App Grid > Settings >
  Service Settings) — the master config for service/RO workflows: General Setup,
  Job Sequence, Flag Tech on, Round-Up rules, Default Service Advisor, RO/Job
  Flags, Holds, Parts Request, pay-type setups (Customer/Warranty/Internal/
  Insurance), Reminders, Express Mode, Tags, RO KPI List, Quotes, Role Config,
  Consumer Portal, Approval Settings, Deferred Recommendation Rules, Job Clock
  Setup, P&L View Setup. Use when asked where/how a service workflow behavior is
  configured (e.g. "why do tech flag hours auto-match bill time", "how is the
  recommendation opcode set", "where do return-RO / comeback tags come from").
triggers:
  - service settings tekion
  - flag tech on
  - recommendation opcode
  - default service advisor setting
  - ro flag setup
  - job sequence
  - round up hours
  - pre-invoice rule
  - return ro comeback tag
  - job tag filters
  - cant edit job tags
  - tag criteria filter
  - deferred recommendation rules
  - job clock setup
  - express mode setup
---

# Tekion — Service Settings (config reference)

The master switchboard for service/RO workflow behavior. Distilled from Tekion KB0010647
(PDF at `~/tekion-kb/pdfs/`). The **full field-by-field text** is in
`references/service-settings-full.txt` — load it when you need an exact field description.

## Nav & permissions
- **App Grid > Settings > Service Settings section > Service Settings tile.**
- Permissions (`Roles > Permissions > Service > RO`): Service Setup, Access Service
  Settings, Edit Service Settings.
- Left-side tabs; use up/down arrows to reveal more sections, left-arrow to collapse.

## The sections (left-side tabs) and what each governs
1. **General Setup** — the big one. Key fields:
   - **Job Sequence**: Alphabet (Job A/B/C) vs Numerical (Job 1/2/3).
   - **Recommendation Opcode**: default opcode when a recommendation is created without
     one (must exist in Opcode Management).
   - **Flag Tech on**: when tech flag hours auto-match bill hours — `Manual` (stays as
     entered) / `Job Save` / `RO Invoiced` (locks after invoice) / `Job Completed`.
     (Wage Types Config in Employee Onboarding sets flag-on-bill vs actual vs labor hours;
     does NOT apply when Manual.)
   - **Display Amount / Include Fees / Taxes / Coupons in Estimates** (PDF toggles).
   - **Allow to close RO in details view**, **Allow customers to sign invoices online**,
     **Show Service History of Other Dealerships** (same tenant), **Notify customer on
     invoice**.
   - **Round Up Settings**: round Technician Actual / Labor-Bill / Flag hours to nearest
     tenth (hours entered to the hundredth, e.g. 1.56; >5 second-decimal rounds up).
   - **Allow techs to clock in to multiple ROs/Jobs** (per pay-type-combination toggles).
   - **Accept Return RO after Last Service** (N days → shows "Return RO"/Comeback tag;
     renameable in Keyword Configuration), **Restrict duplicate Tag#**, **Onstar
     Integration**, **Select Default Service Advisor for jobs** (same-as-RO vs
     job-creator), **Make Cause mandatory for recommendations**.
2. **Service Module Selection** — which service modules are active.
3. **Parts Request** — parts-request workflow behavior between service & parts.
4. **Customer Pay / Warranty / Internal Pay / Insurance** — per-pay-type defaults
   (cost centers, rules).
5. **Reminders** — service reminder config.
6. **Express Mode Setup** — quick-lane / express check-in workflow.
7. **Tags / Job Tags** — RO and job tag definitions.
8. **RO Flag** — RO-level flag definitions/behavior.
9. **Hold** — RO/job hold reasons & behavior.
10. **RO KPI List** — which KPIs surface on the RO list.
11. **Quotes** — quote workflow config.
12. **Role Configuration** — role-driven service behavior.
13. **Consumer Portal** — what the customer-facing portal shows/allows.
14. **Approval Settings** — RO/job approval rules.
15. **Deferred Recommendation Rules** — how declined/deferred recs are tracked & resurfaced.
16. **Job Clock Setup** — clock-in/out rules (Applicable / Mandatory per job).
17. **Profit and Loss View Setup** — P&L visibility config.

## When to use
- Joe asks "why does X happen on the RO / where is Y configured" → match it to a section
  above, then read the exact field in `references/service-settings-full.txt`.
- Pairs with: `tekion-opcode-create` (Recommendation Opcode must exist there),
  `tekion-service-menu-setups`, `tekion-sitemap` (nav).

## Pre-Invoice validation rules (verified live SCT 2026-07-23)
- URL `/service/settings/ro-settings`, left-nav tab **Pre-Invoice** → "Validation Rules" table.
- Each rule row = name + Warning/Error radio pair + Applicable Job Types + Pay Types + Rule Level (Job/RO).
- **"Pending Recommendations Error"** (RO-level) = the block-invoice-without-approved/deferred-recs rule.
  Fires when recs are in RETURNED_TO_TECH, REVIEWED, SENT_TO_CUSTOMER, SUBMITTED, DRAFTED,
  PRE_DRAFTED, or CUSTOMER_APPROVED. Warning = nag only; Error = hard-blocks invoicing.
- Edit procedure via :9223: find row container by leaf text, walk up to the element containing
  ≥2 `input[type=radio]`, scrollIntoView the target radio, `/mouse` its center, then click the
  page **Submit** button (bottom-right ~1211,689) and require the "Service settings updated
  successfully" toast. Verify with a TRUE remount (nav /home → back → re-read radios) —
  same-URL re-read is a false positive (SAVE-VERIFY TRAP).

## Notification behavior is NOT centralized here (verified 2026-08-24)
Only two notification-ish items exist on this page: **"Notify customer on invoice"**
(General Setup) and the **customer-arrival** notifications (Service Communication Setup).
Everything else lives elsewhere — see skill `tekion-notification-settings-audit` for the
full 5-surface map. Most relevant here: **Parts Request** section →
*"Auto submit Parts Fulfillment request for jobs when: Job is Created, Job is Saved,
Tech is Assigned"* = the real "a job was added to the RO → tell Parts" trigger.

Live section list (TL 1092, 2026-08-24 — more than the KB's 17): General Setup ·
Opcode Mapping & Selection · Service Module Selection · Parts Request · Customer Pay ·
Warranty · Internal Pay · Reminders · Tags · RO Flag · Hold · Booker Workflow ·
Pre-Tech Finish · Pre-Job Completion · Pre-Invoice · Recommendation Addition Rules ·
RO List KPI · Total Sales · Quotes · Role Configuration · Service Communication Setup ·
Consumer Portal · Deferred Recommendation Rules · Follow up Recommendation Rules ·
Recommendation Rules · Return RO · Job Clock Setup · Profit and Loss View Setup ·
Reports · Credit Note Setup · Machine Learning · Opcode Pricing · Tax Settings.

⚠ The page renders ~1,990 innerText lines (ALL sections in one scroll). Never read it
linearly — grep the innerText array and slice around the hit index.

⚠ Routing flake: on :9223 this URL repeatedly redirected to `/parts/tax-code-setup`
even after a `/home` bounce, while loading fine on :9225. If a known-good URL keeps
landing elsewhere, switch browser lanes instead of debugging the route.

## Tags section — RO/Job tags (verified BT 1249, ST 876, TL 1092 on 2026-08-24)
- URL `/service/settings/ro-settings`, left-nav **Tags** (hash `#TAGS`). Two sub-tabs:
  **Active Tags** / **Archived Tags**.
- Table columns: Tag Type · Tag Name · Color · Text Color · Show in RO/PDF (two toggles:
  RO and PDF) · Criteria · Add Manually · Archive. Last row is always a BLANK add-row.
- **Tag Type dropdown values: `RO` · `Job` · `Recommendation`.** The Tag NAME list is
  driven by Tag Type. Under **Job** the available names are:
  PDI, Hold, Service Menu, **Add-on**, Due Bill, Recall, Recommendation,
  Deferred Recommendation, Insurance, Internal Split, Warranty Split, Manual Flag Hrs,
  Adjusted Flag Hrs, UVI, MPI, Return RO, Mobile Shop, Express Shop.
- **"Add-on" is a JOB-type tag** — the label that appears on an RO/job line for work added
  after check-in. It is NOT automatic: a row must exist here. If a store lost its "Add on"
  tag, the row was deleted (check **Archived Tags** first — Unarchive is non-destructive).
- AMG baseline 2026-08-24: BT / ST / TL each have only **3 active tags — MPI, PDI, UVI
  (all Recommendation type)** and **Archived Tags = "No rows found."** No Add-on row exists
  fleet-wide; it must be re-created, not un-archived.
- Restore recipe: blank add-row → Tag Type = **Job** → Tag Name = **Add-on** → pick
  Color/Text Color → toggle **RO** (and **PDF** if it should print) → Save.
- Mechanics: the blank row's Tag Type select sits at ~x587 on the row; Tag Name at ~x800.
  Options render in a portal — query `[class*="option"],[role="option"]` filtered by
  `offsetParent`. Navigating away without Save discards cleanly (no confirm modal fires
  from the Tags row builder). `#TAGS` hash anchor works but the page must be loaded from
  `/home` first — a direct navigate to `/service/settings/ro-settings` on a cold tab can
  silently land on an unrelated screen (`/parts/tax-code-setup`); assert `location.href`.

### Tags table — DOM mechanics that actually work (hard-won 2026-08-25, SCT 876)

The Tags grid is a **ReactTable**, and the page contains ~120 `.rt-table`s. Nothing else
below works until you anchor on the right one:

```js
const crit=[...document.querySelectorAll('.rt-resizable-header-content')]
            .find(e=>e.textContent.trim()==='Criteria');
let tbl=crit; while(tbl && !String(tbl.className||'').split(' ').includes('rt-table')) tbl=tbl.parentElement;
const rows=[...tbl.querySelectorAll('.rt-tbody .rt-tr')];   // last row = blank add-row
const cells=[...row.querySelectorAll('.rt-td')];            // 0 drag,1 Type,2 Name,3 Color,
                                                            // 4 TextColor,5 RO/PDF,6 Criteria,
                                                            // 7 AddManually,8 Archive
```

Five traps, each of which cost turns:

1. **Header text is NOT reachable by TreeWalker / leaf-`innerText` scans.** Searching for a
   leaf element whose text is `"Tag Type"` returns `[]`. The label lives in
   `.rt-resizable-header-content` — query that class directly.
2. **The table scrolls HORIZONTALLY** (`scrollWidth` 1200 vs `clientWidth` 772). Criteria /
   Add Manually / Archive sit **off-screen right** and `/mouse` will click empty space.
   Walk up from `tbl` to the first ancestor with `scrollWidth>clientWidth+5` and set
   `scrollLeft=scrollWidth` BEFORE reading coords. Re-read `getBoundingClientRect()` after.
3. **Read react-select option lists off the React fiber instead of opening the dropdown:**
   walk `cell[Object.keys(cell).find(k=>k.startsWith('__reactFiber$'))]` down `.child/.sibling`
   until `memoizedProps.options` is an array of `{label,...}`. This returned
   `["RO","Job","Recommendation"]` for Tag Type instantly, with no click and no portal race.
4. **Portal options render duplicates at NEGATIVE y.** `[class*=option]` returns rows from
   OTHER collapsed sections at `y≈-2800`. Always filter
   `e.offsetParent && e.getBoundingClientRect().y>0` or you'll `/mouse` off-canvas.
5. **`/eval` returns HTTP 500 whenever the JS throws** — a missing element mid-expression
   looks identical to "the browser broke." Guard every helper with an early
   `if(!crit) return 'NOCRIT';` and return sentinel strings, never let it throw.

### The page RESETS between turns
On :9223 the bound page reverted to a previously-open RO detail URL between nearly every
`execute_code` call. Symptom: `/eval` reads a *fully valid* DOM that belongs to the wrong
screen, and `browser_vision`/screenshot describes an unrelated page ("Pay Type Split By
Payers"). **Do the whole Tags interaction inside ONE `execute_code` call:**
`navigate /service/settings/ro-settings` → sleep 10 → `/mouse` the `Tags` `.ant-tabs-tab`
(find its live center; ~x233 but y MOVES) → sleep 5-6 → then act. Re-navigating at the top of
every call is cheap insurance; assuming continuity is not.

### What is and isn't editable on a Tag row (verified SCT 876, 2026-08-25)
- **Saved rows are LOCKED**: `Tag Type` and `Tag Name` selects carry `aria-disabled="true"`,
  and the `Add Manually` checkbox is `ant-checkbox-wrapper-disabled`. Only Color / Text Color
  and the RO / PDF checkboxes stay live. **There is no in-place edit of an existing tag's
  type/name/criteria — it's archive + re-create.** Say that to Joe before touching anything.
- **The Criteria funnel opens an EMPTY popover.** Clicking `.icon-filter` in cell[6] mounts
  `.ant-popover.root_filterDialogSection_overlay__*` whose `.ant-popover-inner-content` has
  `innerHTML.length === 0` — on every row, saved or blank, polled 10× over 7s. Nothing renders
  to edit. This IS the "I can't edit job tag filters" symptom; do not chase it as a click bug.
- **Selecting a Tag Type on the blank add-row did not commit** via `/mouse` on the portal
  option (row still read `Select`), nor via `/type` + Enter into the react-select input.
  Unresolved — flag it rather than claiming the row was built.
- AMG baseline holds: **no Job-type tag exists at SCT/BT/TL**, so there are no job-tag
  criteria to edit in the first place. Lead with that finding.

## Pitfalls
- Several behaviors are gated by **"when enabled by support"** (e.g. Select Default Service
  Advisor for jobs) — if a toggle is missing, it may need Tekion support to enable.
- Settings here STACK with **PDF Settings** and **Dealer Configurations > Customer
  Notifications** — a single behavior (e.g. showing taxes on estimate, notify-on-invoice)
  often requires BOTH the Service Settings toggle AND the corresponding PDF/Dealer-Config
  setting. Don't assume one toggle is sufficient.
