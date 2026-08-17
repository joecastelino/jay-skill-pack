---
name: tekion-vi-stock-number-rules-fix
description: Fix Tekion Vehicle Inventory Stock# Rules (Vehicle Inventory Setup > Stock# Rules) when a trade-in of a given Make generates a wrong/random stock number instead of the expected prefix (e.g. Mercedes-Benz trade-in not getting an "S..." stock#). Covers navigating to /vi/visettings, editing a rule's Make multi-select via the persistent browser, the modal-scroll gotcha, the two-level Save requirement, and true-remount verification. Verified live at SCT (dealer 876) 2026-08-17.
triggers:
  - stock number wrong
  - wrong stock number
  - vehicle inventory setup
  - stock# rules
  - trade-in stock number
  - stock number rule make missing
  - tekion stock sequence config
---

# Tekion Vehicle Inventory Stock# Rules — Make-List Fix

## When to use
A dealer reports a trade-in vehicle got a random/wrong stock number instead of
the expected prefix pattern (e.g. any non-Toyota trade-in at a Toyota store should
get an "S..." stock number, but a specific Make like Mercedes-Benz didn't). Tekion
Support (Balla Meghana / Shivam Yadav pattern) will correctly diagnose "the make
is not added in the vehicle inventory setup" but their support agents can't touch
dealership settings — only Jay/Joe can fix it directly.

## Root cause pattern
`/vi/visettings` → **Stock# Rules** tab has an ordered list of conditions
(Stock Type | Stock Sub Type | Make combinations) each mapping to a stock-number
pattern (e.g. `C210001`, `T210001`, `S5000`). The LAST rule is usually a broad
catch-all for "any non-factory-brand used trade-in" with a huge Make multi-select
(~70+ manufacturers). If a specific Make (e.g. "Mercedes-Benz") is simply missing
from that list, a trade-in of that make falls through to a different/default rule
instead of matching the catch-all — producing the wrong stock-number prefix.
**Always verify this by reading the rule's Make chip list in the DOM before
concluding anything else** — don't assume, confirm the make is truly absent.

## Nav path (via persistent browser :9223)
1. Switch to the correct dealer FIRST (dealer pill top-right ~1130,32 → popover
   row list at x~1095, rows every ~42px starting y~178 for AR/AM/BC/BT/ST/SV/TL/VC).
   Verify `localStorage.currentActiveDealerId` flipped.
2. Click the 9-dot app grid icon (~30,31) → an app-search overlay opens with an
   input `placeholder="Search"` around (753,77). Type "Vehicle Inventory Setup"
   via native value-setter + `input` event (bare `/type` on that box works fine too).
3. Click the single result "Vehicle Inventory Setup" (find by exact innerText
   match, childless element, offsetParent!==null) → lands on `/vi/visettings`.
   **This tab always defaults to "Stock Type" on load/reload — you must click
   the "Stock# Rules" tab every time you arrive/return to this page.**
4. Click "Stock# Rules" tab text (find live coords via innerText match; was
   ~712,158 in one session — don't hardcode, elements shift).
5. Page shows a **Stock# Configuration** list of collapsed rule rows. Each row
   has a pencil/edit `<button class="...editBtn...">` with `<span class="icon-edit">`
   at the row's right edge, and a kebab `...kebabBtn...` further right. Find the
   target row's edit button via DOM query (icon-edit spans), matching by row's
   surrounding text (e.g. contains "S5000" or the make list you expect).

## Editing the Make multi-select — the gotchas
Clicking the row's pencil opens an **"Edit Stock# Configuration"** modal with:
- Left column "Conditions": Stock Type, Stock Sub Type (single-selects)
- Right column "Values": corresponding value chips
- Below that: a big **Make** multi-select (`ant-select-selection--multiple`)
  containing potentially 70+ chips

**GOTCHA 1 — modal renders taller than the viewport.** The Make field's actual
search/typing input can be scrolled out of view even though the modal "looks"
fully visible in a screenshot at the top. Don't trust it. Find the modal's
scrollable ancestor and scroll it to bottom:
```js
document.querySelectorAll('.ant-select-selection--multiple') // returns 3 elements
// index 0 = Stock Type value chip(s), index 1 = Stock Sub Type chips, index 2 = MAKE (70+ chips)
const wrap = document.querySelector('.ant-modal-wrap.ant-modal-centered');
wrap.scrollTop = wrap.scrollHeight;
```
Then re-read `.getBoundingClientRect()` on the index-2 select's
`.ant-select-search__field` AFTER scrolling — coordinates before/after scroll differ.

**GOTCHA 2 — easy to type into the WRONG field.** All three multi-selects have
a `.ant-select-search__field` at the end of their chip row. If you click a
coordinate before scrolling/re-measuring, you can land in the Stock Type or
Stock Sub Type field instead of Make (cost one wasted round-trip in the verified
session — "Mercedes" got typed into field[0] first). Always identify the Make
field explicitly by array index (`document.querySelectorAll('.ant-select-selection--multiple')[2]`)
or by chip count (Make has by far the most chips), not by screen position alone.

**Typing + selecting:**
```python
api("/mouse", "POST", {"x": cx, "y": cy})   # click the Make field's search input (fresh coords post-scroll)
for ch in "Mercedes":
    api("/press", "POST", {"key": ch})      # one char at a time via /press, NOT /type (React autocomplete needs real keydown)
    time.sleep(0.06)
```
Tekion's own Make data is lowercase-suffix style — the dropdown match came back
as `"Mercedes-benz"` (not "Mercedes-Benz"). Find and click the matching dropdown
option by exact innerText:
```js
document.querySelectorAll('.ant-select-dropdown, [class*="dropdown"]')
  // filter offsetParent!==null && innerText.trim() === 'Mercedes-benz'
```
Click its rect center via `/mouse`. Verify it landed as a new chip in the
Make field (index 2), not accidentally in index 0/1.

## CRITICAL: TWO-LEVEL SAVE — both required or the change is lost
1. **Modal's own Save button** — inside `.ant-modal-content`, look specifically
   for the Save button whose parent IS the modal (there are ALSO page-level
   Cancel/Save buttons behind the modal at different coords — don't confuse them;
   query `document.querySelectorAll('.ant-modal-content')[0].querySelectorAll('button')`
   to scope correctly). Clicking this closes the modal and shows the updated chip
   list on the main Stock# Rules page.
2. **Page-level Save button** (bottom-right of the Stock# Rules page, NOT inside
   any modal) — you MUST also click this to actually persist to the backend.
   Skipping this step leaves the change looking correct in the current DOM but
   it is NOT saved server-side.

## Verification — TRUE REMOUNT required (don't trust same-render DOM)
Per the general Tekion save-verify trap (re-reading your own unsaved DOM after a
same-page action can produce a false positive): navigate AWAY to `/home`, then
back to `/vi/visettings`, **re-click the "Stock# Rules" tab** (page defaults back
to "Stock Type" on every fresh load), and re-read `document.body.innerText` for
the target Make string. Only a match after this full remount+re-tab-click proves
the fix persisted.

## Example (verified 2026-08-17, SCT dealer 876)
Ray Khandan (SCT) reported a Mercedes-Benz trade-in (VIN WD4PE8CDXJP584435, deal
267250) generated a random stock number instead of the expected "S..." prefix.
Tekion support agent Shivam Yadav correctly diagnosed "the make Mercedes-Benz is
not added in the vehicle inventory setup" but had no edit access, and relayed
manual instructions (9-dot → Vehicle Inventory Setup → Stock# Rules → last rule →
pencil → add Make → Save) which Jay executed directly. Confirmed missing from the
~72-make catch-all rule (`S5000` pattern), added "Mercedes-benz", saved at both
levels, verified via full remount. Future Mercedes-Benz trade-ins at SCT now get
proper S-prefixed stock numbers.

## Related skills
- `persistent-browser-server` — :9223 API reference, `/mouse` for React-ignoring
  elements, dealer-switch procedure
- `tekion-sitemap` — general nav reference (add `/vi/visettings` there too)
