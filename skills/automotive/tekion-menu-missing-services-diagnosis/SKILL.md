---
name: tekion-menu-missing-services-diagnosis
description: >
  Diagnose a Tekion service-menu ticket where a manager/advisor says the menu is
  "missing items", "missing services", "the service didn't show up", or the
  package looks short — i.e. WRONG CONTENT, not wrong price. Differential
  diagnosis across the 3 known root causes (row tier-coverage gap, wrong
  baseSystemInterval stamp, row-scope miss), all readable over the API without a
  browser. Sibling of tekion-quotes-menu-price-diagnosis (that one = wrong
  DOLLARS; this one = missing LINES).
triggers:
  - menu is missing items
  - missing services on the menu
  - service didn't show up on the quote
  - package looks short
  - menu content wrong
---

# Tekion Menu — "Missing Items" Differential Diagnosis

## When to load this
Someone (store manager, advisor, Joe relaying them) says a menu package is
**missing services / items / lines**. This is a CONTENT failure, not a pricing
failure. If the complaint is about a wrong dollar amount, use
`tekion-quotes-menu-price-diagnosis` instead.

⚠️ **STEP ZERO still applies** (Joe stopped me twice on this at SCT): pull a clean
throwaway quote on the exact VIN + mileage FIRST to confirm the symptom even
reproduces, before dissecting menu rows. But for "missing items" specifically, ALSO
run the tier-coverage audit below — it's a 10-second API read and it has already
caught a real production bug that a single quote would have missed (a quote only
shows you ONE tier/condition card).

## The 3 known root causes, in order of how fast they are to rule out

### 1. TIER-COVERAGE GAP (found at BC 2026-08-18 — the sneakiest)
A factory line was suppressed across all 6 packageType/drivingCondition combos but
the replacement sibling was enabled on only some. Result: on the uncovered cards the
service renders **nothing at all** — no line, no price, no error.

**THE INVARIANT:** when you suppress a factory line and add a replacement, the
replacement's enabled tier set MUST exactly equal the suppression's tier set.
A swap replacement is NOT an optional add-on.
- **Add-on** (optional upsell over untouched factory content) → tier-selective is fine
  (BT's 25 add-ons are deliberately PREMIUM/SEVERE-only).
- **Swap replacement** (suppressed factory line) → must match suppression exactly
  (BT's oil/rotation/cabin swaps are correctly all-tiers).
Carrying "add-on = Premium-only" muscle memory onto a swap row is exactly how the BC
bug happened.

**Detect:** run `scripts/tier_coverage.py` (below). Any combo printing
`NOTHING ENABLED` is a missing-items bug for every vehicle matching that row.

### 2. WRONG baseSystemInterval STAMP (found at BT 2026-07-13 by Tony)
Each menu **row** carries `baseSystemInterval`, which decides WHICH factory
maintenance package renders at quote time — independent of which interval menu the
row lives in. A row created through the UI inherits the **menu-level default**
(often 5000/10000), NOT the menu's own interval. Bottom-most row wins → vehicle gets
the 5K/10K factory package on a 30K/172.5K menu → short inspection list, missing
engine air filter / ATF / ball joints / brake lines etc.

**Price tell:** a higher interval's Basic quote equals the 10K's price exactly
(e.g. $239.85 at BT) AND shows the short 10K inspection list.
**Detect:** `scripts/check_base_interval.py <menuId>` — every row's stamp should
match the menu's own interval (or the interval-appropriate native-row stamp).
**Fix surface:** inside the expanded row, ant-select `div#BASE_SYSTEM_INTERVAL_SELECT`
("Base System Interval *") → pick `"<interval> mi"`.

### 3. ROW-SCOPE MISS
The vehicle doesn't match any tier row (make/model/year/trim/fuel/cylinder filter),
so it falls through to factory content — or matches a row you didn't intend
(bottom-most applicable row wins). Common at BC where rows are Chevrolet-only:
GMC/Cadillac/Buick never match and bill factory dynamic pricing.
**Detect:** `check_base_interval.py` prints each row's scope; compare against the
complaint vehicle's decoded trim. Confirm the decoded STYLE actually matches the
engine scope — a VIN decoding as 5.3L will silently skip a 6.2L row.

## Fast API read path (no browser)
All three checks read the menu config over plain urllib — no browser, no session
contention, no dealer drift.

```python
HDRS = dict(json.load(open('/tmp/tekion_rec_headers.json')))
HDRS['dealerId']   = '1251'        # target store
HDRS['tek-siteId'] = '-1_1251'
url = f'https://app.tekioncloud.com/api/service-module/u/opcode/service-menu/{MENU_ID}'
```
- Path is `/u/opcode/service-menu/<id>` — the bare `/u/serviceMenu/<id>` 404s.
- Rows: `data.menus[]` sorted by `order`; scope lives ONLY in `parameters[]`
  (top-level make/models/years stay null even on scoped rows — don't be alarmed).
- Services: `row.servicesMetaData.services[]`, each
  `{referenceId, type: MODIFIED_SYSTEM|ADDED, tierMappings:[{packageType,
  drivingCondition, enabled}]}`. A suppressed service STAYS in the list with all
  `enabled:false` — **diff enabled flags, not presence**.
- Name/opcode: `GET /u/opcode/included-service/<referenceId>`.
  ⚠️ If the cached header file is scoped to a DIFFERENT dealer, these lookups 404
  under a swapped dealerId. The tier-flag structure still reads fine — which is all
  the coverage audit needs. Don't let 404s on name resolution stop the diagnosis.
- `data.modifiedTime` on this endpoint is epoch **SECONDS**, not ms.

## One-shot audit script
`scripts/menu_audit.py <MENU_ID> <DEALER_ID>` runs all three checks in one pass and
prints a PROBLEMS summary at the end. Example:
```
python3 scripts/menu_audit.py 65530c2cd0e3ef410082bb2c 1251
```
Store-agnostic — works on any of the 7 AMG dealers. Dumps the raw config to
`/tmp/menu-<MENU_ID>.json` so you can diff before/after a fix.
Run it BEFORE proposing a fix and AGAIN after publishing.

## ⚠️ THE VERIFICATION BLIND SPOT (the real lesson from BC)
**Penny-verifying one card does NOT verify a menu.** At BC I penny-verified six
tiers over a month ($119.95 / $129.95 / $179.95 / $204.95 / $214.95 / $249.95) and
every single check landed on a tier/condition card that happened to have the
replacement enabled. The bug lived in the three combos I never opened. My
verification method and my bug had the *same blind spot*, so the bug was invisible
to my own QA.

**Rule: after ANY suppress/swap menu build, run the tier-coverage audit before
declaring done — and treat a price-verified quote as proof about ONE card only.**
A tier isn't verified until all six packageType/drivingCondition combos are read.

## Reporting to Joe
Don't conflate failure classes. Separate:
- missing LINES (this skill) vs wrong DOLLARS (price-diagnosis skill)
- pre-existing open gaps (e.g. BC's unbuilt T7 Mobil 1, the L8T part-number gap)
  from the newly found bug
State which root cause the evidence supports, and if a live PUBLISHED menu needs
changing, get Joe's explicit go first (never-guess rule) — including confirming the
INTENDED tier coverage rather than assuming all six.
