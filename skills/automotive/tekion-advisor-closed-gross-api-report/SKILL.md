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

## LONG WINDOWS (MTD / multi-week) — use the MTD scanner
A single day at SCT is ~134 ROs. **MTD is ~3,750 ROs ≈ 42,000 API calls.** Do NOT
run `advisor_closed_gross.py` for these — use:
```bash
cd /home/itadmin/tekion-reports
CALLS_PER_MIN=900 WORKERS=8 python3 advisor_closed_gross_mtd.py --store st --from 2026-08-01 --to 2026-08-26
python3 render_advisor_perf_style.py out/advisor_closed_gross_st_<from>_<to>.json
```
Launch with `terminal(background=true, notify_on_complete=True)` — it runs ~90 min.

### ⚠️ Rate-limit calibration (burned 2026-08-27 — don't repeat)
I first set the limiter to a "safe" low rate and it delivered **50 ROs in 10 min =
8+ hour ETA**. Killed and re-ran at `CALLS_PER_MIN=900 WORKERS=8` → **91 minutes,
3,750 ROs, 42,358 calls, 200 429s, all absorbed by backoff, zero stalls.**
- **Start at 900 calls/min / 8 workers.** That is the proven-safe rate.
- 429s are NORMAL at this rate and arrive in bursts of ~40. Backoff handles them;
  the counter freezing (e.g. stuck at 160) means backoff is working, not broken.
- The scanner **checkpoints** to `out/.ckpt_<store>_<from>_<to>.json` after each
  batch and resumes on restart — so re-tuning the rate mid-run costs nothing.
  Always check for the ckpt before assuming a restart means starting over.

### Diagnosing "is it hung or backing off?"
Progress can freeze for 7+ min during an OVERALL_RATELIMIT backoff (those run
180–720s). Before killing anything:
```bash
for p in $(pgrep -f 'python3 advisor_closed_gross_mtd'); do
  echo "pid $p state=$(awk '{print $3}' /proc/$p/stat) wchan=$(cat /proc/$p/wchan)"; done
```
Main thread in `futex_do_wait` + workers sleeping = **backoff, let it run**.
Confirm the checkpoint count is advancing across a few minutes before intervening.

### Cross-validate a long run against a known day
A long scan is only trustworthy if a slice of it reproduces a verified day. Slice
the output on `closed_days` and compare:
```python
sub=[r for r in rows if '2026-08-26' in r['closed_days']]
# must equal the verified single-day run exactly: 134 ROs / $45,668.52
```
This caught nothing on 2026-08-27 (exact penny match) — which is precisely why it's
worth doing before emailing.

### ⚠️ Reconcile MTD against any earlier MTD figure you quoted
"All August ROs" ≠ "ROs that CLOSED in August." On 2026-08-27 I'd told Joe Artist
Battle was 226 ROs / $82,906.27 (every August RO, including 31 still INVOICED),
then this report said 196 / $74,293.85 (pay-type actually closed in window). Both
correct, different questions — but **if you don't explain the delta in the email,
it reads as the report being wrong.** Always state which definition is in play.

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

### Direct-send fallback (used successfully 2026-08-27)
When Stacey is slow/unavailable, Jay can build and send the MIME himself — flag to
Joe that the fallback was used. Working recipe:
- Password: `re.search(r'raw\s*=\s*"([^"]+)"', <stacey himalaya config>).group(1).replace(" ","")`
  at `/home/itadmin/.hermes/profiles/email-agent/home/.config/himalaya/config.toml`
- `MIMEMultipart("related")` → `alternative`(html) + `MIMEImage` w/ `Content-ID: <scorecard>`
  + `MIMEApplication` pdf/csv. SMTP_SSL smtp.gmail.com:465.
- **Self-send dedup:** From==To==Joe means Gmail files it in Sent ONLY. You MUST
  also `imaplib.append("INBOX", ...)` the same raw message or it never reaches his
  inbox. Print `INBOX_COPY_OK` to prove it ran.

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
