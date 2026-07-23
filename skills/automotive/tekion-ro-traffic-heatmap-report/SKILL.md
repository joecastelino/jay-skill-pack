---
name: tekion-ro-traffic-heatmap-report
description: Build a "when do we get the most traffic" staffing report from Tekion — RO open times bucketed by day-of-week x hour, per store, rendered as a Toyota-red heatmap. Zero fan-out (opcode tags are free on repair-orders:search). Built 2026-07-15 for Joe's TXM (Toyota Express Maintenance) department staffing question. Also covers the Slack-download-fails fallback (copy files to Joe's Windows Downloads via /mnt/c).
triggers:
  - txm traffic report
  - ro open times
  - when do we get the most traffic
  - staffing heatmap
---

# Tekion RO Traffic Heatmap (open times by day/hour)

Joe's ask pattern: "when do we get the most traffic in <dept> so I can adjust staff."
Answer = ROs **opened** per day-of-week × hour, per store, as a heatmap + staffing takeaways.

## Existing scripts (adapt, don't rebuild)
- Scan: `/home/itadmin/tekion-reports/txm_open_times_scan.py`
- Render: `/home/itadmin/tekion-reports/render_txm_open_times.py`
- Data: `/home/itadmin/tekion-reports/data/txm-open-times-30d.json` + `-agg.json`
- Output: `/home/itadmin/tekion-reports/output/txm-open-times-30d.{png,pdf}`

## Step 1 — Scan (ZERO fan-out, this is the key efficiency)
Department membership is detectable from **OPCODE tags on the `repair-orders:search`
result itself** — no jobs/operations fetches at all. TXM ROs carry `TXM*` opcodes
(TXMBASIC, TXMPLUS, TXM20, TXM25...). 30 days × 3 Toyota stores (SCT/BT/TL) =
~13K ROs = ~260 search pages, ~6 min total, trivially inside quota.

- `POST /repair-orders:search`, filter `creationTime BTW [ms0,ms1]` (values as strings),
  pageSize 50, paginate via `meta.nextPageToken`.
- NO status filter — traffic = everything opened, including still-open ROs.
- Per RO keep: `documentNumber`, `creationTime`, `status`, matched opcodes.
- Match: `[o for o in opcodes if o.upper().startswith("TXM")]`. For other departments
  swap the prefix/set (derive per store — see memory rule about per-store opcodes).
- TXM = Toyota stores only (SCT, BT, TL). 429 retry: sleep 30*(attempt+1).
- Run as **background terminal** process; `process wait` is clamped to 180s per call —
  just call wait again (scan finished in ~10 min).

Reference 30d counts (Jun 15–Jul 15 2026): SCT 4,198 TXM of 5,298 ROs; BT 906 of
3,735; TL 2,292 of 3,994. Fleet 7,396 (~247/day).

## Step 2 — Aggregate
Convert `creationTime` ms → **America/Los_Angeles** (zoneinfo), bucket
`(weekday, hour)` Counter + byhour + bydow. Save agg JSON so re-renders don't rescan.

## Step 3 — Render
House style (white bg, base64 `logo_0.png`, red #EB0A1E rule, KPI cards w/ red hero,
dark table headers). Per store: heatmap table (rows Mon–Sun, cols = **that store's
operating hours** — see hour-grid rule below, white→red
cell intensity scaled to that store's max, green row totals), one-line insight
(peak slot / busiest day / slowest day / rush hour), mini hour-bar strip.
Headless Playwright: screenshot full_page PNG + `pg.pdf(width="1226px",
height=scrollHeight+40)`. Verify with vision_analyze before sending.

Report insights Joe valued: % of day arriving before 10 AM, second afternoon wave
(1–3 PM), weekend asymmetries (SCT Sunday > Saturday; TL Saturday 7–8a hot, Sunday
dead), per-store staffing rule of thumb.

## ⚠️ Hour-grid rule (Joe corrected this 2026-07-15 — "TOYOTA LANCASTER IS OPEN TILL 8 PM")
Size the HOURS columns to EACH STORE'S operating hours, not a fleet default. My first
render cut off at 6p and hid TL's 5–8p traffic (5p:72, 6p:50, 7p:4 ROs). Known:
**TL = 6a–8p** (`HOURS = range(6,21)`). Verify/ask hours for other stores before
rendering. A single-store variant exists: `render_txm_open_times_tl.py` (TL-only,
own KPI row: total / per-day / busiest day / rush hour).

## Calendar-month re-run variant (\"can you do the same for May\", built 2026-07-15)\nJoe follows up asking the same report for a specific MONTH. Don't touch the rolling-30d\nscripts — month variants exist and are the template:\n- Scan: `/home/itadmin/tekion-reports/txm_open_times_scan_may.py` (TL-only) — window =\n  PT-midnight month bounds: `START = datetime(Y,M,1,tzinfo=PT)`, `END = first of next\n  month`, both ×1000 ms. Output `data/txm-open-times-<month>.json`.\n- Render: `/home/itadmin/tekion-reports/render_txm_open_times_tl_may.py` — aggregates\n  INLINE from the raw rows (no separate -agg.json needed for single-store), divides\n  per-day KPI by actual days in month (31 for May), subtitle/KPI label say the month.\n- One month × one store ≈ 82 pages, ~2 min scan; still run as background + probe quota\n  first (`python3 /home/itadmin/dealer-detail/scripts/tekion-quota-probe.py` → \"OK\").\n- Reference: TL May 2026 = 2,379 TXM of 4,060 ROs (77/day), busiest Sat (488), rush\n  8a–9a, hottest slot Sat 7a (103). Compare vs prior window in the Slack summary —\n  Joe likes the month-over-month sentence.\n\n## Delivery — Slack download fallback (IMPORTANT, hit 2026-07-15)
Joe could NOT download the `MEDIA:` PDF attachment from Slack ("I can't download it").
Fix: **copy the files directly to his Windows Downloads folder** — we're in WSL:
```
cp <files> /mnt/c/Users/joeca/Downloads/
```
Then tell him the `C:\Users\joeca\Downloads\...` paths. His Windows username = `joeca`.
**BUT ask/consider whether he's on his own machine** — 2026-07-15 he was "talking from
a different computer", so local file drops were useless. Universal fallback = EMAIL.

## Delivery — email fallback when the agent bridge is gone (hit 2026-07-15)
`/home/itadmin/bin/ask-agent` did NOT exist (bridge script wiped) → Stacey unreachable.
When Joe says "just email it", send DIRECTLY via SMTP using Stacey's template
(sanctioned last-resort per Joe's standing rule — flag the bridge outage to him/Walter):
- App password: `re.search(r'raw\s*=\s*"([^"]+)"', open('/home/itadmin/.hermes/profiles/email-agent/home/.config/himalaya/config.toml').read()).group(1).replace(' ','')`
- MIME: mixed → alternative(text+html) + PDF attachment; PNG embedded INLINE as
  **base64 data-URI `<img>`** (not CID); footer "Sent from Tekion Open API — live data".
- From==To==Joe → Gmail files ONLY in Sent: MUST `imaplib.append()` a copy to INBOX
  (verify it prints OK).
- Revision etiquette: when re-sending a corrected report, mark subject "(v2 — <what
  changed>)" and state the correction in the body.

## Pitfalls
- `search_files` on `/mnt/c/Users` HANGS (60s timeout) — Windows mount is slow to
  enumerate. Use `timeout 10 ls /mnt/c/Users/` in terminal instead.
- Amounts not needed here, but if added: Tekion $ are CENTS, /100.
- State scope defaults in-line (open-time vs appointment-time, 30d window, Toyota
  stores only) and offer variants — don't block asking.
- **ONE-TIME means one-time** (Joe 2026-07-15: "I don't need this scheduled, I just
  want you to do it 1 time and email me"). Do NOT create a cron for ad-hoc report
  requests, and if follow-ups might imply scheduling, explicitly confirm "no cron
  created" in the reply.
