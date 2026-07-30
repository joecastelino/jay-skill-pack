---
name: tekion-tech-flag-hours-pay
description: Answer "how do we pay techs for unapplied time / extra clocked hours" questions and diagnose flag-hours pay problems in Tekion. Covers how tech pay actually flows (flag hours -> Flag Hours Report -> payroll), the manual flag entry modal, adjusting flag time on CLOSED ROs without reopening, the Wage Type Config $0.00 labor-cost trap, and the unapplied-hours definition. Verified via Tekion KB (KB0018796, KB0025203, KB0014998, KB0020953) on the SV RO 372190 case, 2026-07-29.
triggers:
  - pay techs unapplied time
  - tech flag hours
  - flag hours adjustment
  - labor cost zero technician
  - flag time closed ro
---

# Tekion — Paying Techs / Flag Hours Mechanics

## When to use
A store manager (via Joe) asks "how do we pay our techs for unapplied time?",
"tech clocked more than billed — how do we make them whole?", or a flagged-hours
entry isn't paying/costing correctly.

## Core definitions (KB-verified)
- **Unapplied hours = attendance hours − assigned billed hours** (KB0018796,
  Tech Performance Report). By definition it has NO RO/opcode — it's time in the
  building not covered by billed work.
- **Flat-rate techs are paid on FLAG hours** — payroll pulls from the Flag Hours /
  Tech Performance report. Hourly/clock techs are paid on ATTENDANCE via payroll;
  flagging only affects their proficiency stats, not their pay.
- **Labor Cost on the RO pulls from Wage Type Config** on each tech's Employee
  Onboarding → Employment Details tab (KB0020953). Wage types can be $/hr, % of
  labor sale, or fixed amount, and can vary by pay type/opcode/make/service type.
  The same rate feeds Labor Cost in the Tech Performance report.

## Answer template ("pay techs for unapplied time")
Depends on the pay plan:
1. **Flat-rate**: pay via flag hours. On an OPEN RO: job → kebab (⋮ above the
   camera icon) → **Tech Flag Hours** → enter flag hrs, set **Reason + Flag Type**,
   Save (KB0025203). NOTE: adding a MANUAL entry disables auto-calculation of flag
   hours for that job (banner in the modal). Splitting among techs: labor + bill +
   flag hrs per tech must total the job's labor hours.
2. **Hourly**: nothing to do on the RO — attendance pays them already.
3. Whether to flag actual > billed at all is a PAY-PLAN/POLICY call (who eats the
   gap) — frame that part for Joe, don't decide it.

## Closed ROs — adjust WITHOUT reopening (KB0014998)
Reports tile → **Flag Hours Report** → **Add Adjustment** (top right) → select RO
+ job → adjust technician flag time. No reopen needed. (Remember: if Flag Tech on
= "RO Invoiced" in Service Settings, flag hrs lock at invoice — this adjustment
path is the sanctioned fix.)

## Traps / diagnostics
- **$0.00 Labor Cost next to a flagged tech = Wage Type Config missing/empty** on
  that tech's employee profile. Flagged hours then carry ZERO cost to the RO/GL —
  pay won't post correctly regardless of what's flagged. Fixing = employee-record
  edit → **Joe's hard rule: never touch employee records without his explicit
  permission** — flag it and ask.
- **Pre-invoice rule**: Service Settings can require flag hrs = bill hrs as an
  ERROR (blocks invoicing) vs warning. If flag ≠ bill is intended (paying actual
  on a short-billed diag), check that rule first.
- **"Flag Tech on" setting** (Service Settings): Manual / Job Save / RO Invoiced /
  Job Completed controls when flag auto-syncs to bill hrs. Manual = wage type
  configs do NOT apply.
- Local reference on these settings: `/home/itadmin/tekion-kb/text/SERVICE_SETTINGS_clean.txt`
  (grep "Flag Tech on").

## Getting the RO facts fast (no browser)
OpenAPI `repair-orders:search` `documentNumber IN ["<ro#>"]` + jobs/operations
fan-out gives job payTypes, opcodes, labor sale/cost (CENTS). Actual clocked vs
billed per opcode/tech = skill `tekion-clock-time-by-opcode` (TECH_CLOCK
datasource). The screenshot modal's "Actual hrs" column = job clock punches.

## KB lookup path
`python3 /home/itadmin/tekion-reports/kb_search_scrape.py search "flag hours"` /
`article KBxxxxxxx`. If it errors "KB not authenticated": restore :9223 auth
(login.py --force + cookie/21-localStorage-key injection per
persistent-browser-server skill), then `/navigate` to
`https://app.tekioncloud.com/core/knowledge-base/search` (auto-SSO), then retry.
Key articles: KB0018796 (unapplied calc), KB0025203 (tech flag hours how-to),
KB0014998 (closed-RO adjustment), KB0020953 (labor cost / wage types).

## Reference case (SV RO 372190, 2026-07-29)
Asked by Galang Mo <gmo@scvolkswagen.com> (SV service management — emails Joe
RO-level tech-pay questions). EV range diag: 3.03 actual clocked (techs Jeffrey
Ragamat 0.34 + Loreto Tubilla 2.69) vs 0.60 billed ($300 CP diag); both techs
showed $0.00 Labor Cost → wage-type gap; answer = flag-hours path for flat-rate
+ fix wage types (Joe-permission gate) + policy call on eating the 2.4 hr gap.
Pattern note: SV also had REC +44 hrs over-clock in July 2026 — long-diag
over-clocking is a recurring SV leak.
