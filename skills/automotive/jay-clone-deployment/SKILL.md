---
name: jay-clone-deployment
description: Deploy a fresh Jay clone agent for a new dealership/owner — provision skills, "Jay Core" universal memory (Tekion-common, zero AMG data), scripts tree, persistent browser infrastructure, and separately-supplied credentials. Use when Joe or another owner wants a new Jay instance, when discussing what makes Jay effective beyond skills alone, or when extracting/stratifying memory into Core vs Instance layers.
triggers:
  - clone Jay
  - deploy Jay to another store
  - new Jay instance
  - jay core memory
  - what makes jay work
  - fresh jay for dealership
---

# Jay Clone Deployment

## The Gap: Skills alone ≠ Jay

The public skill pack (221 skills, github.com/joecastelino/jay-skill-pack) gives a fresh agent only **~30-40%** of Jay's effectiveness. The missing 60-70%:

| Gap | What it contains | Size |
|-----|-----------------|------|
| **Memory** | Accumulated corrections, traps, diagnostic discipline, tool quirks, session rules | ~55K |
| **Live environment** | Persistent browsers (:9223, :9224, :9225), cron jobs, script tree, cached data | Infrastructure |
| **Session history** | Recall of past diagnoses via `session_search` | Session DB |
| **GBrain** | ~99 embedded pages of KB articles, transcripts, session distillations | Vector DB |
| **Credentials** | Tekion login, Gmail OAuth, Slack/GitHub tokens | Secrets |

## Layer Architecture

The strategy: split Jay's accumulated knowledge into two layers:

### Jay Core (universal — ships with every clone)
Tekion-common knowledge. Zero AMG identifiers. Contains everything a new owner would otherwise have to discover through months of mistakes:

- **Session architecture:** localStorage not cookies, OTP via email, lock files, shared-session check, never concurrent login
- **Tekion SPA facts:** axios interceptor vs bare fetch, XHR hooks, React Query caching
- **429 taxonomy:** OVERALL_RATELIMIT vs OVERALL_QUOTA vs DEALER_QUOTA, buckets, backoff patterns
- **Diagnostic discipline:** evidence-first, quote-first verification, NEVER-GUESS rule, SAVE-VERIFY trap
- **Gmail delivery traps:** IMAP append ≠ delivery (no Received header), CID inline not data:URI, Gmail collapsing same Message-ID
- **API gotchas:** dollars in CENTS, pageNumber silently ignored, `completeNames` is a list not a dict, `billDuration` in seconds
- **Parts replenishment:** BSL round-down trap, negative-OH backfill, 5 standard reasons for stock-out
- **Opcode efficiency:** load skill BEFORE first call, run preflight, batch one section per call, real click only
- **Browser infrastructure:** headless shell missing → headed chrome under xvfb, persistent :9223 architecture, storage-state injection
- **Tool quirks:** `browser_navigate` separate unauthenticated context, `background bash` → use `/usr/bin/bash`, `declare -A` kills background scripts

### Instance Layer (empty — fills organically per owner)
AMG-specific data that must NOT ship:

- Dealer IDs (AR=6195, BC=1251, BT=1249, etc.)
- People map (Ruben=BC, Kevin=SCT, Sean=TOL, Tony=BT)
- Store-specific conventions and preferences
- Owner working style and corrections
- Per-store email recipients and Slack threads

## Deployable Unit

A full Jay clone gets:

| # | Layer | Delivered via |
|---|-------|--------------|
| 1 | Skills (221) | `git clone jay-skill-pack` |
| 2 | Jay Core memory (~50 entries) | Seed file `jay-core-memory.json` injected into profile |
| 3 | Scripts tree | Copy of `/home/itadmin/tekion-reports/` (parameterized by dealer ID) |
| 4 | Bootstrap script | `bootstrap-jay-clone.sh` — provisions profile, injects skills+core memory+scripts |
| 5 | Instance memory template | Empty scaffold `instance-memory-template.json` with `{"dealer_ids":{}, "people_map":{}, "preferences":{}}` |
| 6 | Credentials | Separately provisioned per-owner |

## Full Self-Backup Kit (BUILT & VERIFIED 2026-09-15)

Location: `/home/itadmin/jay-clone-bundle/` — three scripts + README/RESTORE.

```bash
cd /home/itadmin/jay-clone-bundle
STAMP=$(date +%Y%m%d-%H%M) /usr/bin/bash build-jay-clone.sh --with-history   # ~2 min, 2.6 GB
/usr/bin/bash seal-bundle.sh releases/<STAMP>                                # AES-256 → releases/<STAMP>/secure/
# target machine:
export PASSPHRASE='...' && bash secure/DECRYPT-AND-RESTORE.sh
JAYHOME=/home/itadmin /usr/bin/bash restore-jay-clone.sh
```

**Six tiers** (all relative to the home dir so `tar -C $JAYHOME` reproduces the layout):

| Archive | Contents |
|---|---|
| `jay-01-identity` (6.6 MB) | profile `config.yaml`/`SOUL.md`/`.env`/`auth.json`, memories, 222 skills, `cron/jobs.json`, `.ssh`, `.git-credentials`, `google_token.json`+`client_secret`, both himalaya configs, `.tekion-session.json`, `.gbrain/.env`, project `.env*` — **21 credential files** |
| `jay-02-scripts` | working tree (383 py / 107 sh in `tekion-reports`), `bin`, `caliber-ops`, `the-goods`, `dealer-detail`, all store build dirs |
| `jay-03-infra` | `persistent-browser*` (incl. the authenticated Tekion localStorage), systemd user units |
| `jay-04-knowledge` | `tekion-kb`, `brain/`, `.gbrain/brain.pglite` |
| `jay-05-data` | `tekion-reports/data`, `the-goods/data`, caliber-ops sqlite snapshot |
| `jay-06-history` | `state.db` snapshot (loose file, not in a tar) + `sessions/` |

`CREDENTIAL-INVENTORY.txt` lists every captured path + key NAME (never values) — regenerate/read it to answer "did we get secret X".

### Contained testing (MANDATORY before shipping a kit)

`sandbox-restore-test.sh <release-dir> [--full|--macsim]` — runs the REAL restore inside a
private `unshare -Urm` user+mount namespace:

* `/home/itadmin` is bind-mounted over by a tmpfs → the live profile is unreachable, all writes are RAM
* `/var/spool/cron/crontabs` and `/run/user/<uid>` are shadowed → crontab/systemd calls are contained
* it fingerprints the live crontab + home sha256 before/after and prints `UNCHANGED` / `!! CHANGED`
* pass 2 re-runs with a DIFFERENT `JAYHOME` to exercise the path-rewrite + crontab-rewrite branch

**Rules:**
1. **Every test mode must be contained.** The namespace wrapped only the default mode; `--macsim`
   ran outside it and installed a crontab on the LIVE machine three times. It was byte-identical to
   the real one *only because a bug made the rewrite a no-op* — luck, not design. macsim now passes
   `--no-activate`.
2. Add `--no-activate` to any restore invocation that stages files but must not touch cron/services.
3. Prove containment with a before/after sha256 of the live crontab — don't assert it.

### Bugs found by the sandbox (all fixed)

| Bug | Symptom | Fix |
|---|---|---|
| `sed "s\|\Q$A\E\|$B\|g"` | `\Q..\E` is a **perl-ism**; GNU sed takes it literally → substitution silently does NOTHING. Cron lines kept the old home → every job fails on the new machine. | use `perl -pi -e`, then **verify** the output contains the new path and refuse to install otherwise |
| tar + uid 1000 | Archives record uid/gid 1000. Any host without that uid (macOS, user namespace) can't `chown`, and GNU tar exits **non-zero even though every file extracted** → restore aborts. | always extract with `--no-same-owner` |
| `mapfile` | macOS bash is 3.2 → command not found | while-read loop |
| `sha256sum` | absent on macOS | `shasum -a 256` fallback |
| `$HOME` ≠ passwd home | Jay's `$HOME` is the ephemeral PROFILE home; a sandbox keyed on `$HOME` shadows the wrong dir | resolve via `getent passwd "$(id -un)"` |
| stale kit in release | Build copies the kit into the release; editing the kit afterwards leaves an OLD restore script shipping | `refresh-release-kit.sh <release> [--push-onedrive]` after ANY kit edit; run it before testing |

### Pitfalls learned the hard way

1. **Never edit the build/restore script while it is running.** Bash reads incrementally — editing mid-run produced a phantom `syntax error near unexpected token '('` and an empty tier-1 archive. `bash -n` passes; the corruption is only from the concurrent write.
2. **tar member paths must be relative to `$JAYHOME`'s parent**, i.e. `tar -C $JAYHOME` must land on `.hermes/...`. Building with `-C /` + `home/itadmin/...` extracts to `$JAYHOME/home/itadmin/...` and every post-unpack check silently MISSes. Always `tar -tJf` the result and assert the members before shipping.
3. **Glob args in a tar wrapper:** expand with `compgen -G` inside the base dir; a bare `dir/*.json` that matches nothing makes GNU tar exit non-zero and (worse) the `[[ -e ]]` guard is evaluated against the base dir, not the build cwd.
4. **`sqlite3` CLI is NOT installed** on this host. Use Python's `sqlite3` online-backup API for `state.db`/`dev.db` (raw `cp` of a WAL database silently drops recent commits).
5. **Verify the seal round-trips** — decrypt one archive and diff its sha256 against `SHA256SUMS.txt`. Don't ship an unopened vault.
6. **Dry-run the restore into a throwaway `JAYHOME`** (`--dry-run` skips crontab/systemd/npm). That's how the path-layout bug was caught.
7. Store the generated passphrase **outside** the release dir (`~/.jay-clone-passphrase`, 600). Also: never put the passphrase in the same folder that travels.

### Transport

The sealed set goes to `/mnt/c/Users/joeca/OneDrive/JayClone-<date>/secure/` (1.5 GB) plus the kit files and `SHA256SUMS.txt` one level up. Plaintext archives stay in the persistent home dir as the on-machine backup — they add no exposure the source machine doesn't already have.

### Dual-run hazard (state this to the owner every time)

The clone carries the **same** Slack bot token, Telegram bot token and Tekion localStorage session. Two live instances fight: duplicate Slack replies, Telegram `getUpdates` stealing, Tekion session invalidation (the `/tmp/tekion-session.lock` guard is host-local and does NOT cross machines). Either provision fresh bot tokens for the clone, or keep exactly one machine live.

## Core Memory Extraction (Next Step — Joe's directive)

1. Audit all ~75+ memory entries
2. Tag each: `universal` (Tekion-common, ship in Core) vs `amg` (store-specific, do not ship)
3. Extract universal entries into `jay-core-memory.json` with clean descriptions
4. Produce portable seed file that can be injected into a fresh Hermes profile
5. Estimated: ~50 universal entries out of ~75 total (~60%)

## Pitfalls

- Core memory must contain ZERO AMG identifiers — no dealer IDs, no store codes, no people names, no email addresses
- Credentials are ALWAYS manual setup — never baked into the deployable unit
- Instance memory grows organically just like Jay's did — the new owner teaches their clone their world
- A clone on a different machine needs its own persistent browser setup and cron jobs
- GBrain/session history can't be cleanly packaged (per-instance data) — the clone starts with a fresh brain