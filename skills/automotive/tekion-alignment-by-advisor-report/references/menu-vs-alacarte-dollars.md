# Menu-bundled lines: count them, don't price them

Applies to ANY component-level Tekion report (alignments, rotations, filters, tires) at any store.

## The rule

Tekion bills a service menu as **ONE line**. When a component sells inside a menu, that line's
amount is the **entire package price**, not the component's share.

- `TEK60000PSM` = $1,553.81 — the customer's whole 60K service.
- A stand-alone alignment at SCT = $139.99.

Therefore:

| | Units | Dollars |
|---|---|---|
| À la carte / dedicated line | count it | **real component revenue** |
| Bundled inside a TEK menu | count it | **NOT component revenue** |

- **Units add. Dollars do not.**
- Never render a "Total $" column that sums both.
- Show package dollars in a separate greyed column labelled `not <component> $`,
  with a printed warning on the report that the columns must not be added.

## Detection

```python
import statistics
statistics.median(x['cents'] for x in dedicated)/100   # one clean, consistent price
statistics.median(x['cents'] for x in bundled)/100     # several multiples of it
```

A bundled median that is a large multiple of the à la carte price means you are looking at
package revenue, not component revenue.

Real miss: SCT August 2026 — summing the columns would have overstated alignment revenue by
**$28,354 on $55,970 (+51%)**.

## Never hand-wave a count discrepancy

If two runs disagree on a count, do **not** offer a plausible explanation. Dump both
`(ro, opcode)` sets and diff them both ways, then look up the offending ROs in the closed
index to read their real opcode tags.

```python
sB - sA   # extra rows -> inspect index tags per RO before theorizing
sA - sB   # missing rows; empty means one side is a strict superset
```

I once explained a 448-vs-443 gap as a "candidate scope difference." It was actually an opcode
typo (`ALIGN00BRA` vs the real `ALIGN00RBA`) that silently dropped 5 ROs. The set diff takes
about thirty seconds and names the exact ROs. Joe accepts "I don't know yet"; he does not
accept a confident wrong explanation.

## After patching an opcode set, reissue the period

A same-day patch does not retroactively fix an email that already went out. If the nightly cron
fired **before** the patch landed, re-run and reissue that period's report, and say plainly that
it supersedes the earlier number.

## Coaching angle

Report per-advisor **menu attach share** (menu units ÷ total units). Advisors at 0% have a
menu-*presentation* gap, not a component gap — that is the actionable read, not the raw ranking.
