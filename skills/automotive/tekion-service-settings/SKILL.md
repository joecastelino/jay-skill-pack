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

## Pitfalls
- Several behaviors are gated by **"when enabled by support"** (e.g. Select Default Service
  Advisor for jobs) — if a toggle is missing, it may need Tekion support to enable.
- Settings here STACK with **PDF Settings** and **Dealer Configurations > Customer
  Notifications** — a single behavior (e.g. showing taxes on estimate, notify-on-invoice)
  often requires BOTH the Service Settings toggle AND the corresponding PDF/Dealer-Config
  setting. Don't assume one toggle is sufficient.
