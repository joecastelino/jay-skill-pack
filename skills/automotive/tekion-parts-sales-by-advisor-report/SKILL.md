---
name: tekion-parts-sales-by-advisor-report
description: Build a Tekion parts-sales-by-service-advisor report (e.g. cabin/engine air filters, or any specific part category) for any AMG store — units, revenue, menu-attach, ranked bar-chart summary AND full RO-level line-item detail per advisor. Use whenever Joe asks for a parts sales report "broken down by advisor" or "like the alignment report" — he means BOTH a summary table AND the underlying RO detail, not just aggregate numbers.
---

# Tekion Parts Sales — By Service Advisor (with RO-level detail)

## Critical lesson (BT cabin/air filter report, 2026-08-18 — cost 3 rebuild cycles)
When Joe asks for a parts-sales report "broken down by advisor," he does NOT
mean a plain per-advisor summary table with a rank/bar-chart (that's what the
SCT Alignment-by-Advisor report shows and what Jay defaulted to twice — Joe
rejected both: "still no advisor detail... I don't know what repair orders
each advisor sold on"). For PARTS reports specifically, "by advisor" means:

1. **Page 1**: KPI summary + ranked advisor table with bar chart (units, revenue,
   menu-attached, RO count per advisor) — this part IS like the alignment report.
2. **Page 2+**: a full RO-LEVEL DETAIL table, one section per advisor (sorted by
   rank), listing every individual line item: RO#, date, customer, category
   (cabin/air), part number, type (menu vs à la carte), qty, revenue. This is
   the part that's DIFFERENT from the alignment report and was missing from
   the first two attempts — Joe wants to see exactly which ROs and customers
   produced each advisor's numbers, not just the rolled-up total.

Always build BOTH pages/sections into one PDF from the start for any
parts-sales-by-advisor ask. Don't ship summary-only and wait for a correction.

## Data pipeline (BT cabin/air filter example, dealer 1249)
Working directory: `/home/itadmin/tekion-reports/cabin-air-filter-bt/`

1. **Part number scoping**: cabin filter PN prefix `87139`, engine air filter
   PN prefix `17801` (Toyota). Confirm PN prefixes for the target part/store
   before reusing this pattern elsewhere — don't assume Toyota prefixes apply
   to VW/GM stores.
2. **RO-only ledger** (excludes counter/parts-sales-order rows): join ledger
   rows to `refType == FULFILMENT` (RO-attached), NOT `SALES_ORDER` (counter).
   Saved as `bt-detail-rows.json` / `bt-mtd-rows-with-advisor.json`.
3. **Advisor attribution**: pull `assignee.advisor.id` per RO from
   `/repair-orders:search` results (`bt-ro-search-results.json`), then resolve
   advisor UUIDs to names via Tekion OpenAPI `GET /openapi/v4.0.0/users/{id}`
   with `dealer_id = "americanmotorscorporation_<dealer#>_0"` (see
   `/home/itadmin/tekion-api/tekion_client.py` for `load_config`/`get_token`/
   `api_get`). Cache resolved names (`bt-advisor-names.json`) — don't re-resolve
   every run.
4. **Join** ledger rows + advisor names into one row-per-line-item list
   (`ro`, `category`, `class` [menu/ala_carte], `partNumber`, `qty_signed`,
   `lineRevenue`, `transactionTime`, `customer`, `advisor_id`, `advisor_name`).
   ALWAYS reconcile: `sum(qty_signed)` and `sum(lineRevenue)` grouped by advisor
   must equal the store-wide MTD totals exactly (e.g. 502 units / $14,126.21) —
   if they don't match, the advisor join has a bug (missing/duplicate rows).

## Renderer (reportlab, two-page-type PDF)
Script: `/home/itadmin/tekion-reports/cabin-air-filter-bt/render_bt_cabin_air_ro_detail.py`

- Page 1: KPI boxes (dark header, red numbers) + advisor summary table
  (rank, name, category splits, total, revenue, menu units, RO count, ASCII
  block-character bar `█` scaled to max advisor's units) — same visual style
  as `render_alignment_by_advisor.py`.
- `PageBreak()`, then loop advisors (already rank-sorted): a `Paragraph`
  header line per advisor (`"NAME — N units · $X · N ROs (...)"`) followed by
  a compact `Table` of that advisor's individual line items (RO#, date,
  customer, category, part#, type, qty, revenue), alternating row shading.
- Gotcha: `customer` field can be `None` in raw ledger rows — guard with
  `(r.get('customer') or 'N/A').strip() or 'N/A'` before use, else `TypeError:
  'NoneType' object is not subscriptable` on render.
- **Customer/description columns MUST use `Paragraph`, not a plain string** —
  a plain Python string in a `reportlab.platypus.Table` cell does NOT wrap; a
  long customer name visually overflows into the next column (e.g.
  "JACQUELINE CASTROCAMACHO Cabin" running together) even though `pypdf`
  text-extraction still reads the words in the right order (extraction doesn't
  care about visual boundaries, so this bug is INVISIBLE to text-only
  verification — you must render to PNG and vision-check at least one detail
  page). Fix:
  ```python
  cell_style = ParagraphStyle('cell', fontSize=7.5, leading=9)
  row = [ro_num, date, Paragraph(customer_name, cell_style), category, ...]
  ```
  Widen that column slightly too (e.g. 1.4in -> 1.5in).
- This naturally produces a long PDF (17-25+ pages for ~500 line items across
  17 advisors) — that's expected and correct, not a formatting bug.
- **Joe wants each advisor's detail section starting on its OWN page**, not
  just back-to-back in a running list (corrected 2026-08-18, after the
  overflow-bug rebuild). Insert a `PageBreak()` before every advisor except the
  first:
  ```python
  for idx, a in enumerate(adv_summary):
      if idx > 0:
          story.append(PageBreak())
          story.append(Paragraph("Repair Order Detail — By Service Advisor (cont.)", sub_style))
      story.append(Paragraph(f"{a['name']} — ...", h3_style))
      ... # that advisor's table
  ```
  A busy advisor's table can still spill onto a 2nd physical page if it has
  many rows (e.g. 60 line items) — that's fine, the NEXT advisor still starts
  fresh on a new page after that spillover. Don't treat page count growing
  past the advisor count as a bug — verify by extracting each page's text and
  checking which advisor-header lines start which page indices.

## Delivery via Stacey (draft-only)
Route through Stacey (`agent-to-agent-bridge`) as usual — background/`nohup`
the `ask-agent stacey` call (foreground 180s timeouts are normal for PDF+image
rebuilds), then independently verify per `jay-gmail-draft-verification` skill.
For a multi-page detail PDF specifically, PNG-only verification isn't enough —
use `pypdf.PdfReader` on the bytes pulled straight from the draft's own
`application/pdf` MIME part to confirm page count AND that page 2+ actually
contains the RO detail rows (not just the summary repeated).

## Reusability
This pattern (RO-only ledger join + advisor resolution + summary-then-detail
PDF) generalizes to any "parts sold by X, broken down by advisor" ask —
alignment services, tires, batteries, any specific opcode/part category.
Swap the PN-prefix classification step and reuse the join/render/verify
pipeline as-is.
