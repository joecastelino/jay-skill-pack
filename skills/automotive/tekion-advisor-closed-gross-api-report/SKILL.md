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

### "Now build the same for <other store>" — ONE-SHOT RUNNER (proven 2026-08-27, BC then TL)
Joe's follow-up after any store's pair of reports is *"can you build the same for
X?"* — this has now repeated three stores running (BT → BC → TL). Expect it, and
do the whole pair (Daily Closed + Closed MTD) in a **single background bash
script**, not four separate foreground calls. The fastest path is to **copy the
previous store's `_<store>_advisor_run.sh` and swap the two-letter code** — the
template is stable:
```bash
# /home/itadmin/tekion-reports/_<store>_advisor_run.sh
cd /home/itadmin/tekion-reports
python3 advisor_closed_gross.py --store bc --date 2026-08-26
python3 render_advisor_perf_style.py out/advisor_closed_gross_bc_2026-08-26.json
CALLS_PER_MIN=900 WORKERS=8 python3 advisor_closed_gross_mtd.py --store bc --from 2026-08-01 --to 2026-08-26
python3 render_advisor_perf_style.py out/advisor_closed_gross_bc_2026-08-01_2026-08-26.json
```
`bash -n` it, then `terminal(background=true, notify_on_complete=True)` with
`/usr/bin/bash` (never bare `bash` — see the background-script memory note), logging
to `data/_<store>_advisor_run.log`. The DAILY finishes in ~2 min so you can post it
to Joe immediately while the MTD keeps scanning — don't make him wait for both.

**Match the date window of the store you just did.** He wants apples-to-apples with
the previous store's pair, so reuse the same `--date` / `--from/--to`.

**Store volume reference (Aug 2026 MTD, 1st–26th):** SCT ≈ 3,750 ROs / ~90 min ·
**TL ≈ 3,270 ROs (index pass 153s / 293 calls) — TL is a HIGH-volume store, on par
with SCT, roughly 2x BC** · BC ≈ 1,529 ROs / ~25–30 min (14,416 calls, 37 429s) ·
BT ≈ same order as BC. Daily single-day counts: TL ≈ 169 ROs / $45.2K, SCT ≈ 134,
BC = 68. Use these to give an ETA instead of guessing. BC ran essentially clean at
900/8 — that rate is comfortable for a mid-volume store.

**Don't quote the scanner's own printed ETA to the user.** `advisor_closed_gross_mtd.py`
prints `[work] N to fetch (~N*5 calls, ~Xh)` from a naive worst-case divide — it
said **~3.2h** for TL's 3,270 ROs while SCT's 3,750 actually finished in 91 min at
the same 900/8. Estimate from the volume table above (≈ 40–45 ROs/min observed),
not from that line, or you'll scare Joe off a run that's an hour.

**Cross-validation is cheap here — always do it.** The MTD JSON is
`{"meta":..., "rows":[...]}` with per-RO `closed_days`, `gross`, `ro`. Slice it on
the daily run's date and assert an exact match on count, dollars, AND the RO id set:
```python
sub = [r for r in mtd["rows"] if "2026-08-26" in r["closed_days"]]
assert {r["ro"] for r in sub} == {r["ro"] for r in daily["rows"]}
```
BC 2026-08-27: 68 ROs / $30,586.90 both ways, empty symmetric difference. Report
that reconciliation to Joe — it is what makes the MTD number credible.

**Polling pitfall:** do NOT poll the log from `execute_code` with `time.sleep()` —
that tool has a hard 300s cap and the sleep burns it (happened 2026-08-27). Just
call `terminal("tail -20 <log>")` directly; the notify_on_complete handles the rest.

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

## Delivering it by email — USE `jay_mail.py`, NOTHING ELSE
```python
import sys; sys.path.insert(0, "/home/itadmin/tekion-reports")
import jay_mail as JM
JM.send_report(subject="SCT Advisor Performance — ...",
               html=html,                       # must reference cid:scorecard
               inline_png="/path/scorecard.png",
               attachments=[pdf, csv])          # to=None => self-send to Joe
```
`/home/itadmin/tekion-reports/jay_mail.py` raises `DeliveryError` unless the
message is confirmed in the inbox. Never hand-roll smtplib/imaplib again.
Regression suite: `python3 /home/itadmin/tekion-reports/test_jay_mail.py` (14 tests,
includes a live round trip) — run it if you touch the mail path.

### Building the email body FROM the `_perf.csv` — it has TWO sections (trap, 2026-08-27)
`render_advisor_perf_style.py`'s CSV is **not** a flat table. It is the summary
table, then a **blank row**, then a `RO DETAIL` marker row, then a second header
(`RO,Advisor,PayTypes,...`) and the per-RO rows. Naively iterating `rows[1:]` to
build the HTML summary table throws `IndexError: list index out of range` on the
blank row. Stop at the section break:
```python
c = list(csv.reader(open(stem + "_perf.csv")))
hdr, body = c[0], []
for r in c[1:]:
    if len(r) < 13 or r[0] in ("RO DETAIL", "RO"): break
    body.append(r)
keep = [0, 1, 2, 3, 4, 12]   # Advisor, ROs, Bill Hrs, ELR, Hrs/RO, Total Gross
```
Six columns is the right density for an email body — the full 13 belong in the
PNG/PDF/CSV, not squeezed into HTML.

Also: `%`-format these HTML fragments, don't f-string them. Nested quotes inside
an f-string expression (`{"left" if i==0 else "right"}`) fight the surrounding
quoting and the `width:100%` literals need `%%` escaping under `%`-format.

### Independently re-verifying a `send_report` after the fact
`send_report` already prints `DELIVERED (inbox append) <message-id> labels={'inbox'}`
and raises otherwise — **capture that Message-ID**, it is the only reliable handle.

To re-open the message yourself, reuse jay_mail's own credentials rather than
re-deriving them. The module exposes `JM.JOE` and `JM._password()`; there is **no
`APP_PW` constant** and regexing the source for a hardcoded password finds nothing
(it reads Stacey's config). Check `[k for k in dir(JM) if not k.startswith('__')]`
if the API surface shifts.

**Search by Message-ID, never by subject.** These subjects contain em-dashes/en-dashes,
and `imaplib` encodes commands as ASCII → `UnicodeEncodeError: 'ascii' codec can't
encode character '\u2014'` before the command even leaves the client. The
`CHARSET UTF-8` prefix does not save you here.
```python
M.select('"[Gmail]/All Mail"', readonly=True)          # All Mail — see Trap 2
t, d = M.uid('search', None, 'X-GM-RAW', 'rfc822msgid:%s' % bare_msgid)
```

**A delivered report can still land `\Seen`.** On 2026-08-27 one of the two BC
emails came back `FLAGS (\Seen)` while its twin was unread — pre-read means Joe
scrolls past it. Clear the flag from INBOX (not All Mail):
```python
M.select('INBOX'); M.uid('store', uid, '-FLAGS', '(\\Seen)')
```

### ⚠️ The 2026-08-27 delivery incident — two traps, both now handled
**Trap 1 — self-send dedup + read flag.** From==To==Joe with the SAME Message-ID
on both the SMTP send and the IMAP append → Gmail collapses them into one message
labeled BOTH `\Inbox` and `\Sent` and marked `\Seen`. Technically in the inbox,
but pre-read and merged into the Sent conversation, so Joe never sees it.
**Fix: self-sends go IMAP-APPEND ONLY, fresh Message-ID, appended UNREAD.**

**Trap 2 — Gmail omits the SELECTED mailbox's own label from X-GM-LABELS.**
Same message, three different answers:
```
SELECT INBOX              -> X-GM-LABELS ("\\Sent")
SELECT "[Gmail]/All Mail" -> X-GM-LABELS ("\\Inbox" "\\Sent")   <-- the truth
SELECT "[Gmail]/Sent Mail"-> X-GM-LABELS ("\\Inbox")
```
Reading labels while INBOX is selected made me tell Joe a delivered message was
"Sent-only, never delivered" — **a wrong diagnosis I had to retract.**
**Fix: ALWAYS `SELECT "[Gmail]/All Mail"` before fetching labels.**

Also: `SEARCH HEADER Message-ID ...` gives FALSE NEGATIVES on Gmail — use
`SEARCH X-GM-RAW rfc822msgid:<bare-id>`. And existence ≠ delivery: finding the
message proves nothing, only the parsed label set does. Match on a SET, never a
substring (`"\\Sent"` contains neither more nor less than what you parse).

External recipients (Kevin/Tony/Sean) are unaffected — those go SMTP and verify
`\Sent`. `jay_mail` routes automatically on whether `to` is Joe.

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
- **Flag the missing logo BEFORE the run, not after.** Joe's answer on 2026-08-27
  (TL) was simply *"that is fine"* — he does not want an unbranded report withheld.
  Say it once up front in the "starting the run" message, then ship. Do NOT repeat
  the logo nag on every subsequent delivery. On disk today: `logo_st.png` and
  `logo_0.png` (which IS the SCT mark — never use it as a fallback).
- **Post the DAILY the moment it lands.** The pair is deliberately split: daily ≈
  2–4 min, MTD 30–90 min. Poll with `terminal("sleep 90; tail -25 <log>")` (a
  foreground sleep in `terminal` is fine — it's the 300s `execute_code` cap that
  bites), and as soon as the render lines appear, read
  `out/<stem>_perf.csv`, cut at the `RO DETAIL` section break, and post the top-8
  table + PNG. Then say the MTD RO count + ETA and let notify_on_complete wake you.
- **Add 2–3 outlier callouts to every delivery.** Joe reacts to the anomalies, not
  the table: an advisor with very high Hrs/RO (heavy repair lane), very low Hrs/RO
  with high RO count (express flow), or near-zero parts sale (internal/warranty
  queue). This is what turned the BC and TL deliveries into conversations.
- Logo: `render_advisor_perf_style.py` loads `logo_<store>.png` from
  `/home/itadmin/tekion-reports/` keyed off `META["store"]`, and renders **text-only
  with a stderr warning** when that file is missing. It used to hardcode `logo_0.png`
  — which is the **Stevens Creek Toyota** logo — so every BT/BC/TL/SV run was branded
  with the wrong dealership. Never reinstate a cross-store fallback. On disk today:
  `logo_st.png` only. Ask Joe for a store's logo rather than substituting one.
  **Flag the missing logo to Joe in the same message you deliver the report** (BC ran
  text-only on 2026-08-27) and offer to re-render once he sends it — don't silently
  ship an unbranded page or quietly swap in another store's mark.
- `send_report(inline_png=...)` **raises** unless the html contains `cid:scorecard` —
  always include `<img src="cid:scorecard">` in the body.
- Reuse the house visual language: white bg, red `#EB0A1E` rule + hero KPI,
  `#1a1a1a` table header, green totals, red bar scaled to leader.
