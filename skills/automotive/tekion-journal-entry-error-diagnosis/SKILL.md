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
  - SO going into JE error
  - cost center not found
  - imbalance transaction
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

## 0. THE definitive diagnostic + audit trails (verified VC 1891, 2026-09-18)

### Posting Preview = the only thing that names the cause
**RO → kebab ⋮ (top-right) → "View Posting Preview"** → lines/fields highlighted **RED** identify
the exact cause: *"Control field invalid"*, *"GL account missing"*, *"Cost center not mapped"*.
Per **KB0026432** this applies only when the preview shows red fields; if it opens clean while the RO
still says journal-entry error, that's a different issue.
⚠️ **A JE Refresh overwrites the failed state — the original lines and error reason are GONE.**
So run Posting Preview/read the error BEFORE anyone refreshes. Never accept "refresh fixed it" as a
root cause: refresh is recovery (KB0026965), not diagnosis.

### Documented causes of RO JEs in error (KB0025997 + KB0026432)
1. Invalid **Control type** on a GL account used in the posting → fix: set Control type to
   *Custom & Non-Mandatory*, close the RO, then revert.
2. **Description Mandatory** on the GL account but the line has no description → uncheck it.
3. **Accounting date in a closed period** → either disable AGS *"Always use cashiering date as
   accounting date for customer pay ROs and SOs"* or grant previous-month posting permission.
4. **Missing GL mapping** for a cost center / pay type (KB0015431: "cost centre used in the RO was
   not mapped in GL Account mapping").
5. **Vehicle inventory balance $0** block → AGS → *"Send RO/SO postings to error if vehicle
   inventory account balance is zero"* → turn OFF.
6. AR **credit limit exceeded**. 7. **Duplicate VIN**. 8. **RO was force-closed** (pushes JE into error).
Also KB0017795 states the literal error: *"The Journal Entry is not balanced."*

### Audit logs — "did someone change something?" (answers it in one click)
The **history icon** (`div` with class `icon-history`, top-right ≈ **x1244, y96**; x1229 on account
edit pages) opens **Audit Logs** with user + timestamp + old→new values. Empty = *"No Logs Available!"*.

| Screen | What its audit proves |
|---|---|
| `/accounting/accountSettings` (AGS) | every global accounting setting change |
| `/accounting/autopostingsettings/list` | Posting Preferences + Templates changes |
| `/core/coupons/edit/<b64(code)>` | whether the coupon itself was edited |
| CoA account edit `/accounting/chartOfAccounts/dealer/<d>/account/<d>_<acct>/edit` | account master changes |

**VC result (2026-09-18): nobody changed anything.** Coupon 6995 = *No Logs Available*; acct 4403 =
*No Logs Available*; Auto-Posting Settings last touched **Carol Brewer, May 30 2023**; AGS last
touched **Carol Brewer, Jun 30 2026** (added 9191 to *GL Accounts Not Requiring Sales Chain*).
⇒ When audit trails are silent across the whole window, the change is **Tekion-side**, not dealer-side.

### Release-notes lookup (did Tekion ship a fix?)
DMS Home → the Release Notes TekTouch's *"Read All (n)"* is an **`<a href="/core/release/<releaseId>">`**
(read the href — clicking it doesn't navigate in :9223). The release page shows **Released On: <date>**
and item counts per department; filter with `?departmentId=ACCOUNTING|SERVICE|CORE|SALES|PARTS|...`.
**VC: ARC September 2026 Release, Released On: Sep 16, 2026** — 23 items / 9 departments; the only
Accounting item was *"Clear Non-Mandatory Fields on General Ledger Accounts"*. No JE/auto-posting/
coupon/discount item exists → timing can align with the symptom, but do NOT claim the release fixed it.

### Where the discount GL actually comes from (supersedes "it's in the GLAM")
The RO discount posting lines take their account **from the COUPON's GL Account Split**
(Coupon Management → *GL Account Split*: Labor → 4403, Parts → 4703, 100/100 at VC). **GLAM has no
discount/coupon dimension**: Fixed Operations → *Services* rules use Pay Type / Service Type / GL
Account (sale accounts only: 4410/4418/4402…), *Part & Accessories* uses Pay Type / Service Type /
Source Code / Customer Tax Status / **Sale Type (Fixed Ops)** — whose only values are
Wholesale / Retail / Repair Order / Internal. Discount lines post with **Description = "Coupon Code - <code>"**.
Related: AGS → Auto Posting → ***GL Accounts Not Requiring Sales Chain*** (KB0020992) is the declared
list of Sale-type accounts that need no Cost of Sale / Inventory Offset; **Sales Chains** live at
`/accounting/accountingChain/list` (a Sale-type account normally needs Sale → Cost of Sale → Cost
Offset). VC's list held only 9162/9163/9167/9191 (F&I income) and 4403/4703 are **not** in it and have
**no Sales Chain row** — flag it as a config gap, but it is **not proven causal** (a live CP RO posted
balanced with that gap in place). Check these account flags on the edit page: Control Number Mandatory /
Control 2 Mandatory / Description Mandatory / Disable Postings (all OFF on 4403/4703).

### Route-discovery trick
KB articles' *"Take me to …"* links are real DMS routes — navigate the :9223 tab to the KB article and
read `[...document.querySelectorAll('a')].map(a=>a.getAttribute('href'))`. This is how
`/accounting/accountSettings` (Accounting Global Settings) and `/accounting/accountingChain/list`
(Sales Chains) were found. Guessing routes is futile: unknown `/accounting/*` paths silently redirect
to `chartOfAccounts/list`.

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
| **$0.00** + **every GL resolved, no blank** | **Tekion posting-service defect** — nothing to fix, the entry is valid. Just repost | Joe (repost) — see §5d |
| **Non-zero** (Dr ≠ Cr) | **Malformed entry** — lines are missing, not accounts. No mapping change will fix it | Accounting must rebuild |
| `COST_CENTER_NOT_FOUND` + line-1 GL literally `null` | **Cost-centre not mapped** (internal ROs) — add the centre in Setup Fields → Cost Centre Setup, then Refresh + Submit each JE | Joe (config) |

⚠️ **Do not assume mapping gap.** Two of the four buckets above look identical in the Error tab
(both Balance $0.00). The discriminator is whether a GL cell is blank — check before diagnosing.

Real example (SCT 8/24/2026) — 117 errors, 114 were the mapping gap, 2 were NOT:
- `1686422` Warranty Credit Memo — Balance **−$236,238.16**: Dr `3001 A/P-TOYOTA` $261,581.49 vs only
  $25,343.33 of credits across 15 `2211 - PDI` lines. Credit side truncated.
- `1685915` Used vehicle purchase, stock CT27020 — Balance **−$26,660.00**: single line
  Dr `2400 USD VEH INV - NON-CERT TOYOTA`, no offsetting credit at all.

Call these out separately in the report. Saying "117 JEs, all the same mapping bug" when 2 aren't
is exactly the kind of wrong root cause Joe rejects instantly.

## 5a-2. VC (VW Clovis, 1891) — DISCOUNT NOT POSTED → out-of-balance JE, 2026-09-16

Reported by Chris Wiese / Carol Brewer (VC business manager): "the discount isn't coming over so it
goes in error and Carol is manually putting it in." **Second occurrence** (first 9/3, again 9/11).

Two errored JEs, both `CUSTOMER_PAY - Repair Order`, journal `30 - SERVICE CASH SALES`, doc type
`7 - Repair Order Invoice`, **every GL cell populated (NO blank cell)**, Balance ≠ 0:

| JE | RO | Acct date | Debit | Credit | **Balance** | Discount on RO |
|---|---|---|---|---|---|---|
| 122656 | 141821 | 09/03/2026 | $136.63 | $157.50 | **$20.87** | $20.87 |
| 123249 | 141957 | 03/19/2026 | $167.54 | $197.54 | **$30.00** | $30.00 |

**The discriminator (verified arithmetic — do this, don't trust OCR signs):**
- 141821 revenue lines `4410 $13.36 + 4770 $77.46 + 2221 tax $5.36 = $96.18` gross;
  `1188 CASH SALES = $75.31` = **gross minus the $20.87 discount** → `96.18 − 75.31 = 20.87`
  = the header Balance exactly.
- 141957: `4410 $3.76 + 4770 $96.19 + tax $5.42 = $105.37`; cash `1188 $75.37`;
  `105.37 − 75.37 = $30.00` = Balance exactly. (Vision misread 4770 as 80.19 — solving for the
  unknown from the header Credit total is what exposed it; **never diagnose off a screenshot's
  per-row digits.**)

So the structure is: **debit cash at the NET amount collected, credit revenue at GROSS, and never
emit the discount/contra-revenue line** → entry is malformed by exactly the discount → sits in
Error until someone hand-posts it. **This is the "non-zero balance = malformed entry, lines are
missing" bucket — a GL-mapping change cannot fix it** (there is no blank cell to fill), and it is
NOT the §5b/§5c blank-holding-account defect despite being the same store and the same "parts/service
auto-posting" family.

### RESOLVED 2026-09-18 — it is NOT a GLAM gap; the discount GL lives on the COUPON

Joe asked the discriminator directly: *"how do I fix it in the GLAM?"* **Answer: you don't — GLAM
has no discount/coupon slot at VC, and the posting template is fine too.** Walked live, dealer 1891:

**1. GLAM maps the SALE side only.**
- `Fixed Operations → Services (3)` = cards `Service- Customer Pay` / `Service- Internal Pay` /
  `Service- Warranty Pay`. Columns: **`Pay Type · Service Type · GL Account`** — CP rule rows:
  `Sublet→4481`, `Rental→9184`, `Express→4410`, `VW Car Care Maintenance→4418`, `All→4402`.
- `Fixed Operations → Part & Accessories (1)` = card `Parts and Accessories`. Columns: `Pay Type ·
  Service Type · Source Code · Customer Tax Status · Sale Type (Fixed Ops) · GL Account`. Values in
  play are only **Wholesale / Retail / Repair Order / Internal** — no `Discount`, no `Coupon`.
  Rows map the sale side: `4770` (CP RO Express), `4702` (CP RO), `4762/4764` counter,
  `4704/4706` warranty+internal, `4708` Carefree, `4710` Care/Care Plus.
- `Fixed Operations → Others (2)` = `FIXED OPERATIONS SALES TAX` (Labor/Parts/Sublet/Deductible →
  `2221 SALES + USE TAXES PAYABLE`) and `FIXED OPERATIONS OTHER` (one undimensioned row →
  `1188 CASH SALES`). **The blank dimension cell here is NORMAL at VC — it is NOT the defect**
  (earlier note in this skill was wrong to call it a leading signal).
- Therefore `4403 SERV CUST PAY DISCOUNTS VW` / `4703 PARTS CUST PAY DISCOUNTS VW` are the *contra*
  pair to `4402`/`4702` and can never be produced by a GLAM rule.

**2. The discount GL comes from the COUPON record.** Swept all 11 VC coupons live — every one is
already correctly mapped, so there was nothing to fix:

| Coupons | Labor GL | Parts GL | Split |
|---|---|---|---|
| GF, GIFTCARD, 10LABOR, 10CX, 15PL, 20PRTLBR, 5995LOF, 6995, 4995, 50OFF, 75OFF | 4403 SERV CUST PAY DISCOUNTS VW | 4703 PARTS CUST PAY DISCOUNTS VW | 100 / 100 |

**3. The posting template is fine.** Auto-Posting Settings → Posting Templates → **Repair Order →
Customer Pay → Fees → `Coupons`** line EXISTS (`Control`/`Control 2` = Default). ⚠️ The `Control` /
`Control 2` columns are **reference-field pickers, not GL accounts** — the dropdown offers
`Service Advisor Id, RO Number, VIN, VIN Last 8, Op Code, Part number, Customer Number, Customer
Name, Stock Number, Claim Number, Third Party Warranty Provider`. Don't mistake them for a GL slot.

**4. Live state 9/18:** JE `122656` (RO 141821) and `123249` (RO 141957) are both **Posted,
Balance $0.00**, and both now carry the contra lines (`4703 $26.00` + `4403 $4.00` on 123249).
VC Error queue = **0 Result(s)**. → discounts DO post now; the missing-line condition was
**time-bounded (pre-fix entries), not a standing config gap**.

**Fix for entries already in error = Refresh JE → Submit** (KB0026965 / KB0017733) — not a mapping
change, not hand-editing lines. If a *new* RO still drops its discount, get the RO# and trace the
coupon application on that RO: that would be a coupon-application failure, not GLAM.

### 5a-3. Joe's follow-up — "it shouldn't have to refresh, something else is wrong" (2026-09-18)

He escalated in four steps: **how do I fix it in the GLAM → it shouldn't need a refresh → why did this
go into error and MINE did not → did Tekion push an update?** Each time the wrong answer is a
workaround. He rejected a proposed error-queue watcher outright (*"no, I don't need that. I just need
to know why"*). **When Joe asks "why", answer the why — do NOT propose automation/monitoring/next
steps.** Per the fix-date rule, date every artifact against the release date before attributing cause.

**1. The control-case proof (pull the NEW entry, don't trust the screenshot).** Joe opened a fresh RO
and added a discount. His screenshot was unreadable/OCR-wrong (it read the store as "Volkswagen of
Cicero" and journal "20"; live is Clovis + journal `30`). Live JE `123820`, RO `142091`, created by
Joe 09/18 7:52 AM, **Posted, Dr=Cr=$144.23, Balance $0.00, GP $41.70** — and it carries the contra
lines with the source stamped on them:
```
 8. 4703 PARTS CUST PAY DISCOUNTS VW   $6.31   Description: "Coupon Code - 6995"   Count 0
 9. 4403 SERV CUST PAY DISCOUNTS VW   $38.84   Description: "Coupon Code - 6995"   Count 0
```
So the discount legs carry a **line description `Coupon Code - <code>`** (the Control/Control-2 columns
are `-`) and **Count = 0** while sale/tax lines read Count 1. Contrast the failing JEs 122656/123249
(§5a-2): same store, same journal, same coupon 6995, same LOF job — different outcome. Same coupon +
same job type + different result = **a time-bounded change, not a data difference.**

**2. ⚠️ REFRESH DESTROYS THE EVIDENCE.** The refresh overwrites the failed record in place (Modified
Time moves, lines are rewritten). After a refresh you can NOT post-mortem the cause — that's why the
"why" stayed unanswerable here. **Capture before anyone refreshes: Posting Preview screenshot + the
original posting-line set + the error text.** If a failing RO still exists, that's the whole answer.

**3. The RO-side root-cause list + the definitive diagnostic (KB0025997 / KB0026432 / KB0015431).**
These are the current under-reported articles — they supersede treating every error as a GLAM gap:
1. **Invalid Control type** on a GL account in the posting (fix: set Control type → `Custom &
   Non-Mandatory`, close, then REVERT it after)
2. **Description Mandatory** on the GL account but the line has no description
3. **Accounting date in a closed period** (fix A: turn off *Always use cashiering date as accounting
   date for customer pay ROs/SOs*; fix B: grant previous-month posting permissions)
4. **Missing GL account mapping** for a cost center / pay type — KB0015431: *"Cost centre used in the
   RO was not mapped in the GL Account mapping"*
5. **Vehicle inventory account balance $0** block setting
6. AR **credit limit exceeded** · 7. **Duplicate VIN** · 8. **RO was force-closed** (pushes the JE
   into error; mapping must be corrected before a manual fix)

**THE diagnostic that names the exact field: open the RO → kebab `⋮` (top-right) → "View Posting
Preview" → red-highlighted fields = the cause** ("Control field invalid", "GL account missing",
"Cost center not mapped"). KB0026432 warns: if Posting Preview shows *no* red fields, it's a different
(service-side) defect — don't force-fit this list. Use this on any RO that is still erroring.

**4. What was ruled out at VC (live, dealer 1891) — so it doesn't get re-walked:**
| Check | Page | VC state |
|---|---|---|
| Control type | CoA account edit | 4403/4703 = `Custom` ✓ |
| Control Number / Control 2 / **Description Mandatory** | CoA account edit | **all OFF** ✓ |
| Disable Postings | CoA account edit | OFF ✓ |
| VI balance $0 → error block | AGS → Auto Posting | **OFF** ✓ |
| Repair Orders Close CP/Internal/Warranty | AGS → Posting Preferences | **Auto-Post** ✓ (RO Adjustment = Draft; Vehicle Inventory Stock-In = Draft) |
| **Coupons** posting line | Auto-Posting Settings → Templates → RO → Customer Pay → Fees | present ✓ |
| Discount GL accounts declared? | AGS → Auto Posting → **GL Accounts Not Requiring Sales Chain** | ✗ only 4 F&I accounts (`9162/9163/9167/9191`) |
| Sales Chain rows for 4403/4703 | `/accounting/accountingChain/list` | **No rows found** ✗ |
| Account Sub-Type | CoA account edit | **empty** on 4403/4703 |

The last two are the only structural asymmetries left: `4403/4703/4403A` are **`S-Sale` type with no
Sales Chain and not declared in "GL Accounts Not Requiring Sales Chain"** (KB0020992 says that list is
exactly for sale accounts needing no Cost of Sale / Inventory Offset). **Do NOT call this the cause** —
the new JE 123820 posts balanced *with* the gap in place. Present it as a tightening, explicitly
labelled unproven.

**5. "Did Tekion push an update?" — where to look (KB has NO ARC release notes).**
DMS Home → the Release Notes card's **`Read All (N)` is an `<a>`, not a button** — read
`a.getAttribute('href')` → **`/core/release/<24-hex-id>`** (clicking/window.open-hooking both fail;
the drawer won't expand). Department tabs are `<li>`; the filter also works as a URL param:
`?departmentId=ACCOUNTING|CORE|SERVICE|SALES|PARTS|TEKION_PAY|ANALYTICS|COMMUNICATIONS|PERMISSIONS`.
**ARC September 2026 release: `Released On: Sep 16, 2026`** — 23 items / 9 depts. Accounting carried
exactly ONE item (*Clear Non-Mandatory Fields on General Ledger Accounts* — Account Sub-Type /
Department / FS Group / FS Sub-Group); Core 4 (printer+scanner logs, Enterprise Security Settings,
new Get Help widget, "All" in employee-view dealer dropdown); Sales 3 (Total Vehicle Price in
Desking/Deal Sheets, TVP in Vehicle Inventory, CA CARS Act compliance setup); Parts 1 (False Hold
icon); Tekion Pay 1 (electronic paper-check); Analytics 1; Communications 1; Permissions 6.
**Nothing about journal entries, auto-posting, coupons, discounts or GL posting.** So the 9/16 release
is *timing-consistent* with "failures before / works after" but is **not** a documented posting fix —
say that plainly instead of implying causation.

### Route + mechanics discoveries that cost turns here
- **Accounting Global Settings = `/accounting/accountSettings`** (KV0020992's tab list: Journal Entry
  Settings · Auto Posting · Schedules · Reconciliation Accounts · General Settings). Add to §1 dead
  ends: `/accounting/global-settings`, `/accounting/globalsettings/list`,
  `/accounting/accounting-global-settings`, `/accounting/settings/global`, `/accounting/settings`,
  `/accounting/accountSettings/...` variants **all silently redirect to `chartOfAccounts/list`** —
  assert `location.href` every time.
- **Finding a screen's route from the KB (reusable, fast):** open the KB article that links it, then
  `[...document.querySelectorAll('a')].map(a=>a.getAttribute('href')).filter(h=>/tekioncloud/.test(h))`.
  That's how `/accounting/accountSettings` and `/accounting/accountingChain/list` were found after
  URL guessing failed.
- **Table-level "expandable search" (CoA / Sales Chain / JE list):** a magnifier icon at the RIGHT of
  the table header (~x1159 on CoA, x1224 at VC Sales Chain, x1111 on the JE list) expands an input
  whose placeholder is exactly **`Search...`**; type via native value-setter + `input` + Enter.
  The global box placeholder is **`Search here...`** and does NOT filter these tables — typing there
  returns the unfiltered list and reads as a false negative. Sales-Chain search for `4403`/`4703`/
  `DISCOUNT` correctly returned *No rows found*; the CoA search returns whole **rows** (Account Type,
  Sub-Type, Balance, Control Type, **Count**, Department, Modified Time, Franchise, Active).
- **CoA account edit URL:** `/accounting/chartOfAccounts/dealer/<dealerId>/account/<dealerId>_<acct>/edit`
  — tabs Account Details · Postings · Monthly Balances · Daily Balances; the flag toggles
  (Control Number Mandatory / Control 2 / Description Mandatory / Posting Line Count Adjustment /
  Disable Postings) are `.ant-switch`/checkbox — read states, never infer.
- **KB SSO re-bootstrap (corrects the older advice):** when `kb_search_scrape.py` returns
  `{"error":"KB not authenticated..."}`, the fix is a single `/navigate` to
  **`https://app.tekioncloud.com/core/knowledge-base/search`** (it runs the SSO handshake in the
  tracked tab and lands on `tekion.service-now.com/sp`). Do NOT chase the ServiceNow login form —
  "Use external login" → User ID → just bounces back. And remember the scraper **hijacks the :9223
  bound page**, so do KB reads before/after DMS DOM work, and re-assert `location.href` after.
- **The "Error" status tab is STICKY across navigations** — before searching the JE list,
  click **`All`** or you get `No Rows Found` on a JE that exists (cost a turn here).

### Mechanics for this diagnosis (each of these cost turns to find)
- **Sweep every coupon's GL split in one loop:** `/core/coupons` lists the codes (read the
  `N Result(s)` list); each edit page is `/core/coupons/edit/<base64(code)>`. Per page regex
  `document.body.innerText` for `\b\d{4}\s*-\s*[A-Z][A-Z0-9 &\/\-'.,()]{3,60}` to get the account
  strings, and read every visible `input` (`"Account Split" = "100.00"` per side). 11 coupons ≈ 2.5 min.
- **PITFALL — never split "scrollIntoView + read coords" from the `/mouse` click.** Coords go stale
  between evals (asked for `Repair Order` at y748; the real element was at y476 → the click silently
  did nothing and the page never switched). Compute the centre AND dispatch in the SAME `/eval`:
  `el.scrollIntoView({block:'center'}); const b=el.getBoundingClientRect(); const x=..,y=..;
  const tgt=document.elementFromPoint(x,y)||el;
  ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t=>tgt.dispatchEvent(new
  MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y,button:0})));`
  Plain `/mouse` **no-ops** on the Auto-Posting Settings sub-tabs (`Repair Order`, `Customer Pay`)
  and on the GLAM nav; the JS-dispatched sequence works. Return what `elementFromPoint` actually hit
  so you know you got the right node.
- **Terminal guard:** a heredoc / `-c` script string containing `&` is rejected by the tool
  ("uses '&' backgrounding"). Write the script with `write_file` and run the file — bit me on the
  `Part & Accessories` label.
- **`re.escape` + `json.dumps` = a broken JS regex:** `re.escape("Part & Accessories")` emits
  `Part\ &\ Accessories`; the `\ ` survives into the JS string literal as an escaped backslash and
  the regex never matches a single element. Match labels by exact string equality instead.
- **Chart of Accounts `Modified Time` is a nightly balance-recompute stamp, NOT an edit date** —
  on 9/18 every account read `09/18/26 7:22 AM` (even 1188, 1339, 4402…). Never use it to date an
  account's creation or to establish a fix date; use the JE daily series (§6 fix-date rule).
- **KB SSO drops during long DMS sessions:** the KB scraper then returns
  `{"error": "KB not authenticated. ..."}`. Re-run `/home/itadmin/tekion-auth/login.py --force`,
  then click Get Help → Knowledge Base once on :9223 before retrying the KB scrape.

Source artifacts for this case: **`/home/itadmin/tekion-reports/clvw_141821/`** (Chris's forwarded
PDF as received in chat + the extracted JE screenshots). NOTE incoming chat attachments land in
`~/.../cache/documents/` which is WIPED on the daily reset — move them into `/home/itadmin/...`
in the same turn you receive them.

**Reporting framing that landed well with Joe here:** lead with "the discount is never posted into
the auto-posting JE — the entry doesn't balance by exactly the discount — it's NOT a wrong-GL-account
problem: every posting line has an account and there's no blank cell." Then table the two JEs
(id / RO / acct date / debit / credit / balance / discount), then the arithmetic tell
(`gross-revenue − cash-collected = Balance`), then the current queue state, then explicitly separate
**what is proven** from **what is not yet proven** (config vs Tekion) with the single test that
separates them. Joe's ask was literally "don't do anything, just tell me what is wrong" — diagnosis
only, no writes (§5e).

---

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

## 5d. TL (Toyota of Lancaster, 1092) — SO 863805 / JE 877332, 2026-08-29 — the NON-defect bucket

**This is the case that proves not every Error JE has anything wrong with it.** Joe asked about
one SO going into JE error; the reflex was "another mapping gap like SCT/VC." It was not.

JE `877332` — journal `32 - PARTS CASH SALES`, doc type `4 - Parts Invoice`,
`WHOLESALE - Part Sale - 863805-1`, 8/28/26, Jorge Belmontes:
```
2100 ACCTS RCVBLE-CUST      +103.12   control 1322103
4750 SLS-PARTS WHSL-MECH    -103.12
6750 C/S-PARTS WHSL-MECH     +96.85
2410 PARTS-TOYOTA (EX TIRES) -96.85
Debit 199.97 = Credit 199.97 · Balance $0.00 · all 4 GLs resolved · NO blank line
```

**How it was ruled out as a defect (reuse this method):**
1. **Diff against posted siblings with matching scope** — same customer control (`1322103`), same
   day, same journal, same doc type. Found 7 posted twins (`877289 877291 877293 877299 877305
   877329`) that are byte-for-byte the same shape, same accounts, same control type, same `count`
   flags. If a posted twin exists with an identical structure, it is **not** a config gap.
2. **Ask Tekion's own validator.** The Aug-2026 "Error Detection and Resolution" feature exposes an
   **`/error-report`** endpoint on the JE — it returned **`errorCount: 0`** for 877332. Tekion itself
   cannot name a defect on the record. Always hit this before writing a diagnosis; it's the fastest
   discriminator between "bad record" and "failed to post."
3. **Look at the posting-batch timeline.** Errors and successes were interleaved second-by-second:
   `10:15:33 ERROR 877282 · 10:16:27 POSTED 877285 · 10:16:51 ERROR 877287 · 10:17:27 POSTED 877289
   · 10:24:21 ERROR 877309 · 10:30:02 POSTED 877329 · 10:30:17 ERROR 877332`. Interleaving = a
   per-transaction failure on Tekion's posting service, **not** an outage and **not** a config gap
   (a config gap fails 100% of the matching sale type, deterministically). That day: 21 wholesale
   parts JEs failed, 45 identical ones posted.

**Conclusion + remedy:** the 21 are valid entries that fell over on Tekion's side → **just repost**.
Open the JE → tick **"Perform action and move to next Journal Entry"** (bottom left) → Submit,
which chains straight to the next error. **Change no GL account on these.** A repost that fails
again on an untouched entry is the proof for the Tekion ticket.

**Full TL error queue that day (29 open and still growing — 6 appeared during the session):**

| # | Bucket | Real defect? |
|---|---|---|
| 21 | Wholesale parts sales, journal 32 (incl. 877332) | **No** — balanced, mapped, `errorCount 0` → repost |
| 5 | `IMBALANCE_TRANSACTION` — ROs 398883, 397786, 398859, 396920 + Warranty Credit Memo 874332 ($125,525.71) | **Yes** — Dr ≠ Cr, lines truncated → accounting rebuilds |
| 3 | `COST_CENTER_NOT_FOUND` — internal ROs 398649, 398467, 394780 | **Yes** — cost centre `66abf46265ab9216a9e72a0a` unmapped, line-1 GL is `null` |

**Escalation packet for a Tekion ticket** (this framing is what makes it undeniable): pair
**877332 (ERROR)** against **877329 (POSTED)** — same customer, same journal, same doc type, same
four GL accounts, **15 seconds apart**, and Tekion's own error-report returns `errorCount: 0` on
the failed one.

### Pull the JE from the accounting API, not the DOM
This whole diagnosis was done read-only against the accounting API (captured axios headers replay
from plain urllib, same as the other internal Tekion endpoints). Much faster than the virtualized
list + react-select scraping in §2–3, and it gives you `count` flags, control numbers, error codes
(`IMBALANCE_TRANSACTION`, `COST_CENTER_NOT_FOUND`) and the `/error-report` result that the UI
never surfaces. **Use the API for the diagnosis; use the UI only when Joe needs to click something.**

---

## 5e. HARD RULE — Joe owns the GL writes

Established 2026-08-29 on this case: Jay offered to fire the 21 resubmits; Joe said **"don't want
you to resubmit. What can I do on my end."**

- **Never** resubmit/repost a journal entry, add a GL mapping row, or change accounting setup
  without an explicit, unambiguous go-ahead. Reposting writes to the general ledger.
- The general AUTOMATION MANDATE (run it yourself, ship automation) applies to **reports, scrapers,
  opcodes** — **not** to posting to the GL.
- Offer the action, state plainly that it's a real GL write, then **stop and wait**.
- Default deliverable for accounting issues = **diagnosis + exact click-path Joe can execute**,
  split by who owns each bucket (Joe / accounting / Tekion), plus an offer to draft the vendor ticket.
- Read-only lookups (resolving a cost-centre ID to its name, pulling JE lines) are fine unprompted —
  say "read-only, no changes" so he knows.

---

## 5f. "It went to PREPAID PARTS" — the RO payment-HOLDING account + a missing release JE (BC 1251, 2026-09-18)

Joe's shape: *"I went and looked at journal entries, it went to prepaid parts. I don't know why."*
Store symptom from the business manager: **"shows closed but never closed."**

### The mechanism (verified BC 1251)
Every payment taken on an RO is an **`assetFlowType: CASHIERING_EVENT`** JE named
**`Deposit - Repair Order - <ro#>`** — 2 accounts only: **Dr 225 CASH SALES / Cr <holding account>**.
The invoice JE (`CUSTOMER_PAY - Repair Order - <ro#>` / `INTERNAL - ...`, `assetFlowType: REPAIR_ORDER`,
8–17 accounts incl. revenue + tax + cost-of-sale) then **DEBITS the holding account** to release it.
Healthy RO ⇒ **2 JEs** and the holding account washes to $0. POS/Parts counter sales work identically
(`Deposit - Part Sale - <so#>`, `SO_DEPOSIT`, Dr payment-method acct / Cr holding).

### Where "PREPAID PARTS" comes from — GLAM, not the RO
`/accounting/glaccountmapping/list?module=FO_OTHERS` → left-nav **Fixed Operations → Others (2)** →
card **`Fixed Operations Other`** → **`Fixed Operations (Other)`** table. BC's rows:
```
Service Cash Holding Account | All | 204 - PREPAID PARTS
Parts Cash Holding Account   | All | 204 - PREPAID PARTS
```
That single row IS the answer to "why does it go to prepaid parts" — 204 is BC's service+parts payment
holding account. (SCT instead points Parts Cash Holding at `2045 CASH SALES`, which makes the deposit JE a
self-cancelling wash — same mechanism, different destination. Do **not** call BC's choice a defect.)

### The real defect: the release JE is MISSING
Fast detector — pull the RO's JEs and count:
```python
# POST /api/accounting/u/v2/transaction/m/search with captured headers
b["groupBy"]=[]; b["pageInfo"]={"start":0,"rows":30}; b["searchText"]=""
b["filters"]=[{"field":"refText","operator":"IN","values":["100781"]}]   # works; refId IN [roId] also works
```
- Control RO (94831) → `count: 2` (CUSTOMER_PAY + Deposit). RO 98897 → 2.
- BC **RO 100781 → `count: 1`** = JE **548017** "Deposit - Repair Order - 100781", POSTED, 08/11/26,
  $678.86, accts `1251_225,1251_204`. **RO 100590 → `count: 1`** = JE **549361**, $129.95, 08/14/26.
  ⇒ the print-side held, the customer was billed, but **$808.81 was never released out of 204**.
- ⚠ A JE search that comes back with only the Deposit leg means the *invoice* JE never posted — it is NOT
  in the Error queue (check the Error tab before assuming it failed; failing ones show
  `ACCOUNT_INVALID / "GL Account not found: null"`).

### Scope test (cheap, from the holding account's own postings)
Pull `/api/accounting/u/glAccount/v2/postings/m/search` for the holding acct (`1251_204`,
`durationType: PREVIOUS_MONTH` + `MONTH_TO_DATE`, `rows:200`, paginate `pageInfo.start`), group by
`parentRefText`, and flag every **REPAIR_ORDER ref with only ONE line** (never a matching Dr/Cr pair).
BC Aug–Sep: 946 ROs had the pair, **21 had only one leg**. Cross-check the CoA balance: 204 read
**−$25,786.14** (a *negative asset* = net credits = stranded deposits) with 5282 posting lines,
Dr $1,059,056 vs Cr $1,082,659.
⚠ Contamination: ROs from *today* legitimately show one leg (invoice JE hasn't posted yet), so date
every flagged RO (`scheduledTime`) before reporting it as stranding.

### Reading a JE without the UI
`POST /api/accounting/u/v2/transaction/m/search` (captured from the JE list) returns `data.hits[]` with
`transactionNumber` (= the 7-digit display ID), `description`, `transactionAmount` (DOLLARS),
`glAccountIds[]`, `status`, `metaData.assetFlowType|payType`, `scheduledTime`, `errors{errorCode,errorMessage}`.
Filters that WORK: `refText IN`, `refId IN`, `status IN ["ERROR"|"DRAFT"]`. `refText` searchText is fuzzy —
always also filter `refText IN [<exact>]`. Deep-linking
`/accounting/journalEntry/transactionId/<txnId>/dealerId/<d>/transactionType/AUTO_POSTING/view` renders
**blank** — open the JE from the list or read it from this API instead.
Scope the holding account's own postings with `glAccountId.original IN ["<dealer>_<acct>"]`.

## 6. Reporting to Joe

He wants: the count, the pattern (grouped by order/creator/journal — not 10 unrelated bullets), the
exact blank line quoted against a working posted example, the one-sentence root cause, and the fix
he could apply. Explicitly restate that you changed nothing. If an ID he gave doesn't resolve, say so
and ask what it is rather than guessing (7-digit JE IDs prefix-match, so a 6-digit number will return
a bogus 10-row "hit" — don't present that as the answer).

**Split the queue by OWNER, not just by symptom** (§5d table is the model): which JEs Joe can repost
himself, which need a config row, which accounting has to rebuild, and which are Tekion's defect.
Lead with the largest bucket and its remedy. Offer to draft the vendor ticket text.

**Do NOT lead with a mapping-gap story until you've confirmed a GL cell is actually blank** — SCT
and VC were mapping gaps, TL was not, and pattern-matching to the previous store's root cause is
exactly the kind of confident-wrong answer Joe rejects.

## Related skills
- `tekion-sitemap` — nav base; Accounting URLs above are mirrored there
- `tekion-parts-sales-orders` — the source documents behind PARTS CASH SALES JEs
- `tekion-parts-tax-not-calculating-diagnosis` — sibling "config gap causes wrong posting" pattern
