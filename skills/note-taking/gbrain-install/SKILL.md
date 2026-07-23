---
name: gbrain-install
description: Install & configure GBrain (Garry Tan's knowledge brain) — PGLite, ZeroEntropy embeddings, brain directory, recurring jobs. Use when setting up gbrain from scratch or recovering from a broken install.
triggers:
  - install gbrain
  - repair gbrain
  - brain setup
---

# GBrain Install & Configuration

## Prerequisites
- Bun (`~/.bun/bin/bun`)
- ZeroEntropy API key (preferred) or OpenAI key
- ~/brain/ directory (MECE structure)

## Install

```bash
cd ~/gbrain
git pull origin main
~/.bun/bin/bun install
export PATH="$HOME/.bun/bin:$PATH"
```

## The init hang problem

`gbrain init` hangs during PGLite WASM initialization when run via `bash -c`. The init function calls `createEngine()` which spawns a worker thread that never resolves in certain shell contexts.

### Fix: Manual init

Skip `gbrain init` entirely — create config and apply migrations directly:

```bash
# 1. Create config manually
mkdir -p ~/.gbrain
cat > ~/.gbrain/config.json << 'EOF'
{
  "embeddingProvider": "zeroentropy",
  "embeddingModel": "zembed-1",
  "brainDir": "/home/itadmin/brain",
  "dbPath": "/home/itadmin/.gbrain/brain.pglite"
}
EOF

# 2. Save API key
echo "ZEROENTROPY_API_KEY=ze_..." > ~/.gbrain/.env

# 3. Apply migrations directly
cd ~/gbrain
~/.bun/bin/bun -e "
const { initPGlite, applyMigrations } = require('./src/db');
const db = await initPGlite('/home/itadmin/.gbrain/brain.pglite');
await applyMigrations(db);
console.log('Done');
"
```

## Verify

```bash
export PATH="$HOME/.bun/bin:$PATH"
gbrain stats          # page/embed/link counts
gbrain query "test"   # should return results
```

## Recurring jobs

```bash
# Dream cycle (3 AM nightly — memory consolidation)
gbrain dream --schedule daily --at 03:00

# Brain sync (every 15 min — re-import changed markdown)
gbrain sync --watch --interval 900
```

## Dream cycle wiring (learned 2026-06-12, doctor 70→95)

A "successful" dream run can still be half-broken — read the phase list, not the exit code.

1. **Cron prompts must NOT export API keys inline** — the Tirith security scanner
   blocks the command waiting for approval nobody will give at 3 AM. Use:
   ```bash
   set -a; source ~/.gbrain/.env; set +a
   ```
2. **Pass `--dir ~/brain`** — without it, lint/backlinks/sync/synthesize silently
   skip ("no on-disk checkout") because the brain is PGLite-only.
3. **`~/brain` must be a git repo** — the sync phase hard-fails with
   "Not a git repository". `git init && git add -A && git commit` once; have the
   sync cron commit changes each run.
   - **Set a local git identity** or commits fail with "empty ident name not
     allowed" (seen 2026-06-12 on JoeCLaptop): `cd ~/brain && git config
     user.email "gbrain-sync@localhost" && git config user.name "GBrain Sync"`.
     This is silent until a sync actually produces changes, then breaks the
     commit and the dream git-sync phase.
4. **Orphan check**: create an `index.md` hub page wikilinking every page, then
   materialize edges with `gbrain link index <slug> --link-type references`.
   `check-backlinks fix` alone does NOT clear orphans (markdown links ≠ DB edges).
5. **Frontmatter required** on every page or lint flags it (title/type/tags/created).

## Resolver health (doctor `resolver_health` FAIL)

gbrain audits the Hermes skills dir (`~/.hermes/profiles/<agent>/skills/`). To pass:

- **RESOLVER.md** at skills root: markdown tables where the skill column is a
  backtick-wrapped path **starting with `skills/`**, e.g.
  `` | tekion login | `skills/automotive/tekion-autonomous-login/SKILL.md` | ``
- **manifest.json** at skills root: `{"skills": [{"name": ..., "path": ...}]}` where
  **name must equal the path slug** (e.g. `automotive/tekion-opcode-api`), not the
  frontmatter name — otherwise every entry warns "not in manifest".
- **`triggers:` in each SKILL.md frontmatter as a block-style YAML list.**
  Inline `triggers: [a, b]` is NOT parsed (regex only matches `  - item` lines):
  ```yaml
  triggers:
    - tekion login
    - tekion session
  ```
- Verify with `gbrain check-resolvable --json` (slow ~60s; redirect to a file,
  it also prints non-JSON progress lines before the JSON — strip with regex).

## Running the dream cycle correctly (learned 2026-06-12)

```bash
export PATH="$HOME/.bun/bin:$PATH"
set -a; source ~/.gbrain/.env; set +a   # NEVER export keys inline — trips Tirith security scanner in cron (approval hang)
gbrain dream --dir ~/brain               # --dir is REQUIRED or lint/backlinks/sync/synthesize phases skip silently
```

Requirements for a fully-green dream cycle:
1. **~/brain must be a git repo** — the sync phase hard-fails with "Not a git repository" otherwise. `cd ~/brain && git init && git add -A && git commit -m init`
2. **Every page needs YAML frontmatter** (title/type/tags) or lint flags `no-frontmatter`
3. **Orphan check**: create an `index.md` hub page, then materialize edges with `gbrain link index <slug> --link-type references` for every page. `gbrain extract links` does NOT create edges from wikilinks reliably; explicit `gbrain link` does. Verify with `gbrain orphans --count` (should be ≤1, the index itself).
4. Cron jobs that touch ~/brain should `git add -A && git commit` afterward so the next dream sync stays clean.

## Resolver health (doctor `resolver_health` FAIL → fix)

Doctor scores skills via `gbrain check-resolvable`. Three pieces must agree, all under the skills dir (e.g. `~/.hermes/profiles/jay/skills/`):

1. **RESOLVER.md** — markdown table rows where the skill column is a **backtick-wrapped path starting with `skills/`**: `| trigger phrase | \`skills/category/name/SKILL.md\` |`. Plain paths or paths without the `skills/` prefix are NOT parsed.
2. **manifest.json** — `{"skills": [{"name": ..., "path": ...}]}` where **name must equal the full path slug** (`category/name`, i.e. path minus `/SKILL.md`), not just the dirname. Mismatch → "trigger not in manifest" warnings. If manifest.json is absent gbrain auto-derives it (warn only).
3. **SKILL.md frontmatter `triggers:`** — must be a **block-style YAML list**. Inline `triggers: [a, b]` is silently ignored (parser regex only matches `\n  - item` lines):
   ```yaml
   triggers:
     - trigger phrase one
     - trigger phrase two
   ```

Verify: `gbrain check-resolvable --json` → want `reachable == total, gaps == 0`. Pipe to a file first — the command can take >60s and mixes log lines with JSON (`re.search(r'\{.*\}', raw, re.S)` to extract). Same for `gbrain doctor --json`.

## The nightly refresh dies silently — HOME mismatch / missing .env / `set -e` (diagnosed 2026-06-23)

Symptom: GBrain *looks* alive (audit dir has recent files, `gbrain stats` shows pages) but the
brain has been **frozen for weeks** — no new pages ingested, `dream.log` 0 bytes and stale, and
`~/.gbrain/brain-refresh.log` **does not exist at all**. The 3 AM cron refresh has been dying on
its first line every night and nobody noticed because nothing logged.

### Root cause: there are TWO `$HOME`s and TWO `.gbrain` dirs
On this fleet, the agent's interactive session has `HOME=/home/itadmin/.hermes/profiles/<agent>/home`,
but **cron runs as the OS user `itadmin` with `HOME=/home/itadmin`**. So:
- `~/.gbrain` resolves DIFFERENTLY in your session vs. under cron. **Both dirs exist.**
- `brain-refresh.sh` did `set -euo pipefail` then `source "$HOME/.gbrain/.env"`. Under cron that's
  `/home/itadmin/.gbrain/.env` — which was **MISSING** (only the profile-home copy existed). With
  `set -e`, the script exited immediately, never reaching the gbrain commands OR the log writes.
- The two `config.json` files can also disagree: the profile-home one had the embedding model set,
  but `/home/itadmin/.gbrain/config.json` had **`embedding_disabled: true`** → even if it ran, no
  embeddings. They DO share one DB (`database_path: /home/itadmin/.gbrain/brain.pglite`).
- The crontab line had **no `>> log 2>&1` redirect** (unlike every sibling job), so the failure was
  invisible. `getent passwd itadmin | cut -d: -f6` confirms cron's HOME = `/home/itadmin`.

### Diagnose (fast checklist)
```bash
ls -la /home/itadmin/.gbrain/.env            # MISSING here = the killer (cron HOME)
ls -la /home/itadmin/.gbrain/brain-refresh.log   # absent = script never reached log writes
ls -la /home/itadmin/.gbrain/dream.log       # 0 bytes + stale mtime = dream hasn't run
cat /home/itadmin/.gbrain/config.json | grep -i embedding   # embedding_disabled:true = bad
crontab -l | grep brain-refresh              # check for a `>> ...log 2>&1` redirect
```

### Fix
1. **Harden the script** so it can't die on a missing `.env` and isn't HOME-fragile — loop over
   candidate `.env` paths, drop `set -e` around the source, hardcode the brain dir, force the log path:
   ```bash
   set -uo pipefail                      # NOT -e (a missing .env must not kill the run)
   export PATH="$HOME/.bun/bin:/home/itadmin/.bun/bin:$PATH"
   for ENVF in "$HOME/.gbrain/.env" "/home/itadmin/.gbrain/.env" \
               "/home/itadmin/.hermes/profiles/<agent>/home/.gbrain/.env"; do
     [ -f "$ENVF" ] && { set -a; source "$ENVF"; set +a; break; }
   done
   BRAIN_DIR="/home/itadmin/brain"; LOG="/home/itadmin/.gbrain/brain-refresh.log"; mkdir -p "$(dirname "$LOG")"
   # ... git commit, then: gbrain sync --repo "$BRAIN_DIR" --no-pull / extract --stale / dream --yes
   ```
   (Note: this version uses `gbrain sync --repo ... --no-pull` + `extract --stale` + `dream --yes` —
   the installed CLI's flags; older `--dir`/`--schedule` examples above are from an earlier gbrain.)
2. **Create the missing cron-HOME .env + align its config** (copy the working profile-home ones):
   ```bash
   cp ~/.gbrain/.env /home/itadmin/.gbrain/.env && chmod 600 /home/itadmin/.gbrain/.env
   cp ~/.gbrain/config.json /home/itadmin/.gbrain/config.json   # ensures embeddings enabled
   ```
3. **Add the missing log redirect** to the crontab line so future failures are visible. Edit the
   crontab the SAFE way (NEVER `crontab -l | sed | crontab -` — a sed error empties it): read it,
   patch line-by-line in python, `crontab /tmp/newcron`, back up first.
4. **Verify exactly as cron will** (this is the only test that matters — it reproduces the HOME):
   ```bash
   HOME=/home/itadmin /home/itadmin/bin/brain-refresh.sh ; echo EXIT=$?
   tail -40 /home/itadmin/.gbrain/brain-refresh.log        # want the 22-phase cycle + "Brain is healthy"
   HOME=/home/itadmin gbrain stats                         # page/chunk/embedded counts should climb
   HOME=/home/itadmin gbrain search "some new page topic"  # the new page must surface
   ```
   A successful run logs `[cycle.*] start/done` for ~22 phases, `Embedded N chunks`, and
   `Brain is healthy. N phase(s) checked`. `Embedded 0 chunks` right after a sync is normal (the sync
   step already embedded them). Confirm the new concept page committed to git (the script auto-commits).

**Takeaway:** when an agent's nightly job "should already be working" but the brain is stale, assume
the **cron HOME ≠ session HOME** and check for a missing `.env`/log under `/home/itadmin/` FIRST,
before touching gbrain itself. The audit dir and `gbrain stats` looking healthy is a red herring —
they reflect manual/session runs, not the dead cron.

## Sync cron: commit MUST target /home/itadmin/brain, not session ~/brain (confirmed 2026-06-24)

The brain-sync cron prompt runs `cd ~/brain` then `git add -A && git commit`. But in an
agent session `~/brain` resolves to `/home/itadmin/.hermes/profiles/<agent>/home/brain`
— a STALE checkout — while the **canonical repo the cron + dream cycle use is
`/home/itadmin/brain`** (holds the real pages + up-to-date commit history). Both share
ONE DB at `/home/itadmin/.gbrain/brain.pglite`.

Consequence: `gbrain import/embed/link/orphans` hit the right DB regardless of cwd (DB is
shared), so those steps "just work" — but **file edits to index.md and `git commit` land
in the wrong directory** if you trust `~/brain`. First commit attempt 2026-06-24 said
"nothing to commit" because the edit went to /home/itadmin/brain (correct via `patch` abs
path) but the commit ran in session-HOME ~/brain (clean). Fix: always hardcode
`BRAIN=/home/itadmin/brain; cd "$BRAIN"` for the commit, and edit
`/home/itadmin/brain/index.md` by absolute path.

Also: a page can be wikilinked in index.md yet STILL be an orphan — markdown wikilinks ≠
DB edges. `gbrain orphans` counts DB edges. `gbrain link index <slug> --link-type
references --link-source sync` materializes the edge. **The `<slug>` MUST be the
path-qualified slug** (e.g. `projects/session-20260625_104417_5458b2`), NOT the bare
filename slug — passing the bare slug fails with `addLink failed: page "index" or
"<slug>" not found` even though `gbrain get` resolves the bare form. Confirmed 2026-06-25.
(Saw tekion-parts-replenishment:
already `[[wikilinked]]` in index.md but orphaned until explicit `gbrain link`.) The lone
remaining orphan after linking everything is `index` itself — that's expected/fine.

## `gbrain import` can silently skip a git-committed page — use `sync --repo` to catch it (2026-06-25)

The brain-sync cron uses `gbrain import ~/brain/ --no-embed`. `import` uses **mtime/content-hash
dedup** and can SKIP a page that is already committed to git but absent from the DB (its mtime
predates the DB's last-seen, so import calls it "unchanged"). Symptom: `import` reports e.g.
"2 pages imported" but a brand-new session page is **not** in `gbrain list` / `gbrain get <slug>`
returns `page_not_found`, and `gbrain link index <slug>` fails with
`addLink failed: page "<slug>" (source=default) not found`.

**Fix:** run the git-diff-based importer instead — it walks the commit range, not mtimes:
```bash
gbrain sync --repo /home/itadmin/brain --no-pull   # ingests + embeds anything in new commits
```
This caught & embedded `session-20260625_104417_5458b2` after plain `import` had missed it
("1 chunks created, 1 pages embedded"). After it lands you can `gbrain link index <slug> ...`.
Consider preferring `gbrain sync --repo` over `gbrain import` in the sync cron for this reason.

**Two misleading clues that confirm this is the import-vs-link gap (re-confirmed 2026-06-25, gbrain 0.42.37):**
1. `gbrain get <path-slug>` and `gbrain list -n 300` BOTH resolve/show the page fine
   (path-qualified slug, e.g. `projects/session-...`) — yet `gbrain link index <slug>` still
   fails. **`get` succeeding is NOT proof `link` will work.** Only `sync --repo` registers the
   page in the partition `link` reads.
2. The link error reads `addLink failed: page "index" (source=default) or "<slug>"
   (source=default) not found` — it names `index` too, which is a red herring (index IS present;
   `gbrain get index` works). The real problem is `<slug>` isn't under `source=default` until
   `sync --repo` ingests it. Don't chase the `index`/`source=default` wording; just run
   `gbrain sync --repo /home/itadmin/brain --no-pull` and re-link.
3. `gbrain import` after the link fix reports the new pages as "skipped (unchanged)" — it will
   NOT re-register them; `sync --repo` (git-diff based) is the only thing that does. The diff line
   `Synced <old>..<new>: +N added` confirms it actually ingested the new commits.

Note: `gbrain import <single-file.md>` finds **0 files** — import only takes a DIRECTORY. To
re-ingest one page, either re-run `import <dir>` or use `gbrain sync --repo`. Also: `gbrain list`
defaults to ~50 rows; use `gbrain list -n 200` or `gbrain get <slug>` to confirm a specific page.

## Adding a concept page + keeping it searchable (the routine after a good diagnosis)
When you finish a hard diagnosis worth remembering, capture the *concept* (the why) as a brain page,
distinct from the *skill* (the how). Steps:
1. Write `/home/itadmin/brain/concepts/<slug>.md` with frontmatter `title/type: concept/tags`.
2. Add a `[[<slug>]]` wikilink under the relevant section of `/home/itadmin/brain/index.md` so it's
   not an orphan (the dream cycle resolves wikilinks → DB edges; an unlinked page = orphan warning).
3. Run the refresh (or wait for 3 AM). Verify with `gbrain search "<topic>"` — the page's chunks
   should appear. The brain repo is `/home/itadmin/brain` (the git checkout the cron syncs).

## Brain directory structure (MECE)

```
~/brain/
  people/       # Individual people
  companies/    # Organizations
  projects/     # Active projects
  tools/        # Tools, platforms, DMS
  sessions/     # Session audit summaries
  concepts/     # Abstract ideas, terminology
```

## Pitfalls

- **Do NOT set both ZEROENTROPY_API_KEY and OPENAI_API_KEY** — gbrain sees multiple providers and refuses to pick in non-interactive mode
- **Do NOT pass keys via CLI** (`gbrain init --zeroentropy-key X`) — this also hangs
- **Stale lock files** in `~/.gbrain/` from failed inits block subsequent runs — delete them
- **PATH must be explicit** — `export PATH="$HOME/.bun/bin:$PATH"` before every gbrain command
- **`gbrain init --non-interactive` does NOT work** with multiple embedding providers configured
- **Cron prompts must not export API keys inline** — the security scanner blocks the command waiting for approval that never comes; source `~/.gbrain/.env` with `set -a` instead
- **`gbrain dream` without `--dir`** silently skips all filesystem phases (lint/backlinks/sync) — easy to miss because exit code is still 0
