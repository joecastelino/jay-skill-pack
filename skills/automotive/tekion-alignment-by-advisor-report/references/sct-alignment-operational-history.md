# SCT Alignment Pipeline — Operational History

Key operational lessons from running the SCT alignment pipeline June–August 2026.

## DEALER_QUOTA Exhaustion (Aug 2026)

A THIRD quota type beyond OVERALL_RATELIMIT and OVERALL_QUOTA. Signature:
- `/repair-orders:search` and `/repair-orders/{id}/jobs` return 200
- `/jobs/{id}/operations` 429s with `Limit exhausted for type : DEALER_QUOTA`
- The standard quota probe (search pageSize=1) returns 200 and LIES

Diagnose with: `O.call('GET','/repair-orders/<rid>/jobs/<jid>/operations')`

Both backoff guards in `sct_align_mtd.py` now match "DEALER_QUOTA" (patched 2026-08-01).

### DEALER_QUOTA can persist >22h
Seen: outage from 7 PM → still 429 at 5 PM next day.

**Hunt the hog FIRST:** the dealer-detail nightly `sync:all` (cron 23:00, `cron-sct-sync.sh` → `npm run sync:all` → tsx) can get stuck retrying for 17+ hours against the 429 wall. Diagnose: `pgrep -af "sync-all|cron-sct-sync|tsx --conditions"` + `ps -o lstart=` on the flock pid. Fix: kill the WHOLE tree (flock, .sh, npm, tsx, node) and confirm lock file is gone.

**Month rollover:** when recovery lands after the 1st, MTD scan window auto-computes to only the new month → misses prior-month data.

## Stale Same-Day Index Trap
The scan caches `data/sct-mtd-<YYYY-MM-DD>-closed-index.json` keyed by DATE only. If anything ran the scan earlier the SAME day (e.g. a 9:31am probe), the 7pm run reuses that morning index and silently misses every RO closed since. A "loaded cached index: N ROs" log line at 7pm is the tell. Fix: check index file mtime; if hours old, mv to .bak and re-run.

## Scripts
- `/home/itadmin/tekion-reports/sct_align_full_june.py` — full-month scanner
- `/home/itadmin/tekion-reports/sct_align_mtd.py` — month-to-date scanner
- `/home/itadmin/tekion-reports/render_sct_align_full_june.py` — 2-page scorecard renderer
- Interpreter: `/home/itadmin/.hermes/hermes-agent/.venv/bin/python3.11`