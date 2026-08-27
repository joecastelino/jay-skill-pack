---
name: tekion-reopen-closed-ro
description: Reopen a CLOSED Tekion repair order (RO) when the UI shows no "Reopen" option. Verified live at VW of Clovis (dealer 1891) on RO 141673, 2026-08-27 — flipped CLOSED → READY_FOR_INVOICE via the internal reopen endpoint.
triggers:
  - reopen RO
  - reopen closed repair order
  - can you reopen 141673
  - re-open ticket tekion
  - RO closed need to add a job
---

# Reopen a CLOSED Tekion RO

## TL;DR — the one call that does it

In the authenticated `:9223` browser, with captured axios headers in `window.__HH.h`:

```js
POST /api/service-module/u/ro/closed/<roObjectId>/reopen
body: {"reason": "<text>"}
```

Returns `{data:{reopenedPayer:[...], closedPayer:null, roResponse:{... status:"READY_FOR_INVOICE" ...}}}`.
RO header immediately shows **Ready for Invoice**, jobs flip Closed → Completed, `Add Job` reappears.

## Why you can't find it in the UI (don't waste an hour like I did)

Exhaustively verified on 3 closed ROs at dealer 1891 — **there is NO Reopen affordance anywhere**:
- RO header kebab (`#headerBtn`) = Add/Edit Coupon, Add/Edit Fee, Audit Logs, Cashier, Hold,
  Invoice Pdf Preview, Media, Payers View, Profit/Loss View, RO Clocked Time,
  Schedule Appointment, Update Estimate Amounts, View RO PDF. **No Reopen.**
- Green "Closed" status pill is NOT clickable (no status dropdown).
- Cashiering panel → only "Show Receipt". Transaction kebab → only "Show Receipt".
- Payers Consolidated View → payer kebab only "Payers Details"; Resync Payer +
  Invoice Selected Payer(s) are disabled.
- RO-list row kebab = View RO PDF / Cashier / Profit-Loss. Bulk **Action** menu = Create
  Quick RO, Claim List, Download Reprints, Download Excel, Technician Queue, Warranty
  Posting + Close CP/IP/WP/RO. **All close, none reopen.**

The role permission IS granted — role `656e20059bf81e46893228de` (VC Controller persona) has
`Repair Order ReOpen` **ON** and `Repair Order ReOpen Closed` (Service → Special Permissions)
**ON**. So the menu item is hidden by a *front-end gate*, not permissions.

The bundle gate (chunk `58884.*`):
```js
isReOpenROMenuDisabled: status !== INVOICED          // ← CLOSED fails this
isReOpenROAfterCloseDisabled: (e,{roCustomerPayStatus,roWarrantyPayStatus,roInternalPayStatus}) =>
   e === VOID || (cp!==CLOSED && wp!==CLOSED && ip!==CLOSED)
```
and `REOPEN_CLOSED_RO` is additionally gated on `isCreditROFeatureEnabled()` (chunk `69721.*`,
`$ = (key,type) => key===REOPEN_CLOSED_RO.key && type===RO && isCreditROFeatureEnabled()`).
The **Credit RO feature is off at AMG**, so the "Reopen Closed RO" menu item never renders —
but the backend endpoint is fully functional and permission-checked server-side.

## Procedure

1. **:9223 must be authed + on the right dealer.** Verify
   `localStorage.currentActiveDealerId`. Switch via the dealer pill (~1120,20) →
   `[class*="root_dealerInfoItem_container"]` row → `scrollIntoView` → `/mouse` its center.
   Setting the localStorage id directly does NOT work.
2. **Get the RO's Mongo id.** RO list → expandable search `input[searchfield="ALL"]`
   (click ~942,149 first to expand), native value-setter + `input` event + Enter
   KeyboardEvent. Click the RO → id is in the URL
   `/ro/repair-orders/<roObjectId>/jobs`.
3. **Capture axios headers** (bare fetch with only localStorage headers 500s / 404s).
   Install an XHR hook, then trigger an in-app XHR by clicking a TAB (Jobs ↔
   Recommendations) — a full page nav wipes the hook:
   ```js
   window.__HH=null;
   var so=XMLHttpRequest.prototype.open, ss=XMLHttpRequest.prototype.send,
       sh=XMLHttpRequest.prototype.setRequestHeader;
   XMLHttpRequest.prototype.open=function(m,u){this.__u=u;this.__h={};return so.apply(this,arguments);};
   XMLHttpRequest.prototype.setRequestHeader=function(k,v){this.__h[k]=v;return sh.apply(this,arguments);};
   XMLHttpRequest.prototype.send=function(b){
     if(this.__u&&this.__u.indexOf('app.tekioncloud.com/api/')>0&&!window.__HH)
       window.__HH={u:this.__u,h:this.__h};
     return ss.apply(this,arguments);};
   ```
   Headers include `tekion-api-token`, `roleId`, `userId`, `tenantname`, `dealerId`,
   `tek-siteId`, `applicationId: ARC_NA`, `productIds: ARC`.
4. **Fire the reopen** (add `Content-Type: application/json`):
   ```js
   fetch('/api/service-module/u/ro/closed/<roId>/reopen',
     {method:'POST',headers:h,body:JSON.stringify({reason:'<why>'})})
   ```
5. **Verify** — hard `/navigate` to the RO jobs page; header must read
   **Ready for Invoice** and jobs must be **Completed** (not Closed).

## Reason text
`GET /api/service-module/u/settings/service-settings` → `creditNoteSetup`:
- `reopeningNotesMandatory: false` at VC (so `reason:""` is accepted — pass a real
  reason anyway for the audit log).
- Configured reasons list, e.g. `"Reopening for Warranty related changes"`
  (id `a8dce9df-11b7-4fb5-a671-e8822eee6cf0`).

## Accounting side-effects (KB SVC30 "Accounting updates in Service 3.0")
Reopening a closed RO **reverses the accounting**. Under Service 3.0 payer-level posting,
reopening a single payer creates a **full reversal for the entire base pay type** plus a
**credit note / cancelled invoice** for that payer; re-closing posts one JE with separate
lines per payer, tagged **REV**. Under 2.0 it reopens all base pay types and posts a delta
on re-close. Tell Joe/the office whenever you reopen a *cashiered* RO — the payment
($615.51 on 141673) stays on the customer account and the invoice must be re-closed.

## Related endpoints found in the bundle (untested)
- `reOpenROPayers` — payer-level reopen (`REOPEN_PAYER`), gated on
  `isReopenPayerVisible` (needs Service V3 + payer-level posting).
- `reOpenEntity` / `reOpenRecommendation` → `.../reopen` for jobs & recommendations
  (perms `Repair_Order_Job_Recommendation_Reopen`, `Repair_Order_Mpvi_Form_Reopen`).

## Pitfalls
- `/api/service-module/u/repair-orders/<id>` = 404. The correct read is
  **`/api/service-module/u/ro/<id>`** (returns `{jobs,recommendations,sublets,ro}`).
- Bare in-page `fetch` with hand-built localStorage headers fails — always replay
  captured axios headers.
- `browser_navigate` / `browser_vision` tools open a SEPARATE unauthenticated context.
  Use the :9223 HTTP API's own `/eval`, `/mouse`, `/screenshot`.
- Strip overlays before any click:
  `document.querySelectorAll('[id*=pendo],[class*=pendo],.ant-notification').forEach(e=>e.remove())`
- OpenAPI has no reopen endpoint and the token bucket may be 429'd — this path uses the
  browser session only, zero OpenAPI quota.
