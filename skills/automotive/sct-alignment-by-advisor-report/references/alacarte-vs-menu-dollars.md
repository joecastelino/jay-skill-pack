# À la carte vs Service Menu — counting and dollars

Captured 2026-09-02 after a near-miss on the SCT August report.

## Joe's terminology → report columns

| Joe says | Report column | Meaning |
|---|---|---|
| "a la carte" | **Dedicated** | alignment sold as its own line/opcode |
| "service menu" / "in a menu" | **Bundled** | alignment included inside a TEK menu package |

When Joe asks for "alignments sold INCLUDING SERVICE MENUS AND A LA CARTE" he is asking
for the **existing** MTD report split, not a new deliverable and not BG.

## Which script

- **`sct_align_mtd.py` + `render_sct_align.py`** — the closed-MTD alignment-by-advisor
  report Kevin gets nightly. THIS is what Joe means by "I think you had that as a skill prior."
- Do **not** build a new renderer. Re-run/re-render the existing one.
- `sct_align_bg_scan.py` / `render_sct_align_bg.py` is the Align+BG variant — only when
  BG is explicitly requested.

## CRITICAL: menu line dollars are NOT alignment dollars

Tekion bills a service menu as **one line**. A bundled alignment therefore has **no separate
alignment price** — the amount on that line is the price of the **entire package**
(e.g. `TEK60000PSM` = $1,553.81, the customer's whole 60K service).

Consequences:

- **Never** sum dedicated $ + bundled $ into a "Total $" column. On SCT August 2026 that
  would have overstated alignment revenue by roughly **$28K**.
- True component revenue = **à la carte lines only**.
- Show menu package dollars in a **separate greyed column** labelled e.g. `not align $`,
  with an explicit warning on the sheet that the columns must not be added.
- Counts are fine to add — a bundled alignment is still one alignment sold.

Reference figures, SCT August 2026 (closed):
448 alignments / 448 ROs / 14.5 per day / 404 à la carte + 44 menu /
à la carte revenue **$55,970**, avg **$138.54** (a la carte list price $139.99).

## Never explain a count gap without a two-way set diff

If this report's number disagrees with another run (nightly vs ad-hoc, store vs store),
**do not narrate a plausible reason.** Dump both RO-number sets and diff them both ways.
It takes ~30 seconds and it names the exact ROs.

Real example: I told Joe a 448-vs-443 gap was a "scan scope difference." It was not — it
was a bug (see below). The set diff would have caught it immediately.

## Known historical bug: ALIGN00RBA opcode typo

- `sct_align_mtd.py` had the opcode transposed as `ALIGN00BRA`; correct is **`ALIGN00RBA`**.
- Fixed **2026-08-31 19:23**. The nightly had already run at **19:01**, so the emailed
  August number (**443**) came from the buggy build.
- Five ROs were skipped: **577147, 578500, 579093, 579597, 581768**.
- Correct August 2026 total is **448**. September onward is clean.
- The old 443 output file was backed up rather than overwritten.

Lesson: after patching a scanner, check whether that period's report already went out on
the pre-patch build, and re-render if so.
