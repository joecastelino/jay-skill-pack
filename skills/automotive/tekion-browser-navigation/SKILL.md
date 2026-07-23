---
name: tekion-browser-navigation
description: Log into Tekion DMS via browser, switch dealerships, navigate to Opcode Management, search for opcodes, and edit opcode details. Covers OTP retrieval via IMAP, session persistence, dealer switching pitfalls, and search quirks.
triggers:
  - tekion browser navigation
  - switch dealership
  - opcode search browser
---

# Tekion Browser Navigation & Opcode Editing

> **⚠️ V2 NOTICE (June 2026): Tekion deployed opcodeManagementV2.** If the edit
> page shows CP/W/I pay type buttons and Customer/Manufacturer rate spinbuttons
> (not a Fixed Price combobox in an rt-tr-group table), use the
> **`tekion-opcode-pricing-v2`** skill instead. This skill covers the OLD V1 UI.
> Key V2 differences: no Fixed Price dropdown, labor rate is entered in a
> `[role="spinbutton"]` Customer field, and the edit URL is
> `/ro/opcode/edit/OPCODE` (reachable by clicking the opcode text in the list).

## Prerequisites

- Tekion credentials: `jcastelino@scvolkswagen.com` / `<TEKION_PASSWORD>`
- Gmail IMAP creds for OTP: `jcastelino@americanmotorscorp.com` / `<GMAIL_APP_PASSWORD>`
- Session file: `/home/itadmin/.tekion-session.json`

## Login Flow (2FA with OTP)

1. Navigate to `https://app.tekioncloud.com`
2. Enter username, click Next
3. Enter password, click Login
4. **Fetch OTP** — use Python imaplib with polling (NOT himalaya, it fails on HTML-only emails). **Important**: OTP emails can take 10-30 seconds to arrive after clicking Resend. Poll in a loop:

```python
import imaplib, email, re, time

mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
mail.login("jcastelino@americanmotorscorp.com", "<GMAIL_APP_PASSWORD>")

otp = None
for attempt in range(8):  # poll up to ~40s
    time.sleep(5)
    mail.select('"[Gmail]/All Mail"')
    status, messages = mail.search(None, '(SUBJECT "Tekion-Login OTP" SINCE "DD-Mon-YYYY")')
    # Use today's date in SINCE filter to avoid 130+ old OTP emails
    ids = messages[0].split()
    if not ids:
        print(f"Attempt {attempt+1}: no new OTP yet...")
        continue

    # Get the latest
    status, data = mail.fetch(ids[-1], "(RFC822)")
    raw = data[0][1]
    msg = email.message_from_bytes(raw)

    # OTP is often in text/HTML part, NOT text/plain
    for part in msg.walk():
        ct = part.get_content_type()
        payload = part.get_payload(decode=True)
        if ct in ("text/plain", "text/html") and payload:
            codes = re.findall(r'\b(\d{6})\b', payload.decode(errors="ignore"))
            if codes:
                otp = codes[0]
                break
    if otp:
        print(f"OTP: {otp}")
        break

mail.logout()

if not otp:
    print("Timed out waiting for OTP — click Resend on Tekion page and retry")
```

5. Enter OTP code, click "Verify and Proceed"
6. **Save session immediately** — extract localStorage tokens:

```js
(function() {
    const keys = ['t_token', 't_user', 'dse_t_user', 'currentActiveIsWorkspace', 'currentActiveWorkspace'];
    const data = {};
    for (const k of keys) { const v = localStorage.getItem(k); if (v) data[k] = v; }
    return JSON.stringify(data);
})()
```

## Dealer Switching (CRITICAL)

The dealer switcher is notoriously difficult. **Do NOT use the chevron icon (e36)** — it often doesn't work.

### Method that works (confirmed reliable):

1. Click the dealer container via JS:
```js
document.querySelector('.root_dealerSelect_container__eXjxN2P5EN')?.click();
```

2. The dealer popover opens. The dealer list is inside `.ant-popover-inner-content` rendered as a portal. **IMPORTANT**: The popover content may not appear in the DOM immediately after `.click()` — the portal needs time to render. Use a `setTimeout` delay (~500ms) before querying the popover, or use `browser_snapshot` + `browser_vision` to verify it's open. **DO NOT use `browser_snapshot` to find dealer items** — the popover isn't in the accessibility tree. Instead, use JS with a delay to find and click the target:

```js
// Find dealer items in the popover
const inner = document.querySelector('.ant-popover-inner-content');
const items = inner.querySelectorAll('li, div, span, [role="option"], [class*="item"]');
for (const el of items) {
    const text = el.textContent?.trim();
    if (text?.startsWith('ST') && text?.includes('Stevens')) {
        el.click();
        break;
    }
}
```

**Important**: Each dealer item renders as text like `STStevens Creek Toyota` (code + name, no space). Search by prefix match (e.g., `text.startsWith('ST')`) rather than exact match.

3. **Verify** the switch — look for "ST Stevens Creek Toyota" in the snapshot. The line shows the new dealer code and name.

**Store codes:** BT=Blackstone Toyota, BC=Blackstone Chevy, ST=Stevens Creek Toyota, SV=Stevens Creek VW, TL=Toyota of Lancaster, AR=Alfa Romeo SJ, VC=VW Clovis.

## Opcode Management Navigation

1. Once on correct dealer, click "OM" (Opcode Management) in the sidebar
2. Page shows "Opcode List" with ~2,000 results

## Searching for Opcodes

**Pitfall**: The opcode search is a React-controlled input. The JS `nativeInputValueSetter` trick does NOT reliably trigger React's state — it sets the field visually but the filter doesn't execute.

### Method that works (confirmed reliable):

1. **Clear previous search**: Click the X/close icon next to the search box (ref varies, look for `icon-close` button)
2. **Type fresh**: Use `browser_type` on the search input (`textbox "Search..."`)
3. **Press Enter**: Use `browser_press Enter` — this triggers the React handler
4. **Verify**: Result count drops from ~2,000+ to "1 Result(s)" (or a small number)

**DO NOT use JS `nativeInputValueSetter` + dispatchEvent** — it sets the visual value but the React component's internal state doesn't update, so the filter never fires. `browser_type` + `browser_press Enter` is the only reliable approach.

If `browser_type` times out, it means the field is in a bad state — click the X/close icon to clear it, then retry.

## Editing an Opcode — Page Layout & Scrolling

Tekion opcode detail pages are extremely long. **The page body is only ~720px** — the actual content lives in a nested scrollable container.

### Finding the Scroll Container

```js
// The main content scroll container is the second .overflow-auto element
document.querySelectorAll('.overflow-auto')[1].scrollTop = N;
```

### Key Scroll Positions (BGFINJ detail page at ST)

| Scroll Position | What's Visible |
|-----------------|----------------|
| 0 | Opcode form fields (Type, Display Value, Description, Eligibility, Category, Job Priority, etc.) |
| ~1200 | **Pay Type Pricing Setup table** — CP row's Labor Rate "Select" dropdown, markup fields |
| ~2500 | **Bottom of page** — Save Draft, Cancel, Update buttons, "Consider for Auto Dispatch" checkbox |

### Scrolling Method

Do NOT use `browser_scroll` — it scrolls the document body, not the `.overflow-auto` container. Always use JS:

```js
document.querySelectorAll('.overflow-auto')[1].scrollTop = 1200;  // pricing table
document.querySelectorAll('.overflow-auto')[1].scrollTop = 2500;  // Save buttons
```

### Labor Rate / Pricing Section

### Pricing Table Row Layout

The pricing table uses React-Table (`.rt-tr-group` rows). When the full DOM is queried, rows follow this structure:

| Index | Content | Meaning |
|-------|---------|---------|
| 0 | Individual Service | Opcode type info |
| 1 | Select Select Select... | Eligibility |
| 2 | Select... Select... | Standard Opcode Mapping |
| 3 | W All Select | Warranty header |
| **4** | **CP All Select** | **Customer Pay header ← target** |
| 5 | I All Select | Internal header |
| 6 | each $ | Parts row |
| 7-8 | Select % | Parts pricing |
| 9 | I % $ $ | Internal pricing values |
| 10 | CP % $ $ | Customer Pay pricing values |
| 11 | W % $ $ | Warranty pricing values |

The "Select" in row 4 is a **React-Select component** (Ant Design). Clicking the dropdown indicator opens options.

### React-Select Portal Limitation (CONFIRMED HARD BLOCKER)

The React-Select dropdown options (e.g., "Fixed Price", "Menu Price", "Hourly Price") render in a **React portal** attached to `document.body`. This portal has been **confirmed across multiple sessions** to be:

- **Invisible to `browser_snapshot`** — not in the accessibility tree
- **Invisible to `browser_vision`** — screenshots show no dropdown even when visually open
- **Invisible to JS DOM queries** — `document.querySelectorAll('*')` returns nothing matching "Fixed Price" even with dropdown open
- **Unclickable via JS** — `.click()` on the dropdown indicator does not open it; React synthetic event handlers don't fire from programmatic clicks

**Verified across 3+ sessions with 20+ attempts.** This is not a timing issue or a wrong selector — the portal simply doesn't render options into the DOM in a way that any automation tool can access.

### Workarounds (in order of preference)

1. **Tekion API approach**: Use `browser_console` to intercept the PUT/POST request when a human clicks Save/Update. The API endpoint likely follows the pattern `/ro/opcode/edit/BGFINJ` or similar. Once captured, replay with `fetch()` using the same `t_token`.

2. **Ask the user**: For a one-off opcode update, it's a 30-second manual task vs hours of automation fighting. Tell the user you hit the React-Select portal wall and ask them to make the change.

3. **Overrides tab** (accessible, but saves don't persist — see Override Save Non-Persistence above): The Overrides tab → Parts sub-tab is reachable after SPA nav (`window.location.href = '/ro/opcode/edit/OPCODE'`, then click Overrides tab, then Parts sub-tab). Existing overrides DO render in the accessibility tree (Make/Model/Year/Trim text visible). But new override additions require manual human save — automation cannot persist them. For one-off overrides like RACF cabin filter part pricing, the user can manually add them. SPA navigation after dealer switch is confirmed: `window.location.href = '/ro/opcode/edit/RACF'` works after clicking the dealer in the popover.

## Override Save Non-Persistence (CONFIRMED HARD BLOCKER)

**Puppeteer and browser tool saves do NOT persist for opcode overrides.** This has been confirmed across multiple sessions (June 2026):

- A Puppeteer script that completes full login, navigation, override form filling, and `page.mouse.click()` on the Save button reports success but **overrides are absent on verification**.
- The browser tool's `dispatchEvent` on Save also fails to persist changes.
- The script ran through 2 of 4 Avalon overrides (vehicle setup + part selection + Save click) without errors, yet zero overrides appeared when re-checking the Parts tab.

**Workaround:** Manual entry by the user (Joe) is the only reliable method for adding/editing opcode overrides. The UI requires genuine human interaction for the Save to commit changes to the backend.

## Session Persistence

- Tekion sessions expire quickly (~30 min of inactivity)
- Session uses **localStorage** not cookies
- Save tokens to `/home/itadmin/.tekion-session.json`
- To restore: navigate to Tekion, inject tokens via `page.evaluate()`, then reload
- Session age > 20 hours = expired, must re-login

## Common Pitfalls

- **Browser session dies**: If Tekion redirects to `/login`, session expired. Full re-login needed.
- **Dealer dropdown not in DOM tree**: The dropdown renders outside the accessibility tree. Use vision + JS.
- **Search doesn't filter**: React synthetic events required. Use `browser_type` + `browser_press Enter`.
- **Page truncation**: Tekion detail pages are massive. Use `browser_console` to find specific elements by text content.
- **Himalaya fails on OTP emails**: OTP emails are HTML-only. Use Python imaplib directly.
