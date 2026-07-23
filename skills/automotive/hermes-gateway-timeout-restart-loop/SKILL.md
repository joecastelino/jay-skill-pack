---
name: hermes-gateway-timeout-restart-loop
description: Diagnose and fix an AMG agent (Walter II/base or any profile) that is restarting/flaky with systemd "Failed with result 'timeout'" + status=9/KILL in the journal. Root cause is a hung LLM turn (e.g. gpt-5.5/Codex stall) holding an in-flight 300s API call that blocks clean shutdown past the 60s TimeoutStopSec, so systemd SIGKILLs the gateway and loops. This is NOT a crash, NOT out-of-credits, and the OpenRouter fallback can't save it. Covers how to tell this apart from a billing failure, the exact systemd-log signature, and the per-agent (and fleet-wide) drop-in fix.
triggers:
  - what is wrong with walter
  - walter keeps restarting
  - agent is flaky / timing out / dropping
  - Failed with result 'timeout'
  - status=9/KILL
  - gateway restart loop
  - agent stalled then restarted
  - SIGKILL hermes-gateway
---

# Hermes Gateway Timeout / SIGKILL Restart Loop

## When this skill applies (vs. the billing skill)
A Hermes agent goes flaky — it answers short pings fine but **dies on longer tasks**, and
the journal shows repeated restarts. If `~/bin/ask-agent <agent> "ping"` returns a clean
short reply, it is NOT down on billing — a 402/400 would fail even the ping. For a true
out-of-credits / wrong-model failure, use the **`hermes-agent-provider-switch`** skill
instead. This skill is for the **timeout/SIGKILL restart loop**, which the provider-switch
skill explicitly does not cover (and whose "agent down = usually billing" heuristic will
send you down the wrong path here).

## Step 0 — Map the units (don't guess the service name)
- Base instance = **Walter II** = `hermes-gateway.service`.
- Every other agent = `hermes-gateway-<profile>.service` (profiles observed 2026-06:
  amazon-agent, arnold, autumn, don-ready, dori, email-agent, jay, ralph, solo, tink).
```sh
systemctl --user list-units 'hermes*' --all --no-pager
```
`ACTIVE running` only means the *current* process is up — it says nothing about the
morning's restart history. Always read the journal next.

## Step 1 — Read the journal for the SIGNATURE (this is the whole diagnosis)
```sh
journalctl --user -u hermes-gateway.service --no-pager -n 200 \
  | grep -iE "Started|Stopping|Stopped|Failed with result|Main process exited|status=" | tail -25
```
**The tell — a STOP timeout, not a START timeout:**
```
Stopping hermes-gateway.service...
<60-65s later>
hermes-gateway.service: Main process exited, code=killed, status=9/KILL
hermes-gateway.service: Failed with result 'timeout'.
Started hermes-gateway.service...
```
`status=9/KILL` + `Failed with result 'timeout'` + ~60-65s between `Stopping...` and the
kill = systemd ran out of patience during **shutdown** and SIGKILLed the process. (Contrast:
a START timeout would say "start operation timed out". A clean code-1 exit during a restart
is just the old process making way for the new one — not this bug.)

## Step 2 — Confirm the credential is FINE (rule out billing)
Quick ping + check the active provider/token so you don't misdiagnose as billing:
```sh
timeout 100 ~/bin/ask-agent walter "Jay here, quick ping — reply one short line."
```
A clean reply here + the SIGKILL signature above = **timeout loop, not billing**. (If you
want to fully rule out credentials, decode `~/.hermes/auth.json` per the provider-switch
skill — for the base instance; a profile agent uses that profile's auth.json.)

## Step 3 — Understand the mechanism before fixing
- The agent's internal **stale-call timeout is 300s** (`run_agent.py`: "No response from
  provider for {N}s … Aborting call."). A stalled `gpt-5.5`/Codex turn holds an in-flight
  HTTP call for up to 300s.
- systemd's default **`TimeoutStopSec=60s`** is *shorter* than that 300s. So when a restart
  is issued while a turn is hung, shutdown can't complete in 60s → SIGKILL → "timeout" → loop.
- The configured **OpenRouter fallback** (`fallback_model:` in config.yaml, e.g.
  `z-ai/glm-5.2`) **cannot help** — failover fires on a *failed/empty response*, but here the
  problem is a *blocked shutdown*, not a failed response. Don't waste time "restoring the
  fallback"; it's already wired and irrelevant to this failure.

## Step 4 — The fix (per-agent drop-in; safe to apply fleet-wide)
Create a **SEPARATE** drop-in (do NOT edit existing ones — agents already carry e.g.
`stt-nemotron.conf`; systemd merges drop-ins):

`~/.config/systemd/user/hermes-gateway.service.d/timeout-hardening.conf`  (base = Walter)
or `~/.config/systemd/user/hermes-gateway-<profile>.service.d/timeout-hardening.conf`:
```ini
[Service]
TimeoutStopSec=330
Environment="HERMES_STREAM_READ_TIMEOUT=120"
```
- `TimeoutStopSec=330` (>300s) lets the agent's own stale-call timeout kill the hung turn
  *before* systemd loses patience → no more SIGKILL "timeout" loop.
- `HERMES_STREAM_READ_TIMEOUT=120` makes stalled turns abort at 120s and fail over to the
  OpenRouter fallback faster (also fixes the user-facing stall).

Then:
```sh
systemctl --user daemon-reload
# TimeoutStopSec takes effect IMMEDIATELY on reload — no restart needed.
# The env var applies on the agent's NEXT restart.
systemctl --user show hermes-gateway.service -p TimeoutStopUSec --value   # expect "5min 30s"
```

### Fleet-wide rollout (all agents share the same 60s default → same bug)
Write the same drop-in into each `hermes-gateway-<profile>.service.d/` dir, `mkdir -p` the
dir if needed, then a single `daemon-reload`. Verify every unit shows `TimeoutStopUSec=5min 30s`.
Do **NOT** mass-restart the fleet to push the env — the critical fix (stop-timeout) is live on
reload; the env applies on each agent's next natural restart. Mass-restarting interrupts
in-flight work for no urgent benefit.

## Step 5 — Verify
```sh
systemctl --user restart hermes-gateway.service   # only the agent you actively repaired
sleep 12
timeout 150 ~/bin/ask-agent walter "post-fix check — reply one line + which model you're on."
```
Clean one-line reply = done.

## Pitfalls / lessons (learned the hard way)
- **Don't jump to "billing/dead agent."** A short ping succeeding while long tasks die is the
  classic tell of a *timeout* problem, not credits. The provider-switch skill's "usually
  billing" rule is wrong for this failure mode.
- **Don't "restore the fallback" as the fix** — it's already configured and cannot catch a
  blocked-shutdown SIGKILL. Read the journal *first*; the signature is the diagnosis.
- **STOP timeout vs START timeout** are different: check the gap is between `Stopping...` and
  the kill (stop), not "start operation timed out" (start, which would need a longer
  `TimeoutStartSec` instead — observed default 90s).
- **Never edit an existing drop-in** to add this — add a separate `timeout-hardening.conf`;
  they merge. Clobbering `stt-nemotron.conf` would break fleet voice transcription.
- `TimeoutStopUSec=5min 30s` in `systemctl show` output = the 330s applied correctly.
