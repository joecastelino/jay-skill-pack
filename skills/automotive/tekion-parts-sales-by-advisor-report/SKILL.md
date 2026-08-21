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

## V2 PIPELINE — USE THIS (rebuilt 2026-08-20, tag-parameterized, 3 clean steps)
The 2026-08-18 one-off scripts (`build_bt_filter_report.py`,
`render_bt_cabin_air_ro_detail.py`) are SUPERSEDED. Rebuild used three small
tag-parameterized scripts in `/home/itadmin/tekion-reports/cabin-air-filter-bt/`
so any date range is one command each:

```sh
cd /home/itadmin/tekion-reports/cabin-air-filter-bt
python3 pull_bt_filters.py   2026-08-01 2026-08-21 mtd0820      # start, end(EXCLUSIVE), tag
python3 enrich_bt_filters.py mtd0820
python3 render_bt_filters.py mtd0820 "Month to Date — August 1–20, 2026"
```
Outputs `bt-{rows,summary,classification}-<tag>.json` +
`BT-Cabin-Air-Filter-By-Advisor-<tag>.{pdf,png,csv}`. The renderer prints a
`CHECK units N == summary N | rev X == X` line every run — if it doesn't match,
stop and fix the join, don't ship.

### Ledger pagination: use the `start` OFFSET — time-bisection is NOT needed
Big simplification found 2026-08-20. The internal
`POST /api/parts/activity-log/u/search` ledger **does** paginate via a `start`
offset with page size 500. Verified exact on BT: offsets 0/500/1000 returned
500/500/387 = 1387 rows, and 1387 UNIQUE ids == reported `total` 1387 (no dupes,
no drops). The older `tekion-part-sales-ledger-report` note that "pageNumber is
ignored, must recursively bisect the time window" applies to the `pageNumber`
param only — **try `start` first**, and only fall back to time-window bisection
if unique-id count != `total`. Always assert that equality before trusting a pull.

### Zero-OpenAPI-quota data path
- Sales data: internal activity-log ledger (headers reused from
  `/home/itadmin/sct-physical-2025/api-headers.json`, just override
  `dealerId` and `tek-siteId` — BT = `1249` / `-1_1249`). No browser needed,
  no OpenAPI quota burned.
- Enrichment: OpenAPI `/repair-orders:search` batched by `documentNumber`
  returns BOTH the OPCODE tags (menu vs à la carte classification) and
  `assignee` (advisor) on the same free call — one pass, no per-RO fan-out and
  no `users/{id}` name resolution needed.

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

## Page-1 must be SELF-CONTAINED (fixed 2026-08-20)
Page 1 = KPI row + ranked advisor table + top-menu-package strip + footnote,
all on ONE page. Failure mode hit: rendering the top menu packages as a
vertical 2-column table pushed the definitions footnote onto page 2, so page 2
opened with orphaned footnote text instead of the "Repair Order Detail" header.
Fix that worked — render the menu packages as a **compact horizontal strip**
capped at 6 opcodes (two rows: opcode row in `Courier-Bold` 7.5pt, units row in
`Helvetica-Bold` 12pt RED on LIGHT, `colWidths=[1.2*inch]*len(tops)`, centered,
white grid). Chose the visual redesign over shrinking the advisor table.
Verify after every layout change with BOTH:
- `p1 has footer: True` (grep page-1 extracted text for the footnote), and
- page-2 first lines == `['Repair Order Detail — By Service Advisor', '<store> · <period>']`,
then a `vision_analyze` pass on the page-1 PNG.
Trimming `top_menu_opcodes[:8]` → `[:5]` alone did NOT fix it — the table shape
was the problem, not the item count.

### Draft-only ask to Stacey — the prompt shape that worked first try (2026-08-20)
Invoke via `execute_code` + `subprocess.run([...])` argv list (NOT the top-level
`terminal` tool — parens/quotes in the message break it), with
`timeout 600` (a PDF+CSV+inline-PNG draft build takes ~135s; the 180s
foreground cap causes duplicate drafts on retry). Message must contain, in order:
1. Hard stop up front: "Create a Gmail DRAFT ONLY... DO NOT SEND. Do NOT call
   SMTP, do NOT call any send path, do NOT use X-GM-RAW send. Create the draft
   via imap.append() into [Gmail]/Drafts ONLY."
2. "Override any hardcoded report-recipient default" + explicit `TO:` — Stacey
   has store-report recipient defaults (Kevin/Tony/Ruben/Sean) that will
   hijack a Joe-only draft.
3. Body spec as numbered items with the literal numbers to print.
4. Inline PNG demanded explicitly as a **base64 data-URI img tag in the middle
   of the body**, with the note "This is required - a prior draft missed it."
5. Absolute attachment paths.
6. Terse verification one-liner to echo back:
   `TO=<addr> | INLINE_PNG=<y/n> | PDF=<y/n> | CSV=<y/n> | SENT=<y/n> | IN_DRAFTS=<y/n>`
Then INDEPENDENTLY confirm — `himalaya envelope list -a personal -f
"[Gmail]/Drafts" -s 5` (draft present) AND `-f "[Gmail]/Sent Mail" -s 3`
(nothing went out, and no duplicate drafts). Stacey's self-report alone is not proof.

## Delivery via Stacey (draft-only)
Route through Stacey (`agent-to-agent-bridge`) as usual — background/`nohup`
the `ask-agent stacey` call (foreground 180s timeouts are normal for PDF+image
rebuilds), then independently verify per `jay-gmail-draft-verification` skill.
For a multi-page detail PDF specifically, PNG-only verification isn't enough —
extract text from the bytes pulled straight from the draft's own
`application/pdf` MIME part to confirm page count AND that page 2+ actually
contains the RO detail rows (not just the summary repeated).

### PDF tooling in Jay's environment (settled 2026-08-18 — don't re-litigate)
- `import fitz` (PyMuPDF) **works**. An earlier session concluded it was
  "broken in this venv" — that was a wrong-interpreter artifact. Retry `fitz`
  first; it's the fastest path to BOTH text (`page.get_text()`) and raster
  (`page.get_pixmap(dpi=110).save(png)`) for vision checks.
- `pypdf.PdfReader` failed (exit 1) on these files — don't rely on it.
- poppler-utils (`pdftoppm`, `pdfinfo`) is **not installed**; `apt-get install`
  attempts were inconclusive. Don't burn turns on it.

### Two-proof verification loop (mandatory — never trust a self-report)
1. `himalaya attachment download -a personal -f "[Gmail]/Drafts" <id>`
   (no `-o` flag; lands in /tmp under its original filename).
2. **Byte proof**: `sha256sum` / size-compare the downloaded attachment against
   Jay's local source PDF. Byte-identical = the draft really carries the file
   Jay built (rules out a stale/swapped attachment).
3. **Visual proof**: `fitz` render pages → `vision_analyze`. Required because
   the plain-string-cell overflow bug is INVISIBLE to text extraction.
4. **Sent-vs-draft proof**: check the message's IMAP FLAGS/labels. `\Draft`
   only = unsent. Presence of `\Sent` or `\Inbox` means it actually went out —
   Stacey's `SENT=n` self-report has been wrong before, and a claimed draft ID
   has also turned out to not exist anywhere (Drafts/Trash/All Mail).

## Draft-refresh gotcha (BT cabin/air filter, 2026-08-18)
If a draft was already sent to Stacey/appended to Drafts BEFORE the final
per-advisor-page-break fix landed, the draft's PDF attachment is now STALE
(old page count, no page breaks) even though the subject/body look final.
**Always re-verify the ACTUAL attachment bytes in the live Drafts message**
(download via `himalaya attachment download`, then `pypdf.PdfReader` page
count + spot-check page 0/3/last) — don't trust that "a draft exists with the
right subject" means it has the latest PDF. If stale: delete the old draft via
IMAP (`imap.store(id, '+FLAGS', '\\Deleted')` + `imap.expunge()`) and append a
fresh one with the corrected file. Note: `himalaya envelope list` can still
show a `\Deleted`-flagged message until expunge fully propagates — confirm
with a raw IMAP FETCH FLAGS on that UID returning empty/no-data.

**"I don't see it in drafts" → check Trash first.** Joe will silently trash a
draft himself the moment he opens the PDF and sees a layout defect. A draft
vanishing from Drafts is usually Joe rejecting it, not a delivery failure — pull
it from `[Gmail]/Trash`, download its attachment, and render the pages to find
what he saw. That's how the customer-name overflow bug was actually caught.

## Automating it (Joe's usual next ask after approving a draft)
Joe reviews one hand-built draft, then says "now automate it." Before wiring a
cron, get three answers from him: **cadence** (daily MTD / weekly / month-end),
**recipient** (Joe only, or the store manager too — BT = Tony Garcia
agarcia@blackstonetoyota.com), and **auto-send vs draft-only**. Don't guess —
draft-only vs auto-send is the one he cares about most.

Cron shape is just the three tag-parameterized commands with a date-derived tag:
```sh
TAG=$(date +mtd%m%d); START=$(date +%Y-%m-01); END=$(date -d tomorrow +%Y-%m-%d)
cd /home/itadmin/tekion-reports/cabin-air-filter-bt
python3 pull_bt_filters.py   "$START" "$END" "$TAG"
python3 enrich_bt_filters.py "$TAG"
python3 render_bt_filters.py "$TAG" "Month to Date — $(date '+%B 1–%-d, %Y')"
```
Then hand the PDF/CSV/PNG paths to Stacey via the bridge. Gate the render on the
`CHECK units N == summary N` line — abort the email step if it doesn't match
rather than mailing a broken report. Follow the BT/BC/TOL cron pattern: deliver
to the store's designated Slack thread and/or Stacey draft, never both blind.

## Reusability
This pattern (RO-only ledger join + advisor resolution + summary-then-detail
PDF) generalizes to any "parts sold by X, broken down by advisor" ask —
alignment services, tires, batteries, any specific opcode/part category.
Swap the PN-prefix classification step and reuse the join/render/verify
pipeline as-is.
