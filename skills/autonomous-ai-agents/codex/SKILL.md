---
name: codex
description: Delegate coding tasks to OpenAI Codex CLI agent. Use for building features, refactoring, PR reviews, and batch issue fixing. Requires the codex CLI and a git repository.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Coding-Agent, Codex, OpenAI, Code-Review, Refactoring]
    related_skills: [claude-code, hermes-agent]
---

# Codex CLI

Delegate coding tasks to [Codex](https://github.com/openai/codex) via the Hermes terminal. Codex is OpenAI's autonomous coding agent CLI.


## Auth Methods

Codex supports two auth types with different capabilities:

| Method | Command | Model Access | Computer Use | Best For |
|--------|---------|-------------|--------------|----------|
| API key | `echo $KEY \| codex login --with-api-key` | Full API catalog | ✅ Available | Browser automation, all models |
| ChatGPT | `codex login --device-auth` | ChatGPT catalog only | ❌ Not available | Coding tasks, no API credits needed |

### ChatGPT Device Auth

Uses ChatGPT Pro/Plus subscription — no API credits required. But model selection is restricted to the ChatGPT catalog:

```bash
# Check available models
codex debug models | python3 -c "import sys,json; d=json.load(sys.stdin); [print(m['slug']) for m in d['models']]"
```

Typically only `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, and `codex-auto-review` are available. Using `gpt-5`, `gpt-4o`, or `auto` will fail with: `"The 'X' model is not supported when using Codex with a ChatGPT account."`

The device auth flow:
1. Run `codex login --device-auth` (use `background=true` + `pty=true` with long timeout — user needs time to complete)
2. User visits `https://auth.openai.com/codex/device` and enters the one-time code
3. Code expires in 15 minutes
4. Verify with `codex login status` — should show "Logged in using ChatGPT"

Workspace accounts may block device auth — user may need admin to enable it.

### Computer Use

Computer use (browser automation via screenshots) is **API-only + beta-gated** — NOT available through ChatGPT auth.

**Codex CLI**: Does NOT expose computer_use to agents. `--enable computer_use` is accepted but the agent reports "I don't have a browser or computer_use tool." Codex agents only have shell/file/code tools regardless of auth method or flags.

**OpenAI API direct**: The `computer-use-preview` model requires **separate beta program enrollment** from OpenAI. Even with a valid, funded API key:
- `/v1/responses` with `model: "computer-use-preview"` → `404 model_not_found`
- `/v1/chat/completions` with `model: "computer-use-preview"` → `404 model_not_found`
- The model is NOT in the standard model catalog (verified via `/v1/models`)
- Beta headers (`OpenAI-Beta: computer_use=v1`, etc.) do not bypass this

**Empirically verified on 2025-06-09**: sk-proj API key, 118 models in catalog, zero computer-use models. The `truncation=auto` validation error can appear on first try (misleading — suggests model exists) but subsequent calls consistently return 404.

For persistent browser automation, use Playwright/Puppeteer headless scripts. Hermes-native browser tools (`browser_navigate`, `browser_click`) work but sessions blank to `about:blank` every 2-3 turns — suitable for one-off inspection, not batch operations.

## One-Shot Tasks

```
terminal(command="codex exec 'Add dark mode toggle to settings'", workdir="~/project", pty=true)
```

For scratch work (Codex needs a git repo):
```
terminal(command="cd $(mktemp -d) && git init && codex exec 'Build a snake game in Python'", pty=true)
```

## Background Mode (Long Tasks)

```
# Start in background with PTY
terminal(command="codex exec --full-auto 'Refactor the auth module'", workdir="~/project", background=true, pty=true)
# Returns session_id

# Monitor progress
process(action="poll", session_id="<id>")
process(action="log", session_id="<id>")

# Send input if Codex asks a question
process(action="submit", session_id="<id>", data="yes")

# Kill if needed
process(action="kill", session_id="<id>")
```

## Key Flags

| Flag | Effect |
|------|--------|
| `exec "prompt"` | One-shot execution, exits when done |
| `--full-auto` | Sandboxed but auto-approves file changes in workspace |
| `--yolo` | No sandbox, no approvals (fastest, most dangerous) |

## PR Reviews

Clone to a temp directory for safe review:

```
terminal(command="REVIEW=$(mktemp -d) && git clone https://github.com/user/repo.git $REVIEW && cd $REVIEW && gh pr checkout 42 && codex review --base origin/main", pty=true)
```

## Parallel Issue Fixing with Worktrees

```
# Create worktrees
terminal(command="git worktree add -b fix/issue-78 /tmp/issue-78 main", workdir="~/project")
terminal(command="git worktree add -b fix/issue-99 /tmp/issue-99 main", workdir="~/project")

# Launch Codex in each
terminal(command="codex --yolo exec 'Fix issue #78: <description>. Commit when done.'", workdir="/tmp/issue-78", background=true, pty=true)
terminal(command="codex --yolo exec 'Fix issue #99: <description>. Commit when done.'", workdir="/tmp/issue-99", background=true, pty=true)

# Monitor
process(action="list")

# After completion, push and create PRs
terminal(command="cd /tmp/issue-78 && git push -u origin fix/issue-78")
terminal(command="gh pr create --repo user/repo --head fix/issue-78 --title 'fix: ...' --body '...'")

# Cleanup
terminal(command="git worktree remove /tmp/issue-78", workdir="~/project")
```

## Batch PR Reviews

```
# Fetch all PR refs
terminal(command="git fetch origin '+refs/pull/*/head:refs/remotes/origin/pr/*'", workdir="~/project")

# Review multiple PRs in parallel
terminal(command="codex exec 'Review PR #86. git diff origin/main...origin/pr/86'", workdir="~/project", background=true, pty=true)
terminal(command="codex exec 'Review PR #87. git diff origin/main...origin/pr/87'", workdir="~/project", background=true, pty=true)

# Post results
terminal(command="gh pr comment 86 --body '<review>'", workdir="~/project")
```

## Rules

1. **Always use `pty=true`** — Codex is an interactive terminal app and hangs without a PTY
2. **Git repo required** — Codex won't run outside a git directory. Use `mktemp -d && git init` for scratch
3. **Use `exec` for one-shots** — `codex exec "prompt"` runs and exits cleanly
4. **Match model to auth** — ChatGPT auth only supports `gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`. API key auth supports all models.
5. **Device auth needs patience** — run in background with `background=true` and long timeout; user needs 2-5 min to complete browser flow
6. **Debug auth issues** with `codex login status` and `codex doctor`
7. **List available models** with `codex debug models`
8. **Background for long tasks** — use `background=true` and monitor with `process` tool
9. **Parallel is fine** — run multiple Codex processes at once for batch work
