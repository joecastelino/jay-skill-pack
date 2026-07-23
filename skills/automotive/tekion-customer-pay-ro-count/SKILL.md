---
name: tekion-customer-pay-ro-count
description: Produce the TRUE count + CP dollars + revenue/RO of customer-pay repair orders for a store per month OR per week (incl. prior-4-week trend averages) via Tekion OpenAPI — CP invoice dollars > $0.01, not the misleading CUSTOMER_PAY tag. Verified SCT June 2026 (1,928 of 5,381) and BC weekly 2026-07-05 (226 of 604).
---

# Tekion Customer-Pay RO Count (true invoiced dollars)

Joe's ask pattern: "true numbers for customer-pay ROs for [month] — customer pay over $0.01, need count and RO number."

## Critical insight — tag vs dollars
The `CUSTOMER_PAY` payType TAG on `/repair-orders:search` **overstates** true CP. The tag means a CP line existed at some point on the RO, NOT that customer-pay dollars actually invoiced. Verified SCT June 2026: **4,511 tagged vs 1,928 with actual CP invoiceAmount > $0.01** (of 5,381 closed). Canned reports and tag-counting give the inflated number — Joe wants the invoiced-amount truth.

## Method
1. **Index pass** (fast, free fields): `/repair-orders:search` for the store, `closedTime` window = target month (Pacific tz), status IN CLOSED,INVOICED. Collect all RO ids + numbers. Report the preliminary tag count to Joe so he knows a scan is running.
2. **Fan-out** (slow): for EVERY closed RO, pull `ro-invoices` and sum `invoiceAmount` where payType == CUSTOMER_PAY.
   - **CENTS**: all Tekion $ fields are integer cents — ALWAYS `/100`.
   - Pace under Tekion's rate limit (429 backoff). ~5,400 ROs ≈ 60–90 min.
   - Run as **background** job (`terminal` background=true, invoke with explicit `/usr/bin/bash`), write results + log to files, verify exit code not just log tail.
3. **Filter**: keep ROs where CP total > $0.01. Output count, total $, largest/smallest, and CSV (RO# + CP amount) to `/home/itadmin/tekion-reports/data/` (persistent path — NOT `~`).

## Reference implementations
- Monthly: `/home/itadmin/tekion-reports/sct_june_cp_scan.py` (SCT) — adapt dealer id + date window. Uses `tekion_client.get_token`.
- **Weekly + prior-4-week trend (BC, built 2026-07-05)**: `/home/itadmin/tekion-reports/bc_week_cp.py` (single Mon–Sun week) and `bc_prior4wk_cp.py` (4 prior weeks, per-week buckets + averages). Both reuse `bc_menu_sales_api as O` (O.call has BC dealer 1251 headers) and `search_closed()` from `bc_menu_sales_closed_mtd.py` — for other stores swap in that store's `*_menu_sales_api` module or clone with the right dealer id.

## Weekly-trend gotchas (learned 2026-07-05)
- **Search results do NOT echo closedTime back** (filter works, field returns null) — so to bucket ROs by week you MUST run a separate `search_closed()` query per week window and tag each RO with its week index at index time. You cannot fetch one big window and bucket afterward.
- RO number on search results = `documentNumber` (fallback `repairOrderNumber`); id = `documentId`. Dedupe by documentId.
- Timing: ~0.55s/RO pacing → 604 ROs ≈ 10 min, 1,812 ROs ≈ 25–30 min. Tell Joe the ETA up front and run background with notify_on_complete.
- Joe's "this week" = Mon–Sun Pacific, current partial week through now; "prior 4-week average" = the four full Mon–Sun weeks before it.
- Delivery format Joe asked for verbatim: `CP RO count: [#] | CP revenue: [$] | revenue/RO: [$]`, then for trend a per-week table + avg weekly count + overall rev/RO, with % deltas vs current week. He likes the holiday-week context noted.

## Advisor breakdown (added 2026-07-06, BC)
Joe follows up with \"breakdown by advisor\" — NO re-fan-out needed. `assignee.advisor.id` is FREE on the `/repair-orders:search` response; join it against the per-RO CP dollars already scanned (keyed by documentId), resolve names via OpenAPI `GET /users/{id}` (`userNameDetails.completeNames[DISPLAY_NAME]`). Advisor = final RO assignee. Output table: Advisor | CP ROs | CP Revenue | Rev/RO, plus prior-4-week per-advisor avg ROs/wk + Rev/RO columns for comparison, ranked by CP revenue, Total row at bottom. Flag standouts (big rev/RO swings vs their P4W norm) with 2-3 bullets. Cache the id→name map per store (cf. sct-advisor-cache.json pattern).

## Defaults Joe accepts (state inline, don't block)
- "Last month" = prior calendar month, ROs **closed** in window, Pacific.
- "Customer pay over $0.01" = CP invoice amount > $0.01 regardless of other pay types on the RO.
- Default store = whichever was discussed; offer to run all 7.

## Delivery
- Slack: count headline first (Joe cares about the single number), total $, largest/smallest, MEDIA: link to CSV.
- Email via Stacey — **WARNING**: Stacey's himalaya template send can emit raw MML `<#multipart>/<#part>` markup as the literal body = no attachment. For attachment emails, tell her to build real MIME via python smtplib, or resend yourself via the proven SMTP fallback (app pw from her himalaya config.toml, multipart/mixed + MIMEBase). Verify the attachment actually landed, not just the subject in Sent Mail.

## Pitfalls
- Don't report the tag count as the answer — it's ~2.3x inflated.
- Forgetting `/100` on cents → absurd totals (e.g. $96M instead of $963K).
- Save outputs to `/home/itadmin/tekion-reports/data/` (survives profile reset), not `~`.
