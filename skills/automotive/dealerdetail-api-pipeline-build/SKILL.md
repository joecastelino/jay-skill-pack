---
name: dealerdetail-api-pipeline-build
description: Build the DealerDetail Tekion API-driven data pipeline (replacing the email/Excel prototype) by acting as PM and delegating tickets to Claude Code, then verifying independently. Covers the ticket workflow, the live infra (Supabase project, branch, creds), and the hard-won gotchas (Supabase shadow-DB, server-only smoke tests, git credential path, Tekion app-scope 403 on user lookups).
triggers:
  - dealerdetail api pipeline
  - tekion api pipeline build
  - dealer-detail collector
  - advisor metrics from api
---

# DealerDetail Tekion API pipeline — build workflow

## Goal & approach (locked with Joe 2026-06-15)
Replace the fragile Excel/email ingestion with a Tekion OpenAPI pipeline that pulls + aggregates
advisor service metrics and **wires into the EXISTING dashboard** (NOT a new dashboard — same UI,
new data source). Pilot ONE Toyota store (Stevens Creek Toyota, `st`) on the API path while SCVW
(`sv`) stays on the email path as the control, for side-by-side comparison. ADDITIVE only — do not
delete the prototype until the API path is proven and reconciled.

Joe wants Jay to act as **project manager**: write small, tightly-scoped tickets, feed them to
**Claude Code** one at a time, push to GitHub. Joe values production-grade, safe, scalable code.

## Repo / infra facts
- Repo: `~/dealer-detail` → github.com/oalsadoon-vw/dealer-detail (owner Omar; Joe=joecastelino has
  write access). App is `apps/web` (Next.js 14 App Router, Prisma 6, Supabase, Vitest).
- **Live on Vercel from `main`** → NEVER push experimental work to main. Use branch
  `feature/tekion-api-pipeline`. Open PR to main only after the pilot is proven.
- **Supabase project EXISTS**: ref `ijvfvhqnzjiknhqmmtdh` (aws-1-us-west-1). All creds + the
  prototype schema (11 migrations) are already deployed. Connection values live in `apps/web/.env`
  (Jay wrote it from values Joe pasted; DATABASE_URL=pooler:6543, DIRECT_URL=direct:5432).
- Tekion PROD API creds in `~/tekion-api/config.json` (app_id 4ec8bf78..., all 7 dealer IDs).
  ST dealer_id = `americanmotorscorporation_876_0`. Mirrored into `.env` as TEKION_BASE_URL/
  TEKION_APP_ID/TEKION_SECRET_KEY. Python reference client: `~/tekion-api/tekion_client.py`.
- Architecture spec: `docs/09_API_ARCHITECTURE.md`. Live project state: `docs/PILOT_STATE.md`.
  Tickets: `docs/tickets/T*.md`.

## Ticket plan (6 tickets, sequential, each verified before the next)
- T1 ✅ Additive Prisma schema: SyncRun, RawRepairOrder, OpcodeCategory; Store.tekionDealerId/
  apiSyncEnabled; Advisor.tekionUserId.
- T2 ✅ Server-only Tekion client library (`lib/sources/tekion/`): client.ts, throttle.ts,
  money.ts, types.ts. Smoke test proves live data.
- T2b ✅ Pluggable advisor resolver (`lib/sources/tekion/advisors.ts`): browser-interim path +
  API-production stub, switched by env `TEKION_ADVISOR_RESOLVER`. Resolves id→name LIVE.
- T7 ✅ (2026-06-18) Joe upgraded the app API scope → public `GET /openapi/v4.0.0/users/{id}` now
  resolves names server-to-server, so the browser resolver is RETIRED as default (still available via
  `TEKION_ADVISOR_RESOLVER=browser`). This makes the collector Vercel-deployable (no localhost:9223
  needed). Three bugs fixed in `lib/sources/tekion/client.ts`: (a) `USER_PATH_PREFIX` was the INTERNAL
  browser path `/userservice/u/apc/users` → changed to `${OPENAPI_PREFIX}/users`; (b)
  `extractUserDisplayName` read top-level `data.firstName/lastName` which DON'T EXIST — real OpenAPI
  shape is `data.userNameDetails.completeNames[nameType==='DISPLAY_NAME'].value` (fallback
  `userNameDetails.firstName + ' ' + lastName`); (c) an unknown id returns **HTTP 400
  `{code:"no.user.found"}`** NOT 404 — `resolveUserDetailed` now swallows both → null. Default kind in
  `detectKind` flipped browser→api; `.env` sets `TEKION_ADVISOR_RESOLVER=api`. Added
  `tests/tekion-advisors.test.ts` + `resolve.conditions:["react-server"]` in vitest.config.ts so the
  server-only client is unit-testable (gotcha #2 in config form). VERIFIED LIVE (dealer 876, no
  browser): 74→Brian Keat, 61→Jon Vu, 58→Sylvester White, bogus→null; 17/17 tests pass, tsc clean.
  Resolver gets the LONG dealerId (`americanmotorscorporation_876_0`) — the collector passes it as
  `dealerId: tekionDealerId`; no `TEKION_DEALER_ID` env needed for the collector path.
- T3 ✅ Collector (`lib/sources/tekion/collector.ts` + `scripts/collect-st.ts`, npm `collect:st`):
  paginated repair-orders:search → bounded-concurrency (4-6) fan-out to jobs/operations/parts →
  assemble nested snapshot {ro,jobs[{operations[{parts}]}],vehicle,advisorName} → upsert
  RawRepairOrder by unique (storeId,documentId) with sha256 contentHash change-detection
  (unchanged ROs skip the write = idempotent) → resolve advisor via T2b, upsert Advisor
  (name+tekionUserId) → derive businessDate (closeDate else creation, midnight UTC) → wrap in
  SyncRun (RUNNING→COMPLETED/COMPLETED_WITH_WARNINGS/FAILED + summary). Per-RO try/catch never
  aborts the run. VERIFIED: 142 real ST ROs (0 dupes) + 24 advisors with real resolved names.
- T3b ✅ Hardening: signal-safe SyncRun finalize (SIGINT/SIGTERM → FAILED, not stuck RUNNING) +
  stale-run reaper (self-heals orphaned RUNNING rows at start of each run) + final `=== RESULT ===`
  print block. VERIFIED live: reaper test, SIGTERM kill test, 0-dupe idempotency under killed runs.
  (See gotcha #6.)
- T4 ✅ Aggregator (`scripts/seed-opcode-categories.ts` npm `seed:opcodes` + `lib/aggregate/`\n  opcodeClassifier.ts + aggregator.ts + `scripts/aggregate-st.ts` npm `aggregate:st`): pure DB→DB,\n  RawRepairOrder.payload → AdvisorDailyMetrics + AdvisorDailyCommodity (the SAME tables the email\n  dashboard reads — zero UI change). Classify opcode via OpcodeCategory (store override beats\n  storeId=NULL global). gross=(sale−cost)/100 cents→DOLLARS (email tables are Float dollars; ST must\n  match SCVW units). **DELETE-then-INSERT per recomputed (storeId,businessDate) in a txn = idempotent\n  SET, NOT increment** (API re-pulls same ROs). VERIFIED: 117 metrics + 224 commodity rows / 26 dates,\n  2nd run byte-identical checksum. (See gotchas #9 #10 #11.)\n- T4b ✅ Count-semantics fix: menuCount/alaCount = DISTINCT-RO penetration (not line-items) +\n  populate openRos. (See gotcha #11 — this was the important course-correction.)\n- T5 ✅ Consolidate onto the REAL store (gotcha #13) + manual sync endpoint
  `app/api/sync/[storeId]/route.ts` (POST: auth like ingest/runs routes, validate
  apiSyncEnabled+tekionDealerId, collect→aggregate) + host trigger `scripts/sync-st.ts` (npm `sync:st`).
  Two route GUARDS that matter: (a) SERVERLESS guard — return 501 if `process.env.VERCEL` or
  `TEKION_ADVISOR_RESOLVER==='browser'` (the browser advisor resolver only works on the collector
  HOST, not Vercel serverless — the route is correct for when the API resolver is enabled but must
  not pretend to work deployed); (b) CONCURRENCY guard — return 409 if a non-stale SyncRun is already
  RUNNING (protects the 429 budget from double pulls). VERIFIED: 1 SCT store, 163 ROs, 0 orphans, KPIs
  intact under real store, SCVW untouched.
- T6 ✅ Wire SCT (API) into the EXISTING dashboard next to SCVW (email). KEY FINDING: the dashboard
  read path (`lib/server/services/dashboard.ts` + `app/api/dashboard/route.ts`) is ALREADY
  store-agnostic — it reads AdvisorDailyMetrics/AdvisorDailyCommodity for any storeId with NO
  email-specific assumptions, and store visibility is gated by `tc.org.accessibleStoreIds` +
  organizationId (all 3 AMG stores share org 160d1964...). So SCT renders as soon as it's selectable —
  T6 is SMALL/ADDITIVE, not a build. Real fixes: (a) API stores have `run: null` (no IngestionRun, not
  file-sourced) → ensure ui.tsx + page handle null run in BOTH day & range views without crashing;
  (b) rec display: recAmount=0 makes recClosingPct render a misleading "0%" → make it GENERIC
  "denominator 0 → show '—'/N-A neutral + subtext 'pending Tekion API'" (NOT hardcoded to SCT, so SCVW
  keeps its real %); (c) small API-vs-Email source badge (run===null && metrics exist → "API").

## PR to main / production deploy (2026-06-19)
After T7, the branch `feature/tekion-api-pipeline` was opened as **PR #1 → main**
(https://github.com/oalsadoon-vw/dealer-detail/pull/1) — 11 commits = the FULL T1–T7 pipeline,
mergeable:clean, Vercel preview check passed, 17/17 tests + tsc clean.
- **NO `gh` CLI on this box** — create PRs via GitHub REST API: `POST /repos/oalsadoon-vw/dealer-detail/pulls`
  with the token from `~/.git-credentials` (Authorization: token <pat>). Check mergeability via
  `GET /repos/.../pulls/1` (`mergeable`, `mergeable_state`) and CI via `GET /commits/<sha>/check-runs`.
- **HOLD the final merge for Joe's explicit go** — merging auto-deploys 11 commits to PROD (Omar's repo,
  main→Vercel). Open the PR review-ready, then wait. This is the one decision NOT to make unilaterally.
- **CRITICAL post-merge reality**: merging makes the dashboard READ path + API store visibility live, but
  the nightly COLLECTION is NOT wired — the collector runs from THIS host (sync route guarded to 501 on
  Vercel by design, gotcha T5). After merge, SCT shows only data the host collector has already loaded.
  Fast-follow = a nightly SCT collector host cron (not yet built). Flag this to Joe with the merge offer.

### MERGED 2026-06-19 (Joe said "merge it")
The 11 commits were fast-forward-merged to `main` and pushed (`99a9cd7..e881bd6`). It was a CLEAN
FF — branch was 11 ahead / 0 behind main, working tree clean, zero conflicts possible. Mechanics that
worked: `git checkout main && git pull --ff-only origin main && git merge --ff-only
feature/tekion-api-pipeline && git push origin main` (the repo already had credential.helper pointed at
/home/itadmin/.git-credentials from the build — gotcha #3). The feature branch was left intact (not
deleted) pending Joe's word.
- **Two things to flag at merge time, EVERY time:** (1) main→Vercel is now DEPLOYING, and the bundle
  includes a NEW Prisma migration (`add_tekion_api_pipeline`) — if prod migrations don't auto-run on
  deploy, the new tables won't exist and SCT dashboard/sync routes will 500. (2) The nightly collector
  cron is STILL not wired (see below), so post-merge SCT data only refreshes when the host collector is
  run manually.

## POST-MERGE OPERATIONS / AUDIT (2026-06-19 — "double-check the numbers + names")

When Joe asks to verify the pipeline is "pulling the right data" / "the numbers are accurate" / spots an
"Unassigned" advisor, run this audit loop. Findings below are EXPERIENTIAL — re-confirm against live each
time, but these patterns recur.

### Quick DB-audit script (reusable)
Write `apps/web/_audit.ts` and run `set -a && . ./.env && set +a && npx tsx --conditions=react-server
./_audit.ts` (then `rm` it). Schema gotchas that bit me:
- **Advisor has NO `name` field** — it's `nameRaw` + `nameNormalized` (a `name` select throws
  PrismaClientValidationError listing the real fields). Filter suspicious rows on `nameRaw`.
- **Import path is RELATIVE to the file's location**: scripts in `scripts/` use `../lib/db`; a file at the
  `apps/web` ROOT uses `./lib/db`. Wrong path → `ERR_MODULE_NOT_FOUND .../apps/lib/db`.
- The three library.d.ts `TS18028 private-identifiers` lint warnings are HARMLESS for tsx execution — ignore.
What to dump: stores (id/abbrev/tekionDealerId/apiSyncEnabled), advisors (nameRaw/tekionUserId), SUSPICIOUS
names (`/unassigned|any service|null|undefined|^advisor #/i.test(nameRaw) || !nameRaw`), metrics aggregate
(sum menuCount/alaCount/openRos/dailyLaborGross + date range), raw RO `distinct==total` check, and the
LATEST SyncRun (status/startedAt — catches orphaned RUNNING + staleness).

### Recurring finding #1 — a `null`-named advisor is a STALE NAME, not a real Unassigned bucket
A row with `nameRaw=null` (or "Unassigned") carrying real volume means the collector resolved that
`assignee.advisor.id` BEFORE the scope upgrade (or hit a transient error on that one id). To diagnose: take
the `tekionUserId` straight to the live `/users/{id}` (see skill tekion-openapi-repair-orders ⭐ section).
2026-06-19: `ee31e3e9-bba5-4868-8ead-a2464c95eab1` resolved to **Angel Gutierrez, SERVICE_ADVISOR, active**
— it was the long-known mislabeled UUID, just persisted as null this time. The FIX is simply to RE-RUN the
collector (the upgraded api resolver now names it); no code change. Joe will reject any "Unassigned" on a
closed-RO advisor breakdown — every closed RO has a real assignee that now resolves.

### Recurring finding #2 — `persona` is NOT always SERVICE_ADVISOR
`/users/{id}` returns `userRoleDetails.primaryRole.persona`. Several RO assignees are
**WARRANTY_CLERK / CASHIER / SERVICE_MANAGER / TECHNICIAN**, not advisors (2026-06-19 SCT: Lisa
Rodriguez=WARRANTY_CLERK, Jasmine Perez=CASHIER, Sylvester White=SERVICE_MANAGER). They legitimately appear
as the RO assignee but may not belong in an *advisor-performance* breakdown. Flag this to Joe and offer to
filter the breakdown to `persona == SERVICE_ADVISOR`.

## T8 ✅ — Advisor persona split + \"Others\" bucket (BUILT 2026-06-19, merged to main)
Joe's call on finding #2: keep all roles' DATA (revisit later) but render only SERVICE_ADVISOR as
advisors and dump every other persona into a new **\"Others (non-advisor roles)\"** dashboard section.
Implemented DIRECTLY with file tools (Claude Code CLI hung — see claude-code-headless-jay; don't burn
time retrying a hung invocation, just do the edits when you have full context). The persona flows
**API → DB → dashboard**, end to end:
1. **Schema**: `persona String?` added to `Advisor` (additive). Migration via the shadow-DB-bypass
   pattern (gotcha #1): `prisma migrate diff --from-url=$DIRECT_URL ... --script` → single
   `ALTER TABLE \"Advisor\" ADD COLUMN \"persona\" TEXT;` → `prisma migrate deploy` → `prisma generate`.
2. **client.ts**: `userPersonaCache` + `extractUserPersona(raw)` reads `data.userRoleDetails.primaryRole.persona`;
   `resolveUserDetailed()` return shape is `{ name, persona, sourceField, raw? }`.
3. **advisors.ts**: resolver `.resolve()` now returns `ResolvedAdvisor {name,persona}`; browser resolver
   returns `{name, persona:null}`; **kept `resolveAdvisorName()` back-compat helper** (unwraps `.name`)
   so nothing else breaks.
4. **collector.ts AND aggregator.ts BOTH persist persona** — the aggregator independently re-derives
   Advisor rows via its own `ensureAdvisorId()`, so if you only set persona in the collector the
   aggregator silently nulls it back out. Thread `advisorPersona` through the RO snapshot (types.ts) and
   pass it into `ensureAdvisorId(persona)`.
5. **dashboard.ts service**: `DashboardAdvisor.persona` + new `DashboardData.others[]`; partition
   `allAdvisors` → `advisors` (persona===\"SERVICE_ADVISOR\") vs `others` (everything ELSE, **including
   null**). CAVEAT: email-sourced advisors (SCVW/ARSJ) have null persona and currently fall into Others —
   if SCT-only this is fine, but if you wire the split for an email store, change the predicate to
   `persona===\"SERVICE_ADVISOR\" || persona==null` or gate the split by source.
6. **ui.tsx**: render an \"Others (non-advisor roles)\" section (only when `data.others?.length>0`) with a
   role badge via `formatPersona()`; metrics preserved, nothing dropped (so the data stays revisitable).
Verify: `npx tsc --noEmit` exit 0 + `npx vitest run` 17/17. Merge = FF to main = Vercel prod deploy
(includes the new migration — flag that prod migrations must auto-run or routes 500).

### T8 GOTCHA A — duplicate ADVISOR by stale name (distinct from gotcha #13's duplicate STORE)
A single `tekionUserId` can produce TWO Advisor rows because `@@unique([storeId, nameNormalized])` keys
on the NAME, not the user id. Pre-scope-upgrade the collector stored the assignee as null →
`nameNormalized=\"UNASSIGNED\"`; post-upgrade it resolved the real name → `nameNormalized=\"ANGEL GUTIERREZ\"`.
Both coexist (different normalized names) with the SAME `tekionUserId`, splitting that advisor's metrics
across two rows. 2026-06-19: Angel Gutierrez (`ee31e3e9-bba5-4868-8ead-a2464c95eab1`) had a named row
(06-17/06-18 metrics) AND an \"UNASSIGNED\" ghost (06-15 metrics + tires commodity). FIX = reparent then
delete, in a txn:
- Check for date COLLISION first: `AdvisorDailyMetrics` is unique on `(storeId,advisorId,businessDate)`
  and commodity on `(...,commodityKey)`. If the two rows share a businessDate, a reparent UPDATE will
  violate the constraint — in that case delete the OLDER (pre-upgrade) metric, keep the named row's.
- No collision (the common case): `advisorDailyMetrics.updateMany({where:{advisorId:ghostId},data:{advisorId:namedId}})`
  + same for `advisorDailyCommodity`, then `advisor.delete({where:{id:ghostId}})`. Wrap in `$transaction`.
- The named row is authoritative (post-scope-upgrade). After merge: zero null-name advisors, one row per id.
PREVENTION: re-running the collector with the upgraded resolver names the assignee correctly going
forward, but it does NOT auto-merge the legacy ghost — you must dedup once. Better long-term key would be
`@@unique([storeId, tekionUserId])` but that's a bigger migration (email advisors have null userId).

### T8 GOTCHA B — persona BACKFILL of existing rows + the drained-bucket 429 trap
Adding the persona column does NOT populate it for advisors already in the DB — they stay null until a
collector re-pull re-resolves each user. A full `sync:st` re-pull is the heavy way (and over-budgets 429
on a 7-day window — gotcha #5). The LIGHT way: a users-ONLY backfill script that loops the 21-ish advisors
with a `tekionUserId`, calls `client.resolveUserDetailed(dealerId, userId)`, and writes `persona` (+
backfills `nameRaw` if it was null). That's only ~21 calls — well under budget — EXCEPT:
**TRAP**: if you JUST killed a big 7-day run, the Tekion-side token bucket is still drained, so even a
21-call backfill spends every call in 429 backoff and a 180s foreground run times out with ZERO rows
written (the client's token-bucket throttles US but doesn't know the Tekion window is already exhausted —
same root as gotcha #5). FIX: either wait ~15 min for the window to reset, OR launch the backfill as
`terminal(background=true, notify_on_complete=true, watch_patterns:[\"updated=\",\"FAIL\"])` and DON'T block —
it grinds through backoff and notifies on completion. The backfill script must live INSIDE `apps/web`
(`apps/web/_persona_backfill.ts`) and run with `npx tsx --conditions=react-server` (gotchas #2 #7) — a
bare `.mjs` in /tmp fails with TransformError / ERR_MODULE_NOT_FOUND. Verify after: query advisors,
assert `persona` populated count and zero remaining null names; until it lands the live dashboard dumps
EVERYONE into \"Others\" (no row is yet tagged SERVICE_ADVISOR), so don't report the split as working until
the backfill confirms.

## MULTI-STORE ROLLOUT (2026-07-02, branch feature/multi-store-api — Joe: "all stores on the API path")
All 7 AMG stores are now API-synced; SCVW was SWITCHED OFF the email path (Joe's call — the email/Excel
"control" comparison is over). Key pieces:
- **`npm run seed:stores`** (`scripts/seed-amg-stores.ts`): idempotent upsert of all 7 stores under the
  AMG org, matching EXISTING stores by abbreviation (+aliases BT→BST, TL→TOL, VC→VWC) so the
  duplicate-store trap (gotcha #13) can't recur; guards against a dealerId claimed by a different store.
  Store rows: SCT=1314a22f, SCVW=ea3f47be, ARSJ=b9044b35, BST=97679ffc, BC=70be1c49, TOL=4f001a04,
  VWC=d41af666. Dealer IDs from ~/tekion-api/config.json (876/826/6195/1249/1251/1092/1891).
- **`npm run sync:store -- <ABBREV> [days]`** (`scripts/sync-store.ts`): generalized per-store sync;
  exports `syncStore()` for reuse. sync-st.ts kept for back-compat. GOTCHA: CollectResult has
  `created/updated/unchanged` at TOP LEVEL, not under `.summary` (tsc caught this).
- **`npm run sync:all`** (`scripts/sync-all.ts`): sequential all-stores loop, per-store try/catch
  (one bad store never blocks the rest), inter-store cooldown default 240s (Tekion 1500/15min budget
  is APP-WIDE across all dealers — same lesson as the VI scraper). Env: SYNC_WINDOW_DAYS,
  SYNC_COOLDOWN_SECONDS, SYNC_STORES=CSV subset. Nightly cron script now runs sync:all.
  Backfill recipe: SYNC_WINDOW_DAYS=14 SYNC_COOLDOWN_SECONDS=600 SYNC_STORES=<new stores> in
  background with notify_on_complete (~2h for 6 stores).
- **BRAND-AGNOSTIC MENU CLASSIFICATION** (the key design win): Tekion factory menu-package opcodes
  follow `TEK<mileage><B|P|V><N|S>M` (TEK15000BNM, TEK100000VNM, TEK90000PSM) on EVERY make — verified
  identical 212-opcode SERVICE_MENU sets at BC (Chevrolet) and TOL (Toyota) from
  ~/tekion-reports/data/{bc,tl}-menu-opcodes.json. classifyOpcode() now falls back to regex
  `/^TEK\d{4,6}[BPV][NS]M$/` → MENU when no DB mapping exists; DB rows (store override > global) still
  win. Pattern is deliberately narrow so à-la-carte factory ops (TEK07120301, 8-digit ids) do NOT
  match. Result: SCT menu% 78.26→79.71 same day. Also seeded: BG* fluid services→ALA,
  1TIRE/2TIRE/FLAT→tires, ADBRAKE→brakes, TAC55/TXM10KMIRAI/TXM15K86→MENU.
- **DOUBLE-COUNT GUARD for switched stores**: email ingest uses INCREMENT semantics, the API aggregator
  uses DELETE-then-INSERT — both writing one store double-counts. Two-layer fix: (a) `ingestFiles()`
  (lib/ingest.ts) THROWS for any store with apiSyncEnabled=true; (b) the gmail-ingest cron SKIPS
  attachments routed to API stores BEFORE calling ingestFiles (and still marks the email ingested) —
  without (b) the throw would wedge the message in an unprocessed retry loop forever. Report Builder
  emails keep flowing; they're just ignored.
- Dashboard needs NO change for new stores: org-admin accessibleStoreIds enumerates all stores in the
  org (T6 finding still holds). New stores render as soon as they have metrics.
- Expect fresh unclassified-opcode lists from non-Toyota stores (Chevy/VW/Alfa à-la-carte codes differ);
  surface them to Joe — the taxonomy is his call.

### Multi-store BACKFILL OUTCOME (2026-07-03) + operational gotchas
All 7 stores 14-day backfilled and current, 0 dupes, 0 null-name advisors. Raw RO volumes (14d):
BST 1868, TOL 1778, BC 967, SCT 817, SCVW 359, VWC 322, ARSJ 51. Branch still NOT merged —
Joe holds the merge call (merge → Vercel prod deploy).
- **Supabase drops connections mid-bulk-write**: Prisma `Connection reset by peer` (os error 104)
  during a big collect → run still exits 0 but `fetched > created` (BST: 1814 fetched / 1732 created,
  ~82 ROs lost). NOT fatal — upserts are idempotent; just re-run `sync:store -- <ABBREV> 14` to fill
  holes, then verify raw count + distinct==total. ALWAYS compare fetched vs created+updated+unchanged
  in the summary; a gap = dropped writes.\n- **Budget contention rule**: never run manual backfills during the 1:30–4 AM nightly-cron window —
  the 1500/15min budget is app-wide, so an overlapping manual run starves the cron into 429 FAILED
  runs (they degrade gracefully per-store, but it wastes a night).
- **LOW MENU% AT NON-TOYOTA STORES — AUDIT DONE 2026-07-04, awaiting Joe's taxonomy ruling**:\n  executed the plan (audited all 7 stores' RawRepairOrder payloads 14d + pulled official opcode\n  catalogs for BST/SCVW/VWC/ARSJ via the authenticated XHR method; BC/TOL catalogs already existed).\n  KEY FINDING: **ZERO unclassified opcodes are SERVICE_MENU type in Tekion** — all 590 unclassified\n  are INDIVIDUAL_SERVICE; the TEK regex already catches every real factory menu. So VWC 0%/SCVW\n  7.5%/BC 10.5% menu% is a TAXONOMY DECISION, not a classification bug. 590 opcodes bucketed into\n  Q1–Q6 proposal groups in `APPROVAL-consolidated.csv` + per-store CSVs (nothing seeded):\n  Q1 factory prepaid maint (ToyotaCare TEK09xxxxxx/TAC10, VW CareFree 10KCF/20KCF, VW Care 01xxxxxx)\n  64 ops/$187K; Q2 store packages (PORT*, K1, 995, LOF4CYL/LOF6, GMLOF*, ROADREADY) 25 ops/$108K;\n  Q3 commodity à-la-carte 81/$203K; Q4 repair/diag (REC/CONCERN/DIAGNOSTIC/RECALL) 59/$768K;\n  Q5 housekeeping/internal (TPS/SURVEY/FLOORMAT/PDI…) 100 ops/11,741 ROs/$220K → ignore-candidates;\n  Q6 misc 261/$271K needs line-by-line. Q1+Q2 = the decisions that move menu%. **Do NOT seed until\n  Joe rules on the buckets**; after approval: seed → re-aggregate all 7 → verify checksums → then\n  merge feature/multi-store-api to main (merge = Vercel prod deploy, Joe's call).\n- **TOKEN-RETRY HARDENING (commit ac4ecc7, 2026-07-04)**: nightly sync-all had lost stores to\n  transient Tekion token errors (HTTP 400 on token fetch). Fixed two layers: (a) token fetch in the\n  client retries 3× with backoff 5s/15s/45s on transient 400s/network errors; (b) sync-all does a\n  SECOND-CHANCE pass over any store whose sync failed with a token/auth-class error. 28/28 tests,\n  tsc clean. Rate-limit (429 mid-collect) failures still degrade gracefully per-store as before.

### Recurring finding #0 — the nightly cron SILENTLY NO-OPs if the log dir is missing (hit 2026-07-02)
The crontab line redirects `>> ~/dealer-detail/logs/sct-sync-nightly.log` but the shell redirect is
evaluated BEFORE the script runs — if `logs/` doesn't exist (it's gitignored/never committed), the
redirect fails and cron silently skips the job EVERY night. The script's own `mkdir -p "$LOG_DIR"`
never gets a chance to fix it. Result: pipeline dead June 19→July 2 (13 days stale) with zero errors
anywhere. FIXED: crontab line now starts `mkdir -p /home/itadmin/dealer-detail/logs && flock ...`.
When auditing staleness, check `ls ~/dealer-detail/logs/` FIRST — an absent log file = cron never ran,
not "ran and logged nothing". Recovery = one 14-day backfill run (`COLLECT_ST_WINDOW_DAYS=14`,
background + notify; ~392 ROs, completed without rate-limiting).

### SITE-ACCURACY AUDIT 2026-07-08 (fixedopsreports.com — \"the numbers are wrong\") — three root causes
**fixedopsreports.com = this app's prod Vercel deploy** (redirects to www; deploys from `main`). When Joe
says the site's numbers are off, run this audit (throwaway `apps/web/_audit*.ts` scripts via
`npx tsx --conditions=react-server`, then rm). Findings — these are STRUCTURAL, re-check all three:
1. **MENU TAXONOMY INFLATION (biggest)**: the seeded OpcodeCategory maps TXMPLUS/TXMBASIC/TSC*/TAC*
   (prepaid/express maintenance) → MENU. Joe's scorecard definition of \"menu\" = factory SERVICE_MENU
   opcodes ONLY (`TEK\d{4,6}[BPV][NS]M`). SCT July MTD: site menuCount=551 ROs vs 36 real TEK menu
   lines vs 34 on my closed-MTD scorecard — **~15x inflated**, TXMPLUS alone = 486 lines. Fix awaits
   Joe's taxonomy ruling (the Q1–Q6 buckets from the 2026-07-04 audit): strict TEK for the menu KPI,
   prepaid as its own bucket. To quantify: load OpcodeCategory (store override > global), walk July
   RawRepairOrder payloads, count lines per MENU-classified opcode, split DB-mapped vs regex-only.
2. **FROZEN-STATUS / creationTime-window bug**: the collector windows on `creationTime` (3d), so an RO
   closing >3 days after creation is NEVER re-pulled — its snapshot status freezes \"open\" forever
   (2026-07-08: SCT 201, BC 149, TOL 140, BST 133 phantom-open ROs). Also **closeDate is NULL on 100%
   of rows** — repair-orders:search payload carries no closedTime/invoicedTime, so deriveBusinessDate
   silently falls back to creationTime (closed work is dated by CREATED date). Fix: wire
   `dateField: \"modifiedTime\"` (collector already supports it, sync scripts never pass it) + one 14-day
   modifiedTime backfill to heal frozen rows; derive closeDate from modifiedTime-on-CLOSED or ro-invoices.
   Detection query: count rows where openDate < now-4d AND status NOT IN (CLOSED, INVOICED).
3. **NIGHTLY QUOTA COLLISION**: dealer-detail sync-all (1:30 AM) and the VI inventory pull (2 AM)
   share the app-wide Tekion budget; when OVERALL_QUOTA is drained (e.g. after a stuck-consumer
   incident) BOTH bleed out — 2026-07-08 all 7 stores pulled ros=0 \"(rate-limited, partial)\" and all
   7 VI stores FAILED. Result: stores go days stale (ARSJ/VWC were 5 days behind) and \"current\" days
   are PARTIAL (SCT 7/05 captured 100 of ~200 ROs) → MTD totals mechanically low. Fix: stagger the
   crons (move sync-all off the VI window) + probe quota and SKIP gracefully instead of retry-burning.
   Read the sync log summary lines: `ros=0 ... (rate-limited, partial)` across all stores = drained night.
Also: dashboard \"openRos\" = distinct ROs written per advisor/day (penetration denominator), NOT
currently-open ROs — if the site labels it \"Open ROs\" it misleads; rename or compute true opens from
live status (which requires fix #2 first or the frozen statuses inflate it by hundreds).
Acceptance test after fixes: re-aggregate, then diff site menu numbers vs my SCT/TOL/BC menu-closed
scorecard JSONs in ~/tekion-reports/data/ (`*-menu-sales-closed-*.json`, rows/totals) — match RO-for-RO.

### "SITE NUMBERS ARE WRONG" AUDIT (fixedopsreports.com, 2026-07-08) — the 3 compounding root causes
fixedopsreports.com = this app on Vercel. When Joe says "menus/open ROs are way off," run this diagnosis
(all three were true simultaneously; fixes in commit `1f44dcc` on feature/multi-store-api):
1. **MENU TAXONOMY MISMATCH (biggest)**: old seeded OpcodeCategory rows classify TXMPLUS/TXMBASIC/TSC*/TAC*
   (prepaid/express maintenance) as MENU. SCT July MTD showed 551 "menu ROs" on the site vs 34 on my
   known-good closed-MTD scorecard (strict SERVICE_MENU TEK-opcode definition) — TXMPLUS alone = 486 lines,
   only 36 lines were real TEK menus. ~15x inflation. Fix awaits Joe's taxonomy ruling (strict TEK menus
   for the menu KPI, prepaid as its own bucket = my recommendation). Audit method: pull RawRepairOrder
   payloads for the period, classify ops the way the aggregator does (DB map + TEK regex), split DB-mapped
   vs regex-only counts, compare to the scorecard JSON in ~/tekion-reports/data/.
2. **creationTime WINDOWING FROZE STATUSES**: the collector windowed on creationTime (3d), so any RO
   closing >3d after write-up NEVER got re-pulled — status frozen "open" forever (~620 phantom-open ROs:
   SCT 201, BC 149, TOL 140, BST 133). Plus `closeDate` was NULL on 100% of rows (Tekion returns
   closedTime/invoicedTime null in the search payload) → closed work dated by CREATION date, misaligning
   every closed-period comparison. FIXES: (a) sync-store now windows on **modifiedTime** by default
   (env SYNC_DATE_FIELD overrides) — a close event bumps modifiedTime so the RO gets re-captured;
   (b) collector `deriveCloseTime()`: explicit closedTime/invoicedTime else modifiedTime IF status is
   CLOSED/INVOICED, else null; businessDate follows it; (c) a LIGHT-REPAIR update path fires when the
   payload hash is unchanged but derived closeDate/businessDate are stale (heals legacy rows);
   (d) collector returns `touchedBusinessDates` (incl. the OLD date when an RO moves buckets) and
   sync-store merges them into the re-aggregation set — without this a moved RO double-counts.
3. **NIGHTLY QUOTA COLLISION**: the 1:30AM sync-all and 2AM VI pull share the app-wide OVERALL_QUOTA;
   when either retry-burns a drained bucket, BOTH starve (7/8: all 7 stores pulled 0 ROs; ARSJ/VWC went
   5 days stale). FIXES: sync cron moved to **11 PM**; `scripts/tekion-quota-probe.py` (1-call
   repair-orders:search probe, exit 0/1) gates cron-sct-sync.sh — probe, sleep 20m up to 2h, then SKIP
   gracefully instead of digging the hole. Reusable heal pattern: `scripts/heal-backfill-20260708.sh` =
   probe-wait loop (up to 8h) then SYNC_WINDOW_DAYS=14 SYNC_COOLDOWN_SECONDS=420 sync:all in background.
Also: dashboard "Open ROs" relabeled **"RO Count"** (it's distinct ROs written — a penetration
denominator — NOT currently-open ROs; the data key stays `openRos`). VERIFICATION standard: after
healing + re-aggregation, diff site metrics vs the scorecard JSONs (sct/tol/bc-menu-sales-closed-*.json)
RO-for-RO for the same period.

### Recurring finding #3 — STALENESS is the bigger bug than any single name
The audit's most valuable output is the latest SyncRun. 2026-06-19 it was stuck `RUNNING` (rosFetched=0)
from June 16 — so the dashboard had been serving 3-day-old numbers because **NO nightly collector cron is
wired** (the long-flagged fast-follow). Reap the orphan
(`prisma.syncRun.updateMany({where:{status:'RUNNING'},data:{status:'FAILED',finishedAt:new Date(),...}})`),
then re-sync. THE STANDING RECOMMENDATION: wire a nightly host-side `npm run sync:st` cron (1 AM per Joe's
schedule) — without it SCT goes stale silently. Until that's built, "accuracy" audits will keep finding
stale data, not wrong math.

### Re-sync mechanics + the 7-day-window 429 trap
`npm run sync:st` = collect→aggregate in one shot. The collector default window is **3 days**
(`COLLECT_ST_WINDOW_DAYS` overrides). A 3-day window won't refresh older businessDates already in the DB
(the aggregator only DELETE-INSERTs dates it re-pulls — see gotcha #10), so to refresh a wider span set
`COLLECT_ST_WINDOW_DAYS=7`. **BUT a 7-day SCT window over-budgets the 1500/15min cap** (≈2× the ROs of a
3-day run) → the run spends 10+ minutes in 429 backoff. Launch it as a `terminal(background=true,
notify_on_complete=true)` with watch_patterns `["=== RESULT ===","FAILED","429","=== SYNC COMPLETE ==="]`
and DON'T block on it — npx/tsx buffers stdout so `process log` shows nothing until exit; rely on the
completion notification. Don't keep polling; report findings to Joe while it finishes.

### Rec-closing % is STILL API-blocked AFTER the 2026-06-18 scope upgrade — definitively re-confirmed
Joe expanded the app's API scope expecting it to unlock the closing %. **It unlocked USERS (names), NOT
inspections.** Re-probed 2026-06-19: every plausible endpoint (`/inspections:search`,
`/inspection-results:search`, `/recommendations:search`, `/mpvi:search`, `/multi-point-inspections:search`,
`/vehicle-inspections:search`, `/service-recommendations:search`) returns **404 "No matching handler"** —
they don't EXIST in v4 (not 403 scope errors). Across the **266 downloaded API specs / 42 repair-order
endpoints there is ZERO inspection/recommendation/MPVI/declined spec.** `repair-orders:search` STILL returns
only COMPLETED jobs / sold operations: a 30-RO fan-out showed 126 jobs all `status=COMPLETED`, operation
`status` field is `None`, no `recommended`/`approvalStatus` fields, no DECLINED/AUTHORIZATION rows. So the
rec-closing DENOMINATOR (recommended-but-declined work) is genuinely not in the OpenAPI. The ONLY path to
closing % is the **Report Builder "Open RO Count" export** (which carries the declined lines) — use skill
`tekion-report-builder-scraper` to bolt that onto the pipeline. When Joe says "we got scope so we can get
into closing %", correct the assumption: scope gave names; closing % needs the Report Builder feed (or
Tekion adding an inspection-results endpoint, ask #4 in docs/tekion-api-scope-request.txt). Don't re-probe
inspection endpoints from scratch — this is settled; go straight to the Report Builder recommendation.


1. Write the ticket as a precise spec file `docs/tickets/T<n>_<slug>.md` — include exact model
   defs / endpoint shapes / acceptance criteria / how-to-run. Vague prompts produce drift; specs
   produce correct output.
2. Hand to Claude Code in print mode from `apps/web` (see skill `claude-code-headless-jay` for the
   HOME=/home/itadmin + ANTHROPIC_API_KEY invocation). Use `--max-turns 40-70 --allowedTools
   "Read,Edit,Write,Bash"`. Tell it to read the ticket file and any reference (e.g. the Python client).
3. **Always verify independently** — do NOT trust Claude's "all checks pass" summary. Re-run the
   smoke test / query the live DB / typecheck yourself. (T2: Claude's smoke test couldn't even run
   standalone — see gotcha below.)
4. Clean up throwaway debug scripts Claude leaves behind (it created 8 `tekion-debug-*.ts` in T2).
5. Commit with a descriptive message, push to the feature branch.

## GOTCHAS (all hit and solved 2026-06-15)
1. **Supabase + Prisma shadow DB**: `prisma migrate dev` FAILS — Supabase's `auth` schema doesn't
   exist in Prisma's ephemeral shadow DB (the enable_rls_policies migration references it). Fix:
   generate SQL with `prisma migrate diff --from-url=$DIRECT_URL --to-schema-datamodel=schema.prisma
   --script` then apply via `prisma migrate deploy` (bypasses shadow DB). Claude figured this out itself.
2. **`import "server-only"` blocks standalone scripts**: a tsx script that imports the client throws
   "This module cannot be imported from a Client Component." Run it with
   `tsx --conditions=react-server scripts/foo.ts` (server-only ships an empty module for that export
   condition). Bake this into an npm script: `"tekion:smoke": "tsx --conditions=react-server ..."`.
   Always `set -a && . ./.env && set +a` before running so TEKION_*/DATABASE_URL load.
3. **git push "could not read Username"**: Jay's profile HOME can't see `~/.git-credentials` (it's in
   /home/itadmin). Fix permanently per-repo: `git config credential.helper "store
   --file=/home/itadmin/.git-credentials"`. Also set git user.email/user.name (was empty → commit failed).
4. **[RESOLVED 2026-06-18 — see T7]** Tekion app-scope 403 on USER lookups was FIXED when Joe upgraded
   the app's API scope: PUBLIC `GET /openapi/v4.0.0/users/{id}` now resolves names server-to-server
   (shape `data.userNameDetails.completeNames[DISPLAY_NAME].value`; unknown id → 400 `no.user.found`).
   The browser resolver below is now a FALLBACK only (`TEKION_ADVISOR_RESOLVER=browser`); default is
   `api`. Original 403 notes kept below for history.
   **Tekion app-scope 403 on USER lookups (PUBLIC OpenAPI only)**: GET /openapi/v4.0.0/users,
   /users/{id}, /users-by-permissions ALL return 403 "app version installed in the dealer does not
   support this API version" (install flagged 0.0.0-pilot-1.0.0). RO/jobs/operations/parts DO work.
   BUT advisor id→name IS resolvable NOW via the INTERNAL app endpoint
   `GET https://app.tekioncloud.com/api/userservice/u/apc/users/{id}` through the authenticated
   :9223 browser session (NOT the public OpenAPI) — T2b/T3 resolved 24 real ST names live
   (Juan Roman/64, Sylvester White/58, Jaime Sanchez/UUID, Michael Parayo/UUID…). So the pilot
   collector resolves names on THIS machine (where the browser session lives) and writes clean names
   to Supabase; Vercel only READS names from DB (the browser path is NOT production-deployable —
   serverless has no session/OTP). Real production fix: get Tekion to upgrade the app's API scope so
   the public /users/{id} works server-to-server (would also likely unblock GL Data). Request drafted
   at `docs/tekion-api-scope-request.txt`; Joe will send + flip env `TEKION_ADVISOR_RESOLVER`
   browser→API when approved. ROs carry advisor IDs only (short numerics 58/59/209 + UUIDs); no names
   in payload; appointment object often null.
5. **Tekion 429 OVERALL_RATELIMIT — budget math (T3)**: one FULL collector run over a ~3-day ST
   window burns ~550 calls (≈136 ROs × ~4 nested fetches each: jobs+operations+parts+vehicle) plus
   advisor-resolution calls + any retries. The cap is 1500/15min, so you CANNOT run two full pulls
   inside one 15-min window — the second throws `429 ... "Limit exhausted for type :
   OVERALL_RATELIMIT"` on `/repair-orders:search`. The client's token-bucket caps OUR outbound rate
   but does NOT know the Tekion-side window is already drained from a prior run. Mitigations:
   (a) wait ~15 min between full runs during dev; (b) the collector correctly finalizes SyncRun=FAILED
   on a fatal 429 and re-throws — data already written stays valid & idempotent; (c) FUTURE hardening
   for the nightly job: treat 429 as a RESUMABLE pause with a SyncRun.cursor instead of a hard fail
   (the search loop collects all ROs before fan-out, so a 429 there aborts the page sweep). Keep
   per-RO fan-out concurrency at 4-6, never higher.
6. **Killed process → stuck RUNNING SyncRun → FIXED in T3b (signal-safe finalize + reaper)**: if a
   run is SIGKILLed at a timeout mid-collect, the SyncRun row is left status=RUNNING, rosFetched=0,
   summary=null — the try/catch-then-finalize block never runs because SIGKILL/SIGTERM bypasses it.
   The DATA still lands fine (RawRepairOrder rows insert as they go); only the run-record bookkeeping
   is orphaned. This WILL bite the nightly cron, so don't just clean it up manually — harden it:
   - **Signal-safe finalize** in collector.ts: register SIGINT/SIGTERM handlers at the top of
     collectRepairOrders; an idempotent `finalizeRun(status, opts)` helper guarded by a `finalized`
     boolean (so normal path and signal path can't double-write); on signal → best-effort
     `syncRun.update` to FAILED('interrupted by <signal>'), then `process.exit(130)`. Remove the
     listeners in a `finally` so repeated calls in one process don't stack handlers.
   - **Stale-run reaper** `lib/sources/tekion/reaper.ts`: `reapStaleRuns(maxAgeMinutes=30)` marks any
     RUNNING row older than the cutoff → FAILED('stale run reaped'). Call it at the START of every
     collectRepairOrders (non-fatal try/catch) so each fresh run self-heals orphans from prior kills.
   - **Print a final `=== RESULT ===` block** in the CLI that RE-QUERIES the persisted SyncRun (status
     + summary + row count) — otherwise the summary is the first thing lost when output is tailed.
   - VERIFY independently (don't trust Claude's report): (a) reaper unit test — insert a fake 40-min-old
     RUNNING row, call reapStaleRuns(30), assert it flips to FAILED; (b) kill test — start collect:st,
     `pkill -TERM -f scripts/collect-st.ts` after ~3s, query newest SyncRun, assert
     status=FAILED 'interrupted by SIGTERM' (NOT RUNNING). Use a SHORT window for the kill test to
     spare the 429 budget. Manual cleanup one-liner (for legacy artifacts only):
     `prisma.syncRun.updateMany({where:{status:'RUNNING'},data:{status:'FAILED',finishedAt:new Date()}})`.

12. **docs/ is GITIGNORED (.gitignore line 39) → silent commit failures**: new files under `docs/`
    (architecture, scope request, tickets) are SKIPPED by `git add -A` with no error — the commit
    \"succeeds\" but the docs aren't in it. The original `docs/00_*.md` predate the rule so they look
    tracked, masking the issue. ALWAYS `git add -f docs/...` for new pipeline docs. (Tickets are
    optional scratch; the architecture doc + scope request SHOULD be tracked.)

13. **DUPLICATE STORE rows — the throwaway-vs-real trap (T3→T5)**: the collector CLI's \"find-or-create
    store\" seeding created a SECOND \"Stevens Creek Toyota\" (abbreviation ST, id 3000...099,
    tekionDealerId set, apiSyncEnabled=true) separate from the REAL store the dashboard/orgs know
    (abbreviation SCT, id 1314a22f..., tekionDealerId=NULL). ALL T3/T4 data landed under the orphan ST,
    so the dashboard (which knows SCT) would show nothing. T5 consolidates onto the real SCT store:
    set SCT.tekionDealerId+apiSyncEnabled, re-point RawRepairOrder/SyncRun/Advisor to SCT (MERGE
    advisors by nameNormalized to respect @@unique(storeId,nameNormalized)), delete orphan's
    metrics/commodity rows, delete the orphan store, then RE-RUN the idempotent aggregator under SCT to
    rebuild metrics cleanly. LESSON: never let a collector script silently create a store — resolve the
    EXISTING store by tekionDealerId and FAIL LOUDLY if not found. Prove no data lost via before/after
    row counts (RawRepairOrder stays 142). After consolidation there must be exactly ONE store per name.

7. **tsx test scripts must live INSIDE the project dir + use --conditions=react-server**: a throwaway
   `.ts` in `/tmp` can't resolve `@prisma/client` (MODULE_NOT_FOUND — node_modules isn't reachable).
   Write it to `apps/web/_foo.ts`, run `npx tsx --conditions=react-server ./_foo.ts`, then `rm` it.
   The react-server condition is mandatory anything importing the server-only client/db chain.

8. **Can't background with shell `&` in this tool** — the terminal tool rejects foreground `cmd &`.
   For a "start process then kill/inspect it" test, launch via terminal(background=true) (get a
   session_id/pid), then in a SEPARATE call do the sleep + pkill + DB query. pkill by the script path
   (`-f scripts/collect-st.ts`) is more reliable than chasing the npm→tsx child PID tree.

9. **OpcodeCategory table starts EMPTY (T4) → all-zero menu/ALA KPIs until seeded**: T1 creates the
   table but nothing populates it. With 0 mappings every opcode is "unclassified" and the aggregator
   produces correct plumbing but zero menu/ALA/commodity numbers. Our ST data had 83 distinct opcodes,
   0 mappings. Fix: a `scripts/seed-opcode-categories.ts` (npm `seed:opcodes`, idempotent upsert by
   (storeId,opcode)) with a STARTER global (storeId=NULL) Toyota taxonomy: TSC*/TXM*/TAC* prefixes →
   MENU; ROTATE→commodity "tires", *ALIGN*→"alignment", FACBRAKE→"brakes", BATT→"battery"; VAC/MPVI/
   MISC/EARLYBIRD/DIAG → ALA; leave internal/warranty UNMAPPED (EMPSHOP/TPFM/PORT*/INFO/CAT/K1/RECALL/
   TEK*). This is a STARTER to prove the pipeline — the aggregator MUST print the unclassified-opcode
   list (49/83 in our run) so Joe can extend the taxonomy. The real opcode→category mapping is a
   BUSINESS decision Joe owns; don't perfect it, surface it for review.

10. **Aggregator idempotency = DELETE-then-INSERT SET, a DIFFERENT pattern than the collector's
    upsert/hash (T4)**: the email prototype uses `{increment:...}` because each email is new data, but
    the API re-fetches the SAME ROs every run, so the aggregator must RECALCULATE each
    (storeId,advisorId,businessDate) bucket from scratch and SET. Cleanest convergent impl: inside a
    txn, DELETE all AdvisorDailyMetrics + AdvisorDailyCommodity rows for the (storeId, businessDate)
    set being recomputed, THEN insert fresh — this also removes orphan buckets from a prior stale run.
    Scope strictly to the API store (ST); never touch email-store rows. PROVE idempotency with a
    CHECKSUM, not just row count: sum(menuCount)+sum(alaCount)+sum(dailyLaborGross)+sum(openRos) across
    all rows must be byte-identical before/after a 2nd run (ours: menuCount=190 alaCount=163
    dailyLaborGross=22252.82, stable). The collector proves idempotency via distinct==total; the
    aggregator proves it via checksum-stability across re-runs. Different layers, different proofs.

11. **COUNT SEMANTICS — the course-correction that matters most (T4→T4b)**: the first aggregator cut
    counted menuCount/alaCount as OPERATIONS (line items), which made menuSalesPct come out 127.7%
    (>100%) — nonsense for a penetration rate. The EXISTING email prototype
    (`lib/parsing/parsers/menuSales.ts` ~line 37: `const unique = new Set<string>(); // advisor|ro`)
    defines menuCount as **the count of unique (advisor, RO) pairs** — i.e. distinct ROs in which the
    advisor sold a menu = PENETRATION, capped at 100%. To match SCVW so ST is comparable on the same
    dashboard, the aggregator must dedupe by advisor|documentId (a `Set<documentId>` per bucket for
    menu, a separate one for ALA; menuCount=set.size). Grosses STAY summed across all lines (that
    already matched email lines 55-56 — don't change them). Commodity `qty` stays a quantity (can
    exceed RO count — multiple tires — that's fine).
    **openRos** (the denominator: dashboard computes menuSalesPct = menuCountTotal/openRosTotal in
    `app/(app)/dashboard/ui.tsx:270`, route reads it at `app/api/advisor/route.ts:68`): the column
    `AdvisorDailyMetrics.openRos Int @default(0)` ALREADY EXISTS (no migration needed) — SET it =
    count of distinct RawRepairOrder.documentId per (storeId,advisorId,businessDate). The API-native
    openRos is the distinct-RO count; in the email world it came from the separate OpsTrax "roCount" /
    Vehicle-Attendance report — CAVEAT to flag to Joe: distinct-billable-ROs may not perfectly equal
    OpsTrax Vehicle Attendance (which may include no-sale/declined visits), so reconcile the two before
    trusting the pcts. LESSON: before writing any aggregator, READ how the existing/control pipeline
    defines each metric (grep the parsers for the exact dedupe/Set logic) — match its semantics
    EXACTLY, don't assume "count = rows".

14. **Don't over-build the dashboard wire (T6) — the read path is already store-agnostic**: because
    the aggregator writes the SAME AdvisorDailyMetrics/AdvisorDailyCommodity tables the email dashboard
    reads, and `loadDashboardData` reads by storeId with no email-specific logic, the API store renders
    for FREE once selectable. Before writing ANY dashboard code, confirm this (read dashboard.ts +
    stores service). The only genuine API-vs-email differences to handle: (a) `run:null` (API stores
    have no IngestionRun — file-upload concept doesn't apply) must not crash day/range views;
    (b) zero-denominator metrics (rec) must render '—' not a misleading 0% — make it GENERIC
    (denominator 0 → dash), never `if store===SCT`, so the control store keeps real numbers;
    (c) a tiny source badge. Keep the diff small; this is wiring, not a redesign.

## DATA GAPS to report to Joe (realities, not bugs)
- **Rec-Closing % is API-BLOCKED — fully diagnosed 2026-06-15 (gotcha #12)**: the API can give the
  numerator (rec work SOLD) but NOT the denominator (rec work RECOMMENDED/DECLINED). repair-orders:search
  returns SOLD operations only. The REC opcode IS present but it's just sold work mislabeled REC
  (job.status=COMPLETED, payType=CUSTOMER_PAY, real labor$, corrections[] = tech narrative, NOT a
  recommend/decline ledger). The recommended-but-not-sold lines appear in Tekion as DECLINED /
  AUTHORIZATION opcode rows — these show up in the Report Builder \"Open RO Count\" Excel but are STRIPPED
  by the OpenAPI. Confirmed: NONE of the 43 repair-order API specs expose recommendations/MPVI/inspection
  results. So rec* = 0 + warn until either (a) Tekion enables an inspection-results endpoint (added as
  ask #4 to docs/tekion-api-scope-request.txt), or (b) we bolt a Report Builder browser-scraper on (use
  skill tekion-report-builder-scraper) — Joe's call; default is (a). Do NOT fabricate rec numbers.
- **openRos / OpsTrax reconciliation** (see gotcha #11 caveat).
- **Unclassified opcodes** — surface the list each aggregate run; Joe owns the taxonomy.

## CONFIRMED RO payload field map (T4, from real RO 569025 — trust these exact paths)
Snapshot shape: `{ ro, jobs:[{ job:{...}, operations:[{ operation:{...}, parts:[...] }] }], vehicle,
advisorName }`. Defensive access (job/op may be wrapped OR flat): `const jobObj=j.job??j; const
ops=j.operations??jobObj.operations??[]; const opObj=o.operation??o; const parts=o.parts??opObj.parts??[]`.
- Opcode: `opObj.opcode` (e.g. "TSC10"), desc `opObj.opcodeDescription`.
- Labor (CENTS): `opObj.labor.saleAmount`, `opObj.labor.costAmount`.
- Parts (CENTS, EXTENDED line total — do NOT ×qty): `part.saleAmount`, `part.costAmount` (unit values
  exist as unitSaleAmount/unitCostAmount — ignore). Part also has `quantities`, `partName`, `partNumber`.
- Job pay context: `jobObj.payType` / `jobObj.subPayType`.
- Advisor: top-level `payload.advisorName` + `ro.assignee?.advisor?.id` (tekionUserId).

## IDEMPOTENCY — how it was PROVEN (T3), and the gotcha that looks like a bug
Upsert is by unique `(storeId, documentId)` with a sha256 contentHash change-check (unchanged ROs
skip the write). To prove it: `SELECT COUNT(*) total, COUNT(DISTINCT documentId) distinct FROM
RawRepairOrder` — **total must equal distinct** (e.g. 142=142, 0 dupes), even after several
partial/killed runs. **Looks-like-a-bug-but-isn't**: a "last N days" window is recomputed fresh each
run, so a re-run started minutes later legitimately catches a few BRAND-NEW ROs created at the store
in between → row count creeps up (136→139→142) while distinct==total. That's correct behavior, NOT a
duplicate-insert. Always check distinct==total, not just whether the raw count moved.

## Verified Tekion API facts (trust these)
- POST /openapi/v4.0.0/repair-orders:search — filters[{field,operator,values:[epochMsString]}],
  pageSize≤50, paginate via paginationToken←meta.nextPageToken. Response data.results / meta.totalCount.
- Money is integer CENTS. Gross = labor.saleAmount − labor.costAmount. Parts line saleAmount is
  EXTENDED (qty already applied — do NOT ×qty).
- Advisor nested at assignee.advisor.id. Throttle 1500/15min (use 1400 cap).
- Live counts sane: ST returned 421–467 ROs for a 2–3 day window.

## Reverse-engineering a metric definition from the SCVW Excels (the technique that cracked rec-data)
When a metric's source/definition is in question, READ the 13 ground-truth Report Builder exports in
`dealer-detail/example_excels/` (NOT guesswork). All share sheet `ReportBuilder_Report` and columns
`RO Created Date|Advisor Name|RO Number|Operation OpCode|Operation Tech Story|Year|Model|Mileage In|
Opcode Labor Gross|Opcode Parts Gross|Opcode Labor Price|Opcode Parts Price`. Read with openpyxl
`load_workbook(path, data_only=True)` (NOT read_only — that lacks .dimensions); rows have VARIABLE
width so guard `r[i] if i<len(r) else None`. Most commodity/menu files are EMPTY templates (1-2 rows =
the report DEFINITION you saved); only Open RO Count / Alignments files held real data. Cross-check the
opcodes the Excel shows against what the API returns (query RawRepairOrder payloads, build an opcode
frequency Counter) — that diff is what proved the API strips DECLINED/AUTHORIZATION. Then confirm
against the parser code (`lib/parsing/parsers/*.ts`) for the exact dedupe/Set semantics. This three-way
check (Excel ⇄ API data ⇄ parser code) is the reliable way to nail a definition.

## Verification standard
Post each ticket: re-run smoke/query live DB yourself; confirm prototype tables untouched (additive);
typecheck clean. RO counts should roughly match store appointment volume; amounts integer-cents-derived.
