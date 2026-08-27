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

## TWO RENDERERS — pick by what the user asked for
- `render_advisor_closed_gross.py` — house scorecard style (hero KPI cards, ranked
  advisor table with red bars). Good for a summary/exec read.
- `render_advisor_perf_style.py` — **looks like Tekion's Advisor Performance
  Report**. Use this when the user says "make it look like that report" / "the same
  way it was in advisor performance report" (Joe, 2026-08-27). Outputs `<stem>_perf.{png,pdf,csv}`.

### Advisor-Performance lookalike spec (matches the native screen)
1500px page. **TOTAL row sits at the TOP** of the table (Tekion does this), then
advisors ranked by total gross. Thirteen columns in this exact order:

`Service Advisor · RO Count · Bill Hrs · ELR ($) · Hrs/RO · Labor Sale · Labor Cost ·
Labor Gross · Parts Sale · Parts Cost · Parts Gross · Parts GP % · Total Gross`

Styling: light `#f5f6f7` header (not the dark house header), right-aligned numerics,
filter chips under the title showing the applied scope, then a **Pay Type Mix** table
(Customer Pay / CVSC / Warranty / Internal / No Charge with RO counts + gross).
Page 2 = per-advisor RO detail with a subtotal row per advisor.

## ⭐ Billed hours / ELR / Hrs-per-RO ARE available (discovered 2026-08-27)
`operation.labor.billDuration` is **SECONDS** — `2880` = 0.80 hr. Verified against
the UI showing 0.80 hr on SMOG. So:
- `bill_hrs = sum(billDuration)/3600`
- `ELR = labor_sale / bill_hrs`
- `Hrs/RO = bill_hrs / ro_count`
`laborAllowanceDuration` sits alongside it (same units). This is what lets the API
report reproduce the native report's hour columns — don't tell the user hours are
unavailable.

Coupons/fees are LINK stubs on the search result (`/ro-coupons`, `/ro-fees`);
`ro-coupons` returned an empty `data` object at SCT, and `/ro-sublets` is **404**.
So Coupon Labor / Coupon Part / Sublet columns can't be reproduced yet — omit them
rather than showing zeros that look real.

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
4. **Do NOT trust vision on layout geometry.** On 2026-08-27 vision reported "logo
   missing, only 12 of 13 columns, Total Gross cut off at the right edge" — all
   false. Measure the DOM instead:
   ```python
   pg.evaluate("document.body.scrollWidth")            # vs page width
   pg.evaluate("[...document.querySelectorAll('th')].map(h=>h.getBoundingClientRect().right)")
   pg.evaluate("(document.querySelector('.hd img')||{}).naturalWidth")  # 0 = logo broken
   ```
   Table right edge < page width ⇒ nothing is clipped. Vision is for "does this look
   like the right report", never for whether a column fits.

## Delivering it by email
Joe's usual ask is "email it to me." Route through **Stacey** (`~/bin/ask-agent`,
argument-list form via `execute_code` — parens/quotes break the top-level terminal
tool). Demand a **CID inline** PNG (`multipart/related`, `Content-ID: <scorecard>`,
`<img src="cid:scorecard">`) and explicitly forbid `data:` URIs — Gmail blocks those
and renders a broken image. Attach the PDF + CSV as regular attachments.

**Verify in INBOX, never Sent** — and verify the MIME tree, not just that a message
exists. Self-sends (From==To==Joe) can land only in Sent; and himalaya's `message
read` shows the *text* part, so "cid:scorecard not found" there is a false alarm.
Use imaplib and walk the parts:
```python
for p in msg.walk():
    print(p.get_content_type(), p.get('Content-ID'), p.get('Content-Disposition'))
```
Expect: `multipart/mixed → multipart/related → multipart/alternative(text+html)`,
an `image/png` with `CID=<scorecard>` + `disp=inline`, plus pdf/csv attachments,
and `cid:scorecard in html == True` / `data:image in html == False`.

## Cron vs one-off
Don't assume a recurring job. Joe explicitly declined a cron here ("I dont want it
on a cron job, just a 1 time report for now") — offer it, but default to a one-time
run unless he says otherwise.

## Pitfalls
- f-strings can't contain backslashes in the expression part — build conditional
  HTML fragments (e.g. the logo `<img>`) with `%` formatting on a prior line.
- A full-store day scan with jobs/ops/parts fan-out runs ~3+ min → launch with
  `terminal(background=true, notify_on_complete=True)`, not the 300s code tool.
- Logo lives at `/home/itadmin/tekion-reports/logo_0.png`; base64-embed it.
- Reuse the house visual language: white bg, red `#EB0A1E` rule + hero KPI,
  `#1a1a1a` table header, green totals, red bar scaled to leader.
