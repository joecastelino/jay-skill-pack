---
name: tekion-opcode-pricing-v2
description: >
  DEEP REFERENCE / ARCHIVE for Tekion opcodeManagementV2. The day-to-day work is
  now split into three clean skills — use those FIRST: tekion-opcode-default-pricing
  (labor + parts), tekion-opcode-overrides (vehicle/part override batch rows), and
  tekion-opcode-api (read/audit/verify committed rows). Load THIS skill only when you
  need the full historical detail: complete dealer-switch code, Puppeteer scripts,
  every selector quirk, and the session-by-session debugging archaeology behind the
  verified recipes.
trigger: >
  Tekion deep reference, opcode archaeology, full dealer switch code, Puppeteer
  opcode script, opcode selector history, why does opcode save fail, V1 vs V2 opcode
triggers:
  - opcodeManagementV2 internals
  - opcode pricing deep reference
  - opcode selector archive
---

# Tekion Opcode Pricing (V2 — opcodeManagementV2) — DEEP REFERENCE / ARCHIVE

> ⚠️ **THIS IS THE DEEP-REFERENCE ARCHIVE.** For routine work, use the three clean
> skills instead — they contain the current verified recipes without the archaeology:
>
> | Task | Skill to load |
> |------|---------------|
> | Set labor dollar rate + add parts (Default tab) | **`tekion-opcode-default-pricing`** |
> | Add vehicle/part override rows (cabin filters, batch) | **`tekion-opcode-overrides`** |
> | Read / audit / verify committed override rows | **`tekion-opcode-api`** |
> | Log in / OTP / dealer switch | **`tekion-autonomous-login`** |
>
> Keep reading below ONLY for full historical context: the complete dealer-switch
> implementation, Puppeteer script templates, every selector quirk, and the
> session-by-session debugging that produced those verified recipes.

The V2 opcode management UI replaces the old V1 design. Pricing is NOT in an
rt-tr-group table with Fixed Price comboboxes — it's a flat form layout with
spinbutton inputs and CP/W/I radio buttons.

## Reaching the Opcode Edit Page

**Critical**: The URL `/ro/opcode/edit/OPCODE` works ONLY via SPA-internal
navigation. `page.goto()` loads the Tekion shell but renders the home page or
login redirect — you'll see loading dots and never reach the edit form.

### Method 1 — SPA navigation (Puppeteer, sometimes works):
```js
await page.evaluate(() => {
  window.location.href = '/ro/opcode/edit/BGFINJ';
});
await page.waitForFunction(() => {
  return Array.from(document.querySelectorAll('button'))
    .some(b => b.textContent?.trim() === 'Update');
}, { timeout: 20000 });
```
If the `waitForFunction` times out (common after dealer switch — the SPA
context may reset), fall back to Method 2.

### Method 2 — Opcode list search + click (browser_tool / fallback):
1. Navigate to opcode list: `page.goto('/ro/opcode')` or SPA nav
2. **Search for the opcode** using the opcode-specific search input:
   - Placeholder: `"Search..."` (NOT the header `"Search here..."`)
   - Must use `nativeInputValueSetter` + keydown Enter event
3. After filtering to 1 result, **click the opcode text leaf node**:
   ```js
   await page.evaluate(() => {
     const all = document.querySelectorAll('*');
     for (const el of all) {
       if (el.textContent === 'BGFINJ' && el.children.length === 0) {
         el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
         return;
       }
     }
   });
   ```
4. Wait for the edit page to load (check for Update button)

**In the browser tool**, Method 2 works via `browser_console` dispatch.
In Puppeteer, the DOM click via evaluate may NOT trigger React navigation —
the page often stays on the opcode list. Method 1 is preferred when operational.

## Dealer Switching (Leaf-Element Matching + Evaluate Clicks)

The old pattern (`el.textContent?.startsWith('STStevens')`) fails because
Ant Design popover elements concatenate ALL child text into a single string.
**Must use leaf-element exact text matching:**

```js
async function switchDealer(page, target) {
  // NEVER use page.click(selector) — nodes detach before click fires.
  // Always use page.evaluate to dispatch clicks in the DOM.
  await page.waitForSelector('[class*="dealerSelect_container"]', { timeout: 15000 });
  await page.evaluate(() => {
    document.querySelector('[class*="dealerSelect_container"]')?.click();
  });
  await delay(2000);

  const clicked = await page.evaluate((t) => {
    const inner = document.querySelector('.ant-popover-inner-content');
    if (!inner) return 'no-popover';

    function getLeaves(el) {
      const leaves = [];
      (function walk(node) {
        if (!node.children || node.children.length === 0) {
          const text = node.textContent?.trim();
          if (text && text.length > 3) leaves.push({ el: node, text });
        } else { for (const c of node.children) walk(c); }
      })(el);
      return leaves;
    }

    for (const { el, text } of getLeaves(inner)) {
      if (text === t) { el.click(); return 'clicked'; }
    }
    return 'not-found';
  }, target);

  // ⚠️ CRITICAL: DO NOT page.reload() after dealer switch!
  // The reload resets the dealer back to the default (BC).
  // Instead, wait for the page to settle naturally.
  // The dealer switch may trigger an SPA navigation — wait for it.
  await delay(2000);
  try {
    await Promise.race([
      page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 }),
      page.waitForSelector('[class*="dealerSelect_container"]', { timeout: 15000 })
    ]);
  } catch(e) {}
  await delay(3000);
  
  // Verify
  const dealer = await page.evaluate(() => {
    const el = document.querySelector('[class*="dealerSelect_container"]');
    return el ? el.textContent?.trim().substring(0, 5) : 'NF';
  });
  if (dealer !== 'STSte') {
    // Retry once
    await page.evaluate(() => {
      document.querySelector('[class*="dealerSelect_container"]')?.click();
    });
    await delay(2000);
    await page.evaluate((t) => {
      // broader match
      const all = document.querySelectorAll('.ant-popover-inner-content *');
      for (const el of all) {
        if (el.textContent?.includes('Stevens Creek') && el.textContent.length < 40) {
          el.click(); return;
        }
      }
    }, target);
    await delay(2000);
    try {
      await page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 });
    } catch(e) {}
    await delay(3000);
  }
}
```

Dealer exact names: `Blackstone Toyota`, `Blackstone Chevrolet Cadillac`,
`Stevens Creek Toyota`, `Stevens Creek Volkswagen`, `Toyota of Lancaster`,
`Alfa Romeo of San Jose`, `Volkswagen of Clovis`

**CRITICAL**: Do NOT call `page.reload()` after clicking the dealer — it resets
back to BC. The dealer switch persists via SPA state, not page reload.

## V2 Page Layout — Exact Section Positions

Based on a full section scan of the BGFINJ edit page (scroll container:
`.overflow-auto[1]`):

| Section | scrollTop | Visible elements |
|---------|-----------|-----------------|
| Opcode details | 0 | Type, Code, Display Value, Description |
| Eligibility | 200 | Criteria, Condition, Value dropdowns |
| Category/Service Type | 300 | Dropdowns, Job Priority spinbutton |
| Skill/Display Name | 400 | Skill dropdown, Consumer Scheduling text |
| Cause/Story Line | 500 | Text inputs, Add buttons |
| Standard Opcode Mapping | 600 | OEM/Make/Opcode table |
| Add Labels | 650 | Text input |
| **Default Pay Type** | 700 | CP/W/I radio buttons |
| **Labor** | 720 | Clock-In Mandatory checkbox |
| **Customer rate** | 750 | `[role="spinbutton"]` input + "hr" label |
| **Manufacturer rate** | 750 | Same structure, right column |
| Pay Type Pricing Setup | 800 | Checkbox + rate table (W/CP/I rows) |
| **Parts table** | ~1200-1800 | Part Name (react-select), Quantity, Parts Price |
| Cost Centers | 1369 | Warranty/Internal cost center selects |
| Associated Opcodes | 1777 | Linked opcodes |
| Sublet | 1895 | Sublet pricing table |
| Bottom buttons | ~2000 | Save Draft / Cancel / **Update** |

**Update button is always at the bottom.** You don't need to find its exact
position — just query `button` elements by text.

## Labor Hours (Flag Time) vs Dollar Rate — Critical Distinction

**There are TWO separate things on the edit page and they are NOT the same field:**

### 1. Flag Time Hours (the `hr` spinbuttons)
The two `[role="spinbutton"]` inputs with "hr" labels are technically **flat
rate hours**, but empirically, **putting the DOLLAR AMOUNT directly in these
spinbuttons works and persists across saves** (verified 2-for-2: BGFINJ $226,
BGMAF $113). Set both Customer AND Manufacturer to the dollar rate:
- **Customer**: `113.00` (set via `browser_type` on spinbutton input ref)
- **Manufacturer**: `113.00` (same)

### 2. Dollar Rate (Pay Type Pricing Setup table) — SKIP THIS
The Pay Type Pricing Setup table (scrollTop ~950) is **below the browser tool
viewport** and is NOT needed. Setting the spinbuttons to the dollar rate via
`browser_type` achieves the same result without fighting the unreachable
Fixed Price dropdown. See "Setting the Fixed Price Dollar Rate" below for
the Pay Type table approach if you're using Puppeteer and can reach it.

**Lesson from 2025-06-03**: The Pay Type Pricing table dropdown is a
distraction. `browser_type` on the two spinbuttons + browser_console for
react-select parts is the reliable, 2-minute-per-opcode workflow.

## Setting the Fixed Price Dollar Rate

To set a fixed price dollar rate (e.g., $226.00 for CP):

1. Scroll to the **Pay Type Pricing Setup** table (scrollTop ~800)
2. Find the **CP row** (shows "CP", "All", "Select" in cells)
3. Click the **Labor Rate dropdown** (the "Select" in the CP row):
   ```js
   const cells = pricingTable.querySelectorAll('.rt-td');
   // Cell 9 in the CP row is the Labor Rate ant-select
   cells[9].querySelector('.ant-select-selector').click();
   ```
4. From the dropdown, select **"Fixed Price"** (options: Labor Price Guide,
   Hourly Price, Fixed Price)
5. After selecting Fixed Price, a **dollar input appears** with placeholder
   `"Enter price"`:
   ```js
   const priceInput = cells[9].querySelector('input');
   nativeSetter.call(priceInput, '226.00');
   priceInput.dispatchEvent(new Event('input', {bubbles: true}));
   priceInput.dispatchEvent(new Event('blur', {bubbles: true}));
   ```

The cell text will show "SelectFixed Price $" + the input value after saving.

## Setting the Labor Rate (Flag Time Hours)

The flag time hours use Ant Design InputNumber spinbuttons with "hr" labels:

```html
<button>Increase Value</button>
<button>Decrease Value</button>
<spinbutton>
  <input value="0.00">
</spinbutton>
text: hr
```

### Puppeteer page.type() — VERIFIED WORKING (3/3 runs)
```js
// Scroll to labor section
await page.evaluate(() => {
  const s = document.querySelectorAll('.overflow-auto')[1];
  if (s) s.scrollTop = 900;
});
await delay(1000);

// Find Customer spinbutton input via evaluateHandle
const rateHandle = await page.evaluateHandle(() => {
  const spinbuttons = document.querySelectorAll('[role="spinbutton"]');
  for (const sb of spinbuttons) {
    const input = sb.querySelector('input');
    if (input && input.value === '0.00') return input;
  }
  return null;
});

if (rateHandle.asElement()) {
  await rateHandle.asElement().click({ clickCount: 3 }); // Select all
  await delay(200);
  await rateHandle.asElement().type('226');
  await delay(300);
  await page.keyboard.press('Tab');  // Tab to commit InputNumber
  await delay(500);
}
```

**IMPORTANT**: 
- The `evaluateHandle` approach finds the first `0.00`-valued spinbutton.
  Customer always appears before Manufacturer in DOM order, so this reliably
  targets the Customer rate.
- Tab after typing is ESSENTIAL — Ant Design InputNumber commits on blur.
- The browser_console fallback (`nativeInputValueSetter` + event dispatch)
  does NOT reliably stick — React re-renders reset the DOM value. Use
  `page.type()` in Puppeteer or `browser_type` in the browser tool.

### Clicking Update
```js
await page.evaluate(() => {
  const all = Array.from(document.querySelectorAll('button'));
  for (const btn of all) {
    if (btn.textContent?.trim() === 'Update') { btn.click(); return; }
  }
});
await delay(5000);
```

### Verifying the save
Reload the edit page via SPA navigation, wait for Update button, scroll to
labor section, and check the spinbutton value:
```js
await page.evaluate(() => { window.location.href = '/ro/opcode/edit/BGFINJ'; });
await page.waitForFunction(() => {
  return Array.from(document.querySelectorAll('button'))
    .some(b => b.textContent?.trim() === 'Update');
}, { timeout: 30000 });
await delay(3000);

await page.evaluate(() => {
  const s = document.querySelectorAll('.overflow-auto')[1];
  if (s) s.scrollTop = 900;
});
await delay(1000);

const val = await page.evaluate(() => {
  const sbs = document.querySelectorAll('[role="spinbutton"]');
  for (const sb of sbs) {
    const inp = sb.querySelector('input');
    if (inp && inp.value === '226.00') return inp.value;
  }
  return null;
});
// val === '226.00' means saved successfully
```

## Adding Parts (VERIFIED — React-Select + Browser Tool Workflow)

**CRITICAL DISCOVERY**: The "Part Name" field is a **react-select** component
(`css-2b097c-container`, `#partName_undefined`), NOT an Ant Design Select.
All previous Puppeteer attempts targeting `.ant-select` were wrong.

### Parts Table Structure

The parts table uses react-table with `.rt-td` cells and
`.rt-resizable-header-content` headers. Columns: Part Name | Quantity | Parts Price.

Inputs are indexed sequentially within the table. To find them:
```js
const partNameHeaders = document.querySelectorAll('.rt-resizable-header-content');
let partsTable = null;
for (const h of partNameHeaders) {
  if (h.textContent?.trim() === 'Part Name') {
    partsTable = h.closest('[role="grid"], table, [class*="table"]');
    break;
  }
}
const allInputs = partsTable.querySelectorAll('input');
// allInputs[0] = Part Name (react-select input)
// allInputs[1] = Quantity (value "1")
// allInputs[3] = Parts Price (placeholder "0.00", cell contains "$")
```

### METHOD A: Browser Tool Workflow (VERIFIED WORKING — 2025-06-02)

This is the recommended approach. Puppeteer struggles with react-select's
dropdown because mouse/keyboard events don't reliably trigger the portal.

1. **Log in + switch dealer + navigate to edit page** (browser_console):
   ```js
   window.location.href = '/ro/opcode/edit/BGFINJ';
   ```

2. **Expand the Parts section** (it may be collapsed):
   ```js
   // Find "Parts" h3 heading and click it
   const allEls = document.querySelectorAll('*');
   for (const el of allEls) {
     if (el.textContent?.trim() === 'Parts' && el.children.length === 0) {
       el.click(); break;
     }
   }
   ```

3. **Scroll the inner container to the parts section**:
   ```js
   document.querySelectorAll('.overflow-auto')[1].scrollTop = 2500;
   ```

4. **Open the Part Name react-select dropdown**:
   ```js
   document.querySelector('#partName_undefined .css-g88mmg-control')?.click();
   ```

5. **Wait 2-3 seconds**, then **type the part number into the search input**.
   **CRITICAL — THREE-STEP SEARCH ORDER** (from Joe, 2025-06-02):
   - **Step A**: Try the **bare part number** first (e.g., `"408"`). Wait 2-3s
     for react-select to query the catalog. Tekion indexes by base number.
   - **Step B**: If no catalog match, try **with brand prefix** (e.g., `"BG 408"`).
   - **Step C**: If neither returns a catalog match, click the **"Create"** option
     to add a custom part.
   
   Use the native setter to type (try bare number first):
   ```js
   const input = document.querySelector('[id*="partName"] input, [id*="partsLabelId"] input');
   const nativeSetter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
   nativeSetter.call(input, '408');  // Try bare number FIRST
   input.dispatchEvent(new Event('input', {bubbles: true}));
   ```

6. **Wait 2s, check dropdown options**, then click the match:
   - If the part exists in the catalog: the option text will be `"BG 408 - DESCRIPTION"`
   - If the part DOESN'T exist: the only option is `"Create \"BG 408\""`
   ```js
   const options = document.querySelectorAll('[class*="-option"]');
   for (const o of options) {
     if (o.textContent?.includes('BG 408') && o.offsetHeight > 0) {
       o.click(); break;
     }
   }
   ```

7. **Set the price** after the part is selected (the price resets to $0.00):
   ```js
   // Re-fetch inputs (row may have changed after part creation)
   const allInputs = partsTable.querySelectorAll('input');
   const priceInput = allInputs[3]; // Cell with placeholder "0.00" and "$"
   nativeSetter.call(priceInput, '26.22');
   priceInput.dispatchEvent(new Event('input', {bubbles: true}));
   priceInput.dispatchEvent(new Event('change', {bubbles: true}));
   priceInput.dispatchEvent(new Event('blur', {bubbles: true}));
   ```

8. **Click Update**:
   ```js
   const allBtns = document.querySelectorAll('button');
   for (const btn of allBtns) {
     if (btn.textContent?.trim() === 'Update' && btn.offsetHeight > 0) {
       btn.scrollIntoView({block: 'center'});
       btn.dispatchEvent(new MouseEvent('click', {bubbles: true}));
       break;
     }
   }
   ```

9. **Verify by reloading and checking inputs**:
   ```js
   window.location.reload();
   // After reload, scroll to parts and check allInputs values
   ```

**NOTE**: The Update button may not show a toast notification even on success.
Always verify by reloading the page and checking that values persist.

### METHOD B: Puppeteer (FRAGILE — React-Select Mouse Events Unreliable)

Puppeteer can handle login, dealer switch, labor rate, and scroll. But the
react-select dropdown requires specific mouse coordinates and the portal
renders outside the main DOM tree. The `page.type()` approach on the hidden
search input does NOT trigger react-select's filtering.

**Known-failing scripts**: `/tmp/tekion-bgfinj-full2.mjs`, `/tmp/tekion-bgfinj-v4.mjs`.

If attempting Puppeteer anyway:
- Use `page.mouse.click(x, y)` with coordinates from `getBoundingClientRect()`
- The react-select control is at `#partName_undefined .css-g88mmg-control`
- After clicking, the dropdown appears in a portal — check for `[class*="-menu"]`
- Typing into the react-select input requires `page.mouse.click` on the input
  first, then `page.keyboard.type()`

**Prefer Method A (browser tool)** for parts. It's ~30 seconds vs. hours of
Puppeteer debugging.

## Full Login Flow

### OTP Typing Order — CRITICAL (2025-06-03)

**Type the OTP BEFORE clicking "Verify and Proceed".** The order matters:
1. Wait for Resend button to enable
2. Click Resend
3. Fetch OTP (himalaya `fetch_otp.py` or direct imaplib)
4. **Type OTP into the textbox FIRST** (via `browser_type` or `page.type()`)
5. **THEN click "Verify and Proceed"**

Clicking Verify before typing causes the OTP to be rejected and the page
re-enters the countdown state.

### Session Re-entry (2025-06-03)

An authenticated browser session can be re-entered by navigating to
`https://app.tekioncloud.com/home` — this avoids re-login if the session
hasn't expired (~20 hours). Useful when the SPA redirects to /home after
a reload and you need to get back to the dealer-scoped UI.

## React Input Handling — Critical Discovery (2025-06-02)

**Only real keyboard events trigger React state.** There are two tiers of input methods:

### Tier 1 — WORKS (persists across saves):
- **`browser_type`** (browser tool) — simulates real keystrokes, React onChange fires
- **`page.keyboard.type()`** (Puppeteer) — equivalent to browser_type, keyboard simulation
- **`page.keyboard.press('Tab')`** — blurs InputNumber, triggers commit
- **`page.mouse.click(x, y)`** (Puppeteer) — real mouse events from coordinates

### Tier 2 — DOES NOT WORK (DOM value set, React ignores):
- `nativeSetter.call(input, '1.5')` + `input.dispatchEvent(new Event('input'))`
- `input.dispatchEvent(new InputEvent('input', {bubbles: true}))`
- `document.execCommand('insertText', false, '...')` — mixed results, NOT reliable for spinbuttons
- Any evaluate-based value setting without real keyboard events

### execCommand evaluate pattern (DO NOT USE for spinbuttons):

`document.execCommand('insertText')` was tested extensively and **does NOT work**
for Ant Design InputNumber spinbuttons. Values appear set in the DOM but revert
to their original values after clicking Update. This includes:
- `inp.focus(); inp.select(); document.execCommand('insertText', false, '339.00'); inp.blur();`
- Adding `input`/`change`/`blur` events after execCommand

The only reliable approaches for React-controlled inputs are:
- **browser_type** (browser tool) for visible elements
- **page.keyboard.type()** (Puppeteer) for any element
- **page.mouse.click(x, y)** + **page.keyboard.type()** (Puppeteer) for below-fold elements

**BLUF**: For browser tool, use `browser_type(ref, text)` on input refs from the snapshot.
For Puppeteer, use `page.keyboard.type()` after `click({clickCount: 3})` to select-all.
**Never** use evaluate-based value setting for React-controlled inputs — they will
show the value visually but won't survive a page reload.

### `browser_press` character-by-character
This works (it's real keyboard events) but is **too slow for production** — 
one API call per character. Use `browser_type` instead when refs are available.

## Browser Tool vs Puppeteer — When to Use Which

### CRITICAL: Browser Tool Save Pattern (2025-06-03, REVISED)

**The browser tool CAN save in V2, but ONLY via Save Draft, and ONLY incrementally.**

Extensively tested across BGFINJ, BGMAF, BGTB, BGIND, BGFUEL, and BGTF (June 3, 2026):

- **`browser_type` on spinbuttons**: ✅ React onChange fires, values set correctly
- **`browser_console` `btn.click()` on Save Draft**: ✅ **WORKS** — saves flag time changes
- **`browser_console` `btn.click()` on Update**: ❌ Does NOT trigger React form submission
- **`browser_console` for react-select parts**: ✅ nativeSetter + events work for part search/selection/price
- **`browser_scroll` to reach buttons**: ❌ Snapshot viewport fixed at page top — buttons never in refs

### THE SAVE PATTERN (VERIFIED — 4/4 opcodes: BGTB, BGIND, BGFUEL, BGTF)

**You MUST save incrementally.** Setting all fields and saving once does NOT work in V2 via browser tool.

```
For each opcode:
  1. browser_type both spinbuttons to dollar amount
  2. browser_console: btn.click() on Save Draft  ← SAVE IMMEDIATELY
  3. browser_console: open react-select, search part, select match, set price
  4. browser_console: btn.click() on Save Draft  ← SAVE AFTER EACH PART
  5. (repeat steps 3-4 for each additional part)
  6. Verify: window.location.href reload, check values persisted
```

**Why this works when bulk save doesn't**: Save Draft saves whatever React state has changed since the last save. Setting spinbuttons + parts in one go creates a complex React state delta that the dispatchEvent click can't fully serialize. Saving after each individual change keeps the delta small and serializable.

**Critical**: This contradicts Joe's "ALL FIELDS, ONE UPDATE" rule, but it's the only browser-tool-compatible approach for V2. When using Puppeteer with `page.mouse.click`, a single save may work — but for browser tool, incremental is mandatory.

### Save Draft changes opcode status to "Draft"

Clicking Save Draft on an Active opcode changes its status to Draft. This is cosmetic and does NOT prevent subsequent saves — all incremental saves work fine on Draft opcodes.

### Browser Tool limitation: viewport
The browser snapshot captures the viewport only (~first 800px of the form). 
For a full Tekion opcode update you need to reach:
- Flag time: ~750px ✅ in viewport
- Pay Type Pricing table: ~1400px ❌ below fold 
- Parts section: ~2600px ❌ below fold
- Save/Update buttons: ~2000px ❌ below fold

**The browser tool CANNOT complete a full opcode update alone** because the
Pay Type table, Parts section, AND save buttons are unreachable via snapshot refs.
You must use Puppeteer for the full save workflow.

### Decision tree:
- **Flag time only** (no parts) → Puppeteer: `page.keyboard.type()` + `page.mouse.click` on Save Draft
- **Full opcode (labor + parts)** → Puppeteer for everything, OR browser tool to populate fields + Puppeteer to click save
- **When Puppeteer fails after 2 attempts** → tell Joe which fields are done and ask him to complete manually
- **Never** try to save via browser_console dispatchEvent — it will not work in V2

### Puppeteer dealer switch (verified pattern):
```js
await page.waitForFunction(() => 
  document.querySelector('[class*="dealerSelect_container"]'), { timeout: 10000 });
await page.evaluate(() => 
  document.querySelector('[class*="dealerSelect_container"]').click());
await sleep(1500);
// Wait for popover items to appear
await page.waitForFunction(() => {
  const items = document.querySelectorAll('.root_dealerInfoItem_itemName__4udkRrnq9E');
  for (const item of items) {
    if (item.textContent.trim() === 'Stevens Creek Toyota') return true;
  }
  return false;
}, { timeout: 10000 });
await page.evaluate(() => {
  document.querySelectorAll('.root_dealerInfoItem_itemName__4udkRrnq9E').forEach(el => {
    if (el.textContent.trim() === 'Stevens Creek Toyota') 
      el.closest('[class*="cursor-pointer"]').click();
  });
});
await sleep(4000);

```js
// Login
await page.goto('https://app.tekioncloud.com', { waitUntil: 'networkidle2' });
await page.type('input[type="text"]', 'jcastelino@scvolkswagen.com');
await clickText(page, 'Next');
await page.waitForSelector('input[type="password"]', { timeout: 15000 });
await page.type('input[type="password"]', '<TEKION_PASSWORD>');
await clickText(page, 'Login');

// OTP — always click Resend for a fresh code
await page.waitForSelector('input', { timeout: 15000 });
const otp = execSync('python3 /tmp/get_otp.py', { timeout: 65000 }).toString().trim();
const ins = await page.$$('input[type="text"]');
if (ins.length > 0) await ins[0].type(otp);
await clickText(page, 'Verify and Proceed');
await delay(6000);
await page.waitForSelector('[class*="dealerSelect_container"]', { timeout: 30000 });

// Switch dealer (see Dealer Switching section)
await switchDealer(page, 'Stevens Creek Toyota');

// Navigate to opcode edit (see Reaching the Opcode Edit Page)
await page.evaluate(() => { window.location.href = '/ro/opcode/edit/BGFINJ'; });
await page.waitForFunction(() => {
  return Array.from(document.querySelectorAll('button'))
    .some(b => b.textContent?.trim() === 'Update');
}, { timeout: 30000 });
```

The `clickText` helper:
```js
async function clickText(page, text) {
  await page.waitForFunction((t) => {
    const buttons = Array.from(document.querySelectorAll('button'));
    const btn = buttons.find(b => b.textContent.includes(t));
    if (btn) { btn.click(); return true; }
    return false;
  }, { timeout: 15000 }, text);
}
```

## Reference Implementations

- **Labor only (Puppeteer — verified working)**: `/tmp/tekion-bgfinj-v3.mjs`
  Login, switch dealer, SPA navigate, set Customer rate to 226, save, verify.
- **Labor + Parts (Puppeteer — fragile, parts selector unreliable)**: 
  `/tmp/tekion-bgfinj-full2.mjs`, `/tmp/tekion-bgfinj-v4.mjs`
  Labor saves reliably; react-select parts interaction fails in Puppeteer.
- **Full BGFINJ config (Browser Tool — verified working 2025-06-02)**:
  Labor $226 + Part BG 408 @ $26.22 saved at Stevens Creek Toyota. See
  Method A in "Adding Parts" section for the step-by-step workflow.
- **Full BGMAF config (Browser Tool — verified working 2025-06-03)**:
  Labor $113 + Part 4073 @ $24.13 saved at Stevens Creek Toyota. 2-for-2
  confirmation that the hybrid `browser_type` + `browser_console` method
  is the reliable approach. ~2 min per opcode.
- **BGTBINJ attempt (Puppeteer + Browser Tool — FAILED 2025-06-03)**:
  `/tmp/bgtbinj-puppeteer.mjs`. Flag times saved (Customer 1.50, Manufacturer
  reverted to 0.00), CP Fixed Price $339 not saved, parts (206-2 ×2 @ $76.88,
  408 @ $26.22) not saved. Save Draft changed status to "Draft". Fresh
  opcode configuration is harder than modifying existing opcodes.
  **Lesson**: Fresh opcodes may need Update (not Save Draft), and Update
  requires `page.mouse.click` — dispatchEvent won't work.

### Puppeteer Script Template (verified working for flag times)
```js
import puppeteer from 'puppeteer-core'; // NOT 'puppeteer'
import { execSync } from 'child_process';

const browser = await puppeteer.launch({
  headless: true,
  executablePath: '/home/itadmin/.cache/puppeteer/chrome/linux-148.0.7778.97/chrome-linux64/chrome',
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']
});
```
Run with: `PUPPETEER_SKIP_DOWNLOAD=true node script.mjs`

## V1 vs V2 Quick Reference

| Aspect | V1 (Old) | V2 (Current) |
|--------|----------|--------------|
| Pricing UI | rt-tr-group table, CP All row | Flat form, CP/W/I buttons |
| Labor type | Combobox: Fixed Price/Hourly/Labor Price Guide | N/A — just rate fields |
| Rate entry | ant-input-number in cell[2] | [role="spinbutton"] input |
| Parts | Separate table below pricing | Same page, scrollTop ~1200 |
| Edit page URL | Unknown pattern | /ro/opcode/edit/OPCODE |
| Dealer switch | Simple startsWith | Leaf-element exact match |

## ⚠️ FIRST: Check Viewport Coverage Before Choosing Approach

**The browser tool snapshot is physically limited to the viewport (~800px).**
Before writing any code, check which sections are needed:

| Section | scrollTop | In browser tool viewport? |
|---------|-----------|---------------------------|
| Default Pay Type + Labor spinbuttons | 700-750 | ✅ Yes |
| Pay Type Pricing Setup table | 950-1050 | ❌ No — below fold |
| Parts table | 1800-2500 | ❌ No — below fold |
| Update button | ~2000 | ❌ No — below fold |

**Decision tree (UPDATED 2025-06-03 after 4 verified saves):**
- **Full opcode via browser tool** → **INCREMENTAL SAVE PATTERN (RECOMMENDED):**
  1. `browser_type` spinbuttons to dollar rate → Save Draft immediately
  2. `browser_console` add part 1 → Save Draft immediately
  3. `browser_console` add part 2 → Save Draft immediately
  4. Verify via reload
  5. This pattern was verified 4/4: BGTB, BGIND, BGFUEL, BGTF (~2 min per opcode)
- **Flag time only (no parts)** → `browser_type` + Save Draft. Done in 30s.
- **Puppeteer** → Use when the incremental save pattern fails or for batch operations.
  Only `page.mouse.click` can trigger Update button. Login/OTP overhead makes Puppeteer
  slower than browser tool for single opcodes.
- **CP Fixed Price in Pay Type table** → Skip this entirely. Put dollar rate directly
  in spinbuttons — it persists (verified 5+ opcodes). The Pay Type table Fixed Price
  dropdown input requires real keyboard events that browser_console can't provide.

**Joe's Rule — ALL FIELDS, ONE UPDATE (V2 WORKAROUND):**
> *"why do you try and save with every adjustment you make? why don't you make all the adjustments at 1 time, then hit the update button?"*

In V2 via browser tool, this rule MUST be violated — incremental Save Draft is the only working pattern. However, this is a tool limitation, not a Tekion requirement. When using Puppeteer with `page.mouse.click`, all-at-once saves may work. If Joe pushes back, explain: "V2 browser tool requires individual saves per field. With Puppeteer I could do it in one shot but login/OTP takes longer than the incremental method."
The entire opcode edit page is one form. Set EVERY field (flag time, Fixed Price, all parts), then click Update ONCE. Never save incrementally.

## Browser Console Syntax Quirks

`browser_console(expression=...)` evaluates JS in the page but has odd rules:
- **No top-level `return`** — wrap in IIFE: `(() => { ... })()`
- **No top-level `await`** — wrap in async IIFE: `(async () => { await ... })()`
- Expression must be a single statement that produces a value
- Results are JSON-serialized; DOM nodes become `{}`

## Session Injection Fails — Always Fresh Login

The `.tekion-session.json` contains large localStorage values (t_user is ~124KB).
Injecting via browser_console fails — file:// reads blocked by sandbox, and
the 124KB string overwhelms the evaluate path. **Always do a fresh login**
via browser_type + browser_click. Login takes ~2 min but is 100% reliable.

## OTP: Stale Code Handling

Two fetch methods available:

### Method A: `fetch_otp.py` (himalaya-based, faster when email already arrived)
```bash
python3 /home/itadmin/caliber-ops/scripts/fetch_otp.py
```
Returns OTP to stdout. Best used after waiting 15-20s post-Resend. May timeout
if email hasn't arrived yet.

### Method B: Direct imaplib (more reliable for fresh codes)
Polls Gmail IMAP directly with count-based detection. Better for fresh Resend
clicks because it waits for the email to arrive rather than timing out:
```python
import imaplib, email, re, time
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('jcastelino@americanmotorscorp.com', '<GMAIL_APP_PASSWORD>')
mail.select('"[Gmail]/All Mail"')
# Count existing, poll for increase
```
Full script in `tekion-browser-automation` skill. Use Method B when Resend was
just clicked and the email hasn't arrived yet.

`fetch_otp.py` may return an old OTP. If Tekion rejects it:
1. Wait for Resend button to enable (~45s), click it
2. Query IMAP for the latest Tekion email:
   ```python
   import imaplib, email, re
   mail = imaplib.IMAP4_SSL('imap.gmail.com')
   mail.login('jcastelino@americanmotorscorp.com', '<GMAIL_APP_PASSWORD>')
   mail.select('"[Gmail]/All Mail"')
   status, data = mail.search(None, '(SUBJECT "Tekion")')
   ids = data[0].split()[-3:]
   for mid in reversed(ids):
       status, data = mail.fetch(mid, '(RFC822)')
       msg = email.message_from_bytes(data[0][1])
       for part in msg.walk():
           if part.get_content_type() == 'text/html':
               body = part.get_payload(decode=True).decode()
               codes = re.findall(r'\b\d{6}\b', body)
               if codes: print(codes[0]); break
   mail.logout()
   ```
3. Type OTP → click "Verify and Proceed"

## Puppeteer: Keyboard + Mouse Coordinate Pattern (2025-06-03)

The reliable Puppeteer approach for Tekion React inputs uses real keyboard/mouse
events. **Do NOT use evaluate-based value setters** — React ignores them.

### Pattern: click by coordinates, type by keyboard

```js
// 1. Wait for element to exist AND be visible
await p.waitForFunction(() => {
  const el = document.querySelector('your-selector');
  return el && el.offsetParent !== null;
}, { timeout: 10000 });
await S(500);

// 2. Get screen coordinates
const box = await p.evaluateHandle(() => {
  const el = document.querySelector('your-selector');
  return el?.getBoundingClientRect() || null;
});
const rect = await box.jsonValue();

// 3. Guard against NaN/null
if (rect && !isNaN(rect.x)) {
  await p.mouse.click(rect.x + rect.width/2, rect.y + rect.height/2);
  await S(500);
  await p.keyboard.type('your text');  // Triggers React onChange
  await S(300);
  await p.keyboard.press('Tab');       // Blur commits InputNumber
  await S(500);
}
```

### For spinbuttons specifically:
```js
await p.mouse.click(rect.x + rect.width/2 - 30, rect.y + rect.height/2);
await S(500);
await p.keyboard.press('Control+a');  // Select all
await S(100);
await p.keyboard.type('1.50');
await S(300);
await p.keyboard.press('Tab');
await S(500);
```

### For react-select (parts):
```js
// Click the .css-g88mmg-control to open dropdown
await p.mouse.click(rect.x + rect.width/2, rect.y + rect.height/2);
await S(2000);  // Let dropdown appear
await p.keyboard.type('206');  // Type part number (bare number first)
await S(2500);  // Let react-select query catalog
// Click matching option via evaluate
await p.evaluate(() => {
  const opts = document.querySelectorAll('[class*="-option"]');
  for (const o of opts) {
    if (o.textContent?.includes('206') && o.offsetHeight > 0) { o.click(); return; }
  }
  // Fallback: Create
  for (const o of opts) {
    if (o.textContent?.includes('Create') && o.offsetHeight > 0) { o.click(); return; }
  }
});
```

### CP row ant-select (Fixed Price dropdown) — VERIFIED DOM STRUCTURE (2025-06-03)

The Pay Type Pricing table CP row has this EXACT cell structure:

| Cell index | Content | Element type |
|-----------|---------|-------------|
| cells[0] | "CP" | Plain text |
| cells[1] | "All" | react-select (Customer Type) |
| cells[2] | "Select" | **ant-select with `[role="combobox"]`** — the Labor Rate dropdown |
| cells[3] | (checkbox) | Allow Override |
| cells[4] | (checkbox) | Discount Eligible |
| cells[5] | (checkbox) | Sales Tax |

The clickable element is `cells[2].querySelector('[role="combobox"]')` — 
NOT `.ant-select-selector` (does not exist in this row). The outer div has
class `root_select_select__q2YwMr3QeZ` (note the **Z** suffix).

**Clicking `[role="combobox"]` via `.click()` DOES open the dropdown** (verified).
Selecting "Fixed Price" from the dropdown items DOES work (verified).
After selecting Fixed Price, a price `<input>` with `placeholder="Enter price"`
appears in cells[2].

**However**: the revealed price input requires real keyboard events to persist.
`execCommand('insertText')` sets the DOM value but React discards it on save.
Use `page.keyboard.type()` in Puppeteer, or skip the Pay Type table entirely
and put the dollar rate directly in the Customer/Manufacturer spinbuttons
(verified 2/2: BGFINJ, BGMAF).

```js
// Find the CP row
const groups = document.querySelectorAll('.rt-tr-group');
let cpRow = null;
for (const g of groups) {
  const txt = g.textContent?.trim();
  if (txt.startsWith('CP') && txt.length < 30) { cpRow = g; break; }
}
const cells = cpRow.querySelectorAll('.rt-td');

// Open the Labor Rate dropdown
const combobox = cells[2].querySelector('[role="combobox"]');
combobox.click();  // Opens the dropdown

// Wait, then select "Fixed Price"
const dropdown = document.querySelector('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
dropdown.querySelectorAll('.ant-select-dropdown-menu-item')
  .find(item => item.textContent?.trim() === 'Fixed Price')?.click();

// Price input with placeholder="Enter price" now appears in cells[2]
// BUT: must use page.keyboard.type() in Puppeteer — evaluate-based value setting won't stick
```

### Known NOT to work:
- `nativeSetter.call(input, val)` + events — DOM value set, React ignores
- `document.execCommand('insertText', false, '...')` — **verified NOT to work** for both Ant Design InputNumber spinbuttons AND the CP Fixed Price input (placeholder="Enter price"). Values appear set but revert on Update.
- Computer-use agent (`tekion-cu.py`) — Node.js EPIPE crashes in Playwright
- `browser_console` evaluate for scroll-and-edit — can't reach below-fold elements with browser_type
- `dispatchEvent(new MouseEvent('mousedown'))` on ant-select — does NOT open the dropdown. Use `.click()` on `[role="combobox"]` instead (verified).

## 🔴 SUB-TAB CONFUSION + UPDATE-CLICK FAILURE (2026-06-04 late PM — NEW, READ FIRST)

Two concrete failure modes burned this session that cost ~an hour. Both have simple fixes.

### 1. The "Parts" sub-tab will NOT switch via synthetic `__fire`/dispatchEvent — use a REAL `browser_click`
On the Overrides tab, the Labor/Parts/Fees/Cost-Center/Associated sub-tabs are left-rail
buttons. Clicking the text-leaf "Parts" with synthetic `mousedown/mouseup/click` events
**frequently no-ops** — the view stays on Labor (or wherever it was). I built a COMPLETE
override row (RAV4 2019-2026, all 4 widgets + trim) believing I was on Parts, but it was
actually the **Labor** sub-tab. The cabin-filter PART overrides MUST live on the **Parts**
sub-tab — a Labor-tab row is the wrong place and won't carry a part.
- **FIX:** switch sub-tabs with a real `browser_click` on the sub-tab's ref (from a snapshot),
  NOT `__fire`. Refs shift each render, so snapshot first.
- **THE RELIABLE TELL for which sub-tab you're on:** expand a row and look at the sub-panel.
  - **Labor sub-tab** → expand shows "Labor hrs / Labor Rate / CP $38" fields.
  - **Parts sub-tab** → expand shows a parts table ("Add Custom Parts" link, Part Name
    react-select, Quantity, Unit, Price). Also: the part input
    `[id="@tekion-repairOrders-opcodeManagementV2-customPartsTableCols-customPartsMenuActionId"]`
    and `#customerPayUnitPrice_undefined` only EXIST when expanding a Parts-tab row.
  - Programmatic check: the active left-rail item carries an `active`/selected class; or test
    `!!document.querySelector('input[id*="LaborHrs"]')` after expanding (Labor) vs the part
    input id above (Parts).

### 2. The main "Update" click via `__fire`/dispatchEvent saves the BASE opcode, NOT the override rows
Clicking the bottom **Update** button with synthetic events fired a PUT to
`/api/service-module/u/opcode/RACF_876` carrying the **base opcode body (~2894 bytes, NO
override rows)** — and the API read-back still showed 42 rows (my new RAV4 2019 row did NOT
persist). So a synthetic Update click can register, even fire a network call, and STILL not
commit the override you added.
- **FIX:** use a REAL `browser_click` on the Update (or Overrides "Save"
  `#btnSalesSetupSave[1]`) ref — synthetic clicks are unreliable for the commit. THEN
  **verify via the backend API read-back** (see breakthrough below) that the row count
  incremented AND the new row's part/price are present. In-session row count + a "saved"
  return are NOT proof.
- To pin the exact override-write request before trusting programmatic writes: arm an
  XHR/fetch hook for non-GET to `/override|/opcode` BEFORE clicking, do ONE real-click save,
  and inspect the captured method+URL+body. (This session's synthetic click only captured the
  base-opcode PUT — the real override-save request shape still needs a clean real-click capture.)

### Verified-good single-row UI build (Parts sub-tab, this session)
The full UI recipe (Make=Toyota react-select → Model=RAV4 ant multi-select → Year 2019-2026
multi-pick → Trim modal "All trims" via REAL browser_click on the radio + modal Save via REAL
browser_click → expand row → part `87139-YZZ83` catalog match (NOT "Create") → price 30.88)
all worked cleanly and the row showed complete in-UI. The ONLY remaining gap is the COMMIT
(failure mode #2 above). So: building the row = solved; persisting it = needs a real-click
Update + API verify.

## ⚡⚡⚡ BREAKTHROUGH: Read/Write Overrides via the BACKEND API directly (2026-06-04 PM)

**The single most important discovery for RACF/override batch work.** Instead of
fighting the flaky react-select UI (which silently drops parts, jams on trim, and
dies on Browserbase idle-death), you can read AND verify override rows DIRECTLY from
Tekion's REST API with the session's own auth token. This is the AUTHORITATIVE source
of truth — the UI grid is just a (buggy) render of this data.

### Reading override rows (VERIFIED — returns full committed data)
The override data lives at:
`GET https://app.tekioncloud.com/api/service-module/u/opcode/<OPCODE>_<DEALERID>/override/<TYPE>`
- `<OPCODE>` e.g. `RACF`; `<DEALERID>` from `localStorage.currentActiveDealerId` (ST=876)
  → entityId is `RACF_876`.
- `<TYPE>` is `PARTS` or `LABOR` (UPPERCASE, plural PARTS — `PART`/`parts` return 500
  "Given Override Type doesn't exist").

**Required headers** (the manual `fetch` MUST send these or you get 500 "Token doesn't
exist or is invalid" — `credentials:'include'` alone is NOT enough; the app uses custom
headers, not cookies):
```js
const H={
 "Accept":"application/json, text/plain, */*",
 "applicationId":"ARC_NA","clientId":"web",
 "dealerId":localStorage.getItem('currentActiveDealerId'),   // "876"
 "locale":"en_US",
 "original-tenantid":"americanmotorscorporation",
 "original-userid":localStorage.getItem('__user_id'),        // or the userId from token
 "productIds":"ARC","program":"DEFAULT",
 "roleId":localStorage.getItem('currentActiveRoleId'),
 "subApplicationId":"US",
 "tek-siteId":localStorage.getItem('currentActiveSiteId'),   // "-1_876"
 "tekion-api-token":localStorage.getItem('t_token'),         // the JWT
 "tenantname":"americanmotorscorporation",
 "userId":localStorage.getItem('__user_id')
};
const r=await fetch('https://app.tekioncloud.com/api/service-module/u/opcode/RACF_876/override/PARTS',{credentials:'include',headers:H});
const j=await r.json();   // { data:[ {overrideResponse:{...}}, ... ], status:'success' }
```
**To capture the EXACT headers the app uses** (most robust — token/role/site auto-correct):
hook XHR+fetch on the opcode LIST page, then SPA-navigate to the edit page (the hook
survives `history.pushState`+popstate but NOT a full reload), click Overrides→Labor to
fire one override call, and read `window.__reqLog[0].hdrs`. (LABOR fires on tab open;
PARTS you then fetch manually with those headers.)

### Override row JSON schema (per row in `data[].overrideResponse`)
```
{ id, entityId:"RACF_876", order:<int 1..N>, entityType:"OPCODE",
  parameters:[
    {parameter:"MAKE",  value:{makes:["toyota"]},           allValues:false},
    {parameter:"MODEL", value:{models:["RAV4"]},            allValues:false},
    {parameter:"YEAR",  value:{years:["2018","2017",...]},  allValues:false},   // STRINGS, desc order
    {parameter:"TRIM",  value:{trims:[],trimFilterDetails:{},standardTrimFilterDetails:{},
                               trimSelectionType:"ALL"},     allValues:false}   // "ALL" = All trims
  ],
  override:{ type:"PARTS",
    customParts:[{ id:null, partId:"M_TMNA_87139YZZ81", partNumber:"87139YZZ81",
                   partName:"87139-YZZ81 - ELEMENT, AIR REFINER", overriddenQuantity:1, uom:"ea",
                   customerPay:{overriddenPrice:30.88,sourcePrice:null,linkedToSource:false},
                   warrantyPay:{overriddenPrice:30.88,...} /* + internalPay */ }],
    sourceParts:[], customerPartPricingEnabled:true, eligibleForPartPreparation:true, ... }}
```
- **partId format**: `M_TMNA_` + partNumber with dashes stripped (`87139-YZZ81`→`M_TMNA_87139YZZ81`;
  `87139-48020-83`→`M_TMNA_871394802083`).
- **partName format**: `"<dashed-number> - ELEMENT, AIR REFINER"` (cabin filters) or
  `"<num> - FILTER, AIR A/C"` for 88568-series. Read an existing row to copy the exact suffix.
- **A row with EMPTY `customParts:[]` is INCOMPLETE** — the vehicle saved but the part didn't.
  Audit for these: `data.filter(r=>!r.overrideResponse.override.customParts.length)`.

### Auditing committed rows (use this BEFORE adding — prevents duplicates & finds bad rows)
```js
const rows=j.data.map(rec=>{const o=rec.overrideResponse;const p=o.parameters;
 const g=n=>p.find(z=>z.parameter===n)?.value;
 const yrs=(g('YEAR')?.years||[]).map(Number);
 return {order:o.order, model:(g('MODEL')?.models||[]).join('|'),
   yspan:yrs.length?Math.min(...yrs)+'-'+Math.max(...yrs):'(none)',
   nParts:o.override.customParts.length, part:o.override.customParts.map(x=>x.partNumber).join(',')};
}).sort((a,b)=>a.order-b.order);
```
Verified 2026-06-04 (CONFIRMED CURRENT BASELINE): ST RACF has **42 committed rows**
(orders 1-42), ending at RAV4 2006-2018. This is the AUTHORITATIVE floor — read it via
the PARTS endpoint at the START of any RACF session and reconcile against any prior
claimed total before adding rows. (Earlier sessions falsely claimed 43/46; reload-verify
proved 42.) All 42 complete EXCEPT order 42 (RAV4 2006-2018) which had `customParts:[]` —
a prior UI save dropped its part; needs 87139-YZZ82 @ $30.88 re-attached.
KNOWN GAP (still open): the override WRITE request shape was NOT cleanly captured —
a synthetic Update click only fired the base-opcode PUT (no override rows), and a real
UI build's commit was interrupted by idle-death. Next session: do ONE clean real-click
save with an XHR/fetch hook armed (non-GET to /override) to capture method+URL+body,
then either replay via API or continue UI builds with real-click commits + API read-back.
Remaining Page-2 to add (~16 Toyota + 5 Scion): RAV4 2019-2026→87139-YZZ83, RAV4 EV
2012-2014→YZZ82, RAV4 Prime 2021-2024→YZZ83, Sequoia 2008-2021→YZZ82 / 2023-→YZZA8,
Sienna (3 bands), Solara, Tacoma, Tundra (2), Venza (2), Yaris, + Scion edge cases.
This API read is the ONLY reliable way to know the true committed state — the UI grid
frequently renders EMPTY even when all 42 rows exist in the backend (a render bug, NOT
data loss). NEVER trust the visual grid for row counts; always read the API.

### Write endpoint (TO CAPTURE — do not guess the schema for production financial data)
The create/update call is a non-GET to the override path. Before writing rows
programmatically, CAPTURE one real save: hook `XMLHttpRequest.prototype.open/send` +
`window.fetch` for non-GET to `/override`, add ONE row through the UI (or re-save the
incomplete RAV4 2006-2018 row), and record method+URL+body. Then replay that exact
shape for the remaining rows via `fetch`. Direct API writes are NOT discarded by SPA
reload (unlike unsaved UI rows) — get the schema right from a captured real request
first. ⚠️ This is live pricing data across a production DMS — verify each write by
re-reading the PARTS endpoint and confirming the new row's part+price.

## Overrides Tab — Vehicle/Part Overrides (2025-06-04)

The Overrides tab on the opcode edit page is a **completely different UI** from
the Default tab. It has its own sub-tabs and react-select cascading dropdowns.

### Sub-Tabs
- **Labor** — vehicle labor time overrides (separate from main opcode labor)
- **Parts** — vehicle-specific part overrides (THIS is where cabin filter part overrides go)
- **Fees**, **Cost Center**, **Associated Opcodes**

### Vehicle Selection Pattern (Cascading React-Select)
The override rows use react-select with cascading filters:
1. **Make** → type Toyota, select from dropdown
2. **Model** → enables after Make; type "86", "4Runner", etc. **Note**: "86" and "GR86" are separate entries
3. **Year** → **MULTI-SELECT** — click individual years (not a range input!)
4. **Trim** → enables after Year; usually "Select All"

### Part Selection Priority (Cabin Filters — Joe's Rule)
1. **Standard replacement** first (e.g., YZZ81, YZZ82)
2. **Premium filter** if standard not available (e.g., YZZ96)
3. **OE part number** if neither available (e.g., 88890-41010)

All cabin filter parts priced at **$30.88** (2025-06-04).

### ✅ VERIFIED INPUT RECIPE — Browser Tool CAN Drive Override React-Selects (2025-06-04)

**CORRECTION to prior note**: The browser tool (via `browser_console`) CAN drive the
override cascading react-selects. The prior "not automatable" claim was wrong — the
issue was using the wrong event sequence. The working recipe:

**Reaching the override row reliably:**
- ⚠️ **CRITICAL — NEW OVERRIDES GO IN A FRESH ROW, NOT ROW 0.** The Parts (and Labor)
  sub-tabs of an opcode that already has overrides contain EXISTING rows (e.g. RACF at
  Stevens Creek Toyota has 34 Page-1 rows: trim_0…trim_33). Row 0 sits at y≈293 — the
  SAME coordinates as the empty "add a row" widget on a blank opcode. **Editing by
  coordinate (y~308) on a populated opcode OVERWRITES the first existing override**
  (verified 2025-06-04: accidentally changed a 4Runner override to Prius; recovered by
  reloading WITHOUT saving). ALWAYS scroll to the bottom and click **"Add override"**
  (its button reports x≈-1120/y≈1875 in DOM — it's the LAST element; scroll the inner
  container to bottom first) to spawn a NEW empty row, then operate on that new row's
  coordinates. Count existing rows via `document.querySelectorAll('input[id^="trim_"]').length`
  BEFORE editing — if >0 (or >1), you must add a row, never edit in place.
- **Recovery if you edit the wrong row**: do NOT save. Navigate `window.location.href='/ro/opcode/edit/RACF'`
  (SPA reload) — it discards all unsaved React state and restores original rows. Verify
  row 0 reverted before continuing.
- The visible Make input has a unique id: `#@tekion-repair-orders-opcodeManagementV2-vehicleOverrideTable`
  (NOTE: id literally starts with `@` — must escape in CSS as `[id="@tekion-...vehicleOverrideTable"]`,
  NOT `#@...` which is an invalid selector). There are 3 duplicate widgets in DOM
  (hidden template rows at negative-X); filter by `getBoundingClientRect()` x>200 && x<1300
  to get the VISIBLE one. The visible Labor-row sits at y~308.

**Step 1 — Make field (text-filter react-select):** open the menu with the React
native value setter + `input` event (this is what surfaces the filtered options):
```js
const inp=document.querySelector('input[id="@tekion-repair-orders-opcodeManagementV2-vehicleOverrideTable"]');
inp.focus();
const setter=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
setter.call(inp,'Toyota');
inp.dispatchEvent(new Event('input',{bubbles:true}));   // ← opens the menu with "Toyota" option
```

**Step 2 — Commit an option** (THE KEY that defeated every prior attempt): dispatch
real `mousedown`→`mouseup`→`click` on the `[class*="-option"]` element. A plain
`.click()` alone does NOT commit react-select:
```js
document.querySelectorAll('[class*="-option"]').forEach(e=>{
  if((e.textContent||'').trim()==='Toyota' && e.offsetParent){
    ['mousedown','mouseup','click'].forEach(t=>
      e.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
  }
});
```

**Step 3 — Model / Year (click-to-open dropdowns, not text filters):** open by
dispatching `mousedown`→`mouseup`→`click` on the `[class*="selectedValues_container"]`
cell (locate by coordinates — Model cell ~x654/y308, Year cell ~x904/y308), then
commit the option with the same 3-event dispatch as Step 2.

**Year is MULTI-SELECT** (checkboxes, search box at top). The menu stays open after
each pick, so you can select an entire PDF year-range (e.g. 2001-2009) in ONE row.
Confirmed multi-select via vision. (To check a year, click its checkbox/option with
the same mousedown/mouseup/click dispatch.)

**Step 4 — Trim: FILTER BY ENGINE TYPE (Joe's rule, 2025-06-04):** Do NOT blindly
"Select All" trims. Cabin filter part numbers can differ by engine variant (e.g.
1.8L gas vs plug-in hybrid). Workflow:
1. Open the Trim dropdown — it lists trims, often groupable/filterable by engine type.
2. **Filter/select by engine type**, then click **Apply**.
3. If multiple engine types share the SAME part number → select them together (one row).
4. If engine types take DIFFERENT part numbers → create a SEPARATE override row per
   engine variant, each with its own trim-engine selection and its own part number.
5. "Switch to trims selected" once the engine filter is applied, to confirm the right
   trims are captured before moving to the part field.
This prevents assigning the wrong filter to a hybrid/PHEV variant.

**Step 5 — PART NUMBER lives in an EXPANDABLE SUB-ROW (Joe, 2025-06-04):** The part
field is NOT visible in the override row. It appears only AFTER Make/Model/Year/Trim
are all filled, by EXPANDING the row:
1. Click the **caret expander** in the leftmost cell of the row:
   `div.rt-td.rt-expandable` containing `[data-test-id$="-expanderIcon"]`
   (the icon has classes `icon-caret-down root_table_pivotIcon__... root_table_isExpanded__...`
   once open). The cell carries `tablefieldid="parts"` and
   `data-test="@tekion-repair-orders-opcodeManagementV2-vehicleOverrideTable"`.
   Per-row id pattern: the row is `#<N>` (e.g. `#31 > div.rt-td.rt-expandable`).
2. The expanded panel reveals a **Parts table** with:
   - An **"Add Custom Parts"** link (above the table)
   - Columns: **Part Name | Quantity | Unit | Price**
   - Part Name is a react-select (search the part number, e.g. `87139-YZZ81`, then
     pick the catalog match `"87139-YZZ81 - ELEMENT, AIR REFINER"`; use the bare-number-
     first → "Create" fallback search order from the Default-tab parts workflow)
   - Quantity defaults to `1`, Unit = `each`
   - Set **Price = 30.88** (all cabin filters) via real keyboard / browser_type
3. Three checkboxes also appear in the expanded panel: "Enable Part Price Cap" (leave
   unchecked), "Consider for Parts preparation on Appointment" (checked by default),
   "Eligible for Customer Pay Special Parts Pricing in Customer Management" (checked).
4. The Overrides **Save** button is `querySelectorAll('#btnSalesSetupSave')[1]`.

### ✅ EXACT SELECTORS (Joe-provided & verified, 2025-06-04)

**Make:** click the field, type `T`, press **Enter** → autofills "Toyota".

**Model / Year dropdown options are NOT `[class*="-option"]`** — that's why option
queries returned 0. They are multi-select CHECKBOX divs with ids
`react-select-NNN-option-N` inside container `css-11unzgr`:
- Model menu (row 33 example): `#\33 3 > div:nth-child(4) > div > div.css-31vm84 > div > div`
- Year menu (row 33 example): `#\33 3 > div:nth-child(5) > div > div.css-1r478zj > div > div`
- Each option: `<div id="react-select-168-option-0" class="flex full-width"><label class="...ant-checkbox-wrapper"><input type="checkbox" data-test="@tekion-repair-orders-opcodeManagementV2-vehicleOverrideTable-multiSelect-checkbox">`
- **→ QUERY OPTIONS WITH `[id^="react-select-"][id*="-option-"]`** (read the `<label>`/
  text to match the year/model, click that element with mousedown/mouseup/click).

**Trim opens an `ant-modal`** (the ENGINE-FILTER dialog — Joe's engine rule in UI form):
`body > div:nth-child(41) > div > div.ant-modal-wrap.ant-modal-centered > div`
Contains "Filters (0)" + Apply, radios "All trims (including future trims)" vs
"Specific trims", an **Engine-Liter filter** (e.g. "3.5L"), and N search results.
Set Engine-Liter to isolate the variant → Apply → pick All/Specific trims. For
single-engine year ranges, "All trims" is fine.

**Part Name input** (expanded sub-row): `#partName_undefined > div > div.css-1jt2rif`;
actual input id `@tekion-repairOrders-opcodeManagementV2-customPartsTableCols-customPartsMenuActionId`.
Type the PDF part number (e.g. `87139-YZZ81`), then select the catalog match.

**Price input** (expanded sub-row): `#customerPayUnitPrice_undefined`
(`<input class="ant-input-number-input">`) — set to `30.88`.

### ✅✅ FULLY VERIFIED END-TO-END SEQUENCE — PERSISTS (2026-06-04, Prius test)

This sequence added Toyota/Prius/2001-2009/All-trims/87139-YZZ81/$30.88 to ST RACF
and SURVIVED A PAGE RELOAD. Row count 34→35, part+price intact after reload.

**THE KEY INSIGHT that unblocked everything:** committing Make=Toyota makes Tekion
**regenerate a NEW empty row below**. So the "bottommost" row is now the fresh empty
one — the row you're editing moved UP. **Do not target by "bottommost" after each
commit.** Instead, scope by row CONTENT: find the `.rt-tr` whose cell[2] (Make)
matches and cell[3] (Model) is/ isn't yet set. Cell indices in `.rt-tr`:
`children[0]`=expander, `[2]`=Make, `[3]`=Model, `[4]`=Year, `[5]`=Trim (`#trim_N`).

**Steps (all via browser_console; ~2s sleep between each; verify with browser_vision):**
1. Be on ST → RACF → Overrides tab → **Parts** sub-tab (click the text "Parts",
   children.length===0, with mousedown/mouseup/click). Confirm `trim_` rows present.
2. **Make:** find bottommost `input[id^="@tekion-repair-orders-opcodeManagementV2-vehicle"]`,
   native-setter `'Toyota'` + input event, wait, then commit the option via
   `[id^="react-select-"][id*="-option-"]` whose text==='Toyota' (mousedown/mouseup/click).
   A NEW empty row spawns below — expected.
3. **Model:** re-find the row by content (cell[2] matches /Toyot/ AND cell[3] is
   "Select..."). Click that row's Model dropdown CONTROL (the `.rt-td` cell at index 3,
   click its inner control div). Wait. Now `[id^="react-select-"][id*="-option-"]`
   returns the 88 options — find text==='Prius', commit with mousedown/mouseup/click.
4. **Year (multi-select):** re-find row (cell[3] now contains 'antd' ellipsis id =
   Prius set). Click its Year cell (index 4) control. Options appear; loop the year
   range (e.g. 2001-2009), commit each with mousedown/mouseup/click — menu stays open.
5. **Trim:** the trigger is the `#trim_N` input's WRAPPER, not the input itself.
   `document.querySelector('#trim_33')` then click up the parent chain
   (`.ant-input-affix-wrapper` worked) with mousedown/mouseup/click → ant-modal opens.
   Select radio "All trims (including future trims)" (for single-engine ranges), then
   click the modal's **Save** button (modal has Apply/Cancel/Save — use Save).
6. **Expand parts sub-row:** find the Prius row, click its
   `[data-test-id$="-expanderIcon"]` in cell[0]. One expanded sub-table appears.
7. **Part:** `document.querySelector('[id="@tekion-repairOrders-opcodeManagementV2-customPartsTableCols-customPartsMenuActionId"]')`
   (attribute selector — the `@` breaks `#id` syntax). native-setter the part number
   + input event, wait ~3s, then commit the **real catalog match**
   `[id^="react-select-"][id*="-option-"]` whose text matches
   `/^87139-YZZ81 - ELEMENT/` — NOT the `Create "..."` fallback option.
8. **Price:** `#customerPayUnitPrice_undefined` native-setter `'30.88'` + input +
   change + blur events.
9. **SAVE:** `document.querySelectorAll('#btnSalesSetupSave')` → `[0]`="Update",
   `[1]`="Save". Click `[1]` with mousedown/mouseup/click. Row count increments.
10. **VERIFY PERSISTENCE:** `window.location.href='/ro/opcode/edit/RACF'` (SPA reload,
    NOT browser_navigate), wait ~9s, re-click Overrides→Parts, confirm row count held
    and the Prius row exists. Read price via input `.value` (not innerText):
    `[...document.querySelectorAll('input[id^="customerPayUnitPrice"]')].map(p=>p.value)`.

**Pitfalls hit & solved this run:**
- `[class*="-option"]` returns 0 → use `[id^="react-select-"][id*="-option-"]`.
- After Make commit, a new empty row spawns → re-scope by row CONTENT every step.
- Trim input click does nothing → click the input's `.ant-input-affix-wrapper` parent.
- Part `@`-prefixed id breaks `querySelector('#...')` → use `[id="..."]` attribute form.
- Remote Browserbase blanks to about:blank repeatedly (~4×/session) → keep each
  re-login fast; OTP via `caliber-ops/scripts/fetch_otp.py` (sleep 13s before fetch).
- Price reads empty in innerText because it's an input `.value`.

**Data-quality rules learned across multiple rows (Prius + Prius c verified runs):**
- **Tekion's Year list can be NARROWER than the PDF range.** Prius c PDF says
  2012-2021, but Tekion only offers Prius c through 2019 (US discontinued after 2019).
  When the dropdown tops out below the PDF's upper year, **select every year Tekion
  actually has** and move on — there's no phantom year to assign. Always diff your
  desired years against the available options and proceed with the intersection;
  never block waiting for a year the catalog doesn't list.
- **Exact model-name mapping:** PDF "PRIUS c" → Tekion option "Prius c" (lowercase c).
  Tekion Prius variants seen: "Prius", "Prius Plug-In", "Prius Plug-In Hybrid",
  "Prius Prime", "Prius c", "Prius v". Match the PDF model to the right one (e.g.
  PDF "PRIUS PHV" = Plug-In Hybrid, "PRIUS V" = Prius v).
- **Part-pick rule restated (Joe-confirmed):** use STANDARD REPLACEMENT column part if
  it has any value (even if identical to OE); fall to Premium Charcoal (CH) only if
  Standard blank; fall to OE only if both blank. Prius=87139-YZZ81, Prius c=87139-YZZ82.
- **Single-engine year range → radio "All trims"** is correct and clean. Reserve the
  engine-filter + "Specific trims" path ONLY for rows the PDF splits by engine
  (e.g. regular Prius 2016+: YZZ83 std for 2ZRFXE/M20AFXS vs the YZZ93 charcoal row).
- **Remote Browserbase reliably blanks to about:blank between turns (~once per turn).**
  Budget for a full fast re-login (email→Next→password→Login→OTP via fetch_otp.py with
  `sleep 14` before fetch→verify) + dealer switch BC→ST at the start of essentially
  every row session. This is normal, not a failure — just re-establish and continue.

**⚠️ WORKFLOW ORDERING RULE (Joe-corrected, 2026-06-04):** FINISH EVERY YEAR/ENGINE
ROW OF A MODEL BEFORE MOVING TO THE NEXT MODEL. Each PDF model has multiple year-band
rows (e.g. regular Prius = 2001-2009 + 2010-2015 + 2016- ). Do NOT do the first band
and jump to the next model. Map out the full set of bands for a model up front, then
add them all. Verified Prius (regular) complete block = 3 Tekion rows:
  - 2001-2009 1NZFXE → 87139-YZZ81
  - 2010-2015 2ZRFXE → 87139-YZZ82
  - 2016-2027 2ZRFXE/M20AFXS → 87139-YZZ83 (both engines share the std part, so ONE
    "All trims" row covers them — no engine split needed when std parts match).
  (Prius c 2012-2019 → 87139-YZZ82 is a SEPARATE model, not part of the Prius block.)
**OE-only overlap rows:** a PDF row with `----------` in BOTH Standard and Premium that
duplicates years already covered by a real-replacement row (e.g. Prius 2006-2009
87139-47020) is REDUNDANT — flag it to Joe and skip by default rather than creating an
overlapping duplicate. Don't silently OE-fallback a year range that's already covered.

**⚡ HELPER-INJECTION PATTERN (cuts round-trips, survives blank-outs):** at the start of
each row session, inject 3 helpers into the page once, then every step is a one-liner:
```js
window.__fire=(el)=>{['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));};
window.__setVal=(inp,v)=>{inp.focus();const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(inp,v);inp.dispatchEvent(new Event('input',{bubbles:true}));};
window.__opt=(rx)=>{let hit=null;document.querySelectorAll('[id^="react-select-"][id*="-option-"]').forEach(e=>{if(rx.test((e.textContent||'').trim())&&!hit)hit=e;});if(hit)window.__fire(hit);return !!hit;};
```
Then: `__setVal(makeInput,'Toyota')` → wait → `__opt(/^Toyota$/)` → open Model cell →
`__opt(/^Prius$/)` → open Year cell → loop `__fire` on year options → open Trim
modal → All-trims radio + modal Save via `__fire` → expand → `__setVal(partInput,'87139-YZZ83')`
→ wait 3s → `__opt(/^87139-YZZ83 - ELEMENT/)` (NEVER the `Create "..."` option) →
set price 30.88 → `__fire(querySelectorAll('#btnSalesSetupSave')[1])`. NOTE: helpers
are wiped by the about:blank blank-out / SPA reload — RE-INJECT them after every
reload-verify before starting the next row.

**Empty add-row container:** under the active tabpane,
`...ro_opcodeOverrides_leftPanel__wxxwc2QQjK`. Fill its dropdowns; a new empty row
regenerates below. Row ids are `#<N>` (react-table index); expander cell is
`#<N> > div.rt-td.rt-expandable`.

### ✅✅✅ PRODUCTION BATCH METHOD — ONE-CALL `__buildRow()` (VERIFIED 2026-06-04, 8+ rows persisted)

This is the FASTEST, most reliable way to add many override rows. Verified on the
browser tool (Browserbase) across Prius variants + full RAV4 family — every row
persisted across reload. ~30s per model, one `browser_console` call + one save call.

**Key wins that made batching work (beyond the single-row recipe above):**

1. **Year dropdown is react-window VIRTUALIZED — you CANNOT scroll it.** Only ~4
   year `<div>`s render in DOM at a time (`.css-11unzgr` has `scrollHeight==clientHeight`,
   no inner scroll). BUT: when you OPEN the year menu, `.css-11unzgr` immediately lists
   the FULL available range as option text (e.g. "All,2026,2025,...,1996"). So **read
   `[...document.querySelectorAll('.css-11unzgr [id*="-option-"]')].map(e=>e.textContent.trim())`
   right after opening** — it returns ALL years, not just the 4 visible. Then loop and
   `__fire()` every option whose text is in your desired-years list. Do NOT try to
   scroll/wheel the menu — it does nothing. (Earlier confusion: vision shows a scrollbar
   + the "Search here..." header box, but that's the GLOBAL header search, not a menu
   filter — ignore it.)

2. **makeRx MUST be a CONTAINS match, not anchored.** Right after committing Make,
   the Make cell's text becomes `"option Toyota, selected. ... Toyota"` (the react-select
   a11y string). An anchored `/^Toyota$/` FAILS to re-find the row → "no-select-row" /
   "no-make-row" errors. Use `/Toyota/` (contains). Same for Scion: `/Scion/`.

3. **Async timing: don't run findRow immediately after a commit.** The new empty row
   + the committed row need ~1.5-2.5s to render. The one-call function handles this with
   internal `await sleep()` between every step. If you ever split steps across
   browser_console calls, always `sleep 2` between commit and the next findRow.

4. **Promise + poll pattern for browser_console** (it has no top-level await and returns
   immediately): kick off the async builder storing the result in a global, then poll:
   ```js
   // call 1: start
   (() => { window.__lastLog='RUNNING'; window.__buildRow({...}).then(l=>{window.__lastLog=l;}).catch(e=>{window.__lastLog='ERR:'+String(e);}); return 'started'; })()
   // terminal: sleep 28
   // call 2: read
   (() => { return {log: window.__lastLog}; })()
   ```
   The returned `log` array shows each step's result incl. `avail=` (years offered) and
   `picked=` (years actually selected) — your audit trail. Budget ~28-31s sleep for the
   full builder (it has ~22s of internal waits + catalog query time).

**THE FULL HELPER TOOLKIT (inject once per session; RE-INJECT after every reload/blank-out):**
```js
window.__fire=(el)=>['mousedown','mouseup','click'].forEach(t=>el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window})));
window.__setVal=(inp,v)=>{inp.focus();const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(inp,v);inp.dispatchEvent(new Event('input',{bubbles:true}));};
window.__commitOpt=(rx)=>{let hit=null;document.querySelectorAll('[id^="react-select-"][id*="-option-"]').forEach(e=>{if(rx.test((e.textContent||'').trim())&&!hit&&e.offsetParent)hit=e;});if(hit)window.__fire(hit);return hit?(hit.textContent||'').trim():null;};
window.__makeInput=()=>{let b=null;document.querySelectorAll('input[id^="@tekion-repair-orders-opcodeManagementV2-vehicle"]').forEach(i=>{const r=i.getBoundingClientRect();if(r.x>40&&r.x<1300)b=i;});return b;};
window.__modelText=(td)=>(td?.textContent||'').replace(/.*}/,'').replace(/All2WD.*/,'').trim();
window.__openCell=(tr,idx)=>{const c=tr.querySelectorAll('.rt-td');const cell=c[idx];cell.scrollIntoView({block:'center'});window.__fire(cell.querySelector('input,[class*="control"],[class*="selectedValues"]')||cell);};
window.__findSelectRow=(mk)=>{for(const tr of document.querySelectorAll('.rt-tr')){const c=tr.querySelectorAll('.rt-td');if(c.length<5)continue;if(mk.test(c[2]?.textContent||'')&&/Select\.\.\./.test(c[3]?.textContent||''))return tr;}return null;};
window.__findModelRow=(mk,model,yearSel)=>{for(const tr of document.querySelectorAll('.rt-tr')){const c=tr.querySelectorAll('.rt-td');if(c.length<5)continue;if(!mk.test(c[2]?.textContent||''))continue;if(window.__modelText(c[3])!==model)continue;if(yearSel&&!/Select/i.test(c[4]?.textContent||''))continue;return tr;}return null;};
window.__save=()=>{const b=document.querySelectorAll('#btnSalesSetupSave');if(b.length<2)return'no-save';window.__fire(b[1]);return'saved';};
// FULL builder: opts={make:'Toyota', makeRx?:/Toyota/, modelExact:'RAV4', modelRx?, years:['2001',...], part:'88568-52010-83', price:'30.88', dedupeModels?:[]}
window.__buildRow=async function(o){const S=ms=>new Promise(r=>setTimeout(r,ms)),F=window.__fire,SV=window.__setVal,C=window.__commitOpt,OC=window.__openCell,L=[];
 const mk=o.makeRx||/Toyota/, mrx=o.modelRx||new RegExp('^'+o.modelExact.replace(/[-/]/g,m=>'\\'+m)+'$');
 const mi=window.__makeInput();mi.scrollIntoView({block:'center'});SV(mi,o.make);await S(2600);L.push('make='+C(new RegExp('^'+o.make+'$')));await S(2500);
 let row=window.__findSelectRow(mk);if(!row){L.push('ERR:no-select-row');return L;}OC(row,3);await S(2300);L.push('model='+C(mrx));await S(1600);
 if(o.dedupeModels&&o.dedupeModels.length){row=window.__findModelRow(mk,o.modelExact);if(row){OC(row,3);await S(1800);for(const dm of o.dedupeModels){let h=null;document.querySelectorAll('[id^="react-select-"][id*="-option-"]').forEach(e=>{if((e.textContent||'').trim()===dm&&e.offsetParent&&!h)h=e;});if(h){const cb=h.querySelector('input[type="checkbox"]');if(cb&&cb.checked){F(h);L.push('dedupe-'+dm);}}}document.body.click();await S(1000);}}
 row=window.__findModelRow(mk,o.modelExact,true);if(!row){L.push('ERR:no-model-row');return L;}OC(row,4);await S(2300);
 const menu=document.querySelector('.css-11unzgr');const avail=menu?[...menu.querySelectorAll('[id*="-option-"]')].map(e=>(e.textContent||'').trim()):[];L.push('avail='+avail.join(','));
 let pk=[];if(menu){menu.querySelectorAll('[id*="-option-"]').forEach(e=>{const t=(e.textContent||'').trim();if(o.years.includes(t)){F(e);pk.push(t);}});}L.push('picked='+pk.join(','));document.body.click();await S(1200);
 row=window.__findModelRow(mk,o.modelExact);const c=row.querySelectorAll('.rt-td');const ti=c[5].querySelector('input[id^="trim_"]');const wr=ti.closest('.ant-input-affix-wrapper')||ti.parentElement;wr.scrollIntoView({block:'center'});F(wr);await S(2300);
 const md=document.querySelector('.ant-modal-centered .ant-modal')||document.querySelector('.ant-modal');if(!md){L.push('ERR:no-modal');return L;}
 const aR=[...md.querySelectorAll('.ant-radio-wrapper')].find(x=>/All trims/i.test(x.textContent));if(aR){F(aR);const ri=aR.querySelector('input');if(ri)ri.click();}await S(700);
 F([...md.querySelectorAll('button')].find(b=>b.textContent?.trim()==='Save'));L.push('trim=All');await S(2300);
 row=window.__findModelRow(mk,o.modelExact);const ex=row.querySelector('[data-test-id$="-expanderIcon"]')||row.querySelector('.rt-expandable');ex.scrollIntoView({block:'center'});F(ex);await S(2300);
 const pin=document.querySelector('[id="@tekion-repairOrders-opcodeManagementV2-customPartsTableCols-customPartsMenuActionId"]');if(!pin){L.push('ERR:no-part-input');return L;}pin.scrollIntoView({block:'center'});SV(pin,o.part);await S(3300);
 const pm=C(new RegExp('^'+o.part.replace(/[-]/g,'\\-')+' - '));L.push('part='+pm);if(!pm){L.push('ERR:part-not-found');return L;}await S(900);
 const pr=document.querySelector('#customerPayUnitPrice_undefined');pr.focus();const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;s.call(pr,o.price);['input','change','blur'].forEach(t=>pr.dispatchEvent(new Event(t,{bubbles:true})));L.push('price='+pr.value);return L;};
```

**Per-model loop:** start `__buildRow({...})` → `sleep 28-31` → read `__lastLog`
(confirm `part=...` and `price=30.88`, no ERR) → `__save()` → `sleep 4` →
read `trimRows` count (should +1) → next model. **Verify with a reload every ~8 rows.**

**dedupeModels gotcha:** some PDF models map to a Tekion option whose NAME is a
SUBSTRING of another (e.g. "Prius Plug-In" vs "Prius Plug-In Hybrid"). Committing the
shorter one may ALSO check the longer one (multi-select). Pass `dedupeModels:['Prius Plug-In Hybrid']`
to uncheck the unwanted sibling after the model commit. ALWAYS verify the final model
cell text contains ONLY your intended model.

### Updated Page-2 model-name mappings (PDF → Tekion option, VERIFIED 2026-06-04)
- PDF "PRIUS PHV" → **"Prius Plug-In"** (Tekion offers 2012-2015 only; NO standalone 2010).
  NOTE: "Prius Plug-In Hybrid" is the NEW 2025+ plug-in — WRONG for the 2012-2015 PHV.
- PDF "PRIUS V" → "Prius v"; "PRIUS c" → "Prius c"; "PRIUS PRIME" → "Prius Prime"
  (Tekion caps Prime at 2024).
- "RAV4" base offers 1996-2026; "RAV4 EV" (2012-2014), "RAV4 Prime" (2021-2024),
  "RAV4 Hybrid", "RAV4 Plug-In Hybrid" are SEPARATE Tekion options.
- Catalog year ceilings seen: RAV4 base→2026, RAV4 Prime→2024, Prius Prime→2024,
  Prius Plug-In→2015. ALWAYS read `avail=` and select the intersection.

### Part-pick note for "88568-52010-83"
Some RAV4/Scion early rows list the SAME number in OE and Standard cols (e.g.
`88568-52010-83`). Per the part rule, Standard has a value → use it. Catalog match
text is `"88568-52010-83 - FILTER, AIR A/C"` (not "ELEMENT, AIR REFINER").

### Scion is a SEPARATE Make
Scion models (iM, xA, xB, xD, tC, FR-S, iA, iQ) are under Make="Scion", not Toyota.
Use `make:'Scion', makeRx:/Scion/`. Confirm the Scion option exists in the Make menu.

### Edge cases to FLAG to Joe, not auto-add (Page-2)
- **Supra** — OE-only, TWO filters per car (WAA01+WAA02, +WAA03 for 2023). 2-filter car.
- **Yaris iA (MMVO), Scion FR-S, Scion iA, Scion iQ/iQ EV** — OE-only listings (WB001,
  88568-37020, 88568-74011/74040). Confirm whether to add OE or skip.
- **Scion tC** — table lists parts BUT PDF footnote says it "cannot be retrofitted with
  a Cabin Air Filter." CONFLICT — do not add without Joe's confirmation.
- **OE-only overlap** (e.g. Prius 2006-2009 87139-47020) — skip, already covered by a
  real-replacement row.

**Verified cascade 2025-06-04**: Make=Toyota committed, Model dropdown opened showing
88 options (incl. all Prius variants: Prius, Prius Plug-In, Prius Plug-In Hybrid,
Prius Prime, Prius c, Prius v), Prius committed, Year dropdown opened showing
2001-2027 + "All" as multi-select checkboxes. All via browser_console event dispatch.

**⚠️⚠️ ROOT CAUSE FOUND + VERIFIED FIX (2026-06-04 PM): The trim "All trims" radio in the
trim modal CANNOT be set with synthetic `__fire`/MouseEvent — it silently no-ops, leaving
the row with NO trim. An incomplete (no-trim) row then JAMS the global Save: clicking the
Overrides Save opens a "Save Changes?" confirmation modal that will NOT close because the
row is invalid. THE FIX: set the trim radio with a REAL `browser_click` on the radio ref
(e.g. "All trims (including future trims)" radio), then `browser_click` the trim modal's
Save. Verify the row's trim input now reads "All trims selected" before doing the main Save.
With a COMPLETE row, the main Overrides Save (browser_click the bottom-right "Save" button)
commits directly with NO confirmation modal. ALWAYS reload + recount rows to confirm
persistence — in-session row count is NOT proof of a backend commit. Use browser_vision
annotate to get fresh refs for the trim radio + both Save buttons; refs shift every render.**

**⚠️⚠️ EARLIER NOTE (Overrides Save confirmation modal) — the Overrides Save is a
TWO-STAGE CONFIRMATION when rows have unapplied model/year changes, and
`__fire(#btnSalesSetupSave[1])` ALONE DOES NOT COMMIT.**

When you click the Overrides "Save" button (`#btnSalesSetupSave[1]`), Tekion opens a
**"Save Changes?" ant-modal** that says: *"Following rows have changes in model and/or
year. Please apply or discard changes before saving."* and lists each changed row
(e.g. "42nd Row") with its OWN **Apply** / **Discard** toggle, plus a modal-level
**Save** button. The commit ONLY happens after:
  1. Click **Apply** on EACH listed row (the row's toggle flips "Apply"→"Applied"), THEN
  2. Click the modal's **Save** button.
If you skip the modal (as the old `__buildRow`→`__save()` loop did), NOTHING persists.
This is why the "RAV4 family persisted" claim was FALSE — those 4 rows silently reverted
on reload; only the 8 Prius rows (saved in a session where the modal WAS handled) held.

**SECOND blocker — incomplete rows JAM the modal:** if a freshly-built row is missing its
TRIM (the `__buildRow` ant-modal "All trims" step did NOT stick — observed on RAV4 rows),
the row shows blank in the Trim column, the "Save Changes?" modal stays OPEN, and the
modal Save does nothing. The row must be COMPLETE (Make+Model+Year+Trim "All trims
selected"+Part+Price) before the modal will commit.

**Modal selectors (verified):** the modal is `.ant-modal-content` (filter `offsetParent`).
Its buttons by text: a Close (×), per-row **Apply/Applied** toggle, per-row **Discard**,
and a bottom **Save**. In the annotated snapshot the per-row Apply was a button and the
modal Save was a separate button lower (~y423). USE THE BROWSER TOOL'S REAL `browser_click`
ON THE REF for Apply and modal-Save — synthetic `__fire` MouseEvents opened the modal but
the modal's own Save did not always respond to `__fire`; trusted ref-clicks are safer.

**Recovery:** if the modal jams on a bad row, `window.location.href='/ro/opcode/edit/RACF'`
(SPA reload) discards ALL unsaved rows and restores the last-committed state. Verified:
reload dropped a stuck 43→42 back to the clean 42 committed rows. SAFE on live data.

**REVISED per-row save procedure (use this, NOT the old `__save()`-only loop):**
  1. `__buildRow({...})` → wait → read log → CONFIRM `trim=All` AND part/price set.
  2. **VERIFY the row's Trim cell shows "All trims selected"** before saving (read cell[5]).
     If blank, the trim didn't stick — fix it (open the row's trim widget, "All trims",
     modal Save) before proceeding. A blank-trim row will jam the confirmation modal.
  3. Click Overrides Save (`#btnSalesSetupSave[1]`).
  4. In the "Save Changes?" modal: `browser_click` **Apply** on the new row, confirm it
     reads "Applied", then `browser_click` the modal **Save**.
  5. Wait ~5s; confirm the modal CLOSED (no `.ant-modal-content` with offsetParent).
  6. RELOAD-VERIFY (`window.location.href='/ro/opcode/edit/RACF'`) and confirm row count
     incremented AND the new row's part/price persisted. Do NOT trust in-session row count.

**✅ PERSISTENCE NOW CONFIRMED END-TO-END (2026-06-04 PM, RAV4 2006-2018):** A COMPLETE
row (trim set via REAL browser_click on the "All trims" radio → trim-modal Save →
main Overrides Save) committed and SURVIVED a `window.location.href='/ro/opcode/edit/RACF'`
reload — row count held 42→43 and the RAV4 2006-2018 band + part 87139-YZZ82 were still
present after reload. The earlier "persistence unverified" doubt is RESOLVED: the only
thing that was ever broken was the trim radio not sticking via synthetic clicks (which
left an incomplete row that jammed the confirmation modal). With a complete row, NO
confirmation modal even appears — the main Save commits directly. Net rule: **make the row
COMPLETE (real-click the trim radio, verify "All trims selected"), then a single main
Overrides Save commits; always reload+recount to confirm, never trust in-session count.**

**RECONCILIATION of the prior false "46 rows" claim:** a previous session logged 46 rows
saved, but reload showed only 42 persisted — the 4 RAV4 rows (2006-18, 2019-26, EV, Prime)
had silently reverted because their trim never stuck (synthetic `__fire` no-op) so their
saves jammed/failed. Lesson burned in: a `__save()` returning "saved" and an incrementing
in-session row count are NOT proof of a backend commit. Reload-verify is the only truth.

### ⚠️ EXECUTION-ENVIRONMENT BLOCKERS (2025-06-04) — read before a production write

These are NOT logic problems — the input recipe is proven. They are environment
issues that stopped the live Prius save test and must be handled for a safe write:

1. **The remote browser tool (Browserbase) blanks to `about:blank` mid-session.**
   Happened 3× in one session — during idle and during `browser_navigate`. Each
   blank-out = full re-login (burns a fresh OTP, ~2 min). **DO NOT do a production
   write onto a populated override page (34 live rows) on this browser** — a blank-out
   mid-save risks corrupting existing data. For writes touching live data, prefer the
   **headless Playwright route** (`login.py` injects a stable local session — no
   blank-outs, no OTP churn) and drive the SAME verified recipe there.

2. **Viewport-edge dropdown trap.** The empty "add" row sits at the BOTTOM of the
   list (y≈629 of a 720px viewport). Opening its Model/Year dropdown renders the
   menu partially OFF-SCREEN below the fold, so `[class*="-option"]` queries filtered
   by `offsetParent` return 0 options — even though vision confirms the menu is open.
   FIX: before driving the add-row, `scrollIntoView({block:'center'})` on that row's
   Make input so the dropdown has room to render on-screen. (On row 0 / top-of-page,
   the identical recipe opens all 88 options instantly — pure positioning issue.)

3. **Finding the add-row (no separate "Add override" button needed).** A populated
   Parts/Labor sub-tab keeps a PERSISTENT EMPTY ROW at the very bottom, below the last
   `trim_N`. That empty row IS the add mechanism — fill its Make/Model/Year/Trim and a
   new empty row spawns below it. To locate it: scroll to bottom, then find the
   vehicleOverrideTable Make input with the GREATEST y (lowest on page) whose row shows
   "Select..." in the Make column. The existing rows show `#antd-pro-ellipsis`
   (truncated committed value) in the Make column; the empty add-row shows "Select...".
   (An "Add override" span also exists at x≈-1120/y≈1875 but clicking it did NOT
   increment the row count — use the persistent empty bottom row instead.)

### Reference data — Prius cabin filters (Stevens Creek Toyota RACF, Page 2)
- Prius 2001-2009, engine 1NZFXE → Standard `87139-YZZ81` @ $30.88 (single engine =
  clean test row). NOTE newer Prius years split by engine (2016+ 2ZRFXE/M20AFXS take
  `87139-YZZ83` std vs `87139-YZZ93` charcoal) — exactly why the Trim-by-engine rule
  (Step 4) matters. Full Page-2 PDF data extracted from
  `doc_840e8293b680_05_CabinAirFilters2024_hi.pdf` page index 1.

### ⚠️⚠️ CORRECTION (2026-06-04 PM, second session) — `__buildRow()` is NOT a hands-off batch tool
The earlier claim that `__buildRow()` "persists reliably, ~30s/model" is MISLEADING. Two
hard truths learned re-running it on production data:

1. **`__buildRow()`'s internal trim step (synthetic `__fire` on the All-trims radio) DOES
   NOT STICK** — it leaves the row with a BLANK trim, which jams the Save confirmation modal
   and the row silently reverts on reload. So `__buildRow()` is at best a "fill make/model/
   year/part/price" helper; the TRIM must be done SEPARATELY with a REAL `browser_click` on
   the radio ref, and you must VERIFY cell[5] reads "All trims selected" before saving.
   Treat `__buildRow()` as semi-automated, NOT fire-and-forget. Reload-verify EVERY row.

2. **The Model field is a DIFFERENT widget than Make.** Make is a typeable react-select
   (`@tekion-...vehicleOverrideTable` input). MODEL is an `ant-dropdown-trigger` wrapping a
   react-select (`#displayModel_N`) — it has NO directly-typeable cell input; you must click
   the `.ant-dropdown-trigger`, then type into the dropdown's search box, then commit the
   option via `[id^="react-select-"][id*="-option-"]` (e.g. `react-select-66-option-52`).
   It is MULTI-SELECT: clicking "RAV4" can leave the menu open and a stray `.click()` can
   pull in siblings (RAV4 EV, RAV4 Hybrid...). Click the EXACT option, then `document.body
   .click()` to close, then VERIFY only your model is chip-selected before proceeding.
   `__buildRow`'s model step (native-setter into a cell input) FAILS here — returns
   "NO_MODEL_INPUT" — because there is no such input until the dropdown trigger is opened.

3. **THE DOMINANT BOTTLENECK IS SESSION-IDLE BLANK-OUT, not the form.** Browserbase drops
   the page to `about:blank` whenever the agent PAUSES between conversation turns (waiting
   on the user, long thinking, etc.) — observed 4+ times in one batch. Each blank-out = full
   re-login (fresh OTP, dealer BC→ST switch, re-inject helpers, re-navigate to RACF→Overrides
   →Parts). **The only mitigation is to run the entire batch CONTINUOUSLY in one working
   block without pausing** (Joe explicitly asked: "just run the whole batch... tell me when
   you're done"). If you must stop, expect to re-establish from scratch. For a long unattended
   batch on LIVE data, a headless Playwright session (stable local session, no idle-death,
   no OTP churn) driving the SAME verified recipe is safer than the remote browser tool.

4. **Partial-row cleanup:** a failed mid-build leaves a stray empty/partial row (e.g.
   trim_44, model="Select..."). The row's trash icon often does NOT remove it. The reliable
   cleanup is `window.location.href='/ro/opcode/edit/RACF'` (SPA reload) — discards ALL
   unsaved rows, restoring the last-committed baseline. SAFE because nothing was saved.

5. **Always recount BEFORE trusting a prior session's claimed total.** This session's stated
   floor was "46 rows" but reload showed 42; the verified floor was 43 (34 Page-1 + 9 new,
   through RAV4 2006-2018). Recount via `document.querySelectorAll('input[id^="trim_"]').length`
   on a FRESH reload before adding anything.

### Automation Notes (the `__buildRow()` batch method — use WITH the trim/verify corrections above)
- **Browser tool handles the Overrides UI**, but `__buildRow()` alone is incomplete — pair
  it with a real-click trim step + per-row reload-verify (see correction #1 above).
- **Puppeteer override saves were unreliable** (2025-06-04) — don't bother; the browser
  tool `__buildRow()` route is faster and proven. The old Puppeteer-persistence failure
  was the same incomplete-input root cause, now solved.
- **For batch overrides** (e.g. 25 cabin-filter rows): use `__buildRow()` in a
  start→sleep→read-log→save loop. Re-inject helpers after each reload/blank-out.
  Reload-verify every ~8 rows. Do NOT do them manually — automation is now faster.
- The Overrides Save button is separate from the main Update button.
- Existing overrides appear as rows in the sub-tab (Labor or Parts).

### Overrides Save Button — #btnSalesSetupSave (DUAL ELEMENT WARNING)
The page has **two** elements with `id="btnSalesSetupSave"`:
- **#0** (first match): text "Update" — the Default tab's save button
- **#1** (second match): text "Save" (inside a `<span>`) — the Overrides tab's save button

Use `document.querySelectorAll('#btnSalesSetupSave')[1]` to target the Overrides
Save button. The first match clicks the Default tab's Update button instead.
**However**: even clicking the correct Save button via browser_console does NOT
persist override changes. The button click registers but Tekion requires real
human interaction for the override form submission.

### Known Tekion Vehicle Names
Toyota models as they appear in the Model dropdown: `86`, `GR86`, `4Runner`,
`Avalon`, `Camry`, `Corolla`, `Corolla Cross`, `Corolla Hatchback`, `C-HR`,
`Celica`, `Highlander`, `RAV4`, `Sequoia`, `Sienna`, `Tacoma`, `Tundra`,
`Venza`, `Yaris`, `bZ4X`, etc. (case-sensitive, as listed in dropdown).

## Pitfalls

- **SPA navigation ONLY**: `page.goto()` for edit URLs loads the shell, not the
  edit page. Use `window.location.href` from within the SPA or the search+click
  approach via the opcode list.
- **Overrides UI input IS automatable via browser tool** (CORRECTED 2025-06-04):
  See "✅ VERIFIED INPUT RECIPE" above. The cascading react-selects CAN be driven
  with native value setter + `input` event (to open) and `mousedown→mouseup→click`
  on the option (to commit). The earlier "not automatable / saves don't persist"
  claim was likely a SYMPTOM of incomplete input (values never committed), not a
  save-layer block. Save PERSISTENCE remains UNVERIFIED end-to-end — finish the
  Prius test before declaring it solved either way.
- **`#btnSalesSetupSave` is DUPLICATED**: Two elements share this ID — #0 says
  "Update" (Default tab) and #1 says "Save" (Overrides tab). Use
  `querySelectorAll('#btnSalesSetupSave')[1]` for Overrides. The first match
  clicks the wrong button.
- **Save Draft changes opcode status to "Draft"**: Clicking Save Draft on an
  Active opcode changes its status to Draft. This may prevent subsequent saves
  or change behavior. Prefer Update over Save Draft, but Update requires real
  mouse clicks (Puppeteer `page.mouse.click`) — dispatchEvent won't work.
- **Browser tool can't save in V2**: `browser_console` dispatchEvent/btn.click()
  on Update/Save Draft buttons does NOT trigger React form submission. Only
  Puppeteer `page.mouse.click(x, y)` can save changes. The browser tool is for
  login + dealer switch + field population only.
- **Dealer switch must NOT reload**: `page.reload()` resets the dealer to the
  default (BC). The dealer change persists via SPA state. Wait for natural
  page navigation to settle instead.
- **Never use `page.click(selector)` or `page.$(sel).click()`**: Puppeteer
  ElementHandles detach when the page re-renders. Use `page.evaluate()` to
  dispatch clicks directly in the DOM, or use `page.mouse.click(x, y)` with
  coordinates from `getBoundingClientRect()`.
- **Global search ≠ opcode search**: The header `"Search here..."` navigates
  to Repair Orders. Use the opcode page search `"Search..."` (lowercase,
  in the page body, not the header).
- **React value sticking**: DOM `value` setter + events does NOT survive
  React re-renders. Use `page.type()` (Puppeteer) or `browser_type`
  (browser tool) to trigger React change handlers. The Ant Design InputNumber
  commits its value on **blur** (Tab), not on input/change events.
- **Don't loop**: If an opcode update fails after 3 genuinely different
  approaches (browser tool + browser_console, Puppeteer keyboard, Puppeteer
  mouse coordinates), tell Joe which fields are done and which remain.
  He can complete the rest manually in ~2 minutes. Looping indefinitely
  on one opcode blocks all other work.
- **Scroll container**: `.overflow-auto[1]` is the main content scroll.
  The page body is fixed ~720px — never scroll `window` alone. Sometimes
  both `.overflow-auto[1]` and `window.scrollTo()` are needed for full
  scroll coverage.
- **Node detached**: ElementHandles from `page.evaluateHandle()` become
  invalid after SPA navigation. Always re-fetch handles after navigation.
- **OTP must be FRESH**: Always click Resend and wait for a NEW email.
  Old OTPs expire quickly. The `get_otp.py` script polls for new emails
  by counting before/after Resend.
- **Part Name is react-select, NOT Ant Design**: The parts table uses
  `react-select` (`css-2b097c-container`, `#partName_undefined`), not
  `.ant-select`. Targeting `.ant-select-selector` in the parts row is wrong.
  Use `#partName_undefined .css-g88mmg-control` to open the react-select
  dropdown, then find the search input via `[id*=\"partName\"] input`.
- **Non-catalog parts require \"Create\"**: If searching for a part number
  that doesn't exist in the dealership's catalog, react-select shows a
  single option: `\"Create \\\"PARTNUM\\\"\"`. Click it to create the part inline.
  No separate \"Add Part\" flow needed. **Try the bare number first** (e.g.,
  `\"408\"` not `\"BG 408\"`) — Tekion's catalog often indexes by base part
  number without the brand prefix. Wait 2-3 seconds after typing for
  react-select to query the catalog and display results.
- **Update may succeed silently**: The Update button can save successfully
  without showing a toast notification. Always verify by reloading the
  page and checking that values persisted.
- **Flag time ≠ dollar rate**: The spinbuttons with \"hr\" labels are flat
  rate hours (flag time), NOT dollar amounts. Customer and Manufacturer
  should be set to the labor hours (typically 1.0). The actual dollar
  rate goes in the Pay Type Pricing Setup table under the CP row — change
  the Labor Rate dropdown to \"Fixed Price\" and enter the dollar amount
  in the revealed input.
- **CP row selection in evaluate context**: The `rt-tr-group` rows show
  concatenated text like \"CPAllSelect\" (a header) and \"CP%$$%$$\" (the
  actual pricing row). The header row does NOT contain the ant-select
  dropdown. Target the pricing row with text matching \"CPAllSelect\" BY
  checking for `.ant-select-selector` inside the row. If evaluate-based
  selection fails (no ant-select found), the row is the wrong one.
- **Puppeteer nativeSetter does NOT trigger React**: Using
  `nativeSetter.call(input, '339.00')` + events sets the DOM value but
  React ignores it on save. Use `document.execCommand('insertText')`
  in evaluate context, or `page.keyboard.type()` in Puppeteer.
- **React InputNumber commits on blur**: Tab after typing is ESSENTIAL
  for Ant Design InputNumber spinbuttons.