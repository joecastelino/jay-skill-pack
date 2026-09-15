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