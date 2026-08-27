---
name: tekion-advisor-closed-gross-api-report
description: Build/run an API-sourced advisor gross report for closed ROs at any AMG store, replacing Tekion's unreliable Advisor Performance Report. Keys on true per-invoice pay-type close time and counts ALL pay types (CP, CVSC, warranty, internal).
triggers:
  - advisor gross report
  - build it via the api
  - advisor performance report is wrong
  - gross closed yesterday by advisor
  - replace the tekion report
---

# Advisor Closed-Gross Report (API)

## When to use
Joe's escalation path once a native Tekion report is shown unreliable is
**"can you build a report for me via the API?"** — anticipate it. Tekion's Advisor
Performance Report undercounts three separate ways (see
`tekion-gross-not-posting-to-advisor`): Status INVOICED-vs-CLOSED, Pay Type View
hiding CVSC/warranty, and a closed-date filter that drops ROs. This report is
immune to all three.

## Run it
```bash
cd /home/itadmin/tekion-reports
python3 advisor_closed_gross.py --store st --date yesterday
python3 render_advisor_closed_gross.py out/<json path it prints>
```
Flags: `--store st|bt|bc|sv|tl|ar|vc`, `--date YYYY-MM-DD|yesterday|today`,
`--from/--to` for ranges, `--advisor <id>` to scope one advisor, `--tag` to
suffix the filename. Outputs PNG (page-1 summary), PDF (full RO detail), CSV
(Joe sorts/filters these himself — always produce it).

## How it works (why it beats the UI report)
- Enumerates via `repair-orders:search` on **`closedTime` BTW** with
  **recursive bisection** — `closedTime` pagination tokens drift out of the
  window, so never chain `paginationToken` here (see `tekion-openapi-repair-orders`).
- Recomputes gross from line items: labor `saleAmount-costAmount` + parts
  `saleAmount-costAmount`, **all CENTS ÷100**.
- Keys the day bucket on **per-invoice `closedTime`** from
  `/repair-orders/{rid}/ro-invoices`, not RO status or invoice date.
- Counts every `subPayType`, so CVSC/warranty work can't vanish.
- Resolves advisor names via `GET /users/{id}` (cached in-process).
- Auto-flags **negative-gross** ROs and **partially-closed** ROs in a banner.

## KNOWN GAP — be upfront about this
An RO whose pay-type invoices are *partially* closed (e.g. CP closed, Internal
still open → RO status stays `INVOICED`) is **excluded by Tekion's server-side
`closedTime` filter**, so the script never sees it and the `partial_close` flag
can't fire. Verified: RO 581255 (~$64) was missed while 9 of 10 others were caught.
Tell the user this rather than presenting the total as complete. To close the gap,
add a second pass over `status=INVOICED` ROs in the window and union the results.

## Validation protocol (do this before shipping any run)
1. Hand-verify one day via the API and save the RO list to JSON.
2. Diff the script output against it — **investigate every discrepancy**, don't
   wave off an off-by-one. That diff is what surfaced the partial-close gap.
3. `vision_analyze` the PNG for layout breakage (logo, KPIs, overlap, banners).
   Note: a banner that doesn't appear may mean the *data* lacks that case, not a
   render bug — check the data before "fixing" the template.

## Pitfalls
- f-strings can't contain backslashes in the expression part — build conditional
  HTML fragments (e.g. the logo `<img>`) with `%` formatting on a prior line.
- A full-store day scan with jobs/ops/parts fan-out runs ~3+ min → launch with
  `terminal(background=true, notify_on_complete=True)`, not the 300s code tool.
- Logo lives at `/home/itadmin/tekion-reports/logo_0.png`; base64-embed it.
- Reuse the house visual language: white bg, red `#EB0A1E` rule + hero KPI,
  `#1a1a1a` table header, green totals, red bar scaled to leader.
