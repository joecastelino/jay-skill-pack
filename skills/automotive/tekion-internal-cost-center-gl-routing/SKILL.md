---
name: tekion-internal-cost-center-gl-routing
description: Answer "which GL account does this internal RO cost center post to / can I change it / can I use account X as the hold instead" for Tekion. Covers Setup Fields → Cost Center Setup, GL Account Transaction Mapping → Fixed Operations → Services-Internal, and how to read the Chart of Accounts control type + sub-type before recommending an account swap. Use for PDI / We-Owe / Policy / Safecat / rental internal-pay routing questions.
triggers:
  - cost center gl account
  - internal ro posts to wrong account
  - PDI cost center
  - can I use account as the hold
  - holding account tekion
  - we owe due bill account
  - setup fields cost center
  - services-internal mapping
---

# Tekion — Internal Cost Center → GL Routing

Joe's recurring question shape: *"RO 58xxxx is going to PDI, 4440 — what's wrong?"* /
*"Can I set cash sales 2045 as the hold and forgo the holding account?"*

Two SEPARATE config layers control this. Confusing them is the #1 way to give a
wrong answer:

| Layer | Screen | What it defines |
|---|---|---|
| 1. Cost center **exists** | Accounting Settings → **Setup Fields** → *Cost Center Setup* → **Repair Order – Internal** | The picklist of names an advisor sees in Manage Splits (e.g. `PDI - 2211`, `We Owe / Due Bill - 3042`, `Safecat 5450`). Also the **Enable Control / Enable Control 2** checkboxes that make those RO fields editable. |
| 2. Cost center **routes** | **GL Account Transaction Mapping** → Fixed Operations → **Services** → *Services-Internal* | Rows of `Department · Make · Pay Type · Service Type · Customer Tax Status → GL Account`. The **Service Type** column is where the cost center lands. |

**The account number embedded in a cost center NAME is a human convention only.**
`PDI - 2211` is just a label someone typed. Do NOT infer routing from it — read the
Services-Internal mapping rows.

## Step 1 — Read the Chart of Accounts FIRST (30 seconds, via API replay)

Never recommend an account swap without its **type / sub-type / control type /
control-mandatory** flags. Fastest path — arm an XHR hook on
`/accounting/chartOfAccounts/list`, capture the app's own `glAccount/list` call, then
replay it in-page with a `searchText`:

```js
// after page load, hook XHR (see persistent-browser-server skill for the hook pattern),
// SPA-nav away and back (history.pushState + PopStateEvent) to fire the call,
// then grab window.__cap[0] = {u, m, h, b}
(async()=>{
  var c=window.__cap[0], h=Object.assign({},c.h), out={};
  for (const q of ['2045','2211','3042','4440']) {
    var body=JSON.parse(c.b); body.searchText=q; body.pageInfo={start:0,rows:25};
    var j=await (await fetch(c.u,{method:'POST',headers:h,body:JSON.stringify(body)})).json();
    out[q]=(((j.data||{}).data||{}).accountList||{}).hits||[];
  }
  return JSON.stringify(out);
})()
```
Returns `accountNumber, accountName, accountTypeId, accountSubTypeId, controlField,
controlNumberMandatory`. **Do NOT type into the page search box in a loop** — each
keystroke round-trip took ~5s and the innerText scrape returned stale rows that looked
like every query matched everything (the top-of-list rows never change). That false
result nearly produced a wrong answer.

**SCT 876 reference (verified 2026-08-24):**

| Acct | Name | Type | Sub | Control | Ctl# mand |
|---|---|---|---|---|---|
| 2045 | CASH SALES | ASSET | **CA – Cash** | REFERENCE | Yes |
| 2211 | PDI | ASSET | – | **VIN_LAST_6** | Yes |
| 3042 | ACCESSORIES DUE | LIABILITY | – | VEHICLE | Yes |
| 4440 | SLS PRE-DEL SRV-TOY | **SALE** | – | CUSTOM | No |

## Step 2 — Read Setup Fields → Cost Center Setup

`/accounting/setupFields` (camelCase — every other spelling silently lands on
chartOfAccounts/list). Click the **Cost Center Setup** tab (leaf ≈582,158), then click
the **expand caret** for *Repair Order – Internal* at ≈**(720,260)**.

Caret hit-testing note: locating the caret by text and clicking `x-140` did NOT work.
The reliable move was `/screenshot` + `vision_analyze` asking for caret coordinates,
then `/mouse` the returned point. Remove `.ant-notification,[id*=pendo],[class*=pendo]`
first — toast notifications from other users' ROs swallow the click.

SCT *Repair Order – Internal* list: `4403 Our Rental Discounts`, `4403A LYFT`,
`Lyft Ride`, `Safecat 5450`, `RENTALS 8160`, `PDI - 2211`, `New Car Policy - 7111`,
`Used Car Policy - 7112`, `Service Dept Policy - 7113`, `Parts Dept Policy - 7115`,
+ **View More** (appears past 10 entries — always click it, the list is longer than it looks).

## Step 3 — Read GL Account Transaction Mapping

`/accounting/glaccountmapping/list` → left-nav **Fixed Operations** → **Services (3)**
→ **Services-Internal**. Each accordion leaf is a `LI`/`DIV` — filter with
`children.length<=1` and match on the exact label INCLUDING its count suffix
(`'Services (3)'`, `'Others (2)'`). A strict `children.length===0` filter returns `[]`.

SCT Services-Internal (verified 2026-08-24):
```
03 - SERVICE          | All | Internal Pay | Transportation Policy | All | 7113 POLICY ADJUSTMENT-SVC
03 - SERVICE          | All | Internal Pay | Rental Due Bill       | All | 3042 ACCESSORIES DUE
03 - SERVICE          | All | Internal Pay | Sublet                | All | 4460 SUBLET
03 - SERVICE          | All | Internal Pay | PDI                   | All | 4440 SLS PRE-DEL SRV-TOY
03 - SERVICE          | All | Internal Pay | All                   | All | 4430 SLS CUS MECH MAINT LBR-TOY FLT   <-- catch-all
7 - Used Car Dept     | All | Internal Pay | Sublet                | All | 4460 SUBLET
7 - Used Car Dept     | All | Internal Pay | PDI                   | All | 4440 SLS PRE-DEL SRV-TOY
7 - Used Car Dept     | All | Internal Pay | All                   | All | 4430 SLS CUS MECH MAINT LBR-TOY FLT
```
There is a **`Service Type = All` catch-all row per department**. Any cost center with
no explicit row falls to `4430`. That's usually the real answer to "why did it post
there" — not a broken mapping.

## Step 4 — Answering "can I use account X as the hold?"

Mechanically Tekion will let you map an internal cost center to any ACTIVE GL account.
The judgment call is three checks — run all three before answering:

1. **Sub-type.** `CA – Cash` accounts (2045 CASH SALES) feed **Bank Reconciliation**.
   Routing internal RO charges there puts non-cash activity in a cash account and
   breaks the rec. This is a structural objection, not a style preference — say so.
2. **Control type.** Swapping `VIN_LAST_6` (2211 PDI) for `REFERENCE` (2045) loses
   per-unit VIN tracking, and `controlNumberMandatory` is still `true` — you don't
   escape entering a control, you just enter a less useful one.
3. **Is a hold even needed?** If the credit side already points at a **SALE**-type
   account (4440), the revenue is already in P&L. "Skip the holding account" may mean
   the debit/offset should go to expense/COS, not that a hold account should become cash.

## RESOLVED 2026-08-26 — the cost-center record carries NO GL account

Previously listed as a known gap. **Settled by opening the dialog at BC (1251):**
Setup Fields → Cost Center Setup → *Repair Order – Internal* → row kebab
(`[data-test-id*=optionMenuKebabIcon]`, right edge ≈x1201) → **Edit**. The modal
contains exactly three fields: **Cost Center Name · Enable Control · Enable Control 2**.
No GL account field, matching KB0010144.

**Therefore: cost-center names like `PDI 263A` / `Used Car INV 240` / `Service Dept
Policy 67D` are labels only.** ALL internal GL routing comes from the
Services-Internal mapping rows. The cost center controls only which control number
(VIN, stock#, etc.) is captured on the RO.

Kebab menu offers only **Edit / Deactivate** — there is no delete.

The **Add** dialog (icon-add-circle at ≈1203,260 on the section header) is identical:
title = the section name ("Repair Order - Internal"), fields = Cost Center Name* ·
Enable Control · Enable Control 2, buttons Cancel/Add. **No Department field, no GL
field.** Confirmed at BC 2026-08-26. So "set the account on the cost center" is not a
thing Tekion supports — the cost center is a control-number label only.

Likewise the **Service Settings → Internal Pay** Cost Center/Split grid has just two
columns (Cost Center · Split) — no Department column, so there is exactly ONE store-wide
default cost center, not one per department.

## DEPARTMENTS exist — but they are NOT a cost-center or Services-mapping dimension

Joe will (correctly) push back if you say "there is no department." There IS one:
**Setup Fields → GL Accounts Setup → Department** (leaf ≈250,260). BC (1251) list:
```
U - UCD (Service)          P - PDI (Service)        F - Parts (Parts) [Default]
A - New Vehicle (Vehicle Sales) [Default]           E - Body Shop (Service)
B - Used Vehicle (Vehicle Sales)                    D - Service (Service) [Default]
X - Express Service (Service)                       O - Accounting Office (Business Office) [Default]
```
Row kebab (≈x601) → **Edit** → modal fields = **Code · Label · Department Type ·
Set as Default**. NO GL account field. So a Department is a tag, not a router.

Where Department IS usable as a mapping dimension: **Others → Fixed Operations Other**
(cols: item · **Department** · GL Account; e.g. `Other supplies | D - Service | 61D`,
`Other supplies | F - Parts | 61F`). The Department react-select there lists all 9 depts
incl. `U - UCD (Service)` — proof the dimension exists app-wide.

Where Department is NOT available: **Services → Service - Internal at BC** — that table
is Pay Type · Service Type · GL Account only, and the "Create GL Account Mapping Rule"
modal's first Rules dropdown offers ONLY **Pay Type** and **Sale Type (Fixed Ops)**
(verified scrollHeight = 2 items, not truncated). So BC internal service work cannot be
routed by department; it routes by **Service Type**, and BC has a Service Type literally
named **"Used Car Department"**.

Department also appears as a read-only attribute column on **Chart of Accounts**
(`/accounting/chartOfAccounts/list`, 1,009 accounts at BC) — e.g. 460A→`D - Service`,
467→`F - Parts`. That is the account's own department tag, downstream of routing.

Journal-level routing is yet another layer: **Journal Mapping**
(`/accounting/journalMapping/list`, button top-right of GLAM). BC has
`Repair Order - Internal | Workflow: Service + Pay Type: Internal Pay → 34 - INTERNALS`.
Its rule dims are Workflow/Pay Type/Deal Type/OEM — again no Department.

## The 3 levers for "change the default internal account for department X"

1. **Credit/sale side — labor** → GL Account Transaction Mapping → Fixed Operations →
   Services → **Service - Internal**. Add a row for that Service Type; otherwise it
   falls to the `Pay Type = Internal Pay, Service Type = All` catch-all.
2. **Credit/sale side — parts** → …→ **Part & Accessories** → **PARTS - REPAIR ORDER**.
   Separate table, separate catch-all. Changing labor does NOT move parts.
3. **Default cost center on the RO** → Service Settings (`/service/settings/ro-settings`)
   → left-nav **Internal Pay** → *Cost Center / Split* grid (default row + 100 split).
   Also holds "Set limit for Internal Pay on RO Level" and "Default Internal Labor Rate".

Always ask which of the three Joe means before touching anything.

## BC / Blackstone Chevrolet Cadillac (1251) — verified 2026-08-26

**Column set differs per store.** SCT shows Department · Make · Pay Type · Service Type ·
Tax Status · GL Account. **BC Service-Internal shows only Pay Type · Service Type ·
GL Account** — no Department/Make columns at all, so BC cannot route by department;
it routes by **Service Type**.

Service - Internal (mapping id `6287af0bd20c290007476bf1`):
```
Internal Pay | Sublet           | 466  - SUBLET REPAIRS
Internal Pay | Service Contract | 460B - SERVICE CONTRACTS CUSTOMER LABOR
Internal Pay | PDI              | 464  - NEW VEHICLE INSPECTION LABOR
Internal Pay | MPVI             | 460A - CUSTOMER LABOR - CARS & LIGHT DUTY TRUCKS
Internal Pay | All              | 463  - INTERNAL LABOR - MECHANICAL   <-- catch-all
```
PARTS - REPAIR ORDER (cols: Pay Type · Service Type · Source Code · Sale Type · GL):
```
Internal Pay | All            | All            | Repair Order | 481 - PARTS-INTERNAL  <-- catch-all
Internal Pay | All            | 500 - TIRES    | Repair Order | 490 - TIRES
Internal Pay | All            | 600 - GM TIRES | Repair Order | 490 - TIRES
Internal Pay | All            | 110 - BULK OIL | Repair Order | 491 - GAS, OIL & GREASE
Internal Pay | All            | 111 - ACCESSORIES | Repair Order | 484 - ACCESSORIES
Internal Pay | XPRESS SERVICE | (bulk oil/acc/tires rows) …
Internal Pay | XPRESS SERVICE | All            | Repair Order | 481 - PARTS-INTERNAL
Internal Pay | Sublet         | All            | Repair Order | 466 - SUBLET REPAIRS
```
BC **Service Types** (`/ro/opcode` tab rail = same list the mapping dropdown offers):
All · Sublet · Service Contract · PDI · Main Service · Maintenance Service ·
Service Interval Menu · XPRESS SERVICE · ACCESSORIES · MPVI · **Used Car Department** ·
Service Catalog · Service Menu · Cadillac Express Shop.

→ **UCD ("Used Car Department") has NO explicit row on either table**, so UCD internal
work currently posts labor to **463** and parts to **481** via the catch-alls.
Fix = add `Internal Pay | Used Car Department | <acct>` rows.

⚠️ **Adding that row is only HALF the fix — verify opcode coverage first.** Because BC
routes by Service Type, the new row only captures opcodes actually *tagged* to the
"Used Car Department" service type (`62e806c31e9d980006b3e8ef`). A 90-day census of
BC's UCD department (391 closed ROs) found only **6 of 27** opcodes tagged to it
(UCDETAIL/UCSAFETY/UCSMOG/UCEV/UCFRONTLINE/CERTSAFETY); the other 21 — ALIGN, 4ALIGN,
TIRE1/2/4, FBRAKE, RBRAKE, BELT, BALANCE, AGMBATTERY, CABIN, LOF6, CADTIRE1-4 — are
tagged to XPRESS SERVICE / Main Service / Maintenance Service and would silently keep
posting to 463/481. Most of them are ALSO used heavily outside UCD, so they can't just
be retagged. Run the census before promising Joe the mapping row "captures UCD" —
skill **`tekion-department-opcode-census`**.

BC *Repair Order – Internal* cost centers: 460L Lyft · PDI 263A · Chevy New Car INV 231 ·
Chevy New Truck INV 237 · Used Car INV 240 · Used Truck INV 241 · WeOwe/Due Bill 305 ·
New Car - Lot Damage (inactive) · Used Car Lot Damage (inactive) · Service Lot Damage ·
+View More (Advertising, Company Vehicle Parts 51F, Company Vehicle Service 51D, …).
BC Service Settings → Internal Pay default cost center = **Service Dept Policy 67D**,
split 100; Default Internal Labor Rate **$219.00**; RO-level internal limit $1.00.

## Verified click-path (BC, :9223)

```
/accounting/glaccountmapping/list
  left-nav "Fixed Operations" @92,433  →  "Services (3)" @92,504
  main-panel accordion label "Service - Internal" @547,298   (expands read-only rows)
  pencil on that header row @1200,297  →  /glaccountmapping/<id>/edit?additional={"isCreateMode":false}
    edit grid: per-row Pay Type / Service Type / GL Account ant-v5-selects
      + per-row icon-add-circle @x1201 (adds a row below) and a delete icon
      Cancel @1105,689 · Confirm
  "Add" @1211,168 → modal "Create GL Account Mapping Rule"
      Name* + Rules: [dim] > [value], first Select offers ONLY
      "Pay Type" and "Sale Type (Fixed Ops)"; Cancel @795,538 / Continue
```
Left-nav coords shift once a section is expanded — re-read them each time; the
`Part & Accessories` leaf lands at ≈226,341 after Services collapses.

Screenshot note: `:9223/screenshot -o file` writes **JSON** `{"screenshot":"<b64>"}`,
not a PNG. `vision_analyze` rejects it ("Only real image files are supported") —
base64-decode first.

## KB references (via `tekion-kb-search-scrape`)
- **KB0010144** — ACCOUNTING SETTINGS: Setup Fields – Cost Center Setup (the 4 categories, field-by-field)
- **KB0025864** — how to add a cost center for a PDI
- **KB0022812** — HOW TO: Add a New Repair Order – Internal in Setup Fields
- **KB0018143** — add a cost center for billing an internal repair order
- **KB0010432** — HOW TO: Close an RO – Internal Pay

## Pitfalls
- **Shared browser contention.** :9223 is Joe's lane. Toast notifications for unrelated
  ROs ("Repair Order - 398391 …", other dealers) mean someone else is driving — for
  read-only accounting recon use **:9225** and stop if you see the page navigate on its
  own. Note :9225 can be sitting on a different dealer — assert `location.href` AND the
  header store name before trusting any number.
- **Silent redirects.** Bad accounting URLs land on `chartOfAccounts/list` and LOOK
  successful. Always read back `location.href` after `/navigate`.
- **In-page `fetch` with `localStorage.t_token` 500s** "Token doesn't exist or is invalid"
  on `/api/accounting/...` — the app's axios interceptor adds headers a bare fetch can't
  replicate. Capture real headers via XHR hook and replay those.
- Cost-center dropdown on the RO itself (Manage Splits) is the *third* view of this data —
  it shows only cost centers valid for that pay type. Enumerate it by `/mouse`-clicking
  the `.ant-select` then reading visible `.ant-select-dropdown` innerText.

## Joe's vocabulary + posture (2026-08-25)

- **"the glam"** = **GL Account Mapping** (Accounting → GL Account Transaction
  Mapping). When he says "I fixed the glam," he means the Services-Internal
  mapping rows — verify them, don't re-derive from cost-center names.
- He **dislikes holding/suspense accounts** and will propose skipping them
  ("I DON'T WANT a holding account, I want to setup cash sales as the hold").
  Correct response shape: say plainly whether it's mechanically possible (usually
  yes), then give the structural objection with the *reason* (2045 is `CA – Cash`
  → breaks Bank Rec; loses `VIN_LAST_6` per-unit tracking; control# still
  mandatory so nothing is saved), then offer the clean alternative (if the credit
  is already a SALE account, the debit belongs in expense/COS, not cash).
  Don't just comply, and don't just refuse.
- Close with the **known gap** (debit binding: cost-center record vs mapping row)
  and ask **which side he wants moved — debit/hold or credit/sale** — before
  touching anything.

## Session / auth note

`~/.hermes/shared/tekion-session.py` **does not exist** (it resolves under Jay's
profile home). Use:
```bash
cd /home/itadmin/tekion-auth && \
  /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 login.py --check
```
Bare `login.py` reuses a live session ("session ALIVE — reusing" → `REUSED`)
rather than re-logging in — safe to call before accounting recon.

## Related skills
- `tekion-department-opcode-census` (which opcodes a department actually uses, and
  whether a Service-Type mapping row will really capture them — run this BEFORE
  promising a GL change covers a department)
- `tekion-sitemap` (Accounting URL table + App Grid coords)
- `tekion-journal-entry-error-diagnosis` (when the JE actually errors)
- `tekion-kb-search-scrape`, `persistent-browser-server`
