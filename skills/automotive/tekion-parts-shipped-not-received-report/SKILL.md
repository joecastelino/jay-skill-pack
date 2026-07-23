---
name: tekion-parts-shipped-not-received-report
description: Build the "parts ordered/shipped and NOT received" report for a Tekion store (outstanding part lines on open POs, with aging + $ value). Uses the Parts Receiving "Orders Not Received" queue and an XHR hook on partTrade/u/purchase/search to harvest full per-part JSON (ordered/received/backorder/cancelled qty, unit cost, ref RO/SO, customer). Verified SCT 2026-07-06 (400 POs, 1127 lines, $180K). Load when Joe asks for shipped-not-received, unreceived parts, open PO parts, or PO aging reports.
---

# Tekion "Parts Shipped & Not Received" Report

Produces per-part-line outstanding report: PO, control#, type, created/age, part#, name,
ordered/received/backorder/cancelled/outstanding qty, unit cost, outstanding $, ref RO/SO, customer.
Plus summary: totals by PO type + aging buckets (0-7 / 8-30 / 31-90 / >90d).

## Where the data lives

- **Parts Receiving URL = `/parts/receiving/orders`** — NOT `/parts/parts-receiving` (that route
  loads the shell but renders BLANK forever). Redirects from `/parts/receiving`.
- Page has tabs **Orders | Floats**, right-side views **Exception Reports | Receipt Transactions |
  Shipments** (`/parts/receiving/shipments` = per-PO Order Qty vs Received Qty table), and quick
  filters with live counts: **All / Manual Receipt / Orders Not Received / Backordered / Cancelled /
  Cross shipped**. "Orders Not Received" = the exact population for this report (SCT: 400).
- Backordered count can be 0 even with hundreds of unreceived POs — nobody formally flags BO;
  don't interpret BO=0 as "nothing outstanding."

## ⚠ TRAP: the download icon here exports FLOATS, not orders

The only `icon-download` on `/parts/receiving/orders` fires
`partTrade/u/float/search/download` — a CSV of FLOAT parts (unassigned received parts), useless
for this report. There is NO orders-table export on this screen. Get the data via XHR hook instead.

## Harvest method (verified end-to-end)

1. **Session**: restore into :9223 per `persistent-browser-server` skill (cookies + 21 localStorage
   keys from `.tekion-storage-state.json`, navigate /login first, then /home; verify dealer pill).
2. Navigate `/parts/receiving/orders`, wait ~9s.
3. **Arm XHR hook** capturing FULL responseText of `partTrade/u/purchase/search`:
   ```js
   window.__jayFull=[];
   const O=XMLHttpRequest.prototype.open,S=XMLHttpRequest.prototype.send;
   XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return O.apply(this,arguments);};
   XMLHttpRequest.prototype.send=function(){this.addEventListener('load',()=>{try{
     if(this.__u&&this.__u.includes('partTrade/u/purchase/search'))window.__jayFull.push(this.responseText);
   }catch(e){}});return S.apply(this,arguments);};
   ```
4. Click **"Orders Not Received"** quick-filter leaf (find leaf span/div, `/mouse` its center).
5. **Paginate**: click page numbers 1..N (leaf elements with y>300, pick LAST match — page numbers
   collide with row text). 50 rows/page. **Page 1 serves from React Query CACHE (no XHR)** — force a
   refetch by clicking another quick-filter (e.g. Backordered) then back to Orders Not Received,
   OR clear `__jayFull` and re-click page 1 after visiting page 2+.
6. **Pull captures in ≤16000-char `/eval` slices** — responses are 8–12 MB each; get
   `window.__jayFull[i].length` then slice-loop, write each to disk, parse with
   `json.loads(s, strict=False)`.
7. Dedup hits by `orderNumber` across captures.

## Response shape (data.hits[])

Per PO: `orderNumber, controlNumber, status (SUBMITTED/PARTIALLY_RECEIVED), orderType
(OEM_STOCK_ORDER/OEM_SPECIAL_ORDER), createdTime (ms), oemParts[]`.
Per part in `oemParts[]`: `partNumber, partName, unitCost (DOLLARS here, not cents —
partTrade internal API differs from OpenAPI), orderQuantity, receiveQuantity,
backOrderQuantity, oemBackOrderQuantity, userCanceledQuantity, oemCancelledQuantity,
refNo (originating RO/SO number), requestedByCustomer, sourceCode, sourceCode, vin[]`.

**Outstanding = orderQuantity − receiveQuantity − (userCanceledQuantity + oemCancelledQuantity)**;
keep lines where outstanding > 0. Value = outstanding × unitCost.

## Bonus: PO-list xlsx export (Submitted/Invoiced/Partial tabs)

On `/parts/purchase-order/list`, click a status tab then the `.icon-download1` (≈x1223,y163) →
fires `parts-reporting/u/report/download/PURCHASE_ORDER_REPORT` → poll captured
`media-v3/u/v2/presignedurls` for `uploadStatus:COMPLETED` → S3 URL has MASKED AWS key
("AKIART...Z5S6") so external curl fails — **in-page `fetch()` → arrayBuffer → btoa →
window.__b64**, pull in 16000-char slices, base64-decode to xlsx (inlineStr format; parse with
ET + inlineStr `<is><t>` handling AND sharedStrings fallback). Gives PO-level rows only
(no part lines) — Age column has commas ("1,280"), strip before int().

## Off-viewport click fix

The receiving-page download icon sits at x≈2296 (outside the 1280 viewport). `/click` by selector
500s and `/mouse` can't reach past viewport. Working fallback: dispatch a full synthetic sequence
on the element via `/eval`:
```js
['pointerdown','mousedown','pointerup','mouseup','click'].forEach(t=>
  e.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
```

## Output

Write CSV + multi-tab xlsx (Summary: totals, by-type, aging; Detail: all lines with freeze panes +
auto-filter) to `/home/itadmin/tekion-reports/SCT_parts_shipped_not_received_<date>.{csv,xlsx}`.
Joe likes CSV for sortable data reports. Flag the >90d bucket explicitly — stale special-order
lines (2025 POs) are usually dead/undispositioned and Joe wants the cleanup callout.

Artifacts from the first run: `/home/itadmin/tekion-reports/po-notreceived/` (raw captures +
`outstanding_lines.json`).

## Emailing it
Joe usually wants it emailed to himself: route through Stacey (bridge), subject pattern
`"SCT Parts Shipped and Not Received - as of MM/DD/YYYY"`, attach BOTH xlsx (Summary+Detail tabs)
and CSV. Verify delivery in INBOX. Watch the duplicate: the self-send INBOX force-append can
double up when Gmail also delivers the send — one dup is harmless, but don't append blindly.

## Pitfalls recap
- `/parts/parts-receiving` = blank shell; use `/parts/receiving/orders`.
- Download icon on receiving = FLOATS export, not orders.
- Page-1 XHR cache — force refetch via filter toggle.
- 8–12MB captures — slice-pull, `strict=False` parse, save incrementally.
- unitCost in this internal partTrade API is DOLLARS (unlike OpenAPI RO amounts which are CENTS).
- Report is per-store; re-run after dealer switch (UI pill) for other stores.
