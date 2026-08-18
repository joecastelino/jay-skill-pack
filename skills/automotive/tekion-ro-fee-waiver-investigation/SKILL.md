---
name: tekion-ro-fee-waiver-investigation
description: Investigate whether a specific Tekion Misc/RO-level Fee (e.g. LYFT ride-share charge, shop supply fee, diagnostic fee) is being silently zeroed out on customer-pay ROs while the rest of the ticket bills normally — i.e. someone quietly waiving a charge without a documented coupon/discount. Use when asked "is advisor/manager X hiding/not charging for Y" or "why did our [fee] revenue drop."
triggers:
  - not charging customers for
  - hiding a fee
  - waiving a charge
  - lyft fee not billed
  - fee revenue dropped
---

# Tekion RO Fee Waiver Investigation (e.g. "Tony isn't charging for Lyft")

## When to use
Joe/a store manager suspects an advisor or manager is silently NOT charging
customers for a specific RO-level Misc Fee (ride-share, shop supplies, hazmat,
diagnostic, etc.) even though the fee line exists on the RO. This is a **fee
waiver / revenue-leakage detection**, not a normal reporting task — the signal
you're hunting for is "$0 on a fee line that should have a real amount, on an
otherwise fully-billed customer-pay RO."

## Core data model (OpenAPI, verified 2026-08-18 on BT/Lyft)
- `repair-orders:search` result carries a **free** `transportation` LinkedResource
  (`{link,id}`) per RO — resolves via `GET /transportation-types/{id}` →
  `{"data":{"name": "RIDE_SHARE"|"DROP OFF"|"RENTAL"|"WAIT", ...}}`. Sample a few
  ROs to discover the full id→name set for the store (don't assume Lyft's id is
  fixed across stores — it wasn't checked cross-store).
- `GET /repair-orders/{roId}/ro-fees` → `data.roFees[]`, each:
  `{feeCode, fee:{id,link}, saleAmount, costAmount, unitSaleAmount, priceType
  (SYSTEM_CALCULATED|USER_OVERRIDDEN), source (SYSTEM|USER|EXTERNAL), quantity}`.
  **Dollar amounts are CENTS.** `feeCode` for Lyft = `"LYFT"`. A fee row existing
  with `saleAmount: 0` means the fee WAS added to the RO (advisor engaged the
  ride-share workflow) but the dollar amount never got populated/was zeroed.
- `GET /repair-orders/{roId}/ro-coupons` → if `{}` (empty), there is NO documented
  discount/coupon justifying a $0 fee — rules out "legit comp with a paper trail."
- `GET /repair-orders/{roId}/ro-invoices` → `data.roInvoices[]`, filter
  `payType=="CUSTOMER_PAY"` → `invoiceAmount` (cents). If this is POSITIVE while
  the fee of interest is $0, the customer WAS billed for the rest of the ticket —
  proving selective zeroing of just that one fee line, not a full RO comp.
- RO record also carries `createdByUserId.id` and `modifiedByUserId.id` for free —
  useful to see who touched the RO last, though this is RO-level granularity, NOT
  a field-level edit log (see Limitations below).

## Method
1. **Pull the RO index for the window** via `creationTime GTE` (or `BTW`),
   pageSize 50, follow `nextPageToken` (plain pagination works fine on
   `creationTime`, no bisection needed — bisection is only required for
   `closedTime` windows per `tekion-openapi-repair-orders`).
2. **Filter to the transportation type of interest** + `status IN
   [CLOSED,INVOICED]` (or broader if the user wants open ROs too) + BASE_PAY_TYPE
   tag includes `CUSTOMER_PAY`.
3. **Fan out `ro-fees` on the candidate set** (ThreadPoolExecutor(6), retry on 429
   with `time.sleep(25*(attempt+1))`, checkpoint to JSON every ~20 so a
   kill/timeout resumes — reuse the checkpoint/resume pattern from
   `tekion-openapi-repair-orders`). Flag ROs where the target `feeCode` is present
   with `saleAmount == 0`.
4. **Cross-check each flagged RO**: pull `ro-coupons` (should be empty) and
   `ro-invoices` CUSTOMER_PAY `invoiceAmount` (should be > 0 if selective, not a
   full comp) to confirm the "quietly waived just this one line" pattern rather
   than a legitimate documented discount or a fully-comped RO.
5. **Resolve advisor names** via `/users/{id}` (see `tekion-openapi-repair-orders`
   ⭐ section) for both `assignee.advisor.id` (who owns the RO) and
   `modifiedByUserId.id` (who last saved it).
6. **Look for a disproportionate "last modifier."** Compute: (a) overall zero-fee
   rate across all candidates, (b) for each user who appears as `modifiedByUserId`
   on ANY candidate RO, their personal zero-fee rate among ROs they last-touched.
   A rate 2-3x+ the baseline, concentrated on one person (especially someone
   senior like a Service Director who wouldn't normally need to re-touch a
   closed RO), is the actionable signal.
7. **Trend it by month** (`creationTime` → month) to corroborate a "this started
   recently" claim — bucket zero-rate% per month, don't just give a raw count.

## Limitations — be upfront about these
- The public OpenAPI has **NO field-level audit/history endpoint** for fees
  (`/history`, `/audit`, `/activity` all 404 — confirmed in
  `tekion-openapi-repair-orders`). `modifiedByUserId` is the RO's last-saver,
  not proof that THIS PERSON zeroed THIS FEE LINE specifically. Present findings
  as a strong statistical/circumstantial signal, not a definitive edit-log proof.
- For a courtroom-grade confirmation, someone needs to open the flagged RO(s) in
  the Tekion UI and check the RO's Financial/Activity log for the fee section
  directly (browser-only — not exposed via API). Offer this as the follow-up step.
- `priceType: SYSTEM_CALCULATED` with `saleAmount: 0` is itself a little odd —
  if it were truly system-calculated it should reflect the actual ride cost; a
  $0 value alongside `source: USER` suggests a person touched it, not that the
  system genuinely calculated zero.

## Worked example (BT / Lyft / Tony Garcia, 2026-08-18)
70-day BT scan: 895 CUSTOMER_PAY CLOSED/INVOICED ride-share ROs. 30 (3.4%) had
`feeCode=LYFT` with `saleAmount=0`; 19 of those 30 still had a positive CP
invoice total (selective zeroing, not a full comp); zero `ro-coupons` on any of
them (no documented discount). Monthly zero-rate: June 1.2% → July 4.0% → Aug
4.4% (matches a "started ~2 months ago" complaint). Antonio "Tony" Garcia
(BT Service Director, id `e8393eb2-bd0b-4943-942f-86cb5246624e`) was the
`modifiedByUserId` on 6 of the 30 flagged ROs — vs. an expected ~2 by his overall
share of last-touched ROs (57/895) — a ~3x concentration, on someone who
shouldn't normally need to re-save a closed RO. Reported as a strong signal with
the audit-trail caveat, and offered UI-level financial-log confirmation as the
next step.

## Generalization
Swap `feeCode` (e.g. `"LYFT"` → shop-supply/hazmat/diagnostic fee code — look
these up via a sample `ro-fees` pull first if unknown) and the `transportation`
type filter (or drop it entirely if the fee isn't transportation-linked) to reuse
this for any "is someone hiding/not charging for X fee" investigation.
