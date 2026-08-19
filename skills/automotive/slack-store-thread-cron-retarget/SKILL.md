---
name: slack-store-thread-cron-retarget
description: Retarget an AMG store's Hermes cron report deliveries to a new Slack thread when Joe says "can this thread be <store> reports only?", and sweep the whole fleet for dead channel_not_found cron deliveries.
---

# Slack store-thread cron retarget

## When to use
Joe posts in a brand-new Slack thread and says something like:
- "Can this thread be GM reports only?"
- "Make this the BT thread"

He wants EVERY cron for that store delivering into that exact thread. Do it immediately, confirm, don't ask.

## Why this keeps happening
Joe abandons/recreates threads. The old channel or thread becomes invalid, and Hermes cron Slack delivery fails with `channel_not_found` **silently** — the email leg of the same job still succeeds, so nothing looks broken from Joe's side. Reports just stop appearing.

## Steps
1. Capture the CURRENT channel + thread_ts from the incoming message context (channel `C0...`, thread ts like `1787111034.827789`). Target string = `CHANNEL:THREAD_TS`.
2. List crons and identify every job for that store (match by name prefix, e.g. `BC Menu Sales`, `BC Warranty Closings`).
3. Update each job's Slack destination to the new `CHANNEL:THREAD_TS`.
4. **Fleet sweep** — grep the cron/delivery logs for `channel_not_found` across ALL jobs, not just the store you were asked about. Other stores are usually broken too.
5. Report back: list of retargeted job IDs + schedules, note any that had been failing, and flag any OTHER store's dead deliveries for Joe's decision (don't retarget another store's reports into a store-specific thread without asking — that violates the "X reports only" instruction).

## Known store cron sets
| Store | Jobs |
|---|---|
| BC (Blackstone Chevy/Cadillac, 1251, "GM") | BC Menu Sales — Daily Closed `ea75e889579a` (12pm + 5pm); BC Menu Sales — Closed MTD `35800c950401` (6:15pm); BC Warranty Closings `ae9576ce28ed` (7am) |
| BT (Blackstone Toyota, 1249) | BT Menu Sales Closed MTD `7d023e4565a0` (6am, auto-sends to Tony Garcia agarcia@blackstonetoyota.com, CC Joe) |

## Dead channels/threads (history)
- BC: `C0BGTDMP9U2` (dead) → `C0BR7FHMF17:1787111034.827789` (dead 2026-08-19) → current
- BT: `C0BGTDR158S:1783876504.495759` went `channel_not_found` by 2026-08-19

## Pitfalls
- A `channel_not_found` cron looks HEALTHY in its own run log if it also emails — check the Slack post result specifically.
- Don't dump another store's reports into a single-store thread; ask Joe first.
- Thread-scoped delivery needs the thread_ts, not just the channel — posting to the channel root is not what he asked for.
