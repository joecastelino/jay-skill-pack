---
name: hermes-slack-approval-config
description: Configure who can approve Hermes dangerous command requests in Slack — add/remove approvers, set SLACK_ALLOWED_USERS, and understand how approval routing works.
triggers:
  - hermes slack approval
  - slack approval permissions
  - command approval slack
  - approve button slack
  - SLACK_ALLOWED_USERS
  - who can approve hermes
  - add approver slack
---

# Hermes Slack Approval Configuration

## How It Works

When Jay (or any Hermes agent) triggers a dangerous command (piping to `python3`, `rm -rf`, etc.),
the gateway sends an approval request to the **same chat/channel where the agent was invoked**.
On Slack, this appears as a Block Kit message with buttons: Allow Once, Allow Session, Always Allow, Deny.

**Who can click:** Controlled by `SLACK_ALLOWED_USERS` env var (comma-separated Slack user IDs).
- **Not set (empty):** ANYONE in the channel can click the buttons.
- **Set to `*`:** Anyone can click.
- **Set to specific IDs:** Only those users can click; others' clicks are silently ignored.

This gate is in `gateway/platforms/slack.py`, method `_handle_approval_action` (~line 1339).

## Configuration

The env var must be set in the gateway's environment. On AMG's systemd setup:

```bash
# Check current setting
grep -r 'SLACK_ALLOWED_USERS' /home/itadmin/.hermes/.env /home/itadmin/.config/systemd/user/ 2>/dev/null

# If not set, add to /home/itadmin/.hermes/.env (base gateway reads from env.conf → .env):
SLACK_ALLOWED_USERS=U0B7UHMTMB3,UXXXXXXXX  # Joe + Omar's Slack IDs
```

Then restart: `systemctl --user restart hermes-gateway-jay`

The code reference (for debugging):
```python
# gateway/platforms/slack.py line 1339
allowed_csv = os.getenv("SLACK_ALLOWED_USERS", "").strip()
if allowed_csv:
    allowed_ids = {uid.strip() for uid in allowed_csv.split(",") if uid.strip()}
    if "*" not in allowed_ids and user_id not in allowed_ids:
        # REJECT — silently ignores the click
        return
```

## Finding Slack User IDs

Slack user IDs start with `U` (e.g., `U0B7UHMTMB3` for Joe). Find them:
- From a Slack message: click the user's profile → "Copy member ID"
- From the Slack API: `users.list` or `users.lookupByEmail`

## Routing

Approval messages go to `_status_chat_id` — the chat where the agent session was invoked.
They do NOT go to a separate "admin" channel. So the approver must be in the relevant channel/thread
to see the approval buttons (or the messages must go to a shared channel).

## Pitfalls

- If `SLACK_ALLOWED_USERS` is set but empty after stripping, the guard is **bypassed** and anyone can approve.
- There is no separate "approval channel" — messages route to the invoking chat.
- The `.env` file is sourced by the base gateway (`hermes-gateway.service`) via `env.conf` → `EnvironmentFile`.
  Profile-specific drop-ins may also need the var if the base gateway delegates to profile gateways.
- After changing the env var, the gateway must be restarted for it to take effect.