---
name: agent-to-agent-bridge
description: Talk directly to other AMG agents (Walter II, Ralph, Don, etc.) from Jay's session via a CLI bridge. Use when Joe asks Jay to coordinate with, relay to, or ask another agent something on the same machine.
triggers:
  - message another agent
  - talk to walter
  - agent bridge
  - set up a pipeline with another agent
  - let agent X talk to me
  - other agent cant reach me
---

# Agent-to-Agent Bridge

All AMG agents run as Hermes instances on one machine (user `itadmin`). They are
selected by the `HERMES_HOME` env var, NOT by separate binaries.

## Key facts
- **Walter II = the BASE/default instance** (no profile). `HERMES_HOME=/home/itadmin/.hermes`.
  Running plain `hermes chat -q` from Jay's env hits JAY, not Walter — you MUST override HERMES_HOME.
- Other agents are profiles under `/home/itadmin/.hermes/profiles/<name>`:
  jay, ralph, arnold, solo, don-ready, email-agent (=Stacey), amazon-agent (=Jeff), autumn, dori.
- The hermes binary: `/home/itadmin/.hermes/hermes-agent/venv/bin/hermes`
- A dead WebSocket bridge exists (`~/.hermes/agents/bridge/bridge.py`, port 8765) — 0 agents
  connected, don't rely on it. The CLI one-shot method below is what works.

## The helper (already installed)
`~/bin/ask-agent <agent> "message"` — sends a one-shot chat and prints the clean reply.
Agent aliases: walter, ralph, arnold, solo, don-ready, stacey, jeff, jay, or any profile name.

Example:
```sh
~/bin/ask-agent walter "Jay here. Status on the nightly backfill?"
```

## Manual invocation (if helper missing)
```sh
REAL=/home/itadmin
# Walter II (base):
env -u HERMES_HOME -u HERMES_SESSION_KEY HOME=$REAL HERMES_HOME=$REAL/.hermes \
  $REAL/.hermes/hermes-agent/venv/bin/hermes chat -q "your message"
# A profile agent (e.g. ralph):
env -u HERMES_HOME -u HERMES_SESSION_KEY HOME=$REAL HERMES_HOME=$REAL/.hermes/profiles/ralph \
  $REAL/.hermes/hermes-agent/venv/bin/hermes chat -q "your message"
```

## Enabling INBOUND bridge for another agent (so THEY can reach you) — 2026-06-17

Installing the helper alone is NOT enough. An agent only reaches others if the
capability is in its ALWAYS-INJECTED context. A handshake test where YOU hand it
the exact command will pass, but in the agent's own real sessions it won't know
the capability exists and will fall back to "I'd have to email a person." To
fully wire a target agent (example: autumn):

1. **Copy the helper** into the target's profile home bin (it's profile-agnostic
   — REAL=/home/itadmin is hardcoded, so the same script works for any agent):
   `cp ~/.hermes/profiles/jay/home/bin/ask-agent \
      /home/itadmin/.hermes/profiles/<agent>/home/bin/ask-agent && chmod +x ...`
2. **Add the bridge to the target's MEMORY.md** (path
   `/home/itadmin/.hermes/profiles/<agent>/memories/MEMORY.md`). This is the
   ONLY reliable channel — it's injected every turn. A skill alone won't work
   because the agent won't proactively load it. Spell out: other AMG agents are
   AI on the SAME machine (not people to email), the exact command
   `~/bin/ask-agent <agent> "msg"` (+ full-path fallback), the agent list, the
   "fresh one-shot, no memory, put ALL context in one message" rule, and a
   concrete example for the data they'll need.
   (Target agents may have a SOUL.md persona but NO mention of co-located agents
   — that's why they default to emailing. MEMORY.md overrides this.)
3. **Add `~/bin` to the target's `~/.bashrc`** (`export PATH="$HOME/bin:$PATH"`)
   so the short command resolves; many profiles have empty rc files with no PATH.
4. **Verify with a NO-HINT test**: ask the agent (as Joe would) to "ping <you>"
   WITHOUT giving the command. If it figures out the bridge on its own, it's
   wired. The earlier hand-fed test proves nothing.

LATENCY TRAP: a heavy request (e.g. asking Jay to run a full Tekion scrape via
the bridge) nests agents and can exceed the ~180s ask-agent timeout (exit 124).
A lightweight ping returns fast. For recurring data needs, DON'T have the agent
trigger a live scrape-and-wait — instead drop the data to a shared file on a
schedule (e.g. ~/the-goods/data/*.json) and have the agent read the file.

## Pitfalls
- **NO EMOJI in the message** (2026-07-04): emoji like ⚠️ carry Unicode variation selectors
  that trip the terminal security scanner (`tirith:variation_selector`) and block the command
  pending approval — fatal in headless cron runs. Use plain ASCII ("HARD STOP:", "WARNING:").
- Exit 124/empty reply = timeout, NOT proof the target failed — action asks can time out yet
  still complete. Verify with a fresh terse read-only ask before re-firing an action.
- Always `-u HERMES_HOME` (unset) before re-setting it; Jay's session env points HERMES_HOME at the jay profile.
- Also unset HERMES_SESSION_KEY so the target doesn't inherit Jay's Slack session binding.
- Each call is a FRESH session for the target agent — it has no memory of prior bridge messages.
  Put all needed context in the single message.
- Reply is wrapped in a `╭─ ⚕ Hermes ─╮` box; the helper strips it. Parse that box if doing it manually.
- Timeout: wrap in `timeout 100` — a cold agent init + reply takes ~6-15s, but tool-heavy replies can run longer.

## Enabling the REVERSE direction (make ANOTHER agent able to call YOU/others)
The helper above is OUTBOUND only — it lets Jay reach others. To let another agent
(e.g. Autumn) *initiate* contact requires THREE fixes, learned 2026-06-17 setting up
the Autumn↔Jay pipeline:

1. **Install the helper in the target's profile bin.** The script is profile-agnostic
   (`REAL=/home/itadmin` is hardcoded), so just copy it:
   ```sh
   mkdir -p /home/itadmin/.hermes/profiles/<agent>/home/bin
   cp /home/itadmin/.hermes/profiles/jay/home/bin/ask-agent \
      /home/itadmin/.hermes/profiles/<agent>/home/bin/ask-agent
   chmod +x /home/itadmin/.hermes/profiles/<agent>/home/bin/ask-agent
   ```
2. **Write the capability into the target's ALWAYS-ON MEMORY, not just a skill.**
   This is THE key lesson. Agents do NOT proactively load skills, and most profiles
   have NO system prompt telling them they're co-located with other agents — so in
   their real sessions they default to "I'd have to *email* a person named Jay."
   Append the bridge instructions (command + agent list + "they are AI agents on this
   same machine, NOT people you email" + a ready-made example) to
   `/home/itadmin/.hermes/profiles/<agent>/memories/MEMORY.md`. MEMORY.md is injected
   every turn; a skill is not. (`memory_enabled: true` in their config.yaml gates this.)
3. **Fix PATH.** Most profile `.bashrc` files do NOT add `~/bin`. Append
   `export PATH="$HOME/bin:$PATH"` to `<agent>/home/.bashrc`, AND in the memory entry
   give the FULL path fallback (`/home/itadmin/.hermes/profiles/<agent>/home/bin/ask-agent`)
   so it works regardless.

### Verifying the reverse bridge — test WITHOUT handing over the command
A handshake test where you tell the agent the exact command to run is MISLEADING — it
proves nothing. To truly verify, message the agent the way Joe would (zero hints), e.g.
"ping Jay and tell me what he says." If it figures out the bridge from memory and runs
it, the fix is real.

### Nesting timeout gotcha
A→B where B then calls back A spins up a THIRD nested agent. A cold, tool-heavy agent
(e.g. Tekion-capable Jay) booting inside the target's sandbox can blow the ~180s bridge
timeout on a full scrape-on-demand. Lightweight pings work instantly; heavy
scrape-and-wait may time out. **Preferred pattern for recurring data hand-offs:** don't
make the requesting agent trigger a live scrape and wait — have the data-owner drop a
shared file on a SCHEDULE (cron → JSON/CSV in `~/the-goods/data/`), and the requester
just reads the file instantly. No nesting, no timeout, always-fresh.
