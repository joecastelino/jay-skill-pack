---
name: tekion-opcode-create
description: >
  Create a NEW opcode from scratch in Tekion's Opcode Management application —
  the full Default-tab field reference (opcode type, eligibility, category,
  service type, labor, pay-type pricing, parts, cost centers, associated opcodes,
  sublet, auto-dispatch). Canonical workflow distilled from Tekion KB0025686.
  Use when asked to CREATE/build a new opcode (vs editing pricing on an existing
  one — for that use tekion-opcode-default-pricing / tekion-opcode-overrides).
triggers:
  - create a new opcode
  - create opcode tekion
  - new opcode management
  - build an opcode
  - opcode fields reference
  - opcode service type
  - sublet opcode
  - associated opcodes
---

# Tekion — Create a New Opcode (Opcode Management)

## 🚦 MANDATORY PROTOCOL — run these 3 things BEFORE tool call #1

Joe called out (2026-08-26) that one opcode took **40 minutes / 190 tool calls**. The
post-mortem found 4 causes, all preventable. This gate exists so they cannot recur.
**Budget: ~10 min / ~25 calls per opcode. If you pass 40 calls, STOP and re-read this.**

**1. Load this skill FIRST.** On the UC4ALIGN build I loaded
`tekion-internal-cost-center-gl-routing`, `tekion-autonomous-login` and
`persistent-browser-server` — and never opened THIS one, the only skill with the click
path for the form I was filling. Trigger words: *build/create/clone an opcode*, any
`UC*`/dept opcode, "set it up like <existing op>".

**2. Run the preflight — one call, replaces ~15.**
```bash
cd /home/itadmin/tekion-reports && \
  /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 opcode_preflight.py --dealer <ID>
# ... build ...
  /home/itadmin/.hermes/hermes-agent/venv/bin/python3.11 opcode_preflight.py --restore
```
Checks :9223 alive → waits out any in-flight `cron-pipeline` → pauses the cron (safe
backup+install, no sed-pipe) → asserts `currentActiveDealerId` → reports the SPA url.
Exit 0 = safe to build. Non-zero = do NOT start. `--restore` is not optional.

**3. Use the helper library, don't re-derive mechanics.**
`/home/itadmin/tekion-reports/jay_opcode.py` — every verified recipe below is already
implemented (ES5 `/eval`, scrollIntoView+re-read, type-filter-to-one-option,
tree-leaf-only clicks, section-relative `Add`, price-input polling, readback, commit,
verify). It is a HELPER for hand-building, not a fire-and-forget script.
```python
import sys; sys.path.insert(0,"/home/itadmin/tekion-reports")
from jay_opcode import B
b = B(); b.assert_dealer("1251"); b.goto("/ro/opcode/add")
b.fill_text_fields([code, code, desc])
b.select("Category","Maintenance"); b.select("Service Type","Used Car Department")
b.tree_select_field("Default Pay Type","I - Default internal pay")
b.set_labor_hours(customer=hrs, manufacturer=hrs)
b.add_rate_row("Internal Pay","Fixed Price",int_price)
b.add_rate_row("CP - Default customer pay","Fixed Price",cp_price)
b.set_cost_center("Used Car INV 240")
print(b.readback())        # eyeball BEFORE commit
b.commit(); print(b.verify(code))
```
**Batch one section per `execute_code` call** (fill → verify → next), not one `/eval`
per field. That alone is the difference between 190 calls and ~25.

**4. NEVER write new automation mid-task.** See the "Don't rewrite this as a headless
Playwright script" section below — I burned ~75 calls on exactly that, then threw it
away and hand-built anyway. If a click path is proven, grind it. Script it AFTER, on my
own time, never while Joe is waiting.

**5. If context compaction fires mid-build**, re-read the store's pinned field standard
(in `tekion-department-opcode-buildout`) instead of re-deriving it from the API.

---

Authoritative field-by-field reference for creating a new opcode, distilled from
Tekion's own KB **KB0025686** (PDF saved at `~/tekion-kb/pdfs/`, text at
`~/tekion-kb/text/Create_a_new_opcode_in_the_Opcode_Management_application.txt`).

**Companion skills:**
- Edit labor $ / add parts on an existing opcode → `tekion-opcode-default-pricing`
- Vehicle/part override ROWS → `tekion-opcode-overrides`
- Verify committed state via API → `tekion-opcode-api`
- Navigation / URLs → `tekion-sitemap`

## Permissions & Nav
- Permissions: **Operation Management View** + **Operation Management Update**
  (`Roles > Permissions > Parts > Parts`).
- Nav: **App Grid > Settings > Service Settings > Opcode Management** → Opcode List
  → **Create Opcode** (upper-right). Direct URL pattern: `/ro/opcode`
  (list) / `/ro/opcode/edit/<OPCODE>` (edit). The **Default tab** is the default view.

## Default-tab sections (in order)

### Opcode
- **Opcode type**: `Individual` (independent repair/maint job) · `Service Menu`
  (maintenance item inside a service menu) · `Inspections` (requires Inspection Type:
  UDI / PDI / MPI) · `Tire Storage`.
- **Opcode**: the code as defined by the service dept. NOTE: catalog opcodes pulling
  from the data source start with **TEK**.
- **Display Value**: what shows on the RO and in opcode search (can = the opcode). For
  SCP dealers, the Display Value shows instead of the TEK/system opcode.
- **Description**: the repair/maintenance job description.

### Eligibility Criteria
Defines where the opcode is available in search. **Condition**: `In` (included) /
`Not in` (excluded — e.g. hide from consumer portal, or RO-only). **Value**: options
based on the criteria chosen.

### Category
Used in **GLAM (GL Account Mapping)** to direct charges to accounts, and for
filter/reporting grouping. Loaded at installation.

### Service Type
Drives default labor rates (customer/warranty/internal) per service type; used with
department in GLAM for RO posting accounts; can drive technician wage configs
(Employee Onboarding → Employment Details). Main Service / Maintenance Service /
Service Interval Menu types load at installation.

### Job Priority and Skill
- **Job Priority**: used when auto-dispatch is on and the team's dispatch type is
  Claim Work Job Priority or Auto Dispatch Job Priority. Changeable on the RO.
- **Skill**: groups opcodes for auto-dispatch; techs get primary/secondary skills.
  Extra skill groups added in Dispatch Settings.

### Consumer Scheduling
- **Display Name**: name shown when scheduling via consumer portal.
- **Cause** / **Story Line**: default cause + correction statements pulled to the job.
  Multiple allowed (Add Cause / Add Story Line); all pull to the RO; remove via Delete.

### Standard Opcode Mapping
Maps an OEM opcode to the standard opcode so it pulls to the job. **OEM** (dropdown) +
**Opcode** (OEM code). For warranty jobs the OEM opcode pulls to the claim.

### Default Pay Type *(Service 3.0 only)*
Pay type auto-applied when opcode is added to an RO (+ default payer from Pay Types
Setup). Custom pay types come from Pay Types Setup. TIP: use for prepaid maintenance,
service contracts, fleet programs, warranty billing.

### Labor
- **Clock-In Mandatory**: require tech clock-in before working the op.
- **Customer**: default customer labor time pulled for ALL pay types. A Labor Pricing
  multiplier/kicker applies on top (e.g. 1.5 × 2.0 hr = 3.0 hr on the RO).
- **Manufacturer**: MFR-allowed labor time (Labor Time Guide). NOTE: labor hours only
  pull from **Customer time OR the Labor Time Guide** on the RO.

### Pay Type Pricing Setup
- **Eligible for Customer Pay Special Labor Pricing in Customer Management**: on by
  default (all opcodes). Deselect to bill only at Opcode-Management / Service-Type rates.
- **Labor Rate Configuration** rows: **Pay Type**, **Labor Rate** (Fixed Price / Hourly
  Price / Labor Price Guide + value), **Allow Override**, **Discount Eligible**.
  `Add` (top-right) to add a rule; drag handle to reorder; kebab → Remove / View Audit
  Logs. *(Service 3.0)*

### Parts
- **Consider for Parts Preparation on Appointment**: pre-stage parts when on an appt.
- **Eligible for Customer Pay Special Parts Pricing in Customer Management**.
- **Enable Part Price Cap**: cap total part price.
- Part rows: **Part Name** (dropdown), **Quantity**, **Parts Price**, **Select Fees**
  (auto-bill fees from Fee Management).

### Cost Centers
**Warranty Default Cost Center / Internal Default Cost Center** for warranty + internal
work: **Cost Center** (e.g. Warranty Claim, Internal Loaner Expense) + **Split %** +
**Allow Override** + Delete. Multiple allowed; splits must total **100%**.

### Associated Opcodes
Opcodes auto-added as additional operations when this opcode is added (e.g. alignment
auto-added with a FWD transmission R&R). NOTE: only **Individual** service-type opcodes
auto-add. Added in display order.

### Sublet
Work done by an outside company (towing, body work). Toggle **Sublet Op Code**, then
`Add` per-pay-type sublet pricing rows: **Pay Type**, **Sublet Labor Mark Up**, **Labor
Min/Max Value**, **Sublet Parts Mark Up**, **Parts Min/Max Value**, Delete.

### Auto-Dispatch / Completion
- **Consider for Auto Dispatch**: on by default; deselect for jobs needing no tech
  (sublets, loaners) so a tech isn't force-assigned.
- **Mark as Complete when added as a Job**: off by default; auto-completes the op when
  added (only if pre-job validations pass — Pre-Job Completion rules live in Service
  Settings). Use for no-tech jobs.

## Save
`Save` (lower-right) creates the opcode. Configure default pay types + labor-rate rules
carefully so the right payer/pricing applies automatically on the RO.

## VERIFIED CREATE MECHANICS via :9223 (ROTATEBAL @ BT 1249, 2026-07-02)

Full end-to-end create executed through the persistent browser server. Sequence:

1. **Nav**: SPA `window.location.href='/ro/opcode'` (wait ~8s), then `/click {text:"Create Opcode"}`
   → lands on `/ro/opcode/add` (Draft mode, Opcode Type defaults to Individual Service).
2. **Plain text fields** (work with `/type` after tagging `data-jay` via `/eval`):
   `#opcode_undefined` (the code), `#opcodeDisplayValue_undefined`, `#description_undefined`.
3. **Category / Service Type are react-select CONTAINERS** (`#CATEGORY_FIELD`,
   `#SERVICE_TYPE_FIELD` = `tekion-select-*-container` DIVs). `/type` on the container fails
   ("not an <input>"), a `/mouse` click on it does NOT open a dropdown, and the native
   value-setter throws **"Illegal invocation"** (known quirk). WORKING RECIPE: tag the INNER
   `input` (`c.querySelector('input')` — it reuses the container's id), `/type` a filter string
   into it (e.g. "Maint"), wait ~1.5s, options render as visible `[class*=option]` elements —
   `/mouse` click the option center. Verify via `[class*=singleValue]` innerText.
4. **Flag hours**: `#LABOR_HOURS_FIELD` (Customer) + `#MANUFACTURER_HOURS_FIELD` — `/type` + Tab.
5. **Pay Type Pricing Setup** (same mechanics as tekion-opcode-default-pricing): row badges
   `[class*=pricingTable_payType]` — NOTE the form renders MULTIPLE badge groups at different
   y-bands (eligibility ~251, pricing ~605-687, sublet ~1782); the labor pricing rows are the
   CP/W/I band near the "Pay Type Pricing Setup" section. Confirm row identity with
   `document.elementFromPoint(120, rowY)` = "CP" before clicking. Row's `.ant-select` at x≈493
   → options in `.ant-select-dropdown-menu-item` (LEGACY ant class) = Labor Price Guide |
   Hourly Price | Fixed Price → picking Fixed reveals `input[placeholder="Enter price"]` in
   that row → `/type` the $ + Tab.
6. **Submit button is `Create`** (blue, bottom-right ~x1211,y688), NOT Update/Save.
   ⚠️ A button scan filtering on `/save|cancel|update/i` MISSES it — I only found "Save Draft"
   and thought the form had no commit button until a screenshot+vision pass showed Create.
   Include `create|publish` in button-scan regexes.
7. **Success signal = URL flips to `/ro/opcode/edit/<OPCODE>`** — there is no reliable toast.
   ALWAYS verify by API read-back (opcode search endpoint, see tekion-opcode-api): confirm
   status ACTIVE, flatPrice, hours, dealerId.

Convention cloned for BT maintenance add-ons (matches BGMOAG/4ALIGN/WIPER/CABIN): Individual
Service / Category=Maintenance / Service Type=Maintenance Service / Default Pay Type=CP /
Fixed Price CP / Skill=DEFAULT / no parts for labor-only services.

## Service Type dropdown: search terms are LITERAL, not fuzzy (BC "DECLINED" opcode, 2026-08-18)

The Service Type react-select's option list does NOT fuzzy-match the way Category's does.
Typing a plausible fragment (e.g. `"Miscell"`, which correctly matches Category →
"Miscellaneous") can return a genuinely **empty** option list (`[]`) for Service Type even
though valid options exist — it's filtering on the literal option text, and "Miscellaneous"
is not itself a Service Type. Don't conclude the field is broken or the store lacks Service
Types; instead:

1. **Pull the dealer's full Service Type list via API** (no guessing required):
   ```js
   fetch('https://app.tekioncloud.com/api/service-module/u/opcode/serviceTypes', {
     credentials:'include',
     headers:{dealerId: localStorage.getItem('currentActiveDealerId'), 'tekion-api-token': localStorage.getItem('t_token'), /* + userId/roleId/tek-siteId/tenantname from localStorage, see tekion-opcode-api */}
   })
   ```
   Returns `data[]` of `{name, key, id, status, priceDetails}` — e.g. BC (1251) has Sublet,
   Service Contract, PDI, **Main Service**, Maintenance Service, Service Interval Menu,
   XPRESS SERVICE, ACCESSORIES, MPVI, Used Car Department, Service Catalog, Service Menu,
   Cadillac Express Shop. Names vary per dealer — always pull fresh per store.
2. **To mirror an existing opcode's convention** (e.g. Joe/precedent says "set it up like
   REC"): search that opcode via `/api/service-module/u/opcode/search` (body
   `{"searchText":"REC","page":{"size":10,"number":0}}`), read its `serviceTypeIds[]`, then
   match the id against the full list from step 1 to get the human-readable name to type into
   the dropdown (e.g. REC → id `629607f6857aba0007201fbc` → "Main Service").
3. Then `/type` the exact matched NAME (or a substring of it that's unambiguous) into the
   tagged `[data-jay='svc-input']` — this now returns real option(s) to click.

## Dealer-switch click target: find the `cursor-pointer` ancestor, don't count parent hops

When switching dealers on :9223 before creating a store-specific opcode, resolving the row by
walking a FIXED number of parents up from the text node gives the WRONG element. Walking 3
hops landed on `root_dealerInfoList_itemListContainer` (the whole list, center y≈287) — the
click registered `{"success":true}` but `currentActiveDealerId` never changed. The real target
is the ancestor whose className contains **`cursor-pointer` / `root_dealerInfoItem_container`**
(center ≈ y262 for the BC row). Resolve it by CLASS, not by hop count:

```js
let el = textNode;
while (el && !/cursor-pointer|dealerInfoItem_container/.test(el.className||'')) el = el.parentElement;
const r = el.getBoundingClientRect();  // click r.x+r.width/2, r.y+r.height/2
```

Then ALWAYS verify `localStorage.getItem('currentActiveDealerId')` flipped before navigating —
a silently-failed switch means you create the opcode at the wrong store. Also re-verify the
dealer id after landing on `/ro/opcode/add`; the SPA drifts back to the prior dealer / a stale
RO job page between calls, wiping filled form state. Do switch → navigate → verify → fill in
tight sequences and re-check `/url` after each step.

## ⚠️ BEFORE creating: audit for near-duplicate opcodes (burned 2026-07-02)

An exact-match existence check (`searchFields:["OPCODE"]` + `hits.find(x=>x.opcode===CODE)`)
is NOT enough to declare an opcode "missing":
- **Search is case-sensitive on compare**: "44K" showed MISSING but lowercase **"44k"** existed.
- **Near-dupes hide under different codes**: "FOBBATTERY" missing but **FOBBATT** existed
  ($5.99); "ROTATEBAL" missing but **BALANCE** ($89.95, balance-only) + **ROTATE** ($39.95)
  existed.
Before creating, run BROAD searches on `searchFields:["OPCODE","DESCRIPTION"]` with keyword
fragments (e.g. "ROTATE", "BALANCE", "FOB", "KEY") and compare case-insensitively. Creating a
duplicate = the "Perform Tire Rotation (2)" clutter problem Joe hates. Default to
reuse+reprice an existing cousin (flag the à-la-carte blast radius) and only create new when
the service content genuinely differs (e.g. BALANCE lacked rotation → ROTATEBAL justified).

## Create-form mechanics verified at BC 1251 (UCALIGN 2026-08-26, **re-verified + CORRECTED** UC4ALIGN same day)

Page: `/ro/opcode/add` → commits to `/ro/opcode/edit/<OPCODE>`.
Form is **~2900px tall in a 720px viewport**, inside an **inner scroll container**.
Almost every failure below traces back to those two facts.

### 🔴 THE #1 TIME SINK — there are MULTIPLE "Add" buttons; most are not yours

An earlier version of this skill said *"Labor Rate Configuration `Add` button at ~`1202,294`"*.
**That coordinate is unreliable and the naive "first button whose text is Add" is often the
WRONG button** — on `/ro/opcode/add` another `Add` opens the **Identifier** dropdown
(options: Department / Sites / Engine Litre / Engine Cylinder / Aspiration / …).
Clicking it appears to work, then you spend rounds filling a section that isn't the rate grid.
Tell-tale: the dropdown you get lists vehicle attributes instead of pay types.

**Resolve the Add button RELATIVE TO ITS SECTION HEADER, in page coords:**
```js
(()=>{const vis=e=>e.offsetParent!==null;
 const h=[...document.querySelectorAll('*')].filter(vis).filter(e=>e.children.length===0)
   .find(e=>/Labor Rate Configuration/i.test((e.innerText||'').trim()));
 const hy=h.getBoundingClientRect().top+window.scrollY;      // BC: 769
 return [...document.querySelectorAll('button')].filter(vis)
   .filter(e=>/^Add$/i.test((e.innerText||'').trim()))
   .map(e=>{const r=e.getBoundingClientRect();
            return {pageY:Math.round(r.top+window.scrollY), x:Math.round(r.x+r.width/2)};})
   .filter(a=>Math.abs(a.pageY-hy)<260);})()                 // BC hit: pageY 757, x 1202
```
Then `scrollIntoView({block:'center'})` that exact button and **re-read its rect** before clicking.

### 🔴 Scrolling: `window.scrollTo` DOES NOTHING — use `element.scrollIntoView()`

`window.scrollY` stays `0` no matter what; the form scrolls an inner div. Consequences:
- `window.scrollTo(0, N)` is a silent no-op.
- Any control/option whose `y` is **> ~700 is off-viewport and `/mouse` clicks miss it**
  (they land on whatever is at that screen coord, or nothing). `elementFromPoint` also
  can't reach it.
- Dropdown options routinely render below the fold (Category "Maintenance" first reported
  at `y=742`; after `scrollIntoView` it became `y=640` and clicked fine).

**Rule: for every control AND every option — `scrollIntoView({block:'center'})`, then
RE-READ the bounding rect, then click. Coordinates go stale after every scroll and after
every selection** (picking a value re-flows the row; I had to re-read row coords between
Pay Type → Customer Type → Labor Rate).

### 🔴 Clicking an option can hit the WRONG element with identical text

`I - Default internal pay` appears BOTH as the Default Pay Type field's `singleValue`
(`ant-v5-select-selection-item`, y≈89) and as the open tree's leaf
(`ant-v5-select-tree-title`, y≈415). A generic "find visible element whose innerText ===
option" grabs the field, clicks it, and the menu never closes — looks like the option is
disabled. Scope the search:

```js
// tree-selects (pay type): the leaf is the element with class select-tree-title
.filter(e=>/select-tree-title/.test(e.className))
// react-selects (category / service type / labor rate / cost center):
.filter(e=>/-option/.test(e.className))
// or require an ancestor menu: e.closest('[class*=-menu],[class*=select-dropdown]')
```
Also **assert the menu actually CLOSED** after picking; if it's still open the pick didn't commit.

### Field-by-field (BC 1251)

| Field | Widget | Notes |
|---|---|---|
| Opcode / Display / Description | plain `input[placeholder="Type Here"]` | tag in visual order (top→bottom, left→right); index 3 is a different field, don't fill it |
| Opcode Type | react-select | already defaults to **Individual Service** |
| Category | react-select | type-filter works; option list is long → scrollIntoView |
| Service Type | react-select | literal matching (see section above) |
| Skill | react-select | mandatory, defaults **`tech/generic`** — verify rather than set blindly |
| Labor times | `input[placeholder="0"]` ×2 (Customer, Manufacturer) | both at same y (~1594 page coords) |
| Default Pay Type | **ant-v5 tree-select** | click `.ant-v5-select-tree-title` leaf, not the treenode wrapper. **Defaults to `CP - Default customer pay`** — must be changed for internal ops |
| Labor Rate rows | see below | |
| Internal Default Cost Center | react-select, ships with one blank row (no Add) | **must type-filter** — the list is long and the target isn't rendered until filtered. Input id was `#rc_select_2`; `/type` into it, then click the `-option`. Split auto-fills `100`, Allow Override defaults ON |

### Labor Rate Configuration rows

- **New rows insert ABOVE existing rows.** After adding row 2, the blank row is on TOP
  (y≈491) and the completed row 1 drops to y≈533. Never cache row coords; identify the
  blank row as the one whose cells still read `Select`.
- Row layout: **Pay Type** x≈273 · **Customer Type** x≈455 (midpoint — it uses a widget
  class the generic control scan misses, so target geometrically) · **Labor Rate** x≈638.
- Pay Type cell = tree-select (same leaf-click rule).
- Customer Type = multi-select `All / Individual / Business` → pick **All** (renders as
  "All, Indi…"); close by clicking neutral space (`950,250`).
- Labor Rate options: `Labor Price Guide / Hourly Price / Fixed Price`.
- Price `input[placeholder="Enter price"]` **only exists after Fixed/Hourly is chosen**, and
  is briefly `disabled` right after — poll `is_enabled()` before typing.
- Both row checkboxes (**Allow Override**, **Discount Eligible**) default CHECKED — matches
  the 4ALIGN/ALIGN convention; verify rather than clicking them.
- **Always read every price back**; identify rows by `y`, not by index.

### Commit + verification

`Create` at ~`1211,688` → URL flips to `/ro/opcode/edit/<OPCODE>`. **No reliable toast on
create** (a toast scan returns clock/notification chrome like `"1:33 PM | 99+ | 70"`).

Verify by **hard `navigate` to `/ro/opcode/edit/<OPCODE>`** and re-reading the form —
a genuine remount, and it proves persistence. (A bare in-page `fetch` to
`/api/service-module/u/opcode/search` **500s** — "Token doesn't exist or is invalid" —
because the app's axios interceptor adds auth a plain fetch can't replicate. Use the XHR-hook
recipe or just reload the page.)

### :9223 endpoints that DON'T exist (all 404 — cost several dead calls)

`/key`, `/keyboard`, `/screenshot` as **POST**. Real set used here: `/navigate`, `/eval`,
`/type {selector,text}`, `/mouse {action,x,y}`, `/press`, and `/screenshot` as **GET**
returning `{"screenshot":"<base64>"}`.

**`/eval` intermittently returns a payload with no `result` key** (transient). Wrap it:
```python
def ev(js, tries=3):
    for _ in range(tries):
        r = json.loads(call("eval", {"js": js}))
        if "result" in r: return r["result"]
        time.sleep(1)
    raise RuntimeError(str(r))
```

### ⚠️ Don't rewrite this as a headless Playwright script "to save time"

I tried mid-task: build a generic `bc_ucd_opcode_create.py` so opcodes #3–26 would be fast.
It burned ~25 iterations on tree-selects, row-shift, disabled inputs and stale coords — and
still failed, because it was clicking the wrong `Add` button the whole time. Joe's standing
rule applies: *"You've spent 8 hours trying to save us 40 mins of work."*
**Hand-build on `:9223` until the click path is boring, THEN script it.** The abandoned
attempt is at `~/tekion-reports/bc_ucd_opcode_create.py` if it's ever worth resuming.

## EDITING an opcode you just created (skill/field change) — BC 1251, 2026-08-26

Same page, `/ro/opcode/edit/<OPCODE>`; commit button is **`Update`** (same slot ~`1211,688`),
and unlike Create it DOES fire a toast: `Opcode '<CODE>' has been updated successfully`.

**React-select long lists: clicking the option in the unfiltered list silently fails.**
Changing Skill from `alignment` → `tech/generic`, I opened the dropdown (26 options rendered
with correct coords) and `/mouse`-clicked `tech/generic` at its reported center. Click returned
`{"success":true}`, but `singleValue` still read `alignment`. The list is virtualized/scroll-
positioned and the reported y was stale by the time the click landed.

**WORKING RECIPE — always type-filter down to ONE option first:**
```
1. locate the control by its singleValue text (NOT by label):
   [].slice.call(document.querySelectorAll('div'))
     .filter(x => x.offsetParent!==null && /singleValue/i.test(x.className)
                  && x.innerText.trim()==='<CURRENT VALUE>')[0]
2. scrollIntoView({block:'center'}), re-read the rect (coords shift after scroll)
3. /mouse click it → dropdown opens and focuses a hidden input
4. tag the focused input:  document.activeElement.setAttribute('data-jay','skin')
5. /type {selector:"[data-jay='skin']", text:"tech/gen"}
6. re-scan [class*=option] → should be exactly ONE → /mouse click it
7. verify singleValue flipped BEFORE clicking Update
```

## :9223 endpoint gotchas hit repeatedly this session

- **`/eval` 500s on modern JS.** Payloads using spread (`[...document.querySelectorAll()]`)
  inside certain arrow/closure combinations return `HTTP 500 Internal Server Error` with no
  message. The SAME logic written ES5-style (`[].slice.call(...)`, `function(){}`, no spread,
  no template literals) works every time. When `/eval` 500s, don't debug the page — rewrite
  the JS as ES5.
- **`/screenshot` is a GET**, not a POST, and returns JSON `{"screenshot":"<base64>"}`.
  `curl -s http://127.0.0.1:9223/screenshot -o f.json` then base64-decode the key. There is
  no `-o file` option, and the `browser_vision`/`browser_navigate` tools open a SEPARATE
  unauthenticated context — never use them against :9223.
- **`/press` sends one key per call** — loop per character for numeric input.

## Reading back MANY opcodes via the XHR hook — bounce through the list page

Iterating `pushState('/ro/opcode/edit/<OP>')` straight from one opcode to the next captures
NOTHING for every opcode after the first (React Query serves the detail from cache, no XHR
fires). Insert a `pushState('/ro/opcode')` + ~2s wait BETWEEN each one to force a real remount:

```
for op in ops:
    pushState('/ro/opcode');            sleep 2
    pushState(f'/ro/opcode/edit/{op}'); sleep 3.5
    grab window.__cap entry matching f'/{op}/v2'
```
Also note the hook must be re-armed after any hard reload, and `/opcode/skills` +
`/opcode/serviceTypes` responses get captured on the way in — free id→name maps, use them
instead of hardcoding ids.

## 🔴 PAUSE THE CALIBER PIPELINE CRON BEFORE ANY MULTI-MINUTE :9223 FORM SESSION

**→ Just run `opcode_preflight.py --dealer <ID>` (see the MANDATORY PROTOCOL at the top).
It does everything in this section in one call, and `--restore` undoes it.** The manual
detail below is kept for when the preflight itself needs debugging.

`cron-pipeline.sh` runs **every 15 minutes** and drives the SAME `:9223` browser. Building an
opcode takes longer than 15 minutes, so it WILL navigate your half-filled form away mid-build.
This happened three times in one session (form → `/dse-v2/appointments/scheduler/day`, then
→ `/dse-v2/appointments/list`, where subsequent `/type` calls went into a LIVE appointments
screen instead of the form). Nothing was saved, but each hit cost a full rebuild.

**Before starting:**
```bash
crontab -l > /tmp/crontab.backup.$(date +%s)     # ALWAYS back up first
crontab -l > /tmp/cron_orig.txt
pgrep -af cron-pipeline                          # wait out any in-flight run
```
Comment the line with a marker, write to a temp file, install it. **Note two traps:**
1. `crontab -l | sed ... | crontab -` is forbidden (a sed error installs an EMPTY crontab).
   Edit in Python and install from a file.
2. `crontab <file>` rejects a file with **no trailing newline** ("new crontab file is missing
   newline before EOF, can't install") — always `.rstrip("\n") + "\n"`.

```python
orig = open("/tmp/cron_orig.txt").read()
paused = "\n".join(("#JAYPAUSE "+l) if ("cron-pipeline" in l and not l.startswith("#")) else l
                   for l in orig.split("\n")).rstrip("\n") + "\n"
open("/tmp/cron_paused.txt","w").write(paused)
# terminal: crontab /tmp/cron_paused.txt && crontab -l | grep -c JAYPAUSE
```
Wait for any running instance to exit (`pgrep -f cron-pipeline`) before touching the form.
**Restore immediately when done** and verify `grep -c JAYPAUSE` returns `0`.

A pipeline run already in flight can take several minutes (it pages through hundreds of
orders per store), so check `pgrep` rather than assuming the pause took effect instantly.

## 🔴 THE PREFLIGHT MISSES A SECOND BROWSER CONSUMER — check `cron-tekion.sh` too (2026-08-28)

`opcode_preflight.py` only knows about **`cron-pipeline.sh`** (15-min). There is a SECOND
:9223 consumer it does not check: **`cron-tekion.sh`** — the nightly Caliber RO-dollars
scraper (`scripts/tekion-scraper.ts`). It starts ~1:16 AM, works ~2,971 invoices at ~15s
each, and therefore **owns :9223 for 12+ hours into the business day**. It also drives the
browser to OTHER dealers (it was on *Toyota of Lancaster* mid-build), so it can flip
`currentActiveDealerId` out from under you as well as navigate your half-filled form away.

Preflight can pass GREEN (`no pipeline in flight`, `dealer=1251`) while this is running.
Symptom: mid-build your `pick()` calls start returning `notfound:` / `notfound:DROP OFF`,
and `location.href` shows an RO/invoice page you never navigated to.

**Always check BOTH before a build:**
```bash
pgrep -af "[c]ron-pipeline"
pgrep -af "[c]ron-tekion|tekion-scraper.ts"      # the long one
tail -3 /home/itadmin/caliber-ops/logs/tekion-nightly.log   # shows [N/2971] progress
```

**If `cron-tekion.sh` is running, do NOT kill it and do NOT wait it out — move to :9225.**
Clone the live session across in ~15s (no OTP, lands on the same dealer):
```python
ls = eval9223("JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
inject = {k:v for k,v in json.loads(ls).items() if not k.startswith("amplitude")}  # amplitude keys 413
post9225("/navigate", {"url":"https://app.tekioncloud.com/login"})
for k,v in inject.items():
    post9225("/eval", {"js": f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});'ok'"})
post9225("/navigate", {"url":"https://app.tekioncloud.com/home"})
# verify: {u:/home, d:1251, w:true(Welcome), lg:false(no Username)}
```
Then just point the build client's base URL at `http://127.0.0.1:9225`. Verified end-to-end
on the UCTIRE2 + UCTIRE1 builds — zero interference, all dropdowns behaved identically.

### The "Add" button can produce TWO blank rate rows — remove the extra before Create

On one UCTIRE2 attempt an earlier Add had already fired, so clicking Add again left **two**
blank rows (y≈491 and y≈532). Fill the top one, then delete the spare via its row kebab at
**x≈1197**. The kebab menu (`Remove` / `View Audit Logs`) renders at x≈1197, ~29px below the
row. **`pick("Remove")` fails** — the generic option-scan doesn't match these menu items, and
a scoped scan can grab a stale/duplicate node. Working form: filter for `innerText==='Remove'`
AND `getBoundingClientRect().x > 900`, take the LAST match, and dispatch the pointer sequence
on it. Re-read the row list afterward to confirm only one row remains.

### Always readback the cost center against BOTH header positions

`Warranty Default Cost Center` and `Internal Default Cost Center` render as sibling blocks
(headers ~190px apart). A y-range readback can silently report the wrong one. Anchor on both
header y values and assert the Warranty block is still `Select` (blank) while the Internal
block reads `Used Car INV 240`.

## 🔴 SYNTHETIC-CLICK RECIPE — `/mouse` silently fails on ant-v5 + react-select options (BC 1251, UCFBRAKE/UCRBRAKE 2026-08-26)

The single biggest time sink on the UCFBRAKE build: `/mouse {action:"click"}` at an option's
correct center coordinate returns `{"success":true}` and **does nothing**. I burned ~8 rounds
re-opening the Default Pay Type dropdown, confirming the leaf existed at `y=584`/`y=613`, and
clicking it — the field stubbornly stayed `CP - Default customer pay`. The coords were right;
the synthetic OS-level click just isn't accepted by these widgets.

**FIX — dispatch the full pointer+mouse event sequence on the element itself:**
```js
const r = o.getBoundingClientRect();
const cx = r.x+r.width/2, cy = r.y+r.height/2;
const op = {bubbles:true, cancelable:true, clientX:cx, clientY:cy, view:window};
o.dispatchEvent(new PointerEvent('pointerdown', op));
o.dispatchEvent(new MouseEvent('mousedown', op));
o.dispatchEvent(new PointerEvent('pointerup', op));
o.dispatchEvent(new MouseEvent('mouseup', op));
o.dispatchEvent(new MouseEvent('click', op));
```
`pointerdown`/`pointerup` are **required** — a plain `.click()` or a bare `MouseEvent('click')`
is not enough for ant-v5. This worked first-try on every dropdown afterwards. Reusable helper:

```python
def pick(label):                      # label match is exact, lowercased
    return ev("""(()=>{const vis=e=>e.offsetParent!==null;
     const o=[...document.querySelectorAll('[class*=react-select][class*=option],[class*=select-item-option],[class*=select-tree-title]')]
      .filter(vis).find(e=>(e.innerText||'').trim().toLowerCase()==='"""+label.lower()+"""');
     if(!o)return 'notfound'; o.scrollIntoView({block:'center'});
     /* dispatch sequence above */ return 'ok';})()""")
```
**Keep `/mouse` for OPENING a control** (that works fine) and use the dispatch recipe for
PICKING the option. Open → `time.sleep(2.2)` → dispatch-pick → `time.sleep(2)` → verify.

### Default Pay Type is NOT always a tree-select

This skill previously said it's an ant-v5 **tree**-select (`.ant-v5-select-tree-title`). On the
UCFBRAKE build the very same field rendered as a **grouped flat list** — group headers
`ant-v5-select-item-group` (`Customer Pay` / `Internal Pay` / `Warranty Pay`) with
`ant-v5-select-item-option` children. Searching only for `select-tree-title` returned `noleaf`
and looked like the option didn't exist. **Query BOTH** (`[class*=select-item-option]` and
`[class*=select-tree-title]`) — the `pick()` helper above already does.

### Customer Type multi-select is a TOGGLE — clicking "All" twice clears everything

The row's Customer Type (`[class*=dropdown-trigger]`, x≈475) options `All / Individual /
Business` toggle rather than replace. Sequence observed:
- click `All` → reads `All, Individual, Business` ✅ (this is the goal state)
- then clicking `Individual` → **un-toggles** it, leaving just `Business` ❌

Click `All` **once**, verify the trigger reads `All, Individual, Business`, then STOP and close
the menu (`/mouse` a neutral spot like `950,230`). Do not "also select Individual".

### Standard Opcode Mapping grid (GM stores)

`FBRAKE`/`RBRAKE` at BC carry 3 warranty mapping rows: `gm | chevrolet | 0300`,
`gm | cadillac | 0300`, `gm | gmc | 0300`. Joe's ruling 2026-08-26: **copy them onto UC* clones.**
Grid columns: **OEM** x≈188 · **Make** x≈388 · **Opcode** (plain text input) x≈588.
Rows are at y≈494 / 535 / 576 (41px pitch) and a **blank row auto-appends** after each is filled —
no Add button. OEM list at BC contains only `gm`; Make list is `chevrolet / cadillac / gmc`.
Fill loop (verified, 3/3 first pass):
```python
def row(make, y, tag):
    click(188,y); pick("gm"); click(388,y); pick(make)
    tag_input_at(y, x>500, width>140); type("0300")
```

### `input[placeholder="Type Here"]` — filter by Y, not by document order

Tagging the first three `Type Here` inputs grabbed the **global "Search here..." nav box**
(y=18) as `f0`, so the opcode went into Tekion's search bar and the real Opcode field stayed
empty. Anchor on the header row's y (BC: `y≈284`, labels Opcode/Opcode/Description at `y≈253`):
```js
[...document.querySelectorAll('input')].filter(vis)
 .filter(e=>e.placeholder==='Type Here')
 .filter(e=>Math.abs(e.getBoundingClientRect().y-284)<15)
 .sort((a,b)=>a.getBoundingClientRect().x-b.getBoundingClientRect().x)
```
Symptom to watch for: `location.pathname` still `/ro/opcode/add` but a `No results found`
overlay covers the form, and `elementFromPoint` on your dropdown coords returns
`root_listSection_imageContainer`. That's the global search overlay — press `Escape`, reload,
re-tag by Y.

### `/goto` does not exist — the endpoint is `/navigate`

`call("goto", {...})` → **HTTP 404**. Use `/navigate`. (Full valid set: `/navigate`, `/eval`,
`/type`, `/mouse`, `/press`, GET `/screenshot`.)

### Verification bounce

Reload-verify by navigating to `/home`, waiting ~7s, THEN to `/ro/opcode/edit/<CODE>` (~13s).
Navigating edit→edit can serve cached React Query state. Both UCFBRAKE and UCRBRAKE were
confirmed this way. Unlike Create-with-no-toast noted above, **BC 1251 DID fire a clean toast**:
`Success / Opcode 'UCFBRAKE' has been created successfully` — scan toast text but still reload.

### Timing that worked (don't shorten these)

open dropdown → `2.2s` · after dispatch-pick → `2.0s` · after `Create` → `5–6s` ·
after `/navigate` → `12–13s`. Wrap `/eval` in the retry helper; it 500s transiently and a
bare call will crash the whole `execute_code` block mid-build.

## ✅ THE CLEAN 20-CALL SEQUENCE — verified end-to-end (UCTIRE4, BC 1251, 2026-08-28)

First build that hit the ~10 min / ~25 call budget with **zero misfires**. Every dropdown
landed first try. Reproduce this exact order; the wins are (a) `activeElement` tagging,
(b) one batched `execute_code` per section, (c) one-eval full-form readback before commit.

**Setup — write a 6-function helper to `/tmp/jb.py` once, `sys.path.insert` it in every
later call.** (Same primitives as `jay_opcode.py`; a local file is fine and is what was
actually used.) It needs: `post/ev` (retrying `/eval`), `click`, `typ`, `nav`, and `pick()`
built on the pointer-event dispatch recipe below. Keep `pick()` doing
`sleep(2.2) → dispatch → sleep(2.0)` internally so call sites stay one-liners.

`pick()` option matcher that worked for **every** widget type on the form (react-select,
ant-v5 flat list, ant-v5 tree) — one query, exact match then prefix fallback:
```js
document.querySelectorAll('[class*=option],[class*=select-tree-title]')
  .filter(visible).filter(e => e.children.length <= 1)
```
`children.length<=1` is what keeps it off wrapper divs. Return `'notfound:'+all option
texts` on miss so a failure is self-diagnosing instead of costing another round trip.

### Section order (one `execute_code` per numbered step)

1. `/navigate` to `/ro/opcode/add`, wait 14s, assert `currentActiveDealerId`.
2. **Header inputs** — tag by Y-band, fill all three, read all three back:
   ```js
   input[placeholder='Type Here'] filtered to Math.abs(rect.y - 284) < 15, sorted by x
   → setAttribute('data-jay','h0'/'h1'/'h2')
   ```
3. **Locate all controls in one shot** before touching any of them:
   `getElementById('CATEGORY_FIELD')` / `('SERVICE_TYPE_FIELD')` give reliable centers,
   plus a dump of every visible `[class*=singleValue],[class*=placeholder]` as
   `[text, cx, y]`. That single eval is the map for the whole rest of the build.
4. **Category**, 5. **Service Type**, 12. **Cost Center** — all three use the identical
   recipe (see `activeElement` section below).
6. **Labor hours** — `input[placeholder='0']`, `scrollIntoView` the first, tag both, type
   + Tab each.
7. **Default Pay Type** — find it by its *value text*
   (`[class*=selection-item],[class*=singleValue]` matching `/Default (customer|internal)
   pay/`), `scrollIntoView`, re-read rect, click, `pick("I - Default internal pay")`.
8. **Labor Rate Add button** — locate relative to the `Labor Rate Configuration` header in
   page coords (`|pageY - headerY| < 260`), then `scrollIntoView` it and **re-read the
   rect** (page coords 720 became viewport 414). Click → new blank row appears.
9. **Rate row** — Pay Type (x≈275) → Customer Type (x≈475, click `All` ONCE) → Labor Rate
   (x≈627) → price input appears at x≈818. Re-read the row's cell list after each pick.
10. **Price** — tag `input[placeholder~=/price/i]`, type, Tab, read back.
11. **Checkbox audit** (free, one eval — see below).
13. **Standard Opcode Mapping** — three rows via a reusable `mapping_row(make, y, tag)`
    function; rows at y 494 / 535 / 576, blank auto-appends at +41px.
14. **Full readback** (see below) → eyeball → `Create` → verify bounce.

### 🔑 `document.activeElement` — the universal react-select filter-input tag

Supersedes hunting for `#rc_select_N` ids or guessing container inner inputs. Clicking any
react-select focuses its hidden search input, so:
```python
click(cx, cy); time.sleep(1.5)
ev("(function(){var a=document.activeElement;"
   "if(!a||a.tagName!=='INPUT')return 'noinput';"
   "a.setAttribute('data-jay','cat');return 'ok';})()")
typ("[data-jay='cat']", "Tire"); time.sleep(1.8)
pick("Tire")
```
Worked identically for Category, Service Type, and Internal Default Cost Center. If it
returns `noinput`, the click didn't open the control — retry the click, don't proceed.

**Verification gotcha:** `getElementById('CATEGORY_FIELD').innerText` returns the a11y
string `"option Tire, selected.\nTire"`, not just `"Tire"`. Match with *contains*, never
equality.

### 🔑 Negative Y coordinates are NORMAL after `scrollIntoView`

Post-scroll, elements above the viewport report negative `getBoundingClientRect().y`
(e.g. `-1052`). Don't treat that as an error or filter them out as invalid — it just means
"scrolled past". Only filter on negatives when you're deliberately scoping to the visible
band.

### 🔑 Cost Center: don't scope by a narrow band under its header

Scanning `y > headerY && y < headerY + 120` for the Internal Default Cost Center select
returns **`[]`**. After `scrollIntoView` the header lands at y≈405 and its select sits at
y≈542 — 137px below. Use a ≥160px window, or query
`[class*=ant-v5-select-selector]` below the header. Placeholder text is `Select`, and there
are TWO such rows (Warranty above, Internal below) — take the lower one.

### 🔑 Checkbox ids give a free full-form audit

Every meaningful toggle has a stable id. One eval dumps the entire state:
```js
{}; document.querySelectorAll('input[type=checkbox]').filter(visible)
   .forEach(e => { if (e.id) map[e.id] = e.checked });
```
Expected on a correct BC UCD internal op:
```
CLOCK_IN_MANDATORY_FIELD                              false
ELIGIBLE_FOR_CP_SPECIAL_LABOR_PRICING_FIELD           true
ALLOW_OVERRIDE_undefined / DISCOUNT_ELIGIBLE_undefined true   (the rate row)
ELIGIBLE_FOR_PARTS_PREPARATION_FIELD                  true
CUSTOMER_PART_PRICING_ENABLED_FIELD                   true
PARTS_PRICING_CAP_ENABLED_FIELD                       false
WARRANTY_/INTERNAL_DEFAULT_COST_CENTER_ALLOW_OVERRIDE_FIELD_ID  true
SUBLET_OP_CODE_FIELD_ID false · AUTO_DISPATCH_FIELD_ID true · AUTO_COMPLETE_FIELD_ID false
```
All of those are form defaults — **verify, don't click.**

### 🔑 One-eval pre-commit readback (do this before EVERY `Create`)

```js
{ selects: [class*=singleValue],[class*=selection-item],[class*=dropdown-trigger]
             → innerText, filtered to length < 40,
  inputs : all visible input where type!=='checkbox' && value → value,
  checks : the id→checked map above }
```
Returns the whole opcode as three short arrays — diff it against the source opcode's
identical dump. This catches a missed field for ~1 call instead of a post-commit Update
cycle. Then run the SAME eval after the verification bounce; the two should match
(the reloaded form adds one extra input: description renders twice).

### Commit + verify (unchanged, confirmed again)

`Create` at `1211,688` → URL flips to `/ro/opcode/edit/<CODE>` + toast
`Opcode '<CODE>' has been created successfully` (fires ~6× in the toast scan, that's normal).
Then bounce `/home` (8s) → `/ro/opcode/edit/<CODE>` (14s) and re-read. Never edit→edit.

## Pitfalls / notes
- Opcodes are **store-specific** — create only at the store(s) needed (Joe-confirmed);
  don't replicate across all 7 unless asked.
- Several fields are **Service 3.0 only** (Default Pay Type, Labor Rate Configuration).
- For the browser-automation mechanics of actually typing into V2 fields (spinbuttons,
  react-select parts, incremental Save Draft), see `tekion-opcode-default-pricing` —
  this skill is the FIELD MAP; that skill is the CLICK MECHANICS.
