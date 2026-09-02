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

## Category mapping (opcode suffix — the whole trick)

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
   `Counter(r["date"])` instantly shows whether any days are missing (see the
   gap-quantification section below).
2. **Render:**
   ```bash
   cd /home/itadmin/tekion-reports && python3.11 render_menu_by_advisor_category.py \
     data/sct-menu-closed-mtd-MASTER-2026-08.json 2026-08 "<caveat html or ''>"
   ```
   → `data/SCT-Menu-Sales-Closed-by-Advisor-Category-<YYYY-MM>.{png,pdf}`
   The 3rd arg is optional inline HTML for the amber caveat box (use `&ndash;`
   for dashes — it's injected raw into the HTML).
3. **Verify numbers against the JSON, not against vision.** Compute totals,
   per-category, and per-advisor in Python and compare to the PNG. Vision is a
   STRUCTURAL check only (branding, title, no cut-off) — its per-row transcription
   drifts between calls on dense tables.
   - ⚠️ Vision will report the em-dash placeholders (`—`) in empty matrix cells as
     "missing data / data gaps". **That's a false alarm** — a dash means the
     advisor sold zero in that category. Don't go fix a non-bug.
   - The PNG is ~8,500px tall; crop the top ~1,100px and upscale 2x before
     `vision_analyze` (full-page 400s over the 8,000px limit on larger months).
4. **Email via Stacey** — body-file + one short send ask (see below).

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

## Quantifying an outage gap (do this before shipping any historical month)

If any day in the month is thin or missing from the master, say so with a NUMBER,
don't hand-wave. The OPCODE-tags prefilter is **free** (no fan-out, no
`/operations`) so it works even while quota-blocked:

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
This produced the exact figure that went in the caveat: **52 menu ROs lost to the
Aug 1–10 outage**, identifiable by opcode tag but unpriceable. Ship the report
with the gap disclosed + a promise to restate, rather than withholding it or
presenting a silently-low total as fact.

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

## Reference result — August 2026 (SCT)

158 menus · $48,440.04 labor / $22,731.80 parts = **$71,171.84** · 15 advisors.
Basic 72 / $19,471.27 (27.4%) · Value 63 / $35,987.96 (50.6%) · Premium 23 /
$15,712.61 (22.1%). Top: Artist Battle 27 / $16,475.58, Angel Gutierrez 17 /
$10,840.96, Jaime Sanchez 14 / $7,672.28.
Excludes 52 outage-lost menus (Aug 1–10); true total likely ~$95–100K.
