---
name: tekion-menu-line-sales-by-advisor
description: Build a Tekion "menu sales for closed ROs, by service advisor, grouped by category (Basic/Value/Premium)" report with TRUE menu-line dollars. Use for any month/MTD menu-sales-by-advisor ask, and whenever a menu $ figure looks too low or too high.
triggers:
  - menu sales by advisor
  - closed service menus MTD
  - menu sales grouped by category basic value premium
  - menu dollars look wrong / should be way more than that
  - menu-line dollars vs whole RO dollars
---

# Tekion Menu Sales — by Advisor, grouped by Category

Produces: advisor x category matrix + RO-level detail, PNG + PDF, emailed to Joe.
Verified end-to-end on SCT (dealer 876) August 2026: **226 menus, $145,522.03 pre-tax**.

## THE $ TRAP — read this first

There are two very different "menu dollars" and they differ by ~2x.

`POST /api/service-module/u/reporting/advisor-performance/summary` **filters ROs by
opcode but reports WHOLE-RO dollars.** On RO 578802 it returned **$401.76** — but the
menu operation itself was only **$274.26**. The rest was an unrelated job on the same RO.

- **NEVER** use advisor-performance/summary for menu/opcode-level dollars.
- It IS fine for RO **counts** and for whole-RO metrics (that's what TXM reports use).
- Field name is **`opcodes`** (plural). Passing `opcode` returns 0 rows **silently** —
  no error, just an empty result that looks like "no sales."

Also: the frozen opcode list only defines *which ROs count*. It cannot give you dollars.

## Ground truth for menu-line dollars

Internal, **zero OpenAPI quota**:

```
GET /api/service-module/u/ro/<documentId>
  -> data.jobs[].operations[]
       .opcode
       .totals.totalSaleAmount     <-- INCLUDES SALES TAX
       .totals.laborSaleAmount
       .totals.partSaleAmount
       .totals.feeSaleAmount
       .totals.billingTimeInSeconds
```

All amounts are **CENTS**.

**`totalSaleAmount` includes sales tax.** Report PRE-TAX:

```
pretax = laborSaleAmount + partSaleAmount + feeSaleAmount
residual = totalSaleAmount - pretax
```

- `residual > 0` → sales tax (reconciles to `ro.totals.customerPay.tax`; ~10% of parts at SCT)
- `residual < 0` → a coupon/discount on that operation (17 of 226 rows in Aug)

Do NOT "fix" the residual by adding it back — that inflates the report and double-counts tax.

**No cost fields exist at operation grain** → this yields **SALES only**. Gross profit is
NOT derivable here. Label the report "Sales," never "Gross." (An older renderer said
"Gross" over sales numbers — that's a reporting bug.)

Other field gotchas on the internal RO payload:
- advisor = `ro.allAdvisorIds[0]` (there is **no** `ro.assignee`)
- RO number = `ro.roNo` (**not** `roNumber`)
- customer = `ro.customerInfo`

## Pipeline (all in /home/itadmin/tekion-reports)

```sh
PY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11

# 1. cache roNo -> documentId for the month (OpenAPI search)
$PY sct_ro_idmap.py 2026 8

# 2. fan out internal /ro for menu-opcode ROs -> menu-line dollars
$PY sct_menu_ops_from_ids.py 2026 8

# 3. flatten to renderer row schema (applies the PRE-TAX rule)
$PY adapt_menu_ops_to_rows.py 2026 8

# 4. render PNG + PDF
$PY render_menu_sales_by_advisor_category.py \
     data/sct-menu-rows-2026-08.json 2026-08 "<caveat html or empty>"
```

Step 1 matters: `/repair-orders:search` **still works when `/operations` is
DEALER_QUOTA-blocked (429)**. That's what makes this whole path viable during a quota
outage — you never touch the blocked endpoint.

## MANDATORY: pin the dealer inside the fetch JS

The `:9223` browser **drifts dealers between turns** (found mid-job sitting on BC 1251
when the target was SCT 876). Do not trust `localStorage.currentActiveDealerId`.

Hardcode the headers inside the in-page JS:

```js
const h = Object.assign({}, window.__H);
h.dealerId = "876";
h["tek-siteId"] = "-1_876";
```

Wrong dealer = **400 validationError on every RO** = a silent 0-row report that still
prints a cheerful summary.

## MANDATORY: pace the internal /ro endpoint

It **500s under rapid fire**. A naive tight loop silently lost **166 of 226 ROs** while
printing plausible-looking totals. Required:

- batch **10** ids per `/eval`
- per-id retry with backoff **inside** the page JS, ~250ms nap between ids
- an **outer retry round** over ids that still failed
- assert `errors == 0` and `captured == expected` before rendering

Always print `captured / expected / errors` and stop if they disagree.

## Advisor names

Cache: `data/sct-advisor-cache.json`. Resolve unknowns via OpenAPI:

```
GET /openapi/v4.0.0/users/<id>
  -> userNameDetails.completeNames[nameType=DISPLAY_NAME].value
     userRoleDetails.primaryRole.persona
```

**Caches go stale and mislabel real people.** UUID `1f130e32-51c5-4851-9e53-209ba98a5b24`
was cached as "Any Service Advisor" but is really **Jose Barragan** (25 Aug menu ROs);
`b285082f-e5ba-4e73-a7d5-55e1d48fef7a` = **Michael Parayo**.

SCT has **no genuine Unassigned bucket** — every closed RO has a real advisor. A generic
label ("Any Service Advisor", "Unassigned") in a cache is a **stale mislabel**. Re-resolve
it before publishing, or an advisor gets erased from his own numbers.

## Scope rules (Joe's, definitive)

- Categories: **Basic = `*BNM`, Value = `*VNM`, Premium = `*PSM`**.
- `*BSM` exists in the opcode list but is **dormant (0 sales)** — a 3-category report is correct.
- **ToyotaCare `TEK09*` is NOT a menu sale — EXCLUDE** (Joe ruled 2026-09-02). Consistent
  with excluding TXM/TSC/TAC prepaid maintenance. Aug had 1,037 TEK09 ROs vs 226 real
  menus with **zero overlap** — including them would ~5x the count. Never widen the filter
  to "fix" a low number; find the real capture bug instead.
- Menu filter = the store's frozen `SERVICE_MENU` + `ACTIVE` opcode list
  (`data/sct-tek-maintenance-opcodes.json`, 316 = 79 intervals x 4 tiers).
  Derive per store — do not reuse SCT's list elsewhere.

## Verification before sending

1. `errors == 0` and captured count == expected menu-RO count.
2. Recompute category + advisor totals straight from the rows and diff against the render.
3. `vision_analyze` the PNG: *"what dealership branding is in the header?"* — `logo_0.png`
   and `logo_st.png` are BOTH Stevens Creek Toyota, so a non-SCT report can silently ship
   with SCT branding.
4. Confirm no `NaN`, `undefined`, or generic advisor labels in the output.

## Email

Route through Stacey. Use an **argv list**, not a shell string (parens/quotes in the
message break the top-level `terminal` tool):

```python
subprocess.run(["timeout","175",os.path.expanduser("~/bin/ask-agent"),"stacey",msg],
               capture_output=True, text=True)
```

Demand SMTP (not IMAP append) and a real `Content-Disposition` attachment. **Then verify
independently** — an agent's self-report is not proof. Pull the Gmail app password from
Stacey's himalaya config, `SELECT "[Gmail]/All Mail"`, find the message by
`X-GM-RAW rfc822msgid:<bare-id>`, and confirm all three:

- labels include `\Inbox`
- `FLAGS ()` (unread)
- `Received` header count >= 1  ← proves real SMTP delivery

Aug run verified: Inbox + unread + `Received: 1`, PDF 218,125 bytes byte-exact.

## Known open issue

The nightly closed-MTD master under-captures: Aug had 226 tagged menu ROs but the master
only held 158 (52 lost to an Aug 1-10 quota outage, 16 late/reopened ROs that closed after
the 6PM cron and were never re-swept). Needs a **T+3 re-sweep**, same pattern as the BC
warranty report. This pipeline rebuilds a month correctly from scratch regardless.
