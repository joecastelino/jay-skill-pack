---
name: jay-brain-and-skill-index
description: Operate, diagnose, and repair Jay's GBrain (the single Jay-only knowledge brain) plus the self-maintaining skill index. Use when the nightly brain refresh fails or looks frozen, when `gbrain` is "command not found", when GBrain search returns nothing/stale, when session knowledge needs to be captured into the brain so it's retrievable later, or when the skill index needs descriptions/metadata/usage-counts. Covers the bun-PATH break, the multi-brain split, the embedding-key gotcha, and the capture-session / skill-usage tracking scripts.
triggers:
  - brain refresh failed
  - gbrain command not found
  - gbrain search returns nothing
  - capture this session into the brain
  - update jay's brain
  - skill index usage tracking
  - which skills am I using
  - rebuild skill manifest
  - brain not being updated
  - jay-only brain
---

# Jay's Brain + Skill Index — Operate & Repair

## HOW GBRAIN ACTUALLY WORKS — use its built-ins, don't reinvent (clarified 2026-06-25)
GBrain (v0.42) owns the whole pipeline: chunk → embed → store → retrieve → maintain. My job is to
feed it clean, well-formed pages and USE THE RIGHT COMMANDS, not rebuild what it does.
- **Retrieval — use `gbrain query "<question>"` (a.k.a. `ask`), NOT `search`.** `query` = HYBRID
  search (vector embeddings + RRF reciprocal-rank-fusion + query expansion) → the real "retrieve
  data nodes" tool. `search` is only tsvector keyword match (weaker; readme/Obsidian page often
  floats to top on broad keyword searches — ignore it, it's the readme text quoted in a skill page).
- **Chunking/embedding are automatic** on `import`/`sync`. ZeroEntropy `zembed-1`, 1280-dim, per
  chunk. Pages >~50KB trigger a "consider splitting" WARN (not error) — chunk long transcripts.
- **`gbrain link` SLUG + FLAG GOTCHA (verified 2026-06-25):** to create an explicit edge use
  `gbrain link <from> <to> --link-type references`. The target slug MUST include its category
  prefix — `projects/session-20260625_075211_dce000`, NOT the bare `session-2026...` (bare fails
  with `addLink failed: page "..." not found`). The root hub page is just `index` (no prefix). The
  ONLY valid options are `--link-type` and `--context`; there is **NO `--link-source` flag** (the
  brain-sync cron prompt suggests `--link-source sync` — it's silently ignored/causes the not-found,
  so drop it). Linking the 2 nightly session captures from index nudged Links 174→178.
- **Nightly brain-sync cron normal path (2026-06-25, re-verified clean 2026-06-26):** the every-15-min
  session-end-sync already commits new session pages, so when the brain-sync cron runs, git is usually
  CLEAN and `import` picks up the 1-2 newest `projects/session-*` captures ("2 pages imported / 135
  unchanged" = right tree). The "new pages to link from index" are those session captures. FULL
  HAPPY-PATH SEQUENCE (each git cmd a SEPARATE terminal call, no `&&` chains):
  1. `gbrain import /home/itadmin/brain/ --no-embed` + `gbrain embed --stale` (auto-embeds new sessions).
  2. Find unlinked: `comm -23 <(ls brain/projects/session-*.md|sed 's#.*/##;s#\.md$##'|sort -u) <(gbrain backlinks index|grep -io 'session-[0-9_a-f]*'|sort -u)`.
  3. For each: verify it exists with `gbrain get projects/session-<ts>` (head -3 shows frontmatter),
     then `gbrain link projects/session-<ts> index --link-type child_of` → expect `{"status":"ok"}`.
  4. ALSO add them to index.md's `## Sessions` body list (patch after the last session line; pull the
     title from the page's `title:` frontmatter for the `— description` suffix).
  5. `git add -A` → `git commit -m "brain sync"` (separate calls).
  6. **RE-IMPORT + EMBED AGAIN** so the EDITED index.md page itself gets re-embedded:
     `gbrain import --no-embed` (reports "1 page imported") + `gbrain embed --stale` ("1 chunk").
     Skipping this leaves index.md's new wikilinks unembedded until 3 AM.
  7. Verify: `gbrain stats` Embedded==Chunks; linked-sessions==disk-sessions count; `git status` clean.
- **THE GRAPH/EDGES ARE A SEPARATE, MOSTLY-EMPTY LAYER (key gotcha):** `[[wikilinks]]` in page
  BODIES and the frontmatter `links:` field are CONTENT — they are NOT auto-converted into graph
  edges. As of 2026-06-25 the brain had only 42 links across 99 pages and `backlinks index` = [].
  Real graph edges are created EXPLICITLY via `gbrain link <from> <to> [--type T]`, or sparsely by
  `gbrain extract --stale` (LLM semantic edge extraction — conservative, pulled just 3 `mentions`
  links from 74 pages; it does NOT parse wikilink syntax). So `gbrain graph <slug>` / `backlinks`
  / `graph-query` only return useful nodes for pages where edges were explicitly built. DECISION:
  rely on `query` (hybrid embedding) for retrieval — it works great and needs no graph. Only invest
  in `link` edges if a specific traversal/relationship view is wanted. Don't assume wikilinks=edges.

**GRAPH EDGES NOW WIRED + AUTO-MAINTAINED (2026-06-25, Joe: "hook up graph traversal, use the brain
to its full advantage"):** `/home/itadmin/bin/build-brain-edges.py` deterministically creates the
edge layer via `gbrain link <from> <to> --link-type T` (NOTE flag is `--link-type`, NOT `--type`):
every skills/* → skills-index (child_of), kb/* → kb-index (child_of), memory/* + projects/session-* +
concepts/* + the hubs → index (child_of), PLUS topic cross-links skill/concept ↔ kb article
(related_to) matched on keyword sets (source-code, service-menu, opcode, stock-order, parts,
scheduling, process-automation). Idempotent: checks existing `backlinks <target>` before creating,
+ a belt/suspenders state file `/home/itadmin/.gbrain/brain-edges.state`. Result 2026-06-25: brain
went 42→178 links; `gbrain graph index --depth 2 --direction both` reaches 189 nodes; skills-index
has 38 clean backlinks (0 dupes). **TRAVERSAL USAGE:** `gbrain graph <slug> --depth N --direction
both` (CRITICAL: edges are built child→hub, so from a HUB you must use `--direction both` or `in`
to walk DOWN to children; default direction only walks outbound/up). `gbrain backlinks <slug>` =
inbound. **WIRED INTO PIPELINE:** session-end-sync.sh calls build-brain-edges.py after the
skill-manifest rebuild whenever it captured new pages — so new pages auto-get their edges every
15-min pass. Edges live in the brain DB (PGLite), NOT the markdown repo (nothing to git-commit).
Semantic `gbrain extract --stale` is slow + low-yield (3 links from 74 pages) — left to 3AM refresh.

**BUG in build-brain-edges.py — STALE STATE FILE leaves edges silently unbuilt (found+fixed 2026-06-25):**
The script's `link()` short-circuits on the belt/suspenders state file `/home/itadmin/.gbrain/brain-edges.state`:
if an edge key `<from>\t<to>\t<type>` is in `_edge_state`, it returns False and SKIPS the real
`gbrain link` subprocess — WITHOUT verifying the edge actually exists in the DB. So if a key got
written to state but the edge never persisted (or was lost), the builder reports `edges_created:0`
forever while the page stays unlinked. Symptom: `gbrain backlinks index | grep session | sort -u | wc -l`
< number of `projects/session-*.md` files, yet `build-brain-edges.py` creates 0. FIX (manual, reliable):
link the missing edges DIRECTLY, bypassing the script: `gbrain link projects/session-<ts> index --link-type child_of`.
Find the gap: compare `ls brain/projects/session-*.md` (strip path+.md) vs the dedup'd backlinks-index
session list (`comm -23`). 2026-06-25 this left 6 sessions unlinked (15→21 of 21 after manual link).

**IMPORT can SKIP a committed page (mtime/hash gap) — page absent from brain despite valid .md (2026-06-25):**
A valid session .md (good frontmatter, committed in git) was NOT in the brain — `gbrain list` didn't show
it and `gbrain link <slug> index` failed `addLink failed: page "..." not found`. The dir import had counted
it among "unchanged" and skipped it. FIX: `touch /home/itadmin/brain/projects/<file>.md` to bump mtime, then
re-run `gbrain import /home/itadmin/brain/ --no-embed` (it imports as 1 changed page), `gbrain embed --stale`,
then `gbrain link`. Single-file import does NOT work (`gbrain import <file.md>` → "Found 0 markdown files";
import wants a directory). Always sanity-check after sync: session→index edge count == session .md file count.

**DETECTOR FALSE-POSITIVE + wikilinks NOW make edges (2026-07-03 evening sync):** the classic
disk-vs-`backlinks index` `comm -23` diff flagged session-20260703_150319 as unlinked, but it was
FINE — its only edge is index→page (`link_type: references`, `link_source: "markdown"`), which
doesn't appear in `backlinks index` (that lists edges pointing TO index). So when the comm diff
flags a session, check `gbrain backlinks projects/session-<ts>` for an inbound index→page edge +
its presence in index.md's Sessions list BEFORE remediating — if both exist and `gbrain orphans`
is 0, nothing to do. ALSO NOTE: `link_source: "markdown"` means newer gbrain versions DO create
edges from index.md wikilinks (the older \"wikilinks are content, not edges\" note is stale for
hub-page wikilinks). Healthy 2026-07-03 evening baseline: 292 pages / 913 chunks / 913 embedded /
661 links / 0 orphans.

**ORPHAN DETECTION NEEDS AN INBOUND EDGE — hub→page direction (verified 2026-07-03 dream cycle):**
`gbrain orphans` / the dream-cycle orphans phase counts a page as orphaned unless it has an INBOUND
edge. The usual child→hub link (`gbrain link projects/session-<ts> index --link-type child_of`)
does NOT clear orphan status — after linking 21 orphans that way, the count stayed 21. What clears
it is the hub→page direction: `gbrain link index <slug> --link-type references` (or
`gbrain link skills-index skills/<name> --link-type references` for skill pages). The 2026-07-03
dream run found 21 orphans (all of 2026-07-02's session captures + jay-memory-09 +
skills/bt-tony-menu-rebuild — build-brain-edges had missed them, its stale-state bug again); linking
them index→page took orphans 21→0. When fixing orphans, do BOTH directions if you also want
backlinks-index completeness, but the hub→page edge is the one the orphan scanner needs.
**KB-PAGE ORPHANS use the kb-index hub (verified 2026-07-12):** a KB auto-ingest batch can drop
DOZENS of `kb/svc30-*` orphans at once (59 in one run — the ingest wrote the pages but built no
edges). Clear them with `gbrain link kb-index kb/<slug> --link-type references` (hub→page, same
pattern; a simple while-read loop over the orphan list works — 59/59 ok). Parse the orphan list per
category: `gbrain orphans` groups output under `[kb]` / `[projects]` / etc. headers. Hub mapping:
sessions/memory/concepts → `index`, skills/* → `skills-index`, kb/* → `kb-index`. Latecomer streaks
apply here too — the 15-min session-end-sync's KB ingest can commit NEW kb pages mid-run (one run
had 4 kb + 2 session latecomers after the first orphan pass); loop until `gbrain orphans` = 0.

SIDE PROJECT QUEUED (Joe wants, later — NOT now): interactive brain VISUALIZATION (node-graph of all
pages + edges, like the Obsidian/online graph views Joe has seen). Build after the brain core is
solid. Data source: `gbrain graph`/`graph-query` JSON + `list` for nodes; render as a force-directed
web graph (own repo per Joe's separate-codebase rule).

(prev) FAILURE #2 note + general:
- **Other built-ins worth knowing:** `doctor` (health: resolver/skills/pgvector/RLS/embeddings),
  `graph <slug> --depth N` (node traversal, JSON), `graph-query <slug> --type --direction`,
  `backlinks <slug>`, `timeline`, `brainstorm`/`lsd` (idea generation over the brain),
  `files upload-raw` (size-routed file storage), `export`/`import`/`sync --watch`/`sync --install-cron`.
- **Bottom line for me:** stop hand-rolling retrieval; use `gbrain query`. Keep feeding clean
  embedded pages (the auto-ingest + session-end-sync already do this). The pipeline is GBrain's job.


How Jay's knowledge brain (GBrain) and the skill index work, the recurring failures, and the
scripts that keep them self-maintaining. Joe's intent (2026-06-24): "make sure the brain inside
of Jay is being updated regularly and accurately... actively using it... keeping track of what
skills we're using." Other agents' brains are NOT Jay's concern — only the Jay-specific one.

## The architecture (verified 2026-06-24)
- **ONE Jay brain DB:** `/home/itadmin/.gbrain/brain.pglite` (PGLite engine, ZeroEntropy
  `zeroentropyai:zembed-1` embeddings, 1280 dims).
- **THREE `.gbrain` config dirs** — this is the #1 source of confusion:
  1. `/home/itadmin/.gbrain/` — the itadmin/cron config; its `config.json` `database_path` =
     `/home/itadmin/.gbrain/brain.pglite`. The nightly refresh (cron, HOME=/home/itadmin) uses this.
  2. `/home/itadmin/.hermes/profiles/jay/home/.gbrain/` — **Jay's interactive-session config**
     (Jay's session HOME = `/home/itadmin/.hermes/profiles/jay/home`). It has its own `config.json`
     + `.env` (the API keys) but **NO separate DB** — its `database_path` ALSO points to
     `/home/itadmin/.gbrain/brain.pglite`. So both read/write the SAME brain. Good — keep it that way.
  3. `/home/itadmin/.hermes/profiles/don-ready/home/.gbrain/` — Don Ready's OWN separate DB
     (`.../don-ready/home/.gbrain/brain.pglite`). **Leave it alone — not Jay's.**
- **Brain repo (markdown source):** `/home/itadmin/brain` (git, branch `master`). NOTE this is a
  SHARED fleet vault — it has pages for ALL agents (agents/jay, agents/stacey, agents/walter,
  agents/don, the `readme` "Obsidian Vault managed by Dori", etc.). Jay-relevant pages: agents/jay,
  system/jay-tool-index, people/joe-castelino, companies/american-motors-group,
  concepts/tekion-*, projects/{dealerdetail, caliber-ops, tekion-opcode-pricing, sct-*}.
- **Refresh script:** `/home/itadmin/bin/brain-refresh.sh`, cron `0 3 * * *`, logs to
  `/home/itadmin/.gbrain/brain-refresh.log`.

## Always-run preamble (env every gbrain command needs)
`gbrain` is a TypeScript shebang RUN BY bun. bun lives at `/home/itadmin/.hermes/node/bin/bun`
(it MOVED there — it is NOT in `~/.bun/bin` anymore, that dir only has the `gbrain` symlink).
The embedding key must be exported or sync prints "set ZEROENTROPY_API_KEY" and skips embedding.
```bash
export PATH="/home/itadmin/.hermes/node/bin:/home/itadmin/.bun/bin:$PATH"
set -a; source /home/itadmin/.gbrain/.env; set +a   # loads ZEROENTROPY_API_KEY + OPENAI_API_KEY
HOME=/home/itadmin gbrain stats     # always run gbrain with HOME=/home/itadmin (the cron HOME)
```

## FAILURE #1 — refresh silently dead / `gbrain: command not found` (THE recurring one)
Symptom: `brain-refresh.log` shows `/usr/bin/env: 'bun': No such file or directory` then
`[warn] sync failed / extract failed / dream failed`, or `gbrain` not on PATH. Root cause: bun
moved to `~/.hermes/node/bin`; the script's PATH only had `~/.bun/bin`. The `|| echo warn`
swallowed the error so the run "completed" looking healthy. **This has broken twice — when paths
got reorganized.** FIX (already applied to brain-refresh.sh, re-apply if it regresses):
```bash
export PATH="/home/itadmin/.hermes/node/bin:$HOME/.hermes/node/bin:$HOME/.bun/bin:/home/itadmin/.bun/bin:$PATH"
# plus a fail-LOUD guard at top:
if ! gbrain --version >/dev/null 2>&1; then
  echo "=== $(date -Is) brain-refresh ABORTED: gbrain not runnable (bun? $(command -v bun)) ===" \
    >> /home/itadmin/.gbrain/brain-refresh.log
fi
```
Verify the fix: `HOME=/home/itadmin /usr/bin/bash /home/itadmin/bin/brain-refresh.sh` then tail the
log — should end "Brain is healthy. 22 phase(s) checked". `bash -n` the script first.

## FAILURE #1b — sync cron uses `~/brain` but `~` is the WRONG tree (silent skip)
The brain-sync cron job runs commands like `gbrain import ~/brain/ --no-embed`. Under Jay's session
HOME, `~/brain` = `/home/itadmin/.hermes/profiles/jay/home/brain/` — a STALE 7-file copy, NOT the
canonical 19-file repo at `/home/itadmin/brain/`. The import reports "0 imported, 0 stale, 0 errors"
and looks perfectly healthy while silently skipping the real brain. Confirmed 2026-06-24: importing
the canonical repo instead picked up 2 changed pages + re-embedded 2 chunks the `~/brain` run missed.
**WORSE VARIANT (observed 2026-07-02): the stale tree can CLOBBER, not just skip.** As of 2026-07-03 the stale
`~/brain` copy shares exactly TWO slugs with canonical: `index` and `people/joe-castelino`
(caliber-ops, tekion-dms, tekion-opcode-pricing, american-motors-group, sessions/session-audit-20260609
are stale-ONLY). So a wrong-tree import reporting "2 pages imported" = it clobbered index +
joe-castelino; the canonical re-import restoring exactly 2 pages confirms full recovery. A `gbrain import ~/brain/` under Jay's session HOME reported
"2 pages imported / 2 chunks" — it OVERWROTE those DB pages with the stale 2026-06-09-era content
and embedded it. So a "pages imported" result from the wrong tree is actively harmful, not benign.
RECOVERY: immediately re-import canonical (`HOME=/home/itadmin gbrain import /home/itadmin/brain/
--no-embed` — it re-imports the same N pages as "changed") + `gbrain embed --stale`, then VERIFY the
DB matches canonical: `gbrain get index | grep -c 'session-2026'` == `grep -c 'session-2026'
/home/itadmin/brain/index.md`, and spot-diff a shared page body (`diff <(gbrain get
people/joe-castelino | grep -A100 '^# ') <(grep -A100 '^# ' /home/itadmin/brain/people/joe-castelino.md)`).
Stale-ONLY slugs (caliber-ops, tekion-dms, etc.) will linger with stale content in the DB — they've
been there historically and are low harm, but don't re-feed them.
**THE DREAM-CYCLE CRON HAS THE SAME TRAP (hit 2026-07-17):** the nightly dream cron prompt says
`gbrain dream --dir ~/brain` — under Jay's session HOME its sync phase full-reimports the stale
7-file `~/brain` tree ("Found 7 markdown files... 2 pages imported" = index + joe-castelino
clobbered; a "sync anchor object missing, running full reimport" message precedes it). Run the
dream with `--dir /home/itadmin/brain` (or HOME=/home/itadmin) instead. If already run wrong:
canonical re-import + embed recovers exactly 2 pages; verify index session-ref count DB==disk and
joe-castelino body diff empty. The dream's other phases (extract/consolidate/orphans/purge) operate
on the DB and are unaffected — no need to re-run the whole cycle after recovery.
**RECURRED 2026-07-03 — THE BRAIN-SYNC CRON PROMPT ITSELF IS THE TRAP:** the cron job's prompt
literally says `gbrain import ~/brain/ --no-embed`, so every run under Jay's session HOME clobbers
`index` + `people/joe-castelino` again ("2 pages imported / 2 chunks" from the 7-file stale tree).
DO NOT run the prompt's commands verbatim. On ANY brain-sync cron run: substitute the canonical
path + cron HOME BEFORE the first import (don't wait to detect the clobber), then proceed with the
happy-path sequence. If you already ran the wrong-tree import, recover per below and verify
(index session-ref count matches disk, joe-castelino body diff clean — both confirmed working
recovery checks on 2026-07-03). Also from that run: orphan scan found the day's session captures
PLUS a skill page (skills/tekion-menu-custom-price-row) unlinked — skill-page orphans clear via
`gbrain link skills-index skills/<name> --link-type references` (hub→page), same as index→session.
FIX: always import the CANONICAL path explicitly with the cron HOME:
```bash
HOME=/home/itadmin gbrain import /home/itadmin/brain/ --no-embed 2>&1 | tail -5
HOME=/home/itadmin gbrain embed --stale 2>&1 | tail -3
```
Sanity after: `gbrain stats` Embedded must == Chunks (25 pages / 29 chunks / 29 embedded as of
2026-06-24), both git trees clean. "2 pages imported / N unchanged" with N>0 means you hit the
right tree.

## FAILURE #2 — search returns nothing / page not embedded
Cause: page exists in the repo but wasn't synced, OR sync ran without the embedding key so chunks
imported but didn't embed. FIX: run the preamble (so the key is exported), then
`HOME=/home/itadmin gbrain sync --repo /home/itadmin/brain --no-pull`. Look for
"N pages embedded". Confirm with `gbrain stats` (Embedded should equal Chunks) and a
`gbrain search "..."`. As of 2026-06-24: 25 pages, 29 chunks, 29 embedded.

## CAPTURE A SESSION INTO THE BRAIN (the "store each session so it's findable" piece)
Each session's durable learnings should become a brain page so the nightly refresh embeds them and
`gbrain search` finds them later. Write a markdown page WITH yaml frontmatter and drop it in
`/home/itadmin/brain/projects/<slug>.md`:
```
---
type: session
date: YYYY-MM-DD
title: <short title>
tags: [tekion, parts, ...]
links: [[tekion-parts-replenishment]], [[tekion-apc-tools]]   # wikilink to existing pages, no orphans
---
# <title>
## What we did / ## Key result / ## Files / ## Related
```
Then capture + sync it live (don't wait for 3 AM):
`/home/itadmin/bin/capture-session.sh <slug> < /tmp/page.md`  (writes, commits, gbrain sync).
Keep pages CONCISE and link them so they aren't orphans. Prefer extending an existing project page
over creating many tiny ones. This is distinct from `memory` (which is full at ~98% and is for
compact always-injected facts) — the brain holds the fuller searchable record.

## SESSION-END AUTO-SYNC (multi-session-per-day capture, added 2026-06-25)
Hermes has NO native session-end hook, so a watcher cron captures FINISHED sessions into the brain
between the daily 3 AM refreshes (Joe's intent: "add a session-end sync... automatically parses and
updates the info at the end of the session"). This is what makes multiple sessions a day get stored.
- **Script:** `/home/itadmin/bin/session-end-sync.sh`. **Cron:** every 15 min, logs to
  `/home/itadmin/.gbrain/session-end-sync.log`. State (processed sessions) in
  `/home/itadmin/.gbrain/session-sync.state` (one session basename per line — never re-processed).
- **Mechanism:** scans the jay sessions dir `session_2*.json` (skips `session_cron_*` + request_dumps),
  picks ones IDLE >= 20 min (no writes = finished) and not in the state file and >= 8000 bytes,
  extracts the user+assistant transcript, distills it via a ONE-SHOT no-tools LLM call
  (`hermes chat -q "$prompt" -Q -t "" --max-turns 1` — the venv hermes at
  `/home/itadmin/.hermes/hermes-agent/venv/bin/hermes`), then pipes the page into
  `capture-session.sh <slug>` (commit + `gbrain sync` + embed — searchable immediately).
- **Gotchas:** `hermes -Q` prepends a `session_id:` line — the script awk-strips everything before
  the first `---` frontmatter line. The distill may return `SKIP` (nothing durable) — detected on the
  RAW output BEFORE stripping, else it'd look empty and hit the raw fallback. Slug = `session-<ts>`.
  The live/current session is still being written so the 20-min idle gate safely skips it.
- **First-run seeding:** on install, the state file was pre-seeded with all 221 then-existing
  interactive sessions so it would NOT distill the entire backlog — only NEW finished sessions going
  forward. To backfill, remove lines from the state file.
- **Verify:** `tail /home/itadmin/.gbrain/session-end-sync.log`; `gbrain stats` (Pages grow as
  sessions finish); `ls /home/itadmin/brain/projects/session-*.md`. Validated 2026-06-25 on the SCT
  4Runner menu session — produced a high-quality distilled page from a 448KB transcript in ~36s.
- **Memory cap raised** 2026-06-25 in the two hermes config.yaml files (base + jay profile): the
  memory limit went 18000 to 28000 chars and the user-profile limit 9000 to 12000 (MEMORY.md had
  already exceeded the old 18K). Timestamped `.bak` copies were kept alongside each config.

## SKILL→BRAIN AUTO-BACKFILL NOW WIRED (2026-06-29, Joe directive: "skills should automatically wire into the brain instead of you manually calling it")
Previously `backfill-skills-to-brain.py` was ONLY run by hand, so new/edited automotive skills
silently accumulated UN-searchable in the brain (found a 13-skill gap on 2026-06-29: 51 SKILL.md
files but only 38 brain/skills/*.md pages — incl that day's tol-menu-sales-reports,
tol-alignment-by-advisor-report, tekion-ghost-bin-negative-onhand, tekion-kb-search-scrape, etc.).
NOW `session-end-sync.sh` (every 15 min) auto-backfills: it runs `backfill-skills-to-brain.py`
(pure file writes of brain/skills/*.md + brain/memory/*.md + skills-index.md — fast/cheap every pass),
then checks `git status --porcelain -- skills/ memory/ skills-index.md`; ONLY if something actually
CHANGED does it commit + `gbrain import --no-embed` + `gbrain embed --stale` + set captured_any=1
(so build-brain-edges then wires the new pages). Same cheap change-gated pattern as the KB ingest.
Block sits right after the rebuild-skill-index.sh call. VERIFIED 2026-06-29: no-change pass logs
nothing (correct); injecting a stale page → "-> skill backfill: 1 skill/memory page(s) changed",
regenerates it, import+embed, tree clean. So: create/edit a skill → searchable in brain within 15 min,
no manual `backfill-skills-to-brain.py` call needed. NOTE the backfill only covers the AUTOMOTIVE
skills dir (the 73 generic plugin skills are intentionally excluded as search noise).

## SKILL INDEX with descriptions + metadata + usage counts (SELF-MAINTAINING as of 2026-06-25)
Files under `/home/itadmin/.hermes/profiles/jay/skills/`:
- `manifest.json` — enriched: per skill {name, skill_name, path, **description**, **triggers**,
  category, size_bytes, modified}. Regenerate with `/home/itadmin/bin/rebuild-skill-index.sh`
  (parses each SKILL.md frontmatter; preserves usage counters; adds new skills at 0; drops deleted).
- `usage-stats.json` — `{skills:{<name>:{times_used,last_used}}}`. Survives rebuilds.
- `usage-log.ndjson` — append-only audit (one `{ts,skill}` JSON line per use).
- `RESOLVER.md` — curated trigger→skill table (hand-maintained).

**AUTO-MAINTENANCE (no manual steps needed — wired into session-end-sync, runs every 15 min):**
1. **Manifest auto-rebuild:** `session-end-sync.sh` calls `rebuild-skill-index.sh` at the end of
   every run, so descriptions/sizes/modified-dates/new+deleted skills stay current automatically.
2. **Auto usage logging:** for every FINISHED session it captures, `session-end-sync.sh` runs
   `/home/itadmin/bin/log-skill-uses-from-session.py <session.json>` which scans that session's
   `tool_calls` for `skill_view`/`skill_manage` and bumps `times_used` + stamps `last_used`. KEY
   MAPPING: tool-call args carry the BARE skill name (`tekion-foo`) but usage-stats keys are the
   CATEGORY PATH (`automotive/tekion-foo`) — the helper maps bare→path via the manifest's
   `skill_name`→`name`. Counts +1 per skill PER SESSION (distinct use), not per call, so reloading a
   skill 5× in one session = 1 genuine use. This REPLACES manually remembering `log-skill-use.sh`.
   Verified 2026-06-25: correctly credited `automotive/tekion-quotes-menu-price-diagnosis` (0→1).
- The manual `/home/itadmin/bin/log-skill-use.sh <category/skill-name>` still works for one-off
  same-session crediting, but is now mostly redundant.
See top movers: `python3 -c "import json;d=json.load(open('/home/itadmin/.hermes/profiles/jay/skills/usage-stats.json'));print(sorted([(v['times_used'],k) for k,v in d['skills'].items() if v['times_used']>0],reverse=True))"`

## DIAGNOSTIC: `gbrain list` CAPS session display at ~42 — NOT an import-skip / missing-page bug (2026-06-26)
FALSE-ALARM trap during brain-sync: comparing `gbrain list -n 1000 | grep session | sort -u | wc -l`
(showed 42) against `ls brain/projects/session-*.md` (53 files) looks like 11 committed pages were
import-skipped/missing. THEY ARE NOT MISSING. In v0.42.37 `gbrain list` silently caps the session
rows it prints (~42) regardless of `--limit`/`-n` or `--include-deleted`. Proof the pages are fine:
`gbrain get projects/session-<ts>` returns full frontmatter+body, AND `gbrain query "<topic>"`
returns them at high relevance (0.84–0.93), AND `gbrain backlinks index` lists all 53. So do NOT
trust `gbrain list` for a complete page census or as the import-skip detector. Use the AUTHORITATIVE
checks instead: (a) `gbrain stats` Embedded==Chunks (health), (b) `gbrain backlinks index | grep
session | sort -u | wc -l` == `ls brain/projects/session-*.md | wc -l` (link completeness), (c) spot
`gbrain query` for a known topic. Also: `touch`-ing a .md no longer forces re-import in v0.42.37
(importer is content-hash based, not mtime) — the touch→import FIX documented above for FAILURE
"IMPORT can SKIP a committed page" may be ineffective; verify the page is genuinely absent via
`gbrain get <slug>` (errors if truly missing) BEFORE attempting any re-import remediation.

**DETECTOR GOTCHA — a per-file `gbrain get` LOOP can give a transient FALSE-NEGATIVE (2026-06-28):**
When hunting import-skipped pages, do NOT trust a `for f in session-*.md; do gbrain get $slug; done`
loop as the authority — on 2026-06-28 (v0.42.21) that loop reported "0 missing" on one pass while a
STANDALONE `gbrain get projects/session-<ts>` for the same slug consistently returned `page_not_found`,
and the disk-vs-backlinks `comm -23` consistently flagged it. The AUTHORITATIVE missing-page detector is
the link-completeness diff: `comm -23 <(ls brain/projects/session-*.md|sed 's#.*/##;s#\.md$##'|sort -u)
<(gbrain backlinks index|grep -io 'session-[0-9_a-f]*'|sort -u)` — anything it prints, confirm once with
a SINGLE standalone `gbrain get <slug>` (+ `--include-deleted` to rule out soft-delete), then fix. Also
note `gbrain stats` session count can lag the true count (showed 65 while disk=67 and only 1 page was
actually missing) — don't size the gap from stats; size it from the `comm` diff. The newline-bump fix
below still works on v0.42.21 (1 page imported / 1 chunk embedded, `gbrain get` then resolved).

**WORKING FIX for a content-hash import-skip in v0.42.37 (verified 2026-06-26):** when `gbrain get
projects/session-<ts>` returns `page_not_found` (and `--include-deleted` confirms it's NOT soft-deleted)
yet the .md is valid + git-committed, the importer has a recorded hash but no page row (state/DB mismatch).
`touch` does NOT fix it (importer is content-hash, not mtime). The reliable fix is to BUMP THE CONTENT
HASH by appending a harmless extra trailing newline to the file, then re-import:
  for each missing file → write back its content + one extra `\n`, then
  `gbrain import /home/itadmin/brain/ --no-embed` (reports the bumped pages as imported) + `gbrain embed --stale`,
  then `gbrain link projects/session-<ts> index --link-type child_of`, add to index.md Sessions list,
  git add/commit, and FINAL re-import+embed so index.md re-embeds.
Confirmed 2026-06-26: 2 sessions (161728, 162505) were import-skipped this way; newline-bump re-ingested
both (3 pages imported / 3 chunks embedded) and `gbrain get` then resolved them. NOTE the brain-sync run
is a moving target — the 15-min session-end-sync can commit NEW session pages mid-run, so after your final
your final verify, RE-CHECK `comm -23 <(disk sessions) <(backlinks index)` once more and link any latecomer (happened
2026-06-26: session-20260626_163841 appeared after the first scan and needed a second link+commit+embed pass).
LATECOMER TRIAGE — `gbrain get` FIRST to pick the right fix (verified 2026-06-29): when the diff flags
a latecomer, the two cases need DIFFERENT handling and you can't tell which by inspecting the .md.
Run `gbrain get projects/session-<ts>` immediately: (a) if it RESOLVES (returns frontmatter), the page
was already pulled in by a prior `import` pass in this same run — just `gbrain link ... index --link-type
child_of` + add to index.md + commit + reimport/embed (NO newline-bump). (b) if it returns
`page_not_found` (and `--include-deleted` confirms not soft-deleted), it's a content-hash import-skip —
apply the newline-bump fix THEN link. In the 2026-06-29 run the FIRST latecomer (161548) needed the bump
(committed by session-end-sync AFTER my import, so never ingested) while the SECOND (173215) already
resolved (it rode in as the "1 page imported" of the index.md re-embed pass) and only needed linking.
Doing the cheap `gbrain get` probe first avoids a needless bump on case (a).
**ALWAYS compare import-scan count vs disk count RIGHT AFTER the first import (verified 2026-07-14):**
a first import reporting \"0 pages imported / N skipped / 0 errors\" can look perfectly healthy while
having missed SEVERAL freshly-committed session pages entirely (saw scan total 570 vs 572 .md on disk;
`git log` showed 3 session commits seconds old). Check: `find /home/itadmin/brain -name '*.md' -not
-path '*/.git/*' | wc -l` vs the import's imported+skipped total. If disk > scanned, just re-run the
plain import — it picked up all 3 as \"3 pages imported\", no newline-bump needed. Then embed, link the
new orphans hub→page (`gbrain link index projects/session-<ts> --link-type references`), add to
index.md Sessions list, commit, final re-import+embed. Don't wait for a `page_not_found` to run this
check — it's the cheapest latecomer detector and `gbrain orphans` right after the re-import names
exactly the pages needing links.
CASE (b) REFINEMENT — try a PLAIN RE-IMPORT before the newline-bump (verified 2026-07-10): a
`page_not_found` (not soft-deleted) does NOT always mean a content-hash skip. If session-end-sync
committed the file seconds before your first import, the import scan can MISS the file entirely —
tell-tale: the import's total file count (imported+skipped) is LESS than `find brain -name '*.md' | wc -l`
(saw 394 scanned vs 395 on disk). A second plain `gbrain import /home/itadmin/brain/ --no-embed`
picked it up cleanly as \"1 page imported\" — no bump needed. So triage order for page_not_found:
(1) compare import-scan count vs disk count; (2) re-run plain import + embed; (3) only if it STILL
reports 0 imported and `gbrain get` still fails, apply the newline-bump.
ALSO re-confirmed 2026-07-10: the disk-vs-index.md wikilink `comm` diff shows dozens of older
sessions (June 25–Jul 2 era) absent from index.md's Sessions list while `gbrain orphans` = 0 —
those have edges via build-brain-edges and are FINE. `gbrain orphans` output is the authoritative
orphan check; only remediate diff entries that are NEW sessions from the current run.

LATECOMERS CAN ARRIVE IN A STREAK — LOOP, don't just re-check once (verified 2026-06-29): a single
brain-sync run had THREE latecomer sessions appear back-to-back (115831, 120206, 120700) as the 15-min
session-end-sync committed them mid-run. Each needed its own link→add-to-index.md→commit→re-import→embed
pass. The clean exit condition is: `comm -23 <(disk sessions) <(backlinks index)` prints NOTHING, AND
`gbrain stats` Embedded==Chunks, AND `git status` clean. Keep looping the link+index+commit+reimport+embed
cycle until that diff is empty on a fresh check. NOTE the happy-path is usually trivial — the FIRST import
reports just "1 page imported / 1 chunk" (the one newest session); the rest of the work is linking it +
re-embedding the edited index.md. ALSO observed 2026-06-29: a `git commit` may report "nothing to commit"
even after a real index.md edit, because a concurrent session-end-sync pass already `git add`ed + committed
your staged change as part of its own flow — verify with `git log --oneline -3` (the edit IS captured in a
"brain sync" or "session:" commit); the tree being clean is the success signal, not the commit message.

## DIAGNOSTIC: "only N embeddings / gbrain search finds nothing about a topic we worked on"
KEY INSIGHT (2026-06-25): GBrain's embedding count only reflects pages WRITTEN INTO THE BRAIN REPO.
The bulk of Jay's actual knowledge historically lived in TWO stores GBrain never sees: (a) the
`memory` tool (MEMORY.md, ~22 dense entries) and (b) the 100+ SKILL.md files. So if `gbrain stats`
shows e.g. 26 pages / 31 embedded while you've done weeks of Tekion work, that is NOT a bug or data
loss — Embedded==Chunks is healthy; the brain simply was never fed the skills+memory. Confirm with
`gbrain list -n 100` (count the substantive Tekion pages) vs `find /home/itadmin/brain -name '*.md'`.
The session-end-sync now feeds NEW sessions in, but the EXISTING skills+memory are a backlog that
must be explicitly backfilled (write/import them as embedded pages) if you want one searchable layer.
This is also the foundation for ingesting Tekion user-manual PDFs — they belong in GBrain as\nembedded pages, NOT in the (size-capped) memory tool.\n\n**DECISION MADE + EXECUTED (2026-06-25): Joe chose Option 1 — GBrain as the SINGLE embedded search
layer.** Backfill is DONE: `/home/itadmin/bin/backfill-skills-to-brain.py` writes 1 page per
Jay-owned automotive skill to `brain/skills/<name>.md` (38 pages, full SKILL.md body + desc +
triggers, wikilinked to [[skills-index]]), splits MEMORY.md (24 entries) into
`brain/memory/jay-memory-0N.md` (5 pages, ~5 entries each, [[index]]-linked), and builds the
`brain/skills-index.md` hub. index.md now links skills-index + the 5 memory pages. Run is
idempotent (overwrites pages). After running the script: `git add -A && git commit`, then
`gbrain import /home/itadmin/brain/ --no-embed` + `gbrain embed --stale` (preamble env first).
Result 2026-06-25: 79 pages / 390 chunks / 390 embedded; skill + memory pages confirmed searchable.
Only the 38 AUTOMOTIVE skills were backfilled (the other 73 are generic plugin skills = search
noise). REMAINING TODO: the TEKION-MANUAL INGESTION PIPELINE (PDF/KB → markdown → capture-session
→ embedded page → linked in index.md) — Joe wants the knowledge graphs to keep growing into THIS
same layer. Re-run backfill-skills-to-brain.py whenever skills/memory change materially.

**KB BATCH INGEST DONE (2026-06-25):** the 2026-06-24 tekion-kb batch (sitting unsearchable in
`/home/itadmin/tekion-kb/`) was captured into GBrain via `/home/itadmin/bin/ingest-kb-batch-to-brain.py`
— writes `brain/kb/<slug>.md` (frontmatter type:kb, wikilinked to [[kb-index]]) from distilled/*.md
(3) + text/*.txt KB articles (11) + transcripts/*.txt Loom walkthroughs (7); slug-dedup collapsed
3 loom_<hash> dupes → 18 files on disk. Built `brain/kb-index.md` hub, linked from index.md. After
running: git add/commit, `gbrain import /home/itadmin/brain/ --no-embed` then `gbrain embed --stale`.
Result: 98 pages / 618 chunks / 618 embedded; KB articles now top-hit relevant queries (e.g. "set
min/max stock quantity"). NOTE: two transcript pages (01-parts-ordering-receiving ~57KB,
03-parts-workflows-pricing ~55KB) exceed gbrain's content-sanity warn threshold — a "consider
splitting" WARNING, not an error; the future manual-ingestion pipeline should chunk long transcripts.
This batch ingest is the STOPGAP; the full PDF/KB→markdown→embedded pipeline remains the separate
project Joe wants built. The "readme -- # Obsidian Vault" top hit on broad searches is NOT a ghost
page — it's the readme text quoted inside the backfilled skills/jay-brain-and-skill-index page; harmless.

**AUTO-INGEST OF DROPPED KNOWLEDGE WIRED (2026-06-25, Joe's directive "make sure any knowledge we
drop to you gets ingested into the brain from now on... at the end of every session"):**
`ingest-kb-batch-to-brain.py` is now INCREMENTAL — state file `/home/itadmin/.gbrain/kb-ingest.state`
(lines `<sha1>  <relpath>`) tracks already-ingested KB files by content-hash, so re-runs only
process NEW or CHANGED files. It reads /home/itadmin/tekion-kb/{distilled/*.md, text/*.txt,
transcripts/*.txt}, writes brain/kb/<slug>.md (frontmatter type:kb, [[kb-index]]), rebuilds the
kb-index hub, and prints JSON {new_ingested,total_kb_pages,new_files}. Standalone: pass `--embed`
to commit+import+embed inline. `session-end-sync.sh` now CALLS it every 15-min pass (block added
just before the skill-manifest rebuild): runs the ingest, and IF new_ingested>0 → git add/commit →
`gbrain import --no-embed` → `gbrain embed --stale`. VERIFIED 2026-06-25 with a self-test file
(borealis-quokka-7741) — dropped into text/, picked up on next sync run ("KB auto-ingest: 1 new
page(s)"), searchable at 0.90, then cleaned up. So: ANY file dropped into /home/itadmin/tekion-kb/
(distilled, text, transcripts) is now auto-embedded into GBrain within 15 min, no manual step.
To remove a stale brain page immediately (don't wait for 3 AM orphan-purge): `gbrain delete <slug>`
(soft-delete; e.g. `gbrain delete kb/<slug>`). `gbrain sync` does NOT purge deleted-on-disk pages.

**(superseded) OPEN DECISION raised 2026-06-25:** two models for the searchable\nmemory layer — (1) GBrain as the SINGLE embedded search layer: backfill all ~38 automotive skills +\nmemory entries into GBrain pages and route manuals there too (one query searches everything; Jay's\nrecommendation; cheap duplication) vs (2) keep layers separate (skills stay in skill system, GBrain\nholds only sessions + manuals + concepts). TWO TODOs flow from whichever is chosen: (a) BACKFILL the\nexisting skills+memory into GBrain as embedded pages; (b) build the TEKION-MANUAL INGESTION PIPELINE\n(PDF/KB article → structured markdown page(s) → capture-session.sh → embedded GBrain pages → linked\nin index.md). Do NOT start the big backfill until Joe picks the model.

## Pitfalls
- **Run gbrain with `HOME=/home/itadmin`** (the cron HOME). Jay's session HOME differs; both configs
  point at the same DB, but be consistent.
- **bun is at `/home/itadmin/.hermes/node/bin/bun`** — if `gbrain` errors, this PATH is almost always why.
- **Export the embedding key** (`source /home/itadmin/.gbrain/.env`) before sync or embedding is skipped silently.
- **Don't touch `/home/itadmin/.hermes/profiles/don-ready/home/.gbrain`** — that's Don's brain.
- **`&&` git chains trip the terminal backgrounding guard** — run `git add` / `git commit` / `gbrain sync`
  as separate terminal calls, or via capture-session.sh.
- **The brain repo is gitignored in places + shared** — Jay pages live among other agents'; that's
  expected. A future task may split out a Jay-only DB (queued, low priority).
- Memory tool is FULL (~98%) — put the fuller record in the brain, keep memory for compact facts.
