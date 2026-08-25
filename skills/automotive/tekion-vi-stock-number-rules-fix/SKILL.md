---
name: tekion-vi-stock-number-rules-fix
description: Diagnose and fix Tekion Vehicle Inventory stock-number problems. ⚠️ ROOT CAUSE SETTLED 2026-08-25 — the stock # is stamped at VIN DECODE from the bare global auto-increment counter, before stockType/stockSubType exist, and is never re-evaluated. FOUR UI remedies were tested and FAILED (add Make, add SubTypes, vehicleSubTypeMandatory ON, reverse entry order) — this is a Tekion platform defect, NOT a dealership misconfiguration, so do not propose Stock# Rules edits. Real fix = OpenAPI PUT /vehicle-inventory/{id} (stockID is writable) driven by the detector sct_stock_audit.py. Also covers the Add-Vehicle DOM map (Stock# field id is <dealer>_PRODUCTION; SubType is a radio group; custom non-native Vehicle Type radios), the :9223 cron-pipeline browser-contention trap, CT27xxx = human quarantine tag at SCT, and the model-year-prefix / pre-VIN-factory-order false positives. Verified live at SCT (876).
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

⚠️ **RESOLVED 2026-08-25 — CT27xxx at SCT is a HUMAN QUARANTINE TAG, not a counter.**
Joe: *"27 came in from a manual input, just so we can identify which VINs were broken."*
Staff renumber a broken unit into the CT27xxx band to mark it. **Consequence for triage:
the bare-numeric stream UNDER-COUNTS the damage.** Most affected units never sit in the
bare series long enough to be seen — they get hand-moved into the tag band. To size the
real blast radius you must count `CT27xxx` (tagged) **+** still-bare `15xxx` (untagged).
Before treating any out-of-band series as a mystery second counter, **ASK — a store may
have a manual convention you can't infer from the data.**

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

**⛔ RESOLVED 2026-08-25 — ANSWERED, AND THE MANDATORY-SUBTYPE FIX IS DISPROVEN.**
Tekion never re-evaluates the stock rule, because on the Add-Vehicle path it never
evaluates it at all — the number is stamped at VIN DECODE. Turning
`vehicleSubTypeMandatory` ON was tested live at SCT and did NOT fix it
(Joe: "it still doesn't work"). Text retained only to document the dead end.
See "2026-08-25 DEFINITIVE" below before acting on anything in this section.

## EXECUTING THE FIX — turning ON "Stock SubType is Mandatory" (done live 2026-08-25, SCT 876)

Verified click-path and the traps hit along the way:

```python
# 0) ALWAYS check where the browser actually is first — it drifts between sessions
#    :9223 was sitting on BC (1251) while the ticket was SCT (876).
curl -s :9223/eval -d '{"js":"JSON.stringify({url:location.href,dealer:localStorage.currentActiveDealerId})"}'
```

**TRAP 1 — a Tekion announcement modal silently eats the dealer-pill click.**
A *"Welcome to Service 3.0 🚀"* modal (buttons: `Knowledge Base` / `Got It!`) was
overlaying /home. `/mouse` on the dealer pill returned success and did nothing;
the popover query came back `[]` twice with no error. **A `[]` popover result after
clicking the pill means something is covering it — screenshot before re-trying.**
Dismiss by finding the childless element whose innerText matches `/^Got It!?$/i`
and clicking its rect center, then also strip Pendo:
```js
document.querySelectorAll('[id*=pendo],[class*=pendo]').forEach(e=>e.remove());
```

**TRAP 2 — `/screenshot` on the persistent browser returns JSON, not a PNG.**
`curl -o shot.png` yields `JSON text data` and `vision_analyze` rejects it with
*"Only real image files are supported."* Decode first:
```python
import json, base64
open('/tmp/real.png','wb').write(base64.b64decode(json.load(open('/tmp/shot.json'))['screenshot']))
```

**Dealer switch** (after modal cleared): `/mouse` (1120,31) → rows are
`[class*="root_dealerInfoItem_container"]`, filter `offsetParent!==null`, 8 rows at
x≈1095 starting y=157, 42px pitch (AR/AM/BC/BT/**ST y=325**/SV/TL/VC). Verify
`localStorage.currentActiveDealerId === '876'` AND header innerText says the store.

**The toggle itself** — `/vi/visettings` → **Stock Type** tab (x139,y158; page always
defaults here on load, which for once is the tab we want):
- Label `Stock SubType is Mandatory` at x88,y232
- Its `.ant-switch` is at **x564,y229** — locate it by matching switch `y` against the
  label's `y` (±20px), NOT by index. There are 4+ switches on this page (New Vehicle,
  Used Vehicle, etc.) and index order is not stable.
- Click center ≈ (578,240) → re-read `aria-checked`, expect `true` + class
  `ant-switch ant-switch-checked`
- **Page-level Save** at (1211,687), `ant-btn root_button_primaryButton__*`
  (only ONE Save button on this tab — no modal, so unlike the Stock# Rules edit this
  is a single-level save, not two-level)
- Toast fires immediately: `"Success / Settings saved successfully"` (poll ~0.7s
  intervals; it appeared at the first poll)

**VERIFY THREE WAYS — the toggle's own state is the weakest evidence:**
1. Success toast within ~3s (no toast = save failed, re-submit)
2. True remount: `/navigate` to `/home`, back to `/vi/visettings`, re-read `aria-checked`
3. **Server payload — the only real proof.** Arm the XHR hook, pushState `/home` →
   `/vi/visettings`, read `vi-setup/u/vi?lang`:
```json
{"dealer":"876","subTypeMandatory":{"enable":true,"value":null,"registered":false,"locked":false}}
```
Note the shape: it is an **object with `enable`**, NOT a bare boolean. Pre-fix this
key was `null` entirely. Assert `dealer` matches your target in the same read.

**⛔ RESOLVED 2026-08-25 — ANSWERED, AND THE MANDATORY-SUBTYPE FIX IS DISPROVEN.**
Tekion never re-evaluates the stock rule, because on the Add-Vehicle path it never
evaluates it at all — the number is stamped at VIN DECODE. Turning
`vehicleSubTypeMandatory` ON was tested live at SCT and did NOT fix it
(Joe: "it still doesn't work"). Text retained only to document the dead end.
See "2026-08-25 DEFINITIVE" below before acting on anything in this section.

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

### THE STRONGEST SINGLE PIECE OF EVIDENCE — the same-day twin

The cleanest proof this is a race and not config is **two identical vehicles on the
same day getting different treatment**. SCT 8/22: one NEW Toyota Sienna got bare
`15215` (11:17) while another NEW Toyota Sienna got correct `T2611163` (11:48) —
31 minutes apart, same make/model/stock type, same rule. Config cannot produce a
different result for identical inputs; a timing race can. **Hunt for a twin pair in
the timeline scan — it converts "I think it's a race" into proof, and it's the
single most persuasive line in a Tekion ticket.**

⚠️ **ACCURACY DISCIPLINE — get the bare-vs-prefixed classification right.**
While briefing Walter I described `15215` as bare *and* separately implied nearby
`15230/15232` were the same untagged class; in fact `CT15230` and `CT15232` already
carry hand-typed prefixes, i.e. they are *tagged* records, not raw fallback ones.
The distinction matters because it changes the counts you quote. **When quoting the
bare stream, filter strictly on `^\d{5}$` (no alpha prefix at all) and list the
hand-prefixed ones separately** — don't blend them into one number.

**Still untested (ask Joe to click it, don't assert):** the **refresh/regenerate icon
next to the Stock # field** on the Add-Vehicle form. If clicking it with Type+Subtype+
Make already populated flips the number into the rule's series, then stamp-once is
confirmed and the remedy is procedural (`vehicleSubTypeMandatory` ON + train staff to
hit refresh after setting subtype). If it stays in the bare stream, the rule genuinely
fails to match and the match payload needs investigation.

**Verifying an unsaved draft did no damage:** query the VIN across all 7 dealers via
`/openapi/v4.0.0/vehicle-inventory` — 0 hits fleet-wide = nothing was written.

## 2026-08-25 — SubType-Mandatory turned ON at SCT + Add-Vehicle form facts

`vehicleSubTypeMandatory` flipped to `{enable:true}` at SCT (876). Procedure that
worked: `/vi/visettings` → **Stock Type** tab (leftmost, ~139,158) → label
"Stock SubType is Mandatory" at y≈232 with its `.ant-switch` at x≈564 same row →
click switch center (578,240) → **page-level Save** (single primary btn ~1211,687) →
toast "Settings saved successfully". Verify by remount AND by the `vi-setup/u/vi`
payload (`typeSetting.vehicleSubTypeMandatory.enable === true`), not the toggle alone.

### Add Vehicle form — verified DOM facts
- **Correct nav:** 9-dot grid (30,31) → search "Vehicle Inventory" → click the
  result at (449,222) → `/vi/vehicles` → **"Add Vehicle"** button top-right
  (~1202,89) → lands on **`/vi/vehicle/new`**.
- **GUESSED URLS ARE DEAD ENDS.** `/vi/inventory/add-vehicle`, `/vi/addvehicle`,
  `/vi/inventory`, `/vi/inventory/list` all render a BLANK content area while
  returning HTTP 200 and echoing the URL back from `location.href`. `innerText`
  length ~106 (just chrome/nav) is the tell. Always go through the VI module.
- **Field IDs are `<dealerId>_<FIELD>`:** `876_VIN`, `876_MAKE`, `876_MODEL`,
  `876_YEAR`, `876_BODY_CLASS`, `876_SOURCE`, `876_MILEAGE`.
  ⚠️ **Stock # field id is `876_PRODUCTION`** — NOT `*_STOCK*`. A `/stock/i` scan
  over input ids/names finds it only by accident. Label "Stock #" sits at ~(827,815).
- **✅ STAMP POINT CONFIRMED = VIN DECODE (2026-08-25, Joe verified live).**
  Two observations pin it: (a) on a freshly opened `/vi/vehicle/new`,
  `document.getElementById('876_PRODUCTION').value === ''` — blank at mount, so
  NOT stamped at init; (b) Joe pasted VIN `2T3W1RFV7RW336932` with nothing else
  filled in and the Stock # **immediately populated as a bare `152xx`**, without
  saving. Therefore the number is assigned **at VIN decode**, not at init and not
  at save. Earlier "stamped at init" claims in this skill were WRONG — corrected.

  This one fact explains every failed remedy:
  | Remedy tried | Why it did nothing |
  |---|---|
  | Add Make to rule (8/17) | rule not consulted at decode — Type/SubType empty |
  | Add CPO-Gold/Silver subtypes (8/24) | same |
  | `vehicleSubTypeMandatory` ON (8/25) | enforces before **save**; stamp already happened at **decode** |

  It also explains the intermittency (depends entirely on whether the operator set
  Type/SubType before pasting the VIN) and the 8/21 cluster of nine (one person,
  one habit, nine cars in a row).

- **⛔ `vehicleSubTypeMandatory: true` is RULED OUT as a fix.** Joe tested after it
  was enabled — still bare `152xx`. Left ON anyway (harmless, cleaner data entry).
  Do not re-propose it.

- **NEXT TEST (queued, unresolved at time of writing): reversed entry order.**
  Select Used Vehicle + Used CPO **first**, then paste the VIN. If decode evaluates
  rules against whatever is already populated, this should yield `CT245xx` and the
  fix is purely procedural. If it still yields bare `152xx`, decode ignores the
  rules entirely = genuine Tekion defect, file with the 12 CT27xxx VINs as the
  reproduction set. Script: `/tmp/reverse_test.py` (waits for a free browser window,
  never saves the draft).
- Vehicle Type radios are custom divs `vi_cargoradio_label_container__*` /
  `vi_cargoradio_main_container__*` (New ~482,659 · Used ~622,659). No
  `input[type=radio]` exists. `/mouse` on the label container did NOT flip the
  selection in testing (vision confirmed New Vehicle still selected) — the real
  hit target is still unidentified. **No Stock SubType dropdown renders until
  Used Vehicle is actually selected**, so failing this click blocks the whole test.

### ⚠️ BROWSER CONTENTION — :9223 is NOT exclusively yours
`crontab`: `*/15 * * * * /home/itadmin/caliber-ops/scripts/cron-pipeline.sh` drives
the **same** :9223 browser. Mid-test it will navigate to `/home` and switch dealers
(saw 876 → TL/1092 twice inside one session), silently invalidating coordinates and
returning `None` from element reads. Symptoms: `location.href` suddenly `/home`,
queries returning `[]` for elements that existed a second earlier.
**Before any multi-step :9223 form work:** `pgrep -fa cron-pipeline`, check
`ls -la /tmp/caliber-pipeline.lock` mtime, and either wait for a fresh 15-min window
or run the entire interaction as ONE uninterrupted script. Better: use :9225.

## AUTOMATION PATH — `stockID` IS WRITABLE VIA OpenAPI

The durable fix is not making the UI rule fire — it's correcting/assigning the
number programmatically. Confirmed in the specs:

- `PUT /vehicle-inventory/{vehicle-inventory-id}` (spec file
  `vehicle-inventory__update-a-vehicle.json`). Schema `UpdateVehicleInventory`
  declares only `pricingDetails` in `properties` but `allOf`-inherits
  `BaseVehicleInventory`, and **the official request example includes
  `"stockID": "10N1223"`, `"stockSubType"`, `"stockType"`** — so stock number is
  a writable field.
- `POST /vehicle-inventory` (`create-vehicles`) likewise accepts `stockID` /
  `stockType` / `stockSubType` on create.

Design: OpenAPI-only watcher (no browser) that polls recent inventory, flags any
`stockID` matching the bare-fallback pattern, derives the correct prefix from
`stockType`+`stockSubType`+`make` using the same rule table, and PUTs the right
number. Removes the human ordering dependency entirely. **Requires Joe's explicit
go before any live write** — and confirm write scope is actually granted (the pilot
app version has historically 403'd endpoints that exist in the specs). Test against
sandbox `api-sandbox.tekioncloud.com` dealer `techmotors_4_0` first.

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

## 🔴 2026-08-25 DEFINITIVE — STAMPED AT VIN DECODE. THE UI CANNOT FIX THIS.

**Read this section FIRST. It supersedes every UI-side remedy above.**

Observed directly on `/vi/vehicle/new` at SCT (876), draft never saved:

| Step | Stock # |
|---|---|
| Form opens | `''` (blank) |
| Select Stock Type = Used Vehicle | `''` |
| (subtype attempted) | `''` |
| Type VIN, before blur | `''` |
| **Tab → VIN decode fires** | **`15256`** ← stamped HERE |
| +6s / +12s / +18s | `15256` (never revised) |

**The number is assigned at VIN decode, from the bare global auto-increment
counter, and is never re-evaluated afterward.** At decode time stockType /
stockSubType / bodyClass are not yet committed, so no Stock# rule can match.
Everything downstream — picking Used, picking a subtype, saving — happens too late.

### Four remedies TESTED AND FAILED — do not retry these
1. **Add missing Make to the rule** (8/17, Mercedes-Benz) — vehicle still got `S15042`.
2. **Add missing SubTypes to the CT rule** (8/24, CPO-Gold/Silver) — no change.
3. **`vehicleSubTypeMandatory` = ON** (8/25) — Joe: *"it still doesn't work."*
   It enforces subtype before **save**; the stamp already happened at **decode**.
4. **Reverse the entry order** (Type+SubType before VIN) — Joe: *"no, that doesn't
   work."* Confirms decode does not consult the rules even when the attributes ARE
   present.

**Conclusion: this is a Tekion platform defect, not a dealership misconfiguration.**
Stop proposing Stock# Rules edits. File a ticket and automate the correction.

### Each decode BURNS a counter value
`15247` (Joe's abandoned draft) and `15256` (mine) were both consumed by drafts that
were never saved. Harmless, but it explains gaps in the bare series — don't read a
gap as a deleted/hidden vehicle.

## Add Vehicle form — verified DOM reference (SCT 876)

- **Nav:** 9-dot grid (30,31) → search "Vehicle Inventory" → result at (449,222) →
  `/vi/vehicles` → **Add Vehicle** button (~1202,89) → `/vi/vehicle/new`.
- **GUESSED URLS SILENTLY RENDER BLANK.** `/vi/inventory/add-vehicle`,
  `/vi/addvehicle`, `/vi/inventory`, `/vi/inventory/list` all return 200 and echo
  back from `location.href` while showing an empty content area.
  Tell: `document.body.innerText.length` ≈ 106 (nav chrome only). Always nav via the module.
- **Field ids are `<dealerId>_<FIELD>`:** `876_VIN`, `876_MAKE`, `876_MODEL`,
  `876_YEAR`, `876_BODY_CLASS`, `876_TRIM`, `876_SOURCE`, `876_MILEAGE`.
  ⚠️ **Stock # is `876_PRODUCTION`** — not `*_STOCK*`. A `/stock/i` id scan misses it.
  ⚠️ Ids are dealer-prefixed, so a mid-script dealer drift makes every lookup return
  `null` — assert `localStorage.currentActiveDealerId` before reading fields.
- **Vehicle Type is NOT a real radio.** Custom divs
  `vi_cargoradio_label_container__*` inside `vi_cargoradio_main_container__*`
  (New ≈482,659 · Used ≈622,659). No `input[type=radio]` exists.
  `/mouse` on the text label is a NO-OP. What works: climb to `main_container`,
  dispatch the full chain `pointerdown,mousedown,pointerup,mouseup,click` as real
  `MouseEvent`s, then `/mouse` the icon area (~25px ABOVE label center).
  Verify via the Overview header flipping to `Stock Type: USED` — the vision check
  on the radio glyph is unreliable.
- **Stock SubType is a RADIO GROUP, not a dropdown** — renders only after Used
  Vehicle is selected, inline at y≈764: `Used Vehicle Purchases` (502) ·
  `Used Vehicle Wholesale` (690) · `Used CPO` (837) · `CPO- Gold` (941) ·
  `CPO- Silver` (1049). These ARE `.ant-radio-input`, reachable via
  `i.closest('label').innerText`. **`/mouse` alone did not check them** — all five
  stayed `chk:false`. Needs the same synthetic MouseEvent chain. **Always re-read
  `.checked` after clicking; a silent no-op here invalidates the whole test.**

## ⚠️ BROWSER CONTENTION — :9223 is NOT exclusively yours
`*/15 * * * * /home/itadmin/caliber-ops/scripts/cron-pipeline.sh` drives the SAME
:9223 browser and runs **~7 of every 15 minutes**. Mid-test it navigates to `/home`
and switches dealer (saw 876 → TL/1092 three times in one session), silently
invalidating coordinates; element reads start returning `[]`/`None`.

- Check first: `pgrep -f cron-pipeline.sh` and `stat -c '%y' /tmp/caliber-pipeline.lock`.
- :9225 was **logged out**, and the persistent-browser server exposes **no**
  `/cookies`, `/storage-state`, or `/state` endpoint — you cannot inject a session
  from :9223 by copying `localStorage` alone (`t_token` etc. are there, but cookies
  are not transferable this way).
- **Working pattern:** write the ENTIRE interaction as one script that polls
  `pgrep` until clear, then runs uninterrupted; launch via `terminal(background=true,
  notify_on_complete=true)`. Piecemeal `/eval` calls across turns WILL get clobbered.

## AUTOMATION — the actual fix (stockID is writable)

- `PUT /vehicle-inventory/{vehicle-inventory-id}` — schema `UpdateVehicleInventory`
  lists only `pricingDetails` in `properties` but `allOf`-inherits
  `BaseVehicleInventory`, and the official example payload includes
  `"stockID"`, `"stockType"`, `"stockSubType"`. Stock number IS writable.
- `POST /vehicle-inventory` accepts the same on create.
- Detector built: **`/home/itadmin/tekion-reports/sct_stock_audit.py`**
  (read-only, `--days N`). Classifies `BARE_FALLBACK` / `HAND_TYPED_PREFIX` /
  `WRONG_PREFIX` / `OK` against the rule table and prints the expected stock #.

### Two false-positive traps in the detector (both cost a rebuild)
1. **Prefix encodes MODEL YEAR, not a constant.** `C26`/`T26` are 2026; a 2027 unit
   correctly gets `C27`/`T27` (`C276873`, `T2711003` were flagged wrongly). Derive
   the prefix as letter + 2-digit model year from `vehicleSpecification.year`.
2. **Pre-VIN factory orders are NOT defects.** NEW units whose "VIN" is a factory
   allocation code (`TU36E187`, `TS35F010`, `TX40A828` — 8 chars, letter-heavy, not
   17-char VINs) have no subtype/bodyClass and legitimately take the global counter.
   Exclude `stockType==NEW` with a non-17-char VIN. 21 of 30 initial flags were these.

True signal at SCT over 30 days was **3** units: `S15042`, `CT15232` (also wrong
prefix — should be NT), `CT15230`. Note the audit independently re-flagged `S15042`,
proving the 8/17 "fix" never actually corrected that vehicle.

**Gate: no writes until the detector reproduces exactly the known-bad set and
nothing else, on a run Joe has reviewed.**

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

