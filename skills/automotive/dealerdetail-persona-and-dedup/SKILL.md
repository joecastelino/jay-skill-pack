---
name: dealerdetail-persona-and-dedup
description: Split the DealerDetail advisor dashboard by Tekion persona (SERVICE_ADVISOR vs an "Others" bucket for cashiers/warranty clerks/service managers/techs), backfill the persona column from the Tekion users API, and fix duplicate-advisor rows caused by null-name pre-scope-upgrade pulls. Use when advisor numbers look polluted by non-advisors, when you see an "Unassigned"/null advisor, when personas are 0/N populated, or when the same Tekion userId appears under two Advisor rows.
triggers:
  - advisor persona split
  - dedup advisor rows
  - unassigned advisor
  - service advisor vs others bucket
---

# DealerDetail — Advisor Persona Split & Dedup

## Repo & env (CRITICAL — get these right first)
- Real repo path: **`/home/itadmin/dealer-detail`** (NOT `~/dealerdetail`, which is a non-git specs dir). For this agent `~` ≠ `/home/itadmin`.
- App lives in `apps/web`. Run scripts from there.
- `main` **auto-deploys to Vercel production**. Merging = prod deploy. Never push to main casually.
- Git creds: `git -c credential.helper='store --file=/home/itadmin/.git-credentials' push origin main`
- Node/tsx: `/home/itadmin/.hermes/node/bin` (node v22).
- tsx run pattern (the Tekion client uses react-server conditional imports):
  ```bash
  cd /home/itadmin/dealer-detail/apps/web
  set -a && . ./.env 2>/dev/null && set +a
  npx tsx --conditions=react-server <script.ts>
  ```
  WITHOUT `--conditions=react-server` you get a `TransformError`. A bare `.mjs` importing the client also fails (`ERR_MODULE_NOT_FOUND`) unless run from inside `apps/web`. For pure Prisma queries (no Tekion client), a `.mjs` with `import { PrismaClient } from "@prisma/client"` run from `apps/web` works fine and is faster.

## Schema facts (memorize — easy to get wrong)
- **Store** model: name field is `name`, abbreviation field is **`abbreviation`** (NOT `abbrev`), Tekion id is `tekionDealerId` (e.g. `americanmotorscorporation_876_0`). Find SCT with `where: { abbreviation: "SCT" }`.
- **Advisor** model: `nameRaw` (nullable), `nameNormalized` (the `@@unique([storeId, nameNormalized])` key), `tekionUserId`, **`persona`** (String?, added by the persona-split feature).
- **AdvisorDailyMetrics**: `@@unique([storeId, advisorId, businessDate])`.
- **AdvisorDailyCommodity**: `@@unique([storeId, advisorId, businessDate, commodityKey])`.

## Persona data path
- Source: Tekion public OpenAPI `GET /openapi/v4.0.0/users/{id}` (works for numeric ids AND UUIDs after the scope upgrade Joe enabled).
- JSON path: **`data.userRoleDetails.primaryRole.persona`** → values like `SERVICE_ADVISOR`, `SERVICE_MANAGER`, `WARRANTY_CLERK`, `CASHIER`, `TECHNICIAN`.
- In code: `TekionClient.resolveUserDetailed(dealerId, userId)` returns `{ name, persona, sourceField, raw }`. `extractUserPersona(raw)` does the pluck.

## The dashboard split rule
- `persona === "SERVICE_ADVISOR"` → goes in the **advisors** leaderboard.
- Everything else (including the 3 non-advisor personas, and historically null) → the **"Others (non-advisor roles)"** bucket. Others **keeps all metrics** (nothing dropped) so the data is revisitable.
- Files that implement it (already merged): `lib/sources/tekion/client.ts` (persona cache + extract), `advisors.ts` (`ResolvedAdvisor {name,persona}`), `collector.ts` + `aggregate/aggregator.ts` (BOTH persist persona — the aggregator independently re-derives Advisor rows, so it must set persona too or it stays null), `lib/server/services/dashboard.ts` (`DashboardData.others` + partition), `app/(app)/dashboard/ui.tsx` (Others section + `othersColumns`/`formatPersona`).

## Task A — Backfill the persona column (when personas are 0/N or partial)
1. Write a backfill script in `apps/web` (e.g. `_persona_backfill.ts`) that:
   - finds the store by `abbreviation`, grabs `tekionDealerId`,
   - `prisma.advisor.findMany({ where: { storeId, tekionUserId: { not: null }, /* optionally persona: null */ } })`,
   - for each: `const d = await client.resolveUserDetailed(dealerId, a.tekionUserId)`, then `update` `persona: d.persona`, and backfill `nameRaw` if it was null.
2. **Run it in the BACKGROUND with `notify_on_complete`** — the calls sit in 429 backoff if the bucket is exhausted; foreground will time out at 180s.
3. It is normal for the FIRST 1-2 lookups to FAIL with 429 (`OVERALL_RATELIMIT`) if the bucket just emptied, then succeed once it recovers mid-run. **Just re-run the script filtering `persona: null`** to mop up the stragglers — usually succeeds immediately on the second pass.
4. Verify: query and bucket into SERVICE_ADVISOR / others / null-persona. Target = 0 null personas.
5. Clean up temp scripts (`rm` them) — they are NOT meant to be committed.

## Task B — Fix duplicate advisor (the "Unassigned"/null-name bug)
**Symptom:** the same `tekionUserId` appears under TWO Advisor rows — one named, one with `nameRaw = null` and `nameNormalized = "UNASSIGNED"`. Cause: the collector ran BEFORE the API scope upgrade (couldn't resolve the name), so it stored a null-name row keyed on a different `nameNormalized`; a later pull created a second, named row. The `@@unique([storeId, nameNormalized])` constraint allows both because the normalized keys differ. This **splits the advisor's metrics across two rows.**

**Fix (reparent + delete, transactional):**
1. Find both rows: `where: { storeId, tekionUserId: "<uuid>" }`.
2. Check each row's `advisorDailyMetrics` and `advisorDailyCommodity` `businessDate`s.
3. **Check for date overlap.** If the null row and named row have NO overlapping `businessDate`, you can reparent cleanly. If they DO overlap, the `@@unique` will reject the UPDATE — in that case delete the older (null-row) metric for the colliding date (the post-upgrade named-row data is authoritative).
4. In a `prisma.$transaction`:
   - `advisorDailyMetrics.updateMany({ where: { advisorId: nullRow.id }, data: { advisorId: namedRow.id } })`
   - same for `advisorDailyCommodity`
   - `advisor.delete({ where: { id: nullRow.id } })`
5. Verify advisor count dropped by 1 and there are no remaining null-name rows.

(Real example: Angel Gutierrez, UUID `ee31e3e9-bba5-4868-8ead-a2464c95eab1`, SERVICE_ADVISOR — had a `UNASSIGNED` ghost row with 06-15 metrics + a `tires` commodity, plus a named row with 06-17/06-18. No overlap, clean reparent, deleted ghost.)

## Tekion 429 budget choreography (the recurring villain)
- Limit ≈ **1,500 calls / 15 min** (`OVERALL_RATELIMIT`). The whole org/fleet shares it.
- A **7-day** collect window blows the budget and grinds in backoff for 30+ min — **use the default 3-day window** (`unset COLLECT_ST_WINDOW_DAYS`). `sync:st` = collect→aggregate.
- If you kill a sync mid-run (SIGTERM/-15), the collector's signal handler usually marks its SyncRun FAILED itself, but **verify**: `updateMany({ where:{status:"RUNNING"}, data:{status:"FAILED", finishedAt:new Date()} })` to reap orphans, or the next run sees a stuck RUNNING row.
- Background long ops with `notify_on_complete=true` + watch_patterns `["=== SYNC COMPLETE ===","FAILED","OVERALL_RATELIMIT","rosFetched"]`. NOTE: buffered tsx/Node output only flushes at exit, and stale watch-pattern notifications from a KILLED process can arrive minutes later — match the `session_id` before reacting.
- Permanent staleness fix = the nightly cron (below). Without it, data drifts 3+ days stale and forces big catch-up pulls that blow the budget.

## Nightly cron (the staleness fix)
- Wrapper: `/home/itadmin/dealer-detail/scripts/cron-sct-sync.sh` (sets PATH to hermes node, loads `.env`, `unset COLLECT_ST_WINDOW_DAYS`, `npm run sync:st`, logs to `logs/sct-sync-nightly.log`).
- Crontab line (runs **1:30 AM**, offset from the 1:00 Caliber Tekion job to avoid sharing the 429 budget at the same minute):
  ```
  30 1 * * * /usr/bin/flock -n /tmp/dealerdetail-sct-sync.lock /home/itadmin/dealer-detail/scripts/cron-sct-sync.sh >> /home/itadmin/dealer-detail/logs/sct-sync-nightly.log 2>&1
  ```
- Follows the existing Caliber/VI cron pattern (flock + append log).

## Closing % — known dead end
`recClosingPct` is hardwired to `0.00%`. The Tekion OpenAPI has **no** inspection/recommendation/MPVI/declined-jobs endpoint (confirmed across all 266 specs, even post-scope-upgrade). `repair-orders:search` returns SOLD/COMPLETED jobs only. The denominator (recommended-but-declined work) is ONLY in the Report Builder "Open RO Count" Excel export → needs the `tekion-report-builder-scraper` skill, not the API. Don't burn time hunting an API endpoint for this.

## Pitfalls recap
- `abbreviation` not `abbrev`; `nameRaw`/`nameNormalized` not `name` on Advisor.
- Must use `--conditions=react-server` for any script importing TekionClient.
- Persist persona in BOTH collector AND aggregator.
- First 1-2 backfill calls 429ing is normal — re-run to mop up.
- Check businessDate overlap before reparenting metrics (unique constraint).
- Match `session_id` on delayed watch-pattern notifications — don't react to a killed proc's stale output.
- Clean up temp `_*.ts`/`_*.mjs` scripts before/after committing.
