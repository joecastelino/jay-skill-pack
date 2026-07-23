---
name: tekion-opcode-labor-billing-audit
description: Audit a Tekion opcode for wrong labor hours / wrong labor rate across recent ROs (e.g. ToyotaCare TEK opcodes billing 0.8 instead of 0.5, or TEW vs W rate). Determines whether root cause is opcode config, advisor behavior, or post-creation edits. Read-only diagnosis workflow + open case log.
---

# Tekion Opcode Labor-Billing Audit (wrong hours / wrong rate)

Use when Joe reports "RO billed X hours instead of Y" or "wrong labor rate" on a specific opcode, and it has happened repeatedly.

## Workflow (all read-only — Joe usually says DO NOT FIX until he approves)

1. **Pull the opcode config first** (browser /ro/opcode/edit/<OP> or opcode API — see tekion-opcode-api skill):
   - `laborTime` — if 0, nothing on the opcode enforces hours; they're set at line-creation (guide/entry path).
   - Warranty/CP `priceDetail.laborRateId` — resolve against the store's labor rates (/ro/labor-pricing). A wrong pointer here means the "wrong" rate is literally the configured default.
   - Pricing type DYNAMIC (SCP guide) vs FIXED — DYNAMIC = hours pulled from factory guide per vehicle → explains scattered 0.6/0.8/0.9 values.
2. **Scan recent ROs billed on that opcode** (repair-orders:search prefiltered by opcode tag, then fan out jobs/operations; amounts are CENTS ÷100). Capture per line: hours (billSec/allowSec), effective rate, creator userId, creationTime, modifiedTime.
3. **Rule out post-creation edits**: `modifiedTime == creationTime` on every line = nobody edited after the fact; rate/hours were locked at add-time. `allowSec == billSec` = allowance set at line creation.
4. **Split by creator** (resolve names via OpenAPI GET /users/{id}): if each person is near-100% one rate/behavior, it's two different ADD-PATHS/habits (menu vs direct opcode vs manual rate select), not random error. Many different creators making the same error = systemic config problem, not fat-fingering.
5. **Compare against sibling stores** before declaring "same issue" — opcode rate overrides are PER-STORE. Check whether the other store's opcode has a warranty rate override at all, and what its posted W rate is.

## Verdict patterns
- Opcode points at wrong rate + canOverride=true → half the lines ride the bad default, half get manually fixed → interleaved two-rate pattern with no cutover date.
- laborTime=0 + DYNAMIC → hours scatter matching guide times; fix = store fixed labor time on opcode.
- Fix candidates (ONLY with Joe's explicit go): repoint priceDetail laborRateId to correct rate; set fixed laborTime.

## OPEN CASE — TL TEK09050103 (as of 2026-07-16, Joe said don't fix)
- TL (dealer 1092) rates: TEW = $211.25/hr, standard WARRANTY = $236.63/hr. Opcode TEK09050103 (20K ToyotaCare-SYN) warranty priceDetail points at **TEW ($211.25) — likely wrong**; laborTime=0, DYNAMIC warranty pricing.
- 3-week scan (144 ROs): 12 lines wrong hours (0.6–0.9 vs 0.5) by 8 different creators = systemic; rate split 69 @$211 vs 61 @$236 correlates ~100% with creator. Zero post-creation edits.
- Fix when approved: repoint warranty rate to W $236.63 + store 0.5 fixed labor time. Data: /home/itadmin/tekion-reports/data/tl-tek09050103-scan.json (scanner tl_tek09050103_scan.py).
- Side flag: new TL labor rate "Filter — Cabin and Air Filter" $129.50/hr created 7/14 — possibly unsanctioned, Joe notified.

## SCT comparison (2026-07-16, re-verified fresh 2026-07-17)
- SCT standard Warranty rate = $288.32/hr. SCT ToyotaCare opcodes (TEK09010103/09030103/09050103) have NO warranty rate override — fall through to store W rate. ROs 572747/573023/573103/572892 billed uniform 0.5/0.3 hrs @ exactly $288.32 = NOT the TL issue (no scatter, no rate split).
- If SCT still thinks something is wrong, the only candidate issues are: (1) $288.32 isn't the correct ToyotaCare reimbursement rate (SCT lacks a TC-specific rate like TL's TEW), or (2) allowance hours don't match Toyota's reimbursement. Mechanically the billing is uniform/clean.
- UNRESOLVED: Joe was probing a 2026 model-year ToyotaCare theory (those vehicles were 2024/2025 MY); he never stated the rule. Also asked 2026-07-17 what SCT's actual complaint is (claim rejections vs wrong rate vs wrong hours) — no answer yet. Get the rule from Joe before scanning further.

## Pitfalls
- Never assume one store's opcode/rate setup applies to another — TL has a TEW rate, SCT doesn't.
- Don't guess whether scattered hours are guide-accepted vs manually typed — API can't distinguish; ask an advisor from the "correct" cohort what they do at add-time.
- All OpenAPI $ fields are CENTS (÷100); rate-table dollars in the labor-pricing UI are dollars.
