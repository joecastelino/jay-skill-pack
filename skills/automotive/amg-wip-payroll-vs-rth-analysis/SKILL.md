---
name: amg-wip-payroll-vs-rth-analysis
description: Analyze an AMG per-store semi-monthly WIP workbook (tech payroll vs RTH / labor relieved to WIP) and produce Joe's service-manager meeting prep — trend table, per-tech gap ranking, talking points, recoverable-$ target. First run 2026-07-08 on "2026- SCWV Wip.xlsx" (Stevens Creek VW); Joe approved the format verbatim.
---

# AMG WIP Payroll-vs-RTH Analysis (Service Manager Meeting Prep)

## When to use
Joe drops a store WIP workbook (e.g. "2026- SCWV Wip.xlsx") and asks for "input" ahead of a meeting with the store's service manager. NOTE: this is DISTINCT from /home/itadmin/amg-wip/AMG-WIP.xlsx (the monthly fixed-ops metric tracker, rows=metrics cols=months). This one is the payroll reconciliation workbook.

## Workbook structure
- One tab per SEMI-MONTHLY pay period (two per month, e.g. "1-15" and "16-31" halves), Jan onward.
- Rows = technicians. Columns include gross pay, pay after R&R/OT adjustments, OT premium, RTH (retail time hours / labor $ relieved to WIP), and the gap allocation.
- The payroll-minus-RTH gap is booked to GL accounts:
  - **5416 Unapplied Labor** — the number that matters
  - **6424 Sal & Wages** — guarantee/hourly techs (lube/shop/detail roles)
  - **6444 Training**
- Also cross-references monthly service gross.

## Analysis recipe (Joe-approved format)
1. **Parse with openpyxl/pandas**, combine both halves per month for full-month figures.
2. **6-month trend table**: Month | Payroll | RTH relieved | Applied % (RTH/Payroll) | Unapplied booked. Bold the best and worst months.
3. **Per-tech table for the problem month**: Tech | Pay (after R&R/OT) | RTH | Applied % | $ Gap, **ranked by gap descending**. Tag which techs' gaps flow to 6424 (guarantee). Call out best performers too (shows it's achievable).
4. **Key diagnostic framings Joe uses**:
   - Half the shop under 50% applied = shop-loading/dispatch problem, not one bad tech.
   - Best recent month proves the roster CAN hit that applied % → recoverable $ = (best% − actual%) × payroll. Anchor the meeting on that number.
   - Guarantee bucket (6424) = "do these guarantees still make sense at current volume?"
   - OT premium paid while unapplied is high = OT-approval process question.
   - Unapplied as % of service gross for scale.
5. **Talking points, not a to-do list**: per Joe's meeting-prep rule (see amg-store-manager-meeting-prep skill), frame as questions Joe asks + levers JOE owns, not orders for the manager.
6. **The killer cross-check offer**: pull the store's Tekion **Tech Performance (Beta)** report (/core/reports/service/tech-performance — attendance hrs vs flagged hrs, proficiency %) for the same period. If proficiency is fine but applied % dropped → hours exist but aren't being relieved to WIP correctly (flagging problem); if proficiency also dropped → dispatch/traffic problem. This answers "is it dispatch or is it flagging" before the meeting.

## Baseline (SCVW, H1 2026)
Applied % ranged 53.4% (Jun, worst — $31.8K unapplied) to 69.5% (Apr, best — $14.7K). Monthly payroll ~$95–110K. Use April-level ~70% as the achievable target at SCVW.

## Delivery
Email through Stacey (she owns report emails) to Joe's inbox, HTML tables, worst numbers flagged red. Remember Gmail self-send dedup: From==To==Joe lands only in Sent — Stacey must also append a copy to INBOX; verify in INBOX, never Sent Mail.

## Pitfalls
- Semi-monthly halves must be COMBINED before month-over-month comparison — a single half looks artificially bad/good.
- Training (6444) coding is inconsistent across periods — mention but don't build conclusions on it.
- Use pay AFTER R&R/OT adjustments for the per-tech gap, not raw gross.
