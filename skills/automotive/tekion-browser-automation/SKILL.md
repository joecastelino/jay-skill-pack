---
name: tekion-browser-automation
description: >
  Log into Tekion DMS via browser automation or Puppeteer, retrieve OTP from Gmail
  IMAP, navigate to modules, switch dealerships, and update opcode pricing (Fixed
  Price labor rates, add parts, save). Covers Ant Design dropdown patterns,
  scrollable containers, and the complete opcode edit workflow.
trigger: Tekion login, Tekion browser, opcode management, opcode pricing, Fixed Price, Tekion OTP, dealer switching, Tekion puppeteer
triggers:
  - tekion browser login
  - puppeteer tekion
  - ant design dropdown opcode
  - switch dealership browser
---

# Tekion Browser Automation

> **⚠️ V2 NOTICE (June 2026):** This skill covers the OLD V1 opcode UI
> (rt-tr-group tables, Fixed Price combobox, cell[2] inputs). Tekion has since
> deployed opcodeManagementV2. For V2 (CP/W/I buttons, Customer spinbutton),
> use **`tekion-opcode-pricing-v2`** instead. The V2 edit page URL is
> `/ro/opcode/edit/OPCODE` but ONLY works via SPA navigation (`window.location.href`),
> not `page.goto()`. See the V2 skill for the complete dealer switch approach
> (leaf-element exact matching) and labor rate setting.

## Three Automation Approaches

### Approach A: Built-in Browser Tools (Quick/Debugging)
Use Hermes's `browser_click`, `browser_type`, `browser_console`, `browser_vision`. Good for exploration but breaks on React portals and long pages (snapshots truncated at ~248 elements).

### Approach B: Puppeteer (Recommended for Updates & Full Workflows)
Use for: opcode changes, full login+nav+edit flows, and anything requiring multi-level Tekion navigation. Puppeteer handles:
- `elementHandle.asElement().click()` / `.type()` for Ant Design components
- `page.keyboard.type()` for controlled inputs
- `page.evaluateHandle()` to find elements in deeply nested containers
- **Direct URL navigation** — skip the UI entirely with `page.goto('https://app.tekioncloud.com/ro/opcode/edit/BGFINJ')`
- Screenshot verification at each step

Chrome binary: `/home/itadmin/.cache/puppeteer/chrome/linux-148.0.7778.97/chrome-linux64/chrome`
Install: `cd /tmp && PUPPETEER_SKIP_DOWNLOAD=true npm install puppeteer`
Launch args: `['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage']` + `headless: true`

### Approach C: Playwright (Python headless — best for batch overrides)
For Python-driven headless batch jobs (opcode overrides, multi-row add). Key differences from Puppeteer:
- Async API: `from playwright.async_api import async_playwright`
- JS evaluation via `page.evaluate()` is the most reliable way to interact with react-select and Ant Design popovers
- **Login selectors (proven):**
  ```python
  # Username — :not([disabled]) avoids matching stale disabled email field
  await page.locator('input[placeholder="Type Here"]:not([disabled])').first.fill(EMAIL)
  await page.click('button:has-text("Next")')
  await page.locator('input[type="password"]').fill(PASSWORD)  # NOT input:visible
  await page.click('button:has-text("Login")')
  await page.locator('input[placeholder="Type Here"]:not([disabled])').fill(otp)
  await page.click('button:has-text("Verify and Proceed")')
  ```
- **Pitfalls:**
  - `page.goto(..., wait_until="networkidle")` NEVER completes on Tekion SPA → use `domcontentloaded`
  - `page.locator('input:visible').first` matches DISABLED fields → always add `:not([disabled])`
  - `os.path.expanduser("~")` resolves to Hermes sandbox home → hardcode `/home/itadmin` for paths

## Login Flow

1. Navigate to `https://app.tekioncloud.com`
2. Enter username: `jcastelino@scvolkswagen.com`, click Next
3. Enter password: `<TEKION_PASSWORD>`, click Login
4. Click "Resend" button to trigger fresh OTP (always get a NEW code)
5. Retrieve OTP via Python IMAP (see below)
6. Click "Verify and Proceed"

## OTP Retrieval — Fresh Code Only

**Two methods available:**

### Method 1: fetch_otp.py (Recommended for pipeline/scraper)
Uses Google Workspace API (Gmail) — reliable, no IMAP:
```bash
python3 /home/itadmin/caliber-ops/scripts/fetch_otp.py
# Returns 6-digit OTP directly to stdout
```
This is what the caliber-ops pipeline scraper uses. It searches Gmail for "Tekion-Login OTP" via the Google API and extracts the OTP. Works reliably in both foreground and cron jobs.

### Method 2: Python imaplib (For Puppeteer/Playwright scripts)
For standalone headless scripts that need fresh OTP with Resend + poll:

**Critical**: Always trigger Resend first, then wait for a NEW email (not a cached one).
Count existing OTP emails before the Resend, then poll for count to increase:

```python
import imaplib, email, re, time, sys

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('jcastelino@americanmotorscorp.com', '<GMAIL_APP_PASSWORD>')
mail.select('"[Gmail]/All Mail"')

# Count existing OTP emails
status, data = mail.search(None, '(SUBJECT "Tekion-Login OTP" SINCE "02-Jun-2026")')
initial_count = len(data[0].split())

# Poll for NEW email (count increased)
for attempt in range(12):
    time.sleep(5)
    mail.select('"[Gmail]/All Mail"')
    status, data = mail.search(None, '(SUBJECT "Tekion-Login OTP" SINCE "02-Jun-2026")')
    ids = data[0].split()
    if len(ids) > initial_count:
        status, data = mail.fetch(ids[-1], '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                payload = part.get_payload(decode=True)
                if payload:
                    codes = re.findall(r'\b\d{6}\b', payload.decode())
                    if codes:
                        print(codes[0])
                        mail.logout()
                        sys.exit(0)
print('TIMEOUT')
mail.logout()
```

Save as `/tmp/get_otp.py`, call from Node: `execSync('python3 /tmp/get_otp.py')`

## Dealer Switching

Works reliably with JS click on the popover:

```js
// Click the green dealer badge
await page.click('[class*="dealerSelect_container"]');
await delay(1000);

// Click ST in the opened popover
await page.evaluate(() => {
  const inner = document.querySelector('.ant-popover-inner-content');
  if (inner) for (const el of inner.querySelectorAll('*')) {
    if (el.textContent?.startsWith('STStevens')) { el.click(); return; }
  }
});
```

Dealers: BC, BT, ST, SV, TL, AR, VC. Pattern is "XXFull Name" (e.g., "STStevens Creek Toyota").

## Navigation

- After login + dealer switch, navigate directly to opcode: `https://app.tekioncloud.com/ro/opcode/edit/BGFINJ`
- Must switch dealer FIRST — navigating without dealer context redirects to opcode list
- **Page has nested scroll container**: `document.querySelectorAll('.overflow-auto')[1]` — all scrolling MUST target this, NOT `window` or `body`

## Opcode Pricing Update — Complete Workflow

### 1. Find the CP Row
```js
const groups = document.querySelectorAll('.rt-tr-group');
// Loop groups, find one where text starts with "CP" and includes "Select"
```

### 2. Select Fixed Price (Ant Design Combobox)
The Labor Rate dropdown is an **Ant Design Select** with `role="combobox"`, NOT React-Select:

```js
// Click the combobox to open dropdown
g.querySelector('[role="combobox"]')?.click();
await delay(1500);

// Click "Fixed Price" option
document.querySelectorAll('.ant-select-dropdown-menu-item')
  .find(item => item.textContent?.trim() === 'Fixed Price')?.click();
```

Options are: "Labor Price Guide", "Hourly Price", "Fixed Price"

### 3. Enter Labor Price (Critical Pattern)
**After selecting Fixed Price, the price input appears INLINE in the SAME cell (cell[2])**, not in a separate column! It's an `ant-input-number-input`:

```js
const numInput = g.querySelector('.ant-input-number-input');
await numInput.click();
await numInput.type('226');  // Use Puppeteer ElementHandle.type(), NOT JS setter
```

**PITFALL**: Cells 3-6 are all checkboxes (Allow Override, Discount Eligible, Sales Tax). Do NOT try to type into them — the price field is in cell[2].

### 4. Add Parts
Scroll further down (scrollTop ~2400). Find the parts table:

```js
const tables = document.querySelectorAll('table');
for (const table of tables) {
  if (table.textContent?.includes('Part Name') && table.textContent.includes('Parts Price')) {
    const partInput = table.querySelector('input');
    partInput.click();
    partInput.type('408');  // Part number
    
    // Select from Ant Design dropdown
    document.querySelectorAll('.ant-select-dropdown-menu-item')
      .find(item => item.textContent?.includes('408'))?.click();
  }
}
```

### 5. Enter Parts Price
The parts price is in the same parts table row:
```js
const priceInput = table.querySelectorAll('.ant-input-number-input, input:not([type="checkbox"])');
priceInput.click();
priceInput.type('26.22');
```

### 6. Save
Scroll to bottom (scrollTop ~2800), click "Update" button.
Page has "Save Draft", "Cancel", and "Update" buttons at the bottom.

## Puppeteer Script Template

Full script at `/tmp/tekion-bgfinj-update.mjs`. Modifiable for any opcode/store by changing:
- Part number and price
- Labor price
- Dealer code in the switch step
- Opcode in the edit URL

## Session Persistence

Tekion uses **localStorage**, not cookies. Relevant keys:
- `t_token` — JWT auth token
- `t_user` — user profile JSON  
- `dse_t_user` — dealer-scoped user data
- `currentActiveIsWorkspace` — workspace ID
- `currentActiveWorkspace` — selected dealer

**Session files:**
- Pipeline scraper: `/home/itadmin/caliber-ops/scripts/.tekion-session.json` (auto-saved by scraper)

**Health check:**
```bash
python3 -c "import json; d=json.load(open('/home/itadmin/caliber-ops/scripts/.tekion-session.json')); print(f'{len(json.dumps(d))}B, keys={list(d.keys())}')"
```
- Healthy: >1KB, all 5 keys (t_token, t_user, dse_t_user, currentActiveIsWorkspace, currentActiveWorkspace)
- Corrupted: 2 bytes (`{}`) — scraper will re-authenticate
- Sessions valid for ~20 minutes after last login

**Session reuse in Playwright:**
```python
with open(SESSION_FILE) as f:
    sess = json.load(f)
await page.goto(LOGIN_URL, wait_until="domcontentloaded")
for k in keys:
    if k in sess:
        await page.evaluate(f"localStorage.setItem('{k}', {json.dumps(sess[k])})")
await page.goto(LOGIN_URL + "/home", wait_until="domcontentloaded", timeout=15000)
```
Inject localStorage → navigate home → check `"Welcome back" in body` to confirm.

**🪤 RELOAD TRAP (Overrides tab):** After SPA reload, the Overrides tab defaults to the **Labor** sub-tab which shows EMPTY rows. Always explicitly click the **Parts** sub-tab after reload to see committed override rows. This applies to both browser tool and headless scripts.

## Known Issues

- OTP must be FRESH each run — always click Resend and wait for new email
- `ant-input-number-input` value won't stick via JS `value` setter — use Puppeteer `.type()`
- Cells 3-6 in CP row are checkboxes, NOT price fields
- Price field appears in cell[2] ONLY after selecting Fixed Price
- Never scroll `window` — use `.overflow-auto` container (index 1)
- SVG elements have `className` as `SVGAnimatedString`, not string — check `typeof` before calling `.slice()`
- Puppeteer's `$x` (XPath) doesn't exist — use `page.evaluate()` to find elements by text