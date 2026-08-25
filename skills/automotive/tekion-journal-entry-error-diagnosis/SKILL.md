---
name: tekion-journal-entry-error-diagnosis
description: Diagnose Tekion Accounting Journal Entries stuck in ERROR status (auto-posting JEs that failed to post). Covers the JE list/detail URLs, reading GL posting lines out of the DOM, finding the blank/unmapped GL account, and tracing the root cause back to a missing row in GL Account Transaction Mapping. Use for "look at journal entries", "JEs in error", "auto posting failed", "GL account blank on journal entry".
triggers:
  - journal entries
  - journal entry error
  - JE in error
  - auto posting journal entry
  - GL account mapping
  - accounting error tekion
  - journal entry won't post
---

# Tekion Journal Entry ERROR Diagnosis

**Joe's shorthand:** "**3.0**" = Tekion (the DMS) — e.g. "I need a lot of 3.0 help today".
"**GLAM**" = GL Account Transaction Mapping (`/accounting/glaccountmapping/list`).
Joe applies GL config fixes himself and will say so mid-thread ("I fixed the glam") — **always
re-verify the live mapping state before re-reporting a previously-diagnosed open item.**

Joe's ask is usually **"look at Journal entries, don't change anything, tell me what's wrong."**
This is a READ-ONLY diagnosis. Never click Submit / Save as Draft / Perform action and move to next
unless he explicitly says to fix it.

All work through the `:9223` persistent browser (`/eval`, `/mouse`, `/type`, `/navigate`).
**Verify `localStorage.currentActiveDealerId` matches the target store first** — the session drifts.

---

## 1. URLs (verified SCT 876, 2026-08-21)

| Screen | URL |
|---|---|
| **Journal Entries list** | ✅ `/accounting/journalEntry/list` (camelCase; `/accounting/journalentry/list` also works) |
| JE detail (Error/Draft, editable) | `/accounting/journalEntry/transactionId/<txnId>/dealerId/<dealerId>/transactionType/AUTO_POSTING/edit` |
| JE detail (Posted, read-only) | `/accounting/journalEntry/transactionId/<txnId>/dealerId/<dealerId>/view` |

> ⚠️ **`<txnId>` IS NOT THE 7-DIGIT JE ID** (burned ~6 turns 2026-08-24). The list/header shows a
> display ID like `1685170`; the URL wants an internal 14-digit transaction id like
> `60215445227271`. Navigating with the 7-digit number **silently fails** — you stay on whatever
> page you were on (often a stale RO detail) and `body.innerText` looks like a real page, so it
> reads as a false success. **There is no way to derive txnId from the display ID** — you must open
> the row from the list. See §2 "Open a specific JE by its 7-digit ID".

**Stale-route trap:** the first `POST /navigate` to `/accounting/journalEntry/list` can land on a
previously-open JE detail (`.../transactionId/.../view`). Always assert `location.href` ends in
`/list`; if not, navigate a second time.
| Chart of Accounts | `/accounting/chartOfAccounts/list` |
| **GL Account Transaction Mapping** | ✅ `/accounting/glaccountmapping/list` (all lowercase!) |

**Dead ends — do NOT waste turns on these:**
- `/accounting/journal-entry`, `/accounting/journal-entries`, `/accounting/glam` → silently redirect to **chartOfAccounts/list** (looks like it "worked", it didn't — always assert `location.href`)
- `/accounting/journal/list`, `/accounting/glAccountMapping` (camelCase) → render **blank**
- `/accounting/accountSetup`, `/accounting/accountingSettings`, `/accounting/settings/glAccountMapping` → bounce to `/ro/quotes`
- `/gl/journal-entry` → bounces to `/home`

**Finding new accounting screens:** App Grid (nine-dots at ~22,32) → search box `input[placeholder='Search']` → type e.g. "account". Results list shows Apps / Analytics / **Settings** groups. Under Settings you get: Distribution Accounts, Accounting Global Settings, **GL Account Mapping** — all `/ Accounting Settings`. Click the result text (find by `innerText.startsWith(...)`, it's a multi-line card so exact-match on a leaf node fails).

---

## 2. Reading the Error queue

1. Navigate `/accounting/journalEntry/list`, sleep 8.
2. Status tabs render as leaf nodes at **y≈158** (was y≈146 — coords drift, re-read them):
   `All` (x≈124) · `Draft` (x≈206) · **`Error` (x≈327)** · `Pending Approval` (x≈515). `/mouse` click Error.
   Find them live — note the filter picks the FIRST match by y, since "Error" also appears in every row:
   ```js
   [...document.querySelectorAll('*')].filter(e=>e.children.length===0 &&
     ['All','Draft','Error','Pending Approval'].includes((e.innerText||'').trim()) &&
     e.getBoundingClientRect().width>0)   // tab row is y<200; rows are y>400
   ```
   The tab labels contain animated odometer digits (long `0\n1\n2...` runs in `innerText`) —
   the count is NOT readable from the tab; use the `N Result(s)` line instead.
3. Row count appears as `N Result(s)` in `document.body.innerText`.
4. Parse rows straight out of `body.innerText` — the table is virtualized, there are no `.ant-table-row` nodes. Column order:
   `Status · ID · Type · Accounting Date · Reference Type · Reference · Journal · Journal Type · Document Type · Description · Amount · Created By · Modified Time · Franchise`
5. Row-open: the ID cell is a leaf `div.root_content_blackNormalContent__*` at **x≈344**. Get coords with:
   ```js
   [...document.querySelectorAll('*')].filter(e=>e.children.length===0 && /^\d{7}$/.test((e.innerText||'').trim()) && e.getBoundingClientRect().x>330 && e.getBoundingClientRect().x<380)
   ```
   then `/mouse` click `x+10, y+8`. Verify `location.href` contains `transactionId` — if not, the click missed.

**Search box gotcha:** the page-level expandable search starts at width 0. Click the magnifier
`.icon-search` (**x≈1095, y≈224** on the JE list; find it live and IGNORE the one at ~268,33 =
the global AI-search toggle) to expand, THEN type. `/type` with only `{text:...}` returns
**HTTP 400** — always pass a selector:
```
/type {"selector":"input.root_expandableSearchField_expandableInput__3cvPtuyg2T","text":"..."}
```
It's a **prefix/contains match on the ID column only** — searching a description string returns 0 rows.
Note the search box resets on every navigate and clicking a status tab; re-expand each time.

### Open a specific JE by its 7-digit ID (the ONLY reliable path)
```python
api("/navigate",{"url":".../accounting/journalEntry/list"}); sleep(9)   # assert href ends /list
api("/mouse",{"x":1095,"y":224}); sleep(2)                              # expand search
api("/type",{"selector":"input.root_expandableSearchField_expandableInput__3cvPtuyg2T","text":"1685170"})
api("/press",{"key":"Enter"}); sleep(6)                                 # → "1 Result(s)"
# click the ID leaf (lands ~x374,y314 for a single-result list)
coords = eval("""[...document.querySelectorAll('*')].filter(x=>x.children.length===0
   && (x.innerText||'').trim()==='1685170')[0].getBoundingClientRect()""")
api("/mouse", center(coords)); sleep(8)
# now location.href carries the real transactionId — verify it changed
```
Search works from the **All** tab too (no need to be on Error). ~25s per JE end-to-end, so batch
the pulls in ONE `execute_code` call.

### Scraping the FULL error list (virtualized — you only get ~20 rows per read)
The scroll container is an **unclassed `<div>`** (`className===''`) with `scrollHeight>clientHeight`
and `clientHeight>300`. It is NOT findable by class. Loop: read `body.innerText` → regex rows →
`el.scrollTop += 350` → repeat until `scrollTop` stops advancing. ~45 iterations covers ~117 rows
in about 25s. Row regex that works (Type may be multi-word, and some rows carry an extra
`Rev`/`Adj` badge line — anchor on `Error\n(\d{7})\n`):
```python
re.compile(r"Error\n(\d{7})\n([A-Za-z ]+)\n(\d\d/\d\d/\d\d)\n([^\n]+)\n([^\n]+)\n([^\n]+)\n"
           r"([^\n]+)\n([^\n]+)\n([^\n]+)\n(\$[\d,\.]+)\n([^\n]+)\n([^\n]+)\n")
```
Dedupe into a dict keyed by JE id (rows repeat across scroll reads). Then aggregate with `Counter`
on journal / reference-type / creator / accounting-date — **that grouping IS the report Joe wants**.
Persist to `/tmp/<store>_je_errors.json` since `execute_code` is stateless between calls.

---

## 3. Reading a JE's posting lines (the actual diagnosis)

On the detail page, `document.body.innerText.split('General Information')[1]` gives the header block
(Franchise / Journal Number-Name / Document Type / Description / Reference Type / Reference /
Accounting Date) plus Credit / Debit / **Balance** / Gross Profit and the posting-line table.

For an **editable (Error/Draft)** JE the GL cells are react-selects, not text. Pull them with
(**use the loose `[class*="tekion-select"][class*="container"]` selector — the hashed
`tekion-select-b62m3t-container` class changes between builds — and `y>300`, not `y>500`, or you
drop the first posting line**):
```js
(()=>{const o=[];[...document.querySelectorAll('[class*="tekion-select"][class*="container"]')]
  .filter(e=>e.getBoundingClientRect().y>300).forEach(s=>o.push((s.innerText||'').trim()));
 const a=[...document.querySelectorAll('input')].filter(i=>i.placeholder==='0.00'
  && i.getBoundingClientRect().width>0).map(i=>i.value);
 return JSON.stringify({gl:o,amt:a})})()
```
- The `gl` array's **first two entries are the header selects** (Reference Type e.g.
  `"Parts Sales Order"`, and Reference e.g. `"331575"`) — posting lines start at index 2, and
  `amt[0]` pairs with `gl[2]`. Don't off-by-two the diagnosis.
- A GL cell reading literally **`"Select"`** = the blank/unmapped account. That is the error.
- Amounts pair positionally with the GL list (index 0 ↔ index 0).
- A **Posted** JE renders the same table as plain text (no selects) — the JS above returns empty; just read `innerText` instead. **This difference is the tell for Posted vs Error.**
- Header line `"Auto Posting Journal Entry - <id> / Error / N of 10"` confirms you're in the error set and gives your position.
- **`Gross Profit` in the header does NOT match the line math** (e.g. JE 1685205 shows $116.83 while revenue−cost = $46.58−$37.53 = $9.05; its deposit sibling shows $107.78; a posted wholesale JE shows −$70.85). Looks like a running/aggregate figure, not per-entry. **Unverified — flag it to Joe as unexplained rather than inventing a definition** (NEVER-GUESS rule).
- The sale JE and its deposit JE are a **pair per sales order** and both carry the same defect. Always pull both: sale = `Dr Holding / Cr Revenue + Tax`, deposit = `Dr Cash (2045) / Cr Holding`. Reference/control number on both = the parts SO number.

Cross-check with `vision_analyze` on a screenshot — it reliably calls out the red-highlighted blank
select. Screenshot endpoint is **GET** `http://127.0.0.1:9223/screenshot` returning `{"screenshot": "<b64>"}`
— `POST /screenshot` is 404.

---

## 4. Root-cause: find the missing GL mapping

**The method that works: diff an errored JE against a POSTED JE from the same journal.**
The posted one shows which account belongs in the slot the errored one left blank.

Then go to `/accounting/glaccountmapping/list` and find the mapping table that should have produced it.

Left-nav structure (accordion — parent sections expand to reveal counted children):
```
Variable Operations
  New Vehicles (1) · Used Vehicles (1) · F&I Products (1) · Receivables (2) · Payables (5)
Fixed Operations
  Services (3) · Part & Accessories (6) · Purchase Orders (1) · Warranty Credit (1) · Others (2)
Payment Receipts
  Variable Operations (1) · Fixed Operations (6) · Tekion Pay (1)
Payroll
```
Key leaves for parts/service JE errors:
- **Fixed Operations → Part & Accessories** → cards: Parts-Customer Pay / Parts-Toyota Care / Parts-Internal / Parts-Warranty / **Online Parts Payments** / Parts-Counter. Columns: `Service Type · Source Code · Tax Status · Sale Type (Fixed Ops) · Sales Subtype · Department · GL Account`.
- **Fixed Operations → Others → Fixed Operations (Other)** → `Freight charge`, `Restocking Fee`, `Other supplies`, **`Service Cash Holding Account`**, **`Parts Cash Holding Account`**. Columns: `Fixed Operations (Other) · Department · GL Account`. ← *cash-holding gaps live here*
- **Payment Receipts → Fixed Operations (6)** → Parts/Service Payment Methods by pay type. Columns: `Payment Method (Parts) · Sale Type (Fixed Ops) · GL Account`.

### Nav pitfalls (cost several turns)
- **The section parents (`Variable Operations` / `Fixed Operations` / `Payment Receipts` / `Payroll`)
  are NOT leaf nodes** — they're `div.ant-menu-submenu-title` inside an `li.ant-menu-submenu` and
  they wrap child text, so a `children.length===0` leaf search returns **nothing** and you conclude
  (wrongly) the item doesn't exist. Find them by exact `innerText` match on `li,div` and click the
  title div (`Fixed Operations` ≈ x230,y481 at SCT). The *children* (`Others (2)`,
  `Part & Accessories (6)`) ARE matchable — take the LAST match (`e[e.length-1]`) since the `li`
  and inner `div` both match; the inner div gives the correct clickable center.
- Right-panel mapping **cards** (`Fixed Operations Other`, `Online Parts Payments`, `Parts-Counter`)
  ARE leaf nodes — click by exact leaf text, then re-read `body.innerText`. Clicking the same card
  title again collapses it, which is handy for iterating several cards in one loop.
- Left-nav items live **below the fold** and their coords shift as sections expand/collapse. Always `scrollIntoView({block:'center'})` the target, re-read `getBoundingClientRect()`, THEN `/mouse` click. Clicking a stale coordinate silently opens the *previously* selected section (you'll see e.g. "Receivables Mapping" when you asked for "Others").
- Clicking the same parent twice toggles it shut. Re-read the nav text after each click.

---

## 5. Triage FIRST: not every Error JE is a mapping gap

Before you go hunting mappings, split the error queue by **Balance** (header line on the detail page):

| Balance | Meaning | Fix owner |
|---|---|---|
| **$0.00** + one GL cell reads `"Select"` | **Mapping gap** — Tekion built a balanced entry but couldn't resolve one account | Jay (config) |
| **Non-zero** (Dr ≠ Cr) | **Malformed entry** — lines are missing, not accounts. No mapping change will fix it | Accounting must rebuild |

Real example (SCT 8/24/2026) — 117 errors, 114 were the mapping gap, 2 were NOT:
- `1686422` Warranty Credit Memo — Balance **−$236,238.16**: Dr `3001 A/P-TOYOTA` $261,581.49 vs only
  $25,343.33 of credits across 15 `2211 - PDI` lines. Credit side truncated.
- `1685915` Used vehicle purchase, stock CT27020 — Balance **−$26,660.00**: single line
  Dr `2400 USD VEH INV - NON-CERT TOYOTA`, no offsetting credit at all.

Call these out separately in the report. Saying "117 JEs, all the same mapping bug" when 2 aren't
is exactly the kind of wrong root cause Joe rejects instantly.

## 5b. Known root cause: department-scoped mapping gap

**Symptom pattern seen at SCT 8/21/2026** — 10 Error JEs, all journal `32 - PARTS CASH SALES`,
all Auto Posting, all same creator, from 5 sales orders × 2 JEs each (the sale + the deposit).
Blank line = the **cash-holding / cash-sales** account in both.

Root cause: **the mapping row exists for one department but not the department the transaction ran under.**
Here, `Parts Cash Holding Account` was mapped only for `05 - PARTS & ACCESSORIES (Parts)` → 2045,
but ONLINE RETAIL parts sales post under `06 - Online Parts Sales (Parts)`. Revenue mapped fine
(4748 / 4731 both had dept-06 rows), so only the holding-account lookup came back empty → blank line.

**Generalize:** when a JE errors with ONE blank line and everything else resolves, look at the
`Department` / `Sale Type` / `Sales Subtype` on the *posted* sibling vs the errored one. The blank is
almost always a mapping table that has rows for the common department but not the edge-case one.
A cluster of errors all starting the same day usually = a new sale type / channel went live and
only half its mappings were built.

Fix (only with explicit go-ahead): add the missing row via the mapping card's **Add** button, then
re-open each errored JE and Submit.

### RESOLVED — SCT 876 — mapping fixed by Joe 2026-08-25 (was compounding 8/21→8/24)

**Joe added the row himself on 2026-08-25:**
`Parts Cash Holding Account | 06 - Online Parts Sales (Parts) | 2045 - CASH SALES`
(*Fixed Operations → Others → Fixed Operations (Other)*). New online-retail sales post clean from
~8:20 AM 8/25. Last errors: SO 331926 (8:11) and 331930 (8:27, reworked as 331932).

**"I don't want a holding account, can I just use 2045?" — YES. Answer Joe accepted:**
Tekion ALWAYS writes the two-JE pair (sale + deposit); there is **no toggle to suppress the deposit
leg**. But pointing the holding mapping at the cash account *is* forgoing the holding account —
the deposit JE becomes a **self-canceling wash** (`2045 +X / 2045 −X` = net $0) and nothing ever
parks in a separate holding bucket. Structurally identical to how a normal counter sale already
posts. Verified on SO **331932**: sale JE `1686453` = `2045 +24.88 / 4748 −22.62 / 6748 +17.40 /
2410 −17.40 / 3140 −2.26`; deposit JE `1686452` = `2045 24.88 / 2045 −24.88`. Reversals
(`1686454`/`1686455`, Chris) also clean.

**CRITICAL: the mapping fix does NOT retroactively heal the backlog.** Each already-errored JE has
the blank GL cell *saved on the record*. ~116 pre-fix JEs (57 SOs, $19.1K, 8/21–8/24) remained in
the Error queue after the fix. Cleanup = open one, set the blank line to the cash account, Submit,
then use **"Perform action and move to next Journal Entry"** to chain the rest (no list round-trips).
Do the first pair, screenshot for Joe, then chain.

**Growth curve — this is the headline number when re-reporting:**

| Date checked | Error JEs | Sales orders | $ |
|---|---|---|---|
| 2026-08-21 | 10 | 5 | ~$422 |
| 2026-08-24 | **114** (of 117 total in queue) | **57** | **$19,104.60** |

By accounting date on 8/24: 8/21 = 30 · 8/22 = 50 · 8/23 = 22 · 8/24 = 12 (still generating at 7:35 AM).
Creators: Tiffany Dao 57 · Alfonso Morataya 39 · David Camacho 18. All journal `32 - PARTS CASH SALES`,
Reference Type `Parts Sales Order`.

**Confirmed mapping evidence** (SCT, *Fixed Operations → Part & Accessories*): both the
**Online Parts Payments** and **Parts-Counter** cards route `Retail/ONLINE RETAIL` → dept
`06 - Online Parts Sales (Parts)` → `4748`, and `Wholesale/ONLINE WHOLESALE` → dept 06 → `4731`.
So revenue resolves under dept 06 but the holding account has no dept-06 row → blank line.

Reference JEs 8/24: errored sale `1685170` (SO 331575, $30.74) / deposit `1685169` ($17.74);
errored `1686431`/`1686430` (SO 331922). Working posted control = `1686437` (SO 331924, a **counter**
sale, dept 05) which shows `2045 - CASH SALES $8.98` in exactly the slot the errored ones leave blank.
Errored sale lines pattern: `[BLANK] +deposit$` · `4748 −sale$` · `6748 +cost$` · `2410 −cost$` · `3140 −tax$`.
Deposit JE pattern: `2045 - CASH SALES +$` · `[BLANK] −$`.

Traces to the 8/19/2026 SCT parts tax-code-setup migration that also dropped the ONLINE sale types
(see `tekion-parts-tax-not-calculating-diagnosis`).
**Before re-diagnosing: check whether the dept-06 row was ever added — if not, LEAD with the growth
number, not with a fresh walkthrough of the same evidence.**

---

## 5c. VC (Volkswagen of Clovis, 1891) — SO 71581 case, 2026-08-24

Second confirmed instance of the same class of defect, different store/slot:

- Error queue = exactly **2 JEs**, both journal `32 - PARTS CASH SALES`, Reference Type
  `Parts Sales Order`, Reference `71581-1`, created by Weston Truesdail 8/24 1:14 PM.
  - `121568` sale, $216.64, Balance $0.00 → `[Select] +116.65 · 4764 SLS-P+A CNTR WHL −116.65 ·
    5764 C/S +99.99 · 1445 INVENTORY −99.99`
  - `121567` deposit, $116.65, Balance $0.00 → `1188 CASH SALES +116.65 · [Select] −116.65`
- Blank slot in both = the **parts cash HOLDING/offset account**.
- **Working control:** SO 71539 (Charge Customer, wholesale) JEs `121275` sale
  `1188 CASH SALES +152.33 / 4764 −152.33 / 5764 / 1445` and `121274` deposit
  `1304 RECEIVABLES-CUST-SP+A +152.33 / 1188 CASH SALES −152.33`. Same slot resolves to
  **1188 - CASH SALES** there.
- **Discriminator:** SO 71581 is the only recent VC counter sale paid by **Check**. Every posted
  control (71504/71500/71495/71432/71539/71555/71522) is **Charge Customer**. Charge routes to AR
  (1304) via *Payment Receipts → Fixed Operations → Parts Payment Methods*; Cash/Check/Card all map
  to `1188 - CASH SALES` there — so on a Check sale the payment-method account and the holding
  account are the same 1188, and the holding lookup comes back empty.
- **Structural diff vs SCT:** VC's *Fixed Operations → Others* has **one** rule only
  (`FIXED OPERATIONS SALES TAX`, 4 sales-tax rows). SCT has an additional `Fixed Operations (Other)`
  rule that carries **Parts Cash Holding Account / Service Cash Holding Account**. VC has **no
  Parts Cash Holding Account mapping at all**. ← most likely root cause, but NOT 100% proven
  (unexplained: how 1188 resolved into that slot on the Charge JEs). Per NEVER-GUESS, flag the
  residual uncertainty rather than asserting.
- Correction path: SO is Closed+Paid → **cannot reopen or void** (see `tekion-parts-sales-orders`).
  Fix the mapping, then reopen each Error JE and Submit.

### VC nav notes (cost ~10 turns)
- `/accounting/glaccountmapping/list` **randomly redirects** to whatever SPA route was last hot
  (`/parts/tax-code-setup`, `/parts/parts-settings`, `/parts/inventory/part`, `/parts/default-part-pricing`).
  Always loop the navigate up to 4–5× asserting `location.href` contains `glaccountmapping`.
- **Deep-link by module instead of clicking the nav:**
  `?module=FO_OTHERS`, `?module=PAYMENT_METHODS_FIXED_OPS`, `?module=FO_SERVICES`,
  `?module=FO_WARRANTY_CREDIT`. Far more reliable than the accordion.
- Left-nav leaf clicks at **x≈123 land on the label text and mis-fire**; click at **x≈300** (row
  body) instead. Also collapse `Variable Operations` first so `Others` sits above the fold.
- The mapping **cards** (`FIXED OPERATIONS SALES TAX`, `Parts Payment Methods`) are collapsed by
  default — click the card title leaf to expand before reading `innerText`.
- Sales Order list search: type into `input[placeholder='Ctrl + Shift + L']` + Enter. **Filters
  block it** — click `Clear` (leaf at ≈396,181; `Reset` at ≈306,181 does NOT clear) first or you get
  `0 Result(s)` on a real SO. Results are prefix-ish and the previous rows stay below, so read only
  the first block after `Dep. Name`.

## 6. Reporting to Joe

He wants: the count, the pattern (grouped by order/creator/journal — not 10 unrelated bullets), the
exact blank line quoted against a working posted example, the one-sentence root cause, and the fix
he could apply. Explicitly restate that you changed nothing. If an ID he gave doesn't resolve, say so
and ask what it is rather than guessing (7-digit JE IDs prefix-match, so a 6-digit number will return
a bogus 10-row "hit" — don't present that as the answer).

## Related skills
- `tekion-sitemap` — nav base; Accounting URLs above are mirrored there
- `tekion-parts-sales-orders` — the source documents behind PARTS CASH SALES JEs
- `tekion-parts-tax-not-calculating-diagnosis` — sibling "config gap causes wrong posting" pattern
