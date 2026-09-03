---
name: sct-menu-sales-by-advisor-category-report
description: >
  Build the SCT (Stevens Creek Toyota) Menu Sales CLOSED report for a FULL
  CALENDAR MONTH, broken down BY SERVICE ADVISOR and GROUPED BY CATEGORY
  (Basic / Value / Premium). Renders an Advisor x Category matrix plus
  per-advisor RO-level detail, and emails it to Joe via Stacey. Runs entirely
  OFFLINE from the per-month master cache — zero Tekion API calls — so it works
  even during a DEALER_QUOTA outage.
triggers:
  - menu sales by advisor by category
  - closed service menus by advisor
  - menu report basic value premium
  - menu sales grouped by category
  - sct menu sales last month by advisor
  - monthly closed menu report
---

# SCT Menu Sales — Closed by Advisor & Category (monthly)

Joe's ask (2026-09-02): *"MTD report for closed service menus. By advisor, and
grouped by category, basic, value and premium. SCT last month."*

This is a **month-in-review** variant of the daily
`sct-menu-sales-closed-mtd-scorecard` pipeline. It does **not** scrape — it
renders straight from the month master that the daily 6 PM cron already built.

Interpreter: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11`
Work dir: `/home/itadmin/tekion-reports`

## ⭐ The key insight: NO API CALLS NEEDED

The daily closed cron has already accumulated the whole month into
`data/sct-menu-closed-mtd-MASTER-<YYYY-MM>.json`. A past-month report is a pure
**render off that file**. This matters enormously: on 2026-09-02 the fleet was
in a live `DEALER_QUOTA` outage (`/operations` 429) and this report still
shipped clean in ~10 tool calls. **Never re-scrape a completed month** — it
would be thousands of calls and would fail anyway during an outage.

Master schema reminder (documented in the closed-MTD skill, easy to trip on):
`{"month","records","updated","asof"}` where `records` is a **dict keyed
`"ro|opcode"`**, not a list.
```python
rows = list(json.load(open(master))["records"].values())
```
Row fields: `date` (MM/DD/YY), `ro`, `opcode`, `year`, `make`, `model`,
`mileage`, `labor_gross`, `labor_price`, `parts_gross`, `parts_price`,
`job_type`, `pay_type`, `advisor`, `total_gross`.
Note the field names differ from the emitted RB file (`ro` not `ro_number`,
`mileage` not `mileage_in`, no `ro_created`) — `render_scorecard.py` will
KeyError on a master; that's why this report has its own renderer.

## 🛑 MANDATORY GATE: reconcile the master against a tag census BEFORE sending

**Learned the hard way 2026-09-02 — Joe replied "there is something wrong, I
should have way more than that" to a report I had already emailed and declared
verified.** Every number in it was internally consistent and matched the JSON.
The master itself was incomplete, and nothing in the render/verify path can see
that. **"Matches the JSON" only proves the renderer works, NOT that the data is
complete.** Run this gate before the email step, every time.

### Gate 1 — prior-month baseline sanity check (one call, do it first)

```python
import json, glob, collections, os
for f in sorted(glob.glob("/home/itadmin/tekion-reports/data/sct-menu-closed-mtd-MASTER-*.json")):
    rows = list(json.load(open(f))["records"].values())
    suf  = collections.Counter(r["opcode"][-3:] for r in rows)
    g    = sum(r["labor_gross"] + r["parts_gross"] for r in rows)
    print(os.path.basename(f), len(rows), dict(suf), f"${g:,.2f}")
```
SCT reference band: **June 243 / $99,639 · July 237 / $105,123**. A month landing
materially below ~230 menus / ~$100K is a **scan-completeness failure until
proven otherwise** — never a slow month. Aug showed 158 / $71,172 and I shipped
it anyway. Don't.

### Gate 2 — full-month tag census vs the master (free, works during a quota outage)

The OPCODE tags on `repair-orders:search` results cost zero fan-out, so this runs
even while `/operations` is 429. Census the WHOLE month, not just the known
outage window:

```python
import sys, json, time, collections; sys.path.insert(0, "/home/itadmin/tekion-reports")
import sct_menu_sales_api as O, sct_menu_sales_closed_mtd as C
from datetime import date, datetime, timedelta
frozen = {d["opcode"] for d in json.loads(O.OPCODE_LIST.read_text())}
cap    = {r["ro"] for r in rows}                       # ROs in the master
seen, census = set(), collections.Counter()
for day in range(1, 32):
    d0  = date(2026, 8, day)
    ms0 = int(datetime.combine(d0, datetime.min.time()).timestamp()*1000)
    ms1 = int((datetime.combine(d0, datetime.min.time())+timedelta(days=1)).timestamp()*1000)
    for r in C.search_closed(ms0, ms1):
        tags = {t.get("value") for t in (r.get("tags") or []) if t.get("field") == "OPCODE"}
        for t in tags: census[t] += 1
        if tags & frozen: seen.add(str(r["documentNumber"]))
    time.sleep(0.5)
print("tagged menu ROs:", len(seen), "| in master:", len(cap), "| MISSING:", len(seen - cap))
```
Aug 2026 result: **226 tagged vs 158 captured = 68 missing**, not the 52 I had
attributed to the outage. Bucket the gap by close-day — that's what exposed the
second bug.

### Bug A — the daily cron silently drops late-closing / reopened ROs

Of the 68, **52 were the Aug 1–10 quota outage** but **16 were on days that
scanned "successfully"** (8/15, 8/18, 8/19, 8/24, 8/27, 8/31 — note month-end is
the worst). Cause: the incremental cron scans `closedTime` for TODAY at 6 PM, so
anything that closes after the run, or gets **reopened and re-closed later**
(see skill `tekion-reopen-closed-ro` and the BC warranty T+3 restatement
finding), is never re-swept. This shaves EVERY month, not just outage months.
Until the cron does a rolling T+3 re-sweep, always run Gate 2 on a historical
month and disclose or backfill the delta.

### Bug B — `OPCODE_LIST` (the frozen 316) is STALE; ToyotaCare is invisible

The frozen list is **79 intervals × 4 suffixes (BNM/BSM/PSM/VNM) = 316**, all
`TEK<mileage><TIER>`, and it **predates the June 2026 ToyotaCare migration**
recorded in memory (SCT mileage codes collapsed; work moved to `TEK09*`).
August census:

| Family | ROs |
|---|---|
| Frozen-list interval menus | 226 |
| **`TEK09*` ToyotaCare** | **1,037** |
| Other TEK* | 31 |

**Zero overlap** between the two sets — so the scorecard has never counted any
ToyotaCare volume. `TEK09*` are typed `INDIVIDUAL_SERVICE` (not `SERVICE_MENU`)
and have **no Basic/Value/Premium tier** — the trailing digits are oil/vehicle
variants (`-SYN -CON -EV -MIR -BEV -GRC -86 -YAR -SUP -GRC`), e.g.
`TEK09040104 = 15K Mile ToyotaCare Service-MIR`. Enumerate them from
`data/sct-tek-opcodes-all.json` (1,371 opcodes; filter `opcode.startswith("TEK09")
and status=="ACTIVE"` → 40).

**RESOLVED — Joe ruled 2026-09-03: "No, I don't want toyota care menus."**
TEK09\* ToyotaCare is permanently EXCLUDED from SCT menu-sales reports. The
frozen 316-opcode interval list is the ONLY menu filter. Never widen it to
TEK09 to "explain" a low count — a low count means the master under-captured
(Bug A), not a definition problem. This matches his TXM/TSC/TAC prepaid
exclusion on fixedopsreports.

Also verified: **`BSM` has 79 opcodes and ZERO sales** in June/July/Aug. Only 3
tiers ever sell. A 3-category report is correct — not a missing-tier bug — but
it's worth telling Joe a quarter of his menu setup is dormant.

### What to do when the gate fails

Disclose with **numbers**, not adjectives; give the corrected estimate
(68 × ~$450 avg ≈ $30.6K → ~$101.8K true, which lands right in the June/July
band); tell Joe to disregard any already-sent copy; and state plainly that it's
a scan bug, not a soft month. He accepts "I don't know yet" but not a confident
wrong total.

## Full-month REBUILD when the master is incomplete (zero OpenAPI quota — proven 2026-09-03)

When Gate 2 shows the master is short and DEALER_QUOTA blocks `/operations`,
rebuild the whole month from the INTERNAL browser-session APIs instead (they
cost zero OpenAPI quota). This is how the corrected Aug 2026 report shipped.

1. **Pin the dealer FIRST.** The :9223 session drifts (it sat on BC/1251
   mid-scan and every call silently 500'd/failed). Verify
   `currentActiveDealerId == 876` and re-switch via the UI pill before and
   during long scans.
2. **Census** all closed ROs day-by-day via `C.search_closed` (free), keep the
   ROs whose OPCODE tags intersect the frozen list, cache the RO-number→objectId
   map.
3. **Fan out ONLY the menu ROs** via internal `GET /api/service-module/u/ro/<objectId>`
   and read per-operation `laborDetails`/`partsDetails` sale amounts for the
   menu opcodes. **Pace the calls** (sleep in-loop) — rapid fire → 500s; add a
   final retry sweep so nothing is silently dropped. 226 ROs = a few minutes.
4. **Advisor:** the RO payload's advisor lives in `allAdvisorIds` (RO number is
   `roNo`). Resolve via `sct-advisor-cache.json` + OpenAPI `/users/{id}`
   fallback. 2026-09-03: cached UUID labeled "Any Service Advisor" was actually
   **Jose Barragan** (25 Aug ROs) — cache corrected; SCT has NO genuine
   unassigned bucket.

### ⚠️ TRAP 1 — advisor-performance API returns WHOLE-RO dollars
The tempting shortcut (advisor-perf `summary()` with an `opcodes` filter —
note the field is `opcodes` plural) filters ROs *by* opcode but returns
**whole-ticket** `totalLaborSaleAmount`/`totalPartsSaleAmount` — ~2x inflation
(RO 578802: $401.76 reported vs $274.26 true menu line). Counts from it are
fine; dollars are NOT. Always pull operation-level detail for dollars.

### ⚠️ TRAP 2 — operation `totalSaleAmount` includes tax
Per-operation residual `totalSaleAmount − (laborSale + partsSale)` = **sales
tax minus coupons/discounts** (can be negative on discounted ROs). Report
**pre-tax sales = laborSale + partsSale**. (Aug: $150,000.83 raw vs
$145,522.03 pre-tax — the $4,479 delta is tax net of coupons, NOT shop
supplies.)

### ⚠️ TRAP 3 — no cost at operation level
The internal RO endpoint exposes sale amounts only. This path yields **SALES,
not gross** — label the report "Sales" and say so; the old $71K report was
gross mislabeled against sales expectations.

## Category mapping (opcode suffix — the whole trick)

Every SCT menu opcode is `TEK<mileage><SUFFIX>`.
Every SCT menu opcode is `TEK<mileage><SUFFIX>`. The last 3 chars are the tier:

| Suffix | Joe's label here | Also called |
|---|---|---|
| `BNM` | **Basic** | Basic |
| `VNM` | **Value** | "Basic+" in the quotes portal |
| `PSM` | **Premium** | "Signature" in the quotes portal |

⚠️ **The tier names are NOT stable across contexts.** The quotes portal /
service-menu-setups call these Basic / Basic+ / Signature (see memory + skill
`tekion-quotes-menu-price-diagnosis`), but Joe asked for "basic, value and
premium" on the report. **Use whatever names the requester used**, and always
print the raw suffix next to the label (`Basic · *BNM`) so there's no ambiguity
about what was counted. Do not silently rename tiers between reports.

A 4th bucket `Other` exists in the code for safety; on a healthy month it should
be **empty**. Verify with a suffix census before trusting the render:
```python
collections.Counter(r["opcode"][-3:] for r in rows)   # expect only BNM/VNM/PSM
```
(Aug 2026: 72 BNM / 63 VNM / 23 PSM = 158.)

## Steps

1. **Census the master** — row count, suffix split, per-day spread. A day-by-day
   `Counter(r["date"])` instantly shows whether any days are missing.
2. **RUN THE MANDATORY COMPLETENESS GATE** (Gate 1 + Gate 2 above). Do not skip
   to rendering because the master "looks fine" — it looked fine in Aug 2026 and
   was 30% short. Resolve or disclose the delta before step 3.
3. **Render:**
   ```bash
   cd /home/itadmin/tekion-reports && python3.11 render_menu_by_advisor_category.py \
     data/sct-menu-closed-mtd-MASTER-2026-08.json 2026-08 "<caveat html or ''>"
   ```
   → `data/SCT-Menu-Sales-Closed-by-Advisor-Category-<YYYY-MM>.{png,pdf}`
   The 3rd arg is optional inline HTML for the amber caveat box (use `&ndash;`
   for dashes — it's injected raw into the HTML).
4. **Verify numbers against the JSON, not against vision.** Compute totals,
   per-category, and per-advisor in Python and compare to the PNG. Vision is a
   STRUCTURAL check only (branding, title, no cut-off) — its per-row transcription
   drifts between calls on dense tables.
   - ⚠️ Vision will report the em-dash placeholders (`—`) in empty matrix cells as
     "missing data / data gaps". **That's a false alarm** — a dash means the
     advisor sold zero in that category. Don't go fix a non-bug.
   - The PNG is ~8,500px tall; crop the top ~1,100px and upscale 2x before
     `vision_analyze` (full-page 400s over the 8,000px limit on larger months).
5. **Email via Stacey** — body-file + one short send ask (see below). Only after
   the completeness gate passes or its delta is disclosed in the body.

## Report layout (what Joe signed off on)

Follows his established "by advisor" convention from
`tekion-parts-sales-by-advisor-report`: **ranked summary AND full RO-level
detail**, never summary-only.

1. Header — `logo_st.png` (SCT), red rule, title + `ROs closed <first> – <last>`.
2. KPI row 1 — Total Menu Gross (labor/parts split) + Menus Closed (advisor
   count, avg/menu).
3. KPI row 2 — one card per category: gross, menu count, **% of total gross**,
   avg/menu. The % share is the number Joe actually reads for mix.
4. Optional amber caveat box.
5. **Advisor × Category matrix** — one row per advisor, a `count + $` cell per
   category, then Menus / Total Gross. Sorted by total gross desc. Black
   STORE TOTAL row at the bottom (its column sums are the cheapest visual
   cross-check against the KPI cards).
6. **Detail by Advisor** — each advisor a `page-break-inside:avoid` section with
   a category subheader row (color-coded left border) then its ROs.

Logo: **`logo_st.png`**, never `logo_0.png` — both are SCT but `logo_0`'s neutral
name gets copy-pasted into other stores' renderers and stamps SCT branding on
them. For a non-SCT port of this report, use a text wordmark via `_brand()` in
`render_tech_perf.py`.

## Quantifying an outage gap (superseded — use the MANDATORY GATE above)

⚠️ This section originally scanned only the known outage window (Aug 1–11) and
produced "52 missing", which I put in the caveat and emailed. **That was wrong —
the real figure was 68.** Scanning only the days you already suspect will always
under-report, because it structurally cannot find the late-close/reopen drops on
"healthy" days. Always census the FULL month (Gate 2). Kept here only for the
mechanics of the free tag prefilter:

```python
import sys, json, time; sys.path.insert(0, "/home/itadmin/tekion-reports")
import sct_menu_sales_api as O, sct_menu_sales_closed_mtd as C
from datetime import date, datetime, timedelta
maint = {r["opcode"] for r in json.loads(O.OPCODE_LIST.read_text())}
master_ros = {r["ro"] for r in rows}
missing = []
for day in range(1, 12):
    d0 = date(2026, 8, day)
    ms0 = int(datetime.combine(d0, datetime.min.time()).timestamp()*1000)
    ms1 = int((datetime.combine(d0, datetime.min.time())+timedelta(days=1)).timestamp()*1000)
    for r in C.search_closed(ms0, ms1):
        if C._tek_opcodes(r, maint) and str(r.get("documentNumber")) not in master_ros:
            missing.append((str(d0), str(r["documentNumber"]), sorted(C._tek_opcodes(r, maint))))
    time.sleep(1)
```
This produced the figure that went in the caveat: **52 menu ROs** lost to the
Aug 1–10 outage — but the true total gap was **68** (Gate 2 found 16 more on
non-outage days). Ship a historical month with the gap disclosed + a promise to
restate, rather than presenting a silently-low total as fact.

Confirm the quota is genuinely still blocked with ONE deep probe
(search 200 / jobs 200 / operations 429 = dealer ceiling) before claiming
"can't backfill". **Do not launch a recovery watcher** — DEALER_QUOTA is a
30-day budget, not a rolling window (see the hard rule in
`sct-menu-sales-api-scorecard`).

## Emailing via Stacey — the flow that works first try

Best-known flow (body-file + ONE short send ask, no draft stage):

1. `write_file` the body to `data/menu_adv_cat_body_<YYYYMM>.txt` — greeting
   "Joe,", headline totals, the 3-line category block, top advisors, and the
   whole caveat paragraph. **Putting the caveat in the FILE is what keeps the
   ask short**, which is what keeps Stacey from stalling.
2. One ~7-line ask:
   ```
   timeout 150 ~/bin/ask-agent stacey "Write and run a python script
   (email.mime + smtplib, NOT himalaya part-markup) that SENDS now:
   TO jcastelino@americanmotorscorp.com
   SUBJ: SCT Menu Sales - Closed by Advisor and Category - August 2026
   BODY file: <path>.txt
   ATTACH: <full pdf path>
   Add Joe's standard HTML signature at the bottom.
   Reply: OK BYTES=<pdf size> or ERROR=<msg>"
   ```
3. Verify — `OK BYTES=` is **not** proof. Two read-only follow-ups:
   - subject-agnostic: *"List the last 5 messages in Sent, newest first:
     TS | TO | SUBJ. One line each."*
   - MIME: *"is the MIME real multipart with a Content-Disposition attachment
     filename (not literal part-markup as text)? Reply: MIME=<...> | BYTES=<...>"*
   Cross-check BYTES against `ls -la` on the PDF. 2026-09-02: `195702` matched
   exactly, `MIME=REAL-multipart`.

### ⚠️ PITFALL: `&` in an ask-agent string is rejected by the terminal tool

The first send attempt **failed before running** with:
`"Foreground command uses '&' backgrounding. Use terminal(background=true)..."`
— caused solely by the ampersand in the subject line
`SUBJ: ... by Advisor & Category`, inside double quotes. Hermes' terminal guard
scans the raw command string and doesn't respect quoting.

**Fix: never put a bare `&` in an `ask-agent` / terminal command string.** Write
`and`. (The email subject shipped as "Closed by Advisor and Category" for this
reason; the PDF title itself still uses `&` since that's HTML, not shell.)
Same caution for `<#part>` style angle brackets — reword to "part-markup".

## Files

- `render_menu_by_advisor_category.py` — the renderer (this skill's artifact).
  Args: `<master-json> <YYYY-MM> [caveat-html]`. Letter-format PDF with
  `page-break-inside:avoid` per advisor section.
- `data/sct-menu-closed-mtd-MASTER-<YYYY-MM>.json` — source, built by the daily cron.
- `data/menu_adv_cat_body_<YYYYMM>.txt` — email body.

## Porting to other stores

BC / BT / TOL all use the same `TEK<mileage><SUFFIX>` convention (verified —
it's a Tekion convention, not a Toyota one; see
`dealerdetail-api-pipeline-build`). To port: swap the master path, the address
in the footer, and replace the SCT logo with a text wordmark in brand colors.
**Do not reuse `logo_st.png` / `logo_0.png` on a non-SCT report.**

## Reference result — August 2026 (SCT) — FINAL, rebuilt 2026-09-03, sent + verified

**226 menus · $145,522.03 pre-tax SALES · 16 advisors · 395.1 billed hrs.**
Basic (BNM) 108 / $44,014.10 · Value (VNM) 87 / $71,671.07 · Premium (PSM)
31 / $29,836.86. Top: Artist Battle 33/$27,468 · Angel Gutierrez 28/$25,529 ·
Michael Robert Costa 29/$17,857 · Cristian Gonzalez 24/$13,444 · Jose Barragan
25/$11,179. Built via the full-month zero-quota rebuild above. Baselines (frozen
list, gross-basis from masters): June 243/$99.6K · July 237/$105.1K.

The originally-sent Aug figures (158 / $71,171.84) were understated (68 missing
ROs) AND gross-vs-sales mislabeled — Joe was told to disregard. ToyotaCare
TEK09\* (1,037 Aug ROs) permanently excluded per Joe's 2026-09-03 ruling.

**STILL TODO:** the daily 6 PM cron needs a rolling **T+3 re-sweep** so
late-closing/reopened ROs stop dropping out of the master (16/month even in
healthy months — same fix pattern as BC warranty).
