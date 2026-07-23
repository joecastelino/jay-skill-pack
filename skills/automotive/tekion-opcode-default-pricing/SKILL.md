---
name: tekion-opcode-default-pricing
description: >
  Set Default-tab labor pricing and add parts to a Tekion opcode in the
  opcodeManagementV2 UI. Covers reaching the edit page, the V2 flat-form layout,
  setting the dollar rate via the Customer/Manufacturer spinbuttons, adding parts
  via react-select (bare-number-first search), and the incremental Save Draft
  pattern that the browser tool requires. This is the SIMPLE common case — for
  vehicle/part override rows use tekion-opcode-overrides.
trigger: >
  Tekion opcode pricing, opcode labor rate, set opcode price, BGFINJ, BGMAF,
  fixed price labor, add part to opcode, opcode flag time, opcodeManagementV2,
  default tab pricing, update opcode labor
triggers:
  - set opcode labor price
  - add parts to opcode
  - opcode default pricing
  - fixed price labor rate
---

# Tekion Opcode Default Pricing (V2 — Labor + Parts)

The Default tab of an opcode edit page: set the labor dollar rate and add parts.
This is the V2 flat-form UI (CP/W/I pay-type buttons + spinbutton rate fields),
NOT the old V1 rt-tr-group table.

**Companion skills:**
- **Login / OTP / dealer switch** → `tekion-autonomous-login` / `tekion-browser-navigation`
- **Vehicle/part override rows** (cabin filters etc.) → `tekion-opcode-overrides`
- **Verify committed state via API** → `tekion-opcode-api`
- **Deep reference / historical detail** → `tekion-opcode-pricing-v2`

---

## Reaching the Opcode Edit Page

`page.goto()` for the edit URL loads only the shell — you must use SPA navigation:
```js
window.location.href = '/ro/opcode/edit/BGFINJ';
// wait until an "Update" button exists:
// Array.from(document.querySelectorAll('button')).some(b=>b.textContent?.trim()==='Update')
```
Fallback (opcode list search + click): navigate `/ro/opcode`, type the code into the
page-body search (placeholder `"Search..."`, NOT the header `"Search here..."`), then
click the opcode text leaf node.

---

## ✅ PREFERRED METHOD (verified 4TIRE @ SCT 2026-07-02, :9223 server): Proper flag hours + Pay Type Pricing Setup

The old "dollar-in-the-hr-spinbutton" hack below still works, but the PROPER setup is fully
automatable via the persistent browser server (`/mouse` + `/type` endpoints) and commits with
ONE Update click (matches Joe's "all fields, one Update" rule):

1. **Flag hours**: the two `input.ant-input-number-input` with placeholder `"0"` (Customer x≈89,
   Manufacturer x≈243). Tag with `data-jay` via `/eval`, then `/type` the hours (e.g. `1.00`)
   + `/press` Tab to commit each.
2. **Pay Type Pricing Setup rate**: each row (W/CP/I, badges `[class*="pricingTable_payType"]`)
   has an `.ant-select` "Select" at x≈493. `/mouse`-click the target ROW's select (re-read live
   coords; rows are 41px apart). Dropdown options = **Labor Price Guide | Hourly Price | Fixed
   Price** — items are `.ant-select-dropdown-menu-item` (OLD ant menu classes, NOT
   `.ant-select-item-option`!) inside the non-hidden `.ant-select-dropdown`. `/mouse`-click the
   option.
3. Picking Hourly/Fixed Price reveals a rate input placeholder `"Enter price"` in that row —
   tag + `/type` the dollar rate + Tab. (Hourly Price → charges rate × flag hrs; Fixed Price →
   flat $.)
4. **Update button works via `/mouse`**: `/eval` scrollIntoView the Update button, read its
   rect center, `/mouse`-click it. Success toast "Opcode 'X' has been updated successfully".
   No Save Draft loop needed when driving :9223 with real mouse clicks.
5. Verify: SPA-nav away (`/ro/opcode`) and back to the edit URL, confirm hr values + row shows
   e.g. `I | All | Hourly Price | 160 | $/hr`.

**Pitfalls found:** a mis-aimed `/mouse` opens the WRONG row's dropdown (W is the top row) —
verify with `document.elementFromPoint(120, rowY)` badge text first; close a wrong dropdown
with `/press` Escape (safe, no navigation). After picking the rate type, row Y-coords shift —
re-scan before the next interaction.

## LEGACY: Setting the Labor Dollar Rate via hr spinbuttons (browser_* tools fallback)

**The two `[role="spinbutton"]` inputs with "hr" labels are nominally flag-time hours,
but empirically putting the DOLLAR AMOUNT directly in them works and persists** (verified
5+ opcodes: BGFINJ $226, BGMAF $113, etc.). Set BOTH Customer and Manufacturer to the
dollar rate. Use only when the :9223 server isn't available.

- **Use `browser_type` on the spinbutton input ref** (browser tool) or `page.keyboard.type()`
  (Puppeteer). Real keyboard events are the ONLY thing that survives a save.
- **Tab after typing** — Ant Design InputNumber commits on blur.
- **SKIP the Pay Type Pricing Setup table** entirely *when using the Hermes browser tool*.
  The dropdowns there need real pointer/keyboard events `browser_console` can't provide.
  The spinbutton dollar value achieves the same result.
  **⚠️ EXCEPTION — via the :9223 persistent-browser server the pricing table IS fully
  workable** (verified 2026-07-02, 4TIRE @ SCT). Use it when Joe asks for a
  PAY-TYPE-SPECIFIC rate ("internal 1hr at $160") — then put the REAL HOURS in the
  spinbuttons and the RATE in the table (see next section), not dollars-in-hr.

---

## Per-Pay-Type Labor Rate via Pay Type Pricing Setup (:9223 method — VERIFIED 2026-07-02)

Use case: "set price internal for labor 1hr and at $160" → flag time 1.00 in BOTH hr
spinbuttons + Internal row = Hourly Price @ 160.00. One-shot Update save works.

1. **Flag hours**: tag the two hr inputs (`input.ant-input-number-input`, visible,
   placeholder `'0'`, x≈89=Customer / x≈243=Manufacturer), set `data-jay` attrs, then
   `/type` + `/press Tab` on each.
2. **Find the pricing rows**: badges = `[class*="pricingTable_payType"]` (W/CP/I, visible).
   Each row's Labor Rate dropdown = the `.ant-select` at the SAME y-center as its badge
   (x≈493). ⚠️ Row coords SHIFT after edits above reflow the page — re-scan badge y's
   immediately before every `/mouse` click. First attempt hit the W row because coords
   were stale; a wrong-row open is recoverable with `/press Escape` (safe, no nav, no
   value committed).
3. **Open the target row's dropdown** with `/mouse` at the select's live center.
   Dropdown options are **`.ant-select-dropdown-menu-item`** (LEGACY Ant class), NOT
   `.ant-select-item-option` — querying the modern class returns [] even though the
   dropdown is open. Read options from the visible
   `.ant-select-dropdown:not(.ant-select-dropdown-hidden)`.
4. **Options = `Labor Price Guide | Hourly Price | Fixed Price`.**
   "N hr at $X" ⇒ Hourly Price (rate × flag hours). Flat job price ⇒ Fixed Price.
5. After picking, a new number input appears in that row with **placeholder
   `"Enter price"`** — tag it, `/type` the rate (e.g. `160.00`), Tab.
6. **Save**: `scrollIntoView` the `Update` button, `/mouse` click its center →
   green toast "Opcode 'XXX' has been updated successfully". A single all-at-once
   Update WORKS via :9223 real mouse (the incremental-Save-Draft constraint applies
   only to the Hermes browser tool). VERIFY by SPA-nav away (`/ro/opcode`) and back
   to the edit page: hr inputs show the hours, row shows `Hourly Price | $/hr` with
   the rate (note: displays `160` not `160.00` — normal).

❌ **Do NOT use** `nativeSetter.call(input, val)` + events, or `execCommand('insertText')` —
the value appears set but React discards it on save (verified failure).

Customer always precedes Manufacturer in DOM order, so the first `0.00`-valued spinbutton
is Customer.

---

## Adding Parts (react-select — verified workflow)

The "Part Name" field is a **react-select** (`#partName_undefined`, `css-2b097c-container`),
NOT an Ant Design select. Targeting `.ant-select-selector` is wrong.

**Three-step search order (Joe's rule):**
1. **Bare part number first** (e.g. `"408"`) — Tekion's catalog indexes by base number. Wait 2-3s.
2. **With brand prefix** (e.g. `"BG 408"`) if no bare-number match.
3. **"Create" option** for real parts only as last resort — BUT see the sanctioned
   generic-placeholder use below.

### ✅ Generic placeholder parts via `Create "..."` (Joe-confirmed 2026-07-20)

The `Create "Transmission Fluid"` dropdown option creates an **opcode-local placeholder
part line** with a settable price and **NO parts-master/inventory record** (verified:
parts-master search afterwards shows no match). Joe explicitly sanctions this for generic
lines the Parts dept swaps for the real part at RO time — e.g. a generic "Transmission
Fluid" line so estimates never show the wrong fluid (WS on a CVT vehicle).

**Verified swap recipe (SMTRANSMISSION + its menu included-service @ BT 1249):**
1. Snapshot the before-state to a JSON baseline file (part names + prices) for rollback.
2. Remove the specific-fluid line (e.g. `BG3143 - FULL SYN ATF`), note its exact price.
3. In the blank add-row's **Part Name** select (`#partName_undefined`), type the generic
   name → click `Create "..."` → set Price to the EXACT removed price (fixed-price
   services must not drift a cent).
4. Save → verify via TRUE remount (SPA-nav to /home then back) → verify the customer-facing
   total on a fresh throwaway quote explode.
5. If the opcode is used inside a service menu, remember the **included-service record
   carries a SEPARATE part list** — swap BOTH surfaces (opcode edit page AND
   `/ro/service-menu-setups/included-service/edit-service/<id>/default`).

**⚠️ Fees-select mistargeting trap:** typing near the parts area can land in the **Fees**
select instead of Part Name — symptom = "No Match Found" with NO Create option. The Create
option only ever appears in the real Part Name select (`partName_undefined`). If Create is
missing, screenshot and check which select has focus before concluding Create doesn't exist.

```js
// 1. Open the react-select dropdown
document.querySelector('#partName_undefined .css-g88mmg-control')?.click();
// 2. Type the bare number via native setter
const input = document.querySelector('[id*="partName"] input');
const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
set.call(input,'408'); input.dispatchEvent(new Event('input',{bubbles:true}));
// 3. wait ~2s, then click the catalog match (NOT "Create" unless nothing else)
document.querySelectorAll('[class*="-option"]').forEach(o=>{
  if(o.textContent?.includes('BG 408') && o.offsetHeight>0) o.click();
});
// 4. set price (resets to 0.00 after part selection)
// parts table inputs: [0]=Part Name, [1]=Quantity(1), [3]=Price (placeholder "0.00", "$")
```
If part doesn't exist in catalog, the only option is `Create "BG 408"`.

---

## ⚠️ Saving — Browser Tool Requires INCREMENTAL Save Draft (V2 workaround)

This contradicts Joe's general "all fields, one Update" rule, but it's a V2 browser-tool
limitation, NOT a Tekion requirement. Verified 4/4 (BGTB, BGIND, BGFUEL, BGTF):

```
For each opcode:
  1. browser_type both spinbuttons to the dollar amount
  2. browser_console: click "Save Draft"   ← SAVE IMMEDIATELY
  3. browser_console: add part 1            ← then Save Draft
  4. browser_console: add part 2            ← then Save Draft
  5. Verify: reload (window.location.href) + check values persisted
```
Save Draft saves the small React-state delta since the last save. A bulk delta (all fields
at once) is too complex for `dispatchEvent` to serialize, so it silently fails.

- **`btn.click()` on "Save Draft" via browser_console WORKS.** `btn.click()` on "Update"
  does NOT trigger React form submission via browser_console.
- **Save Draft changes opcode status to "Draft"** — cosmetic, does not block further saves.
- **With Puppeteer**, a single all-at-once save can work, but only `page.mouse.click(x,y)`
  triggers the Update button — `dispatchEvent` won't. Login/OTP overhead makes Puppeteer
  slower than the incremental browser-tool method for single opcodes.

If Joe pushes back on incremental saves: explain it's a V2 browser-tool constraint;
Puppeteer could do one-shot but login/OTP takes longer than the incremental method.

---

## Browser Tool vs Puppeteer
- **Flag time / dollar rate only (no parts):** browser_type + Save Draft. ~30s.
- **Labor + parts:** incremental Save Draft pattern above. ~2 min/opcode.
- **Update button is below the fold** (~scrollTop 2000) and unreachable via browser snapshot
  refs — that's why Save Draft (reachable via browser_console) is used. For Update, use Puppeteer mouse click.
- **If it fails after genuine retries** (browser tool + Puppeteer keyboard + Puppeteer mouse),
  tell Joe which fields are done and which remain — don't loop.

---

## browser_console Syntax Quirks
- No top-level `return` → wrap in IIFE `(() => { ... })()`.
- No top-level `await` → wrap in async IIFE `(async () => { await ... })()`.
- DOM nodes serialize to `{}`; return primitives/strings for inspection.

## Opcode Scope Rule
Opcodes are **store-specific** — each exists only at the store(s) listed in the source
report. Do NOT search the same opcode across all 7 stores. Update only where the report
lists it. (Joe-confirmed.)

## Always Verify
Update can succeed silently (no toast). Reload the edit page via SPA navigation and confirm
the spinbutton/part values persisted before declaring done.
