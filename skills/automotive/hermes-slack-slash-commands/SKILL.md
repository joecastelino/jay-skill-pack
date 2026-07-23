---
name: hermes-slack-slash-commands
description: >
  Diagnose and fix Hermes slash commands on Slack — especially the "/sethome
  failed because the app did not respond" error. The Hermes gateway registers
  exactly ONE Slack slash command (/hermes); every other command (sethome, reset,
  model, new, status, …) must be invoked as a SUBCOMMAND: `/hermes <sub>`. A bare
  `/sethome` is not registered with Slack, so Slack times out. Use when a Slack
  user reports a slash command "doesn't respond", goes to the wrong thread, or
  asks to set the Slack home channel. Also covers the "Sending messages to this
  app has been turned off" DM lockout (App Home Messages Tab disabled) and
  diagnosing any "can't talk to <agent> on Slack" report across fleet profiles.
triggers:
  - sethome failed
  - slack slash command
  - set home slack
  - app did not respond
trigger: /sethome, sethome failed, the app did not respond, slack home channel, set home, slack slash command, /hermes subcommand, slack command not responding, sending messages to this app has been turned off, can't talk to agent on slack, messages tab disabled
---

# Hermes Slack Slash Commands

## The core fact (root cause of most "Slack command broken" reports)

The Hermes gateway's Slack adapter registers **exactly ONE** Slack slash command:

```python
# gateway/platforms/slack.py  (~line 205)
@self._app.command("/hermes")
async def handle_hermes_command(ack, command):
    await ack()
    await self._handle_slash_command(command)
```

Everything else — `sethome`, `reset`, `new`, `model`, `status`, `compress`,
`profile`, etc. — is a **subcommand routed through `/hermes`**, mapped by
`hermes_cli.commands.slack_subcommand_map()`. So:

- ✅ Correct:  `/hermes sethome`   `/hermes reset`   `/hermes model sonnet`
- ❌ Wrong:    `/sethome`   `/reset`   `/model`  → Slack has no handler for these
  registered slash commands, so it shows:
  **"/sethome failed because the app did not respond. Please try again or contact
  the app developer."**

That Slackbot error = Slack itself never reached an app handler (the bare command
isn't registered), NOT a gateway crash. Don't go hunting for a gateway exception
first — check the invocation.

**2026-07-14 confirmed instance:** bare `/restart` → same Slackbot \"failed because
the app did not respond\" error. Correct invocation is `/hermes restart`. AGENT-SIDE
WORKAROUND when the user can't/won't rerun it and a config change needs a gateway
restart (e.g. delegation.model / max_concurrent_children only apply on restart):
self-restart your OWN gateway via a short **delayed** systemd timer so your reply
gets delivered before the bounce, e.g.
`systemd-run --user --on-active=20s systemctl --user restart hermes-gateway-jay.service`.
Never restart synchronously mid-turn — the in-flight reply is lost.

## Fast triage when a user reports a broken Slack command

0. **Was it run inside a THREAD?** Slack blocks ALL slash commands in threads and
   shows "/hermes is not supported in threads. Sorry!" (ephemeral). If the whole
   chat is threaded (common in AMG group channels), the user MUST run it from the
   **main channel message box**, not the thread reply box. Check this FIRST — it
   cost several round-trips in the 2026-06-18 session before being spotted.
1. **Was it invoked as `/hermes <sub>`?** If they typed a bare `/<cmd>`, that's the
   bug. Tell them to use `/hermes <cmd>`. This fixes ~all "did not respond" reports.
2. **Confirm the subcommand exists** in the map:
   ```bash
   cd /home/itadmin/.hermes/hermes-agent
   ./venv/bin/python3.11 -c "from hermes_cli.commands import slack_subcommand_map; import json; print(json.dumps(slack_subcommand_map(), indent=2))"
   ```
   `sethome` and `set-home` are both present and map to `/sethome` / `/set-home`.
3. **Is Slack connected at all?** Check the gateway state:
   ```
   read ~/.hermes/profiles/<agent>/gateway_state.json  → platforms.slack.state == "connected"
   ```
4. **Only if `/hermes <sub>` itself fails** is it a real handler bug — then read
   `gateway/platforms/slack.py:_handle_slash_command` (~line 1513) and the target
   command handler in `gateway/run.py`.

## Setting the Slack home channel (the original task)

"Home channel" = the default destination for proactive/cron deliveries on a
platform. It is **runtime-bound to the exact channel+thread** where `/sethome`
is issued; it is NOT stored in `config.yaml` and NOT in `state.db` (that DB is
just sessions/messages). So you (the agent) **cannot reliably set it by editing a
file** — a Slack group can have many topic threads (e.g. one `C…` channel with
~10 different `thread_id`s in `channel_directory.json`), and a guessed id lands in
the wrong thread.

**The fix the USER runs, in the target Slack channel/thread:**
```
/hermes sethome
```
The gateway captures that live channel context and registers it as the agent's
Slack home. Afterward `send_message(target="slack")` and cron `deliver:"slack"`
land there.

## Reading the logs to confirm the failure mode (2026-06-18)

`tail -40` of `~/.hermes/profiles/<agent>/logs/agent.log` distinguishes the three
"did not respond" causes definitively:

- **Bare `/sethome` → 404 "unhandled request":** a STALE `/sethome` slash command is
  registered in the Slack app config (api.slack.com), but the gateway only handles
  `/hermes`. Log shows literally:
  ```
  WARNING slack_bolt.AsyncApp: Unhandled request ({'type': None, 'command': '/sethome'})
  INFO slack_bolt.AsyncApp: Unsuccessful Bolt execution result (status: 404, body: {"error": "unhandled request"})
  ```
  Slack DID route it; the gateway has no handler. Fix = use `/hermes sethome`, or
  remove the orphaned command from the Slack app config.
- **`/hermes` from main channel but NO inbound log entry at all:** transient
  socket-mode disconnect. Look for nearby `slack_bolt.AsyncApp: The session (...)
  seems to be already closed. Reconnecting...` lines. The request never reached the
  gateway. Fix = just retry once the state is back to `connected`. So "did not
  respond" is NOT always wrong-invocation — a flaky socket is a real third cause.
- **`/hermes <sub>` reaches gateway:** you'll see `gateway.run: inbound message:
  platform=slack ... command=...` — then it's a real handler bug.

GOTCHA on paths: file tools resolve `~` to `…/profiles/jay/home/`, but the live
state files are at `…/profiles/jay/` (no `home/`). Read gateway_state.json /
channel_directory.json / logs/ via their ABSOLUTE `…/profiles/<agent>/` path or
they'll 404.

## Bot SILENT on plain channel messages (not a slash-command issue) — 2026-06-18

Different failure class from slash commands: user types a normal message in a
channel and the bot never replies. Two independent causes, check BOTH:

### Cause 1: mention-gating (BY DESIGN)
`gateway/platforms/slack.py` is **mention-gated in channels** (see its module
docstring ~line 73: "DMs and channel messages (mention-gated in channels)").
Behavior matrix:

| Where the user types            | Bot responds?                          |
|---------------------------------|----------------------------------------|
| DM to the bot                   | ✅ always                              |
| Thread reply under a bot msg    | ✅ always (auto-tracked, `_bot_message_ts`) |
| Top-level channel message       | ❌ ONLY if it @mentions the bot        |
| Channel msg WITH @Bot           | ✅ yes — then ALL later msgs in that thread auto-respond (`_mentioned_threads`, ~line 105) |

So "I can DM/thread it but it ignores me in the main channel" = working as
designed. Fixes: (A) tell the user to @mention once (intended workflow), or
(B) if it's a DEDICATED bot channel, patch the adapter to disable mention-gating
for that channel id (or globally). Option B touches shared gateway code — confirm
with Joe/Walter first per the over-engineering preference.

### Cause 2: user not paired/approved
The gateway only listens to APPROVED Slack user IDs. Lists (per-USER, not
per-channel) live at:
```
~/.hermes/profiles/<agent>/platforms/pairing/slack-approved.json
~/.hermes/profiles/<agent>/platforms/pairing/slack-pending.json
```
Each approved entry: `{"<UID>": {"user_name": "<UID>", "approved_at": <epoch>}}`.
An unpaired user's messages are dropped SILENTLY (no error to them). To add
someone: get their Slack member ID (Slack → profile → ••• More → Copy member ID,
starts with `U`) and append to slack-approved.json.

GOTCHA: entries are bare user IDs, not display names — you cannot tell who is who
from the file. In the 2026-06-18 session two IDs were approved (`U0B7UBQ8Y3T` =
Joe himself, `U0B7UHMTMB3` = Omar) and several round-trips were wasted assuming
"jcastelino" was a missing third user. ASK the user which UID is whom before
concluding someone is unpaired.

## User CANNOT TYPE to the bot at all — "Sending messages to this app has been turned off" (2026-07-14, Jeff)

Third failure class, distinct from silent-bot and slash commands: the DM message box
is DISABLED and Slack shows **"Sending messages to this app has been turned off."**

- This is a **Slack app dashboard config** issue: App Home → Show Tabs → **Messages
  Tab** is off (or "Allow users to send Slash commands and messages from the
  messages tab" is unchecked).
- It is **NOT fixable server-side**: no restart, token swap, or bot/app-token API
  call can change it (App Manifest edits need a `xoxe-` app CONFIG token, which the
  fleet doesn't have). The gateway can be perfectly healthy — Socket Mode connected,
  auth.test ok, bot can even POST outbound DMs to the user — while the user still
  can't type back.
- **Fix (manual, ~30s):** https://api.slack.com/apps/<APP_ID>/app-home → Show Tabs →
  enable Messages Tab + check "Allow users to send Slash commands and messages from
  the messages tab" → user reloads Slack (Ctrl+R). Takes effect immediately, no
  gateway restart.
- Jeff's app id = A0BH9AXT1RU (visible in his SLACK_APP_TOKEN `xapp-1-A0BH9AXT1RU-…`).

FOLLOW-UP (Jeff, same day): after enabling Messages Tab the user could type, but
`/hermes sethome` failed with the AGENT's reply "Unknown command `/hermes`" — Jeff's
Slack app has NO `/hermes` slash command registered at api.slack.com (his app was
created minimally). Slash-command registration is per-app; don't assume every fleet
agent has it. SERVER-SIDE SETHOME FALLBACK (works, verified): `/sethome` just writes
`SLACK_HOME_CHANNEL: <chat_id>` into the profile's config.yaml (see gateway/run.py
`_handle_set_home_command`). So: get the DM channel id via conversations.open with
the bot token (returns `D…` id), write the key into
`/home/itadmin/.hermes/profiles/<profile>/config.yaml` (backup first), restart the
gateway unit. Same trick works for any platform: `<PLATFORM>_HOME_CHANNEL`.

TRIAGE ORDER when "I can't talk to <agent> on Slack": (1) ask/see the EXACT symptom —
if the message box is greyed with that banner, go straight to App Home config and
skip all server-side work; (2) otherwise check systemd unit exists+active, (3)
agent.log for "Socket Mode connected" + "Authenticated as @<bot>", (4) auth.test with
the bot token, (5) send a test DM FROM the bot (conversations.open + chat.postMessage)
to prove outbound. In the 2026-07-14 Jeff case a full token-replace+restart cycle was
spent before the user's error banner revealed the real (config) cause — get the exact
symptom text FIRST.

PROFILE-NAME TRAP: agent display name ≠ profile name. **Jeff runs under profile
`amazon-agent`** (unit `hermes-gateway-amazon-agent.service`); the bare
`~/.hermes/profiles/jeff/` dir is just an orphaned MEMORY.md, no config. Map name→
profile via `gateway_wrapper.sh` journal lines ("profile=amazon-agent agent=jeff") or
grep the profiles' config.yaml/logs, don't assume profile dir = agent name.

### Red herring: session reset window
If the bot went silent for a few minutes around a `Session automatically reset`
banner, messages sent DURING the reset (history-clear + home-channel-set) are
lost. Not a bug — just have them resend after the banner clears.

## Where things live (for deeper debugging)

- Slack adapter:        `gateway/platforms/slack.py`
- Single registered cmd: `@self._app.command("/hermes")` (~line 205)
- Subcommand router:    `_handle_slash_command()` (~line 1513) → `slack_subcommand_map()`
- Subcommand → gateway-command map: `hermes_cli/commands.py :: slack_subcommand_map()`
- Central command registry: `hermes_cli/commands.py :: COMMAND_REGISTRY`
  (CLI, Telegram BotCommands, Slack subcommands, gateway `/help` all derive from it)
- Home/channel directory snapshot: `~/.hermes/profiles/<agent>/channel_directory.json`
- Gateway connection state:        `~/.hermes/profiles/<agent>/gateway_state.json`

## If the user genuinely wants a standalone `/sethome` (no `/hermes` prefix)

That requires registering `/sethome` as its OWN Slack slash command in TWO places:
1. The **Slack app config** at api.slack.com (add the slash command + point its
   Request URL at the same endpoint the gateway serves for `/hermes`).
2. A `@self._app.command("/sethome")` handler in `gateway/platforms/slack.py`
   that calls `_handle_slash_command` with the command normalized.

This touches **shared gateway code used by all AMG agents** — confirm with
Walter/Joe before modifying. Per Joe's "don't over-engineer" preference, prefer
just teaching the `/hermes sethome` invocation unless he explicitly wants the
standalone command.

## Pitfalls

- The Slackbot "did not respond" message is ephemeral ("Only visible to you") and
  comes from Slack, not Hermes — it means Slack found no registered handler within
  its 3s window. First instinct should be "wrong invocation", not "gateway down".
- `set_home` / `set home` (chat text) is the CLI/Telegram style; on Slack it's the
  `/hermes sethome` slash subcommand. Don't conflate them.
- Each agent profile has its OWN gateway_state + channel_directory; check the right
  profile (`~/.hermes/profiles/<agent>/`).
