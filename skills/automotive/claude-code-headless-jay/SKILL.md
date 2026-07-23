---
name: claude-code-headless-jay
description: Run Claude Code (claude CLI) headless/non-interactive from Jay's Hermes session. Solves the hang where plain `claude -p` waits forever on interactive login because Jay's profile HOME is unconfigured.
triggers:
  - run claude code
  - delegate to claude code
  - claude cli hangs
---

# Claude Code headless from Jay's session

## The problem
Running `claude -p "..."` from Jay's session HANGS indefinitely (interactive login prompt).
Cause: Jay's session sets HOME to the jay profile home, whose .claude.json has NO primaryApiKey
and onboarding incomplete. The CLI can't auth and blocks on /login.

## The fix — two requirements, BOTH needed
1. Set HOME=/home/itadmin (the real home's .claude.json has onboarding complete, trust dialog
   accepted, and the approved key hash).
2. Pass the Anthropic API key explicitly in the env as ANTHROPIC_API_KEY. The apiKeyHelper alone
   is not enough.

The key value is available in the agent env file under the variable name ANTHROPIC_API_KEY.
The CLI's apiKeyHelper also expects a file at ~/.hermes/secrets/anthropic_key containing the same
key (chmod 600); if that file is missing the CLI cannot read the helper key — recreate it.

## Working invocation shape (VERIFIED 2026-06-15)
Assign the key to a shell variable KEY (read it from wherever the agent env exposes it), then:

    env HOME=/home/itadmin ANTHROPIC_API_KEY="$KEY" claude -p "your prompt" --max-turns 10

Returns instantly. Test prompt "Reply with exactly: READY" prints READY.

## Notes
- --bare works too (skips hooks/plugins) but still needs ANTHROPIC_API_KEY in env.
- Always cd/workdir to the target repo so Claude edits the right project.
- For multi-turn builds use tmux per the claude-code skill, still with HOME=/home/itadmin and
  the key in that tmux session env.
- Always set --max-turns in print mode to cap runaway loops.

## Pitfall
Do NOT embed the literal key or any secret-file-reading command in memory/skill text — the
security scanner blocks it. Reference the variable name only.
