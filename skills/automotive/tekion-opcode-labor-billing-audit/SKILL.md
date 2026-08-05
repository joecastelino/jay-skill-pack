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

## RESOLVED CASE — BT SMMOAEPR (2026-08-05, Joe: "fix the opcode")

Joe flagged (via screenshot of an open RO's Service Menu / Story Line panel):
"tech Time on the EPR Service menu that has an oil change epr and moa. Needs
to pay .8" — screenshot showed opcode Op1 TEK20000PSM (20K Premium Severe menu)
billing 0.20 hr CP, and a checked Story Line item "EPR Service - Includes Engine
Oil Change, BG EPR Treatment and MOA Additive Internal Engine Cleaning".

- **Found the opcode** by searching the BT (dealer 1249) `/ro/opcode` list for
  keyword `EPR` (see the search technique now documented in
  `tekion-opcode-default-pricing`) — 3 hits, exact description match was
  **SMMOAEPR** ("INCLUDES ENGINE OIL CHANGE, BG EPR TREATMENT, AND MOA ADDITIVE
  INTERNAL ENGINE CLEANING", Category=Service Menu, Type=Individual Service,
  Active). No quotes-explode needed — this is a standalone Story Line checkbox
  item, not a bundled per-op menu line.
- **Root cause**: opcode's Default-tab Labor Customer hr AND Manufacturer hr
  were both `0.20` — that IS the tech flag/pay time (separate from the CP
  customer-facing Fixed Price $95.44, which is untouched by this fix).
- **Fix**: set BOTH Customer and Manufacturer hr spinbuttons to `0.80` via
  :9223 (`/mouse` click to focus each `input.ant-input-number-input`, then
  `/type` + `/press Tab` to commit), clicked Update (`/mouse` on its scrolled-
  into-view center). Verified via a TRUE remount (`/navigate` to `/home` then
  back to `/ro/opcode/edit/SMMOAEPR`) — both fields read 0.80 fresh from server.
- **Scope note given to Joe**: this is a GLOBAL opcode-level change — it applies
  to every future RO/menu tier that pulls this Story Line item at BT, not just
  the 20K interval. Flagged in case Joe wanted it scoped to only the 20K menu
  (he did not object).
- Session also did a fresh `login.py` (session was EXPIRED) + full storage-state
  injection into :9223 (cookies + 21 localStorage keys, all `ok`), then a UI
  dealer-switch from default BC (1251) to BT (1249) via the dealer pill popover
  before any of the above — standard `tekion-autonomous-login` /
  `persistent-browser-server` procedure, no new findings there.
