---
name: tekion-autonomous-login
description: >
  Fully autonomous, headless Tekion DMS login that fetches a fresh OTP and saves
  a reusable session — no human in the loop. Solves the recurring OTP-staleness
  race and the Ant Design verify-click failure. Use as the auth layer in front of
  any Tekion automation (scrapers, opcode updates, computer-use agents).
triggers:
  - tekion login
  - tekion session
  - tekion otp
trigger: Tekion login, Tekion OTP, autonomous login, session token, login.py, tekion-auth, OTP staleness, headless Tekion
---

# Tekion Autonomous Login

The single source of truth for an authenticated Tekion session. Lives at
`/home/itadmin/tekion-auth/login.py`. Run it FIRST in any Tekion workflow; it
either reuses a live session (~0.03s) or does a full headless login (~60s) and
writes the canonical session file.

## Run it

```bash
VPY=/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11
$VPY /home/itadmin/tekion-auth/login.py          # reuse-if-alive, else full login
$VPY /home/itadmin/tekion-auth/login.py --force   # always full login
$VPY /home/itadmin/tekion-auth/login.py --check    # report session status only
```

Exit 0 = session ready (prints `REUSED` or `LOGGED_IN`). Exit 1 = failure.
Canonical session file: `/home/itadmin/caliber-ops/scripts/.tekion-session.json`
(5 keys: t_token, t_user, dse_t_user, currentActiveIsWorkspace, currentActiveWorkspace).

## The four bugs this solved (DO NOT regress)

1. **OTP staleness race** — `fetch_otp.py` grabbed the most-recent OTP email,
   which was often the PREVIOUS code (the old one arrives before the new one).
   FIX: count OTP emails BEFORE submitting Login, then poll until the count
   INCREASES (`wait_for_fresh_otp`). Guarantees a genuinely fresh code.

2. **Login auto-sends an OTP** — clicking "Login" (password screen) already
   triggers a code; the "Resend" button starts DISABLED with a ~40s cooldown.
   So do NOT click Resend first — just baseline-count before Login and wait for
   the auto-sent code. Resend is only a fallback after cooldown elapses.

3. **Ant Design ignores page.fill()** — `page.fill()` sets the DOM value but
   React state stays empty, so Verify acts on an empty field and login silently
   fails. FIX: `elementHandle.click()` then `.type(code, delay=80)` (real
   keystrokes), then `keyboard.press("Tab")` to blur/commit before clicking
   Verify. Same applies to email and password fields.

4. **URL lags the SPA (false negative)** — after a SUCCESSFUL verify, the URL
   can still read `/login?redirectTo=/` for several seconds while the dashboard
   already renders. Checking the URL declares failure on a real success. FIX:
   the success signal is a FRESH (non-expired) `t_token` in localStorage, decoded
   from its JWT `exp` claim — NOT the URL.

## Real login DOM (June 2026)

- Email field: `input#email` (type=**text**, placeholder "Type Here") — NOT type=email
- Next button: text "Next"
- Password field: `input#password` (placeholder "Type Here")
- Login button: text "Login"
- OTP field: `input#otp` (single ant-input, placeholder "Type Here") — NOT split boxes
- Verify button: text "Verify and Proceed"
- Resend button: "Resend in NNs", starts disabled ~40s cooldown

## OTP retrieval

himalaya (IMAP) on account `personal`, folder `[Gmail]/All Mail`, subject
"Tekion-Login OTP", body pattern `Your OTP number is : NNNNNN`. Must set
`HOME=/home/itadmin`. helpers in login.py: `count_otp_emails()`,
`read_latest_otp()`, `wait_for_fresh_otp(baseline, timeout)`.

## Environment

- Python: `/home/itadmin/.hermes/hermes-agent/venv/bin/python3.11` (has playwright 1.60)
- Chromium: Playwright-bundled (`~/.cache/ms-playwright/chromium-1217`) — let
  Playwright pick it, do NOT hardcode the puppeteer chrome path
- Launch args: `--no-sandbox --disable-dev-shm-usage --disable-gpu`, headless=True
- Token lifetime: ~2h10m from issue (JWT `exp`). Probe requires >2min headroom.
- Lock file `/tmp/tekion-session.lock` (fcntl.flock LOCK_EX) prevents concurrent logins.

## Session RESTORE — the storage_state breakthrough (CRITICAL)

Restoring a Tekion session in a SECOND browser is NOT done via localStorage.
This was hard-won by trial and error:

- Injecting the 5 critical localStorage keys → **bounces to /login**.
- Injecting ALL 21 localStorage keys (incl. `t_apmAutnToken`, `persist:primary`,
  `expiryTime`, `currentActiveDealerId`) → **still bounces to /login**.
- **Tekion relies on httpOnly cookies set during login** that JS/localStorage
  cannot see or set. localStorage alone can NEVER restore the session.

**THE FIX:** Use Playwright `storage_state` (captures cookies + localStorage
together). login.py now saves three artifacts after a successful login:
- `.tekion-session.json` — 5 critical keys (legacy, for scrapers that parse it)
- `.tekion-session-full.json` — all 21 localStorage keys
- `.tekion-storage-state.json` — **cookies + localStorage (THE one that restores)**

```python
# save (in login.py, after verify):
ctx.storage_state(path=".../.tekion-storage-state.json")

# restore (in any other Playwright tool):
ctx = browser.new_context(viewport={...},
                          storage_state="/home/itadmin/caliber-ops/scripts/.tekion-storage-state.json")
page = ctx.new_page()
page.goto(BASE + "/home")   # lands authenticated, NO login UI
```

Reference harness: `/home/itadmin/tekion-auth/inject_and_go.py` — restores
storage_state, switches dealer, navigates to an opcode, reads/edits. Use it as
the template for any headless authenticated Tekion action.

## Handoff to other tools

Other automations (scrapers, opcode updaters, computer-use agents) should:
1. Run `login.py` (or just `--check` then `--force` if stale).
2. Create a Playwright context with `storage_state=".tekion-storage-state.json"`
   (NOT localStorage injection — that does not work; see above).
3. Navigate straight into the app — already authenticated, never touch login UI.
4. Switch dealer if needed (default after login is BC). Use the dealer popover +
   a REAL `page.mouse.click()` on the matching leaf element.

## Persistent Browser Server (alternative to login.py)

For interactive/session-persistent workflows where the same browser must survive
across many turns (e.g., Jay teaching Tekion, multi-step opcode workflows), use
the persistent browser server at `~/persistent-browser/server.js` instead of
login.py. This keeps a single Chromium instance alive indefinitely on port 9223.

Key differences from login.py:
- **Session survives across turns** — browser stays open, no re-login needed
- **Headful with Xvfb** — `xvfb-run -a node server.js` on headless Linux
- **HTTP API** — `/navigate`, `/click`, `/type`, `/press`, `/snapshot`, `/screenshot`, `/eval`, `/url`, `/health`
- **@eN ref system** — `/snapshot` injects `data-aria-ref` attributes, then `/click` and `/type` can target `{"ref": "@e5"}`
- **Real keyboard events** — React/Ant Design forms ignore JS `.click()` and `.dispatchEvent()`. The `/press` endpoint uses Playwright's `page.keyboard.press()` which generates native browser events that React processes.

**To authenticate the :9223 context WITHOUT an interactive OTP** (e.g. after a
server restart leaves it on /login), run `login.py` then inject its
`.tekion-storage-state.json` cookies + localStorage via the server's `/cookies`
endpoint and one-at-a-time `/eval` localStorage sets. Full procedure is in the
`persistent-browser-server` skill ("Restoring an authenticated Tekion session").

Server code lives in TWO locations (keep synced):
- `/home/itadmin/persistent-browser/server.js` (Jay's working path)
- `/home/itadmin/.hermes/profiles/jay/home/persistent-browser/server.js` (Codex/profile path)
- Persistence: `launchPersistentContext(userDataDir)` in `browser-data/`
- Start: `cd ~/persistent-browser && xvfb-run -a node server.js`
- Codex build command: `delegate_task(acp_command="codex", acp_args=["--model","gpt-5.5","--skip-git-repo-check","--ephemeral","--sandbox","workspace-write"])`

## Pitfalls

- **ALIVE status ≠ working storage state (hit 2026-07-23):** `tekion-session.py status`
  / `--check` can report ALIVE (valid t_token) while the saved
  `.tekion-storage-state.json` is STALE — injected into :9223 the app renders but
  the DEALER SWITCH silently fails (picker won't flip `currentActiveDealerId`) and
  previously-captured internal-API axios headers 401. A failing dealer switch after
  storage-state injection is the tell: don't debug the picker — run
  `login.py --force` for a full OTP re-login, re-save artifacts, re-inject. Also:
  captured internal-API request headers only live a few days; re-capture after any
  re-login rather than replaying old ones.
- **Missing chromium binary (verified 2026-07-11):** login.py can fail with
  `Executable doesn't exist at /home/itadmin/.cache/ms-playwright/chromium_headless_shell-1223...`
  after a Playwright version bump — the REAL home cache only has older builds (1217)
  while the jay profile home has the new ones. FIX (no download needed):
  ```bash
  ln -sfn /home/itadmin/.hermes/profiles/jay/home/.cache/ms-playwright/chromium_headless_shell-1223 /home/itadmin/.cache/ms-playwright/chromium_headless_shell-1223
  ln -sfn /home/itadmin/.hermes/profiles/jay/home/.cache/ms-playwright/chromium-1223 /home/itadmin/.cache/ms-playwright/chromium-1223
  ```
  Adjust the build number to whatever the error names. Also note login.py prints the
  Playwright banner on failure with exit_code 0 through a pipe — grep for
  `LOGGED_IN|REUSED` AND the Error line, don't trust exit code alone.
- ElementHandle has `.type()`, NOT `.press_sequentially()` (that's a Locator method).
- Default dealer after login is Blackstone Chevrolet (BC), dealerId 1251 context.
- Never `page.reload()` inside the app — resets dealer to BC.
- **React ignores synthetic `element.click()`** for sub-menu/tab navigation inside
  the opcode editor (e.g. switching to the Parts sub-section). Use a real
  `page.mouse.click(x, y)` on the element's bounding-box center instead. When
  finding the element, FILTER OUT off-screen duplicates: require
  `el.offsetParent !== null` AND `rect.x > 0 && rect.x < window.innerWidth`
  (Tekion renders hidden duplicate menu items at negative x like -1382).
- **Claude Code computer-use hangs on first run** until onboarding is pre-approved.
  Symptom: `claude -p` produces no output and never exits. FIX: in `~/.claude.json`
  set `hasCompletedOnboarding=true`, `hasTrustDialogAccepted=true`, and add the
  API key's last-20-chars to `customApiKeyResponses.approved`. The Anthropic API
  key lives in Hermes credential pool: `~/.hermes/auth.json` →
  `credential_pool.anthropic[0].access_token` (export as `ANTHROPIC_API_KEY`).
  `--bare` cold start with cache build takes ~60s (ttft) — keep a warm session
  for repeated calls.
- Background-launching `claude` via the terminal tool: use `background=true` +
  `notify_on_complete=true` (NOT shell `&`/`setsid`/`disown`, which get blocked).
