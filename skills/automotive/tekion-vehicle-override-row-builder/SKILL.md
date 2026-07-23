---
name: tekion-vehicle-override-row-builder
description: Add vehicle/part override rows to a Tekion opcode (Overrides → Parts tab). Copy existing row, modify model/year via checkbox dropdowns, set part/price, save. Only works in real browser tool — headless Playwright cannot render the ant-design vehicle override table.
triggers:
  - copy opcode override row
  - vehicle override checkbox dropdown
  - overrides parts tab
---

# Tekion Vehicle Override Row Builder

## When to Use
Adding vehicle/part override rows to a Tekion opcode (Overrides → Parts tab). Use when you need to add multiple model-specific rows with different year ranges and part numbers. This is the ONLY approach that works for the vehicle override table — headless Playwright/Puppeteer cannot render the ant-design checkbox dropdowns.

## ⛔ When NOT to Use — MENU PACKAGE opcodes have NO Labor/Parts override sections (verified 2026-07-03)
A SERVICE_MENU package opcode (e.g. `TEK90000VNM`, the TEK\d+[BPV][NS]M pattern) shows **only a "Cost Center" module** on its Overrides tab in Opcode Management — no Labor, no Parts sub-sections. You CANNOT build a vehicle-scoped labor time/price override there (hit live on TEK90000VNM trying to set 2.4hr/$469.88 for a specific Camry). Joe confirmed: for menu packages the vehicle-scoped labor/price fix lives in **Service Menu Setups** (the menu's vehicle rows / Included Services), not Opcode Management. Regular opcodes (RACF, 4TIRE, BG*) DO have the Labor/Parts override sections this skill covers.

## Prerequisites
- Active browser tool session (NOT headless)
- Logged into Tekion as the target dealership's account
- Token from `~/.tekion-session.json` or fresh OTP login
- Helper functions injected: `__buildRow`, `__setVal`, `__commitOpt`, `__clickCell`, `__toggleCheckbox`

## Core Workflow: Copy + Modify

### Step 1: Navigate and Verify Baseline
```
1. browser_console: window.location.href = '/ro/opcode/edit/{OPCODE}'
2. browser_click on "Overrides" tab
3. browser_click on "Parts" sub-tab (RELOAD TRAP: defaults to Labor after SPA reload)
4. Verify existing rows are visible
```

### Step 2: Copy an Existing Row
```
1. Identify a source row (preferably clean, single-model row)
2. browser_click on the Copy button (div adjacent to the row, typically with class containing 'copy' or icon)
3. A duplicate row appears with same model/years/part/price
```

### Step 3: Modify the Copy
```
1. Click Model cell → ant-design checkbox dropdown opens
2. Uncheck source model, check target model using browser_click on visible checkbox refs
3. Click Year cell → same checkbox pattern
4. Uncheck old years, check target years using browser_click on checkbox refs
5. Press Escape or click elsewhere to close dropdown
```

### Step 4: Set Part and Price
```
1. Click Part cell → react-select opens
2. Type part number (e.g., 87139-YZZ81)
3. Select from dropdown (or use __setVal + __commitOpt if part exists in catalog)
4. Set price field to target amount (e.g., 21.99)
```

### Step 5: Save
```
1. browser_click on Save button (id="btnSalesSetupSave" or ref from snapshot)
2. Handle "Save Changes?" modal: click "Apply" then modal "Save"
3. Verify: navigate away → reload → Overrides → Parts → confirm row persists
```

## The Reload Trap
After SPA reload (or navigating away and back), the Overrides tab **defaults to the Labor sub-tab**, which shows empty rows making it look like all rows were lost. **Always click the Parts sub-tab** after reload to see committed vehicle override rows.

## Model vs Year Dropdowns
- **Model**: ant-design checkbox dropdown (multi-select). Each model is a checkbox with an `.ant-checkbox` wrapper. Click the parent div or the label text to toggle.
- **Year**: Same ant-design checkbox multi-select pattern. Individual years (e.g., 2024, 2023, 2022) rather than ranges.
- Both render in a portal (not inline in the table), so snapshot element refs are valid while the dropdown is open.

## Part Selection
- **react-select** component. Type part number → select from filtered options.
- If part not in catalog: select "Create" option to add it, then proceed.
- Helper: `__setVal('partNumber-input', '87139-YZZ81')` then `__commitOpt()` to commit.

## Pitfalls
1. **Headless cannot render the vehicle override table** — the ant-design table with Copy buttons, checkbox dropdowns, and part react-select is invisible in headless mode. Must use real browser tool.
2. **JS console clicks don't trigger API calls** — `browser_console` clicks on DOM elements skip the React event system. Use real `browser_click` for Save, modal buttons, and model/year toggle operations.
3. **Browser blanks every ~2-3 turns** — session resets to about:blank, losing all refs. Requires fresh OTP login each time.
4. **Model name must match Tekion catalog exactly** — e.g., "4Runner" not "4-Runner", "Avalon" not "Toyota Avalon". Use the exact name from the Tekion model dropdown.
5. **Year ranges are individual years in the dropdown** — not "2003-2009" as a single option. Must check each year checkbox (2003, 2004, 2005, 2006, 2007, 2008, 2009) individually.
6. **The "Save Changes?" modal appears inconsistently** — sometimes after adding rows, sometimes not. Always check for it after clicking Save.

## Per-Store Parameters
Only two things change between stores:
- **Opcode name**: CABIN (Blackstone), RACF (Stevens Creek), etc.
- **Price**: $21.99 (CABIN), $30.88 (RACF), etc.

Everything else (workflow, helpers, PDF data) is identical.

## Verification Steps
After saving each row:
1. Reload the page: `window.location.href = '/ro/opcode/edit/{OPCODE}'`
2. Click Overrides → Parts (Reload Trap workaround)
3. Expand rows to confirm model, years, part number, and price match
4. Count total rows saved vs expected

## Related Skills
- `tekion-opcode-overrides` — the `__buildRow` helper and rules
- `tekion-opcode-pricing-v2` — opcode management API reference
- `tekion-autonomous-login` — headless login + OTP
- `tekion-browser-navigation` — dealer switching, tab navigation