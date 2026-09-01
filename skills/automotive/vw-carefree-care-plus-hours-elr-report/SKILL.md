---
name: vw-carefree-care-plus-hours-elr-report
description: Build the VW CAREFREE and VW CARE/CARE PLUS hours-sold + ELR backup reports for the two AMG Volkswagen stores (Stevens Creek VW 826, VW Clovis 1891). Use when Joe asks for Carefree / Care / Care Plus hours, their effective labor rate, or backup documentation for the VW rows on the AMG WIP sheet.
triggers:
  - vw carefree report
  - vw care plus hours
  - carefree effective labor rate
  - backup for the vw numbers
  - care/care plus elr
  - scvw carefree hours
  - vw clovis carefree
  - hours we sold of carefree
---

# VW Carefree / Care+Care Plus — Hours Sold & ELR backup report

Joe reports VW **CAREFREE** and **CARE/CARE PLUS** hours on rows 6 and 7 of the two VW
tabs in the AMG WIP workbook. This skill produces the emailable backup for those numbers:
hours, labor sale, ELR, opcode breakdown, and RO-level detail.

## Stores
| Code | Store | Tekion dealer | WIP tab |
|---|---|---|---|
| SV | Stevens Creek Volkswagen | 826 | "Stevens Creek Volkswagen" |
| VC | Volkswagen of Clovis | 1891 | "Volkswagen of Clovis" |

## ⭐ Opcode sets — CENSUS THEM, don't hardcode blind
Verified live 2026-09-01 via `POST /api/service-module/u/opcode/search`
(`{"searchText":X,"pageInfo":{"start":0,"rows":500},"filters":[],"sort":[]}` → `data.hits[]`).
Script: `/home/itadmin/tekion-reports/vw_opcode_census.py <port>` (searches CF, ID4, 10K,
20K, 0103, 0104, 0139, CARE, FREE at both stores).

```python
CAREFREE = {"10KCF", "10KID4", "20KCF", "20KID4"}
CAREPLUS = {"01030020","01030040","01030060","01030080","01040010",
            "01040030","01040050","01040070","01390040","01390080",
            "01340010",            # VC only, IN_ACTIVE
            "90KVWC","100KVWC"}    # VC only, ACTIVE — NOT in Joe's saved group
```

🚨 **Two traps in this opcode list:**
1. **`01030020` is a CAREFREE opcode by description** ("PERFORM VW 20K CARE FREE
   MAINTENANCE SERVICES") but Joe's saved `CARE/CAREPLUS` group puts it in Care Plus.
   **Follow the saved group, not the description.** Don't "fix" it.
2. **`CF` alone is NOT Carefree** — it's `PERFORM COOLING SYSTEM FLUID EXCHANGE`. A
   `CF`-substring match silently pulls in cooling-system flushes.
3. VC has `90KVWC` / `100KVWC` (active Care Plus mileages) that are **absent from Joe's
   saved group** — including them changes the number. Match the sheet first, flag the gap.

## Joe's saved filter groups (VC only — SV has none)
`GET /api/sales/settings/u/v1.0.0/groupFilter/ADVISOR_PERFORMANCE_REPORT_SUMMARY/filter/preference/list`
VC 1891 has `CAREFREE` and `CARE/CAREPLUS`, both **`roClosedTime` BTW + `opcodes IN`,
with `payTypeStatus IN []` (EMPTY = no status filter)**. SV 826 has zero saved groups.

### 🚨 THE TWO STORES' WIP CELLS USE DIFFERENT FILTERS — surface this, don't silently pick one
Aug 2026 proof:

| Store | no status filter | `payTypeStatus IN [CLOSED]` | WIP sheet says |
|---|---|---|---|
| SV Carefree | 146.80 | **135.90** | 135.90 ← Closed basis |
| VC Carefree | **96.03** | 87.43 | 96.03 ← no-status basis |
| SV Care/Plus | **58.98** | 53.70 | (blank) |
| VC Care/Plus | **46.82** | 43.42 | 46.82 ← no-status basis |

So SV was pulled with a Closed filter and VC without one. They are **not comparable**.
Recommend Joe standardise; until he rules, report both and reconcile.

## ⭐ RO GRAIN vs LINE GRAIN — get this right or the number looks wrong
`advisor-performance/summary` with `opcodes IN [...]` returns **every hour on every RO that
contains one of those opcodes**, including unrelated lines on the same ticket. That is the
WIP sheet's basis. The program's own operation lines are much smaller:

| Aug 2026 | RO-basis hrs | Carefree LINE hrs |
|---|---|---|
| SV Carefree | 146.80 | 76.31 |
| VC Carefree | 96.03 | 58.14 |

**Report BOTH.** The RO basis ties to the sheet; the line basis is what a manager means by
"how many Carefree services did we do." Labeling one as the other invites a rejection.

## Build steps
1. **Scan** (live OpenAPI, zero Report Builder index lag, ~4 min for both stores):
   ```bash
   cd /home/itadmin/tekion-reports
   /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 \
       vw_care_scan2.py 2026-08-01 2026-08-31
   # → /home/itadmin/amg-wip/vw-care-full-<start>_<end>.json
   ```
   Method: `repair-orders:search` bisected on `closedTime` (pageNumber is ignored) →
   prefilter ROs on free `OPCODE` tags → fan out jobs → operations, capturing **ALL** ops
   on each candidate RO so both grains are derivable from one pass.
   **Run with `background=true, notify_on_complete=true`** — exceeds the 180s foreground cap.
2. **Render.** 🚨 **Joe wants ONE REPORT PER STORE PER PROGRAM = 4 reports**, not two
   combined two-store reports (he asked for this explicitly 2026-09-01: *"I need 2 separate
   reports by store. I should have 4 reports total"*). **Default to the per-store renderer.**
   ```bash
   # ✅ CANONICAL — 4 standalone reports
   /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 \
       render_vw_care_bystore.py 2026-08-01 2026-08-31 > /tmp/vwbs.json
   # → VW-Carefree-SCVW-<Mon><Yr>   VW-Carefree-Clovis-<Mon><Yr>
   #   VW-CarePlus-SCVW-<Mon><Yr>   VW-CarePlus-Clovis-<Mon><Yr>   (.pdf/.png/.html)
   # writes a JSON summary array to stdout — mail_vw_care_bystore.py reads /tmp/vwbs.json
   ```
   Each report: page 1 = 4 KPIs (hours / ELR / labor sale / ROs), hours-and-ELR basis
   table (RO basis, program lines only, other work), opcode breakdown, pay-type split,
   WIP reconciliation + explanatory note. Page 2 = every RO counted.
   `render_vw_care2.py` (two combined reports) is kept only for a fleet-rollup ask —
   per Joe's standing preference, output stays **separate per store**, rollup is an extra.
3. **Email — one email per report** (4 emails):
   ```bash
   /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 mail_vw_care_bystore.py
   ```
   Subject: `VW <PROGRAM> — <Store> — Hours Sold & ELR, <Month Year>`. Uses
   `jay_mail.send_report()` (real SMTP, CID inline PNG, PDF attached). The per-store
   reconciliation sentence is hardcoded in `WIPNOTE` keyed `(prog, store)` — **update it
   when the month changes**, it references Aug-2026 hour values.
   Then verify all 4 in `[Gmail]/All Mail` via `X-GM-RAW rfc822msgid:<bare-id>`:
   labels must include Inbox, `Received` count ≥ 1, an `image/png` part with
   `Content-ID: <scorecard>`, a PDF attachment, and `data:image` absent.
3. **Gate against the WIP sheet** before sending — the reconciliation table on page 1 must
   show the sheet value and the diff. A non-zero diff needs an explanation in the report,
   not a silent adjustment.
4. `vision_analyze` the PNG before delivering (branding + layout check). Vision misreads
   the word CAREFREE as "CARFINDER" — ignore that, verify the numbers against the JSON.

## Branding
No VW logo asset exists (SCT is the only store with a logo file; dealer sites Cloudflare-403).
Use the **text wordmark** "AMERICAN MOTORS GROUP" with VW dark blue `#001E50`. Inject via
`CSS.replace("__ACCENT__", ACCENT)` — never `%`-format (the CSS contains `width:100%`).

## Aug 2026 results (reference)
| Program | Store | ROs | Hours (RO basis) | Labor Sale | ELR |
|---|---|---|---|---|---|
| CAREFREE | SCVW | 96 | 146.80 | $53,503.01 | $364.46 |
| CAREFREE | VW Clovis | 59 | 96.03 | $21,891.15 | $227.96 |
| CAREFREE | **Total** | 155 | **242.83** | $75,394.16 | **$310.48** |
| CARE/CARE PLUS | SCVW | 39 | 58.98 | $13,019.17 | $220.74 |
| CARE/CARE PLUS | VW Clovis | 30 | 46.82 | $6,013.61 | $128.44 |
| CARE/CARE PLUS | **Total** | 69 | **105.80** | $19,032.78 | **$179.89** |

Both programs are **~100% WARRANTY pay** (Carefree: 154 of 156 ops; the handful of CP lines
are Care Plus). Expect a warranty-rate ELR, not a customer-pay one. The SV-vs-VC ELR gap
($364 vs $228 Carefree) is a real rate difference between the two stores — worth flagging
to Joe, it is not a data error.

## Pitfalls
- Money from OpenAPI operations is **CENTS** (`saleAmount`/100); `billDuration` is
  **SECONDS** (/3600), but `labor.billableHours` is already hours — prefer it when present.
- `payTypeFirstClosedTime` and `roClosedTime` return **identical** results at both VW stores
  for these buckets — the basis question is status-filter, not date-field.
- Don't use Report Builder for the current or just-ended month; its ES index lags ~4 days.
- **Ternary-inside-`f`-string trap** (bit me building the per-store reconciliation row): a
  `h.append(f"...{x}" if cond else f"...")` spanning several implicitly-concatenated lines
  binds the `if/else` to the *whole* concatenation, silently producing a malformed `<td>`.
  Compute the cell text into a variable first, then interpolate once.
- **Verify tables by parsing the generated HTML, not by `vision_analyze`.** Vision
  hallucinated an entirely fictional 3-column reconciliation table (invented a "-140.00"
  diff) on a page that was actually correct. Use vision only for branding/layout/overlap;
  regex the `.html` for the real cell values.
- When the report ties exactly to the sheet, print **"exact match"** in the Diff column, not
  `+0.00` / `-0.00` — a signed zero reads like a rounding problem.
