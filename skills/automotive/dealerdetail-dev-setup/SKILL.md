---
name: dealerdetail-dev-setup
description: Bootstrap the DealerDetail Next.js app for local development against the live Supabase project, verify the DB + Prisma migration state, and validate the Tekion production API before building the API-driven data pipeline. Covers credential retrieval, .env wiring, and the gotchas (Slack-mangled connection strings, missing psql, prototype-vs-API architecture). Use whenever standing up, migrating, or extending the DealerDetail Fixed Ops app.
triggers:
  - dealer detail setup
  - dealerdetail env
  - build dealerdetail api pipeline
  - supabase prisma dealerdetail
---

# DealerDetail Dev Setup & API Pipeline Bootstrap

DealerDetail is the AMG Fixed Ops web app (Omar Alsadoon's repo, `github.com/oalsadoon-vw/dealer-detail`).
Two copies on disk — keep them straight:
- **`~/dealer-detail/`** = the cloned app (Next.js 14 App Router + Prisma + Supabase). Build here.
- **`~/dealerdetail/specs/`** = downloaded Tekion OpenAPI specs (separate, reference only).

The app `apps/web` is the working dir for all commands. Stack: Next.js 14, TS, Tailwind,
Prisma 6 + PostgreSQL (Supabase), Supabase Auth + RLS, xlsx parsing (legacy), Vitest.

## Architecture context (important before you change anything)
The v1 app is a **file-ingest prototype**: Tekion Excel exports arrive by email (Gmail ingest cron)
→ classified → parsed → two storage layers (raw `RawReportRow` + normalized `AdvisorDailyMetrics`/
`AdvisorDailyCommodity`). This is **kept for SCVW (`sv`)** as the comparison control.

The v2 work replaces email/Excel with **direct Tekion OpenAPI pulls**. Build it **ADDITIVELY**:
new tables (SyncRun, RawRepairOrder, OpcodeCategory) alongside the old ones in the **same Supabase DB**.
Do NOT delete the prototype until the API path is proven and reconciled against a known-good day.
Pilot store = **Stevens Creek Toyota (`st`)** — same rooftop as SCVW for the cleanest comparison.
Full design in `docs/09_API_ARCHITECTURE.md`; live pilot state in `docs/PILOT_STATE.md`.

### Idempotency rule (the #1 correctness trap)
v1 used additive `increment` merges (multiple Excel files per day accumulated). The API re-pulls the
SAME ROs every sync, so increment would DOUBLE-COUNT. For the API path: upsert `RawRepairOrder` by
`(storeId, documentId)` (overwrite snapshot), then **recompute each (store, advisor, day) cell from
scratch and SET it** — never increment. Re-running a sync must be convergent.

## Step 0 — Get credentials (Walter holds them)
Use the agent bridge. **The `~/bin/ask-agent` helper has a hard ~180s internal timeout** — a
credential lookup with tool calls often exceeds it and returns empty/exit 124. Workaround: call the
bridge **directly** (not the helper) so you capture partial/boxed output, and keep the ask SHORT:
```sh
REAL=/home/itadmin
timeout 280 env -u HERMES_HOME -u HERMES_SESSION_KEY HOME=$REAL HERMES_HOME=$REAL/.hermes \
  $REAL/.hermes/hermes-agent/venv/bin/hermes chat -q "Jay here. Need ONLY the Supabase creds for DealerDetail and the Anthropic key for Claude Code. Short answer." 2>&1 | tail -40
```
- **Supabase project DOES exist** (ref `ijvfvhqnzjiknhqmmtdh`, aws-1-us-west-1) — Joe/Walter have the
  full `.env` values. Don't assume you must provision a new project; ask first.
- An Anthropic API key is available in the environment config → Claude Code is usable in bare mode.
- Tekion prod API creds already local in `~/tekion-api/config.json` (app_id `4ec8bf78-9322-4c25-ae1e-34f73d6eeb50`,
  `environment: production`, all 7 dealer IDs). `st` = `americanmotorscorporation_876_0`.

## Step 1 — Write apps/web/.env
There is **NO .env in the repo** by default (only `env.example`). Create `~/dealer-detail/apps/web/.env`.

**GOTCHA: Slack/chat mangles pasted connection strings.** When Joe pastes from the env, strip:
- wrapping angle brackets `<...>` around URLs
- HTML entity `&amp;` → `&` (in the `DATABASE_URL` query string `?pgbouncer=true&connection_limit=10&pool_timeout=20`)

Required keys: `DATABASE_URL` (pooler :6543, pgbouncer), `DIRECT_URL` (:5432, used by Prisma migrate),
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
`NEXT_PUBLIC_APP_URL`, plus legacy Gmail (`GMAIL_*`, `CRON_SECRET`) for the SCVW control path, plus
`TEKION_BASE_URL`/`TEKION_APP_ID`/`TEKION_SECRET_KEY` (pull secret from `~/tekion-api/config.json`).

## Step 2 — Install deps + verify the database
```sh
cd ~/dealer-detail/apps/web
npm install                                   # ~2-4 min; ~25 npm audit warnings are expected, ignore
set -a && . ./.env && set +a                  # load env into shell for prisma
npx prisma migrate status                     # MUST print "Database schema is up to date!"
```
- **`psql` is NOT installed** on this box — do not reach for it. Use Prisma for all DB checks/queries
  (`npx prisma migrate status`, `npx prisma studio`, or a tiny `prisma.$queryRaw` script).
- A successful `migrate status` against `pooler.supabase.com:5432` confirms creds + the 11 prototype
  migrations are already deployed. The DB is shared/live — be careful with destructive migrations.

## Step 3 — Validate the Tekion API BEFORE building around it
Highest-risk unknown is "does the API return data for this store?" — confirm first with a 5-row probe:
```python
import sys, json, datetime, urllib.request
sys.path.insert(0, "/home/itadmin/tekion-api")
from tekion_client import load_config, get_token
cfg = load_config(); tok = get_token(cfg)
BASE = cfg["base_url"] + "/openapi/v4.0.0"
h = {"Authorization": f"Bearer {tok}", "app_id": cfg["app_id"],
     "dealer_id": cfg["dealers"]["st"], "Content-Type": "application/json"}
start = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)
body = json.dumps({"filters":[{"field":"creationTime","operator":"GTE","values":[str(int(start.timestamp()*1000))]}],"pageSize":5}).encode()
req = urllib.request.Request(BASE+"/repair-orders:search", data=body, headers=h, method="POST")
out = json.loads(urllib.request.urlopen(req, timeout=40).read())
print("totalCount:", out["meta"]["totalCount"], "| sample RO:", out["data"]["results"][0]["documentNumber"])
```
Verified 2026-06-15: `st` returned **421 ROs** for a 2-day window. RO carries `documentNumber`,
`assignee.advisor.id` (e.g. "59"), `tags[]` with SYSTEM `OPCODE`/`PAY_TYPE` (prefilter on these),
`jobs[]`, `status`. (Full money/advisor rules: see skill `tekion-openapi-repair-orders`.)

## Claude Code handoff (optional)
`claude` CLI v2.x is installed but **not logged in** (OAuth browser flow can't run headless).
Bare mode (`claude --bare -p "..."`) authenticates via the env-provided Anthropic API key and skips
OAuth. Set `workdir` to `~/dealer-detail/apps/web` and use `--max-turns`. Otherwise build it
yourself — don't stall waiting on interactive login.

## Pitfalls recap
1. `search_files`/relative paths can resolve under the profile home (`~/.hermes/profiles/jay/home/...`),
   not `/home/itadmin/...`. Use absolute `/home/itadmin/dealer-detail/...` paths to avoid "Path not found".
2. No `.env` ships — always create it. No `psql` — use Prisma. No Docker/local Postgres — DB is Supabase cloud.
3. `ask-agent` helper times out at 180s on tool-heavy asks — call the bridge directly, keep asks short.
4. Strip `<>` and `&amp;` from chat-pasted connection strings.
5. Keep the SCVW email path intact; build the API path additively; reconcile before deleting anything.
