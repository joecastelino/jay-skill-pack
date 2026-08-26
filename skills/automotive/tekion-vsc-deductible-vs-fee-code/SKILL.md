---
name: tekion-vsc-deductible-vs-fee-code
description: Answer "we need a deductible fee code" / "how do we bill the customer's deductible or hardware overage" on a Tekion RO covered by a service contract (Fidelity, CVSC, extended warranty). The deductible is a NATIVE field in the pay-type split grid, not a fee — this skill proves whether it already got collected and explains why a fee code is the wrong fix. Also covers the trap that the OpenAPI CANNOT see the deductible.
triggers:
  - deductible fee code
  - create a fee for the deductible
  - how do we charge the deductible
  - customer to pay deductible
  - hardware overage
  - service contract split / CVSC / Fidelity
  - warranty company won't cover the whole job
---

# Tekion: VSC deductible — it is NOT a fee code

## The answer, up front

When a job is covered by a vehicle service contract (CVSC pay type — Fidelity,
Zurich, Endurance, etc.), the customer's **deductible** and any **parts/hardware
overage** are billed through the **Pay Type Split By Payer** grid on that job, in
a first-class `Deductible` field tied to the contract. **Do not build a fee code
for it.**

Why a fee code is actively wrong:
- The native deductible is bound to the contract record (contract no., company,
  expiry) and flows into the warranty claim + nets against the contract company.
- A fee posts to a fee GL account with **no contract linkage** → breaks claim
  reconciliation and puts two competing deductible numbers on one ticket.
- Overage is the same grid: reduce the CVSC payer's amount and the grid
  back-solves the balance to the CP payer. Also not a fee.
- Most stores already have *a* deductible-ish fee code sitting active (AR has
  `CPOD — Certified Preowned Deductible`), so "we don't have one" is usually
  false too. Check before agreeing anything is missing.

## ⚠️ THE TRAP: the OpenAPI is BLIND to the deductible

This is what makes the ticket look real. Every cheap API signal points the wrong
way, and you can confidently conclude "the deductible was never collected":

| What you check | What it shows | Why it misleads |
|---|---|---|
| `/repair-orders/{rid}/ro-fees` | only unrelated fees (LYFT rows at $0) | deductible isn't a fee, so of course it's absent |
| `/repair-orders/{rid}/jobs` | `payType: CUSTOMER_PAY`, **`subPayType: null`** | split is invisible at job level |
| `.../operations` | full labor/parts $ | totals only, no payer allocation |
| a `CUSTOMER TO PAY DEDUCTABLE` job | **$0.00, 0 hrs, no parts, no fees** | it's an empty placeholder — see below |

There is **no OpenAPI read path for the per-job payer split or the deductible
amount.** You must open the job in the browser.

### The one FREE API tell that a contract split IS live
Two places, both on data you already have:

1. **RO search `tags`** — look for `PAY_TYPE: CVSC` and
   `PAY_TYPE: SPLIT_CUSTOMER_PAY_SPLIT`. Their presence means a service-contract
   split exists on this RO.
2. **`/repair-orders/{rid}/ro-invoices`** — the contract money appears as
   `payType: CUSTOMER_PAY` with **`subPayType: CVSC`**, alongside a *separate*
   `payType: CUSTOMER_PAY` / `subPayType: CUSTOMER_PAY` line. That second line is
   what the customer actually owes = deductible + overage. If it's > $0, the
   deductible was collected.

Reconcile all invoice lines (cents!) against the RO header Total before saying
anything is missing.

## ⚠️ The $0 placeholder-job trap — this is what generates the ticket

Advisors frequently open a concern job literally named
**"CUSTOMER TO PAY DEDUCTABLE AND HARDWARE AMOUNT OVERAGE"** as a note-to-self,
then correctly bill the deductible inside Manage Splits on the *covered* job —
and never clean up the shell. What's left is a $0.00 / 0 hrs / no-parts job
sitting on the RO.

A manager (or a service director glancing at the RO) sees that empty job,
concludes there's no way to charge a deductible, and asks for a fee code.
**Nine times out of ten the mechanism already fired one job over.** Always check
the covered job's split before entertaining the fee-code request.

## Method

### 1. Locate the RO across all 7 stores
RO numbers are NOT unique per store — a bare RO# can hit 3-4 dealers. Sweep all
dealers and disambiguate on `status` + `creationTime` (see
`tekion-openapi-repair-orders` and `tekion-ro-job-paytype-triage`).
Verified example: RO **5607** returned hits at AR *and* BC *and* BT *and* SV;
only the AR one was recent/INVOICED.

### 2. Cheap API pass — build the money picture
Pull `ro-invoices` (payType/subPayType split), `jobs`, `operations`, `ro-fees`,
`ro-coupons`. Establish: total, which jobs are CP vs W vs I, and whether a
`subPayType: CVSC` invoice line exists. **Amounts are CENTS — divide by 100.**

### 3. Browser pass — read the actual split (the only ground truth)
Switch the `:9223` browser to the store (dealer pill ≈1130,32 → click the store
row; verify `localStorage.currentActiveDealerId` flipped), then open **each
covered job**:

```
https://app.tekioncloud.com/ro/repair-orders/<documentId>/jobs/<jobId>
```

Poll until `document.body.innerText.length > 1800` AND the URL contains the
jobId (a nav that "succeeds" can still be serving the previous job's DOM), strip
pendo/notification overlays, then slice the text between
`"Pay Split By Payer"` and `"Collapse All Operations"`.

A job with the deductible billed renders exactly this:

```
Pay Split By Payer
Payer                    Split Amount    Split Percentage
<customer>      CP  Deductible   $309.79     6.96 %
<contract co>   CVSC             $4,142.91  93.04 %
Contract Information
Contract No.     W________
Contract Company FIDELITY
Deductible       $309.79
```

Note the **`Deductible` label on the CP payer row** and the separate **Contract
Information** panel repeating the figure. Jobs with no deductible show the CP
row at `$0.00 / 0 %` and CVSC at 100%.

**Loop every CVSC job, not just one.** In the verified case the deductible sat on
ONE job (the first/largest covered job) and the other three covered jobs were
100% CVSC with $0.00 deductible — which is correct (one deductible per contract
claim, not per job).

### 4. Confirm the store isn't actually missing a fee code
Only if you still think a fee is warranted. Fee list via
`fee/v3/search` (see `tekion-fee-not-showing-diagnosis` for the `window.__H`
header builder and the `/core/fees` page URL). Scan active codes for
`DED|CONTRACT|CVSC|WARR|OVER`.

## Worked example (AR / dealer 6195, RO 5607, 2026-08-26)

Complaint: *"Eric wants to create a deductible fee code. I don't see why."*

- 2017 Giulia, 83,398 mi, 10 jobs, 4 payers, total **$17,742.24**, INVOICED 8/25.
- Jobs A-B internal MPI/TPS $0; C = recall `93C` warranty $842.48; D-E internal
  concerns $60 ea; **F-I = four CVSC-covered leak repairs**; J = the $0 shell.
- Job F: CP **Deductible $309.79 (6.96%)** / CVSC $4,142.91 (93.04%),
  Contract Information panel populated (Fidelity).
- Jobs G ($489.40), H ($4,503.87), I ($7,233.67): 100% CVSC, deductible $0.00.
- Job J "CUSTOMER TO PAY DEDUCTABLE AND HARDWARE AMOUNT OVERAGE": **$0.00** —
  pure placeholder, created 6 days after job F.
- Invoices reconcile exactly: CVSC $16,469.85 + CP $309.91 + W $842.48 +
  I $120.00 = $17,742.24.
- AR already has 47 fees incl. active `CPOD — Certified Preowned Deductible`.

**Verdict delivered: no fee code needed — the deductible was collected natively
on job F; job J is a leftover shell and should be voided.**

Minor: CP invoice $309.91 vs deductible $309.79 = **12¢**, almost certainly tax
on a taxable portion. Flag small deltas like this proactively rather than
letting someone else "find" them later — but don't invent a root cause for 12¢.

## Pitfalls

- **Don't judge from the job list.** The RO job list shows job J at `$0.00` and
  jobs F-I at their FULL amounts (`$4,452.70` etc.) with pay type `CP` — nothing
  in that view reveals that 93% of each is going to the contract company.
- **`subPayType` is null on the `/jobs` payload** even when a CVSC split exists.
  Don't read null as "no split."
- **One deductible per claim, not per job** — $0.00 deductible on 3 of 4 covered
  jobs is correct, not a bug.
- Voiding the placeholder job on an **INVOICED** RO is a financial change —
  ask Joe/the store before doing it (see `tekion-ro-void-job-remove-parts`).
- Customer names/phones and contract numbers are on these pages. Skills sync to
  a PUBLIC repo — keep PII out of any writeup.

## Cross-refs
- `tekion-ro-payer-split-sunbit` — how to CREATE/EDIT a split (write side),
  Manage Splits modal, the "new payer stays at $0/0%" trap
- `tekion-ro-job-paytype-triage` — locating the RO, cross-store RO# collisions
- `tekion-openapi-repair-orders` — search payload shape, cents, dealer sweep
- `tekion-fee-not-showing-diagnosis` — fee master/`ADD_TO_RO` config if a fee
  genuinely is the answer
- `persistent-browser-server` — :9223 lanes, dealer switch, DOM-settle polling
