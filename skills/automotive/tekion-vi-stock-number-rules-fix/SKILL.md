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

## ⚡ STEP ZERO — read `stockRuleConfig` from the API, don't eyeball the UI

The UI list only shows condition labels + a sample stock #. The **real** diagnostic
data (attribute weights, per-rule counters, exact lowercase make lists, subtype
lists) is in the settings payload. Get it via XHR hook on the persistent browser:

```python
# 1) arm the hook (guard with a flag so re-running doesn't double-wrap)
hook = """(()=>{window.__cap=[];const O=XMLHttpRequest.prototype.open,S=XMLHttpRequest.prototype.send;
if(!window.__hk){XMLHttpRequest.prototype.open=function(m,u){this.__u=u;return O.apply(this,arguments)};
XMLHttpRequest.prototype.send=function(b){const s=this;this.addEventListener('load',()=>{try{
  if(s.__u&&s.__u.indexOf('vi-setup')>-1)window.__cap.push({u:s.__u,r:s.responseText.slice(0,400000)})
}catch(e){}});return S.apply(this,arguments)};window.__hk=1;}return 'ok'})()"""
api("/eval","POST",{"js":hook})

# 2) drive the SPA with pushState — NOT /navigate (see pitfall below)
api("/eval","POST",{"js":"history.pushState({},'','/home');window.dispatchEvent(new PopStateEvent('popstate'));'ok'"}); sleep(3)
api("/eval","POST",{"js":"history.pushState({},'','/vi/visettings');window.dispatchEvent(new PopStateEvent('popstate'));'ok'"}); sleep(8)

# 3) read it — endpoint is /api/vi-setup/u/vi?langParam=en_US
js = """(()=>{const h=(window.__cap||[]).filter(x=>x.u.indexOf('vi-setup/u/vi?lang')>-1);
if(!h.length)return 'none';const j=JSON.parse(h[h.length-1].r);const d=j.data||j;
return JSON.stringify({dealer:d.dealerId,rules:d.stockRuleConfig,types:d.typeSetting}).slice(0,16000)})()"""
```

**PITFALL — `/navigate` kills the hook.** A real page load wipes the injected
override, so `window.__cap` comes back `[]` / `'none:[]'`. Only `history.pushState`
+ `PopStateEvent` keeps the hook alive. Cost a wasted round-trip.

**PITFALL — verify `dealerId` INSIDE the response, not just localStorage.** The
:9225 browser drifts dealers between turns. I pulled a `stockRuleConfig` that
looked bizarre (one lone NEW auto-increment rule, no used rules at all) and nearly
reported it as SCT's — it was **TL (1092)**. Different stores have wildly different
rule sets. Always assert `d.dealerId == expected` before analyzing.

## How rules actually resolve — WEIGHTED SPECIFICITY, not row order

`stockRuleConfig.stockRuleTypeWeights` defines the resolution order. Observed at SCT:

```
STOCK_TYPE 1 · BODY_CLASS 2 · STOCK_SUBTYPE 3 · MODEL 4 · TRADE_OWNERSHIP_TYPE 5
YEAR 6 · MAKE 7 · DEAL_VEHICLE_SOURCE 8 · SOURCE 9 · MFR_MODEL_CODE 10
TRANSFERRED 11 · RANGE 12
```

The on-screen "Conditions Priority" column reflects this. A rule only fires when
**every** attribute in its `applicabilityRule` matches. So a rule requiring
`STOCK_TYPE + STOCK_SUBTYPE + MAKE` needs all three populated **at the moment the
stock # is stamped** (record creation) — see the order-of-operations trap below.

## TWO SEPARATE DEFECTS — wrong PREFIX vs wrong NUMBER

Joe's phrasing ("it should have been decoded as CT", "they added the CT") maps to
the second one. Diagnose which you have BEFORE editing anything:

**Defect A — wrong/missing PREFIX.** A Make or Subtype is absent from the rule's
multi-select, so the vehicle matches no rule. Fix = add the value (procedure below).

**Defect B — the rule NEVER FIRED and a human typed the prefix by hand.** This is
invisible in the UI and is the one that keeps recurring. **The tell: compare each
rule's `ruleCounts.currentCount` against live stock numbers.**

```
SCT rule 3:  CT, startingValue 20000, currentCount 3161  -> would issue CT23161
SCT live:    CT24558, CT27021                            -> nowhere near it
SCT rule 4:  NT, startingValue 1000,  currentCount 1481  -> would issue NT2481
SCT live:    NT2946                                      -> nowhere near it
```

Corroborate with the **bare-numeric global fallback stream** — when no rule matches,
Tekion issues a plain incrementing number with no prefix. Sort recent inventory by
`createdTime` and look for stock IDs sitting in one continuous numeric series:

```
15034 (8/15) · 15042 (8/17) · 15051 (8/19) · 15121 · 15155 · 15196 (8/20) · 15215 (8/22) · 15232 (8/24)
```

Any "prefixed" stock # whose digits fall inside that stream (`S15042`, `CT15232`)
is a hand-typed prefix on a fallback number — proof the rule didn't fire. Pull the
data via OpenAPI `/openapi/v4.0.0/vehicle-inventory` (time-bisect on
`modifiedStartTime`/`modifiedEndTime`, filter `stockType == USED`, sort by
`createdTime`) and print `stockID / stockSubType / source.type / make`.

Bonus tell: two parallel counters for the same prefix (SCT had CT24xxx **and**
CT27xxx interleaved by the minute on 8/21) — one of them isn't coming from a rule.

## THE ORDER-OF-OPERATIONS ROOT CAUSE — `vehicleSubTypeMandatory`

Read `typeSetting.vehicleSubTypeMandatory` from the same payload. At SCT it was
**`null`** (the "Stock SubType is Mandatory" toggle on the Stock Type tab is OFF).

Every used-vehicle rule requires `STOCK_SUBTYPE`. If subtype is blank when the
record is created, **no used rule can match, no matter how many subtypes you add
to the rule.** It falls to the global counter and staff type the prefix on after.

So the correct fix ORDER is:
1. Turn **"Stock SubType is Mandatory"** ON (Stock Type tab) — forces subtype at creation.
2. THEN add the missing subtypes/makes to the rule.

Reverse that order and the new values still match nothing.

**KNOWN GAP — STOP AND ASK (never-guess rule).** I have NOT verified whether Tekion
re-evaluates the stock rule when subtype is filled in *after* creation, or stamps
once and never revisits. If it's stamp-once, mandatory-at-creation is the only thing
that works. Confirm via a controlled test (create one used vehicle with subtype set
at creation vs. one set after) or a Tekion ticket — do not assert either way.

### 2026-08-25 LIVE REPRODUCTION — the rules are BYPASSED, not misconfigured

Joe ran an unsaved Add-Vehicle draft at SCT (876), VIN `2T3W1RFV7RW336932`,
2024 Toyota RAV4 XLE, and screenshotted the form. On screen simultaneously:

```
Stock Type    = Used Vehicle        ✅
Stock Subtype = Used CPO            ✅   (Certified Pre-Owned checked)
Make          = Toyota              ✅
Body Class    = SUV
Stock #       = 15247               ❌   should have been CT24608
```

That is an **exact, complete match for CT rule #3** (`USED` + `Used CPO` + `toyota`)
and it still produced a bare fallback number. `15247` is the next entry in SCT's
bare global stream (…15215 8/22 · 15232 8/24 · **15247 8/25**).

**Conclusion: the stock # is stamped ONCE at record init / VIN decode — before Stock
Type and Sub Type are selected. At that instant no USED rule can match (all three
require STOCK_SUBTYPE + MAKE), so it falls to the global counter. Selecting the
subtype a second later does NOT re-trigger rule evaluation.** This is why adding
`CPO- Gold` / `CPO- Silver` to the CT rule (done 8/25) changed nothing — the rule is
never consulted regardless of its contents.

**Corollary for triage:** a "the rule is missing X" edit can NEVER fix this class of
ticket. Verify the *timing* before touching any multi-select.

**Still untested (ask Joe to click it, don't assert):** the **refresh/regenerate icon
next to the Stock # field** on the Add-Vehicle form. If clicking it with Type+Subtype+
Make already populated flips the number into the rule's series, then stamp-once is
confirmed and the remedy is procedural (`vehicleSubTypeMandatory` ON + train staff to
hit refresh after setting subtype). If it stays in the bare stream, the rule genuinely
fails to match and the match payload needs investigation.

**Verifying an unsaved draft did no damage:** query the VIN across all 7 dealers via
`/openapi/v4.0.0/vehicle-inventory` — 0 hits fleet-wide = nothing was written.

## CROSS-CHECK: every configured subtype must appear in some rule

`typeSetting.vehicleTypes[].subTypes[]` lists what staff can actually pick. Diff it
against the subtypes referenced across `stockRuleConfig.conditions[].applicabilityRule.STOCK_SUBTYPE`.
Anything present in the first list and absent from the second is a **guaranteed
permanent fallback**. At SCT (2026-08-24):

| Subtype | In a rule? |
|---|---|
| Used Vehicle Purchases | ✅ NT rule |
| Used Vehicle Wholesale | ⚠️ S rule only — 73 non-Toyota makes, **no Toyota** |
| Used CPO | ✅ CT rule |
| **CPO- Gold** | ❌ none |
| **CPO- Silver** | ❌ none |

Gold/Silver were live in production data (CT24156/24157/24163/24198/24201/24225/24395)
and had matched nothing since the day they were created.

## ⚠️ BEFORE ENABLING A DORMANT RULE — COUNTER COLLISION

If a rule has never fired, its counter is far BELOW the numbers already in use.
Turning it on makes it issue duplicates (SCT CT would start at CT23161 while
CT24558/CT27021 already exist; NT would start at NT2481 vs live NT2946). **Bump
`startingValue` / the sequence above the highest in-use number first.** Flag this
to Joe as part of any "make the rule work" plan.

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

## READ THE CONFIG BY API FIRST — don't diagnose off the rendered list

The rendered Stock# Rules list shows only `Stock Type | Sub Type | Make` chips and a
sample stock #. The REAL config (including each rule's live counter) comes from the
SPA's own fetch. Arm an XHR hook on :9225/:9223 then pushState away and back
(`/home` → `/vi/visettings`), and read `vi-setup/u/vi?langParam=en_US`:

```js
// response.data.stockRuleConfig
{ conditions: [ { applicabilityRule:{STOCK_TYPE,STOCK_SUBTYPE,MAKE,BODY_CLASS},
                  stockRules:[{type:'LETTERS',ruleValues:{LETTERS:['CT']}},
                              {type:'AUTO_INCREMENTING_NUMBERS',ruleValues:{...}}],
                  ruleCounts:{startingValue:{AUTO_INCREMENTING_NUMBERS:'20000'},
                              currentCount:4607} } ],
  stockRuleTypeWeights:{STOCK_TYPE:1,BODY_CLASS:2,STOCK_SUBTYPE:3,MODEL:4,
    TRADE_OWNERSHIP_TYPE:5,YEAR:6,MAKE:7,DEAL_VEHICLE_SOURCE:8,SOURCE:9,
    MFR_MODEL_CODE:10,TRANSFERRED:11,RANGE:12} }
```
Also grab `response.data.typeSetting` — it lists every configured sub-type per stock
type plus `vehicleSubTypeMandatory`.

**Matching is WEIGHTED ATTRIBUTE SPECIFICITY, not row order.** The on-screen
"Conditions Priority" column reflects `stockRuleTypeWeights`. A rule only applies if
ALL of its `applicabilityRule` attributes match; more/heavier attributes win.

**HOW TO VERIFY A RULE IS ACTUALLY FIRING (the critical check):**
`startingValue + currentCount` = the next number that rule will issue. Compare it to
live stock numbers from the OpenAPI vehicle-inventory pull. If they line up, the rule
is firing. Example (SCT 2026-08-24, all five verified healthy):

| Rule | start + currentCount | live stock# |
|---|---|---|
| C (New/Car) | 1 + 6887 → C26**6887** | C266842 ✅ |
| T (New/SUV) | 1 + 11172 → T26**11172** | T2611157 ✅ |
| CT (Used CPO/toyota) | 20000 + 4607 → CT**24607** | CT24558 ✅ |
| NT (Used Purch/toyota) | 1000 + 1949 → NT**2949** | NT2946 ✅ |
| S (73 makes) | 5000 + 3457 → S**8457** | S8456 ✅ |

⚠️ **A STALE XHR CAPTURE WILL LIE TO YOU AND PRODUCE A FALSE ROOT CAUSE.** In this
session an early capture returned much lower counts (CT 3161, NT 1481, S 2587) for the
same dealer 876, which made every rule look like it had never fired — leading to a
wrong "the rules never match, humans hand-type the prefix" diagnosis that had to be
retracted to Joe. **Always re-arm `window.__cap=[]` fresh, force a real refetch, and
take the LAST matching response — then sanity-check the derived next-number against
live inventory before concluding anything.**

## Second failure mode: SUB-TYPE NOT COVERED BY ANY RULE

Every USED rule requires `STOCK_SUBTYPE` to match. Compare `typeSetting.vehicleTypes[]
.subTypes[]` against the union of all `applicabilityRule.STOCK_SUBTYPE` values. Any
sub-type in use but absent from every rule can NEVER match → falls through to the bare
global auto-increment counter, and staff hand-type the prefix afterward.

SCT case 2026-08-24: sub-types `CPO- Gold` and `CPO- Silver` were live (CT24156,
CT24163, CT24198, CT24225, CT24395) but the CT rule listed only `Used CPO`. Joe added
both to the CT rule's Sub Type multi-select; verified persisted via true remount:
`STOCK_SUBTYPE: ["Used CPO","CPO- Gold","CPO- Silver"]`. Still-open gaps at SCT:
`Used Vehicle Wholesale` + Toyota is in NO rule (rule 5 covers wholesale for the 73
non-Toyota makes only), and `vehicleSubTypeMandatory` is `null` — if sub-type is blank
at record-creation time no USED rule can match at all.

**UNVERIFIED — stop and ask, do not assert:** whether Tekion re-evaluates the stock
rule when sub-type is filled in AFTER creation, or stamps the number once and never
revisits. This determines whether rule edits alone fix the problem or the sub-type
must be mandatory at creation. Settle it with a controlled test, don't guess.

**Tell-tale of a fallback number:** it sits in the bare-numeric series the store's
un-ruled records use (SCT: 15034 8/15 → 15042 → 15051 → 15121 → 15155 → 15196 →
15215 → 15232 8/24). `S15042` and `CT15232` are that counter with a prefix typed on.
A parallel out-of-band series (SCT `CT27001`→`CT27021`, alongside healthy `CT24xxx`)
is likewise NOT rule-issued — investigate its origin separately.

**Before switching a dormant rule live, bump its starting value.** If a rule's derived
next-number is BELOW stock numbers already in use, it will issue collisions.

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

## Example (2026-08-17, SCT dealer 876) — ⚠️ THIS FIX WAS ONLY HALF THE PROBLEM
Ray Khandan (SCT) reported a Mercedes-Benz trade-in (VIN WD4PE8CDXJP584435, deal
267250) generated a random stock number instead of the expected "S..." prefix.
Tekion support agent Shivam Yadav correctly diagnosed "the make Mercedes-Benz is
not added in the vehicle inventory setup" but had no edit access, and relayed
manual instructions (9-dot → Vehicle Inventory Setup → Stock# Rules → last rule →
pencil → add Make → Save) which Jay executed directly. Confirmed missing from the
~72-make catch-all rule (`S5000` pattern), added "Mercedes-benz", saved at both
levels, verified via full remount.

**CORRECTION (2026-08-24) — the numbering was never fixed.** That Mercedes got
**S15042**, and 15042 sits inside SCT's bare global fallback stream
(15034 → 15042 → 15051 → 15196 → 15215 → 15232). The "S" was hand-typed onto a
fallback number; the S rule never fired. Adding the make only made the vehicle
*eligible* for the rule — it did nothing about the rule not matching at stamp time
(`vehicleSubTypeMandatory: null`). A week later Joe reported "same thing happened"
on VIN 2T3RWRFV1SW263674, and a Sienna trade the same day got **CT15232** — same
fallback stream, hand-typed prefix, and *wrong prefix too* (subtype was Used Vehicle
Purchases → should have been NT, not CT).

**LESSON: never close a stock# ticket on a prefix edit alone.** Always verify the
rule's `ruleCounts.currentCount` actually advanced and that new stock numbers land
in the rule's own series — not the global stream. A prefix that merely *looks* right
on screen proves nothing about which mechanism produced it.

## Joe-interaction notes
- Joe's shorthand for defect B is **"they added the CT"** / "it should have been
  decoded as CT" — he means a human typed the prefix, not that the rule mislabeled.
  Take that literally; it's a precise diagnosis, not a vague complaint.
- He challenged my initial row-order framing with **"but isn't this an order of
  operations rule"** — he was right, and the answer is `stockRuleTypeWeights` +
  the stamp-at-creation timing. Pull the weights before theorizing about priority.
- He asks **"so what do you want me to fix"** — he wants a short, ordered, concrete
  edit list (what field, what screen, what order), not an essay. Lead with the edits,
  keep caveats short and clearly separated from the actionable part.
- Stay read-only until he says go on live VI settings; state plainly that nothing
  was changed.

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
