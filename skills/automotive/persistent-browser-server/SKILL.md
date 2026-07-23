---
name: persistent-browser-server
description: >
  Long-running Playwright browser server (HTTP API on port 9223) that survives
  across Hermes turns. Use for any SPA that needs a persistent session (Tekion,
  admin panels, dashboards). Solves the "browser blanks to about:blank every
  2-3 turns" problem.
triggers:
  - persistent browser
  - browser server port 9223
  - playwright server
trigger: persistent browser, browser session, long-running browser, Playwright server, HTTP browser API, browser persistence
---

# Persistent Browser Server

A Node.js Express + Playwright server that keeps a Chromium browser open
indefinitely. All browser operations go through a simple HTTP API on port 9223.
The browser NEVER closes between requests — perfect for SPA sessions that need
to survive many turns.

## Architecture

```
┌─────────────┐     HTTP API      ┌──────────────────┐
│  Jay/Hermes  │ ───────────────→ │  Playwright       │
│  (execute_   │ ←─────────────── │  Server (Node)    │
│   code)      │   JSON results   │  Port 9223        │
└─────────────┘                   │  Persistent       │
                                  │  Chromium browser │
                                  └──────────────────┘
```

## File Locations (KEEP SYNCED)

The server runs from the profile home because Codex subagents resolve `~` there:
- **Running location:** `/home/itadmin/.hermes/profiles/jay/home/persistent-browser/`
- **Jay's edit location:** `/home/itadmin/persistent-browser/server.js`
- **Copy before restart:** `cp /home/itadmin/persistent-browser/server.js /home/itadmin/.hermes/profiles/jay/home/persistent-browser/server.js`
- **Browser data:** `browser-data/` (cookies, localStorage, session state via Playwright `launchPersistentContext`)

## Start/Stop

```bash
# Kill old server
fuser -k 9223/tcp

# Start (headless Linux — Xvfb required for headful Chromium)
cd /home/itadmin/.hermes/profiles/jay/home/persistent-browser
xvfb-run -a node server.js &

# Or via Hermes background process tool
terminal(command="cd ~/.hermes/profiles/jay/home/persistent-browser && xvfb-run -a node server.js", background=true)

# Health check
curl -s http://localhost:9223/health  # {"status":"ok"}
```

## Full API

| Method | Endpoint | Body | Returns |
|--------|----------|------|---------|
| GET | `/health` | — | `{"status":"ok"}` |
| POST | `/navigate` | `{"url":"https://..."}` | `{"url":"..."}` |
| POST | `/click` | `{"ref":"@e5"}` or `{"text":"Login"}` or `{"selector":".btn"}` | `{"success":true}` |
| POST | `/type` | `{"ref":"@e3","text":"hello"}` or `{"selector":"input","text":"hello"}` | `{"success":true}` |
| POST | `/press` | `{"key":"Enter"}` | `{"success":true,"key":"Enter"}` |
| GET | `/snapshot` | — | `{"snapshot":"@e1 button \"Login\"\n@e2 textbox...", ...}` |
| GET | `/screenshot` | — | `{"screenshot":"base64png"}` |
| POST | `/eval` | `{"js":"document.title"}` | `{"result":"Page Title"}` |
| POST | `/mouse` | `{"x":1239,"y":319}` (opt `clicks`, `button`, `move:true`) | `{"success":true,"x":..,"y":..}` |
| GET | `/url` | — | `{"url":"https://..."}` |
| POST | `/console` | — | `{"messages":[...]}` |

## Python Client Pattern

```python
import urllib.request, json

def api(endpoint, method="GET", body=None, timeout=30):
    url = f"http://localhost:9223{endpoint}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data,
        headers={"Content-Type": "application/json"} if body else {},
        method=method)
    resp = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(resp.read())
```

## The @eN Ref System

`/snapshot` injects `data-aria-ref` attributes into the DOM and returns:

```
@e1 button "Login"
@e2 textbox "Username"
@e3 textbox "Password"
```

Then `/click` and `/type` can target by ref: `{"ref": "@e2"}`. This guarantees
what you see in the snapshot is exactly what gets clicked.

Snapshot walks every visible element, infers ARIA roles, computes accessible
names (aria-label → labelledby → label[for] → text content).

## Critical: `/mouse` — real coordinate click for stubborn React/Ant cells

Some React/Ant Design controls ignore EVERYTHING short of a genuine OS-level
pointer sequence — not `/click` (selector/text/ref), not a JS `.click()`, not even
directly invoking the element's React `onClick` off its fiber props. The verified
case (2026-06-25): Tekion's **Trim Details** cell — a `disabled <input>` wrapped in
a `<div role="button">` — refused to open its modal via any of those. `/click`
returned `{"success":true}` but no modal rendered.

**Fix = the `/mouse` endpoint** (added to server.js 2026-06-25). It does a real
Playwright `page.mouse.move(x,y)` then `page.mouse.click(x,y)` (pointerdown→up→
click). React/Ant honor it.

```python
# 1) read the element's center from /eval, 2) real-pointer click it
coords = api("/eval","POST",{"js":
  "(()=>{const e=document.querySelector('SELECTOR');const r=e.getBoundingClientRect();"
  "return JSON.stringify({cx:Math.round(r.x+r.width/2),cy:Math.round(r.y+r.height/2)});})()"})
c = json.loads(coords["result"])
api("/mouse","POST",{"x":c["cx"],"y":c["cy"]})   # opens the modal/popover
```

Options: `clicks` (e.g. 2 for double-click), `button` ("left"/"right"), `move:true`
(move only, to trigger hover without clicking). The handler in server.js:

```js
app.post('/mouse', async (req, res) => {
  try {
    const p = await getOrCreatePage();
    const { x, y, clicks, button, move } = req.body;
    if (typeof x !== 'number' || typeof y !== 'number')
      return res.status(400).json({ error: 'x and y (numbers) are required' });
    await p.mouse.move(x, y);
    if (move) return res.json({ success: true, x, y, moved: true });
    await p.mouse.click(x, y, { clickCount: clicks || 1, button: button || 'left' });
    res.json({ success: true, x, y });
  } catch (err) { res.status(500).json({ error: err.message }); }
});
```

**Workflow note:** `/mouse` uses ABSOLUTE viewport coords. Read the live
bounding-rect center from `/eval` each time (don't hardcode — layout shifts, and
the negative-x ghost copies will give wrong coords). For a known modal layout you
can hardcode button coords once verified by screenshot (e.g. Trim modal Apply
≈x367,y94; Save ≈x1006,y712 at 1280×720). Prefer selector `/click` when it works;
reach for `/mouse` only for cells that demonstrably ignore it.

## Critical: React/Ant Design Forms

React-controlled inputs (like Tekion's Ant Design forms) **ignore**:
- JS `element.click()` — no React handler fired
- `element.dispatchEvent(new Event('submit'))` — no React handler
- `page.fill()` + click — React state may be empty

**USE `page.keyboard.press('Enter')` via the `/press` endpoint** instead.
Playwright's native keyboard events go through the browser's real event pipeline
and React processes them correctly.

Pattern for form submission:
```python
api("/type", "POST", {"ref": "@e2", "text": "username"})
api("/press", "POST", {"key": "Enter"})  # submits the form
```

## Tech Stack

- **Runtime:** Node.js + Express
- **Browser:** Playwright Chromium with `launchPersistentContext(userDataDir)`
- **Persistence:** Browser context stored in `browser-data/` — cookies + localStorage survive restarts
- **Display:** Xvfb virtual framebuffer for headless Linux
- **Viewport:** 1280×720

## Building with Codex

The server was built by delegating to Codex (gpt-5.5) via Hermes:

```
delegate_task with acp_command="codex", acp_args including gpt-5.5 model
```

Codex handles the full build cycle: scaffold, implement, test, verify.

## ✅ Restoring a Tekion session into :9223 — IT WORKS (corrected 2026-06-27)

**UPDATE 2026-06-27 — the injection method SUCCEEDED end-to-end** (cookies via
`/cookies`, then all 21 localStorage keys via `/eval`, then `/navigate` to a deep
part URL — the SPA stayed authenticated, did NOT bounce to `/login`, and rendered
real part data). The earlier "OFTEN FAILS" warning below was partly a
**self-inflicted bug**, not an inherent Tekion limitation. Read these three
corrections FIRST before trusting the pessimistic section underneath:

1. **`/eval` PARAM IS `js`, NOT `expression`.** Sending `{"expression": ...}` →
   **HTTP 400 Bad Request** (server reads `req.body.js`, returns 400 when missing).
   This 400 is what looked like "injection fails." Use `{"js": "<expr>"}`. The 413
   note below is ALSO suspect — setting all 21 keys one-at-a-time with the correct
   `js` param worked fine; 413 only happens if you cram all keys into ONE payload.

2. **After injection you usually land on the DEFAULT dealer (Blackstone Chevrolet,
   dealerId 1251), NOT your target store.** Switching dealer by setting
   `localStorage.currentActiveDealerId='876'` + navigate **DOES NOT WORK** — the app
   resets it back to 1251 on next paint (dealer context is multi-key + token-bound).
   You MUST switch through the UI: click the dealer pill (top-right, class
   `root_dealerSe...`, ≈x1100,y20) via `/mouse`, wait ~2.5s for the popover, then
   `/mouse`-click the target store leaf (find its live center via `/eval` on
   `innerText==='Stevens Creek Toyota'`, class `root_dealerInfoItem_itemName`,
   filter `offsetParent!==null && x>0`). Verify `localStorage.currentActiveDealerId`
   flipped to 876 afterward.

3. **BARE IN-PAGE `fetch()` TO `/api/...` FAILS AUTH** — returns
   `{"status":500,"message":"Token doesn't exist or is invalid"}` even when the page
   itself is fully authenticated and rendering data. The app's axios instance attaches
   auth headers via an interceptor that a raw `fetch()` does NOT replicate. TWO reliable
   ways to get data instead: (a) **READ THE RENDERED DOM** — most Tekion detail pages
   show the data you need (e.g. the part's **Bin Details** section gives live per-bin
   on-hand: bin 2420 Primary +5, bin 5005 −16, Total −11) — just `/eval`
   `document.body.innerText` and slice the section; (b) **XHR-hook + let the app fire
   its own request** (override `XMLHttpRequest.prototype.open/send`, grab `responseText`
   on 'load', then drive the SPA to refetch) — the app's interceptor adds the headers,
   the hook captures the response. NEVER expect a cold `fetch()` to authenticate.

**BIG-KEY TRAP (verified 2026-07-13):** `t_user` (~64KB) and `dse_t_user` (~60KB) are too big/fragile for shell-quoted curl bodies. POSTing `/eval` with `curl -d '<json escaped inline>'` silently corrupts or drops these two keys — you end up with 19/21 keys set, `currentActiveDealerId` present, but the SPA still renders the LOGIN FORM (welcome:false, loginForm:true). FIX: (a) always write the JSON request body to a temp file and use `curl -d @/tmp/body.json` — never inline shell-quote eval payloads; (b) for the two big keys, accumulate in chunks: `window.__tmp=''` then repeated `window.__tmp += <40KB json chunk>` evals, finally `localStorage.setItem(name, window.__tmp)` and verify `.length` matches the source value length. After those two keys land, `/navigate` to `/home` → "Welcome back" appears.

**login.py location:** `/home/itadmin/tekion-auth/login.py` (NOT in caliber-ops/scripts — only the output file `.tekion-storage-state.json` lives at `/home/itadmin/caliber-ops/scripts/`). A `REUSED`/ALIVE probe result means the storage-state file is fresh enough to inject.

Minimal working restore (verified 2026-06-27):
```python
ss = json.load(open("/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json"))
post("/cookies", {"cookies": ss["cookies"]})                      # 5 cookies
post("/navigate", {"url":"https://app.tekioncloud.com/login"})    # establish origin
for it in ss["origins"][0]["localStorage"]:                       # 21 keys, one at a time
    post("/eval", {"js": f"localStorage.setItem({json.dumps(it['name'])},{json.dumps(it['value'])});'ok'"})
post("/navigate", {"url":".../parts/inventory/part/view/M_TMNA_9008091180/details"})
# → stays authenticated. Then switch dealer via the pill (see correction #2).
```
If `login.py --check` reports a stale token, run `login.py` (no flag) to refresh
the storage-state file first.

---

## ⚠️ (LEGACY pessimistic note — kept for context, but see corrections above)

**HARD-WON FINDING (June 2026):** The cookie + localStorage injection procedure
below was reported as UNRELIABLE for Tekion. In a real session it failed every attempt:
`/cookies` reported `added:5` and localStorage `t_token` was set, but on
`/navigate` to `/home` the SPA route guard bounced to `/login` and **wiped
localStorage** (the `/login` page clears it on mount). Setting localStorage then
doing `window.location.assign('/home')` also fails — same wipe. The httpOnly
`tekion-api-token` cookie alone does NOT authenticate the SPA; it needs cookies
AND localStorage present *atomically at first paint*, which `addCookies` +
runtime `/eval` cannot achieve because the redirect-through-/login destroys it.

**FALSE POSITIVE TRAP:** After injection, the URL may STAY on `/home` (not bounce)
yet the page renders the LOGIN FORM ("Username / Next"). Always verify auth by
checking `document.body.innerText` does NOT contain "Username" / "Welcome back"
DOES appear — not just the URL.

**THE RELIABLE METHOD for any one-shot authenticated Tekion action** (navigate,
read, screenshot, even multi-step within one run) is a HEADLESS Playwright
browser built with `storage_state` — NOT the :9223 server. Template:
`/home/itadmin/tekion-auth/inject_and_go.py`. Pattern:
```python
ctx = browser.new_context(viewport={...},
    storage_state="/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json")
page = ctx.new_page(); page.goto(BASE+"/home", wait_until="domcontentloaded")
# verify: NOT /Username/.test(body.innerText)  → authenticated
```
Each headless subprocess starts at the DEFAULT dealer (Blackstone Chevrolet /
1251), so do the dealer switch inside the SAME run. Run login.py FIRST; if the
saved storage-state is stale server-side (renders login form), `login.py --force`
to get fresh cookies — note `--check` only reports the file's existence/JWT exp,
NOT whether the token is accepted server-side, so a "REUSED/ALIVE" result can
still be a dead session. Only fall back to the :9223 injection below if you
specifically need a session that survives across Hermes turns.

## Restoring an authenticated Tekion session into :9223 (NO OTP re-login) — UNRELIABLE, see warning above

The persistent server uses its OWN `browser-data/` profile, separate from
`login.py`'s storage_state. After a server restart the :9223 context is
**unauthenticated** — navigating to `https://app.tekioncloud.com` bounces to
`/login`. Scrapers that call `:9223/eval` (e.g. `sct_menu_sales_api.py` advisor
resolution) then silently fall back to UUIDs. Fix without an interactive OTP
(NOTE: confirmed to fail for the SPA route guard — see warning above; works only
for pure `:9223/eval` fetch-based advisor resolution where no SPA nav happens):

1. **Add a `/cookies` endpoint** (one-time; httpOnly cookies CANNOT be set via
   `/eval`+localStorage — JS can't see them). Insert after `/health` in
   `server.js`, then sync both file copies and restart:
   ```js
   app.post('/cookies', async (req, res) => {
     try {
       const cookies = req.body.cookies || [];
       await browserContext.addCookies(cookies);
       res.json({ success: true, added: cookies.length });
     } catch (e) { res.status(500).json({ error: String(e) }); }
   });
   ```
2. **Get a fresh session file**: run `login.py` (writes
   `/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json` = cookies +
   localStorage). `--check` output format is non-standard JSON; just run the
   full `login.py` (exit 0 + `LOGGED_IN`/`REUSED`).
3. **Inject cookies** from the storage-state file's `cookies[]` → `POST /cookies`.
4. **Inject localStorage** from `origins[].localStorage[]` for the tekioncloud
   origin. CRITICAL: set keys **ONE AT A TIME** via `/eval` —
   `localStorage.setItem(<json.dumps name>, <json.dumps value>)`. Setting all 21
   keys in a single `/eval` payload → **HTTP 413 Payload Too Large** (express
   default body limit). One-at-a-time stays under the limit.
5. **Navigate** to `https://app.tekioncloud.com/home` and verify:
   `t_token` present AND url stays on `/home` (not `/login`) = authenticated.
   The scraper's fetch JS reads `__user_id`, `currentActiveRoleId`,
   `currentActiveSiteId`, `t_token` from localStorage — confirm all four exist.
6. Re-run the scraper; UUID advisors now resolve to real names.

Health check `exit 7` (curl) = connection refused = server down → restart it.

## Second Tekion instance for subagents = :9225 (built 2026-07-14)

`/home/itadmin/persistent-browser-2/` (port 9225, own browser-data, executablePath patched,
node_modules symlinked to /home/itadmin/persistent-browser/node_modules). Purpose: SUBAGENT
browser lane so delegated Tekion work never fights Jay's :9223 dealer context. Tekion allows
concurrent sessions — same storage-state injects fine into both. Restore auth with the standard
cookie+21-key localStorage injection (chunk keys >30KB via window.__tmp accumulation, verify
length). After injection it lands on default dealer 1251 — subagent must UI-switch dealer itself.
RULE: Jay's own live edits stay on :9223; delegated jobs use :9225 ONLY. One dealer context per
port — never run two subagents on :9225 simultaneously with different target stores.

## FASTEST re-auth for :9225 — clone the LIVE :9223 session (verified 2026-07-21)

When :9225 has dropped to /login but :9223 is still authenticated, skip login.py entirely:
dump :9223's live localStorage and inject it into :9225. No cookies needed — the session
is localStorage-borne and Tekion allows concurrent sessions.

```python
# 1) dump from :9223
ls = eval9223("JSON.stringify(Object.fromEntries(Object.entries(localStorage)))")
d = json.loads(ls)
# 2) SKIP the amplitude_* keys — amplitude_unsent_identify_* is ~5MB and 413s the server;
#    the remaining ~28 keys total ~127KB and inject fine ONE KEY PER /eval call
inject = {k:v for k,v in d.items() if not k.startswith("amplitude")}
post9225("/navigate", {"url":"https://app.tekioncloud.com/login"})   # establish origin
for k,v in inject.items():
    post9225("/eval", {"js": f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});'ok'"})
post9225("/navigate", {"url": target_url})
```

BONUS vs storage-state injection: because `currentActiveDealerId` (+ t_user/dse_t_user)
comes from the live session, :9225 lands on the SAME DEALER :9223 was on — no default-1251
UI dealer-switch dance needed. t_user (~64KB) and dse_t_user (~60KB) injected fine as single
keys via python urllib (the 40KB-chunk trap is a shell-quoted-curl problem, not a size limit).

## Cloning a second instance (verified 2026-07-10, APC portal on :9224)

For a second site needing its own persistent session (e.g. apc.tekioncloud.com, whose
sessions can't be restored from storage_state), clone the server instead of sharing :9223:

```bash
mkdir -p /home/itadmin/persistent-browser-apc/browser-data
cp <profile-home>/persistent-browser/server.js /home/itadmin/persistent-browser-apc/
cd /home/itadmin/persistent-browser-apc
sed -i 's/const PORT = 9223;/const PORT = 9224;/' server.js
sed -i "s|path.join(os.homedir(), 'persistent-browser', 'browser-data')|'/home/itadmin/persistent-browser-apc/browser-data'|" server.js
ln -sfn /home/itadmin/persistent-browser/node_modules node_modules
HOME=/home/itadmin xvfb-run -a node server.js   # background=true
```

**CRITICAL: add `executablePath`** to `launchPersistentContext` options —
`'/home/itadmin/.hermes/profiles/jay/home/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'`.
The stock server.js omits it; on this box the default headless-shell binary is missing, so
`/health` returns ok but every page op returns "Browser context not initialized" with an
EMPTY server log (launch fails silently inside start()).

APC login quirk: the "Login" button ignores text `/click` (returns success, no effect) —
read its bounding rect and `/mouse` the center. OTP boxes: `/mouse` box[0], then `/press`
each digit. Wait for a NEW OTP email by envelope ID (>last seen), not by count.

## Pitfalls

- **tekioncloud.com navs can fail with `net::ERR_FAILED` / `chrome-error://chromewebdata` while other sites load fine (2026-07-16)** — seen after the session dropped to /login: even post `login.py --force` + full cookie/21-key injection (all keys verified), every `/navigate` to app.tekioncloud.com errored, but example.com worked. Site-specific network failure inside that Chromium instance; cause unresolved (likely needs a server restart to clear). Do NOT loop retrying — fall back to a standalone headless Playwright run with `storage_state` (e.g. `/home/itadmin/tekion-reports/refresh_withpart_headers.py` for header recapture). Restart :9223 later when time permits.
- **Pendo tour overlay swallows `/mouse` clicks (Tekion, verified 2026-07-11)** — a
  `_pendo-guide-backdrop_` / `pendo-backdrop-region-*` div can cover the UI; `/mouse`
  returns success but nothing happens. Diagnose with `/eval`
  `document.elementFromPoint(x,y)` (walk parentElement chain — if you see "pendo",
  that's it). Fix: `document.querySelectorAll('[id*="pendo"],[class*="pendo"]').forEach(e=>e.remove())`
  then re-click.
- **Two file locations** — Codex builds in profile home but Jay edits in `/home/itadmin/`; copy before restart
- **Port already in use** — old process from previous session may linger; `fuser -k 9223/tcp` first
- **STALE PROFILE LOCK = "browser context not initialized" (verified 2026-06-26)** — `/health`
  returns `{"status":"ok"}` but `/url` returns `{"error":"Browser context not initialized..."}`,
  and the server log shows: *"The profile appears to be in use by another Chromium process
  (NNNN) on another computer (JoeCLaptop). Chromium has locked the profile..."* → `chrome` exits
  with code 21 and the context never opens. CAUSE: a previous Chromium crashed without releasing
  its singleton lock in `browser-data/`. FIX:
  ```bash
  fuser -k 9223/tcp; sleep 2
  cd /home/itadmin/.hermes/profiles/jay/home/persistent-browser/browser-data
  rm -f SingletonLock SingletonCookie SingletonSocket
  # then restart the server (xvfb-run -a node server.js) and verify /url != error
  ```
  A buffered launch-failure log line can REPLAY as a watch-pattern notification ("9223",
  "unavailable") AFTER you've already restarted a healthy server — verify which PID/session is
  actually live (`/url` works) before chasing the alarm; kill the dead session to stop replays.
- **Xvfb required** — headful Chromium won't start without a display on headless Linux
- **React ignores synthetic events** — always use `/press` for form submission, never JS `.click()`
- **Crash recovery** — if page crashes, server auto-creates new page from persistent context
- **500 errors on click/type** — element not found or ref stale; run `/snapshot` first
- **Restart drops session** — fresh context means re-login; the `browser-data/` dir preserves state
