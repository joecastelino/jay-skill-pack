---
name: tekion-add-services-select-automation
description: Automate the Ant Design v5 "Add Services" Select dropdown in Tekion service menu editing. The Select does NOT respond to normal DOM events — this skill documents the TWO working approaches discovered through extensive trial and error.
---

# Tekion Add Services Select Automation

## The Problem

The "Add Services" dropdown in Tekion's service menu editor uses Ant Design v5 Select (`antd`/`rc-select`). Standard DOM manipulation FAILS:
- ❌ `input.dispatchEvent(new Event('input'))` with value setter — no response
- ❌ `document.execCommand('insertText', false, ch)` — sets value but no dropdown
- ❌ Full `KeyboardEvent('keydown')` + `keyup` + `change` sequence — no response
- ❌ Playwright `page.fill()` / `/type` endpoint — no response
- ❌ Mouse click via `/mouse` endpoint — Select doesn't recognize as real click

## Why It Fails

Ant Design Select uses React's synthetic event system. Its state is managed through `memoizedProps.onInputChange` in the React fiber tree — direct DOM manipulation doesn't trigger React re-renders.

## Working Approach #1: React Fiber `onInputChange` (Direct)

Call the Select component's React `onInputChange` handler directly via the fiber tree.

```javascript
// 1. Find the blank "Select" row
const els = [...document.querySelectorAll('[id^="ADDED_SERVICES_NAME_"]')].filter(e => e.offsetParent);
const blank = els.findLast(e => e.innerText.trim() === 'Select');
const inp = blank.querySelector('input');

// 2. Walk up React fiber tree to find onInputChange (usually depth 14)
const key = Object.keys(inp).find(k => k.startsWith('__reactFiber'));
let node = inp[key];
for (let i = 0; i < 25 && node; i++) {
  if (node.memoizedProps && node.memoizedProps.onInputChange) {
    // 3. Call it with (value, {action: 'input-change'})
    node.memoizedProps.onInputChange('Fuel', {action: 'input-change'});
    break;
  }
  node = node.return;
}

// 4. Wait 2+ seconds for options to render
// 5. Pick option:
const opts = [...document.querySelectorAll('[class*=option]')].filter(e => e.offsetParent);
const match = opts.find(o => o.innerText.includes('Your Service Name'));
match.dispatchEvent(new PointerEvent('click', {bubbles: true, cancelable: true, pointerId: 1, pointerType: 'mouse'}));
```

**Critical gotcha**: Every call to `onInputChange` CONSUMES the blank row, even if no option is picked. You get ONE shot per page load. After picking an option, a new blank row appears — you can chain multiple adds without reloading.

**Unreliable after page reload**: The fiber tree depth and component structure can change after a `location.reload()`. This approach works best on a freshly-expanded row with NO prior reload.

## Working Approach #2: `execCommand` + `onInputChange` (More Reliable)

The combination of `execCommand('insertText')` to physically type into the input AND THEN calling `onInputChange` is the most reliable pattern:

```javascript
// 1. Find blank
const els = [...document.querySelectorAll('[id^="ADDED_SERVICES_NAME_"]')].filter(e => e.offsetParent);
const blank = els.findLast(e => e.innerText.trim() === 'Select');
const inp = blank.querySelector('input');

// 2. Type via execCommand (this triggers some React handlers)
inp.focus();
const text = 'Brake Fluid';
for (const ch of text) {
  document.execCommand('insertText', false, ch);
}

// 3. ALSO trigger onInputChange (completes the React state update)
const key = Object.keys(inp).find(k => k.startsWith('__reactFiber'));
let node = inp[key];
for (let i = 0; i < 25 && node; i++) {
  if (node.memoizedProps && node.memoizedProps.onInputChange) {
    node.memoizedProps.onInputChange(text, {action: 'input-change'});
    break;
  }
  node = node.return;
}
```

This approach worked in the browser tools (`browser_console`) and was the ONLY approach that reliably produced options.

## Setting Tier Checkboxes (Premium-Only)

After picking an option, set checkboxes to `[false, false, false, true]` for Premium tier only:

```javascript
const cbs = [...document.querySelectorAll('input[type=checkbox]')].filter(c => c.offsetParent);
for (let i = cbs.length - 1; i >= 3; i--) {
  const g = cbs.slice(i - 3, i + 1);
  if (g[3].checked !== true) g[3].dispatchEvent(new MouseEvent('click', {bubbles: true}));
  if (g[0].checked) g[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));
  if (g[1].checked) g[1].dispatchEvent(new MouseEvent('click', {bubbles: true}));
  if (g[2].checked) g[2].dispatchEvent(new MouseEvent('click', {bubbles: true}));
}
```

**Important**: The checkbox array iterates from the END (most recently added service's checkboxes).

## Finding and Expanding the Universal Row

The menu table is virtualized. To reach the bottom row:

```javascript
// Scroll the virtualized container
const cont = document.querySelector('.overflow-y-auto');
if (cont) cont.scrollTo(0, cont.scrollHeight);

// Click the last expand arrow (pivotIcon)
const cs = [...document.querySelectorAll('[class*=pivotIcon]')].filter(e => e.offsetParent);
const c = cs[cs.length - 2]; // Second-to-last = the expand button
c.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
```

## Tools That Work vs Don't

| Tool | Works? | Notes |
|------|--------|-------|
| `:9225` `/eval` endpoint | ✅ For reads, ❌ for Select | Can find and inspect React fibers |
| `:9225` `/mouse` endpoint | ❌ | Ant Design ignores synthetic mouse events |
| `:9225` `/type` endpoint | ❌ | Returns 500 or doesn't trigger Select |
| `browser_console` (Playwright) | ✅ | Real browser, `execCommand` works |
| `browser_type` (Playwright) | ⚠️ Untested | Would likely work if input has a ref |
| `browser_click` (Playwright) | ✅ | Use for Save/Publish buttons |

## Recommended Workflow

1. **Navigate** to menu edit page (`browser_navigate`)
2. **Scroll to bottom**: `browser_console` → scroll `.overflow-y-auto`
3. **Expand universal row**: `browser_console` → click last pivotIcon
4. **Add each service**: `browser_console` → execCommand + onInputChange + pick + tiers
5. **Save between batches** or after all done

## Known Limitations

- Only ~22 options appear per search (virtualized option list)
- Some included services may not appear in search (check if they're Active in Service Menu Setups > Included Services)
- The `onInputChange` approach requires finding the correct fiber depth (varies by page load)
- Cannot batch add services in a single call — each requires waiting for options
- Chrome-based browser tools required (`browser_console`); :9225 server's `/eval` alone is insufficient for typing