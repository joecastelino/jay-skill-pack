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

## 🤖 FLEET AUTOMATION — all 7 stores, nightly, one email per store (live 2026-08-28)
Joe asked for the whole fleet on a cron with **separate emails by store**. Wired:

🚨 **CRON `python3` = `/usr/bin/python3`, WHICH HAS NO PLAYWRIGHT (silent 3-night outage, found 2026-08-31).**
`fleet_advisor_daily.sh` called bare `python3`. Interactively that resolves to the venv
(`/home/itadmin/.hermes/hermes-agent/venv/bin/python3`) and works; under cron's PATH it
resolves to `/usr/bin/python3` → `ModuleNotFoundError: No module named 'playwright'` in
`render_advisor_perf_style.py`. Consequences, all silent:
- **scrapes and `mtd_append` all SUCCEEDED** — no data was lost, JSONs are intact
- but every render died → no `_perf.png` → `mail_advisor_daily.py` bailed
- the log read `MTD APPEND FAILED (daily still good)` which is **MISLEADING** — the append
  itself worked; the `&&`-chained render after it is what failed
- result: **0 of 7 stores emailed for close days 8/28, 8/29, 8/30** and nobody noticed until
  Joe asked for a store by hand.

FIXED: the script now pins `PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11` and
calls `$PY` everywhere. **Never use bare `python3` in any cron'd script here.** Recovery is
cheap — re-render from the existing JSON and re-mail; no re-scrape needed:
```bash
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11
$PY render_advisor_perf_style.py out/advisor_closed_gross_<s>_<date>.json
$PY mail_advisor_daily.py --store <s> --date <date>
```
**Health check worth running any time Joe asks for a store by hand** (it usually means the
cron is dead): `grep -E "EMAIL FAILED|SENT " data/_fleet_daily_$(date -d yesterday +%F).log`.

`/home/itadmin/tekion-reports/fleet_advisor_daily.sh` — cron **3:30 AM daily** (Joe is up
by 4). For each of `st bt bc tl sv vc ar`, in order: scrape yesterday → render →
`mtd_append.py` onto the running MTD → `mail_advisor_daily.py`. ~15 min end to end.
- **SEQUENTIAL with 60s cooldowns.** Never parallelize — it drains the app-wide
  OVERALL_QUOTA bucket and breaks every other Tekion consumer for hours.
- **`flock -n` on `/tmp/advisor-fleet-daily.lock`** so a long run can't overlap the next.
- Slot chosen to miss the 2 AM VI pull and the 11 PM dealer-detail sync.
- Per-store failures are isolated (`continue`), and an MTD-append failure still ships the
  daily. Takes an optional date arg for a manual backfill: `fleet_advisor_daily.sh 2026-08-27`.

`mail_advisor_daily.py --store <s> --date <d>` builds the per-store email: 6-column summary
(Advisor/ROs/Bill Hrs/ELR/Hrs/RO/Total Gross), the T-3 index-lag explainer (⚠️ **now stale —
Tekion fixed the lag 2026-08-31, see the section above; this block should be dropped or
reworded to "batch index, check Last Generated On" on the next edit**), auto-generated
**outlier callouts** (heavy-repair lane = Hrs/RO ≥2.5; internal/warranty queue = ≥8 ROs with
<$250 parts; whale = ≥22% of store gross), CID inline PNG + PDF + CSV. `--dry-run` to preview,
`--native "N ROs / $X"` to add a head-to-head line.

**Fleet baseline, closed 8/27/2026** (use for sanity-checking future runs):
SCT 225/$49,554.21 · BT 161/$62,284.54 · TOL 162/$32,027.01 · BC 91/$29,981.94 ·
SV 32/$28,830.33 · VC 31/$12,383.44 · AR 4/$6,427.84. **Fleet 706 ROs / $221,489.31.**
Note SV/VC/AR are LOW RO count but high $/RO (SV = $901/RO) — that's normal for those
stores, not a scrape failure.

**ALL 7 STORES now on a matching Aug 1–27 MTD** (backfilled 2026-08-28, one-time
`_mtd_backfill_aug.sh`, sequential smallest-first w/ 5-min cooldowns, zero failures):
SCT 3,975/$946,833.61 · TL 3,427/$686,274.10 · BT 3,141/$748,912.38 · BC 1,620/$632,576.09 ·
VC 549/$187,101.70 · SV 513/$229,875.45 · AR 83/$115,539.47. **Fleet 13,308 ROs /
$3,547,112.80.** From here the nightly cron keeps them current incrementally — this was
the last full scrape.
Aug 1–26 bases for reference: BT 2,980/$686,627.84 · BC 1,529/$602,594.15 ·
TL 3,265/$654,247.09 · SV 481/$201,045.12 · VC 518/$174,718.26 · AR 79/$109,111.63.

⚠️ **A 3-second "MTD OK" is not automatically a failure** — `advisor_closed_gross_mtd.py`
reuses an existing output file for the same window. BC/BT/TL "finished" in 3–5s during the
backfill because their Aug 1–26 files already existed from earlier builds. VERIFY rather
than assume either way: check the file mtime, and assert `base.ro_count + daily.ro_count ==
merged.ro_count` and the dollars sum exactly. All 7 passed that check.

## ⭐ NEVER RE-SCRAPE MTD — APPEND THE DAILY (Joe's directive 2026-08-28)
Joe asked for this explicitly to cut runtime and tokens: **`MTD(1..N) = MTD(1..N-1) + daily(N)`**.
A full MTD re-scrape is ~42,000 calls / ~90 min; a daily is ~2–4 min. Use:
```bash
cd /home/itadmin/tekion-reports
python3 advisor_closed_gross.py --store st --date 2026-08-27          # ~3 min
python3 mtd_append.py --base out/advisor_closed_gross_st_2026-08-01_2026-08-26.json \
                      --add  out/advisor_closed_gross_st_2026-08-27.json
python3 render_advisor_perf_style.py out/advisor_closed_gross_st_2026-08-01_2026-08-27.json
```
`mtd_append.py` merges keyed on RO number, **daily row WINS on collision** (a partially-
closed RO seen again later has more invoices closed = more complete). It writes
`meta.assembled="incremental"` + `assembled_from[]` for provenance, and hard-**exits on a
gap** in the date window (run the missing day first) or a store mismatch. `--dry-run`
previews. Verified 2026-08-28: 3,750 ROs/$897,279.40 + 225/$49,554.21 → 3,975/$946,833.61,
exact to the penny, zero duplicate ROs.

**When you still MUST do a full re-scrape:** (a) first build of a month, (b) a gap in the
daily chain, (c) restating days <T-3 where late invoices may still be landing. For (c)
just re-run those individual days and `--add` them — the merge restates them in place
(it prints `N restated`).

## ✅ NATIVE ADVISOR PERFORMANCE INDEX LAG — FIXED BY TEKION (re-verified 2026-08-31)
**The old "never trust Advisor Performance newer than T-3" rule is RETIRED.** Do not repeat
it to Joe or the stores.

History: measured SCT 2026-08-28, the native report was a batch index that backfilled over
~3 days — 8/27 at T-1 showed **55 of 225 ROs (24%, $36,905 missing)**, 8/26 at T-2 = 76%,
T-3 and older = 100% penny-exact.

Re-tested after the 8/29–8/30 weekend and the lag is **gone**. SCT 876, native vs this API
report, close-day by close-day:

| Close day | Age | API ROs | Native | % found | $ delta |
|---|---|---|---|---|---|
| 8/24 | 7d | 258 | 259 | 100% | +$573 |
| 8/25 | 6d | 270 | 269 | 100% | +$403 |
| 8/26 | 5d | 135 | 136 | 101% | +$121 |
| 8/27 | 4d | 225 | 225 | 100% | −$162 |
| 8/28 | 3d | 239 | 239 | 100% | −$253 |
| 8/29 | 2d | 26 | 26 | 100% | $0 |
| **8/30** | **1d** | **46** | **46** | **100%** | **+$47** |

**What changed:** the report header's "Last Generated On" is now **~11:30 PM PT** (was
~3:30 AM). The batch index regenerates late-night and catches the full prior day.

**No Tekion defect ticket is warranted.** The 3 SCT residual ROs that were still missing at
T-2 on 8/28 — **577056 / 580281 / 581233** (closed 8/26, $1,598.82) — all backfilled on
their own and now return present. A ticket was drafted and correctly killed.

**Cross-store check:** BT (1249) confirms it isn't SCT-only — native now runs at or above
the API report on 8/29–8/30, not undercounting.

Still true, and still why this report exists:
- It is a **BATCH index, not live** — read "Last Generated On" in the header before quoting
  a same-day figure.
- The API report remains the **tie-breaker for any advisor pay dispute**, because it is
  immune to all three original failure modes (INVOICED-vs-CLOSED status filter, CVSC hidden
  under Pay Type View, index lag).
- Residual ±1 RO / small-dollar deltas are **definitional, not errors**: an RO whose pay
  types straddle midnight lands on both days in this report (see the RO 392344 case below).

⚠️ Comparison trap hit during this re-test: don't diff native against a **stale incremental**
API file. BT's on-disk MTD was an old append chain and made native look inflated; pull fresh
store numbers for the days being compared before drawing any conclusion.

Full aging-curve history + the XHR-replay repro method lives in
`tekion-gross-not-posting-to-advisor`.

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
with SCT, roughly 2x BC** · **BT = 2,980 ROs / 76 min (35,971 calls, 184 429s) — BT
is ALSO high-volume; an earlier version of this skill guessed "BT ≈ same order as
BC" and that was WRONG by 2x, don't guess a store's volume** · BC ≈ 1,529 ROs /
~25–30 min (14,416 calls, 37 429s). Daily single-day counts (8/26): **BT = 200 ROs /
$43,554.65**, TL ≈ 169 / $45.2K, SCT = 134 / $45,668.52, BC = 68 / $30,586.90.
Use these to give an ETA instead of guessing. BC ran essentially clean at
900/8 — that rate is comfortable for a mid-volume store.

**High-volume stores hit MULTIPLE long backoffs.** BT froze at exactly 1000 rows
for ~8 min, then again around 2300 and 2950 (429 counter stepping 64→104→144→184 in
+40 bursts). Every one resolved itself. The `/proc/<pid>/wchan == futex_do_wait`
check below is the only thing you need before deciding to wait rather than kill.

**Cheap cross-store sanity check on the MTD total:** BT 2,980 ROs / $686,627.84
(labor $542,746.55 + parts $143,881.29), 1,662.52 bill hrs, ELR $134.82, 1.56 hrs/RO,
parts GP 38.16%. An ELR far outside ~$130–140 or hrs/RO outside ~1.4–1.7 on a Toyota
store means check the run, not the store.

**BC (1251) MTD baseline, Aug 1–26 2026:** 1,529 ROs / **$602,594.15** total gross
(labor sale $510,787 / parts sale $391,955), 11 advisors, leader Michael Reyes
164 ROs / $77,938.52. GM store ELRs run HIGHER than Toyota — BC advisors sit
$166–$254 (fleet-normal there), so do NOT apply the Toyota $130–140 ELR sanity
band to BC/Cadillac. Same-day 8/26 daily = 68 ROs / $30,586.90, reproduced exactly
by the MTD slice (empty symmetric RO-set difference).

**TL (1092) MTD baseline, Aug 1–26 2026:** 3,265 ROs / **$654,247.09** total gross
(labor $470,759 / parts $183,488), 22 advisors, leader Sean Preston 199 ROs /
$89,323.85 (2.65 Hrs/RO — he's the *service manager*, heavy-repair lane, worth asking
Joe whether he belongs in the advisor ranking). Run cost: **52,432 calls, 240 429s,
106 min** at 900/8 — longer than the 40–45 ROs/min rule of thumb because the 429
backoffs ate ~20 min of wall clock. On a high-volume store quote **~70–110 min**, not
the low end. Same-day 8/26 daily = 169 ROs / $45,161.18. TL ELRs $152–$215 (Toyota
store but higher than SCT/BT — don't apply the $130–140 band store-blind).

**Outliers that made the BC delivery land well** (pattern to reuse): the advisor
with ~3.2 Hrs/RO on low RO count = heavy-repair lane; the advisor with ~$254 ELR
and near-zero parts sale ($25 across 78 ROs) = dedicated internal/warranty queue.
Call these out and ask whether they're intentional.

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

**⚠️ An exact match is NOT guaranteed, and a mismatch is usually CORRECT.** The two
runs legitimately differ by exactly the ROs whose pay-type invoices closed across
**two business dates**. TL 2026-08-28: daily 8/26 = 169 ROs / $45,161.18 vs the MTD
slice = 170 / $58,183.50. The single delta was **RO 392344** (Mauricio Orellana,
$13,022.32) with invoices closing on both 8/26 *and* 8/27 — the same-day run
correctly excludes it, the MTD correctly includes it, and **all 169 shared ROs
matched to the penny**. So don't `assert` blindly: diff the RO sets, pull the
offending RO's `closed_days`, and if it spans dates outside the daily window, name
the RO and call it the known partial-close behavior rather than a bug. One
big-ticket RO can move a single day's total 25%+ — always explain the delta in the
delivery or it reads as the report being wrong.

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
5. **Ignore vision's "the date 2026 is in the future / invalid" complaint.** It fires
   on every one of these renders because the model's own sense of "now" predates the
   real system date. Confirm with `date` and move on — it is never a render bug.
6. **Vision IS the right tool for branding.** It correctly caught that a BT report
   was wearing the Stevens Creek logo (2026-08-27). Trust it on "is this the wrong
   dealership's mark / wrong store name", distrust it on geometry and digits.

## Delivering it by email — USE `jay_mail.py`, NOTHING ELSE

### 📧 MTD MAILER (built 2026-08-28)
`mail_advisor_mtd.py --store <st|bt|bc|tl|sv|vc|ar> --start YYYY-MM-DD --end YYYY-MM-DD [--dry-run]`
Reuses `mail_advisor_daily.py`'s CODE/OUT/money/summary_rows. Reads
`out/advisor_closed_gross_<store>_<start>_<end>{,_perf}.{json,png,pdf,csv}`.
Subject: `<STORE> Advisor Performance — Closed MTD (Aug 1–27, 2026)`.
No index-lag callout block (MTD is mostly >T-3, so the warning is noise).
PITFALL: the biggest store (SCT, ~4k ROs) can throw
`smtplib.SMTPServerDisconnected: Connection unexpectedly closed` mid-send on the
attachment push — just re-run that one store; it is not a data problem.
PITFALL: Gmail re-marks self-addressed mail `\Seen` seconds after delivery —
re-clear with `M.uid('store', u, '-FLAGS', '(\\Seen)')` AFTER the final verify pass,
and re-check, because one clear can get re-stamped.
PITFALL: `X-GM-RAW subject:(...)` multi-term searches return `BAD Could not parse
command` from imaplib — verify per Message-ID with `rfc822msgid:<bare-id>` instead.

**Delivered 2026-08-28, all 7 Aug 1–27 MTD packs** (advisor counts, useful as a
roster sanity check): SCT 3,975/$946,833.61/19 adv · BT 3,141/$748,912.38/23 ·
TOL 3,427/$686,274.10/22 · BC 1,620/$632,576.09/13 · SV 513/$229,875.45/9 ·
VC 549/$187,101.70/4 · AR 83/$115,539.47/2. Joe's ask arrived as *"I need the 7
month to date emails, you sent me the Dailey"* — i.e. once the dailies ship, the
MTD pack is the expected follow-up. Send both, or say explicitly which you sent.

🚨 2026-08-28: IMAP APPEND IS NOT DELIVERY — always SMTP, even to Joe
Joe: *"I don't see them in my email"* about 7 reports that IMAP had confirmed were in
INBOX with the `\Inbox` label. **They were appended, never delivered.** An APPENDed
message is placed directly into the mailbox and never traverses Gmail's delivery
pipeline, so it has:
- **NO `Received:` header** ← the definitive tell
- no notification, no push, no filter processing
- sometimes `\Answered \Seen` already set

It is *in the mailbox* and *invisible to the human*. `jay_mail.send_report` now sends
**everything via SMTP** (self-sends included) and asserts a `Received` header via
`_has_received()` before claiming success. The old "self-sends go append-only to dodge
Gmail's same-Message-ID dedup" rule is **REVERSED** — SMTP self-send verified clean:
labels `("\Inbox" "\Sent")`, `FLAGS ()`, exactly 1 Received header.

**Verification checklist — a label alone proves nothing:**
```python
inbox    = bool(uid_search('X-GM-RAW', 'rfc822msgid:%s' % bare))   # in INBOX
unread   = b'\\Seen' not in flags                                   # will surface as new
received = count of headers starting 'received:' >= 1               # ACTUALLY DELIVERED
```
All three, or it wasn't delivered. Report the count honestly (`5/7 delivered`), never
"verified" off the label.

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
🚨 **SUPERSEDED 2026-08-28** — append-only was the WRONG fix; it made the mail
invisible to Joe. Correct fix = SMTP with a **fresh Message-ID** (that alone defeats
the dedup collapse) + clear any `\Seen` afterward.

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
**UPDATED 2026-08-28 — this report IS now on a cron.** `fleet_advisor_daily.sh` runs
3:30 AM daily for all 7 stores (see the FLEET AUTOMATION section). Joe's earlier "I
dont want it on a cron job" applied to the one-off SCT build only; he later escalated
to the whole fleet on a schedule. MTD emails remain **manual/on-demand** —
`mail_advisor_mtd.py` is not in the cron.

## ⚠️ ARCHITECTURE DEBT — it re-scrapes the whole window every run (Walter II asked, 2026-08-28)
`advisor_closed_gross_mtd.py` is **stateless**: it hits the OpenAPI live for the
full window on every invocation. TL Aug 1–26 = 3,265 ROs → 52,432 calls → 106 min.
The only persistence is the crash-resume checkpoint `out/.ckpt_*.json` plus the
output JSON/PNG/PDF/CSV. Nothing carries between runs, so tomorrow's MTD re-pulls
Aug 1 again from scratch. If asked "is this in a DB", the honest answer is no —
**but the right DB already exists and is unwired:**

- `dealer-detail` (Postgres/Supabase + Prisma) has **`RawRepairOrder`** — full RO
  payload incl. nested jobs/operations/parts, natural key `[storeId, documentId]`,
  content-hashed for idempotent upsert.
- **`SyncRun.cursor` = a `modifiedTime` watermark**, i.e. incremental sync is
  already designed in.
- `AdvisorDailyMetrics` / `AdvisorDailyCommodity` = per-advisor per-business-date
  rollups.
- Blocker: the nightly sync cron (11 PM) still runs **SCT only**
  (`cron-sct-sync.sh`); the all-7 `sync:all` lives on the **unmerged**
  `feature/multi-store-api` branch.

Wiring these reports to that DB turns a ~106-minute scrape into a ~5-second query.
**Before merging the two data paths, resolve the close-date definition conflict:**
dealer-detail buckets on `businessDate` derived from
`modifiedTime`/`deriveCloseTime`, while this report keys on true per-invoice
`closedTime` from `/ro-invoices`. They disagree on partially-closed ROs (see the
RO 392344 case above), so totals will NOT tie until one definition is picked.

**Overlap with fixedopsreports.com ≈ 70%** — same Tekion `repair-orders:search`
fan-out, same RO population, same advisor dimension. What each side uniquely has:

| | dealer-detail DB | this report |
|---|---|---|
| Labor/parts gross by advisor by day, RO count | ✅ | ✅ |
| Menu / ALA / REC classification | ✅ | ❌ |
| Commodity (tires, alignment) | ✅ | ❌ |
| Recommendations sold $ | ✅ | ❌ |
| Bill Hrs / ELR / Hrs per RO | ❌ | ✅ |
| Labor + parts **cost** (true gross, not sale) | ❌ | ✅ |
| Parts GP % | ❌ | ✅ |
| Pay-type mix (CP/CVSC/warranty/internal) | ❌ | ✅ |

## "send them to me" — the standard closeout
After the pair lands, Joe's next message is usually **"send them to me"** (BC,
2026-08-27). That means: BOTH reports, **two separate emails** (one Daily, one MTD
— do not merge), each with the scorecard PNG inline via CID + the PDF + the CSV
attached, delivered through `JM.send_report(..., to=None)` — **SMTP, fresh
Message-ID, left UNREAD** (the older "append-only self-send" instruction elsewhere
in this file is OBSOLETE; see the IMAP-APPEND-IS-NOT-DELIVERY section — an append
has no `Received:` header and Joe cannot see it). Then verify per the delivery section: select
`[Gmail]/All Mail`, search `X-GM-RAW rfc822msgid:`, parse the label SET, walk the
MIME tree, assert `data:image` absent, and clear any `\Seen` from INBOX. Report the
verification result in one line — Joe has been burned by "verified" that wasn't.
Subjects that worked: `<STORE> Advisor Performance — Closed MM/DD/YYYY` and
`<STORE> Advisor Performance — Closed MTD (Month D–D, YYYY)`.

## Pitfalls
- f-strings can't contain backslashes in the expression part — build conditional
  HTML fragments (e.g. the logo `<img>`) with `%` formatting on a prior line.
- A full-store day scan with jobs/ops/parts fan-out runs ~3+ min → launch with
  `terminal(background=true, notify_on_complete=True)`, not the 300s code tool.
- **Flag the missing logo BEFORE the run, not after.** Joe's answer on 2026-08-27
  (TL) was simply *"that is fine"* — he does not want an unbranded report withheld.
  Say it once up front in the "starting the run" message, then ship. Do NOT repeat
  the logo nag on every subsequent delivery. On disk today: `logo_st.png` and
  `logo_0.png` (which IS the SCT mark — never use it as a fallback). Branded
  re-renders are still owed for **BC and TL** if Joe ever sends those logos.
- **Store order Joe has walked so far: SCT → BT → BC → TL.** Each time he said
  "can you do the same for <next store>". Remaining un-built: SV, AR, VC. When he
  names one, copy `_tl_advisor_run.sh`, swap the code, keep the same date window.
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
