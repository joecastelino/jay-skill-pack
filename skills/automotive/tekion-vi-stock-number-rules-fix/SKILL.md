---
name: tekion-vi-stock-number-rules-fix
description: Diagnose and fix Tekion Vehicle Inventory Stock# Rules (Vehicle Inventory Setup > Stock# Rules) when a vehicle gets a wrong/random stock number. Covers BOTH root causes — (1) a Make missing from a rule's Make multi-select so the wrong PREFIX is assigned, and (2) the rule matching for prefix but the NUMBER falling through to the global auto-increment counter. Includes the API-first diagnostic (OpenAPI vehicle-inventory timeline scan proving the fallback-counter signature), the subtype-coverage audit, /vi/visettings editing, the modal-scroll gotcha, the two-level Save requirement, and true-remount verification. Verified live at SCT (dealer 876) 2026-08-17 and 2026-08-24.
triggers:
  - stock number wrong
  - wrong stock number
  - vehicle inventory setup
  - stock# rules
  - trade-in stock number
  - stock number rule make missing
  - tekion stock sequence config
  - should have been decoded as
  - stock number decoded wrong
  - random stock number
---

# Tekion Vehicle Inventory Stock# Rules — Make-List Fix

## When to use
A dealer reports a trade-in vehicle got a random/wrong stock number instead of
the expected prefix pattern (e.g. any non-Toyota trade-in at a Toyota store should
get an "S..." stock number, but a specific Make like Mercedes-Benz didn't). Tekion
Support (Balla Meghana / Shivam Yadav pattern) will correctly diagnose "the make
is not added in the vehicle inventory setup" but their support agents can't touch
dealership settings — only Jay/Joe can fix it directly.

## Root cause pattern #1 — Make missing from the rule's Make list
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

## STEP ZERO — API first, browser second (added 2026-08-24)

**Do NOT open the browser first, and do NOT go spelunking in Hermes session logs
for prior context.** Both cost real time in the 2026-08-24 session. The OpenAPI
answers "what did this VIN actually get?" in one call:

```python
import sys; sys.path.insert(0,"/home/itadmin/tekion-api")
import tekion_client as tc
cfg = tc.load_config(); did = cfg["dealers"]["st"]      # dealers dict: ar/bc/bt/st/sv/tl/vc
out = tc.api_get(cfg, "/openapi/v4.0.0/vehicle-inventory", did,
                 {"count": 5, "vin": "<VIN>"}, retries=1)
# fields that matter: stockID, stockType, stockSubType, source.type,
#                     vehicleSpecification.make/model/year, createdTime, modifiedTime
```
Loop the same call over all 7 dealer IDs when you don't know which store the unit
landed in — it's ~2s total and beats asking.

**`createdTime` vs `modifiedTime` tells you whether a human renumbered it.** On the
2026-08-24 RAV4 the two were 13 seconds apart and never touched again, i.e. the
stock number you're looking at IS the one the rule engine assigned — nobody fixed
it by hand afterward.

### Building the stock-ID timeline (the thing that proves root cause #2)

`vehicle-inventory` caps at 100 rows/page and `page.from` is unreliable, so paginate
by **recursive time-window bisection** on `modifiedStartTime`/`modifiedEndTime`,
deduping on `id`, and query each status separately:

```python
def window(status, start, end, depth=0, acc=None):
    acc = acc if acc is not None else []
    out = tc.api_get(cfg, "/openapi/v4.0.0/vehicle-inventory", did,
        {"count":100,"status":status,"modifiedStartTime":start,"modifiedEndTime":end}, retries=1)
    total = out.get("meta",{}).get("total",0)
    if total == 0: return acc
    if total <= 100 or depth > 28 or end-start <= 1:
        acc.extend(out.get("data",[])); return acc
    mid = (start+end)//2
    window(status,start,mid,depth+1,acc); window(status,mid,end,depth+1,acc)
    return acc

seen = {}
for st in ("STOCKED_IN","SOLD","ON_HOLD","IN_TRANSIT"):
    for v in window(st, start_ms, end_ms): seen[v["id"]] = v
```
Filter to `stockType=="USED"` and `createdTime >= start`, sort by createdTime, and
print `date | stockID | stockSubType | source.type | make`. ~55 days of SCT used
inventory = 374 rows, ~77s. **NEVER put SOLD in the same `status:IN` filter as the
others** (same trap as the VI scraper — bare SOLD is a 48k archive that breaks
pagination).

## Root cause #2 — prefix is RIGHT, number falls through to the global counter

Discovered 2026-08-24 at SCT. This is a DIFFERENT failure from the missing-Make
case above and the 8/17 "Mercedes fix" did **not** address it.

**Signature:** the stock ID carries the correct alpha prefix from the matched rule,
but the numeric portion is nowhere near that rule's own sequence — instead it sits
exactly inside the store's **bare-numeric new-vehicle auto-increment stream**.

Worked example (SCT, dealer 876):

| Date | VIN | Got | Rule's own series |
|---|---|---|---|
| 08/17 15:12 | WD4PE8CDXJP584435 (Mercedes Sprinter) | **S15042** | S84xx |
| 08/24 12:19 | 5TDDSKFC8SS159289 (Sienna, Toyota trade, subtype *Used Vehicle Purchases*) | **CT15232** | NT29xx |

Proof: SCT's bare-numeric NEW stock IDs ran 15034 (8/15) → 15051 (8/19) → 15196
(8/20) → 15215 (8/22). **15042 and 15232 land dead inside that stream.** That's the
fallback `AUTO_INCREMENTING_NUMBERS` counter, not any Stock# rule.

Note the Sienna also got the wrong PREFIX (CT instead of NT for the
*Used Vehicle Purchases* subtype) — so a single unit can exhibit both failures.

**Diagnostic rule of thumb:** collect the store's bare-numeric stock IDs from the
same timeline scan. If the numeric part of the bad stock ID interleaves with them
chronologically, it's the fallback counter — stop looking at Make lists.

## Subtype-coverage audit (the gap that feeds the fallback counter)

Enumerate the stock subtypes actually IN USE from the timeline scan, then diff them
against the rule conditions on screen. SCT rules as of 2026-08-24:

```
New  | Car                                  -> C210001
New  | Suv | Truck/van                      -> T210001
Used | Used Cpo | Toyota                    -> CT20000
Used | Used Vehicle Purchases | Toyota      -> NT1000
Used | <~73 other makes>                    -> S5000
```
Live subtypes found in the data with **no matching rule**: `Used Vehicle Wholesale`
(+Toyota), `CPO- Gold`, `CPO- Silver`. Anything whose subtype has no rule row has
nothing to match and drops to the fallback counter. Always run this diff before
concluding "the Make list is fine, so the config is fine."

**Second anomaly worth flagging to Joe:** SCT is running **two CT counters in
parallel** — CT24xxx (CT24556, CT24558) and CT27xxx (CT27001 → CT27021) interleaved
by the minute on 8/21. One of them is not coming from the CT20000 rule.

## Reading stockRuleConfig from the API — and the dealer-context trap

The full VI setup JSON (including `stockRuleConfig`) comes back on
`GET /api/vi-setup/u/vi?langParam=en_US`. A bare in-page `fetch()` won't
authenticate, so arm an XHR hook and let the SPA fire it, then force a refetch via
`history.pushState` away and back (a full reload wipes the hook):

```js
// arm hook
window.__cap=[];const O=XMLHttpRequest.prototype.open,S=XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return O.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(b){this.addEventListener('load',()=>{
  try{window.__cap.push({u:this.__u,r:this.responseText.slice(0,300000)})}catch(e){}});
  return S.apply(this,arguments)};
// force refetch
history.pushState({},'','/home');window.dispatchEvent(new PopStateEvent('popstate'));
// ...wait, then...
history.pushState({},'','/vi/visettings');window.dispatchEvent(new PopStateEvent('popstate'));
// read
const h=(window.__cap||[]).filter(x=>x.u.includes('vi-setup/u/vi?lang'));
JSON.parse(h[h.length-1].r).data.stockRuleConfig
```

**TRAP THAT BURNED A TURN:** the payload is for whatever dealer the browser is
*currently* on, not the one you're investigating. On :9225 the context was TL (1092)
while the ticket was SCT (876) — the returned `stockRuleConfig.dealerId` was `"1092"`
with a single NEW-only condition, which looks alarmingly like "the used rules are
missing." **Always assert `stockRuleConfig.dealerId` equals your target dealer
before interpreting it.** Switch dealer through the UI pill first (setting
`localStorage.currentActiveDealerId` does not work).

`stockRuleConfig` shape:
- `conditions[]` — each `{applicabilityRule:{STOCK_TYPE:[...],...}, stockRules:[{type,format,ruleValues}], ruleCounts:{startingValue,currentCount}, locked}`
- `stockRuleTypeWeights` — the **priority weights** deciding which condition wins when
  several match: `RANGE:12, TRANSFERRED:11, MFR_MODEL_CODE:10, SOURCE:9,
  DEAL_VEHICLE_SOURCE:8, MAKE:7, YEAR:6, TRADE_OWNERSHIP_TYPE:5, MODEL:4,
  STOCK_SUBTYPE:3, BODY_CLASS:2, STOCK_TYPE:1`. Useful when two rules both match.
- `type:"AUTO_INCREMENTING_NUMBERS"` with `ruleCounts.currentCount` = the fallback
  counter behind root cause #2.

## STOP-and-ask discipline on this ticket type

Per Joe's never-guess rule: if the API record **disagrees with what the user saw on
their screen**, report both and ask — do not theorize. On 2026-08-24 the RAV4
(2T3RWRFV1SW263674) came back as **CT27021**, i.e. already CT-prefixed, while Joe
said "it should have been decoded as CT." Rather than invent a reconciliation, the
right move was: state what the API shows, present the fallback-counter pattern found
in the surrounding data as the real defect, and ask which stock number he actually
saw. Stay read-only until he answers.

## Related skills
- `persistent-browser-server` — :9223/:9225 API reference, `/mouse` for React-ignoring
  elements, dealer-switch procedure. **`/goto` does not exist — the endpoint is
  `/navigate`** (a `/goto` POST returns HTTP 404 and looks like a dead server).
- `tekion-vi-api-migration` — the OpenAPI vehicle-inventory two-query pattern and the
  SOLD-status pagination trap reused by the timeline scan above
- `tekion-sitemap` — general nav reference (`/vi/visettings` is listed there)
