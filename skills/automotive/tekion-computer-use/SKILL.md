---
name: tekion-computer-use
description: >
  Autonomous vision-guided browser automation for Tekion DMS. Uses the persistent
  Playwright browser server (port 9223) as the interaction layer and Claude Sonnet 4
  (via OpenRouter) as the vision/decision-making brain. Claude sees page snapshots,
  decides what to click/type, and the agent executes via HTTP API calls.
trigger: >
  tekion computer use, vision browser, autonomous tekion, tekion cu, browser agent,
  update opcode pricing, navigate tekion, tekion automation
triggers:
  - vision guided tekion automation
  - claude clicks tekion
  - autonomous browser tekion
---

# Tekion Computer-Use Agent

Production vision-guided browser automation for Tekion DMS. Combines a persistent
Playwright browser (port 9223) with Claude Sonnet 4's vision capabilities for
fully autonomous Tekion navigation and form-filling.

## Architecture

```
┌──────────────┐     HTTP API      ┌──────────────────┐
│  agent.py    │ ─────────────────→│  Persistent       │
│  (LLM brain) │ ←─────────────────│  Browser Server   │
│              │   snapshot +      │  (port 9223)      │
│  sends page  │   screenshot      │                   │
│  to Claude   │                   │  Persistent       │
│  Sonnet 4    │                   │  Chromium         │
│  via OpenRtr │                   │  Tekion session   │
└──────────────┘                   └──────────────────┘
```

The agent does NOT use coordinate-based clicking. It uses structured @eN refs
from the snapshot API — 100% reliable element targeting.

## Quick Start

```bash
# 1. Ensure persistent browser is running
curl -s http://localhost:9223/health  # should return {"status":"ok"}

# 2. Run a task
cd ~/tekion-cu
python3 agent.py --task "Navigate to Used Car Recon view and count ROs in Pending Inspection"

# Dry-run (see what it would do without executing)
python3 agent.py --task "Update RACF opcode" --dry-run --verbose
```

## Commands I Use

### Simple inspection tasks
```bash
python3 ~/tekion-cu/agent.py --task "What page am I on? What elements are visible?"
python3 ~/tekion-cu/agent.py --task "Navigate to Repair Order menu" --max-steps 5
```

### Opcode pricing updates
```bash
python3 ~/tekion-cu/agent.py --task "Navigate to Service Menu > Opcode Management, find opcode RACF, and add a vehicle override for 2024 Tacoma with labor $38 and parts $30.88"
```

### Form filling (Ant Design — uses /press Enter, not JS click)
The agent automatically uses `/press` for form submission since React/Ant Design
ignores JS `.click()`. The system prompt instructs Claude to always use Enter
for form submission.

## Session Management

The persistent browser server stores its session in `browser-data/` via
`launchPersistentContext`. To check session health:

```bash
# Check token via eval
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"js":"localStorage.getItem(\"t_token\") ? \"LOGGED_IN\" : \"NO_SESSION\""}' \
  http://localhost:9223/eval
```

If expired, run the login daemon:
```bash
cd ~/tekion-auth && python3 login.py --force
```

Then inject the new session into the persistent browser:
```bash
# The persistent browser needs its own login — it has its own localStorage
# So we navigate to login page and use the agent to log in, or:
# Run the inject script that copies session tokens into the persistent browser
python3 ~/tekion-auth/inject_and_go.py
```

## File Locations

| File | Purpose |
|------|---------|
| `~/tekion-cu/agent.py` | Main agent (622 lines) |
| `~/.tekion-cu/config.json` | API key and model config |
| `~/persistent-browser/server.js` | Browser server (edit here) |
| `~/.hermes/profiles/jay/home/persistent-browser/` | Running copy (sync before restart) |
| `~/tekion-auth/login.py` | Autonomous login daemon |

## Configuration

`~/.tekion-cu/config.json`:
```json
{
  "openrouter_api_key": "sk-or-...",
  "model": "anthropic/claude-sonnet-4"
}
```

Or use environment variables: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`

### Why Claude Sonnet (Joe asked, June 2026 — approved "for now, let's see how it performs")
1. June 4 session finding: Claude meaningfully better than GPT-5.5 at coordinate-precise clicking and recovering from misclicks; GPT-5.5 computer-use crashed in an OTP loop (emitted unrecognized `CMD: OTP` commands).
2. Better at inferring element roles from screenshots when snapshots are ambiguous.
3. More reliable at returning raw JSON-only actions (GPT models tend to wrap in ```json fences → parse failures).
4. Cheaper (~$3/M input vs GPT-4o ~$5/M) for ~2K-token snapshots × many steps.
Swapping models is a one-line change in config.json if Joe wants to revisit.

## Server Start/Stop

```bash
# Kill old
fuser -k 9223/tcp

# Sync code
cp ~/persistent-browser/server.js ~/.hermes/profiles/jay/home/persistent-browser/server.js

# Start (background)
cd ~/.hermes/profiles/jay/home/persistent-browser && xvfb-run -a node server.js &
```

## Supported Actions

The LLM can choose from:
- `click` by @eN ref, visible text, or CSS selector
- `type` into fields by @eN ref
- `press` keyboard keys (Enter, Tab, Escape, ArrowDown, etc.)
- `navigate` to URLs
- `wait` for specified seconds
- `done` / `fail` to end the task

## Pitfalls

- **React/Ant Design** — must use `/press` Enter for form submission, never click
- **SPA timing** — agent auto-waits 2.5s after navigate, 0.5s after click/press
- **networkidle timeout** — server.js was patched to use `domcontentloaded` (60s timeout)
- **Server restart** — loses session; must re-login through the persistent browser
- **Two file locations** — always sync server.js before restart (`cp` to profile path)
- **Tekion redirect** — if loading `/home` redirects to `/login`, session expired
