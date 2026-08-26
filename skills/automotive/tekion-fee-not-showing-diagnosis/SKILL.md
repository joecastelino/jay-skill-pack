---
name: tekion-fee-not-showing-diagnosis
description: Diagnose "the store can't see / isn't getting charged fee X" in Tekion — e.g. "SCT isn't seeing fees 1TIRE 2TIRE 3TIRE 4TIRE". Covers the Fee Management v3 API (list + per-fee detail), the ADD_TO_RO ("Allow to Add at RO Level") flag that controls whether a fee appears in the RO fee dropdown, opcode→fee attachment, and how to prove whether a fee is actually landing on real ROs. Use for any Tekion fee visibility, fee-not-auto-applying, or fee-attach-rate question.
triggers:
  - isn't seeing fees
  - fee not showing up
  - fee not being charged
  - can't add fee to RO
  - tire fee / disposal fee / hazmat fee missing
  - why isn't fee X applying
---

# Tekion "fee not showing / not charging" diagnosis

## When to use
A store says a fee code is missing, can't be selected on an RO, or isn't being
billed. Distinct from `tekion-ro-fee-waiver-investigation` (that one is
"someone is deliberately zeroing a fee"). This one is **config + attach-rate**.

**Wrong skill?** If the complaint is "fee X is *charging tax* / shouldn't be
taxed", use **`tekion-fee-charging-tax-diagnosis`** instead — that's the new
Parts Tax Code Setup leaving `pricingSetup.active[].taxConfigs` empty, and it has
a one-call sweep that answers it. It also documents the
`partTrade/u/sale/order/search` pagination trap (`page.from` is IGNORED — every
page returns the same 20 rows, so multi-hundred-order scans silently lie).

**Also wrong skill?** If someone wants a **NEW fee code created for a service-
contract deductible or hardware overage** (CVSC / Fidelity / extended warranty),
STOP — use **`tekion-vsc-deductible-vs-fee-code`**. The deductible is a native
field in the job's Pay Type Split grid, bound to the contract record; a fee code
breaks claim reconciliation. It is usually already being collected on the covered
job while a $0.00 "CUSTOMER TO PAY DEDUCTABLE" placeholder job makes it look
like it isn't.

## ⚠️ THE #1 TRAP — `/ro-fees` is NOT the whole story

`GET /repair-orders/{roId}/ro-fees` returns **only RO-LEVEL fees**.
Fees attached to an **opcode** land at **JOB level**:

```
GET /repair-orders/{roId}/jobs/{jobId}/job-fees   → data.roFees[]   ← same key name!
```

Note the response key is `roFees` on BOTH endpoints — easy to think you already
checked. In this session, scanning 6,000 SCT ROs with only `/ro-fees` produced
the confident-but-WRONG conclusion *"zero CATIR* tire fees have ever posted to
any RO."* Re-running the identical scan at job level showed CATIR2 on 45/48,
CATIR3 5/5, CATIR4 87/96 — the fees were working fine all along.

**Rule: any "is fee X actually billing?" question requires a JOB-level scan.**
Only manually-added / RO-wide fees (LYFTCONC, RENTAL, StorageFee) show on
`/ro-fees`.

## The three independent things that must all be true

| Layer | What it controls | How to read it |
|---|---|---|
| 1. Fee master `active` | Fee exists at all | `fee/v3/search` → `active`, `dealerFeeStatus` |
| 2. `ADD_TO_RO` override flag | Whether the fee appears in the **RO Add/Edit Fee dropdown** (manual add) | `fee/v3/details` → `pricingSetup.active[].overrideFlags` |
| 3. Opcode attachment | Whether the fee **auto-applies** when an opcode is billed | opcode search → `fees[]` / `feecodes[]` |

A fee can be ACTIVE and correctly priced and still be invisible to advisors
(ADD_TO_RO off) *and* still auto-apply fine on opcodes. Diagnose all three —
the store's complaint usually maps to exactly one.

`ADD_TO_RO` = KB's **"Allow to Add at RO Level."** Reference stores that have it
ON at SCT: `CABATT`, `SS`, `StorageFee`, `LYFTCONC`. OFF: all `CATIR*`,
`LOFDISP`, `TDF*` (these are opcode-driven only).

## Fee Management API (internal, verified SCT 876, 2026-08-20)

Page URL is **`/core/fees`**. `/service/settings/fees`, `/core/fee-management`,
`/fee-management`, `/fees` all render a BLANK page or bounce to `/home`.

```js
// 1) full fee list (66 fees at SCT)
POST /api/service-module/u/fee/v3/search?withNoDealers=false&locale=en_US
{pageInfo:{start:0,rows:50}, sort:[{order:'DESC',field:'modifiedTime'}],
 searchText:null, filters:[]}
→ data.hits[]  // paginate by bumping start by 50

// 2) per-fee full detail (REQUIRED for real overrideFlags)
POST /api/service-module/u/fee/v3/details?locale=en_US
{fees:[{feeCode:'CATIR4', id:'<id from search>'}]}
→ data[0].pricingSetup.active[].{overrideFlags, feeConfigs[].salePricingDetail, excludeOpcodes}
```

**CRITICAL:** the `overrideFlags` field on the **search** result is a legacy/empty
array — it reports `ADD_TO_RO=false` for *every* fee including ones that
demonstrably have it on. You MUST call `fee/v3/details` and read
`pricingSetup.active[].overrideFlags` for the truth. Same for the older
`configs[]` block — `pricingSetup` is the live one, `configs` is legacy.

`salePricingDetail.flatPrice` here is in **DOLLARS×100? No — it is the literal
displayed amount in cents**: CATIR4 `flatPrice: 700` = $7.00, LOFDISP `137` =
$1.37. Cross-check against a real `job-fees` `saleAmount` (also cents) before
quoting dollars to Joe.

Dead ends (all 404): `/fee/search`, `/fees/search`, `/feemanagement/*`,
`/fee-management/search`, `/fee/all`, `/fee/list`, `/dealer-fee/search`.
`/fee/bootstrap` returns `{status, errorDetails}` — useless.

## Opcode→fee attachment

```js
POST /api/service-module/u/opcode/search
{pageInfo:{start:0,rows:20}, searchText:'<OPCODE>',
 sort:[{order:'DESC',field:'createdTime'}], filters:[],
 nextPageToken:null, searchFields:['OPCODE']}
→ data.hits[].{fees:[{feeCode,id}], feecodes:[...]}
```
Filter `hits` by exact `x.opcode === CODE` — search is fuzzy and returns cousins.
`GET /api/service-module/u/opcode/{ID}_{dealerId}` and `/opcode/details/*` both
**500** — search is the only read path.

## Auth (`window.__H`) — rebuild after EVERY hard nav

The XHR-hook approach to capture headers does NOT survive `/navigate`. Build
headers straight from localStorage instead; re-run this after each navigation:

```js
(()=>{const g=k=>localStorage.getItem(k);window.__H={
"Accept":"application/json, text/plain, */*","applicationId":"ARC_NA","clientId":"web",
"dealerId":g('currentActiveDealerId'),"locale":"en_US",
"original-tenantid":"americanmotorscorporation","original-userid":g('__user_id'),
"productIds":"ARC","program":"DEFAULT","roleId":g('currentActiveRoleId'),
"subApplicationId":"US","tek-siteId":g('currentActiveSiteId'),
"tekion-api-token":g('t_token'),"tenantname":"americanmotorscorporation",
"userId":g('__user_id'),"Content-Type":"application/json"};return 'ok'})()
```
Then call the APIs with in-page `fetch(..., {headers:window.__H})`. Verify
`window.__H.dealerId` matches the target store before trusting any result.

## Method

1. **Pull the full fee list** → find every fee whose code/description matches the
   complaint. Expect **legacy duplicates**: at SCT the codes literally named
   `1TIRE/2TIRE/4TIRE` ("CALIFORNIA TIRE FEE") are INACTIVE (killed 9/16/2022 at
   CDK conversion) and were replaced by `CATIR1–4` ("CA Tire Tax"). Same pattern:
   `TIRDIS1-4` → `TDF1-4`, `TD` → `TDF*`. **The store often complains using the
   dead code's name.** Always list active + inactive and show the mapping.
2. **Pull `fee/v3/details`** on the live codes → read `ADD_TO_RO`, price,
   `excludeOpcodes`, pay-type eligibility filters.
3. **Read opcode attachment** for every plausible opcode (don't assume — at SCT
   `1TIRE`=mount&balance-1 and `TIRE1`=replace-1-tire are DIFFERENT opcodes and
   only one had the fee).
4. **Prove it against real ROs with a JOB-LEVEL scan** (see trap above).
   ThreadPoolExecutor(12-14), ~65s for 262 candidate ROs. Report an **attach
   rate per opcode**, not a yes/no.
5. **Bucket misses by RO number / date** to distinguish "always broken" from
   "broke recently."

## Worked example — SCT tire fees, 2026-08-20
Complaint: *"SCT isn't seeing fees 1tire, 2tire, 3tire, 4tire."*
- Codes `1TIRE/2TIRE/4TIRE` = INACTIVE legacy; no `3TIRE` fee ever existed.
  Live = `CATIR1` $1.75 / `CATIR2` $3.50 / `CATIR3` $5.25 / `CATIR4` $7.00, all ACTIVE.
- **Root cause of "can't see them": ADD_TO_RO is OFF on all four CATIR fees** →
  they never appear in the RO Add/Edit Fee dropdown. (CABATT/SS/StorageFee have
  it ON, which is why those are visible.)
- Bonus finding from the job-level scan: opcode `1TIRE` has **no fee attached**
  (`fees:[]`) while 2TIRE→CATIR2, 3TIRE→CATIR3, 4TIRE→CATIR4, TIRE1→CATIR1 all
  are. Attach rates: 1TIRE **5/112**, 2TIRE 45/48, 3TIRE 5/5, 4TIRE 87/96,
  TIRE1 3/4. ~107 uncollected CA tire fees — state-mandated pass-through, so an
  audit exposure, not just revenue.
- Tire *disposal* is billed as a **part line** (`TDF`, $20 on the operation's
  parts), NOT as a fee — don't confuse it with the `TDF*` fee codes.
- Proposed fix: (1) turn ON "Allow to Add at RO Level" on CATIR1-4;
  (2) attach CATIR1 to opcode `1TIRE`.

## Misc gotchas
- `/screenshot` on the `:9223` server returns JSON `{"screenshot": "<base64>"}`,
  not raw bytes — decode before writing, or `vision_analyze` rejects the file
  with "Only real image files are supported."
- `/eval` payload key is **`js`**, not `expression`. A syntax error or a
  bare-`return`-at-top-level returns HTTP **500** from the server (not a JS
  error) — always wrap in `(()=>{...})()` or `(async()=>{...})()`.
- `document.body.innerText` on many Tekion settings pages returns only the
  nav chrome (~350 chars) even when the page is fully rendered — the content is
  in canvas/shadow subtrees. Don't conclude "page is blank" from innerText;
  screenshot + `vision_analyze` to confirm.
- Recovering a lost internal endpoint: `grep -ohE "api/[A-Za-z0-9/_.:-]*fee[A-Za-z0-9/_.:-]*"`
  over `~/.hermes/profiles/jay/sessions/session_*.json` — past XHR-hook captures
  are stored verbatim in the transcripts. This is how `fee/v3/search` and
  `fee/v3/details` were recovered after a dozen guessed 404s. **Do this FIRST
  next time instead of guessing endpoint names.**
