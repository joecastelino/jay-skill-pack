---
name: tekion-uber-lyft-transportation-swap
description: Reference for the AMG project to replace Tekion's native Lyft transportation/ride-fee integration with Uber. Load when asked about Uber API integration, swapping Lyft for Uber in Tekion, or prepping for Uber engineering team talks.
---

# Tekion Uber/Lyft Transportation Swap

## Background
Joe wants to swap Tekion's native **Lyft** transportation integration (advisor taps Transportation → Lyft on an RO, ride books, fare auto-populates as an RO fee) for **Uber**. Uber has no native Tekion integration — there's no equivalent button/plugin to flip on. Business rationale for the swap itself was never stated in the original ask; if it comes up, capture it here.

## Key technical findings (verified 2026-08-04)
1. **Tekion's public RO Fee API is READ-ONLY.** Checked OpenAPI spec `repair-order__get-repair-order-fees.json` — there's a GET for RO-level fees but **no POST/PUT to create/update a fee**. This means even with a perfect Uber fare in hand, there is no clean API write path to drop it onto an RO. The only way to write a fee is through the Tekion UI (RO → Misc Charges/Fee screen) — same as what advisors already do manually when Lyft's auto-populate fails.
2. **Uber's relevant product = Uber for Business (Guest Rides / Central).** This lets a business book/track a ride FOR a customer without the customer needing their own Uber account/app — the correct analog to Lyft's dealer-paid ride flow. It exposes ride booking + completion data via API/webhook.
3. **Remaining blocker to any implementation:** access to an Uber for Business account with API credentials. Nothing else can start without this.

## Proposed architecture (not yet built — pending Uber engineering call)
1. Advisor requests a ride via a lightweight internal tool (Slack command or small form) instead of Tekion's native Lyft button.
2. A middleware service calls the Uber for Business API to book the ride, tagged with the RO#.
3. Uber fires a webhook on ride completion.
4. Middleware pulls the final fare from the completion webhook/receipt.
5. **Browser automation** (not API) writes that fare as a Misc Fee/Misc Charge line on the Tekion RO, since Tekion's public API can't write fees.

## Purpose of talks with Uber's engineering team
Two blockers the call needs to resolve before building anything:
1. **Access** — does AMG already have, or need to set up, an Uber for Business account with API credentials?
2. **API/webhook confirmation** — verify Uber for Business exposes: (a) a booking endpoint supporting guest/customer rides paid by the dealership, (b) a completion webhook or pollable endpoint returning the final fare, (c) auth model (API key vs OAuth) and rate limits — needed to scope the middleware correctly.

## Do NOT
- Promise a native Tekion↔Uber integration — it doesn't exist and Tekion's public API can't support a write-side equivalent of the Lyft plugin.
- Assume the Tekion fee-write gap might be solved later without checking — re-verify against current OpenAPI specs if this resurfaces after an API version bump (Tekion has upgraded app/API scope before, see tekion-api-upgrade-audit skill).

## Status / where things left off
As of 2026-08-06: architecture is designed, blocked on (1) Uber for Business account/credentials and (2) the engineering call to confirm API/webhook shape. Nothing has been built yet (no middleware, no browser-automation fee-writer). Full session detail: session_id `20260804_113325_1a318799` (brain note: `/home/itadmin/brain/projects/session-20260804_113325_1a318799.md`).
