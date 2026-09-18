---
name: tekion-prepaid-plan-shortpay-cvsc
description: Diagnose "the plan only pays $X but the RO total is $Y" / "we used to apply the discount and it closed, now it won't" warranty & prepaid-maintenance short-pays (ToyotaCare/TAC, TSC, VSC, service contracts) in Tekion. Covers the CVSC sub-pay-type root cause, the pre-tax-coupon trap, and the control-RO comparison that proves the correct structure.
triggers:
  - ToyotaCare only pays but the total is higher
  - prepaid maintenance short pay
  - warranty short paid
  - we used to apply the discount and it would close
  - schedule still expecting the full amount
  - cant close at the plan allowance
  - TAC10 TAC5 TSC2 TSC3 wrong total
  - service contract pays less than the RO
---

# Tekion: prepaid-plan / warranty SHORT-PAY ("plan pays $X, RO is $Y")

Verified live 2026-09-17 on **BT (Blackstone Toyota, dealer 1249) RO 153664** — 2025
Camry, TAC10 Toyota Auto Care 10K. Store: *"ToyotaCare only pays $65.00, but the total
is $129.71. We used to apply the discount and it would close correctly… now it won't
let us close it at the $65.00."*

## ⭐ ROOT CAUSE (in one line)

**The job's sub-pay-type is `CUSTOMER_PAY` instead of `CVSC`.** The job is therefore
NOT on the plan's contract payer, so Tekion never applies the contract allowance — the
op prices at RETAIL, the plan's fixed allowance never lands, and the whole balance sits
on the customer.

## Step 0 — Two clarifying asks up front (don't burn a turn later)

1. **Which store?** Ask in the same breath as starting the fleet sweep (BT staffer
   U0B7UBQ8Y3T reports these for Blackstone Toyota; RO 153664 case).
2. **"Where are you seeing the full amount / the 'schedule' figure?"** Stores call the
   customer-payer balance in Payers View (or the accounting schedule) "the schedule" —
   pin the exact screen before diagnosing so the answer points at the right surface.

## Step 1 — Cross-store sweep (never assume the store)

RO numbers are not unique across the 7 stores. `repair-orders:search` with
`filters:[{field:"documentNumber",operator:"IN",...}]` against every dealer in
`cfg["dealers"]`. BT 153664 collided with two CLOSED older ROs (ST 2016, TL 2021) —
disambiguate on `status` + recent `creationTime`.

## Step 2 — Read the job's payType AND subPayType

`GET /repair-orders/{rid}/jobs`. The tell is a job whose concern contains the plan
service text (e.g. `"TOYOTA AUTO CARE 10K SERVICE."`) with:

| | broken | healthy |
|---|---|---|
| `payType` | `CUSTOMER_PAY` | `CUSTOMER_PAY` |
| `subPayType` | **`CUSTOMER_PAY`** | **`CVSC`** |

`payType` stays CUSTOMER_PAY in BOTH — **only `subPayType` distinguishes them**. Do
not conclude the job is mis-assigned from `payType` alone.

The same `subPayType` shows up on `/ro-invoices`: the healthy RO posts a separate
invoice line `payType: CUSTOMER_PAY, subPayType: CVSC`.

## Step 3 — ⭐ CONTROL-RO COMPARISON (do this before advising — it is the proof)

Free, ~10s, and it is what turns "I think" into "here is the convention":

```python
post("/repair-orders:search", {"filters":[
  {"field":"opcode","operator":"IN","values":["TAC10"]},
  {"field":"creationTime","operator":"BTW","values":[str(lo),str(now)]}],"pageSize":50})
# then per hit: /jobs, /ro-invoices, /job-coupons
```

Also count RO `tags` where `field == "PAY_TYPE"` — on BT, 34/50 TAC10 ROs carried
`CVSC`; the broken one carried none.

**BT control result (153789 / 153783 / 153782, all CLOSED):** every one posts
`CUSTOMER_PAY / CVSC · $65.00 · CLOSED`, with the plain `CUSTOMER_PAY` invoice at
`$0.00`. And the control's TAC10 job **is built to the allowance**:

```
op TAC10 labor $21.53 · billDur 2880
  04152YZZA1  qty 1  $4.91
  0W20BULK    qty 6  $33.72  (@ $5.62)
  9043012031  qty 1  $1.49
= 21.53 + 40.12 + (40.12 × 8.35% = $3.35) = $65.00 EXACTLY
```

The broken RO's job instead carried **labor $55.00 + parts $71.80** — retail, with an
expensive per-quart oil (`00279-08QTE-01 ... $13.08 × 5`) instead of bulk.

## Step 4 — ⚠️ THE PRE-TAX COUPON TRAP (why "the discount used to work")

Store's workaround: apply a coupon sized **post-tax** (`$129.71 − $65.00 = $64.71`)
and type that as the coupon's `effectiveDiscount`.

Two things break it:
1. **Tekion applies the coupon PRE-TAX** and then recomputes tax on the reduced base.
   The tax-inclusive reduction ≠ the coupon amount, so the customer's net does not land
   on the target. On 153664 a `$64.71` coupon against a `$130.97` job left **$66.26**.
2. **`priceType: USER_OVERRIDDEN` coupons are a FIXED dollar amount — they do not
   re-scale when the job price changes.** The audit log on 153664 showed the labor price
   edited 7 times in one afternoon ($55→$5→$50→$47.99→$52.01→$51.90→$51.91) with the
   coupon added / deleted / re-added / zeroed / re-set. Every price edit knocks the
   balance off the plan allowance again. **That is the "it used to work, now it
   doesn't" — the coupon isn't broken, it's pinned.**

Read the coupon from `GET /repair-orders/{rid}/jobs/{jid}/job-coupons` →
`data.coupons[].effectiveDiscount` (CENTS) + `priceType`. Note `/repair-orders/{rid}/ro-coupons`
returns `data: {}` even when a job-level coupon is live — **query the job-level endpoint**.

## Step 5 — Separate the hard CLOSE BLOCKER from the money problem

They are independent; state both. On 153664 the money was cosmetic-by-comparison but the
close was hard-blocked:

- **Job status `IN_PROGRESS`** → in the **Payers Consolidated View** (header
  `Invoice` button, `id="invoice"`) the payer's `Invoice` checkbox is
  **`disabled:true`**. A payer you cannot invoice is a payer that can never close.
  Fix = **Mark as Complete**. Nothing to do with the dollars.
- Read the payer rows + statuses by slicing `document.body.innerText` from
  `"Payers Consolidated View"`. Expand every `.icon-caret-right` first to get per-line
  amounts, coupon allocation, and tax codes.
- Note the header **Total** and the job **Labor Price** field can differ between two
  reads minutes apart — the store may be editing the RO live. Re-read, don't cache.

## Step 6 — The fix (per payer split, browser only — no OpenAPI write path)

1. Job → **Mark as Complete**.
2. Job → **Manage Splits** → put the plan allowance (**$65.00**) on the contract payer
   and **$0.00** on the customer. The contract payer must already exist on the RO (it
   often does, sitting at `$0.00` / status `NA` — e.g. BT `1356241 - ToyotaFinancialSE`).
   If absent: **Add New Payer** → **Pay Type = `CVSC - Vehicle Service Contract`** →
   search the plan payer. (If it refuses, see `tekion-ro-payer-split-sunbit` — the #1
   trap is that you must *reduce the ORIGINAL payer's amount*, not raise the new one's.)
3. **Remove the hand-made coupon** once the split is right — it fights the split.
4. Re-read Payers View, then invoice.

⚠ Per the never-guess rule: `CVSC` + the split amount is a **financial re-assignment on a
live customer RO**. State the baseline, show the control ROs, get an explicit go before
writing. Diagnosing is free and read-only — do all of Steps 1–5 autonomously.

## Pitfalls

- Tekion $ = **CENTS** in the OpenAPI (`6471` = $64.71).
- `/jobs` returns `data.jobs` (dict) on some ROs and a bare list on others —
  `d=resp["data"]; rows = d["jobs"] if isinstance(d,dict) else d`.
- `search` results have **no `id` key**; the RO id is `r["jobs"]["id"]`.
- Don't say "the job is customer-pay so it's wrong" — `payType` is CP on the healthy
  ones too. It's `subPayType`.
- Two "Need Attention" flags on sibling jobs and an
  `The total internal pay amount exceeds the configured internal limit` warning in
  Payers View are **additional, separate** items — report them, don't conflate.
- `:9223` header `Invoice` button sits at **x≈1263, off the 1280 viewport** — `/mouse`
  silently misses. Use `document.getElementById('invoice').click()` via `/eval`.

## Cross-refs
- `tekion-ro-payer-split-sunbit` — the write-side split mechanics + grid traps
- `tekion-ro-close-blocked-triage` — when the real issue is "can't close"
- `tekion-ro-job-paytype-triage` — cross-store RO# collision, pay-type radios
- `tekion-vsc-deductible-vs-fee-code` — deductible vs fee code on VSC jobs
