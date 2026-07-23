---
name: jay-skill-pack-sync
description: Maintain the PUBLIC skill-pack repo github.com/joecastelino/jay-skill-pack — the auto-synced, secret-redacted mirror of Jay's entire skill library, README sorted by usage count. Use when Joe asks about the skill pack repo, when a sync fails, when a new secret needs redaction, or when installing Jay's skills into another agent.
triggers:
  - skill pack repo
  - jay-skill-pack
  - publish skills to github
  - skill repo out of date
  - add skills to another agent
  - redact secret from skill pack
---

# Jay Skill Pack — public repo auto-sync

## What it is
- **Repo:** https://github.com/joecastelino/jay-skill-pack (public, owner joecastelino, branch `main`)
- **Local clone:** `/home/itadmin/jay-skill-pack/` (persistent path, survives profile reset)
- **Source of truth:** `/home/itadmin/.hermes/profiles/jay/skills/` (all categories, any dir containing SKILL.md — 157 skills as of 2026-07-23)
- **Sync script:** `/home/itadmin/bin/sync-skill-pack.py` — copies skills, REDACTS secrets, regenerates README.md (table sorted by `times_used` desc from `usage-stats.json`) + `index.json`, commits+pushes ONLY on real diff.
- **Auto-run:** wired into `/home/itadmin/bin/session-end-sync.sh` (every-15-min cron), right after `rebuild-skill-index.sh`. Log: `/home/itadmin/.gbrain/skill-pack-sync.log`. So any skill create/edit OR usage-count bump publishes within ~15 min, no manual step.

## Redaction (CRITICAL — public repo)
- **Literal denylist:** `/home/itadmin/.skill-pack-redact.json` (chmod 600, NEVER commit it). Maps literal secret → placeholder. Currently: Tekion DMS password → `<TEKION_PASSWORD>`, Joe's Gmail app password → `<GMAIL_APP_PASSWORD>`.
- **Generic regexes** in the script: `xox[bap]-…` slack tokens, `ghp_/gho_/…` github tokens, `AKIA…` AWS keys, long `sk-…` API keys.
- **Fail-loud leak check:** after copying, the script greps the repo copy for every denylist literal; if found it ABORTS (exit 2) and does NOT push.
- **WHEN A NEW SECRET ENTERS ANY SKILL** (new password, token, app password): add the literal to `.skill-pack-redact.json` BEFORE the next 15-min sync, or it goes public. If one already leaked: add to denylist, run sync, then **rewrite git history** (`git filter-repo` or force-push a fresh history) AND rotate the secret — deleting in a new commit is not enough.

## Manual ops
```bash
python3 /home/itadmin/bin/sync-skill-pack.py        # force a sync now (prints OK/SYNCED/ABORT)
tail /home/itadmin/.gbrain/skill-pack-sync.log      # recent runs
grep -rl '1969Firebird\|<GMAIL_APP_PASSWORD>' /home/itadmin/jay-skill-pack/skills/  # independent leak check (expect empty)
```
Push auth = `/home/itadmin/.git-credentials` (joecastelino token) via repo-local `credential.helper store --file`.

## Install into another agent
```bash
git clone https://github.com/joecastelino/jay-skill-pack.git
cp -r jay-skill-pack/skills/* ~/.hermes/profiles/<agent>/skills/
```
Then supply real credentials where placeholders appear (`<TEKION_PASSWORD>`, `<GMAIL_APP_PASSWORD>`, `<REDACTED_*>`).

## How the README sorting works
- Usage counts come from `usage-stats.json` (`{skills:{"<category>/<name>":{times_used,last_used}}}`), maintained automatically by session-end-sync's `log-skill-uses-from-session.py` (+1 per skill per distinct session).
- Descriptions come from `manifest.json`; if the manifest holds a bare YAML fold marker (`>` / `|`) instead of text (rebuild-skill-index quirk on folded-scalar frontmatter), the script re-parses the SKILL.md frontmatter itself, joining the indented continuation lines. Fix belongs in the script's `frontmatter_desc()`, not the manifest.
- Ties broken alphabetically by path. `index.json` = machine-readable same data.

## Pitfalls
- `terminal()` with a bare multi-line `TOKEN=$(...)` + curl once hung/BLOCKED; run GitHub API calls via execute_code→terminal with `--max-time` and `-o file -w "%{http_code}"`.
- The script `rm -rf`s and rebuilds `jay-skill-pack/skills/` each run — never hand-edit files under `skills/` in the repo (they'll be overwritten); edit the real skill via skill_manage and let the sync publish it. README/index.json likewise generated.
- Repo-local git identity is set (user.name "Jay (AMG Tekion Agent)", user.email Joe's) — don't rely on global config.
- unsloth reference files trigger false-positive "token=" greps (gitbook image URLs) — harmless, not secrets.
