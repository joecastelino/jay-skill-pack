---
name: tekion-spa-data-extraction
description: Extract data from Tekion's SPA when raw API calls fail due to the axios auth interceptor. Covers XHR hooks, React fiber state extraction, dirty-form PUT capture, and Playwright browser tools — the four proven methods for getting menu JSON, included service IDs, and other SPA-held data.
---

# Tekion SPA Data Extraction (When API Is Blocked)

Extract data from Tekion's Single Page Application when raw API calls fail due to the axios auth interceptor. This is THE method for getting menu JSON, included service IDs, opcode lists, and any other SPA-held data that `fetch()` or raw `XMLHttpRequest` can't reach.

## When To Use This

- You need the full menu JSON but `GET /api/.../setup/{id}` returns "Token doesn't exist or is invalid" (500)
- You need included service IDs but the API endpoint rejects bare requests
- You need any SPA state data that's not exposed through the OpenAPI
- You've been fighting the "Token doesn't exist" wall for more than 2 attempts

## Why Raw API Calls Fail

Tekion's SPA uses an **axios interceptor** that injects auth headers (`t_token` from localStorage + dealer-id + site-id headers) into every request. `fetch()` and raw `XMLHttpRequest` calls from outside the SPA's axios instance completely bypass this interceptor → 500 "Token doesn't exist or is invalid."

The `t_token` in localStorage is a JWT, but it's NOT sufficient alone — the axios interceptor adds additional context headers that the backend requires.

## Method A: XHR Hook (Capture Request/Response Payloads)

**Use when:** You need to capture an API response (GET menu JSON, PUT payload, search results) that the SPA triggers during normal interaction.

**Install hook (via browser_console, :9225 /eval, or Playwright):**
```js
window.__captured = null;
const origSend = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.send = function(body) {
  const self = this;
  this.addEventListener('load', function() {
    const url = (self.__u || '');
    if (url.includes('YOUR_TARGET_PATH') && self.__m === 'METHOD') {
      window.__captured = {
        status: self.status,
        responseText: this.responseText,
        requestBody: typeof body === 'string' ? body : null
      };
    }
  });
  return origSend.apply(this, arguments);
};
```

**Critical pitfall:** XHR hooks DO NOT survive SPA navigation (`location.href = ...`). The hook must be installed AFTER the page loads but BEFORE the interaction that triggers the API call. For GET requests that fire on page load, you must:
1. Install hook via browser_console or :9225 /eval
2. Use `location.reload()` (NOT `location.href = newUrl`) to preserve the hook
3. OR: trigger the interaction that fires the API call without navigation

**Persistence:** Save captured data to `sessionStorage` (survives SPA internals) or `localStorage` (survives everything) immediately:
```js
sessionStorage.setItem('__menuPayload', body);
```

## Method B: React Fiber State Extraction

**Use when:** You need data that's already loaded in the page's React component state. This is FASTER and RELIABLE — no hook timing issues, no navigation fragility.

**Find the React root:**
```js
// Tekion's React root is NOT at document.getElementById('root')
// It's at the main app div
const allDivs = document.querySelectorAll('div');
for (const d of allDivs) {
  for (const k of Object.keys(d)) {
    if (k.startsWith('__reactFiber') || k.startsWith('__reactInternalInstance')) {
      // Found it! d is a React-mounted element
    }
  }
}
```

**Walk up the fiber tree to find menu state:**
```js
let node = mainDiv[reactKey];
let depth = 0;
while (node && depth < 80) {
  const ms = node.memoizedState;
  if (ms) {
    if (ms.menus && Array.isArray(ms.menus)) {
      // FOUND! ms.menus = full menu array
      // ms.tiers = tier configuration
      // Each menu has .servicesMetaData.services[] with .referenceId and .displayName
    }
    // Also check for: ms.servicesMetaData, ms.tiers, ms.opcodes
  }
  node = node.return; // Walk UP the tree
  depth++;
}
```

**Key paths in menu state:**
- `memoizedState.menus[]` — all vehicle rows
- `memoizedState.menus[N].servicesMetaData.services[]` — services on row N, each has:
  - `referenceId` — the included service ID (hex string)
  - `displayName` — human-readable name
  - `tierIds` — which tiers this service is active for
- `memoizedState.tiers[]` — tier configuration, each has:
  - `id` — tier ID
  - `tierName` — "Basic", "Value", "Premium", etc.

**Also check React Context providers** — walk `.child` and `.sibling` too if walking `.return` doesn't find it:
```js
function walk(node, depth) {
  if (!node || depth > 30) return;
  if (node.memoizedState?.menus) { /* found */ }
  walk(node.child, depth+1);
  walk(node.sibling, depth+1);
}
```

## Method C: Dirty Form + Capture PUT

**Use when:** You need the full serialized menu JSON that the SPA sends on Save.

**How to dirty the form:**
The SPA only fires a PUT when there are unsaved changes. Clicking Save on a clean form does nothing.

**Proven ways to dirty:**
1. Add a service via Add Services dropdown (execCommand + onInputChange + pick option — see `tekion-add-services-select-automation`)
2. Remove then immediately re-add that same service (undo the removal)
3. Change the Base System Interval dropdown value

**Avoid:** JS checkbox toggles (`dispatchEvent(new MouseEvent('click'))`) on tier checkboxes — React/Ant Design often ignores these.

**Capture pattern:**
```js
// Install hook BEFORE dirtying
sessionStorage.removeItem('__menuPayload');
// ... dirty the form ...
// Click Save (real browser event needed)
// After 200: payload is in sessionStorage
const payload = sessionStorage.getItem('__menuPayload');
const menu = JSON.parse(payload);
```

## Method D: Playwright browser_* Tools (Simplest)

When the persistent browser (:9225) is fighting you, the Playwright-powered `browser_*` tools are more reliable for interactive work:

1. `browser_navigate` — logs in, handles OTP
2. `browser_console` — runs JS in SPA context (survives between turns, unlike :9225 /eval across navigations)
3. `browser_click` — real browser events (better than :9225 /mouse for React)
4. `browser_type` — native keyboard input

**Pitfall:** Session expires; must re-login via OTP.

## Quick Reference: Which Method When

| What you need | Best method | Why |
|---|---|---|
| Menu JSON (full structure) | B: React fiber | Already in memory, no timing issues |
| Included service IDs | B: React fiber on Included Services page | Already loaded in component state |
| API response for search | A: XHR hook + search interaction | Need to trigger API, capture response |
| PUT payload for Save | C: Dirty form + hook | Must go through SPA's serializer |
| Interactive UI work | D: browser_* tools | Real browser events, reliable React handling |

## Pitfalls

1. **XHR hooks die on navigation** — every `location.href =` or `location.reload()` wipes all overrides. Install hook fresh after each navigation.
2. **sessionStorage vs localStorage** — sessionStorage survives SPA internals but NOT full page reloads. localStorage survives everything. Use `localStorage` for workflows where you might navigate away and come back.
3. **React fiber key varies** — `__reactFiber$` is the modern key; `__reactInternalInstance$` is legacy. Check both.
4. **Token in localStorage isn't enough** — the `t_token` JWT needs additional context headers from axios interceptor. Can't replicate from outside.
5. **Don't use `/mouse` for React checkboxes** — the persistent browser's `/mouse` endpoint dispatches events that React's synthetic event system ignores for checkboxes. Use `browser_click` or the React fiber approach instead.
6. **Save button only fires PUT when form is dirty** — clicking Save on a clean form = no network activity. Must make a real change first.