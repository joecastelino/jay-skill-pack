---
name: hermes-system-audit
description: >
  Run a comprehensive system audit of the AMG Hermes fleet — gateway services,
  persistent browser servers, cron jobs, GBrain, disk, memory, and agent profiles.
  Use when Joe reports agent degradation, after weekend incidents, or for recurring
  health checks.
triggers:
  - system audit
  - fleet audit
  - check all systems
  - why is walter broken
  - what is broken
  - weekend incident
  - venv incident
---

# Hermes Fleet System Audit

Comprehensive health check of the entire AMG Hermes fleet.

## Audit Checklist

### 1. Service Units — venv paths and state

```bash
systemctl --user list-units 'hermes-gateway-*' --no-legend --no-pager --all
```
All 10 should show `active running`. Then verify ALL units use `.venv` (not the old `venv`):

```bash
for u in $(systemctl --user list-unit-files 'hermes-gateway-*' --no-legend --no-pager | awk '{print $1}'); do
  ex=$(systemctl --user show "$u" --property=ExecStart)
  echo "$u: $(echo "$ex" | grep -oP '/hermes-agent/[^/]+/bin/python')"
done
```

**⚠️ Also check the BASE unit** (Walter) — he has no `--profile` flag. His ExecStart
may be correct `.venv` but his drop-in PATH entries may still point to the old `venv`:

```bash
systemctl --user cat hermes-gateway.service | grep -E 'ExecStart|PATH'
```

### 2. Persistent Browser Servers — all 3 ports

```bash
for port in 9223 9224 9225; do
  curl -s --max-time 3 http://localhost:$port/health 2>&1 || echo "DEAD"
done
```

| Port | Purpose |
|------|---------|
| 9223 | Jay's Tekion DMS (primary) |
| 9225 | Subagent Tekion lane |
| 9224 | APC partner portal |

**Restart required `xvfb-run`** because `headless:false` is hardcoded in server.js.
Without it: "Missing X server or $DISPLAY" crash.

**💀 3AM RESET TRAP:** Browser DATA survives in the persistent directories, but the
node PROCESS dies at the 3AM profile wipe. No auto-restart exists. After 3AM all three
must be restarted manually.

### 3. Cron Jobs — delivery health

Check for `channel_not_found` (deleted Slack channels), `paused`, `error`.
BC and BT Slack channels are known to go stale periodically.

### 4. Agent Profiles — config integrity

11 profiles expected. Jeff has no config.yaml (intentional).
**Walter II has NO profile** — he runs as the base gateway service (no `--profile` flag).
His model is claude-fable-5 via anthropic direct.

### 5. GBrain

```bash
HOME=/home/itadmin gbrain stats && HOME=/home/itadmin gbrain orphans
```
✅ Embedded == Chunks, orphans == 0.

### 6. Disk/Memory

```bash
df -h / && free -h && uptime
```
Healthy: ≥50G free, ≥8G RAM free, load <2.0.

## Output Format

- 🔴 CRITICAL: breaks core function (browsers down, gateway dead)
- 🟡 WARNING: degraded but not blocking (stale config, delivery failures)
- 🟢 HEALTHY: passed

For each issue: what broke, impact, and exact fix command.