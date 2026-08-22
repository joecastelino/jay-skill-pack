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
| JE detail (auto-posting) | `/accounting/journalEntry/transactionId/<txnId>/dealerId/<dealerId>/transactionType/AUTO_POSTING/edit` |
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
2. Status tabs render as leaf nodes at **y≈146**: `All` (x≈112) · `Draft` (x≈183) · **`Error` (x≈281)** · `Pending Approval` (x≈402). `/mouse` click Error.
3. Row count appears as `N Result(s)` in `document.body.innerText`.
4. Parse rows straight out of `body.innerText` — the table is virtualized, there are no `.ant-table-row` nodes. Column order:
   `Status · ID · Type · Accounting Date · Reference Type · Reference · Journal · Journal Type · Document Type · Description · Amount · Created By · Modified Time · Franchise`
5. Row-open: the ID cell is a leaf `div.root_content_blackNormalContent__*` at **x≈344**. Get coords with:
   ```js
   [...document.querySelectorAll('*')].filter(e=>e.children.length===0 && /^\d{7}$/.test((e.innerText||'').trim()) && e.getBoundingClientRect().x>330 && e.getBoundingClientRect().x<380)
   ```
   then `/mouse` click `x+10, y+8`. Verify `location.href` contains `transactionId` — if not, the click missed.

**Search box gotcha:** the page-level expandable search starts at width 0. Click the magnifier `.icon-search` at **x≈1087, y≈216** to expand, THEN type. `/type` with only `{text:...}` returns **HTTP 400** — always pass a selector:
```
/type {"selector":"input.root_expandableSearchField_expandableInput__3cvPtuyg2T","text":"..."}
```
It's a **prefix/contains match on the ID column only** — searching a description string returns 0 rows.

---

## 3. Reading a JE's posting lines (the actual diagnosis)

On the detail page, `document.body.innerText.split('General Information')[1]` gives the header block
(Franchise / Journal Number-Name / Document Type / Description / Reference Type / Reference /
Accounting Date) plus Credit / Debit / **Balance** / Gross Profit and the posting-line table.

For an **editable (Error/Draft)** JE the GL cells are react-selects, not text. Pull them with:
```js
(()=>{const o=[];[...document.querySelectorAll('[class*="tekion-select-b62m3t-container"]')]
  .filter(e=>e.getBoundingClientRect().y>500).forEach(s=>o.push((s.innerText||'').trim()));
 const a=[...document.querySelectorAll('input')].filter(i=>i.placeholder==='0.00'
  && i.getBoundingClientRect().width>0).map(i=>i.value);
 return JSON.stringify({gl:o,amt:a})})()
```
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
- Left-nav items live **below the fold** and their coords shift as sections expand/collapse. Always `scrollIntoView({block:'center'})` the target, re-read `getBoundingClientRect()`, THEN `/mouse` click. Clicking a stale coordinate silently opens the *previously* selected section (you'll see e.g. "Receivables Mapping" when you asked for "Others").
- Clicking the same parent twice toggles it shut. Re-read the nav text after each click.
- Right-panel mapping cards are collapsed accordions — click the card title (`x>350`) to expand and reveal its table.

---

## 5. Known root cause: department-scoped mapping gap

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

### OPEN ITEM — SCT 876 (as of 2026-08-21, diagnosed read-only, NOT fixed, awaiting Joe)
`Parts Cash Holding Account` exists only for dept `05 - PARTS & ACCESSORIES (Parts)` → `2045 - CASH SALES`.
No dept-`06 - Online Parts Sales (Parts)` row. Proposed fix:
`Parts Cash Holding Account | 06 - Online Parts Sales (Parts) | 2045 - CASH SALES`, then re-submit the 10 errored JEs.
Affected: journal 32 PARTS CASH SALES, SOs 331573 / 331575 / 331577 / 331579 / 331580 (sale + deposit each),
all created by Tiffany Dao on 8/21/2026, ~$264 sale side + ~$158 deposit side.
Reference JEs: errored `1685205` (sale, $88.77) / `1685203` (deposit, $51.24); working posted control `1685197` / `1685196` (wholesale, dept 05).
Errored sale lines: `[BLANK] $51.24` · `4748 SLS-TOY PARTS ONLINE RETAIL -$46.58` · `6748 CST PRT ONLINE RTL-TOY $37.53` · `2410 PARTS INV-TOY EXCL-TIRES -$37.53` · `3140 ACCRD TAXES-SALES -$4.66`.
Likely related to the 8/19/2026 SCT parts tax-code-setup migration that also dropped the ONLINE sale types
(see `tekion-parts-tax-not-calculating-diagnosis`) — first online retail sales ran 8/21 and exposed both gaps.
**Check whether this was ever applied before re-diagnosing.**

---

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
