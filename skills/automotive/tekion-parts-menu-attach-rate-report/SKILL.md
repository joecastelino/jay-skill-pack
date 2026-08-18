---
name: tekion-parts-menu-attach-rate-report
description: Build a "how many of part X were sold, and what % were bundled into a service menu vs sold à la carte" report for any Tekion store and part category (e.g. cabin filters, engine air filters, wiper blades). Combines the part-sales ledger with a cheap RO-tag menu classification. Use when Joe asks for a parts sales report that must "include service menus" / show menu attach rate.
triggers:
  - filter sales report with menus
  - menu attach rate
  - parts sold vs menu bundled
  - cabin filter sales report
  - air filter sales report
  - part attach rate to service menu
related_skills:
  - tekion-part-sales-ledger-report
  - tekion-openapi-repair-orders
---

# Tekion Part-Category Sales Report WITH Service-Menu Attach Classification

Verified end-to-end at Blackstone Toyota (BT, dealer 1249), 2026-08-18: cabin filter
(PN prefix 87139) + engine air filter (PN prefix 17801), 30-day window, 965 total
units / $26,738.61, 603 unique ROs, 28% menu-attach rate, ZERO unclassified ROs.

## When to use
Joe asks for a parts-category sales report (filters, wipers, batteries, etc.) that
must show how much was sold **inside a service menu package** vs **as a standalone
opcode** ("include service menus" is the trigger phrase). This is a layer ON TOP OF
`tekion-part-sales-ledger-report` — do the ledger harvest exactly as that skill
describes, then add the RO-tag classification step below.

## The two-layer method (cheap — no operation fan-out needed)

### Layer 1 — Part sales ledger (see tekion-part-sales-ledger-report for full detail)
Harvest `POST /api/parts/activity-log/u/search` (transactionType=SALE) for the
whole store over the window, filter client-side by PN prefix (the API's own
partNumber filter does NOT support LIKE/prefix — see that skill's pitfalls). Net
out UN_FILLED reversals. **Also drop `subType` null / `type` in {LOCK, UNLOCK}
rows** — these are counter reservation events, not real sales (found at BT: 16 of
1,067 rows). Split `refType`: FULFILMENT=RO sale, SALES_ORDER=counter sale,
CUSTOMER=return (exclude, report separately if non-zero).

### Layer 2 — RO menu classification (the new piece this skill adds)
For every unique RO number from the FULFILMENT rows, batch-fetch via OpenAPI
`repair-orders:search` with `documentNumber IN [<=50 ids]`, dealer_id for the
target store. This is **FREE** — no jobs/operations fan-out, `tags` comes back on
the search result itself (same trick used in the alignment-by-advisor report).

Classify each RO by its OPCODE tags:
```python
import re
MENU_RE = re.compile(r'^TEK\d{4,6}[BPV][NS]M$')  # fleet-wide SERVICE_MENU opcode convention
opcodes = [t["value"] for t in ro.get("tags",[]) if t.get("field")=="OPCODE"]
menu_ops = [o for o in opcodes if MENU_RE.match(o)]
cls = "menu" if menu_ops else ("ala_carte" if opcodes else "unclassified")
```
Join back to the ledger rows by RO number (`refNumber` on the ledger row ==
`documentNumber` on the RO search result). At BT this resolved 603/603 ROs with
zero unclassified — expect near-100% coverage since `documentNumber IN` batches of
50 reliably return full results (unlike time-window search, this isn't paginated).

### ⚠️ Known approximation — state this caveat in the report
Classification is at the **RO level**, not proven part-to-opcode level: "menu" means
*some* menu-package opcode tag is present on the RO, not that the specific filter
part was verified to be a line item *within* that specific menu opcode's parts list.
On a multi-service RO (e.g. a customer also got an unrelated 30K menu AND paid
separately for an à la carte filter swap same visit) this could over-count "menu."
For a HARD proof-level classification (matching the rigor of the alignment report's
`corrections[]` story-text method), you'd need to fan out to
`jobs/operations/parts` and confirm the specific part line sits under a job whose
operation opcode is the menu package — this costs one fan-out call per RO and
wasn't done here for speed. Default to the cheap RO-tag method and disclose the
approximation; only do the expensive proof if Joe specifically doubts a number.

## Aggregation
Per part category: total units/revenue, RO vs counter split, and among RO units:
menu-attached vs à la carte vs unclassified (units, revenue, unique RO count each).
Also roll up top menu opcodes driving attach (Counter of `menu_ops` across menu-
classified rows) — useful to show Joe WHICH interval packages (30K/60K/90K etc.)
are carrying the part.

## Delivery
- Scorecard PNG: house style (white bg, red #EB0A1E 3px header rule, `.kpi.hero`
  red cards for headline total units + revenue, dark `#1a1a1a` table headers).
  Render via headless Playwright screenshot of local HTML (not matplotlib).
- Multi-tab xlsx: Summary, Menu Opcodes, one Detail tab per part category (RO#,
  part#, class, menu opcode(s), qty, price, revenue, timestamp, customer) with
  counter sales appended below the RO rows in the same tab.
- Plain-text Slack summary table.

## Pitfalls
- **Don't reuse a cached logo image without verifying it matches the target
  store.** `logo_0.png` in `~/tekion-reports/` is Stevens Creek Toyota's logo — used
  by default in several older render scripts (`render_menu_sales_paged_bc.py` etc.)
  even for non-SCT reports. `vision_analyze` the logo file (or just skip the image
  and use a styled text wordmark) before shipping a report for a DIFFERENT store —
  caught this on the BT report (SCT logo would have gone out under BT's name).
- **Store nickname ambiguity**: Joe used "BST" to mean Blackstone Toyota (BT,
  dealer 1249) — not one of the canonical 7 store codes. When a store reference is
  ambiguous, state your assumption inline in the response and proceed (don't block
  with clarify if a reasonable default exists) — Joe will correct if wrong.
- **Delegation budget**: this full pattern (browser ledger harvest + bisection edge
  cases + OpenAPI RO batch + classification + render) is too much for one ~80-
  iteration subagent run. Split it: delegate ONLY the browser-dependent ledger
  harvest to a subagent (that's the part needing the isolated Tekion session /
  :9225), then do the OpenAPI RO-tag classification, aggregation, and rendering
  yourself directly via execute_code/terminal — those steps are pure data work with
  no browser dependency and are much faster done directly than re-delegated.
- Bisection dead-ends (count>20 even at 1ms) and the partNumber-LIKE-ignored trap
  are documented in `tekion-part-sales-ledger-report` — read that skill first, this
  one only adds the menu-classification layer on top.
- **Window pivot after delivery (e.g. Joe says "actually just give me month-to-
  date" after you already built a 30-day report)**: don't re-harvest. If the new
  window is a strict subset of the already-harvested range, just refilter the raw
  ledger JSON on its timestamp field (Pacific tz) and re-run the same
  aggregate→classify→render pipeline on the subset — the RO-tag classification data
  you already pulled covers a superset of RO numbers too, so no new OpenAPI calls
  are needed either. Parameterize the renderer/xlsx-builder scripts with a `tag`
  CLI arg (e.g. `-mtd`) so both windows' outputs can coexist on disk.
- **Renderer KPI labels must be dynamic, not hardcoded to the window**: a "(30d)"
  or similar period label baked into the HTML template will silently go stale when
  you re-run for a different window (e.g. MTD) — vision_analyze caught a stale
  "(30d)" label after a same-script MTD re-render. Derive the label text from the
  actual date range being rendered, not a literal string.
