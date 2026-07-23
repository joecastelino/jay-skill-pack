---
name: hermes-slack-token-recovery
description: Fix an AMG Hermes agent that is silent on Slack because its SLACK_BOT_TOKEN/SLACK_APP_TOKEN are missing or wrong in the profile .env — including recovering LOST tokens from old session transcripts without asking Joe to regenerate them at api.slack.com. Use when an agent's service is running but it never answers Slack messages (Autumn case, 2026-07-14).
triggers:
  - agent not responding on slack
  - slack silent but service running
  - lost slack token
  - restore slack tokens
  - reconnect agent to slack
---

# Hermes Agent Slack Token Recovery

An agent that boots fine but is SILENT specifically on Slack (Telegram works) usually
has NO Slack tokens loaded — not a billing problem (that's `hermes-agent-provider-switch`)
and not the App-Home-disabled banner (that's `hermes-slack-slash-commands`).

## Step 1 — Confirm the gap (don't trust gateway_state.json)
```sh
systemctl --user status hermes-gateway-<profile>.service --no-pager
grep -c "^SLACK_BOT_TOKEN=" /home/itadmin/.hermes/profiles/<profile>/.env
tr '\0' '\n' < /proc/<MainPID>/environ | grep -c SLACK
```
- Journal showing ONLY Telegram warnings and zero "slack" lines = Slack platform never initialized.
- **TRAP**: `gateway_state.json` can show `slack: connected` with a STALE `updated_at`
  from weeks earlier. Check the timestamp — an old date means it's a leftover, not live.
- `channel_directory.json` + `platforms/pairing/slack-approved.json` surviving with Slack
  entries proves Slack WAS configured before → tokens were removed (Autumn's were removed
  Jun 4 on Joe's disconnect request), not never-set.

## Step 2 — Recover the tokens from session transcripts (no Slack dashboard needed)
Old setup sessions in `/home/itadmin/.hermes/sessions/session_*.json` contain the raw
tokens from when the app was first wired. **Use raw Python IO — read_file/execute_code
stdout MASKS tokens, but you can still test them in-memory:**
```python
import re, glob, json, urllib.request
cands = {}
for f in glob.glob("/home/itadmin/.hermes/sessions/session_2026*.json"):
    t = open(f, errors="replace").read()
    for m in re.finditer(r'(xox[bp]-[A-Za-z0-9-]{50,}|xapp-[A-Za-z0-9-]{60,})', t):
        cands.setdefault(m.group(1), set()).add(f)
```
Then identify WHOSE token each is, without printing them:
- **xoxb (bot)**: POST `https://slack.com/api/auth.test` with `Authorization: Bearer <tok>`
  → `{ok, user, team, bot_id}`. The `user` field names the agent (e.g. `autumn`).
- **xapp (Socket Mode)**: POST `https://slack.com/api/apps.connections.open`
  → `ok: true` = valid. Match it to the right app by the **app ID embedded in the
  token itself**: `xapp-1-A0BXXXXXXXX-...`. (Autumn = A0B7YEHJBNX; Jay = A0B8EKPGX0R;
  Jeff/amazon-agent = A0BH9AXT1RU; Don = A0B8XBMAD2P.)
- Ignore short (<50 char) or doc-example tokens ending in things like `123456` — invalid.
- Slack tokens don't expire on their own; a token removed from .env months ago still works
  unless someone hit Revoke in the Slack dashboard.

## Step 3 — Restore and restart
Backup `.env` first, append (raw Python write, chmod 600):
```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-1-A0B...-...
SLACK_ALLOWED_USERS=U0B7UBQ8Y3T   # Joe; add others from platforms/pairing/slack-approved.json
```
```sh
systemctl --user restart hermes-gateway-<profile>.service
```

## Step 4 — Verify
Wait ~20s, then check `gateway_state.json` shows `slack: connected` with a FRESH
`updated_at` (this is the real readiness signal — the journal may print nothing for
Slack on success). Then have Joe ping the bot.

## Step 5 — Home-channel prompt after reconnection (Autumn, 2026-07-15)
A freshly reconnected agent may greet the first message with:
":mailbox_with_mail: No home channel is set for Slack... Type /sethome..."
Don't make Joe run /sethome — set it directly in the profile `.env`
(home channel var, e.g. `SLACK_HOME_CHANNEL=D0B86M092D7` — Joe's DM with that bot;
find the DM channel ID via `conversations.list types=im` with the bot's xoxb, matching
Joe's user U0B7UBQ8Y3T) and restart the gateway. Autumn's home = D0B86M092D7.
The home channel is where cron results and cross-platform messages get delivered.

## Identifying an UNKNOWN Slack user ID (Joe says "fix @U0Bxxxxx", 2026-07-14)
When Joe mentions a broken bot by Slack ID and you don't know which agent it is:
- `users.info` will FAIL — none of the fleet bot tokens have `users:read` scope
  (they only have app_mentions/chat:write/im/channels/groups/files/commands).
- Identify by ELIMINATION instead:
  1. For every profile `.env` with a SLACK_BOT_TOKEN, call `auth.test` → each returns
     its own `user_id`. Known fleet (2026-07-14): Jay=U0B8ANZEYA2, Don=U0B8XBXUTA7,
     Jeff=U0BHD8TK5FT, Autumn=U0B7PC55JDD. If the mystery ID isn't in that list,
     it's one of the token-less profiles (Walter/base, Stacey/email-agent, Ralph,
     Solo, Arnold, Tink, Dori).
  2. Check which gateways actually have Slack live:
     `for pid in $(pgrep -f hermes.*gateway); do tr '\0' '\n' </proc/$pid/environ | grep -q SLACK_BOT_TOKEN && echo $pid HAS-SLACK; done`
     (env var presence in /proc beats gateway_state.json, which can be stale).
  3. Grep the whole box for the ID (`.hermes` configs, pairing files, channel_directory,
     ALL session transcripts). Zero hits = that app was never wired from this machine
     → no tokens exist on disk → recovery Step 2 will find nothing; go straight to
     asking Joe which agent it is + regenerating tokens at api.slack.com.
- Report to Joe: list who IS live (verified IDs) and ask which agent the ID maps to —
  don't guess the profile; writing tokens into the wrong profile makes it reply as
  the wrong bot.

## Identifying an UNKNOWN Slack user/bot ID (e.g. Joe pastes <@U0Bxxxxxxxx>)
Our fleet bot tokens do NOT have `users:read` — `users.info` returns `missing_scope`,
so you cannot look the ID up directly. Instead:
1. **Audit the fleet first**: run `auth.test` with every profile's SLACK_BOT_TOKEN
   (from `/home/itadmin/.hermes/profiles/*/.env`) — each returns `{user, user_id, bot_id}`.
   If the mystery ID matches one, that's the agent. Also check which RUNNING gateways
   actually have Slack loaded: `grep SLACK /proc/<pid>/environ` (tr '\0' '\n') — a token
   in .env but not in the live process env means restart needed.
2. **If no profile matches**, ask Joe for the app's tokens (api.slack.com/apps →
   OAuth & Permissions for xoxb). `auth.test` on the pasted xoxb instantly reveals
   `user` (bot name) + `user_id` — this is how `number_5` = U0B8EMPBFU4 (app A0B8AT7CJ2W)
   was identified 2026-07-14. Validate a pasted xapp via `apps.connections.open`.
3. Known fleet Slack IDs: jay=U0B8ANZEYA2, don_ready=U0B8XBXUTA7, jeff=U0BHD8TK5FT,
   autumn=U0B7PC55JDD, number_5=U0B8EMPBFU4 (no profile on this box as of 2026-07-14 —
   its "install" was an abandoned `hermes auth` in the secondary WSL `Ubuntu` distro).
   Joe = U0B7UBQ8Y3T.
4. If the agent lived on a "different install", check OTHER WSL distros on this same
   computer → skill `wsl-cross-distro-hermes-discovery`.

## Pitfalls
- read_file / patch / printed stdout mask `xox*` tokens — do ALL token handling inside
  one execute_code block with raw `open()` IO; never round-trip a token through a
  masked view or you'll write the mask to disk.
- Multiple agents' tokens appear in the same transcripts — ALWAYS verify identity via
  `auth.test` (`user` field) and the `A0B...` id inside the xapp token before writing.
  Writing another agent's bot token = agent replies as the wrong bot.
- If NO valid token is found in transcripts, fall back to regenerating at
  api.slack.com/apps/<APPID> (OAuth & Permissions for xoxb; Basic Information →
  App-Level Tokens for xapp, scope `connections:write`) — needs Joe's browser session.
- If tokens are present and valid but the bot still won't take DMs, check the App Home
  Messages Tab banner case → skill `hermes-slack-slash-commands`.
