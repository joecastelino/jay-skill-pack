# ELR block (rows 34–55) — validated definitions

Cracked + gate-validated against Joe's known-good June 2026 column, Sept 2026.

## THE BASIS RULE (Joe, verbatim: "all the other stores are MTD")

- **Toyota stores (SCT, BT, TL) → ELR is YTD** (Jan 1 → end of month).
- **All other stores (SV, BC, VC, AR) → ELR is MTD.**

Getting this backwards was the single biggest source of mismatch. Hours Sold /
Attendance / Workshop Analysis blocks are MTD for *every* store — only the ELR
block splits.

## BT service vs body shop: use ADVISOR, not department

Two working splits exist and they return DIFFERENT numbers. For the
**advisor-summary API** (ELR, hours, RO counts) the correct split is by
`primaryAdvisorId`:

```python
BT_BODY = ["73c7e798-5d39-4603-b516-16eae5f36216",
           "bfa0b344-a494-4117-a225-269b91e12f36",
           "93017239-1132-4ecd-b881-1f023d4b8af7"]
NB = {"field":"primaryAdvisorId","operator":"NIN","values":BT_BODY}  # Toyota of Fresno (service)
IB = {"field":"primaryAdvisorId","operator":"IN", "values":BT_BODY}  # Blackstone Body Shop
```

Proof: BT service CP ELR YTD-Jun = **132.74**, exactly matching the sheet.
The `departmentId NIN ["1249_department_3"]` filter gave 148.82 (wrong for ELR).

**Keep `departmentId` for Tech Performance / Workshop Analysis only** — there it
is exact (body prod 1,355.40). Different API, different correct filter.

## Row definitions (SCT pattern, YTD)

| Row | Definition |
|---|---|
| r35 TOYOTA CUSTOMER | payType CUSTOMER_PAY, opcodes NIN (TAC∪TSC) |
| r36 TOYOTA WARRANTY | payType WARRANTY |
| r37 TOYOTA INTERNAL | payType INTERNAL, opcodes NIN PDI |
| r38 TOYOTA TXM | opcodes IN TXM set (any pay type) |
| r39 TOYOTA CARE | opcodes IN TAC set |
| r40 TOYOTA PREPAID | opcodes IN TSC set |
| r41 TOYOTA PDI | opcodes IN ["PDI"] (any pay type) |
| r43 OTHER CUSTOMER | CUSTOMER_PAY + makeId NIN [toyota,scion] |
| r45 OTHER INTERNAL | INTERNAL + makeId NIN [toyota,scion] |

r35–41 carry **no make filter** (store-wide); only r43–45 filter to non-Toyota.
**r49–55 are spreadsheet formulas** (`=AV35`…) — never compute them. Exception:
TL r49 is hardcoded.

## Opcode set rules (derived from SCT's saved groups, which are authoritative)

```python
TXM = [o for o in txm_codes if not re.search(r'PLUS|ROTATE', o.upper())]
TAC = [o for o in tac_codes if re.fullmatch(r'TAC\d*', o)]   # excludes TACOMALOCK
TSC = [o for o in tsc_codes if re.fullmatch(r'TSC\d*', o)]
```

Per-store opcodes from `POST /api/service-module/u/opcode/search`
body `{"searchText": "...", "pageInfo": {"start":0,"rows":2000}}`, keep
`status == "ACTIVE"`. **SCT's saved groups do NOT transfer to BT/TL** — opcodes
are store-specific.

## PDI — validated

Opcode is literally `PDI` at every store. `PDICILAJET` has **zero** YTD activity
(SCT and TL) — ignore it.

YTD thru Aug 2026: SCT ELR 286.58 / 3,224.40 hrs · BT 242.59 / 2,078.60 ·
TL 236.73 / 1,607.10 · BC 258.56 / 1,237.70 (BC runs real PDI volume too).
SV (1 RO), AR (3), VC (0) effectively don't use it.

June gate: SCT **286.16** and BT **242.62** matched the sheet exactly.

## Sheet artifact: TL r41 PDI mirrors r37 INTERNAL

TL's PDI cell has been carrying the INTERNAL value (both 154.29 in June). The
true TL PDI ELR is **236.73**. Do not "fix" the engine to reproduce 154.29 — the
engine is right and the sheet cell is a copy. Ask Joe whether to write the true
value or preserve the mirror.

## Expected drift — do not chase

Reopened ROs settle after close, so YTD figures restate slightly. ~1–2% gaps are
normal (SCT warranty 300.04 vs 304.78; SCT PDI hours 418.40 vs 416.90; BT
internal 148.56 vs 151.32). Flag as drift; don't invent filters to close it.
